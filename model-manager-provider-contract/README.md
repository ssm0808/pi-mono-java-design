# MateService Model Manager 通用 Provider 对接设计

| 属性 | 值 |
|---|---|
| 文档版本 | 2.2.0 |
| 状态 | 目标设计；Mate Chat 调用已冻结，接口 1-3 保持候选 |
| 设计日期 | 2026-08-26 |
| pi-mono 源码基线 | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` |
| 初始 pi-mono-java 源码基线 | `d649866a6cae967ace18ceaeb9597edd47e5721e` |
| 当前 pi-mono-java 复核基线 | `56be8eee59415a5f86658d6635a7b7e8891263d3` (`origin/main`) |
| mate-service 源码基线 | `6d5e6f3714e1cf8744d187a4796ca06300ad7e33` |
| 初始设计仓分析基线 | `3fde5735cd27433c3e3e5e03a5ce39b297ad3b00` |
| 本次设计仓分析基线 | `f1bacba636d7d1f85cf034f22680e184ab4567d4` |
| 本次设计修订基线 | `871b9be3cba4b32e4bc29fd784afbb98bc4842cf` |
| 已纳入设计提交 | `78c01c9143d00b0973ff36e0d82bb87154dd81e2`（内部网关免认证） |
| 适用边界 | pi-mono-java Runtime ↔ mate-service Model Manager |

## 1. 结论

确定 Provider 身份只需要稳定且唯一的 `provider.id`。`name`、`baseUrl`、凭据和 `api`
都不参与身份；运行时模型唯一键为 `(provider.id, model.id)`。

CampusClaw 只注册一个 Mate 通用 Provider：

```text
providerId = mate-model-manager
apiId      = openai-completions       # CampusClaw 内部配置，不进入 HTTP
model key  = (mate-model-manager, <Mate modelId>)
auth       = ProviderAuth.none()
```

模型调用采用前台请求作用域的 Chat 流：

```http
POST <campusmate-base-url>/mate-service/v1/LLM/chat
Content-Type: application/json
Accept: text/event-stream
```

- CampusClaw 经内部网关调用，不携带应用层身份或凭据；
- Provider 把 `AgentLoop Context` 转为 Mate Chat 请求；Mate 不认识 Java Message 类型；
- 成功响应是原始 OpenAI 风格 Chat SSE，不包装 ResultBean，不改写 chunk；
- 调用取消通过关闭请求/SSE 连接实现，不存在独立 cancel operation；
- Mate 如何映射上游模型、字段、endpoint 和凭据属于 Mate 内部实现，不进入本契约；
- Token 使用量由 CampusClaw 解析，并按 pi 的 Record + Stats 模型持久化。

本版是破坏性协议调整：废止 1.x 的 OpenAI Responses create/cancel 设计。调用协议不再包含
`input/instructions/store/background/previous_response_id`，也不再捕获 Response ID 发起远程取消。

## 2. 设计边界与术语

| 概念 | 身份或取值 | 责任 |
|---|---|---|
| Runtime Provider | `mate-model-manager` | 模型目录、NoAuth、Context 转换、Chat SSE 解析 |
| Runtime 内部 API | 默认 `openai-completions` | 选择 CampusClaw 内部协议实现；不发送给 Mate |
| Mate 模型 | 大小写敏感的 `modelId` | 调用方选择模型的唯一公开值 |
| Mate 上游路由 | Mate 私有 | 上游 Provider、模型、endpoint、凭据及适配方式 |
| Session Entry | 可分支消息记录 | User、Assistant、Tool 和其他会话内容 |
| Session Record | 不参与分支的运行事实 | Usage、operation 等运行记录 |

身份规则：

1. `providerId` 是 Provider 注册表唯一键；修改 URL、名称或内部 API 不创建新身份。
2. `modelId` 为 1-64 字符、大小写敏感的不透明字符串；CampusClaw 必须原样使用目录值。
3. HTTP 请求不携带 `apiId/providerId/agentId/sessionId/upstreamModelId`。
4. 免认证决定只覆盖本文剩余四个 Model Manager 接口；其他 CampusMate 接口保持未决。
5. 网关准入和网络 ACL 是部署边界，不定义为 CampusMate 业务认证契约。

![Provider 身份与运行契约](provider_identity_model.svg)

[PlantUML 源码：`provider_identity_model`](diagram.puml#L1)

## 3. 源码证据

### 3.1 pi-mono 观察行为

| 证据 | 观察行为 |
|---|---|
| `packages/ai/src/models.ts`：`Provider`、`MutableModels`、`ModelsImpl`、`createProvider` | Provider 注册和调用按 `provider.id`；Provider 持有认证、目录和 stream 能力。 |
| `packages/ai/src/types.ts`：`Model`、`SimpleStreamOptions`、`ToolChoice`、`Usage` | Model 同时携带 Provider/API；通用 `toolChoice` 为 `auto/none`；Usage 始终存在。 |
| `packages/agent/src/agent-loop.ts`：`runLoop`、`streamAssistantResponse` | 普通 Loop 不计算 `toolChoice`；收到 Assistant ToolCall 后执行工具并继续下一轮。 |
| `packages/coding-agent/src/core/compaction/compaction.ts`：`completeSummarization` | 摘要调用显式使用 `toolChoice: "none"`，避免调用工具。 |
| `packages/ai/src/api/openai-completions.ts`：`stream`、`convertMessages` | Chat Provider 处理 system/user/assistant/tool、ToolCall、reasoning 扩展和 usage chunk。 |
| `packages/agent/src/harness/session/types.ts`：`UsageRecord`、`SessionStats` | Usage 是独立 Record，可关联 assistant、compaction、branch summary 和 deferred fetch。 |
| `packages/session-backends/sqlite-node/src/sqlite/migrations/001_initial.sql` | SQL 后端把 `entries`、`records` 和 `session_stats` 分表保存。 |
| `packages/session-backends/sqlite-node/src/sqlite/repo.ts`：`appendRecord` | Usage Record 插入后，同一串行写路径增量更新 Stats。 |
| `packages/session-backends/sqlite-node/src/sqlite/storage/session-stats.ts` | 汇总 cached、uncached、total tokens 和总费用。 |

pi 的 `Usage` 在流开始时初始化为全零，收到上游 usage 后覆盖；上游不返回 usage 时无法区分
“未报告”与“真实为零”。本设计严格沿用该语义，不新增 `reported` 字段。

### 3.2 pi-mono-java 观察行为与差距

| 证据 | 当前行为 | 目标差距 |
|---|---|---|
| `modules/ai/.../types/Provider.java`、`Api.java` | Provider/API 是封闭 enum。 | 无法开放注册 `mate-model-manager` 等身份。 |
| `modules/ai/.../provider/ApiProviderRegistry.java` | 按 `Api` 而不是 Provider 身份路由。 | 需增加完整 `AiProviderRegistry`。 |
| `modules/ai/.../provider/openai/OpenAICompletionsProvider.java` | 已发送 `stream_options.include_usage=true` 并解析 Chat usage。 | 缺少 Mate 专用 NoAuth/URL/请求字段和完整 reasoning 重放。 |
| `modules/ai/.../types/AssistantMessage.java` | 保存请求模型和 response ID，没有 `responseModel`。 | 原始 chunk 的实际 model 需要可选内部字段保存。 |
| `modules/coding-agent-cli/.../runtimeapi/event/RuntimeEntryCodec.java`：`assistantEntry`、`assistantMessage` | 集中式 Entry 不保存 usage，重建时固定 `Usage.empty()`。 | Token 用量在数据库往返后丢失。 |
| `modules/coding-agent-cli/.../db/gaussdb/install/session_schema.sql` | 已有 `t_session_entries/t_session_sequences/t_session_materialized`。 | 缺少 pi 对应的 Record 和 Stats 表。 |
| `modules/coding-agent-cli/.../persistence/MyBatisRuntimeSessionRepository.java`：`appendLocked` | 每条 Entry 更新 `active_leaf_id`。 | Usage 不能作为 Entry，否则破坏消息分支。 |

上表记录的是初始基线 `d649866a6` 行为；在当前复核基线 `56be8eee` 中，
Mate Chat Provider 和 Usage SQL 已经实现。本次新观察到的配置差距为：

- `modules/coding-agent-cli/src/main/resources/application.yml:89-108` 分别声明
  `campusmate.model-manager.base-url` 和 `campusmate.runtime.base-url`，且默认 origin 不同；
- `application.yml:129-140` 与 `MateToolAutoConfiguration.java:31-81` 又让 Mate Tool
  从 `mate.innerGWSerive` 读取第三个地址，但其接口路径仍都在 `/mate-service/...`；
- `MateServiceModelManagerProvider.java:68-76` 直接读取前者；
- `AgentRuntimeProperties.java:15-34` 与 `MateServiceClient.java:184-197` 使后者成为另一个
  CampusMate 地址权威。

统一地址的目标设计见
[《CampusMate 统一客户端地址配置设计》](../campusmate-shared-client-configuration/README.md)。

### 3.3 mate-service 观察行为

mate-service 基线只有 Agent 模型 ID 绑定，没有模型目录、调用接口或 Usage 表：

- `README.md:116` 只把 `model_id` 描述为模型网关 ID；
- `src/main/resources/db/schema.sql` 只有 `t_agent_binding_models`；
- `SchemaSqlTest` 明确断言当前不存在模型定义表；
- `ApiExceptionHandler` 已采用真实 HTTP 状态及 `resCode/resMsg` 国际化错误体。

因此 `POST /mate-service/v1/LLM/chat` 是 **target-only design**。本文只冻结 CampusClaw 可观察
的 HTTP 语义，不规定 Mate 内部上游适配实现。

### 3.4 OpenAI 协议证据

OpenAI [Chat Completions](https://developers.openai.com/api/reference/cli/resources/chat/subresources/completions)
使用 `messages` 和 Chat Completion chunks；OpenAI
[Responses](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)
使用 `input` 和 `max_output_tokens`。本接口选择 Chat 消息与 Chat SSE，但保留
`max_output_tokens` 作为明确的 Mate 扩展，因此属于 Mate 统一 Chat 契约，不宣称逐字段等同
OpenAI 官方 Chat Completions。

## 4. Provider 与配置

### 4.1 CampusClaw 配置

```yaml
campusmate:
  base-url: ${CAMPUSMATE_BASE_URL}
  model-manager:
    chat-path: ${CAMPUSMATE_MODEL_MANAGER_CHAT_PATH:/mate-service/v1/LLM/chat}
    api: ${CAMPUSMATE_MODEL_MANAGER_API:openai-completions}
```

- `campusmate.base-url` 是 Model Manager、受管 Runtime 与 Mate Tool 共享的部署 origin；
- 它由 `CAMPUSMATE_BASE_URL` 显式提供，没有产品级默认地址；
- `chat-path` 默认保留大小写 `/mate-service/v1/LLM/chat`；
- `api` 只用于 CampusClaw 内部 `Model.api` 和协议适配器选择；
- 当前唯一注册值为 `openai-completions`，配置为未注册值时启动失败；
- Provider 不读取 `Model.baseUrl/apiKey/headers` 构造 Mate 请求。

`campusmate.model-manager.base-url` 和 `CAMPUSMATE_MODEL_MANAGER_BASE_URL` 不再是目标配置，
也不保留为可覆盖共享 origin 的兼容别名。

### 4.2 完整 Provider

```java
public interface AiProvider {
    ProviderId id();

    ProviderAuth auth();

    List<Model> getModels();

    Mono<Void> refreshModels(ModelRefreshContext context);

    AssistantMessageEventStream streamSimple(Model model, Context context, SimpleStreamOptions options);
}
```

`MateServiceModelManagerProvider` 固定：

| 属性 | 目标值 |
|---|---|
| `id()` | `ProviderId("mate-model-manager")` |
| `auth()` | `ProviderAuth.none()` |
| `Model.provider` | `mate-model-manager` |
| `Model.api` | 配置项 `campusmate.model-manager.api`，默认 `openai-completions` |
| HTTP 地址 | `campusmate.base-url + campusmate.model-manager.chat-path` |
| HTTP 凭据 | 无 |

`apiId` 不出现在目录或调用 HTTP 中。保留内部 API 字段是为了兼容当前 Model 类型并对齐 pi
的 Provider/API 分层，不允许调用方通过请求覆盖。

![通用 Provider 与 Mate 边界](generic_provider_boundary.svg)

[PlantUML 源码：`generic_provider_boundary`](diagram.puml#L69)

## 5. Model Manager 接口清单

| # | Method | Path | 状态 | 用途 |
|---:|---|---|---|---|
| 1 | `GET` | `/mate-service/internal/v1/models` | 目标候选 | 全局模型目录和 ETag 刷新 |
| 2 | `GET` | `/mate-service/internal/v1/agents/{agentId}/models` | 目标候选 | Agent 可调用模型列表 |
| 3 | `GET` | `/mate-service/internal/v1/agents/{agentId}/models/{modelId}` | 目标候选 | 原子解析一个可调用模型 |
| 4 | `POST` | `/mate-service/v1/LLM/chat` | 已冻结 | 创建前台流式 Chat 调用 |

1.x 的 `POST /responses` 和 `POST /responses/{responseId}/cancel` 已废止，不构成兼容别名。
剩余四个接口统一依赖内部网关，不携带 `X-HW-ID`、`Authorization`、`X-HW-APPKEY` 或其他
应用身份/凭据。接口 1-3 的字段仍是候选，不因调用接口冻结而自动批准。

模型目录候选详见
[`contract/operations/01-list-models.json`](contract/operations/01-list-models.json) 和
[`model-manager-provider-v1-review.html`](model-manager-provider-v1-review.html)。

## 6. 接口 4：创建前台流式 Chat

### 6.1 路径和请求头

```http
POST /mate-service/v1/LLM/chat
Content-Type: application/json
Accept: text/event-stream
Accept-Language: zh-CN
```

`Accept-Language` 只影响 SSE 建立前的 JSON 错误；成功 SSE 不做语言转换。请求不支持
`Idempotency-Key`，每个 POST 都创建一次新模型消费；结果未知时不得自动重放。

### 6.2 请求示例

```json
{
  "model": "managed-coding-model",
  "messages": [
    {
      "role": "system",
      "content": "You are a coding assistant."
    },
    {
      "role": "user",
      "content": "读取 README.md 并总结"
    },
    {
      "role": "assistant",
      "content": null,
      "reasoning_content": "I need to read the file first.",
      "tool_calls": [
        {
          "id": "call_01",
          "type": "function",
          "function": {
            "name": "read_file",
            "arguments": "{\"path\":\"README.md\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_01",
      "content": "README file content"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "read_file",
        "description": "Read a local file",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {"type": "string"}
          },
          "required": ["path"]
        }
      }
    }
  ],
  "tool_choice": "auto",
  "max_output_tokens": 4096,
  "temperature": 0.2,
  "stream": true,
  "stream_options": {
    "include_usage": true
  }
}
```

### 6.3 顶层字段

| 字段 | 必需性与校验 | Provider/Mate 可观察语义 |
|---|---|---|
| `model` | 必填；1-64 字符；大小写敏感 | Mate 模型 ID；CampusClaw 原样发送 |
| `messages` | 必填非空数组 | 只允许第 6.4 节四种角色并保持顺序 |
| `tools` | 可选数组 | 首版只允许 `type=function` |
| `tool_choice` | 可选；`auto` 或 `none` | 普通 Loop 省略；摘要调用传 `none` |
| `max_output_tokens` | 可选正整数 | Mate 扩展；CampusClaw 不改名、不截断；省略时不以 `Model.maxTokens` 补值 |
| `temperature` | 可选；`0 <= value <= 2` | 省略使用 Mate 配置；显式值是本次调用覆盖 |
| `stream` | 必填且只能为 `true` | 成功响应固定 SSE |
| `stream_options` | 必填对象 | 只允许 `include_usage=true` |

已定义但目标模型不支持的 `temperature/tool_choice/max_output_tokens` 等可选项允许 Mate
静默忽略。接口未定义的顶层或嵌套字段返回 `400 INVALID_LLM_CHAT_REQUEST`，防止双方版本
漂移。请求不接受 `apiId/agentId/sessionId/apiKey/baseUrl/headers/providerId/upstreamModelId`。

### 6.4 messages

| role | content | 附加字段 | 约束 |
|---|---|---|---|
| `system` | 必填字符串 | 无 | Provider 将 `Context.systemPrompt` 作为首个 system message |
| `user` | 必填字符串 | 无 | 首版仅文本，不接受 content part 数组 |
| `assistant` | 字符串或 `null` | `tool_calls`、推理重放字段 | `content=null` 时必须至少有一个 ToolCall |
| `tool` | 必填字符串 | `tool_call_id` | ID 必须匹配此前 Assistant ToolCall |

Assistant ToolCall 采用：

```json
{
  "id": "call_01",
  "type": "function",
  "function": {
    "name": "read_file",
    "arguments": "{\"path\":\"README.md\"}"
  }
}
```

历史 Assistant 允许白名单字段 `reasoning_content`、`reasoning`、`reasoning_text` 和
`reasoning_details`。这些值来自上一次原始模型响应，CampusClaw 保存并按
`ThinkingContent.thinkingSignature` 原样重放；Mate 不要求调用方重新生成推理内容。
`reasoning_details` 为不透明 JSON 数组，其他三个字段为字符串。推理字段不得进入普通日志。

首版不支持图片、音频、文件、content part 数组或 Tool 图片结果。Provider 必须在 HTTP
请求前返回明确的本地不支持错误，不得丢弃非文本块后继续调用。

### 6.5 tools

只接受以下公共子集：

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read a local file",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string"}
      }
    }
  }
}
```

`name` 和 `parameters` 必填，`description` 可选；不支持 `strict`、厂商内置工具或任意扩展
属性。Mate 不执行 Tool；模型返回 `assistant.tool_calls` 后仍由 AgentLoop 执行，并把结果
作为下一轮 `role=tool` 消息。

### 6.6 成功 SSE

成功返回原始 OpenAI 风格 Chat Completion SSE：

```text
data: {"id":"chatcmpl_01","object":"chat.completion.chunk","model":"upstream-model","choices":[{"index":0,"delta":{"role":"assistant","content":"总结结果"},"finish_reason":null}]}

data: {"id":"chatcmpl_01","object":"chat.completion.chunk","model":"upstream-model","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: {"id":"chatcmpl_01","object":"chat.completion.chunk","model":"upstream-model","choices":[],"usage":{"prompt_tokens":120,"completion_tokens":24,"total_tokens":144}}

data: [DONE]
```

- 不包装 `resCode/resMsg/result`；
- 不解析后重新编码，不重写 `id/model/choices/usage/finish_reason/reasoning`；
- usage chunk 允许缺失，即使请求固定要求 `include_usage=true`；
- 原始 `model` 可能是上游值，仅允许在 CampusClaw 内部保存为 `responseModel`，不得进入公共
  Session API 或普通日志；
- `[DONE]` 原样结束正常流。

精确 operation 及独立评审页见
[`contract/operations/04-create-chat.json`](contract/operations/04-create-chat.json) 和
[`model-chat-v2-review.html`](model-chat-v2-review.html)。

### 6.7 错误

SSE 建立前使用真实 HTTP 状态和仅含 `resCode/resMsg` 的公司错误体：

| HTTP | resCode | 语义 |
|---:|---|---|
| 400 | `INVALID_LLM_CHAT_REQUEST` | JSON、字段、消息、Tool 或固定 stream 参数非法 |
| 404 | `MODEL_NOT_FOUND` | Mate 模型 ID 不存在 |
| 429 | `MODEL_RATE_LIMITED` | Mate 或上游限流，可带 `Retry-After` |
| 502 | `UPSTREAM_MODEL_ERROR` | 上游在 SSE 建立前返回协议错误 |
| 503 | `MODEL_UNAVAILABLE` | 模型或路由不可用 |
| 503 | `MANAGER_UNAVAILABLE` | Mate Model Manager 暂时不可用 |
| 504 | `MODEL_INVOCATION_TIMEOUT` | SSE 建立前等待模型响应超时 |

SSE 建立后 HTTP 状态不能再改变。Mate 发送：

```text
event: error
data: {"resCode":"UPSTREAM_STREAM_ERROR","resMsg":"The upstream model stream failed."}
```

随后直接关闭连接且不发送 `[DONE]`。调用方主动取消不是流错误，不发送该事件。

### 6.8 取消、重试与竞争

- 调用方取消时 Provider 关闭 HTTP 请求和 SSE body；Mate 收到下游断连后结束上游工作；
- 无论是否已收到 Chat Completion ID，都不发送第二个取消请求；
- Provider 将调用方取消映射为 `StopReason.ABORTED`；
- 非取消的传输、协议或上游失败映射为 `StopReason.ERROR`；
- 取消与正常完成竞争时只向 AgentLoop产生一个终态；
- 结果未知的创建请求不得自动重放，避免重复消费。

![Mate Chat 调用与断连取消](model_manager_invocation_sequence.svg)

[PlantUML 源码：`model_manager_invocation_sequence`](diagram.puml#L142)

## 7. AgentLoop 与 Chat 映射

| AgentLoop/Provider 输入 | Mate Chat 请求 | 规则 |
|---|---|---|
| `Model.id` | `model` | 原样 Mate 模型 ID |
| `Context.systemPrompt` | 首个 `system` message | 空值时不生成 |
| `UserMessage` 文本 | `user.content` | 保留消息顺序；非文本拒绝 |
| `AssistantMessage` 文本 | `assistant.content` | 多个文本块按原顺序拼接 |
| `AssistantMessage.ToolCall` | `assistant.tool_calls[]` | arguments 序列化为 JSON 字符串 |
| `ToolResultMessage` | `tool` message | `tool_call_id` 关联 ToolCall；content 为字符串 |
| `ThinkingContent.thinkingSignature` | Assistant reasoning 白名单字段 | 按保存的字段种类重放 |
| Agent Tool | `tools[].function` | JSON Schema 原样投影；不发送 `strict` |
| `SimpleStreamOptions.toolChoice` | `tool_choice` | 只允许 `auto/none` |
| 显式 `SimpleStreamOptions.maxTokens` | `max_output_tokens` | 未显式设置时省略，不用 `Model.maxTokens` 补值 |
| 显式 temperature | `temperature` | 未设置时省略 |
| `ThinkingLevel` | 不发送 | 推理开关和 effort 完全由 Mate 模型配置决定 |
| 固定传输字段 | `stream/stream_options` | 固定 `true` 和 `include_usage=true` |

Provider 解析原始 Chat SSE：

- `chunk.id` → `AssistantMessage.responseId`；
- 请求的 Mate 模型 ID → `AssistantMessage.model`；
- `chunk.model` → 可选 `AssistantMessage.responseModel`；
- `delta.content` → Text 事件；
- `delta.reasoning_content/reasoning/reasoning_text/reasoning_details` → Thinking 事件和签名；
- `delta.tool_calls` → ToolCall start/delta/end；
- `finish_reason` → `STOP/LENGTH/TOOL_USE/ERROR`；
- usage → `Usage`，其中 output 已包含 reasoning token；上游给出 breakdown 时可保留 reasoning；
- `[DONE]` → 正常流结束。

```java
public interface ManagedModelInvocationClient {
    AssistantMessageEventStream createChat(ManagedChatRequestDTO request);
}
```

客户端没有 `cancelResponse`。HTTP DTO 只表达本节 JSON，不接收或返回 AgentLoop Java 类型。

![Java Provider 与 pi 对齐](java_provider_alignment.svg)

[PlantUML 源码：`java_provider_alignment`](diagram.puml#L226)

## 8. Token 用量持久化

### 8.1 当前问题

CampusClaw 内存和本地 JSONL 可以保留 `AssistantMessage.usage`，但集中式 Runtime 投影只把
Assistant content 和 finish reason 写入 `t_session_entries`，重建时固定使用
`Usage.empty()`。`t_session_materialized` 虽曾在注释中预留 `lifetimeUsage`，当前没有写入
路径，也不是 pi 当前 SQL 的对应结构。

### 8.2 目标表

目标 openGauss 设计对齐 pi 的 `records` 与 `session_stats`，使用公司表名前缀：

#### `t_session_records`

| 字段 | 建议类型 | 语义 |
|---|---|---|
| `session_id` | `VARCHAR(128)` | 所属 Session |
| `record_seq` | `BIGINT` | 与 Entry 共用会话全局序号 |
| `id` | `VARCHAR(128)` | 会话内不可复用的 Record ID |
| `lane` | `VARCHAR(64)` | 当前固定 `main` |
| `run_id` | `VARCHAR(128)` | 一次接受的用户执行 ID |
| `type` | `VARCHAR(64)` | 首版为 `usage` |
| `op_kind` | `VARCHAR(64)` | 可选 operation 分类 |
| `timestamp` | `TIMESTAMPTZ(3)` | Record 产生时间 |
| `payload` | `JSONB` | 类型相关不可变数据 |

主键为 `(session_id, id)`，唯一约束为 `(session_id, record_seq)`；至少建立
`(session_id, type, record_seq)`、`(session_id, lane, record_seq)` 和
`(session_id, run_id, record_seq)` 索引。

#### `t_session_stats`

| 字段 | 建议类型 | 初始值 |
|---|---|---:|
| `session_id` | `VARCHAR(128)` 主键 | Session 创建时写入 |
| `message_count` | `BIGINT` | 0 |
| `cached_tokens` | `BIGINT` | 0 |
| `uncached_tokens` | `BIGINT` | 0 |
| `total_tokens` | `BIGINT` | 0 |
| `cost_total` | `NUMERIC(30,12)` | 0 |

Token 字段和费用必须非负。费用单位沿用 `ModelCost/Usage.cost` 的美元语义；使用 NUMERIC 是
openGauss 数据质量加固，不要求复制 SQLite 的 REAL 物理类型。

### 8.3 Usage Record

```json
{
  "cause": "assistant",
  "entryId": "entry-assistant-01",
  "attempt": 1,
  "stopReason": "stop",
  "usage": {
    "input": 100,
    "output": 24,
    "cacheRead": 20,
    "cacheWrite": 0,
    "totalTokens": 144,
    "cost": {
      "input": 0.001,
      "output": 0.002,
      "cacheRead": 0.0001,
      "cacheWrite": 0,
      "total": 0.0031
    }
  }
}
```

首版至少写 `cause=assistant`；类型同时预留 `compaction/branch_summary/deferred_fetch`。Record
不是公共 Session Entry，不进入历史 SSE 或消息分支。

### 8.4 原子写入和汇总

一次 Assistant 结束必须在同一数据库事务中：

1. 锁定 Session 和 `t_session_sequences`；
2. 分配 Assistant Entry 与 Usage Record 的两个连续全局序号；
3. 插入 Assistant Entry，并把 `active_leaf_id` 更新为 Assistant Entry；
4. 插入 Usage Record，但不修改 `active_leaf_id`；
5. 增加 `message_count` 并更新 `t_session_stats` 的 Usage 汇总；
6. 提交，任一步失败则全部回滚。

汇总规则与 pi 一致：

```text
cached_tokens   += usage.cacheRead
uncached_tokens += usage.input + usage.cacheWrite
total_tokens    += usage.totalTokens
cost_total      += usage.cost.total
```

Entry 与 Record 共用 `t_session_sequences.next_seq`，所以公开 Entry 序号允许出现间隔；它仍然
严格递增并可用于 `afterSeq` 查询。唯一 Record ID 先插入、Stats 后更新，重复写入因唯一约束
整笔回滚，不得重复累计。

`message_count` 统计可恢复为 Agent Context 的持久化 User、Assistant 和 Tool Result 消息；
Thinking、Usage、运行状态和流控制事件不计入消息数。

上游 usage 缺失时严格按 pi 保存全零 Usage 和 Usage Record，不增加 `reported`。这意味着
统计可能低估，但不会把估算值冒充上游报告值。

`t_session_materialized.payload` 删除 `lifetimeUsage` 责任，只保留 `activePath` 等其他物化视图；
Session 创建时初始化 Stats，清理时删除 Records 和 Stats。

![Token Usage Record 与 Stats](token_usage_persistence.svg)

[PlantUML 源码：`token_usage_persistence`](diagram.puml#L292)

## 9. 一致性、安全和日志

- Mate 请求只允许协议头，不允许调用方身份、API Key、任意 endpoint 或 headers；
- Provider 不自动模型 fallback，不静默切换 Mate modelId；
- 原始 SSE 可能携带上游 model/ID/reasoning，不记录完整流、prompt、Tool 参数或 thinking；
- JSON 错误不得暴露 endpoint、credential、私有路由、stack trace 或推理正文；
- Agent 绑定只用于接口 2/3 的模型选择，不进入接口 4 调用鉴权；
- 接口 4 不发送 `agentId`，Mate 不以调用阶段重新校验 Agent 绑定；
- 请求和响应设置连接、首字节、流空闲、总执行时间与缓冲上限，但具体数值由部署配置管理；
- 调用方断开连接后不得让前台模型任务继续无界运行；
- Usage Record 与 Assistant Entry 的事务失败必须中止会话执行，不能只记录日志后继续。

## 10. 差异分类

| 分类 | 2.0 设计差异 | 原因 |
|---|---|---|
| 架构改造 | Responses create/cancel 改为单个前台 Mate Chat POST。 | 响应天然属于发起请求，断连即可表达取消。 |
| 架构改造 | 成功响应改为原始 Chat SSE，不改写 model 或事件。 | CampusClaw Provider 直接复用 Chat 解析语义。 |
| 架构改造 | Java 按 ProviderId 选择完整 Provider，apiId 仅内部配置。 | 对齐 pi Provider 身份，同时隐藏协议选择。 |
| 架构改造 | Model Manager、受管 Runtime 与 Mate Tool 共用 `campusmate.base-url`。 | 三类接口属于同一 CampusMate 部署 origin。 |
| 架构改造 | 新增 `t_session_records/t_session_stats`。 | 对齐 pi SQL，避免 Usage 成为分支 Entry。 |
| 安全加固 | 子模块只配置 `/mate-service/` 路径，不能覆盖 host。 | 防止单个客户端被配置改道到其他 origin。 |
| 产品约束 | `providerId=mate-model-manager`、`ProviderAuth.none()`。 | CampusClaw 与 Mate 经内部网关互信。 |
| 产品约束 | 请求不带 agent/session/API/凭据/上游信息。 | 保持调用与业务授权、连接配置分离。 |
| 产品约束 | `tool_choice` 只支持 `auto/none`。 | 覆盖 pi 普通 Loop 和摘要调用的通用语义。 |
| 产品约束 | 推理 effort 不进入请求。 | 推理开关和强度完全由 Mate 模型配置管理。 |
| 产品约束 | 首版文本-only；图片和 Tool 图片在 Provider 本地失败。 | 冻结最小可靠 Chat 契约，禁止静默数据丢失。 |
| Mate 扩展 | Chat 请求使用 `max_output_tokens`。 | 用户确认的 Mate 接口字段，不宣称官方 Chat 标准。 |
| Mate 扩展 | SSE 建立后使用 `event:error` + ResultBean 错误数据。 | HTTP 状态已固定，仍需稳定机器错误码。 |
| pi 对齐限制 | usage 缺失按全零处理。 | pi Usage 没有 reported/available 标志。 |
| 数据加固 | openGauss Stats 使用 BIGINT/NUMERIC。 | 保留 pi 语义并避免浮点汇总误差。 |

Mate 的上游模型映射、字段改名、endpoint、credential 注入、请求重试和厂商兼容策略不由本文
规定。本文只定义 CampusClaw→Mate 请求和 Mate→CampusClaw 可观察响应。

## 11. 目标迁移顺序

1. 引入开放 `ProviderId/ApiId/AiProvider/AiProviderRegistry` 和 `ProviderAuth.none()`；
2. 增加共享 `campusmate.base-url`，删除 Model Manager、Runtime 和 Mate Tool 的独立地址键，
   并在启动时验证 URI 与 apiId；
3. 实现 `MateServiceModelManagerProvider`，复用/提取 OpenAI Completions 转换与解析能力；
4. 增加 `AssistantMessage.responseModel` 和 reasoning 重放支持；
5. 实现 `/mate-service/v1/LLM/chat` 客户端，关闭 SDK 自动创建重试；
6. 删除 Runtime Responses create/cancel 路径和 Response ID 取消逻辑；
7. 增加 `t_session_records/t_session_stats` 及同事务 Assistant+Usage 写入；
8. 生产配置切换到 Mate Provider 后关闭 Runtime 直连厂商和自动 fallback。

## 12. 验收标准

### HTTP 与 Provider

- 完整 URL 为 `${CAMPUSMATE_BASE_URL}/mate-service/v1/LLM/chat`，其 origin 与受管 Runtime、
  Mate Tool 请求完全一致；
- `campusmate.model-manager.base-url`、`campusmate.runtime.base-url`、`mate.innerGWSerive`
  和三个旧应用环境变量已删除；
- 默认内部 apiId 为 `openai-completions`，未知配置导致启动失败且不发请求；
- 请求不包含身份/凭据、Agent/Session、apiId 或上游连接信息；
- 文本、四种消息、Assistant ToolCall、ToolResult 和四类 reasoning 重放字段转换正确；
- 图片、音频、文件和 Tool 图片在 Provider 本地失败且无 HTTP 请求；
- 普通 Loop 省略 `tool_choice`，摘要使用 `none`；
- 未设置每次调用 maxTokens 时省略 `max_output_tokens`；显式值不改名、不截断；
- `stream=false`、缺少 include_usage、未知字段和未知模型返回冻结错误；
- 已定义但模型不支持的可选参数允许忽略；
- 成功 SSE 的字节内容、字段和值不被 Mate 改写，正常流以 `[DONE]` 结束；
- usage 存在和缺失两种成功流都能完成；
- SSE 前错误使用 HTTP + ResultBean，SSE 后错误使用 `event:error` 后关闭；
- 调用方断连映射 `ABORTED`，普通失败映射 `ERROR`；
- 网络结果未知时不重放创建 POST。

### Token SQL

- Usage Record 不出现在当前分支，不更新 `active_leaf_id`；
- Assistant Entry、Usage Record、Stats 成功时全部提交，任一失败时全部回滚；
- Entry/Record 共用序号且 Entry 查询可跨过内部序号间隔；
- 重复 Record ID 不重复累计 Stats；
- cached、uncached、total 和 cost 的累计与 pi 公式一致；
- usage 缺失时保存全零记录；
- Session 删除同步清理 Records 和 Stats；
- `t_session_materialized` 不再保存 lifetimeUsage。

### 文档制品

- operation JSON 可解析，HTML 中没有认证页签、凭据头或 401/403；
- HTML 在桌面、360px 和禁用 JavaScript 时均可阅读；
- Markdown 不含 Mermaid；PlantUML 全部 ASCII；
- `plantuml -tsvg diagram.puml` 成功，SVG 是合法 XML 且与源码同步；
- Markdown SVG 链接和 PlantUML 行锚有效；
- `git diff --check` 通过。

## 13. 当前评审状态

已冻结：

- 单一 `mate-model-manager` 通用 Provider；
- 内部网关免应用层认证；
- `POST /mate-service/v1/LLM/chat` 请求、原始 SSE、错误、断连取消和不重试语义；
- CampusClaw 内部 apiId 默认 `openai-completions` 且可配置；
- Model Manager、受管 Runtime 与 Mate Tool 共用唯一 `campusmate.base-url`；
- pi 对齐的 Usage Record + Session Stats 持久化目标。

仍为候选：接口 1-3 的目录字段、Mate 管理面和 Mate 内部上游适配实现。

评审入口：

- [`model-manager-provider-v1-review.html`](model-manager-provider-v1-review.html)：接口 1 候选；
- [`model-chat-v2-review.html`](model-chat-v2-review.html)：已冻结 Chat 调用契约。

## 14. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.2.0 | 2026-08-26 | 将 Mate Tool 纳入共享 CampusMate origin，删除 `mate.innerGWSerive` 独立地址目标配置并同步验收范围。 |
| 2.1.0 | 2026-08-26 | 将 Model Manager 地址收敛到 Model Manager 与受管 Runtime 共用的 `campusmate.base-url`，删除独立 base URL 目标配置，同步当前实现复核基线。 |
| 2.0.0 | 2026-08-24 | 用 `POST /mate-service/v1/LLM/chat` 替换 Responses create/cancel；冻结 OpenAI 风格 messages、原始 Chat SSE、断连取消、配置化 `openai-completions` 内部 apiId、Token Usage Record 与 Stats SQL 对齐。 |
| 1.3.0 | 2026-08-23 | 五个 Model Manager 接口采用内部网关免应用层认证；Mate Provider 使用 `ProviderAuth.none()`。 |
| 1.2.0 | 2026-08-22 | Responses create 采用语义透明代理。 |
| 1.1.0 | 2026-08-22 | 冻结 Responses create/cancel 和前台取消扩展。 |
| 1.0.0 | 2026-08-21 | 明确 Provider 身份、Java 对齐、Mate 托管调用和五项运行接口候选。 |
