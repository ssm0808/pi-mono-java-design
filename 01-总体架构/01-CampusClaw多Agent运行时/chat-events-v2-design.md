# CampusClaw Session Events v2 重设计

| 属性 | 值 |
|---|---|
| 文档版本 | 0.1.1 |
| 状态 | 资源模型 A 与 POST 三种用户事件范围已确认；其余字段评审中 |
| 设计仓基线 | `c4f1ba2f2b8f4ee7cf9b7d5eaa554c42bd525bed` |
| CampusClaw 实现核对提交 | `c9d858bc8261bf07f5585f545b53495bf2226a56` |
| pi Runtime 固定基线 | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` |
| mate 公共契约基线 | [`mate-service 通用对话 API`](../../02-服务与接口/07-mate-service通用对话API/README.md) 1.4.4 |
| 外部公共契约核对日 | 2026-09-03 |
| 更新日期 | 2026-09-03 |

## 1. 已确认资源模型

CampusClaw 采用 Session Events 三接口，内部执行不成为公共资源，也不增加
`executionId` 或 `runId`：

| Method | Path | 职责 | 当前状态 |
|---|---|---|---|
| `POST` | `/campusclaw-service/v1/sessions/{sessionId}/events` | 每次接受并持久化一条三种联合类型之一的用户事件 | 事件范围已确认，其余字段评审中 |
| `GET` | `/campusclaw-service/v1/sessions/{sessionId}/events/stream` | 订阅跨多次内部执行的 Session live SSE | 只确认职责，字段未开始评审 |
| `GET` | `/campusclaw-service/v1/sessions/{sessionId}/events` | 读取固定快照的权威历史 | 只确认职责，字段未开始评审 |

这三个 operation 同构于 mate 公共 API 的“提交、实时观察、权威恢复”职责，但不是
字节透明转发。Claw 保留内部 `sessionId`、Entry 身份和更丰富的 Runtime 事件；mate
继续拥有 `chatId`、公共 `eventId`、终端用户授权和安全字段投影。

`user.interrupt` 进入 POST 的用户事件联合类型，替代独立
`POST /sessions/{sessionId}/abort`。`user.tool_confirmation` 同样进入该联合类型。
Steer、FollowUp 和 Slash Command 是否并入 Events 不在本轮自动决定，继续保留现行
v1 契约，待三个核心 operation 完成后逐项评审。

该选择属于架构变更：当前 Java 的 POST 返回一次执行范围的 SSE；目标 POST 只返回
普通 JSON 接受结果。产品约束仍是不公开执行 ID；安全加固仍是凭据只形成执行级瞬态
快照，不持久化、不记录、不发往模型或工具发现。

![Session Events 目标资源模型](设计图/事件接口重设计/target_session_events_resource_model.svg)

[PlantUML 源码：`target_session_events_resource_model`](设计图/事件接口重设计/diagram.puml#L1)

## 2. 第一项：提交 Session 用户事件

当前只评审：

```http
POST /campusclaw-service/v1/sessions/{sessionId}/events
Content-Type: application/json
Accept: application/json
```

已确认本接口支持 `user.message`、`user.interrupt`、
`user.tool_confirmation`。每次请求只能提交其中一条，表示不支持数组或批量提交，
并不表示接口只接收 `user.message`。

完整候选字段、请求示例、成功与错误响应及四个选择题见
[`chat-events-v2-review.html`](chat-events-v2-review.html)。可编辑源是
[`接口契约-v2/common.json`](接口契约-v2/common.json) 与
[`01-submit-session-event.json`](接口契约-v2/操作/01-submit-session-event.json)。

当前推荐快照如下，但尚未确认：

1. `access-token` 对三种用户事件均为必填，但 Claw 只在实际 Mate tool execute 使用；
2. 请求体使用 `event` 包装和有序 `content[]`，与 mate 请求结构同构；
3. `200 ResultBean` 返回完整内部用户事件，包含 `entryId`、`entrySeq`、
   `createdAt` 及规范化业务字段；
4. 不引入 `Idempotency-Key`。响应丢失时通过权威历史对账，不盲目重放 POST。

同构只减少 mate 到 Claw 的请求转换，不改变所有权。Claw 的 `entryId/entrySeq` 是
内部持久化身份；mate 的公共 `eventId` 仍由 mate 契约管理，不能把内部 Entry 身份
直接暴露给浏览器。

## 3. 目标分层与生命周期

![Session Events 目标类图](设计图/事件接口重设计/target_session_events_classes.svg)

[PlantUML 源码：`target_session_events_classes`](设计图/事件接口重设计/diagram.puml#L110)

目标结构采用五个责任边界：

- Web 边界只接收 Request VO、返回不可变 Response VO，不把 DTO 或持久化记录穿透给
  Controller；
- Application Service 根据 `event.type` 选择独立 Handler，避免新增事件时修改中央
  `switch`；
- 请求快照只固定解析后的结构、对象身份、locale 和瞬态凭据。Session 状态、执行容量、
  待确认 Tool Call 等可变权威状态必须在所属事务或 Session 锁内重新检查；
- Runtime Coordinator 继续拥有一次内部执行，Projector 先持久化权威 Entry，再发布
  completed live event；delta 等 preview 只 best-effort 发布；
- `SessionLiveEventHub` 是 Spring 单例，每条 SSE 连接拥有独立有界 Subscription。
  慢消费者或断线只移除自身，不能阻塞执行、其他订阅者或取消 Session。

历史查询在第一页固定水位、过滤条件和分页方向，后续不透明 page 必须绑定同一快照。
live Hub 不重放、不承担恢复；任何 SSE gap、订阅溢出或 POST 响应不确定都回到历史对账。

## 4. 源码证据与差距

| 分类 | 源码证据 | 结论 |
|---|---|---|
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java:39-91` · `RuntimeEventController.submit/list` | POST 创建 `SseEmitter` 并返回 `text/event-stream`；GET 只接收 `limit/page` |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventService.java:76-139` · `submit/prepareAndSubmit/acceptUserEntry` | 只接受 `user.message`，要求 idle，持久化后直接启动内部执行并返回其 EventStream |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventStream.java:22-159` · `attach/detachInternal` | EventStream 属于一次执行且最多一个 subscriber；断线会清空该流缓冲 |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventQueryService.java:53-99` · `list/pageOf` | page 只携带 afterSeq 与 thinking，没有固定历史快照水位 |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionControlService.java:59-132` · `steer/followUp/abort/prepareAbort` | Abort 是独立接口行为；Steer 与 FollowUp 使用执行内队列 |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java:57-120` · `acceptUserEvent/listCurrentBranch` | `user.message` 在事务内追加并将 Session 标为 running；历史按 afterSeq 开放读取 |
| 目标架构 | 本文三接口及目标图 | 提交、live 与历史解耦；支持跨执行、多订阅者的 Session live Hub |
| 产品约束 | 本文资源模型 | 无公共 Run/Execution；mate 公共边界只暴露 `chatId` 和公共事件身份 |
| 安全加固 | POST 请求快照 | 凭据只在必要的实际 Mate tool execute 使用，不进入持久化、日志、SSE 或历史 |

pi 固定基线中的 Agent Loop、Message/Tool 生命周期继续作为 Runtime 内核行为参考；
本次不把 pi 的进程内事件、本地 Session 文件或 CLI 传输直接当成 CampusClaw HTTP 契约。

[Anthropic Managed Agents 的 Events and streaming](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)
与 [List Events](https://platform.claude.com/docs/en/api/beta/sessions/events/list) 用于校验
“提交与观察分离、preview 非权威、断线后查询事件历史”的公共边界；这些页面只能证明
公开契约，不能证明其内部存储或调度实现。
[OpenCode 官方 Server 文档](https://opencode.ai/docs/server/) 当前公开的是实例级
`/event` SSE，因此这里只作多客户端通知对照，不把其源码中的 Session durable stream
描述成公开稳定契约。

## 5. 实施切片与验收

资源模型落地时按以下顺序实施：

1. 引入用户事件联合 Request VO、Handler Registry 和三个 Handler；POST 改为普通
   ResultBean，并以事务或 Session 锁完成状态复核与持久化；
2. 引入 `SessionEventPublisher` 与多订阅者 `SessionLiveEventHub`，先让现有
   Coordinator 双写到新发布边界，再删除 POST 持有的 `RuntimeEventStream`；
3. 新增独立 GET stream，验证同 Session 多订阅者、跨 idle/execution 保持连接、慢消费者
   隔离、heartbeat 和断线不取消执行；
4. 将历史游标升级为固定快照，验证新写入不进入已开始翻页的快照；
5. mate bridge 切换到“先保持 live 观察，再独立 POST”，通过公共 `eventId` 与 Claw
   Entry 映射对账，最后移除独立 Abort 调用路径。

验收必须覆盖：POST 成功但响应丢失、live SSE 中断、订阅队列溢出、两个同时订阅者、
interrupt 接受后延迟退出、错误 Tool 确认、服务重启后仅靠历史恢复，以及 POST 不因
观察流断开而自动重放。

## 6. 决策记录

| 日期 | 项目 | 结论 |
|---|---|---|
| 2026-09-03 | 资源模型 | 已确认选择 A：Session Events 三接口，执行保持内部状态，无 `executionId/runId` |
| 2026-09-03 | POST 事件范围 | 已确认同一 POST 接受 `user.message`、`user.interrupt`、`user.tool_confirmation`；一次请求提交一条，不支持批量 |
| 2026-09-03 | POST 字段 | 评审中；四个推荐项只是当前提案，不视为用户确认 |

## 7. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.1 | 2026-09-03 | 明确并冻结 POST 支持三种用户事件；将“一次一条”解释为请求批量边界，避免误读成只支持 `user.message`。 |
| 0.1.0 | 2026-09-03 | 固化资源模型 A，记录当前 Java 源码差距，增加目标资源图与类图，并启动第一个 POST operation 的四项字段评审。 |
