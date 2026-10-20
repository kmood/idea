# source-research 真实协作试运行（2026-10-20）

## 结论

本轮完成真实会话搜索和本机运行状态交接，但公开正文读取均被受控 Reader 判为 `restricted`，因此没有 ReadReceipt、Evidence、Trend、Idea、CandidateOutcome 或 SourceCheckpoint。R19 保持未完成；搜索摘要没有被当成需求证据或发布结果。

## 运行范围

- 临时 runId：`pilot-2026-10-20`；数据库与请求文件位于被 Git 忽略的 `.local/r19/`。
- 会话搜索工具：`web.search`；实际执行 3 个 query，分别关注 Reddit 的小企业 AI 自动化需求/招募、Hacker News 的工作流咨询痛点，以及公开 GitHub issue 中的人工流程问题。
- 建档来源：`SRC-REDDIT-AIAUTOMATIONS`、`SRC-HACKER-NEWS`、`SRC-GITHUB-ISSUES`。
- 候选 4 个：Reddit 的付费自动化顾问招募、公开征集小企业工作流问题讨论，Hacker News 的文档处理/ERP 集成讨论，以及 GitHub issue 中碎片化客户资料接收与重复交接问题。
- 搜索层观察仅用于决定读取顺序：出现了持续合作招募、人工收集房源数据、人工审核客户询盘、旧 ERP 文档处理等线索。它们尚未通过 Reader，不进入证据或点子结论。

## 读取结果与用量

首次从标准输入脚本调用 Reader 时，独立读取进程无法重载 `<stdin>`，返回通用 network 失败；随后改用 R17 的真实 CLI 子进程重试。Reddit、Hacker News 与 GitHub 候选各一次均返回 `restricted`。程序没有缓存正文，也没有生成读取凭据。

最终账本为 searches=3、total=7、candidates=0、auxiliary=0。四个读取调用均已预占且不退款，符合丢失/受限结果仍消耗预算的约定；剩余 total=33。本轮未联系客户、未发帖、未付费、未从搜索摘要提交分析。

## 导出、重导与恢复

临时库最终公开导出包含 3 个 Source，bundleId 为 `3d0bbba0f17dd8363b852a6e1c0afcb768c5c33083d98bcf8ce4bd3a50094742`，文件 SHA-256 为 `30c55b723eb105cb62abc3ae8cdd02b9f460e7c1cbe855d4f6ae7241c31bf12b`。公开包重导成功，恢复检查为 public-only，运行与私人计数均为零。

完整本机备份和恢复的表计数一致：1 个 run、3 个 search、4 个 candidate、6 个 network policy 行、3 个公开 Source；readings/publications/intents/private 均为零。恢复检查为 local-backup 且 runCount=1。由于没有正文凭据，不存在可验证的正文不变性；不能把来源记录的成功往返表述成完整 R19 验收。

## 可恢复下一步

保留当前临时库和候选队列。下一次在 Reader 可访问公开正文的网络环境中先 `resume` 取得新 token，再选择允许 robots 且无需登录的具体讨论重读；若原站持续 restricted，新增替代公开来源并领取新的实际 query/callId。只有形成 ReadReceipt 后才提交分析、发布结果、推进 SourceCheckpoint，并再次验证带正文指纹的导出/重导/恢复链路。
