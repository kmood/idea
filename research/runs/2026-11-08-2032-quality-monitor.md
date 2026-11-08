# 2026-11-08 20:32（Asia/Shanghai）质量守门运行记录：Source 映射补录切片 4/8

- 背景：承接切片 3，按 ID 数字序补录；本批 12 条（CN89、CN90、CN93–CN97、CN100、CN101、CN103、CN105、CN106）以政府采购/成交公告、个体工商户中标明细和机构遴选为主，全部为 2026-10-25 采集、单行定义、无复检追加行。
- 研究问题：含 PDF 直链（CN100）与长 URL 的成交类来源，能否沿用同构字段与首链规则无损结构化。
- 检索范围/来源：本机 `sources/INDEX.md` 补充小节第 529–579 行、迁移映射 JSON、`src/records/legacy.py` 与 `src/records/contracts.py`；无外部检索。
- 读取成功/失败：12 条原始行全部可读、字段齐全，无失败。
- 审查/候选/新增：新增 Source 映射 12 条（112 → 124），候选 0、精选 0、新增点子 0、去重 0。
- 证据与状态变化：
  1. 脚本直接从原行解析首个 Markdown 链接作为主 URL（含 CN100 的 ccgp-neimenggu PDF 长链与 accessCode 参数，逐字保留不截断），并断言行内 last_success=2026-10-25，避免手抄 URL 出错。
  2. 12 条沿用同构：`kind=Source`、`languages=["zh"]`、`accessStatus=readable`、顶层时间置 null、日期落 `legacyDates`（均 2026-10-25）、`expectedSha256` 与当前 `sources/INDEX.md` 哈希一致；名称取原行中文短标题、受众逐字取自“中文……受众”短语。
  3. 末尾追加、2 空格缩进；落盘后脚本把 12 条主 URL 与原行首链逐条比对全部一致，diff 中非 `expectedSha256`/Reddit 短链删除行为 0，历史条目零改动。
- 减少的未知：迁移预览成功（334 条记录、124 条 Source、unresolved 仍 45），12 条新记录逐条通过 `validate_record`；确认 PDF 直链与超长 URL 不影响 Source 结构化，规则可继续复用。
- 反证/替代：不适用（本机结构补录）。CN93、CN100、CN101、CN103、CN105、CN106 等个体工商户成交/合同信号及其“未公开付款/验收/净收入”的边界留待 Evidence 阶段处理，本批只建 Source 身份。
- 剩余缺口：仍有 54 个缺失 Source（约 4–5 个切片），之后进入 45 个点子文件 Idea/Evidence 映射；“需补证”与契约枚举映射、E3 的 fact+paymentSignal 约束继续留待 Evidence 阶段。
- 结构/隔离：未写 `.local/`，未改证据等级、稳定 ID、原始 URL 与历史结论；`git diff --check` 通过。
- 检查与故障：research 79/79、local_web 10/10 通过；records 71 项中 1 项失败（unresolved 45）维持，继续阻断提交/推送，不降标。
- 断点与下一步：切片 5 按数字序处理 CN117 起 12 个缺失 ID，继续保持行内日期断言、首链自动比对、预览/契约校验与 diff 纯新增四项核对。
