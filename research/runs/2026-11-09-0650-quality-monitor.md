# 2026-11-09 06:50（Asia/Shanghai）质量守门运行记录：PTT 连接超时改道与 GL11 QuickBooks 重复交易帖回源（免费流程主导、零采购、E2 维持）

- 研究问题：首选目标是 IDEA-20261022-007/010 共用的 PTT soho 板两个过期委托（CN11），关键未知是买方是否在推文或后续楼层留下选人/付款痕迹；PTT 不可达后改道 IDEA-20261021-005（QuickBooks 重复交易审计，待验证/E2），检验首个来源帖 948481 是否出现付费解决方、采纳标记或服务采购，评估“只读重复审计报告”方向的付费空间。
- 轮换说明：上一轮为 Make 厂商社区（电商自动化），本轮先尝试台湾 BBS（地域与平台轮换，失败），实际完成轮改为财务软件官方支持社区（小企业财务运营行业），与前几轮行业不重复；不预设 AI、自动化优先。
- 范围与来源（未登录只读，无验证码/付费墙/UA 伪装）：
  1. PTT 两次有界请求（25 秒、30 秒）均连接超时、HTTP 000、0 字节：`https://www.ptt.cc/bbs/soho/M.1792383103.A.B4F.html`，原始错误留存命令输出，不第三次重试；
  2. `https://quickbooks.intuit.com/learn-support/en-us/banking/re-remove-duplicate-transactions/01/948481/highlight/true`（HTTP 200，775,109 字节，301/302 跳转规范化地址 `/community/banking-4/remove-duplicate-transactions-29635?postid=533414`，totalPages=1，HTML 存 /tmp/qb/q948481.html 不入库）。
- 读取成功/失败：成功 1、失败 2（同一 PTT URL 两次超时，按 1 个失败来源计）；QuickBooks 静态 HTML 含完整楼层，仅末条“Show 1 more reply”折叠内容要求登录，未绕过、不推测。
- 核验到的原始事实：
  1. 帖子前缀为 Question 而非 Solved（页面 13 处 “Solved” 均为界面配置文案），8 条回复、102 次浏览，时间线 2021-09-23 至 2023-10-13，之后休眠约三年；
  2. 三名独立用户陈述重复问题：yatpui（QBO 单笔重复 5 次以上）、User120（Desktop Pro 2019 一笔 Chase 下载交易过账五次，本人怀疑银行侧故障）、MMB2023（转账自动/手工重复且前任做过冲销 JE）；
  3. 两名版主（Angelyn_T、QueenC）均给免费官方流程：逐笔删除、隐私窗口排查、Record as transfer → Match → Exclude、对账报告，并提醒冲销分录先咨询会计；
  4. 唯一商业提及为 Fiat Lux - ASIA（Level 14 成员）以 grsm.io 推广跳转链接推荐第三方自助工具 TransactionPro，无报价、无代做服务、无接受记录；
  5. 无雇佣、合同、交付、验收、付款或复购，无采纳答案标记。
- 证据裁决：七层裁决停在需求层（三名独立用户）与免费方案层；TransactionPro 是自助 SaaS 产品替代而非服务报价，不能计采购。E2/待验证维持，不升 E3、不升 paid，候选/精选仍 0/0。
- 减少的未知：关闭“该帖是否存在付费解决路径”未知——免费官方流程与自助工具已覆盖公开讨论，且三年无新活动、无采纳；同帖不再回源。第二个来源帖（1338727，29,000 条未结项目）保留给后续轮次单独回源，不与本帖混同。PTT 侧未知未减少，台账新增 ptt.cc 当前网络不可达。
- 反证/免费替代：官方匹配/排除/对账流程免费且被版主反复强化；批量删除已被 TransactionPro 产品化，人工服务空间受挤；部分重复根因在银行下载故障，外部审计无法根治；误删破坏对账、冲销属会计判断，代清理责任门槛高。
- 审查/候选/新增数：复核来源 2 个（CN11 读取失败、GL11 成功）、新增 Source 0、新增点子 0；新增 deep 边界笔记 1 篇（无指纹）；候选/精选 0/0。
- 去重：无新增来源/点子、无合并；948481 仍归属 GL11 与 IDEA-20261021-005，原 learn-support URL 与规范化社区 URL 同时留痕，不改稳定 ID。
- 资料动作：新增 `research/deep/2026-11-09-quickbooks-duplicate-thread-free-workflow-and-tool-affiliate-boundary.md`；`ideas/IDEA-20261021-005.md` 追加回源段、历史行并更新头部日期（映射 3 条）；`sources/INDEX.md` 仅 GL11 行追加回源记录（178 条）。重算两文件迁移指纹，映射 diff 仅 expectedSha256 行（非指纹 diff 为 0），新哈希与整文件 sha256 一致。
- 检查：legacy-preview 534 条、unresolved 为空（输出重定向 /tmp，不写仓库 .local）；records 71/71、research 79/79、local_web 10/10 全绿；`git diff --check` 通过；`.local/` 零跟踪。
- 剩余缺口：czju.suzhou.gov.cn 整域 403（CN182 二标段合同与采购文件）、CN219（ccgp.gov.cn 403）、CN04（linux.do）、.gov.tw 整域 DNS、v2ex 整站超时、GL48（boards.ie Cloudflare 403）、威海法院精确 URL、ptt.cc 连接超时（CN11 两帖选人/付款未知挂起）；正向“小商户同单验收—尾款—复购”链条仍未取得（IDEA-20261025-001 恢复条件）；两笔翻译固定单个人实收登出态不可得。
- 故障：ptt.cc 两次连接超时（HTTP 000），属站点当前网络不可达而非 403，按有界原则不第三次请求；QuickBooks 末条折叠回复需登录，按规则不绕过；测试与仓库无故障。
- 断点与下一步：两个中文原子提交（资料＋指纹／运行日志＋STATE 断点）推送并 ls-remote 核验；下一轮强制轮换行业与平台，优先内容/教育/专业服务类可达原始买方材料，目标为同单验收、个人实际到账或退款原件；PTT 待网络恢复后再复检，不换镜像不伪装。
