# CampusClaw 产品前端体验设计

| 属性 | 值 |
|---|---|
| 文档版本 | 1.9.0 |
| 状态 | target-only 产品设计；主对话、确认、停止与恢复已按当前契约补齐；公共映射和生产身份集成完成前使用 Mock Gateway |
| 界面评审状态 | 沿用 O1 与浅暖灰；保留首次进入、常规和运行稳定键，增加工具确认、停止处理中、提交不确定、历史恢复与配置冲突样例；视觉验收独立于契约确认 |
| 主设计依据 | [`README.md`](README.md)，维护源码证据、目标差异、设计理由、状态与 Design Token |
| 人类评审界面 | [`frontend-review.html`](frontend-review.html)，集中展示低保真、高保真和待确认项 |
| 品牌标识资产 | [`campusclaw-mark-o1.png`](campusclaw-mark-o1.png)，原始透明 PNG；界面直接引用，不通过生成模型重绘，也不缩进深色品牌方块 |
| 图源 | [`diagram.puml`](diagram.puml)，含产品边界、全局目标组件类图、事件投影与状态流 |
| 本次对齐基线 | 设计仓 `2ee2a3211da68ad87b0d9cab353e691b00bdaebd`；Mate Events 1.5.0、内部 Events B01～B15 与 Thinking 展示规则 |
| 本次前端源码复核 | `pi-mono-java@dfb90cac4e233e09a0b8f047f7e9f4682f5ad238`；范围及符号见 [本次证据与差距](public-chat-alignment.md#2-源码证据与差距)；以下早期基线不代表当前实现 |
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
| 本次 Header 交互复核 | 设计仓 `9b8c5b79eea1d77e42da4b8c73c4b8e572be1d45`；实现仓 `pi-mono-java@4cc8dd86f601417c22cf9306e52152acbb59bb60`；仅复核 `frontend/src/components/DebugHeaders.vue` 和 `frontend/src/debugHeaders.ts`，见 6.1；不升级其余 Runtime/公共契约证据 |
| Postman 核对 | 2026-08-28；核对官方 Headers 编辑文档、`Agent Runtime` collection 及真实 SSE 响应 |
| 更新日期 | 2026-09-09 |

2026-09-08 对齐说明：当前交互以[公共对话对齐专项](public-chat-alignment.md)与本页现行规则为准。
独立 abort、steers、follow-ups 已退役；本期没有消息队列。产品浏览器仍使用 Mate 公共契约，
不能照搬 Claw 的 POST SSE、数字页码、sourceEventId/targetEventId 或工具文本块。
旧运行态 PNG 不再作为当前交互稿；当前 HTML 已移除旧跟进控件。

Thinking 展示模型返回的原始推理，规则与局部源码依据见[Thinking 展示](../01-CampusClaw多Agent运行时/chat-events-history-design.md#thinking-original-text)。

## 1. 结论

CampusClaw 前端应从“把 HTTP/SSE operation 摊在页面上的本地调试台”改为面向任务的
Agent 工作台。主界面只暴露用户能够理解并需要决策的概念：Agent、会话、消息、附件、
模型、深度思考、执行状态与执行中控制。当前实现是内部调试工作台：已有开发态 Headers，
只在初始消息提交时使用临时快照；没有生产凭据仓库或已落地的公共 Chat Gateway。
本次复核不能继续将“没有任何 Header 输入”或“尚无富文本”描述为当前实现。
产品路由仍保持浏览器凭据无持有，`Service URL`、`session_id`、ETag、原始 JSON 和 SSE frame
也不进入产品主流程。为了快速验证 Runtime 到 Mate Tool execute 的凭据传递，
内部开发构建已实现隔离的 `debugHeaders` 抽屉；它不进入产品构建、不持久化秘密，且只对
`POST /sessions/{sessionId}/events` 构造请求级 Header 快照。抽屉采用 Postman 风格的通用
Key/Value 表格；按 2026-09-09 用户反馈预置三个可编辑、可删除的常用名称，不限定其他 Header 或凭据模式；浏览器禁止设置的名称与无效值只在对应行报错。
编辑器作为独立的 `Headers` 面板，不与现有“开发者诊断入口”合并；它只复用该入口的折叠面板、虚线边框、暖灰表面、紧凑字号和次级按钮，
不引入独立的凭据卡片或认证视觉。

本轮提出一个桌面优先的单工作区方案：左侧会话导航、中央对话、顶部 Session 能力、
底部 Composer。思考和工具调用按实际时间顺序组成对话内 Agent 活动流；每次工具调用合并为
一条紧凑 activity disclosure，并在安全投影后显示调用入参。展开详情始终按
“输入参数 → 输出结果”纵向排列，不做左右分栏。运行中只允许停止并保留新消息草稿；
停止完成后再提交新消息，不展示加入队列或运行中注入模式。内部诊断不进入产品首页。

Composer 中的 Slash Command 独立保存命令草稿；通过首字符 `/` 或“+ → 命令”打开精简清单，选择后收成可删除标签；
参数单独编辑，统一上箭头显式提交。清单保持服务端顺序，选择后仍需明确运行，
Builtin 结果作为当前页面临时区域而不是对话消息；Skill 在内部新契约中触发普通消息执行，
公共执行映射确认后复用对话、确认与恢复流程。完整交互、组件和协议门禁由
[Slash Command 前端专项](../../04-命令与技能/00-Slash-Command通用模块/前端设计/README.md)维护，
本专题只保留整体工作区和视觉基线。

Assistant 正文以原始 Markdown 文本为权威，经过受限语法解析和固定 Vue 组件投影为安全
富文本；表格、列表、引用、链接、行内代码和代码块均有明确样式、溢出和复制行为。用户
原文、Thinking 原文、工具入参和工具原始结果不进入该 Markdown 渲染链。思考区域以纯文本
展示模型返回的可读原始推理，保留文字和换行；经类型化事件与公共 bridge 投影。具体规则见[Thinking 展示](../01-CampusClaw多Agent运行时/chat-events-history-design.md#thinking-original-text)。

布局层级与工具密度继续采用 Codex-inspired 而非品牌复制；品牌层改用已确认的 O1 五片有机
标识，界面直接引用同一张透明 PNG，不允许生成式重绘。配色由冷灰调整为暖白、暖灰与深暖黑，
O1 珊瑚色只承担品牌识别，运行和完成状态仍使用语义绿色，不使用 OpenAI/Codex 商标或标志。

## 2. 设计权威顺序与 HTTP 风格对齐

本专题沿用 Runtime HTTP 设计的“设计依据与人类评审面分离”方式，但不引入没有实际
消费方的 UI JSON Schema：

1. 本文件与引用的专项分工维护设计依据，维护源码证据、目标设计、设计理由、状态机、视觉
   Token 和验收规则；
2. [`frontend-review.html`](frontend-review.html) 是主要人类评审界面，按稳定
   `screenKey` 展示三个界面状态、评审材料与待确认项；
3. [`diagram.puml`](diagram.puml) 是架构图唯一图源，SVG 只由 PlantUML 生成；
4. 低保真 HTML 是可编辑布局源，PNG 是其评审快照；高保真 PNG 是视觉方向稿，不是
   可直接切图的实现资产。

| 对齐项 | HTTP 设计方式 | 前端设计采用方式 |
|---|---|---|
| 文档入口 | 顶部属性表记录版本、状态、权威源和基线 | 采用相同属性表，并显式记录三个 `screenKey` 的评审状态 |
| 人类评审 | 独立 HTML 按 `operationKey` 展示 operation | 独立 HTML 按 `screenKey` 展示 first-use、idle、running |
| 视觉语言 | HTTP 评审页使用中性表面、细边框和蓝色选择态 | 文档评审面保持同一结构；产品稿保留 Codex-inspired 工具层级，改用 O1 品牌标识、暖中性表面和深陶土色焦点/链接 |
| 证据表达 | 区分观察行为、产品约束、安全加固和架构变化 | 保持相同分类，不把高保真目标误写为现有实现 |
| 机器契约 | JSON 是字段级精确契约源 | 不新增目标不明确的 UI JSON；这是产品设计制品差异 |

## 3. 源码与契约证据

### 3.1 早期已观察行为（历史证据，不作本次实现现状）

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

### 3.2 早期已评审特性分支实现（历史证据）

| 证据 | 已评审行为 |
|---|---|
| `pi-mono-java@d03c08db` 的 `RuntimeRequestContext.mateCredentials:45-50`、`MateCredentialHeaders:13-23` | 提交消息时精确读取 `X-HW-ID`、`X-HW-APPKEY`、`Authorization`、`access-token` 四个 Header。 |
| `MateCredentials:21-86` | 凭据是不可变执行快照；完整性要求 `X-HW-ID` + `access-token` + 至少一种 APPKEY/JWT，诊断字符串只记录是否存在。 |
| `HttpMateToolClient:95-180, 298-370`、`MateToolDiscovery` | Agent、Skill 和 Tool metadata 发现方法不再接受凭据参数；只有 Tool execute 检查完整性并附加四项快照。 |
| `HttpMateToolClientTest:270-400, 476-483` | 回归测试覆盖发现无凭据、JWT、APPKEY、双凭据、缺少 `access-token` fail closed 和脱敏 `toString`。 |

上表保留当时的评审记录，不用于判断该 PR 当前状态。本次前端实现现状以
[dfb90ca 源码证据](public-chat-alignment.md#2-源码证据与差距)为准。

### 3.3 已确认契约约束

- 每个 Session 同一时刻最多有一个 active execution。
- Mate 提交、实时流与历史读取分离；Claw 内部 POST 为请求级 SSE，两者独立维护。
- 公共 `agent.message/agent.thinking` 通过 `phase` 区分预览与完整记录；`eventId` 用于去重，完整记录覆盖预览。
- 内部 B05 已确认关闭 thinking 不隐藏此前思考原文；产品不通过删除历史思考原文来表现开关状态，仍遵循授权和保留策略。
- Model 与 Thinking 只允许在 Session `idle` 时修改，并通过强 ETag 防止覆盖并发修改。
- 本期不接受 running 时的新消息或排队；user.interrupt 回执不等于目标实际停止。
- 消息请求使用 `event.content[]`；公共文本最多 2048 Unicode code point、附件最多 4 个。上传与预览由独立附件资源负责。
- 精确 Runtime 设计明确要求浏览器/UI 经 mate-service 调用，内部 SSE 不能字节透明转发。
- 产品不收集原始凭据；宿主身份集成必须单独验证。开发态 Headers 不成为生产登录方案。

### 3.4 目标设计与分类

| 目标差异 | 分类 | 理由 |
|---|---|---|
| 产品主界面不再直接调用内部 Runtime V1 | 架构变化 | 当前直接适配器没有生产认证能力；浏览器还需要稳定的公共 Chat/Agent 资源，而不是内部 Session 标识。 |
| 保持产品路由凭据无持有 | 产品约束 + 安全加固 | 统一登录和公共 bridge 仍承担生产身份；产品 Chat 页不新增 JWT/APPKEY/`access-token` 表单、构建配置、存储或 Header 注入。 |
| 保留已有 `debugHeaders` 内部诊断抽屉 | 架构隔离 + 安全加固 | 快速验证内部 Runtime 凭据透传，但只在 `import.meta.env.DEV` 或独立诊断构建中可达；用户关闭页签或刷新即清除。 |
| 调试 Header 使用通用 Key/Value 表格与可删除预置 | 产品约束（target-only 交互调整） | 预置三个常用名称减少重复输入，保留任意 Key/Value；每行独立启停、删除，仅点击“增加请求头”才追加空行，避免输入过程中不断产生多余行。 |
| 独立 `Headers` 面板复用原开发者诊断入口视觉 | 产品约束（target-only） | Header 配置与 Agent/Session 诊断职责分离，但沿用已熟悉的虚线边界、暖灰表面和次级控件，保持内部工具一致，也避免将通用 Header 误表达成凭据管理卡片。 |
| 浏览器受限名称与格式使用行内校验 | 安全加固 | UI 不预设可选 Header，但 `Host`、`Content-Length`、`Cookie`、`Origin`、`Sec-*`、`Proxy-*` 等 Fetch 禁止名称不能发送；无效 token、换行值和大小写不敏感的重复名称在对应行阻止提交。 |
| 自动生成 Header 不展示，手工值优先 | 产品约束 | 请求适配器生成的 Header 不渲染、不枚举；开发者显式填写同名 Header 时在请求合并阶段采用手工值，但 UI 不显示自动值或覆盖状态。 |
| 现有 Header 编辑器仅覆盖初始消息 | 安全加固 + 架构变化 | 这是旧调试适配器范围；新内部控制请求也有独立 Header 要求，不能原样复用旧白名单。生产不暴露编辑器。 |
| 生产认证由 mate-service / 网关边界完成 | Target-only architecture | 浏览器身份、登录态、授权与审计不由 Chat 页面收集原始凭据；具体会话承载和刷新机制必须在公共 API 评审时确认，不能从当前直接适配器推断。 |
| 隐藏 ETag、原始 SSE 与内部错误 | 安全加固 | 降低内部实现泄漏和错误信息越界风险；凭据不是产品“隐藏字段”，只有内部诊断构建存在明确例外。 |
| 停止与后续新消息 | 产品约束 | 停止走 user.interrupt；实际停止后新提交，不承诺原生 Steer 或 FollowUp。 |
| 运行中保留草稿 | 产品约束 | 不发送第二条用户消息，不展示队列或跟进模式切换。 |
| 将工具事件合并为紧凑 activity disclosure | 产品约束 | 保留执行透明度，同时避免 started/completed/result 三段协议噪音；执行中默认展开，完成后折叠。 |
| 工具详情按“输入参数 → 输出结果”纵向排列 | 产品约束 | Codex 的详情区是缩进的纵向流；左右分栏会把两个不同阅读阶段误导为并列比较，并压缩长参数和长结果。 |
| 思考 disclosure 与工具 activity 按事件顺序组成 Agent 活动流 | 产品约束 | 让用户在一个连续区域内理解当前做什么和调用了什么，又不把思考原文混入工具 payload。 |
| 产品思考区展示模型返回的原始推理 | 产品约束 | 直接查看模型本次返回的思考内容。 |
| 公共 bridge 保留 `agent.thinking.content` 原文 | 架构变更 | 保留协议和身份投影，内容按原文传递；前端标题使用状态文案。 |
| 工具 activity 展示经安全投影的调用入参 | 产品约束 + 安全加固 | 入参能解释 Agent 的实际动作；浏览器只接收经 bridge 脱敏、截断和用户资源映射后的结构，不暴露密钥、内部 ID 或绝对路径。 |
| 从独立 `agent.tool_call` 读取参数，按 `toolCallId` 合并确认和结果 | 架构变化 | 新公共事件已显式提供调用；产品不再依赖 Assistant 内嵌 ToolCallSpec 或旧工具进度事件。 |
| Assistant 正文使用安全 Markdown 富文本 | 产品约束 | 模型天然会输出表格、代码、列表和强调；纯文本会把结构标记直接暴露给用户。 |
| 禁止原始 HTML、Markdown 图片和任意协议链接 | 安全加固 | 模型输出和外部内容均不可信；避免 XSS、跟踪像素、应用内路由欺骗与危险协议跳转。 |
| 流式与历史消息共用同一 Markdown 源和渲染器 | 架构变化 | 保证 delta 预览、completed 替换与刷新恢复后的视觉结果一致。 |
| 保留独立开发者诊断入口 | 架构变化 | 保留接口联调效率，但与面向用户的路由、权限和构建产物隔离。 |
| 采用 Codex-inspired 而非复制 Codex 品牌 | 产品约束 | 复用工具型工作台的层级和密度，不使用 OpenAI/Codex 商标，也不声称存在官方公开 Token。 |
| 使用原始 O1 透明 PNG 和浅暖灰表面 | 产品约束 | 当前调试实现已有同一品牌资产；保留形状、比例和颜色，新增确认与恢复区域不改变品牌或导航风格。 |

### 3.5 本次源码、契约与实施边界

详见[公共对话对齐专项](public-chat-alignment.md)。它唯一维护本轮源码差距、两跳对照、
消息/确认/中断/恢复状态机、配置与 Slash 一致性及验收用例；本文件维护整体体验和视觉。
本轮未修改实现仓、Mate 精确契约或 Runtime 内核，不升级已有 pi/Codex 历史证据。

## 4. 用户、目标与非目标

### 4.1 目标用户

- 主要用户：选择受管 Agent 完成校园运营、教学、运维或分析任务的业务人员。
- 次要用户：需要查看 Agent 活动与失败原因的支持人员。
- 开发者：只在内部诊断入口中查看 Runtime IDs、原始事件和请求信息，并可为提交消息配置临时 Header。

### 4.2 本轮目标

- 确认桌面端信息架构与三个关键状态。
- 确认产品化执行控制、工具活动呈现与断线恢复文案。
- 确认思考内容与工具调用的同区时序展示，以及工具入参的投影、脱敏、展开和降级规则。
- 确认视觉方向、基础尺寸和色彩语义。
- 确认 Assistant 富文本语法、流式稳定性、安全边界和响应式溢出规则。
- 评审内部 `debugHeaders` 的通用 Key/Value 表格、仅内存生命周期和请求级透传范围。
- 明确当前内部十项目标接口与旧调试实现的差距，以及生产前端仍需补齐的公共映射。

### 4.3 非目标

- 本轮不实现 Vue 组件、不替换现有调试客户端。
- 本轮不设计 mate-service 公共 API 的精确路径和 VO。
- 本轮不承诺移动端完整功能等价；只定义响应式降级原则。
- 高保真 PNG 是视觉方向，不是可直接切图交付的组件资产。

## 5. 产品边界

![CampusClaw 产品前端边界](frontend_product_boundary.svg)

[PlantUML 源码：`frontend_product_boundary`](diagram.puml#L1)

生产链路必须是：浏览器调用 mate-service 公共 HTTP/SSE，mate-service 完成认证、授权、
`chat_id` 与内部 `session_id` 映射、错误脱敏和 Event 投影，再调用 CampusClaw Runtime。
当前仓库的直接 Runtime client 只能作为本地诊断基线，不能被描述为已满足生产安全边界。
该 client 的临时 Headers 仅是内部开发能力；公共链路的身份建立不得通过给
CampusClaw 页面增加凭据表单或把秘密写入 `VITE_*` 来补齐。

![开发者调试 Header 请求链路](frontend_debug_header_flow.svg)

[PlantUML 源码：`frontend_debug_header_flow`](diagram.puml#L44) · [原尺寸](frontend_debug_header_flow.svg)

调试 Header 是上图生产边界之外的内部例外：开发者在通用 Key/Value 表格中填写的启用项只在
当前页面内存中存活，提交时快照并仅附加到初始 `POST /events`。这不是生产登录机制，也不能
证明 Runtime 已验证凭据；编辑器不会根据 Key 猜测凭据类型或自动建立认证模式。

## 6. 信息架构与界面状态

三个界面状态使用与 HTTP `operationKey` 相同的稳定评审键。中文名称用于评审沟通，
`screenKey` 用于设计、组件 Story、视觉回归和测试名称，不随文案调整而改变。

| 中文简称 | screenKey | 当前状态 | 主要评审材料 | 依赖边界 |
|---|---|---|---|---|
| 首次进入 | `firstUse` | 待确认 | 低保真评审板 | Agent 目录和公共 Chat 创建属于 mate-service 目标态 |
| 常规对话 | `idleConversation` | 待确认 | 低保真 + 高保真常规态 | 复用已确认 Session/Event 能力，经公共 bridge 投影 |
| 执行中及恢复 | `runningConversation` | 新交互已补齐；待浏览器布局验收 | 可操作 HTML + 专项状态图 | 停止与草稿，不暴露内部 operation 名称；本期无队列 |

| 区域 | 主要内容 | 用户动作 | 默认隐藏内容 |
|---|---|---|---|
| 左侧导航 | 新建会话、最近会话、Agent 中心、设置 | 创建、切换、搜索会话 | `session_id`、接口地址 |
| 顶部栏 | Agent 名称、自动保存、模型、深度思考、粗粒度状态 | 切换 idle Session 的模型/思考；运行时停止 | ETag、资源版本；产品构建不提供凭据入口 |
| 对话画布 | User turn、Agent 活动流（思考 disclosure + 工具 activity + 安全入参）、Assistant 安全富文本、附件、错误恢复提示 | 阅读、选择文本、打开安全链接、复制正文/代码、展开思考或工具详情 | SSE frame、瞬时 Entry ID、原始未脱敏入参、可执行 HTML |
| Composer | 附件、普通消息、Slash 命令入口；运行中保留消息草稿 | 发送新消息、打开命令清单、显式运行当前可用命令；运行中可停止 | operation path、内部请求体 |
| 开发者诊断 | 请求摘要、原始事件、内部标识、临时 Header | 创建/恢复 Session，以通用 Key/Value 行配置下一次消息提交的 Header | 仅内部构建可见；值只在页面内存中，诊断摘要只显示 Key 和“已配置/未配置” |

### 6.1 开发者调试 Header（现有诊断入口，行编辑调整为 target-only）

2026-09-09 用户确认：移除截图中的常驻说明，预置三个可删除请求头，并以明确按钮增加空行。
这是本专题的产品交互约束，替代 1.0.0 的自动空白尾行规则；本次只更新设计文档与 HTML 原型，Vue 实现待同步。

| 源码证据（`pi-mono-java@4cc8dd86f601417c22cf9306e52152acbb59bb60`） | 已观察行为 | 目标与理由 |
|---|---|---|
| `frontend/src/components/DebugHeaders.vue` · `rows`、`ensureTrailingRow`、`deleteRow`、`clearRows`、template | 初始一条空行；输入时自动补尾行；删除或清空后仍保留空行；表格上方有截图中的请求范围和内存说明 | 默认三个名称；显式增行、允许删至零行；移除面板常驻说明，减少干扰和无操作新增 |
| `frontend/src/debugHeaders.ts` · `validateDebugHeaders`、`validateHeaderValue` | 启用行必须同时有 Key/Value；全空行忽略；校验名称、重复与值并生成 Headers | 保留一般行校验；仅未使用的预置行（仍为原始 Key 且 Value 为空）也忽略，避免首次打开即报错或把三个名称误当必填凭据 |

其余章节中的 dfb90ca 和更早源码记录仍是各自范围的历史基线，本次不据上述两个组件文件推断新的传输实现。

`debugHeaders` 使用顶部工具图标打开右侧抽屉，且在首次进入、已建 Session 和执行中都可查看
当前配置。抽屉内是独立的 `Headers` 面板，不显示“开发者诊断入口”名称，也不包含 Agent ID、Session ID、创建或恢复操作。
该入口只存在于内部开发构建；生产构建不渲染图标、抽屉、状态 store 或凭据文案。

`Headers` 面板的样式直接继承现有 `.dev-diagnostics` 视觉：使用可折叠 summary、暖灰次级表面、1 px 虚线边界、
12 px 诊断文字、38 px 输入/按钮和 8 px 控件圆角。面板 summary 只命名为 `Headers` 并显示启用计数，不另加实线卡片顶栏、凭据模式或主动作按钮。

| 表格元素 | 行为 |
|---|---|
| 默认行 | 按顺序预置 `access-token`、`X-HW-ID`、`Authorization`，Value 均为空；三行默认勾选，均可编辑、关闭和删除，不填充示例秘密或历史值。 |
| 启用 | 每行独立开关；关闭后保留 Key/Value，但不进入下一次请求快照和启用计数。 |
| Key | 普通文本输入，不提供固定下拉选项或认证模式；比较、重复校验和请求合并均大小写不敏感。 |
| Value | 普通文本输入，不自动拼接 `Bearer`、替换变量或根据 Key 推断秘密类型。 |
| 增加请求头 | 每点击一次，在末尾追加一行空 Key/Value，默认勾选并聚焦新行 Key；即使已有空行，也只按本次点击增加一行。 |
| 删除 | 只删除当前行，不补行、不恢复预置；可以删至零行。焦点移到相邻行 Key，无剩余行时移到“增加请求头”。 |
| 全部清空 | 删除所有行及内存值，保持零行并聚焦“增加请求头”；不自动恢复三项预置。 |
| `Headers (n)` | `n` 只统计启用、完整且通过校验的自定义 Header。 |

- 首屏只显示三个预置行，不附加空白尾行。填写、切换启用和删除都不增加行；关闭再打开面板保留当前行，只有页面重新初始化才恢复三个空值预置。
- 面板移除“仅当前页面内存；分别附加到消息、命令、停止或确认 POST。读取请求不携带这些临时凭据。协议头由客户端固定。”等常驻说明；只保留标题/计数、操作、表格和必要的行内错误。请求范围和内存生命周期继续在设计说明维护。
- 请求适配器自动生成的 Header 不渲染、不枚举，也不显示覆盖状态；开发者填写同名 Key 时仍在请求合并阶段采用手工值。
- 未使用的预置行（仍为原始 Key 且 Value 为空）与全空行忽略：不报错、不计数、不发送空值 Header。预置 Key 被改写后按普通行处理；其余启用行的 Key 和 Value 必须同时填写，名称必须是合法 HTTP token，Value 不得含 CR/LF，同名自定义 Key 不得重复。
- UI 允许自由输入，但 Fetch 禁止的请求头名称在对应行显示“浏览器禁止设置这个 Header”并阻止提交；不通过常驻说明或固定可选列表限制用户。
- Header 修改即时写入当前页面内存，不提供“应用”“保存凭据”“从 URL 导入”“复制完整 curl”或“显示原始请求”。“全部清空”覆写内存和输入；关闭抽屉保留，刷新、关闭页签或切换 API base 清除。
- 页面不保存或回显历史值，日志、遥测、错误和复制摘要只能记录 Header Key 与是否已配置；浏览器 DOM 和 DevTools 仍可观察当前输入与线上请求，因此该能力只存在于受控开发构建。
- 任一启用行校验失败时保留 Composer 草稿并聚焦第一条错误，不发起网络请求。服务端仍按自身契约决定凭据完整性、认证和授权结果。

### 6.2 当前可编辑原型

[低保真布局](low-fidelity.html)已移除运行中跟进控件，保留常规、首次进入、运行，并补充确认与恢复。
[主对话交互评审](frontend-review.html#conversation-workbench)提供消息、等待确认、停止、断线和配置冲突状态。
HTML 是本轮可编辑交互源，不再把旧 PNG 标成它的同步快照。

### 6.3 常规视觉基线

[原尺寸常规视觉稿 v8](high-fidelity-conversation-v8.png)只用于对照 O1、浅暖灰表面、
开放式正文和纵向详情，不定义当前接口、状态或能力。

### 6.4 旧运行稿归档

[历史运行视觉稿 v8](high-fidelity-running-v8.png)与[历史低保真快照](low-fidelity.png)
包含已退役控制，仅作存档链接，不在当前评审面直接展示，也不作为本轮视觉验收结果。

### 6.5 Slash Command 专项

Slash Command 不新增页面路由，在同一 Composer 中使用可删除命令标签与参数编辑。取消独立 `/` 按钮和可见模式栏，
通过“+ → 命令”或空草稿首字符 `/` 打开只含规范名称与一句说明的清单；统一上箭头提交，取消恢复消息草稿。命令清单、参数编辑、
running 状态清单、Help 临时结果和未匹配错误的评审面见
[Slash Command 交互评审稿](../../04-命令与技能/00-Slash-Command通用模块/前端设计/slash-command-review.html)。
专项中的组件、Store 和 Mate Gateway 均为 target-only；现有内部调试台尚未实现这些对象。

## 7. 关键状态与交互

### 7.1 首次进入

从公共 Agent 目录选择能力后创建 Chat；目录、Chat 列表和身份集成仍需独立接口确认。
加载、空目录、无权限、创建失败分别展示；失败保留选择，不自动重复创建有副作用资源。
不可用 Agent 不建立虚假的 Session。产品不提供凭据表单。

### 7.2 Idle 对话

Composer 使用有序 text/file 内容块；最多 2048 Unicode code point 和 4 个附件，
附件上传完成后才能发送。发送时冻结草稿；只在完整回执确认后清除对应旧草稿。
模型与 thinking 的完整资源和并发版本统一管理，失败不覆盖实际配置。
删除会话仍位于会话菜单并二次确认；执行中不自动中断或删除，先提示停止。
公共删除能力未绑定时不可仅凭内部 Session 接口开启产品删除。

### 7.3 Running 对话

只保留新消息草稿和停止操作，不提供队列、模式切换或反转快捷键。
停止请求的接受与目标实际终止分开显示；等待工具确认也不能发送第二条消息。
确认卡提供允许、拒绝及可选拒绝原因；回执不代表工具执行成功。
精确控制目标是公共接入门禁，不能把内部 targetEventId 悄悄加入公共请求。

### 7.4 断线与恢复

连接断开不等于执行结束；显示“执行可能仍在继续”或“提交结果不确定”。
恢复只重开公共读流并查询历史，不重发消息、确认或中断。保持已确认内容和草稿；
末页、空页和旧 idle 不能作为当前可发送的凭据。权限撤销时清空受影响内容。

### 7.5 内部诊断范围

保留通用 Headers 的独立暖灰折叠面板与内存快照。现有实现只覆盖初始消息；它不是
新 Events 三输入与 Skill 的完整请求适配器。新内部接口的 Header、目标、流及生命周期
按各 operation 单独实现，不因为同一路径就覆盖原执行凭据。生产构建不装配此面板。

上述状态、原型操作、请求快照、两跳差异和反例统一见
[公共对话对齐专项](public-chat-alignment.md#4-状态与交互)。

## 8. 公共 Event 到 UI 的投影

![公共事件到产品 UI 投影](runtime_event_ui_projection.svg)

[PlantUML 源码：`runtime_event_ui_projection`](diagram.puml#L212) · [原尺寸](runtime_event_ui_projection.svg)

当前产品使用 `agent.message/thinking/tool_call/tool_result` 与 `chat.status_idle`。
POST 回执、实时流和历史进入同一 EventReducer；不使用旧 `assistant.*`、`entryId`、
`tool.execution.*` 或 `stream.end/error` 作为产品协议。
工具参数从独立调用读取，按 toolCallId 合并确认与结果；事件自身仍按 eventId 去重。

[事件与安全展示](public-chat-alignment.md#5-事件正文与工具显示)维护字段级映射；
[恢复规则](public-chat-alignment.md#6-历史与断线恢复)维护三来源合并与分页。
活动区继续采用紧凑 disclosure，参数在上、输出在下，Thinking 原文独立纯文本展示，内部工具参数不进入产品浏览器。

## 9. Assistant 富文本设计

### 9.1 内容与信任边界

富文本只是一种前端显示投影，不改变公共 Chat 消息格式。公共 bridge
必须保留已确认的 `agent.message.content` 正文，不得预先转换为 HTML；前端始终保留
`rawMarkdown`，渲染失败时可安全回退并支持复制原文。

| 内容面 | 首版显示方式 | 设计理由 |
|---|---|---|
| Assistant 正文 | 受限 Markdown → 语义 AST → 固定 Vue 组件 | 解决表格、列表、代码和强调的可读性，同时不信任模型生成 HTML。 |
| User 正文 | 纯文本 `pre-wrap` | 忠实显示用户实际提交内容，避免把用户输入伪装成系统 UI 或可点击动作。 |
| Thinking | Agent 活动流内的原始推理 disclosure | 原样展示公共 content，标明“原始推理”，保留换行；标题使用前端状态文案，完成后折叠为“分析过程”。 |
| Tool arguments | 安全 JSON/key-value viewer | 解释工具实际输入；只渲染 bridge 脱敏和预算后的结构，不激活链接、HTML 或应用动作。 |
| Tool result | 公共 content 字符串按纯文本展示 | 工具内容来自外部系统；不得自动继承 Assistant Markdown 权限。 |
| Error / recovery | 纯文本产品文案 | 错误面不接受模型或下游返回的富文本，避免错误注入。 |

### 9.2 支持语法与降级

| Markdown 输入 | 首版渲染 | 交互与降级规则 |
|---|---|---|
| 段落、软/硬换行 | `<p>` 与受控换行 | 连续段落保持 12 px 节奏，不复用源文本中的任意 HTML。 |
| 标题 | 消息内 `h2`–`h4` 视觉层级 | `h1` 下调为消息内 `h2`；超出层级统一钳制，不能覆盖页面主标题语义。 |
| 有序/无序/任务列表 | `ol`、`ul`、只读 task item | checkbox 不可交互，避免让模型输出伪操作状态。 |
| 强调、粗体、删除线 | `em`、`strong`、`del` | 保持正文颜色，不用大面积状态色。 |
| 引用、分隔线 | `blockquote`、`hr` | 引用用左边线和次要文字，不伪装为系统警告。 |
| 行内代码 | `code` chip | 等宽字体；可随正文选择复制。 |
| fenced code block | 代码容器 | 显示语言标签和“复制代码”；复制内容不含 fence，长行容器横向滚动。 |
| GFM table | 语义 `table` 外包横向滚动容器 | 保留表头；数字默认不自动推断含义，仅按 Markdown 对齐标记对齐。 |
| 安全链接 | 外部链接 | 只允许绝对 `https:` / `http:`；新窗口打开并设置 `noopener noreferrer`，显示外链图标。 |
| raw HTML | 转义后的可见文本 | 永不进入 DOM；不提供“允许 HTML”开关。 |
| Markdown image / embed | 隐藏媒体并显示替代文字 | 首版不发起远程图片请求；图片必须来自受控附件内容块和附件服务。 |
| 相对链接、`javascript:`、`data:`、`file:`、`blob:` | 不可点击文本 | 模型不能导航应用内部路由、执行协议或读取本地资源。 |

数学公式、脚注、图表 DSL、iframe、音视频和可交互 HTML 不在首版范围。未知节点降级为其
可见纯文本，不得因为单个节点失败而丢失整条 Assistant 消息。

### 9.3 渲染架构与安全

![Assistant 安全富文本渲染](assistant_rich_text_rendering.svg)

[PlantUML 源码：`assistant_rich_text_rendering`](diagram.puml#L133)

1. 公共 `EventReducer` 只维护 `rawMarkdown`、streaming 状态和持久化消息身份，不保存 HTML。
2. `RichTextRenderer` 复用现有 markdown-it 解析骨架，关闭 raw HTML，将 token 映射到受控 AST；
   本次不新增解析依赖。若后续更换依赖，另行评审许可证、体积与维护成本。
3. AST 经过节点 allowlist、URL policy 和可配置渲染预算，再由固定 Vue 组件递归渲染；禁止
   `v-html`、`innerHTML` 和字符串拼接事件属性。
4. 链接组件统一协议检查、外链标识和 `rel`；代码复制组件只接收文本；表格组件只接收 AST
   cell，不解释 HTML。
5. 超出公共 Chat 契约或前端渲染预算时，显示“内容较长，已使用纯文本模式”，保留可选择文本
   和复制原文。精确字符/节点上限必须在公共 Chat 契约评审时冻结，不能由组件各自硬编码。
6. CSP 继续禁止 inline script；富文本样式限定在 `.assistant-rich-text` 根节点下，不能覆盖应用
   导航、Composer、按钮或错误提示。

### 9.4 流式、完成态与恢复

- 每个 `agent.message` 的 `phase=delta` 只追加 `rawMarkdown`；最多每个 animation frame 触发一次解析，
  不因 token 级更新反复播报或强制滚动。
- 已闭合块复用稳定 key；尚未闭合的表格、链接、强调或 fenced code tail 以转义纯文本显示，
  闭合后再升级为对应组件，避免整条消息在流式过程中跳动。
- `agent.message` 的 `phase=completed` 用权威持久化全文替换 delta buffer，并执行一次完整解析。若 preview
  与 completed 不同，以 completed 为准，不合并两个 HTML 结果。
- GET history、SSE completed 和断线恢复必须调用同一 renderer；以同一 `rawMarkdown` 输入得到
  结构等价 DOM，刷新后不允许退回管道符表格或丢失代码块。
- `aria-live` 在 streaming 时关闭；完成后只播报一次“回答已完成”。用户主动聚焦代码复制、
  表格滚动或链接时使用正常语义，不把每个 delta 发送给读屏。

### 9.5 视觉、复制与响应式

- Assistant 富文本继续使用开放式正文，不加整块气泡；正文 14 px / 1.8，标题与段落间距按
  内容层级收敛，连续列表和表格不制造双倍空白。
- 表格宽度优先适应正文；最小列宽保证可读，超出时只在 `.table-scroll` 内横向滚动，不让
  页面或 Composer 产生横向滚动。窄屏保留表头，不把表格改写为含义不稳定的卡片。
- 代码块使用中性表面、1 px 边界、语言标签和 44 × 44 px 复制按钮；默认不折行，长行横向
  滚动。复制成功以非颜色 Toast/状态文字反馈。
- 选择正文后使用浏览器原生复制可得到可读纯文本；消息菜单提供“复制原文”，复制
  `rawMarkdown`；代码块“复制代码”只复制代码内容。
- 外链获得可见焦点和外链标识；链接文案为空、只有标点或与目标域名明显不一致时，组件仍
  显示目标主机作为辅助信息，降低钓鱼风险。

## 10. 视觉与组件基线

### 10.1 布局

- 设计画布：1440 × 900；桌面优先。
- 左侧导航：248 px；可折叠至 72 px。
- 顶部栏：72 px；只放 Session 级能力和状态。
- 对话正文：建议最大宽度 900 px；保留长内容阅读空间。
- Composer：固定在对话区底部，最大宽度与正文一致，输入增长至 8 行后内部滚动。

### 10.2 O1 品牌与暖中性专业配色

| Token | 建议值 | 用途 |
|---|---:|---|
| `--brand-mark` | `#D97757` | O1 品牌标识主色；不承担运行、成功或警告语义 |
| `--brand-interactive` | `#A9472B` | 链接、可见焦点等小面积品牌交互；用于正文时需满足对比度 |
| `--surface-canvas` | `#FFFCFA` | 对话主画布 |
| `--surface-secondary` | `#F8F3F0` | 应用壳和侧栏 |
| `--surface-tertiary` | `#F4ECE8` | 用户消息、工具弱背景和分组 |
| `--surface-selected` | `#EFE4DE` | 当前会话、选中命令 |
| `--text-primary` | `#2C2724` | 正文与标题 |
| `--text-secondary` | `#6C625D` | 次要信息 |
| `--border-subtle` | `rgba(76,50,39,.06)` | 分隔线、低强调边界 |
| `--border-default` | `#DED4CF` | Composer、活动分隔线和展开详情边界 |
| `--action-primary` | `#2B2522` | 新建、发送、允许执行 |
| `--action-primary-hover` | `#463B36` | 主动作 hover |
| `--status-running` | `#00A240` | 执行中状态点和小面积进度，对应 `green-500` |
| `--status-success` | `#008635` | 已完成，对应 `green-600` |
| `--status-warning` | `#E25507` | 需要用户注意但非失败的状态 |
| `--status-danger` | `#E02E2A` | 错误、停止确认和不可逆操作 |
| `--focus-ring` | `#A9472B` | 键盘焦点与链接；不作为大面积填充色 |

工具层级和密度仍参考本机可观察的 Codex light-theme Token，但上述暖中性色与 O1 品牌色是
CampusClaw 的 target-only 产品设计，不是 OpenAI 官方公开品牌规范。O1 原始透明 PNG 是图形
权威；CSS 不重绘、不拆分五个色块，也不对其重新着色。珊瑚色不铺满按钮、导航或消息表面，
避免与错误/警告混淆。运行中与完成都可使用绿色，但必须同时通过 spinner/进度文本和
check/“已完成”标签区分，不能只依赖颜色。

对比度核对：`#2C2724` / `#FFFCFA` 为 14.45:1，`#6C625D` / `#FFFCFA` 为 5.80:1，
`#A9472B` / `#FFFCFA` 为 5.67:1。O1 主色 `#D97757` / `#FFFCFA` 仅 3.06:1，因此只用于
非文字品牌图形；小号正文、链接或按钮文案不得直接使用该色。

### 10.3 可访问性与键盘

- 正文与交互文字至少满足 WCAG 2.2 AA；状态不能只靠颜色表达。
- 所有图标按钮具有可读名称；主要命中区至少 44 × 44 CSS px。
- 普通消息 idle 时 `Enter` 发送、`Shift+Enter` 换行；running 时保留草稿且不提交新消息。
- Slash 清单使用 listbox 键盘语义；选中只填入，第二次明确 Enter 才执行，IME composition 期间不触发选择或执行。
- Tool Activity 使用可聚焦的 disclosure；展开状态通过 `aria-expanded` 表达，详情的 DOM 顺序始终是输入在前、输出在后。
- Thinking 与 Tool 使用独立 disclosure；读屏只在分析开始、工具状态变化和分析完成时播报状态；用户可聚焦阅读原始推理全文，不逐 token 自动播报。
- 入参 viewer 用语义化 description list/tree 表达键值和层级；被脱敏、被截断和无入参都有非颜色文字状态。
- 流式文本更新使用低打扰 live region，避免每个 token 都被读屏播报。
- 富文本保留语义标题、列表、引用、表格和代码；复制按钮具有包含语言/用途的可读名称。
- `prefers-reduced-motion` 下取消 spinner 旋转，保留静态状态文本。

### 10.4 响应式

- `>= 1280 px`：完整导航与对话。
- `1024..1279 px`：导航默认折叠，会话列表用抽屉打开。
- `< 1024 px`：顶部模型/思考进入 Session 菜单；Composer 状态提示保持显式。
- `< 768 px`：本轮只保证核心对话、附件、发送和停止；Agent 目录与诊断不做并排布局。
- 工具输入和输出在所有断点都保持纵向顺序；只允许单个参数值、表格或代码结果自身横向滚动，不把两区改成左右列。

## 11. 公共契约缺口

Mate Events 1.4.4 三操作已经确认但未作为本次实现证据；“公共 SSE 尚未评审”不再是正确描述。
Claw B01～B15 又改变了控制关联、工具文本块、Skill 与历史边界，必须先完成公共桥接对齐。

| 接入项 | 当前范围与门禁 |
|---|---|
| Agent、Chat 与附件资源 | 目录、列表、创建、上传及绑定分别确认；Runtime 的 Session 名称不等于公共 Chat 标题 |
| Events 适配 | 按专项对照维护公共三接口与内部两接口；不能透明转发或混用游标 |
| 确认与停止 | 待公共目标身份与状态关联明确；恢复后不以旧终态或当前执行查询替代原子目标校验 |
| 工具、配置、压缩与用量 | 公共字符串结果与内部文本块/包装/扩展记录需明确映射，不猜 Schema 或静默丢弃 |
| 身份集成 | 宿主登录态与 Mate 已确认认证要求对齐；产品不采集原始凭据 |
| Slash 执行 | 内部 Skill SSE 已确认，Mate 公共执行仍未确认；真实 Gateway 在此之前关闭 |

## 12. 错误、边界与 DFX

- 按各 Gateway 的稳定错误码分支，不能将 Runtime SESSION_* 直接当成公共 CHAT_*。
- 401/403 交由宿主身份与权限流程；不弹凭据输入，不自动重放写入。撤权清空敏感内容。
- CHAT_BUSY：保留草稿、刷新业务状态；不建议加入队列或调整方向。
- TOOL_CONFIRMATION_NOT_PENDING：移除旧确认按钮并补读；不能自动确认新工具。
- 版本冲突：刷新配置后让用户重新确认，不自动带新版本重试。
- 网络或未知响应：保留已确认内容，显示结果不确定；HTTP 200/EOF 不是业务终态。
- 限流/暂不可用：读取受支持的 Retry-After，显示等待提示；读可重试、写不自动重放。
- 入参或结果无法安全投影：显示不可用，不回退显示内部 raw payload。
- 长历史分批加载并保持滚动锚点；长正文采用渲染预算和纯文本回退，不截断权威记录。

具体状态、错误反例与恢复验收见[专项实施切片](public-chat-alignment.md#8-实施切片理由与验收)。

## 13. 设计决策

- [ADR-0016：产品前端隔离 Runtime 调试协议](ADR-0016-campusclaw-product-frontend-boundary.html)
  （Proposed）：生产 UI 使用公共 bridge；内部协议只在诊断入口出现。

## 14. 实施分期

1. **设计确认**：沿用三类页面壳，按专项核对确认、停止、恢复和配置状态及公共接入条件。
2. **前端壳与 mock adapter**：实现路由、导航、对话、思考/工具活动流、入参 viewer、Composer、状态机与
   `RichTextRenderer`；产品 adapter 保持无 JWT/APPKEY/`access-token` 能力，只使用非秘密 fixture 和调用上下文。
3. **公共 bridge 对齐**：以已确认 Mate Events 三操作为准，补齐与新 Claw 的目标关联、工具结果、历史及身份映射；其余公共资源按各自专题评审。
4. **Slash 前端切片**：按专项先实现 Parser、独立草稿、Catalog、Mock Gateway、临时结果与无障碍；公共执行协议确认前不接真实 POST。
5. **真实集成**：公共能力通过后替换 mock adapter；实现历史去重、断线恢复、配置并发冲突和错误投影，不把内部 ETag 直接放进产品界面。
6. **诊断隔离**：保留已有 DEV-only `debugHeaders` 内存 store，按新 operation 更新快照范围；验证生产包不可达，不携带原请求自动重试。

## 15. 测试与验收

本轮 F1～F6 场景见[公共对话对齐专项](public-chat-alignment.md#8-实施切片理由与验收)。
保留 Assistant 富文本安全、原始 O1、纵向参数/结果、诊断构建隔离和秘密内存生命周期门禁。

- 富文本 golden 覆盖段落、列表、引用、链接、行内/块代码、GFM table 与未知节点；每个字符边界拆分流，完成态与历史渲染等价。
- 安全 corpus 覆盖 raw HTML、事件属性、危险协议、相对路由、远程图片、深层嵌套和超预算输入；无任意 HTML 注入或额外网络请求，降级可复制公开原文。
- 工具入参覆盖敏感字段、绝对路径、内部资源 ID、超深对象、长数组、HTML/Markdown/ANSI/URL；服务端投影失败时不回退显示内部数据，前端正则不作为唯一脱敏边界。
- Headers 覆盖三个空值预置、可编辑/启停/删除、每次按钮点击只加一条空行、输入不补行、删除与清空可达零行、焦点、未使用预置的忽略、任意 Key/Value、大小写不敏感重复、非法 token、CR/LF、Fetch 禁止名称、启用计数和手工覆盖；自动 Header 不进 DOM，新 operation 快照范围单独验证。
- 诊断秘密不写入 localStorage、sessionStorage、IndexedDB、URL、构建变量、日志、遥测或错误；刷新、关闭页签、切 API base 和清空后值不存在，修改表单不改变已接受执行。
- 产品构建不装配 Runtime/Headers 入口，不持有秘密；生产 DOM 与诊断摘要不泄漏内部身份、凭据或原始 SSE，跨源诊断按明确 CORS 名称允许，不使用无界通配。
- 视觉与可访问性覆盖独立暖灰 Headers、纵向输入/输出、原始 O1、键盘焦点、流式读屏节流、色彩对比、reduced motion 及表格/代码自身滚动。

原型状态回归使用 `node test_frontend_review.cjs`（需要 jsdom），覆盖发送、回执、确认、
停止、未知结果、历史补读、配置冲突、草稿保留、输入边界与无网络行为。
该测试验证设计原型，不等于真实 Vue 或 Mate/Claw 集成通过。

## 16. 验证要求

- 执行 `plantuml -tsvg diagram.puml`，验证 ASCII、SVG XML、Markdown 图片/图源链接和行锚点。
- 保留稳定图名；新增全局目标组件类图与对话状态图；生成物不手工修改。
- 1440、1024、768、390 检查浅色导航、长文本换行、焦点、控件大小、纵向工具详情与原始 O1。
- 校验 HTML 脚本语法、原型状态机和 `git diff --check`；禁用脚本时仍可阅读静态说明。
- 旧运行态 PNG/low-fidelity.png 是历史存档，不要求其与当前 HTML 同步，也不将其作为当前验收图。
- 必须单独实际查看生成 SVG 的原尺寸与缩放视图；源码/DOM 检查不能替代像素验收。
- 若工具访问限制导致不能验收 HTML 实际布局，交付时明确报告，不声称视觉回归通过。

本轮验证记录（2026-09-08）：主体验与 Slash 共 9 张 SVG 已重新生成并通过 XML 校验，
PlantUML ASCII、图源行锚点、82 个本地资源引用和 HTML 内联脚本语法检查通过。
`test_frontend_review.cjs` 的 11 组 DOM 状态回归通过；测试使用已有 jsdom 环境，未添加项目依赖。
已实际查看生成图和目标组件图的原尺寸/缩放视图，Slash 与原完整版对照保留原职责链。
浏览器拒绝访问本地 HTML，本轮未绕过该限制；1440/1024/768/390 的真实页面布局、
真实 Vue、网络、认证与 API 集成仍未验证，不把静态源码或 DOM 检查称为像素验收。

Header 交互验证（2026-09-09）：13 组原型回归通过，包含新增的预置、显式增行、删除/清空至零行和焦点检查。
Chrome 实际操作确认点击后由三行变四行、删除后回到三行；检查 1440、1024、768、390 宽度的 Headers 布局。
本专题 6 张 SVG 由 PlantUML 重新生成并通过 XML 校验，仅 Header 图产生变更；ASCII、无 Mermaid、45 个 Markdown 本地引用/图源行锚点及 `git diff --check` 通过。
已查看 Header SVG 原尺寸与缩放结果，并与修改前图对照；其余图无变更。本次不验证 Vue 或后端集成，也不扩大前述公共对话视觉验收范围。

## 17. 高保真生成说明

本节仅记录历史资产生成方法，不是本轮生成结果。常规态 v8 与运行态 v8 以 v7 为底稿，不经过生成模型；先清除旧的小号品牌容器，再从
`campusclaw-mark-o1.png` 进行 Lanczos 等比缩放和 alpha 合成。该处理不改变五个色块的形状、比例、
间距、方向或颜色。活动区、暖中性色、导航、顶部栏、最终答案与 Composer 保持 v7 不变；实际实现也直接
引用同一 PNG，并以本设计文档的字段、Token 与交互规则为准。

[查看生成使用的完整 Prompt](imagegen-prompts.md)

## 18. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.9.0 | 2026-09-09 | 同步 Session Events 命名和事件消费边界。 |
| 1.8.0 | 2026-09-09 | 同步用户确认的 Slash 标签式交互：+ 菜单入口、无前导 Slash 的精简清单、独立参数与统一上箭头，正式交互详见专项 1.4.0。 |
| 1.7.0 | 2026-09-09 | 明确 Thinking 展示模型返回的原始推理。 |
| 1.6.0 | 2026-09-09 | 按用户反馈精简 Headers 面板：删除常驻说明；预置 access-token、X-HW-ID、Authorization 三个可编辑/可删除的空值行；仅“增加请求头”追加空行，取消自动尾行，删除/清空允许零行；未使用预置不报错、不计数或发送。复核实现 4cc8dd8，更新设计、交互原型及图源，Vue 实现待同步。 |
| 1.5.0 | 2026-09-08 | 对齐 Mate 公共三接口与内部 B01～B15 差异；补齐主对话、工具确认、中断、恢复、配置共享与目标组件；移除现行原型的旧跟进控件，保持浅暖灰。 |
| 1.4.0 | 2026-09-07 | 增加 Slash Command 前端专项入口和整体边界：独立 Composer 模式、显式执行、临时结果与公共执行协议门禁；同步清除已退役的 running 队列快捷键表述。 |
| 1.3.0 | 2026-09-07 | 同步三个控制接口退役与本期无队列；停止执行通过 user.interrupt 完成，实际停止后新提交。旧图片仅为视觉基线，其他 v1 映射待迁移。 |
| 1.2.0 | 2026-08-28 | 按用户确认删除“隐藏的请求头”区域及覆盖状态展示；`Headers` 面板只呈现可编辑的通用 Key/Value 行。请求适配器自动生成 Header 的内部行为不变，手工同名值仍在请求合并阶段优先。 |
| 1.1.0 | 2026-08-28 | 按用户选择将通用 Header 编辑器保持为独立 `Headers` 面板，不与 Agent/Session 的“开发者诊断入口”合并；视觉复用原诊断入口的折叠 summary、暖灰次级表面、虚线边界、紧凑字号、38 px 输入和次级按钮；表格交互和请求边界不变，仍不提供凭据模式、固定 Header 或主动作。 |
| 1.0.0 | 2026-08-28 | 按用户确认改用 Postman 风格的通用 Headers 表格：删除固定四 Header、认证模式、应用按钮和常驻说明；新增任意 Key/Value、逐行启停/删除、自动空白尾行、启用计数、折叠的自动 Header、手工覆盖状态和浏览器限制行内校验；补充 PI、OpenCode、Codex、DSH 与 Postman 对照证据。 |
| 0.9.0 | 2026-08-27 | 在产品路由仍保持无凭据的前提下，新增 target-only `debugHeaders` 内部诊断设计：固定支持 `X-HW-ID`、`Authorization`、`X-HW-APPKEY`、`access-token`，只在页面内存中存活，仅快照到初始 `POST /events`；对齐已评审实现 `pi-mono-java@d03c08db`，其 Agent/Skill/Tool 发现不透传、只有 Tool execute 使用四项快照；补充隔离、脱敏、CORS、断线不重放和验收规则。 |
| 0.8.0 | 2026-08-27 | 基于 `pi-mono-java@320d7907` 修正凭据边界：当前前端只发送非秘密 `X-HW-ID`，不支持 JWT/APPKEY 输入、配置、存储或 Header 注入；删除“凭据可在开发者诊断中查看”的错误设计，明确生产身份与授权由 mate-service / 网关承担且具体浏览器会话机制待评审；同步 ADR、评审页、低保真与 PlantUML/SVG。 |
| 0.7.1 | 2026-08-26 | 修正 O1 在界面中被深色方块和过小身份容器弱化的问题；品牌位改为透明底原图直接显示并等比放大，同步常规态/运行态 v8、低保真与评审面。 |
| 0.7.0 | 2026-08-26 | 对照本机 Codex activity disclosure 实现，将思考改为安全标题/摘要而非原始推理；工具改为紧凑活动行，执行中展开、完成后折叠，输入与输出始终纵向排列，未开始工具不显示；同步常规态/运行态 v7、低保真、评审面和 PlantUML/SVG。 |
| 0.6.0 | 2026-08-26 | 确认 O1 为 CampusClaw 品牌标识，新增原始透明 PNG 权威资产；禁止生成式重绘，低保真/评审 HTML 直接引用同一文件，高保真 v6 采用确定性缩放与合成；将冷灰表面调整为暖白、暖灰和深暖黑，保留绿色运行/完成语义。 |
| 0.5.0 | 2026-08-26 | 基于 `pi-mono-java@bde12370` 的 Thinking 持久化投影、Assistant `tool_call.arguments` 与工具生命周期实现，将思考与工具按时序组成 Agent 活动流；增加工具入参关联、服务端脱敏、资源映射、结构化 viewer、降级与测试规则；同步常规态/运行态 v5、低保真、评审面和 PlantUML/SVG。 |
| 0.4.0 | 2026-08-26 | 基于 `pi-mono-java@56be8eee` 的当前 Vue 文本插值、事件投影和 Runtime 文本保真行为，新增 Assistant-only 安全 Markdown 设计：支持语法、信任边界、AST-to-Vue 渲染、链接/图片/HTML 策略、流式稳定尾块、复制/响应式/可访问性与安全测试；新增富文本 PlantUML/SVG、常规态 v4、低保真和评审面。 |
| 0.3.0 | 2026-08-20 | 对照本机 Codex desktop 实现，将运行中跟进改为单一当前模式：desktop 默认“调整方向”，可配置“加入队列”，`Cmd/Ctrl+Shift+Enter` 单次反转；明确 Steer 不硬中断当前模型/工具、队列 UI 与现有 HTTP 控制项身份缺口；更新低保真、运行态 v4、评审页、ADR 与图。 |
| 0.2.0 | 2026-08-20 | 对齐 Runtime HTTP 1.37.0 的属性表、权威顺序、稳定评审键、证据分类和 HTML 评审风格；新增 `frontend-review.html`；依据本机 Codex/ChatGPT 应用可观察 Token 将视觉改为 Codex-inspired 黑白中性体系，并生成常规态与运行态 v3 高保真稿。 |
| 0.1.0 | 2026-08-20 | 基于现有 Vue 调试台、Runtime V1 源码、精确契约和 Postman 实测，提出低保真三状态、高保真常规/运行态、产品边界和公共契约缺口。 |
