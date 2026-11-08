# 2026-11-08 21:12（Asia/Shanghai）质量守门运行记录：Source 映射补录切片 8/8（Source 阶段收尾）

- 背景：承接切片 7，先从 45 个缺映射点子文件重算剩余缺失 Source：实际为 17 个（CN236、CN240、CN264、CN271、CN272、CN275、CN277–CN282、CN284、CN288、CN291、CN312、CN314），比交接预估的 18 个少 1 个，因切片 7 已覆盖部分交叉引用；本批含两种行格式（补充小节 `last_attempt / last_success=` 与接单/农村产权小节 `；日期原文可读`），脚本兼容并分别断言。
- 研究问题：两种行格式、两个采集日期（15 条 2026-10-27、CN312/CN314 为 2026-11-05 复检）混排时，URL、日期与受众短语能否全部自动提取且不串用。
- 检索范围/来源：本机 `sources/INDEX.md` 第 45–54、708–754 行、45 个 `ideas/IDEA-2026102[4-7]-*.md` 的来源引用、迁移映射 JSON、`src/records/legacy.py` 与 `src/records/contracts.py`；无外部检索。
- 读取成功/失败：17 条原始行全部可读、字段齐全，无受限来源、无读取失败。
- 审查/候选/新增：新增 Source 映射 17 条（160 → 177），候选 0、精选 0、新增点子 0、去重 0。
- 证据与状态变化：
  1. 脚本对每行同时断言首链 URL 与显式日期标记（两种格式二选一），17 条主 URL 与原行首链全部一致；受众用 `中文……受众` 短语正则提取并人工复核输出，无跨行误取。
  2. CN312、CN314 落 `firstCollectedAt=2026-11-05`（复检日），其余 15 条为 2026-10-27；全部 readable，`legacyDates` 含 lastAttempt/lastSuccess，顶层时间置 null。
  3. 177 条 Source 的 `expectedSha256` 与当前 `sources/INDEX.md` 哈希（86bb6989…b1030）一致；末尾追加、2 空格缩进，diff 中非 `expectedSha256`/Reddit 短链删除行为 0，历史条目零改动。
- 减少的未知：重算确认 45 个点子文件引用的全部 CN/GL 来源已无缺失（剩余缺失 ID 为 0）；迁移预览 387 条记录、177 条 Source、unresolved 仍 45（全部是点子文件本体的 Idea/Evidence 显式映射，不再是 Source 外键缺口）；17 条新记录及全部 177 条 Source 按 `apply_preview` 路径补系统时间戳后均通过 `validate_record`。
- 反证/替代：不适用（本机结构补录）。CN271/CN272/CN264 明确不允许分包或仅为采购需求、CN275 平台结算 500 元缺到账凭证、CN278/CN279 个体工商户成交但缺付款验收等证据边界，维持原正文结论，留待 Evidence 阶段逐条挂接，本轮不升级证据等级。
- 剩余缺口：Source 阶段（8 个切片共 101 条新增，76 → 177）完成；下一阶段为 45 个点子文件补 Idea/Evidence 显式映射，守门点包括文档头“需补证”到契约枚举（待验证/候选/优先验证/搁置/淘汰）的映射依据、E3 必须 fact+非空 paymentSignal、Evidence 外键已可全部解析。
- 结构/隔离：未写 `.local/`，未改证据等级、稳定 ID、原始 URL 与历史结论；`git diff --check` 通过。
- 检查与故障：research 79/79、local_web 10/10 通过；records 71 项中 1 项失败（`test_current_repository_migration_roundtrip_and_recovery`，unresolved 45）维持，继续阻断提交/推送，不降标。
- 断点与下一步：从 `IDEA-20261024-001.md` 起按文件逐个构造 Idea+Evidence 映射，参照映射中 `IDEA-20261022-046` 结构，每轮 3–5 个文件并保持 unresolved 单调下降；枚举映射依据写入运行记录。
