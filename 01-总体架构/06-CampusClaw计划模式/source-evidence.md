# 计划模式源码证据与实现差距

版本：2.4.0；核对日期：2026-09-19。标记与计划事件专项见[§14](#plan-marker-evidence)，其他主线范围保留[§12](#12-主线实现状态核验2026-09-18)及[§13](#plan-streaming-evidence)的独立核验记录。本文区分源码事实、基线能力和推荐增量；不把历史“待实现”标签当作当前源码结论。

提问接入核对开发分支 `9f785bea3ffff8f6566cd1b2727285af46a2aead`：统一 Session 更新、计划审核、TODO 和 AskUserQuestion 已存在，确定性测试及父审查独立验证见[提问证据 §2](ask-user-question.md#2-基线与已观察实现)。相对旧接入点 `699f929f6826b595ed1d0162f6def66e2f84760b` 的变化路径和实际类职责映射同处维护。下文固定 `09b32d8e` 的旧计划表只证明该提交；其中 待实现 和未运行测试的描述不代表当前开发分支状态，企业接入及真实模型仍未验证。

当前 Build/Plan 与提问展示的静态核验绑定 `1d08f98eb04f8ea6e01bcfbfd4008c1b638391c4`，具体已实现行为、新目标与基线区别由[§9](#9-buildplan-与逐题交互核验)维护。下方历史接入表继续保留各自固定提交范围，不能据其 待实现 标记判断 1d08f98e 尚无模式、审核、TODO 或结构化提问。

业务 Agent 模式文件覆盖与当前 Java 发布差距见 [§11](#11-业务-agent-模式提示词覆盖)。当前模式提示词以 [§10 最新上游核验](#10-两份模式提示词的最新上游核验)为依据；§1～§9 保留各自历史提交和核验范围，不代表最新上游或当前 Java 的完整实现状态。

## 1. 固定提交

| 仓库 | 实际分析基线 | 证据边界 |
|---|---|---|
| deepseek-ai/deepseek-harness | `0a53fb55bea101816fa226bb964ae2bed71c343b` | 固定 `dsh-0.1.2-alpha.2`；读取固定提交的源码与 standard preset，未使用本机较新 checkout 替代 |
| badlogic/pi-mono | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` | Runtime 内核、工具结果与下轮模型调用顺序的固定基线 |
| superheromeZzh/pi-mono-java | `09b32d8ea4a4b43b34be302d8b2745bdc417c9a2` | 2026-09-14 fetch 后 origin/main；本地 f61906b 已包含全部本专题分析的 Java、Mapper 和 SQL 内容 |
| anomalyco/opencode | `849c2598abc7d2b40261e74b5826bc74ffc78308` | 核对计划文件路径、TODO 工具/存储/事件及任务管理模板；该模板不是 Claude 官方提示词 |
| openai/codex | `d58d0e5841e0de08e251673db2d5af8cf3a1ad51` | 核对 Plan 模板、计划正文提取、update_plan Handler 与 App Server 通知；不代表所有模型使用同一模板 |
| pi-mono-java-design | `0a74625e0dd4ea6387b6765c7cb0f9105970d05c` | 本次修订前的设计主线；保留当前 Session Events、权限、工具 profile 和元数据契约 |

前序分析使用 Java `510d882ca45541e0086586dab89c429c5a18cf20`。本次采用 `09b32d8e`；两者之间是仓库指引变更，本专题 Runtime 路径不变。对比本地 `f61906b` 至 `09b32d8e` 的差异仅在指引、前端样式/开发代理及配套文档脚本；不据此声称 Agent Loop 或确认机制发生新增变化。

## 2. DeepSeek 计划模式

以下路径相对 DeepSeek 仓库，链接固定到同一提交。

| 路径 / 符号 | 已观察行为 | 设计用途 |
|---|---|---|
| [`packages/plan/plan-mode/src/index.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/0a53fb55bea101816fa226bb964ae2bed71c343b/packages/plan/plan-mode/src/index.ts) · `PlanModeConfig`、`resolveConfig` | section 为部署提供的非空指导文本；插件没有自行选择一套业务计划提示词 | 计划指令正文归 Runtime 部署，不嵌入 Agent/工具元数据；Agent.mode 仅提供创建默认值 |
| 同文件 · `PlanModeController`、`plan:policy` | 根据 Agent 计划状态提供系统提示词；退出工具持续注册 | 模式影响 Prompt，工具定义跨模式稳定 |
| 同文件 · `exit_plan_mode` execute | 接收完整 Markdown；通过用户审核取得决定；批准后安排退出 | 复用结构化审核边界；CampusClaw 映射为独立事件 |
| [`packages/plan/plan-mode/README.md`](https://github.com/deepseek-ai/deepseek-harness/blob/0a53fb55bea101816fa226bb964ae2bed71c343b/packages/plan/plan-mode/README.md) · Implementation / Limitations | 模式不提供工具权限强制隔离；模式日志可恢复，部分未落盘选择仍在进程内 | 明确提示词约束及持久化边界，不承诺硬只读 |
| [`packages/preset/agent-presets/presets/standard/agent.cordis.yml`](https://github.com/deepseek-ai/deepseek-harness/blob/0a53fb55bea101816fa226bb964ae2bed71c343b/packages/preset/agent-presets/presets/standard/agent.cordis.yml) · planning group / config.section | 真实 preset 指导模型先调研、完成决策、用退出工具提交审核；与 README 极简示例不同 | 提示词内容参考；CampusClaw 使用独立编写的领域指令 |

`planProjectionDefinition.stateVersion=3` 是投影结构版本，不能解释成一份业务计划有第三版。该实现没有可直接照搬的 CampusClaw `planId/version` 公共协议。DeepSeek 在用户选择继续规划时用工具失败传回反馈；CampusClaw 目标将正常修订表示为 approved=false，属于产品展示差异。

## 3. pi Runtime 语义

| 路径 / 符号 | 已观察行为 | 目标保留 |
|---|---|---|
| [`packages/agent/src/agent-loop.ts`](https://github.com/badlogic/pi-mono/blob/5cd93f688aaab89dbb6dfa4aca535f21796ae185/packages/agent/src/agent-loop.ts) · `runLoop`、`streamAssistantResponse` | 每轮由 context 组装模型请求，完整工具结果进入上下文后再开始下一轮 | 计划审核完成为工具结果，下一轮使用更新后的模式提示词 |
| 同文件 · `executeToolCalls`、`prepareToolCall` | 工具定义、Schema 校验与 hook 是明确边界 | 沿用 CampusClaw 对应能力，不添加计划副作用元数据 |
| [`packages/coding-agent/examples/extensions/plan-mode/index.ts`](https://github.com/badlogic/pi-mono/blob/5cd93f688aaab89dbb6dfa4aca535f21796ae185/packages/coding-agent/examples/extensions/plan-mode/index.ts) · `before_agent_start`、`tool_call`、`agent_end` | 示例扩展通过提示和部分工具限制提供计划交互 | 只作对照；本专题选择 DeepSeek，不迁入 pi 示例的 Bash 规则或步骤解析 |

pi 的进程内循环不是 CampusClaw HTTP、数据库事务、权限或跨实例恢复契约。使用它解释 Loop 顺序，不推出新的公共 Run、Session 文件或 token 级持久化。

## 4. CampusClaw 现有接入点

以下完整仓库相对路径按前缀分组；行号来自同内容的本地 f61906b，提交链接使用本专题 Java 基线。

### 4.1 Agent / Session / 工具

| 仓库相对路径 | 相关符号 | 已观察行为与增量 |
|---|---|---|
| `modules/agent-core/src/main/java/com/campusclaw/agent/Agent.java` | `setSystemPrompt`、`startExecution` | 已有 Prompt 设置方法；Agent 使用自身 AgentState 驱动执行；本专题不假定存在 setStreamFunction 方法 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java` | `runTurns`、`runToolPhase`、`invokeModel`（约 113、144、179 行） | 每轮通过 context.systemPrompt() 组装请求，工具批次结果后继续循环；可在审核工具返回前更新该实例的 Prompt |
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/AgentContext.java` | `systemPrompt`、`setSystemPrompt` | 直接代理共享 AgentState，不是创建时复制后永不更新的字符串 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/BeforeToolCallContext.java` | record `assistantMessage/toolCall/args/context` | 可判断审核调用是否是该 Assistant 唯一 ToolCall，无需新增模型工具元数据 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSessionFactory.java` | `create`、`configureAgent`（约 67、97 行） | 三入口统一 prepare、工具装配、Prompt 和 hook；目标在此接入模式快照与退出工具工厂 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/ManagedAgentSession.java` | `prompt`、`compactBeforePrompt`、`continueAfterCompaction` | 包装执行与压缩；新增 SessionPlanContext，不把摘要当模式权威 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/builtin/BuiltInToolProperties.java` | defaults、`toolsFor` | 现有 Runtime/Cron/Child 固定配置与顺序；目标为 Runtime 增加 ExitPlanMode、TodoUpdate |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/builtin/DefaultConfiguredToolAssembler.java` | `assemble` | 依当前入口 profile 调用工厂；不按计划模式过滤工具 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/agent/SubagentExecutionService.java` | `runChild` | 用独立 ManagedAgentSessionRequest 创建 Child；当前没有计划模式传递，需增加调用时快照 |

### 4.2 API / 执行控制 / 恢复

前缀 R = `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/`；每项路径均在此明确前缀下解析。

| R 下路径 | 符号 | 已观察行为与差距 |
|---|---|---|
| `web/RuntimeSessionController.java` | create、get、delete | 目前只有创建、查询和删除；目标在 Session 资源路径增加四字段 updateSession，尚不存在通用 POST 更新方法 |
| `web/RuntimeSessionConfigurationController.java` | listModels、changeModel、changeThinking | 既有 model/thinking 使用属性路径；它们的存在不能推导应为每个新 Session 属性再建 endpoint |
| `session/RuntimeSessionConfigurationService.java` | requireMutableSession、requireUpdated、changeModel、changeThinking | 已有 ETag、idle、原子更新结果映射及统一响应装配；扩展 updateSession 复用这一应用边界，不新增模式专用 Service |
| `dto/SessionConfigurationUpdateDTO.java` | Status | 已区分 UPDATED、UNCHANGED、NOT_FOUND、BUSY、VERSION_MISMATCH；统一四字段更新复用该结果模型 |
| `event/RuntimeEventService.java` | `submit`、`submitConfirmation` | 已分派三类 user.*；不存在计划确认输入，目标增加第四分支 |
| `event/RuntimeMessageEventService.java` | `prepare`、`accept`、`startAccepted` | 先准备未启动的执行再接受消息；目标由接受事务返回最新模式快照，在启动前应用，不能把工厂 I/O 移入锁内 |
| `event/RuntimeControlEventService.java` | `acceptToolConfirmation`、`accept` | 接受前预留响应/等待容量、提交后回执先行、按固定结果段补读；可以复用传输流程 |
| `event/RuntimeEventProjector.java` | `beginConfirmation`、`persistConfirming`（约 381、399 行） | 现有工具确认保存 tool_call 和 confirming idle，然后关闭该段输出；计划需独立正文和审核语义 |
| `runtime/RuntimeActiveExecution.java` | `beginToolConfirmation`、`stageContinuationOutput`、`claimAndResumeToolConfirmation` | 已有一个待确认 Future 与新段输出交接；目标抽出窄的双类型待交互对象，避免两套取消/输出代码 |
| `runtime/RuntimeSessionControlDispatcher.java` | `dispatchStop`、`dispatchConfirmation` | 控制请求经固定执行身份投递；目标增加计划确认交接并共用停止路径 |
| `persistence/RuntimeExecutionPersistenceService.java` | `acceptMessage`、`markToolConfirming`、`acceptToolConfirmation`、`commitTerminal` | 事务同时管理事件、段与状态；目标扩展计划等待/确认，不在 Controller 写多张表 |
| `persistence/MyBatisRuntimeExecutionControlRepository.java` | `markConfirming`、`acceptConfirmation`、`claimConfirmation`、`persistConfirmation` | 锁 Session/执行、登记续跑段、保存决定、原执行至多领取一次；不是自动接管失联执行 |
| `event/RuntimeExecutionCoordinator.java` | `scheduleTimeout`、`timeout`、`commitAndRelease` | maxDuration 覆盖整个执行，取消 pending confirmation；可靠终态提交后释放资源，失败保留执行并重试终态 |
| `runtime/RuntimeSessionEngineRegistry.java` | `register`、`createSession`、`complete` | 仅保存活动执行，idle 不缓存 Agent；新执行必须重新读取持久化模式 |
| `session/RuntimeSessionResponseAssembler.java` | `getView`、`createView` | Session DTO 统一转换 VO 与 ETag；目标只补 mode，不投影执行内部待审核目标 |
| `vo/GetSessionResponseVO.java` | 字段集合 | 当前无 mode，也不暴露待确认工具；本专题仅补工作模式，不增加待审核目标字段 |
| `event/RuntimeEntryCodec.java` | `effectiveContextEntries`、模型消息转换 | 历史与模型上下文分离；新增计划展示事件不能重复变成模型消息 |

### 4.3 客户端确认恢复

以下文件实际核对 Java 仓库同一提交 `09b32d8ea4a4b43b34be302d8b2745bdc417c9a2`，行号取该提交。它们证明既有工具确认的事件恢复方式；计划分支仍为 待实现。

| 仓库相对路径 / 符号 | 已观察行为 | 计划设计用途 |
|---|---|---|
| `frontend/src/runtime/eventStore.ts` · `hasToolConfirmation`、`executionState`（27～51 行） | 从最近根消息、工具调用/结果、确认回执和 idle reason 计算 pendingTool、confirming 及中断状态，不读取 Session 待确认指针 | 增加计划事件与精确 targetEventId 的投影；不把缺失的分页记录当成仍可批准 |
| `frontend/src/composables/useRuntimeApi.ts` · `loadHistory`、`recover`（161～207 行）、`confirmTool`（339～343 行） | 分页补读后刷新 Session，状态矛盾时提示核对；工具确认同时检查 running、停止状态及事件投影 | 审核恢复沿用事件加 Session 概况对账，前端状态不能替代服务器准入 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeExecutionControlRepository.java` · `markConfirming`（116～141 行）、`acceptConfirmation`（145～170 行）、`rejectConfirmation`（374～386 行） | 工具等待保存在执行记录；接受时锁 Session/执行，拒绝停止中、非 CONFIRMING 或 pendingToolCallId 不匹配 | 保留内部待审核记录、精确目标检查与决定单次接受；无需增加 Session 公共待审核字段 |

### 4.4 存储与工具元数据

| 仓库相对路径 | 已观察事实 |
|---|---|
| `modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql` · t_sessions / t_session_executions / t_session_tool_confirmations | 已有 Session 配置、根执行、段和工具决定表；没有本设计的 mode、pending_plan_event_id 或计划决定表 |
| `modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml` · markSessionRunning / markSessionIdle / 配置更新 | Session 状态/配置变化更新 resource_version；保留其版本规则，不因内部待审核指针变化单独推进版本 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/dto/ToolInfo.java` | Mate 工具原始元数据 DTO；本设计不扩充字段 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/mate/MateToolMeta.java` | 七项投影：toolId、toolName、description、inputSchema、outputSchema、isConcurrencySafe、permission；本设计保持 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/ListMateToolsTool.java` · stableJson | 模型只看到 scope 和 name/description/inputSchema；不增加计划字段或计划专用工具定义 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/runtime/RuntimeToolPermissionPolicy.java` · decide | 既有 CallMateTool 权限路径独立于计划；approve 不覆盖 allow/ask/deny |

## 5. 09b32d8e 基线下未实现的目标

RuntimePlanReviewService、PlanReviewPort、RuntimePlanReviewAdapter、SessionPlanContext、PlanPolicyPromptComposer、RuntimePendingInteraction、ExitPlanModeTool，以及新 VO/DTO 和数据库列/表均为目标结构。上述类名、方法和关系帮助实施切片，不代表源码中已经存在。既有 RuntimeSessionController 与 RuntimeSessionConfigurationService 的 updateSession 方法，以及 Repository 的模式写入方法也是 待实现 增量，原类本身已存在。

Session 工作模式通过资源更新表达属于产品约束与 API 架构调整；当前缺少通用 Session 更新入口是实施差距。跨实例审核和提示词更新属于架构扩展；元数据稳定、idle 主动切换、Child 继承与自然语言澄清属于产品约束；精确审核目标校验、单次消费、跨 Session 隔离与凭据不落盘属于安全加固。提示词引导本身不被归类为强制安全隔离。

统一 Session 更新的组合事务、名称复用和接口替换证据集中见[HTTP 专项核对](../01-CampusClaw多Agent运行时/chat-http-v1-design.md#81-统一-session-更新源码核对)；已有独立属性写入不能当作组合原子性证明。


## 6. TODO UPDATE 基线与接入证据

清单领域事件的主要证据为 DeepSeek / OpenCode / Codex 的固定源码。公共历史与断线对账采用 Claude Managed Agents 官方 Beta 文档（2026-09-15 重新核对）：[Tools](https://platform.claude.com/docs/en/managed-agents/tools)、[Events](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)。公开文档未提供内置 TodoUpdate 或同名更新事件；没有可归因的服务端源码 commit，不推断其内部表、事务或调度。

| 固定源码路径 / 符号 | 已观察行为 | 采纳与差异 |
|---|---|---|
| DeepSeek 0a53fb55：`packages/todo/tool-todo/src/index.ts` · apply、toTodoList、execute；`src/types.ts` · TodoItem、SessionEventMap | todo_write 整份替换 content/status，追加 todo/write；投影在下一 turn/start 清空 | 采纳最小列表与显式快照；CampusClaw 首版单进行中，使用原根消息作用域，不照搬 alpha 日志格式 |
| OpenCode 849c2598：`packages/core/src/tool/todowrite.ts` · execute；`packages/core/src/session/todo.ts` · SessionTodo.update；`packages/schema/src/session-todo.ts` · Event.Updated | 工具调用服务，事务替换 TODO 表后发布 todo.updated，携带 sessionID/todos | 采纳后端明确发布领域更新；不引入独立 TODO 表；这是固定 v2 源码，不等于稳定公共 HTTP 契约 |
| Codex d58d0e58：`codex-rs/core/src/tools/handlers/plan.rs` · PlanHandler.handle_call；`codex-rs/protocol/src/plan_tool.rs` · UpdatePlanArgs；`codex-rs/app-server/README.md:1771` | update_plan 解析参数并发出 EventMsg::PlanUpdate；App Server 文档定义 turn/plan/updated；Plan 模式拒绝调用此清单工具 | 采纳工具到显式进度通知的分层；CampusClaw 使用既有请求 SSE 与持久化历史，不照搬 JSON-RPC、字段命名或模式拦截 |
| pi 5cd93f68：`packages/coding-agent/examples/extensions/todo.ts` · reconstructState、execute | 示例从当前分支工具结果 details 恢复列表 | 说明结果也可承载进度；不是 pi 内核公共 TODO 事件，CampusClaw 客户端不采用该派生方式 |
| Java 09b32d8e：`modules/agent-core/src/main/java/com/campusclaw/agent/tool/AgentToolResult.java` · record | content 与内部 details 分离 | 保持模型 ToolResult 文本；公共 todos 由后端最终结果映射 |
| Java 同基线：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/builtin/BuiltInToolProperties.java` · defaults、toolsFor | Runtime 默认八工具，无 TodoUpdate | 新工具、枚举、工厂和 Runtime 默认 profile 均为 待实现 |
| Java 同基线：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventProjector.java` · project、persistToolResults | TurnEndEvent 批次保存结果；先构造/检查帧，再 appendEntry 后 emit | 目标增加成功 TODO 的显式事件映射；仍在批次结果提交点发布 |
| Java 同基线：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/RuntimeExecutionPersistenceService.java` · appendEntry | 接收 List<CommittedEventDTO>，在段提交事务内追加 Entry 与事件列表 | 既有接口可传工具结果及任务事件两条记录，工具无须依赖数据库或 SSE |
| Java 同基线：同目录 `MyBatisRuntimeSessionRepository.java` · appendEventsLocked、recordProjectionIfComplete、findEventPage | 按列表保存多事件，投影数量取 events.size；历史直接读持久化事件并检查投影完整性 | 目标同 anchor 两事件、计数 2；GET 不重新构造 TODO，不新增持久化 API |
| Java 同基线：`modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql` · t_session_events、t_session_event_projection | eventId/eventSeq 唯一，anchor_entry_id 非唯一；投影表保存 event_count | 已有结构支持一 Entry 多事件，不需要 TODO 表或新列 |
| Java 同基线：`frontend/src/runtime/eventStore.ts` · mergeEvent、reconcileEvents、executionState | eventId 去重、历史/live 合并和根消息归属；无 TODO 面板 | 复用统一仓库，新增 applyTodoUpdated，直接消费显式快照 |

完整 SHA 沿用 §1，未升级固定基线；Java modules 与 frontend/src 范围无 TodoUpdate/TodoWrite。TodoUpdateTool、RuntimeTodoEventMapper、TodoSnapshotDTO、TodoUpdatedEventResponseVO、事件分支及面板均为 待实现。已核验的是可复用的提交骨架，未运行新增产品测试。公共显式事件属于架构变更，build 范围、元数据稳定和根执行隔离属于产品约束。

## 7. 提示词组合与逐项更新约束

源码固定点与 §1 相同；没有升级基线。Claude 官方 Tools 与 Session event stream 在 2026-09-14 重新核对，仍为 Beta 公开契约。本文仅借鉴其通用工具承载和 description 指导调用时机，不把 CampusClaw 提示词说成 Claude 托管服务的内部提示词。

| 基线 / 仓库相对路径及符号 | 已观察行为 | CampusClaw 采纳与理由 |
|---|---|---|
| DeepSeek `packages/preset/agent-presets/presets/standard/agent.cordis.yml` · planning / config.section | 标准预设要求先检查事实、完成关键取舍、只用 exit_plan_mode 提交完整方案；口头同意不批准；明确禁止用 todo_write 跟踪规划阶段 | plan 只调研和设计，build 才维护实施进度；采用同一阶段边界。将文件/代码案例改写为园区业务与混合工具约束属于产品适配 |
| DeepSeek `packages/plan/plan-mode/src/index.ts` · resolveConfig、PlanModeController 构造函数中的 plan:policy | 部署提供非空 section，模式控制注入；工具清单保持稳定 | 复用现有基础 SYSTEM；用纯 Composer 选择部署静态段，不迁入 Cordis。组合与部署资源为 待实现 架构扩展 |
| DeepSeek `packages/todo/tool-todo/src/index.ts` · DESCRIPTION_HEAD/SINGLE/TAIL（45～66 行）、toTodoList | 描述要求全量清单、完成即更新、不积攒完成；工具验证值和部署并行数量规则，不验证业务目标已完成 | TODO 调用时机集中由固定工具 description 维护；单进行中是 CampusClaw 产品约束，不将提示词要求冒充强校验 |
| OpenCode `packages/opencode/src/tool/todowrite.txt` · When to use / Rules；`packages/opencode/src/session/prompt/anthropic.txt` · Task Management | 工具描述与模型模板均要求及时更新；验证后才完成，不积攒多项。该 anthropic.txt 是 OpenCode 自己的模板 | 借鉴工具描述指导调用；通用执行原则留在 SYSTEM，不要求 BUILD 重复细则；不迁入其字段或推断 Claude Managed Agents 内部规则 |
| Codex `codex-rs/core/gpt_5_1_prompt.md` · Planning、update_plan；`codex-rs/core/src/tools/handlers/plan.rs` · handle_call | 指定模板强调及时变更状态，同文件也允许一次更新多项；Handler 解析参数、在 Plan 模式拒绝 update_plan、发出 PlanUpdate | 仅作提示词约束与程序校验的区别对照；不把“一项对应一次调用”或模板内容视作全产品硬保证。CampusClaw 参考其显式进度通知，使用自己的公共事件名，仍不引入模式拦截 |
| Java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSessionFactory.java` · create、configureAgent（67～112 行） | 先装配 tools，再加载基础 SYSTEM 并 setSystemPrompt；无计划/实施分段 Composer | 这是旧提交接入点；当前 Composer 及两份资源的迁移差距见 §10，不再按 TodoUpdate 能力拼接进度段 |
| Java `modules/agent-core/src/main/java/com/campusclaw/agent/Agent.java` · setSystemPrompt（109～111 行）；`modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java` · invokeModel（179～183 行） | setter 写入本 Agent 状态，下轮请求读取当前 systemPrompt 和同一 tools | 批准后替换完整 SYSTEM，再让审核工具返回；下轮自然使用 build 组合，无需更改 Loop 分支或重新装配工具 |
| Java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/ManagedAgentSession.java` · continueAfterCompaction、finishCompaction | 继续使用同一 Agent，压缩替换消息而非重建工具/系统规则 | 组合规则留在执行 SYSTEM，不依靠摘要推断模式，也不在压缩后重复追加段落 |

[Claude Tools 的 custom tool 指导](https://platform.claude.com/docs/en/managed-agents/tools#custom-tools)只说明应用定义描述与参数、模型选择调用、应用返回结果；[通用事件流程](https://platform.claude.com/docs/en/managed-agents/events-and-streaming#handling-custom-tool-calls)不承诺 TODO 自动调用或进度面板。没有服务端源码 commit，不推断其内部状态机。

[提示词正文](plan-policy.md)和[组合与模型验收](plan-policy.md#8-组合检查与模型场景验收)是当前目标。稳定元数据、build-only 进度和 Child 角色边界属于产品约束；审核精确身份和服务端事务继续作为安全与一致性边界。提示词本身不构成硬只读或自动判定工作完成的保证。本次仅完成静态源码、设计与资源校验，未执行模型遵循率或产品端到端测试。

## 8. Agent 默认模式

Agent 顶层 mode 是本产品新增的默认配置，不归因为 DeepSeek/Claude 的同名字段。Mate 956b547f 与 Runtime 固定 09b32d8e 的 DTO、发布目录、解析快照、Session 创建路径核对，以及相对旧 Mate 9dd5d85 的范围差异，集中记录在[元数据主设计 §2.3](../../03-数据与存储/02-Agent元数据GaussDB/README.md#23-mode-专项源码核对)。本专题继承以下目标：新交互 Session 复制 Agent 默认，缺字段兼容 build；已有 Session、Child 和 Cron 按各自既有模式权威工作。plan 仍不调用 TODO；公共工具事件与审核事务未改变。

## 8. 计划文件与方案载体

核对日期：2026-09-15。下列结论仅覆盖指明的固定代码或官方公开契约；Session 日志文件不等于单独的业务计划文件。

| 基线 | 方案保存与提交 | 证据与适用边界 |
|---|---|---|
| DeepSeek Harness | exit_plan_mode 直接接收完整 Markdown 字符串，交互 detail 展示该正文；此路径不要求计划文件 | 固定 0a53fb55，`packages/plan/plan-mode/src/index.ts` · exit_plan_mode parameters/execute、interaction.ask；alpha |
| OpenCode | 使用 Markdown 计划文件，退出规划时引用并确认该文件 | 固定 849c2598，`packages/opencode/src/tool/plan.ts` · PlanExitTool；`packages/opencode/src/session/session.ts:331` · plan；Git 项目在 .opencode/plans，否则全局 data/plans |
| Codex | Plan 模板输出 proposed_plan 正文块；会话处理为计划 item，此协议不依赖独立文件 | 固定 d58d0e58，`codex-rs/collaboration-mode-templates/templates/plan.md` · Finalization rule；`codex-rs/core/src/session/turn.rs` · extract_proposed_plan_text；不据此断言不存在可选文件工作流 |
| pi | plan-mode 示例提取 Assistant 编号计划，并用自定义 Session Entry 保存执行状态；不要求独立方案文件 | 固定 5cd93f68，`packages/coding-agent/examples/extensions/plan-mode/index.ts` · persistState、agent_end、session_start；示例扩展，不是全产品内置计划协议 |
| Claude Code | 官方 plansDirectory 配置指定计划文件目录，文档缺省 ~/.claude/plans | [官方设置](https://code.claude.com/docs/en/configuration)，本次官方检索条目明确该设置；新 settings-reference 页面抓取超限。没有服务端源码归因 |
| Claude Managed Agents | 迁移文档建议先 planning-only session，再用第二个 session 执行；该公开说明未要求统一原生计划文件 | [官方迁移文档](https://platform.claude.com/docs/en/managed-agents/migration) · Plan mode；Beta，不能与 Claude Code 文件机制混同 |

上表保留历史证据。CampusClaw 当前目标采用 Assistant 正文 + 空参数退出调用 + agent.plan 来源绑定，理由与代价由[主设计 §1.3](README.md#13-完整方案保存在哪里)维护；最新核验见[§13](#plan-streaming-evidence)。执行清单仍由独立 agent.todo_updated 记录。


## 9. Build/Plan 与逐题交互核验

核对日期：2026-09-15；实施仓固定为 `1d08f98eb04f8ea6e01bcfbfd4008c1b638391c4`，静态读取工作树 `/private/tmp/campusclaw-latest.qKWgL8`。前次问答证据 `9f785bea3ffff8f6566cd1b2727285af46a2aead` 的验证结果仍只绑定旧提交；本次没有重跑实现测试、实际模型或企业桥接。相对旧提交，本次涉及的变化包含 `QuestionCard.vue`、`PlanCard.vue`、`ModeControl.vue`、`App.vue` 的交互与草稿调整；下表给出当前观察，避免把既有问答闭环与本版新增体验混写。

### 9.1 CampusClaw 已观察行为与新增目标

下表路径相对 pi-mono-java；Java 前缀 R = `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。

| 路径 / 符号 | 1d08f98e 已观察行为 | 当前目标与理由 |
|---|---|---|
| `frontend/src/components/ModeControl.vue` · labels；`frontend/src/projectors/runtimeEventProjector.ts` · projectRuntimeEvents | 协议使用 build/plan，UI 显示普通模式/计划模式 | UI 统一 Build/Plan，协议枚举不改；产品展示约束 |
| `frontend/src/components/QuestionCard.vue` · fieldset v-for、submit；`frontend/src/runtime/questionInteraction.ts` · QuestionDraftStore、validateQuestionDrafts、normalizeQuestionAnswers | 一次渲染全部问题；按 Session/问题事件保存页内草稿；校验整批后一次发出答案 | 待实现：每次显示一题、保存当前题位置、前后导航保留草稿、末题统一提交；降低同时阅读和操作的负担，保留整批事务 |
| `frontend/src/projectors/runtimeEventProjector.ts` · agent.tool_call/agent.tool_result/agent.question；`frontend/src/components/ToolActivity.vue` · details | 只有关联 agent.plan 的 ExitPlanMode 被主图吸收；提问仍生成通用工具活动，等待时默认展开，问题参数和结果重复出现 | 待实现：问题/答案卡吸收精确关联的调用与结果，原始日志仅诊断可见；失败和缺关联显示简短状态，保留错误可见性 |
| `frontend/src/App.vue` · ConversationTimeline、conversation-dock、statusLabel；`frontend/src/runtime/eventStore.ts` · executionState/canAnswerQuestion/canReviewPlan | 问题卡在时间线，普通 Composer 留在底部；confirming 使用统一等待文案，历史与 Session 决定交互可用性 | 待实现：活动问题在原时间线位置逐题展示，Composer 以独立布局行保留草稿编辑、Slash 和停止归属，发送仍按 running 禁用；回答、审核和授权区分文案；客户端状态继续从事件恢复 |
| R `tool/question/AskUserQuestionTool.java` · execute；R `runtimeapi/event/RuntimeUserQuestionService.java` · normalizeCurrent | 工具等待完整答案，返回 JSON 文本；答案根据已提交问题快照归一 | 保留模型工具结果和服务端整批校验；隐藏 UI JSON 不删除工具调用/结果，也不重复注入公共问答事件 |
| R `runtimeapi/persistence/MyBatisRuntimeExecutionControlRepository.java` · acceptQuestionAnswer、rejectQuestionAnswer、acceptPlanConfirmation、rejectPlanConfirmation、persistPlanConfirmation | 先锁 Session 和当前执行，精确检查待交互及停止；问题回答不改模式；批准才原子更新 build、保存决定并创建续跑段 | 保留数据库审核权威和三种交互隔离；逐题 UI、普通肯定和卡片关闭不能替代正式批准 |
| R `session/PlanPolicyPromptComposer.java` · compose/planPrompt；`modules/coding-agent-cli/src/main/resources/prompts/plan/PLAN_ROOT_REVIEW.txt`、`ASK_USER.txt` | 六段资源按 mode、入口和工具清单组合；现有文字允许集中问 1～3 题，未明确默认优先一题 | 待实现：通用提问原则归入基础 SYSTEM，模式资源收敛为 PLAN.md / BUILD.md；description/Schema 保持，当前源码与迁移验收见 §10 |

本版不改变审核协议、原根续跑、工具清单稳定或提示词式规划边界。UI 汇聚属于产品展示约束；数据库精确接受和现有权限检查仍提供各自保障，Plan 不因此成为强制只读沙箱。

### 9.2 固定参考实现与适用边界

| 基线与仓库相对路径 / 符号 | 已观察行为 | 采用与明确差异 |
|---|---|---|
| Codex `d58d0e5841e0de08e251673db2d5af8cf3a1ad51`：`codex-rs/tui/src/bottom_pane/request_user_input/mod.rs` · current_question、move_question、go_next_or_submit、submit_answers（251、788、872、886 行）；同目录 multi_question_first/last 快照 | TUI 以 current_idx 显示一题，切题保存草稿，到最后组装全部答案并提交，历史插入结构化问答摘要 | 参考逐题阅读与聚合回答；CampusClaw 继续要求每题有效回答，不照搬该 TUI 的空答确认、自动处理或附件能力；此证据不等同闭源桌面 UI |
| 同 Codex：`codex-rs/core/src/tools/handlers/request_user_input.rs` · RequestUserInputHandler.handle_call（47 行） | 等待 request_user_input 响应，serde_json 序列化答案，作为成功 FunctionToolOutput 返回模型 | 工具 JSON 是模型续跑数据，UI 可以显示语义摘要；无需移除后端结果 |
| 同 Codex：`codex-rs/collaboration-mode-templates/templates/plan.md` · explore first、Asking questions、Finalization rule | 先探索可查事实，只为影响方案的未知提问，完整方案以 proposed_plan 输出；清单工具与 Plan 分离 | 参考必要澄清和简洁方案；CampusClaw 继续使用已提交 agent.plan 与正式计划审核，不把 proposed_plan 文本标签变成批准凭据 |
| OpenCode `849c2598abc7d2b40261e74b5826bc74ffc78308`：`packages/opencode/src/agent/agent.ts` · build/plan；`packages/opencode/src/tool/plan.ts` · PlanExitTool | 内置 build/plan 两个 primary Agent；Plan 有 edit deny 及计划文件例外，退出工具通过问题选择后创建 synthetic build 用户消息 | 采用 Build/Plan 命名；CampusClaw mode 属于同一 Session，批准续跑同一根，不照搬 Agent 切换、文件审核或权限模式 |
| 同 OpenCode：`packages/app/src/pages/session/composer/session-question-dock.tsx` · SessionQuestionDock、question、next/back/jump、submit | Web 输入区问题卡以 store.tab 显示当前题；缓存位置与答案，末题一次提交 answers；卡片测量可用高度，含收起与恢复 | 参考紧凑的逐题交互和视口适配；CampusClaw 关闭只收起，不等于其 question.reject；该固定 v2 源码不是已稳定公共 API 声明 |
| pi `5cd93f688aaab89dbb6dfa4aca535f21796ae185`：`packages/agent/src/agent-loop.ts` · runLoop（155 行）、executeToolCalls；约 218 行将 toolResults 追加 context | 工具完整结果加入上下文后进入后续模型调用 | 保留模型调用/结果配对；问题卡展示调整不改变 Loop 语义，数据库与请求级 SSE 仍为 CampusClaw 架构扩展 |

固定基线没有升级：本机 Codex HEAD 为 be33f80b、pi HEAD 为 4af9d21d，以上读取均显式指定固定提交；OpenCode 工作树 HEAD 就是 849c2598。没有借助产品名称推断未读取的服务端实现，也没有把源码静态核验记作交互或模型测试通过。


## 10. 两份模式提示词的最新上游核验

核对日期：2026-09-17。先以 `git ls-remote --symref <upstream> HEAD` 确认远端默认分支，再在临时 bare 仓库 fetch 并读取对应 commit；没有用本机 checkout 冒充最新上游，也没有改动既有基线工作树。“最新”指此次查询时的默认分支 HEAD，不代表稳定发布版。本节只升级提示词、模式装配和相关工具描述的证据；其他生命周期、公共 API 和前端结论仍绑定原核验提交。Claude 托管产品未参与本次提示词源码比较，未更新其公开文档核对日期。

### 10.1 新旧提交与核验范围

| 基线 / 上游默认分支 | 原核验 commit | 本次最新 commit | 读取路径、关键符号与变化 |
|---|---|---|---|
| [Codex / main](https://github.com/openai/codex) | `d58d0e5841e0de08e251673db2d5af8cf3a1ad51` | `b0659c53865dd48b0cd69c454368cea3980017cc` | `codex-rs/collaboration-mode-templates/templates/{plan,default}.md`；`codex-rs/core/src/context/world_state/collaboration_mode.rs` 的模式消息构造；`codex-rs/core/gpt_5_1_prompt.md` 的 Planning/执行规则；`codex-rs/core/src/tools/handlers/plan_spec.rs` 的 update_plan 描述。plan、所列模型基础模板和工具描述未变；default 将模式名占位符展开为 Default and Plan；模式解析类型迁入 codex_prompts，未改变本节的分工结论。 |
| [OpenCode / dev](https://github.com/anomalyco/opencode) | `849c2598abc7d2b40261e74b5826bc74ffc78308` | `88c6c7abc7f320b6aabed2634ac0b2d6e6ecea67` | `packages/opencode/src/session/reminders.ts`；`prompt/{plan,plan-mode,build-switch,anthropic}.txt`（相对该 session 目录）；`packages/core/src/tool/todowrite.ts` 的 description/execute。上述文件相对旧提交未变；保留普通与实验规划流程的差别，不把其中一种说成唯一模式实现。 |
| [DeepSeek Harness / master](https://github.com/deepseek-ai/deepseek-harness) | `0a53fb55bea101816fa226bb964ae2bed71c343b` | `0d1f50007f9bca3f52b06e1c3074fa14d5fb0720` | `packages/preset/agent-presets/presets/standard/agent.cordis.yml` 的 planning；`packages/plan/plan-mode/src/index.ts` 的 PlanModeController/plan:policy/exit_plan_mode；`packages/todo/tool-todo/src/index.ts` 的 DESCRIPTION_HEAD/SINGLE/TAIL。规划政策语义未变，TODO 文件未变；插件增加命令定义身份并调整附件接口，不影响当前取舍。根 package.json 为 `0.1.6-alpha.1`，仍为 alpha。 |
| [pi / main](https://github.com/badlogic/pi-mono) | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` | `e4c75a73222ae2c72abb5f5314fa35ee8effc508` | `packages/coding-agent/src/core/system-prompt.ts` 的 buildSystemPromptSections/buildRules/diffSystemPromptSections；`packages/coding-agent/examples/extensions/plan-mode/index.ts` 的模式上下文与 persistState；`packages/agent/src/agent-loop.ts` 的 runLoop/prepareNextTurn。基础提示词新增命名分节、工具 guidelines 与差异计算；plan-mode 示例未变。示例仍不是内核自带 Plan/Build 协议。 |

### 10.2 已观察风格与目标取舍

| 已观察源码行为 | CampusClaw 当前目标与具体理由 |
|---|---|
| Codex Plan 模板详细界定规划流程；Default 模板很短。具体模型基础模板另含执行、测试和进度要求，update_plan 描述并未承载全部工作规范。 | 学习短模式增量的写法；PLAN.md 负责规划和审核边界，BUILD.md 只负责实施模式与批准后的衔接。不能据 Default 短就断言其他 Agent 没有详细规则。 |
| OpenCode 分开模型基础模板、模式提醒与工具描述；build-switch 很短，模式提醒经合成消息注入，实验规划模板更细。其 anthropic.txt 是 OpenCode 自有模板。 | 学习职责分离，不迁移其消息注入或五阶段模板。CampusClaw 沿用每轮读取 SYSTEM 与批准后完整重组的现有接入。 |
| DeepSeek 由配置提供 plan:policy，退出规划后不注入该规划政策；TODO description 规定完整列表、完成即更新和简单任务跳过。 | 规划期禁止 TODO 留在 PLAN.md；实施进度细则集中在 TodoUpdate description。保留短 BUILD.md 是为了明确原审核方案和 CampusClaw 模式切换规则，不复制一份执行手册。 |
| pi 最新基础 Prompt 按命名块组织规则，工具 guidelines 可参与基础规则；计划示例独立注入上下文。 | 只借鉴规则归属与简洁表达；不引入分节差异协议、模板解析器或新框架。两份文件整体加载，Composer 仍是纯组合。 |

上述收敛属于**架构变更**：减少部署模式资源及重复规则；根/Child 的职责、正式审核、混合工具的规划限制、稳定元数据属于**产品约束**；服务端审核身份、权限和事务仍沿用既有安全边界。收益是规则单一维护、模式资源更短；代价是迁移时必须同时校准基础 SYSTEM 和工具描述，并对根/Child 的模型遵循情况重新验收。提示词不提供强制只读或自动验证业务完成的保证。

### 10.3 当前 Java 与实施差距

Java 本次静态读取本地 `pi-mono-java@0b81c168d816aed7864cc9fbb9caa0771407e880`，不是远端最新声明；相对 §9 的 `1d08f98eb04f8ea6e01bcfbfd4008c1b638391c4`，本次只核验下列提示词装配范围，未重跑产品或模型测试。

| 仓库相对路径 / 符号 | 已观察实现 | 待实现 调整 |
|---|---|---|
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/PlanPolicyPromptComposer.java` · compose、planPrompt | 仍读取 PLAN_COMMON、PLAN_ROOT_REVIEW、PLAN_CHILD、BUILD_ROOT、EXECUTION_TODOS、ASK_USER 六份 .txt，按入口、模式与工具名选择段落。 | 仅加载 PLAN.md / BUILD.md；当前 `compose(prompts, mode, entryPoint)` 消费 §11 的业务/预制文本快照并增加确定的一行角色说明；不按工具清单拼接提问或 TODO 段。ExitPlanMode 可用性仍由独立校验保持。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSessionFactory.java` · create、configureAgent、applyPrompt | 工具装配后加载基础 SYSTEM，使用 Composer 并保留执行基础快照。 | 保留此接入及批准后从原始 BASE 重组的顺序，不叠加旧模式文本，不改变 Tool/Skill 元数据。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/agent/RuntimeAgentPromptLoader.java` · load | 读取受管 SYSTEM.md 和 Skill 提示，SYSTEM.md 可以缺省；不自动提供本次所需的通用执行规范。 | 经现有受管 Agent 发布机制落实 [BASE 通用规则](plan-policy.md#2-基础-system-的通用行为)，是两文件迁移验收的一部分；不新增第三份内置 BASE 资源，也不宣称现有 loader 已补齐这些规则。 |

当前有效模型正文见 [PLAN.md](PLAN.md)、[BUILD.md](BUILD.md)，部署组合与 P01～P21 验收见 [plan-policy.md](plan-policy.md)。本仓此次只修改设计与目标提示词资产；Java 资源替换、受管 SYSTEM 发布及实际模型评估均需实施仓完成。


### 10.4 模型角色名称

2026-09-17 再次查询并 fetch 四个上游默认分支，commit 均与 §10.1 相同。角色用词核验范围如下；模式和多 Agent 角色提示词是不同来源，不能把角色名归因为 Plan 模板的统一约定。

| 基线与仓库相对路径 / 符号 | 已观察用词 |
|---|---|
| Codex `codex-rs/prompts/src/model_messages/multi_agent.rs:7` · DEFAULT_MULTI_AGENT_V2_ROOT_AGENT_USAGE_HINT_TEXT | 角色提示词为 “You are `/root`, the primary agent…”；`/root` 是树中位置，角色措辞是 primary agent；子 Agent 提示词使用 parent agent。 |
| OpenCode `packages/opencode/src/agent/agent.ts:153,179` · build/plan 定义；`packages/opencode/src/session/prompt/plan.txt` | build/plan 在定义中分类为 primary，与 subagent 区分；规划提示词直接称“你”，无“交互根 Agent”标题。 |
| DeepSeek `packages/preset/agent-presets/presets/standard/agent.cordis.yml:115` · planning | 标准规划政策直接以 “You are in plan mode.” 开始，未单列根 Agent 小节。 |
| pi `packages/coding-agent/examples/extensions/subagent/agents/worker.md:3,20` | 示例角色说明使用 subagent，返回说明使用 main agent；这是扩展示例，不是内核固定角色协议。 |

CampusClaw 采用 `Main Agent` / `Subagent` 作为模型可见角色名称，与 pi 示例的用词一致；这是产品表述选择，不改变架构和权限。Runtime/Child 入口名、根执行和父子关系继续表达技术归属；Subagent 的“父 Agent”仍指直接委派者。角色由 Runtime 固定注入，具体正文与映射由 [PLAN.md](PLAN.md) 和[提示词组织](plan-policy.md#1-职责与装配)维护。


## 11. 业务 Agent 模式提示词覆盖

2026-09-17 本次设计前再次查询上游默认分支并 fetch：Codex main `b0659c53865dd48b0cd69c454368cea3980017cc`、OpenCode dev `88c6c7abc7f320b6aabed2634ac0b2d6e6ecea67`、DeepSeek master `0d1f50007f9bca3f52b06e1c3074fa14d5fb0720`、pi main `e4c75a73222ae2c72abb5f5314fa35ee8effc508`。相对 §10.1 提交未变化，本节扩大读取范围以核验自定义/回退机制；最新默认分支不等于稳定版，DeepSeek 仍为 `0.1.6-alpha.1`，OpenCode 实验规划路径保留 experimental 边界。

### 11.1 基线覆盖机制与区别

| 基线、仓库相对路径与符号 | 已观察实现 | 与本次目标的关系 |
|---|---|---|
| pi `packages/coding-agent/src/core/resource-loader.ts:1023` · discoverSystemPromptFile；526～530 行；`packages/coding-agent/src/core/system-prompt.ts:121` · buildSystemPromptSections | 没有显式 systemPromptSource 时，先找可信项目 `.pi/SYSTEM.md`，再找全局 Agent 目录 SYSTEM.md；都没有则返回 undefined。自定义正文用于 preamble 分支，否则生成内置基础内容；APPEND_SYSTEM.md 是另一条追加来源。 | 参考“业务文件优先，缺失回退”的思想。它覆盖基础 SYSTEM，并非原生发现 PLAN.md/BUILD.md；不把它的追加机制混入完整替换规则。 |
| DeepSeek `packages/plan/plan-mode/src/index.ts:100` · resolveConfig；212～218 行 · plan:policy；`packages/preset/agent-presets/presets/standard/agent.cordis.yml:114` · config.section | 插件要求部署提供非空 section，标准 preset 给出规划政策；规划开启时注入该段，关闭时返回空字符串。插件自身没有目录同名文件回退规则。 | 直接支持“部署可自定义规划政策”的职责分离；CampusClaw 选择业务 Agent 本地文件和内置默认值，不引入 Cordis 配置体系。 |
| OpenCode `packages/opencode/src/config/agent.ts:11` · load；`config/variable.ts:34` · substitute；`agent/agent.ts:283` · prompt 合并；`session/llm/request.ts:56` · prepare；上述路径相对 packages/opencode/src | Agent Markdown 正文作为 prompt，也支持配置 `{file:...}` 引用；同名 Agent 可合并自定义 prompt；模型请求优先 agent.prompt，否则使用 Provider 基础模板，之后仍加入其他 system 内容。 | 说明 Agent 级自定义提示词是已有模式，但覆盖的是 Agent 基础 prompt。`session/reminders.ts` 仍单独注入内置 plan/build-switch 提醒；不能声称自定义 plan Agent prompt 就完整替换它们。 |
| Codex `codex-rs/protocol/src/openai_models.rs:624` · CollaborationModeMessages；`codex-rs/prompts/src/model_messages/collaboration.rs` · ResolvedCollaborationModeMessages::new；`codex-rs/core/src/context/world_state/collaboration_mode.rs:24` · from_collaboration_mode | 模型目录可提供独立 default/plan 文本；解析器有 bundled 默认，运行时优先目录覆盖，再选 mode.settings.developer_instructions。 | 有模式文本可替换的源码机制，入口是目录/调用配置，未在此路径发现业务目录 PLAN.md/BUILD.md 自动发现约定。不能把全部指令来源简化成同名文件优先。 |
| Codex `codex-rs/core/src/config/mod.rs:3889` · model_instructions_file 读取 | 支持从指定文件提供基础指令，作为 base_instructions 的一类来源。 | 属于基础指令覆盖，不等于仅替换 Plan/Default 模板。 |

以上是源码事实，不推断托管产品内部提示词。CampusClaw 的精确文件名、逐文件回退和作用目录是本产品选择；类似机制支持该扩展的合理性，但没有据此宣称四个基线具有完全相同的文件协议。

### 11.2 Java 当前装配与发布差距

本次读取本地干净源码 `pi-mono-java@21c3f59be033e7bdd5506a2d9d48baa2581bc3c7`，不是远端最新声明。相对前次 `0b81c168d816aed7864cc9fbb9caa0771407e880`，以下范围只有 AgentSessionFactory 增加 prepare 返回空值校验；其他所列文件无变化。未运行实现或模型测试。

以下 Java 路径相对 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。

| 路径 / 符号 | 已观察行为 | 待实现 调整 |
|---|---|---|
| `runtimeapi/agent/RuntimeAgentPromptLoader.java` · load、readOptionalFile、safeRealPath、requireManagedSize | 仅 SYSTEM.md 与 Skill 摘要；受管目录内真实路径、普通文件、无链接与大小检查。 | 复用安全读取；新增两可选模式文件的独立选择、空白/编码错误失败与不可变 AgentPromptSnapshotDTO；默认资源由 Loader 启动时固定。 |
| `session/PlanPolicyPromptComposer.java` · compose、load | 全局六份固定资源，无按 Agent 路径读取。 | 纯 `compose(prompts, mode, entryPoint)`，不持有 Agent 可变状态；业务选择已由 Loader 完成。 |
| `session/AgentSessionFactory.java` · create、applyPrompt | prepare 返回后另从 `.campusclaw` 读取 BASE；工厂调用 Composer。 | PreparedAgentRuntime 带提示词快照，工厂与执行直接使用，不再通过可变目录路径重读。 |
| `runtime/PreparedAgentRuntime.java` · record | 仅 agentId、agentRoot、metadata、skills，未携带模式正文。 | 增加不可变 prompts 快照，执行内共享；不暴露到公共 VO。 |
| `runtime/AgentRuntimeManager.java` · prepare、refresh、withAgentLock、loadSnapshot | prepare 缓存命中在锁外读取；刷新/重建在每 Agent 的 ReentrantLock 内。 | 包括缓存命中在内，同锁读取完整 PreparedAgentRuntime 与提示词快照，使发布和读取不交错；不是分布式锁。 |
| 同文件 · rebuild、writeRuntimeTree、publish、containsForbiddenEntry | staging 只生成 agent/settings/SYSTEM/绑定 Agent/Skill 文件，整目录替换并清理备份；额外合法普通文件可存在，但 refresh 不保留它们。 | 明确保留当前 PLAN.md/BUILD.md 两可选文件到 staging，统一校验发布；缺失不创建，非法文件报错，不通过“缓存不完整 → 重建”擦掉错误覆盖。 |

受管文本上限沿用 `modules/common/src/main/java/com/campusclaw/common/constant/ClawConstants.java` · Skill.MAX_FILE_BYTES（1 MiB）。不新增 Maven 依赖、Agent 元数据字段、公共 API 或数据库字段。仅新增内部 DTO 与装配/刷新行为；部署方负责文件分发，现有 Mate Runtime 响应没有这两份提示词字段。

### 11.3 决策与验收

业务文件独立完整替换、仅缺失回退、当前执行固定快照、Subagent 使用自身目录、refresh 保留可选文件是**架构扩展**；角色与正式审核仍为**产品约束**；复用受管路径限制且对无效覆盖失败，是**安全加固/配置可靠性约束**。收益是业务可定制工作方式而不改预制资源；代价是发布与读取需保持一致，自定义正文承担自身行为评估。规则由 [plan-policy.md §1](plan-policy.md#11-业务文件优先与独立回退)维护，实施必须覆盖 P16～P21，不能以文件能够读取替代生命周期和刷新验证。

## 12. 主线实现状态核验（2026-09-18）

上游 `https://github.com/superheromeZzh/pi-mono-java.git` 默认分支 main，经 `ls-remote --symref` 与隔离于工作树的 fetch 确认并读取完整提交 `8c5fda1dde51675859bc9c07e145dbe253656dea`。相对前次本地 `21c3f59be033e7bdd5506a2d9d48baa2581bc3c7`，本次新增核验两文件提示词、目录覆盖和快照装配；相对问答开发分支 `9f785bea3ffff8f6566cd1b2727285af46a2aead` 与 UI 旧点 `1d08f98eb04f8ea6e01bcfbfd4008c1b638391c4`，核对当前主线工具、事件、逐题卡片和工具日志汇聚。§1～§11 保留历史证据，只能在各自提交范围解释“待实现”。外部 Agent 比较结论未变，本次未升级外部基线。

Java 路径前缀 R 为 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`，资源前缀 S 为 `modules/coding-agent-cli/src/main/resources/`。

| 核验范围 | 仓库相对路径 / 关键符号 | 当前实现与边界 |
|---|---|---|
| 三工具与装配 | R `tool/{plan/ExitPlanModeTool,todo/TodoUpdateTool,question/AskUserQuestionTool}.java` · execute；`tool/builtin/{BuiltInToolName,BuiltInToolProperties,DefaultBuiltInToolFactory}.java`；S `application.yml` | 已实现；11 项 Runtime 缺省工具，两种模式共用定义；Child/Cron 缺省不装配三工具。 |
| 审核/提问等待 | R `runtimeapi/runtime/RuntimeSessionEngineRegistry.java` · createSession；`RuntimeActiveExecution.java` · await、claimAndResumePlanReview、claimAndResumeQuestionAnswer；`RuntimePendingInteraction.java` | 已实现；执行对象直接实现 PlanReviewPort/UserQuestionPort，共享一个交互槽；批准应用模式后才完成等待。目标图中的独立 Adapter 为推荐职责拆分，不代表工具功能缺失。 |
| 权威事件 | R `runtimeapi/event/RuntimeEventProjector.java` · beginPlanReview、beginQuestion、persistToolResults、toolResultEvents；`RuntimeTodoEventMapper.java` · map | 已实现 agent.plan、agent.question 和 agent.todo_updated；计划/问题与 confirming 同次提交，TODO 与最终成功 ToolResult 同次提交。 |
| 模式文件与选择 | R `runtimeapi/agent/RuntimeAgentPromptLoader.java` · loadSnapshot、loadOverrides、readOptionalModeFile、decodeUtf8；S `prompts/plan/{PLAN,BUILD}.md` | 已实现两资源、逐文件覆盖/缺失回退、严格 UTF-8 与非法覆盖失败；六份 TXT 已删除。BASE 仍来自受管 SYSTEM 和 Skill，通用业务指令是否已发布不能由代码推断。 |
| 快照及刷新 | R `runtime/AgentRuntimeManager.java` · prepare、rebuild、loadExistingModeOverrides、writeRuntimeTree、loadSnapshot；`PreparedAgentRuntime.java`；`runtimeapi/agent/AgentPromptSnapshotDTO.java` | 已实现同一 Agent 锁内准备、不可变文本及来源快照、重建保留两可选文件。 |
| 提示词应用 | R `session/PlanPolicyPromptComposer.java` · compose；`AgentSessionFactory.java` · applyPrompt；`ManagedAgentSession.java` · applyMode | 已实现从原执行快照组合 BASE/角色/当前模式；批准后重组不重新读盘。SessionPlanContext 是目标拆分，实际职责由上述对象承担。 |
| 逐题问答与日志汇聚 | `frontend/src/components/QuestionCard.vue` · currentIndex、displayedQuestions、previousQuestion、nextQuestion、submit；`frontend/src/projectors/runtimeEventProjector.ts` · projectRuntimeEvents、matchingQuestion、questionToolStatus | 已实现当前一题、本地前后导航、整批答案提交；问题/方案卡吸收关联调用结果，问题生成失败保留状态。 |
| TODO 客户端恢复 | `frontend/src/runtime/eventStore.ts` · executionTodos | 从当前根的最后一条 agent.todo_updated 读取完整快照；主图同步使用实际消费符号，不能据推荐职责名不同判断功能缺失。 |

验证状态：本次读取源码、对比指定旧新提交并校验设计；未执行新的 Java/数据库/浏览器或模型回归。§2/§9 的历史测试结果仍绑定原提交，不升级为本次通过。Mate 公共桥接保持待实现；业务 SYSTEM 发布、真实模型遵循和生产环境验收为未核验。独立服务/Adapter 等推荐类名与实际职责归属分开记录，禁止用某个目标类不存在概括整个功能待实现。

<a id="plan-streaming-evidence"></a>

## 13. 正文流式与审核绑定专项

2026-09-19 确认相关上游默认分支并隔离 fetch HEAD；下表为当次源码快照，不是稳定发布声明。设计仓基于 main `8f7fc06ab8990dd657c1a7671250434a628b7525`。只升级正文、调用及审核来源范围，其他历史结论不自动升级。

| 仓库 | 旧证据 → 本次默认分支完整 commit | 核验范围与变化影响 |
|---|---|---|
| pi-mono-java | `8c5fda1dde51675859bc9c07e145dbe253656dea` → main `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12` | 旧完整参数审核仍存在；文本流已实现，同响应来源绑定待实现；读取远端 commit，未覆盖本地 `21c3f59b` 工作树 |
| openai/codex | `b0659c53865dd48b0cd69c454368cea3980017cc` → main `78245b47af2a7aafcabe025828ceecca69db4df1` | Plan 模板与正文解析仍分离于工具结果；仅核验下列源码，不将实验性 App Server plan delta 说成稳定公共 API |
| badlogic/pi-mono | `e4c75a73222ae2c72abb5f5314fa35ee8effc508` → main `36b60d2e8985899743c4cf5bd5f8929832a3f05d` | 保留 Assistant 文本/调用生命周期与完整结果后续轮次；不把示例计划扩展等同统一产品协议 |
| deepseek-ai/deepseek-harness | `0d1f50007f9bca3f52b06e1c3074fa14d5fb0720` → master `ddefc45fbc7f8e46dd73185e68295696d1297887` | `packages/plan/plan-mode/package.json` 为 `0.1.6-alpha.2`；退出工具仍接收完整 plan，不支持“所有基线都用正文提交”的概括 |

### 13.1 已观察源码

以下 Java 前缀 R = `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`；路径相对各仓库。

| 来源与路径 / 符号 | 实际行为与对目标的约束 |
|---|---|
| Java `modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java` · runTurns、invokeModel、runToolPhase | 一次模型响应可同时有文本与 ToolCall；先写上下文、发 MessageEnd，再执行工具。无调用且无控制消息则结束；目标不能指望纯正文结束后自动再请求退出工具 |
| Java R `tool/plan/ExitPlanModeTool.java` · parameters、requirePlan、execute | required plan 字符串，校验标题/长度后 reviews.await(callId, plan)；工具不负责生成计划。空参数契约与结果引导待实现 |
| Java R `runtimeapi/event/RuntimeEventProjector.java` · projectMessageUpdate、persistAssistant、beforeToolCall、beginPlanReview | 普通 TextDelta 已投影；完整 Assistant 先提交，再记录调用。beginPlanReview 从调用参数取正文；persistAssistant 末尾清空 assistantEntryId，目标需另保留不可变已提交映射，不能读已清空字段 |
| Java R `runtimeapi/event/RuntimeCommittedEventFactory.java` · agentMessage、textContent、agentPlan | 消息正文将 TextContent 直接按顺序拼接；计划 payload 只有调用与正文，无 sourceMessageEventId。目标共用正文提取，不二次修剪或插入换行 |
| Java R `runtimeapi/runtime/RuntimeActiveExecution.java` · beginPlanReview、await、claimAndResumePlanReview | 原执行等待、领取决定并应用模式；完整审核与批准续跑已经实现，新增来源绑定不能表述为整套审核待实现 |
| Java `modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateChatSseParser.java` · appendText、appendToolCall | 模型文本与工具参数分别产生增量；参数生成不等于工具执行，公共 projector 没有因此自动暴露参数 preview |
| Java `frontend/src/projectors/runtimeEventProjector.ts` · projectRuntimeEvents | 消息与计划分别投影，计划吸收关联工具日志；新计划 preview 与 completed 同 ID 投影待实现，当前目标见 §14 |
| pi `packages/agent/src/agent-loop.ts` · streamAssistantResponse、executeToolCalls、executePreparedToolCall；`packages/agent/src/types.ts` · AgentEvent | Assistant 增量与工具执行更新、完整工具结果属于不同阶段；工具回调可报更新，最终结果参与模型历史。无需为计划正文引入通用工具结果流 |
| Codex `codex-rs/collaboration-mode-templates/templates/plan.md` · Finalization rule | 方案作为模型正文中的 proposed_plan 块；Plan 模式由开发者模式指令退出，不是 CampusClaw 的 ExitPlanMode({}) 审核工具 |
| Codex `codex-rs/core/src/session/turn.rs` · handle_plan_segments、emit_streamed_assistant_text_delta、maybe_complete_plan_item_from_message | 流式解析正文为普通文本或 ProposedPlanDelta；最终从完整消息提取 plan item。支持正文流式与最终权威分离，但并非我们空参数工具方案的原样实现 |
| DeepSeek `packages/plan/plan-mode/src/index.ts` · PlanModeController 中 EXIT_PLAN_MODE parameters/execute/presentCall | plan 必填；交互 detail 取 args.plan，批准后 pendingIntents 安排模式变化。第一种不是所有 Agent 的通用实现 |

### 13.2 托管公开契约与目标差异

2026-09-19 重新读取 [Claude Managed Agents Events and streaming](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)：Beta preview 为临时 best-effort，不持久化、不重放；文本 agent.message 支持增量，agent.thinking 仅 start，工具调用/结果及 MCP 事件不走这套 preview。仅说明公开观察契约，不能据此推断内部工具是否渐进执行，更不能证明其实现了 CampusClaw 的计划审核工具。

CampusClaw 同响应正文与空参数退出调用的当前目标及标记解析增量统一见[§14](#plan-marker-evidence)和[流式主文](plan-streaming.md)。此处的 pi、DeepSeek 与 Claude 记录仅证明各自当次读取的行为，不替代 §14 的局部更新，也不证明其他基线采用相同的计划事件。

本次只有静态源码与设计契约验证。未运行 Java、数据库、实际 Provider、浏览器端到端或性能测试；首字时间改善是设计目的，不能宣称已验证的耗时收益。

### 13.3 历史设计验收范围

以下记录对应设计提交 `f5eaa8c752905e65b2292dee4d350f980fab8ed5`，不是标记解析方案的当前验收；当前检查单独登记在 §14。

| 检查 | 结果与证明边界 |
|---|---|
| 共享事件校验器 | POST/GET 同形、来源正文/根/调用/先后关系、旧历史兼容通过；38 项计划反例被拒绝，另保留 114 POST、57 历史、15 批次、15 TODO、31 问答反例检查 |
| 契约静态测试 | test_chat_api、test_document_maintenance、test_control_retirement、test_command_catalog_contract、test_command_response_contract、test_help_contract 共 53 项通过；skill-statistics 校验通过；生成 HTML 与 JSON 同步 |
| 专题机械与视觉 | 7 个 SVG 由 PlantUML 生成；ASCII、XML、Markdown SVG/图源行锚点、git diff --check 通过；完整类图与旧版对照，新增时序及受影响审核/端到端图检查原尺寸与缩放阅读 |
| 全仓 API 总入口 | validate-chat-api.py --full 未通过：全仓 Markdown 扫描遇到本次范围外的失效路径 `../../02-服务与接口/03-模型管理Provider契约/diagram.puml`；未修改或跳过该检查冒充全通过 |
| 接口页 DOM 测试 | test_chat_api.cjs 未运行成功：本地及桌面捆绑 Node 环境均缺 jsdom；Python 静态测试不替代 DOM 交互验收 |

模型同响应输出、压缩保护、数据库事务、两跳桥接、真实前端流式合并及性能均仍待实施验收。原有 AskUserQuestion/TODO/状态图随同一图源重新生成及行锚点更新，不新增这些功能的架构结论。

<a id="plan-marker-evidence"></a>

## 14. 标记解析与计划专用流式事件

核对日期 2026-09-19；设计起点为 `9282157268d26e7d9135a54df5474fed7b522701`。重新确认 Codex 默认分支 main 并隔离 fetch；Java 使用重新 fetch 的 origin/main，未改用户工作树。只更新下表列出的范围，不将其他模块或 §13 的 pi、DeepSeek、Claude 核验日期滚动为本次最新。

| 仓库 | 上次证据 → 本次完整提交 | 范围与结论影响 |
|---|---|---|
| pi-mono-java / main | `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12` → `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12` | 未变化；重新读取 ExitPlanMode 参数/执行、RuntimeEventProjector 文本投影/提交/审核及 RuntimeCommittedEventFactory 完整消息/计划。已实现完整审核，标记解析、空参数绑定和 plan delta/completed 待实现 |
| openai/codex / main | `78245b47af2a7aafcabe025828ceecca69db4df1` → `78245b47af2a7aafcabe025828ceecca69db4df1` | 未变化；重新读取模板、流式解析器、plan Item 生命周期及 App Server 事件映射。源码仍将 item/plan/delta 标为 EXPERIMENTAL，不宣称稳定发布 |

### 14.1 源码事实与公开契约

Java 路径前缀 R 沿用 §13.1；Codex 路径相对其仓库。

| 来源 / 路径 / 关键符号 | 已观察行为 |
|---|---|
| Codex `codex-rs/collaboration-mode-templates/templates/plan.md` · Finalization rule | 正式方案位于独占行的 proposed_plan 标签内，每轮最多一块；模板不承担网络流解析 |
| Codex `codex-rs/utils/stream-parser/src/proposed_plan.rs` · ProposedPlanParser、extract_proposed_plan、closes_unterminated_plan_block_on_finish | 增量识别标记，区分普通文本和计划片段；包含响应结束时补闭合未闭合块的测试。不能将 CampusClaw 严格闭合规则说成 Codex 原样行为 |
| Codex `codex-rs/core/src/session/turn.rs` · ProposedPlanItemState（约 1918）、handle_plan_segments（约 2115）、maybe_complete_plan_item_from_message（约 2246） | 后端创建 Plan item、发送计划增量，完整消息到达后提取权威方案；不是前端收到普通完整消息才包装为计划 |
| Codex `codex-rs/app-server-protocol/src/protocol/event_mapping.rs` · EventMsg::PlanDelta（约 372）；同目录 `common.rs` · PlanDelta（约 1954） | 映射为 item/plan/delta；公开通知标记为 EXPERIMENTAL，Item started/completed 属于 Codex 生命周期 |
| Java R `tool/plan/ExitPlanModeTool.java` · parameters、requirePlan、execute | 当前 required plan 字符串，完成标题/长度检查后 await；不是工具生成正文 |
| Java R `runtimeapi/event/RuntimeEventProjector.java` · projectMessageUpdate、persistAssistant、beginPlanReview | 当前普通 TextDelta 投影、原 Assistant 提交、工具调用提交及完整审核事务已存在；审核从参数取文，提交后清理 assistantEntryId，新绑定须保存不可变已提交来源 |
| Java R `runtimeapi/event/RuntimeCommittedEventFactory.java` · agentMessage、textContent、agentPlan | TextContent 直接拼接，usage 放在完整消息；计划没有 phase。目标需分离公开普通正文与原始模型历史，不能删除原始方案或重复 usage |

2026-09-19 重新读取 [OpenAI App Server 官方文档](https://learn.chatgpt.com/docs/app-server)：plan Item 的增量是实时展示，最终完整文本为权威且可能不同；文档和上表源码共同支持“增量预览 + 最终全量覆盖”，不证明 CampusClaw 的持久化事务或退出审核工具。

### 14.2 CampusClaw 目标与差异理由

- **架构变更，待实现**：后端 PlanTextParser 识别标记，最终 PlanTextSnapshotDTO 同时供普通消息投影与 PlanProposalBinder 使用；原 Entry 保留完整模型响应，来源绑定不暴露成新的公共字段。
- **产品约束，待实现**：agent.plan 只用 delta/completed，第一条非空 delta 建卡，不引入 Codex 的 started；同一计划 ID 延续到审核事务提交后的完整事件，保持现有 type + phase 契约。
- **安全加固，待实现**：要求唯一显式闭合块与同响应唯一 ExitPlanMode({})；拒绝未闭合、多块/嵌套及混合调用进入审核。相对 Codex 的结束补闭合更严格，代价是模型格式不合格时需要修正。
- **产品约束**：继续使用企业两跳身份、当前待审核状态和明确批准；预览、闭合标签及流关闭均不授权执行。首字延迟改善是目标，未完成性能验证。

实施、故障、发布和运行时验收唯一维护在[流式主文 §2～§6](plan-streaming.md#2-目标标记识别与计划专用增量)。公共样例校验不能证明模型始终同响应输出、内部 Entry 绑定、事务原子性、断线并发或实际前端渲染。

### 14.3 当前设计验证

| 检查 | 实际结果与边界 |
|---|---|
| validate-chat-events.py | 通过；54 项计划反例拒绝，覆盖字段、两 phase、非空增量、身份冲突、迟到增量、历史排除 preview、新写提交顺序及审核关联；保留 114 POST、57 历史、15 批次、15 TODO、31 问答反例。允许无 preview、最终全量校准、合法重复片段与旧无 phase 读取 |
| Python 静态测试与生成同步 | test_chat_api、test_document_maintenance、test_control_retirement、test_command_catalog_contract、test_command_response_contract、test_help_contract 共 53 项通过；skill-statistics 通过；render_chat_api.py --check 通过 |
| 图形与文档 | 计划专题 7 个 SVG 与前端相关图重新生成；专题及前端机械校验通过：PlantUML ASCII、XML、Markdown 图/源码行锚点及 git diff --check。全局类图对照旧版，类图与受影响时序按原尺寸及文档宽度查看；问答/TODO 图仅生成同步和锚点更新，不新增其行为结论 |
| 全仓 API 校验 | validate-chat-api.py --full 未通过：范围外 Markdown 仍引用不存在的 `../../02-服务与接口/03-模型管理Provider契约/diagram.puml`；不以局部通过冒充全仓通过 |
| 接口页交互与视口 | test_chat_api.cjs 未运行成功：缺少 jsdom。本地 HTML 的浏览器访问被 URL 安全策略阻止，未绕过；桌面与 360 px 页面显示、键盘/焦点交互未验收。静态 HTML 内容检查不替代真实 DOM 验证 |

当前交付仅设计文档、接口样例、设计校验器与生成图；没有修改产品实现。Java 解析器、数据库竞争、真实前端流式、Mate 两跳和模型首字性能仍为待实现/待验收。
