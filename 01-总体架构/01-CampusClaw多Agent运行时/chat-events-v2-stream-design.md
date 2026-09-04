# Session 实时订阅接口设计

| 属性 | 值 |
|---|---|
| 文档版本 | 0.1.2 |
| 状态 | 第二个接口评审中；五个基础类型名与 S1～S4 已确认，其余细节仍为候选，target-only |
| 前置决策 | POST 已确认；`eventId`、不公开内部序号、Session 因果顺序继续生效 |
| 设计仓本次变更前基线 | `e45f374`；首次候选基线为 `463d55c` |
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
五个基础类型名及以下四项已确认；其他字段不因渲染、校验或提交而视为确认。

### 1.1 本轮已确认的四项决定

| 评审项 | 已确认目标 | 分类与理由 |
|---|---|---|
| S1 · A-data-only | 业务帧只用 `data: JSON`，类型放在 JSON 内，不输出 SSE `event:` 或 `id:`，不使用 `Last-Event-ID` 恢复 | 架构变更：与 Mate 使用相同分派方式，不重复维护两处类型信息 |
| S2 · A-type-and-phase | 正文和思考使用 `phase=delta/completed`；工具调用、工具结果及 idle 为完整事件，不采用独立 `event_start/event_delta` | 架构变更：业务类型与生成阶段分开，减少 Mate 转换；具体字段仍待评审 |
| S3 · A-user-events-receipt-history-only | 实时流不推送 `user.*`，用户事件从 POST 回执及历史获得 | 产品约束：不重复通知提交者；其他订阅者需查询历史才能看到用户输入 |
| S4 · A-no-read-tool-token | GET 不要求 `access-token`，不更新执行凭据；保留 `X-HW-ID` 与 JWT/APPKEY 上下文，POST 三种事件仍必填 | 产品约束与安全加固：只读订阅不调用工具，不把工具令牌复制进订阅对象 |

本轮只确认上述选择，不确认整个 GET。对应选项已从表单移除，精确选择保存在
operation 的 `review.confirmedChoices`；当前仍停留在第二个接口。

## 2. 请求与凭据（S4 已确认，其余新细节待评审）

- Path `sessionId` 沿用共享 ID 规则；必须存在且未删除。
- JWT 与 APPKEY 沿用已确认的具体非生产示例值，以及 `X-HW-ID` 的用户凭据 ID 语义。
  GET 中这些 Header 只属于订阅请求上下文，不复制到 Subscription、事件、日志或
  Agent 执行对象，不调用 Mate tool execute。框架可能仍持有原始请求对象，不承诺
  应用能够在 Header 读取后立即擦除框架内存。
- 上游负责真实性与访问授权；Claw 仍不自行解析或校验 JWT/APPKEY，不新增本地 401
  或凭据互斥规则。这是既有内部服务信任边界，不意味着浏览器可以绕过 Mate 直连。
- S4 已确认 GET 不要求 `access-token`；即使提供也不复制到订阅或交给 Agent，
  不更新执行凭据。POST 的三种用户事件仍统一必填，不重新开放该决定。
- 无请求体、无 query；携带正文、query 或 `Last-Event-ID` 候选返回
  `400 INVALID_EVENT_STREAM_REQUEST`，避免调用方误以为支持恢复。
- `Accept-Language` 沿用 `zh-CN/en-US`，缺失或不支持时为 `en-US`，只决定错误文案。
  它不改变已持久化文本或模型输出语言。兼容带自定义 Header 的服务端 HTTP/SSE 客户端；
  不要求浏览器使用原生 EventSource 直连 Claw。

## 3. 连接和帧（S1 已确认，连接细节仍为候选）

以下订阅就绪流程仍为候选：先注册到正确 Session，再发送 Header 和第一条 `: connected` 注释。
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

S1 已确认业务帧只用 `data:` JSON，不输出 SSE `event:` 或 `id:`，不使用
`Last-Event-ID` 恢复，不把业务 `eventId` 冒充恢复游标。当前示例每帧一行 JSON，
以空行结束；文本中的换行按 JSON 转义，不分拆为额外的业务帧。
首次连接不补发历史、不合成 idle；候选无事件时每 15 秒保活一次，间隔可由服务端配置，
部署时与代理超时协调。Heartbeat 不是事件，不持久化，不带 ID 或时间。

## 4. 已确认类型、阶段结构与候选字段

2026-09-04 用户明确指定下表五个基础类型名。名称属于已确认的目标 API 产品约束：
Agent 消息、思考、工具调用与结果统一使用 `agent.*`，前四项与 Mate 同名；状态保留
Claw 的 Session 资源身份，使用 `session.status_idle`。完整事件在流和历史中使用
同名，不提供旧候选名称的兼容别名；这不改动 v1 迁移基线或 Runtime 内部枚举。

S2 已确认沿用 Mate 的 `type + phase` 结构：`agent.message` 和 `agent.thinking`
以 `delta/completed` 区分新增片段与完整内容；工具调用、工具结果和 idle 是完整事件，
不增加 `phase`。下表其他字段约束、thinking 内容策略仍是候选，整个 GET 尚未确认。
本表不是完整的 Runtime 事件清单，不能据此删除其他事件能力。

| Claw 已确认 `type` | Mate 已确认 `type` | 类型与 phase 已确认，其余字段及历史细节候选 |
|---|---|---|
| `agent.message` | `agent.message` | `eventId/type/phase/content`；只有 `completed` 带 `createdAt` 并进入权威历史 |
| `agent.thinking` | `agent.thinking` | 同上；只在 thinking 启用且有可公开摘要时输出，不转发原始推理 |
| `agent.tool_call` | `agent.tool_call` | `eventId/type/createdAt/toolCallId/toolName/arguments/requiresConfirmation`；完整事件 |
| `agent.tool_result` | `agent.tool_result` | `eventId/type/createdAt/toolCallId/content/isError`；失败时可有稳定 `errorCode`；完整事件 |
| `session.status_idle` | `chat.status_idle` | `eventId/type/createdAt/reason`；完整事件，reason 候选为 `done/terminated/failed/confirming` |

在已确认类型、`phase` 和已有事件身份/排序规则之上的字段候选约束：

- `eventId` 是服务端逻辑事件身份，不是帧序号或执行 ID。同一正文/摘要的 delta 与
  completed 复用该 ID；completed 后不再发送该事件的 delta。具体 ID 正则不在本轮
  从 Mate 自动继承。
- `phase=delta/completed` 已确认；`content` 暂按字符串展示。delta 是新追加的非空片段，
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

S3 已确认实时流不推送 `user.*`，与 Mate 一致；它们通过 POST 回执与历史观察。
其他订阅者不会实时收到用户输入，需要历史同步。这不是不接受或不保存用户事件；
第一接口仍接受并持久化三种用户事件，历史仍是完整事件的恢复依据。

`session.model.changed`、`session.thinking.changed`、压缩生命周期、工具进度以及
Child Agent 投影尚未在 v2 完整评审。当前 v1 保留，不能因本轮只展示基础示例而删除
这些能力。独立 `event_start/event_delta` 结构不再作为待选；当前使用已确认的
`type + phase`，不自动照搬 Claude 的字段、ID 或 thinking 进度信号语义。

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

命名核对读取上述固定 `a8192e0` 提交的 `RuntimeEventType`；本轮补充核对同一提交的
`RuntimeEventController` 和 `RuntimeSseEmitterSubscriber`，不漂移到实现仓 HEAD。
其中原 `ASSISTANT_MESSAGE_*`、`ASSISTANT_THINKING_*`、`TOOL_EXECUTION_*`、
`TOOL_RESULT`、`SESSION_STATUS_IDLE` 不等于已确认的 v2 类型；后续需在 API 投影层
按业务语义转换，不能把枚举常量原样输出。此次只改设计，没有修改实现代码。

主公共基线 [Claude Managed Agents 事件流文档](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)
在本次核对仍标为 Beta，公开了 best-effort preview、完整事件覆盖、重连后查询历史。
不据此推断服务端表、序号分配或内部调度。已确认的类型名、`type + phase`、S1/S3/S4
及候选 15 秒保活属于本项目决定或方案，不是 Claude 原样契约；Claude thinking preview 当前只表示
开始、不发送内容，也不能作为本项目“公开摘要已实现”的证据。

Mate 对照是[本地已确认目标设计](../../02-服务与接口/07-mate-service通用对话API/README.md)
§5，不是 Mate 服务端实现。本轮不修改 Mate 文档；其时间排序与 Claw 决策的差异保留为
后续 bridge 对账议题，不能静默混同。

## 7. 待确认与实施验收

五个基础类型名及 S1～S4 均已确认，不再列为待选。剩余评审范围为具体事件字段约束、
thinking 内容、idle `reason`、connected/ping、容量与错误细节，以及 GET 整体确认。
当前示例保留这些待评审细节，不能把四项选择扩大为所有字段已确认；已有的事件身份、
内部顺序、POST 接受行为及凭据安全边界继续生效，不重新征求选择。

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
| 0.1.2 | 2026-09-04 | 确认 S1 data-only、S2 type + phase、S3 用户事件只走回执/历史、S4 GET 不要求 access-token；移除四项选择题并记录精确选择，保留其余字段与 GET 整体评审状态。 |
| 0.1.1 | 2026-09-04 | 按用户指定确认五个基础类型名，同步全部候选示例及流/历史同名约束；S2 仅继续评审增量结构，不保留会重新开放旧名称的选项；phase、字段和 GET 整体仍未确认。 |
| 0.1.0 | 2026-09-04 | 第一个 POST 确认后启动 GET stream；提供 Header、帧、基础事件、故障与恢复候选，保留四项待确认，记录当前实现差距与 Mate 映射。 |
