# 2026-11-09 03:45（Asia/Shanghai）质量守门运行记录：GL49 湄公河委员会设计顾问采购授标披露路径确认与同机构复采登记（证据补强、状态不变）

- 研究问题：GL49（MRC 项目品牌识别与传播物料个人设计顾问采购，10-27 截止）在 2026-10-22 收录时无选人或付款证据；本轮检验截止后机构是否披露授标/短名单，并顺带确认同栏目是否存在可对照的个人顾问复采。来源类型为国际区域组织官网（含公开 WordPress REST API），与今天此前境内政采、自由职业平台、GitHub、企业官网、论坛轮换。
- 范围与来源（未登录只读，无验证码/付费墙绕过，共 5 次请求）：
  1. 公告原页 `https://www.mrcmekong.org/employment-mrc/design-and-development-of-the-project-brand-identity-introductory-publications-and-promotional-items`（HTTP 200，558 KB）；
  2. 栏目集合 `GET /wp-json/wp/v2/employment-mrc?per_page=20`（HTTP 200，响应头 X-WP-Total=4、X-WP-TotalPages=1）；
  3. 条目详情 id=18395、id=18383（各一次公开 API GET，HTTP 200）；
  4. 栏目 HTML 列表 `/employment-mrc/`（HTTP 404，该路径无列表页，API 为有效公开入口）。
- 读取成功/失败：除列表 HTML 为站点本身 404 外全部成功；API 为站点自描述公开接口（页面内 oembed/REST 链接同源暴露），仅读取已发布条目，不涉及绕过或登录内容。
- 核验到的原始事实：
  - GL49 对应条目 id=18385，date/modified 均为 2026-10-15，10-27 截止后零修改；公告确认 Individual Consultant、合同期 2026-11-15 至 2027-03-15、发布 2026-10-14、截止 2026-10-27。
  - employment-mrc 公开全集仅 4 条（X-WP-Total=4），全部为空缺/顾问公告，无短名单、授标、合同或结果类条目：该机构不在此栏目披露顾问采购授标结果，本项目成交方、合同金额、验收与付款在公开渠道不可得，后续不再回源同一公告。
  - 同机构复采：id=18395《Event Graphic Designer for 5th MRC Summit and International Conference in 2027》，date=2026-10-28（GL49 截止次日），Individual Consultant、居家、Special Service Agreement（SSA）、2026-11 至 2027-04、截止 2026-11-21，本轮当日仍开放。属同一买方的第二个独立设计顾问采购，支持机构级重复设计需求，但按规则不计为第二个独立买方；本轮仅登记定位与关键字段，不新建 Source、不读任务书，留待后续轮次按来源建档流程处理。
  - 雇佣/顾问区分：id=18383《Web & Graphic Designer》为驻老挝万象的固定期限雇员岗（Fixed-term Appointment、一年期可续、M-09 薪级、仅老挝籍可申），属雇佣关系，明确排除在顾问采购证据外，防止把招聘当副业采购。
  - 另有 id=18325《Regional Consultant (for the 5th MRC Summit in 2027)》（2026-09-30 发布），本轮未展开，仅在集合层面确认存在。
- 证据裁决：GL49 维持 E3（公开采购+完整任务书）、待验证，无 paymentSignal 升级；IDEA-20261022-022 不进候选/精选（0/0）。复采信号强化“该机构持续需要个人设计顾问”的需求侧事实，但单买方重复不等于市场普遍性，且五年资历、英语评审与印刷支持门槛不变。
- 审查/候选/新增数：复核点子 1 条、来源 1 条、同栏目条目 4 条；新增点子 0、新增 Source 0（18395 仅定位登记）、合并 0；候选/精选 0/0。
- 去重：同买方同栏目多个空缺不合并为一条，也不重复计数；雇员岗与顾问岗按合同类型区分，不混同。
- 减少的未知：关闭“截止后是否披露授标/结果”未知（结论：该渠道无授标披露机制，公开不可得）；确认同机构存在第二个居家设计顾问采购（18395，11-21 截止）及一个需排除的雇员岗（18383）。保留未知：GL49 实际成交方与金额、18395 任务书细节与最终授标。
- 反证/免费替代：模板库、内部设计人员、专业机构与 AI 草图辅助仍是替代；单机构复采不能证明个人可中标，SSA 合同仍要求专业履历与英文评审。
- 资料动作：更新 `ideas/IDEA-20261022-022.md`（回源段、雇员/顾问区分、历史行、头部日期）、`sources/INDEX.md` GL49 详细行（last_attempt/last_success=2026-11-09、回源结论与 18395 定位）；重算两文件迁移指纹（点子 2 条、INDEX 178 条），映射 diff 仅含指纹行；JSON/HTML 仅留 /tmp 不入仓库。
- 检查：legacy-preview 534 条、unresolved 为空、无 REVISION_CONFLICT；records 71/71、research 79/79、local_web 10/10 全绿；`git diff --check` 通过；`.local/` 零跟踪。
- 剩余缺口：CN219 等境内政府采购站点解封；CN04 待 linux.do 恢复；台湾 .gov.tw 待网络恢复；v2ex 整站待恢复；威海法院原页待精确 URL 或网络通路；GL48 待 Cloudflare 访问条件改变；18395 是否建 Source 待后续轮次按流程评估。
- 故障：无新增；`/employment-mrc/` HTML 列表 404 为站点路由现状（API 与具体文章正常），不计故障。
- 断点与下一步：分两个中文提交（资料留痕、运行记录与 STATE）推送并核验；下一轮换行业与来源类型，优先验收/平台托管放款/个人到账原始材料。
