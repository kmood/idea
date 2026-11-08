# 2026-11-08 22:45（Asia/Shanghai）质量守门运行记录：Idea/Evidence 映射 IDEA-20261027-016 至 020（5 文件 13 条记录）与 restricted 来源信号处理

- 背景：1027 批次第四小批，本轮处理 016–020；含 1 个 restricted 来源（CN219）和多个无金额成交公告，EV 从 EV-20261027-023 起。
- 研究问题：（1）回源 403、仅搜索定位的金额能否记支付信号；（2）成交公告无金额、预算与成交字段口径冲突时如何落信号；（3）E2 批次内可读成交与受限页面如何分别处理。
- 检索范围/来源：`ideas/IDEA-20261027-016.md` 至 `020.md` 全文、证据段与历史表、177 条 Source 主记录（含 accessStatus/legacyDates）、迁移映射 JSON、既有无金额成交与 restricted 处理惯例；无外部检索、未尝试绕过 403。
- 读取成功/失败：8 个 Source 中 7 个 readable，CN219 为 restricted（中国政府采购网回源 403、lastSuccess 为空、legacyDates 仅 lastAttempt=2026-10-27）；按逐行首链规则核对，8 条内联链接与 Source 主 URL 全部一致，无 DRIFT、无 FALLBACK。
- 审查/候选/新增：5 个文件新增 13 条记录（8 Evidence + 5 Idea），候选 0、精选 0、新增点子 0、去重 0；unresolved 19 → 14，预览 502 条记录。
- 证据与状态变化：
  1. restricted 裁决（本轮关键）：CN219 的 54,000元、1年服务、18课时等信息仅来自搜索定位，原文回源 403 未核验，EV-20261027-024 定 E2/fact 但 paymentSignal=null，summary 明确“可定位但不可引用为已核验成交，待复读原文”，firstCollectedAt 只取日期 2026-10-27；同文件 CN218 原文可读、成交346,243.15元，EV-20261027-023 正常记 E2/fact/quote。
  2. 无金额/口径冲突成交：CN220 殡葬人力外包（预算270万、页面120元字段与合同金额字段口径冲突，正文要求以合同附件核对）定 E3/fact/intent，不把预算或120元当成交额；CN225、CN226 两条档案整理成交公告均未披露金额，同 CN314 规则定 E3/fact/intent。
  3. 采购公告无成交：CN221（幕墙清洗控制价77,577.64元）、CN272（7项目预算合计55万元、明确不接受分包转包）定 E2/fact/intent，控制价/预算不外推为成交；CN224 养老家政成交3,617,500元、分项与验收明确，定 E3/fact/quote。
  4. 五个 Idea 文档头均为暂不适合当前轻量副业→ researchStatus=搁置；EV 编号 EV-20261027-023 至 030 顺序占用；CN272 按 17:40 升级历史时间落 firstCollectedAt，CN219 日期级，其余取历史表精确时间（09:40/09:50/10:00/10:10/10:20，带 +08:00）。
  5. 13 条按 apply 路径补系统戳后全过 `validate_record`，8 个 sourceId 外键在 177 条 Source 内全部可解析；E3 的 fact+非空 paymentSignal 约束通过（intent 满足非空）。
- 语义 diff 核验：相对 HEAD 顶层键 87 → 118（本轮 +5、累计 +31），无丢失键；Source 76 → 177 纯新增、共享记录除 expectedSha256 外无字段差异；既有记录变化仍限于哈希刷新与两条已登记 Reddit 短链，零记录丢失。
- 减少的未知：1027 批次 34 个文件已完成 20 个；跑通“restricted 金额不记信号”“成交字段口径冲突保守落 intent”“合同明确禁止分包（CN272）写入 rebutsClaim”三种情形；剩余 14 个 unresolved 为 IDEA-20261027-021 至 034。
- 反证/替代：仅结构化映射，未改正文等级与结论；心理资质与危机干预（CN218/219）、劳务派遣许可与殡葬现场责任（CN220）、高空作业资质且禁止分包（CN221/272）、政府整包与入户安全（CN224）、档案保密与现场设备（CN225/226）等反证逐条进入 rebutsClaim。
- 剩余缺口：14 个文件待映射（031—034 为 E3 严格校验但个人边界未知→搁置）；CN219 待可达时复读原文再确认金额信号；CN04 原帖 URL、CN103 双路径可达性仍待核；全部 unresolved 归零前 records 阻断不解除。
- 结构/隔离：未写 `.local/`，未改稳定 ID、原始 URL、证据等级与历史结论；未提交、未推送，`git diff --check` 通过。
- 检查与故障：research 79/79、local_web 10/10 通过；records 71 项中 1 项失败（`test_current_repository_migration_roundtrip_and_recovery`，unresolved 14）维持，继续阻断提交/推送，不降标、不跳过测试。
- 断点与下一步：处理 `IDEA-20261027-021.md` 起下一小批（建议 021–025），EV 从 EV-20261027-031 起。
