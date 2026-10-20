# source-research 真实协作试运行（2026-10-20）

## 结论

R19 已完成一轮真实的“会话搜索 → 本机 Reader 读取 → 引用分析 → 临时库发布 → 导出与恢复”链路。GitHub 公开 issue 生成了 ReadReceipt，并发布 1 个 E1 作者陈述级待验证点子；Hacker News 页面成功取得公开 HTML，但当前正文解析器不能识别其讨论结构；Reddit 在 DNS 降级修复前失败，本轮没有重试。成功、受限和未覆盖范围均保留，搜索摘要没有被当作需求证据。

本轮只证明公开研究链路可以运行。新点子尚无独立样本、付费证据或生产使用核验，不进入精选 1–3 个方向。正式 Markdown 研究入口、每日自动任务和网站均未切换。

## 运行范围

- 临时 runId：`pilot-2026-10-20`；数据库、缓存与请求文件位于被 Git 忽略的 `.local/r19/`。
- 会话搜索工具：`web.search`；实际执行 3 个 query，分别关注 Reddit 小企业 AI 自动化需求、Hacker News 工作流咨询痛点和 GitHub issue 中的人工流程问题。
- 建档来源：`SRC-REDDIT-AIAUTOMATIONS`、`SRC-HACKER-NEWS`、`SRC-GITHUB-ISSUES`。
- 候选共 4 个：Reddit 2 个、Hacker News 1 个、GitHub issue 1 个。搜索层内容只决定读取顺序。
- 运行曾过期，按同一已授权任务以 `r19-continue-doh` 续授；没有增加预算。

## 网络与读取结果

首次读取时，系统 DNS 将所有测试域名映射到 `198.18.0.0/15`，Reader 按公网地址约束拒绝。诊断后加入窄范围 DoH 降级：只有系统答案全部属于该基准测试网段时，才通过固定 Google Public DNS 地址连接；TLS 验证 `dns.google`，解析结果和最终正文目标仍逐一执行公网地址检查。普通私网、混合地址及 DoH 返回私网继续拒绝。实现与边界见 `docs/research-network.md`。

修复后结果如下：

- Hacker News：robots 与候选页均取得公开响应；第一次受 crawl-delay 与单操作期限共同影响而超时，第二次取得约 86 KiB HTML，但正文解析器无法定位讨论正文，返回 `parse`，没有 ReadReceipt。
- GitHub issue：成功生成 ReadReceipt `read:7bee4173e8d39bc8afeeac5429141e3dec55f8edd935614b3595296cdad87646`，正文指纹 `6f57bb9e6098b4c4b7b80f275fc8ba73243ac4946d98bf6005403fa2c62f2b86`，包含 119 个可定位正文块。
- Reddit：保留修复前的受限失败，本轮没有用新增网络路径重试，因此不作可访问性结论。

最终执行账本为 searches=3、candidates=2、total=11、auxiliary=0；剩余 searches=9、candidates=8、total=29。失败、超时和解析失败调用均未退款。本轮未联系客户、未发帖、未付费，也未使用登录账号或浏览器登录态。

## 发布结果

GitHub issue 作者描述 Microsoft 合作伙伴或 Power Platform 咨询公司的客户接入过程：资料零散到达，风险和缺失信息容易漏掉，可能重复创建请求，交付团队收到的交接不一致。引用块为 `b-502cf969e794bc035760-1`；正文另一个块描述结构化记录、风险摘要、去重请求、发现简报及 Word 交接方案。

程序发布了以下保守结果：

- Idea：`idea:5b8fb14c0f27620af774b71f5691abaedc56e250a6e59704c06be0bfbb29d65a`
- Evidence：`evidence:5b8fb14c0f27620af774b71f5691abaedc56e250a6e59704c06be0bfbb29d65a:1`
- Manifest：`manifest:f139c8bb951ea1d4c723b52e27d57ecd7124d1991b36c1ef8314031aa948a950`
- Outcome：`outcome:5b8fb14c0f27620af774b71f5691abaedc56e250a6e59704c06be0bfbb29d65a`
- SourceCheckpoint：`checkpoint:pilot-2026-10-20:SRC-GITHUB-ISSUES`

点子标题为“咨询公司客户资料接入与交付交接自动化”，赚钱方式是假设提供集成实施服务并按项目及维护收费。证据等级为 E1、性质为作者声称；付费意愿、问题频率、预算、合规与集成限制、是否已用于生产均为未知。后续需要独立讨论和真实付费信号，不能依据单个方案型 issue 推断市场成立。

## 导出、重导与恢复

最终公开包位于本机 `.local/r19/public-complete.json`，含 9 条公开记录；bundleId 为 `562b83f99ea0ca3296c334050efddad449abfcf28a1eda349a61467a86d2738c`，文件 SHA-256 为 `0ceb14b361fa282322dd139a37993a1ba14c3d6716caecf2488d0b1b866cdaf3`。公开包重导成功。

完整备份恢复前后计数一致：9 条研究记录、13 个版本、13 个事件、1 条证据关联、26 个操作、1 个 run、3 个 search、4 个 candidate、1 个 execution、6 个 network policy、1 个 reading、1 个 publication、1 个 progress、9 个 intent；无私人状态。原库、公开重导库和完整恢复库的 receipt ID、revision、正文指纹与 119 个块一致，原始缓存文件哈希也等于正文指纹。

另在隔离目录验证 public-only 恢复：公开 Manifest 和 SourceCheckpoint 可恢复，运行、请求计划及私人计数均为空；正文缓存按预期缺失，恢复建议为重新读取，没有从公开摘要伪造缓存或本机意图。

## 后续边界

下一轮优先为该问题寻找独立的咨询交付讨论或采购信号，并补支持 Hacker News 讨论页的正文适配。用户已允许提供账号或使用本机已登录的受控浏览器扩展来源，但本轮没有使用；该能力需独立设计本机会话隔离、脱敏、审计和私有内容保存边界，不能把现有公开 Reader 说成已经支持登录态。
