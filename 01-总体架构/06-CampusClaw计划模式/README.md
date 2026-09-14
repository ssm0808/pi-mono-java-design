# CampusClaw 计划模式设计

| 属性 | 值 |
|---|---|
| 文档版本 | 1.3.0 |
| 更新日期 | 2026-09-14 |
| 状态 | 推荐目标设计，target-only；本次不修改产品实现 |
| 计划模式主基线 | DeepSeek Harness `0a53fb55bea101816fa226bb964ae2bed71c343b`，`dsh-0.1.2-alpha.2` |
| Runtime 语义基线 | pi `5cd93f688aaab89dbb6dfa4aca535f21796ae185` |
| CampusClaw 实现基线 | `09b32d8ea4a4b43b34be302d8b2745bdc417c9a2`；本次分析范围与本地 `f61906b9136246ca60f333704b6fc92b5420d0ec` 内容相同 |
| 设计仓变更前基线 | `337346b1f59267392a631e22e92bb9829b335f26` |
| 源码依据 | [基线、符号与差距](source-evidence.md) |

## 1. 设计结论

名称、模型、思考和模式统一通过 `POST /sessions/{sessionId}` 更新；单字段与组合提交共享一笔事务。Session 的工作模式使用 `mode=plan|build` 表达，切换归属 Session 资源更新。`state=idle|running` 继续表示执行忙闲，两者共同描述 Session，不能合并为一个枚举。采用 DeepSeek 的“稳定工具清单、计划提示词、完整方案审核、批准后续跑”机制，接入 CampusClaw 已有的 `AgentSessionFactory`、`ManagedAgentSession`、Session Events 和数据库执行控制。

用户在同一个 Session 中进入计划模式，Agent 查询资料、澄清需求并形成完整方案；用户批准指定方案后，原执行继续实施。多轮澄清可以跨越多次 `user.message`，无需更换 Agent 或 Session。

### 1.1 明确采用的边界

- **工具元数据稳定。** `ToolInfo`、`MateToolMeta`、Agent/Skill 绑定结构、`ListMateTools` 输出、`CallMateTool` 输入均不增加计划字段；不添加 `readOnly`、`sideEffect`、`allowedInPlan`，不改变 `permission` 和 `isConcurrencySafe` 的含义。
- **通过提示词限制规划行为。** 工具描述和参数帮助模型理解操作；不增加按计划模式拦截业务工具的白名单或副作用分类器。原有工具权限、工作区边界、绑定检查与凭据规则继续生效。该方案不提供服务端强制只读保证。
- **审核状态由服务端维护。** 普通对话中的“可以”“继续”不自动批准方案。确认请求必须引用当前待审核 `agent.plan.eventId`；旧方案不可被误批准，不建立独立 `planId/version` 管理体系。
- **复用现有执行。** 继续使用 POST Events 对应 SSE、GET 历史、固定根消息和内部续跑段；等待审核期间 Session 仍为 `running`，不接受第二条普通消息。
- **保持工具定义跨模式一致。** Runtime profile 增加一个内置工具 `ExitPlanMode`，在普通模式和计划模式中都保持注册。新增工具名称不等于新增元数据字段；普通模式调用它返回模式不匹配错误。

统一更新及 mode 已纳入[当前九项契约](../01-CampusClaw多Agent运行时/接口契约/catalog.json)，语义由[HTTP 主设计](../01-CampusClaw多Agent运行时/chat-http-v1-design.md#24-模型目录与统一-session-更新)唯一维护。计划审核输入和批准事件仍为[接口增量](interface-delta.md)，尚未进入当前 JSON 源；不能据此声称客户端或服务端已支持完整计划审核。

### 1.2 与 DeepSeek 的对应及差异

| DeepSeek 观察行为 | CampusClaw 目标 | 分类与理由 |
|---|---|---|
| 计划状态控制系统提示词，工具清单不变 | `mode` 控制每个执行实例的系统提示词；模式切换不重装工具 | 直接借鉴；隔离工作方式与工具契约 |
| `exit_plan_mode` 展示完整 Markdown 并请求批准 | `ExitPlanMode` + `agent.plan` + `user.plan_confirmation` | 架构变更；接入已有 HTTP、SSE 和事件身份 |
| 计划状态以 `plan/mode` 日志恢复 | Session 行保存当前模式，领域 Entry 保存变更；同事务维护 | 架构变更；复用既有 GaussDB 配置和历史模型 |
| 运行中切换在后续 step 生效 | 用户主动切换只允许 idle；审核批准是唯一运行中退出路径 | 产品约束；与当前配置准入一致，不引入通用运行中模式队列 |
| 通过独立提问能力澄清需求 | 首版使用普通 Assistant 问题和下一条 `user.message` | 架构选择；完成交互闭环，无需新增通用问卷协议 |
| 新 spawn 默认不继承计划模式 | Child 在调用时复制父执行当前模式，并只向父返回结果 | 产品约束；避免把规划任务委派成默认实施任务；仍是提示词约束 |
| 插件依赖进程内待切换状态 | 已受理审核决定先持久化，再唤醒原执行实例 | 架构变更；复用 CampusClaw 跨实例确认交接 |

只借鉴 DeepSeek 的计划机制，不引入其 Cordis 插件系统、WebSocket Remote Journal、token 级日志或完整事件溯源存储格式。该参考版本为 alpha，成熟度不作为方案正确性的依据。

## 2. 用户流程与状态

### 2.1 操作流程

1. 用户在空闲 Session 通过更新 `mode=plan` 进入计划模式，成功响应返回最新 Session 资源及 ETag。
2. 用户提交普通消息。工厂恢复当前模式并加入计划提示词；Agent 使用已有工具调研。
3. 需要澄清时，Agent 用普通回答提出问题并结束本次执行。Session 回到 idle，但 `mode=plan` 保持；用户回答后开始下一次规划执行。
4. 方案完整时，Agent 单独调用 `ExitPlanMode({plan})`。服务端保存完整计划，进入审核等待并关闭当前 SSE。
5. “修改方案”提交 `result=revise` 和可选反馈；原执行继续规划，重新提交时产生新的计划 eventId。
6. “批准并执行”提交 `result=approve`；服务端原子接受决定、关闭计划模式并创建续跑段。原执行收到决定后更新提示词，返回工具结果，下一次模型请求开始实施。
7. 业务工具仍按既有 `allow/ask/deny` 执行；方案批准不能代替具体工具的权限确认。

关闭计划卡片不发送批准请求。审核等待中要退出任务，使用现有 `user.interrupt`，目标仍是原始 `user.message.eventId`；收到真实终态后再修改模式或发送新消息。

### 2.2 状态组合

| Session state | mode | 待审核计划 | 含义与允许操作 |
|---|---:|---|---|
| idle | build | 无 | 普通模式；可进入计划、发送消息 |
| idle | plan | 无 | 计划模式等待下一条用户输入；可退出计划、回答澄清问题 |
| running | plan | 无 | 正在调研或生成方案；允许中断，不接受 M2 或执行配置更新；仅名称更新允许 |
| running | plan | 有 | 等待计划审核；接受针对该 eventId 的批准/修订，或中断 |
| running | build | 无 | 普通执行或批准后的实施；权限确认仍独立适用 |

`session.status_idle(reason=confirming)` 继续表达“当前 HTTP 交互结束、执行等待用户确认”，不增加粗粒度 Session 状态。前端根据完整计划、审核决定与结束事件恢复审核卡片，规则见 [§6.2](#62-恢复与结果不确定)；Session 响应不暴露待审核目标。工具权限确认继续使用 `agent.tool_call.requiresConfirmation`。

![计划模式状态与准入](plan_mode_state.svg)

[原尺寸 SVG](plan_mode_state.svg) · [PlantUML 源码：`plan_mode_state`](diagram.puml#L249)

## 3. 推荐全局目标类图

图中绿色为既有结构，蓝色为 target-only 新增结构；`extended` 表示既有类需要扩展。所有标为 target-only 的连线均为推荐关系，不能视作当前已实现关系。

![CampusClaw 计划模式全局目标类图](plan_mode_target_classes.svg)

[原尺寸 SVG](plan_mode_target_classes.svg) · [PlantUML 源码：`plan_mode_target_classes`](diagram.puml#L1)

这张主图贯通入口、应用服务、执行对象、公共工具接口和数据库。HTTP Controller 只接收请求 VO、输出响应 VO；工具依赖窄的 `PlanReviewPort`，不读取 Servlet、SSE 或 Mapper。模式与审核业务分别由应用服务负责，底层共用已有事务和执行控制端口。

### 3.1 组件职责与生命周期

| 组件 | 生命周期 / 目标调整 |
|---|---|
| `RuntimeSessionController`、`RuntimeEventController` | Spring 单例；分别增加 Session 更新和计划确认输入，保持 ResultBean / SSE 分工 |
| `RuntimeMessageEventService`、`RuntimeExecutionCoordinator`、`RuntimeSessionControlDispatcher` | 既有 Spring 单例；分别在接受后应用模式快照、收尾时取消待交互、按固定执行目标领取计划决定；通过原有 registry/holder 定位执行 |
| `RuntimeSessionConfigurationService`（扩展） | 既有 Spring 单例；增加 `updateSession`，处理四类属性、ETag、按提交字段准入、最终配置与模式能力检查，复用响应组装；不持有活动 Agent |
| `RuntimePlanReviewService`（新增） | Spring 单例；校验方案审核业务、构造事件，调用既有事务边界；不长期持有用户请求 |
| `RuntimeExecutionPersistenceService`、两个 Repository | 既有 Spring 单例；增加计划等待和确认事务；数据库仍是跨实例权威 |
| `RuntimePlanReviewAdapter`（新增） | 每个根执行一个；实现 `PlanReviewPort`，连接工具与既有等待/续跑机制 |
| `RuntimeActiveExecution`、`RuntimePendingInteraction`（后者新增） | 每个执行一个；把现有单个工具确认 Future、输出交接和取消责任收敛到一个最多容纳一项交互的对象，支持 `TOOL_PERMISSION` 与 `PLAN_REVIEW` 两种明确类型 |
| `ManagedAgentSession`、`SessionPlanContext`（后者新增） | 每个执行一个；保存基础提示词、当前执行模式快照、提示词应用方法；不包含 HTTP 请求或数据库句柄 |
| `PlanPolicyPromptComposer`（新增） | Spring 单例、不可变配置；根据基础提示词、模式和 root/child 角色组装文本，无 I/O、无租户状态 |
| `ExitPlanModeTool`（新增） | 每个 Runtime Session 实例新建；只校验工具参数并调用 `PlanReviewPort`，默认串行执行 |
| `RuntimeEventProjector`、`RuntimeEventOutput` | 沿用每执行投影与每请求输出边界；完整事件先提交再推送，跨实例确认响应通过既有结果轮询获得完整事件 |

不引入通用 Mode Registry、工作流引擎、第二套 Agent Loop、动态工具注册或可插拔 Plan Backend。`RuntimePendingInteraction` 只共享已存在的等待、取消与输出交接责任，计划批准和工具授权的业务判断仍分别维护。

### 3.2 内部接口与接入位置

以下签名为新增或扩展的目标接口，不是当前源码 API；类型名中 VO 只出现在 Web/Application 边界，Mapper 参数和返回使用 DTO。

| 位置 | 目标接口 / 方法 | 接入理由 |
|---|---|---|
| 配置应用服务 | `updateSession(sessionId, ifMatch, UpdateSessionRequestVO)` → `RuntimeSessionView<GetSessionResponseVO>` | 由 Session 更新入口调用既有配置服务；复用配置事务、完整 Session 响应和 ETag |
| 审核输入 | `acceptPlanConfirmation(sessionId, UserPlanConfirmationEventRequestVO, locale)` → `AcceptedControlStreamDTO` | 复用接受前预留、完整回执、固定续跑段 |
| 工具端口 | `PlanReviewPort.review(toolCallId, plan, CancellationToken)` → `PlanReviewDecisionDTO` | 不向公共工具层引入 HTTP / Mapper |
| 审核业务 | `beginReview(ExecutionTargetDTO, toolCallId, plan)` → 已提交待审核记录 DTO | 由原执行发起，校验模式、原调用和当前段 |
| 持久化边界 | `markPlanReviewing(...)`、`acceptPlanConfirmation(...)`、`claimPlanConfirmation(...)`、`acknowledgePlanConfirmation(...)` | 对照现有工具确认的四阶段，独立校验计划 eventId |
| Session 提示词 | `SessionPlanContext.applyCommittedMode(SessionModeSnapshotDTO)` | 用完整基础文本重新组装提示词，不用字符串删除或重复追加 |
| 消息接受结果 | `UserMessageAcceptanceDTO` 增加 `SessionModeSnapshotDTO`，`startAccepted` 在启动前应用 | 保留接受前 prepare，避免配置竞争与数据库锁内远程装配 |
| 工厂参数 | `ManagedAgentSessionRequest` / `ToolAssemblyContext` 增加计划上下文与退出工具工厂 | 这是内部装配参数，不修改 Agent/Tool/Skill 元数据 |

`RuntimeEventService` 当前是三分支 sealed switch；首版增加一个明确的计划确认分支，转交专用服务，不在分支内实现审核逻辑。无需为了增加一个事件整体替换现有分派框架。

公共 `AgentTool` 接口保持不变。`ExitPlanMode` 使用现有 `SEQUENTIAL`；在 `BeforeToolCallContext.assistantMessage` 中校验该响应只包含一个 ToolCall，防止一张审核卡与同批其他调用共用等待点。该检查只约束审核协议，不用于识别或阻断其他业务工具的副作用。

## 4. 提示词与工具装配

### 4.1 提示词应用

默认文本见 [CampusClaw 计划指令](plan-policy.md)。作为 classpath 资源随 Runtime 部署；如需要环境覆盖，只允许部署配置提供完整文本，启动时校验非空并固定本进程文本，不从 Agent 元数据、工具返回值或 Skill 文档修改它。

执行装配顺序：

1. 保留 `RuntimeMessageEventService` 的 prepare → accept → start 顺序：接受前预留容量、加载基础 SYSTEM 并创建尚未启动的 `ManagedAgentSession`。此时可预读模式用于准备，但该值不作为最终执行依据；工厂加载和远程 I/O 不进入数据库锁。
2. 接受事务锁定 Session 后读取最新 `t_sessions.mode`，对已准备的固定工具 profile 检查计划能力，将 `SessionModeSnapshotDTO` 与固定执行目标一起作为接受结果返回。Session 更新与消息接受在同一 Session 锁上串行化。
3. 提交后、`RuntimeExecutionCoordinator.start` 前，将接受结果应用到 `SessionPlanContext`，用已加载的基础 SYSTEM 组合提示词并调用 `Agent.setSystemPrompt`，再绑定审核 Adapter、入队回执并启动模型。禁止直接沿用 prepare 阶段可能过期的模式；接受后初始化失败走现有 accepted-start-failure 可靠收尾。
4. 原执行领取批准决定后，在返回 `ExitPlanMode` 的工具结果前应用已提交的 `mode=build`。`AgentLoop.invokeModel` 下一次读取 `AgentContext.systemPrompt()`，自然使用更新后的文本。
5. 修订决定保持 `mode=plan`。模式配置事件不转换为模型角色消息；工具结果向模型说明批准或修订结果。

不需要在循环中增加“如果是计划模式就跳过某工具”的分支，也不需要调用 `Agent.setTools`。只更改当前执行自己的 Prompt；Spring 单例不保存某个 Session 的模式，活动 Session 的基础 SYSTEM 不因目录刷新而改变。

压缩和恢复保持既有语义：普通澄清消息和 `ExitPlanMode` 调用/结果进入模型历史；`agent.plan` 的独立展示投影、模式配置和用户确认回执不再次注入为重复模型消息。压缩摘要不成为模式或批准事实的权威，恢复模式从 Session 行读取。模型在批准后的首个 step 仍能读取原调用中的完整计划，不能仅依赖前端卡片或摘要。

### 4.2 工具 profile

| 入口 | 目标行为 |
|---|---|
| Runtime | 原八项默认工具后追加 `ExitPlanMode`；两种模式使用同一个已解析 profile，名称、description、parameters、顺序均不随模式变化 |
| Child | 不增加审核工具；在每次 `Agent` 调用开始时复制父执行当前模式，构造新的 Child `SessionPlanContext`；Child 提问或方案返回父 Agent |
| Cron | 保持当前工具 profile，默认普通模式；不新增 Job 字段或无人审批队列 |

显式配置 profile 的完全替换语义保持不变。Runtime profile 未包含 `ExitPlanMode` 时，进入计划模式返回 `PLAN_MODE_UNAVAILABLE`，不偷偷补入工具；已处于计划模式的 Session 在下一次执行前也必须检查该能力。离开计划模式不依赖此工具可用性。

Child 继承发生在调用时。不能把根执行创建时的 `plan` 永久捕获在 `BoundAgentTool` 中，否则批准后新建 Child 仍会错误保持规划。传递不可变 `SessionModeSnapshotDTO`，不共享父 `AgentState`、审核 Future 或可变上下文。父取消与最大深度继续按既有实现处理。

### 4.3 ExitPlanMode 模型契约

| 项目 | 目标 |
|---|---|
| 名称 | `ExitPlanMode`，遵循现有 PascalCase |
| 参数 | 只接受必填字符串 `plan`，禁止额外字段；首个非空行必须以 `# ` 开始 |
| 大小 | `plan` 最多 262144 个 UTF-16 单元，完整保存；超限返回既有 `TOOL_ARGUMENTS_INVALID`，不截断后让用户批准 |
| 使用条件 | Runtime 根执行、当前计划模式、调用完整且为该 Assistant 唯一 ToolCall、无其他待确认交互 |
| 批准结果 | `AgentToolResult` 文本块包含 JSON `{"approved":true}` 及明确续跑指令；公共结果仍沿用 text 块数组 |
| 修订结果 | 正常结果文本包含 `{"approved":false,"feedback":"..."}`，说明继续规划；不把用户修订作为工具执行故障 |
| 失败 | 参数、模式或审核通道异常用明确工具失败返回；失败不退出计划模式；不伪造批准 |

相对 DeepSeek，修订采用正常的 `approved=false` 结果，是产品展示上的差异，避免将正常的审核反馈显示为工具故障。新增模式/审核失败码集中在接口增量中定义，不通过解析异常文本推断。

正文长度是逻辑上限，完整事件还必须满足部署的 SSE 编码字节上限。提交审核前按现有编码器验证 `agent.plan` 帧大小；超出时按既有 `EVENT_PAYLOAD_TOO_LARGE` 路径可靠结束，不建立待审指针或截断正文。原 ToolCall 若先触发现有大小限制，同样不能继续产生可批准计划。

## 5. HTTP 与事件接口增量

统一 Session 更新及 requested 模式事件由[当前契约](../01-CampusClaw多Agent运行时/chat-api-review.html#updateSession)维护；尚未登记的计划审核报文由[接口增量设计](interface-delta.md)维护。本节只说明接入关系。

Session 是配置权威资源。当前九项目标契约以统一 POST 更新名称、模型、思考和模式，入口为 `RuntimeSessionController`，应用编排复用 `RuntimeSessionConfigurationService`。该接口和模式执行仍是 target-only；源码尚未提供统一更新与计划能力。

| 接口 | 目标增量 |
|---|---|
| `POST /campusclaw-service/v1/sessions/{sessionId}` | 已登记四字段部分更新；含 mode/modelId/thinking 时要求 idle，仅名称可在 running 更新；统一要求 `If-Match`、原子提交与同源 Session/ETag |
| `GET /campusclaw-service/v1/sessions/{sessionId}` | `mode` 已进入共享响应源；Session 响应不增加待审核目标，审核卡片由 Events 恢复 |
| `POST /campusclaw-service/v1/sessions/{sessionId}/events` | 在原三类输入上增加 `user.plan_confirmation`；复用接受回执和对应续跑 SSE |
| `GET /campusclaw-service/v1/sessions/{sessionId}/events` | requested 的 `session.mode_changed` 已登记；完整 `agent.plan`、`user.plan_confirmation` 与 planApproved 模式事件仍为审核增量 |

不增加 `/plans` CRUD、单独批准 endpoint、独立 Session 订阅流、公共 Run/Execution ID 或幂等键。本期使用模式按钮调用 Session 更新接口，不同时扩展 `/plan` Slash Command；普通消息接口仍不解析 Slash 文本。

### 5.1 审核事务与事件顺序

![计划提交、审核与原执行续跑](plan_mode_review_sequence.svg)

[原尺寸 SVG](plan_mode_review_sequence.svg) · [PlantUML 源码：`plan_mode_review_sequence`](diagram.puml#L168)

提交计划时：先由原有 Projector 记录唯一的 `agent.tool_call`，`requiresConfirmation=false`，因为该调用不在申请工具权限。随后在同一个短事务内校验固定目标和模式，追加 `agent.plan` 与 `session.status_idle(confirming)`、关闭原段、登记待审核目标。提交成功后按该顺序推送并关闭 SSE。计划工具尚未返回，不提前制造 `agent.tool_result`。

接受审核时，锁顺序保持 `t_sessions` → 当前 `t_session_executions` → 段/决定行：

1. 复核同 Session、根消息、当前执行、未停止、当前等待类型及 `targetEventId` 精确相等，并确认对应计划事件已提交且属于当前分支。
2. 追加完整 `user.plan_confirmation`，创建新续跑段并登记决定；清除待审核指针，执行控制状态恢复 `RUNNING`，Session 粗粒度状态仍为 `running`。
3. 对 approve，在同事务把 `mode` 改为 build、追加 `session.mode_changed` 并更新资源版本。对 revise，不变更模式，只保存反馈。
4. 提交后接收实例先入队本次完整回执，再投递新段的模式变更及后续输出。本地通知只是优化，执行实例通过数据库控制检查也能领取决定。
5. 领取决定时再次校验固定执行/旧段/计划 eventId/停止状态。绑定新段输出后，完成该执行唯一的等待 Future。原执行应用提示词、返回工具结果、继续模型循环。

模式变更、确认回执与续跑目标有任何一项保存失败，整个接受事务回滚。前端“同意”按钮、预读 Session 或历史卡片的可点击状态都不能替代锁内最终校验。

### 5.2 并发与取消

- approve、revise、重复确认之间只允许一个事务成功；其余返回 `PLAN_CONFIRMATION_NOT_PENDING`。不因重复请求生成新的执行段。
- 中断先提交时拒绝确认；确认先提交后中断仍定位同一个根执行，新段按正常停止流程处理。若原执行尚未领取批准就已停止，不继续实施，也不撤销已经保存的用户批准事实。
- 计划必须作为该 Assistant 的唯一 ToolCall 提交；校验失败时不建立审核等待，返回工具错误供模型修正。该规则不承诺撤销同批已经执行的其他调用。
- 等待计划审核与等待工具授权共用“最多一个待交互”不变量。`user.tool_confirmation` 不能消费计划等待，`user.plan_confirmation` 不能消费工具权限等待。
- 终态、取消、超时和清理路径必须清除待审核指针并取消等待 Future；先提交可靠终态，再释放资源准入。HTTP 关闭不会触发这些操作。

## 6. 持久化与恢复

### 6.1 最小存储增量

以下为目标结构；沿用现有 MyBatis、GaussDB、Entry 树、公共事件表和执行段机制。

| 位置 | 增量 / 权威边界 |
|---|---|
| `t_sessions` | 增加 `mode VARCHAR(16) NOT NULL DEFAULT 'build'`，CHECK 限定为 plan/build；当前模式权威，修改时与 Entry、resource_version 同事务 |
| `t_session_executions` | 增加可空 `pending_plan_event_id VARCHAR(128)`；存在时与 `pending_tool_call_id` 一起定位 ExitPlanMode，状态必须为 `CONFIRMING`；工具权限等待时该字段为空 |
| `t_session_plan_confirmations`（新增） | 保存已接受的审核决定及跨实例消费状态；只引用计划 eventId，不复制完整方案，不提供业务计划版本 |
| `t_session_entries`、`t_session_events` | 增加三种领域/公共事件的编解码和投影；计划正文的展示权威是已提交 `agent.plan`，模型历史仍来自原 Assistant ToolCall |
| `t_session_execution_segments` 及关联表 | 复用；允许 `user.plan_confirmation` 触发新段；approve 的模式变更也关联该段以供确认响应读取 |

新决定表字段：`session_id`、`execution_id`、`confirmation_event_id`、`target_event_id`、`previous_segment_id`、`segment_id`、`tool_call_id`、`result`、可空 `feedback`、`state`、`created_at`、可空 `claimed_at/completed_at`。ID 列沿用现有 128 长度；tool_call_id 和反馈用 TEXT；result 只允许 `approve/revise`；state 沿用 `PENDING/CLAIMED/COMPLETED`。

主键为 `(session_id, confirmation_event_id)`；唯一约束为 `(session_id, target_event_id)` 和 `(session_id, execution_id, segment_id)`。仅 revise 可带反馈，时间戳与消费状态约束对齐现有工具决定表。所有追加与查询都带 Session 条件，不单凭 eventId 查询跨 Session 内容。新表必须纳入 Session 删除/保留清理，清理顺序先决定及引用、后执行和事件；SQL COMMENT 使用中文。

`pending_plan_event_id` 仅属于当前执行的内部控制状态，不投影到 Session 响应，也不在 `t_sessions` 再保存一份指针。它与计划事件、确认决定和执行段在同一事务内维护；不为该内部指针单独增加 Session 的 `resource_version/updated_at` 变更。mode、state 等公共资源变化继续按既有规则维护版本及同源 ETag。

这一边界沿用当前工具确认：客户端从事件计算展示状态，服务端从锁内执行记录判断是否仍可接受决定。减少 Session 响应与具体交互类型的耦合，代价是刷新审核卡需要补齐相关事件，GET Session 本身不能定位待审核方案。该差异属于架构变更；普通历史分页和页面可点击状态均不作为提交准入的权威。

### 6.2 恢复与结果不确定

审核卡片复用既有工具确认的事件恢复方式，以下计划分支为 target-only：

1. 从完整事件历史确定最近一条 `user.message` 的根消息 eventId；只处理属于该根消息的计划、工具结果和结束事件。`user.plan_confirmation` 通过 `targetEventId` 关联计划，不按最后一段 Markdown 或时间戳猜测目标。
2. 完整 `agent.plan` 负责正文展示；其后的对应 `session.status_idle(reason=confirming)` 表示本段进入等待。确认回执、对应 ExitPlanMode 的工具结果、中断请求或真实终态出现后，旧计划不再提供审核按钮。修订后的新计划使用新 eventId；历史方案仍可展示。
3. 刷新时沿用 `loadHistory` 分页补读，再读取 Session 的 mode/state 并按 eventId 对账。历史尚未补齐、缺少关联记录、正在停止或 Session 状态与事件矛盾时禁用审核，显示恢复中或待核对。不能仅凭某页未出现确认记录断言仍可批准；分页读完也不是跨请求固定快照。
4. 事件投影只决定客户端展示，确认请求始终由服务端在锁内复核当前等待类型、计划 eventId、分支及停止状态。其他客户端已先处理时返回接口增量定义的冲突错误，刷新历史和 Session，不自动重放确认。

| 场景 | 目标行为 |
|---|---|
| 浏览器刷新 / SSE 断开 | 分页 GET Events 恢复计划、决定及结束记录，GET Session 核对 mode/state；按上述事件规则恢复审核卡，不自动重发消息或确认 |
| 计划帧丢失，但原执行仍在等待 | 补齐当前根消息的完整计划和确认等待记录后恢复卡片；读到确认、结果或终态即移除旧审核操作，缺失记录时保持待核对 |
| 确认由另一实例接收 | 决定入库；原持有执行和凭据的实例领取，接收实例按固定新段读取已提交结果；本地 preview 不承诺跨实例重放 |
| 批准回执丢失 | 查询目标计划后是否已有确认记录，并读取 Session/后续事件；已接受的确认不重发，EOF 不代表执行成功 |
| 执行达到既有 maxDuration | 审核等待计入现有执行时限，不无限占用活动容量；取消等待，按既有可靠收尾提交真实终态，不能把超时当成批准 |
| 执行进程丢失 | 可以恢复已提交历史和模式，不能恢复原内存凭据、Future 或自动实施；不得仅因某实例无本地 Holder 就宣称任务已结束 |

当前基线没有可证明的跨实例失联执行自动接管能力。本设计不增加租约调度器，也不承诺进程丢失后自动续跑。未能确认原执行已退出时，保留不确定/running 并走现有故障处置；确认退出后的修复必须使用固定执行身份提交失败终态并释放准入，禁止直接把 Session 改 idle 或重放 Mate 调用。**断线恢复可实施，进程崩溃自动接管不在本功能承诺中。**

关闭整个集群的功能配置或回滚前，需要停止接收新的计划任务，等待或中断现有待审核执行；旧版本无法解释新事件类型，不允许直接在已有计划数据上降级旧读写路径。

## 7. 前端与 Mate 边界

CampusClaw 自带 Runtime 调试前端可以直接消费本专题的内部 Session 契约。页面显示独立的模式开关和审核卡片；`running` 时禁用手动切换，审核按钮绑定 eventId 而非“最后一段 Markdown”；卡片恢复按 [§6.2](#62-恢复与结果不确定)处理，Session 类型不新增待审核字段。提交按钮点击后进入提交中，不能重复创建确认请求；409 后重新获取 Session 和历史。

只有收到并对账到服务端接受决定，才显示“已批准”或“已退回修改”；生成方案结束、关闭 SSE、普通回答中的肯定文本都不能触发执行。计划 Markdown 按前端现有安全渲染规则显示，不执行其中 HTML/脚本，外链与工具调用不由文档内容自动触发。

面向企业浏览器的 mate-service 仍拥有 `chatId → sessionId` 私有映射、认证、权限和公共事件投影。本专题不替换既有 Mate 公共三接口：产品桥接需要将新增三类事件投影到公共事件，并保持批准目标从公共 eventId 到内部计划 eventId 的可校验映射。字段同名不能推定两跳 ID 共值。公共 Chat 模式配置及确认联合类型需在 Mate 契约中同步，不能把内部 Session 更新路径或 sessionId 直接暴露给浏览器。

Runtime、Mate bridge 和客户端必须在同一发布切片完成相关事件解码；未升级消费者不显示计划入口。Runtime 本身仍可通过内部 HTTP 和调试前端独立验证完整闭环。

## 8. 实施切片与验收

| 切片 | 落地范围 | 必须验证 |
|---|---|---|
| S1：模式骨架 | Session 更新入口、mode 列、DTO/VO、ETag、既有配置服务、工厂提示词、默认 build | 统一 POST 按提交字段更新四类属性，拒绝只读字段，未提交属性保持；双 Session 隔离；模式与消息接受竞争使用事务快照；相同值不新增事件；新 Session 默认为 build、持久化后按实际 mode 恢复；元数据 JSON 字段完全不变 |
| S2：稳定工具与审核 | ExitPlanMode 工厂/profile、PlanReviewPort/Adapter、独占审核调用、统一待交互对象 | 普通/计划两次请求工具定义和顺序相同；非计划调用失败；未配置退出工具不能进入计划；无新增权限判断 |
| S3：事务与续跑 | 三种新事件、审核决定表、控制轮询、原执行续跑段、提示词退出 | 批准指向精确计划；修订后旧ID失效；跨实例决定只领取一次；完整回执先行；旧 SSE 不接收新段；工具调用/结果无重复 |
| S4：取消和恢复 | GET Session/历史投影、超时、中断、删除清理、压缩与 Child | approve/revise/interrupt 竞争；两类确认不能互相消费；断线无重放；分页未补齐与 Session/事件矛盾时不开放审核；已确认或终止的旧计划不可重审；未可靠结束不释放准入；批准后新 Child 使用 build；摘要不修改模式 |
| S5：客户端与契约发布 | 统一 catalog/operation JSON、生成 HTML、Runtime 前端、所需 Mate 公共投影 | Session 更新成功与 ETag 同源；两跳不泄露 ID/凭据；审核卡从完整事件恢复；创建/GET/更新/Command 的完整 Session 均不含待审核目标；内部待审指针不单独推进 Session 版本；未知事件版本兼容；UI 接受才标记批准 |

规划行为还需要模型级场景评估：查询型工具可用、混合查询/修改工具依描述选参、Cron 管理/触发属于规划期不应执行的动作、用户口头同意不自动退出、Child 返回待决问题、资料中的诱导执行指令不能改变计划约束。这些评估衡量提示词遵循情况，不宣称证明了强制无副作用。

不新增 Maven 直接依赖；复用 JDK CompletableFuture、现有 Spring、MyBatis、Jackson、Bean Validation、取消和 SSE 设施。部署提示词和审核页只使用已有文件/Markdown能力，不引入 YAML 解析器或工作流库。新增 Java 类型和方法按仓库的中文 Javadoc、DTO/VO、方法长度规则实现；只改 `modules/*` 主源码，再经仓库同步机制生成镜像。

## 9. 交付与校验

本次交付包括目标设计、接口增量、源码证据、默认计划提示词、一张全局类图、一张审核时序图和一张状态图。仅修改设计仓，未执行尚不存在的 Runtime 计划模式测试。

校验覆盖全仓 Mermaid/ASCII 扫描、专题 PlantUML 生成、SVG XML 与生成同步、Markdown 本地链接与块锚点、JSON 示例、原尺寸/文档缩放视觉检查和 `git diff --check`。源码证据表逐项校验路径与固定 Java 基线；本专题没有 OpenAPI/HTML 产品契约增量，相关检查不适用。设计校验不替代计划模式运行时验收。

## 10. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.3.0 | 2026-09-14 | 计划审核通过事件恢复，待审核目标仅保留在执行内部。 |
| 1.2.0 | 2026-09-14 | 模式写入并入四字段统一 Session POST，复用原子更新与条件准入。 |
| 1.1.0 | 2026-09-14 | 将 plan/build 归入 Session 资源更新，统一 mode 字段及既有配置服务接入。 |
| 1.0.0 | 2026-09-14 | 基于 DeepSeek 在现有 Session、工具和事件控制框架上定义稳定元数据的计划模式与审核续跑。 |
