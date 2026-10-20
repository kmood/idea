# 分析稿校验（R10）

`Analyzer(runtime, run_id, token).validate(draft)` 核验 Agent 对实际读取材料的分析稿，返回 draft、draftHash 及由凭据派生的 bindings。此阶段不发布 Evidence/Trend/Idea、不改候选状态、不执行网页文字；发布和断点事务在 R12–R14 实现。发布前必须重新检查执行权、引用及目标版本，不能把本次通过作为永久授权。

稿件严格包含 candidateId、disposition、reason、nextCondition、claims、unknowns、counterEvidence、target、content。总量限 256 KiB，主张、反证和未知项分别最多 100 项。禁止夹带收藏、忽略、个人实验等字段。

- trend：content 包含 title、summary、impact（nature/text）和 questions。
- idea：content 包含 title、audience、problem、earningHypothesis、industry、sideHustleTypes、markets、cost。audience 为文字，后三个分类字段为列表，cost 允许 null。赚钱方式仍是待验证假设，校验通过不代表个人精选或已有收入。
- update：target 指定已有 Trend/Idea 的 recordId/revision，content 提供 summary；目标必须未归档、未合并且版本仍一致。
- deferred：content/target 为空，要求原因和 nextCondition，允许没有已读主张。
- rejected：content/target 为空，要求原因、nextCondition 和已读主张。不能只凭搜索标题判定正文内容。

每项 claim 严格包含 text、nature、level、refs、independence、payment、rebutsClaim。nature 仅 fact/author_claim/inference；unknowns 单独保留，不将未知成本换算为零。inference 只能是 E0。refs 为 receiptId/blockIds 列表：凭据须是已有 ReadReceipt，状态 readable/partial，引用块必须同时存在于公开凭据和经过指纹校验的本机正文缓存。缓存缺失/失效要求重读，不用块说明冒充原文。非 deferred 处置必须读取候选本身，另一个 URL 的辅助材料不能替代。日期、来源、原始/最终 URL、访问时间及截断标记由凭据绑定，不接受稿件自行指定。

E2 的 independence 每项包含 receiptId、blockId、actorId、originId、basis、scope。至少两个已引用的可见样本，作者、原始观察和正文内容都须不同；完全重复正文即便换 URL 或声明不同作者也不算独立。scope 明确 same_site/cross_site，按实际读取 URL 主机区分，不能仅换来源 ID 就声称跨站。主机不同不保证实际作者独立，basis 仍需 Agent 核验；系统不能证明填写的作者身份真实，也不能识别所有改写转载。

payment 为空或包含 stage（intent/quote/paid）、basis 和 refs，引用必须来自该主张的已读材料。E3 必须是 fact 且有支付核验材料；作者声称收入不能以 author_claim 标记直接升为 E3。程序只核验前置材料齐备及引用一致，语义真假、采购是否真实、作者身份及核验说明是否充分仍由研究判断，不能把通过校验称为交易认证。

counterEvidence 每项包含 text/refs，也必须引用实际读取块。rebutsClaim 保存所反驳主张的文字定位。校验输出不复制正文缓存；所有阅读文字仍按外部不可信资料处理。partial 凭据仅支持已见块，不证明评论完整，更不能按页面总评论数补样本。

测试使用受控合成读取结果，覆盖未知成本、来源/日期绑定、假凭据和未读回复、缓存缺失、推断等级、作者收入自述、E2 重复作者/转载、E3 核验材料、分流、反证、取消及更新版本冲突。不代表已完成在线研究。
