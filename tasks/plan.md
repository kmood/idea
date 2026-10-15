# 技术实施计划：records-history

状态：用户于 2026-10-15 批准，执行中。依赖 [已批准规格](../SPEC-records-history.md)；任务勾选只在 [todo.md](todo.md) 维护。实现进度见任务清单。其他模块不在本轮实施范围。

## 技术与存储

采用 [ADR-001](../docs/decisions/001-local-records-storage.md) 的 Python 标准库 + 本机 SQLite + 研究 JSON 快照方案。现有 Python 3.14.4、SQLite 3.46.1 已核实；不在本轮升级运行时。

拟新增路径：
- src/records/：contracts.py（边界校验/错误）、storage.py（事务/建库）、service.py（研究操作）、personal.py、relations.py、queries.py、exchange.py、backup.py、legacy.py；按任务需要增加，不先建空壳。
- tests/records/：对应的契约、真实落盘、并发、故障和导入导出测试；合成样例与临时库不进入正式内容库。
- .local/：本机库、备份、临时请求；data/research.json：未来研究快照。

## 数据层设计

最小表族按能力逐步增加：research_records（id/kind/revision/payload）、evidence_links（引用关系）、record_versions（不可变研究版本）、research_events（事件序列）、personal_states/personal_events（私有）、Assessment 类型记录（独立版本，复用研究版本表）、operations（scope/key/requestHash/result）、metadata（schemaVersion/导入导出检查点）。索引由查询需要决定；不提前构建搜索引擎。

所有外键每连接显式启用，SQL 参数绑定。JSON 内部嵌套字段必须校验，历史引用保存 recordId+revision。存储字段可 snake_case，外部 JSON 保持规格 camelCase。后端代码使用类型注解和清晰函数边界，业务结果均走统一 Result，不靠异常文本决定行为。

读写入口按能力分开：ResearchStore 不暴露个人写入，PersonalStore 仅供用户交互层，调度/采集只获得研究入口。Python 接口隔离用于避免误调用，不声称隔离同一系统账号上的恶意代码。

## 原子、重复与并发

连接设置显式 autocommit=True，业务用 SQL BEGIN IMMEDIATE / COMMIT / ROLLBACK；不混用 Connection.commit 的不同语义。SQLite 默认回滚日志模式即可满足首版，暂不引入 WAL 文件运维；同步设置须保持安全默认，不降低持久性。

每次短事务依次：占用 scope+operationId 唯一键 → 比对请求摘要/回放已完成结果 → 核验 expectedRevision → 改数据与历史 → 记录结果 → 一起提交。无网络调用置于数据库事务中。请求摘要以规范化意图产生，不含本次尝试时间；不能从重试层重新生成 operationId。

已提交但响应丢失：同键回放；提交前进程退出：事务回滚，重试可重新执行。相同键不同内容拒绝。锁等待有界，建议五秒，超时返回 STORAGE_ERROR 与可重试说明，不猜测执行完成。只有确认存在进行中意图才返回 OPERATION_PENDING。首次 personal/assessment 使用 expectedRevision=null 并原子创建。

语义去重不由存储层自动猜测；这里只保证稳定 ID、操作幂等与明确合并事务。合并/解除合并检查类型、环与双方版本，保留旧记录及用户状态分歧。

## 查询、快照与导入

查询首版采用参数化筛选与大小写归一后的子串搜索，分页上限100，成本未知有独立条件；不实施语义向量检索。历史按本机单调 seq 分页；eventId 全局稳定。导入事件保持 eventId，重新分配本机 seq，保留来源顺序和时间。

导出在一致性读事务中取得研究记录/版本/事件/公开操作结果，按允许字段生成单个 JSON。写同目录临时文件、flush/fsync 后原子替换，再记录导出摘要。崩溃落在替换与标记之间时允许幂等重导出，不能宣称 DB 与 Git 文件一次事务提交。

快照包含 schemaVersion、bundleId（由规范化内容摘要产生）、baseBundleId 和研究数据；只有研究内容变化才推进包版本。相同包重复导入无变化。导入先完整校验：坏引用/重复 ID/版本断裂/合并环都整批拒绝。空库可导入；有数据时要求来自已知共同基线且本地研究没有未导出/未同步变更；遇到分叉只报告，不自动按时间戳选赢家。个人域不参加研究替换。

导入检查点/导出摘要放本机 metadata，不作为业务事件反复写入包。import 操作本身的去重结果保存在本机，不将包导入动作再次导出造成自引用；包内携带研究变更操作的去重结果。导出/导入结果标明保存范围，Git 推送留给 scheduled-sync。

## 迁移与备份

legacy 入口读取受支持的现有 Markdown，生成预览包与源文件摘要，不能静默忽略无法解析内容；若格式不支持，报待人工映射字段。预览应用时再核对摘要，期间有研究更新则重做预览；保留原文及已知来源 ID。导入时间与原始首次收录时间分开。

backup 使用 SQLite backup API 生成新文件并校验 integrity_check、foreign_key_check、版本/引用及关键行数。restore 仅写入不存在的新目标，默认禁止覆盖；恢复后比对历史和去重信息。只有在完整迁移演练和显式切换后才更新 Agent 的正式写入路径，当前自动研究仍采用现有 Markdown。

## 验证命令（待相应任务实现后执行）

以下都是计划中的入口，当前不存在应用代码，不把它们列为已通过检查。命令在仓库根执行：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_*.py' -v
python3 -m compileall -q src/records
PYTHONPATH=src python3 -m records --help
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 init
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 export --output data/research.json
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 import --input data/research.json --operation-id import-approved-bundle
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 backup --output .local/backups/manual.sqlite3
PYTHONPATH=src python3 -m records restore --input .local/backups/manual.sqlite3 --output .local/restored.sqlite3
PYTHONPATH=src python3 -m records legacy-preview --root . --output .local/legacy-preview.json
```

operation-id 示例必须对应一次具体导入，重试同意图复用，其他意图换新值。测试用临时目录，不执行示例 init/import 改正式库。unittest 为 [Python 标准测试框架](https://docs.python.org/3.14/library/unittest.html)。此模块不打包前端，无网页开发命令；compileall 仅语法检查，不能替代功能测试。

## 实施顺序与检查点

任务 T01–T13 见 todo：最小来源落盘 → 版本/故障保护 → 点子与证据 → 私人状态 → 评估查询 → 合并关系 → 公开导出 → 安全导入 → 备份恢复 → 旧文预览 → CLI 与交接。每个功能从入口走到实际存储及验证，不先实现所有表再补业务。

共享基础存储按顺序实现；本计划不启动多个 Agent。每2–3项设置检查点，问题未解决不得降低规格门槛。最终必须覆盖规格第8节全部验收场景，才标模块完成。

## 风险与处理

| 风险 | 处理 |
| --- | --- |
| 公私数据同库，错误导出可能泄露 | 允许字段导出、独立作用域、含唯一私有标记的反向检查；禁止原始 dump 同步 |
| DB 与 Git 快照不同步 | 明确检查点/未导出状态；先导入冲突检查，再工作，再导出；失败后重试同意图 |
| 定时研究与迁移同时修改 | 源摘要校验；正式切换前重扫变化，不能覆盖新资料 |
| 并发与进程中断损坏历史 | SQLite 事务、预期版本、真实多进程终止/恢复测试 |
| 备份也含私有信息 | 本地非静态目录，忽略 Git，备份/恢复都校验，恢复到新文件 |

## 审阅点

建议采用上述单机存储方案及任务顺序。产品数据边界已确认，暂无需要补充的产品问题；技术计划已批准。从 T01 开始，不顺带实现网站或其他模块。
