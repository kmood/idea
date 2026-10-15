# 规格：资料与历史（records-history）

状态：用户于 2026-10-15 要求继续本规格后的技术方案与任务拆分，按批准记录；2026-10-15 已完成 records-history 实现与验收，正式资料未迁移。依赖：无。依据：[已确认意图](docs/intent/personal-opportunity-library.md)与[已批准能力划分](CAPABILITY-MAP.md)。本文件规定可验证的行为和模块边界，不预选数据库、框架或 HTTP 路由。

## 1. 目标与范围

为采集、评估、本地网站和调度提供统一的资料读写与历史契约。研究更新不能覆盖个人选择；重试不能重复入库；合并与更正不能使证据、历史或用户记录消失。

包括：来源、趋势、点子、证据、评估结果、个人操作、历史、导入导出及恢复。
不包括：网页采集实现、语义匹配算法、评分模型、UI、登录、定时器与 Git 网络推送。这些能力消费本模块结果，不自行建立另一份资料真相。

## 2. 已确认的默认方案

- 研究资料与可公开的分析可随仓库保存；收藏、忽略、准备验证和私人实验反馈仅在本机持久化，默认不进 Git。
- 同一局域网设备经本机服务读取同一份个人状态，不依赖各浏览器独立保存作为唯一副本。
- 研究数据有一个明确权威来源；数据库/索引若用于加速，必须声明是权威数据还是可重建副本，不能双向无规则覆盖。具体存储方案在技术计划中选择。
- 首版不提供永久删除研究记录；归档、失效、纠错和合并保留历史。误合并可由新修正事件解除关联，不擦掉原事件。
- 历史展示以 Asia/Shanghai 为默认；存储使用带时区的 ISO 8601 时间，未知原帖日期为 null，不能用抓取时间替代。

## 3. 数据契约

所有记录具备 schemaVersion、稳定 id、revision、createdAt、updatedAt。版本从 1 开始，仅实质变化递增；id 不随标题/分类改变，不从可修改内容推导。既有 CN01/GL01 等来源 ID 保留。

| 记录 | 必需信息 | 关键约束 |
| --- | --- | --- |
| Source | 名称、原始入口、受众/语言、访问状态、lastAttempt、lastSuccess | lastSuccess 可为空；访问失败不得推进成功时间/采样游标；可读入口和已读讨论分开 |
| Trend | 标题、变化摘要、证据关联、潜在影响及待验证问题 | 潜在影响可为推断，必须明确；无需强行填写商业模式 |
| Idea | 标题、服务对象、具体问题、可能赚钱方式、证据关联、行业/副业类型/市场、研究状态 | 商业路径允许明确标注的假设；入库不要求成交、成本或完整计划 |
| Evidence | sourceId、原始 URL、支撑的具体主张、摘要、发布时间或未知、访问时间、性质与等级 | 性质区分事实/作者声称/Agent 推断；反证标明所反驳的主张；推广/自述不能冒充已核验付款 |
| Assessment | ideaId、个人匹配结论、维度理由、未知项、依据证据 ID、生成时间 | 较适合/有条件适合/暂不适合/未知；成本区间须有币种与假设，未知不可编码成 0；不在本模块计算评分 |
| PersonalState | recordId、favorite、ignored、validationStage、notes、独立 revision | favorite 与 ignored 独立；validationStage 为未开始/准备验证/验证中/结束，不能自动推断成成功 |
| HistoryEvent | eventId、recordId、作用域、操作 ID、时间、执行者、事件类型、变更前后/可还原引用、原因与证据 | 研究与个人历史分域；纠错追加事件，不改旧事件；历史必须可由接口读取 |

证据等级遵循研究手册 E0–E3，但等级只描述其主张。需要支付信号时额外区分付费意向/采购或报价/已付款。已有事件引用的证据被更正后仍能查看当时版本。

研究状态独立于用户操作：待验证、候选、优先验证、搁置、淘汰；另设 archived、mergedInto 处理归档/合并。Agent 可更新研究状态，不能更改个人验证进度或实验结论。

## 4. 读写接口（逻辑契约）

类型定义：Id 为非空稳定字符串；Revision 为正整数；OperationId 为一次意图生成、重试复用的稳定字符串；Record 为上表带类型标签的数据；Page 包含 items 与 nextCursor；Result 统一为成功值或结构化错误。

| 操作 | 输入 | 输出/语义 |
| --- | --- | --- |
| readRecord | id、scope=research 或 personal | Record 与 revision；旧合并 ID 返回原条目及 canonicalId，不隐藏原历史 |
| listRecords | type、query、filters、cursor、limit（1–100，默认20） | Page；支持类型/行业/市场/证据/匹配/成本及未知值过滤；默认 updatedAt 降序、id 次序作为稳定次排序 |
| createResearch | record、operationId | 创建记录及首次历史；同 ID 不覆盖；验证来源/证据关联存在 |
| patchResearch | id、expectedRevision、patch、reason、operationId | 只改提供的允许字段；未知字段拒绝；禁止写个人字段 |
| saveAssessment | ideaId、assessment、expectedRevision、operationId | 保存外部评估结果与历史，不计算推荐算法 |
| setPersonalState | id、expectedRevision（首次为 null）、patch、operationId | 仅个人字段变化及个人历史；研究同步不能调用此操作来替用户做选择 |
| mergeRecords | sourceId、targetId、双方 expectedRevision、reason、operationId | 事务性建立合并关联和研究历史；保留两条记录/证据，不自动消除用户状态差异 |
| unmergeRecords | sourceId、targetId、双方 expectedRevision、reason、operationId | 解除指定合并关系并追加更正历史，保留原合并事件与双方记录 |
| linkDerivedIdea | trendId、ideaId、双方 expectedRevision、operationId | 建立 derivedFrom 关联并保留趋势；不是改掉趋势的 ID/类型 |
| listHistory | id、scope、cursor、limit | 按事件顺序分页；可包含关联旧 ID，个人历史仅本机授权读取 |
| exportResearch / importResearch | 版本化资料包 / 资料包+operationId | 仅研究资料、研究历史及所需操作去重信息；个人内容不在默认导出中 |
| backupLocal / restoreLocal | 本地备份目标 / 已校验备份 | 包含个人数据的本地一致性备份；恢复前验证并保留当前副本，禁止静默覆盖较新数据 |

个人状态尚未保存时，readRecord(personal) 对存在的研究记录返回默认 false/未开始/空备注与 revision=null；首次写入要求 expectedRevision=null 并原子创建 revision=1。研究记录不存在仍返回 NOT_FOUND。saveAssessment 使用评估记录自身版本，首次写入同样用 null；不改个人版本。

以上不是网络端点。后续 local-web 负责身份/局域网访问控制与页面呈现，本模块维护字段白名单和作用域隔离。

分页遇到并发更新允许重新查询；不承诺跨页固定快照，客户端按稳定 ID 去重。历史读取按单调事件序列分页，不依赖可能相同的时间戳。

返回格式示意（契约示例，不是真实采集结果；未指定语言）：
```json
{"ok": false, "error": {"code": "REVISION_CONFLICT", "message": "记录已更新，请重新读取", "recordId": "IDEA-EXAMPLE", "currentRevision": 3}}
```

错误码固定为 VALIDATION_ERROR、NOT_FOUND、REVISION_CONFLICT、DUPLICATE_ID、IDEMPOTENCY_CONFLICT、OPERATION_PENDING、SCOPE_VIOLATION、STORAGE_ERROR。错误不泄露凭据/私人正文；失败不得返回成功标志。

## 5. 一致性、重复与合并

- 一次成功修改必须同时持久化记录、历史和操作去重信息；中途失败不可出现数据已变但历史缺失。进程重启后也成立。
- 相同 operationId 与相同规范化请求返回原结果，不新增记录/历史；不同请求复用 ID 返回 IDEMPOTENCY_CONFLICT。未完成操作返回 OPERATION_PENDING，调用者不得因超时换 ID 重做。
- 操作结果判定、去重键占用必须有原子保障；实现方案必须处理崩溃后未决操作。首版不自动过期去重记录。
- patch 先比较 expectedRevision，不匹配时拒绝覆盖。两个设备同时修改个人状态，仅一个成功，另一方读取最新版本后重试。
- 个人 revision 与研究 revision 独立；Agent 补证不会造成个人选择丢失。无内容变化的 patch 不增加版本或业务历史，仍可记住操作结果。
- 合并禁止自指、循环与错误类型，首版只合并同类型条目。旧 ID 仍可查，来源/证据保留。
- 合并不把两个相互矛盾的用户状态静默合为一个；各旧 ID 状态保留，canonical 查询返回关联状态与冲突提示，由用户决定后另记事件。
- 搜索/列表默认收起已合并记录，但可按 ID 和历史访问；归档/淘汰可筛选，不等于永久删除。

## 6. 仓库迁移与恢复

现有 Markdown 目录和历史研究记录不得删除或无提示替换。迁移先预览映射，保留来源 ID；来源列表只有入口检查时不能升级为已核验具体讨论。空趋势/点子目录保持空，不造数据填充。

研究资料导入必须验证 schemaVersion、ID 唯一性、引用、历史版本和合并关系。完全相同导入应无变化；同 ID 不同历史分支标记冲突，不根据“文件较新”直接覆盖。坏文件整体失败或明确隔离，不能部分成功却不报告。

个人记录不进入研究导出。恢复测试需证明研究和个人数据均可保留，操作去重信息也恢复，避免恢复后再次执行旧操作。含个人数据的备份不进入 Git 或公开静态目录。

## 7. 结构、技术与风格

本规格批准后采用 Python 标准库 + SQLite + 公开 JSON 快照，技术决策见 ADR-001；实际操作和数据边界见 docs/records-operations.md。

现有：AGENTS.md、docs/intent/、docs/agent/、sources/、trends/、ideas/、research/。
拟新增职责目录（具体语言后缀在计划中确定）：src/records/ 数据契约与存储入口、tests/records/ 契约和故障测试、tests/fixtures/records/ 合成样例；私人存储路径与忽略规则必须在实现前明确。

接口字段使用 camelCase；稳定错误码使用 UPPER_SNAKE_CASE；只在输入边界进行完整校验。更新逻辑必须表达预期版本和操作 ID，不允许直接覆盖整条记录来模拟部分更新。历史、用户状态与研究内容不得通过同一个无作用域写入口任意修改。

## 8. 验收与测试策略

技术计划选定语言后确定测试框架和可执行命令；必须覆盖真实落盘、重启、并发与故障恢复，不能只 mock 存储。所有样例明确为合成数据，不写入正式点子库。不以覆盖率数字代替以下行为验收。

| 验收项 | 测试场景与预期 |
| --- | --- |
| 持久化 | 创建条目并收藏，重启后正文、来源、选择、历史一致 |
| 最小入库 | 无付费证据且成本未知的合法点子可入库；缺来源/对象/问题/赚钱假设则拒绝 |
| 证据纠错 | 追加反证/更正后能查看新旧结论和各自依据，未知日期仍为 null |
| 并发保护 | 两个请求带相同 revision 修改同一域，最多一个成功，另一个冲突；跨域个人选择不被研究更新覆盖 |
| 幂等恢复 | 相同请求重试/重启后重试只产生一次业务变化；同键不同请求被拒绝 |
| 崩溃恢复 | 在正文/历史提交边界注入故障，重启后要么全有要么全无，未决操作可解释 |
| 去重关联 | 合并保留旧 ID、所有证据/历史和用户记录；循环合并拒绝；误合并可追加解除事件 |
| 状态隔离 | Agent 无法将用户验证阶段改为完成；私有备注不出现在 research 导出及错误正文 |
| 查询 | 类型/行业/成本未知/证据/匹配组合筛选准确，空结果正常；历史分页无丢失 |
| 导入迁移 | 既有来源 ID 保留，重复导入不重复；冲突/坏引用明确报告，原文未丢失 |
| 备份恢复 | 本地备份恢复后用户记录完整，研究导出无个人字段，去重信息仍有效 |

实现后的验证命令：
```bash
PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_*.py' -v
python3 -m compileall -q src/records
git diff --check
```

2026-10-15：37 项测试、语法及真实 CLI 验证通过；原文迁移只在临时库演练。

## 9. 边界与待确认项

始终：保存来源与历史、校验关联、区分事实和假设、保护个人选择、报告未决失败；验收前完成实际落盘和恢复测试。
先确认：将私人记录同步到远程、永久删除历史、改变已批准的数据边界、破坏性迁移。
禁止：自动制造成交、未知记零、丢弃历史去重、推送凭据、把同步成功等同于业务验证成功。

已确认默认方案：个人操作/实验反馈只在本机保存并单独备份，研究资料通过仓库同步。后续技术计划需解决存储格式、并发/事务机制、导入导出与备份命令；这些实现选择不要求用户预先指定技术栈。

本规格已批准；[技术计划](tasks/plan.md)、[任务清单](tasks/todo.md)及 ADR-001 已批准并完成实施。实现仅覆盖本模块，不代表其他模块规格已批准。

实际接口、旧文日期精度约定及迁移切换条件见 [操作说明](docs/records-operations.md)。
