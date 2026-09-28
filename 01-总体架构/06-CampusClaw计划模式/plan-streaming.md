# 计划参数流式生成与审核绑定

版本：1.2.0；日期：2026-09-28。状态：**参数来源调整待实现**。Java main `553dcd5e2ff682f9684810a043b442b37a02e54a` 已实现正文标记解析、`agent.plan delta/completed`、审核及前端预览；本目标恢复 `ExitPlanMode({plan})`，通过参数增量继续提供计划预览。模型可靠性与端到端时延仍待实测。[主设计](README.md)维护模式与审核事务，[源码证据 §15](source-evidence.md#plan-argument-streaming-evidence)维护本次源码范围。

## 1. 当前流程与问题

设施巡检方案应在生成时可读，完成后准确进入审核。当前 Java 要求模型在正文中生成精确的计划标记，再在同一 Assistant 中调用唯一的空参数 ExitPlanMode；任一标记、顺序或绑定条件不满足，便不能形成可审核计划。未调用工具时，普通回答会自然结束，并不会由 Runtime 自动补一次审核。该实现已落地，不能继续把正文流式整体标为待实现。

此前 `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12` 通过 `ExitPlanMode({plan})` 提交完整计划，参数生成期间没有公共预览。用户观察该方式提交准确；这是实际使用反馈，不是成功率统计。本目标将生成和提交收敛为一次有 Schema 的工具调用，再从同一调用参数提取展示增量，减少必须依赖正文标记的条件。仍需模型正确调用工具，不能保证任何模型都必然提交。

当前 Mate Provider 已产生 `ToolCallDeltaEvent`，但工具名称和 ID 在完成前未同步进 partial ToolCall，Runtime 也未将参数增量投影为计划。本目标必须补齐身份和增量投影接线；不能只恢复参数 Schema 就宣称流式已完成。Codex 当前公开源码采用正文计划与独立 Plan item，不能从其产品体验推断本项目不同模型、Prompt 和 Provider 组合也有相同可靠性；对照及版本边界见 §15。

## 2. 目标：完整参数提交与计划专用增量

Main Agent 直接调用 `ExitPlanMode({"plan":"# 设施巡检方案\n\n..."})`。模型只生成一份完整 Markdown，不再要求正文控制标记，也不要求先输出正文再调用空参数工具。后端从该调用的参数增量中解码 plan 字符串，继续发送既有 `agent.plan delta`；完整参数通过最终校验与审核事务后，发送同 ID 的 completed。前端继续渲染计划事件，不解析模型参数或猜测文本类型。

`agent.plan` 保持 `phase=delta/completed`，不增加 started、百分比或独立开始事件。后端确认可信内置工具身份后分配计划 eventId，第一段非空已解码正文才发送 delta；同一计划的 delta 与 completed 使用相同 eventId。修订或新的模型响应使用新 ID，预分配不等于保存成功。无预览也可直接提交完整计划。

### 2.1 模型输出与工具契约

| 项目 | 规则 |
|---|---|
| 调用 | `ExitPlanMode({plan})`；parameters 为 object，required=[plan]，additionalProperties=false；plan 为 string，minLength=1，maxLength=262144；应用层同时校验 UTF-16 单元数与首个非空行以 `# ` 开始 |
| 作用域 | 仅 Runtime Main Agent 当前 plan 响应中的可信内置 ExitPlanMode；Build、Subagent、Thinking、普通文本、工具结果及其他工具不启动计划预览 |
| 正文 | 参数完整解码后的 Markdown；保留换行、空格及 Unicode，不 trim、不重写；计划正文只出现在参数中一次，不要求控制标记 |
| 绑定 | 完整 Assistant 正常以 TOOL_USE 结束且只有该 ToolCall；绑定已保存原始 Entry、固定执行/段、当前响应、调用和一次准备快照，不查找最近答案，不接受模型提供的 eventId |
| 大小 | 完整 plan 最多 262144 UTF-16 单元，并满足原 Assistant、完整调用、计划编码帧及既有缓冲上限；JSON 转义后的原始字节预算与解码正文预算分别限制，超限不能截断成可审计划 |
| 参数错误 | 完整合法 JSON 中缺参、错型、额外字段、标题或长度不合法：真实 isError=true，向模型返回字段错误与同次校验使用的可信定义；不确认、不执行、不猜参、不自动重放，下一轮由模型修正 |
| 原始流错误 | 非法/未闭合 JSON、重复键、尾随垃圾、ERROR/ABORTED/LENGTH 不提交审核；沿 Provider/响应错误路径处理，未形成合法调用时不伪造 ToolResult；容量错误沿用 EVENT_PAYLOAD_TOO_LARGE |
| 绑定错误 | 非当前调用、身份冲突、混合工具或来源不完整：不提交审核，沿用 PLAN_REVIEW_UNAVAILABLE 等既有失败分类；不复用旧候选或改变模式 |
| 未调用工具 | 普通解释不创建待交互；不由后端生成计划或补调用，不因模型说“已完成”而退出模式 |
| 返回 | 工具等待真实 approved/feedback；批准后才应用 build 并继续，修订保持 plan 并重新提交完整参数；失败不授予权限 |

增量提取不能用正则裁剪 JSON 或直接拼接原始 arguments。必须以 JSON 词法状态解码目标字符串，处理引号、反斜线、换行、跨片 `\uXXXX` 和代理项；只发布已确定且 Unicode 完整的前缀，半个转义或代理项继续保留；最终 plan 中的孤立代理项或未完成转义必须拒绝，不替换非法字符形成可审计划。重复键、未知字段、非字符串、尾随内容等在最终严格解析与参数校验中拒绝，不采用宽松解析的“最后一个值获胜”。预览尚未看到的字段也可能令最终调用无效，故预览永远不是合法性证明。

内部流身份至少包含当前响应与 contentIndex，并与固定执行/段隔离。Mate 保留现有 ToolCallDeltaEvent 结构，在每次新建的 partial 快照中及时提供截至该片已确定的工具名称/ID；身份尚未齐全时，Runtime 先有界缓存，不改写已发出的快照。预览和最终结果都必须匹配已装配的可信内置工具及完整 ToolCall。不能把任意名为 plan 的参数转成计划，也不能仅凭 Provider index 跨响应关联。中途身份变化应废弃候选；达到缓存预算时停止该候选 preview，仍可在完整响应合法且容量允许时提交。解析按新增输入推进，避免每片重扫累计文本造成平方级开销。

### 2.2 目标顺序

场景是模型为设施巡检生成一份可审核方案。起点是当前响应出现退出工具参数增量，终点是完整计划与审核等待提交；批准续跑引用主设计审核图。本图为待实现的参数流接线，沿用已实现的公共事件和事务，不表示新增远程边界。

![计划流式生成与审核绑定](plan_streaming_sequence.svg)

[原尺寸 SVG](plan_streaming_sequence.svg) · [PlantUML 源码：plan_streaming_sequence](diagram.puml#L655)

1. Provider 将原始流归一化为内部工具参数事件；Runtime 在可信身份确定后提取 plan 字符串，发送非空 agent.plan delta。普通说明继续走 agent.message，Thinking 不参与计划解析。
2. 完整响应到达，Provider 严格解析最终参数，Runtime 保存原始 Assistant 与完整 ToolCall。原始记录保存不代表参数通过业务校验，也不表示审核就绪。
3. 运行时从当前已装配工具集中解析可信目标，再由 ToolPipeline 校验完整参数；`ExitPlanModeTool.prepare` 校验标题等语义，建立不可变 `PlanArgumentSnapshotDTO`。`BeforeToolCallContext.preparedInvocation` 将同一次准备结果交给 Host，避免展示与审核分别取值。
4. Binder 将该快照绑定到当前完整响应、已保存 Entry、唯一退出调用及预分配计划 ID；Host 在审核事务中重查固定执行/段、当前模式、停止状态和单交互条件，保存 agent.plan completed、待审指针与 confirming。
5. 提交成功后发送 completed 与 confirming，结束本段 SSE。completed 全量替换同 ID 预览；与等待记录及 Session 对账后才可审。Session 仍 running/plan，工具仍等待真实决定。
6. approve/revise 复用原接受、领取与续跑事务；批准目标仍是计划 eventId。批准后工具返回，后续业务调用继续独立执行可信目标解析、参数校验、权限判断/必要确认、业务执行和结果回传，不因计划批准跳过工具授权。

最终完整参数是唯一计划内容来源，不要求它等于客户端实际收到的所有 delta。流中丢片、没有 preview 或停止投递 preview 都不改变最终权威来源；最终参数无效则不能以预览兜底。参数闭合与模型结束均不直接发送 completed 或切换模式。

图中 AgentLoop 覆盖模型请求与 Provider 归一化的事件交付；ToolPipeline 是工具执行职责，包含现有 Loop 分派时的已装配工具查找和 ToolExecutionPipeline 的 validate/prepare/hook/execute，不声称现有 Pipeline 类独自解析工具注册表。Host 对应 Projector、Binder 与审核应用编排，Session authority 对应既有事务/Repository 权威，Client 为事件 reducer 和计划卡；这些角色不表示新进程或远程调用。

## 3. 权威对象与内部职责

复用[完整目标类图](README.md#3-推荐全局目标类图)，不新增第二套 Agent Loop、HTTP 路径或计划文件。

| 对象 / 接入点 | 生命周期与职责 |
|---|---|
| Mate Provider / ToolCallDeltaEvent | 传输中立的调用增量与身份；当前已产生参数 delta，身份在 partial 中及时可见的接线待实现；不认识计划业务或直接输出公共事件 |
| RuntimeEventProjector | 每执行；按当前响应/调用持有预览状态，保存原 Entry 身份并衔接完整记录，不依赖已清空字段找回来源 |
| PlanArgumentPreviewParser（待实现） | 每响应/调用一实例；有界解码参数中的 plan 字符串，只生成临时展示，不负责最终权威校验、不触发执行 |
| ExitPlanModeTool.prepare / PlanArgumentSnapshotDTO（调整/新增待实现） | 由 Pipeline 在 Host 交互之前准备；完整参数及语义校验后生成不可变 plan 快照，与本次 PreparedToolInvocation 关联，供审核绑定与工具执行共享 |
| PlanProposalBinder / PlanProposalSnapshotDTO（现有类型已实现，参数来源调整待实现） | Binder 绑定已保存 Entry、上述准备快照和唯一调用；Proposal 固定执行目标、assistantEntryId（内部）、planEventId、sourceEventId、toolCallId 与 content，事务内另查可变状态 |
| PlanReviewPort / RuntimePendingInteraction | `review(toolCallId, cancellation)` 仅等待已绑定审核；不在等待接口再传另一份正文；单交互、取消和续跑边界保持 |
| Persistence / Repository / EventFactory | 事务校验与完整计划保存；GET 读取权威记录，不重解析模型历史、不持久化每片参数 |
| Client reducer / PlanCard | 按 Session + eventId 维护预览和完整记录，检查 sourceEventId；第一条 delta 建卡，completed 替换，普通消息与计划各有 ID |

模型上下文保留原始 Assistant、携带完整 plan 的 ToolCall 和配对 ToolResult；公共 agent.plan 是同一内容的展示投影，不重复注入模型历史。普通消息只展示模型实际普通正文；无正文时沿用完整消息/usage 的既有记录规则，不绘制空消息、不重复 usage。批准后首次模型请求必须保留本次调用的完整 plan 与结果配对，压缩不得仅留下摘要并声称等价；来源调整后须重新验收该路径。

解析与候选按当前响应、调用、执行和段隔离；新响应、终态、取消和清理释放旧缓冲。同名工具或重复 toolCallId 不得跨响应取旧计划。沿用原内存凭据和等待对象边界，不增加进程崩溃自动接管。

## 4. 公共事件与页面恢复

精确字段和 POST/GET 示例唯一维护在[共享事件源](../01-CampusClaw多Agent运行时/事件契约/common.json)与操作 JSON，本页只解释生命周期。

| 阶段 | 字段与行为 |
|---|---|
| agent.plan delta | eventId/type/sourceEventId/phase/content；content 是非空新增已解码文本；不带 createdAt、toolCallId、usage、sourceMessageEventId；不入历史 |
| agent.plan completed | eventId/type/sourceEventId/phase/content/createdAt/toolCallId；content 为完整 plan；与历史同名同形，之后不发同 ID delta |
| agent.tool_call | 既有完整调用事件形状不变；ExitPlanMode.arguments 从 {} 改为 {plan}；其他工具参数仍按各自契约，不增加通用 delta phase |
| user.plan_confirmation | 保持 targetEventId/result/条件 feedback；只能引用当前待审核完整计划，预分配 ID 不可批准 |
| 旧记录 | 旧无 phase 的完整计划仍可读；旧空参数调用与已保存计划按原事件关系展示，不用新工具 Schema 重验历史，也不重新推断旧正文 |

因此前端计划事件与审核接口不必增加字段、URL 或版本；公开完整 tool_call 的参数内容会改变，严格工具专属校验、调试展示、示例和契约门禁需要同步。当前前端 generic arguments 接受对象，具备兼容基础，但不能据此免除回归：completed 到达前、最终参数失败或绑定失败时，不应把整段原始 JSON 重复当作用户答案。完整计划继续按 root + toolCallId 吸收关联调用/结果，缺少完整计划时显示简短失败状态，诊断视图按既有规则查看原始数据。

没有 delta 时 completed 直接建卡。只有 preview 时不可审：可信 done/failed/terminated/confirming 后停止生成提示并标为“未提交审核”；单纯 EOF/断网显示“待核对”，补读历史和 Session。缺页、旧根、冲突或未知状态禁审，不重放 POST；别的计划 completed 不升级当前预览。模式控件须在批准与恢复时读取服务端权威状态，不能一直显示旧 plan。

preview 是 best-effort；连接丢弃某计划增量后停止该 ID 的后续 delta，等待 completed 覆盖。增量不按文本去重；completed 按 eventId 幂等合并，迟到 delta 忽略。补读历史与本地预览合并后仍须执行终态收尾，不把旧预览移到终态之后恢复“生成中”。中止草稿可只在当前页只读保留，刷新不承诺恢复。受限 Markdown、复制、滚动、键盘焦点和不逐 token 播报规则保持。

Mate 公共桥接仍待实现；公共两跳保持各自 ID 映射、认证和历史契约，不暴露内部 sessionId。preview 与 completed 映射为同一公共计划 ID，不能每片重建 ID；本次不扩大为通用工具参数公开流或重做所有 Mate 接口。

### 4.1 其他工具是否同步流式输出

| 层次 | 本次范围 |
|---|---|
| 模型/Provider 参数生成 | 支持该能力的 Provider 可对多种工具产生内部参数 delta；当前 Mate 已有此事件，实际网关是否及时输出需实测 |
| Runtime 业务投影 | 仅可信 ExitPlanMode.plan 解码为 agent.plan；工具名相同字符串或其他工具 plan 字段不触发 |
| 浏览器公共参数预览 | 不新增通用 agent.tool_call delta，不默认展示其他工具的半成品参数、内部 Schema 或敏感字段 |
| 工具执行 | 完整调用经可信绑定、完整参数校验、权限/必要用户确认后才执行业务并回传结果；增量到达不提前执行或确认 |

其他工具若以后需要实时展示，应单独定义适合业务的安全展示字段、身份、失败/取消与历史恢复语义；内部 delta 存在不等于公共协议已开放。

## 5. 取舍、兼容与性能验证

选择完整参数加专用流式投影属于架构变更：用一次有明确字段的调用表达生成与提交，去掉额外正文标记条件，同时复用计划卡和审核事务。代价是 JSON 字符串增量解码、流身份与最终校验的协调，以及长参数转义开销；不能把某基线模型的效果推广为所有 Provider 的可靠性保证。

固定来源、完整校验、单交互与审核事务属于一致性和安全约束。预览只有展示价值，不是审核承诺或授权依据。Schema 约束也不能替代服务端校验；错误保持真实 isError 并给模型修正依据，不由后端猜参或重试业务。

不新增 Maven/npm 直接依赖、数据表或独立资源。复用 JDK 的有界字符状态机、现有 Jackson 最终解析与既有 Spring/MyBatis/Vue。实现前须验证现有 Jackson 配置是否拒绝重复键、尾随输入；不能假定异步 Jackson 会逐字符产出未闭合字符串，若选它承担增量读取须先验证。没有新增直接依赖，因而没有本次新增传递依赖；后续引库仍须另行披露依赖图与取舍。

发布前停止新 Plan 接受并排空/中断旧活动执行，再同步工具 Schema、description、内置及业务 PLAN/BUILD、Provider 身份、解析和审核绑定。业务模式文件是完整覆盖，不能只改内置资源便认为生效。公共 phase 不迁移，读取端保留旧无 phase 完整计划和旧空参数历史；活动执行不得混用新旧工具 Schema/提示词。回滚同样排空活动 Plan，并验证已有新记录可读，不能重新解释历史。

计时点包括请求开始、首个工具参数 delta、首个计划正文 delta、模型完成、Assistant 保存、审核提交、浏览器首字和审核可用。使用相同模型版本、任务与上下文比较提交成功率及首字/可审耗时，并记录缺调用、参数错误、绑定失败等原因；工具定义及 Prompt 生效另验。若 Provider 只一次性返回完整参数，仍可正确审核但没有首字改善；检查网关缓冲、flush 和前端批处理，不承诺未经实测的收益。日志不记录正文、敏感参数、推理或凭据。

## 6. 实施切片与验收

| 切片 | 范围 | 必须验证 |
|---|---|---|
| PS1 | ExitPlanMode Schema/prepare、内置和业务 PLAN/BUILD、description | required plan、类型/字段/标题/UTF-16/编码容量校验；只生成一份参数、无额外模型往返；错误含字段与可信定义且 isError=true；未调用时不伪造审核；Build/Subagent 不误提交 |
| PS2 | 中立 Provider 流身份、有界预览解析与 Projector | 每个字符处分片、转义/引号/CRLF/Unicode/代理项、多个调用交错、名称/ID 延迟与变化、重复键/尾随输入；只认可信内置 ExitPlanMode；无空 delta、无普通工具参数泄露、无平方级扫描；上游一次性参数仍能完成 |
| PS3 | 不可变准备快照、Binder 与审核事务 | 最终校验在交互之前；同次快照共享、原 Entry 和唯一调用精确关联；completed 在事务之后，未发预览也可提交；混合工具/取消/截断不误审；approve/revise/interrupt 竞争；首次批准模型请求保留完整 plan 与结果 |
| PS4 | 现有公共契约和客户端回归 | delta/completed 字段不变；新完整参数、旧历史均可读；final 覆盖部分增量，completed-only、失败/取消/断网/分页/迟到/修订与模式切换；终态后 preview 不再生成；调用日志不重复展示正文；390 px、滚动及键盘焦点 |
| PS5 | 实际 Provider、Mate、发布与回滚 | 本次参数 Schema 与业务覆盖确实生效；记录模型样本成功率与首字/审核耗时；两跳身份与安全投影；其他工具不产生公共参数 delta且执行准入顺序不变；排空与新旧历史回滚可读 |

设计契约样例、校验器和生成图只证明文档一致性，不证明待实现的 Java 参数解析、浏览器集成或真实模型可靠性。实现与模型验收分别记录，不把已有标记解析测试当作参数流验收。

## 7. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.2.0 | 2026-09-28 | 以 ExitPlanMode 完整 plan 参数提交审核，专用参数增量复用计划事件并保持其他工具公共协议。 |
| 1.1.0 | 2026-09-19 | 后端解析计划标记，使用同一计划身份的 delta/completed 流式展示并在审核提交后完成。 |
| 1.0.0 | 2026-09-19 | 定义同响应正文生成、空参数退出调用与审核绑定。 |
