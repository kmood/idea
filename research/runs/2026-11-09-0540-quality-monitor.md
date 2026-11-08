# 2026-11-09 05:40（Asia/Shanghai）质量守门运行记录：CN303 同买方第二单 Spanish Audit 回源（重复授标确认、实收仍不可见、E3 不升级）

- 研究问题：关闭上轮留下的关键未知——otherEmployerJobs 中的 Spanish Website Translation Audit 是否同一买方、是否授予同一供应方、是否构成复购证据，以及能否取得放款/实收字段。行业为翻译/校对专业服务，海外众包平台；按轮换避开连续机构采购与法院案例。
- 范围与来源（未登录只读，无验证码/付费墙/UA 伪装，共 2 次请求，均 HTTP 200，各约 1.1 MB）：
  1. `freelancer.com/projects/editing/spanish-website-translation-audit`（projectId=40449131）；
  2. `freelancer.com/projects/linguistics/arabic-translation-verification`（CN303 项目 40547881，用于逐字段比对买方对象）。
- 读取成功/失败：成功 2、失败 0。解析两页 NGRX_STATE 内嵌 rawDocument（projectsSeo），无登录态字段。
- 核验到的原始事实：
  1. 西语审核单：固定价、closed/closed_awarded，2026-05-17 07:56 UTC 发布、05-24 截止、最新活动 05-18；预算 30–250 欧元，12 份提案、均价 50 欧元；
  2. 买方原始需求：英文信息页西语（西班牙本土）译文复核，610 个翻译键，对照英文源查误译并给润色替代，须用 SimplyLocalize 工具，含一次简短在线会议（brief online call）做工具说明；
  3. selectedBids 仅 TransManual24（孟加拉国 Dinajpur），30 欧元/1 天、completed=true；sellerRating 5.0/reviewCount=94 为账户累计；userEarningsPercentage=7.02 为账户统计；
  4. 两项目 client 对象逐字段完全一致（注册时间 1702472417000、迪拜、零评价、四项验证标记相同、profileComplete=false），确认同一买方；
  5. 时间线：西语单 2026-05-17 授标 → 阿语单 2026-06-29 授标，相隔约 43 天，同一买方两次授予同一团队，两单均 completed=true；
  6. 两页 TransManual24 reviewCount 分别为 94 与 97，差异原样保留不统一；登出态 milestones/milestoneRequests 仍为空对象，无放款、提现、本单评价字段。
- 证据裁决：证据从“授标”推进确认到“同买方→同供应方重复授标＋两单平台完成状态”，为库内首条平台结构化重复授标证据；但七层中平台结算/个人实收层仍缺失，重复授标≠两笔款均已到账，30/100 欧元不升 paid，E3 维持。CN303 不新增 Source/点子，候选/精选 0/0。
- 减少的未知：关闭“第二单是否存在且同供应方”未知（确认存在、同买方、同团队）；“复购”收窄为“重复授标已确认、重复实收未确认”。保留未知：实际放款与净提现、总工时、买方零评价原因、Flutter 小时单是否成交。
- 反证/免费替代：12 份提案均价仅 50 欧元、中标 30 欧元/1 天，显示低门槛竞价与价格压力；供应方为 2007 年注册团队账户、模板化投标话术，其路径不可直接迁移为个人获客；一次性在线会议与英语沟通仍构成私人条件门槛；机器翻译＋内部母语同事复核是天然替代。
- 审查/候选/新增数：复核来源 2 条项目页（CN303 通道）、新增 Source 0、新增点子 0、deep 笔记追加回源节 1 处（无指纹）；候选/精选 0/0。
- 去重：西语单作为 CN303 同买方通道内的第二单留痕，不另建 Source；与 CN302 档案评价（Tim R./Dragos V.）继续分开，不把显示名评价与结构化订单混并。
- 资料动作：更新 `sources/INDEX.md` CN303 行（追加第二轮回源）；`research/deep/2026-10-27-translation-repeat-hire-boundary.md` 追加“2026-11-09 第二轮回源”节；重算 INDEX 迁移指纹 178 条，映射 diff 仅指纹行。
- 检查：legacy-preview 534 条、unresolved 为空、无 REVISION_CONFLICT；records 71/71、research 79/79、local_web 10/10；`git diff --check`；`.local/` 零跟踪。
- 剩余缺口：czju 解封（CN182 二标段＋采购文件）、CN219、CN04/linux.do、.gov.tw、v2ex、威海法院精确 URL、GL48 Cloudflare；Flutter 小时单未展开；西语/阿语两单实际放款登出态不可得，不再重复抓取同页。
- 故障：无新增；czju.suzhou.gov.cn 整域 403 仍待恢复。
- 断点与下一步：两个中文原子提交推送并 ls-remote 核验；下一轮换行业与来源类型，优先无争议同单验收或退款争议的原始材料，不预设 AI/自动化优先。
