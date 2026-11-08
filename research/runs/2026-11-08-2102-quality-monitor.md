# 2026-11-08 21:02（Asia/Shanghai）质量守门运行记录：Source 映射补录切片 7/8

- 背景：承接切片 6，按 ID 数字序补录；本批 12 条（CN218、CN219、CN220、CN221、CN224–CN227、CN230、CN232、CN233、CN235）以工会心理服务、殡葬辅助、幕墙清洗、家政、档案整理、消防维保、设备拆除/租赁、增殖放流和工会春秋游等政府采购成交/公告类来源为主，均为单行定义、无复检追加行。
- 研究问题：本批含 1 条回源受限来源（CN219，403、last_success 待回源），验证 restricted 口径与其余 11 条 readable 口径能否在同一切片共存且日期断言不被放宽。
- 检索范围/来源：本机 `sources/INDEX.md` 补充小节第 690–707 行、迁移映射 JSON、`src/records/legacy.py`、`src/records/storage.py` 与 `src/records/contracts.py`；无外部检索。
- 读取成功/失败：12 条原始行全部可读、字段齐全；CN219 原网页 403 的历史结论沿用，本轮不重新回源、不绕过访问限制，无新增读取失败。
- 审查/候选/新增：新增 Source 映射 12 条（148 → 160），候选 0、精选 0、新增点子 0、去重 0。
- 证据与状态变化：
  1. CN219 按受限来源处理：`accessStatus=restricted`，`legacyDates` 仅含 `lastAttempt=2026-10-27`、无 lastSuccess，顶层时间置 null；其余 11 条为 readable，`legacyDates` 含 lastAttempt/lastSuccess 均为 2026-10-27。脚本对两种行内日期格式分别断言，落盘后复核 CN219 字段与 CN02 口径一致。
  2. 12 条主 URL 与原行首链脚本自动比对全部一致；多 URL 情形本批未出现。
  3. 同构字段继续沿用：`kind=Source`、`languages=["zh"]`、名称取中文短标题、受众逐字取自“中文……受众”短语、`expectedSha256` 与当前 `sources/INDEX.md` 哈希（86bb6989…b1030）一致。
  4. 末尾追加、2 空格缩进；diff 中非 `expectedSha256`/Reddit 短链删除行为 0，历史条目零改动。
- 减少的未知：迁移预览成功（370 条记录、160 条 Source、unresolved 仍 45）；对 12 条预览记录按 `apply_preview` 真实路径补系统时间戳后逐条通过 `validate_record`（预览记录为 legacy 形态、缺系统戳，不能直接校验，已用与入库一致的转换方式核对）。确认 restricted/readable 混排断言机制有效。
- 反证/替代：不适用（本机结构补录）。CN221 仅采购需求未成交、CN225/CN226/CN235 未公开金额或仅候选、CN230/CN232 个体工商户成交但无付款验收等证据边界，留待 Evidence 阶段处理，不在本轮升级判断。
- 剩余缺口：仍有 18 个缺失 Source（切片 8，ID 需按补充小节重算），之后进入 45 个点子文件 Idea/Evidence 映射；“需补证”与契约枚举映射、E3 的 fact+paymentSignal 约束继续留待 Evidence 阶段。
- 结构/隔离：未写 `.local/`，未改证据等级、稳定 ID、原始 URL 与历史结论；`git diff --check` 通过。
- 检查与故障：research 79/79、local_web 10/10 通过；records 71 项中 1 项失败（`test_current_repository_migration_roundtrip_and_recovery`，unresolved 45）维持，继续阻断提交/推送，不降标。
- 断点与下一步：切片 8 处理剩余 18 个缺失 ID，先用既有脚本从补充小节重算 ID 清单，再沿用行内日期断言、首链自动比对、预览/契约校验与 diff 纯新增四项核对。
