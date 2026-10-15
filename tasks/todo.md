# records-history 任务清单

状态：用户于 2026-10-15 批准计划，按序执行。规格已批准；本文件是唯一任务勾选位置。下面路径与测试入口是拟新增/修改目标。

每项先编写有意义的失败测试，再实现最小行为。测试必须使用临时真实数据库；通用语法检查为 `python3 -m compileall -q src/records`，不替代功能测试。

## T01：保存并重新读取一个来源

- [x] 完成
- 依赖：无；预计范围：中（3–5文件）
验收：
- [x] 创建合法 Source 后关闭连接再打开，内容与首次历史一致
- [x] 非法字段/缺少入口拒绝；本机目录受 Git 忽略
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_source.py' -v`。
涉及文件：`src/records/contracts.py`、`src/records/storage.py`、`src/records/service.py`、`tests/records/test_source.py`、`.gitignore`。

## T02：更新来源时保护版本和重复请求

- [x] 完成
- 依赖：T01；预计范围：中（3–5文件）
验收：
- [x] 同意图重试只产生一次变化；相同键不同请求拒绝
- [x] 同版本并发更新至多一个成功，无变化 patch 不增业务版本
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_mutations.py' -v`。
涉及文件：`src/records/storage.py`、`src/records/service.py`、`tests/records/test_mutations.py`。

## T03：验证崩溃后的事务恢复

- [x] 完成
- 依赖：T02；预计范围：小（1–2文件）
验收：
- [x] 提交前故障后正文/历史/操作结果全回滚
- [x] 提交后响应丢失可回放；锁等待失败可解释且不假报成功
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_recovery.py' -v`。
涉及文件：`src/records/storage.py`、`tests/records/test_recovery.py`。

### 检查点：T03 后

- [x] 运行当前全部记录模块测试及语法检查，审阅通过的场景、失败与实际限制。
- [x] 向用户展示本阶段可运行结果；未经解决的问题不得通过跳过测试或弱化规格进入下一阶段。

## T04：保存带证据的趋势和点子

- [x] 完成
- 依赖：T03；预计范围：中（3–5文件）
验收：
- [x] 最小合法点子/趋势可保存，无成本/成交仍允许
- [x] 坏引用拒绝；补反证后保留旧证据版本与历史
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_evidence.py' -v`。
涉及文件：`src/records/contracts.py`、`src/records/service.py`、`src/records/storage.py`、`tests/records/test_evidence.py`。

## T05：保存个人选择且不被采集覆盖

- [x] 完成
- 依赖：T04；预计范围：中（3–5文件）
验收：
- [x] 初始 null revision 可保存，重启后收藏/忽略/验证阶段保留
- [x] 个人并发冲突有提示；研究入口拒绝个人字段写入
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_personal.py' -v`。
涉及文件：`src/records/personal.py`、`src/records/storage.py`、`src/records/contracts.py`、`tests/records/test_personal.py`。

### 检查点：T05 后

- [x] 运行当前全部记录模块测试及语法检查，审阅通过的场景、失败与实际限制。
- [x] 向用户展示本阶段可运行结果；未经解决的问题不得通过跳过测试或弱化规格进入下一阶段。

## T06：保存评估并按条件浏览

- [x] 完成
- 依赖：T05；预计范围：中（3–5文件）
验收：
- [x] 保存外部评估使用独立版本，不自动计算分数
- [x] 组合筛选及未知成本行为准确，列表/历史分页可重复验证
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_queries.py' -v`。
涉及文件：`src/records/queries.py`、`src/records/service.py`、`src/records/contracts.py`、`tests/records/test_queries.py`。

## T07：合并重复记录且保留用户分歧

- [x] 完成
- 依赖：T06；预计范围：中（3–5文件）
验收：
- [x] 合并/解除后旧ID与证据可查询，双方用户状态不丢失
- [x] 拒绝自指/循环/错类型/版本冲突；趋势派生链接不改原ID
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_relations.py' -v`。
涉及文件：`src/records/relations.py`、`src/records/storage.py`、`tests/records/test_relations.py`。

### 检查点：T07 后

- [x] 运行当前全部记录模块测试及语法检查，审阅通过的场景、失败与实际限制。
- [x] 向用户展示本阶段可运行结果；未经解决的问题不得通过跳过测试或弱化规格进入下一阶段。

## T08：导出可审阅且不含个人内容的快照

- [x] 完成
- 依赖：T07；预计范围：中（3–5文件）
验收：
- [x] 研究记录、版本、历史及研究操作结果可导出
- [x] 内容不变输出字节不变；私有标记不出现；写出失败旧快照完整
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_export.py' -v`。
涉及文件：`src/records/exchange.py`、`src/records/storage.py`、`tests/records/test_export.py`。

## T09：导入研究快照而不覆盖个人记录

- [x] 完成
- 依赖：T08；预计范围：中（3–5文件）
验收：
- [x] 空库可重建；同包重导无业务变化，个人选择保留
- [x] 坏包整批失败，分叉/本地未导出修改拒绝；操作回放信息仍有效
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_import.py' -v`。
涉及文件：`src/records/exchange.py`、`src/records/storage.py`、`tests/records/test_import.py`。

### 检查点：T09 后

- [x] 运行当前全部记录模块测试及语法检查，审阅通过的场景、失败与实际限制。
- [x] 向用户展示本阶段可运行结果；未经解决的问题不得通过跳过测试或弱化规格进入下一阶段。

## T10：备份和恢复到独立文件

- [x] 完成
- 依赖：T09；预计范围：小（1–2文件）
验收：
- [x] 含研究及个人信息的一致性备份可恢复，去重信息不丢
- [x] 坏备份拒绝；目标已存在拒绝；原库不被改写
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_backup.py' -v`。
涉及文件：`src/records/backup.py`、`tests/records/test_backup.py`。

## T11：预览现有 Markdown 迁移

- [x] 完成
- 依赖：T10；预计范围：中（3–5文件）
验收：
- [x] 生成保留原ID、原文引用及收录时间的预览；未知不补造
- [x] 无法解析字段明确报告，原文未修改，源摘要改变阻止应用旧预览
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_legacy.py' -v`。
涉及文件：`src/records/legacy.py`、`tests/records/test_legacy.py`、`tests/fixtures/records/legacy-source.md`、`tests/fixtures/records/legacy-idea.md`。

### 检查点：T11 后

- [x] 运行当前全部记录模块测试及语法检查，审阅通过的场景、失败与实际限制。
- [x] 向用户展示本阶段可运行结果；未经解决的问题不得通过跳过测试或弱化规格进入下一阶段。

## T12：提供可执行的资料管理入口

- [x] 完成
- 依赖：T11；预计范围：中（3–5文件）
验收：
- [x] CLI 包装 init/读写请求/导入导出/备份恢复/迁移预览，统一错误退出码
- [x] 真实子进程完成录入→收藏→补证→导出→恢复；输入来自文件且不打印私有正文到错误日志
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_cli.py' -v`。
涉及文件：`src/records/__main__.py`、`src/records/cli.py`、`tests/records/test_cli.py`、`README.md`。

## T13：完成模块交接与迁移演练

- [ ] 完成
- 依赖：T12；预计范围：中（3–5文件）
验收：
- [ ] 在临时库完成全部规格验收和当前资料迁移演练，正式原文与用户资料保持完整
- [ ] 记录可用命令和写入路径切换条件，未批准切换前不改定时任务数据入口
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_acceptance.py' -v`。
涉及文件：`tests/records/test_acceptance.py`、`docs/records-operations.md`、`AGENTS.md`、`research/STATE.md`、`tasks/todo.md`。

### 检查点：T13 后

- [ ] 运行当前全部记录模块测试及语法检查，审阅通过的场景、失败与实际限制。
- [ ] 向用户展示本阶段可运行结果；未经解决的问题不得通过跳过测试或弱化规格进入下一阶段。

## 完成映射

T01/T04：持久化与最小入库；T02/T03：并发/幂等/崩溃；T04：证据纠错；T05：个人隔离；T06：查询；T07：合并关联；T08/T09：导出及导入；T10：备份恢复；T11：旧资料迁移；T12/T13：真实入口与整体验收。
