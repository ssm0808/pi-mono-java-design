# 前端体验源码与视觉证据

[返回前端主设计](README.md)

版本：1.7.0；更新日期：2026-09-17。初次整理基线为设计仓 `6026ba48`，计划前端增补基线为 `42243077`。本文件保存按日期和源码版本隔离的核验资料，结论只适用于标明的 commit 或安装包；具体工具标题核验见[§7](#mate-tool-display-evidence)，其他体验核验见[§6](#experience-evidence)，前次实现验证见[§5](#current-implementation)，前四节是历史证据，不将旧缺口延伸为当前缺陷。

| 证据 | 基线 |
|---|---|
| 本次对齐基线 | 设计仓 `2ee2a3211da68ad87b0d9cab353e691b00bdaebd`；Mate Events 1.5.0、内部 Events B01～B15 与 Thinking 展示规则 |
| 历史前端源码复核 | `pi-mono-java@510d882ca45541e0086586dab89c429c5a18cf20`；当时 `sessionIndex.upsert` 的前插行为使点选会话自动到顶部，直接 Name Controller 路由缺失；详见 [工作台专项](runtime-workbench-alignment.md) |
| 本专题修改基线 | 设计仓 `ee2c8e61800d95e609982e3ee354b1ee06f70fe4`；该提交中的原路径为 `campusclaw-frontend-design/`，当前路径为 `01-总体架构/04-CampusClaw前端体验/` |
| 早期设计仓基线 | `3cc234f068209c90639f812bcb8e1825301fa565` |
| HTTP 设计风格基线 | 当前工作区 `chat-http-v1-design.md` 1.38.0；设计仓 `c250e3f07536871d3d676242e552a5eb4346b0c7` |
| Codex 视觉证据 | 本机 `ChatGPT.app` 26.814.41407（build 6720）中的 light-theme CSS Token；`app.asar` SHA-256 `8fba32f8baa6d984b0f0f4149d3da46221e3adb3b52836f85fe65e31e655a8c0` |
| Codex 跟进交互证据 | 同一安装包 `webview/assets/app-initial-BCLYDefw.js` 的 `followUpQueueMode`、`K9s()`、submit action，以及 `webview/assets/zh-CN-ByRVSIXt.js` 的 Composer 文案 |
| Codex 活动展示证据 | 本机 `ChatGPT.app` 26.820.60940（build 7119）的 `tool-activity-disclosure-CZUjU0Tu.js`、`agent-activity-item-BL0IhzOn.js`、`reasoning-item-heading-Cdl3NWmT.js`、`local-conversation-turn-Ngva_Lp3.js`；`app.asar` SHA-256 `c964aebbf9a6a0f70799d01215c611d8ef6ee63f816b3d57beccddd47a811fd9` |
| pi-mono-java 原体验证据基线 | `bde123706305a41e51c9a47b22e6ad11bbd8204c`；用于本文既有活动流与富文本分析 |
| 本轮凭据复核源码基线 | `320d790726a70aada6100052952d5494d2a378ac`；`frontend/README.md`、`frontend/.env.example`、`frontend/src/App.vue`、`frontend/src/components/DevDiagnostics.vue`、`frontend/src/composables/useRuntimeApi.ts` 及 Runtime 路由测试在该 commit 上无本地修改 |
| 工具凭据实现对齐 | 变更前基线 `pi-mono-java@320d790726a70aada6100052952d5494d2a378ac`；已评审特性提交 `d03c08dbae870f19eee8d4fa79a707185f7a26b5`，位于 [Draft PR #181](https://github.com/superheromeZzh/pi-mono-java/pull/181)，尚未作为 `main` 现状 |
| Header 编辑器对照基线 | `pi-mono@4af9d21d`、`opencode@849c2598`、`openai/codex@be33f80b`、`deepseek-harness@cd5ef814`；源码路径见 3.1 |
| 当前工作台设计起点 | 设计仓 `599edb072cf75e3d8f85c775c53c0e83befd285d`；Header 前次交互基线为 `4cc8dd86f601417c22cf9306e52152acbb59bb60`，升级范围见工作台专项 |
| Postman 核对 | 2026-08-28；核对官方 Headers 编辑文档、`Agent Runtime` collection 及真实 SSE 响应 |

## 1. 历史实现观察

| 证据 | 已观察事实 |
|---|---|
| `frontend/README.md:26-28, 40-58` | 当前工作台明确不提供 JWT/APPKEY 凭据编辑器，所有 `VITE_*` 只允许非秘密浏览器参数，并禁止把 Provider 凭据、JWT 或 APPKEY 编译进浏览器产物。 |
| `frontend/.env.example:1-7` | 示例环境变量只包含 API 基址、非秘密 `callerId` 和 Agent 展示/内部 ID，没有 JWT、APPKEY、Token 或认证 Header 配置。 |
| `frontend/src/App.vue:177-290`、`frontend/src/components/DevDiagnostics.vue:4-10, 13-25` | 产品工作区与开发者诊断入口只提供 Agent/Session、模型、Thinking、会话和执行控制；诊断入口也没有凭据输入或查看能力。 |
| `frontend/src/style.css:650-704` | 现有 `.dev-diagnostics` 是 680 px 最大宽度的折叠面板，使用暖灰次级表面、虚线强边框、12 px 字号、8 px 圆角输入和次级按钮；这是本轮 Header 编辑器的视觉基线。 |
| `frontend/src/composables/useRuntimeApi.ts:18-20, 480-495` | `requestRaw` 只统一附加 `Accept`、`Accept-Language` 和非秘密 `X-HW-ID`；没有构造 `Authorization` 或 `X-HW-APPKEY`，也没有 credential store。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java:58-73`、`RuntimeRequestContext.java:45-50` | 当前只有提交消息的 `POST /sessions/{sessionId}/events` 会读取 `X-HW-ID`、`X-HW-APPKEY`、`Authorization` 并生成本次执行快照；基线尚无 `access-token`。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/HttpMateToolClient.java:93-190, 298-373` | 变更前基线实现把三项凭据同时用于 Mate 发现和 Tool execute；该行为已在特性提交中收敛，但仍是 `main@320d7907` 的已观察基线。 |
| `modules/coding-agent-cli/src/test/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeSessionRoutesTest.java:102-120` | 当前 Runtime 删除请求可在没有凭据 Header 时通过，JWT 与 APPKEY 同时出现也不由 Runtime 本地校验；当前直接调试链路依赖这一内部无本地认证边界。 |
| `frontend/src/App.vue:1-291` | 当前 Vue 前端已经形成 Agent 工作区壳、对话时间线、Composer 与运行中控制，但浏览器仍直接调用 Runtime V1，尚未落地 mate-service 公共 bridge。 |
| `frontend/src/components/ConversationTimeline.vue:37-65` | Assistant 正文使用 Vue 文本插值直接输出 `turn.text`；Thinking 是 Assistant body 内的一个“查看思考过程”折叠区；Tool 活动卡展开后只显示结果，不显示调用入参。 |
| `frontend/src/style.css:784-789` | `.assistant-message` 仅设置 `white-space: pre-wrap` 和换行，没有标题、表格、引用、链接或代码块样式。 |
| `frontend/package.json:13-21` | 运行依赖只有 Vue，没有 Markdown parser、AST renderer 或 sanitizer。 |
| `frontend/src/composables/useRuntimeApi.ts:157-176, 311-352` | 浏览器直接调用 `/campusclaw-service/v1` 并消费请求范围 SSE；流事件的 `data` 先作为 JSON 解析，不产生服务端 HTML。 |
| `frontend/src/projectors/runtimeEventProjector.ts:40-90, 112-145` | delta 按文本追加，completed 以完整文本替换 preview；Thinking 按 `assistantEntryId` 追加到 Assistant turn；Tool 只从 `tool.*` 事件读取名称、状态和结果，没有解析 Assistant completed 中的 `tool_call.arguments`。 |
| `frontend/src/types/product.ts:22-37` | `AssistantTurn` 仅有单个 `thinking:string`；`ActivityTurn` 只有 `toolCallId`、`toolName`、`status` 和 `result`，尚无入参字段或安全投影类型。 |
| `RuntimeSessionController`、`RuntimeEventController`、`RuntimeSessionConfigurationController`、`RuntimeSessionControlController` | 当前后端已实现 11 个内部 Session Runtime operation。 |
| `RuntimeEventType.java:13-26` | 对外事件同时包含持久化消息、瞬时 Assistant delta、工具进度和流终止事件。 |
| `RuntimeEventProjector.java:149-213, 215-238, 257-285` | Assistant preview 与 completed 分离；Thinking started/delta/completed 按 `assistantEntryId + contentIndex` 投影；`tool.execution.*` 只携带 `toolCallId`、`toolName`、状态和 delta，不携带入参。 |
| `RuntimeEntryCodec.java:67-88, 430-442, 512-517, 557-601` | `assistant.message.completed.message.content[]` 保留 `tool_call` 的 `toolCallId`、`name` 和结构化 `arguments`；这是工具入参的现有内部来源，前端可在工具开始前按 `toolCallId` 建立关联。 |
| Postman `Agent Runtime` collection | Session、Configuration、Events、Control 四组请求与源码 11 个 operation 一致；真实 `POST /events` 响应按 frame 展示大量 delta，证明原始事件视图适合诊断，不适合终端用户阅读。 |
| `pi-mono@4af9d21d` 的 `packages/coding-agent/docs/custom-provider.md:96-119`、`packages/coding-agent/src/core/model-config.ts:160-207` | PI Provider 将 Headers 建模为通用字符串映射，但只提供配置/扩展接口，没有逐请求图形编辑器。 |
| `opencode@849c2598` 的 `packages/app/src/components/dialog-custom-provider.tsx:273-315`、`packages/app/src/components/dialog-custom-provider-form.ts:97-128` | OpenCode 已提供可增删的 Header/Value 行，并执行去空白与大小写不敏感的重复名称校验；这是四个本地实现中最接近的通用编辑器。 |
| `openai/codex@be33f80b` 的 `codex-rs/config/src/mcp_types.rs:258-260`、`codex-rs/tui/src/history_cell/mcp.rs:427-445`；[Codex 官方配置参考](https://developers.openai.com/codex/config-reference) | Codex 通过 `http_headers` / `env_http_headers` 通用映射配置 Provider/MCP Header，TUI 展示时遮蔽静态值，但没有逐请求 Key/Value 编辑器。 |
| `deepseek-harness@cd5ef814` 的 `packages/llm/llm-pi-ai/src/config.ts:147-148, 325, 458`、`packages/client/ui-settings-models/src/client/ProviderEditor.tsx:1-21` | DSH Provider 配置支持通用 Header 映射；当前 UI 只暴露精选字段，其余配置由 `settings.yaml` 维护。 |
| [Postman 官方 Headers 文档](https://learning.postman.com/latest-v-12/docs/use/send-requests/create-requests/headers) | Postman 允许任意 Key/Value、逐行启停、Header 预设与自动补全，并折叠自动生成 Header、显示手工覆盖关系；本设计借鉴其表格交互而不复制完整 API 客户端信息架构。 |
| 本机 `ChatGPT.app` 26.814.41407 的 `app.asar` light-theme Token | 可观察到 `gray-0/50/75/100/500/750/900`、近黑 primary solid、5%/10% alpha border、灰色 user message background、green success 与 blue focus/link；这是 Codex-inspired 视觉证据，不是公开品牌规范。 |
| 同一 `app.asar` 的 `webview/assets/app-initial-BCLYDefw.js`：`followUpQueueMode`、`K9s()`、`composer.submitButtonTooltip.*` 与 submit telemetry | Codex desktop 的跟进模式取值为 `steer` / `queue`，desktop 默认 `steer`；`Cmd/Ctrl+Shift+Enter` 对单条消息执行相反模式；已排队消息支持送入当前运行、编辑、删除、重试与恢复。历史 `interrupt` 配置会归一为 `steer`。 |
| 同一 `app.asar` 的 `webview/assets/zh-CN-ByRVSIXt.js` | 产品文案使用“调整方向”“加入队列”“停止”；“调整方向”的说明是提交但不中断正在运行的模型，而不是立即中止当前模型或工具。 |
| 本机 `ChatGPT.app` 26.820.60940 的 `tool-activity-disclosure-CZUjU0Tu.js` 与 `agent-activity-item-BL0IhzOn.js` | Codex activity body 使用纵向 `flex-col` 和缩进详情；执行中 item 默认展开，完成项折叠为动作摘要，输入和输出不采用左右分栏。 |
| 同一安装包的 `reasoning-item-heading-Cdl3NWmT.js` 与 `local-conversation-turn-Ngva_Lp3.js` | 思考展示从 reasoning summary / 当前 activity 推导简短标题；完成后收敛为轻量 disclosure。该证据只支持折叠交互借鉴；CampusClaw 展示模型返回的原始推理。 |
| [OpenAI 官方 ChatGPT desktop app 文档](https://learn.chatgpt.com/docs/app) | 官方文档确认桌面应用上下文，但未公开 activity disclosure 的精确视觉规则；本设计的交互细节以本机可观察实现证据和 CampusClaw 产品约束为依据。 |
| [OpenAI 官方 Codex use cases](https://developers.openai.com/codex/use-cases) | 官方将 Codex 表述为理解代码、构建/测试、评审并交付任务的工作界面；官方未公开可复制的 Codex Design Token，因此具体色值以本机可观察资源和本设计决策为依据。 |

## 2. 历史特性分支观察

| 证据 | 已评审行为 |
|---|---|
| `pi-mono-java@d03c08db` 的 `RuntimeRequestContext.mateCredentials:45-50`、`MateCredentialHeaders:13-23` | 提交消息时精确读取 `X-HW-ID`、`X-HW-APPKEY`、`Authorization`、`access-token` 四个 Header。 |
| `MateCredentials:21-86` | 凭据是不可变执行快照；完整性要求 `X-HW-ID` + `access-token` + 至少一种 APPKEY/JWT，诊断字符串只记录是否存在。 |
| `HttpMateToolClient:95-180, 298-370`、`MateToolDiscovery` | Agent、Skill 和 Tool metadata 发现方法不再接受凭据参数；只有 Tool execute 检查完整性并附加四项快照。 |
| `HttpMateToolClientTest:270-400, 476-483` | 回归测试覆盖发现无凭据、JWT、APPKEY、双凭据、缺少 `access-token` fail closed 和脱敏 `toString`。 |

上表保留当时的评审记录，不用于判断该 PR 当前状态。该阶段公共接入差距见
[dfb90ca 源码证据](public-chat-alignment.md#2-源码证据与差距)；本次计划前端核验范围见下节。


<a id="plan-frontend-evidence"></a>

## 3. 计划模式前端历史核验（2026-09-15）

前端设计基线 `pi-mono-java-design@42243077d8605024a5d4470867525879b0d1a088`；Java 核验 `origin/main@29ebec6a8cad99896414211cda28c6fffec71bee`。旧前端基线 `510d882ca45541e0086586dab89c429c5a18cf20` 仅保留原范围。全量读取本次涉及的 App、ComposerBox、ConversationTimeline、runtime/product 类型、eventStore、runtimeEventProjector、useRuntimeApi；后端读取 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeSessionController.java`，create/get/delete 尚无通用 update。该范围尚无计划类型与 UI，不证明其他特性分支或部署不支持计划模式。

Codex 固定源码仍为 `d58d0e5841e0de08e251673db2d5af8cf3a1ad51`，通过 git show 读取，未使用工作树 HEAD `be33f80b` 替换。完整读取 `codex-rs/tui/src/chatwidget/plan_implementation.rs`、`codex-rs/core/src/tools/handlers/plan.rs`、`codex-rs/protocol/src/plan_tool.rs`，定向读取 `codex-rs/app-server/README.md` 的 plan/Item/提问协议段。符号与结论见[计划交互 §1](plan-interaction.md#1-源码与交互依据)。前者证明 TUI 的实施选择，不能当作桌面前端源码；具体卡片尺寸与位置是 CampusClaw 目标设计。

官方 [Features](https://learn.chatgpt.com/docs/features) 与 [App Server](https://learn.chatgpt.com/docs/app-server) 于 2026-09-15 重新核对。前者显示侧栏与 Add/Plan mode；后者区分方案 Item、delta、任务更新与提问。当前公开文档与固定源码可能不同，分别使用，不升级固定 commit，也不推断服务端存储。


<a id="question-slash-evidence"></a>

## 4. 计划、问答与 Slash 的前端核验（2026-09-15）

设计仓基线 `761b7640f76b74162423c0372496cdef0b88d708`；计划/问答目标来自计划模式 1.9.0、interface-delta 1.9.0 和 AskUserQuestion 1.0.0；核验时另有只涉及首版安装 SQL 的工作树增量，不纳入本前端任务。

Java 固定源码 `699f929f6826b595ed1d0162f6def66e2f84760b`（开发分支，代码提交 `17dbb20a`）；旧 `29ebec6a` 的无计划前端结论不延伸到该提交。全量读取以下仓库相对路径：

- `frontend/src/App.vue`：decidePlan、changeMode、配置/PlanCard/进度装配。
- `frontend/src/components/ComposerBox.vue`、`PlanCard.vue`、`ProgressDisclosure.vue`：标签式命令、同位置停止、按方案身份隔离反馈、安全 Markdown、显式任务摘要。
- `frontend/src/composables/useRuntimeApi.ts`、`useCommandComposer.ts`：统一 Session POST、confirmPlan/recover、独立草稿和清单失效。
- `frontend/src/runtime/commands.ts`、`eventStore.ts`、`types/runtime.ts`、`projectors/runtimeEventProjector.ts`：freezeInvocation、expectedKind、executionState/executionTodos/canReviewPlan 与方案/任务事件投影。

上述源码已有计划、审核与 Slash，固定提交没有问题/答案事件类型。公开 Mate Gateway 与桌面精确像素未由这些路径证明。

另观察同一实现仓问答开发工作树（HEAD `79cfa34daef20adfa13ae1bee7cc9c41ba5c9dc7`，未提交增量），全量读取两个文件；它们已实现问题输入与草稿校验，不能表述为“前端完全未开发”，也不视为已发布。以下 SHA-256 固定本次观察，不追踪进行中的后续修改：

| 仓库相对路径 / 符号 | SHA-256 |
|---|---|
| `frontend/src/components/QuestionCard.vue` · state / choose / writeCustom / submit / template | `95e2d8107d55d193e666c8d7bb8dde5707ba7371fb0710be11a2b0bf549d7408` |
| `frontend/src/runtime/questionInteraction.ts` · QuestionDraftStore / validateQuestionDrafts / questionAnswerEvent | `3563257198efd22ce5664c3e5236b3050f32362eb666bb8a3f4ef37a621d97b1` |

Codex 固定基线仍为 `d58d0e5841e0de08e251673db2d5af8cf3a1ad51`。新增全量读取 `codex-rs/protocol/src/request_user_input.rs`（RequestUserInputArgs/RequestUserInputEvent）及 `codex-rs/core/src/tools/handlers/request_user_input.rs`（RequestUserInputHandler::handle_call）：根执行限制、模式相关阻塞、问题与回答模型可归因于源码。CampusClaw plan/build 均等待全部答案，固定三种输入与事件恢复是自身目标约束，不复制 Codex 的可选非阻塞、isSecret 或自动解决字段。

官方 [Slash commands](https://learn.chatgpt.com/docs/reference/slash-commands) 与 [App Server](https://learn.chatgpt.com/docs/app-server) 于 2026-09-15 核对：输入 `/` 选择/过滤、命令随环境变化；提问是 experimental，resolved 也可由清理或中断产生。前者只支持发现方式，后者只支持公开协议边界；CampusClaw 颜色、选项卡片位置和单选/多选规则不是 Codex 官方 Token 或复制协议。

<a id="current-implementation"></a>

## 5. 当前实现状态（2026-09-15）

设计起点为 `pi-mono-java-design@3d76ec37311d134f27235e1ed6a2a35dd64ce6b2`。实现起点为 `pi-mono-java@9f785bea3ffff8f6566cd1b2727285af46a2aead`，位于 [Draft PR #301](https://github.com/superheromeZzh/pi-mono-java/pull/301) 的 `codex/plan-mode-runtime` 分支；“已实现”指已提交代码和下列验证范围，不等于已合入主线或已部署。

| 能力 | 实现状态与源码证据（路径相对 pi-mono-java） |
|---|---|
| 模式、计划审核与实施进度 | 已实现。`frontend/src/composables/useRuntimeApi.ts` 的 changeSetting/confirmPlan、`runtime/eventStore.ts` 的 executionState/executionTodos/canReviewPlan、`components/PlanCard.vue` 与 ProgressDisclosure 从显式事件消费完整方案和任务快照。plan 不生成调研进度，批准后续跑原根。 |
| AskUserQuestion | 已实现。`frontend/src/components/QuestionCard.vue`、`runtime/questionInteraction.ts`、`projectors/runtimeEventProjector.ts` 和 useRuntimeApi.answerQuestion 已接入三类问题、全批校验、权威答案、原根恢复与独立草稿；不解析工具文本生成问题。 |
| Session 恢复与不确定结果 | 已实现。`frontend/src/composables/useWorkbenchSessions.ts` 的 resumeSession/refreshState 与 `useRuntimeApi.ts` 的 recover 只读历史和 Session，受 generation、分页完成与原执行状态控制，不自动重放 POST；本地索引保留恢复身份。 |
| Composer 停止与 Slash | 已实现。`frontend/src/components/ComposerBox.vue` 的主按钮在发送位置切为停止，运行中命令独立执行；`composables/useCommandComposer.ts` 和 `runtime/commands.ts` 保留标签、参数、服务端顺序和冻结调用。 |
| Header 校验与独立快照 | 已实现。`frontend/src/debugHeaders.ts` 的 validateDebugHeaders 先拒绝 CR/LF，再规范化空格/Tab；`App.vue` 的 submit/executeCommand/stop/decideTool/decidePlan/answerQuestion 六类动作独立读取开发 Header，读取与 Session 配置不携带这些自定义值。 |
| DEV 按 IP 获取 Token | 已实现，真实认证中心未联调。`frontend/dev/authMiddleware.ts` 的 createAuthMiddleware/devAuthPlugin、`dev/authCenter.ts` 与 `vite.config.ts` 已装配仅本机开发接口；`components/DebugHeaders.vue` 处理回填及迟到响应。账号密码只由开发服务读取，不编入浏览器。 |

上述起点的验证来自 [AskUserQuestion 实现记录](../06-CampusClaw计划模式/ask-user-question.md#2-基线与已观察实现)：前端 172 项、类型检查与构建通过，浏览器 18 项使用真实 Vue 与合成 HTTP 响应；实际 JAR HTTP 另外验证原执行问答/审核/任务事件闭环。前端布局用合成响应的结果不替代生产 Mate、真实认证中心或真实模型联调。

### Claw 前端交互补齐

当前实现提交为 `fcae53829c2884ea1d3cc522c183f5a125a67f45`，相对上述 `9f785bea` 仅修改前端及实施说明，仍由 Draft PR #301 交付。未新增依赖，未修改后端、公共契约或数据库。后续 `b9f51cd1` 仅校正实施说明中的事件数量与验证基线。

| 已实现交互 | 源码证据（路径相对 pi-mono-java）与验收边界 |
|---|---|
| Composer 配置 | `frontend/src/components/ModeControl.vue`、`ComposerBox.vue`、`composables/useModeMenu.ts`：常驻模式菜单，支持方向键、Enter、Escape 与焦点返回；配置仍等待权威 Session/ETag，900 px 及以下收纳模型与思考。 |
| 问答与方案卡 | `frontend/src/components/QuestionCard.vue`、`PlanCard.vue`、`runtime/planClipboard.ts`：问题可折叠，首个错误可达，接受后摘要最多三行、可展开完整权威答案；复制完整原始 Markdown，失败有反馈，不触发批准。 |
| 任务与命令结果 | `frontend/src/composables/useDockDisclosures.ts`、`components/ProgressDisclosure.vue`、`CommandResultRegion.vue` 与 `runtime.css`：分开保留折叠偏好，Slash 清单临时收起两者；新根默认展开实施任务，终态自动收起，共用区域最高 30dvh。 |
| 本地会话索引 | `frontend/src/runtime/sessionIndex.ts` 的 decodeLegacyIndex/patchMetadata/recordActivity/setPinned：v1 原序迁移到 v2；选择、恢复、改名和配置不改变活动排序，新建或接受新消息才更新；元数据补丁保留最新存储中的活动、置顶与 pending 身份。 |
| Sidebar 操作 | `frontend/src/components/AppSidebar.vue`、`composables/useSessionRename.ts`、`useRuntimeApi.ts#renameSession`：搜索本地会话、置顶和直接改名；运行中可只改名称，统一 Session POST 使用同源 ETag；412 或不确定回执保留草稿，不自动重发。 |

独立复核在该提交运行 Vitest **19 文件、189 项**、`npm run typecheck` 和生产构建，均通过；首次受限沙箱运行中的四项本地 HTTP 认证测试因监听限制未通过，允许回环监听后完整回归通过。无独立 lint script；未重跑本次未修改的 Java/数据库验证，上述 `9f785bea` 记录仍保留原提交范围。

真实 Vue 浏览器配合合成 HTTP 验证模式键盘操作、问题校验/草稿/只读答案、计划复制与批准、运行中改名、412 和丢失回执后的无重放、置顶/搜索/刷新恢复，以及 Dock 偏好恢复。1440×900 时长命令结果与任务清单共用区域实测 270 px；840 px 使用窄屏设置，390×844 无横向溢出，复制/批准/停止按钮为 44 px。最终构建复验空名称错误聚焦，无浏览器控制台异常。合成夹具只证明这些前端行为，真实认证、系统输入法候选窗和移动端软键盘仍未联调。

### 企业接入（本次范围外）

| 项目 | 已核验边界与依赖 |
|---|---|
| Mate 公共 Chat Gateway | 当前 Vue 使用内部 `/campusclaw-service/v1` 请求级 SSE。公共提交 JSON、独立 GET stream、Chat 身份和恢复需要单独适配；[Mate 待决事项 C-001/C-003/C-004/C-006/C-007](../../02-服务与接口/07-mate-service通用对话API/协作/README.md) 尚涉及分页、创建/配置及控制/计划/问答映射，不可直接复用内部字段。 |
| 附件上传 | Composer 未接真实上传。[附件服务](../../02-服务与接口/01-CampusMate附件服务/README.md) 以公共 Chat 归属并在 READY 后绑定；内部 Session ID 不能当成 chat_id，也不能用本地 fileId 模拟成功。 |
| 面向用户的 Agent 中心 | `mate-agent-definition-service@956b547f5ca12ca89e68f73012f92a4406b0c9fa` 的 `src/main/java/com/huawei/hicampus/mate/agentdefinition/controller/AgentDefinitionController.java#listAgents` 是管理用元数据列表，返回完整 systemPrompt、permission 和绑定信息。它不是已确认的用户可用 Agent 目录，也没有公共 Chat 创建链路；不能直接打开生产目录入口。 |

Mate 示例仓上述 HEAD 于 2026-09-15 与远端 HEAD 核对一致，Controller 清单只有 AgentDefinitionController 和 `agentdefinition/modelmanager/controller/LlmChatController.java`，所查源码没有公共 Chat/附件 Controller。该结论仅限此仓与提交，不证明其他企业仓库或部署不存在这些服务。本次只实现 Claw 前端，不开发 Mate 接入。后续接入需补充对应实现位置、身份与已确认契约，再进行两跳验收；现有禁用入口保留具体原因。

<a id="experience-evidence"></a>

## 6. 配置、布局与 Plan 体验核验

设计起点 `pi-mono-java-design@e179513`；实际源码 `pi-mono-java@1d08f98eb04f8ea6e01bcfbfd4008c1b638391c4`，核验日期 2026-09-15。前次验证 `fcae53829c2884ea1d3cc522c183f5a125a67f45` 的 189 项测试只证明当时场景；本次完整阅读下列文件确认新反馈涉及的源码，不把旧测试结果当作新体验验收。截图是问题证据，不能单凭截图判断部署 commit；本节以明确提交为实现分析对象。

| 用户问题 | 仓库相对路径 / 符号 | 已观察行为与目标差距 |
|---|---|---|
| 1、2：刷新重填 | `frontend/src/components/DebugHeaders.vue:12` rows/snapshot；`frontend/src/composables/useDebugAuth.ts:7` ip | 组件内存初始化，刷新丢失；按环境持久化与保存应用为 target-only。 |
| 3、4：菜单与搜索遮挡 | `frontend/src/style.css:208,274` thread-nav/thread-menu；`frontend/src/runtime.css:6,137` conversation-dock/mode-menu；`frontend/src/components/ModeControl.vue` | 绝对定位菜单处于 overflow 滚动祖先内，能够被裁切；独立浮层、边缘定位与布局占位为 target-only。截图搜索区域遮挡的具体像素触发条件未实测，纳入布局验收。 |
| 4：缺删除与菜单关闭 | `frontend/src/components/AppSidebar.vue:24,109` openMenuId/menu template；`frontend/src/App.vue:117,262` deleteConversation | 会话菜单只有改名/置顶，无外点/Esc 关闭；删除只取当前 Session 并从顶部触发。按行删除与统一菜单关闭为 target-only。 |
| 5：JSON 与字体 | `frontend/src/components/ToolActivity.vue:57,68` dl/pre；`frontend/src/projectors/runtimeEventProjector.ts:36,37` 参数 stringify/结果原文；`frontend/src/runtime.css:30` plain-result；`frontend/src/style.css:1536` tool-arguments | 输入为 12px 等宽键值布局，结果继承 UI 字体且不解析 JSON；共享安全结构 viewer 与无损原文回退为 target-only。 |
| 6：完成/等待文案 | `frontend/src/projectors/runtimeEventProjector.ts:80` session.status_idle；`frontend/src/components/ConversationTimeline.vue` hasVisibleRunningTurn | 追加“本轮已完成” notice，waiting_answer 未算可见等待会生成运行占位；共享状态文案与去重复投影为 target-only。 |
| 7：统一配置/热更新 | `frontend/.env.example`；`frontend/vite.config.ts` defineConfig；`frontend/src/components/DevDiagnostics.vue`；`frontend/src/composables/useRuntimeApi.ts` apiBase/callerId；`frontend/dev/authMiddleware.ts` createAuthMiddleware | 环境变量启动时加载，诊断入口只有创建/恢复；运行时配置服务与面板热应用无实现。九个既有键及完整边界见[工作台 §6.3～6.6](runtime-workbench-alignment.md#63-统一开发者设置与既有配置映射target-only)。未读取真实 env.local 的值。 |
| 8、9、10：问答与 Plan | `frontend/src/components/QuestionCard.vue` fieldset v-for/submit；`frontend/src/runtime/questionInteraction.ts` QuestionDraftStore；`frontend/src/projectors/runtimeEventProjector.ts:24,33` | 已实现整批回答与原执行等待，但一次渲染全部题，仅 ExitPlanMode 被专用卡吸收；逐题导航、AskUserQuestion 工具合并和提示词调整为 target-only，详见[计划证据 §9](../06-CampusClaw计划模式/source-evidence.md#9-buildplan-与逐题交互核验)。 |

固定 Codex `d58d0e5841e0de08e251673db2d5af8cf3a1ad51` 的 `codex-rs/tui/src/bottom_pane/request_user_input/mod.rs`（current_question/go_next_or_submit/submit_answers）证明 TUI 逐题、末题整批提交；Handler 仍将 JSON 答案返回模型。这是开源 TUI 证据，不冒充闭源桌面源码或像素规范。OpenCode `849c2598abc7d2b40261e74b5826bc74ffc78308` 的 `packages/opencode/src/agent/agent.ts` 与 `packages/app/src/pages/session/composer/session-question-dock.tsx` 证明 Build/Plan 与逐题状态；其输入区位置作为对照，CampusClaw 保留时间线题卡与独立 Composer。

OpenCode [Agents](https://opencode.ai/docs/agents/) 于 2026-09-15 实际核对，公开 Build/Plan 与权限模式；本设计只采用命名，不将其权限保证带入 CampusClaw 的提示词式 Plan。Vite [环境变量](https://vite.dev/guide/env-and-mode) 与 [HMR](https://vite.dev/guide/api-hmr) 同日核对。实现 `frontend/package-lock.json` 锁定 Vite 6.4.3 与 @vitejs/plugin-vue 5.2.4；读取对应安装源码的 handleHMRUpdate（env/config 触发 restartServerWithUrls）和 Vue rerender/reload 分支，支持代码热更新边界，不证明新配置服务已存在。

本次没有修改或测试产品实现、真实认证、模型遵循或 Mate 接入。新规则属于前端产品约束及配置架构变更；模型仍保留原 ToolCall/ToolResult，公共事件与运行时权限不因隐藏 JSON 改变。


<a id="mate-tool-display-evidence"></a>

## 7. CallMateTool 具体名称展示核验（2026-09-17）

设计起点 `pi-mono-java-design@2a24aaeb127910e62dd3e96c5a1ea72f5931bf4f`；实现核验使用本地 `main` 的明确快照 `pi-mono-java@21c3f59be033e7bdd5506a2d9d48baa2581bc3c7`，不是最新上游声明。下列文件按所列符号读取且与该提交无工作树差异，仅升级工具名称展示范围；此前 §6 的 `1d08f98eb04f8ea6e01bcfbfd4008c1b638391c4` 保留其他体验证据，不把旧缺口延伸到新提交。

| 仓库相对路径 / 符号 | 已观察实现 | 目标差距 |
|---|---|---|
| `frontend/src/components/ToolActivity.vue` · `BUILT_IN_TOOL_LABELS`、`toolLabel`、template | CallMateTool 固定映射为“调用业务工具”，两种标题分支只传入外层 toolName | 标题读取具体名称，复用同一展示函数；当前尚未实现 |
| `frontend/src/projectors/runtimeEventProjector.ts` · `projectRuntimeEvents`、`matchingToolResult` | 调用保留 toolName、原始 argumentValue 和格式化参数行；按 sourceEventId + toolCallId 关联结果，孤立结果有缺调用占位 | argumentValue 可提供技术名回退；还需消费新增展示名投影，关联键保持 |
| `frontend/src/types/product.ts` · `ActivityTurn`；`frontend/src/types/runtime.ts` · `RuntimeEvent` | 已有 toolName、argumentValue、status；agent.tool_call 类型没有 displayName | 展示模型保留独立 displayName；需要上游传递，不能覆盖 toolName |
| `frontend/src/components/ToolConfirmation.vue` · template | 确认标题直接显示 tool.toolName，参数来自 tool.arguments | 与活动行共用具体名称规则，授权目标和参数保持 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/CallMateTool.java` · `name`、`parameters`、`execute` | 包装器名为 CallMateTool；tool 是 Exact Mate tool name；execute 以该名称解析 ID，再传 args 执行 | 已有技术名称来源；displayName 仍须从服务端元数据传递 |

新增元数据核对（同一实现提交，2026-09-17）：

| 仓库相对路径 / 符号 | 已观察实现与缺口 |
|---|---|
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/dto/ToolInfo.java` · displayName / JsonNaming | 元数据 DTO 已有 displayName，SNAKE_CASE 将网关 display_name 映射到该属性；字段存在不证明每个工具实际都有值 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/HttpMateToolClient.java` · queryToolMetaByIds / toMeta | 查询反序列化为 ToolInfo，再构造 MateToolMeta；toMeta 未读取 getDisplayName |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/mate/MateToolMeta.java` · record | 有 toolId/toolName/description/schema/permission 等字段，无 displayName |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/MateToolSessionCache.java` · toNameIndex / CacheState | 保存 name-to-ID 索引，没有展示名称快照 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/MateToolDiscovery.java` · listAgentTools / listSkillTools / resolveToolId | 发现写入 Session 缓存，执行按名解析 ID；当前返回 ID 的路径不足以同时提供展示名称 |

同时读取 `frontend/src/components/structuredActivity.test.ts`：已有结构 viewer 与结果文本块测试，未运行本次产品测试。标题优先 displayName 是[已确认目标](README.md#mate-tool-display)，元数据保留、调用名称快照、事件传递及前端消费尚未接通；不能表述为只改 UI 即可完成。

工具名称专项已扩展为普通框架 label 和业务元数据统一映射 displayName；新增事件 factory、持久化投影与严格前端解码器证据，以及 pi/Claude 最新核对见[M03 专项证据](../02-CampusClaw工具系统/source-evidence.md#tool-display-evidence)。M03/M06 和 Mate 公共精确契约已补齐此目标；传递和 UI 消费仍待实现。其他历史证据不升级。没有修改实现仓或验证部署页面，未新增依赖；现有前端类关系与 PlantUML 图源不变。

验证（2026-09-17）：Markdown 无 Mermaid、PlantUML ASCII、SVG XML、图源与 SVG 引用及行锚点、新标题链接均通过检查；前端专题隔离执行 `plantuml -tsvg diagram.puml`，8 张生成 SVG 与在库文件逐字节一致。图源与生成图无变更，未重做视觉验收；`git diff --check` 通过，未运行产品测试。
