# CampusAgent Runtime HTTP API 设计

| 属性 | 值 |
|---|---|
| 文档版本 | 1.14.0 |
| 状态 | 目标设计，尚未实施 |
| 接口评审状态 | Session 生命周期的三个 operation 已确认；第四个接口已确认显式 Run 资源模型，正在评审 CreateRun 输入；其余 operation 待逐个评审 |
| 人类评审契约 | [`chat-http-v1-review.html`](chat-http-v1-review.html)，主维护文档 |
| OpenAPI | [`chat-http-v1.openapi.yaml`](chat-http-v1.openapi.yaml)，1.7.1，过渡期机器契约 |
| WebSocket 语义基线 | [`chat-ws-v2.asyncapi.yaml`](chat-ws-v2.asyncapi.yaml)，2.12.0 |
| pi-mono 源码基线 | `086c32e74530564922d011ade23ff582c9d63116` |
| pi-mono-java 源码基线 | `dff835743fc7f3c93e1154c3eb51028749867ca8` |
| Anthropic TypeScript SDK 源码基线 | `64a1e8e285bbcc4cef2b15ebcadccd8e5f6987ff` |
| Anthropic Managed Agents 文档核对 | 2026-08-17；`managed-agents-2026-04-01` beta |
| 更新日期 | 2026-08-17 |

## 1. 结论

HTTP 版不是把全部命令收进一个 `/chat` 接口，也不是让调用方继续提交
WebSocket 的 `method + params` Frame。已确认的资源模型以 Session、Run、History、
Event 和 Model 为资源边界，共 13 个 operation；其中 Run 是调用方可见、可独立
查询和控制的一轮执行资源。

调用方仍是 `mate-service` Runtime bridge 或明确获授权的内部服务端 SDK。
浏览器不直连 Runtime；公共 `chat_id` 仍由 mate-service 映射为内部
`session_id`。附件正文继续由 Attachment Service 承载，Runtime HTTP API
只接受 `attachment_ids`。

## 2. 接口分组

基础路径为 `/campusclaw-service/v1`。网关 Host 可按部署环境配置，
不属于业务路径的版本契约。
逐接口的展示、评审状态和已确认响应样例以
[`chat-http-v1-review.html`](chat-http-v1-review.html) 为主维护文档。
OpenAPI YAML 在迁移期内继续作为机器可读投影；本轮不删除也不宣告废弃，
待用户后续明确决定。

### 2.1 Session 生命周期

| Method | Path | 语义 |
|---|---|---|
| `POST` | `/agents/{agent_id}/sessions` | 根据 Agent 创建 Session，由 CampusClaw 分配 `session_id` |
| `GET` | `/sessions/{session_id}` | 读取 Session 当前配置、粗粒度状态和 active Run 指针 |
| `DELETE` | `/sessions/{session_id}` | 逻辑删除 Session，使其对 API 立即不可见，并异步清理 Runtime 数据 |

HTTP 没有 `connect(mode=resume)`。每个请求独立认证和定位 Session；网络恢复只需
重新读取 Session、Run 或 History。`POST /agents/{agent_id}/sessions`
不包含 Request Body，不接受调用方指定的 `session_id` 或
`model_id`。`agent_id` 是创建后不可变的 Agent 绑定；
`session_id` 由 CampusClaw 生成，`model_id` 由 Agent 目录的
`defaultModel` 决定。创建后的模型切换必须显式调用
`PUT /sessions/{session_id}/model`；删除后的 `session_id`
永久禁止复用。

该接口支持两套公司凭据，OpenAPI 使用“两个可选安全要求、
每个要求内两个 Header 必须同时满足”表达。JWT 是文档、
Swagger 示例和新客户端的默认选择；APPKEY 是明确公开的兼容契约，
不得只藏在实现分支中。

| 认证模式 | 必填 Header | 定位 | 约束 |
|---|---|---|---|
| JWT | `X-HW-ID` + `Authorization: Bearer <JWT>` | 首选/默认 | 公司 JWT 验证器负责 claim、签名、issuer 和 audience |
| APPKEY | `X-HW-ID` + `X-HW-APPKEY` | 兼容 | 公司 APPKEY/私钥体系验证器负责具体校验算法 |

两组凭据二选一。同时携带 `Authorization` 和 `X-HW-APPKEY`
视为身份语义冲突，返回 HTTP `401` 和
`AUTH_CREDENTIAL_CONFLICT`；任一组合缺失、格式错误或校验失败统一
返回 `401 UNAUTHENTICATED`。选中一种模式且验证失败后禁止
再尝试另一种模式，避免认证降级和身份混淆。
`traceparent` 不属于本 HTTP API 契约。

创建成功前，Runtime 必须完成以下初始化：

1. 通过统一认证适配层验证且仅生成一个不可变
   `CallerAuthContext`，再验证 PATH 中 `agent_id` 的资源 ID 格式；
2. 在受控根目录中解析 Agent 目录，拒绝路径或符号链接越界；
3. 读取 `.campusagent/settings.json`，验证 `settings.agentId`
   与 PATH 值按 ASCII 字节完全一致，并固定 `agentVersion`；
4. 验证 `enabledModels` 非空、无重复且包含 `defaultModel`；
5. 调用 `resolveModel(agent_id, defaultModel)` 获得有效模型 descriptor；
6. 在所有外部配置校验通过后生成全局唯一、删除后不复用的
   `session_id`；
7. 组装不可变 SessionContext，加载 `SYSTEM.md` 和 Skills，注册
   `read/get_tool_info/call_tool`，并创建独立 `AgentSession + Agent`；
8. 原子保存包含 `agent_version` 和 bundle revision 的内部
   SessionRecord，并将已就绪 Session 注册到 SessionPool；
9. 使用 `ResultBeanFactory.getFactory().normal(sessionResponseVO)` 包装
   SessionResource，返回 `201 Created`、`Location` 和 ResultBean。

初始化只组装运行对象，不调用大模型、不消耗 token，不创建
Message 或 RunRecord；因此创建响应中 `state=idle` 且
`active_run=null`。`thinking=hidden` 来自 Runtime 的 Session 默认值，
不写入 Managed `settings.json`。任一步在 SessionRecord 提交前失败都不
暴露 `session_id`，并丢弃未持久化的内存 Session。

`settings.json` 是发布快照，Model Manager 仍是模型绑定、启用状态和
调用的最终权威。目录缺少有效默认模型时返回 HTTP `422`，
响应体 `resCode=AGENT_MODEL_NOT_CONFIGURED`；Model Manager 暂时不可用时
返回 HTTP `503`，响应体 `resCode=MANAGER_UNAVAILABLE`。

已确认的第一个接口使用 `SessionCreateResponseVO`，其字段不因后续
GetSession 评审而隐式扩张。第一个接口的完整成功响应为：

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "session_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "agent_id": "agent_011CZkYqphY8vELVzwCUpqiQ",
    "model_id": "model_011CZq2GkV8aD4NwP7sLmXfR",
    "state": "idle",
    "thinking": "hidden",
    "active_run": null,
    "created_at": "2026-08-15T11:30:00Z"
  }
}
```

`agent_version` 和内部 record revision 只在 CampusClaw 持久化，不进入
创建响应。创建操作不要求 `Idempotency-Key` 或 `If-Match`；
每次成功 `POST` 都创建新 Session。如果持久化已成功但响应在网络中
丢失，无条件重试会再创建一个 Session；未被 mate-service 绑定的
孤立 Session 由后台超时清理。其他副作用接口的幂等或并发规则属于
各自 operation，不由创建 Session 接口继承。

#### 2.1.1 第二个已确认接口：读取 Session

```http
GET /campusclaw-service/v1/sessions/{session_id}
```

该接口按 `session_id` 读取已经存在的 Session 当前资源，不创建或恢复
Session，不调用模型、不消耗 token，也不为了查询而实时调用 Model Manager。
它是 Session 控制面的只读入口，用于确认资源存在及访问权、读取当前默认
配置、判断是否存在 active Run，并取得后续 GetRun 的定位指针。已确认契约使用
独立的 `GetSessionResponseVO`，不改变第一个接口已经确认的创建响应。

| 字段 | 已确认契约 | 具体作用 |
|---|---|---|
| `session_id` | 必填 | Session 不透明标识 |
| `agent_id` | 必填 | 创建后不可变的 Agent 绑定 |
| `model_id` | 必填 | Session 当前默认模型；允许后续切换 |
| `state` | `idle \| running` | 只回答 Session 当前是否存在 active Run |
| `thinking` | `hidden \| full` | Session 默认的 reasoning content 披露级别，不表示推理强度 |
| `active_run` | object 或 `null` | active Run 指针；仅含 `run_id` 和 `queued \| running` 状态，idle 时为 `null` |
| `created_at` | RFC 3339 | Session 创建时间 |
| `updated_at` | RFC 3339 | Session 资源最后更新时间 |

`active_run.state` 只取 `queued | running`，用于让调用方决定是否立即读取
GetRun。`phase`、该 Run 固化的 `model_id/thinking`、partial Message、open
content、工具和 steer 队列全部属于 GetRun，不在此处复制。`history_seq` 和
分页 cursor 属于 History API；`run_seq` 属于 Run Event API。这样
GetSession 的响应大小固定，不承担聊天恢复快照职责。

当前响应提案为：

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "session_id": "01JY8W6M8D9K4H2Q7P3V5N1R0T",
    "agent_id": "agent_01JY8VZY4CRQN4PJW8M94D1B2C",
    "model_id": "claude-sonnet-4-5",
    "state": "running",
    "thinking": "hidden",
    "active_run": {
      "run_id": "run_01JY8X2E3R4T5Y6U7I8O9P0A1S",
      "state": "running"
    },
    "created_at": "2026-08-15T10:30:00+08:00",
    "updated_at": "2026-08-16T09:15:21+08:00"
  }
}
```

![GetSession 已确认响应](http_get_session_response.svg)

[PlantUML 源码：`http_get_session_response`](diagram.puml#L1225)

pi 的 `thinkingLevel` 表示推理强度，可取
`off | minimal | low | medium | high | xhigh | max`；CampusClaw 当前已经确认的
`thinking` 表示 reasoning content 可见性，只取 `hidden | full`。已确认保持
已确认语义；需要推理强度时新增 `reasoning_effort`，避免同一个字段混合两个
正交概念。若本轮直接拆成 `thinking_visibility + reasoning_effort`，必须明确
重开第一个接口，而不能静默改变已确认契约。

GetSession 当前不返回 `name`、`history_seq`、完整 `transcript`、
`queuedSteer`、`phase`、`attached` 或 `locked`。用户可见会话名称属于
mate-service 的 Chat 元数据；完成的 Message/RunRecord 由 History API
分页返回；active Message、open content、工具、steer 队列和执行阶段由
GetRun 返回；`attached` 是 pi 的连接相对状态，`locked` 是 live Runtime 的
内部独占状态，均不是 CampusClaw 公共 Session 属性。

| 读取需求 | 负责接口 |
|---|---|
| Session 当前默认 `model_id/thinking`、`idle/running` 和 active Run 指针 | `GET /sessions/{session_id}` |
| 已提交 Message/RunRecord、`history_seq` 和分页 cursor | `GET /sessions/{session_id}/history` |
| active/terminal Run 的 phase、固化配置、partial Message、工具和 steer 状态 | `GET /sessions/{session_id}/runs/{run_id}` |
| Run 的实时增量及 `run_seq` 恢复 | `GET /sessions/{session_id}/runs/{run_id}/events` |

读取成功返回 `ETag` 和 `Cache-Control: no-store`。已确认仅将 `ETag` 用于
后续 Model/Thinking 配置写入的 `If-Match` 并发控制，不给本 GET 增加
`If-None-Match/304` 分支。不存在和已删除的 Session 统一返回
`404 SESSION_NOT_FOUND`，避免泄露历史状态；`active_run` 固定为只含
`run_id/state` 的指针。

本小节和主维护 HTML 中的第二个接口已经用户确认。OpenAPI 本轮仍不更新。

#### 2.1.2 第三个已确认接口：删除 Session

```http
DELETE /campusclaw-service/v1/sessions/{session_id}
X-HW-ID: <CALLER_ID>
Authorization: Bearer <JWT>
```

该接口不只是把 Session 从当前 Pod 的内存池中移除，而是结束
CampusClaw 对该 Runtime Session 的管理。已确认语义是：服务端先原子
持久化 `DELETING` 状态和可重试的清理任务，然后返回 `204 No Content`。
从持久化成功开始，GetSession、创建 Run 和配置写入都不再能访问
该 Session；后台 Worker 完成物理清理，但不向调用方暴露删除任务
状态。因此 `204` 表示“逻辑删除已完成”，不表示所有存储介质上的
字节已经擦除。

| 契约点 | 已确认契约 | 设计原因 |
|---|---|---|
| Request Body | 无 | 删除目标由 URI 唯一确定 |
| 成功响应 | `204 No Content`，无 ResultBean | HTTP `204` 不允许业务响应体 |
| active Run | 接受删除并自动 abort，终态收敛为 `aborted` | 删除 Session 是更强的终止意图，不要求调用方编排两个接口 |
| 不存在、删除中或已删除 | 对具有删除 scope 的调用方统一返回 `204` | 保证网络重试幂等，不暴露 tombstone 状态 |
| 幂等与并发 Header | 不要求 `Idempotency-Key` 或 `If-Match` | URI 和持久化 tombstone 已提供幂等语义；删除不是配置修改 |
| Runtime 清理范围 | History、RunRecord、Run Event Journal、幂等记录和内存运行对象 | 避免已删除 Session 继续占用 Runtime 资源 |
| 最小保留 | tombstone 严格只包含 `session_id` 和 `deleted_at` | 禁止 Session ID 复用，并支持删除重试去重 |
| 不属于本接口 | mate-service Chat 名称/业务元数据、附件对象 | 它们分别由 mate-service 和 Attachment Service 拥有 |

逻辑删除与清理任务必须在同一持久化事务中提交。如果该事务失败，
返回 `500 SESSION_DELETE_FAILED`，Session 不得停留在部分删除状态。事务
提交后的 abort、内存释放或物理清理失败由持久化任务重试；已删除
Session 对公共 API 仍然不可见。

tombstone 字段集合已对齐：若落地为 `t_session_tombstone`，则该表永久记录
严格只有 `session_id` 和 `deleted_at`，不增加 `purged_at`、`cleanup_state`、
`owner_scope` 或 Session 业务快照。内部重试次数、租约、错误和清理进度属于
短期 `t_session_cleanup_task`，清理完成后删除任务记录。由于 tombstone 不保留
owner 信息，对“不存在/已删除”的重复删除只能依据 `CallerAuthContext` 的动作级
Session 删除 scope 授权，不得依赖 tombstone 重建资源所属关系。

认证继续沿用前两个接口已确认的 JWT 首选和 APPKEY 兼容契约，混合
凭据仍返回 `401 AUTH_CREDENTIAL_CONFLICT`。语法无效的 `session_id` 返回
`400 INVALID_SESSION_ID`；资源存在但调用方无权删除时返回
`403 FORBIDDEN`。异常响应只有 `resCode/resMsg`，不包含 `result`。

![HTTP Session 逻辑删除](http_delete_session.svg)

[PlantUML 源码：`http_delete_session`](diagram.puml#L1312)

本小节和主维护 HTML 中的第三个接口已经用户确认。OpenAPI 本轮仍不更新。

![HTTP Session 创建](http_session_creation.svg)

[PlantUML 源码：`http_session_creation`](diagram.puml#L996)

### 2.2 消息与 Run

用户已经确认采用“显式 Run 资源”：Run 是调用方可见的一等资源，GetSession
继续保留 `active_run` 指针。Anthropic 风格 Session Events 仅保留为设计参考，
不再是当前 HTTP 资源模型候选。

| Method | Path | 语义 |
|---|---|---|
| `POST` | `/sessions/{session_id}/runs` | 提交用户文本/附件并创建异步 Run |
| `GET` | `/sessions/{session_id}/runs` | 分页列出 Run |
| `GET` | `/sessions/{session_id}/runs/{run_id}` | 读取 active 快照或权威终态 |
| `POST` | `/sessions/{session_id}/runs/{run_id}/steers` | 向 active Run 追加文本指导 |
| `POST` | `/sessions/{session_id}/runs/{run_id}/abort` | 幂等请求终止 Run |

`POST /runs` 原子持久化用户 Message、分配 `run_id` 并占用 active-run；成功返回
`202 Accepted`、`Location`、`run_id` 和 `user_message_id`。响应表示已接受，不表示
模型执行完成。接受 Run 时服务端把 `session.current_model_id`
原子固化到 `RunRecord.model_id`；同一 Run 的所有模型调用都使用该值，
后续 Session 模型切换不影响已开始 Run。`POST /runs`、Steer 和 Abort 必须携带
`Idempotency-Key`；相同键和相同规范化负载返回原结果，相同键不同负载返回
`409 IDEMPOTENCY_CONFLICT`。

#### 2.2.1 已确认架构决策：每轮执行是显式 Run 资源

`Run` 可以理解为：一个 Session 中，由一次用户输入触发的一轮独立执行。

```text
Session：持续保存整段会话上下文
  ├─ Run 1：用户问“分析订单”
  ├─ Run 2：用户问“只看异常订单”
  └─ Run 3：用户问“导出报告”
```

它不是新的 Session，也不是一次底层模型请求。一个 Run 可能包含多次模型调用、
工具调用、重试和多个 Assistant Message。用户已经确认它是调用方可见的一等资源，
因此 `POST /sessions/{session_id}/runs` 的完整作用是：

1. 持久化本次用户消息；
2. 为本轮执行分配 `run_id`；
3. 固化本轮使用的 `model_id`、`thinking` 和附件快照；
4. 占用 Session 唯一的 active Run 位置；
5. 创建后台执行任务；
6. 立即返回 `202`，不等待模型执行结束。

`run_id` 随后用于查询本轮状态和阶段、接收增量事件、Abort 或 Steer 本轮、
区分 Session 内的多轮执行、在 HTTP 断线后恢复，以及独立记录本轮错误、耗时和
模型快照。

Anthropic Managed Agents 选择了不同的对外模型。官方文档将 Session 定义为
事件驱动状态机：调用方通过 `POST /v1/sessions/{session_id}/events` 发送
`user.message`，响应返回已经接收并由服务端分配 `event_id` 的用户事件；执行状态
由 Session 的 `idle | running | rescheduling | terminated` 和 Session Event
Stream 表达。事件排在先前事件后时 `processed_at=null`，而不是创建独立的
Session Run。[Anthropic Send Events API](https://platform.claude.com/docs/en/api/cli/beta/sessions/events/send)、
[Session event stream](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)、
[Session operations](https://platform.claude.com/docs/en/managed-agents/session-operations)

Anthropic 创建 Session 后可以再发送事件，也可以用 `initial_events` 在创建时
直接进入 `running`；这些初始事件会在创建响应前校验并持久化，但不会在创建响应
中回显。[Start a session](https://platform.claude.com/docs/en/managed-agents/sessions)
其名为 Deployment Run 的资源只记录一次 Deployment 触发是否成功创建 Session，
成功时关联 `session_id`，明确不跟踪 Session 执行生命周期，因此不等同于这里的
Session Run。[Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)、
[Deployment Runs API](https://platform.claude.com/docs/en/api/beta/deployment_runs)

| 对比项 | 已选：CampusClaw 显式 Run | 未选参考：Session Events |
|---|---|---|
| 提交用户输入 | `POST /sessions/{id}/runs` | `POST /sessions/{id}/events`，发送 `user.message` |
| 接收结果标识 | `run_id`、`user_message_id` | 用户事件 `event_id` |
| 执行状态归属 | 独立 Run 资源 | Session 状态 |
| 执行过程 | Run Events | Session Events |
| 中止与 Steer | 针对 `run_id` 的 Abort / Steer | `user.interrupt` / 后续 `user.message` |
| 多轮区分 | 每轮一个 `run_id` | 依靠事件序列和 Session 状态 |
| 并发语义 | 一个 active Run，冲突返回 `409` | 事件可排在先前事件后，`processed_at=null` 表示尚未处理 |
| 断线恢复与审计 | 按 `run_id` 精确恢复，独立记录错误、耗时和模型快照 | 按 Session 事件游标恢复，轮次边界由调用方推导 |
| 对现有设计的影响 | 保持 GetSession `active_run` 以及 GetRun、Run Events、Abort、Steer | 必须重开 GetSession，并重构上述 Run operation 与 History 边界 |

![HTTP 执行资源模型对比](http_execution_resource_model.svg)

[PlantUML 源码：`http_execution_resource_model`](diagram.puml#L1529)

用户已在 2026-08-17 选择显式 Run：mate-service 可以按 `run_id` 精确查询、恢复、
中止、Steer 和审计某一轮执行。实现仍借鉴 Anthropic 的持久化事件、权威完整事件
与非权威增量预览分层，但不取消 Run 资源，也不重开已确认的 GetSession
`active_run`。

#### 2.2.2 第四个评审中接口：创建 Run

```http
POST /campusclaw-service/v1/sessions/{session_id}/runs
X-HW-ID: <CALLER_ID>
Authorization: Bearer <JWT>
Idempotency-Key: <OPAQUE_KEY>
Content-Type: application/json
```

该接口把一条新的用户输入提交给已经存在的 Session，并创建一个可独立查询的
异步 Run。它不是“同步聊天”接口：成功响应只表示输入和执行意图已被可靠接受，
不等待首个 token、工具调用或最终 Assistant Message。调用方随后通过 GetRun、
Run Events 和 History 观察过程与终态；客户端关闭或 HTTP 请求连接中断不会终止
已经接受的 Run，终止必须显式调用 Abort Run。

当前请求提案为：

```json
{
  "message": "请分析附件中的订单数据，并列出异常项。",
  "attachment_ids": [
    "attachment_011CZm8VpK4rNs6WtY2hDqfB"
  ]
}
```

| 字段 | 当前推荐约束 | 具体作用 |
|---|---|---|
| `message` | 可选；提供时包含至少一个非空白字符，最多 262144 个字符 | 用户文本；校验时可判断空白，但持久化和幂等比较使用原始值，不做 trim |
| `attachment_ids` | 可选；最多 32 个，元素唯一、大小写敏感并保留请求顺序 | 引用已由 Attachment Service 绑定当前 Session 的附件 |

`message` 和 `attachment_ids` 至少有一项有效值，允许纯文本、纯附件以及
文本加附件三种形态。纯附件请求不生成隐藏默认 Prompt。

当前推荐保持最窄业务输入，不把所有 pi `PromptOptions` 暴露为 HTTP 字段。pi 的
`AgentSession.prompt()` 除图片外还接受 `expandPromptTemplates`、
`streamingBehavior=steer|followUp`、`source` 和内部 preflight callback；后四者分别
属于命令展开、运行中队列策略、Runtime 来源标记和进程内回调，不是 mate-service
创建新 Run 时应控制的业务数据。CreateRun 已要求 Session 没有 active Run，
Steer/FollowUp 由后续独立 operation 表达，因此不接收 `streamingBehavior`。

请求也不接收 URL、MIME、文件名、Base64、OBS key、tenant、user、system
instructions、tool choice、timeout、priority 或任意 provider 参数。认证负责调用方
身份；Agent 定义负责系统指令和工具；Attachment Service 负责附件正文；Runtime
策略负责超时、重试和调度。`Idempotency-Key` 已承担客户端重复提交标识，不再增加
`client_request_id`。

本轮需要确认两类可能的额外输入：

1. 是否继续使用扁平的 `message + attachment_ids`，还是改为可排序、可扩展的
   `content[]` typed blocks；前者与 pi 的“text + images”边界更接近，Java VO
   校验也更直接，当前推荐前者；
2. 是否允许请求用 `model_id/thinking` 覆盖单 Run。当前推荐不允许：CreateRun
   原子固化 Session 当前模型和 thinking；模型或 thinking 的持久切换由 Session
   配置 operation 完成。若担心配置读取与 Run 创建之间的竞争，可后续评审
   `If-Match` 配置前置条件，而不是复制可变配置到请求体。

`Idempotency-Key` 必填，长度为 8 到 128 个可见 ASCII 字符，作用域为
`(session_id, createRun)`，并在 Session 删除前保留。规范化负载由原始
`message` 值和有序 `attachment_ids` 组成；省略 `attachment_ids` 与空数组
等价。服务端必须先查询已经接受的同键结果，再检查 active Run 或重新解析附件：
同键同负载始终返回原 `run_id/user_message_id`，即使原 Run 已完成或依赖服务
当前不可用；同键不同负载返回 `409 IDEMPOTENCY_CONFLICT`。所有接受前错误都
不占用幂等键，调用方可以用原键重试。

推荐接受顺序如下：

1. 完成双凭据认证、Session 动作授权，以及 PATH、Header 和 JSON 严格校验；
2. 查询已接受的幂等结果；命中时校验负载指纹并立即返回原结果；
3. 读取未删除 Session，检查当前没有 active Run；
4. 向 Attachment Service 批量解析整组附件，验证 Session 绑定和 READY 状态，
   单向标记 `referenced_at`，并对“有效历史附件 + 本次附件”执行完整模型输入策略校验；
5. 解析 Session 当前模型的权威 descriptor，固化 `model_id/thinking`，生成
   `run_id` 和 `user_message_id`；
6. 在 CampusClaw 本地同一事务中持久化用户 Message、`queued` RunRecord、
   Session active-run 指针、幂等结果和持久化执行任务；
7. 返回 `202 Accepted`，后台执行器领取任务并将 Run 推进到 `running` 和终态。

第 6 步的数据库唯一约束必须保证每个 Session 至多一个 active Run；两个不同
幂等键并发提交时只能有一个成功，另一请求返回 `409 RUN_ACTIVE`。CampusClaw
事务与 Attachment Service 的 `referenced_at` 更新之间没有跨服务 XA：若附件已
标记引用但第 6 步失败，引用标记保守保留并由附件生命周期对账处理；不得因此
返回虚假的 `run_id`，也不得消费幂等键。Run 一旦接受，后续模型输入读取或
Provider 调用失败属于 Run 终态错误，不再改写本接口的 `202`。

当前推荐成功响应保持最窄结构：

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "run_id": "run_01JY8X2E3R4T5Y6U7I8O9P0A1S",
    "user_message_id": "msg_01JY8X2E3R4T5Y6U7I8O9P0B2T"
  }
}
```

`202` 已经表达 accepted，因而不重复返回常量 `accepted=true`；是否为幂等重试
是服务端实现细节，也不返回 `idempotent`。Run 的 `state`、固化后的
`model_id/thinking`、执行 phase 和终态由 GetRun 负责。响应同时返回指向
GetRun 的 `Location`、`Cache-Control: no-store` 和实际 `Content-Language`。

![HTTP 异步 Run 接受边界](http_create_run.svg)

[PlantUML 源码：`http_create_run`](diagram.puml#L1412)

显式 Run 资源模型已经确认。本轮只评审 CreateRun 输入：输入结构、是否允许单 Run
覆盖 `model_id/thinking`，以及是否接受非模型业务 metadata。成功状态、active Run
冲突或排队、成功 `result` 和错误码仍是后续决策，不因本轮展示而确认。OpenAPI
本轮不更新。

### 2.3 事件与历史

Run Event Journal 归属于已确认的显式 Run 资源，并使用 `run_id/run_seq` 作为
对外恢复边界。

| Method | Path | 语义 |
|---|---|---|
| `GET` | `/sessions/{session_id}/runs/{run_id}/events` | 读取 Run 的有序事件；支持 SSE 和 JSON 分页 |
| `GET` | `/sessions/{session_id}/history` | 按 `history_seq` 分页读取权威 Message/RunRecord |

事件接口按 `Accept` 提供两种同义视图：

- `text/event-stream`：实时消费；SSE `id` 等于 `run_seq`，断线后使用
  `Last-Event-ID` 恢复；
- `application/json`：使用 `after_run_seq` 分页补拉、批处理或对账。

HTTP 版不保留连接级 `seq`。`run_seq` 成为一个 Run 内唯一的权威事件游标；
为支持跨请求补拉，Runtime 必须持久化有界 Run Event Journal。这是相对现有
WebSocket 设计的架构改造。终态 Message 和 RunRecord 仍写入权威 History，
客户端不能仅依赖事件缓存恢复长期历史。

### 2.4 模型与 Session 配置

| Method | Path | 语义 |
|---|---|---|
| `GET` | `/sessions/{session_id}/models` | 列出当前 Agent 和调用身份可用模型 |
| `PUT` | `/sessions/{session_id}/model` | 切换 Session 当前模型 |
| `PUT` | `/sessions/{session_id}/thinking` | 修改默认 thinking 披露级别 |

模型列表使用 Session scope，而不是公开 `/agents/{agent_id}/models`，避免调用方
绕过 Session 绑定查询其他 Agent。Model/Thinking 变更只允许在没有 active Run
时执行，并要求 `If-Match` 携带最近一次 Session `ETag`；并发版本不一致返回
`412 PRECONDITION_FAILED`。

## 3. WebSocket 到 HTTP 的语义映射

| WebSocket v2 | HTTP v1 |
|---|---|
| `connect(mode=create)` | `POST /agents/{agent_id}/sessions`；CampusClaw 生成 `session_id` |
| `connect(mode=resume)` | 无对应命令；重新 `GET` Session/Run/History |
| `chat.send` | `POST /sessions/{session_id}/runs` |
| `chat.steer` | `POST .../runs/{run_id}/steers` |
| `chat.abort` | `POST .../runs/{run_id}/abort` |
| `chat.history` | `GET /sessions/{session_id}/history` |
| `session.get` | `GET /sessions/{session_id}` |
| `models.list` | `GET /sessions/{session_id}/models` |
| `model.set` | `PUT /sessions/{session_id}/model` |
| `thinking.set` | `PUT /sessions/{session_id}/thinking` |
| EventFrame | Run Event Journal；事件机制借鉴 Anthropic，但恢复和控制边界仍是 `run_id` |
| RequestFrame `id` | HTTP 请求关联由网关/框架处理，不参与业务幂等 |
| connection generation/close code | 删除；改用 HTTP 状态、ETag 和幂等键 |

## 4. 状态、并发与恢复

资源模型已经确认，但以下并发、终态和恢复细节仍是 CreateRun 及后续接口的当前
提案，尚未逐项冻结：

- 每个 Session 同一时刻只允许一个 active Run；冲突返回 `409 RUN_ACTIVE`。
- Run 接受后不依赖发起 HTTP 连接存活；连接关闭不等于 Abort。
- `GET Run` 返回 running 快照或 `done/aborted/error/interrupted` 终态。
- Pod 重启且原 Run 无法继续时，Message 和 RunRecord 对账为 `interrupted`，
  错误码为 `RUN_INTERRUPTED`。
- SSE 断线优先以 `Last-Event-ID` 继续；Event Journal 已过保留水位时返回
  `410 EVENT_CURSOR_EXPIRED`，客户端改用 Run 快照和 History 恢复。
- Session 读取响应返回 `ETag`；配置写入使用 `If-Match`，Run 副作用写入使用
  `Idempotency-Key`，两类机制职责不混用。
- `Session.state` 只表达是否存在 active Run；执行阶段由 GetRun 返回，避免把
  pi 的执行过程枚举误当成 Session 生命周期状态。
- `history_seq` 只由 History API 返回，`run_seq` 只由 Run Event API 返回；
  GetSession 不复制任何恢复水位。

## 5. ResultBean、HTTP 状态与国际化

公司内部普通 JSON 接口的成功响应使用
`resCode/resMsg/result` 三字段 ResultBean，异常响应只包含
`resCode/resMsg`，不使用 RFC 9457 `application/problem+json`。这是相对原 HTTP
草案的公司集成约束。本版已经冻结 Session 生命周期三个接口；
其余 operation 的业务语义仍按后续逐个评审，但普通 JSON 响应
最终也必须遵守同一包装。SSE 事件流和 HTTP `204` 无响应体
不使用 ResultBean。

| 字段 | 成功 | 异常 | 调用方规则 |
|---|---|---|---|
| `resCode` | 固定字符串 `0` | 稳定大写 snake_case 错误码 | 只根据此字段分支，不解析 `resMsg` |
| `resMsg` | 固定 `success` | 按 Locale 解析的人类可读文本 | 只用于展示和日志 |
| `result` | operation 对应 Response VO | 不出现 | 仅成功响应读取 |

ResultBean 只包装响应体，不把所有异常降级为 HTTP `200`。
HTTP status 仍表达传输和粗粒度失败类别，`resCode` 表达稳定业务
语义。例如：

```json
{
  "resCode": "AGENT_MODEL_NOT_CONFIGURED",
  "resMsg": "该 Agent 未配置有效的默认模型。"
}
```

第一个接口冻结的错误码、HTTP status 和中英文消息如下。
错误码枚举名、MessageSource key 和 `resCode` 必须完全一致：

| HTTP | `resCode` | `zh_CN` | `en_US` |
|---|---|---|---|
| `400` | `INVALID_AGENT_ID` | `agent_id 格式不正确。` | `The agent_id format is invalid.` |
| `401` | `UNAUTHENTICATED` | `调用方身份认证失败。` | `Caller authentication failed.` |
| `401` | `AUTH_CREDENTIAL_CONFLICT` | `请求不能同时携带 JWT 和 APPKEY 凭据。` | `JWT and APPKEY credentials must not be supplied together.` |
| `403` | `FORBIDDEN` | `当前调用方无权为该 Agent 创建 Session。` | `The caller is not allowed to create a Session for this Agent.` |
| `404` | `AGENT_NOT_FOUND` | `指定的 Agent 不存在。` | `The specified Agent does not exist.` |
| `422` | `AGENT_NOT_AVAILABLE` | `指定的 Agent 当前不可用。` | `The specified Agent is currently unavailable.` |
| `422` | `AGENT_MODEL_NOT_CONFIGURED` | `该 Agent 未配置有效的默认模型。` | `The Agent has no valid default model configured.` |
| `500` | `SESSION_INITIALIZATION_FAILED` | `Session 初始化失败。` | `Session initialization failed.` |
| `503` | `MANAGER_UNAVAILABLE` | `Model Manager 暂时不可用，请稍后重试。` | `Model Manager is temporarily unavailable. Try again later.` |

第二个 GetSession 接口已确认使用
`INVALID_SESSION_ID`、`UNAUTHENTICATED`、`AUTH_CREDENTIAL_CONFLICT`、
`FORBIDDEN` 和 `SESSION_NOT_FOUND`；仍保持异常体只有
`resCode/resMsg`。这些 operation-specific 错误已随第二个接口确认而冻结。

第三个 DeleteSession 接口已确认：成功返回无响应体的
`204`；失败使用 `INVALID_SESSION_ID`、`UNAUTHENTICATED`、
`AUTH_CREDENTIAL_CONFLICT`、`FORBIDDEN` 和 `SESSION_DELETE_FAILED`。
不存在、删除中或已删除按已确认语义统一返回 `204`，因此不新增
`SESSION_NOT_FOUND`。以下错误码和消息已经冻结：

| HTTP | `resCode` | `zh_CN` | `en_US` |
|---|---|---|---|
| `400` | `INVALID_SESSION_ID` | `session_id 格式不正确。` | `The session_id format is invalid.` |
| `401` | `UNAUTHENTICATED` | `调用方身份认证失败。` | `Caller authentication failed.` |
| `401` | `AUTH_CREDENTIAL_CONFLICT` | `请求不能同时携带 JWT 和 APPKEY 凭据。` | `JWT and APPKEY credentials must not be supplied together.` |
| `403` | `FORBIDDEN` | `当前调用方无权删除该 Session。` | `The caller is not allowed to delete this Session.` |
| `500` | `SESSION_DELETE_FAILED` | `Session 删除失败。` | `Session deletion failed.` |

第四个接口当前提案成功返回 `202` ResultBean，失败仍只有
`resCode/resMsg`。附件不存在、越权、未绑定、已删除或其他不可披露状态统一为
`INVALID_ATTACHMENT`，避免资源枚举；附件属于当前 Session 但尚未 READY 时才
返回可重试的 `ATTACHMENT_NOT_READY`。以下错误码和消息仅用于预览，尚未进入
字段评审：

| HTTP | `resCode` | `zh_CN` | `en_US` |
|---|---|---|---|
| `400` | `INVALID_SESSION_ID` | `session_id 格式不正确。` | `The session_id format is invalid.` |
| `400` | `INVALID_IDEMPOTENCY_KEY` | `Idempotency-Key 格式不正确。` | `The Idempotency-Key format is invalid.` |
| `400` | `INVALID_RUN_REQUEST` | `Run 请求内容不符合约束。` | `The Run request does not satisfy the required constraints.` |
| `401` | `UNAUTHENTICATED` | `调用方身份认证失败。` | `Caller authentication failed.` |
| `401` | `AUTH_CREDENTIAL_CONFLICT` | `请求不能同时携带 JWT 和 APPKEY 凭据。` | `JWT and APPKEY credentials must not be supplied together.` |
| `403` | `FORBIDDEN` | `当前调用方无权在该 Session 中创建 Run。` | `The caller is not allowed to create a Run in this Session.` |
| `404` | `SESSION_NOT_FOUND` | `指定的 Session 不存在。` | `The specified Session does not exist.` |
| `409` | `RUN_ACTIVE` | `该 Session 已存在正在执行的 Run。` | `The Session already has an active Run.` |
| `409` | `IDEMPOTENCY_CONFLICT` | `Idempotency-Key 已用于不同的请求内容。` | `The Idempotency-Key was already used with different request content.` |
| `409` | `ATTACHMENT_NOT_READY` | `附件尚未准备就绪，请稍后重试。` | `The attachment is not ready. Try again later.` |
| `422` | `INVALID_ATTACHMENT` | `请求包含无效附件。` | `The request contains an invalid attachment.` |
| `422` | `ATTACHMENT_NOT_SUPPORTED` | `当前模型不支持该附件输入。` | `The current model does not support the attachment input.` |
| `500` | `RUN_ACCEPTANCE_FAILED` | `Run 接收失败。` | `Run acceptance failed.` |
| `503` | `RUNTIME_DEPENDENCY_UNAVAILABLE` | `Runtime 依赖服务暂时不可用，请稍后重试。` | `A Runtime dependency is temporarily unavailable. Try again later.` |

Locale 从 `Accept-Language` 解析，第一版只支持 `zh-CN` 和
`en-US`；缺失、不支持或资源 key 缺失时回退 `en-US`，禁止使用
JVM 系统 Locale。响应返回 `Content-Language`，其值为实际使用的
`en-US` 或 `zh-CN`。Service 异常只携带错误码和有界参数；
`@RestControllerAdvice` 负责 Locale 解析、消息格式化、HTTP status
和 ResultBean 异常响应。

异常响应不得包含凭据、内部 Header、私有 claim、Prompt、原始 thinking、
OBS 地址、Bucket、预签名 URL 或内部堆栈。`503` 的重试建议通过
标准 `Retry-After` Header 传递，不向 ResultBean 增加私有字段。

## 6. Java 开发体验与内部制品替换

### 6.1 代码边界

Controller 接收和返回 VO，Service 返回未包装的 Response VO；
ResultBean 不进入 Service、Session Factory、Runtime Store 或 Manager Adapter。
创建 Session 的 Controller 目标代码形状为：

```java
SessionCreateResponseVO result = sessionService.createSession(agentId);
return ResponseEntity.created(location)
        .body(ResultBeanFactory.getFactory().normal(result));
```

这是 target-only 代码形状。当前 pi-mono-java 基线没有该 HTTP
Controller，本地与设计仓库也没有公司内部 `ResultBeanFactory`
的 Maven 坐标、完整包名或方法签名证据。因此不在设计中伪造
内部 groupId/artifactId/version 或异常 Factory 方法；落地前必须以
公司内部制品的实际 API 作为新的源码基线。

### 6.2 双制品互斥模式

为了同时满足公司外可构建和公司内直接拉取，使用两个 Maven
profile 为同一个编译契约提供互斥实现：

| profile | ResultBean 来源 | 使用场景 |
|---|---|---|
| `standalone` | `campusclaw-result-bean-compat` 清室兼容制品 | 默认激活；GitHub、本地和无内网 CI |
| `company` | 公司内部真实 ResultBean 制品 | 由公司 Maven `settings.xml` 的 `activeProfiles` 自动激活 |

`campusclaw-result-bean-compat` 只重新实现已批准公开的最小 API
形状和 JSON 契约，不复制、反编译或发布公司内部源码。在获得
合规批准和真实包名后，兼容制品提供与内部制品完全相同的
FQCN、公共泛型签名和 Jackson 字段，因此 Controller 源码在两种
profile 下保持同一行 `ResultBeanFactory.getFactory().normal(result)`。

两个制品绝不能同时进入 compile/runtime classpath，否则会出现重复
FQCN 和不可预期的 class loading。Maven Enforcer 必须在 `validate`
阶段验证恰好一个 provider；公司内部仓库 URL、server ID 和凭据
只位于公司管理的 `settings.xml`，不写入 Git 中的 POM。公司环境通过
`activeProfiles` 激活 `company` 后，Maven 直接从内部仓库解析真实制品；
业务代码不改 import、不改 Factory 调用。

![ResultBeanFactory 公司内外双制品替换](http_result_bean_compatibility.svg)

[PlantUML 源码：`http_result_bean_compatibility`](diagram.puml#L1080)

### 6.3 错误与国际化实现

Java 使用 `RuntimeApiErrorCode` 枚举保存稳定错误码与 HTTP status，
`RuntimeApiException` 只保存 error code 和消息参数。
`RuntimeApiExceptionHandler` 使用 Spring `MessageSource` 和已固定的
Locale 规则解析 `resMsg`，再调用公司制品实际支持的异常包装
API。由于目前只已知成功调用形状 `normal(...)`，设计不猜测
内部 Factory 的异常方法名；获得内部 jar 后再固定该适配。

资源文件至少包含 `messages_en_US.properties` 和
`messages_zh_CN.properties`。两份资源必须具有完全相同的 key 集合。
启动测试和 CI 对枚举、`en_US`、`zh_CN` 执行集合等值校验；
契约测试分别在 `standalone` 和 `company` profile 下断言：

1. `normal(result)` 的 JSON 精确为 `resCode/resMsg/result`；
2. null、空集合、时间和嵌套 VO 的 Jackson 行为一致；
3. 中英文 Locale、回退语言和 `Content-Language` 一致；
4. 九个错误码的 HTTP status、`resCode`、`resMsg` 一致，
   且响应均不包含 `result` 字段；
5. 公司 profile 的依赖树不包含兼容制品，standalone profile
   的依赖树不包含内部制品。

如果公司合规规则不允许兼容制品使用内部 FQCN，必须改用
CampusClaw 自有 Facade + 内部 Adapter；这时可保持相同 JSON 和开发
体验，但不能同时承诺业务源码 import 与内部类完全相同。

## 7. 安全与附件边界

- `CredentialHeaderResolver` 只解析 `X-HW-ID`、`Authorization` 和
  `X-HW-APPKEY`，并先拒绝缺失、不完整或混合凭据；Controller 不写
  JWT/APPKEY 两套分支。
- `JwtCredentialVerifier` 和 `AppKeyCredentialVerifier` 是公司认证库的
  窄 Adapter，成功后都返回同一个不可变 `CallerAuthContext`；后续
  Agent/Session 授权不知道凭据模式。
- JWT 是文档和新客户端首选，不是服务端默认降级链。一旦选中模式，
  校验失败必须终止。
- 凭据只存在于认证边界，不记日志、不写 ResultBean、不进入
  Service/Session/Prompt/History；`session_id` 不是凭据。
- Runtime 对每个请求重新校验 Session、Agent、Model 和动作权限。
- HTTP 契约不接收 `traceparent`。部署平台如需调用链遥测，由网关和
  框架在契约外处理，不把它传入业务对象。
- `agent_id`、`model_id` 和 `attachment_id` 均大小写敏感且不透明。
- `POST /runs` 当前推荐只接受文本和附件 ID，不接受单次 `thinking` 覆盖，
  并禁止 URL、MIME、文件名、Base64、OBS Object Key、tenant/user 字段。
- `Idempotency-Key` 只作为作用域内去重键，调用方不得放入凭据或个人信息；
  服务端日志只记录有界摘要，不记录原值。
- Runtime 仍通过 Attachment Service 的内部 resolve/content API 获取可信元数据
  和有界字节流，不直连 OBS。

![HTTP 双认证适配](http_dual_authentication.svg)

[PlantUML 源码：`http_dual_authentication`](diagram.puml#L1148)

## 8. 源码证据与差异分类

规范来源为仓库相对路径
`pi-mono-java-manager-driven-multi-agent-runtime/chat-ws-v2.asyncapi.yaml`。本轮 HTTP
认证设计额外核对 pi-mono-java 基线
`dff835743fc7f3c93e1154c3eb51028749867ca8`。本轮资源模型比较还核对了
Anthropic Managed Agents 官方文档在 2026-08-17 公开的
`managed-agents-2026-04-01` beta 契约。

| 分类 | 证据或决策 |
|---|---|
| 观察到的行为 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ServerMode.java` 基线 285-307：当前使用 WebSocket Upgrade，其余请求交给 RouterFunctions Adapter |
| 观察到的行为 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ChatWebSocketHandler.java` 基线 115-227、422-459：v1 命令、断线生命周期和累计消息更新 |
| 观察到的行为 | `modules/ai/src/main/java/com/campusclaw/ai/stream/AssistantMessageEvent.java` 基线 44-164：结构化 provider 流事件 |
| 观察到的行为 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ServerMode.java` 基线 237-307、340-344：当前 HTTP 路由未安装入站认证 Adapter，CORS 仅放行 Authorization Header |
| 观察到的行为 | `modules/agent-core/src/main/java/com/campusclaw/agent/subagent/a2a/A2aAgentBackend.java` 基线 40-62、226-238：出站 A2A 请求已使用 `X-HW-ID + X-HW-APPKEY`，但它不是入站验证实现 |
| 观察到的行为 | pi-mono `packages/protocol/src/schemas.ts` 基线 38-45、241-258：协议 `SessionSnapshot` 顶层包含 `phase`、`thinkingLevel`、完整 `transcript`、连接相对 `attached` 和 live Runtime `locked` |
| 观察到的行为 | pi-mono `packages/protocol/src/schemas.ts` 基线 26-35：`ThinkingLevel` 取 `off/minimal/low/medium/high/xhigh/max`，表达推理强度 |
| 观察到的行为 | Anthropic TypeScript SDK `src/resources/beta/sessions/sessions.ts` 基线 638-710：Managed Agents 的 Session 是控制面资源，包含 Agent 快照、环境/资源、预算/用量、标题/元数据和状态，但不内嵌 transcript 或 active Run 恢复快照 |
| 观察到的行为 | Anthropic [Session event stream](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)：Managed Agents 的交互是事件驱动；`user.message` 启动或继续工作，事件在更早事件之后排队时 `processed_at=null`，中止通过 `user.interrupt` 表达 |
| 观察到的行为 | Anthropic [Send Events API](https://platform.claude.com/docs/en/api/cli/beta/sessions/events/send)：`POST /v1/sessions/{session_id}/events` 返回服务端已接收的事件及其 `event_id`，普通 Session 交互没有独立的 Session Run ID |
| 观察到的行为 | Anthropic [Start a session](https://platform.claude.com/docs/en/managed-agents/sessions) 与 [Session operations](https://platform.claude.com/docs/en/managed-agents/session-operations)：Session 维护跨多次交互的历史，事件驱动 `idle/running/rescheduling/terminated` 状态；`initial_events` 可让新 Session 直接进入 running |
| 观察到的行为 | Anthropic [Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)：Deployment Run 是 Deployment 触发的追加记录，只跟踪 Session 创建成功或失败；成功后通过 `session_id` 转到 Session Event Stream，不跟踪 Session 执行生命周期 |
| 观察到的行为 | pi-mono `packages/coding-agent/src/core/agent-session.ts` 基线 789-805：`AgentSession.dispose()` 中止重试、压缩、分支、bash 和 Agent 运行，断开扩展并释放内存资源；它未定义 HTTP 逻辑删除或持久化 tombstone |
| 观察到的行为 | pi-mono `packages/coding-agent/src/modes/interactive/components/session-selector.ts` 基线 598-630：交互模式删除直接将 Session JSONL 移入回收站，失败时回退为 unlink；这是本地文件行为，不是服务端删除事务 |
| 观察到的行为 | pi-mono-java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/SessionPool.java` 基线 143-157、204-274：`remove()` 只从内存 Map 移除并关闭 `SessionManager`；JSONL 可在后续创建时恢复，闲置淘汰也只释放内存对象 |
| 观察到的行为 | pi-mono-java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ChatWebSocketHandler.java` 基线 168-210 与 `modules/agent-core/src/main/java/com/campusclaw/agent/AgentSession.java` 基线 165-177：断连或 abort 能停止流和子 Agent，但当前没有 DeleteSession HTTP 操作 |
| 观察到的行为 | pi-mono `packages/coding-agent/src/core/agent-session.ts` 基线 609-680、1063-1074、1116-1273：`prompt` 构造文本和可选 inline image 的 UserMessage，等待 Agent 执行，并在 `message_end` 将消息追加到 SessionManager；没有独立 HTTP Run 资源、`run_id` 或持久化幂等结果 |
| 观察到的行为 | pi-mono `packages/coding-agent/src/core/agent-session.ts` 的 `PromptOptions` 基线 2629-2649：单次 prompt 可带 images；`expandPromptTemplates`、`streamingBehavior`、`source` 和 preflight callback 是 CLI/RPC Runtime 控制，不是通用业务消息字段；`model_id/thinking` 不在该参数中 |
| 观察到的行为 | pi-mono `packages/agent/src/agent.ts` 基线 347-358、486-535：`activeRun` 是进程内执行对象，同一 Agent 已有 activeRun 时拒绝新 prompt，finally 清理；它不是持久化、可查询的 RunRecord |
| 观察到的行为 | pi-mono-java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ChatHandler.java` 基线 53-136：现有 HTTP POST 把 prompt 生命周期绑定到 SSE 响应，并在取消时 abort；没有先持久化异步 Run 再返回的接受边界 |
| 观察到的行为 | pi-mono-java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ChatWebSocketHandler.java` 基线 252-273 与 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSession.java` 基线 153-177：WebSocket prompt 只接受非空文本，先追加 JSONL UserMessage 再调用 prompt，并以 `isStreaming` 拒绝并发；没有附件 ID、Run ID 或幂等存储 |
| 观察到的行为 | pi-mono-java `modules/agent-core/src/main/java/com/campusclaw/agent/Agent.java` 基线 183-194、218-268：`startExecution` 通过 executionLock 保证单次 current execution，并在虚拟线程执行结束时清理；没有共享数据库 active-run 唯一约束或执行任务 |
| 产品约束 | Session/Message、附件引用和 Manager 权威保持不变；执行轮次是否公开为 Run 尚未确认 |
| 产品约束 | 普通 JSON 成功响应使用 `resCode/resMsg/result`，异常响应只使用 `resCode/resMsg`；错误码和国际化 key 一致，真实 HTTP status 仍保留 |
| 产品约束 | 用户提供的公司集成基线定义 JWT 与 APPKEY 两组入站 Header；JWT 作为默认文档路径 |
| 产品约束 | DeleteSession 永久 tombstone 严格只包含 `session_id`、`deleted_at`；清理状态、重试信息、owner 和业务快照不进入 tombstone |
| 安全加固 | 双凭据二选一、拒绝混合凭据、校验失败不降级、逐请求认证、Session-scoped 模型查询、附件只传 ID、ResultBean 错误脱敏 |
| 架构改造 | 一组 HTTP 资源接口、统一 `CallerAuthContext` 的双认证 Adapter、CampusClaw 生成 Session ID、编译生成的 Managed `settings.json`、目录默认模型初始化、ResultBeanFactory 双制品互斥替换、ETag 并发控制、SSE/JSON Event Journal、持久化 tombstone 和可重试清理任务驱动的异步 Session 物理删除 |
| 已确认架构 | 将当前进程内 `prompt` 调用提升为调用方可见的持久化异步 Run：用户 Message、RunRecord、Session active 指针、幂等结果和 `t_run_dispatch_task` 在本地事务中提交；事件作为 Run 内事实流，不替代 `run_id` |
| 设计原因 | mate-service 需要按轮精确恢复、中止、Steer 和审计，显式 `run_id` 提供稳定边界；Anthropic 的持久化事件、权威完整事件和临时增量分层作为 Run Event Journal 的实现参考 |
| 已确认设计 | CampusClaw GetSession 收敛为配置、粗粒度状态和 active Run 指针；History 水位归 History API，执行 phase 与恢复详情归 GetRun，实时增量归 Run Event API。相较 Anthropic，Agent 发布快照、环境、Vault、预算、用量、标题和业务元数据不由本 Session 资源拥有 |
| 待确认输入 | CreateRun 当前推荐只接收 `message + attachment_ids`，并原子固化 Session 当前 `model_id/thinking`；是否改为 `content[]`、是否允许单 Run 配置覆盖、是否接受非模型业务 metadata 仍在评审中 |

公司内部 ResultBean 制品信息以及 JWT/APPKEY 入站凭据组合来自
用户提供的集成约束。当前工作区不含对应入站认证库或
ResultBean 制品元数据。ResultBean 坐标/FQCN/方法，以及 JWT 和
APPKEY 的 claim、签名、issuer、audience 与校验算法均必须在落地前
依据真实内部制品补齐。除这些待校准适配点外，
本文全部 HTTP 行为仍为 target-only design，不得表述为现有
pi-mono-java 实现。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.14.0 | 2026-08-17 | 用户选择候选 A，确认每轮执行是调用方可见的显式 Run 资源；恢复 GetSession `active_run`、GetRun、Run Events、Abort 和 Steer 的既定边界；第四接口进入输入评审，依据 pi `PromptOptions` 区分文本/附件业务输入与模板展开、运行中队列、来源和 callback 等内部控制，提出扁平字段或 `content[]`、Session 配置快照或单 Run 覆盖、是否接受 metadata 三项决策；OpenAPI 未更新 |
| 1.13.0 | 2026-08-17 | 将第四个接口退回架构前置评审：先确认“每轮执行是否成为调用方可见的一等 Run 资源”，再评审字段；增加显式 Run 与 Anthropic 风格 Session Events 的身份、状态、事件、中止、并发、恢复和审计对比，明确选择 Events 会重开已确认 GetSession `active_run`；原 CreateRun 字段契约降级为候选 A 条件式预览；核对 Anthropic `managed-agents-2026-04-01` 官方契约并新增资源模型 PlantUML，OpenAPI 未更新 |
| 1.12.0 | 2026-08-17 | 用户确认第三个 DeleteSession 接口，冻结 `204` 逻辑删除、active Run 自动 abort、重复删除统一 `204`、Runtime 数据清理和仅含 `session_id/deleted_at` 的永久 tombstone；启动第四个 CreateRun 评审，提出持久化异步接受边界、必填幂等键、文本/附件输入、单 active Run、最窄 `202` ResultBean 与错误国际化；增加 pi/pi-mono-java prompt/并发/HTTP SSE 源码证据和 PlantUML，OpenAPI 未更新 |
| 1.11.1 | 2026-08-17 | 对齐第三个接口的永久 tombstone 字段：严格只保留 `session_id`、`deleted_at`；清理状态、重试信息和 owner 不进入 tombstone，由短期清理任务承载；第三个接口整体仍在评审中，OpenAPI 未更新 |
| 1.11.0 | 2026-08-17 | 启动第三个 `DELETE /sessions/{session_id}` operation 评审；提案在持久化逻辑删除和清理任务后返回 `204`、active Run 自动 abort、重复删除统一 `204`、清理 Runtime 数据并仅保留最小 tombstone；增加 pi/pi-mono-java 删除与释放行为证据，前两个已确认接口不变，OpenAPI 未更新 |
| 1.10.1 | 2026-08-17 | 用户确认第二个 `GET /sessions/{session_id}` operation；冻结 `active_run={run_id,state}`、ETag 仅用于配置写并发控制、不存在与已删除统一返回 `404 SESSION_NOT_FOUND`，并将双接口 HTML 更新为均已确认；OpenAPI 未更新 |
| 1.10.0 | 2026-08-16 | 收窄 GetSession：删除 `history_seq` 和 active Run 的 phase/model/thinking，只保留 Session 当前配置、`idle/running` 与 `run_id/state` 指针；明确 History、GetRun、Run Event 的职责边界；主维护 HTML 同时展示已确认的第一个接口与评审中的第二个接口，OpenAPI 未更新 |
| 1.9.0 | 2026-08-16 | 将主维护 HTML 切换为第二个 GetSession 接口评审；增加 `history_seq` 水位、Session state 与 active Run phase 分工、thinking 可见性与 pi 推理强度的语义隔离，以及 transcript/name/attached/locked 的边界；第二个接口仍未确认，OpenAPI 未更新 |
| 1.8.0 | 2026-08-15 | 增加仓库内可直接打开的 HTML 接口评审文档并固定为人类评审主维护契约；OpenAPI YAML 暂作过渡期机器投影，不在本轮废弃 |
| 1.7.1 | 2026-08-15 | 用户明确确认第一个 `POST /agents/{agent_id}/sessions` operation；固定该 operation 的已确认评审状态，其余 12 个 operation 仍待逐个对齐 |
| 1.7.0 | 2026-08-15 | 第一个 Session 创建接口的异常包装收敛为仅 `resCode/resMsg`，明确禁止序列化 `result`；同步 OpenAPI Schema、中英文错误示例和契约测试 |
| 1.6.0 | 2026-08-15 | HTTP 契约删除 traceparent；增加首选 `X-HW-ID + Authorization` JWT 与兼容 `X-HW-ID + X-HW-APPKEY` 两组明示安全要求；固定混合凭据拒绝、验证失败不降级、统一 CallerAuthContext 适配层及 `AUTH_CREDENTIAL_CONFLICT` 中英文错误 |
| 1.5.0 | 2026-08-15 | 第一个创建 Session 接口改为 `resCode/resMsg/result` ResultBean，保留真实 HTTP status；固定八个错误码及中英文消息、Accept-Language/Content-Language 规则；增加 standalone 兼容制品与 company 内部制品的 Maven profile 互斥替换设计 |
| 1.4.0 | 2026-08-15 | 将创建 Session 改为无请求体的 `POST /agents/{agent_id}/sessions`，由 CampusClaw 生成 `session_id` 并从 Managed settings 解析默认模型；固定目录验证、模型校验、SessionContext/AgentSession 组装、持久化和失败清理顺序；创建和查询共用不含内部版本的 SessionResource，创建不使用 `Idempotency-Key` 或 `If-Match` |
| 1.3.0 | 2026-08-15 | Session 创建请求收敛为只必填 `agent_id`；从 `.campusagent/settings.json` 读取 `agentVersion/defaultModel/enabledModels`，经 Model Manager 校验后初始化并返回有效模型；明确 Run 原子固化 Session 当前模型 |
| 1.2.0 | 2026-08-14 | 将 Runtime HTTP API 的统一基础路径调整为 `/campusclaw-service/v1`；明确 Session 同一性由 `session_id` 与不可变 `agent_id` 绑定确定，可切换的 `model_id` 不参与绑定冲突判断 |
| 1.1.0 | 2026-08-06 | 将 HTTP 版重构为 Session、Run、事件/历史、模型配置四组共 13 个 operation；删除 connect/resume 与连接级状态，增加 SSE/JSON Event Journal、ETag 和 Session 删除语义 |
| 1.0.0 | 2026-08-05 | 初版 HTTP 映射草稿 |
