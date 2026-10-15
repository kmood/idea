# 技术实施计划：source-research

状态：规格已获用户批准（2026-10-15），本技术方案及 [任务清单](todo.md)待审阅。尚未开始实现。已完成资料模块的 [原计划](records-history/plan.md)与 [原任务](records-history/todo.md)已归档；本文件是当前活动计划。

## 目标、选型与明确限制

依据 [来源研究规格](../SPEC-source-research.md)，采用 [ADR-002](../docs/decisions/002-bounded-agent-research.md)的 Agent 协作 + Python 标准库 + 现有 SQLite 方案。不增加运行依赖、付费 API 或后台调度器，不切换正式研究入口。

首版的搜索与分析由当前 Agent 在现有工具环境中执行；本机 Python CLI 不能直接调用会话内 web 工具。协作协议是：领取预算/调用 ID → Agent 调用现有搜索工具 → 交回发现记录 → 受控 Reader 读取正文 → Agent 根据实际读取块提交分析 → 程序校验并发布。普通发现 JSON 不是已读证据；缺执行器或正文不可读时按规格返回 blocked/deferred。

不把人工准备好记录再 import 的演示称为自动研究。首版必须能在当前 Agent 会话执行真实的一轮协作流程；独立无人值守搜索程序不在本方案承诺内。

## 组件与依赖

- `src/research/`：contracts.py（请求/结果）、runner.py（有界轮次）、bridge.py（搜索/分析交接）、network.py（受控连接）、reader.py（正文块与凭据）、analysis.py（主张检查）、dedupe.py、publication.py、progress.py、coverage.py、cli.py。按切片引入，不预建空壳。
- `src/records/`：provider 扩展由此负责，详见 [扩展契约](../docs/records-research-extension.md)。runtime.py / publishing.py / migrations.py 等按职责加入；不让 research 直接操作 SQLite。
- `tests/research/` 与 `tests/records/` 分别验证研究行为和提供方兼容性；合成网页放 `tests/fixtures/research/`。真实试运行只写临时库和脱敏运行报告。
- `.local/research-cache/` 保存短期可见正文，默认七天过期；清理只针对程序记录的已完成任务缓存，不删研究记录、历史或待处理意图。缓存可重建，记录指纹与引用不可丢。

依赖顺序：兼容资料扩展 → 单轮恢复与执行权 → 预算 → 受控读取 → Agent 发现和分析 → 去重发布 → 游标/回顾 → CLI 与在线验收。共同基础按序实施，本计划不启动多个 Agent。

## 数据和兼容策略

Source/Evidence 使用可选严格字段；公开运行元数据使用 ResearchArtifact 的固定子类型，业务版本与旧证据保持不变。临时队列、调用预算、租约及缓存不导出。跨重启/跨导入去重依靠持久化定位键、公开发布意图和记录结果，不依靠标题或聊天记忆。

DB/公开包升级到 v2；旧业务版本和幂等摘要不重写。库升级在新副本中执行，包导入先验证 v1 或 v2 再处理 lineage。具体原子步骤、恢复检查和新字段见提供方扩展提案；该提案随本计划审阅，实施前更新提供方规格。禁止使用 legacy 字段装新采集元数据。

## 执行权、预算与恢复

执行权使用 SQLite 短事务中的 dbInstanceId + ownerId + fence + leaseUntil。默认租约 90 秒，每次 CLI 操作/读取前续租；单次外部读取最多 30 秒。Agent 思考超过租约时须 resume 重新领取，若另一轮占用则 busy。每次 publishStep 和进度变更都校验 fence，不能只在开始时检查。租约失效不得取消或覆盖已完成业务事务。

用持久 callId 先预占预算，再外部调用；网络不可提供“恰好一次”，所以丢失结果的调用仍耗预算，后续允许在剩余额度内重读。发布由稳定 operationId 提供幂等。执行租约信息不参与业务请求摘要，恢复后可回放原操作。

拟定默认运行参数（可配置，上限不要求耗尽）：

| 参数 | 默认值 | 行为 |
| --- | --- | --- |
| 搜索尝试 | 12 | 一个 query 是一次，批量工具调用按实际 query 数计数；重试也计数 |
| 具体讨论候选 | 10 | 逐项计候选；重新读取另计实际网络请求 |
| 辅助核验页 | 8 | 官方文档等不占讨论名额，但占总请求 |
| 全部外部调用/请求 | 40 | 搜索 query、正文、robots、重定向每跳与重试均计数 |
| 本机读取期限/搜索授权有效期 | 30 秒 | 本机读取覆盖 DNS、连接、TLS 和正文；搜索授权过期计为超时，迟到结果不直接发布 |
| 整轮期限 | 20 分钟 | 包含 Agent 交接等待；重启不重置原期限，续授需显式记录预算增量 |
| 同来源最小间隔 | 3 秒 | robots/服务器约束更严格则遵守；跨命令持久保存下次允许时间 |
| 临时故障重试 | 最多 1 次 | 同候选本轮内，计总预算；限流/权限不立即重试 |
| 重定向 | 最多 3 跳 | 每跳重新校验地址、robots、间隔与剩余额度 |
| 正文大小 | 2 MiB | 响应和解压后均有界；超限记 partial，不暗中截断为完整读取 |

本机 Reader 使用可终止工作进程，包含 DNS 阻塞也能截止。会话搜索工具若无取消接口，本机只能使授权到期、计数并拒收迟到结果，不能终止工具内部执行或承诺其费用停止；执行器等待工具返回后恢复轮次，不另外并发重试。

单轮过期只停止新外部操作与新分析，允许完成已开始的短保存事务并留下断点。取消由调用方设置；无无限循环/长睡眠。resume 默认只使用剩余预算；续授带单独稳定授权 ID，不能重试时重复加额度。

## Reader 与信任边界

仅 GET 公开 HTTP(S)，首版仅默认端口、无认证、无 Cookie、无用户提供的请求头或环境代理。解析目标后检查所有解析 IP，拒绝非公网地址及 IPv4 映射的非公网 IPv6；连接固定到已验证地址，同时保留原主机 Host/SNI 与证书验证，避免验证后重新 DNS 解析。所有重定向重复同样流程。测试网络替身通过显式测试依赖注入，不能靠生产开关放行 localhost。

robots 通过同一受控连接获取再 parse，不使用能绕过防护的自动 read；404/410 视为无文件，401/403/429 或暂时失败保守延期，缓存不超过一天。robots、下载和解析都有大小与期限限制；有登录/验证码迹象即 restricted，不尝试绕过。

首版支持 HTML/纯文本和明确包含正文的订阅条目，使用标准库解析非执行文本。去除脚本、样式和导航噪声，输出具有块 ID 的可见内容与截断说明；不能可靠分出正文时 deferred。不执行 JS、扩展附件或主动请求任意页面资源。日期和评论是否完整必须有解析依据；正文指纹只用于查找版本，不自动判断语义是否一致。

ReadReceipt 由 Reader 保存，分析入口只能引用已有 receiptId/块 ID，不能创建 receipt。采集文本的提示注入不改变 Agent 指令，也不执行文本中的命令。同一系统账号可直接改库的恶意代码不属于该能力隔离所能防护的范围。

## 判断、去重与发布

Agent 输入结构化 AnalysisDraft：处置类型、每项主张的性质/等级、引用块、独立性依据、反证与未知、目标对象/痛点/赚钱假设；来源和时间由已保存凭据绑定。程序核验必填项、引用实际可见、证据等级前置条件和发布字段白名单；Agent 负责判断内容含义，不能声称程序验证了现实世界真假。

精确身份优先来源 ID + 稳定帖/回复 ID，否则使用保守规范化 URL。原始 URL 始终保留；仅去掉列明跟踪参数，不改变未知参数。重复内容核对可见块和主张；不因广告/计数变动自动补证。语义相似只形成 possibleDuplicate；明确同一对象/问题/交付的重复经带理由的决定调用已有合并入口，变体保留。

先保存 PublicationManifest 和本地步骤意图，再按依赖发布 Source→Receipt/Evidence→Trend/Idea→关联→CandidateOutcome→SourceCheckpoint。每步正文与本地回执同事务；发布公开清单的步骤确认可重试。失败后先读取回执/操作结果，不能重造 ID。对同一稿重复执行只回放；稿件改变则保留旧意图并产生新稳定键。同步者只发布真实落盘结果，不以草稿或预占作为完成。

SourceCheckpoint 区分发现位置、连续处置位置和缺口集合。来源没有可靠顺序时采用已读集合+有限重叠，不使用时间假装完整游标。失败缺口不被后面的成功覆盖；旧帖新回复作为新内容版本。新机器缺缓存时先恢复公共发布清单/去重依据，再重读未完成项。

CoverageReview 由已完成轮次/来源/证据引用支持；程序拒绝仅条数或零新增作为转阶段依据。三轮无实质新证据时生成渠道回顾要求，Agent 交回有理由调整。输出阶段建议交调用方保存，本模块不自启后续轮次。

## 计划中的命令与验证

现有资料回归命令仍有效；下面 research 和 upgrade 命令是**拟实现接口**，当前不能运行，也未声称测试通过。

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_*.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/research -p 'test_*.py' -v
python3 -m compileall -q src/records src/research
PYTHONPATH=src python3 -m research --help
PYTHONPATH=src python3 -m research --db .local/rehearsal.sqlite3 run --input .local/run.json
PYTHONPATH=src python3 -m research --db .local/rehearsal.sqlite3 resume --input .local/resume.json
PYTHONPATH=src python3 -m research --db .local/rehearsal.sqlite3 request --input .local/action.json
PYTHONPATH=src python3 -m research --db .local/rehearsal.sqlite3 inspect --run-id RUN-EXAMPLE
PYTHONPATH=src python3 -m records upgrade --input .local/v1.sqlite3 --output .local/v2.sqlite3
```

run/resume 返回下一项有界动作或最终结果；request 支持 reserveSearch、submitDiscovery、readCandidate、submitAnalysis、publish、reviewCoverage、cancel 等明确动作，不接受任意函数名。会话执行器按返回动作驱动，操作人员无需逐条手工整理。分析/搜索交接缺失时返回可恢复 partial/blocked，不虚构输出。

R01–R19 的验收与依赖只在 [todo.md](todo.md) 勾选。每 2–3 项检查点运行已实现测试、审阅失败与限制并向用户报告，不因赶进度跳过失败。最后在线试验与离线测试分开记录；线上环境阻碍则相应任务保持未完成。

## 风险与边界

| 风险 | 对策 |
| --- | --- |
| 会话搜索工具无法被 Python 直接调用 | 显式 Agent 交接协议；不安装未经选择的 SDK，不声称独立搜索能力 |
| 动态页面覆盖不足 | 标注不支持，选择允许公开读取的替代来源，真实试运行报告覆盖范围 |
| v1/v2 历史或快照衔接出错 | 旧库副本迁移、旧 ID/摘要不变、基线兼容和外部变更回归 |
| 暂停进程恢复后仍写入 | 事务内 fence 检查；恢复备份后更换 dbInstanceId 并提升代号，拒绝旧凭证 |
| 部分发布造成重复或漏读 | 公共清单+稳定操作 ID+本机原子回执+缺口游标 |
| 普通探测制造 Git 噪声 | 私有运行域与公开实质事件分离；无变化正文不增版本 |

暂无需补充的产品问题。请审阅 Agent 协作方式、运行默认值、提供方扩展与切片顺序；批准后实施，不同步开展网站、精选算法或正式数据入口切换。
