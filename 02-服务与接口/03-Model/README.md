# Model

版本：2.11.0 · 2026-10-09 · M02。当前设计只通过 CampusMate 调用模型；业务 Agent 设置决定模型绑定；每个新执行查询 Mate 窗口，输出额度由 Mate 控制；查询与输出策略迁移、旧全局目录删除待实现。

| 内容 | 维护位置 |
|---|---|
| 模型选择、Provider 分层、调用适配与验收 | 本文 |
| Mate 模型信息查询与执行快照 | [模型能力](model-capabilities.md)；新增查询精确契约由该专题维护，待实现 |
| Chat 请求、响应、错误码和示例 | [Chat 接口说明](chat-api.html)，由 [chat-api.json](chat-api.json) 生成；输出额度由 Mate 控制，其他 Chat 行为保持 |
| 用量表、事务与统计 | [用量持久化](usage.md) |
| 固定源码基线、观察结果和实现差距 | [源码证据](source-evidence.md) |
| 服务地址、路径、超时和配置校验 | [共享客户端配置](../02-CampusMate共享客户端配置/README.md) |

## 1. 职责与全局结构

Runtime 选择模型、执行工具并保存会话；AI 模块把上下文转换为模型请求，把响应流转换为统一消息事件；CampusMate 管理上游路由、逐模型能力、协议差异、endpoint 和凭据。

![Model 全局目标类图](model-classes.svg)

[PlantUML 源码](diagram.puml#L1) · [原尺寸 SVG](model-classes.svg)

主图是推荐目标结构，分组表示职责边界。已有骨架与待清理实现见源码证据；不再保留另一套现状类图。Provider、请求 Mapper 和 WebClient 是共享对象；Parser、事件流和累积状态每次调用独立创建。AI 返回事件与最终消息，数据库写入留在 Runtime。

<a id="model-source"></a>

## 2. 模型来源

Agent 的 `.campusclaw/settings.json` 维护 `defaultModel/bindingModels`；默认模型必须属于绑定列表，缺失、空白、重复或不一致时失败。`AgentRuntimeManager` 加载设置，`PreparedAgentRuntime/AgentDirectorySnapshotDTO` 固定同一次准备的绑定数据；本地模型列表与选择不访问远端，也不填虚假能力。

每个新执行在锁外单独查询 Mate 当前选中模型的 `contextWindow`，应用服务在锁内复核 Session 版本、模型与绑定后，固定该执行的不可变模型信息。自动压缩、Tool Loop 和原根确认续跑共用结果；下一次新执行再次查询。独立手工压缩和 Subagent/Cron 各自查询。能力不写入 Agent 目录，不由 refresh 控制更新；查询失败不回退旧窗口。精确字段、入口、锁边界及压缩规则由[模型信息专题](model-capabilities.md)统一维护。

Claw 不查询或消费 maxTokens，不为普通 Chat 或摘要指定输出额度；Mate 自行管理输出参数及上游差异。删除 `campusmate.model.context-window/max-output-tokens` 与 Java 默认值。现有已发布绑定仍是模型使用范围的唯一权威，远端信息不能扩大允许列表。

这是产品约束与架构变更：绑定按业务发布，动态窗口按执行读取，避免能力长期陈旧；Mate 统一控制生成额度。代价是新执行多一次查询及故障依赖，并失去 Claw 自有摘要输出预算。与 pi 的差异及源码证据见[架构对比 A06](../../01-总体架构/07-Agent架构对比/README.md#a06)。

<a id="provider"></a>

## 3. Provider 调用边界

### 身份与路由

| 对象 | 规则 |
|---|---|
| Provider | 身份键为 `provider.id`，名称、URL、凭据和协议不参与身份；唯一内置实现 `CampusMateProvider`，ID 为 `campusmate`，认证为 `ProviderAuth.none()` |
| 模型身份 | `(provider.id, model.id)`；Mate modelId 为 1–64 字符、大小写敏感的不透明值 |
| 调用入口 | `CampusClawAiService` 先查 `AiProviderRegistry`，未命中再查 `ApiProviderRegistry`；二者都未命中时在发 HTTP 前失败，不替换模型 |
| 调用接口 | 保留 `AiProvider.id/auth/streamSimple` 及 `ApiProvider` 抽象；注册表只路由已解析 Model，不提供模型发现或可用性判断 |
| 连接配置 | 读取统一的 `campusmate.*`；不使用 `Model.baseUrl/apiKey/headers` 覆盖部署地址、协议或请求头 |

Provider 身份与协议路由分开，避免按厂商堆叠中央分支。内部协议默认值、未注册值的启动失败规则，以及 URL/path 校验由[共享配置](../02-CampusMate共享客户端配置/README.md)维护。

<a id="provider-identity"></a>

### 身份与历史数据

新 Model、注册、Assistant 和持久化 `_provider` 使用 `campusmate`。旧 `mate-model-manager` 不作为别名，不增加 enum 兼容解析、转发类或 SQL/历史文件迁移；已有 `_provider` 原样读取，压缩与 Subagent/Cron 的身份比较不把新旧值视为相同。

保留 `provider.mate` 包以及 `MateChatRequestMapper/MateChatSseParser/MateReasoningSignature` 名称。`MateInvocationErrorCode`、`MATE_MODEL_MANAGER_ERROR` 和日志 `event/operation/errorCode` 保持原义；稳定错误码不是 Provider ID。Logger 使用 `CampusMateProvider`，字段规则见[调用日志](../../01-总体架构/05-CampusClaw调用日志/README.md)。

<a id="chat"></a>

## 4. Chat 调用与适配

使用 `POST /mate-service/v1/LLM/chat`。精确 HTTP 字段、报文和错误码集中在 [Chat 接口说明](chat-api.html)；本节维护 Provider 到该接口的转换。

调用经内部网关，不发送 `X-HW-ID/Authorization/X-HW-APPKEY`、`agentId/sessionId` 或上游连接信息；服务准入依赖网关与网络 ACL。Mate 不在调用阶段重新检查 Agent 绑定，也不执行 Tool。

一次 POST 对应一次前台调用，不支持 `Idempotency-Key`，结果未知时不得重放。成功 SSE 原样返回 Chat chunks，以 `[DONE]` 结束；流建立前错误使用真实 HTTP 状态，建立后发送 `event:error` 并关流，不再发送 `[DONE]`。取消关闭请求和 body，沿连接传播到上游；Provider 的正常完成、`ABORTED` 和 `ERROR` 竞争时只能产生一个终态。

本图只展示一次模型调用，Provider routing 保留路由选择，Mate provider 合并请求映射和流解析协作。HTTP 建流前拒绝不进入增量阶段；正常 [DONE]、流失败和调用方取消各自产生一次终结结果，取消关闭请求并由 Mate 传播至上游。输出限制省略为图示待实现增量，底层 Provider 事件不直接等同公共事件。

![Chat 调用时序](chat-sequence.svg)

[PlantUML 源码](diagram.puml#L187) · [原尺寸 SVG](chat-sequence.svg)

### 请求映射

| AgentLoop / Provider 输入 | Mate Chat 请求 | 规则 |
|---|---|---|
| `Model.id` | `model` | 原样 Mate 模型 ID |
| `Context.systemPrompt` | 首个 `system` message | 空值时省略 |
| `UserMessage` 文本 | `user.content` | 保留顺序，非文本拒绝 |
| `AssistantMessage` 文本 | `assistant.content` | 按顺序拼接文本块 |
| `AssistantMessage.ToolCall` | `assistant.tool_calls[]` | arguments 序列化为 JSON 字符串 |
| `ToolResultMessage` | `tool` message | `tool_call_id` 关联 ToolCall，content 为字符串 |
| `ThinkingContent.thinkingSignature` | Assistant reasoning 白名单字段 | 按原字段种类重放 |
| Agent Tool | `tools[].function` | JSON Schema 原样投影，不发送 `strict` |
| `SimpleStreamOptions.toolChoice` | `tool_choice` | 只允许 `auto/none` |
| 输出 token 上限 | 不发送 | 普通调用及摘要均由 Mate 控制；Mapper 不转发 options 中残留额度，见[输出与上下文规则](model-capabilities.md#4-输出控制与上下文消费) |
| 显式 temperature | `temperature` | 未设置时省略 |
| `ThinkingLevel` | 不发送 | 推理开关和 effort 由 Mate 配置 |
| 固定字段 | `stream/stream_options.include_usage` | 均为 `true` |

reasoning 白名单为 `reasoning_content/reasoning/reasoning_text/reasoning_details`，前三项为字符串，最后一项为不透明 JSON 数组。可读内容展示模型原始推理，signature 用于下次重放；展示规则见 [Thinking 设计](../../01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md#thinking-original-text)。

首版只支持文本、function Tool 和上述 reasoning。图片、音频、文件、content part 数组与 Tool 图片在发 HTTP 前失败，不丢块后继续。未知字段及已定义可选字段的处理遵循接口说明；`event:error` 是 Mate 扩展；请求中的输出额度字段按未知字段拒绝。

### 响应、用量与运行约束

| SSE 数据 | Provider 输出 |
|---|---|
| `chunk.id` | `AssistantMessage.responseId` |
| 请求 model / `chunk.model` | `AssistantMessage.model` / 可选 `responseModel` |
| content / reasoning / tool_calls 增量 | Text / Thinking 与签名 / ToolCall start、delta、end |
| `finish_reason` | `STOP/LENGTH/TOOL_USE/ERROR` |
| usage | `Usage`；output 已含 reasoning token，可保留上游 breakdown |

Provider 仅解析 Usage，Runtime 保存和汇总；事务、缺失 Usage、分支隔离与失败处置统一见[用量持久化](usage.md)。

调用须配置连接、首字节、流空闲、总执行时间与缓冲上限，数值由部署管理。不记录完整 SSE、prompt、Tool 参数或 thinking；错误不得暴露 endpoint、credential、私有路由、stack trace 或推理正文。

<a id="streaming-json"></a>

### 通用工具参数预览

设备巡检工具的参数逐步到达时，上层需要提前展示有用信息；工具执行仍必须等待完整调用。AI 提供通用部分参数对象，Runtime 再按业务和权限选择展示字段。此能力在 `a1e6450427abeabaa1af04d5964f371dbbf4cf68`（[PR #336](https://github.com/superheromeZzh/pi-mono-java/pull/336)）已实现，尚未合入 main；不改变本文其他待实现项。

`MateChatSseParser` 为每个工具调用保留原始参数缓冲和独立 `StreamingJsonParser`。后者按新增字符解析对象、数组、嵌套值、字符串、数值、布尔与 null；未闭合字符串只暴露完整 Unicode 前缀，数值/字面量等到词法边界才发布。`ToolCallDeltaEvent.partial` 及时携带已知 ID/name 和深度只读参数快照，空参数 delta 也可传播刚到达的身份，旧快照不随新输入变化。

每调用预览限制为 1048576 个原始 UTF-16 单元和嵌套深度 64。语法错误、重复键或预算超限永久停用该预览；这是展示降级，不使完整调用失败。词法扫描按新增输入推进，快照仍有深复制成本；预算不限制原有完整参数缓冲，不能把它解释为整体内存或吞吐保证。

结束时从原始缓冲独立执行既有 Jackson Map 解析，不用补全对象代替最终参数，不把预览送入执行或权威错误消息。普通工具完整解析的既有重复键末值、尾随内容接受语义保持。额外严格扫描产生 `ToolArgumentJsonStatus`（VALID/INVALID/UNKNOWN），只存在内存中的 `ToolCallEndEvent`，不改变其 JSON 序列化、ToolCall、模型历史或公共事件。生产 Mate 始终提供 VALID/INVALID；兼容结构化事件构造器和反序列化缺省为 UNKNOWN，不能把 UNKNOWN 当作原始输入通过严格验证。

原始 JSON 非法或截断仍使 Provider 失败。业务参数校验、权限/必要确认和执行仍由 Agent/Runtime 在完整调用之后负责；AI 不依赖计划工具。Runtime 只把可信 ExitPlanMode 的 plan 前缀投影成公共计划事件，并在内部诊断为 INVALID 时拒绝审核；精确身份、冻结预览和审核规则归[计划流式专题](../../01-总体架构/06-CampusClaw计划模式/plan-streaming.md)。其他工具的半成品参数不自动公开。

本次以 2026-10-09 隔离 fetch 的 pi main `f1b2e77f5b13b2a199b1052cb79c235451afe7d7` 为 AI 主基线，核验 `packages/ai/src/utils/json-parse.ts#parseStreamingJson`、`packages/ai/src/api/openai-completions.ts` 的累积/结束路径以及 `types.ts` 的 partial 语义。pi 的修复解析、最终容错和可变 partial 不直接照搬：Java 保留事件快照与完整解析边界；这是架构适配。完整新旧提交、源码符号、验收和安全差异见[专项证据 §16](../../01-总体架构/06-CampusClaw计划模式/source-evidence.md#plan-generic-json-evidence)。仅使用现有 JDK/Jackson，无新增直接或传递依赖。

<a id="implementation"></a>

## 5. 实施与验收

已核验的 Java `21c3f59b` 具备业务 Agent 设置主链和 CampusMate 调用链，仍保留全局目录及相关日志。具体源码、历史观察和独立核验范围仅在[源码证据](source-evidence.md)维护；下表描述目标实施顺序，已完成项只做验证。

| 步骤 | 实施内容 | 验收 |
|---|---|---|
| S0 · 模型能力（待实现） | 按[能力专题 C1～C4](model-capabilities.md#5-java-分层与实施切片)实现 Mate 查询、自主输出策略、执行快照及默认值删除 | 验证每个新执行一次查询、锁外读取与竞争、窗口变化、所有调用无输出额度及镜像一致性 |
| S1 · 模型选择 | 固定 §2 的设置加载与快照链 | 覆盖缺失、空白、重复、默认值不在列表、Agent 隔离，以及默认/切换/压缩/Subagent/Cron 同源；禁止回退 |
| S2 · 全局目录清理 | 删除 `ModelRegistry`、两处 JSON 探测、`ModelCatalogService`、`CatalogRuntimeModelManager` 及专用环境凭据解析；迁移 SSE 仍使用的成本计算 | Spring 不再装配上述目录 Bean；启动无外部模型文件探测及加载日志；无消费者的能力辅助方法删除 |
| S3 · 调用与依赖清理 | 移除 AI Service 的目录依赖；删除 Anthropic、OpenAI Completions、OpenAI Responses、Mistral 具体适配器及专属测试，按下表清理 SDK 并同步公司镜像 | 只内置 CampusMate，空 API 注册表可启动；新旧身份遵守 §3；公共消息、流、枚举与有消费者的工具不误删 |
| S5 · 参数预览（PR 已实现） | 通用增量解析、身份快照、内部诊断及独立完整解析 | 每字符分片、嵌套数组/对象、Unicode、身份延迟/多工具交错、快照只读与隔离；预览超限不拒绝完整调用；重复键/尾随输入兼容；诊断不序列化 |
| S4 · 回归 | 验证 §4 映射与流生命周期、用量事务及[配置验收](../02-CampusMate共享客户端配置/README.md#10-验收标准) | 覆盖非文本本地拒绝、未知/可选字段、usage 缺失、流前/流后错误、并发隔离、取消与唯一终态；canonical 构建/测试和公司镜像编译通过 |

测试名称和能力注册表 selector 只在对应测试真实存在并执行后更新。受阻项按实际结果记录，不把设计确认记成实现通过。

### 依赖影响

不新增 Maven 依赖。CampusMate 请求与流处理继续使用现有 Jackson、WebClient、Reactor Netty；取消厂商直连可减少 SDK 维护，但没有包体积、性能或可靠性的量化结论。

| 删除的直接依赖 | 范围 | 固定基线中的主要传递依赖 |
|---|---|---|
| `com.anthropic:anthropic-java:2.18.0` | 根版本管理、AI 与公司镜像 POM | client-okhttp/core、Kotlin、OkHttp logging、Jackson 扩展、Swagger、Victools、Apache HttpClient/Core 5 |
| `com.openai:openai-java:4.29.1` | 同上 | client-okhttp/core、Kotlin、OkHttp、Jackson 扩展、Swagger、Victools；与 Anthropic 路径存在仲裁 |

源码消费者和运行依赖树证据见[源码证据](source-evidence.md#dependencies)。删除后重新核对全 Reactor 与公司镜像，确认两个 SDK 不再进入产物；保留仍被使用的 Jackson、Reactor/Netty、日志、`json-schema-validator` 和测试用 MockWebServer，不机械排除共享传递依赖。公司父 POM 的完整依赖树与删减产物尚未验证。

## 6. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.11.0 | 2026-10-09 | AI 提供通用只读参数预览与内部原始 JSON 诊断，保持完整解析和执行边界。 |
| 2.10.0 | 2026-09-19 | Mate 控制全部输出额度，Claw 每个新执行读取模型窗口并在执行内复用。 |
| 2.9.0 | 2026-09-19 | 按模型查询 Mate 能力并发布到 Agent 快照，窗口必填、输出上限可选，删除统一 token 默认值。 |
| 2.8.2 | 2026-09-17 | 模块统一命名为 Model，更新目录、图名与引用。 |
| 2.8.1 | 2026-09-17 | 精简目录、文件名和重复说明，集中模型规则、调用适配及实施验收。 |
| 2.8.0 | 2026-09-17 | 模型来源收敛为业务 Agent `.campusclaw/settings.json`，删除全局 JSON 目录及目录适配链。 |
| 2.7.0 | 2026-09-14 | 按模块职责重写正文，集中源码与用量专题，复用接口说明并重排全局类图及调用顺序图。 |
| 2.6.0 | 2026-09-14 | 默认仅内置 CampusMate，统一 Provider 身份与类名，明确第三方适配器、模型预置及 SDK 的削减边界。 |
| 2.5.0 | 2026-09-09 | 明确 Thinking 展示模型返回的原始推理。 |
| 2.4.0 | 2026-08-26 | 模型配置统一使用 `campusmate.model` 与对应环境变量。 |
| 2.3.0 | 2026-08-26 | CampusMate 共用配置树和端点目录，记录已实现的 Mate Chat 边界。 |
| 2.2.0 | 2026-08-26 | Mate Tool 共用 CampusMate origin。 |
| 2.1.0 | 2026-08-26 | Model Manager 与受管 Runtime 共用 `campusmate.base-url`。 |
| 2.0.0 | 2026-08-24 | 冻结前台 Chat、断连取消、API 适配与用量落库规则。 |
| 1.3.0 | 2026-08-23 | 五个 Model Manager 接口采用内部网关免应用层认证；Mate Provider 使用 `ProviderAuth.none()`。 |
| 1.2.0 | 2026-08-22 | Responses create 采用语义透明代理。 |
| 1.1.0 | 2026-08-22 | 冻结 Responses create/cancel 和前台取消扩展。 |
| 1.0.0 | 2026-08-21 | 明确 Provider 身份、Java 对齐、Mate 托管调用和五项运行接口候选。 |
