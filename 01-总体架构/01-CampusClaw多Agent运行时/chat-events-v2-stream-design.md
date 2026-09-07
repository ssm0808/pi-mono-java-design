# POST Events 请求级 SSE 设计

| 属性 | 值 |
|---|---|
| 文档版本 | 0.4.4 |
| 状态 | 合并方向、完整 user.* 首帧、对应 idle 关闭（含等待工具确认）、中断推送分工、数据库中断机制、单消息准入及中断查询优化已确认；数据库细节、其余并发竞态、字段与错误细节候选，target-only |
| 设计仓本次变更前基线 | `c16ed3f904a85d01d69deb1a3575e2c52cdaa958` |
| L5 字段确认前设计仓基线 | `7349cdf2e037700ddf4917eebef0e19799252f47`；只同步目标字段决定，未重新核对实现 |
| L6 字段确认前设计仓基线 | `050bda2579004b630021300986881ac61ba7142e`；只同步目标字段决定，未重新核对实现 |
| L7 字段确认前设计仓基线 | `019b2dbfbc85edb23d94ffbda7b4963237286f7e`；Mate 返回链路补充核对见历史查询 §2.1 |
| 本次实现核对 | `pi-mono-java@918005ee8ccc88d179fc31a0de17a92b4a01383b` |
| M7 补充源码核对 | `dfb90cac4e233e09a0b8f047f7e9f4682f5ad238`；五个并发、流与配置文件相对 `918005e` 无变化，路径与符号见总体设计 §4.4 |
| 原实现基线 | `a8192e047f4061bd385297d3dc6c4358362d0d49`；复核文件与差距见 §6 |
| Mate 契约对照 | 通用对话 Events 1.4.4，已确认目标契约，不是实现证据；本轮不修改 |
| 外部参考核对 | Claude Managed Agents 官方事件流与 List Events，2026-09-04，Beta |
| 更新日期 | 2026-09-07 |

## 1. 当前操作与已确认范围

```http
POST /campusclaw-service/v1/sessions/{sessionId}/events
Content-Type: application/json
Accept: text/event-stream
X-HW-ID: credential-jwt
Authorization: Bearer opaque-token
access-token: opaque-access-token
```

一次 POST 发送一条用户事件，在同一响应中接收对应 SSE，不再先开 GET 再 POST。
原独立 `GET /sessions/{sessionId}/events/stream` 已撤销；普通
`GET /sessions/{sessionId}/events` 历史查询保留，不合并进写请求。
当前模型为 [合并 POST](接口契约-v2/操作/01-submit-session-event.json)，
[POST 保留评审页](chat-api-review.html#submitSessionEvent) 定位统一页面中的 POST 操作。
用户已明确要求开始修改历史查询，[当前评审页](chat-api-review.html#listSessionEvents) 因此切换为
ListEvents；POST 已确认决定和未决项仍保留，不视为整体通过。

已确认：三类输入、event 包装、content[]、Header 语义与具体测试示例、三类统一携带
access-token、eventId、不公开内部序号、内部因果顺序、无幂等键且历史对账，均继续有效。
S1 data-only、S2 type + phase 与五个输出类型名也继续有效。

M6 单消息准入已确认：同一 Session 的 M1 未完成前，拒绝任何调用方提交的 M2，
不将 M2 排队或写入已接受事件历史。接受 user.message 时，在数据库短事务中锁定
Session、复核 idle、追加消息并改为 running，提交后才启动执行和输出回执。
具体数据库证据与接受/释放边界见 [总体设计 §3.2](chat-events-v2-design.md#32-已确认一个-session-同时只处理一条用户消息)。

用户进一步明确允许首个业务帧返回本次提交的完整 `user.*` 事件，含 eventId；
它只向本次 POST 回执一次，后续才推送对应 Agent/Session 事件，不广播其他用户输入。
这取代原 S3 的“流内完全不出现 user.*”。原 Q3 的完整回执内容保留，普通 JSON
ResultBean 外壳不再使用；S4 的只读 GET 无工具令牌规则不适用于合并 POST。

用户已确认 M3 结束规则：收到本次对应的 `session.status_idle` 后关闭本条响应；
等待工具确认时也关闭，之后通过新的确认 POST 接收续跑结果。这是已确认目标设计的
产品约束，不代表当前 Java 已实现，也不表示整个操作或具体 reason 取值已确认。

## 2. 请求与凭据边界

- 请求体仍是一条三种联合类型之一的 event：user.message、user.interrupt、
  user.tool_confirmation。完整约束与三种示例由 operation model 维护。
- 两种 Header 模式都必须带 access-token；保留 X-HW-ID 的用户凭据 ID 语义、
  JWT/AppKey 不在 Claw 内校验的既有信任边界，不增加本地 401 或互斥规则。
- 原始凭据只进入本次执行所需的内存对象，仅随实际 Mate tool execute 发送。
  响应队列、路由索引、事件、历史、模型请求和日志不得保存它们。
- 网络断开不等于 Agent 执行结束。未完成执行不能因 HTTP 关闭就丢失凭据，也不能把
  中断请求携带的凭据覆盖到正在运行的原执行。确认续跑具体采用哪个执行凭据对象
  留在所属 Handler/Runtime 实施中明确，不借合并扩大凭据发送范围。
- 使用支持 POST 流式读取的服务端 HTTP 客户端或 fetch。SSE 是响应格式，
  原生 EventSource 不是 POST 的发送方式；Mate 仍是面向浏览器的公共边界。
- 不提供 Last-Event-ID 恢复，不以 eventId 冒充游标；参数拒绝与容量细节仍待评审。

## 3. 帧结构与成功含义

完整用户事件提交成功后，首个业务帧返回该事件，然后才投递该请求对应的执行输出。
允许在无业务数据时有心跳注释，但不能让 Agent delta 或其他事件越过回执。
服务端需在接受前预留流缓冲并固定目标，提交后先排入本次回执，再向这条响应投递后续
输出。跨实例中断不要求执行实例等待接收实例写回执：终态持久化供后者补读，接收方
保持本条响应的回执先行。网络写出在事务外，不为等客户端收完首帧而锁住 Session。

下面首帧与收到对应 idle 后关闭已确认，其他输出字段仍为候选：

```text
Content-Type: text/event-stream
Cache-Control: no-store

data: {"eventId":"b7ef45d40a854c33af7a36df871a21e8","type":"user.message","createdAt":"2026-09-03T08:30:15.123Z","content":[{"type":"text","text":"请分析东区园区的异常告警。"}]}

data: {"eventId":"d5c19f7c4b1642e6806aeb860752d99b","type":"agent.message","phase":"delta","content":"正在整理告警信息，"}

data: {"eventId":"d5c19f7c4b1642e6806aeb860752d99b","type":"agent.message","phase":"completed","createdAt":"2026-09-04T08:30:19.451Z","content":"已整理告警信息，建议先核查上联链路。"}

data: {"eventId":"d4e3e8b9653047a99ac10396a17fe84d","type":"session.status_idle","createdAt":"2026-09-04T08:30:20.000Z","reason":"done"}

```

示例为独立精简请求的回执；精确的附件请求与响应配对以 operation model 为准。
每帧是单行 JSON 加空行，JSON 内换行必须转义。没有 SSE event/id 字段，不包装 ResultBean。
200 表示已进入接受后的流式响应，不是任务成功；完整首帧是持久化接收凭据，不是执行终态。

## 4. 已确认关闭与中断分工，待定绑定细节

结束规则已确认：收到本次对应 idle 后关闭响应，等待工具确认时也关闭；不等待下一条
用户消息。仅结束本次 HTTP 交互，等待确认不代表任务成功。之后新发确认 POST，
由新响应接收工具结果与续跑；不把新结果发给已经关闭的旧响应。

M4 中断推送分工已确认：原消息响应保留原执行输出；中断响应只返回本次完整回执，
随后等待同一个目标实际停止的 idle，不复制正文、思考或工具输出。两条仍连接的响应
接收同一条 idle，复用同一 eventId，然后各自关闭。回执仅表示中断已接受。

M6 下，M1 等待工具确认或停止尚未完成时资源仍为 running，拒绝新 user.message。
等待确认时发送的 session.status_idle 只结束本次 HTTP 交互，不把数据库状态改为 idle；
只有 M1 真正完成或实际停止并提交可靠结束状态后，才允许下一条消息。
user.interrupt 和 user.tool_confirmation 各按控制条件接受，不使用新消息的 idle 前置条件。

M5 数据库中断机制也已确认：停止请求与 user.interrupt 同事务保存，并绑定不可复用的
内部执行身份；各实例批量检查本机活动执行并发起本地取消，接收实例检查对应权威终态。
不得把任意 Session idle 当作本次终态。数据库字段、检查周期、并发竞争、reason 具体值
和停止失败细节仍待评审。

| 本次输入 | 本条响应的绑定范围（候选） | 对应 idle 的触发与 reason 示例（候选） |
|---|---|---|
| user.message | M1 未完成前拒绝 M2 已确认；本条流对应 M1 的执行段，包括模型、工具与该段状态 | 对应 done/failed/terminated，或进入 confirming；确认等待仍保留 running |
| user.tool_confirmation | 当前 Session 中指定 toolCallId 的有效待确认操作及由本次确认触发的续跑段 | 对应 done/failed/terminated，或再次进入 confirming |
| user.interrupt | 首帧后只等待目标停止结果、不复制 Agent 输出已确认；接受时必须在数据库事务中固定内部执行身份；等待确认等状态准入细节仍候选 | 实际停止后的 terminated；停止失败路径另评审，不能提前伪造终态 |

设计理由：本次交互结束就关闭其 HTTP 响应，不跨下一次无关执行。等待工具确认需要
用户新动作，以另一次确认 POST 开始下一段交互，避免旧响应无限等待用户操作。
`confirming` 只是该状态的候选 reason 字面值，确认关闭策略不等于确认这个字段取值。

中断与原消息流可以同时存在。已确认在数据库接受事务中绑定原执行身份，保存停止请求；
执行方发现后触发本地取消。原流已断开则通过历史对账，不能改绑下一轮执行。
M1 完成后 M2 才能开始。跨这个完成边界的迟到中断、已接受后自然完成、确认与中断竞争
等具体响应细节仍待评审；前述 targetEventId 建议未进入请求，超时响应规则也尚未确认。

跨实例停止请求、数据库事务、批量检查、M7 本地通知与等待去重，以及容量和故障边界，
只在[总体设计 §4.4](chat-events-v2-design.md#44-已确认数据库停止请求与实例批量检查)维护。
本流只消费该机制产生的已提交目标终态，并遵守首帧先行、终态去重与慢连接隔离。
超时或实例失联不能伪造 idle；不把 ListEvents 当作内部通知通道。

不增加公共 runId/executionId；内部绑定对象和请求生命周期不穿透 HTTP。
多工具确认、配置/压缩与子 Agent 投影另行评审。独立 abort、steers、follow-ups 已明确退役；
停止经 user.interrupt，调整方向在实际停止后新提交。FollowUp 本期不启用，
仅保留 [未来扩展设计](chat-follow-up-future-design.md)，不放宽单消息准入或增加公共字段。

### 4.1 输出类型与字段状态

| 已确认 type | 已确认阶段规则 | 字段 / 行为及确认范围 |
|---|---|---|
| user.* 首帧 | 不带 phase，仅本次完整回执 | eventId/type/createdAt 及对应已确认业务字段；完整内容已确认 |
| agent.message | phase=delta/completed | completed 的 content 为完整正文字符串已确认（L5）；delta 字段、createdAt 等其余细节仍保留候选状态；同 ID 完整内容替换 preview |
| agent.thinking | phase=delta/completed | 仅启用且有可公开摘要时输出，不泄露原始推理；具体内容策略待评审 |
| agent.tool_call | 无 phase 的完整事件 | arguments 的 JSON 对象结构已确认（L6）；eventId/type/createdAt/toolCallId/toolName/requiresConfirmation 保留各自原有状态 |
| agent.tool_result | 无 phase 的完整事件 | content 数组且仅包含 text 块已确认（L7/L8）；eventId/type/createdAt/toolCallId/isError 及失败 errorCode 保留各自原有状态 |
| session.status_idle | 无 phase 的完整事件 | eventId/type/createdAt/reason；reason=done/terminated/failed/confirming 仍候选 |

2026-09-07 用户在 ListEvents 选择 `L5-agent-message-content=A-string`。
按完整事件同形规则，本 POST 的 `agent.message` completed 帧同步确认 `content` 字符串；
设计理由和剩余字段范围见[历史查询 §2](chat-events-v2-history-design.md#2-历史返回什么)。
本轮不改变示例值、delta 设计、图中关系或两个接口的整体待评审状态。
同日用户选择 `L6-tool-call-arguments=A-object`，本 POST 同步确认完整工具调用事件的
`arguments` JSON 对象；原因和工具结果内容结构的下一步评审仍由历史查询 §2 维护。
2026-09-08 用户选择 `L7-tool-result-content=A-content-blocks`，本 POST 同步将完整工具
结果的 content 改为数组，现有文本包装为一个 text 块。用户随后明确本期工具只返回文本（L8），
不增加 JSON 块或图片块。Mate 的文本返回与源码边界见[历史查询 §2.1](chat-events-v2-history-design.md#21-mate-工具的文本返回与源码边界)；
工具名称/参数投影、空文本及错误细节仍待评审。

完整事件在 SSE 与 ListEvents 同名同形；落盘范围仍须配合历史接口确认，
不能假定当前 Java 已保存 Tool Call 或 idle。preview 不持久化、不补发；同一 eventId
出现 completed 后不再发送 delta。背压丢弃某个 preview 后，该连接停止此 ID 后续 delta，
等待完整内容覆盖，避免把缺片段的拼接结果显示为完整答案。工具参数、结果不泄露凭据、
堆栈或不允许公开的内部数据，Mate 还需进行公共安全投影。

## 5. 失败、背压与恢复候选

| 时点 | 推荐处理，尚待完整评审 |
|---|---|
| 确认尚未接受、SSE Header 前 | 400/404/409/503 或确认回滚后的 500 JSON，仅 resCode/resMsg |
| 已经接受但启动/续跑失败 | 不再宣称“未接受”；能可靠记录失败终态时推送对应 failed，否则断开并历史对账 |
| SSE Header 后发生编码/网络/队列故障 | 不改 HTTP 状态，不拼接 JSON 错误外壳；关闭本条响应，未收到终态视为结果不确定 |
| 已接受执行发生业务失败 | 候选发送已提交的 session.status_idle(reason=failed)，再结束响应 |
| 客户端断开 | 仅解绑本次输出，不取消执行、不重发 POST；后台继续持久化 |

客户端只有收到本次绑定的明确结束事件才可判断本次交互结束；单纯 EOF、HTTP 200、
网络错误或超时都不代表成功。不恢复旧 GET 重连机制，不自动重放任何 mutating POST。
主动取消业务仍须发送 user.interrupt，而不是关闭读取器。

每条 POST 响应按事件数和字节数限缓冲，preview 可舍弃；完整事件无法入队或单帧超限
则关闭该响应。网络写出不在 Session 事务内等待，慢连接不阻塞执行或中断接受。
首帧保留顺序和容量需在接受前校验；持久化成功后若网络发送失败属于结果不确定。
心跳建议 `: ping`，空闲间隔由服务端配置（15 秒仅候选）；不再需要 connected 就绪
握手，因为没有独立读流。所有容量、默认值、超时细节继续待评审。

断线后使用 GET ListEvents 普通整数分页查询完整记录，按 eventId 去重，保持响应数组顺序。
仍在执行时可以后续补读或重新加载；没有可靠终态证据就不能标为完成。未收到首帧时，没有
幂等键或客户端相关 ID，就可能无法唯一判定同文请求是否已接受；保留草稿并提示不确定，
不能凭相同文本猜测后重发。已确认的普通分页边界、完整帧同形和对账细节见
[ListEvents 设计](chat-events-v2-history-design.md)。原消息与中断响应共用的 idle 在历史
仅一条；历史页读完、旧 idle 或确认等待的 idle 都不是当前资源可接受 M2 的凭据。
分页大小、结果元数据与空页规则只在历史专题维护；执行关联及 Mate 展示细节仍需确认。
时间允许回退，不用最后 createdAt 作下界，也不自行构造内部序号。

![请求级 SSE 生命周期：关闭及中断推送分工已确认，数据库中断机制已确认，参数及竞态细节待评审](设计图/事件接口重设计/target_session_live_stream_lifecycle.svg)

[PlantUML 源码：`target_session_live_stream_lifecycle`](设计图/事件接口重设计/diagram.puml#L208)

## 6. 证据、差距与外部边界

源码为 `918005ee8ccc88d179fc31a0de17a92b4a01383b`，相对原 `a8192e0` 的七个
复核文件均无变化。完整仓库相对路径与符号列在
[总体设计 §4.2](chat-events-v2-design.md#42-本次合并方案源码复核)。

观察到的当前代码：POST SSE / GET 历史、单 subscriber、有界流；正常结束为
session.status.idle + stream.end，失败为 stream.error，随后 complete；断线 detach
不 abort。目标差距：三输入联合请求、v2 完整首帧、data-only、type + phase、
eventId、不公开序号、请求控制绑定与已确认的对应 idle 关闭都还需要改造。

[Claude Managed Agents 事件流](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)
及 [List Events](https://platform.claude.com/docs/en/api/beta/sessions/events/list)
于 2026-09-04 重新核对，接口仍需 beta header。它们提供独立读取流、best-effort preview
与持久化历史，可证明公开行为，不能证明内部存储或调度。本次 Claw 刻意不沿用其独立
读流，是用户选择的架构差异；只保留 preview 不等于权威记录的参考边界。

Mate 通用对话 API 1.4.4 是本地目标契约，不是已运行后端证据。Claw 内部合并不自动改变
Mate 公共路径、身份映射、读取流或用户授权。桥接方案需后续独立同步，不字节透明转发。

## 7. 实施验收与待确认

已确认项不再展示选项。待确认：数据库控制字段与约束、实测索引选型、检查周期及超时，确认续跑与控制竞争；
idle reason、具体字段和 thinking 内容；Header 后错误、保活、容量；合并接口整体确认。
对应 idle 关闭、等待工具确认分段、中断推送分工、数据库中断机制、单消息准入及中断查询优化已确认，不重复询问。用户已明确推进 ListEvents，POST 剩余问题仍保留待评审，不据此整体通过。

实施验收需覆盖：原响应保留执行输出，中断响应只含回执与同一停止 idle，终态 eventId 一致；
三输入首帧与请求内容一致且只一次；提交前绑定/回执先行；极快完成；
确认续跑和中断目标竞态；同 Session 下一次执行隔离；断线与慢连接不影响执行；
失败/确认等待不能被误判成功；无首帧结果不确定；旧时间晚写与有序历史。
数据库中断、单消息准入与 M7 的完整实施验收统一见[总体设计 §5](chat-events-v2-design.md#5-实施切片与验收)，
本节不重复维护调度与数据库检查清单。
本轮仅改设计，未运行尚未实现的 v2 Runtime 集成测试。

## 8. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.4.4 | 2026-09-08 | 同步 L7/L8：agent.tool_result.content 使用仅含 text 块的数组；Mate 返回链路与待决工具身份投影由历史专题维护，其他字段及 POST 整体仍待评审，PlantUML 不变。 |
| 0.4.3 | 2026-09-07 | 同步 L6：agent.tool_call.arguments 使用 JSON 对象；其他工具字段、结果与整个 POST 仍待评审，源码证据及 PlantUML 不变。 |
| 0.4.2 | 2026-09-07 | 同步 L5：agent.message completed 的 content 使用完整正文字符串；其余字段、错误和整个 POST 仍待评审，源码证据及 PlantUML 不变。 |
| 0.4.1 | 2026-09-07 | 删除数据库中断机制与验收的重复副本，改引总体设计；历史参数引用 ListEvents，流响应与确认范围不变。 |
| 0.4.0 | 2026-09-07 | 同步三个独立控制接口退役与 FollowUp 暂不启用；本期仍仅三输入且拒绝执行中的下一条消息，输出和未决项不变。 |
| 0.3.6 | 2026-09-07 | 历史补读同步 L4 合法超范围空成功；空页不证明执行结束或 POST 未接受，POST 报文和确认状态不变。 |
| 0.3.5 | 2026-09-06 | 历史补读同步默认 50/上限 200 与无 total 决定；POST 报文、结束规则和确认状态不变。 |
| 0.3.4 | 2026-09-06 | 历史对账同步普通整数分页、取消固定快照决定；POST 报文、结束规则和确认状态不变。 |
| 0.3.3 | 2026-09-06 | 当前评审切换至 ListEvents；POST 保留独立页面和未决项，链接完整事件同形、固定快照与断线对账候选，不变更 POST 报文或确认状态。 |
| 0.3.2 | 2026-09-05 | 确认 M7：同实例提交后通知、固定执行目标的等待去重、实测索引选型；补齐登记后补读、每响应终态去重及清理边界。设计基线 `e370d2d`，补充源码 `dfb90ca`；不改变公共报文或冻结数值参数。 |
| 0.3.1 | 2026-09-05 | 确认 M6：M1 未完成前拒绝 M2，消息与 running 状态同事务提交；确认等待的 SSE idle 不释放资源准入，控制事件另行检查。补充目标生命周期与验收；迟到中断和超时仍待评审。 |
| 0.3.0 | 2026-09-04 | 确认 M5 数据库停止请求与实例批量检查；明确 A/B 通过持久化结果交接、首帧投递屏障及固定内部目标，本期不引入 Redis；数据库与故障参数仍待评审。 |
| 0.2.2 | 2026-09-04 | 确认 M4 原消息与中断响应分工、共用同一停止 idle 的 eventId；补充多实例定位问题解释和当前源码链接，更新生命周期图；不选择路由实现或确认其他字段。 |
| 0.2.1 | 2026-09-04 | 记录用户确认 M3：对应 idle 后关闭，等待工具确认时也关闭，新确认 POST 接收续跑。同步状态和生命周期图；精确 reason、并发输出绑定及错误细节仍候选，整个操作仍待评审。 |
| 0.2.0 | 2026-09-04 | 撤销独立 GET stream，合并到 POST SSE，确认完整本次 user.* 首帧；保留 S1/S2、Header、eventId 与排序；三输入绑定和结束规则仍候选，更新源码基线与三图。 |
| 0.1.2 | 2026-09-04 | 确认 S1 data-only、S2 type + phase、S3 用户事件只走回执/历史、S4 GET 不要求 access-token；移除四项选择题并记录精确选择，保留其余字段与 GET 整体评审状态。 |
| 0.1.1 | 2026-09-04 | 按用户指定确认五个基础类型名，同步全部候选示例及流/历史同名约束；S2 仅继续评审增量结构，不保留会重新开放旧名称的选项；phase、字段和 GET 整体仍未确认。 |
| 0.1.0 | 2026-09-04 | 第一个 POST 确认后启动 GET stream；提供 Header、帧、基础事件、故障与恢复候选，保留四项待确认，记录当前实现差距与 Mate 映射。 |
