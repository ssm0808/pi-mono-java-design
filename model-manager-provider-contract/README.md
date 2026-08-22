# MateService Model Manager 通用 Provider 对接设计

| 属性 | 值 |
|---|---|
| 文档版本 | 1.2.0 |
| 状态 | 目标设计；资源模型已确认；接口 4、5 已冻结，接口 1-3 保持候选 |
| 设计日期 | 2026-08-22 |
| pi-mono 源码基线 | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` |
| pi-mono-java 源码基线 | `d0efb2fd18f2f2a7db121a1cbd4f039348a8094a` |
| mate-service 源码基线 | `6d5e6f3714e1cf8744d187a4796ca06300ad7e33` |
| 设计仓分析基线 | `11e53de2c2c4a7e5cb498b163995aec6c4580bb4` |
| 适用边界 | pi-mono-java Runtime ↔ mate-service 内部 Model Manager |

## 1. 结论

在 pi-mono 的当前实现中，**确定一个 Provider 身份只需要稳定且唯一的
`provider.id`**。`name`、`baseUrl`、认证信息和 `api` 都不是身份：

- `name` 是展示信息；
- `baseUrl`、headers 和凭据是可变连接配置；
- `api` 是模型使用的协议/流实现，一个 Provider 可以同时承载多个 `api`；
- 模型的运行时唯一键是 `(provider.id, model.id)`，不是单独的 `model.id`；
- 一个可执行的 Provider 除身份外，还必须提供认证语义、模型目录和流式调用实现。

本设计推荐 pi-mono-java 对齐 pi-mono 的完整 Provider 模型，并在 Runtime 中只注册
一个通用 Provider：

```text
providerId = mate-model-manager
apiId      = openai-responses
model key   = (mate-model-manager, <Mate catalog modelId>)
```

mate-service 内部可以管理多个真实上游 Provider，但只把不透明 `modelId` 和运行所需的
安全模型描述投影给 Runtime。上游 `providerId`、厂商模型 ID、base URL、请求 headers
和凭据均不得跨出 mate-service。模型调用也由 mate-service 完成，不把上游配置下发给
pi-mono-java。

资源模型已确认：MateService 托管调用，Runtime 不直连厂商。本版进一步冻结调用与取消
接口：Mate 接受 OpenAI Responses 线协议，Runtime Provider 负责把 AgentLoop `Context`
转换为 Responses 请求，并把 Responses SSE 转换为 `AssistantMessageEvent`。调用接口不携带
`agentId`，也不在调用时校验 Agent 绑定；这是 CampusClaw 与 CampusMate 互信前提下的
产品授权决策，不应误写为 mate-service 当前已实现行为。

创建接口的请求体是可直接发送给 OpenAI Responses 兼容上游的语义载荷。Provider 在
进入 Mate 前完成唯一一次 `AgentLoop Context -> Responses JSON` 转换；Mate 不再把
`input`、`tools`、reasoning 或其他已接受字段转换为 Chat Completions、厂商 DTO 或
自定义消息。Mate 只把目录 `model` 的值替换为私有 `upstreamModelId`，并在 HTTP
连接层注入 endpoint、凭据和受控 headers。仅支持 Chat Completions 的上游不属于本接口。

## 2. 术语和身份边界

本文中的 Provider 专指 LLM Provider，不是 Spring Bean Provider 或消息 Channel。

| 概念 | 身份键 | 作用 | 是否暴露给 Runtime |
|---|---|---|---|
| Runtime 通用 Provider | `mate-model-manager` | pi-mono-java 中模型目录、认证和流式调用的所有者 | 是，固定值 |
| mate-service 上游 Provider | `providerId` | mate-service 内部区分不同供应商、租户端点或网关实例 | 否 |
| Runtime 模型 | `(mate-model-manager, modelId)` | Runtime 选择和比较模型 | 是 |
| 上游模型 | `(providerId, upstreamModelId)` | mate-service 路由到真实厂商模型 | 否 |
| API 协议 | `apiId` | 选择流协议实现，不表示供应商身份 | Runtime 只见固定通用协议 |

身份规则：

1. `providerId` 大小写敏感、创建后不可变、删除后不得复用。
2. 修改名称、端点、凭据引用、headers 或协议实现不创建新身份，只递增资源 revision。
3. 同一 `apiId` 可以被多个 Provider 使用；同一 Provider 可以为不同模型使用多个
   `apiId`。
4. `modelId` 由 Mate 模型目录定义，是 1-64 字符、大小写敏感的不透明字符串；Runtime
   必须原样使用目录返回值，不得解析、构造或强制套用 `model-<32 hex>` 格式。
5. `modelId` 在目录中唯一，并精确映射到 Mate 内部的上游 Provider、端点、凭据和
   `upstreamModelId`；这些私有路由信息不跨出 mate-service。

![Provider 身份与运行契约](provider_identity_model.svg)

[PlantUML 源码：`provider_identity_model`](diagram.puml#L1)

## 3. 源码观察

### 3.1 pi-mono 当前行为

| 证据 | 观察到的行为 |
|---|---|
| `packages/ai/src/models.ts:88-149`，`Provider` | 完整 Provider 拥有 `id/name/baseUrl/headers/auth/getModels/refreshModels/filterModels/stream`，不是单纯协议适配器。 |
| `packages/ai/src/models.ts:225-230,254-318`，`MutableModels`、`ModelsImpl` | Provider 注册表以 `provider.id` 为唯一键；相同 ID 的注册执行替换；模型查询先按 Provider，再按模型 ID。 |
| `packages/ai/src/models.ts:628-695`，`requireProvider`、`stream` | 调用时根据 `model.provider` 找到 Provider，解析并应用该 Provider 的认证，然后委托 Provider 流。 |
| `packages/ai/src/models.ts:739-862`，`CreateProviderOptions`、`createProvider` | 构造可执行 Provider 时 `id/auth/models/api` 必填；`name/baseUrl/headers` 可选；`api` 可为单一实现，也可为按 `model.api` 分派的实现表。 |
| `packages/ai/src/models.ts:934-944`，`modelsAreEqual` | 模型相等要求 `id` 与 `provider` 同时相等。 |
| `packages/ai/src/types.ts:35-76,820-850`，`ProviderId`、`Model` | Provider ID 是开放字符串；Model 明确同时携带 `provider` 与 `api`。 |
| `packages/ai/src/compat.ts:1-10,83-140` | 旧 `ApiProvider` 是迁移期兼容入口，源码说明会随 ModelManager 迁移删除；不能再把它当成新设计基线。 |
| `packages/coding-agent/docs/custom-provider.md:31-91` | 自定义认证、过滤、刷新或流式行为应注册完整 Provider，旧 provider-config 形式仅兼容。 |
| `packages/ai/src/providers/openai.ts:1-15`，`openaiProvider` | OpenAI Provider 使用 `openai-responses` 作为协议实现，Provider 身份与 API 协议分离。 |
| `packages/ai/src/api/openai-responses.ts:99-189,273-344`，`stream`、`buildParams` | Responses 调用使用 `stream=true`、`store=false`，显式关闭 SDK 自动重试，并在 reasoning 调用中请求 `reasoning.encrypted_content`。 |
| `packages/ai/src/api/openai-responses-shared.ts:131-342,500-792`，`convertResponsesMessages`、`processResponsesStream` | Context 被转换为多模态 input、Assistant 输出、函数调用和 Tool 结果；reasoning item 被保存并在后续无状态调用中重放。 |

因此，“确定 Provider”应分成两个问题：

| 问题 | 最小信息 |
|---|---|
| 这个 Provider 是谁 | `provider.id` |
| 这个 Provider 能否执行 | `id` + 认证语义 + 模型目录 + 对应 `api` 的 stream 实现 |

### 3.2 pi-mono-java 当前行为与不足

| 证据 | 观察到的行为 | 与 pi-mono 的差距 |
|---|---|---|
| `modules/ai/src/main/java/com/campusclaw/ai/types/Provider.java:19-37` | Provider 是封闭 enum，未知值只能归入 `CUSTOM`。 | 无法保留任意 Provider 身份。 |
| `modules/ai/src/main/java/com/campusclaw/ai/types/Api.java:16-22` | API 协议也是封闭 enum。 | 已知 `openai-responses` 可复用，但未来扩展协议仍无法开放注册。 |
| `modules/ai/src/main/java/com/campusclaw/ai/provider/ApiProvider.java:31-59` | 所谓 Provider 只提供 `getApi/stream/streamSimple`。 | 实际职责是协议适配器，缺少 Provider 身份、认证和模型目录。 |
| `modules/ai/src/main/java/com/campusclaw/ai/provider/ApiProviderRegistry.java:22-152` | 注册表按 `Api` 索引，最后注册者覆盖。 | 调用按协议而不是按 Provider 身份路由。 |
| `modules/ai/src/main/java/com/campusclaw/ai/CampusClawAiService.java:141-147` | 根据 `model.api()` 查找 `ApiProvider`。 | 同协议的多个 Provider 无法拥有独立运行策略。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/config/CustomModelLoader.java:92-123` | 所有自定义模型都写为 `Provider.CUSTOM`，模型中还可嵌入 API Key。 | Provider 身份塌缩；秘密进入 Model 数据对象。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/model/RuntimeModelManager.java:20-39` | Runtime 已有模型解析端口，但默认 `resolveAvailableModel` 先列表再解析。 | 两次读取之间可能发生停用或解绑，需要服务端原子解析。 |
| `modules/ai/src/main/java/com/campusclaw/ai/provider/openai/OpenAIResponsesProvider.java:174-225,251-541`，`buildParams`、`handleResponseEvent`、`convertInputItems` | 已使用 Responses 请求和事件，但用户图片、Tool 图片结果及 `ThinkingContent` 历史未完整转换。 | 需要对齐 pi-mono 的多模态输入与 stateless reasoning 重放。 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java:198-288`，`invokeModel`、`consumeStream` | AgentLoop 只把 `Model + Context + SimpleStreamOptions` 交给流函数，并在本地取消时停止消费。 | 调用边界没有 `agentId`；Mate Provider 必须从 SSE 捕获 response ID 并补充远程取消。 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/loop/StreamFunction.java:18-33`，`stream` | 流函数签名不包含 Session 或 Agent 身份。 | Mate 调用请求不得虚构 `agentId/sessionId` 字段。 |

本设计以 pi-mono 当前完整 Provider 为基线。pi-mono-java 现有
`ApiProvider/ApiProviderRegistry` 仅作为迁移输入，不作为目标抽象。

### 3.3 mate-service 当前行为

| 证据 | 观察到的行为 |
|---|---|
| `README.md:116` | `model_id` 仅被视为模型网关 ID，当前没有模型网关目录查询接口。 |
| `src/main/resources/db/schema.sql:59-73` | 只有 `t_agent_binding_models(agent_id, model_id, model_order)`，保存有序绑定。 |
| `src/main/java/com/huawei/hicampus/mate/agentdefinition/dto/AgentModelBindingDTO.java:15-22` | Java 数据层同样只保存 Agent、model ID 和顺序。 |
| `src/main/java/com/huawei/hicampus/mate/agentdefinition/validation/ResourceIdRules.java:15-24` | 已定义 `model-` 加 32 位十六进制 UUID 的模型 ID。 |
| `src/test/java/com/huawei/hicampus/mate/agentdefinition/mapper/SchemaSqlTest.java:23-35` | 测试明确断言当前不存在模型表。 |
| `src/main/java/com/huawei/hicampus/mate/agentdefinition/vo/UpdateAgentRequestVO.java:30-36` | 当前 Agent 更新边界仍用上述模型 ID 正则校验绑定值。 |
| `src/main/java/com/huawei/hicampus/mate/agentdefinition/controller/ApiExceptionHandler.java:59-168` | 当前错误响应使用真实 HTTP 状态、`resCode/resMsg` 和 MessageSource 国际化。 |

所以本文的模型目录、上游 Provider、凭据引用、解析、调用和取消能力全部是
**目标设计**，不是 mate-service 已实现行为。目录模型 ID 的 1-64 字符规则也与当前
Agent 更新边界的类型化 UUID 正则不同；该差异属于目标产品约束，后续实现必须统一绑定
校验，但本次不修改 mate-service 代码。

### 3.4 现有设计输入

设计仓基线 `pi-mono-java-manager-driven-multi-agent-runtime/README.md:276-286` 已把
Model Manager 定义为模型描述、可用性、凭据和调用的最终权威，并要求 Runtime 映射
Provider 结构化增量。`pi-mono-java-manager-driven-multi-agent-runtime/chat-http-v1-design.md:614-630`
已确认公共 Session 模型列表只返回 `model_id` 字符串，不暴露 Provider 配置。

本文细化的是 **mate-service Model Manager 到 pi-mono-java Runtime 的内部接口**，不
扩大浏览器或公共 Session API。内部目录为构造 Runtime `Model` 可以携带安全能力和成本
字段；上游身份、端点、headers 和凭据仍不进入内部响应，公共模型列表仍只投影模型 ID。

### 3.5 OpenAI 官方协议基线

- OpenAI [Create a model response](https://developers.openai.com/api/reference/typescript/resources/beta/subresources/responses/methods/create)
  定义 `POST /responses`、字符串或 item 数组输入、流式 Response 事件以及包含 `id/model`
  的 Response 对象；官方示例直接使用 `input_text/input_image`、function tool、
  `reasoning` 和 `stream=true`。本接口使用相同字段和嵌套结构，不建立第二套输入模型。
- OpenAI Responses 类型说明把 `reasoning.encrypted_content` 定义为 `store=false` 等无状态
  场景下重放 reasoning item 的包含项；本设计据此对齐 pi-mono 的 reasoning 签名保留。
- OpenAI [Cancel a response](https://developers.openai.com/api/reference/cli/resources/beta/subresources/responses/methods/cancel)
  定义 `POST /responses/{response_id}/cancel` 并返回 Response 对象，但官方只保证取消
  `background=true` 的响应。Mate 对前台活动流的取消是明确标注的兼容扩展。

## 4. 目标 Provider 契约

### 4.1 Provider 信息分层

| 分层 | 字段/能力 | 必需性 | 说明 |
|---|---|---:|---|
| 身份 | `providerId` | 必需 | 唯一决定 Provider；Runtime 固定为 `mate-model-manager`。 |
| 展示 | `displayName` | 必需但不参与身份 | 默认可等于 `providerId`。 |
| 连接 | `baseUrl`、默认 headers | 可选 | 对通用 Provider 指向 mate-service，不是上游厂商地址。 |
| 认证 | `auth` / service credential resolver | 必需 | 认证 Runtime 到 mate-service；不包含上游凭据。 |
| 目录 | `getModels()` | 必需 | 同步返回最后一次成功发布的模型目录。 |
| 刷新 | `refreshModels()` | 动态目录必需 | 使用 `GET /models` + ETag 更新；失败保留上一成功目录。 |
| 过滤 | `filterModels()` | 可选 | 只适合凭据维度过滤；Agent 授权不得塞入此无上下文函数。 |
| 调用 | `stream/streamSimple` | 必需 | 调用 mate-service SSE 并映射统一事件。 |
| 延迟结果 | `fetchDeferred/cancelDeferred` | 首版不支持 | 以后若上游出现异步 Job 再独立设计。 |

### 4.2 Runtime 模型投影

Mate-service 内部模型描述投影为 pi-mono-java `Model` 时采用：

| Java Model 字段 | 来源 |
|---|---|
| `id` | `modelId` |
| `name` | `displayName` |
| `provider` | 固定 `ProviderId("mate-model-manager")` |
| `api` | 固定 `ApiId("openai-responses")` |
| `baseUrl` | Provider 客户端配置中的 mate-service 内部地址，不取响应字段 |
| `reasoning` | `reasoningSupported` |
| `thinkingLevelMap` | `thinkingLevelMap` |
| `input` | `inputModalities` |
| `cost` | `cost`，按 pi 的每百万 token 费率语义 |
| `contextWindow` | `contextWindow` |
| `maxTokens` | `maxOutputTokens` |
| `headers` | 空；调用上下文由受控 HTTP client 添加 |
| `apiKey` | 删除；Provider 通过 service credential resolver 认证 |

通用 Provider 的 `getModels()` 是全局目录，不承担 Agent 权限。接口 2、3 仍可在模型选择
阶段提供 Agent 维度目录或解析，但已冻结的调用接口只依据服务身份和 `model` 目录 ID
执行，不再次校验 Agent 绑定。

## 5. 总体架构

![通用 Provider 与 MateService 边界](generic_provider_boundary.svg)

[PlantUML 源码：`generic_provider_boundary`](diagram.puml#L73)

职责固定如下：

| 组件 | 职责 |
|---|---|
| `AiProviderRegistry` | 以开放 `ProviderId` 注册和解析完整 Provider。 |
| `MateServiceModelManagerProvider` | 拥有通用 Provider 身份、目录缓存、服务认证和事件映射。 |
| `ManagedModelCatalogClient` | 调用全局目录、Agent 可调用目录和原子解析接口。 |
| `ManagedModelInvocationClient` | 发送 Responses JSON、接收 Responses SSE，并按 response ID 显式取消。 |
| mate-service Model Manager | 管理真实 Provider、模型、凭据引用、路由、限流、调用和审计。 |
| mate-service OpenAI 透明代理 | 校验 Responses 子集，不重组请求体；只替换请求 `model`、注入私有连接配置，并把响应 `model` 改回 Mate 模型 ID。 |
| `AgentLoop` | 维护上下文、执行 Tool、继续下一轮模型调用。 |

## 6. MateService 运行时接口清单

基础路径：`/mate-service/internal/v1`。这些接口只面向 pi-mono-java Runtime 或其他已授权
内部服务，不是浏览器公共 API。

| # | Method | Path | Provider/Runtime 用途 | 当前状态 |
|---:|---|---|---|---|
| 1 | `GET` | `/models` | 完整 Provider 的 `getModels/refreshModels` 全局目录来源 | 目标候选；资源模型已确认，字段待评审 |
| 2 | `GET` | `/agents/{agentId}/models` | 按 `model_order` 返回当前可调用模型，用于选择器和默认模型解析 | 目标候选 |
| 3 | `GET` | `/agents/{agentId}/models/{modelId}` | 在一次服务端读中校验绑定、模型、Provider 和凭据状态并返回描述 | 目标候选 |
| 4 | `POST` | `/responses` | 创建一次 OpenAI Responses 兼容的前台流式调用 | 已冻结；目标设计 |
| 5 | `POST` | `/responses/{responseId}/cancel` | 取消仍处于活动状态的前台流式响应 | 已冻结；目标设计 |

Provider 管理 CRUD、凭据轮换、模型发布和 Agent 绑定管理属于管理面，不是 Provider 对接
所需运行时接口；本主题不擅自定义这些公共/管理接口。

### 6.1 公共 HTTP 规则

- JSON 使用 Jackson 默认 lower camel case；不得配置全局 `SNAKE_CASE`。Java Controller
  使用 Request/Response VO，只有真实字段例外才增加显式 Jackson 属性注解。
- 接口 4、5 的 OpenAI Responses wire 字段是明确例外：保留
  `max_output_tokens/input_text/input_image/function_call` 等官方 snake_case 名称，使用
  字段级 Jackson 映射，不得改成 lower camel case，也不得启用全局 `SNAKE_CASE`。
- 普通 JSON 成功返回 `{"resCode":"0","resMsg":"success","result":...}`；错误只返回
  `resCode/resMsg` 并使用真实 HTTP 状态。接口 4 的成功 SSE 和接口 5 的成功 Response
  对象为 Responses 兼容例外，不使用 ResultBean。
- 内部接口接受两种替代认证：`X-HW-ID + Authorization: Bearer <JWT>`，或
  `X-HW-ID + X-HW-APPKEY`。一次请求必须且只能提供一组完整凭据；两组同时出现返回
  `401 AUTH_CREDENTIAL_CONFLICT`。
- JSON 错误消息按 `Accept-Language` 国际化；稳定机器判断只依赖 `resCode`。
- 不在业务 JSON 中发明 trace ID。分布式追踪由平台 HTTP instrumentation 处理。

### 6.2 接口 1：全局模型目录

`GET /models` 返回所有当前启用且拥有可用 Provider 配置的模型。它不应用 Agent 绑定，
不分页；目录按 `modelId` 稳定排序。条件响应使用强 ETag：

```http
GET /mate-service/internal/v1/models
If-None-Match: "model-catalog-42"
```

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "catalogRevision": 42,
    "models": [
      {
        "modelId": "managed-coding-model",
        "displayName": "Managed General Model",
        "reasoningSupported": true,
        "thinkingLevelMap": {
          "off": "off",
          "low": "low",
          "medium": "medium",
          "high": "high"
        },
        "inputModalities": ["text", "image"],
        "cost": {
          "input": 0,
          "output": 0,
          "cacheRead": 0,
          "cacheWrite": 0
        },
        "contextWindow": 128000,
        "maxOutputTokens": 8192,
        "modelRevision": 7
      }
    ]
  }
}
```

`providerId`、`upstreamModelId`、`baseUrl`、credential 状态和上游 headers 不进入响应。
没有变化时返回 `304` 且无 body。刷新失败时 Runtime Provider 保留最后一次成功目录，
同时把失败暴露为可观测状态；不得把目录清空。

精确候选契约及资源模型比较见
[`contract/operations/01-list-models.json`](contract/operations/01-list-models.json) 和生成的
[`model-manager-provider-v1-review.html`](model-manager-provider-v1-review.html)。

### 6.3 接口 2：Agent 可调用模型

`GET /agents/{agentId}/models` 在一次请求中联结当前 `t_agent_binding_models`、模型启用
状态、Provider 启用状态和凭据可用性，按 `model_order` 返回完整安全描述。它支持
`RuntimeModelManager.listAvailableModels`，不需要 Runtime 先下载全局目录再自行猜测
权限。

- 响应使用 `Cache-Control: no-store`，因为它是实时授权结果；
- Agent 存在但当前无可调用模型时返回 `200` 和空数组；
- Agent 不存在返回 `404 AGENT_NOT_FOUND`；
- 不返回已绑定但当前停用或凭据不可用的模型。

### 6.4 接口 3：原子解析一个可调用模型

`GET /agents/{agentId}/models/{modelId}` 必须在一次一致性读取中确认：

1. Agent 存在且启用；
2. 当前 Agent 仍绑定该模型；
3. 模型存在且启用；
4. 上游 Provider 存在且启用；
5. 数据库中的 `credential_ref` 可解析，但不返回凭据；
6. 模型描述完整且可投影为 Runtime Model。

成功返回与接口 1 相同的单个安全模型描述。不存在或不可调用统一返回
`404 MODEL_NOT_CALLABLE`，避免通过错误差异枚举其他 Agent 的模型。Manager 故障返回
`503 MANAGER_UNAVAILABLE`。

pi-mono-java 的 `RuntimeModelManager.resolveAvailableModel` 必须覆盖现有默认实现并直接
调用本接口，不能再先调用 list 再 resolve。Session 执行路径中的 `resolveModel` 也调用
本接口，确保执行前重新授权。

### 6.5 接口 4：创建流式模型调用

`POST /responses` 使用 OpenAI Responses 请求和成功 SSE 结构。它是 Responses 线协议的
透明受控子集，不接收 `AgentLoop` 的 Java 对象，也不接收 `agentId`、`sessionId` 或
`invocationId`。将请求中的目录 `model` 替换成真实上游模型 ID 后，body 可以直接发往
配置的 OpenAI Responses 兼容 `POST /responses`，不需要协议或消息结构转换：

```json
{
  "model": "managed-coding-model",
  "instructions": "You are a coding assistant.",
  "input": [
    {
      "role": "user",
      "content": [
        {"type": "input_text", "text": "请分析这张图片"},
        {"type": "input_image", "detail": "auto", "image_url": "data:image/png;base64,..."}
      ]
    },
    {
      "type": "function_call",
      "id": "fc_01",
      "call_id": "call_01",
      "name": "read_file",
      "arguments": "{\"path\":\"/workspace/README.md\"}"
    },
    {
      "type": "function_call_output",
      "call_id": "call_01",
      "output": "file content"
    }
  ],
  "tools": [
    {
      "type": "function",
      "name": "read_file",
      "description": "Read a local file",
      "parameters": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"]
      },
      "strict": false
    }
  ],
  "max_output_tokens": 4096,
  "temperature": 0.2,
  "reasoning": {"effort": "medium", "summary": "auto"},
  "include": ["reasoning.encrypted_content"],
  "stream": true,
  "store": false,
  "background": false
}
```

字段契约：

| 字段 | 必需性与约束 | Mate 行为 |
|---|---|---|
| `model` | 必填；1-64 字符；大小写敏感；必须精确匹配目录返回值 | 解析私有路由并替换为 `upstreamModelId`；不得按固定前缀解析 |
| `input` | 必填；字符串或 Responses `ResponseInputItem[]` | 数组允许文本、图片、历史 Assistant message、`function_call`、`function_call_output` 和 reasoning item |
| `instructions` | 可选字符串 | 作为 system/developer 指令转发 |
| `tools` | 可选；首版只接受 `type=function` | 保留 `name/description/parameters/strict`，不执行 Tool |
| `max_output_tokens` | 可选正整数 | 不能超过目录模型上限 |
| `temperature` | 可选；Responses 数值语义 | 不支持该选项的模型返回 `MODEL_OPTION_UNSUPPORTED` |
| `reasoning` | 可选 Responses reasoning 对象 | effort 等值按目录能力校验 |
| `include` | 可选；首版只允许 `reasoning.encrypted_content` | 支持 `store=false` 下的无状态 reasoning 重放 |
| `stream` | 必填且只能为 `true` | 原值转发；成功响应始终为 SSE |
| `store` | 必填且只能为 `false` | 原值转发；Mate 不补默认值，也不建立可检索的服务端会话 |
| `background` | 必填且只能为 `false` | 原值转发；首版只支持前台流式调用 |

`previous_response_id`、`conversation`、`metadata`、`apiKey`、`baseUrl`、任意请求
headers、`providerId`、`upstreamModelId`、Chat Completions `messages` 和未列出的 Responses
字段均不支持；`stream_options` 也不进入首版白名单。未知或不支持字段返回
`400 INVALID_RESPONSE_REQUEST`。透明代理表示“已接受的 Responses 字段不转换”，不表示
无条件透传任意字段。

Mate 解析请求只用于认证、字段白名单、能力和限额校验。校验成功后以原始 JSON 语义树
构造上游请求，只修改 `model` 的值；`input`、`instructions`、`tools`、
`max_output_tokens`、`temperature`、`reasoning`、`include`、`stream`、`store`
和 `background` 的字段名、嵌套结构、数组顺序和值均不得重组、降级或丢弃。JSON
重新编码导致的属性顺序或空白变化不属于协议转换。

Mate 在 HTTP 连接层注入私有 endpoint、凭据和受控 headers；这些值不进入 body。上游必须
原生支持 OpenAI Responses 协议。Mate 不允许把该请求转换为 `/chat/completions`、厂商
消息格式或另一个模型 API；不兼容的目录路由返回 `MODEL_UNAVAILABLE`，后续如需
Chat Completions 必须设计独立 `apiId` 和 operation。

上游返回后，`response.id` 原样透传；所有 SSE Response 对象中的 `response.model`
改回请求中的 Mate 模型 ID。其余成功事件保持 OpenAI Responses 结构，包括
`response.created`、output item 生命周期、文本/reasoning/函数参数增量和
`response.completed/response.incomplete/response.failed/error`。这是语义透明代理，
不是字节透传。

发送首个 SSE 字节前的失败使用普通 ResultBean。SSE 已开始后不再改写 HTTP 状态，错误
使用 Responses `error`、`response.failed` 或 `response.incomplete`。Tool 实际执行和下一轮
上下文组装仍由 `AgentLoop` 完成。

该 POST 不支持 `Idempotency-Key`，每次请求都创建新的模型消费。连接结果未知时 Runtime
不得自动重放 POST。

### 6.6 接口 5：取消模型调用

`POST /responses/{responseId}/cancel` 使用从 `response.created.response.id` 获得的 OpenAI
response ID。ID 大小写敏感且只能原样传回；Mate 不生成第二套调用 ID。

- 仅仍处于活动状态的响应可以取消；成功返回 `200` 和 Responses Response 对象，
  `status=cancelled`，`id` 保持上游值，`model` 改回 Mate 模型 ID；成功体不使用 ResultBean。
- Mate 不保存终态。响应完成、失败、已取消或不存在时统一返回
  `404 RESPONSE_NOT_ACTIVE` ResultBean；因此重复取消不是幂等操作。
- 取消成功后原 SSE 连接直接结束，不发送伪造的 `response.completed`，也不增加非标准
  `response.cancelled` 事件。
- Provider 本地收到取消且已知 response ID 时调用本接口；尚未收到 `response.created` 时
  只关闭 SSE。两条路径都在 AgentLoop 收敛为 `StopReason.ABORTED`。
- 取消与正常完成竞争时，只有先完成状态迁移的一方成功；正常完成先发生时取消返回 404。
- 官方 OpenAI 取消只保证 `background=true` 响应；本接口把相同路径扩展为 Mate 的前台
  活动流取消。Mate 如何保存活动句柄或处理多实例路由属于其内部实现，不进入对接契约。

精确请求、响应和错误示例见
[`contract/operations/04-create-response.json`](contract/operations/04-create-response.json)、
[`contract/operations/05-cancel-response.json`](contract/operations/05-cancel-response.json) 和
生成的 [`model-response-v1-review.html`](model-response-v1-review.html)。

![Model Manager 调用时序](model_manager_invocation_sequence.svg)

[PlantUML 源码：`model_manager_invocation_sequence`](diagram.puml#L141)

## 7. MateService 私有领域模型

本节只记录 1.0.0 已有的目标候选，不是本次冻结的接口契约。Mate 可以采用不同的表、
缓存、活动句柄和多实例路由实现；只要满足第 6 节的可观察 HTTP 语义，CampusClaw 不对
这些内部机制提出约束。

### 7.1 上游 Provider

目标 `t_model_provider` 至少包含：

| 字段 | 说明 |
|---|---|
| `provider_id` | 稳定不透明主键，唯一决定上游 Provider。 |
| `display_name` | 管理面展示名，不参与身份。 |
| `protocol_config` | 一个或多个上游 `api_id` 及协议参数；敏感值使用引用。 |
| `endpoint_url` | 上游端点；只在管理面和路由器内部使用。 |
| `default_headers` | 受控 header 模板；禁止保存明文 secret。 |
| `credential_ref` | 指向 Secret Store 的引用，不是凭据值。 |
| `enabled` | Provider 是否可参与目录和调用。 |
| `revision` | 乐观并发、缓存失效和审计版本。 |
| `created_at/updated_at` | 审计时间。 |

### 7.2 模型

目标 `t_model_definition` 至少包含：

| 字段 | 说明 |
|---|---|
| `model_id` | 1-64 字符、大小写敏感的不透明主键；值由模型目录定义。 |
| `provider_id` | 私有上游 Provider 逻辑关联。 |
| `upstream_model_id` | 厂商模型/部署 ID，只供路由使用。 |
| `display_name` | 内部 Runtime 可展示名称。 |
| `api_id` | 选择该 Provider 内部的上游协议适配器。 |
| `reasoning_supported/thinking_level_map` | 推理能力和统一等级映射。 |
| `input_modalities` | 至少包含 `text`；可含 `image`。 |
| `cost` | 与 pi Model 对齐的每百万 token 费率。 |
| `context_window/max_output_tokens` | Runtime 前置校验所需限制。 |
| `enabled/revision/created_at/updated_at` | 生命周期和审计字段。 |

已有 `t_agent_binding_models` 继续保存 Agent allowlist 和顺序，逻辑关联
`t_model_definition.model_id`。GaussDB 分布式部署不要求物理外键，但 Service 必须在同一
事务内保证绑定目标存在。

数据库只保存 `credential_ref`。Secret Store 的具体产品、轮换协议和加密实现尚无已确认
公司制品，本文不发明具体产品名或密钥格式。

## 8. pi-mono-java 目标接口

### 8.1 完整 Provider 抽象

目标 Java 使用开放值对象，不再用 enum 作为扩展边界：

```java
public record ProviderId(String value) {}

public record ApiId(String value) {}

public interface AiProvider {
    ProviderId id();

    String name();

    Optional<URI> baseUrl();

    Map<String, String> headers();

    ProviderAuth auth();

    List<Model> getModels();

    Mono<Void> refreshModels(ModelRefreshContext context);

    AssistantMessageEventStream stream(Model model, Context context, StreamOptions options);

    AssistantMessageEventStream streamSimple(Model model, Context context, SimpleStreamOptions options);
}
```

`AiProviderRegistry` 以 `ProviderId` 为键。`CampusClawAiService` 根据
`model.providerId()` 解析 Provider，再由完整 Provider 按 `model.apiId()` 选择内部协议
实现。现有 `ApiProvider` 应重命名为 `ProtocolAdapter`，注册表重命名为
`ProtocolAdapterRegistry`，仅作为 Provider 内部复用能力。

已知 Provider/API 可以提供常量，但反序列化和注册边界必须接受合法开放字符串。

### 8.2 Model Manager 客户端端口

```java
public interface ManagedModelCatalogClient {
    List<ManagedModelDescriptorDTO> listModels();

    List<ManagedModelDescriptorDTO> listCallableModels(String agentId);

    ManagedModelDescriptorDTO resolveCallableModel(String agentId, String modelId);
}

public interface ManagedModelInvocationClient {
    ResponsesEventStream createResponse(ManagedResponseCreateRequestDTO request);

    Mono<ManagedResponseDTO> cancelResponse(String responseId);
}
```

`MateServiceModelManagerProvider` 组合这两个端口：目录 DTO 只在 Provider 内转换为
`Model`；Provider 把 `Context` 转换为 Responses DTO，再把 `ResponsesEventStream` 转换为
`AssistantMessageEventStream`。HTTP client 不接收或返回 AgentLoop 消息类型。Mate-service
Controller/API 边界使用 `*RequestVO/*ResponseVO`，Mapper 和内部传输使用 DTO，符合
mate-service 现有分层。

Mate-service 的 create Request VO 必须按字段显式保留 OpenAI wire 名称；Service 在同一
Responses JSON 语义树上完成校验和 `model` 值替换，再交给上游 HTTP client。不得先转换
为 Chat Completions VO、厂商 VO 或另一组“统一消息”DTO 后重新组装请求。

现有 `RuntimeModelManager` 可保留为 Runtime 业务端口，但实现改为：

| 方法 | 目标行为 |
|---|---|
| `resolveDefaultModel(snapshot)` | 使用 `snapshot.defaultModelId()` 调接口 3；不信任本地目录即代表当前授权。 |
| `resolveModel(snapshot, modelId)` | 调接口 3；执行路径每次重新授权。 |
| `listAvailableModels(snapshot)` | 调接口 2，保持 mate-service `model_order`，再投影为 model ID。 |
| `resolveAvailableModel(snapshot, modelId)` | 必须覆盖默认实现并直接调接口 3，消除 list+resolve 窗口。 |

### 8.3 AgentLoop 到 Responses 的字段映射

| AgentLoop/Provider 输入 | Responses 请求 | 目标行为 |
|---|---|---|
| `Model.id()` | `model` | 原样使用 Mate 目录 ID；Mate 内部替换上游模型 ID |
| `Context.systemPrompt()` | `instructions` | 不改写为 Chat Completions system message |
| `UserMessage` 文本 | `input[].content[].input_text` | 保留消息顺序和文本 |
| `UserMessage` 图片 | `input[].content[].input_image` | 使用受支持的 data URL 或 URL 结构，不丢弃图片 |
| `AssistantMessage` 文本 | `type=message, role=assistant, output_text` | 保留 message ID/文本签名以支持历史重放 |
| `AssistantMessage.ToolCall` | `type=function_call` | 保留 `call_id`，同模型合法 item ID 可重放 |
| `ToolResultMessage` | `type=function_call_output` | 文本或图片结果按模型能力发送 |
| `ThinkingContent.thinkingSignature` | `type=reasoning` input item | 重放包含 `encrypted_content` 的完整 reasoning item |
| Agent Tool | `tools[].type=function` | 转换 JSON Schema；Tool 仍由 AgentLoop 执行 |
| `SimpleStreamOptions.maxTokens()` | `max_output_tokens` | 受目录模型上限约束 |
| `SimpleStreamOptions.temperature()` | `temperature` | 仅模型支持时发送 |
| `SimpleStreamOptions.reasoning()` | `reasoning.effort` | 使用目录 `thinkingLevelMap` 映射 |

Provider 固定发送数组形式 `input`、`stream=true`、`store=false` 和
`background=false`，确保 Provider 输出在替换 `model` 后可直接调用 Responses 上游。收到
`response.created` 后保存 `response.id`；订阅取消时已知 ID 则调用 cancel operation，未知
ID 则关闭创建请求。SSE 正常事件沿用现有 Responses 解析器；调用方取消映射为
`StopReason.ABORTED`，传输或上游失败映射为 `StopReason.ERROR`。

![Java Provider 与 pi-mono 对齐](java_provider_alignment.svg)

[PlantUML 源码：`java_provider_alignment`](diagram.puml#L225)

## 9. 一致性、失败与安全

### 9.1 一致性

- 全局目录可以缓存并使用 ETag；Agent 可调用目录和单模型解析不缓存。
- `getModels()` 在刷新失败时保留最后成功目录，符合 pi-mono 动态 Provider 语义。
- 创建 Response 时，Mate 必须按请求中的精确 `model` 目录 ID 解析当前模型、Provider、
  endpoint 和 credential；模型不存在返回 `MODEL_NOT_FOUND`，模型或依赖不可用返回
  `MODEL_UNAVAILABLE`。
- 调用接口只校验服务调用方，不携带或重新校验 Agent 绑定。接口 2、3 的 Agent 目录结果
  只服务模型选择，不是接口 4 的授权凭证。
- 不得静默切换到内置模型、另一个 Mate 模型或另一个上游路由。
- create 和 cancel 的活动状态迁移必须保证正常完成与取消只有一个胜者；Mate 内部并发
  机制不属于本对接契约。

### 9.2 错误边界

| HTTP/流阶段 | 错误码/事件 | 语义 |
|---|---|---|
| `400` | `INVALID_RESPONSE_REQUEST` | JSON 无法读取、字段不在白名单、`stream/store/background` 缺失或值非法，或模型 ID 为空/超长。 |
| `401` | `UNAUTHENTICATED`、`AUTH_CREDENTIAL_CONFLICT` | 内部调用方认证失败。 |
| `403` | `FORBIDDEN` | 调用方无 Model Manager 权限。 |
| `404` | `MODEL_NOT_FOUND`、`RESPONSE_NOT_ACTIVE` | 目录模型不存在，或 cancel 目标不再活动。 |
| `422` | `MODEL_OPTION_UNSUPPORTED` | 选定模型不支持请求能力。 |
| `429` | `MODEL_RATE_LIMITED` | mate-service 或上游限流；可带 `Retry-After`。 |
| `502` | `UPSTREAM_MODEL_ERROR` | 上游协议或响应错误。 |
| `503` | `MODEL_UNAVAILABLE`、`MANAGER_UNAVAILABLE` | 模型路由不可用，或目录、Secret Store、Manager 暂时不可用。 |
| `504` | `MODEL_INVOCATION_TIMEOUT` | Manager 强制终止超时调用。 |
| SSE 已开始 | Responses `error`、`response.failed`、`response.incomplete` | 保持 Responses 事件；HTTP 状态已不能改变。 |

上下文溢出错误需要归一为 pi 能识别的稳定语义，例如
`context_length_exceeded`，但不得把限流或普通上游错误误映射为溢出。

### 9.3 安全加固

- 上游 secret 只存在于 Secret Store 和调用期内存，不进入 Model、数据库明文字段、API
  响应、SSE、日志或异常消息。
- Provider 管理面必须验证 endpoint scheme、DNS/IP 边界和允许域，防止 SSRF；运行时
  调用不能覆盖 endpoint。
- Runtime 不能透传任意 headers、metadata 或 provider options，所有字段采用 allowlist。
- Mate 对已接受的 Responses body 只允许替换 `model` 值；禁止对 `input/tools/reasoning`
  做协议转换，也禁止静默删除字段后继续调用。
- 调用授权只依据有效服务凭据；请求中不存在可伪造的 `agentId`。
- reasoning summary 和 `encrypted_content` 可以按 Responses 协议进入 SSE/历史重放，但不得
  写入普通日志或错误消息。
- 每个调用设置输入大小、Context token、输出 token、并发、执行时间和 SSE 缓冲上限。
- 审计记录 `responseId/modelId/providerId/revision/结果/用量`，但不
  记录完整提示词、工具参数、secret 或原始 thinking。

## 10. 差异分类

| 分类 | 设计差异 | 原因 |
|---|---|---|
| 架构改造 | Java 从按 `Api` 查 `ApiProvider` 改为按 `ProviderId` 查完整 `AiProvider`。 | 对齐 pi-mono 当前 Provider 归属和多协议能力。 |
| 架构改造 | `Provider`/`Api` enum 改为开放值对象，现有 enum 常量转为便利常量。 | 支持通用 Provider 和第三方扩展，不再塌缩为 `CUSTOM`。 |
| 架构改造 | Mate-service 新增模型目录、Agent 可调用解析、调用和取消能力。 | 当前代码只有模型 ID 绑定，无法形成可执行 Provider。 |
| 架构改造 | Model Manager 作为 mate-service 内部组件向 Runtime 提供安全描述和调用流；公共 Session API 仍只暴露模型 ID。 | 细化现有 Manager 最终权威设计，同时不扩大浏览器可见面。 |
| 架构改造 | 调用线协议从自定义 Context/AssistantMessageEvent 改为 OpenAI Responses request/SSE。 | Mate 均为 OpenAI 类型模型，复用成熟协议并把 Java 映射职责留在 Provider。 |
| 架构改造 | Mate 调用端改为 Responses 语义透明代理，已接受 body 只替换 `model` 值。 | 让 Provider 生成的请求可直接调用 Responses 兼容 LLM，避免 Mate 再维护消息转换器。 |
| 架构改造 | response ID 直接透传，响应 `model` 改写为 Mate 模型 ID。 | 取消无需第二套调用 ID，同时保持 Mate 模型抽象不泄露上游路由。 |
| 安全加固 | Runtime 只看到单一通用 Provider；mate-service 托管上游配置和 secret。 | 避免凭据扩散、任意 endpoint/header 注入和多处协议实现漂移。 |
| 产品约束 | 调用接口不携带 `agentId`，不校验 Agent 绑定。 | CampusClaw 与 CampusMate 互信，Agent 绑定只用于模型选择。 |
| 产品约束 | 模型 ID 采用目录返回的 1-64 字符不透明值，不强制类型化 UUID。 | 兼容实际模型管理器 ID；调用方不得自行解析格式。 |
| 产品约束 | 创建请求不支持幂等键或自动重放。 | 网络结果未知时重放可能造成重复模型消费。 |
| 产品约束 | `stream/store/background` 必须显式为 `true/false/false`。 | 让安全策略在 Provider 生成请求时确定，Mate 无需补写 body 默认值。 |
| OpenAI 兼容扩展 | `POST /responses/{responseId}/cancel` 可取消前台活动流。 | 官方 cancel 只保证 background response；Mate 需服务 AgentLoop 的前台取消。 |
| OpenAI 兼容例外 | create 成功 SSE 和 cancel 成功 Response 不使用公司 ResultBean。 | 保持 Responses 客户端与事件解析兼容；所有非 2xx 仍使用公司错误体。 |
| 产品约束 | 不允许自动模型 fallback。 | 保持用户选择、成本、能力和审计结果可解释。 |
| 产品约束 | Tool 执行留在 AgentLoop。 | Model Manager 只负责模型流，不接管 Agent 编排。 |

## 11. 迁移顺序

1. 在 Java 增加 `ProviderId/ApiId/AiProvider/AiProviderRegistry`，保留现有 enum 与
   `ApiProviderRegistry` 兼容适配。
2. 让内置 Provider 通过完整 Provider 包装现有协议适配器；新增测试证明同一
   `apiId` 可被两个不同 `providerId` 使用。
3. 修改 `Model`，移除 `apiKey`，把 Provider/API 类型改为开放值对象；兼容读取旧配置。
4. 在 mate-service 建立 Provider/模型私有目录和 Secret Store 引用，并统一 Agent 绑定与
   目录的 1-64 字符模型 ID 规则。
5. 实现 `MateServiceModelManagerProvider` 与目录 ETag 缓存，替换
   `CatalogRuntimeModelManager` 生产 Bean；本地开发仍可显式启用 catalog fallback。
6. 实现 Responses create/cancel HTTP client；复用并补齐 Java Responses 映射器的图片、
   Tool 图片结果、reasoning 签名、取消、背压、超时和审计行为；Mate 侧只实现
   Responses 校验和 `model` 值替换，不实现协议转换器。
7. 生产配置关闭 Runtime 直连上游和内置 fallback；删除旧兼容路由前运行双栈契约测试。

## 12. 验收标准

- 两个不同 Provider 使用同一 `apiId` 时可以同时注册、独立认证和调用。
- 两个相同 `modelId` 只有在 Provider 不同时才可共存；模型比较使用二元键。
- Runtime 模型目录和所有日志均不出现上游 base URL、credential、私有 Provider ID 或
  上游模型 ID。
- 全局目录 ETag 未变化返回 304；刷新失败不清空 Provider 上次成功目录。
- 文本、用户图片、Assistant 历史、函数调用、Tool 文本/图片结果和 reasoning item 均能
  从 AgentLoop Context 无损转换为 Responses `input[]`；Tool 仍由 AgentLoop 执行。
- 捕获 Provider 发给 Mate 的 JSON 和 Mate 发给上游的 JSON；把后者 `model` 改回目录值
  后，两者必须语义相等，尤其 `input/tools/reasoning` 不得重组、降级或丢失。
- 目录路由的上游必须原生支持 OpenAI Responses；仅支持 Chat Completions 或厂商消息格式
  时返回明确错误，不在 Mate 内部转换。
- Mate 把请求的目录模型 ID 替换为私有上游模型 ID，并在每个 Response 对象中改回目录
  模型 ID；Runtime 和日志不出现私有路由。
- `response.created.response.id` 原样进入 AssistantMessage，并可用于 cancel path。
- `stream/store/background` 缺失、值不符合 `true/false/false`、未知字段和未知模型分别
  得到已冻结错误。
- SSE 首字节前使用 ResultBean 错误；SSE 开始后使用 Responses 错误/失败/不完整事件。
- 活动取消返回 `200 status=cancelled` 并关闭原流；再次取消、已完成或未知 ID 返回 404。
- 正常完成和取消竞争时只产生一个终态；网络结果未知时 Provider 不重放 create POST。
- 本地取消映射为 `StopReason.ABORTED`，普通传输或上游失败映射为 `StopReason.ERROR`。
- 请求无法注入 `apiKey/baseUrl/headers/providerId/upstreamModelId`。
- 无可用模型时返回空列表或明确错误，不回退到本地内置 Provider。

## 13. 当前评审决策

已确认资源模型：**单一通用 Provider，MateService 托管调用**。

- 接口 4 `POST /responses`：已冻结。
- 接口 5 `POST /responses/{responseId}/cancel`：已冻结。
- 接口 1-3：仍为候选，未因本次调用协议确认而自动获批。

目录候选评审入口：
[`model-manager-provider-v1-review.html`](model-manager-provider-v1-review.html)。调用与取消的
已冻结契约入口：[`model-response-v1-review.html`](model-response-v1-review.html)。

## 14. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.2.0 | 2026-08-22 | 将 create operation 冻结为 OpenAI Responses 语义透明代理；Provider 完成唯一一次 Context 转换，Mate 对已接受 body 只替换 `model` 值，并要求显式 `stream=true/store=false/background=false`；禁止 Responses-to-Chat 或厂商协议转换。 |
| 1.1.0 | 2026-08-22 | 确认 MateService 托管调用资源模型；冻结 OpenAI Responses create/cancel 接口、模型和 response ID 映射、无状态输入、错误与取消语义；补充 pi-mono 对齐差异。 |
| 1.0.0 | 2026-08-21 | 基于 pi-mono、pi-mono-java 和 mate-service 当前源码，明确 Provider 身份、完整运行契约、Java 对齐方案、MateService 私有领域模型与五项运行时接口候选；建立资源模型决策门。 |
