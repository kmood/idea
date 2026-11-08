# 翻译服务公开评价中的重复买方信号

日期：2026-10-27（Asia/Shanghai）。研究问题：公开平台是否能把“期待再次合作”推进到同一买方跨项目评价？本页仅检验复购证据形态，不推荐或新增翻译点子。

## 原始材料和角色

[CN302 Freelancer公开档案](https://www.freelancer.com/u/transmanual24)第170—186及233—343行；[平台评分说明](https://www.freelancer.com/support/freelancer/project/freelancer-ratings)定义重复雇佣率为既有客户再次聘用的比率。平台档案显示“25%”重复雇佣率，但未给分母、期间或算法细节；这只是平台统计，不是独立银行流水。

同一档案内，买方显示名Dragos V.出现在三则不同项目评价：乌尔霍博语翻译（显示50美元、相对4个月前）、英语至曼丁卡语翻译项目一（800美元、相对10个月前）与相近标题的项目二（85美元、相对10个月前）。三则都为买方评价区内容，不是供应方自述；相对时间由页面展示，未推算绝对日期。另有Tim R.评价文字称“多次合作”，但本次只见其一条评价，不能计作第二条可核项目。供应方档案自称是团队/公司，服务覆盖大量语种；不得迁移为单人可复制的报价或交付能力。

## 支持范围和反证

- 平台同一显示名、不同项目标题和不同页面金额，构成比“期待再次合作”更强的买方重复下单信号。乌尔霍博语与曼丁卡语是不同需求，至少平台展示为不同项目评价；但同名不等于实名核验。两条曼丁卡语标题相近，项目是否拆单或同一委托无法确认，不当作完全独立需求。
- 平台金额是评价关联项目的展示数，不是团队或个人扣除平台费、译员工资、返工、税费后的净到账。三个项目详情页点击均返回缓存未命中，无法核对需求原文、验收、结算或退款。档案有110条评价不等于110名独立买方。
- 供应方具有团队及多语种能力，竞争、质量控制与内部审校投入未知；AI及免费机器翻译为可能替代，但本轮无同单替代比较。平台历史评价也不证明当前可获同类买方。

判断变化：公开资料确有较具体的重复买方线索，但仍无法满足“同一买方两笔实际支付、供应方净回款”的完整证明，不晋升候选。若以后能读取三个项目详情并匹配买方身份、完成状态和实际付款，再核对是否跨时间复购；访问失败不作推定。

## 后续同轮复核：不同买方的具体订单范围

2026-10-27 23:25，通过检索找到并完整读取[CN303阿拉伯语界面复核项目40547881](https://www.freelancer.com/projects/linguistics/arabic-translation-verification)；这是档案中Tim R.评价所指的项目，不是Dragos V.三笔仍未读到详情的项目。原页第93—107行由买方写明：已有沙特阿拉伯语译稿，需复核713个界面键、约5600词，另核两份各14页幻灯片，交付为更新后的本地化键和幻灯片。第93—150行显示预算30—250欧元、已完成、9份提案及授予该团队；团队在竞标中写100欧元/3天，第245—258行平台显示买方付款方式已验证。档案评价区该项目显示105欧元且买方给好评。

这补足了一个买方原始需求、工作量与平台选人/完成状态，也形成强烈单位经济性疑问：页面价额与713键、5600词、28页的核对范围相对照，但总工时、是否全部实际完成、团队内部分工、平台费及实际提现都未知，不能计算时薪。页面的“Paid on delivery”是付款安排标签，“Payment method verified”是买方支付方式验证，均不是本单银行到账证据；档案评价价额亦不直接等于净回款。该客户评价说多次合作，但仍未找到其第二个与同一供应方的可核项目，不把它用于复购判断。与CN302同一供应方/订单链，独立买方数只增加一个可定位项目，不把两页算两单。

## 23:55 平台评价与付款的关联边界

[CN306 Freelancer公开评价资格说明](https://www.freelancer.com/faq/topic.php?id=23)第13—23行写明：评价与项目完成、平台Milestone Payment有关，允许部分付款后将中标金额改为已付金额，再标记完成。[平台较新帮助页](https://www.freelancer.com/support/Payments/feedback-option)则区分固定价项目完成后的评价和时薪项目已付周里程碑后的评价；两页均未标生效日期，表述不完全一致，不能证明CN302各项目发生时适用的精确条件。平台规则是平台自身说明，不是独立流水。故CN302同名买方的三条公开评价可视作比单纯“已完成”更接近站内支付的信号，但不能将评价显示的50/800/85美元逐笔记为实际付款，更不能写成提款到银行、净回款或已跨期稳定复购。若取得对应项目详情/交易记录和买方身份核验，才可能进一步升级；现阶段候选维持0。


## 2026-11-09 回源：项目40547881登出态结构化字段复核

未登录只读项目页（HTTP 200，1.10 MB），解析页面 `webapp-state`（NGRX_STATE.projectsSeo 内嵌 rawDocument）取得结构化字段，与10-27人工行读互证：

- 项目 `projectId=40547881`，title “Arabic UI Translation Verification”，固定价（type=fixed），status=closed、subStatus=closed_awarded；startTime=2026-06-29 21:21 UTC、latestActivityTime=2026-06-29 22:37 UTC，页面发布日期的相对时间由此得到绝对参照。预算 30–250 欧元（currencyDetails EUR，exchangeRate 1.14151），bidStats：9 份提案、平均报价 146 欧元。
- selectedBids 仅一条：TransManual24（地址孟加拉国 Dinajpur），amount=100 欧元、period=3 天、completed=true；sellerRating average=5、reviewCount=97 为该团队账户累计信誉，不是本单评价；userEarningsPercentage=7.04 是平台对投标账户的统计字段，不是本单放款或净收入。
- NGRX 状态中 `milestones:{}`、`milestoneRequests:{}` 均为空对象，employerFeedback/freelancerFeedback/projectFeedback 在登出态不存在；无里程碑放款、托管释放、提现、银行到账、本单评价或复雇字段。client 对象 rating 为 0 条评价，verification 仅 paymentVerified=true、emailVerified=true、phoneVerified=true、depositMade=true——depositMade 是买方账户级托管验证，不证明本单已付款。页面仍只有 “Paid on delivery” 付款方式标签。
- otherEmployerJobs 暴露同一买方另两个条目：“Spanish Website Translation Audit”（30–250 欧元，/projects/editing/spanish-website-translation-audit）与 “Flutter App In-App Purchase Expert Needed”（15–25 美元/小时）。前者是潜在的同买方第二个翻译类项目，可能对应 CN302 档案中 Tim R. “多次合作” 评价，但本轮不展开、不计复购，留待后续轮次回源该项目页核对买方身份与完成状态。

结论不变：本页支持具体买方需求、选人（100 欧元中标）与平台完成状态，但登出态仍无法证明实际放款金额、译员净提现或总工时；CN302 档案评价显示的 105 欧元与本单投标 100 欧元的差异继续保留历史原句，不用结构化字段覆盖。候选仍为 0。

## 2026-11-09 第二轮回源：同买方第二单落地，重复授标确认但实收仍不可见

未登录只读两页（各约 1.1 MB，均 HTTP 200，共 2 次请求），解析 NGRX_STATE 内嵌 rawDocument 并逐字段比对。

### Spanish Website Translation Audit（projectId=40449131）

- 固定价，status=closed、subStatus=closed_awarded；startTime=2026-05-17 07:56 UTC、endTime=2026-05-24、latestActivityTime=2026-05-18 09:18 UTC。预算 30–250 欧元（EUR，exchangeRate 1.16151），bidStats：12 份提案、平均 50 欧元；rawDocument 仅内嵌 5 条投标样本，授标记录另在 selectedBids。
- 买方原始需求：英文信息页已译为西班牙本土西语，要求对照英文源复核 610 个翻译键，查误译与生硬表达并给出润色替代；须使用买方 SimplyLocalize 工具，并有一次简短在线会议做工具说明（brief online call）——含一次性语音环节，与避免频繁英语语音的私人条件相关但不等同持续客服。
- selectedBids 仅一条：TransManual24（孟加拉国 Dinajpur），amount=30 欧元、period=1 天、completed=true；sellerRating 5.0、reviewCount=94（账户累计，非本单评价）；userEarningsPercentage=7.02 为账户统计，不是本单放款。

### 同一买方与重复授标的确认

- 两项目 client 对象逐字段完全一致（registrationTime=1702472417000、迪拜地址、零评价、paymentVerified/emailVerified/phoneVerified/depositMade 均 true、profileComplete=false），且 CN303 页 otherEmployerJobs 曾列出本项目，确认同一买方。
- 时间线：西语审核 2026-05-17 授标 30 欧元/1 天 → 阿语界面复核 2026-06-29 授标 100 欧元/3 天，相隔约 43 天，同一买方两次把项目授予同一团队 TransManual24，两单 selectedBids 均 completed=true。这是库内迄今最直接的“同买方→同供应方重复授标”平台结构化证据，可关闭上轮留下的“第二单是否存在、是否同供应方”未知。
- 口径差异原样保留：两页内嵌的 TransManual24 reviewCount 分别为 94（西语页）与 97（阿语页，本轮复抓仍为 97），疑为页面快照/缓存口径不同，不自行统一。

### 七层裁决与边界

证据推进到“授标＋平台完成状态”层（两单均 closed_awarded、completed=true），但登出态 milestones/milestoneRequests 仍为空对象，无托管释放、放款金额、提现、银行到账、本单评价字段；买方零评价、depositMade 仅账户级验证。因此：

- 可确认：真实需求、报价区间、授标选择、平台完成状态、同买方对同团队的重复授标；
- 不可确认：30/100 欧元是否实际放款、译员净提现、总工时与复购付款；重复授标不等于两笔钱均已到账，不升 paid；
- 该供应方为孟加拉国团队账户（2007 年注册、90+ 语言模板化投标），其路径不能直接等同于用户个人获客；一次性简短在线会议与英语沟通仍是门槛。

结论：CN303 维持 E3、需补证，不进候选/精选；本轮回源把“复购”未知从无证据收窄为“重复授标已确认、重复实收未确认”。候选/精选仍 0/0。
