# 有依据的覆盖回顾（R15）

`Runner.coverage(run_id, token).publish(draft)` 校验并发布 CoverageReview。draft 必须列出按时间排序的 runIds、固定版本的 Source/Evidence 引用、未覆盖领域、质量理由、建议和结构化 coverage。执行者必须持有当前租约；回顾不会启动下一轮、改变研究阶段或写入收藏、忽略、匹配度等个人状态。

coverage 明确记录 industries、audiences、markets、sideHustleTypes、sourceTypes 和 readScopes，以及可持续来源 ID、失败替代、重复/过时处理方式、后续轮巡办法和可选渠道调整。各维度不能是空列表。可持续来源必须在 sourceRefs 中，sourceTypes 必须来自引用 Source 的 profile，readScopes 必须来自引用 Evidence 对应的 ReadReceipt。程序还核对 Evidence 的读取块、URL、访问时间、runId 和 sourceId，不能用搜索摘要或无凭据文字充当覆盖依据。

程序从所有当前、未归档并绑定 ReadReceipt 的 Evidence 计算各轮是否有实质新增，不信任 draft 自报数量。最近连续三轮没有新 Evidence 时，建议必须是 adjust，并给出具体 channelAdjustment；准入标准不会因此降低。单轮零新增、累计条数或经过天数都不能直接推出 incremental。

incremental 只是交给调用方的建议。它至少要求可追溯 Evidence、可持续来源、失败替代、已命名缺口、重复/过时处理说明和后续轮巡办法。concentrate 表示继续集中收集；adjust 表示改变查询或渠道。发布器只保存建议及依据，调用方依据既有授权决定后续动作。

CoverageReview 使用稳定内容 ID 和 fenced publishStep，重复稿件只回放一份历史。结构化 coverage 随公开研究包导出、导入并继续接受引用校验；旧版不含 coverage 的已有回顾仍保持可读。

测试使用合成公开来源、Reader 凭据和多个轮次，覆盖结构化维度、引用归属、三轮空窗、增量准入、重复发布及公开包往返。它不代表已完成真实网络覆盖回顾。
