# 2026-11-08 19:52（Asia/Shanghai）质量守门运行记录：映射补录前置依赖核查

- 背景：按 19:36 断点推进唯一阻断项（45 个新点子文件缺显式映射），本轮只做有界前置核查，不写入任何映射条目。
- 研究问题：能否直接从 IDEA-20261024-001 起逐文件补录 Idea/Evidence 映射；新文件引用的来源是否都已有 Source 记录可供外键引用。
- 检索范围/来源：本机 `src/records/legacy.py`、`src/records/contracts.py`、`src/records/storage.py`、`research/migrations/2026-10-15-records-map.json`、`sources/INDEX.md`、45 个 `ideas/IDEA-2026102[4-7]-*.md`；无外部检索。
- 读取成功/失败：全部本机文件可读，无失败。
- 审查/候选/新增：审查 45 个待补文件与 383 条补充小节来源行，候选 0、精选 0、新增点子 0、新来源 0、去重 0。
- 证据与状态变化（结构性发现，改变修复路径）：
  1. `sources/INDEX.md` 含两类来源定义：主表 86 条（`| CN/GL |` 行）与“研究来源补充”小节 383 个条目行、去重后 353 个唯一来源 ID（部分 ID 另有“（日期复检）”追加行）；迁移映射只收录 76 条 Source 记录，其中 46 条对应补充小节、30 条对应主表。
  2. 45 个新点子文件共引用 102 个未映射来源 ID，全部在补充小节有定义、主表无定义；没有任何一个新文件只引用已映射来源（可先补录文件数为 0）。
  3. `storage.references()` 强制 Evidence 的 `sourceId` 必须指向已存在的 Source 记录，因此在补录 Idea/Evidence 前必须先为这 102 条补充小节来源补 Source 映射，顺序不能颠倒；否则 `apply_preview` 会在写入阶段失败。
  4. 契约另确认：Idea 的 `researchStatus` 枚举仅含 待验证/候选/优先验证/搁置/淘汰，新文档头部“需补证”不是合法枚举，补录时需按正文守门结论映射到合法值并在映射评审记录中说明依据，禁止静默改语义；E3 证据必须 `nature=fact` 且带非空 `paymentSignal`。
- 减少的未知：确认 45 文件补映射不是孤立工作，真实顺序为“先补 102 条 Source 映射 → 再补 45 文件 Idea/Evidence 映射 → 重算 expectedSha256 → records 测试转绿”；排除了“直接逐文件补录即可”的假设。
- 反证/替代：不适用（本机结构核查）。
- 剩余缺口：102 条 Source 的 name/url/audience/languages/accessStatus/lastAttempt/lastSuccess 需逐条对照补充小节原文提取，字段不全的条目只能标待核、禁止猜测；45 文件的 Evidence 级别、paymentSignal 与 researchStatus 映射需逐文档评审；心跳停摆的调度原因仍未在仓库内确认。
- 结构/隔离：未写 `.local/`，未改任何证据等级、稳定 ID、原始 URL 与历史结论；`git diff --check` 通过。
- 检查与故障：research 79/79、local-web 10/10 通过；records 71 项中 1 项失败（unresolved 45）维持，继续阻断提交/推送，不降标。
- 断点与下一步：下一轮起按每轮 10–15 条的小切片从补充小节提取 Source 映射（先 CN21–CN29 等被多文件引用的高频来源），每条保留原始定位与日期；Source 层完成前不写 Idea/Evidence 条目。
