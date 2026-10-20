# 来源进度、缺口与有界重试（R14）

`Runner.progress(run_id, token)` 返回当前轮次的来源进度入口。位置必须使用该来源内稳定的 candidateId 或内容位置 ID；同一来源不能在 ordered/unordered 两种顺序模型间静默切换。

`discover(source_id, order, positions, discovered, overlap_strategy, cursor_valid=True)` 保存本机发现序列，并同步公开 SourceCheckpoint 的发现位置。ordered 表示 positions 按可连续处理的顺序给出；unordered 不设置完成游标，只维护 processed 集合。重复的重叠位置会去重。游标失效时传 `cursor_valid=False`，系统保留原发现/完成位置，合并重叠结果并返回 `restart_with_overlap`，不会把失效游标公开为新进度。

读取前调用 `begin_attempt`。首次尝试后只允许一次重试；上一尝试尚未记结果时不会再次派发。失败用 `fail` 保存错误、缺口、是否可重试和可选 retry_at。限流等待未到时返回 RATE_LIMIT，永久错误或第二次失败返回 RETRY_EXHAUSTED。进度层只限制尝试次数，不预占网络额度；Reader 的每次 robots、正文、跳转和重试仍必须经过 execution 预算账本，因此恢复不能补回已消费额度，也不能绕过总调用上限。

`settle(source_id, position, outcome_id, last_receipt=None)` 只接受已保存、同 run/source/candidate 的 CandidateOutcome。成功后移除该位置缺口并同步公开检查点。ordered 来源只把 completed 推进到从序列开头连续完成的最后位置；前面有缺口时，后面的成功只进入 processed，不越过缺口。unordered 来源始终令 completed 为 null。`sync_checkpoint` 可在本机状态已保存但公开同步被中断后安全重试。

本机状态保存完整位置序列、尝试次数、等待时间和同步所需状态，随本地备份恢复，不进入公开研究包。公开 SourceCheckpoint 只含来源、顺序、发现/连续完成位置、缺口、已处理集合、重叠策略和最近读取凭据。同步通过 fenced publishStep 和稳定操作摘要执行；无变化不会新增版本，租约过期的执行者不能更新。

测试使用合成来源和 CandidateOutcome，覆盖前缺口阻止游标越过、无序已读集合、旧位置重叠、失效游标、限流等待、一次重试、错误 Outcome 拒绝及备份恢复。它不表示已经完成真实来源的在线游标试运行。
