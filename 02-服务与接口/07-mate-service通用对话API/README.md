# mate-service 通用对话 Events API

[返回服务与接口导航](../README.md)

| 属性 | 值 |
|---|---|
| 文档版本 | 1.0.0 |
| 状态 | 三个 operation 已确认；待实现 |
| 设计性质 | target-only；不得描述为当前 mate-service 或 CampusClaw 已实现行为 |
| 设计仓变更前基线 | `743eca488ad559387706b5df54e2248a4124e5ef` |
| CampusClaw 源码核对基线 | `7e54b47f2539982f8f1855a0b6bb38b6ab8742ae` |
| pi 固定参考基线 | `badlogic/pi-mono@5cd93f688aaab89dbb6dfa4aca535f21796ae185` |
| Claude Managed Agents 公开文档核对日期 | 2026-09-02；Beta 公共契约，无可归因服务端源码 |
| 更新日期 | 2026-09-02 |

## 1. 已确认接口

Mate 对外只使用 `Chat/chatId/chat.*`；Claw 内部继续使用
`Session/sessionId/session.*`。三个接口共享同一组公共事件定义，但提交、实时观察和权威历史
彼此分离：

| # | 方法与路径 | 用途 | 返回 |
|---:|---|---|---|
| 1 | `POST /mate-service/v1/chats/{chatId}/events` | 提交一条用户事件 | 普通 JSON 回执 |
| 2 | `GET /mate-service/v1/chats/{chatId}/events/stream` | 从连接时刻开始观察 Chat 的实时事件 | 长连接 SSE，仅 live preview 与实时通知 |
| 3 | `GET /mate-service/v1/chats/{chatId}/events` | 查询可恢复、可审计的权威事件历史 | 固定快照分页 JSON |

精确 operation 模型和生成后的主评审面：

- [三接口契约评审页](chat-events-v1-review.html)
- [01 · 提交事件](接口契约/操作/01-submit-chat-event.json)
- [02 · 订阅实时事件](接口契约/操作/02-stream-chat-events.json)
- [03 · 查询事件历史](接口契约/操作/03-list-chat-events.json)

本专题不生成 OpenAPI。三份 JSON 是可编辑的精确契约源，HTML 由它们生成；本 Markdown
说明边界、字段语义、源码证据和设计理由。

## 2. 资源与责任边界

![公共 Chat Events 边界](设计图/public_chat_event_boundary.svg)

[PlantUML 源码：`public_chat_event_boundary`](设计图/diagram.puml#L1)

| 组件 | 责任 | 不负责 |
|---|---|---|
| 浏览器 / Agent UI | 提交公共用户事件；展示实时 preview；用历史对账 | 持有 `sessionId`、解释 Claw 私有事件、自动重放结果不确定的 POST |
| mate-service | 公司认证、Chat 授权、`chatId -> sessionId` 私有解析、三接口公共投影、国际化错误 | 模型与 Tool 执行、向浏览器暴露 Claw 内部 ID 或原始思考 |
| CampusClaw | Session 执行、取消传播、Tool 生命周期、权威 Entry 持久化和内部事件 | 读取公共 `chatId`、定义浏览器契约、保存最终用户认证信息 |

这次设计不规定 Mate 到 Claw 的最终 HTTP 路径；Claw 的 HTTP Events 接口将在后续专题中
单独设计。Mate 侧只能依赖稳定的内部领域语义，不能把当前 Runtime SSE 字节透明转发出去。

## 3. 公共约定

### 3.1 认证、Header 与 Path

三个接口使用相同认证规则：

| 位置 | 字段 | 必需 | 允许值与语义 |
|---|---|---:|---|
| path | `chatId` | 是 | 区分大小写的字符串，长度 `1..64`；不施加额外正则，不接受内部 `sessionId` |
| header | `X-HW-ID` | 是 | 公司调用方身份；非空字符串 |
| header | `access-token` | 是 | 当前调用上下文的访问令牌；非空字符串 |
| header | `Authorization` | 条件必需 | `Bearer <JWT>`；与 `X-HW-APPKEY` 至少提供一个 |
| header | `X-HW-APPKEY` | 条件必需 | 公司 AppKey；与 `Authorization` 至少提供一个 |
| header | `Accept-Language` | 否 | `zh-CN` 或 `en-US`；缺失或不支持时使用 `en-US` |

如果 `Authorization` 和 `X-HW-APPKEY` 同时存在，必须使用 JWT；JWT 无效时直接返回认证
失败，不能回退到 AppKey。mate-service 先认证、授权 Chat，再解析私有 `sessionId`。

### 3.2 JSON 与时间

- JSON 字段使用 lower camel case；已知请求对象忽略未知属性；不支持的 `type` 仍是错误；
- `null` 不等价于省略。文档标为“省略”的字段出现 `null` 时按非法输入处理；
- `eventId` 由服务端生成，固定为 32 个小写十六进制字符，正则
  `^[0-9a-f]{32}$`；同一 Chat 内稳定且不复用；
- `createdAt` 是服务端接受或持久化事件的时间，格式为包含三位毫秒的 RFC 3339 UTC，
  例如 `2026-09-02T08:30:15.123Z`；
- 所有 JSON 成功和失败响应发送 `Cache-Control: no-store`；失败响应的
  `Content-Language` 是实际采用的语言；
- 普通成功响应使用 `ResultBean`：`resCode="0"`、`resMsg="success"`、`result`；
- 失败响应只包含 `resCode` 和 `resMsg`，不得返回 `result: null` 或内部错误细节；
- 客户端按稳定的 `resCode` 分支，不能按已国际化的 `resMsg` 分支。

### 3.3 公共事件身份

公共契约没有 `eventSeq`。每个持久化事件都有独立 `eventId`；`agent.message` 和
`agent.thinking` 的多帧实时增量与最终完整事件复用同一个 `eventId`。POST 回执中的
`eventId` 只标识被接受的那条 `user.*` 事件，不是 execution、Turn、Tool Call 或后续
Agent 输出的关联 ID。

执行边界由事件时间顺序和 `chat.status_idle` 识别，不增加 `turnId`、`runId` 或
`messageEventId`。Tool 的唯一例外是 `agent.tool_result.toolCallId`，它引用对应
`agent.tool_call.eventId`。

## 4. 接口一：提交用户事件

```http
POST /mate-service/v1/chats/{chatId}/events
Content-Type: application/json
Accept: application/json
```

一次请求只提交一个事件，请求体固定只有顶层 `event`：

| 字段 | 类型 | 必需 | 允许值与语义 |
|---|---|---:|---|
| `event` | object | 是 | `user.message`、`user.interrupt` 或 `user.tool_confirmation` 三种联合类型之一 |
| `event.type` | string | 是 | 联合类型 discriminator；其他值返回 `CHAT_EVENT_TYPE_INVALID` |

### 4.1 `user.message`

```json
{
  "event": {
    "type": "user.message",
    "content": [
      {"type": "text", "text": "分析上传文件并给出处理建议"},
      {"type": "file", "fileId": "7f12d8a380964fdc8518f48be1cf6a42"}
    ]
  }
}
```

| 字段 | 类型 | 必需 | 允许值与语义 |
|---|---|---:|---|
| `type` | string | 是 | 固定 `user.message` |
| `content` | array | 是 | 长度 `1..5`；只允许 text/file；顺序保留 |
| `content[].type` | string | 是 | `text` 或 `file` |
| `content[].text` | string | text 项必需 | 非空白，最多 2048 个 Unicode code point；最多一项且必须是第一项 |
| `content[].fileId` | string | file 项必需 | `^[0-9a-f]{32}$`；最多四项；数组内不得重复 |

允许 text-only、file-only 或 text + files。文件项只保存 `fileId` 引用；二进制、文件名和
其他元数据由独立文件接口解析，不在 Chat 事件中重复。

Chat 必须处于允许新消息的 idle 状态。active execution 或
`chat.status_idle(reason="confirming")` 时返回 `CHAT_BUSY`，不会把消息隐式变成 Steer、
FollowUp 或队列项。同一 Chat 最多一个 active message execution。

### 4.2 `user.interrupt`

```json
{
  "event": {
    "type": "user.interrupt"
  }
}
```

| 字段 | 类型 | 必需 | 允许值与语义 |
|---|---|---:|---|
| `type` | string | 是 | 固定 `user.interrupt`；无其他业务字段 |

它请求终止当前整棵执行树，包括主 Agent、执行中的 Tool 和 Child Agent。HTTP 200 只表示
中断事件已被接受；客户端必须等待实时流或历史出现
`chat.status_idle(reason="terminated")` 才能提交下一条 `user.message`。idle Chat 收到
interrupt 返回 `CHAT_NOT_RUNNING`。

本契约不支持把 `interrupt` 和 `message` 放进同一请求，也不支持批量 events。客户端流程
必须是“提交 interrupt → 等待 terminated idle → 提交 message”。

### 4.3 `user.tool_confirmation`

```json
{
  "event": {
    "type": "user.tool_confirmation",
    "toolCallId": "c8de683be2ab4e25a8d97f7cf507c150",
    "result": "deny",
    "denyMessage": "不要执行会修改生产配置的操作"
  }
}
```

| 字段 | 类型 | 必需 | 允许值与语义 |
|---|---|---:|---|
| `type` | string | 是 | 固定 `user.tool_confirmation` |
| `toolCallId` | string | 是 | `^[0-9a-f]{32}$`；必须引用等待确认的 `agent.tool_call.eventId` |
| `result` | string | 是 | `allow` 或 `deny` |
| `denyMessage` | string | 否 | 仅 `deny` 可提供；可省略，提供时非空白且最多 2048 个 Unicode code point；`allow` 时必须省略 |

确认事件只在 Chat 的当前状态为 `confirming` 且 Tool Call 正在等待确认时接受。它会作为
完整历史事件保留，以便审计和 UI 恢复；实时流不重复发送 `user.tool_confirmation`。

### 4.4 成功回执

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "eventId": "b7ef45d40a854c33af7a36df871a21e8",
    "createdAt": "2026-09-02T08:30:15.123Z"
  }
}
```

| 字段 | 类型 | 必需 | 语义 |
|---|---|---:|---|
| `resCode` | string | 是 | 固定 `0` |
| `resMsg` | string | 是 | 固定 `success` |
| `result.eventId` | string | 是 | 被接受的 `user.*` 事件 ID；与历史中的该事件完全相同 |
| `result.createdAt` | string | 是 | 服务端接受时间；与历史事件的 `createdAt` 完全相同 |

回执不回显请求，不返回 `acceptedAt`、`processedAt` 或执行结果。若客户端在收到回执前
断线，结果不确定；本版本没有 Idempotency-Key，客户端必须查询历史，不能盲目重放 POST。

### 4.5 提交接口错误

| HTTP | `resCode` | 场景 |
|---:|---|---|
| 400 | `CHAT_ID_INVALID` | `chatId` 长度非法 |
| 400 | `CHAT_EVENT_INVALID` | JSON、联合类型字段、content 或确认字段非法 |
| 400 | `CHAT_EVENT_TYPE_INVALID` | `event.type` 不属于三个允许值 |
| 401 | `UNAUTHENTICATED` | 认证字段缺失或凭据无效 |
| 403 | `CHAT_ACCESS_DENIED` | 无权访问 Chat |
| 404 | `CHAT_NOT_FOUND` | Chat 不存在 |
| 409 | `CHAT_BUSY` | active execution 或正在等待确认时提交消息 |
| 409 | `CHAT_NOT_RUNNING` | idle Chat 收到 interrupt |
| 409 | `TOOL_CONFIRMATION_NOT_PENDING` | Tool Call 不存在、不属于当前 Chat 或未等待确认 |
| 429 | `TOO_MANY_REQUESTS` | 租户、调用方或 Chat 限流 |
| 500 | `INTERNAL_ERROR` | 未预期的服务端错误 |
| 503 | `CHAT_RUNTIME_UNAVAILABLE` | Claw 暂不可用，事件未被接受 |

## 5. 接口二：订阅实时事件

```http
GET /mate-service/v1/chats/{chatId}/events/stream
Accept: text/event-stream
```

连接成功后，服务端发送 `Content-Type: text/event-stream` 和
`Cache-Control: no-store`。它是 Chat 级长连接：跨越多次 execution 和 idle 状态；出现
`chat.status_idle` 不关闭连接。服务端可以用 SSE comment `: ping` 保活。

### 5.1 Frame 规则

每个业务 frame 只有一行 `data:`，值是完整 JSON：

```text
data: {"eventId":"4b3e522e7f6746be8781a2c8876fd1da","type":"agent.message","phase":"delta","content":"建议先隔离受影响端口，"}

: ping

data: {"eventId":"4b3e522e7f6746be8781a2c8876fd1da","type":"agent.message","phase":"completed","createdAt":"2026-09-02T08:30:18.451Z","content":"建议先隔离受影响端口，再核对上联链路。"}
```

不得发送 SSE `event:` 或 SSE `id:`。此接口从连接建立时刻开始发送 live 事件，不接受
`Last-Event-ID`、不重放，也没有公共 sequence。断线恢复使用“重开流 + 查询历史 + 按
`eventId` 去重”。

### 5.2 事件类型总表

| `type` | 是否有 delta | 是否进入历史 | 作用 |
|---|---:|---:|---|
| `agent.message` | 是 | 仅 `completed` | Assistant 对用户可见的文本 |
| `agent.thinking` | 是 | 仅 `completed` | Claw 审核后的公开思考摘要，不是 private chain-of-thought |
| `agent.tool_call` | 否 | 是 | 一次已公开的 Tool 调用及安全参数 |
| `agent.tool_result` | 否 | 是 | Tool 的公开结果或稳定公开错误 |
| `chat.status_idle` | 否 | 是 | 当前 execution 已停止或暂停等待确认 |

`user.*` 事件不通过 SSE 重复推送，只能从 POST 回执和 GET 历史观察。没有
`chat.running`、`chat.terminated`、`stream.end`、`stream.error`、Turn 或 Session 公共事件。

### 5.3 `agent.message` 与 `agent.thinking`

delta：

```json
{
  "eventId": "4b3e522e7f6746be8781a2c8876fd1da",
  "type": "agent.thinking",
  "phase": "delta",
  "content": "正在核对告警时间线"
}
```

completed：

```json
{
  "eventId": "4b3e522e7f6746be8781a2c8876fd1da",
  "type": "agent.thinking",
  "phase": "completed",
  "createdAt": "2026-09-02T08:30:17.305Z",
  "content": "已核对告警时间、设备范围和关联影响。"
}
```

| 字段 | delta | completed | 允许值与语义 |
|---|---:|---:|---|
| `eventId` | 必需 | 必需 | 同一逻辑事件复用同一 32 位小写十六进制 ID |
| `type` | 必需 | 必需 | 固定 `agent.message` 或 `agent.thinking` |
| `phase` | 必需 | 必需 | `delta` 或 `completed` |
| `content` | 必需 | 必需 | delta 是本帧新追加的非空片段，允许只含空格或换行；completed 是完整权威文本 |
| `createdAt` | 必须省略 | 必需 | delta 不是持久化事件；completed 是持久化时间 |

客户端按顺序追加 delta；收到 completed 后，以 completed 的完整 `content` 替换 preview。
若 execution 被中断且没有 completed，则丢弃未完成 preview。`agent.thinking.content` 只允许
公开摘要；原始推理内容不得到达 Mate 公共边界。

### 5.4 `agent.tool_call`

```json
{
  "eventId": "c8de683be2ab4e25a8d97f7cf507c150",
  "type": "agent.tool_call",
  "createdAt": "2026-09-02T08:30:16.420Z",
  "toolName": "query_campus_alarm",
  "arguments": {"siteName": "东区园区"},
  "requiresConfirmation": true
}
```

| 字段 | 类型 | 必需 | 允许值与语义 |
|---|---|---:|---|
| `eventId` | string | 是 | 同时充当公共 `toolCallId`；结果和确认都引用它 |
| `type` | string | 是 | 固定 `agent.tool_call` |
| `createdAt` | string | 是 | Tool Call 被持久化的时间 |
| `toolName` | string | 是 | 非空白，最多 128 个字符的稳定公开 Tool 名称 |
| `arguments` | object | 是 | 允许空对象；仅包含已做公开安全投影的 JSON 参数 |
| `requiresConfirmation` | boolean | 是 | `true` 表示执行前需要 `user.tool_confirmation` |

当 `requiresConfirmation=true`，随后发送
`chat.status_idle(reason="confirming")`。事件本身不重复 `toolCallId` 字段，因为
`eventId` 已是唯一 Tool Call ID。

### 5.5 `agent.tool_result`

```json
{
  "eventId": "89f8316e07ef4c9aa3fd056a91a182b0",
  "type": "agent.tool_result",
  "createdAt": "2026-09-02T08:30:19.102Z",
  "toolCallId": "c8de683be2ab4e25a8d97f7cf507c150",
  "content": "找到 3 条相关告警。",
  "isError": false
}
```

| 字段 | 类型 | 必需 | 允许值与语义 |
|---|---|---:|---|
| `eventId` | string | 是 | Tool Result 自己的事件 ID，不等于 `toolCallId` |
| `type` | string | 是 | 固定 `agent.tool_result` |
| `createdAt` | string | 是 | 结果被持久化的时间 |
| `toolCallId` | string | 是 | 引用对应 `agent.tool_call.eventId` |
| `content` | string | 是 | 公开结果文本；允许空字符串 |
| `isError` | boolean | 是 | 是否为 Tool 失败结果 |
| `errorCode` | string | 否 | 仅 `isError=true` 时可提供；提供时是非空白且最多 128 字符的稳定公开错误码；`isError=false` 时必须省略 |

Tool 被 interrupt 取消时不伪造 `agent.tool_result`；客户端由后续
`chat.status_idle(reason="terminated")` 收敛 UI。`toolName` 不在结果中重复。

### 5.6 `chat.status_idle`

```json
{
  "eventId": "d4e3e8b9653047a99ac10396a17fe84d",
  "type": "chat.status_idle",
  "createdAt": "2026-09-02T08:30:20.000Z",
  "reason": "done"
}
```

| 字段 | 类型 | 必需 | 允许值与语义 |
|---|---|---:|---|
| `eventId` | string | 是 | 本次 idle 状态事件 ID |
| `type` | string | 是 | 固定 `chat.status_idle` |
| `createdAt` | string | 是 | 状态被确认的时间 |
| `reason` | string | 是 | `done`、`terminated`、`failed` 或 `confirming` |

| `reason` | 含义 | 是否允许提交 `user.message` |
|---|---|---:|
| `done` | execution 自然完成 | 是 |
| `terminated` | 当前 execution 被用户 interrupt；Chat 本身仍可继续使用 | 是 |
| `failed` | 当前 execution 失败，但 Chat 已恢复 idle | 是 |
| `confirming` | execution 暂停，等待 Tool 确认 | 否，只允许对应 `user.tool_confirmation` 或 interrupt |

### 5.7 流错误边界

SSE Header 尚未发送时，认证、授权、Chat 不存在和容量错误使用普通 JSON 错误。SSE 建立
后不发送业务 `stream.error`；编码、网络或内部订阅异常直接结束传输。客户端重连并查询
权威历史，不能依据连接关闭推断 execution 成败。

## 6. 接口三：查询权威历史

```http
GET /mate-service/v1/chats/{chatId}/events?createdAtGte=2026-09-02T08%3A30%3A00.000Z&limit=100&types=agent.message&types=chat.status_idle
Accept: application/json
```

### 6.1 Query 参数

| 字段 | 类型 | 必需 | 默认值 | 允许值与语义 |
|---|---|---:|---|---|
| `createdAtGte` | string | 否 | 无下界 | 含三位毫秒的 RFC 3339 UTC；inclusive |
| `limit` | int32 | 否 | `100` | `1..200` |
| `types` | repeated string | 否 | 全部八类 | 使用 `types=x&types=y`；OR 语义；空值或未知值非法；重复值归一化一次 |
| `page` | string | 否 | 无 | 非空 opaque cursor；出现时不得同时传其他 query 参数 |

`types` 允许值固定为：

```text
user.message
user.interrupt
user.tool_confirmation
agent.message
agent.thinking
agent.tool_call
agent.tool_result
chat.status_idle
```

### 6.2 固定快照分页

第一页在服务端捕获查询上界和过滤条件。`nextPage` 内部携带
`createdAtGte/limit/types`、固定快照上界和私有续读位置；后续页不会混入第一页之后新产生
的事件。事件按 `createdAt` 升序返回；相同时间戳由服务端私有稳定顺序决定，所有分页保持
一致。游标不暴露或暗示 `eventSeq`。

需要继续获取新事件时，客户端发起新的第一页查询，以最后一次看到的 `createdAt` 作为
inclusive `createdAtGte`，并按 `eventId` 去重。

### 6.3 历史事件形状

历史只包含完整权威事件，不包含 delta、SSE ping 或 Claw 私有事件。

`user.message`：

```json
{
  "eventId": "b7ef45d40a854c33af7a36df871a21e8",
  "type": "user.message",
  "createdAt": "2026-09-02T08:30:15.123Z",
  "content": [
    {"type": "text", "text": "分析上传文件并给出处理建议"},
    {"type": "file", "fileId": "7f12d8a380964fdc8518f48be1cf6a42"}
  ]
}
```

`user.interrupt`：

```json
{
  "eventId": "aee903c130e048b9bc2894fc32cd63a8",
  "type": "user.interrupt",
  "createdAt": "2026-09-02T08:31:01.016Z"
}
```

`user.tool_confirmation`：

```json
{
  "eventId": "2781508bb1c9496f94a0454d0bf8c0f8",
  "type": "user.tool_confirmation",
  "createdAt": "2026-09-02T08:30:18.800Z",
  "toolCallId": "c8de683be2ab4e25a8d97f7cf507c150",
  "result": "allow"
}
```

`agent.message` 和 `agent.thinking` 只保存 completed 形态，并保留
`phase="completed"`；`agent.tool_call`、`agent.tool_result` 和
`chat.status_idle` 与实时流的完整形态完全相同。UI 可以按 `toolCallId` 把确认和结果合并
展示，但历史仍保留三个独立审计事件。

### 6.4 成功响应

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "events": [
      {
        "eventId": "b7ef45d40a854c33af7a36df871a21e8",
        "type": "user.message",
        "createdAt": "2026-09-02T08:30:15.123Z",
        "content": [{"type": "text", "text": "分析上传文件并给出处理建议"}]
      },
      {
        "eventId": "4b3e522e7f6746be8781a2c8876fd1da",
        "type": "agent.message",
        "phase": "completed",
        "createdAt": "2026-09-02T08:30:18.451Z",
        "content": "建议先隔离受影响端口，再核对上联链路。"
      }
    ],
    "nextPage": "eyJzbmFwc2hvdCI6IjIwMjYtMDktMDJUMDg6MzA6MjAuMDAwWiJ9"
  }
}
```

| 字段 | 类型 | 必需 | 语义 |
|---|---|---:|---|
| `resCode` | string | 是 | 固定 `0` |
| `resMsg` | string | 是 | 固定 `success` |
| `result.events` | array | 是 | 长度 `0..limit`；按稳定升序排列 |
| `result.nextPage` | string | 否 | 还有当前快照的下一页时返回非空 opaque cursor；否则必须省略，不返回 null 或空串 |

## 7. 断线恢复

![实时流与固定历史对账](设计图/public_chat_event_recovery.svg)

[PlantUML 源码：`public_chat_event_recovery`](设计图/diagram.puml#L35)

恢复算法：

1. 先打开 Chat SSE，再提交用户事件，避免漏掉最早的 live preview；
2. 本地用 `eventId + type` 维护 preview；completed 覆盖同 ID 的 delta 累积；
3. SSE 断开后标记结果不确定，不取消 execution、不重放 POST；
4. 立即重开 SSE，同时调用 GET 历史；
5. 历史记录为权威：用 `eventId` 去重，completed 替换 preview，历史不存在的未完成 delta 可丢弃；
6. 使用固定快照 `nextPage` 读完本轮历史，再用最后 `createdAt` inclusive 开新查询追增量。

这继承 Claude Managed Agents“临时 preview + 权威完整历史 + 重连对账”的公开语义，但
事件命名、Chat 资源、公司认证、固定 reason 和字段形状都是 CampusClaw 产品决策，并非
Claude 服务端实现事实。

## 8. 错误码与国际化

以下是本专题固定的业务错误。认证、限流和 500 继续复用公司公共错误组件。

| HTTP | `resCode` | `zh-CN` | `en-US` |
|---:|---|---|---|
| 400 | `CHAT_ID_INVALID` | `chatId 长度必须为 1 到 64 个字符。` | `chatId must contain between 1 and 64 characters.` |
| 400 | `CHAT_EVENT_INVALID` | `事件内容不符合要求。` | `The event does not satisfy the required constraints.` |
| 400 | `CHAT_EVENT_TYPE_INVALID` | `事件 type 不受支持。` | `The event type is not supported.` |
| 400 | `CHAT_EVENT_CREATED_AT_GTE_INVALID` | `createdAtGte 必须是包含毫秒的 RFC 3339 UTC 时间。` | `createdAtGte must be an RFC 3339 UTC timestamp with millisecond precision.` |
| 400 | `CHAT_EVENT_LIMIT_INVALID` | `limit 必须是 1 到 200 之间的整数。` | `limit must be an integer between 1 and 200.` |
| 400 | `CHAT_EVENT_TYPES_INVALID` | `types 为空或包含不支持的事件类型。` | `types is empty or contains an unsupported event type.` |
| 400 | `CHAT_EVENT_PAGE_CONFLICT` | `使用 page 时不能同时传入其他查询参数。` | `No other query parameters may be provided together with page.` |
| 400 | `CHAT_EVENT_PAGE_INVALID` | `page 无效，请重新发起第一页查询。` | `page is invalid. Start a new query from the first page.` |
| 403 | `CHAT_ACCESS_DENIED` | `无权访问该 Chat。` | `You do not have permission to access this Chat.` |
| 404 | `CHAT_NOT_FOUND` | `Chat 不存在。` | `The Chat does not exist.` |
| 409 | `CHAT_BUSY` | `当前 Chat 不能接受新的用户消息。` | `The Chat cannot accept a new user message.` |
| 409 | `CHAT_NOT_RUNNING` | `当前 Chat 没有可中断的执行。` | `The Chat has no running execution to interrupt.` |
| 409 | `TOOL_CONFIRMATION_NOT_PENDING` | `指定的 Tool Call 不在等待确认。` | `The specified Tool Call is not awaiting confirmation.` |
| 503 | `CHAT_RUNTIME_UNAVAILABLE` | `对话执行服务暂时不可用。` | `The conversation runtime is temporarily unavailable.` |

通用错误至少包括 `UNAUTHENTICATED`（401）、`TOO_MANY_REQUESTS`（429）和
`INTERNAL_ERROR`（500）。实现必须从公司公共错误目录取双语文案，不在本专题复制出第二套
定义。

## 9. 源码证据与差异分类

### 9.1 已观察源码行为

| 基线 | 路径与符号 | 观察结果 |
|---|---|---|
| `pi-mono-java@7e54b47f` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java` · `submitEvent` / `listEvents` | 当前 Claw 是 POST 请求范围 SSE + GET 历史，没有独立 Chat/Session 长连接 stream GET |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventType.java` · enum values | 当前内部类型包括 assistant/thinking/tool execution、session 状态和 stream 终止事件，不等于本公共五类 SSE |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventService.java` · `acceptUserMessage` | 当前只接受 `user.message`，要求 idle 并原子接受；interrupt 与 tool confirmation 尚未成为该 HTTP 请求联合类型 |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventProjector.java` · projection methods | 当前投影 provider/agent/tool 内部事件，完整 Assistant、Thinking 和 Tool Result 可落为持久记录 |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEntryCodec.java` · encode/decode methods | 当前持久记录有内部 entry identity、sequence 和 createdAt；本设计不把内部 sequence 暴露为 `eventSeq` |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java` · append/query methods | 当前历史按内部 entry sequence 和当前分支读取，不是本设计的 createdAt 固定快照公共分页 |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionControlService.java` · abort methods；`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/agent/SubagentExecutionService.java` · child cancellation | 当前取消可以等待主执行收敛，并向 Tool/Child Session 传播；idle abort 当前是 no-op，公共 idle interrupt 冲突是目标差异 |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/PreparedAgentRuntime.java` · permission handling | ASK/确认公共闭环尚未实现；`user.tool_confirmation` 是 target-only |
| `pi@5cd93f68` | `packages/ai/src/types.ts` · `AssistantMessageEvent`；`packages/agent/src/types.ts` · `AgentEvent` | Provider 增量与 Agent message/tool 生命周期分层，Tool Call 使用独立 ID |
| 同上 | `packages/agent/src/agent-loop.ts` · `streamAssistantResponse`；`packages/coding-agent/src/core/agent-session.ts` · `_handleAgentEvent` / `abort` | 增量用于 live update，完整 message end 才持久化；abort 等待执行变为 idle |
| 同上 | `packages/protocol/src/schemas.ts` · `TranscriptProgressSchema` / `SessionSnapshotSchema`；`packages/server/src/sessions.ts` · `handleRuntimeEvent` / `broadcastSnapshot` | 临时 transcript progress 与权威 snapshot 是不同投影 |

### 9.2 公开契约证据

- [Claude Managed Agents · Events and streaming](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)：
  提交、事件历史和流式观察分离；`event_start/event_delta` 是 best-effort preview，完整
  `agent.message` 是权威记录；断线后重新开流并查询历史对账。
- [Claude Managed Agents · List Session Events](https://platform.claude.com/docs/en/api/beta/sessions/events/list)：
  公开查询包含 created-at 条件、limit、order、page 和 types。本设计只采纳问题形态，
  将其收敛为升序固定快照、`createdAtGte/limit/types/page`。

Claude Managed Agents 在核对日仍是 Beta 公共 API。公开文档不能证明其内部表、sequence、
游标编码或服务端调度实现，本设计没有对此作推断。

### 9.3 CampusClaw 目标决策

| 分类 | 决策与理由 |
|---|---|
| 产品约束 | Mate 对外叫 Chat，Claw 内部叫 Session；公共层只保留三种 user event、五种 SSE event 和四个 idle reason，减少客户端状态机 |
| 产品约束 | `interrupt + message` 不批量提交；终止完成后再提交消息，保证单 active execution |
| 安全加固 | `agent.thinking` 只允许公开摘要；Tool 参数、结果和错误必须经过安全投影；内部 ID、路径、凭据和 private chain-of-thought 不出边界 |
| 架构变化 | POST、live SSE、durable history 分离；live 流不重放，历史固定快照；用 `eventId` 对账，不公开内部 sequence |
| 架构变化 | `agent.tool_call.eventId` 直接作为 toolCallId，减少重复字段；确认事件持久化以满足恢复和审计 |
| target-only | 新增 `user.interrupt`、`user.tool_confirmation`、独立 stream GET、固定快照历史和新的公共事件投影；这些均未在当前 Claw HTTP 层实现 |

本设计没有读取或引用本地 mate-service 实现作为设计基线；Mate 三个 operation 全部按
target-only 处理。实现阶段必须补充实际 mate-service commit、路径和符号，再校准 Controller、
VO、Service 与错误组件名称。

## 10. 实现和测试门禁

- Controller 使用独立 `*RequestVO` / `*ResponseVO`；字段级校验放请求 VO，Chat 状态、
  Tool Call 归属、固定快照和跨字段规则放 Service；
- 请求 VO 不放默认值；`limit=100` 和 `Accept-Language=en-US` 在 Service 统一归一化；
- `event.type` 使用受控联合类型反序列化；已知对象忽略未知字段，但未知 discriminator 拒绝；
- 覆盖 message 的 text-only/file-only/mixed、文本 Unicode code point 边界、文件数量/重复/
  顺序、allow/deny 和 denyMessage 条件字段；
- 覆盖 idle interrupt 冲突、interrupt 等待整棵执行树终止、confirming 时消息冲突、确认
  Tool Call 归属，以及中断 Tool 不伪造结果；
- 覆盖 SSE 只有 `data:`、ping comment、五类事件、同 ID delta/completed、completed 覆盖
  preview、连接断开不取消 execution；
- 覆盖历史八类事件、无 delta、createdAt inclusive、types OR/去重、固定快照不混入新事件、
  同时间稳定排序、无下一页时省略 `nextPage`；
- 做 discovery-to-invocation 契约测试，证明公开 `toolName`、`eventId/toolCallId` 与 Claw
  执行所需内部 Tool ID 不混用；
- 所有错误双语断言同时校验 HTTP、`resCode`、`Content-Language` 和无 `result`。

## 11. 生成与校验

```bash
python3 render_chat_events_v1.py
python3 validate-chat-events-v1.py
plantuml -tsvg 设计图/diagram.puml
```

校验覆盖三份 operation 模型、生成 HTML 同步、JavaScript 语法、响应式样式、SSE frame、
公共事件集合、lowerCamelCase、PlantUML ASCII、SVG XML 与同步、Markdown 图路径/行锚、
全仓 Mermaid 禁用和 `git diff --check`。

## 12. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-09-02 | 确认 POST 提交、Chat 级 live SSE 和固定快照历史三个 operation；固定三种用户事件、五种实时事件、八种历史事件、四个 idle reason、`eventId` 身份、字段形状、双语错误和断线对账；整体替换 0.1.0 请求范围 SSE 评审稿。 |
| 0.1.0 | 2026-09-01 | 建立单 POST 请求范围 SSE 初稿；该方案已由 1.0.0 替换。 |
