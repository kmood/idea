# 2026-11-08 20:22（Asia/Shanghai）质量守门运行记录：Source 映射补录切片 3/8

- 背景：承接切片 2，继续按 ID 数字序补录；本批 12 条（CN70、CN73–CN78、CN81、CN82、CN85、CN86、CN88）以代运营纠纷法院案例、营销撮合/验货平台和摄影退款案例为主，每个 ID 仅单行定义、无复检追加行。
- 研究问题：跨两个采集日期（10-24 与 10-25）、含多 URL 与法院二手报道的来源行，能否按行内真实日期与首链规则无损结构化。
- 检索范围/来源：本机 `sources/INDEX.md` 补充小节第 510–528 行、迁移映射 JSON、`src/records/legacy.py` 与 `src/records/contracts.py`；无外部检索。
- 读取成功/失败：12 条原始行全部可读、字段齐全，无失败。
- 审查/候选/新增：新增 Source 映射 12 条（100 → 112），候选 0、精选 0、新增点子 0、去重 0。
- 证据与状态变化：
  1. 日期不再统一取值：CN70 行内 last_attempt/last_success 为 2026-10-24，其余 11 条为 2026-10-25；`firstCollectedAt` 与 `legacyDates` 均逐行取真实日期，脚本先提取行内日期再落盘，避免沿用上批 10-24 默认值。
  2. 多 URL 来源（CN70 三个、CN85/CN86 等单链）统一以原行首个 Markdown 链接为主 URL；落盘后用脚本把 12 条主 URL 与原行首链逐条比对，全部一致，其余项目页链接保留在来源索引原文供 Evidence 阶段挂接。
  3. 12 条沿用同构字段：`kind=Source`、`languages=["zh"]`、`accessStatus=readable`、顶层时间置 null、`expectedSha256` 与当前 `sources/INDEX.md` 哈希一致；名称取原行中文短标题并做最小标点规范化，受众逐字取自“中文……受众”短语，保留“法院案例/平台/个体网店”等主体差异。
  4. 末尾追加、2 空格缩进；diff 审计显示非 `expectedSha256`/Reddit 短链删除行为 0，历史条目零改动。
- 减少的未知：迁移预览成功（322 条记录、112 条 Source、unresolved 仍 45），12 条新记录逐条通过 `validate_record`；确认行内日期异质时“逐行提取”规则可行，后续切片遇到跨日期来源可直接沿用。
- 反证/替代：不适用（本机结构补录）。CN73–CN78、CN88 等法院案例本身是代运营履约失败/退款的反证来源，但其证据主张留待对应 Evidence 映射处理，本批只建 Source 身份。
- 剩余缺口：仍有 66 个缺失 Source（约 5–6 个切片），之后进入 45 个点子文件 Idea/Evidence 映射；“需补证”与契约枚举映射、E3 的 fact+paymentSignal 约束继续留待 Evidence 阶段。
- 结构/隔离：未写 `.local/`，未改证据等级、稳定 ID、原始 URL 与历史结论；`git diff --check` 通过。
- 检查与故障：research 79/79、local_web 10/10 通过（本轮一条 shell 命令曾把 tests/local_web 误写成 tests/local-web 触发 ImportError，属命令笔误，重跑正确目录通过，非测试回归）；records 71 项中 1 项失败（unresolved 45）维持，继续阻断提交/推送。
- 断点与下一步：切片 4 按数字序处理 CN89 起 12 个缺失 ID，继续保持行内日期提取、首链比对、预览/契约校验与 diff 纯新增四项核对。
