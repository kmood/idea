# 多步研究发布与恢复（R13）

`Publication(runtime, run_id, token)` 把已校验的 AnalysisDraft 转成可恢复的公开发布步骤。调用顺序是 `prepare(validated, locator)`，取得 PublicationManifest 后再调用 `resume(manifest_id, max_steps=None)`。两者都受当前运行租约约束；过期执行者不能准备、恢复或确认步骤。

prepare 会用当前正文缓存重新校验分析稿，先在本机保存完整请求计划，再把 PublicationManifest 发布到公开资料库。清单提前固定每一步的 targetId、operationId、requestHash、预期版本和依赖。业务记录只能在清单已经存在后发布。本机计划包含执行请求，因此随本地备份保存，不进入公开研究包，也不包含收藏、忽略或私人实验反馈。

步骤按依赖顺序执行：Evidence 先于 Trend/Idea 更新，CandidateOutcome 最后确认关联结果。反证作为带 rebutsClaim 的 Evidence 发布；未知成本仍只保留为未知，不生成零成本字段。已有 Source 和 ReadReceipt 是分析、发布的前置记录，不在本流程中重复创建。E2 的公开 Evidence 以首个凭据作为观察锚点，independence 保存分析时已校验的独立性分组和依据；系统不能据此证明作者身份真实。

每个业务步骤通过 R12 的原子 publishStep 保存。业务提交后，发布器再把返回的记录 ID/版本写回清单。若进程恰好在两者之间中断，恢复会以同一 operationId 重放业务请求，然后只补清单确认，不创建第二份记录或历史。`max_steps` 用于有界执行；返回 partial 表示公开清单仍有未确认步骤，complete 才返回 outcomeId。

同一 draftHash 和 locator 重试会复用本机计划及公开清单。稿件或 locator 改变会产生新的清单和目标 ID，并以 supersedes 指向上一份未归档清单；旧清单和已完成步骤保持不变。更新既有 Trend/Idea 时，计划固定目标版本，版本漂移会失败，不能静默覆盖并发修改。

恢复依赖本机计划保存的原始请求体。完整本地备份可在新进程领取租约后继续相同目标 ID；只有公开包而没有本机计划时，本阶段不会从请求摘要猜测正文，需在 R16 通过保守重读和重新分析恢复。正式 Markdown 研究入口及自动任务尚未切换到此发布器。

测试使用合成来源、读取凭据和中断点，覆盖清单先行、Evidence 后中断、业务已提交但确认丢失、备份恢复、改稿关联、反证、更新及旧执行者拒绝。它不代表已经完成真实公网试运行。
