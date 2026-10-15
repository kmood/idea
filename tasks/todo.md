# source-research 实施任务

状态：规格、技术方案与本清单已批准（2026-10-16），正在实施。本文件是当前模块的唯一任务勾选位置，[资料模块旧清单](records-history/todo.md)已完整归档。

按红→绿顺序实施，每项先写与验收有关的失败测试，再实现和审阅。下面新增文件与命令均为计划，尚不存在。文件列表是代码/验证主要范围，若实现发现需跨越职责或显著超出五个文件，先重新拆分，不静默扩大切片。提供方公共契约与备份兼容在研究程序使用前完成。

## R01：在新副本升级旧资料库

- [x] 完成
- 依赖：无；预计范围：中（5 个主要文件）
验收：
- [x] 旧库保持原样，v2 副本可读写原记录且保留私人状态和去重信息；未知版本在任何写入前拒绝
- [x] 升级失败不留下可误用的半成品；提供方规格同步扩展边界
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_schema_upgrade.py' -v`。
涉及文件：`SPEC-records-history.md`、`src/records/migrations.py`、`src/records/storage.py`、`src/records/backup.py`、`tests/records/test_schema_upgrade.py`。

验证记录：2026-10-16，先确认 5 项新测试失败，实施后 records 全部 42 项通过。升级只开放 Python 接口；CLI 在 R17 接入。

## R02：兼容研究快照的格式升级

- [x] 完成
- 依赖：R01；预计范围：中（3 个主要文件）
验收：
- [x] v1 包校验后导入，旧 ID/事件/请求摘要不改写；首个 v2 包基线可核验
- [x] v2 往返字节稳定；旧检查点转换、外部快照变化及分叉仍被正确识别
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_bundle_versions.py' -v`。
涉及文件：`src/records/exchange.py`、`src/records/bundles.py`、`tests/records/test_bundle_versions.py`。

验证记录：2026-10-16，4 项格式用例中先确认 2 项失败，实施后 records 全部 46 项通过；v2 往返字节一致，旧基线和分叉检查保留。

## R03：保存来源档案与准确日期精度

- [ ] 完成
- 依赖：R02；预计范围：中（4 个主要文件）
验收：
- [ ] Source 可保存严格 profile；新 Evidence 精确时间或日级日期及依据往返保留
- [ ] 旧记录无需补字段；未知日期不填零或伪造时分，嵌套未知字段拒绝
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_observation_metadata.py' -v`。
涉及文件：`src/records/contracts.py`、`src/records/service.py`、`src/records/bundles.py`、`tests/records/test_observation_metadata.py`。

### 检查点：R03 后

- [ ] 运行现有 records 测试，以及已实现的 research 测试（该目录尚未建立时不伪称运行）；执行对应源目录 compileall 与 git diff --check。
- [ ] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

## R04：保存有类型的研究元数据

- [ ] 完成
- 依赖：R03；预计范围：中（5 个主要文件）
验收：
- [ ] ResearchArtifact 固定子类型有版本/历史并可导出重建；来源及证据关联可追溯
- [ ] 坏引用整批拒绝；普通 create 请求不能伪造 Reader 凭据；私人内容不进入允许字段
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_artifacts.py' -v`。
涉及文件：`src/records/artifacts.py`、`src/records/contracts.py`、`src/records/storage.py`、`src/records/bundles.py`、`tests/records/test_artifacts.py`。

## R05：保存并恢复一个研究轮次

- [ ] 完成
- 依赖：R04；预计范围：中（4 个主要文件）
验收：
- [ ] 稳定 runId 和请求摘要保存于本机运行域；重启可查实际状态和未完成意图
- [ ] 同键不同请求拒绝；新增运行表纳入本地备份但不进入公开研究包
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_runtime.py' -v`。
涉及文件：`src/records/runtime.py`、`src/records/storage.py`、`src/records/backup.py`、`tests/records/test_runtime.py`。

## R06：限定执行权与调用预算

- [ ] 完成
- 依赖：R05；预计范围：中（4 个主要文件）
验收：
- [ ] 两个执行者竞争只允许一个；过期后重新领取提升 fence，旧执行者不能改状态
- [ ] 预占调用、重试、deadline 和续授幂等可验证，丢响应不退额度，预算耗尽停止外部动作
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_runner.py' -v`。
涉及文件：`src/records/runtime.py`、`src/research/runner.py`、`src/research/contracts.py`、`tests/research/test_runner.py`。

### 检查点：R06 后

- [ ] 运行现有 records 测试，以及已实现的 research 测试（该目录尚未建立时不伪称运行）；执行对应源目录 compileall 与 git diff --check。
- [ ] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

## R07：实现有界公开网络读取

- [ ] 完成
- 依赖：R06；预计范围：小（2 个主要文件）
验收：
- [ ] 校验并固定公网 IP，Host/SNI 与证书校验正确；每次重定向重新验证
- [ ] robots、超时、大小限制、请求间隔可测试；拒绝内网/元数据/重绑定/认证与超限跳转
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_network.py' -v`。
涉及文件：`src/research/network.py`、`tests/research/test_network.py`。

## R08：生成实际正文读取凭据

- [ ] 完成
- 依赖：R07；预计范围：中（5 个主要文件）
验收：
- [ ] 真实读取器输出有定位的可见正文块、指纹、精度及截断状态，并通过资料层保存 receipt
- [ ] 标题/登录页/无法解析正文不变成需求证据；坏格式与提示注入不执行；缓存缺失可以重读
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_reader.py' -v`。
涉及文件：`src/research/reader.py`、`src/records/artifacts.py`、`src/records/runtime.py`、`tests/research/test_reader.py`、`tests/fixtures/research/public-thread.html`。

## R09：接通 Agent 搜索与候选队列

- [ ] 完成
- 依赖：R08；预计范围：中（4 个主要文件）
验收：
- [ ] Agent 领取 callId 后交回发现记录，先建档来源再排队，分页可检查候选状态
- [ ] 无工具时如实 blocked；搜索摘要和手写正文不能产生 receipt；迟到结果不越过执行权检查
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_bridge.py' -v`。
涉及文件：`src/research/bridge.py`、`src/research/runner.py`、`src/records/runtime.py`、`tests/research/test_bridge.py`。

### 检查点：R09 后

- [ ] 运行现有 records 测试，以及已实现的 research 测试（该目录尚未建立时不伪称运行）；执行对应源目录 compileall 与 git diff --check。
- [ ] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

## R10：验证分析稿并分流内容

- [ ] 完成
- 依赖：R09；预计范围：中（3 个主要文件）
验收：
- [ ] 真实凭据支撑的 AnalysisDraft 可分流 trend/idea/update/deferred/rejected；未知成本仍允许入库
- [ ] 块引用、事实/作者声称/推断、E2 独立性和 E3 核验依据检查生效；未读评论不计样本
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_analysis.py' -v`。
涉及文件：`src/research/contracts.py`、`src/research/analysis.py`、`tests/research/test_analysis.py`。

## R11：定位重复并保留变体

- [ ] 完成
- 依赖：R10；预计范围：中（4 个主要文件）
验收：
- [ ] 跨轮次定位键和内容版本关联原 ID；跟踪参数与内容参数区别处理
- [ ] 语义相似保留 possibleDuplicate；同源多点子不变成独立样本，旧帖新回复不被去重掉
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_dedupe.py' -v`。
涉及文件：`src/research/dedupe.py`、`src/records/identity.py`、`src/records/storage.py`、`tests/research/test_dedupe.py`。

## R12：原子发布一步研究结果

- [ ] 完成
- 依赖：R11；预计范围：中（4 个主要文件）
验收：
- [ ] publishStep 同一事务校验 fence、预期版本、精确身份并保存正文/历史/操作回放/本地回执
- [ ] 提交前故障全回滚，提交后丢响应回放；不接受个人字段和越权 Assessment/实验写入
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_publishing.py' -v`。
涉及文件：`src/records/publishing.py`、`src/records/service.py`、`src/records/storage.py`、`tests/records/test_publishing.py`。

### 检查点：R12 后

- [ ] 运行现有 records 测试，以及已实现的 research 测试（该目录尚未建立时不伪称运行）；执行对应源目录 compileall 与 git diff --check。
- [ ] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

## R13：恢复多步证据与点子发布

- [ ] 完成
- 依赖：R12；预计范围：中（3 个主要文件）
验收：
- [ ] PublicationManifest 先持久化目标 ID 和步骤，Source→证据→条目→关联可中断接续
- [ ] 证据已保存后中断仍显示 partial；恢复不重造记录，改稿有新意图且保留旧稿关联
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_publication.py' -v`。
涉及文件：`src/research/publication.py`、`src/records/runtime.py`、`tests/research/test_publication.py`。

## R14：维护缺口游标和有界重试

- [ ] 完成
- 依赖：R13；预计范围：中（5 个主要文件）
验收：
- [ ] 只有确认保存或明确无变化处置才推进连续位置；前失败后成功仍保留缺口
- [ ] 未知顺序使用已读集合；旧帖重叠、游标失效、限流和一次重试均可恢复且不超预算
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_progress.py' -v`。
涉及文件：`src/research/progress.py`、`src/research/runner.py`、`src/records/runtime.py`、`src/records/artifacts.py`、`tests/research/test_progress.py`。

## R15：生成有依据的覆盖回顾

- [ ] 完成
- 依赖：R14；预计范围：中（3 个主要文件）
验收：
- [ ] 回顾引用实际来源/轮次/发现，说明行业、人群、地域、副业模式和未覆盖领域
- [ ] 三轮无新证据要求渠道调整；条数/零新增不能单独触发转增量，不修改用户选择或自启下一轮
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_coverage.py' -v`。
涉及文件：`src/research/coverage.py`、`src/research/runner.py`、`tests/research/test_coverage.py`。

### 检查点：R15 后

- [ ] 运行现有 records 测试，以及已实现的 research 测试（该目录尚未建立时不伪称运行）；执行对应源目录 compileall 与 git diff --check。
- [ ] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

## R16：恢复完整运行状态与私人数据

- [ ] 完成
- 依赖：R15；预计范围：中（4 个主要文件）
验收：
- [ ] 新运行表、公开发布清单和私人历史完整备份恢复；重建后旧租约失效
- [ ] 丢缓存保守重读；仅导入公开包可找回已发布身份和断点但不伪造私人状态/未同步结果
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_research_recovery.py' -v`。
涉及文件：`src/records/backup.py`、`src/records/migrations.py`、`src/records/runtime.py`、`tests/records/test_research_recovery.py`。

## R17：提供可执行的 Agent 协作入口

- [ ] 完成
- 依赖：R16；预计范围：中（4 个主要文件）
验收：
- [ ] CLI 的 run/resume/request/inspect/help 由真实子进程验证；JSON 错误退出统一且无正文泄漏
- [ ] 操作指南明确现有搜索工具交接和 Reader 边界，不要求用户逐条整理；不实现后台调度
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_cli.py' -v`。
涉及文件：`src/research/cli.py`、`src/research/__main__.py`、`tests/research/test_cli.py`、`docs/source-research-operations.md`。

### 检查点：R17 后

- [ ] 运行现有 records 测试，以及已实现的 research 测试（该目录尚未建立时不伪称运行）；执行对应源目录 compileall 与 git diff --check。
- [ ] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

## R18：完成异常与并发整体验收

- [ ] 完成
- 依赖：R17；预计范围：中（3 个主要文件）
验收：
- [ ] 从发现到读取、分类、发布、恢复的合成全流程通过；所有规格场景有测试或明确在线验证位置
- [ ] 旧进程恢复、部分写入、跨格式快照、提示注入及私有标记回归通过；不跳过失败测试
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_acceptance.py' -v`。
涉及文件：`tests/research/test_acceptance.py`、`tests/research/test_adversarial.py`、`docs/source-research-operations.md`。

## R19：完成一轮真实公开来源试运行

- [ ] 完成
- 依赖：R18；预计范围：中（5 个主要文件）
验收：
- [ ] 当前 Agent 执行有界搜索→程序读取→引用分析→临时库发布，并区分成功、受限和未覆盖范围
- [ ] 验证导出/重导/恢复及正文不变性；更新交接状态，正式 Markdown 和定时写入入口不切换
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_acceptance.py' -v`。
涉及文件：`research/runs/source-research-pilot.md`、`docs/source-research-operations.md`、`AGENTS.md`、`research/STATE.md`、`tasks/todo.md`。

### 检查点：R19 后

- [ ] 运行现有 records 测试，以及已实现的 research 测试（该目录尚未建立时不伪称运行）；执行对应源目录 compileall 与 git diff --check。
- [ ] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

## 验收映射与完成边界

R01–R04：资料契约/格式兼容；R05–R06：持久断点、执行权和资源上限；R07–R09：公开读取、正文凭据与来源先行；R10–R11：准入/证据/去重；R12–R14：原子回执、多步恢复和缺口游标；R15：质量与覆盖回顾；R16：完整恢复与私人隔离；R17–R18：真实命令和异常验收；R19：在线可用性与交接。

R19 除测试命令外必须执行操作指南中的受限真实试运行，报告实际 runId、工具和程序读取范围、用量、公开记录结果及阻碍；不得把离线合成测试算作线上完成。若搜索/网络依赖不可用，则 R19 保持未完成并保留断点，不能宣称模块已经完成在线验收。

不以本清单批准替代正式数据库入口切换许可，不修改每日自动化目标或实现网站/个人匹配模型。
