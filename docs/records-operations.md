# 资料与历史模块操作说明

2026-10-15：T01–T13 已实现并验收。Python 3.14 标准库，无第三方运行依赖；实测 Python 3.14.4 / SQLite 3.46.1。模块提供本机库和 CLI，不提供网页、登录或网络监听。

## 当前数据入口

正式研究仍写 `sources/`、`ideas/`、`trends/`、`research/` 下的 Markdown。当前没有创建正式 `.local/records.sqlite3`，没有切换每日研究任务，没有生成正式 `data/research.json`。本次迁移、恢复、CLI 验收只使用临时目录。

切换后 SQLite 是运行时写入权威；研究 JSON 是显式导出检查点，不能作为另一份无规则覆盖的写入口。个人选择、私人历史、私人操作结果仅在本机库；Git 备份研究资料不能代替本地完整备份。

## 验证和入口

在仓库根目录执行：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/records -p 'test_*.py' -v
python3 -m compileall -q src/records
PYTHONPATH=src python3 -m records --help
```

以下命令是实际可用入口；示例会创建本机数据，采用前先按下方切换步骤核对：

```bash
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 init
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 status
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 request --scope research --input .local/request.json
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 request --scope personal --input .local/personal-request.json
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 export --output data/research.json
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 import --input data/research.json --operation-id import-this-bundle
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 backup --output .local/backups/manual.sqlite3
PYTHONPATH=src python3 -m records restore --input .local/backups/manual.sqlite3 --output .local/restored.sqlite3
```

`status` 返回研究是否有未导出变更、上次包 ID、研究记录数及个人状态数，不返回私人正文。JSON 成功为 `{"ok":true,"value":...}`，退出码 0；失败为 `{"ok":false,"error":...}`，退出码 2。`--help` 输出命令说明。输入只接受 UTF-8 JSON 对象，拒绝重复键和非有限数字；错误不回显请求正文。

## 请求契约

外部字段 camelCase，Python 方法 snake_case。完整字段白名单见 `src/records/contracts.py`，逻辑行为见已批准规格。创建记录时提供 `id`、`kind` 和该类型必填字段；schemaVersion、revision、createdAt、updatedAt、archived、mergedInto 由模块产生。没有永久删除接口。

合成 Source 请求（不是新研究资料）：

```json
{"action":"createResearch","operationId":"demo-create-source","record":{"id":"DEMO-SOURCE","kind":"Source","name":"合成来源","url":"https://example.com/","audience":["测试"],"languages":["zh"],"accessStatus":"untried","lastAttempt":null,"lastSuccess":null}}
```

已有条目的个人选择请求：

```json
{"action":"setPersonalState","id":"IDEA-20261015-001","expectedRevision":null,"patch":{"favorite":true,"validationStage":"准备验证"},"operationId":"user-favorite-this-idea"}
```

首次个人状态 expectedRevision 为 null，后续必须使用读回的个人 revision。favorite 和 ignored 独立；没有写入时返回 false/false/未开始/空备注。PersonalStore 是本地用户交互入口，研究入口拒绝这些字段；这不构成对同一系统账号恶意代码的安全隔离。局域网身份验证属于尚未实现的 local-web。

| scope | action | 参数（除 action） |
| --- | --- | --- |
| research | createResearch | record、operationId |
| research | patchResearch | id、expectedRevision、patch、reason、operationId |
| research | readRecord | id、可选 revision |
| research | listRecords | 可选 kind、query、filters、cursor、limit |
| research | listHistory | id、可选 cursor、limit |
| research | saveAssessment | ideaId、assessment、expectedRevision、operationId |
| research | mergeRecords / unmergeRecords | sourceId、targetId、sourceRevision、targetRevision、reason、operationId |
| research | linkDerivedIdea | trendId、ideaId、trendRevision、ideaRevision、operationId |
| personal | readRecord / relatedStates | id |
| personal | setPersonalState | id、expectedRevision、patch、operationId |
| personal | listHistory | id、可选 cursor、limit |

Assessment 复用研究记录及版本表，ID 为 `assessment:<ideaId>`，独立 revision；不修改点子正文或个人版本。必须使用 saveAssessment 更新；读取评估历史用该 ID。fit 枚举为较适合/有条件适合/暂不适合/未知；reasons 是维度→理由对象；unknowns、evidenceIds 是列表；generatedAt 为带时区时间。cost 为 null 或 `{min,max,currency,assumptions}`，不自动计算分数。

Evidence 的 nature 为 fact / author_claim / inference；paymentSignal 为 null / intent / quote / paid。E3 要求 fact 和非空支付信号，作者自述不能直接升级；程序只校验结构，研究者仍须核实具体主张。Trend 的 impact 为 `{nature,text}`。Idea 的行业、sideHustleTypes、markets 为列表，researchStatus 与个人验证阶段独立。

筛选示例：`{"action":"listRecords","kind":"Idea","filters":{"industry":"电商运营","market":"海外","evidence":"E2","costUnknown":true},"limit":20}`。还支持 sideHustleType、fit、maxCost（须同时给 currency）、archived、includeMerged、researchStatus。未知成本不算 0；默认收起已合并项。分页 cursor 是整数，列表允许并发更新后重新查询，按稳定 ID 去重；历史按 seq 分页。个人合并分歧通过 relatedStates 返回，研究查询不泄露私人状态。

## 同步与恢复

- 同一个意图的重试必须复用 operationId。相同键不同请求返回 IDEMPOTENCY_CONFLICT；正常失败事务回滚，可重试原意图。锁等待默认最多约 5 秒，返回 STORAGE_ERROR，不把超时视作完成，也不换键盲重试。
- 相同包可重复导入，研究变更操作的回放结果随包保存。导入动作本身只在本机去重，不反复写入包。
- 有本地研究数据时，只接受已知检查点的直接后继，且旧版本/事件/操作结果完整保留。本地未导出变更、分叉或跳过中间包返回冲突；保留双方快照，按顺序导入中间包或先人工审阅，不按时间戳选赢家。
- 导出持有短 SQLite 写锁，写同目录临时文件、fsync 后替换，再记本机检查点。文件与数据库不是跨系统原子事务；替换后崩溃可重试相同内容。禁止覆盖数据库、非 JSON、无有效格式标记的文件、符号链接或已发生外部变化的快照。后续 scheduled-sync 应串行协调 Git 文件操作，避免其他进程在检查与替换之间同时修改目标。
- 备份/恢复用 SQLite backup API 和一致性快照，校验完整性、外键、研究版本/事件以及私人版本链、去重结果和行数据摘要。只写新目标；不会替换运行中的数据库。备份也包含私人正文，不上传、不作为静态文件公开。
- `.local/`、SQLite 文件和 Python 缓存均忽略 Git。本模块没有自动删除备份和历史的功能。

## 原文迁移与正式切换

```bash
PYTHONPATH=src python3 -m records legacy-preview --root . --mapping research/migrations/2026-10-15-records-map.json --output .local/legacy-preview.json
PYTHONPATH=src python3 -m records --db .local/rehearsal.sqlite3 legacy-apply --root . --input .local/legacy-preview.json --operation-id apply-reviewed-preview
```

支持 Markdown 的 `records-json` 代码块，或路径→记录列表的显式映射。自由文本不能可靠拆解时返回 unresolved，禁止静默漏掉或猜测字段；所有未映射项解决后才整体应用。来源、点子、趋势及研究日志均进入文件摘要清单，新增文件也会使旧预览失效。显式映射可带 expectedSha256，本次现有资料映射已逐项绑定原文摘要。

`legacy.originalText/path/sha256` 保存原文出处。`legacy.firstCollectedAt` 保存已知首次收录时间/日期；`legacy.dates` 保存仅精确到日的 publishedAt/accessedAt/lastAttempt/lastSuccess，不伪造午夜或抓取时分。旧记录精确时间未知时主字段为 null，旧证据的访问日期必须保留在 legacy.dates；新采集则填写真实带时区访问时间。createdAt/updatedAt 是本次进入结构化库的时间。来源入口可读不代表具体讨论成功，CN05 的 lastSuccess 保持空。

正式切换必须：确认最新预览与映射 → 在新库迁移演练并导出/备份/恢复 → 复核期间新增研究资料 → 显式确认切换 → 更新 AGENTS 与研究/调度写入路径。原 Markdown 和旧库继续保留。当前只完成演练，不执行正式切换。

## 验收记录

37 项 unittest 全部通过，语法检查及 CLI help 正常。覆盖真实临时 SQLite、重启、线程竞争、子进程提交前退出/提交后丢响应、锁超时、证据版本、私人隔离、筛选、可逆合并、确定性快照、分叉/坏包拒绝、备份恢复和 CLI 全流程。

当前资料迁移演练得到 11 Source + 5 Evidence + 1 Idea + 1 Trend；原 ID、原文、日级日期和证据限制保留，未新增需求或成交结论。审阅发现的导出目标、畸形嵌套输入、私人恢复版本链问题已修复并有回归测试。移除 expectedRevision 检查的变异测试会被并发测试捕获。

代码审阅覆盖行为正确性、职责边界、输入/私有导出限制及分页查询；无第三方依赖安装、无新增网络集成。此模块不实现语义去重、推荐评分、网页、定时器或 Git 自动同步。
