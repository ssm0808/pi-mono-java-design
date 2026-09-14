# 前端体验源码与视觉证据

[返回前端主设计](README.md)

版本：1.1.0；更新日期：2026-09-15。初次整理基线为设计仓 `6026ba48`，计划前端增补基线为 `42243077`。本文件保存按日期和源码版本隔离的核验资料，结论只适用于标明的 commit 或安装包；当前设计以主设计为准，工作台与公共接入差距由各专项维护。

| 证据 | 基线 |
|---|---|
| 本次对齐基线 | 设计仓 `2ee2a3211da68ad87b0d9cab353e691b00bdaebd`；Mate Events 1.5.0、内部 Events B01～B15 与 Thinking 展示规则 |
| 本次前端源码复核 | `pi-mono-java@510d882ca45541e0086586dab89c429c5a18cf20`；`sessionIndex.upsert` 的前插行为使点选会话自动到顶部，直接 Name Controller 路由缺失；详见 [工作台专项](runtime-workbench-alignment.md) |
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

## 3. 计划模式前端核验（2026-09-15）

前端设计基线 `pi-mono-java-design@42243077d8605024a5d4470867525879b0d1a088`；Java 核验 `origin/main@29ebec6a8cad99896414211cda28c6fffec71bee`。旧前端基线 `510d882ca45541e0086586dab89c429c5a18cf20` 仅保留原范围。全量读取本次涉及的 App、ComposerBox、ConversationTimeline、runtime/product 类型、eventStore、runtimeEventProjector、useRuntimeApi；后端读取 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeSessionController.java`，create/get/delete 尚无通用 update。该范围尚无计划类型与 UI，不证明其他特性分支或部署不支持计划模式。

Codex 固定源码仍为 `d58d0e5841e0de08e251673db2d5af8cf3a1ad51`，通过 git show 读取，未使用工作树 HEAD `be33f80b` 替换。完整读取 `codex-rs/tui/src/chatwidget/plan_implementation.rs`、`codex-rs/core/src/tools/handlers/plan.rs`、`codex-rs/protocol/src/plan_tool.rs`，定向读取 `codex-rs/app-server/README.md` 的 plan/Item/提问协议段。符号与结论见[计划交互 §1](plan-interaction.md#1-源码与交互依据)。前者证明 TUI 的实施选择，不能当作桌面前端源码；具体卡片尺寸与位置是 CampusClaw 目标设计。

官方 [Features](https://learn.chatgpt.com/docs/features) 与 [App Server](https://learn.chatgpt.com/docs/app-server) 于 2026-09-15 重新核对。前者显示侧栏与 Add/Plan mode；后者区分方案 Item、delta、任务更新与提问。当前公开文档与固定源码可能不同，分别使用，不升级固定 commit，也不推断服务端存储。
