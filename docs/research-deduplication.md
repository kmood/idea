# 跨轮次定位与重复检查（R11）

`Deduplicator(path).inspect(receipt_id, cursor='', limit=50, post_id=None, reply_id=None)` 只读检查公开研究记录，返回定位键、同定位的读取凭据、既有处置记录和下一页。最多每页 100 条；必须累积所有页，nextCursor 为空才表示本次扫描结束。第一页没有匹配不能当作全库没有重复。此接口不写历史、不合并、不推进断点，也不代替 R12 发布事务内的身份检查。

URL 规则：将协议与主机转换为小写，只删除明确列出的 utm_source、utm_medium、utm_campaign、utm_term、utm_content、utm_id、gclid、fbclid、msclkid。保留路径、未知参数、参数顺序、重复参数、原始编码与 fragment；评论锚点、回复编号、分页和业务参数不丢失。不把 http/https、默认端口、尾斜杠或不同参数顺序擅自等同。原始 URL 保留在原凭据，规范化只用于定位。包含用户名或密码的 URL 不作为公开定位。

`locator(source_id, url, post_id=None, reply_id=None)` 优先使用明确提供的站内稳定帖/回复 ID，否则使用保守规范化 URL。稳定 ID 必须有站点解析依据；程序不猜测标题或路径中的数字，也不宣称已实现各站点解析器。R12 发布 CandidateOutcome 时应保存返回的 locator，供公开导入后恢复；已有稳定 ID 的处置可找回原 recordRefs。

相同来源的 originalUrl/finalUrl 定位匹配后，按有序正文块 ID 比较，返回 same_content 或 changed_content。正文块由 Reader 对规范化文字计算，导航噪声已经在读取阶段排除。新回复、顺序或可见文字变化不会被吞掉；相同正文的时间元数据变化不会直接制造新需求。两种结果均带 needsClaimReview，且标明任一凭据是否截断：相同块仅证明本次可见内容相同，不证明整帖全部评论相同；不同块也可能只是无关广告或计数变化，必须核对主张后再决定补证。

`linked_records(receipt_id, cursor='', limit=50)` 分页返回引用该凭据的 Evidence 以及关联的 Trend/Idea，引用使用当前业务记录固定的证据版本，因此不会因后来改写证据而错误追溯。只靠读取凭据数量识别观察，不按关联点子数量增加独立样本。业务记录合并或更新仍需通过既有资料接口和后续发布步骤处理。

`possible_duplicate(receipt_id, other_receipt_id, reason)` 接受带理由的语义相似建议，明确返回 possibleDuplicate、merge=false；不自动分类语义、不合并变体、不更改私人操作。真正合并需要核对同一对象、问题与交付，并留下理由。

定位依据来自公开 ReadReceipt、CandidateOutcome、Evidence 与业务关系，而非进程内记忆或仅本机缓存。无需新数据库表或改写旧 ID。测试覆盖保守 URL 处理、跨轮读取、跟踪参数重复、旧帖新回复、不同定位变体、稳定 ID 处置、同源多个点子、分页以及公开包导出重导入。这里完成的是重复检查基础，尚未完成后续原子发布及真实在线研究。
