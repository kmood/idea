# 能力划分：个人副业研究库

状态：已获用户明确同意（2026-10-14）。依据 [已确认意图](docs/intent/personal-opportunity-library.md)。这是一套单机应用的逻辑模块，不代表需要多个服务或分别部署。

| 模块 ID | 职责与边界 | 依赖 | 可独立检查的结果 |
| --- | --- | --- | --- |
| records-history | 网站、趋势、点子、证据、个人操作与历史的保存和读取；稳定 ID、合并关联、持久化约束 | 无 | 重启后资料/选择不丢失，变更能追溯，合并不丢来源 |
| source-research | 网站收录、公开讨论采样、初始集中收集、后续增量采集、核验去重与趋势/点子分类 | records-history | 可追溯来源的资料入库，证据弱的标注清晰，重复输入不产生重复项 |
| opportunity-review | 跨行业适配判断、证据分析、精选 1–3 个方向及两周实验建议 | records-history | 入库与推荐分离，解释匹配原因与证据缺口，不把估计当成交 |
| local-web | 本机与局域网浏览，搜索筛选、详情/历史、收藏/忽略/准备验证 | records-history、opportunity-review | 不同设备看到一致记录，个人操作持久化且不被采集覆盖 |
| scheduled-sync | 既有定时任务接续、阶段切换、运行记录、有限重试、检查/提交/推送及网站数据刷新协调 | records-history、source-research、opportunity-review、local-web | 可断点恢复，无变化不重复提交，推送失败不丢本地成果，网页反映最近有效数据 |

## 顺序

records-history → source-research → opportunity-review → local-web → scheduled-sync。

这是规格与能力依赖顺序；实现阶段应按小的端到端功能切片交付，不要求先写完整数据库再写全部界面。现有 Codex 定时任务仍负责调度，暂不引入第二套调度器。

## 边界约定

- records-history 提供后续各模块使用的数据契约，其他模块不各自维护互相冲突的数据副本。
- opportunity-review 提供判断结果，local-web 展示结果并保存用户操作；推荐计算不依赖浏览器运行。
- scheduled-sync 调用既有能力和刷新机制，不再定义一套采集、评分或数据规则。
- 记录合并需关联旧 ID，历史不得被新版本静默覆盖。
- 技术栈、具体字段/API、服务端口及访问控制在各模块规格与技术方案中确定，本表不作预选。

## 规格索引与状态

| 模块 | 规格 | 状态 |
| --- | --- | --- |
| records-history | [资料与历史](SPEC-records-history.md) | 草案待审阅 |
| source-research | 尚未编写 | 待基础契约确定 |
| opportunity-review | 尚未编写 | 待基础契约确定 |
| local-web | 尚未编写 | 待基础契约确定 |
| scheduled-sync | 尚未编写 | 待基础契约确定 |

模块划分已确认；模块规格通过后再进入技术计划和任务拆分。尚无应用模块完成实现。
