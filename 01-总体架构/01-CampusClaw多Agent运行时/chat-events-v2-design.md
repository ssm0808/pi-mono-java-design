# CampusClaw Session Events v2 重设计

| 属性 | 值 |
|---|---|
| 文档版本 | 0.3.1 |
| 状态 | POST 合并、完整 user.* 首帧及对应 idle 关闭（含等待工具确认）已确认；输出范围、具体字段与错误细节仍评审，target-only |
| 设计仓基线 | `c4f1ba2f2b8f4ee7cf9b7d5eaa554c42bd525bed` |
| CampusClaw 实现核对提交 | `c9d858bc8261bf07f5585f545b53495bf2226a56` |
| 本次 HTTP 合并核对提交 | `918005ee8ccc88d179fc31a0de17a92b4a01383b`；原 `a8192e0`，变更路径与结论见 §4.2 |
| 事件顺序补充核对提交 | `a8192e047f4061bd385297d3dc6c4358362d0d49`；只补充本文 §4.1 证据，不替换其他主题基线 |
| pi Runtime 固定基线 | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` |
| mate 公共契约基线 | [`mate-service 通用对话 API`](../../02-服务与接口/07-mate-service通用对话API/README.md) 1.4.4 |
| 外部公共契约核对日 | 2026-09-04；仅对照 preview 与权威历史，不照搬独立读取流 |
| 更新日期 | 2026-09-04 |

## 1. 已确认资源模型

2026-09-04 用户明确要求把 POST 提交与 GET 实时推送合并：一次请求发送事件，并在
同一 HTTP 响应中接收对应 SSE。这里合并的是原 GET 实时流，不是 ListEvents 历史查询。

| Method | Path | 职责 | 当前状态 |
|---|---|---|---|
| `POST` | `/campusclaw-service/v1/sessions/{sessionId}/events` | 提交一条用户事件；首帧完整回执，随后推送对应事件 | 合并方向、首帧与对应 idle 关闭已确认；整个操作仍待评审 |
| `GET` | `/campusclaw-service/v1/sessions/{sessionId}/events` | 固定快照权威历史及断线对账 | 职责、身份与顺序已确认；具体字段未完整评审 |

原独立 `GET /sessions/{sessionId}/events/stream` 从 v2 目标中撤销；旧 JSON model
移除，旧方案可从 Git 历史恢复。不增加 `executionId/runId`，不把响应连接变成公共执行
资源。请求级推送也不意味着去掉持久化事件或历史恢复。

这项改变是相对旧三接口提案的架构变更，与当前 Java 的 POST SSE 传输方向一致；
不等于直接恢复 v1 的请求字段、类型名或公开序号。Mate 公共 API 不在本次修改范围，
其三接口形态仍独立成立；将来由 Mate bridge 消费一次 Claw POST 响应并做安全投影，
不能机械删除 Mate 的公共读取流。

`user.interrupt` 和 `user.tool_confirmation` 仍走同一 POST 联合类型。独立 Abort
的替代方向不变；Steer、FollowUp 和 Slash Command 是否并入仍另行评审，当前 v1
迁移基线继续保留。

![Session Events 目标资源模型](设计图/事件接口重设计/target_session_events_resource_model.svg)

[PlantUML 源码：`target_session_events_resource_model`](设计图/事件接口重设计/diagram.puml#L1)

## 2. 当前评审：提交事件并接收对应推送

```http
POST /campusclaw-service/v1/sessions/{sessionId}/events
Content-Type: application/json
Accept: text/event-stream
X-HW-ID: credential-jwt
Authorization: Bearer opaque-token
access-token: opaque-access-token
```

已确认继续有效：

- 每次一条 `user.message`、`user.interrupt` 或 `user.tool_confirmation`；
  使用 `event` 包装、有序 `content[]`，不接受批量。
- `X-HW-ID` 是用户凭据 ID，不是公司、服务或应用标识。两种 Header 示例及说明不回退：
  `credential-jwt`、`credential-appkey`、`Bearer opaque-token`、
  `opaque-appkey`、`opaque-access-token` 都是实现测试中的非生产字面值。
- 三种用户事件在 JWT/APPKEY 模式下均必须携带 `access-token`。Claw 不自行解析或校验
  JWT/APPKEY；真实性和授权由上游负责，允许已有两种凭据同时出现，不新增互斥规则。
- 凭据从 POST 读取，只在内存中保留到本次 Agent 执行结束，只随实际 Mate tool execute
  发送；不发给模型、工具发现，不进入日志、Session 持久化、事件或回执。HTTP 断开不是
  执行结束，也不能因此提前清除仍需执行的凭据。
- 对外使用 `eventId`，不暴露 `entryId/entrySeq/runId/executionId`。
  Claw 与 Mate 的 eventId 是否共值仍待 bridge 评审，字段同名不等于值相同。
- 不接受 `Idempotency-Key`；已提交但响应丢失时通过历史对账，不盲目重放 POST。

### 2.1 本次明确替代与保留的决定

| 原决定 | 合并后的状态 | 原因 / 分类 |
|---|---|---|
| Q3：普通 JSON ResultBean 返回完整用户事件 | JSON 外壳被替代；完整用户事件作为首个 SSE 业务帧返回，已确认 | 架构变更：一次响应承载接收回执与输出 |
| S1：data-only | 保留；不使用 SSE `event:`、`id:` 或 Last-Event-ID 恢复 | 已确认格式不因 HTTP method 改变 |
| S2：type + phase | 保留；正文/思考为 delta/completed，工具与 idle 不带 phase | 已确认投影 |
| S3：流不推送 user.*，仅回执/历史可见 | 用户明确调整：首帧返回本次完整 user.*，仅一次，不广播其他用户输入 | 产品约束：同一请求内确认接收，不重复业务输出 |
| S4：只读 GET 不需要 access-token | 原只读流已撤销，此项不再适用该入口；POST 三类仍必填 | 适用范围改变，不是放宽写入凭据 |
| M3：响应结束规则 | 已确认收到本次对应 idle 后关闭；等待工具确认时也关闭，之后通过新确认 POST 接收续跑结果 | 产品约束：结束本次 HTTP 交互，不把等待确认当作任务成功；具体 reason 与并发归属仍待评审 |
| 原 POST 整体已确认 | 仅被本次替代的响应部分重新评审，其余已确认字段保留 | 不把旧整体确认标签误用于新合并接口 |

完整首帧包括服务端 `eventId`、原事件 `type`、`createdAt` 和规范化业务字段。
它是已经持久化并接受的用户事件，不代表 Agent 已完成或中断已停止；不额外套 ResultBean，
不增加 `phase`。首帧只能来自当前 POST，后续推送必须晚于该回执入队。

五个基础输出类型保留：`agent.message`、`agent.thinking`、`agent.tool_call`、
`agent.tool_result`、`session.status_idle`。完整事件在 SSE 与历史使用相同名称和字段。
这不是全部 Runtime 事件清单，不据此删除配置、压缩、进度或子 Agent 能力。

### 2.2 精确评审入口与未确认范围

- [当前合并 POST 评审页](chat-events-v2-review.html)：
  [唯一 operation model](接口契约-v2/操作/01-submit-session-event.json)。
- [响应生命周期与源码差距](chat-events-v2-stream-design.md)：三种输入各自的输出范围、
  已确认结束规则，以及背压和恢复候选。
- [旧确认页](chat-events-v2-confirmed.html) 只保留变更提示并链接当前页，不再展示已失效
  的普通 JSON POST 为当前已确认接口。
- `common.json.reviewState` 当前为 `submitSessionEvent`，
  `confirmedOperations=[]`；这不撤销已确认字段，只表示新操作尚未整体确认。

结束规则已确认：收到本次对应的 `session.status_idle` 后关闭本条响应；等待工具确认
时也关闭，之后通过新的 `user.tool_confirmation` POST 接收续跑结果。关闭的是本次
HTTP 交互，不代表任务成功；不相关的 Session idle 不能结束本次响应。
三类请求的精确绑定范围、并发中断与原流终态投递、`reason` 的具体取值及错误细节仍为
候选。本次仅确认关闭策略，不整体确认合并接口或提前确认输出字段。

## 3. 目标分层与生命周期

![Session Events 目标类图](设计图/事件接口重设计/target_session_events_classes.svg)

[PlantUML 源码：`target_session_events_classes`](设计图/事件接口重设计/diagram.puml#L81)

推荐骨架保留 Web、Application、Runtime、流式输出、持久化边界，不保留长期 Session
订阅 Hub：

- Controller 验证 Request VO，交给 Service，使用只读 Response VO 编码 SSE；
  DTO/Mapper 不越过 Service 暴露到 HTTP。
- Service 固定解析结构、对象身份和 locale，使用 Handler Registry 分派三类用户事件。
  可变 Session/Tool 状态、容量与执行目标在所属事务或 Session 协调边界内复核。
- 每个 POST 有独立有界 `RequestEventStream`；候选 `RequestEventRouter` 只按内部绑定
  的执行段或中断目标投递，不按“当前 Session 最新执行”动态猜测归属。
  Controller 不持有或遍历全局 Session 订阅。
- 接受前预留响应队列，在同一协调边界绑定目标；用户事件提交后先排入完整回执，再允许
  执行/续跑/中断产生可投递输出。网络写出不占数据库锁。目标提前结束时在接受前拒绝，
  不能接受后空等一个已经错过的 idle。
- Application 层按执行管理 Projector 订阅，不让 Runtime 内核拥有 HTTP 投影器。
  Projector 与用户 Handler 共用有序追加边界；完整事件提交后有序发布，
  preview 只 best-effort 发布。HTTP 关闭只解绑该响应，不取消已接受执行。
- 中断可与原消息响应同时存在，但不新增公共订阅接口；两条响应的终态绑定与去重仍为
  候选，详见生命周期文档。Spring 单例 Router 不持有请求原始凭据。

历史第一页固定水位、过滤条件和分页方向；后续 opaque page 绑定同一快照。
请求级 SSE 不重放。断线、队列溢出或接收结果不确定都回到 ListEvents 对账；时间不能作
增量游标，不把重新 POST 当作重连。

### 3.1 已确认的事件处理、写入与展示顺序

本节是已确认的 v2 目标要求，属于架构变更，不表示当前实现已完整支持多来源事件的
依赖检查。“顺序正确”指保持业务因果关系，不是按机器时钟还原所有事件的物理发生顺序。
例如：用户消息先于由它触发的模型工具调用，工具调用记录先于对应工具结果，工具结果
先于依赖该结果的模型最终回答。这里没有新增公共事件类型或字段。

1. 同一 Session 的权威事件先经过统一的接受边界，检查来源顺序和前置事件依赖，再确定
   写入顺序。不能让不同工作线程各自抢数据库锁，把抢锁先后当作业务先后。
2. 按已确定的顺序，在同一个短事务内完成可变状态与依赖复核、内部序号分配及记录追加。
   同一 Session 的追加锁保持到提交；前置事件未提交或写入失败时，依赖它的事件不得先
   进入权威历史。不能先独立领号、再交给异步线程任意提交。串行范围不包括模型生成、
   工具执行或等待缺失的前置事件，这些耗时操作不占用数据库事务。
3. 无依赖的并发事件不存在唯一的业务先后，以该 Session 统一接受顺序为准。上游已发生
   乱序时，按来源顺序或显式依赖等待、校验；缺少足够信息就不能宣称恢复了因果顺序，
   更不能用时间戳或随机 `eventId` 猜测。缓冲上限、超时和失败处置属于后续实施细节。
4. ListEvents 只读取已提交的权威记录，按内部顺序返回；过滤后的结果保留相对顺序，
   客户端按响应数组顺序展示，不按 `createdAt` 或 `eventId` 重新排序。`createdAt`
   只用于时间展示，允许相同或不递增；本次不改其取值语义、示例或精度约定，也不新增
   数据库插入时间字段。对外继续使用 `eventId`，不公开 `entryId/entrySeq`。
5. 已确认的固定快照历史只纳入对应水位内已提交的记录，不让后来提交的事件插入已经
   翻过的页面。此处明确排序和提交约束，不提前确认 ListEvents 的过滤、游标字段、分页
   方向选项或保留期，也不确认 live SSE 的详细事件契约。

推荐目标类图用 `SessionEventAppender` 表示共享的接受与有序追加职责：三个用户事件
Handler 和 Runtime Projector 都经过该边界，再由 Repository 执行短事务。该类名及具体
调度机制是 target-only 落地建议；确认的是共同顺序约束，而不是必须增加某种队列。
它是 Spring 单例协作者，但协调状态按 Session 隔离；多实例场景仍须在持久化事务中
复核依赖和状态，不能只依赖某个 JVM 内的互斥锁。查询不经过该写入边界，不等待模型
或工具执行完成。

## 4. 源码证据与差距

| 分类 | 源码证据 | 结论 |
|---|---|---|
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java:39-91` · `RuntimeEventController.submit/list` | POST 创建 `SseEmitter` 并返回 `text/event-stream`；GET 只接收 `limit/page` |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeRequestContext.java:45-50` · `mateCredentials`；`campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/common/client/mate/MateCredentials.java:21-74` | 当前实现把 `X-HW-ID` 作为不透明 Header 值读入执行凭据，只检查非空，不解析其业务身份 |
| 已观察实现 | `campusclaw/src/test/java/com/huawei/hicampus/claw/codingagent/runtimeapi/web/RuntimeSessionRoutesTest.java:69-93` · `createWithJwtReturnsConfirmedResultBean/getWithAppKeyReturnsEtagAndNoStore`；`RuntimeEventRoutesTest.java:88-120,193-197` · `postStreamsNamedEventsWithoutResultBean/authenticated` | 当前测试使用 `credential-jwt`、`credential-appkey`、`Bearer opaque-token`、`opaque-appkey` 和 `opaque-access-token` 等非生产字面值；本设计复用它们作为具体示例，但不据此增加格式约束 |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventService.java:76-139` · `submit/prepareAndSubmit/acceptUserEntry` | 只接受 `user.message`，要求 idle，持久化后直接启动内部执行并返回其 EventStream |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventStream.java:22-159` · `attach/detachInternal` | EventStream 属于一次执行且最多一个 subscriber；断线会清空该流缓冲 |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventQueryService.java:53-99` · `list/pageOf` | page 只携带 afterSeq 与 thinking，没有固定历史快照水位 |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionControlService.java:59-132` · `steer/followUp/abort/prepareAbort` | Abort 是独立接口行为；Steer 与 FollowUp 使用执行内队列 |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java:57-120` · `acceptUserEvent/listCurrentBranch` | `user.message` 在事务内追加并将 Session 标为 running；历史按 afterSeq 开放读取 |
| 目标架构 | 本文两接口及目标图 | 提交和对应 SSE 合并到 POST，GET 历史保留；多类型输入与请求输出绑定为 target-only |
| 产品约束 | 本文资源模型 | 无公共 Run/Execution；mate 公共边界只暴露 `chatId` 和公共事件身份 |
| 产品约束 | `X-HW-ID` | 标识当前请求对应的用户凭据；不是公司、服务或应用调用方标识 |
| 产品约束（target-only） | POST `access-token` | 三种用户事件在 JWT/APPKEY 模式下均必须携带，统一调用方请求头组装；不把三事件必填表述为现有 Java 已支持的行为 |
| 安全加固 | POST 凭据处理 | 凭据从请求读入后只在内存中保留到本次 Agent 执行结束，只在必要的实际 Mate tool execute 使用，不进入持久化、日志、SSE 或历史 |

### 4.1 事件顺序补充核对

本节核对 `pi-mono-java@a8192e047f4061bd385297d3dc6c4358362d0d49`，下表路径均相对
实现仓。与原基线 `c9d858bc8261bf07f5585f545b53495bf2226a56` 比较，下表五个文件均无
变化；新增的是对这些符号的排序证据分析，不是切换其他主题的实现结论。

| 分类 | 仓库相对路径与符号 | 已观察行为与边界 |
|---|---|---|
| 已观察实现 | `campusclaw/src/main/java/com/huawei/hicampus/claw/agent/Agent.java:294-306` · `emit` | 在当前线程依次通知 listener；这不是多来源的全局因果排序器 |
| 已观察实现 | `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/RuntimeEventProjector.java:105-116,238-254,382-385` · `onEvent/persistAssistant/emitPersisted` | 同一 Projector 同步处理回调，持久化完成后发送完整事件；不能由此推断不同 Projector 或其他写入入口已共同检查前置依赖 |
| 已观察实现 | `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java:55-87,208-218` · `acceptUserEvent/appendEntry/appendLocked` | 事务锁定 Session，再取序号、插入和递增；保存到达该写入边界的顺序，并不自动恢复上游乱序 |
| 已观察实现 | `campusclaw/src/main/resources/mapper/session/RuntimeSessionMapper.xml:47-75,132-164` · `lockSessionForUpdate/lockNextSequence/insertEntry/listCurrentBranch` | 使用行锁；历史 SQL 按 `entry_seq` 排序，不按 `timestamp` 排序 |
| 已观察实现 | `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/RuntimeEventQueryService.java:53-60,90-99` · `list/pageOf` | 保留查询结果顺序，以最后一项内部序号生成下一页；当前实现没有 v2 固定快照水位 |
| 架构变更（target-only） | 本文 §3.1 与 `SessionEventAppender` 推荐边界 | 所有来源共同遵守前置依赖和有序提交；ListEvents 读取已提交顺序，时间戳只作展示。需按 §5 实施并测试，不能把数据库行锁当作全部保证 |

pi 固定基线中的 Agent Loop、Message/Tool 生命周期继续作为 Runtime 内核行为参考；
本次不把 pi 的进程内事件、本地 Session 文件或 CLI 传输直接当成 CampusClaw HTTP 契约。

[Anthropic Managed Agents 的 Events and streaming](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)
与 [List Events](https://platform.claude.com/docs/en/api/beta/sessions/events/list) 用于校验
“提交与观察分离、preview 非权威、断线后查询事件历史”的公共边界；这些页面只能证明
公开契约，不能证明其内部存储或调度实现。
[OpenCode 官方 Server 文档](https://opencode.ai/docs/server/) 当前公开的是实例级
`/event` SSE，因此这里只作多客户端通知对照，不把其源码中的 Session durable stream
描述成公开稳定契约。

### 4.2 本次合并方案源码复核

本次实际读取 `pi-mono-java@918005ee8ccc88d179fc31a0de17a92b4a01383b`。
以下路径前缀均为
`campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/`。
这七个文件相对旧 `a8192e047f4061bd385297d3dc6c4358362d0d49` 均无 diff；
变化的是目标设计，不是把本次方案误说成已实现。

| 相对上述前缀的路径 / 符号 | 已观察行为与新目标差距 |
|---|---|
| `web/RuntimeEventController.java:61-91` · submit/list | 当前 POST 返回 SSE、GET 返回历史，无独立 GET stream；新方案复用传输方向 |
| `event/RuntimeEventService.java:101-141` · prepareAndSubmitLocked/acceptUserEntry | 当前只接收消息，保存后发送 user.message 并启动；三类输入和完整 v2 回执仍需改造 |
| `event/RuntimeEventStream.java:84-159` · complete/attach/detachInternal | 单 subscriber、有界缓冲、断线清缓冲，不自行 abort；尚无控制 POST 的独立绑定 |
| `web/RuntimeSseEmitterSubscriber.java:33-49` · onEvent/onComplete | 当前 named SSE 和可选 id，完成后 emitter.complete；目标 data-only 不等于当前格式 |
| `event/RuntimeExecutionCoordinator.java:154-168` · completeExecution | 当前收尾持久化、发送终态、complete 流；已确认目标中的等待确认分段关闭不能据此宣称已有 |
| `event/RuntimeTerminalEventFactory.java:34-57` · emit | 当前成功/中断发 session.status.idle + stream.end，失败发 stream.error；目标已确认收到对应 idle 后关闭，具体 reason 与失败处理仍待评审，尚未实现 |
| `event/RuntimeEventQueryService.java:53-99` · list/pageOf | 当前按内部序号分页，尚无固定快照水位 |

本次不修改 pi Agent Loop、Tool Loop 或 Session 内核语义，也不以 pi 的进程内事件
证明 HTTP 合并设计。原 pi 固定基线仅保留为其他 Runtime 设计的证据范围。

## 5. 实施切片与验收

以下是 target-only 实施建议，不是本轮实现完成报告：

1. 保留 POST SSE Controller 方向，新增三类联合 Request VO 与 Handler Registry；
   首个业务帧改为 v2 完整用户事件，保留统一凭据边界。
2. 建立每请求有界流与内部目标绑定；接受前预留容量，在所属锁内复核目标，提交回执
   后再放行输出，避免快执行漏回执或终态、以及控制请求跨到下一轮执行。
3. 在 API 投影层映射 data-only、type + phase、eventId；完整事件与历史同形，
   不把 v1 started/delta/completed 类型直接重命名就宣称实现完成。
4. 结束规则已确认：对应 idle 后关闭，等待确认时关闭并由新确认 POST 接收续跑；
   待输出绑定与错误细节确认后实施。Header 前 JSON 失败、Header 后传输断开和业务失败
   必须区分，不把单纯 EOF 当作成功。
5. 历史升级固定快照与内部有序读取。Mate bridge 将来消费 Claw POST SSE，公共
   路径和连接策略不因内部改动自动改变；当前不修改 Mate 实现或契约。

验收包括：首帧只返回本次用户事件且先于输出；极快完成和写后响应丢失；原消息与中断
并发、控制目标提前结束、不捕获下一轮事件；工具确认分段与重复确认；preview 丢弃后
完整内容覆盖；慢流溢出不阻塞执行；断线不取消、不重发；重启后历史对账；
前置依赖延迟/失败、相同或回退时间、并发提交与固定快照分页保持数组顺序。
这些运行时测试尚未实施；本轮验证的是设计源、生成 HTML、PlantUML 与 SVG。

## 6. 决策记录

以下按发生顺序保留历史；当前约束以 §1–§2 的最新决定为准。

| 日期 | 项目 | 结论 |
|---|---|---|
| 2026-09-03 | 资源模型（历史，已被 2026-09-04 合并决定替代） | 当时确认选择 A：Session Events 三接口，执行保持内部状态，无 `executionId/runId` |
| 2026-09-03 | POST 事件范围 | 已确认同一 POST 接受 `user.message`、`user.interrupt`、`user.tool_confirmation`；一次请求提交一条，不支持批量 |
| 2026-09-03 | POST 事件身份 | 已确认成功响应使用 `eventId`，不公开 `entryId` 或 `entrySeq`；内部 Entry 标识和序号可继续用于持久化与排序，Q3 只继续评审响应宽度 |
| 2026-09-03 | `X-HW-ID` 语义 | 已确认为用户凭据 ID；不是公司、服务或应用调用方标识 |
| 2026-09-03 | Header 示例与处理说明 | 已确认使用 `credential-jwt`、`credential-appkey`、`Bearer opaque-token`、`opaque-appkey`、`opaque-access-token`；凭据从请求读取，只在内存中保留到本次 Agent 执行结束，并仅随实际 Mate tool execute 发送。此项不确认 `access-token` 必填策略 |
| 2026-09-04 | POST `access-token` 必填 | 已确认统一携带：三种用户事件在 JWT/APPKEY 模式下都必填；携带不代表使用，只随实际 Mate tool execute 发送，Q1 移出待选项 |
| 2026-09-04 | 事件顺序 | 已确认先按 Session 统一检查依赖并确定顺序，再在同一短事务内分配内部序号和追加；依赖事件不得越过未提交的前置事件。ListEvents 按已提交的内部顺序返回，客户端不按 `createdAt` 重排，仍不公开 `entrySeq`。本次不更改时间字段语义，也不确认其余接口字段 |
| 2026-09-04 | POST 整体确认并推进 | 用户明确表示第一个接口可以、开始下一个接口；按当前稿确认 Q2 `event + content[]`、Q3 完整用户事件、Q4 不设幂等键且历史对账；移除 POST 待选题，转入 GET stream |
| 2026-09-04 | GET 基础类型命名 | 已确认 `agent.message`、`agent.thinking`、`agent.tool_call`、`agent.tool_result`、`session.status_idle`；完整事件在流与历史同名。只确认名称，phase、增量结构、字段及 GET 整体仍待评审 |
| 2026-09-04 | GET S1～S4 | 已确认 A-data-only、A-type-and-phase、A-user-events-receipt-history-only、A-no-read-tool-token；移除四项选择题，保留具体字段、连接细节和 GET 整体评审状态；POST 不变 |
| 2026-09-04 | 合并提交与实时推送 | 用户明确改为一次 POST SSE，撤销独立 Claw GET stream，保留 ListEvents；既有请求、Header、eventId、排序、S1/S2 继续有效，关闭细节待评审 |
| 2026-09-04 | 完整首帧回执 | 用户明确允许首帧返回本次完整 user.*（含 eventId）；调整 S3，后续不广播其他用户事件；不是自动确认整个合并接口 |
| 2026-09-04 | M3 结束规则 | 用户明确回复“结束规则我认可的”：收到本次对应 idle 后关闭响应，等待工具确认时也关闭，之后通过新确认 POST 接收续跑结果。仅确认关闭策略；reason 具体取值、并发输出归属、错误细节和整体操作仍待评审 |

## 7. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.3.1 | 2026-09-04 | 确认 M3 对应 idle 关闭，含等待工具确认分段；同步评审模型、HTML、生命周期说明及图和回归校验。不更改请求、Header 或响应示例字段，不整体确认合并接口；变更前设计提交 c315ad8，实现基线 918005ee 不变。 |
| 0.3.0 | 2026-09-04 | 合并 POST 提交与实时 SSE、确认完整 user.* 首帧回执；撤销独立 GET stream，保留历史；同步评审状态、三图和校验，补充 918005ee 与 a8192e0 的源码对比；结束规则仍候选。 |
| 0.2.2 | 2026-09-04 | 固化 GET stream S1～S4 的四项 A 选择，同步实时订阅 0.1.2、评审页、图与回归校验；不自动确认整个 GET 或切换 ListEvents。 |
| 0.2.1 | 2026-09-04 | 确认第二接口的五个基础类型名，同步评审面、实时订阅 0.1.1、生命周期图和校验；同步 POST 中断说明的 idle 名称引用，不改 POST 字段或已确认状态，S2 仅继续讨论增量结构。 |
| 0.2.0 | 2026-09-04 | 确认第一个 POST 的当前稿，结束 Q2/Q3/Q4；当前页切换到第二个 GET stream，已确认 POST 单独只读保存；增加候选流契约、专门设计、生命周期图和状态切换校验。 |
| 0.1.7 | 2026-09-04 | 确认事件处理、事务写入与 ListEvents 的共同顺序规则；补充 `a8192e0` 源码证据和目标差距，更新共享追加边界、目标图与顺序专项验收；保留时间示例及 Q2/Q3/Q4 待决状态。 |
| 0.1.6 | 2026-09-04 | 确认三种用户事件统一携带 `access-token`，两种 Header 模式均必填；保留示例值、使用范围和生命周期，移除 Q1 待选项并增加回归校验。 |
| 0.1.5 | 2026-09-04 | 按用户修正冻结 v2 公共事件身份：三种 POST 成功响应统一使用 `eventId`，删除 `entryId/entrySeq`；内部 Entry 序号不穿透 HTTP，Q3 收窄为完整事件与最窄回执的响应宽度评审；增加对应校验。 |
| 0.1.4 | 2026-09-03 | 冻结用户认可的 Header 具体非生产示例值与凭据处理说明；明确该确认不包含 `access-token` 必填策略。 |
| 0.1.3 | 2026-09-03 | 将凭据处理改写为“请求读取—内存保留到执行结束—仅 Tool execute 发送”的具体过程；全部凭据 Header 改用当前源码测试中的具体非生产示例值。 |
| 0.1.2 | 2026-09-03 | 修正并冻结 `X-HW-ID` 的身份语义：它是用户凭据 ID，不是公司、服务或应用调用方标识；同步替换请求示例占位符并增加回归校验。 |
| 0.1.1 | 2026-09-03 | 明确并冻结 POST 支持三种用户事件；将“一次一条”解释为请求批量边界，避免误读成只支持 `user.message`。 |
| 0.1.0 | 2026-09-03 | 固化资源模型 A，记录当前 Java 源码差距，增加目标资源图与类图，并启动第一个 POST operation 的四项字段评审。 |
