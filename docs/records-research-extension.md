# records-history 提供方扩展提案：研究运行与可追溯发布

状态：技术方案已批准（2026-10-16）；按 tasks/todo.md 逐项实施，不代表全部接口已实现。服务于已批准的 [source-research](../SPEC-source-research.md)，保持 [资料原规格](../SPEC-records-history.md)的个人域与历史约束。批准后实施前将这些兼容扩展纳入提供方规格。

## 公开数据契约

保留已有业务记录及稳定 ID，不改已有版本或 operationId 摘要。新增字段只作用于新版本；导入旧资料时不能补造采样凭据。

- Source 增加可选 profile：主域名、子入口、行业、来源类型（community/official/report）、访问边界和复检理由；每个嵌套字段使用白名单。
- Evidence 增加可选 observation：receiptId、块/回复定位、独立性依据、日期精度及支付核验说明。新采集发布必须具备 observation，既有迁移证据仍按旧契约读写。publishedAt 继续使用精确时间或 null；只有日期时另存 publishedDate 与 precision=date，禁止伪造时区午夜。
- 新增 ResearchArtifact 类型，artifactType 与 data 必须匹配固定契约，禁止任意 JSON 字典。子类型为 ReadReceipt（公开阅读摘要）、CandidateOutcome（实质处置）、PublicationManifest（公开发布意图/步骤结果）、SourceCheckpoint（有效采样进度）、CoverageReview（有依据的覆盖回顾）。复用不可变版本和研究事件；已存在记录的引用须验证存在及版本；PublicationManifest 中预分配的目标 ID 是待创建身份，不假装已有记录，必须与步骤依赖相符。
- ReadReceipt 公开部分只含稳定标识、URL、可见范围、内容指纹、必要短摘录/概述和时间依据；无完整缓存、认证信息或私人状态。无变化复检不重建同一正文凭据，新的可见范围/主张才产生新依据。
- PublicationManifest 先记录分配的目标 ID、稳定业务 operationId、请求摘要、预期版本及依赖；只包含公开研究意图。步骤完成后关联真实结果，未完成项不能冒充成功。新机器可根据它保守重读/接续，不重新生成目标 ID。

## 本机运行域

同一资料库增加 research_runs、research_candidates、research_calls、research_intents、research_leases 等按需表；本机正文缓存位于 `.local/research-cache/`。这些是运行元数据，不是第二份 Source/Idea 正文。频繁探测、搜索工具原始输出、预算预占和租约不进入研究快照；公共断点只能由有效处置生成。

提供方负责有界分页、稳定请求键、版本比较、事务和备份。研究层消费 ResearchRuntimeStore / ResearchPublisher 接口，不访问表名。独立私有用户表与 PersonalStore 保持原样，研究执行器不取得个人写入能力。

## 执行权与发布契约

- acquireRun / resumeRun：在短事务中判断占用，返回 dbInstanceId、ownerId、单调递增 fence 和 leaseUntil；同 runId 不同请求摘要拒绝。busy 是未执行结果。
- reserveCall / finishCall：原子预占预算及 callId；超时或结果丢失仍算已使用，不能返还后盲重试；新外部尝试有新 attemptId，但仍归同一候选和轮次预算。
- saveCandidate / saveIntent：保存工作版本和分配的业务 ID；重试同意图回放，变更意图须显式关联旧版。
- publishStep：每次事务先校验 dbInstanceId/ownerId/fence/期限，再校验预期版本与读凭据，调用共享的业务保存内核，原子保存业务结果和该步骤的本地回执。业务去重摘要不含租约代号，恢复换执行者仍可回放原操作。
- checkpointSource：只对已确认结果更新连续处置位置与缺口集合；不能与尚未保存的结果脱节。lastAttempt/lastSuccess 的最新探测值主要在本机状态，公开 Source/Checkpoint 仅在有效研究进度或可访问性变化时更新摘要。
- inspectRun / listCandidates：分页读取安全状态，limit 1–100；缓存正文通过仅本机读取入口按需取得，不能默认放入错误信息。

精确重复查找和身份唯一性也在提交事务内核验，不能仅在 Agent 判断时检查。必要时返回已有 canonical ID 让调用方重整意图；不静默把不同正文并成相同记录。网络、模型判断和工具等待均在事务外。

## 格式升级与恢复

区分 DB schemaVersion 与研究包 schemaVersion；旧业务记录的 schemaVersion=1 及历史正文保持原样。新的公共包使用 v2，新增类型及字段由新校验器识别；v1 导入经过严格验证、显式转换，不改旧 eventId、operationId 或请求摘要。

旧库默认拒绝新写入，先用备份 API 复制到不存在的新路径，在副本上执行版本化迁移和完整性验证；失败删除本次临时副本，原库保留。不得在构造函数中先写 schema 再发现版本不支持。

v1→v2 转换保留旧 bundleId 与基线证明。已验证 v1 基线转换后的首个 v2 包沿用其 lineage，导出时允许替换属于该已验证基线的旧快照；不能因格式变化绕过外部修改检查。v2 之后继续直接后继和历史前缀检查；旧程序明确拒绝 v2，不声称双向兼容。

本地备份包含全部运行表、个人数据和公开研究记录，恢复后更换 dbInstanceId，租约必须重新领取且 fence 提升；即使备份内旧代号较小，也不能重新接受原库旧凭证。正文缓存不作为备份必要条件，丢失时保留已确认发布结果及指纹，待处理候选重新读取；不把缺缓存当作已读全文。公共快照能恢复发布身份与有效断点，不能恢复私人选择或全部未同步工作。

## 必须补充的回归

v1 库/包可读且升级不改旧历史；v2 往返确定性；新嵌套字段与引用严格校验；运行日志/私人标记不泄漏；崩溃后回执与正文一致；过期执行者拒绝写入；恢复重领执行权；临时副本升级失败不影响原库。现有 37 项资料模块测试保持通过，不降低原验收标准。
