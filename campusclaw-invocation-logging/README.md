# CampusClaw 调用日志设计

| 属性 | 值 |
|---|---|
| 文档版本 | 1.0.0 |
| 状态 | 目标设计；待 CampusClaw 实现，mate-service 调用端部分为 target-only |
| 设计日期 | 2026-08-25 |
| 设计仓基线 | `b905a642eb176547370bda33d5a350d536245678` |
| CampusClaw 源码基线 | `42eb8b0ccb98b512d886722f2ad7ce8340d5a77a`（`origin/main`） |
| CampusClaw 本地核对头 | `2b666cc9ac97606d588904e9e80f3bd6ad8c72a7`；所引用源码与基线无差异 |
| mate-service 源码基线 | `6d5e6f3714e1cf8744d187a4796ca06300ad7e33` |
| 适用范围 | mate-service / 内部 SDK → CampusClaw Runtime → CampusMate Model Manager / Tool Service |
| 关联设计 | [Runtime HTTP API](../pi-mono-java-manager-driven-multi-agent-runtime/chat-http-v1-design.md)、[Model Manager Provider](../model-manager-provider-contract/README.md) |

## 1. 结论

当前“CampusClaw 调用失败但没有日志”不是单一日志级别问题，而是失败传播模型与日志边界
共同形成的可观测性缺口：

1. Runtime 没有统一的入站访问日志，无法先确认请求是否到达 CampusClaw；
2. 请求体和参数错误只记录 `DEBUG`，而默认配置为 `WARN`，因此 400 类错误通常完全不可见；
3. Mate Model Manager 的映射、HTTP、SSE 和解析错误会被转换成
   `AssistantMessage(stopReason=ERROR)`，不一定以 `Throwable` 结束执行；
4. `RuntimeExecutionCoordinator` 只在最终 `Throwable != null` 时记录失败，导致调用方已经收到
   `stream.error`，服务端仍可能没有对应日志；
5. 现有日志只有局部 `sessionId` 或异常堆栈，没有一次请求、一次执行和一次模型调用之间的
   稳定关联信息；
6. 如果 DNS、TLS、连接或路由在请求进入 CampusClaw 前失败，CampusClaw 本身不可能产生日志，
   必须由调用端记录。

目标方案增加四层结构化生命周期日志：调用端、CampusClaw HTTP、Runtime 执行、下游模型/
工具调用。每层至少记录开始和唯一终态，使用显式不可变诊断上下文跨 Servlet、虚拟线程和
Reactor 传递。日志只记录白名单元数据，不记录凭据、Header 值、Prompt、消息正文、thinking、
工具参数/结果或原始 SSE。

本设计不新增数据库表，不改变 11 个 Runtime HTTP 路径、请求/响应 VO、ResultBean 或 SSE
公共字段，也不恢复已经删除的 `traceparent` 业务契约。公司网关若已有跨服务请求标识，可在
实施时映射为日志 `parentRequestId`；具体 Header 名称当前没有源码证据，保持为集成校准点，
不在本文中臆造。

## 2. 已观察问题

### 2.1 模型失败可产生 `stream.error`，但没有服务端失败日志

以当前 Mate Model Manager 调用为例，源码路径如下：

1. `MateServiceModelManagerProvider.streamSimple()` 在本地请求映射失败时直接
   `stream.pushError(...)`；网络、HTTP 和响应协议错误则进入 `parser::fail`。Provider 本身
   没有 Logger。
2. `MateChatSseParser.fail()` 把异常转换为终态 Assistant 错误消息；`event:error`、提前关闭、
   非法 JSON 和非法 Tool 参数都走这一路径，没有记录失败阶段和稳定错误码的日志。
3. `AgentLoop.runInternal()` 看到 `StopReason.ERROR` 后正常退出循环，不抛异常。
4. `RuntimeEventProjector.persistAssistant()` 保存 Assistant 并把 `terminalReason` 设为
   `ERROR`，但 `projector.failure()` 仍可为 `null`。
5. `RuntimeExecutionCoordinator.executionFailure()` 只返回超时、Future 异常或
   `projector.failure()`；此时结果仍为 `null`，`logFailure()` 不输出任何内容。
6. `RuntimeTerminalEventFactory.emit()` 单独根据 `StopReason.ERROR` 发送
   `stream.error/SESSION_EXECUTION_FAILED`。因此调用方可见失败，日志却为空。

这条路径说明不能只补一个 `catch + log.error`：模型失败是一个正常完成的类型化终态，日志
设计必须把 `StopReason.ERROR` 本身当作失败结果。

### 2.2 请求拒绝默认不可见

`RuntimeExceptionHandler` 当前行为是：

- 非法请求体和方法参数只记 `DEBUG`；
- `RuntimeApiException` 仅在 HTTP 5xx 时记 `ERROR`；
- 400、404、409、412、422、428 等业务拒绝没有统一完成日志；
- 没有请求开始日志，因而不能判断调用是未到达、正在挂起，还是已被拒绝。

`application.yml` 同时将 `root` 和 `com.campusclaw` 设为 `WARN`。Kubernetes profile 虽把
`com.campusclaw` 调到 `INFO`，仍不会输出 `DEBUG` 参数错误；手工维护的
`mate-campusclaw/application.properties` 继续使用 `WARN`。

### 2.3 异步边界丢失上下文

Agent 通过虚拟线程异步执行，Model Manager 使用 Reactor Netty/WebClient。Servlet 线程上的
MDC 不能作为这两条异步链路的可靠事实来源。当前 Runtime 创建 `RuntimeActiveExecution` 和
`SimpleStreamOptions` 时也没有携带本次 HTTP 请求标识；`SimpleStreamOptions.sessionId` 虽已
存在，Runtime Agent 装配没有设置它。

## 3. 目标与非目标

### 3.1 目标

- 每个到达 CampusClaw 的 Runtime HTTP 请求都有可检索的开始和唯一完成日志；
- 4xx、5xx、SSE 流内失败和客户端断线均有明确、互不混淆的结果；
- 每个 active execution 和每次 Model Manager 调用都有开始、耗时与唯一终态；
- `StopReason.ERROR` 即使没有 Throwable，也必须产生日志；
- 通过 `requestId + sessionId + userEntryId + modelInvocationId` 关联调用阶段；
- 失败阶段和错误码稳定，可用于查询、统计和告警，不依赖解析异常文案；
- 生产输出为单行结构化 JSON，适合容器 stdout 收集；
- 敏感数据默认不进入日志，且通过自动化测试锁定。

### 3.2 非目标

- 不记录或重放完整请求、响应和 SSE；
- 不把日志当作 Session 历史、审计账本或业务事件存储；
- 不新增公开 Run 资源或改变“Session 同时只有一个 active execution”的产品模型；
- 不在本次设计中新增公共 `X-Request-ID`、`traceparent` 或其他 HTTP 契约 Header；
- 不规定公司日志平台、索引、归档桶或跨区域保留策略的内部实现；
- 不用日志替代超时、重试、状态机和持久化的一致性处理。

## 4. 总体架构

![CampusClaw 调用日志架构](campusclaw_invocation_logging_architecture.svg)

[PlantUML 源码：`campusclaw_invocation_logging_architecture`](diagram.puml#L6)

日志功能由以下边界共同完成：

| 边界 | 目标职责 | 当前状态 |
|---|---|---|
| mate-service / 内部 SDK 调用端 | 记录 CampusClaw 请求开始、HTTP/SSE 完成、DNS/TLS/connect/route 失败 | mate-service 当前基线没有公共 Chat → CampusClaw Client；target-only |
| CampusClaw HTTP | 记录请求到达、规范化 operation、HTTP status、ResultBean `resCode`、SSE 终态和耗时 | 缺少统一实现 |
| Runtime execution | 记录用户 Entry 接受、执行开始/成功/失败/取消/超时，以及 Session 与执行关联 | 仅 Throwable 失败有一条局部 WARN |
| Model Provider | 记录请求映射、连接、HTTP、SSE、解析、取消和耗时 | 无日志 |
| Tool Client/Pipeline | 记录发现和实际执行的终态，复用 execution 上下文 | 有零散错误日志，但字段和关联不统一 |
| 输出与采集 | SLF4J key-value → Spring Boot ECS JSON → stdout → 平台采集 | 当前为普通文本 Logback；目标配置 |

### 4.1 模块边界

保持现有 `ai → agent-core → coding-agent-cli` 依赖方向：

- `modules/ai` 定义最小的 `AiDiagnosticContext`、模型调用阶段与 Provider 终态日志；
- `modules/agent-core` 只把安全的诊断上下文传入每次 `SimpleStreamOptions`，不依赖 Web 类型；
- `modules/coding-agent-cli` 定义 HTTP/Runtime 上下文、访问日志、执行日志和 SSE 生命周期；
- `mate-campusclaw` 继续由同步脚本生成 Java 源码；其手工维护的
  `application.properties` 必须单独同步日志配置。

不得让 `modules/ai` 反向依赖 `coding-agent-cli`，也不得把 Servlet Request、原始 Header Map
或 `MateCredentials` 放入通用 AI 上下文。

## 5. 诊断上下文

![诊断上下文传播](campusclaw_log_context_propagation.svg)

[PlantUML 源码：`campusclaw_log_context_propagation`](diagram.puml#L201)

### 5.1 标识层次

| 字段 | 生成/获得时机 | 生命周期 | 是否对外 | 用途 |
|---|---|---|---|---|
| `requestId` | CampusClaw 请求 Filter 生成 UUID | 单个入站 HTTP 请求 | 否 | 判断请求是否到达并关联 HTTP/SSE 日志 |
| `parentRequestId` | 公司网关或调用端已有机制提供时映射 | 跨服务调用链 | 否 | 可选跨服务关联；Header 名待集成校准 |
| `sessionId` | 路径参数或创建成功后的资源 ID | Runtime Session | 已在业务契约中存在 | 关联同一 Session；不是凭据 |
| `agentId` | 创建路径或 Session/目录快照 | Agent 生命周期 | 已在业务契约中存在 | 定位 Agent 配置阶段 |
| `userEntryId` | 用户 Entry 原子接受成功后生成 | 单次 active execution | 以持久化 Event 对调用方可见 | 作为内部执行的稳定事实边界 |
| `modelInvocationId` | 每次进入 Provider 时生成 UUID | 单次模型尝试 | 否 | 区分工具循环、压缩和重试产生的多次模型调用 |
| `toolCallId` | 模型 ToolCall 提供 | 单次 ToolCall | SSE 中按既有契约可见 | 关联工具开始/终态；不记录参数 |

`requestId` 不从不可信来路直接接受，避免日志注入和不同调用方伪造关联。若公司网关已有
可信请求标识，应由部署适配层验证后写入独立 `parentRequestId`，不能覆盖本地
`requestId`。

### 5.2 显式上下文而非 MDC-only

目标增加三个不可变对象：

| 对象 | 所属模块 | 白名单字段 |
|---|---|---|
| `HttpRequestLogContext` | `coding-agent-cli` | `requestId/parentRequestId/operation/method/routeTemplate/startNanos` |
| `RuntimeInvocationLogContext` | `coding-agent-cli` | HTTP 字段 + `sessionId/agentId/userEntryId/modelId` |
| `AiDiagnosticContext` | `ai` | `requestId/sessionId/userEntryId` |

Filter 可在同步 Servlet 线程内把 `requestId` 镜像到 MDC，便于框架异常日志自动关联，但必须在
`finally` 清理。`RuntimeActiveExecution` 保存不可变 `RuntimeInvocationLogContext`；
`SimpleStreamOptions` 保存仅含三个安全 ID 的 `AiDiagnosticContext`，Provider 再创建
`modelInvocationId`。虚拟线程、CompletableFuture 和 Reactor 回调均读取显式对象，不依赖
ThreadLocal 继承。

`SimpleStreamOptions` 中的诊断上下文是 Java 内部字段：Provider 不把它序列化到 Mate Chat
请求，不把它混入已有 `metadata`、`headers` 或有状态模型 `sessionId` 语义。

### 5.3 异步完成去重

一次 SSE 请求可能同时触发 `SseEmitter.onCompletion`、`onTimeout`、`onError`、写入
IOException 和 execution terminal 回调。HTTP/SSE 完成状态使用原子 compare-and-set，确保：

- HTTP/SSE 完成日志只记录一次；
- execution 完成日志独立记录一次；
- 客户端断线只终止投影，不把已接受执行误记为取消；
- 断线后 execution 后续成功或失败仍有独立终态日志。

## 6. 日志事件目录

所有 `eventName` 均为稳定英文机器标识；消息模板也使用英文，满足 CampusClaw 当前日志
规范。日志消费者根据字段查询，不解析 message 文案。

### 6.1 调用端事件

| `eventName` | 级别 | 终态 | 必填字段 | 说明 |
|---|---|---|---|---|
| `campusclaw.client.call.started` | INFO | 否 | `clientCallId/operation/httpMethod/targetService` | 调用端准备发送；不得记录完整 URL 和 Header |
| `campusclaw.client.call.completed` | INFO/WARN/ERROR | 是 | started 字段 + `outcome/durationMs` | 记录 HTTP/SSE、connect/TLS/DNS/route 结果 |

调用端失败阶段至少区分 `campusclaw_connect`、`campusclaw_http`、
`campusclaw_stream`、`campusclaw_decode`。这一层是 target-only：当前 mate-service 基线只有
Agent definition API，没有已实现的公共 Chat bridge 或 CampusClaw Client。

### 6.2 HTTP 与 SSE 事件

| `eventName` | 级别 | 终态 | 必填字段 | 说明 |
|---|---|---|---|---|
| `campusclaw.http.request.started` | INFO | 否 | `requestId/operation/httpMethod/routeTemplate` | 证明请求已到达 CampusClaw |
| `campusclaw.http.request.completed` | INFO/WARN/ERROR | 是 | started 字段 + `outcome/httpStatus/durationMs` | 普通 HTTP 或 SSE Header 前失败 |
| `campusclaw.sse.completed` | INFO/WARN/ERROR | 是 | `requestId/sessionId/outcome/streamStarted/durationMs` | `stream.end`、`stream.error` 或超时 |
| `campusclaw.sse.disconnected` | INFO | 是 | `requestId/sessionId/executionContinues=true` | 调用端断线；不等同于 Runtime 失败 |

`operation` 必须使用已确认的 11 个 `operationKey`，例如 `submitUserMessage`，不得使用
含具体 ID 或 page token 的原始 URI。异常处理器把稳定 `resCode` 放入 request-scoped
诊断状态，Filter 在完成日志中读取；不通过解析 JSON 响应体获得错误码。

### 6.3 Runtime 事件

| `eventName` | 级别 | 终态 | 必填字段 | 说明 |
|---|---|---|---|---|
| `campusclaw.execution.started` | INFO | 否 | `requestId/sessionId/agentId/userEntryId/modelId` | 必须在 User Entry 持久化并开始 Agent 后记录 |
| `campusclaw.execution.completed` | INFO/ERROR | 是 | started 字段 + `outcome/terminationReason/durationMs` | 成功、ERROR、ABORTED、超时和内部异常统一收口 |
| `campusclaw.tool.invocation.completed` | INFO/WARN/ERROR | 是 | execution 字段 + `toolCallId/toolName/outcome/durationMs` | 不记录 arguments、delta 或 result |

关键规则：`terminalReason=error` 即使 `Throwable == null`，也必须记录
`outcome=failure/errorCode=SESSION_EXECUTION_FAILED`。`terminalReason=aborted` 记录
`outcome=success/terminationReason=aborted`，除非取消清理本身失败。

### 6.4 Model Manager 事件

| `eventName` | 级别 | 终态 | 必填字段 | 说明 |
|---|---|---|---|---|
| `campusclaw.model.invocation.started` | INFO | 否 | `requestId/sessionId/userEntryId/modelInvocationId/providerId/modelId/attempt` | 发起请求映射前记录 |
| `campusclaw.model.invocation.completed` | INFO/WARN/ERROR | 是 | started 字段 + `outcome/durationMs` | 映射、HTTP、SSE、协议、取消和成功统一收口 |

Model Provider 必须在全部终态分支只写一次 completed：

- 本地请求映射抛异常；
- DNS、TLS、connect、response timeout；
- 非 2xx ResultBean；
- 2xx 但 Content-Type 非 `text/event-stream`；
- `event:error`；
- 非法 JSON、reasoning 字段冲突、非法 Tool 参数；
- 流在 `[DONE]` 前关闭；
- 调用方取消；
- 正常 `[DONE]`。

不得按每个 Chat chunk、thinking delta、文本 delta 或 Tool arguments delta 记录日志。

## 7. 通用字段

### 7.1 核心字段

| 字段 | 类型 | 规则 |
|---|---|---|
| `eventName` | string | 固定目录值，不拼接用户数据 |
| `outcome` | `success \| failure \| unknown` | 与 ECS outcome 语义对齐；取消/断线另用 `terminationReason` |
| `terminationReason` | string | `completed/aborted/disconnected/timeout/error/rejected` |
| `requestId` | UUID string | CampusClaw 本地生成 |
| `parentRequestId` | string | 仅可信网关适配存在时写入 |
| `operation` | string | 11 个 operationKey 或固定内部 operation |
| `httpMethod` | string | 大写标准 Method |
| `routeTemplate` | string | 规范化模板，不含实际 ID、query 或 page |
| `httpStatus` | integer | HTTP 响应 status；SSE 流内失败仍可能为 200 |
| `durationMs` | long | 单调时钟计算，非 wall-clock 时间戳相减 |
| `sessionId/agentId/userEntryId` | string | 已校验的资源 ID；未知时字段缺失，不写空字符串 |
| `providerId/modelId` | string | 请求目标模型；禁止记录上游 response model |
| `modelInvocationId` | UUID string | 单次 Provider 调用生成 |
| `attempt` | integer | 同一 execution 内从 1 开始；工具续轮和压缩重试可递增 |
| `failureStage` | string | 第 7.2 节稳定枚举 |
| `errorCode` | string | 优先复用公开 resCode；内部诊断码不得对外返回 |
| `exceptionClass` | string | Java 类名；只有最深失败事件附完整 Throwable |
| `retryable` | boolean | 仅当既有错误/策略能证明时写入，不从 status 猜测 |

### 7.2 失败阶段

| `failureStage` | 触发边界 | 典型错误 |
|---|---|---|
| `request_route` | 请求没有匹配 operation | 404 路由错误 |
| `request_validation` | Path、Query、JSON、Bean Validation | `INVALID_*` |
| `session_lookup` | Session/Agent/Model 查找 | `SESSION_NOT_FOUND`、`MANAGER_UNAVAILABLE` |
| `event_acceptance` | 容量、并发、User Entry 事务 | `SESSION_BUSY`、`EVENT_ACCEPTANCE_FAILED` |
| `agent_prepare` | 受管目录、历史恢复、Agent 装配 | 初始化和目录错误 |
| `model_request_mapping` | Context → Mate Chat JSON | 不支持内容、序列化失败 |
| `model_connect` | DNS/TLS/connect | `MATE_TRANSPORT_ERROR`（内部诊断码） |
| `model_http` | 非 2xx 或错误体解析 | Mate `resCode` 或 `MATE_HTTP_ERROR` |
| `model_stream` | `event:error`、提前关闭、response timeout | `UPSTREAM_STREAM_ERROR` |
| `model_parse` | Content-Type、chunk、reasoning、Tool 参数 | `INVALID_MATE_RESPONSE`、`INVALID_CHAT_SSE` |
| `tool_execution` | Tool 解析、调用和终态 | Tool 领域错误码 |
| `runtime_persistence` | Entry、Usage、finishExecution | 持久化异常 |
| `sse_write` | SseEmitter 写失败 | `CLIENT_DISCONNECTED` 或真实服务器写失败 |
| `execution_timeout` | Runtime 最大执行时长 | `RUNTIME_TIMEOUT`（内部诊断码） |
| `unexpected` | 未分类异常 | `INTERNAL_ERROR` |

内部诊断码只用于日志和指标，不增加 Runtime HTTP/SSE 契约错误码。若下游已经返回安全且
稳定的 `resCode`，日志保留该码；不记录本地化 `resMsg` 和完整错误响应体。

## 8. 失败诊断流程

![CampusClaw 调用失败诊断顺序](campusclaw_failure_logging_sequence.svg)

[PlantUML 源码：`campusclaw_failure_logging_sequence`](diagram.puml#L107)

### 8.1 通过事件缺口判断故障位置

| 已观察日志 | 结论 |
|---|---|
| 有 `client.call.started`，无 CampusClaw `http.request.started`，调用端终态为 connect/TLS/DNS/route | 请求未到 CampusClaw；排查调用端配置、Service、网关、证书和网络 |
| 有 `http.request.started`，随后 `http.request.completed` 为 4xx/5xx，未出现 execution.started | 请求到达但在执行接受前失败 |
| 有 `execution.started`，无 `model.invocation.started` | Agent prepare、历史恢复、上下文转换或调度阶段失败/挂起 |
| 有 `model.invocation.started`，completed 为 `model_connect/model_http` | CampusClaw → Model Manager 传输或 HTTP 错误 |
| model completed 为 `model_stream/model_parse`，execution completed 为 failure | SSE 建立后上游或协议失败；这是当前“有 stream.error 无日志”的重点修复路径 |
| 有 `sse.disconnected`，随后 execution.completed success | 调用端断线，但已接受执行继续并完成 |
| 有 start，超过配置上限仍无 completed | 日志终态门禁或超时实现失效，应触发缺失终态告警 |

### 8.2 错误日志所有权与去重

同一失败允许有多个“边界终态摘要”，但完整异常堆栈只记录一次：

| 失败来源 | 附 Throwable 的事件 | 上层事件 |
|---|---|---|
| 请求解析/Controller 前异常 | `http.request.completed` 或专用异常详情事件 | 调用端只记录 status/resCode 摘要 |
| Provider 网络/协议异常 | `model.invocation.completed` | execution 和 SSE 只记录安全 code/stage 摘要 |
| Tool 内部异常 | `tool.invocation.completed` | execution 只记录 Tool 阶段摘要 |
| Runtime 投影/持久化/清理异常 | `execution.completed` | HTTP/SSE 只记录 `SESSION_EXECUTION_FAILED` 摘要 |
| 客户端断线 | `sse.disconnected` 不附堆栈 | 不是服务器故障，不生成重复 ERROR |

外层不得再次打印同一个异常堆栈。日志告警只以 `execution.completed outcome=failure` 和
`http.request.completed` 的服务器失败为主，Provider/Tool 终态用于根因下钻，避免一次错误
触发多条同级事故告警。

## 9. 结构化输出

CampusClaw 基线使用 Spring Boot `3.4.1`、SLF4J 和 Logback，具备 Spring Boot 内置 ECS
结构化 console encoder。目标使用 SLF4J 2 key-value API 写稳定字段，并由 Kubernetes profile
输出单行 ECS JSON，不新增 Logstash encoder 依赖。

失败示例（字段顺序不构成契约）：

```json
{
  "@timestamp": "2026-08-25T08:20:31.415Z",
  "log.level": "ERROR",
  "service.name": "campusclaw-agent",
  "message": "model invocation completed",
  "eventName": "campusclaw.model.invocation.completed",
  "outcome": "failure",
  "requestId": "3eaec4e9-b966-4678-94cf-4572cc3ee2ba",
  "sessionId": "session-550e8400e29b41d4a716446655440003",
  "userEntryId": "entry-550e8400e29b41d4a716446655440004",
  "modelInvocationId": "10361ec1-a567-4259-a6db-2e88132d4029",
  "providerId": "mate-model-manager",
  "modelId": "managed-coding-model",
  "attempt": 1,
  "failureStage": "model_stream",
  "errorCode": "UPSTREAM_STREAM_ERROR",
  "durationMs": 1842,
  "exceptionClass": "com.campusclaw.ai.provider.mate.MateModelInvocationException"
}
```

成功示例：

```json
{
  "@timestamp": "2026-08-25T08:20:35.002Z",
  "log.level": "INFO",
  "service.name": "campusclaw-agent",
  "message": "runtime execution completed",
  "eventName": "campusclaw.execution.completed",
  "outcome": "success",
  "terminationReason": "completed",
  "requestId": "3eaec4e9-b966-4678-94cf-4572cc3ee2ba",
  "sessionId": "session-550e8400e29b41d4a716446655440003",
  "userEntryId": "entry-550e8400e29b41d4a716446655440004",
  "durationMs": 5427
}
```

### 9.1 配置目标

Canonical `application.yml` 保持应用大部分 Logger 为 WARN，仅为诊断事件包开启 INFO：

```yaml
logging:
  level:
    root: WARN
    com.campusclaw: WARN
    com.campusclaw.ai.observability: INFO
    com.campusclaw.codingagent.observability: INFO
```

Kubernetes profile 增加 ECS console 输出：

```yaml
logging:
  structured:
    format:
      console: ecs
    ecs:
      service:
        name: campusclaw-agent
```

`mate-campusclaw/src/main/resources/application.properties` 是同步脚本排除的手工文件，必须显式
增加等价配置及重写后的包名：

```properties
logging.level.com.huawei.hicampus.mate.matecampusclaw.ai.observability=INFO
logging.level.com.huawei.hicampus.mate.matecampusclaw.codingagent.observability=INFO
logging.structured.format.console=ecs
logging.structured.ecs.service.name=mate-campusclaw
```

本地默认可以继续使用人类可读 console 格式，但字段和事件名必须相同。应用不在容器内维护
滚动日志文件，避免与 stdout 采集重复和占满临时磁盘。

### 9.2 级别

| 场景 | 级别 |
|---|---|
| 开始、成功、正常 Abort、客户端断线 | INFO |
| 400/404/409/412/422/428、下游 429/503/504、可恢复超时 | WARN |
| 应用 5xx、持久化失败、模型协议/解析失败、未预期异常 | ERROR |
| 诊断细节但不影响结果 | DEBUG；生产默认关闭 |

业务并发冲突 `SESSION_BUSY` 仍记录 WARN 便于诊断，但告警规则不按单条 WARN 触发；按窗口
比例判断是否异常。

## 10. 安全与数据最小化

### 10.1 允许字段

- 已验证的 `agentId/sessionId/userEntryId/toolCallId`；
- CampusClaw 请求目标 `providerId/modelId`；
- operation、route template、HTTP status、稳定错误码、失败阶段、耗时、计数；
- Java exception class；受控诊断 sink 中最深根因的堆栈。

### 10.2 禁止字段

- `Authorization`、`X-HW-APPKEY`、`X-HW-ID` 的值及全部原始 Header；
- JWT、Cookie、API Key、私有 claim、凭据模式；
- 请求/响应 JSON、Prompt、User/Assistant 文本、文件名、文件正文、Base64；
- thinking、reasoning 字段、签名及原始 SSE chunk；
- Tool arguments、Tool result、Tool delta；
- 上游 `responseModel`、Chat Completion ID、内部 endpoint 完整 URL、OBS 地址；
- page token、ETag 值和本地化 `resMsg`；
- 完整 Throwable message 的无条件结构化副本。

日志字段使用白名单 Builder，不接受任意 `Map<String,Object>`。异常信息先映射为稳定
`failureStage/errorCode/exceptionClass`；只有受控 ERROR 事件附 Throwable。单元测试向所有
输入注入哨兵 secret、Prompt、thinking、Tool 参数和响应体，断言采集日志中不存在哨兵值。

当前 Runtime 契约已经明确 Header 值不得记日志，`sessionId` 不是凭据。本设计保持这一边界，
也不在 CampusClaw 日志中引入公共 `chatId` 或最终用户身份。

## 11. 代码改造映射

### 11.1 `modules/coding-agent-cli`

| 目标位置 | 改造 |
|---|---|
| `runtimeapi/observability/RuntimeRequestLoggingFilter` | 生成 requestId、匹配 operation、记录开始和原子完成；注册 AsyncListener |
| `runtimeapi/observability/HttpRequestLogContext` | 保存 HTTP 白名单上下文 |
| `runtimeapi/observability/RuntimeInvocationLogContext` | 保存 Session/execution 白名单上下文 |
| `RuntimeExceptionHandler` | 不再单独依赖 DEBUG；把 status/resCode/stage 写入请求诊断状态，意外异常由最深 HTTP 事件附堆栈 |
| `RuntimeEventService` | User Entry 接受后补齐 userEntryId，记录 execution.started |
| `RuntimeExecutionContextFactory` / `RuntimeSessionEngineRegistry` | 把 context 传入 ActiveExecution 和 ManagedAgentSessionRequest |
| `RuntimeActiveExecution` | 保存不可变上下文和单调开始时间，不保存凭据或请求体 |
| `RuntimeExecutionCoordinator` | 对 `StopReason.ERROR` 无 Throwable 分支也记录 failure；统一成功/失败/取消/超时终态 |
| `RuntimeSseEmitterSubscriber` | 接收诊断上下文，区分 disconnect、服务器写失败和正常终态；原子去重 |
| Tool Pipeline / Mate Tool Client | 逐步迁移到统一 tool terminal 事件；删除同一异常的重复局部堆栈 |

### 11.2 `modules/ai` 与 `agent-core`

| 目标位置 | 改造 |
|---|---|
| `ai/observability/AiDiagnosticContext` | 定义不会序列化给 Provider 的安全上下文 |
| `SimpleStreamOptions` | 增加显式 diagnostic context；Builder、copy 和 factory 同步 |
| `Agent` / `AgentSessionFactory` | Runtime Session 装配时设置 diagnostic context，工具续轮沿用，同一 Provider 调用生成新 modelInvocationId |
| `MateServiceModelManagerProvider` | 统一 start/completed；映射、connect、HTTP、Content-Type、cancel 全覆盖 |
| `MateChatSseParser` | 终态回调携带安全 code/stage；解析 `event:error` 的稳定 resCode，不保留完整 data |
| `MateModelInvocationException` | 保留 diagnostic code/stage/retryable，不把安全诊断字段暴露为公共 SSE 扩展 |

### 11.3 `mate-campusclaw` 镜像

Java 改动只在 `modules/*` 完成，再运行 `scripts/sync-mate-campusclaw.sh`。镜像的
`application.properties` 不由脚本覆盖，实施 PR 必须单独更新并通过镜像编译。

### 11.4 mate-service 调用端

当前 `mate-service@6d5e6f3` 没有 Browser Chat → CampusClaw 的实现，因此下列内容明确为
target-only：

- `CampusClawClient` 生成 `clientCallId`；
- 在连接前写 `client.call.started`；
- 对 connect/TLS/DNS/HTTP/SSE/decode 写唯一 completed；
- 记录公共 `chatId` 时遵循 mate-service 自身隐私规则，不能把内部 `sessionId` 暴露给浏览器；
- 若公司基础设施已经定义可信跨服务请求标识，再把它映射为 `parentRequestId`。

CampusClaw 自身日志功能不依赖该 Client 才能落地；但要定位“请求根本没有进入 CampusClaw”，
调用端日志是必要条件。

## 12. 测试设计

### 12.1 单元测试

| 测试 | 核心断言 |
|---|---|
| `RuntimeRequestLoggingFilterTest` | 每个请求一个 started、一个 completed；route 使用模板；4xx/5xx 含 status/code；无原始 URI/query/body |
| `RuntimeExceptionHandlerLoggingTest` | validation、RuntimeApiException、unexpected 映射正确；无重复堆栈 |
| `RuntimeExecutionCoordinatorLoggingTest` | `StopReason.ERROR + failure=null` 仍产出 execution failure；success/abort/timeout 各唯一终态 |
| `RuntimeSseEmitterSubscriberLoggingTest` | completion/error/timeout/write failure 竞争只记录一次；disconnect 标记 executionContinues |
| `MateServiceModelManagerProviderLoggingTest` | mapping、connect、非 2xx、Content-Type、error event、非法 chunk、提前关闭、cancel、成功均恰好一个 terminal log |
| `SensitiveLogContractTest` | credentials、Prompt、thinking、Tool arguments/results、raw SSE 哨兵值不出现在日志中 |
| `LoggingConfigurationTest` | canonical、k8s 与 mirror 配置均开启专用 INFO logger；k8s/mirror 使用 ECS JSON |

Logger 测试使用 Logback `ListAppender` 捕获实际事件和 key-value，不 mock `Logger`，避免只验证
方法调用而没有验证最终日志内容。

### 12.2 集成测试

1. 启动真实 CampusClaw 进程并捕获 stdout；
2. 发送非法 JSON，断言 `http.request.started/completed`、400 和
   `INVALID_EVENT_REQUEST`；
3. 使用 MockWebServer 返回 503 ResultBean，断言 `model_http` 与安全 resCode；
4. 返回 200 SSE `event:error`，断言 model、execution、SSE 三个终态可关联，且 HTTP status
   仍为 200；
5. 返回非法 chunk 或在 `[DONE]` 前关闭，断言 `model_parse/model_stream`；
6. 客户端在 User Entry 接受后断开，断言 `sse.disconnected` 且 execution 后续仍有终态；
7. 解析每一行 JSON，检查 `service.name/eventName/requestId/outcome` 和敏感字段黑名单；
8. 在生成的 `mate-campusclaw` 包名和手工 properties 下重复关键进程测试。

### 12.3 缺失终态门禁

测试和运行告警都验证以下不变量：

- 每个 `http.request.started` 在请求/流上限内出现一个 HTTP 或 SSE 终态；
- 每个 `execution.started` 在最大执行时长加清理宽限内出现一个 execution.completed；
- 每个 `model.invocation.started` 在响应总超时加宽限内出现一个 model completed；
- started/terminal 的数量可以按 ID 一一配对，不允许重复或悬空。

## 13. 运行与告警

### 13.1 推荐查询

- 调用失败：`eventName=campusclaw.execution.completed AND outcome=failure`；
- 模型连接失败：`eventName=campusclaw.model.invocation.completed AND failureStage=model_connect`；
- 上游流错误：`failureStage IN (model_stream, model_parse)`；
- 请求未到达：调用端存在 `client.call.started/completed`，同一平台关联上下文不存在
  `campusclaw.http.request.started`；
- 断线后继续执行：同一 `sessionId/userEntryId` 先出现 `sse.disconnected`，后出现
  `execution.completed`；
- 悬空调用：started 超过对应上限仍没有 terminal。

### 13.2 告警基线

- P1/P2 不按单条异常触发，使用 5 分钟窗口失败率和绝对数量；
- `runtime_persistence`、连续 `model_parse` 和缺失 execution terminal 优先级高；
- `SESSION_BUSY`、用户输入 400 和单次客户端断线默认不告警，只用于趋势；
- `model_http` 按下游 status/resCode 分组，区分限流、不可用和协议错误；
- 日志告警不得依赖英文 exception message 正则。

日志保留由公司日志平台配置，应用不硬编码。建议至少 14 天可检索、90 天受控归档，但该数值
必须在实施时对齐公司数据分级和成本政策；未获得平台依据前不把建议写成产品承诺。ERROR
堆栈索引应限制 RBAC，访问日志与完整堆栈可以使用不同保留期。

## 14. 发布顺序

1. 先引入结构化事件模型、敏感字段测试和配置，不改变 Runtime 业务响应；
2. 接入 HTTP started/completed，验证当前 4xx/5xx 均可见；
3. 接入 execution context 和 `StopReason.ERROR` 终态，直接修复当前无日志路径；
4. 接入 Mate Model Provider 分阶段终态；
5. 接入 SSE disconnect 和 Tool 终态；
6. 同步并验证 `mate-campusclaw` 镜像与手工 properties；
7. 在预发布环境以全量 INFO 运行，核对日志量、字段、敏感数据和告警；
8. mate-service 公共 Chat Client 实现时补调用端日志和平台跨服务关联适配。

回滚只需关闭专用 observability logger 或撤回日志实现，不影响 HTTP/SSE 业务契约和数据库。
不得以临时把整个 `com.campusclaw` 调到 DEBUG 的方式替代本设计，因为那会放大日志量并可能
暴露非白名单上下文。

## 15. 源码证据与差异分类

| 分类 | 源码证据或目标决策 |
|---|---|
| 已观察行为 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java:61-77`：提交接口建立 SseEmitter、调用 Service 并注册 detach，没有请求或流生命周期日志 |
| 已观察行为 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeExceptionHandler.java:45-67,117-120`：validation 只记 DEBUG；RuntimeApiException 只在 5xx 记 ERROR |
| 已观察行为 | `modules/coding-agent-cli/src/main/resources/application.yml:110-114`：root 与 `com.campusclaw` 默认 WARN；`application-k8s.yml:9-11` 只提升到 INFO |
| 已观察行为 | `mate-campusclaw/src/main/resources/application.properties:80-83`：镜像运行配置仍为 WARN，且该文件由镜像同步规则明确排除 |
| 已观察行为 | `modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateServiceModelManagerProvider.java:105-156`：映射和 HTTP 错误转入事件流，类中没有 Logger |
| 已观察行为 | `modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateChatSseParser.java:80-133`：error event、提前关闭和解析异常统一 `pushError`，不记录 stage/code 日志 |
| 已观察行为 | `modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java:100-107`：ERROR/ABORTED 是正常终态分支，不抛异常 |
| 已观察行为 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventProjector.java:223-240`：Assistant ERROR 被持久化并只更新 terminalReason |
| 已观察行为 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java:156-179,214-217`：只有非 null Throwable 才写失败 WARN |
| 已观察行为 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeTerminalEventFactory.java:34-57`：即使 Throwable 为 null，StopReason.ERROR 仍发送公共 stream.error；这证明“客户端失败但日志为空”路径成立 |
| 已观察行为 | `modules/agent-core/src/main/java/com/campusclaw/agent/Agent.java:57-58,255-278`：Agent 在虚拟线程运行；请求线程 MDC 不是可靠传播机制 |
| 已观察行为 | `modules/ai/src/main/java/com/campusclaw/ai/types/SimpleStreamOptions.java:32-44` 已有 provider options；`AgentSessionFactory.java:99-113` 使用 `new Agent(aiService)`，没有设置 Runtime 诊断上下文 |
| 已观察行为 | 根 `pom.xml:30-32,130-139` 固定 Spring Boot 3.4.1、SLF4J 与 Logback；本地依赖已包含 Spring Boot ECS structured encoder，可不新增日志 encoder 依赖 |
| Target-only | mate-service 基线没有公共 Chat bridge/CampusClaw Client；进入 CampusClaw 前的网络失败日志需在未来调用端实现 |
| 架构变更 | 新增显式不可变诊断上下文和分层生命周期事件；不以 MDC-only 跨异步边界 |
| 架构变更 | `StopReason.ERROR` 成为 execution failure 日志条件，不再依赖 Throwable 是否存在 |
| 安全加固 | 日志字段改为白名单，禁止 Header、凭据、Prompt、thinking、Tool 参数/结果和原始 SSE |
| 产品约束 | 不改变 11 个 HTTP operation、ResultBean、SSE、Session/Entry 恢复模型或无公共 Run 决策 |

## 16. 验收标准

- 非法请求、Session 不存在、并发冲突、事件接受失败均有入站开始和完成日志；
- 当前 Mate Provider 的 mapping、connect、HTTP、Content-Type、error event、非法 chunk、提前
  close 和 cancel 全部有唯一模型终态；
- `StopReason.ERROR + Throwable=null` 必须出现 `execution.completed outcome=failure`；
- 调用方收到 `stream.error` 时，可通过 `requestId/sessionId/userEntryId` 找到 execution 和
  Provider 根因；
- 客户端断线记录 `executionContinues=true`，不得误报 execution aborted；
- 日志中不存在凭据、Header 值、正文、Prompt、thinking、Tool 参数/结果和 raw SSE；
- 每条生产日志为合法单行 JSON，字段可由日志平台独立索引；
- 不记录逐 token、逐 delta 或心跳日志；
- `modules/*` 与 `mate-campusclaw` Java 镜像同步，手工 properties 具有等价日志配置；
- 相关 Java 测试、进程集成测试、Spotless、Checkstyle、镜像编译通过；
- 设计 Markdown 无 Mermaid，PlantUML ASCII-only，SVG 与源码同步，链接和行锚有效。

## 17. 待集成校准点

以下内容没有当前源码或公司制品证据，不应在实现中自行猜测：

1. 公司网关可信跨服务 request/correlation ID 的 Header 名称、格式和信任边界；
2. 集中日志平台的索引名、采集注解、RBAC、脱敏插件和最终保留周期；
3. mate-service 公共 Chat API 及其 CampusClaw Client 的具体包、接口和公共 `chatId` 日志规则；
4. 公司告警平台的规则格式和 on-call 路由。

这些校准点不阻塞 CampusClaw 本地 `requestId`、execution/model 终态和 ECS stdout 日志落地。

## 18. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-08-25 | 基于当前无日志失败路径，新增调用端、HTTP/SSE、Runtime execution、Model/Tool 四层结构化日志设计，固定显式异步上下文、失败阶段、敏感字段白名单、测试与发布顺序。 |
