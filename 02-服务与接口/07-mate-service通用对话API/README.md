# mate-service 通用对话 Events API

[返回服务与接口导航](../README.md)

[Mate Chat API 协同评审入口](协作/README.md)

| 属性 | 值 |
|---|---|
| 文档版本 | 1.4.4 |
| 状态 | 三个 operation 已确认；待实现 |
| 设计性质 | target-only；不得描述为当前 mate-service 或 CampusClaw 已实现行为 |
| 设计仓变更前基线 | `743eca488ad559387706b5df54e2248a4124e5ef` |
| OpenAPI 增补前基线 | `cb94cdb29eeda701116e24cb9fd5e23090f5a91a` |
| Swagger 请求头修正前基线 | `d3bdc83917b0b6951171be781b2377fd89d5040c` |
| OpenAI Tool Call ID 修正前基线 | `ecf4cc06619f7a02c467d7212a0a12d86ab56a9f` |
| 完整用户事件回执修正前基线 | `d29418845b6782185e296edd5f138f5e993ac044` |
| 示例文案优化前基线 | `5ac57bac4c58c0ae86630f591f1f699a065c9e4f` |
| Events 示例整体润色前基线 | `7887d55ed86033e7163494d0dda2f0bb85544a83` |
| 工具调用同意回执示例增补前基线 | `44a13fd95fcc4caec0f75e55291dc53fcc8daaf8` |
| 实时流工具交互示例增补前基线 | `d6e339478bbc7475a5b5f0aa4d5fdebd05bd1600` |
| CampusClaw 源码核对基线 | `7e54b47f2539982f8f1855a0b6bb38b6ab8742ae` |
| pi 固定参考基线 | `badlogic/pi-mono@5cd93f688aaab89dbb6dfa4aca535f21796ae185` |
| Claude Managed Agents 公开文档核对日期 | 2026-09-02；Beta 公共契约，无可归因服务端源码 |
| OpenAI API 公开文档核对日期 | 2026-09-02 |
| 更新日期 | 2026-09-02 |

## 1. 已确认接口

Mate 对外只使用 `Chat/chatId/chat.*`；Claw 内部继续使用
`Session/sessionId/session.*`。三个接口共享同一组公共事件定义，但提交、实时观察和权威历史
彼此分离：

| # | 方法与路径 | 用途 | 返回 |
|---:|---|---|---|
| 1 | `POST /mate-service/v1/chats/{chatId}/events` | 提交一条用户事件 | 完整用户事件 JSON |
| 2 | `GET /mate-service/v1/chats/{chatId}/events/stream` | 实时接收 Chat 从连接建立后产生的事件 | 长连接 SSE，仅实时预览与通知 |
| 3 | `GET /mate-service/v1/chats/{chatId}/events` | 读取可恢复、可审计的完整事件历史 | 固定快照分页 JSON |

精确 operation 模型和生成后的主评审面：

- [三接口契约评审页](chat-events-v1-review.html)
- [OpenAPI 3.1 机器契约](chat-events-v1.openapi.yaml)
- [01 · 提交事件](接口契约/操作/01-submit-chat-event.json)
- [02 · 订阅实时事件](接口契约/操作/02-stream-chat-events.json)
- [03 · 查询事件历史](接口契约/操作/03-list-chat-events.json)

standalone HTML 是主要人类契约，三份 operation JSON 驱动该页面；OpenAPI 3.1 是同步的
机器可读投影，用于 Swagger UI、代码生成和实现校验。本 Markdown 说明边界、字段语义、
源码证据和设计理由。任何字段调整必须同时更新 operation model、OpenAPI 和校验器。

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

如果 `Authorization` 和 `X-HW-APPKEY` 同时存在，必须使用 JWT；JWT 无效时直接返回认证
失败，不能回退到 AppKey。mate-service 先认证、授权 Chat，再解析私有 `sessionId`。

OpenAPI 中，`X-HW-ID` 和 `access-token` 显式定义为每个 operation 的必需
header parameter，因此 Swagger 会在三个接口的 Parameters 区直接展示。
`Authorization` 和 `X-HW-APPKEY` 属于二选一认证凭据，仅在
`securitySchemes` 中定义；`Authorization` 不再重复定义为普通 header
parameter。`Content-Type: application/json` 由 `requestBody.content` 声明。

Mate 这三个对外 operation 不声明 `Accept-Language`；Mate 公共国际化上下文
负责确定错误文案语言，错误响应的 `Content-Language` 只表示实际使用的
语言。后续 Claw HTTP Events 接口需要接收语言时，应在 Claw 契约中单独
声明 `Accept-Language`，不从 Mate 契约隐式继承。

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
`agent.thinking` 的多帧实时增量与最终完整事件复用同一个 `eventId`。POST
`result.event.eventId` 只标识被接受的那条 `user.*` 事件，不是 execution、Turn、
Tool Call 或后续 Agent 输出的关联 ID。

执行边界由事件时间顺序和 `chat.status_idle` 识别，不增加 `turnId`、`runId` 或
`messageEventId`。Tool 同时有两种不同身份：

- `eventId` 是 Mate 为每条持久化事件生成的公共事件 ID；
- `toolCallId` 是 OpenAI Tool Call 关联 ID。Responses API 直接使用 function call
  的 `call_id`，Chat Completions API 直接使用 `tool_calls[].id`。

`agent.tool_call`、`user.tool_confirmation` 和 `agent.tool_result` 使用完全相同的
`toolCallId` 关联一次 Tool Call；三条事件各自仍有独立 `eventId`。
`toolCallId` 区分大小写，在公共契约中是不透明非空字符串；不声明正则、
最大长度或稳定前缀，客户端不得解析、修改或自行构造。Responses 返回的
function call item `id`（例如 `fc_...`）不是本字段。

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

OpenAPI 使用 `event.oneOf + discriminator(propertyName=type)` 展示三个联合类型。Swagger
UI 的请求示例下拉框提供四个命名示例：

| 示例名 | 展示内容 |
|---|---|
| `userMessage` | 附上园区巡检记录，请 Agent 梳理异常告警并提出处理建议 |
| `userInterrupt` | 中断当前正在执行的分析 |
| `toolConfirmationAllow` | 允许隔离受影响端口，并省略 `denyMessage` |
| `toolConfirmationDeny` | 拒绝修改生产配置，并要求 Agent 提供替代方案 |

因此另外两种事件不会被塞进同一个庞大示例，也不会新增 endpoint；Schema 区通过
`oneOf` 展开类型，Try it out 区通过 `examples` 切换具体请求。

示例摘要采用“业务场景在前、协议类型作为辅助标识”的表达方式。调用方可以先按场景
选择示例，再通过标题中的类型或 JSON 的 `event.type` 确认精确协议类型。

### 4.1 `user.message`

请求示例：用户附上园区巡检记录，请 Agent 梳理异常告警并提出处理建议。

```json
{
  "event": {
    "type": "user.message",
    "content": [
      {"type": "text", "text": "请结合附件中的巡检记录，梳理东区园区的异常告警，并给出处理建议。"},
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

请求示例：用户中断当前正在执行的分析。

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

请求示例：用户拒绝会修改生产配置的端口隔离操作，并请 Agent 改用无变更风险的方案。

```json
{
  "event": {
    "type": "user.tool_confirmation",
    "toolCallId": "call_unLAR8MvFNptuiZK6K6HCy5k",
    "result": "deny",
    "denyMessage": "该操作会修改生产配置，请先给出无变更风险的处理建议。"
  }
}
```

| 字段 | 类型 | 必需 | 允许值与语义 |
|---|---|---:|---|
| `type` | string | 是 | 固定 `user.tool_confirmation` |
| `toolCallId` | string | 是 | 原样回传等待确认的 `agent.tool_call.toolCallId`；直接来自 OpenAI `call_id` / `tool_calls[].id`，区分大小写且不透明，非空，无格式正则 |
| `result` | string | 是 | `allow` 或 `deny` |
| `denyMessage` | string | 否 | 仅 `deny` 可提供；可省略，提供时非空白且最多 2048 个 Unicode code point；`allow` 时必须省略 |

确认事件只在 Chat 的当前状态为 `confirming` 且 Tool Call 正在等待确认时接受。它会作为
完整历史事件保留，以便审计和 UI 恢复；实时流不重复发送 `user.tool_confirmation`。

### 4.4 完整用户事件成功响应

园区巡检分析请求已接收并保存：

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "event": {
      "eventId": "b7ef45d40a854c33af7a36df871a21e8",
      "type": "user.message",
      "createdAt": "2026-09-02T08:30:15.123Z",
      "content": [
        {
          "type": "text",
          "text": "请结合附件中的巡检记录，梳理东区园区的异常告警，并给出处理建议。"
        },
        {
          "type": "file",
          "fileId": "7f12d8a380964fdc8518f48be1cf6a42"
        }
      ]
    }
  }
}
```

中断分析的指令已接收并保存：

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "event": {
      "eventId": "aee903c130e048b9bc2894fc32cd63a8",
      "type": "user.interrupt",
      "createdAt": "2026-09-02T08:30:14.800Z"
    }
  }
}
```

工具调用确认有两个互斥的响应示例。若用户允许隔离受影响端口，返回的完整事件中
`result="allow"`，并且必须省略 `denyMessage`：

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "event": {
      "eventId": "61a4b8cf5e2d4f93a7c018b6d9e42f75",
      "type": "user.tool_confirmation",
      "createdAt": "2026-09-02T08:30:16.420Z",
      "toolCallId": "call_unLAR8MvFNptuiZK6K6HCy5k",
      "result": "allow"
    }
  }
}
```

若用户拒绝会修改生产配置的操作，返回的完整事件中 `result="deny"`，并保留用户给出的
替代要求：

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "event": {
      "eventId": "2781508bb1c9496f94a0454d0bf8c0f8",
      "type": "user.tool_confirmation",
      "createdAt": "2026-09-02T08:30:16.420Z",
      "toolCallId": "call_unLAR8MvFNptuiZK6K6HCy5k",
      "result": "deny",
      "denyMessage": "该操作会修改生产配置，请先给出无变更风险的处理建议。"
    }
  }
}
```

| 字段 | 类型 | 必需 | 语义 |
|---|---|---:|---|
| `resCode` | string | 是 | 固定 `0` |
| `resMsg` | string | 是 | 固定 `success` |
| `result.event` | object | 是 | 服务端接受并持久化后的完整 `user.*` 事件；按 `type` 匹配三个事件 Schema 之一 |
| `result.event.eventId` | string | 是 | 服务端生成的事件 ID；与历史中的该事件完全相同 |
| `result.event.type` | string | 是 | 请求对应的 `user.message`、`user.interrupt` 或 `user.tool_confirmation` |
| `result.event.createdAt` | string | 是 | 服务端接受并持久化该事件的时间；与历史记录完全相同 |
| `result.event.content` | array | `user.message` 必需 | 服务端接受的完整文本/文件内容数组；形状与请求和历史 `UserMessageEvent` 一致 |
| `result.event.toolCallId` | string | `user.tool_confirmation` 必需 | 原样保存的 OpenAI Tool Call ID；形状与历史确认事件一致 |
| `result.event.result` | string | `user.tool_confirmation` 必需 | `allow` 或 `deny`；这是事件业务字段，不是外层 ResultBean 的 `result` 包络 |
| `result.event.denyMessage` | string | 否 | 仅拒绝时可按实际持久化内容返回；允许时必须省略 |

`result.event` 复用历史接口的 `UserMessageEvent`、`UserInterruptEvent` 和
`UserToolConfirmationEvent` Schema，不另外维护“精简回执事件”。响应会返回规范化后实际
持久化的完整业务字段，并补充服务端字段 `eventId`、`createdAt`；不会返回 `acceptedAt`、
`processedAt`、Agent 输出、execution 状态或后续 `chat.status_idle`。

若客户端在收到响应前断线，提交结果仍然不确定；本版本没有 Idempotency-Key，客户端必须
查询权威历史，不能盲目重放 POST。`user.*` 事件不进入 live SSE，因此不会因同时消费 SSE
而重复收到这条提交事件。

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

## 5. 接口二：实时接收 Chat 事件

```http
GET /mate-service/v1/chats/{chatId}/events/stream
Accept: text/event-stream
```

连接成功后，服务端以 `text/event-stream` 持续推送该 Chat 的新事件，并通过
`Cache-Control: no-store` 禁止缓存对话内容。连接可以跨越多次执行和空闲状态；收到
`chat.status_idle` 只表示当前执行已经收敛，不会关闭连接。服务端可以使用 `: ping` 注释保活。

### 5.1 Frame 规则

每个业务 frame 只有一行 `data:`，值是完整 JSON：

以下示例展示同一条回复从实时增量收敛为完整记录：

```text
data: {"eventId":"d5c19f7c4b1642e6806aeb860752d99b","type":"agent.message","phase":"delta","content":"结合巡检记录与告警信息，"}

: ping

data: {"eventId":"d5c19f7c4b1642e6806aeb860752d99b","type":"agent.message","phase":"completed","createdAt":"2026-09-02T08:30:19.451Z","content":"结合巡检记录与告警信息，建议先隔离受影响端口，并进一步核查上联链路状态。"}
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

实时增量（`phase=delta`）：

```json
{
  "eventId": "4b3e522e7f6746be8781a2c8876fd1da",
  "type": "agent.thinking",
  "phase": "delta",
  "content": "正在梳理巡检记录与告警时间线……"
}
```

完整记录（`phase=completed`）：

```json
{
  "eventId": "4b3e522e7f6746be8781a2c8876fd1da",
  "type": "agent.thinking",
  "phase": "completed",
  "createdAt": "2026-09-02T08:30:17.305Z",
  "content": "已完成巡检记录、告警时间线和影响范围的梳理。"
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

示例：Agent 准备隔离受影响端口，并在执行前请求用户确认。

```json
{
  "eventId": "c8de683be2ab4e25a8d97f7cf507c150",
  "type": "agent.tool_call",
  "toolCallId": "call_unLAR8MvFNptuiZK6K6HCy5k",
  "createdAt": "2026-09-02T08:30:16.000Z",
  "toolName": "isolate_campus_port",
  "arguments": {
    "deviceName": "SW-DC-01",
    "portName": "GigabitEthernet0/0/24"
  },
  "requiresConfirmation": true
}
```

| 字段 | 类型 | 必需 | 允许值与语义 |
|---|---|---:|---|
| `eventId` | string | 是 | Tool Call 事件自己的 32 位小写十六进制事件 ID；不是 `toolCallId` |
| `type` | string | 是 | 固定 `agent.tool_call` |
| `toolCallId` | string | 是 | OpenAI Tool Call 关联 ID；Responses 取 `call_id`，Chat Completions 取 `tool_calls[].id`；区分大小写且不透明，非空，无格式正则 |
| `createdAt` | string | 是 | Tool Call 被持久化的时间 |
| `toolName` | string | 是 | 非空白，最多 128 个字符的稳定公开 Tool 名称 |
| `arguments` | object | 是 | 允许空对象；仅包含已做公开安全投影的 JSON 参数 |
| `requiresConfirmation` | boolean | 是 | `true` 表示执行前需要 `user.tool_confirmation` |

当 `requiresConfirmation=true`，随后发送
`chat.status_idle(reason="confirming")`。客户端提交确认时必须原样回传该
`toolCallId`，不得回传 `eventId` 或 OpenAI Responses function call item 的 `fc_...` ID。

### 5.5 `agent.tool_result`

示例：用户拒绝工具调用后，服务端记录该操作未执行。

```json
{
  "eventId": "89f8316e07ef4c9aa3fd056a91a182b0",
  "type": "agent.tool_result",
  "createdAt": "2026-09-02T08:30:16.600Z",
  "toolCallId": "call_unLAR8MvFNptuiZK6K6HCy5k",
  "content": "用户已拒绝，本次工具调用未执行。",
  "isError": true,
  "errorCode": "TOOL_CALL_DENIED"
}
```

| 字段 | 类型 | 必需 | 允许值与语义 |
|---|---|---:|---|
| `eventId` | string | 是 | Tool Result 自己的事件 ID，不等于 `toolCallId` |
| `type` | string | 是 | 固定 `agent.tool_result` |
| `createdAt` | string | 是 | 结果被持久化的时间 |
| `toolCallId` | string | 是 | 与对应 `agent.tool_call.toolCallId` 完全相同的 OpenAI Tool Call ID |
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

### 5.7 需要确认并同意执行的工具交互

下面是 `StreamEvents` 中“用户同意后执行端口隔离”的完整响应示例：

```text
data: {"eventId":"5e9a24c8d7134f6baa10c9827d45e301","type":"agent.thinking","phase":"delta","content":"正在评估隔离受影响端口的范围与风险……"}

data: {"eventId":"5e9a24c8d7134f6baa10c9827d45e301","type":"agent.thinking","phase":"completed","createdAt":"2026-09-02T08:30:16.000Z","content":"已确认异常集中在 SW-DC-01 的上联端口，隔离操作会修改生产配置。"}

data: {"eventId":"6c7d8e9f01234567a89bcdef01234567","type":"agent.tool_call","toolCallId":"call_unLAR8MvFNptuiZK6K6HCy5k","createdAt":"2026-09-02T08:30:16.100Z","toolName":"isolate_campus_port","arguments":{"deviceName":"SW-DC-01","portName":"GigabitEthernet0/0/24"},"requiresConfirmation":true}

data: {"eventId":"7d8e9f0123456789abcdef0123456789","type":"chat.status_idle","createdAt":"2026-09-02T08:30:16.200Z","reason":"confirming"}

: ping

data: {"eventId":"8e9f0123456789abcdef0123456789ab","type":"agent.tool_result","createdAt":"2026-09-02T08:30:16.800Z","toolCallId":"call_unLAR8MvFNptuiZK6K6HCy5k","content":"已隔离 SW-DC-01 的 GigabitEthernet0/0/24 端口。","isError":false}

data: {"eventId":"9f0123456789abcdef0123456789abcd","type":"agent.message","phase":"delta","content":"已按确认完成端口隔离，"}

data: {"eventId":"9f0123456789abcdef0123456789abcd","type":"agent.message","phase":"completed","createdAt":"2026-09-02T08:30:17.000Z","content":"已按确认完成端口隔离，建议继续观察上联链路告警并安排后续根因排查。"}

data: {"eventId":"a0123456789abcdef0123456789abcde","type":"chat.status_idle","createdAt":"2026-09-02T08:30:17.100Z","reason":"done"}
```

`confirming` 与 `agent.tool_result` 之间，客户端通过提交事件接口发送
`user.tool_confirmation(result="allow")`。该事件属于用户提交和权威历史，不在 SSE 中重复
推送；确认被接受后，同一条 Chat 流继续发送工具结果、Agent 回复和最终 `done`。

### 5.8 流错误边界

SSE Header 尚未发送时，认证、授权、Chat 不存在和容量错误使用普通 JSON 错误。SSE 建立
后不发送业务 `stream.error`；编码、网络或内部订阅异常直接结束传输。客户端重连并查询
权威历史，不能依据连接关闭推断 execution 成败。

## 6. 接口三：查询 Chat 事件历史

```http
GET /mate-service/v1/chats/{chatId}/events?createdAtGte=2026-09-02T08%3A30%3A00.000Z&limit=2&types=user.message&types=agent.message
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

用户消息（`user.message`）：

```json
{
  "eventId": "b7ef45d40a854c33af7a36df871a21e8",
  "type": "user.message",
  "createdAt": "2026-09-02T08:30:15.123Z",
  "content": [
    {"type": "text", "text": "请结合附件中的巡检记录，梳理东区园区的异常告警，并给出处理建议。"},
    {"type": "file", "fileId": "7f12d8a380964fdc8518f48be1cf6a42"}
  ]
}
```

中断指令（`user.interrupt`）：

```json
{
  "eventId": "aee903c130e048b9bc2894fc32cd63a8",
  "type": "user.interrupt",
  "createdAt": "2026-09-02T08:30:14.800Z"
}
```

工具确认结果（`user.tool_confirmation`）：

```json
{
  "eventId": "2781508bb1c9496f94a0454d0bf8c0f8",
  "type": "user.tool_confirmation",
  "createdAt": "2026-09-02T08:30:16.420Z",
  "toolCallId": "call_unLAR8MvFNptuiZK6K6HCy5k",
  "result": "deny",
  "denyMessage": "该操作会修改生产配置，请先给出无变更风险的处理建议。"
}
```

`agent.message` 和 `agent.thinking` 只保存 completed 形态，并保留
`phase="completed"`；`agent.tool_call`、`agent.tool_result` 和
`chat.status_idle` 与实时流的完整形态完全相同。`agent.tool_call` 同时保留它的
`eventId` 和 OpenAI `toolCallId`。UI 可以按 `toolCallId` 把 Tool Call、确认和结果关联
展示，但历史仍保留三个独立 `eventId` 的审计事件。

### 6.4 成功响应示例

以下示例只查询用户消息和 Agent 回复，并设置 `limit=2`。服务端返回两条完整记录；当前
固定快照仍有后续记录，因此同时返回 `nextPage`：

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
        "content": [
          {"type": "text", "text": "请结合附件中的巡检记录，梳理东区园区的异常告警，并给出处理建议。"},
          {"type": "file", "fileId": "7f12d8a380964fdc8518f48be1cf6a42"}
        ]
      },
      {
        "eventId": "4b3e522e7f6746be8781a2c8876fd1da",
        "type": "agent.message",
        "phase": "completed",
        "createdAt": "2026-09-02T08:30:17.000Z",
        "content": "已取消会修改生产配置的操作。建议先核查上联链路与告警时间线，再安排变更窗口处理。"
      }
    ],
    "nextPage": "pg_4M7qK2vN9xR5dT8wC1hF6sL3"
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

[PlantUML 源码：`public_chat_event_recovery`](设计图/diagram.puml#L44)

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
| `pi-mono-java@7e54b47f` | `modules/ai/src/main/java/com/campusclaw/ai/provider/openai/OpenAIResponsesProvider.java:415-426,465-473,515-521,534-544` · `handleOutputItemAdded` / `handleOutputItemDone` / `convertAssistantInput` / `convertToolResultInput` | OpenAI Responses function call 的 `call_id` 被写入 `ToolCall.id`，后续 Tool Call 和 Tool Result 输入都把同一值写回 `callId`；该链路未使用 function call item `id` |
| 同上 | `modules/ai/src/main/java/com/campusclaw/ai/types/ToolCall.java:24-28` · `ToolCall.id`；`modules/ai/src/main/java/com/campusclaw/ai/types/ToolResultMessage.java:26-32` · `toolCallId` | Claw 归一化模型使用独立 Tool Call ID 关联调用和结果 |
| 同上 | `modules/ai/src/test/java/com/campusclaw/ai/provider/openai/OpenAIResponsesProviderIntegrationTest.java:217-262` · `streamsToolCallResponse` | 测试明确区分 item `id="fc_1"` 和 `call_id="call_xyz"`，并断言归一化 `ToolCall.id()` 等于 `call_xyz` |
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
- [OpenAI Responses API](https://developers.openai.com/api/reference/typescript/resources/beta/subresources/responses/methods/create)：
  function call output 同时有 item `id` 和用于对应 function call output 的 `call_id`；本契约
  使用后者。
- [OpenAI Chat Completions API](https://developers.openai.com/api/reference/cli/resources/chat/subresources/completions)：
  Assistant 的 `tool_calls[].id` 与 Tool message 的 `tool_call_id` 关联同一次调用。

Claude Managed Agents 在核对日仍是 Beta 公共 API。公开文档不能证明其内部表、sequence、
游标编码或服务端调度实现，本设计没有对此作推断。

### 9.3 CampusClaw 目标决策

| 分类 | 决策与理由 |
|---|---|
| 产品约束 | Mate 对外叫 Chat，Claw 内部叫 Session；公共层只保留三种 user event、五种 SSE event 和四个 idle reason，减少客户端状态机 |
| 产品约束 | `interrupt + message` 不批量提交；终止完成后再提交消息，保证单 active execution |
| 安全加固 | `agent.thinking` 只允许公开摘要；Tool 参数、结果和错误必须经过安全投影；内部 ID、路径、凭据和 private chain-of-thought 不出边界 |
| 架构变化 | POST、live SSE、durable history 分离；live 流不重放，历史固定快照；用 `eventId` 对账，不公开内部 sequence |
| 架构变化 | POST 成功时在 `result.event` 返回完整、已持久化的 `user.*` 事件，并与历史接口复用同一 Schema；这使创建响应可直接作为权威记录合并，同时不把 Agent execution 结果混入写入响应 |
| 架构变化 | `eventId` 与 `toolCallId` 分离；`agent.tool_call` 显式公开 OpenAI `call_id` / `tool_calls[].id`，确认和结果原样引用该值。这是有意的 OpenAI 身份耦合，非 OpenAI Provider 不得伪造 `call_` ID；若要纳入本公共契约，必须另行版本决策 |
| 架构变化 | 确认事件持久化，与 Tool Call 和 Tool Result 共享 `toolCallId`，同时各自保留独立 `eventId`，以满足恢复和审计 |
| target-only | 新增 `user.interrupt`、`user.tool_confirmation`、独立 stream GET、固定快照历史和新的公共事件投影；这些均未在当前 Claw HTTP 层实现 |

本设计没有读取或引用本地 mate-service 实现作为设计基线；Mate 三个 operation 全部按
target-only 处理。实现阶段必须补充实际 mate-service commit、路径和符号，再校准 Controller、
VO、Service 与错误组件名称。

## 10. 实现和测试门禁

- Controller 使用独立 `*RequestVO` / `*ResponseVO`；字段级校验放请求 VO，Chat 状态、
  Tool Call 归属、固定快照和跨字段规则放 Service；
- 请求 VO 不放默认值；`limit=100` 在 Service 统一归一化；Mate 这三个
  operation 不接收 `Accept-Language`；
- `event.type` 使用受控联合类型反序列化；已知对象忽略未知字段，但未知 discriminator 拒绝；
- 覆盖 message 的 text-only/file-only/mixed、文本 Unicode code point 边界、文件数量/重复/
  顺序、allow/deny 和 denyMessage 条件字段；
- 覆盖三种 POST 成功响应均只通过 `result.event` 返回完整持久化用户事件，并逐字段断言
  与历史 `UserMessageEvent`、`UserInterruptEvent`、`UserToolConfirmationEvent` Schema 一致；
- 覆盖 idle interrupt 冲突、interrupt 等待整棵执行树终止、confirming 时消息冲突、确认
  Tool Call 归属，以及中断 Tool 不伪造结果；
- 覆盖 SSE 只有 `data:`、ping comment、五类事件、同 ID delta/completed、completed 覆盖
  preview、连接断开不取消 execution；
- 覆盖历史八类事件、无 delta、createdAt inclusive、types OR/去重、固定快照不混入新事件、
  同时间稳定排序、无下一页时省略 `nextPage`；
- 做 discovery-to-invocation 契约测试，证明公开 `toolName`、事件 `eventId`、
  OpenAI Responses `call_id` / Chat Completions `tool_calls[].id` 和 Claw 执行所需内部 Tool ID
  不混用；Responses item `id=fc_...` 不得投影为 `toolCallId`；
- 覆盖 `agent.tool_call -> user.tool_confirmation -> agent.tool_result` 的完整往返，断言三者
  原样共享大小写敏感的 OpenAI `toolCallId`、各自使用独立 `eventId`，且实现不对
  `toolCallId` 施加前缀、长度或正则校验；
- 所有错误双语断言同时校验 HTTP、`resCode`、`Content-Language` 和无 `result`。

## 11. 生成与校验

```bash
python3 render_chat_events_v1.py
python3 validate-chat-events-v1.py
npx --yes @redocly/cli lint chat-events-v1.openapi.yaml
plantuml -tsvg 设计图/diagram.puml
```

校验覆盖三份 operation 模型、OpenAPI 3.1 路径/安全方案/`oneOf`/命名示例、生成 HTML
同步、JavaScript 语法、响应式样式、SSE frame、公共事件集合、lowerCamelCase、
PlantUML ASCII、SVG XML 与同步、Markdown 图路径/行锚、全仓 Mermaid 禁用和
`git diff --check`。

## 12. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.4.4 | 2026-09-02 | 为实时流增加“用户同意后执行端口隔离”的完整工具交互示例，覆盖 `tool_call`、`confirming`、POST 确认边界、`tool_result`、Agent 回复与最终 `done`；事件类型和字段不变。 |
| 1.4.3 | 2026-09-02 | 补充“允许工具调用”的提交成功响应示例，与既有拒绝示例并列展示；明确 `allow` 响应省略 `denyMessage`，字段、Schema 和行为不变。 |
| 1.4.2 | 2026-09-02 | 整体润色三个 Events 接口的说明与示例，统一为真实、连贯的园区巡检场景，并为实时流和历史页增加命名示例；字段、Schema 和行为不变。 |
| 1.4.1 | 2026-09-02 | 优化提交接口的示例摘要：统一采用业务场景在前、协议类型作为辅助标识的表达方式；字段、Schema 和行为不变。 |
| 1.4.0 | 2026-09-02 | POST 成功响应改为在 `result.event` 返回完整、已持久化的 `user.message`、`user.interrupt` 或 `user.tool_confirmation`，并直接复用历史事件 Schema；响应仍不包含 Agent execution 结果。 |
| 1.3.0 | 2026-09-02 | 将 `toolCallId` 改为直接使用 OpenAI Tool Call ID：Responses 取 `call_id`，Chat Completions 取 `tool_calls[].id`；`agent.tool_call` 增加必需 `toolCallId`，确认和结果原样引用；`eventId` 仍是独立的 32 位公共事件 ID；移除 `toolCallId` 正则和长度假设。 |
| 1.2.0 | 2026-09-02 | 按标准 Swagger 表达修正请求头：`X-HW-ID` 和 `access-token` 改为三个 operation 的必需 header parameter；JWT 和 APPKEY 保留为二选一 security scheme；Mate 删除 `Accept-Language` 请求声明，Claw 接口边界不变。 |
| 1.1.0 | 2026-09-02 | 增加三接口 OpenAPI 3.1 机器契约；提交事件用 `oneOf + discriminator` 和四个命名示例展示三种用户事件；将 page 示例改为不可推断内部字段的 opaque cursor；接口行为保持 1.0.0。 |
| 1.0.0 | 2026-09-02 | 确认 POST 提交、Chat 级 live SSE 和固定快照历史三个 operation；固定三种用户事件、五种实时事件、八种历史事件、四个 idle reason、`eventId` 身份、字段形状、双语错误和断线对账；整体替换 0.1.0 请求范围 SSE 评审稿。 |
| 0.1.0 | 2026-09-01 | 建立单 POST 请求范围 SSE 初稿；该方案已由 1.0.0 替换。 |
