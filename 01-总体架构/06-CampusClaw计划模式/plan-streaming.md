# 计划正文流式生成与审核绑定

版本：1.1.0；日期：2026-09-19。状态：**目标设计，待实现**。普通文本流、完整计划审核和批准续跑已实现；标记解析、计划 delta、空参数退出及前端预览为待实现增量。[主设计](README.md)维护模式与审核事务，[源码证据 §14](source-evidence.md#plan-marker-evidence)维护本次源码范围。

## 1. 当前流程与等待来源

实现核验为 pi-mono-java main `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12`，未覆盖本地旧工作树。当前模型把完整正文放入 `ExitPlanMode({plan})` 参数；Provider 虽可产生参数增量，Runtime 公共投影只处理普通文本/思考增量。响应结束后先保存 Assistant 和完整调用，beforeToolCall 才取出 plan、保存计划与 confirming、关闭该段 SSE。工具本身不生成正文，而是等待用户决定；批准后原执行切换 Build 并继续。

这使计划首字不可见时间包含整份参数生成时间。没有生产计时证据，不能推断模型、数据库、网关分别占用的时间，也不能宣称流式降低了整体任务耗时。

## 2. 目标：标记识别与计划专用增量

Main Agent 在同一 Assistant 响应中输出一个 `<proposed_plan>` 块，再调用唯一的 `ExitPlanMode({})`。标记属于模型输出约定，由后端解析，不是前端协议。标记外的前置说明投影为 `agent.message`，标记内正文投影为 `agent.plan`；Thinking 不参与正文解析。前端不识别标签、标题或工具参数，也不把普通消息事后改装为计划卡。

`agent.plan` 只使用 `phase=delta/completed`，与其他文本事件保持一致。识别开始标记时只在内部预分配不透明 plan eventId；第一段非空正文才发送 delta，前端以此创建“计划生成中”卡片。不新增 started、空 delta、百分比或独立开始事件。同一计划的所有 delta 与最终 completed 使用相同 eventId；修订或新的模型响应使用新 ID，预分配不等于保存成功。

### 2.1 模型输出与工具契约

| 项目 | 规则 |
|---|---|
| 标记 | 精确英文 `<proposed_plan>` / `</proposed_plan>`，各独占一行，不翻译、不包在外层代码围栏中；标记行是保留控制行，正文举例需转义，不能嵌套或出现第二个块 |
| 解析作用域 | 仅 Runtime Main Agent 的 Plan 响应正文；普通 Build、Thinking、工具结果和 Subagent 返回不启动计划卡解析 |
| 正文 | TextContent 按原顺序直接拼接，解析器状态跨 chunk/文本块；去除两条标记行及其行结束符，其余正文原样保留，不 trim、不补换行、不重写 Markdown；支持 LF/CRLF 和最终无换行的结束标记 |
| 顺序 | 可有前置普通说明；计划块结束后只允许空白，然后唯一 ExitPlanMode 调用；调用后不允许非空正文。前置说明保持在计划卡之前，不将后置普通文本拼回旧消息造成时序倒置 |
| 调用 | `ExitPlanMode({})`，Schema 为空对象且 additionalProperties=false；正文只生成一次，不放回参数，也不要求额外一轮模型请求 |
| 绑定 | 后端以当前 Assistant、已保存原始 Entry、固定执行/段和唯一调用建立不可变快照；不接受模型提供的 eventId，不查找“最近一条答案” |
| 大小 | 计划最多 262144 UTF-16 单元，首个非空行以 `# ` 开始，同时满足原 Assistant、计划完整帧及现有缓冲容量；超限不截断为可审核正文 |
| 缺失或错误 | 缺块、缺结束标记、空正文、多个/嵌套块、非法顺序、混合工具、ERROR/ABORTED/LENGTH 均不得提交审核；有退出调用时走既有 PLAN_REVIEW_UNAVAILABLE，参数非法为 TOOL_ARGUMENTS_INVALID，容量异常沿用 EVENT_PAYLOAD_TOO_LARGE |
| 仅正文无调用 | 不创建待交互，也不自动补工具或开启下一轮；既有 Loop 自然结束后预览标为“未提交审核” |
| 返回 | 工具只返回完整 approved/feedback 结果，失败不批准；批准后才切 Build，修订重新生成完整块 |

解析器只暂存可能构成控制行的前缀；一旦排除标记立即释放普通正文，不等待整行或整份方案。前缀有界，正文受累计长度预算限制。遇到确定的结构错误即停止该候选后续 preview，最终再次验证完整响应；不得将已发出的计划增量当作最终内容或审核依据。完整响应中的计划正文可以校准 preview，不能强制要求最终正文等于客户端收到的全部增量。

### 2.2 目标顺序

![计划流式生成与审核绑定](plan_streaming_sequence.svg)

[原尺寸 SVG](plan_streaming_sequence.svg) · [PlantUML 源码：plan_streaming_sequence](diagram.puml#L836)

1. 模型文本增量经过 Provider → Agent MessageUpdate → Runtime 计划解析器；普通说明走 agent.message，计划正文走 agent.plan delta，开始标签本身不发事件。
2. 响应完整后用相同语法重解析原始 Assistant，形成不可变解析结果。先保存原始 Assistant Entry、仅前置普通正文的 agent.message completed 和一次 usage，再保存唯一完整 tool_call。
3. Binder 绑定已保存 Entry、解析结果、预分配计划 ID、原根与唯一退出调用；没有预览时也可从完整响应分配 ID，不以 delta 成功投递为前提。
4. beforeToolCall 的审核事务锁内重查固定执行/段/分支、原 Entry/调用、mode=plan、未停止、无其他待交互；保存 agent.plan completed、待审指针和 confirming。
5. 提交成功后发送 completed 和 confirming，关闭本段 SSE。completed 全量替换同 ID 预览；只有与 confirming、Session/后续记录对账通过后可审。Session 仍 running/plan，工具仍未返回。
6. approve/revise 沿用原接受、领取和续跑事务；批准目标仍为计划 eventId，不是 Assistant ID、toolCallId 或预览文字。

闭合标记只表明文本块结束，不发送 completed、不切换模式、不表示审核已经成功。权威 completed 的产生时点仍是审核事务成功，而非模型流刚结束。

## 3. 权威对象与内部职责

复用[完整目标类图](README.md#3-推荐全局目标类图)，不新增第二套 Agent Loop、HTTP 路径或计划文件。

| 对象 / 接入点 | 生命周期与职责 |
|---|---|
| RuntimeEventProjector | 每执行；MessageStart 创建当前响应解析状态，路由普通/计划增量，保存完成后的原 Entry 身份；不可依赖 persistAssistant 后已清空的 assistantEntryId |
| PlanTextParser（待实现） | 每 Assistant 响应一实例；由 Projector 持有，处理跨 chunk 保留标记和正文，生成普通/计划片段；完整消息重解析也使用同一语法实现，不属于通用 Provider 层 |
| PlanTextSnapshotDTO（待实现） | 完整响应解析后不可变；包含普通正文、计划正文与结构有效性；公共消息投影与审核绑定共享一次最终解析结果，不分别裁剪正文 |
| PlanProposalBinder（待实现） | 无状态；绑定当前响应、已保存原始 Entry、PlanTextSnapshotDTO、唯一退出调用和预分配 ID，校验来源及顺序 |
| PlanProposalSnapshotDTO（待实现） | 每候选至审核收尾；不可变字段为固定执行目标、assistantEntryId（内部）、planEventId、sourceEventId、toolCallId、content；来源身份不暴露给客户端 |
| PlanReviewPort / RuntimePendingInteraction | 提交携带共享快照；工具 await(toolCallId, cancellation) 只等待已绑定调用，不再传入第二份正文 |
| Persistence / Repository / EventFactory | 事务内重新校验可变状态，沿用原 Entry 和事件关联保存 plan completed；GET 读保存值，不重解析模型历史，不持久化每个 delta |
| Client reducer / PlanCard | 按 Session + eventId 维护计划 preview/完整记录，并检查 sourceEventId 一致；第一条 delta 建卡，completed 覆盖；普通消息与计划有不同 ID |

模型上下文保留原始带标记 Assistant、空参数调用及配对 ToolResult。公共 agent.message 只含标记外前置说明，不重复计划；无普通正文时保留 content="" 的完整消息及一次 usage，前端不绘制空消息。计划不重复 usage，也不再次注入模型历史。审批后首次模型请求必须保留原始获批块及调用/结果，压缩不得以摘要替代并声称等价。

解析状态与候选按当前 Assistant、执行和段隔离；新响应、终态、取消和清理释放旧缓冲。即使 toolCallId 重复也不得跨响应取旧计划。沿用原内存凭据/等待对象边界，不增加进程崩溃自动接管能力。

## 4. 公共事件与页面恢复

精确字段和 POST/GET 示例唯一维护在[共享事件源](../01-CampusClaw多Agent运行时/事件契约/common.json)与其操作 JSON，本页只解释生命周期。

| 阶段 | 字段与行为 |
|---|---|
| agent.plan delta | eventId/type/sourceEventId/phase/content；content 为非空新增文本；不带 createdAt、toolCallId、usage、sourceMessageEventId；不入历史 |
| agent.plan completed | eventId/type/sourceEventId/phase/content/createdAt/toolCallId；content 为完整计划，无标记；与历史同名同形，后续不得再发同 ID delta |
| user.plan_confirmation | 保持 targetEventId/result/条件 feedback；只允许引用当前待审核完整计划，不因预览 ID 已分配而接受批准 |
| 旧完整计划 | 既有无 phase 的记录按完整计划解码，不重写存量；新写明确 completed；旧记录不补造来源关联 |

新事件不引入 planId/version，也不使用 sourceMessageEventId 做卡片合并；来源 Assistant 的约束保留在后端。完整事件在 SSE/GET 保持一致，旧无 phase 形状仅用于已有数据兼容；旧的完整记录在实时补读中同样可识别。

没有 delta 时，completed 直接建卡。只有 delta 而未收到 completed 的卡片始终不可审：该段可信 done/failed/terminated/confirming 到达后停止生成提示并标为“未提交审核”；若其他完整计划出现，只将其对应卡片设为已提交，不把旧预览升级为它。单纯 EOF/断网显示“待核对”，补读历史和 Session；缺页、旧根、冲突或未知状态禁审，不重放 POST。

preview 是 best-effort；丢弃一个计划 ID 的增量后，该连接停止该 ID 后续 delta，等待完整内容覆盖。增量内容不按文本去重（重复文本可能合法）；completed 按 eventId 幂等合并，已完成后迟到 delta 忽略。内部与跨实例响应只保证完整事件可恢复，不承诺丢失增量续传。没有 completed 的中止草稿可仅保留本页只读展示，刷新不承诺恢复。

前端只对正文使用受限 Markdown；标签不进入显示或复制结果，开始标签无正文时不画空卡。保留滚动、复制和焦点，状态通知不逐 token 播报，不显示虚构百分比。原型没有本增量，不能以既有原型通过代替真实流式验收。

Mate 公共桥接待实现；公共 POST JSON、GET 长连接和历史分页保持各自契约。桥接须统一映射原根、计划 ID 与工具身份，预览和 completed 使用同一公共计划 ID，不能每片新生成 ID或透传内部 sessionId。公共计划/确认/模式模型需同步确认并实现后再开放企业入口；本专题不扩大为重做所有 Mate 接口。

## 5. 取舍、兼容与性能验证

采用后端标记解析与专用计划 delta 是架构变更：让前端在生成中直接知道内容类型，不承担模型语法解析，也不需要事后换卡；代价是增量解析、最终解析、候选身份及接口联合类型同步。仅两种 phase 是与现有文本事件保持一致的产品决定；不引入 started，第一字之前仍显示既有规划活动状态。

完整审核事务、单交互和原根续跑是产品约束。要求完整闭合、唯一块、固定来源与锁内复核是一致性/安全约束；Codex parser 的 finish 可收束未闭合块，不作为本产品允许截断方案进入审核的依据。保留正文为工具参数会继续等待整份参数或增加 JSON 增量解析；普通消息事后转卡不能满足生成期间识别计划的目标。

不新增 Maven/npm 直接依赖、数据库表或独立资源。复用 JDK 的字符状态机、现有 Jackson、Spring/MyBatis/Bean Validation、Vue 与 Markdown renderer。发布前停止新 Plan 接受并排空/中断旧活动执行，再同步工具 {} Schema、预制/业务 PLAN/BUILD、解析/编解码/历史及前端。先升级读取端兼容旧无 phase 完整计划和新两 phase，再启用新写；不能把合法旧工具参数当成新协议混用，不在执行中途切换提示词快照。

计时点为请求开始、首个 TextDelta、首个计划正文 delta、模型完成、Assistant 保存、审核事务成功、浏览器首字与审核可用。比较相同模型/任务/上下文的首字和可审总耗时；检查代理缓冲、SSE flush、渲染批处理和正文规模，不承诺未经实测的百分比收益。计时日志不记录正文、推理或凭据。

## 6. 实施切片与验收

| 切片 | 范围 | 必须验证 |
|---|---|---|
| PS1 | PLAN/BUILD、业务覆盖及工具 {} Schema | 同响应单块后唯一调用；正文只生成一次；无额外模型轮次；Build/Subagent/普通解释不误建卡 |
| PS2 | Parser、最终解析 DTO、Projector、Binder | 标签每个字符切分、跨 TextContent、LF/CRLF、结束无换行；不等待整行；只有标签不发空 delta；多块/嵌套/缺闭合/顺序/错误/截断拒审；原始上下文与普通投影分别正确；同响应和不同根隔离 |
| PS3 | 两 phase 编解码与审核事务 | delta 不带保存时间/调用/usage；不支持 started；同 ID 最终覆盖、未发 preview 也能提交；保存先于 completed；调用和原 Entry 精确绑定；停止竞争不误审；旧无 phase 可读、新写必 completed；首次批准模型调用保留获批块及配对 |
| PS4 | 前端卡片、历史及失败恢复 | 首非空 delta 建卡、completed-only 建卡、前置说明不重复计划、usage 一次；部分增量丢失/最终校准/迟到/断网/中止/缺页/修订/409 不误审；普通根不串用；390 px、键盘焦点和滚动保持 |
| PS5 | Provider/Mate/发布与性能 | 实际模型生成标记正文后工具；网关及时输出；跨实例仅完整输出可用；公共两跳同一计划身份不泄露；业务覆盖迁移；记录首字/可审核耗时，失败与回滚可读旧历史 |

契约样例与校验器只能证明设计数据一致，不能证明 Java 标记解析、数据库、浏览器或真实模型性能。这些实施验收均待执行。

## 7. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.1.0 | 2026-09-19 | 后端解析计划标记，使用同一计划身份的 delta/completed 流式展示并在审核提交后完成。 |
| 1.0.0 | 2026-09-19 | 定义同响应正文生成、空参数退出调用与审核绑定。 |
