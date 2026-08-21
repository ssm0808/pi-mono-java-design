# MateService Model Manager 通用 Provider 对接设计

| 属性 | 值 |
|---|---|
| 文档版本 | 1.0.0 |
| 状态 | 目标设计；推荐资源模型待确认；接口 1 为当前评审项，其余接口为候选清单 |
| 设计日期 | 2026-08-21 |
| pi-mono 源码基线 | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` |
| pi-mono-java 源码基线 | `3d9b9c55569486f024d6a507ce004101a56dee3f` |
| mate-service 源码基线 | `6d5e6f3714e1cf8744d187a4796ca06300ad7e33` |
| 设计仓分析基线 | `2ae2cd5cdee927f78f78cc7130a85ea0984d3987` |
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
apiId      = mate-model-manager-stream
model key   = (mate-model-manager, model-<32 hex>)
```

mate-service 内部可以管理多个真实上游 Provider，但只把不透明 `modelId` 和运行所需的
安全模型描述投影给 Runtime。上游 `providerId`、厂商模型 ID、base URL、请求 headers
和凭据均不得跨出 mate-service。模型调用也由 mate-service 完成，不把上游配置下发给
pi-mono-java。

这是本设计当前唯一需要确认的资源模型决策。若选择“仅目录下发、Runtime 直连厂商”，
则 Provider 身份、凭据责任、协议适配器和本文接口都会发生根本变化；因此当前 HTML
评审页把后续字段视为条件草案。

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
4. `modelId` 是 mate-service 生成的类型化不透明 ID，沿用当前
   `^model-[0-9a-fA-F]{32}$` 规则；不得把厂商模型名编码进 ID。
5. `modelId` 创建后不可变且不得复用。更换同一逻辑部署的端点可以保留 ID；更换为
   语义不同的上游模型必须创建新 `modelId`。

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

因此，“确定 Provider”应分成两个问题：

| 问题 | 最小信息 |
|---|---|
| 这个 Provider 是谁 | `provider.id` |
| 这个 Provider 能否执行 | `id` + 认证语义 + 模型目录 + 对应 `api` 的 stream 实现 |

### 3.2 pi-mono-java 当前行为与不足

| 证据 | 观察到的行为 | 与 pi-mono 的差距 |
|---|---|---|
| `modules/ai/src/main/java/com/campusclaw/ai/types/Provider.java:19-37` | Provider 是封闭 enum，未知值只能归入 `CUSTOM`。 | 无法保留任意 Provider 身份。 |
| `modules/ai/src/main/java/com/campusclaw/ai/types/Api.java:16-22` | API 协议也是封闭 enum。 | 无法注册 `mate-model-manager-stream` 等扩展协议。 |
| `modules/ai/src/main/java/com/campusclaw/ai/provider/ApiProvider.java:31-59` | 所谓 Provider 只提供 `getApi/stream/streamSimple`。 | 实际职责是协议适配器，缺少 Provider 身份、认证和模型目录。 |
| `modules/ai/src/main/java/com/campusclaw/ai/provider/ApiProviderRegistry.java:22-152` | 注册表按 `Api` 索引，最后注册者覆盖。 | 调用按协议而不是按 Provider 身份路由。 |
| `modules/ai/src/main/java/com/campusclaw/ai/CampusClawAiService.java:141-147` | 根据 `model.api()` 查找 `ApiProvider`。 | 同协议的多个 Provider 无法拥有独立运行策略。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/config/CustomModelLoader.java:92-123` | 所有自定义模型都写为 `Provider.CUSTOM`，模型中还可嵌入 API Key。 | Provider 身份塌缩；秘密进入 Model 数据对象。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/model/RuntimeModelManager.java:20-39` | Runtime 已有模型解析端口，但默认 `resolveAvailableModel` 先列表再解析。 | 两次读取之间可能发生停用或解绑，需要服务端原子解析。 |

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

所以本文的模型目录、上游 Provider、凭据引用、解析、调用和取消能力全部是
**目标设计**，不是 mate-service 已实现行为。

### 3.4 现有设计输入

设计仓基线 `pi-mono-java-manager-driven-multi-agent-runtime/README.md:276-286` 已把
Model Manager 定义为模型描述、可用性、凭据和调用的最终权威，并要求 Runtime 映射
Provider 结构化增量。`pi-mono-java-manager-driven-multi-agent-runtime/chat-http-v1-design.md:614-630`
已确认公共 Session 模型列表只返回 `model_id` 字符串，不暴露 Provider 配置。

本文细化的是 **mate-service Model Manager 到 pi-mono-java Runtime 的内部接口**，不
扩大浏览器或公共 Session API。内部目录为构造 Runtime `Model` 可以携带安全能力和成本
字段；上游身份、端点、headers 和凭据仍不进入内部响应，公共模型列表仍只投影模型 ID。

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
| `api` | 固定 `ApiId("mate-model-manager-stream")` |
| `baseUrl` | Provider 客户端配置中的 mate-service 内部地址，不取响应字段 |
| `reasoning` | `reasoningSupported` |
| `thinkingLevelMap` | `thinkingLevelMap` |
| `input` | `inputModalities` |
| `cost` | `cost`，按 pi 的每百万 token 费率语义 |
| `contextWindow` | `contextWindow` |
| `maxTokens` | `maxOutputTokens` |
| `headers` | 空；调用上下文由受控 HTTP client 添加 |
| `apiKey` | 删除；Provider 通过 service credential resolver 认证 |

通用 Provider 的 `getModels()` 是全局目录，不承担 Agent 权限。Agent 可调用集合由
`RuntimeModelManager` 调用 Agent 维度接口获取，真正调用前 mate-service 再做一次原子
授权检查。

## 5. 总体架构

![通用 Provider 与 MateService 边界](generic_provider_boundary.svg)

[PlantUML 源码：`generic_provider_boundary`](diagram.puml#L73)

职责固定如下：

| 组件 | 职责 |
|---|---|
| `AiProviderRegistry` | 以开放 `ProviderId` 注册和解析完整 Provider。 |
| `MateServiceModelManagerProvider` | 拥有通用 Provider 身份、目录缓存、服务认证和事件映射。 |
| `ManagedModelCatalogClient` | 调用全局目录、Agent 可调用目录和原子解析接口。 |
| `ManagedModelInvocationClient` | 创建 SSE 调用和显式取消，不做上游协议判断。 |
| mate-service Model Manager | 管理真实 Provider、模型、凭据引用、Agent 绑定、路由、限流、调用和审计。 |
| mate-service 上游适配器 | 把厂商协议转为统一 AssistantMessageEvent 事件，不执行 Tool。 |
| `AgentLoop` | 维护上下文、执行 Tool、继续下一轮模型调用。 |

## 6. MateService 运行时接口清单

基础路径：`/mate-service/internal/v1`。这些接口只面向 pi-mono-java Runtime 或其他已授权
内部服务，不是浏览器公共 API。

| # | Method | Path | Provider/Runtime 用途 | 当前状态 |
|---:|---|---|---|---|
| 1 | `GET` | `/models` | 完整 Provider 的 `getModels/refreshModels` 全局目录来源 | 当前评审项；条件草案 |
| 2 | `GET` | `/agents/{agentId}/models` | 按 `model_order` 返回当前可调用模型，用于选择器和默认模型解析 | 目标候选 |
| 3 | `GET` | `/agents/{agentId}/models/{modelId}` | 在一次服务端读中校验绑定、模型、Provider 和凭据状态并返回描述 | 目标候选 |
| 4 | `POST` | `/agents/{agentId}/model-invocations` | 创建一次有界模型调用，响应为 AssistantMessageEvent 兼容 SSE | 目标候选 |
| 5 | `DELETE` | `/model-invocations/{invocationId}` | 幂等取消正在执行的上游调用 | 目标候选 |

Provider 管理 CRUD、凭据轮换、模型发布和 Agent 绑定管理属于管理面，不是 Provider 对接
所需运行时接口；本主题不擅自定义这些公共/管理接口。

### 6.1 公共 HTTP 规则

- JSON 使用 Jackson 默认 lower camel case；不得配置全局 `SNAKE_CASE`。Java Controller
  使用 Request/Response VO，只有真实字段例外才增加显式 Jackson 属性注解。
- JSON 成功返回 `{"resCode":"0","resMsg":"success","result":...}`；错误只返回
  `resCode/resMsg` 并使用真实 HTTP 状态。
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
        "modelId": "model-550e8400e29b41d4a716446655440000",
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

`POST /agents/{agentId}/model-invocations` 请求范围内持续输出 SSE。Runtime 生成唯一
`invocationId`，格式为 `^invocation-[0-9a-fA-F]{32}$`，每次逻辑调用只使用一次：

```json
{
  "invocationId": "invocation-550e8400e29b41d4a716446655440000",
  "sessionId": "session-550e8400e29b41d4a716446655440001",
  "modelId": "model-550e8400e29b41d4a716446655440000",
  "context": {
    "systemPrompt": "You are a coding assistant.",
    "messages": [],
    "tools": []
  },
  "options": {
    "temperature": 0.2,
    "maxTokens": 4096,
    "thinkingLevel": "medium",
    "cacheRetention": "short"
  }
}
```

请求只允许 Provider 无关且经白名单确认的 Context/StreamOptions。不得接受
`apiKey`、`baseUrl`、`providerId`、`upstreamModelId`、任意请求 headers、transport
或任意 metadata。未知字段按当前 mate-service Jackson 策略拒绝。

发送首个 SSE 字节前，mate-service 原子执行接口 3 的全部检查并预留
`invocationId`。失败使用普通 ResultBean 错误响应。SSE 开始后，事件名与
pi-mono-java `AssistantMessageEvent` 对齐：

```text
start
text_start | thinking_start | toolcall_start
text_delta | thinking_delta | toolcall_delta
text_end   | thinking_end   | toolcall_end
done | error
```

`done` 与 `error` 是互斥终态，发送后关闭流。mate-service 可以发送 SSE comment heartbeat，
但不得把 heartbeat 映射为 AssistantMessageEvent。Tool 只以 tool-call 内容返回，实际 Tool
执行仍由 `AgentLoop` 完成。

同一 `invocationId` 的重复 POST 返回 `409 MODEL_INVOCATION_CONFLICT`，不重放旧 SSE，
也不再次调用模型。连接结果未知时 Runtime 不得自动重放 POST；需要根据 Session 执行
状态决定后续恢复。

### 6.6 接口 5：取消模型调用

`DELETE /model-invocations/{invocationId}` 幂等返回 `204`：

- 正在执行：标记取消并向上游传播 abort；
- 已终止、已取消或不存在：仍返回 `204`，避免取消竞争和信息枚举；
- Runtime 关闭 SSE 连接时同时调用 DELETE；仅依赖 TCP 断开不足以表达可靠取消；
- Provider 收到取消后把本地流收敛为 `error(reason=aborted)`，不得切换到其他模型。

![Model Manager 调用时序](model_manager_invocation_sequence.svg)

[PlantUML 源码：`model_manager_invocation_sequence`](diagram.puml#L140)

## 7. MateService 私有领域模型

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
| `model_id` | `model-` 类型化不透明主键。 |
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
    AssistantMessageEventStream stream(ManagedModelInvocationRequestDTO request);

    Mono<Void> cancel(String invocationId);
}
```

`MateServiceModelManagerProvider` 组合这两个端口：目录 DTO 只在 Provider 内转换为
`Model`，调用 DTO 只在 HTTP client 边界序列化。Controller/API 边界使用
`*RequestVO/*ResponseVO`，Mapper 和内部传输使用 DTO，符合 mate-service 现有分层。

现有 `RuntimeModelManager` 可保留为 Runtime 业务端口，但实现改为：

| 方法 | 目标行为 |
|---|---|
| `resolveDefaultModel(snapshot)` | 使用 `snapshot.defaultModelId()` 调接口 3；不信任本地目录即代表当前授权。 |
| `resolveModel(snapshot, modelId)` | 调接口 3；执行路径每次重新授权。 |
| `listAvailableModels(snapshot)` | 调接口 2，保持 mate-service `model_order`，再投影为 model ID。 |
| `resolveAvailableModel(snapshot, modelId)` | 必须覆盖默认实现并直接调接口 3，消除 list+resolve 窗口。 |

![Java Provider 与 pi-mono 对齐](java_provider_alignment.svg)

[PlantUML 源码：`java_provider_alignment`](diagram.puml#L205)

## 9. 一致性、失败与安全

### 9.1 一致性

- 全局目录可以缓存并使用 ETag；Agent 可调用目录、单模型解析和调用授权不缓存。
- `getModels()` 在刷新失败时保留最后成功目录，符合 pi-mono 动态 Provider 语义。
- 目录结果只用于展示和本地能力预检；调用授权以 POST 开始时的 mate-service 当前状态
  为准。
- Model/Provider 在 Session 创建后被停用时，下一次调用失败为
  `MODEL_NOT_CALLABLE`；不得静默回退到内置模型或另一个上游模型。
- 模型切换和模型调用都走原子解析；列表不是授权凭证。

### 9.2 错误边界

| HTTP/流阶段 | 错误码/事件 | 语义 |
|---|---|---|
| `400` | `INVALID_AGENT_ID`、`INVALID_MODEL_ID`、`INVALID_INVOCATION_REQUEST` | 格式或请求体错误。 |
| `401` | `UNAUTHENTICATED`、`AUTH_CREDENTIAL_CONFLICT` | 内部调用方认证失败。 |
| `403` | `FORBIDDEN` | 调用方无 Model Manager 权限。 |
| `404` | `AGENT_NOT_FOUND`、`MODEL_NOT_CALLABLE` | 资源不存在或当前不可调用。 |
| `409` | `MODEL_INVOCATION_CONFLICT` | `invocationId` 已被使用。 |
| `422` | `MODEL_OPTION_UNSUPPORTED` | 选定模型不支持请求能力。 |
| `429` | `MODEL_RATE_LIMITED` | mate-service 或上游限流；可带 `Retry-After`。 |
| `502` | `UPSTREAM_MODEL_ERROR` | 上游协议或响应错误。 |
| `503` | `MANAGER_UNAVAILABLE` | 目录、Secret Store 或 Manager 暂时不可用。 |
| `504` | `MODEL_INVOCATION_TIMEOUT` | Manager 强制终止超时调用。 |
| SSE 已开始 | `error(reason=error|aborted)` | 错误通过终态事件表达，HTTP 状态已不能改变。 |

上下文溢出错误需要归一为 pi 能识别的稳定语义，例如
`context_length_exceeded`，但不得把限流或普通上游错误误映射为溢出。

### 9.3 安全加固

- 上游 secret 只存在于 Secret Store 和调用期内存，不进入 Model、数据库明文字段、API
  响应、SSE、日志或异常消息。
- Provider 管理面必须验证 endpoint scheme、DNS/IP 边界和允许域，防止 SSRF；运行时
  调用不能覆盖 endpoint。
- Runtime 不能透传任意 headers、metadata 或 provider options，所有字段采用 allowlist。
- Agent 绑定在目录、解析和调用三个入口都执行；调用时检查是最终授权。
- `thinking` 内容是否允许进入 SSE 由产品策略和 Session 开关共同决定，能力支持不等于
  自动披露。
- 每个调用设置输入大小、Context token、输出 token、并发、执行时间和 SSE 缓冲上限。
- 审计记录 `invocationId/agentId/sessionId/modelId/providerId/revision/结果/用量`，但不
  记录完整提示词、工具参数、secret 或原始 thinking。

## 10. 差异分类

| 分类 | 设计差异 | 原因 |
|---|---|---|
| 架构改造 | Java 从按 `Api` 查 `ApiProvider` 改为按 `ProviderId` 查完整 `AiProvider`。 | 对齐 pi-mono 当前 Provider 归属和多协议能力。 |
| 架构改造 | `Provider`/`Api` enum 改为开放值对象，现有 enum 常量转为便利常量。 | 支持通用 Provider 和第三方扩展，不再塌缩为 `CUSTOM`。 |
| 架构改造 | Mate-service 新增模型目录、Agent 可调用解析、调用和取消能力。 | 当前代码只有模型 ID 绑定，无法形成可执行 Provider。 |
| 架构改造 | Model Manager 作为 mate-service 内部组件向 Runtime 提供安全描述和调用流；公共 Session API 仍只暴露模型 ID。 | 细化现有 Manager 最终权威设计，同时不扩大浏览器可见面。 |
| 安全加固 | Runtime 只看到单一通用 Provider；mate-service 托管上游配置和 secret。 | 避免凭据扩散、任意 endpoint/header 注入和多处协议实现漂移。 |
| 安全加固 | 调用前原子重验 Agent 绑定；列表不作为授权。 | 消除状态变化和越权窗口。 |
| 产品约束 | 不允许自动模型 fallback。 | 保持用户选择、成本、能力和审计结果可解释。 |
| 产品约束 | Tool 执行留在 AgentLoop。 | Model Manager 只负责模型流，不接管 Agent 编排。 |

## 11. 迁移顺序

1. 在 Java 增加 `ProviderId/ApiId/AiProvider/AiProviderRegistry`，保留现有 enum 与
   `ApiProviderRegistry` 兼容适配。
2. 让内置 Provider 通过完整 Provider 包装现有协议适配器；新增测试证明同一
   `apiId` 可被两个不同 `providerId` 使用。
3. 修改 `Model`，移除 `apiKey`，把 Provider/API 类型改为开放值对象；兼容读取旧配置。
4. 在 mate-service 建立 Provider/模型私有目录和 Secret Store 引用，先实现接口 1-3。
5. 实现 `MateServiceModelManagerProvider` 与目录 ETag 缓存，替换
   `CatalogRuntimeModelManager` 生产 Bean；本地开发仍可显式启用 catalog fallback。
6. 实现调用 SSE 和取消接口，完成统一事件映射、背压、超时和审计。
7. 生产配置关闭 Runtime 直连上游和内置 fallback；删除旧兼容路由前运行双栈契约测试。

## 12. 验收标准

- 两个不同 Provider 使用同一 `apiId` 时可以同时注册、独立认证和调用。
- 两个相同 `modelId` 只有在 Provider 不同时才可共存；模型比较使用二元键。
- Runtime 模型目录和所有日志均不出现上游 base URL、credential、私有 Provider ID 或
  上游模型 ID。
- 全局目录 ETag 未变化返回 304；刷新失败不清空 Provider 上次成功目录。
- Agent 解绑或模型停用发生在 list 之后、invoke 之前时，invoke 返回
  `MODEL_NOT_CALLABLE` 且不产生上游调用。
- 同一 `invocationId` 重复 POST 不产生第二次模型消费。
- text、thinking、tool-call、done、error 和 abort 事件均可无损映射为当前
  `AssistantMessageEvent`；Tool 仍由 AgentLoop 执行。
- SSE 断开和显式 DELETE 都能最终终止上游调用；取消接口重复调用仍为 204。
- 请求无法注入 `apiKey/baseUrl/headers/providerId/upstreamModelId`。
- 无可用模型时返回空列表或明确错误，不回退到本地内置 Provider。

## 13. 当前评审决策

推荐选择：**单一通用 Provider，MateService 托管调用**。

评审入口：[`model-manager-provider-v1-review.html`](model-manager-provider-v1-review.html)。
该页当前只确认资源模型；选定后再逐接口冻结认证、参数、响应、SSE 和错误。若选择推荐
方案，接口 1 的候选字段可以进入下一轮评审；若选择配置下发方案，应先重写本设计的
安全边界和 Java Provider 映射。

## 14. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-08-21 | 基于 pi-mono、pi-mono-java 和 mate-service 当前源码，明确 Provider 身份、完整运行契约、Java 对齐方案、MateService 私有领域模型与五项运行时接口候选；建立资源模型决策门。 |
