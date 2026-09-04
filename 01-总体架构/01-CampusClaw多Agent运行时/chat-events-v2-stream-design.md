# Session 实时订阅接口设计

| 属性 | 值 |
|---|---|
| 文档版本 | 0.1.1 |
| 状态 | 第二个接口评审中；五个基础类型名已确认，其余仍为候选，target-only |
| 前置决策 | POST 已确认；`eventId`、不公开内部序号、Session 因果顺序继续生效 |
| 设计仓本次变更前基线 | `8019b88`；首次候选基线为 `463d55c` |
| 实现核对 | `pi-mono-java@a8192e047f4061bd385297d3dc6c4358362d0d49` |
| 原实现基线 | `c9d858bc8261bf07f5585f545b53495bf2226a56`；本文五个源码文件在两提交间无变化 |
| Mate 契约对照 | 通用对话 Events 1.4.4，已确认目标契约，不是实现证据 |
| 公开参考核对 | Claude Managed Agents 官方事件流文档，2026-09-04，Beta |
| 更新日期 | 2026-09-04 |

## 1. 用途与评审边界

```http
GET /campusclaw-service/v1/sessions/{sessionId}/events/stream
X-HW-ID: credential-jwt
Authorization: Bearer opaque-token
Accept: text/event-stream
```

保持一条指定 Session 的只读连接，接收订阅就绪之后产生的新事件。不提交消息、不启动
执行、不取消执行，也不为正在运行的 Agent 更换凭据。空闲时可以订阅；一次执行结束后
连接继续等待下一次执行。同一 Session 可以有多个订阅者。

本轮候选以 [operation JSON](接口契约-v2/操作/02-stream-session-events.json) 和
[当前评审页](chat-events-v2-review.html) 为精确示例。第一接口的已确认状态不再开放选择；
本轮只确认 §4 的五个基础类型名；其他字段不因渲染、校验或提交而视为确认。

## 2. 请求与凭据（候选）

- Path `sessionId` 沿用共享 ID 规则；必须存在且未删除。
- JWT 与 APPKEY 沿用已确认的具体非生产示例值，以及 `X-HW-ID` 的用户凭据 ID 语义。
  GET 中这些 Header 只属于订阅请求上下文，不复制到 Subscription、事件、日志或
  Agent 执行对象，不调用 Mate tool execute。框架可能仍持有原始请求对象，不承诺
  应用能够在 Header 读取后立即擦除框架内存。
- 上游负责真实性与访问授权；Claw 仍不自行解析或校验 JWT/APPKEY，不新增本地 401
  或凭据互斥规则。这是既有内部服务信任边界，不意味着浏览器可以绕过 Mate 直连。
- 推荐不要求 `access-token`；即使提供也不用于执行。前次“统一携带”针对 POST 的
  三种用户事件，不自动冻结 GET 必填。S4 可选择为调用方组装方便而统一携带。
- 无请求体、无 query；携带正文、query 或 `Last-Event-ID` 候选返回
  `400 INVALID_EVENT_STREAM_REQUEST`，避免调用方误以为支持恢复。
- `Accept-Language` 沿用 `zh-CN/en-US`，缺失或不支持时为 `en-US`，只决定错误文案。
  它不改变已持久化文本或模型输出语言。兼容带自定义 Header 的服务端 HTTP/SSE 客户端；
  不要求浏览器使用原生 EventSource 直连 Claw。

## 3. 连接和帧（候选）

订阅必须先注册到正确 Session，再发送 Header 和第一条 `: connected` 注释。
客户端看到该注释才认为订阅就绪；不能仅启动一个异步 GET，就立即假设后续 POST 输出
不会漏。`connected` 不包含 Session 状态，也不替代历史查询。

```text
Content-Type: text/event-stream
Cache-Control: no-store

: connected

data: {"eventId":"d5c19f7c4b1642e6806aeb860752d99b","type":"agent.message","phase":"delta","content":"正在整理告警信息，"}

data: {"eventId":"d5c19f7c4b1642e6806aeb860752d99b","type":"agent.message","phase":"completed","createdAt":"2026-09-04T08:30:19.451Z","content":"已整理告警信息，建议先核查上联链路。"}

: ping
```

推荐业务帧只含一行 `data:` JSON，帧以空行结束；不输出 SSE `event:` 或 `id:`，不把
业务 `eventId` 冒充恢复游标。文本中的换行按 JSON 转义，不分拆为额外的业务帧。
首次连接不补发历史、不合成 idle；候选无事件时每 15 秒保活一次，间隔可由服务端配置，
部署时与代理超时协调。Heartbeat 不是事件，不持久化，不带 ID 或时间。

## 4. 已确认类型名与候选字段

2026-09-04 用户明确指定下表五个基础类型名。名称属于已确认的目标 API 产品约束：
Agent 消息、思考、工具调用与结果统一使用 `agent.*`，前四项与 Mate 同名；状态保留
Claw 的 Session 资源身份，使用 `session.status_idle`。完整事件在流和历史中使用
同名，不提供旧候选名称的兼容别名；这不改动 v1 迁移基线或 Runtime 内部枚举。

本次没有确认 `phase`、增量结构、thinking 内容或整个 GET。下表第三列仍是沿用 Mate
“完整事件 + 文本增量”的候选；S2 只继续讨论结构，不再开放名称选择。本表不是完整的
Runtime 事件清单，不能据此删除其他事件能力。

| Claw 已确认 `type` | Mate 已确认 `type` | 候选形状与历史 |
|---|---|---|
| `agent.message` | `agent.message` | `eventId/type/phase/content`；只有 `completed` 带 `createdAt` 并进入权威历史 |
| `agent.thinking` | `agent.thinking` | 同上；只在 thinking 启用且有可公开摘要时输出，不转发原始推理 |
| `agent.tool_call` | `agent.tool_call` | `eventId/type/createdAt/toolCallId/toolName/arguments/requiresConfirmation`；完整事件 |
| `agent.tool_result` | `agent.tool_result` | `eventId/type/createdAt/toolCallId/content/isError`；失败时可有稳定 `errorCode`；完整事件 |
| `session.status_idle` | `chat.status_idle` | `eventId/type/createdAt/reason`；完整事件，reason 候选为 `done/terminated/failed/confirming` |

字段候选约束：

- `eventId` 是服务端逻辑事件身份，不是帧序号或执行 ID。同一正文/摘要的 delta 与
  completed 复用该 ID；completed 后不再发送该事件的 delta。具体 ID 正则不在本轮
  从 Mate 自动继承。
- `phase` 仅为 `delta/completed`；`content` 是字符串。delta 是新追加的非空片段，
  可只含空白；completed 是完整文本，允许空串。completed 必须覆盖 preview，不把
  增量拼接结果当作权威内容。delta 必须省略 `createdAt`。
- 新订阅可能在回复中途建立，没有此前的 delta；其 preview 可以不完整，完整事件或
  历史会纠正展示。背压丢弃某条消息的 delta 后，该连接应停止该 ID 后续 delta，直到
  completed，避免把缺片段文本误呈现成连续输出。
- `toolCallId` 原样关联工具调用、POST 确认和结果，不等于任何一个事件的 `eventId`。
  参数为 JSON object，允许空对象；`requiresConfirmation/isError` 为 boolean。
  工具名称为非空字符串；结果 content 允许空串；成功时必须省略 `errorCode`。
- 工具参数和输出只能包含该内部 API 允许的业务信息，仍禁止凭据、内部异常堆栈等。
  Mate 必须再做公共安全投影，不能透明转发。完整事件在 stream 与 ListEvents 使用
  相同名称和字段，不创建另一套历史别名。
- `confirming` 表示等待工具确认，不允许新的 `user.message`；通过已确认 POST 提交
  确认或中断。`terminated` 只在执行停止后发出，不以中断请求的 200 替代。
  `done/failed` 也不关闭订阅。工具被取消时不伪造成功结果。

本轮推荐不重复发送 `user.*`，与 Mate 一致；它们通过 POST 回执与历史观察。其代价是
其他订阅者不会实时收到用户输入，需要历史同步；S3 可选择推送全部已接受用户事件，
届时提交者按 `eventId` 去重，Mate 公共流仍遵守自己的过滤规则。

`session.model.changed`、`session.thinking.changed`、压缩生命周期、工具进度以及
Child Agent 投影尚未在 v2 完整评审。当前 v1 保留，不能因本轮只展示基础示例而删除
这些能力。另一种待选结构是以独立 `event_start/event_delta` 引用目标 `eventId`，
完整事件仍使用上表名称；选择它时再评审预览字段及 thinking 内容策略，不自动照搬
Claude 的字段、ID 或进度信号语义。当前示例仍展示尚未确认的 `type + phase` 方案。

## 5. 顺序、故障与恢复

沿用已确认顺序：先检查依赖再事务写入，完整记录提交成功后才能发布。针对同一 Session，
提交后的发布也必须经过同一有序边界；“先提交再异步发布”本身不足以保证两个发布线程
不颠倒顺序。提交到队列的短步骤保持先后，网络写出在每个订阅自己的调度器中进行，
不在数据库事务内等待网络。具体发布队列和重启后的通知补偿不在本轮冻结。

每个连接独立限事件数和缓冲字节数。preview 可丢弃；完整事件无法入队、单帧超过上限
或传输失败时关闭该订阅，不能静默继续并声称内容完整。限额与最大连接数作为配置，
具体默认值待容量评估；慢订阅者不阻塞 Agent、其他连接或其他 Session。

| 时点 | 候选处理 |
|---|---|
| Header 前 | 使用 operation 中的 400/404/500/503 JSON 错误，只有 `resCode/resMsg` |
| Header 后 | 不更改 HTTP 状态、不发送 ResultBean 或 `stream.error`；关闭当前连接并让客户端历史对账 |
| Agent 执行失败 | 若能够提交完整状态记录，发出 `session.status_idle(reason=failed)`；它不是订阅传输错误 |
| Session 删除 / 服务关闭 | 清理对应订阅；不把连接结束伪装成执行成功，不额外取消其他执行 |

建立订阅与 Session 删除必须协调，避免“先验证存在、后删除、最后注册孤儿订阅”。
当前类图把这项责任放在目标 `SessionEventSubscriptionService`，Controller 不直接完成
可变状态准入。它是 Spring 单例；实际队列/locale 属于每条连接，不能持有其他连接凭据。

断线恢复：先重新注册并等 `connected`，再查询固定快照历史，同时缓冲新 live 内容；
按 `eventId` 合并，历史数组顺序是已提交顺序。不能按 `createdAt` 排序，也不能照搬
Mate 1.4.4 的“最后 createdAt 作为增量下界”：Claw 已确认时间不保证递增，这样可能漏掉
晚到的旧时间事件。可靠增量游标尚待第三接口确认；此前用覆盖所需历史范围的新快照对账，
不自行构造游标，不盲目重放 POST。只读重连可退避重试，404 则停止无意义重连。

![实时订阅候选生命周期](设计图/事件接口重设计/target_session_live_stream_lifecycle.svg)

[PlantUML 源码：`target_session_live_stream_lifecycle`](设计图/事件接口重设计/diagram.puml#L283)

## 6. 证据与差距

以下路径相对实现仓，实际核对提交为 `a8192e047f4061bd385297d3dc6c4358362d0d49`；
与原 `c9d858bc8261bf07f5585f545b53495bf2226a56` 比较，五个文件无变化。

| 已观察符号与路径 | 观察及目标差距 |
|---|---|
| `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/web/RuntimeEventController.java` · `submit/list` | POST 返回 SSE，GET 为历史；没有独立 GET stream |
| `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/web/RuntimeSseEmitterSubscriber.java` · `onEvent/onHeartbeat` | 当前写出 `event:` 及可选 `id:`，心跳注释是 `heartbeat`；data-only 与 connected/ping 是目标差异 |
| `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/RuntimeEventStream.java` · `attach/emit/emitBestEffort/detachInternal` | 单 subscriber，双上限，preview 可舍弃；不能直接当作多订阅者 Session Hub |
| `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/RuntimeEventType.java` · enum | 使用 started/delta/completed、tool.execution、配置/压缩和 stream 控制类型；S2 基础投影尚未实现 |
| `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/RuntimeSseDispatcher.java` · `execute/close` | 每连接独立虚拟线程写出可复用；不证明已有跨执行订阅或持久化重放 |

本次命名核对仍读取上述固定 `a8192e0` 提交的 `RuntimeEventType`，不漂移到实现仓 HEAD。
其中原 `ASSISTANT_MESSAGE_*`、`ASSISTANT_THINKING_*`、`TOOL_EXECUTION_*`、
`TOOL_RESULT`、`SESSION_STATUS_IDLE` 不等于已确认的 v2 类型；后续需在 API 投影层
按业务语义转换，不能把枚举常量原样输出。此次只改设计，没有修改实现代码。

主公共基线 [Claude Managed Agents 事件流文档](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)
在本次核对仍标为 Beta，公开了 best-effort preview、完整事件覆盖、重连后查询历史。
不据此推断服务端表、序号分配或内部调度。已确认的五个 Claw 类型名及候选 `phase`、
GET Header、15 秒保活都是本项目决定或方案，不是 Claude 原样契约；Claude thinking preview 当前只表示
开始、不发送内容，也不能作为本项目“公开摘要已实现”的证据。

Mate 对照是[本地已确认目标设计](../../02-服务与接口/07-mate-service通用对话API/README.md)
§5，不是 Mate 服务端实现。本轮不修改 Mate 文档；其时间排序与 Claw 决策的差异保留为
后续 bridge 对账议题，不能静默混同。

## 7. 待确认与实施验收

五个基础类型名已确认，不再列为待选。当前四项：S1 data-only 或具名 SSE；
S2 `type + phase` 或独立预览事件；S3 是否推送 `user.*`；S4 GET 是否要求
`access-token`。具体字段与其余生命周期细节同属候选，尚未确认整个 GET。

确认后实施切片：订阅 Service 与注册/关闭骨架 → Session Hub 与每连接有界队列 →
类型投影与不可变响应 VO → 有序发布及历史对账。Controller 不返回内部 DTO，不直连 Mapper。
优先补齐缺失的 Tool Call 与 idle 完整记录，不能仅改 SSE 输出就宣称可由历史恢复。

目标验收覆盖：首次注册与 POST 并发、注册与删除竞态、多连接隔离、跨两次执行、空闲
保活、同 ID preview/completed 替换、旧时间晚提交、发布线程乱序、超大完整帧、慢连接
溢出、GET 不覆盖执行凭据、断线后历史对账且不重复 POST、404 停止重连、工具确认与
取消闭环。上述是尚未实施的运行时测试；本次只校验设计模型、HTML 与生成图。

## 8. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.1 | 2026-09-04 | 按用户指定确认五个基础类型名，同步全部候选示例及流/历史同名约束；S2 仅继续评审增量结构，不保留会重新开放旧名称的选项；phase、字段和 GET 整体仍未确认。 |
| 0.1.0 | 2026-09-04 | 第一个 POST 确认后启动 GET stream；提供 Header、帧、基础事件、故障与恢复候选，保留四项待确认，记录当前实现差距与 Mate 映射。 |
