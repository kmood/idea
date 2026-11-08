# 2026-11-08 21:52（Asia/Shanghai）质量守门运行记录：Idea/Evidence 映射 IDEA-20261025-002 至 007（6 文件 16 条记录）与 CN103 URL 漂移登记

- 背景：21:42 完成 10-24 批次后，本轮处理 10-25 批次 6 个文件（002–007）；001 含 7 个来源，留单轮处理。映射 JSON 在 21:52 轮落盘，运行记录与 STATE 断点于 21:58 交接核对后补齐，确认未重复提交。
- 研究问题：（1）6 个小文件批量映射时如何保持 EV 编号连续、状态枚举与正文一致；（2）内联链接与 Source 主 URL 出现路径漂移时如何不丢定位又不伪造 URL。
- 检索范围/来源：`ideas/IDEA-20261025-002.md` 至 `IDEA-20261025-007.md` 全文、177 条 Source 主记录、迁移映射 JSON、冲突迁移表；无外部检索。
- 读取成功/失败：6 文件全部来源在 Source 映射中可解析，无缺失、无 restricted；10 条 Evidence 中 9 条内联链接与 Source 主 URL 一致，CN103 为 DRIFT（见下），本批无 FALLBACK。
- 审查/候选/新增：6 个文件新增 16 条记录（10 Evidence + 6 Idea），候选 0、精选 0、新增点子 0、去重 0；unresolved 41 → 35，预览 444 条记录。
- 证据与状态变化：
  1. E2×2：CN82、CN90（平台招募页与机构入库公告，无支付信号，nature=fact、paymentSignal=null）；E3×8：CN94、CN95、CN96 取 intent（有预算/限价但无成交金额披露），CN100、CN103、CN101、CN105、CN106 取 quote；全部 nature=fact，无 author_claim、全库仍不使用 paid。
  2. 六个 Idea 文档头均为需补证/暂不适合类，按 21:22 确立的枚举规则统一映射 researchStatus=搁置；evidenceIds 各自挂接，EV 编号 EV-20261025-001 至 010 顺序占用，下一可用 EV-20261025-011。
  3. 16 条按 apply 路径补系统戳后全过 `validate_record`；10 个 sourceId 外键在 177 条 Source 内全部可解析。
- CN103 URL 漂移登记：正文内联为 `https://www.jl.gov.cn/ggzy/sysggzy/sysjyxx/syszchtgs/202605/t20260526_9631801.html`，Source 主记录为 `https://www.jl.gov.cn/ggzy/sysggzy/sysjyxx/syszfcg/ccszchtgs/202605/t20260526_9631801.html`；同一文档 ID（9631801）、栏目路径深度不同，非两个语义来源。按既定 DRIFT 规则 EV-20261025-007 采用 Source 主 URL，并在冲突迁移表追加登记，正文内联不改写。
- 减少的未知：10-25 批次 7 个文件中 6 个完成显式映射，批量小文件的编号、枚举、URL 三态链路再次跑通；剩余 35 个 unresolved 集中在 IDEA-20261025-001 与 IDEA-20261027-001 至 034。
- 反证/替代：仅结构化映射，未改正文等级与结论；机构入库主体门槛（CN90）、平台任务量不保证（CN82）、百万级年度合同对应主业供应链投入（CN103）等反证逐条保留在各 rebutsClaim。
- 剩余缺口：35 个文件待映射；CN04 原帖 URL、CN103 双路径可达性待核；全部 unresolved 归零前 records 阻断不解除。
- 结构/隔离：未写 `.local/`，未改稳定 ID、证据等级与历史结论；工作区仍为全量迁移改动，未到提交环节。
- 检查与故障：research 79/79、local_web 10/10 通过；records 71 项中 1 项失败（`test_current_repository_migration_roundtrip_and_recovery`，unresolved 35）维持，继续阻断提交/推送，不降标。
- 断点与下一步：单轮处理 `IDEA-20261025-001.md`（7 个来源、文档头需补证→搁置），EV 从 EV-20261025-011 起；之后进入 IDEA-20261027-001 起 34 个文件。
