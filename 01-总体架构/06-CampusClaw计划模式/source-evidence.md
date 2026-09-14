# 计划模式源码证据与实现差距

版本：1.5.0；核对日期：2026-09-14。本文区分源码事实、基线能力和 CampusClaw 推荐增量；不把历史设计中“待实现”标签当作当前源码结论。

## 1. 固定提交

| 仓库 | 实际分析基线 | 证据边界 |
|---|---|---|
| deepseek-ai/deepseek-harness | `0a53fb55bea101816fa226bb964ae2bed71c343b` | 固定 `dsh-0.1.2-alpha.2`；读取固定提交的源码与 standard preset，未使用本机较新 checkout 替代 |
| badlogic/pi-mono | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` | Runtime 内核、工具结果与下轮模型调用顺序的固定基线 |
| superheromeZzh/pi-mono-java | `09b32d8ea4a4b43b34be302d8b2745bdc417c9a2` | 2026-09-14 fetch 后 origin/main；本地 f61906b 已包含全部本专题分析的 Java、Mapper 和 SQL 内容 |
| anomalyco/opencode | `849c2598abc7d2b40261e74b5826bc74ffc78308` | 仅核对 TODO 描述和 anthropic 模型模板的任务管理段；该模板不是 Claude 官方提示词 |
| openai/codex | `d58d0e5841e0de08e251673db2d5af8cf3a1ad51` | 核对指定 gpt_5_1 提示词与 update_plan Handler；不代表所有模型使用同一模板 |
| pi-mono-java-design | `9aac37890edd257354c9dab0819bec0e94e513c8` | 本次修订前的设计主线；保留当前 Session Events、权限、工具 profile 和元数据契约 |

前序分析使用 Java `510d882ca45541e0086586dab89c429c5a18cf20`。本次采用 `09b32d8e`；两者之间是仓库指引变更，本专题 Runtime 路径不变。对比本地 `f61906b` 至 `09b32d8e` 的差异仅在指引、前端样式/开发代理及配套文档脚本；不据此声称 Agent Loop 或确认机制发生新增变化。

## 2. DeepSeek 计划模式

以下路径相对 DeepSeek 仓库，链接固定到同一提交。

| 路径 / 符号 | 已观察行为 | 设计用途 |
|---|---|---|
| [`packages/plan/plan-mode/src/index.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/0a53fb55bea101816fa226bb964ae2bed71c343b/packages/plan/plan-mode/src/index.ts) · `PlanModeConfig`、`resolveConfig` | section 为部署提供的非空指导文本；插件没有自行选择一套业务计划提示词 | 计划指令归 Runtime 部署，不扩充 Agent/工具元数据 |
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

以下文件实际核对 Java 仓库同一提交 `09b32d8ea4a4b43b34be302d8b2745bdc417c9a2`，行号取该提交。它们证明既有工具确认的事件恢复方式；计划分支仍为 target-only。

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

## 5. 明确未实现的目标

RuntimePlanReviewService、PlanReviewPort、RuntimePlanReviewAdapter、SessionPlanContext、PlanPolicyPromptComposer、RuntimePendingInteraction、ExitPlanModeTool，以及新 VO/DTO 和数据库列/表均为目标结构。上述类名、方法和关系帮助实施切片，不代表源码中已经存在。既有 RuntimeSessionController 与 RuntimeSessionConfigurationService 的 updateSession 方法，以及 Repository 的模式写入方法也是 target-only 增量，原类本身已存在。

Session 工作模式通过资源更新表达属于产品约束与 API 架构调整；当前缺少通用 Session 更新入口是实施差距。跨实例审核和提示词更新属于架构扩展；元数据稳定、idle 主动切换、Child 继承与自然语言澄清属于产品约束；精确审核目标校验、单次消费、跨 Session 隔离与凭据不落盘属于安全加固。提示词引导本身不被归类为强制安全隔离。

统一 Session 更新的组合事务、名称复用和接口替换证据集中见[HTTP 专项核对](../01-CampusClaw多Agent运行时/chat-http-v1-design.md#81-统一-session-更新源码核对)；已有独立属性写入不能当作组合原子性证明。


## 6. TODO UPDATE 基线与接入证据

TODO 公共工具交互以 Claude Managed Agents 官方 Beta 文档为主基线，核对日期 2026-09-14：
[Tools](https://platform.claude.com/docs/en/managed-agents/tools) 的 Available tools / Custom tools 未提供内置 TODO；[Session event stream](https://platform.claude.com/docs/en/managed-agents/events-and-streaming#handling-custom-tool-calls) 通过 agent.custom_tool_use、requires_action 和 user.custom_tool_result 组织外部执行。[List Events](https://platform.claude.com/docs/en/api/beta/sessions/events/list) 是公开事件联合类型。它们只证明公开契约，无服务端源码 commit。

CampusClaw 采纳工具业务由通用调用/结果承载的风格，仍由 Runtime 内置工具执行，并用已有 agent.tool_call/agent.tool_result 输出；不迁入客户端执行、requires_action 或新的用户结果提交接口。TODO 参数和状态并非 Claude 的原生约定。

| 固定源码路径 / 符号 | 已观察行为 | 采纳与差异 |
|---|---|---|
| DeepSeek 0a53fb55：`packages/todo/tool-todo/src/index.ts` · apply、toTodoList、execute；`packages/todo/tool-todo/src/types.ts` · TodoItem、SessionEventMap | todo_write 整份替换，只有 content/status；状态 pending/in_progress/completed，部署可选择并行进行中；追加 todo/write，最新快照投影于下一 turn/start 清空 | 参考最小完整列表；CampusClaw 首版最多一个进行中；公共进度直接用工具成功结果，不增加 todo/write 的第二份领域日志，属于产品约束及架构变更 |
| pi 5cd93f68：`packages/coding-agent/examples/extensions/todo.ts` · reconstructState、execute | 示例从当前分支的 todo 工具结果 details 恢复完整列表 | 借鉴结果可恢复；CampusClaw 公共事件不暴露 details，改用既有 content.text 的工具 JSON。不是迁入 pi 扩展系统 |
| Java 09b32d8e：`modules/agent-core/src/main/java/com/campusclaw/agent/tool/AgentToolResult.java` · record | 工具返回 content 与内部 details | TodoUpdate 直接返回 text ContentBlock，保留公共接口 |
| Java 同基线：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/builtin/BuiltInToolProperties.java` · runtime、toolsFor | Runtime 默认八工具，显式配置按入口解析；没有 TodoUpdate | 新工具、枚举、工厂与 Runtime 默认追加为 target-only；Cron/Child 默认值不变 |
| Java 同基线：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventProjector.java` · project、persistToolResults（188～198、358～366 行） | TurnEndEvent 批次结果进入通用 ToolResult 路径；检查帧后 appendEntry，再 emit | 复用权威提交，无需 TodoUpdate 专用事件分支；进度发送时点是公共结果提交，不是工具 Java 方法刚返回 |
| Java 同基线：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEntryCodec.java` · toolResultEntry（134～155 行）；`RuntimeCommittedEventFactory.java` · agentToolResult（103～113 行） | Entry 保存工具名与内容，公共结果包含 sourceEventId/toolCallId/content/isError，成功结果不含 details/toolName | 客户端关联调用取工具名，从成功结果文本读清单；不扩充外层字段 |
| Java 同基线：`frontend/src/runtime/eventStore.ts` · mergeEvent、reconcileEvents、executionState | eventId 去重、历史顺序保留 live 尾部，以原根消息关联执行；没有 TODO 投影 | 增加纯函数 deriveTodos 与面板；实时、恢复共用，target-only |

完整 SHA 沿用 §1；本次核验固定提交，没有升级基线。对 Java `modules` 和 `frontend/src` 检索 TodoUpdate/TodoWrite 无实现命中；上述通用路径已存在，未执行 TODO 产品测试。TodoUpdateTool、客户端 deriveTodos 和其整份列表约束均属于新目标，具体生命周期与验收由 [TODO 主设计](todo-update.md) 维护。不从 Claude 文档推断内部 TODO 表、持久化事务或自动恢复调度器。


## 7. 提示词组合与逐项更新约束

源码固定点与 §1 相同；没有升级基线。Claude 官方 Tools 与 Session event stream 在 2026-09-14 重新核对，仍为 Beta 公开契约。本文仅借鉴其通用工具承载和 description 指导调用时机，不把 CampusClaw 提示词说成 Claude 托管服务的内部提示词。

| 基线 / 仓库相对路径及符号 | 已观察行为 | CampusClaw 采纳与理由 |
|---|---|---|
| DeepSeek `packages/preset/agent-presets/presets/standard/agent.cordis.yml` · planning / config.section | 标准预设要求先检查事实、完成关键取舍、只用 exit_plan_mode 提交完整方案；口头同意不批准；明确禁止用 todo_write 跟踪规划阶段 | plan 只调研和设计，build 才维护实施进度；采用同一阶段边界。将文件/代码案例改写为园区业务与混合工具约束属于产品适配 |
| DeepSeek `packages/plan/plan-mode/src/index.ts` · resolveConfig、PlanModeController 构造函数中的 plan:policy | 部署提供非空 section，模式控制注入；工具清单保持稳定 | 复用现有基础 SYSTEM；用纯 Composer 选择部署静态段，不迁入 Cordis。组合与部署资源为 target-only 架构扩展 |
| DeepSeek `packages/todo/tool-todo/src/index.ts` · DESCRIPTION_HEAD/SINGLE/TAIL（45～66 行）、toTodoList | 描述要求全量清单、完成即更新、不积攒完成；工具验证值和部署并行数量规则，不验证业务目标已完成 | 固定工具 description + build 进度段双重说明时机；单进行中是 CampusClaw 产品约束，不将提示词要求冒充强校验 |
| OpenCode `packages/opencode/src/tool/todowrite.txt` · When to use / Rules；`packages/opencode/src/session/prompt/anthropic.txt` · Task Management | 工具描述与模型模板均要求及时更新；验证后才完成，不积攒多项。该 anthropic.txt 是 OpenCode 自己的模板 | 借鉴工具描述与 SYSTEM 同时指导；不迁入其 priority/cancelled 等字段，不推断 Claude Managed Agents 有同样内部规则 |
| Codex `codex-rs/core/gpt_5_1_prompt.md` · Planning、update_plan；`codex-rs/core/src/tools/handlers/plan.rs` · handle_call | 指定模板强调及时变更状态，同文件也允许一次更新多项；Handler 解析参数、在 Plan 模式拒绝 update_plan、发出 PlanUpdate | 仅作提示词约束与程序校验的区别对照；不把“一项对应一次调用”或模板内容视作全产品硬保证。CampusClaw 不照搬其 PlanUpdate 专用事件或模式拦截 |
| Java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSessionFactory.java` · create、configureAgent（67～112 行） | 先装配 tools，再加载基础 SYSTEM 并 setSystemPrompt；无计划/实施分段 Composer | 可从实际工具列表判断 TodoUpdate，不增加能力元数据；模式快照接入、分段资源和 Composer 待实现 |
| Java `modules/agent-core/src/main/java/com/campusclaw/agent/Agent.java` · setSystemPrompt（109～111 行）；`modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java` · invokeModel（179～183 行） | setter 写入本 Agent 状态，下轮请求读取当前 systemPrompt 和同一 tools | 批准后替换完整 SYSTEM，再让审核工具返回；下轮自然使用 build 组合，无需更改 Loop 分支或重新装配工具 |
| Java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/ManagedAgentSession.java` · continueAfterCompaction、finishCompaction | 继续使用同一 Agent，压缩替换消息而非重建工具/系统规则 | 组合规则留在执行 SYSTEM，不依靠摘要推断模式，也不在压缩后重复追加段落 |

[Claude Tools 的 custom tool 指导](https://platform.claude.com/docs/en/managed-agents/tools#custom-tools)只说明应用定义描述与参数、模型选择调用、应用返回结果；[通用事件流程](https://platform.claude.com/docs/en/managed-agents/events-and-streaming#handling-custom-tool-calls)不承诺 TODO 自动调用或进度面板。没有服务端源码 commit，不推断其内部状态机。

[提示词正文](plan-policy.md)和[组合与模型验收](plan-policy.md#8-组合检查与模型场景验收)是当前目标。稳定元数据、build-only 进度和 Child 角色边界属于产品约束；审核精确身份和服务端事务继续作为安全与一致性边界。提示词本身不构成硬只读或自动判定工作完成的保证。本次仅完成静态源码、设计与资源校验，未执行模型遵循率或产品端到端测试。
