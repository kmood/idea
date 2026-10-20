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

- [x] 完成
- 依赖：R02；预计范围：中（4 个主要文件）
验收：
- [x] Source 可保存严格 profile；新 Evidence 精确时间或日级日期及依据往返保留
- [x] 旧记录无需补字段；未知日期不填零或伪造时分，嵌套未知字段拒绝
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_observation_metadata.py' -v`。
涉及文件：`src/records/contracts.py`、`src/records/service.py`、`src/records/bundles.py`、`tests/records/test_observation_metadata.py`。

### 检查点：R03 后

- [x] 运行现有 records 测试，以及已实现的 research 测试（该目录尚未建立时不伪称运行）；执行对应源目录 compileall 与 git diff --check。
- [x] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

验证记录：2026-10-16，5 项元数据用例先验证缺失能力及 URL 校验错误；修复后 51 项 records 测试、compileall 和 diff --check 通过。research 尚无实现，不声称运行该测试目录。备份格式判定涉及 backup.py 一行行为修改，为第五个实现/验证文件。

## R04：保存有类型的研究元数据

- [x] 完成
- 依赖：R03；预计范围：中（5 个主要文件）
验收：
- [x] ResearchArtifact 固定子类型有版本/历史并可导出重建；来源及证据关联可追溯
- [x] 坏引用整批拒绝；普通 create 请求不能伪造 Reader 凭据；私人内容不进入允许字段
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_artifacts.py' -v`。
涉及文件：`src/records/artifacts.py`、`src/records/contracts.py`、`src/records/storage.py`、`src/records/bundles.py`、`tests/records/test_artifacts.py`。

验证记录：2026-10-19，7 项元数据/凭据边界用例；全量 58 项 records 测试、compileall、diff --check 通过。Reader 专用能力使用合成凭据测试，实际网络读取尚待 R07/R08；导入/恢复属于可信资料恢复入口，不等同于新的读取证明。

## R05：保存并恢复一个研究轮次

- [x] 完成
- 依赖：R04；预计范围：中（4 个主要文件）
验收：
- [x] 稳定 runId 和请求摘要保存于本机运行域；重启可查实际状态和未完成意图
- [x] 同键不同请求拒绝；新增运行表纳入本地备份但不进入公开研究包
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_runtime.py' -v`。
涉及文件：`src/records/runtime.py`、`src/records/storage.py`、`src/records/backup.py`、`tests/records/test_runtime.py`。

验证记录：2026-10-19，4 项持久化/备份用例；全量 62 项 records 测试、编译与差异检查通过。运行表按需在提供方短事务中创建，未改普通资料构造路径；执行权与预算由 R06 接入。

## R06：限定执行权与调用预算

- [x] 完成
- 依赖：R05；预计范围：中；实施拆为提供方执行权/预算与研究层运行器两个提交
验收：
- [x] 两个执行者竞争只允许一个；过期后重新领取提升 fence，旧执行者不能改状态
- [x] 预占调用、重试、deadline 和续授幂等可验证，丢响应不退额度，预算耗尽停止外部动作
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_runner*.py' -v`。
涉及文件：提供方核心拆入 `src/records/execution.py`，由 runtime.py 接入，storage.py 增加事务内 guard；backup.py 提前接入 R16 的恢复身份失效部分，避免提交已知旧凭证漏洞。现有 test_runtime.py 适配租约参数，test_runner.py 验证执行权/预算；研究层 contracts.py、runner.py 与 test_runner_facade.py 单独提交。

### 检查点：R06 后

- [x] 运行现有 records 测试，以及已实现的 research 测试（该目录尚未建立时不伪称运行）；执行对应源目录 compileall 与 git diff --check。
- [x] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

验证记录：2026-10-20，62 项 records + 10 项 research 测试、compileall 与 diff --check 通过。并发连接竞争只产生一个持有者；start 重试不重置截止时间；损坏超额账本不能备份。真实网络、搜索和分析尚未接入。

## R07：实现有界公开网络读取

- [x] 完成
- 依赖：R06；实施拆分：R07a 受控连接/可终止进程（network.py 与 test_network_transport.py），R07b robots、预算和跨命令间隔（fetcher.py、records/network_policy.py、runtime.py 备份接入及 test_network.py）。原两文件估计不足以保持研究层不直接访问 SQLite。
验收：
- [x] 校验并固定公网 IP，Host/SNI 与证书校验正确；每次重定向重新验证
- [x] robots、超时、大小限制、请求间隔可测试；拒绝内网/元数据/重绑定/认证与超限跳转
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_network*.py' -v`。
涉及文件：`src/research/network.py`、`tests/research/test_network.py`。

验证记录：2026-10-20，13 项网络用例覆盖固定连接、TLS 原域名、阻塞进程终止、压缩体、robots/重定向、Retry-After、跨实例间隔及备份。全量 62 records + 23 research 通过。在线临时库试读 Python 官方文档时，系统 DNS 返回 198.18.0.135（非公网测试网段），因此在首个 robots 请求的地址检查阶段拒绝，未绕过；该限制留给 R19 在线验收处理，不声称读到了正文。

## R08：生成实际正文读取凭据

- [x] 完成
- 依赖：R07；实际拆分：正文解析、Reader 编排、资料事务与本机缓存指针；独立文件避免将网络解析混入资料契约。新增缓存忽略规则与操作说明。
验收：
- [x] 真实读取器输出有定位的可见正文块、指纹、精度及截断状态，并通过资料层保存 receipt
- [x] 标题/登录页/无法解析正文不变成需求证据；坏格式与提示注入不执行；缓存缺失可以重读
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_reader.py' -v`。
补充文件：`src/research/document.py`、`src/records/readings.py`、`.gitignore`、`docs/research-reader.md`。
涉及文件：`src/research/reader.py`、`src/records/artifacts.py`、`src/records/runtime.py`、`tests/research/test_reader.py`、`tests/fixtures/research/public-thread.html`。

## R09：接通 Agent 搜索与候选队列

- [x] 完成
- 依赖：R08；实际范围：交接接口与独立 discovery 资料适配器；抽出 execution 事务内方法，使预算与队列原子提交，补充本机备份验证和来源创建执行权守卫。
验收：
- [x] Agent 领取 callId 后交回发现记录，先建档来源再排队，分页可检查候选状态
- [x] 无工具时如实 blocked；搜索摘要和手写正文不能产生 receipt；迟到结果不越过执行权检查
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_bridge.py' -v`。
补充文件：`src/records/discovery.py`、`src/records/execution.py`、`src/records/service.py`、`docs/research-agent-bridge.md`。
涉及文件：`src/research/bridge.py`、`src/research/runner.py`、`src/records/runtime.py`、`tests/research/test_bridge.py`。

### 检查点：R09 后

- [x] 运行现有 records 测试，以及已实现的 research 测试（该目录尚未建立时不伪称运行）；执行对应源目录 compileall 与 git diff --check。
- [x] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

## R10：验证分析稿并分流内容

- [x] 完成
- 依赖：R09；实际范围：分析契约、引用校验与测试；补充 discovery 单候选查询，避免研究层直接访问 SQLite。
验收：
- [x] 真实凭据支撑的 AnalysisDraft 可分流 trend/idea/update/deferred/rejected；未知成本仍允许入库
- [x] 块引用、事实/作者声称/推断、E2 独立性和 E3 核验依据检查生效；未读评论不计样本
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_analysis.py' -v`。
补充文件：`src/records/discovery.py`、`docs/research-analysis.md`。
涉及文件：`src/research/contracts.py`、`src/research/analysis.py`、`tests/research/test_analysis.py`。

## R11：定位重复并保留变体

- [x] 完成
- 依赖：R10；实际范围：去重接口、公开身份查询与测试；直接从公开凭据/处置/关系恢复定位，不新增本机身份表，也不更改 storage。
验收：
- [x] 跨轮次定位键和内容版本关联原 ID；跟踪参数与内容参数区别处理
- [x] 语义相似保留 possibleDuplicate；同源多点子不变成独立样本，旧帖新回复不被去重掉
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_dedupe.py' -v`。
操作说明：`docs/research-deduplication.md`。
涉及文件：`src/research/dedupe.py`、`src/records/identity.py`、`tests/research/test_dedupe.py`。

## R12：原子发布一步研究结果

- [x] 完成
- 依赖：R11；实际范围：共享资料保存内核、fenced 发布接口、运行回执完整性和故障/恢复测试；未修改 storage schema。
验收：
- [x] publishStep 同一事务校验 fence、预期版本、精确身份并保存正文/历史/操作回放/本地回执
- [x] 提交前故障全回滚，提交后丢响应回放；不接受个人字段和越权 Assessment/实验写入
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_publishing.py' -v`。
操作说明：`docs/research-publishing-step.md`。
涉及文件：`src/records/publishing.py`、`src/records/service.py`、`src/records/runtime.py`、`tests/records/test_publishing.py`。

### 检查点：R12 后

- [x] 运行现有 records 测试，以及已实现的 research 测试（该目录尚未建立时不伪称运行）；执行对应源目录 compileall 与 git diff --check。
- [x] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

## R13：恢复多步证据与点子发布

- [x] 完成
- 依赖：R12；实际范围：中；拆分为本机发布计划、公开清单和研究层恢复编排，并补充公开身份查询与反证类型，避免摘要承诺与实际请求漂移。
验收：
- [x] PublicationManifest 先持久化目标 ID 和步骤，Source→证据→条目→关联可中断接续
- [x] 证据已保存后中断仍显示 partial；恢复不重造记录，改稿有新意图且保留旧稿关联
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_publication.py' -v`。
操作说明：`docs/research-publication.md`。
涉及文件：`src/research/publication.py`、`src/research/analysis.py`、`src/research/runner.py`、`src/records/publishing.py`、`src/records/runtime.py`、`src/records/identity.py`、`tests/research/test_publication.py`、`tests/research/test_analysis.py`。

验证记录：2026-10-20，9 项发布恢复用例覆盖清单先行、部分发布、本地备份、提交后确认丢失、清单承诺冲突、改稿 supersedes、反证、既有条目更新及旧执行者拒绝；全量 69 项 records + 56 项 research 测试、编译与差异检查通过。公开包缺少本机请求计划时不从摘要猜测正文，留给 R16 保守恢复；正式研究入口未切换。

## R14：维护缺口游标和有界重试

- [x] 完成
- 依赖：R13；实际范围：中；本机进度适配器保存序列/尝试状态，研究层只从已落盘 CandidateOutcome 推进公开 SourceCheckpoint。
验收：
- [x] 只有确认保存或明确无变化处置才推进连续位置；前失败后成功仍保留缺口
- [x] 未知顺序使用已读集合；旧帖重叠、游标失效、限流和一次重试均可恢复且不超预算
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_progress.py' -v`。
操作说明：`docs/research-progress.md`。
涉及文件：`src/research/progress.py`、`src/research/runner.py`、`src/records/progress.py`、`src/records/runtime.py`、`tests/research/test_progress.py`。

验证记录：2026-10-20，6 项进度用例覆盖连续缺口、无序集合、重叠/失效游标、限流/单次重试、Outcome 绑定及备份恢复；全量 69 项 records + 62 项 research 测试、编译与差异检查通过。进度层不预占或返还额度，每次真实外部尝试仍由 execution 账本强制计数；正式研究入口未切换。

## R15：生成有依据的覆盖回顾

- [x] 完成
- 依赖：R14；实际范围：中；新增结构化覆盖维度、运行证据计数和公开引用校验，旧 CoverageReview 仍可读取。
验收：
- [x] 回顾引用实际来源/轮次/发现，说明行业、人群、地域、副业模式和未覆盖领域
- [x] 三轮无新证据要求渠道调整；条数/零新增不能单独触发转增量，不修改用户选择或自启下一轮
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_coverage.py' -v`。
操作说明：`docs/research-coverage.md`。
涉及文件：`src/research/coverage.py`、`src/research/runner.py`、`src/records/artifacts.py`、`src/records/identity.py`、`tests/research/test_coverage.py`。

验证记录：2026-10-20，4 项覆盖回顾用例覆盖维度/引用归属、三轮空窗调整、增量准入、幂等发布及公开包往返；全量 69 项 records + 66 项 research 测试、编译与差异检查通过。建议只作为公开研究结论保存，不修改个人状态、不切换阶段且不启动新轮次。

### 检查点：R15 后

- [x] 运行现有 records 测试，以及已实现的 research 测试；执行对应源目录 compileall 与 git diff --check。
- [x] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

## R16：恢复完整运行状态与私人数据

- [x] 完成
- 依赖：R15；实际范围：中；在既有动态备份校验上增加保守恢复清单，不复制正文缓存，也不从公开摘要重建私有请求。
验收：
- [x] 新运行表、公开发布清单和私人历史完整备份恢复；重建后旧租约失效
- [x] 丢缓存保守重读；仅导入公开包可找回已发布身份和断点但不伪造私人状态/未同步结果
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_research_recovery.py' -v`。
操作说明：`docs/research-recovery.md`。
涉及文件：`src/records/migrations.py`、`src/records/runtime.py`、`tests/records/test_research_recovery.py`。

验证记录：2026-10-20，2 项恢复用例覆盖现有运行表、私人历史、旧租约失效、缓存缺失重读、稳定 receipt ID、部分发布续接及仅公开包降级；完整测试与检查见本次提交记录。正式研究入口未切换。

## R17：提供可执行的 Agent 协作入口

- [x] 完成
- 依赖：R16；实际范围：中；新增严格 JSON 文件 CLI 和明确动作白名单，复用现有 Runner/Bridge/Reader/Analyzer/Publication/Coverage 边界。
验收：
- [x] CLI 的 run/resume/request/inspect/help 由真实子进程验证；JSON 错误退出统一且无正文泄漏
- [x] 操作指南明确现有搜索工具交接和 Reader 边界，不要求用户逐条整理；不实现后台调度
验证：`PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_cli.py' -v`。
涉及文件：`src/research/cli.py`、`src/research/__main__.py`、`tests/research/test_cli.py`、`docs/source-research-operations.md`。

验证记录：2026-10-20，2 项真实子进程用例覆盖帮助、启动、来源先行、搜索预占/交回、候选检查、恢复及输入不回显；完整测试与检查见本次提交记录。搜索仍由当前会话 Agent 显式执行，未增加后台调度。

### 检查点：R17 后

- [x] 运行现有 records 测试，以及已实现的 research 测试；执行对应源目录 compileall 与 git diff --check。
- [x] 审阅场景覆盖、失败和限制并向用户报告可运行结果；未解决问题不得通过跳过测试进入下一阶段。

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
