# 单步原子发布（R12）

`ResearchPublisher(runtime).publish_step(run_id, token, intent_id, request)` 将一项已准备好的公开研究写入资料层。它只接受已通过 `save_intent` 保存的稳定意图；意图固定目标记录 ID、业务 operationId、请求摘要和预期版本。租约令牌不参与业务摘要，因此恢复后取得新执行权仍能回放同一业务请求。

每次调用先在写事务中校验数据库身份、owner、fence、租约期限、run、意图摘要、目标 ID 和预期版本。随后调用与 `ResearchStore` 相同的创建或修改内核，将业务正文、不可变版本、研究事件、业务操作回放以及本机意图完成回执一并提交。完成回执只保存 `{recordId, revision}`，正文仍以业务版本为准。提交前任一步失败会整体回滚；调用方在提交后丢失响应时，可用相同意图和请求重放，返回当时固定的记录版本，不重复新增历史。

请求只有两种严格形状：

- create：`action`、`record`、`reason`，意图的 expectedRevision 必须为 null。
- patch：`action`、`recordId`、`expectedRevision`、`patch`、`reason`，版本必须与事务内当前版本一致。

新 Evidence 必须包含 observation，并在事务内重新检查 ReadReceipt 存在、状态可读、来源和 URL 一致、块定位实际存在、回复定位属于已观察块，以及访问时间和发布日期精度均来自该凭据。该检查不重新解释正文语义；R10 的分析校验仍是前置步骤，R13 才负责把分析稿转换为多步发布意图。

发布接口拒绝 Assessment、个人字段和 ReadReceipt 伪造。Assessment 属于独立判断接口；收藏、忽略、验证阶段和私人笔记仍由个人域保存。Reader 是唯一能创建 ReadReceipt 的入口。目标 ID 已存在会返回 DUPLICATE_ID，版本已变化会返回 REVISION_CONFLICT；接口不会静默覆盖或合并不同记录。精确重复和 canonical 处理由 R11 检查及后续发布编排决定。

本机备份会验证完成回执、固定记录版本和业务 operation 的摘要及结果完全一致。恢复会轮换数据库身份并使旧租约失效；新 owner 取得执行权后可重放已完成步骤。当前接口一次只发布一个步骤，不创建 PublicationManifest，也不自动推进候选、来源游标或后续步骤，这些属于 R13–R14。

测试覆盖创建、修改、提交前故障回滚、提交后响应丢失、请求变化、旧 owner、目标冲突、版本冲突、未读块、个人字段、Assessment 以及备份恢复。所有网页和模型文字仍视为不可信数据，校验通过不代表现实需求或付款事实已由程序认证。
