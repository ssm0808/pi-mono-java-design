# 定时任务源码与官方证据

[主设计](README.md) · [Agent 架构对比](../07-Agent架构对比/README.md#a14)

| 属性 | 值 |
|---|---|
| 文档版本 | 0.35.0 |
| 核验日期 | 数据库专项为 2026-10-10，见[Claw 数据库设计（定时增量）](../../03-数据与存储/Claw数据库设计.md#source-baseline)；其余各节保留实际核验日期与范围 |
| 产品范围 | 每次运行创建独立 Session，复用已绑定 Agent；不提供已有 Session 目标 |
| 状态边界 | 历史主线范围见各节；PR #332 三张调度表、Mapper、同库受理与启动控制已实现、未合并，差距及数据库验收见[Claw 数据库设计（定时增量）](../../03-数据与存储/Claw数据库设计.md#gaps)；生产公司身份系统未核验 |

2026-10-10 的数据库源码、完整 head/base/merge-base、字段字典与差距集中于 [Claw 数据库设计（定时增量）](../../03-数据与存储/Claw数据库设计.md#source-baseline)。本文后续历史证据不随本次局部核验升级；旧“待实现”描述仅代表其当时核验范围。

<a id="java-evidence"></a>

## 1. Java 源码快照与核验范围

本节记录 2026-09-29 的 Java 核验。实现仓为 `superheromeZzh/pi-mono-java`。当次通过 `git ls-remote --symref origin HEAD` 确认默认分支为 `main`，随后 `git fetch origin main`；远端默认分支与读取工作树均为完整 commit `553dcd5e2ff682f9684810a043b442b37a02e54a`。这表示 2026-09-29 查询时的默认分支源码，不代表稳定发布版本。核验时工作树仅有未跟踪 `.m2/`，未将该目录作为源码证据，也未修改实现仓。2026-09-30 对该提交的调度实现补充读取见[Spring 与 JDK 证据](#spring-scheduling-evidence)，不改变其他模块证据的日期归属。

核验范围为 `modules/cron`、HTTP Runtime 的 Session 创建/消息受理/执行持久化与输出策略、公共 Session 工厂、Cron runner、请求凭据与业务确认入口、相关 POM 和 GaussDB DDL。`campusclaw/` 是生成镜像，本次以 `modules/` 为主，不另行声称镜像构建通过。本文不证明 Mate 服务端认证、租户隔离、凭据签发与刷新、集群故障恢复或外部业务幂等。

历史证据 `f61906b9136246ca60f333704b6fc92b5420d0ec` 保留在 [M01 源码证据](../01-CampusClaw多Agent运行时/source-evidence.md#4-session-创建与-http-入口核对)及 [Agent 架构对比](../07-Agent架构对比/README.md)。这里只升级下表实际重新读取的范围，不将其余旧结论延伸为当前 main 的实现缺陷或完成状态。

## 2. 已实现的进程内 Cron

以下链接固定到上述完整 commit；链接文字为仓库相对路径，符号与行号均来自同一快照。

| 编号 | 源码路径与定位 | 已观察行为与证据边界 |
|---|---|---|
| J01 | [modules/cron/src/main/java/com/campusclaw/cron/CronService.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/CronService.java#L29)；`SmartLifecycle`、`createJob`、`enableJob`、`disableJob`、`triggerJob` | 随 Spring 启停；协调任务存储、调度与运行日志。内部启停方法存在，不等于已有公共任务管理 HTTP API。 |
| J02 | [modules/cron/src/main/java/com/campusclaw/cron/tool/CronTool.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/tool/CronTool.java#L35)；`INPUT_SCHEMA`、`create`（181）、`requireOwnedJob`（238）、`parseSchedule`（250） | 模型入口提供 create/list/delete/trigger/status/runs；create 自动绑定当前 Agent；其他 Agent 的 Job 表现为不存在。Schema 拒绝额外字段，但这种 Agent 过滤不证明租户或用户授权。 |
| J03 | [modules/cron/src/main/java/com/campusclaw/cron/model/CronSchedule.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/model/CronSchedule.java#L26)；`At`、`Every`、`CronExpr`；[modules/cron/src/main/java/com/campusclaw/cron/model/CronPayload.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/model/CronPayload.java#L18)；`AgentPrompt` | 计划支持 at/every/cron；payload 只保存 agentId/prompt，不保存模型、工具、SYSTEM 快照、租户或长期授权。 |
| J04 | [modules/cron/src/main/java/com/campusclaw/cron/engine/CronEngine.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/engine/CronEngine.java#L62)；`start`（62）、`scheduleJob`（121）、`triggerJob`（177）、`executeAndReschedule`（185） | 单线程 ScheduledExecutorService 安装任务，定时路径持有进程内 tickLock 并同步执行；手工 trigger 直接 executeJob，没有经过定时路径中的 tickLock/running 检查。不能将其描述为统一的跨节点触发互斥。 |
| J05 | [modules/cron/src/main/java/com/campusclaw/cron/engine/CronEngine.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/engine/CronEngine.java#L301)；`computeNextDelay`、`cleanStaleRunning`（337）、`recordJobOutcome` | every 以上次完成时间与创建时间的较大值为基准；失败使用退避，连续 3 次错误禁用；cron 采用 Spring CronExpression，未指定时区时使用节点默认时区；启动时仅清理超过 2 小时的 running 标记。没有持久 occurrence、misfire 窗口或可靠接管协议。 |
| J06 | [modules/cron/src/main/java/com/campusclaw/cron/store/CronStore.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/store/CronStore.java#L54)；`load`、`save`（70）、`addJob`（82）、`updateJob`（112）、`saveUnsafe`（141） | Job 写入本地 jobs.json；ReentrantReadWriteLock 只在本实例内生效；I/O 错误记录日志并返回空列表或不抛出保存失败。不是数据库持久化或可靠成功回执。 |
| J07 | [modules/cron/src/main/java/com/campusclaw/cron/store/CronRunLog.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/store/CronRunLog.java#L55)；`appendRun`、`getRecentRuns`（70）；[modules/cron/src/main/java/com/campusclaw/cron/engine/CronJobExecutor.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/engine/CronJobExecutor.java#L45)；`execute` | 每 Job JSONL 追加 RUNNING 与完成记录；执行异常记录稳定错误码，诊断文本不进入 run.errorMessage；输出是提取后的 Assistant 文本。不是公共 Session 历史或持久根执行关联。 |
| J08 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/cron/ManagedCronSessionRunner.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/cron/ManagedCronSessionRunner.java#L53)；`execute`、`resolveDefaultModel`（75）、`extractAnswer`（82） | 用 CRON profile、ThinkingLevel.OFF、MateCredentials.empty()、空 before/after hooks 创建隔离内存 Session，prompt().join() 后提取文本。未创建 t_sessions、execution 或 event 关联，也未接入 Runtime 容量和超时协调器。 |
| J09 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSessionFactory.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSessionFactory.java#L69)；`create`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/AgentRuntimeManager.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/AgentRuntimeManager.java#L95)；`prepare`、`refresh`（120） | 每次创建时 prepare Agent，校验启用状态，以同次 runtime 解析模型和装配工具；prepare 优先当前完整已发布目录，refresh 才强制从 Mate 重建。触发时读取当前目录不等于每次触发都远端刷新。 |
| J10 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/ManagedAgentSessionRequest.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/ManagedAgentSessionRequest.java#L75)；兼容构造器；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/PlanPolicyPromptComposer.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/PlanPolicyPromptComposer.java#L32)；`compose` | 旧 Cron runner 使用的构造器默认 mode=build；但 CRON 的 SYSTEM 仅 basePrompt，不追加 buildPrompt。目标必须分别说明执行模式和提示词组合，不把二者混为一种既有行为。 |

现有实现已能在单进程内定时执行 Agent，不能把它整体标为“待实现”。新增集群领取、数据库事务、触发去重、持久化后台受理与公共运行详情尚未由以上实现提供。

## 3. 可复用的 Session、执行与历史

| 编号 | 源码路径与定位 | 已观察行为与复用限制 |
|---|---|---|
| J11 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeSessionController.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeSessionController.java#L62)；`create`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionService.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionService.java#L64)；`create`、`newSession`（117） | 先解析目录与默认模型，再创建空历史 Session；默认 thinking=true，要求支持 reasoning 的默认模型，mode 来自 Agent。后台新建目标需明确自己的 build/thinking 准入，不能把当前方法直接视为通用后台受理。 |
| J12 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeMessageEventService.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeMessageEventService.java#L96)；`submit`、`prepare`（149）、`accept`（174）、`startAccepted`（190） | 本地 Session 操作锁内准备执行，检查 idle，持久化受理后先入队回执再启动；服务返回 RuntimeEventStream，仍与请求 SSE 上下文连接。没有 scheduleId/runId 受理键。 |
| J13 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionContextFactory.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionContextFactory.java#L57)；`create`、`createPreparedMessage`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/runtime/RuntimeSessionEngineRegistry.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/runtime/RuntimeSessionEngineRegistry.java#L97)；`register`、`createHolder`（169）、`createSession`（205） | 恢复历史、创建流、注册活动执行；Registry 有 Semaphore 容量、Session 本地锁、权限策略和工具快照；createSession 固定 RUNTIME profile。后台 CRON profile 与无输出上下文仍需新增接线。 |
| J14 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/RuntimeExecutionPersistenceService.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/RuntimeExecutionPersistenceService.java#L69)；`acceptMessage`、`commitTerminal`（290） | @Transactional 原子受理 user.message、创建 execution/初始 segment 并关联公共事件；终态固定到原执行目标。可作为后台受理事务的基础，但当前没有把 Schedule/Run 与新 Session 一并受理的服务。 |
| J15 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java#L116)；`acceptUserEventLocked`；[modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml#L63)；`lockSessionForUpdate` | 数据库行锁内重新检查 Session idle、plan 可用性，再追加消息并置 running。本地检查不代替数据库准入；这是普通 Session 并发基础，不构成定时任务需要提供已有会话目标的理由。 |
| J16 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventOutput.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventOutput.java#L35)；`persistenceOnly`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/PersistenceOnlyRuntimeEventOutput.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/PersistenceOnlyRuntimeEventOutput.java#L20) | 已有无响应流输出策略；Projector 先持久化，该策略丢弃事件工厂，不构造 SSE、不持有连接/缓冲，也不拥有执行取消权。可用于后台执行，当前 Cron runner 尚未使用。 |
| J17 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java#L91)；`start`、`scheduleTimeout`（154）、`commitTerminal`（271）、`retryTerminal`（341） | 订阅投影、安装确认处理器、启动 Agent、处理超时并提交唯一终态；终态写入失败保留执行并重试。可复用生命周期；不等于已有跨进程模型执行接管、启动 CAS 或 Run 对账。 |
| J18 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeContextHistoryService.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeContextHistoryService.java#L34)；`restoreHistory`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/CommittedEventQueryService.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/CommittedEventQueryService.java#L40)；`list` | 按权威线性历史恢复模型上下文，按公共事件分页读取。定时运行结果可沿用消息权威；不需再在 Run 保存一份完整聊天文本。 |
| J19 | [modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql#L26)；`t_sessions`（26）、`t_session_executions`（81）、活动执行唯一索引（118）、segments（146）、entries（363）、events（426） | 已有 Session、根执行、段、内部历史和公共事件存储；Session 同时只能存在一条非终态根执行。当前 DDL 无 schedule/run/claim 表，Session 状态只有 idle/running；不能用它表示调度领取或未知运行状态。 |

推荐复用既有存储与投影，新增 `ScheduledRunAcceptanceService` 组织同库短事务，并把后台 profile、persistenceOnly 输出和 Run 关联接入公共执行链。该服务、启动权持久 CAS、Run 终态对账均为待实现。不能通过依次调用“创建 Session HTTP + POST 消息 HTTP”宣称获得原子受理，不能在回执丢失时再次创建会话重发 prompt。

当前产品范围固定为每次运行新建 Session。同库受理关联新 Session、首消息、根执行与 Run；同一 Run 的重复内部通知只读取原关联，不重新创建或启动执行。[执行与工程落地](execution.md)维护事务、容量准入、不补跑和故障对账规则，均待实现；普通 Session 的行锁、历史恢复和查询只是既有基础，不能将它们写成定时新会话接线已经完成。

## 4. 身份、权限与交互证据

| 编号 | 源码路径与定位 | 已观察行为与未核验边界 |
|---|---|---|
| J20 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeRequestContext.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeRequestContext.java#L45)；`mateCredentials`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/mate/MateCredentials.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/mate/MateCredentials.java#L7) | 从请求取得 X-HW-ID、X-HW-APPKEY、Authorization、access-token；凭据对象明确说明 Runtime 不验证真实性、组合或最低完整性，执行时交 Mate 授权，不持久化。不能推断已有长期委托或 Token 刷新。 |
| J21 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/question/BusinessConfirmationAdapter.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/question/BusinessConfirmationAdapter.java#L90)；`requireAvailable`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/BusinessToolDispatcher.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/BusinessToolDispatcher.java#L31)；`assembled` | 公共工厂绑定业务确认适配器；适配器只允许 RUNTIME，CRON/CHILD 返回入口不支持，缺问题端口也失败。当前不存在 Cron 无人审批等待队列。 |
| J22 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/dto/RuntimeSessionDTO.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/dto/RuntimeSessionDTO.java#L19)；Session 字段；[modules/cron/src/main/java/com/campusclaw/cron/model/CronJob.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/model/CronJob.java#L19)；Job 字段 | 这两类对象及 J19 DDL 无 tenantId/ownerId/长期授权引用；读取范围内没有证明可信租户 scope 的解析与仓储约束。通用 RequestHeaderInfo 出现 agentTenantId 字段不足以证明当前链路已隔离。Mate 服务端与公司认证集成未核验。 |

目标的 `ScheduleAuthorizationPort`、可信管理作用域及无人值守凭据接线待实现。Mate 是可信接口定义、主体授权和按 Agent 绑定解析业务凭据的权威来源，精确内部草案与生产集成边界见[Mate 定时执行上下文](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md)。每次触发仍需可信解析、参数校验、权限判断；任务启用不等于永久批准任意业务工具。首版遇权限 ASK、自定义提问或计划审核时记录原因并结束本次根执行，不进入持久等待；参数错误保留模型修参机会，不自动猜参或重放。普通 Session 继续使用本次请求的 Header 快照，不持久化秘密；工具五阶段与公共安全投影由 M03 唯一维护，定时入口差异见[非交互规则](execution.md#noninteractive)。

## 5. 依赖与历史基线变化

| 编号 | 源码路径 | 核验结论 |
|---|---|---|
| J23 | [pom.xml](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/pom.xml#L25)；`properties`、`dependencyManagement` | JDK 21、Spring Boot 3.4.5、MyBatis Starter 3.0.4；JobRunr Starter 7.3.1 仅出现在版本管理中，不证明已引入运行时依赖。 |
| J24 | [modules/cron/pom.xml](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/pom.xml#L21)；[modules/coding-agent-cli/pom.xml](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/pom.xml#L24) | Cron 已直接依赖 agent-core、Jackson、spring-context；Host 已有 JDBC、MyBatis、PostgreSQL JDBC。模块 POM 与公司镜像 POM 未直接引入 JobRunr。复用 Spring CronExpression 与宿主数据库 Adapter 可避免新增外部直接依赖；本次未运行 dependency tree，完整传递图与包体增量未核验。 |

已比较 `f61906b9136246ca60f333704b6fc92b5420d0ec` → `553dcd5e2ff682f9684810a043b442b37a02e54a` 的相关路径差异，并读取新快照：

| 范围 | 观察到的变化 | 对本专题结论的影响 |
|---|---|---|
| ManagedCronSessionRunner | 从 ModelCatalogService 查找切为 RuntimeModelManager.resolveDefaultModel，读取已发布 defaultModelId | 以新模型解析路径解释触发时配置；保持 Cron 创建内存 Session 的边界，不外推为已有后台持久受理 |
| AgentSessionFactory | 加入 PlanPolicyPromptComposer、准备结果检查、基于同次 runtime 的 Mate 工具装配与业务确认绑定 | 新设计需保持同次准备快照，并单独说明 CRON 的 basePrompt 行为 |
| RuntimeSessionEngineRegistry | 绑定 Agent、权限和工具调用快照，追加 mode 与用户提问/计划审核接线 | 后台复用应保留这些可信准备能力，新增 CRON 策略而非绕过 Host |
| RuntimeMessageEventService | 受理时传入计划审核工具可用性，启动时应用已接受模式 | 普通消息受理遵守权威 mode；本产品定时任务不向已有会话追加输入 |
| CronTool 与其他旧结论 | 已读取当前 Schema/Agent 绑定实现；旧表未核验的基线与模块保持原证据归属 | 只更新本专题证据，不批量替换 M01～M09 的历史 SHA，也不以旧缺口推断当前 main |

## 6. 测试证据与未执行项

实际阅读的测试断言包括：

- [modules/coding-agent-cli/src/test/java/com/campusclaw/codingagent/tool/cron/ManagedCronSessionRunnerTest.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/test/java/com/campusclaw/codingagent/tool/cron/ManagedCronSessionRunnerTest.java#L71)：`preparesAgentAndUsesCronProfileAtTriggerTime` 断言 CRON、Agent、空凭据及模型解析；`usesPublishedDefaultWhenItIsNotFirstBinding` 断言使用明确 default model，不取第一条 binding。测试 mock 公共工厂，不能据此证明真实集群、持久化或身份链路。
- [modules/cron/src/test/java/com/campusclaw/cron/engine/CronJobExecutorTest.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/test/java/com/campusclaw/cron/engine/CronJobExecutorTest.java#L36)：`failureRecordCarriesStableErrorCodeInsteadOfDiagnosticText`、`uncodedFailureUsesGenericStableCodeWithoutDiagnosticText` 断言稳定错误码与不泄露诊断文本。

另定位了 `CronEngineTest`、`CronStoreTest`、`CronRunLogTest`、`CronToolTest`、`CronScheduleTest`，其存在仅说明已有测试材料。2026-09-29 的源码核验没有运行 Maven 测试、编译、真实 GaussDB、多副本故障注入、DST 边界测试、企业身份联调或压测。主设计新增原子受理、唯一触发、租约代次、启动 CAS、未知执行对账与无人值守权限均仍需实施与验收，不能因静态证据或旧测试存在而写成已通过。2026-09-30 的表达式边界小验证单独记录在[Spring 与 JDK 证据](#spring-scheduling-evidence)。

<a id="claude-evidence"></a>

## 7. Claude Managed Agents 官方契约

2026-09-29 重新读取以下官方页面。Scheduled deployments 属于 Beta，要求 `managed-agents-2026-04-01`；没有可归因的服务端源码 commit。下表只证明公开契约，不能推导内部表、事务顺序、调度器、锁或节点接管算法。

| 来源 | 本次核对的公开行为 |
|---|---|
| [Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments) | Cron 到期创建新 Session；DST 春跳跳过、秋回触发两次。实际启动 jitter 最多为周期的 15%，下限 5 秒、上限 9 分钟。暂停不终止在途，恢复不补暂停期间触发；创建限流不重试，不可恢复错误暂停。主 Agent 归档/删除使 Deployment 归档，此时不产生 Run。指南未定义完整重叠与一般故障补跑策略。 |
| [Create Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/create) | Agent 字符串固定创建时最新版本，也可指定版本；initial_events 1～50 条，API 另含受限制的 system.message，不能说只支持 user.message。可不设 schedule，成为仅手动 Deployment；Cron 为五字段 POSIX 与 IANA timezone，不含秒字段。schedule 非空自动触发，指南新建示例为 active，不支持从“先设计配置”推导默认暂停。 |
| [Update Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/update) | 再提交 Agent 字符串重新固定最新版本，省略保持；initial_events 整体替换；schedule:null 取消自动计划。更新作用于未来启动，不修改在途 Session。 |
| [List Deployment Runs](https://platform.claude.com/docs/en/api/beta/deployment_runs/list) | Run 是 Session 创建结果，session_id 与 error 二选一；同一 deployment_id/scheduled_at 最多一个 Run，scheduled_at 是 jitter 前 UTC 时间。不表示外部业务恰好执行一次，也不表示任务已完成。 |
| [Run Deployment Now](https://platform.claude.com/docs/en/api/beta/deployments/run) | 手动运行创建 Session，并以 manual 触发记录关联结果；不能以创建成功替代 Session 后续终态。 |
| [Pause](https://platform.claude.com/docs/en/api/http/beta/deployments/pause)、[Unpause](https://platform.claude.com/docs/en/api/http/beta/deployments/unpause)、[Archive](https://platform.claude.com/docs/en/api/http/beta/deployments/archive) | 生命周期各自为管理操作；暂停仍可手动运行，归档不可恢复。指南没有明确说明归档是否终止在途；CampusClaw 直接删除配置及 Run，不自动取消已受理执行，见 §8.13；这是产品选择，不是对 Claude 归档的推断。 |
| [Deployment 模型](https://platform.claude.com/docs/en/api/http/beta/deployments) | 状态是 active/paused，归档另由 archived_at 表达；预览最多五项，暂停时可保留假设恢复后的预览。CampusClaw 仅采用 active/paused，不提供归档状态或字段，删除成功返回完整配置回执，随后不再提供读取。 |
| [Authenticate with vaults](https://platform.claude.com/docs/en/managed-agents/vaults) | Vault/凭据以 workspace 为作用域，Deployment 通过引用关联；运行期解析与更新。公开 workspace 访问模型不证明 CampusClaw 的公司租户/用户隔离或委托授权，不能直接存聊天 Token 替代它。 |

相对 A14 的 2026-09-22 证据，本次只更新 Claude 调度范围：将旧“最多 10 秒 jitter”校正为当前比例窗口；明确 Run 的创建结果含义、主 Agent 归档/删除不落 Run 的例外及固定版本语义。未重核的 Claude Session/preview/工具文档仍保留各专题原日期；其他四个开源 Agent 基线保留 A14 原 SHA 与成熟度。

公开 API 的自动生成示例可能同时填入 session_id/error 等占位值，不能用此覆盖字段约束。主设计依据字段文字与指南，并明确区分 CampusClaw 的额外状态与可靠性目标。

<a id="configuration-evidence"></a>

## 8. Claw 配置接口的源码核验

2026-09-29 收敛接口时再次确认 Claw 上游默认 main 并 fetch，仍为 `553dcd5e2ff682f9684810a043b442b37a02e54a`；重读 CronSchedule/CronPayload、CronService/CronEngine、AgentRuntimeManager/MateServiceClient、RuntimeSessionController、AgentDirectorySnapshotDTO 与 UserMessageContentRequestVO。旧新提交未变。下表实现观察保留该快照；目标解释按当前已确认的单条 user.message、可选 schedule 和每次新建 Session 更新，不把目标决定写成已有实现。

C01～C07 保留此前对前端和本地 Mate 示例的历史观察，不构成本版待实现接口清单。Mate 当时读取的是本地 `4b957a3a846659f5b7569c9d6133abc070cd2e3c`，不是当日最新上游或完整生产部署；其 README 定位为待集成的可运行示例。历史 `956b547f5ca12ca89e68f73012f92a4406b0c9fa` 的其他结论不随此升级。本次不新增 Mate 路由、页面、公共 Chat 映射或 Agent 目录契约。

| 编号 | 仓库相对路径与符号 | 已观察实现与配置设计影响 |
|---|---|---|
| C01 | Claw `frontend/README.md`；`frontend/src/App.vue` · configuredAgentId；`frontend/src/components/AppSidebar.vue` | 前端是内部 Runtime 工作台，Agent 从环境变量/开发设置取得；Agent 中心禁用，无定时任务页。新增正式配置客户端不能复用内部直连作为后备路径。 |
| C02 | Claw `frontend/src/composables/useRuntimeApi.ts` · API_PATH/request/createSession/changeSetting | 固定 `/campusclaw-service/v1`；使用 ResultBean 形状、ETag/If-Match 与 no-store。请求头是既有实现事实；当前无条件请求目标及迁移差距见 §8.12，不能将此模式继续作为 Schedule 推荐，也不能证明已有 Mate 公共接入。 |
| C03 | Claw `frontend/src/composables/useWorkbenchSessions.ts`；`frontend/package.json` | 会话索引按后端/Agent/caller 本地隔离，草稿留内存；无定时配置列表、请求幂等恢复、vue-router 或表单库。仅保留观察，不在 Claw 契约规定页面存储方式。 |
| C04 | Mate `src/main/java/com/huawei/hicampus/mate/agentdefinition/controller/AgentDefinitionController.java` · listAgents/getAgent/getRuntimeAgent/updateAgent | 已有 `/mate-service/v1/agents` 及详情/runtime/更新；未观察 Schedule 或公共 Chat Controller。只有这些接口存在，不证明完整权限链。 |
| C05 | Mate 同包 `vo/ListAgentRequestVO.java`、`vo/ListAgentResponseVO.java`；`service/impl/AgentDefinitionServiceImpl.java` · listAgents；`src/main/resources/mapper/AgentDefinitionMapper.xml` | 列表 pageIndex 默认1、pageSize默认20上限100；data/total/pageIndex；按 name/displayName/enabled/version 过滤。没有可信操作者/租户范围过滤，不能把 enabled=true 当授权。 |
| C06 | Mate 同包 `vo/AgentInfoResponseVO.java`；`service/impl/AgentDefinitionServiceImpl.java` · buildAgentInfo | 管理聚合含 SYSTEM、permission 和全部绑定。普通候选需授权后安全摘要，不能让浏览器收到管理聚合再隐藏。 |
| C07 | Mate 同包 `vo/ApiSuccessResponseVO.java`、`vo/ApiErrorResponseVO.java`；`controller/ApiExceptionHandler.java` | 示例模拟 ResultBean，更新空 result 被省略；错误是稳定码与文案，无 fieldErrors。Agent 异常未设置 Content-Language。新配置完整资源回显与语言 Header 是新增契约。 |
| C08 | Claw `modules/cron/src/main/java/com/campusclaw/cron/CronService.java` · createJob；`store/CronStore.java` · saveUnsafe/updateJob | create 存储后立即 schedule；文件保存异常仅日志，无配置版本及数据库事务。不能直接包装此方法声称配置 API 已可靠提交。 |
| C09 | Claw `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/AgentRuntimeManager.java` · prepare/rebuild/publish | 完整缓存命中不拉取 Mate，缺失则拉 Agent/Skill、写 staging 并发布目录。配置保存不调用 prepare；元数据校验与目录发布分离。 |
| C10 | Claw 同 codingagent 根 `runtimeapi/agent/AgentDirectorySnapshotDTO.java`、`AgentDirectorySnapshots.java`；`runtime/MateServiceClient.java` · getAgentRuntime/AgentRuntime；`runtime/AgentRuntimeManager.java` · AgentIdentity | Runtime 元数据及目录身份有 version，但当前装配快照不含版本选择；远端查询仅按 agentId，无历史版本解析或 Environment 选择契约。缺的是可执行历史绑定，不是整个系统没有版本字段。 |
| C11 | Claw 同根 `runtimeapi/web/RuntimeSessionController.java`；`session/RuntimeSessionUpdateService.java`；`persistence/MyBatisRuntimeSessionRepository.java` · updateSession | 既有 Session 更新使用 ETag/If-Match、428/412 与数据库锁内版本重验。该事实是现行无条件请求目标的实现差距，不要求 Schedule 暴露版本或客户端条件令牌；其当前数据库并发契约由配置文档维护。Mate Agent 更新仍为锁行后最后写入生效，不宣称全系统已经统一。 |
| C12 | Claw `modules/common/src/main/java/com/campusclaw/common/constant/ClawConstants.java` · RuntimeApi.MAX_MESSAGE_CHARACTERS；同 codingagent 根 `runtimeapi/vo/UserMessageContentRequestVO.java` · TextRequestVO/FileRequestVO；`modules/cron/src/main/java/com/campusclaw/cron/model/CronPayload.java` · AgentPrompt | 普通文本上限262144，Runtime 已有文本和文件引用块，严格类型与未知字段检查。已确认配置输入为单条 user.message，首版只接受文本块；普通 Session 的现有文件引用形状不代表定时附件能力；不扩成多初始事件或 system.message。旧 CronPayload 仍只有 agentId/prompt，输入保存与运行接线须迁移，不能直接宣称已支持调度附件。配置更新另须保留省略/null差异。 |
| C13 | Claw `modules/cron/src/main/java/com/campusclaw/cron/model/CronSchedule.java` · At/Every/CronExpr；`engine/CronEngine.java` · computeNextDelay | 三类型已有，Cron 采用 Spring CronExpression；已确认继续使用 Spring 六字段，精确规则见[配置契约](configuration.md#spring-cron-contract)。旧 every 按完成/创建时间计算；新配置 HTTP 仅接受 Cron，不暴露或自动迁移旧 At/Every。六字段复用既有依赖，但不表示可以直接接收 Claude 五字段，亦不构成硬实时保证。 |
| C14 | Claw 同 codingagent 根 `runtimeapi/web/RuntimeSessionController.java` · get/update/create | Claw Session 资源使用 sessionId。创建返回 201/Location，GET/更新采用 ETag/If-Match；这些是 Session 事实，当前无条件请求目标见 §8.12，Schedule 不提供 ETag。Schedule 创建尚无 Session 关联，不返回 sessionId。 |

此前在 Mate 示例 Controller/Service/Mapper、`src/main/java`、resources 与 POM 范围，未观察公司认证适配、租户范围、Chat 映射或调度配置服务；这是历史样例边界，不推断其他部署。当前 [Claw 配置设计](configuration.md) 只要求其自身取得可信调用范围并校验绑定，具体适配待接线，不用读取 Header 代替认证证据。

配置主基线采用 2026-09-29 重读的 Claude [Create Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/create)、[Update Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/update)及 [Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)。当前已确认目标是：schedule 可省略，省略时只保存配置；提供 schedule 后创建即登记自动计划；运行由显式试运行或后续定时触发发起，保存本身不执行。输入为单条 user.message，首版仅支持文本，不支持附件；Cron 采用 Spring 六字段。省略保持、schedule:null 清除与嵌套整体替换沿用配置规则；缺少环境选择及历史版本 pin 仍是能力差距。active 的自动运行承诺需以运行链路可用为发布前提。当前响应及并发字段以[创建响应对齐](configuration.md#creation-response-review)为准，不从公开文档缺少描述推断 Claude 内部没有保护。

本节没有运行前后端产品测试、数据库或身份联调；测试要求见配置文档。现有 Spring/MyBatis/Jackson 可支撑该配置切片，无新增直接依赖；完整传递依赖图未重跑。

<a id="spring-scheduling-evidence"></a>

### 8.1 Spring 与 JDK 调度边界核验

2026-09-30 补充核对官方文档，并显式读取 Java `553dcd5e2ff682f9684810a043b442b37a02e54a` 的下列路径。该范围解释[主设计的 Spring 使用方式](README.md#spring-scheduling)和[六字段配置契约](configuration.md#spring-cron-contract)，不升级其他 Agent 基线或模块的历史提交。

| 来源与版本 | 已观察事实与适用边界 |
|---|---|
| Java 同提交的 [CronEngine.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/engine/CronEngine.java#L62)；`start`（62）、`scheduleJob`（121）、`executeAndReschedule`（185）、`computeNextDelay`（301） | `start` 建立 JDK 单线程 ScheduledExecutorService；`scheduleJob` 取消旧 Future、算出下一次延迟后注册一次回调；定时回调同步执行并重装下一次；`computeNextDelay` 用 Spring CronExpression.parse/next 与 ZonedDateTime 算时间。当前实现是 JDK 调度加 Spring 时间计算，没有使用 @Scheduled 或 TaskScheduler 注册每条 Job。 |
| Java 同提交的 [CronSchedule.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/model/CronSchedule.java#L26)；`CronExpr`；[modules/cron/pom.xml](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/pom.xml#L35)；`spring-context` | 既有 CronExpr 保存 expression 与可空 timezone，模块已直接依赖 spring-context。目标继续使用其六字段语法；新 HTTP 的 timezone 可省略并默认 Asia/Shanghai，保存、回显有效值，规则由配置契约维护；旧节点默认时区不传播为目标规则，旧工具迁移另定，不需要新增 Maven 依赖。 |
| [Spring Task Execution and Scheduling](https://docs.spring.io/spring-framework/reference/integration/scheduling.html)，2026-09-30 读取时页面为 7.0.9 | 官方分别提供 @Scheduled 方法声明与 TaskScheduler/Trigger 编程式注册；前者适合应用预定义的固定任务，后者适合按运行期配置装配任务，CronTrigger 可承载 Cron 规则。此处是框架能力与场景选型依据，不证明 CampusClaw 已采用这些入口。滚动 7.x 文档不能冒充本地 6.2.6 的完整行为核验。 |
| [CronExpression 6.2.x Javadoc](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/scheduling/support/CronExpression.html)，读取时为 6.2.19；`parse`、`next` | 定义秒、分、时、日、月、星期六字段及 0/7 为周日；说明名称、范围、步长、日/星期扩展和宏。它是 6.2 分支公开契约，不是本地 6.2.6 二进制；产品开放范围由配置契约明确，不因解析器能接受就自动扩展输入。 |
| [JDK 21 ScheduledThreadPoolExecutor](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ScheduledThreadPoolExecutor.html) | 延迟任务到期后才有执行资格，但不保证何时实际开始。六字段提供秒级表达能力，不保证模型或业务在目标秒精确启动；线程占用、负载与执行准入仍影响开始时间。 |

表达式边界小验证使用本地 Spring context/core/jcl 6.2.6，在 JDK 21 通过 `java --class-path <本地依赖> --source 21 /dev/stdin` 执行临时片段，基准为 `2026-09-30T10:00:00+08:00[Asia/Shanghai]`：

| 验证输入 | 实际结果与可证明范围 |
|---|---|
| Spring `0 0 8 1 * 1` | 下一次为 `2027-02-01T08:00+08:00`，证明该样例要求日与星期同时匹配。 |
| Spring `0 0 8 * * MON-FRI` | 下一次为 `2026-10-01T08:00+08:00`；工作日只按星期匹配，不排除法定节假日。 |
| Spring `30 0 8 * * *` | 下一次为 `2026-10-01T08:00:30+08:00`，验证指定秒位。 |
| Spring `*/10 * * * * *` | 下一次为 `2026-09-30T10:00:10+08:00`，验证秒字段步长。 |
| Spring `0 0 8 1 * MON` | 下一次为 `2027-02-01T08:00+08:00`，验证名称形式的日/星期同时匹配。 |
| Spring `0 8 * * 1-5` 与 `0 0 8 * * * 2026` | `isValidExpression` 均为 false，验证拒绝五字段和额外年字段。 |
| 本地候选探针 cron-utils 9.2.1 的 UNIX `0 8 1 * 1` | 下一次为 `2026-10-01T08:00+08:00`，与上述 Spring 样例不同；仅用于展示不能直接补秒迁移的反例，不证明 Claude 服务端采用该库。该探针与其 slf4j-api 2.0.17 未加入产品依赖。 |

临时片段未保存为仓库测试，以上不是完整方言兼容、DST、实际定时精度或产品集群验收。已确认的是沿用 Spring 六字段；@Scheduled 固定任务与 TaskScheduler 动态任务是可用的框架方式，当前源码仍采用 JDK 调度器。多实例领取、持久游标、忙跳过和恢复不补跑由[执行专题](execution.md)单独维护，均待实现；不能从时间解析器的选择推导这些运行策略已经存在。

<a id="first-fire-evidence"></a>

### 8.2 首次触发与周期推进的基线核验

2026-09-30 重新确认以下四个开源上游的默认分支并隔离 fetch，读取明确提交，不修改其用户工作树。托管产品同日重新读取官方文档。本节仅升级首次时间、周期基准和入口归属的证据；不把旧版完整生命周期、权限或恢复结论一并升级。默认分支快照不是稳定发布保证。

| 基线 | A14 历史提交 → 本节核验提交 | 范围与变化 |
|---|---|---|
| DeepSeek Harness | master `c36a83ff6bb95e3f82cf79f9be7c724270a8aa61` → `639ed015397290b3745d163aafe02ffee4aa3f84` | `0.1.7-alpha.1` → `0.2.0-rc.2`；Schedule 仍为默认关闭的 experimental bundle。every 首次等待间隔、后续固定时间表的原则未变；最小间隔由历史 300 秒变为 60 秒。 |
| pi | main `95fbc04997eaee961eb673fa7923e9220609ebd5` → `1b347794e2a630e4359f2584f4eea388145d0ddf` | 只核验 experimental/pico3 的进程 Job，不等于通用 Agent 定时 HTTP 产品；首次与后续间隔分别计算。旧、新提交的 job.ts 均将 every 直接加到毫秒时钟，历史“秒数”表述不成立。 |
| OpenCode | dev `fe3f3a41f79ad292cc3c7c629567385a20ec5130` → `2fa3363c924c5c3e367b84a87ae478296a0ed59b` | 官方 GitHub 定时入口继续消费 GitHub Actions schedule 事件；不能把外部 Cron 的首次与周期计算归给 Runtime。 |
| Codex harness | main `a1f40f3f1326eff7c81b860a4f4e27c1be186e10` → `bcd6d9ab6b9f26f85d76d0c680b3f88b367bffa0` | 只核验计划插件元数据、事件来源归类及相关入口；本次范围未发现可据以判断首次触发或固定间隔推进的执行实现。 |

**DSH：首次等一个间隔，后续保持固定时间表。** `every_seconds` 为整数且至少 60 秒，没有 startAt/anchorAt；工具额外字段白名单不允许调用方自带起点。`ScheduleService.create` 在进入串行队列前取 t0，`createEveryScheduleRecord` 计算首次为 `t0 + every_seconds × 1000`。这不是“持久化完成后再等一个间隔”：排队过久时保存完成可能已经到期。下一次已保存时刻为 s、间隔为 I 时，`resolveEveryOccurrence` 取 `s + floor((now-s)/I) × I` 作为最新到期项，再推进一个间隔；不读取 Agent 的完成时间。

同间隔或只改内容保留原计划；改间隔按更新进入队列槽位时的新基准重算。记录返回 everySeconds 与规范化 UTC scheduledAt，后者是会推进的计划游标，不是独立且不可变的首次 startAt。工具视图另有 scheduled/overdue 状态和 host 投递模式，不能当作 Claw 的字段契约直接复制。

| DSH 路径与符号（均固定上述新提交） | 证明范围 |
|---|---|
| [packages/schedule/schedule/src/types.ts:363](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/types.ts#L363)、[tools.ts:222](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/tools.ts#L222) | 创建输入与额外字段限制。 |
| [src/index.ts:249](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/index.ts#L249) · create；[src/domain.ts:1355](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/domain.ts#L1355) · createEveryScheduleRecord | 创建时钟取样点与首次计划计算。 |
| [src/domain.ts:789](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/domain.ts#L789) · resolveEveryOccurrence；[src/update.ts:86](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/update.ts#L86) · changedRecord；[src/index.ts:370](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/index.ts#L370) · update | 固定相位、最新到期项及修改间隔的起点处理。 |
| [src/types.ts:47](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/types.ts#L47) · EveryScheduleRecord；[src/domain.ts:1850](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/domain.ts#L1850) · scheduleView | 持久记录与工具视图，不声明 Claw 响应兼容。 |

**pi：首次默认不等待，后续结束后再计时。** `JobInput` 的 notBefore 为 Unix 毫秒时间戳，every 为毫秒间隔。`initial` 使用 `notBefore ?? now`，首次不读取 every：调度器已激活、依赖与执行资格满足且存在 ProcessHost 时，省略 notBefore 即开始；未来 notBefore 先等待，过去值不增加等待。`poll` 观察到进程结束并记录输出后，以 `runtime.now() + every` 设置下次等待，因此是固定延迟。ProcessStatus 没有真实结束时间戳，不能把“观察结束后的当前时间”误写成精确的进程退出时刻。

源码为 [packages/agent/src/harness/pico3/kinds/job.ts:4](https://github.com/badlogic/pi-mono/blob/1b347794e2a630e4359f2584f4eea388145d0ddf/packages/agent/src/harness/pico3/kinds/job.ts#L4) 的 JobInput，`initial`（64）、`poll`（131，下一次计算在166）；[harness.ts:150](https://github.com/badlogic/pi-mono/blob/1b347794e2a630e4359f2584f4eea388145d0ddf/packages/agent/src/harness/pico3/harness.ts#L150) 的 Date.now 默认时钟和227附近的毫秒 sleep；[types.ts:935](https://github.com/badlogic/pi-mono/blob/1b347794e2a630e4359f2584f4eea388145d0ddf/packages/agent/src/harness/pico3/types.ts#L935) 的 ProcessStatus；[index.ts:1](https://github.com/badlogic/pi-mono/blob/1b347794e2a630e4359f2584f4eea388145d0ddf/packages/agent/src/harness/pico3/index.ts#L1) 的 experimental 声明。JobResult 返回退出码、次数及输出，内部 untilMs checkpoint 不是面向用户的 Schedule 资源。

**OpenCode：由 GitHub Actions 决定 Cron 时间。** [packages/web/src/content/docs/github.mdx:124](https://github.com/anomalyco/opencode/blob/2fa3363c924c5c3e367b84a87ae478296a0ed59b/packages/web/src/content/docs/github.mdx#L124) 配置 schedule Cron 与 prompt；[packages/opencode/src/cli/cmd/github.handler.ts:391](https://github.com/anomalyco/opencode/blob/2fa3363c924c5c3e367b84a87ae478296a0ed59b/packages/opencode/src/cli/cmd/github.handler.ts#L391) 读取外部 eventName，501附近新建 Session。所查 server/core/schema/protocol 范围未发现用户任务的 cron/startAt/intervalSeconds/notBefore 字段；内部清理、刷新和重试使用的 Effect Schedule 不构成用户定时任务证据。[GitHub 官方 schedule 文档](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)声明五字段 POSIX、默认 UTC/可选 IANA timezone、最短五分钟和可能延迟；不据此定义 Claw 的 every 默认起点。

**Codex：产品有计划，所查开源元数据不决定首次行为。** [codex-rs/app-server-protocol/src/protocol/v2/plugin.rs:777](https://github.com/openai/codex/blob/bcd6d9ab6b9f26f85d76d0c680b3f88b367bffa0/codex-rs/app-server-protocol/src/protocol/v2/plugin.rs#L777) 的 ScheduledTaskSummary/ScheduledTaskSchedule 声明 hourly/daily/weekdays/weekly，只是插件摘要；core-plugins/src/remote.rs 的648/1525附近与 app-server/src/request_processors/plugins.rs:2310接收和投影元数据。[codex-rs/history/src/heartbeat.rs:23](https://github.com/openai/codex/blob/bcd6d9ab6b9f26f85d76d0c680b3f88b367bffa0/codex-rs/history/src/heartbeat.rs#L23) 的 from_turn_trigger 只归类宿主触发来源。本范围未发现 first-fire、RRULE 下一次计算或固定间隔推进，不能推断开源内核负责调度。

同日重新读取的[OpenAI Scheduled tasks 官方文档](https://learn.chatgpt.com/docs/automations)公开 RRULE、自定义周期及聊天内分钟间隔任务；每次可新建聊天或继续原聊天。文档没有精确定义省略首次时间后的计算公式，也未建立与 Claw intervalSeconds/startAt 同形的 HTTP 契约；不把产品支持 RRULE 推断为特定默认锚点或 fixed-delay 算法。

**Claude Managed Agents：只声明 Cron，独立手动运行。** 同日重读[创建接口](https://platform.claude.com/docs/en/api/http/beta/deployments/create)、[资源模型](https://platform.claude.com/docs/en/api/http/beta/deployments)及[Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)：schedule 为可空的 cron/expression/timezone，无 every/startAt；创建响应提供 upcoming_runs_at 供查看计划时刻，执行可能稍晚；显式 run 才用于即时试运行。它能支持“保存配置与试运行分开”的产品选择，不能支持 every 首次时间的结论。

当前 Claw 配置仅支持 Cron；本节保留基线首次时间与间隔推进的历史源码事实，不将 every/startAt 作为现行 Claw 字段。基线间首次执行默认值不同，不能把任何一种默认值当作统一行业规则。

本节为静态源码与公开文档核验。示例时间是按源码公式推导，未执行这些基线的产品任务或测试，未修改实现仓；完整运行、停机与企业调度验收仍需独立证明。

<a id="timezone-evidence"></a>

### 8.3 时区输入与默认来源的基线核验

2026-09-30 当次重新确认默认分支并隔离 fetch，读取以下明确提交；这次只升级时间字段、时区解析与宿主边界，不改写 §8.2 及其他模块的历史 SHA。默认分支快照不等于稳定发布，DSH Schedule 与 pi Pico v3 仍为实验能力。

| 基线 | 前次提交 → 本次提交 | 核验范围与变化 |
|---|---|---|
| DSH | master `639ed015397290b3745d163aafe02ffee4aa3f84`，未变 | `0.2.0-rc.2`；Schedule 默认关闭，读取工具 Schema、时间解析、记录与更新。 |
| pi | main `1b347794e2a630e4359f2584f4eea388145d0ddf` → `ee602414c703be8da722ec56de7f2399e62581ac` | 本次核验的 experimental/pico3 无 diff；只证明进程 Job 不接收日历时区，未发现更直接的内置 Cron 用户契约。 |
| OpenCode | dev `2fa3363c924c5c3e367b84a87ae478296a0ed59b`，未变 | 官方 GitHub 定时入口与 handler；时区由 GitHub Actions 决定。 |
| Codex harness | main `bcd6d9ab6b9f26f85d76d0c680b3f88b367bffa0` → `d42056091aded7feb1d88ac7e83972108b2aa478` | 插件计划摘要与投影等核验文件无变化；不能据其推断宿主时区默认值。 |

**DSH 显式区分日历与绝对时间。** Cron 创建与替换均要求完整 expression/time_zone，无默认时区，不回退主机时区。time_zone 接受 UTC 或合法 IANA Area/Location，经 Intl 校验并规范化；保存、回显规范化 timeZone 与 UTC scheduledAt。at 字符串必须自带 Z 或数值偏移；另有 `{date,time,time_zone}` 本地时间对象形式，三项必填，解析后只保存 UTC scheduledAt，不保留原 offset/时区。every_seconds 无 timezone、无调用方提供的 startAt，保存间隔与 UTC scheduledAt。

证据：同一提交的 [tools.ts:370](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/tools.ts#L370) 的 Cron/at Schema；[domain.ts:332](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/domain.ts#L332) 的 parseOffsetInstant、370 起 canonicalizeTimeZone；[domain.ts:1292](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/domain.ts#L1292) 的 createAtScheduleRecord、1355 起 every、1483 起 Cron 记录；[domain.ts:1829](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/domain.ts#L1829) 的 parseCronInput；[update.ts:122](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/schedule/schedule/src/update.ts#L122) 复用相同解析器。旧值往返的辅助证据是同文件 changedRecord：at/after 原时间未变可跳过未来校验，新设过去时间拒绝；这不等于 DSH 支持 Claw 的 every 过去起点契约。

**pi 不解析日历时区。** [JobInput](https://github.com/badlogic/pi-mono/blob/ee602414c703be8da722ec56de7f2399e62581ac/packages/agent/src/harness/pico3/kinds/job.ts#L4) 时间相关字段为 notBefore/every 数值，无 timezone；[harness.ts:150](https://github.com/badlogic/pi-mono/blob/ee602414c703be8da722ec56de7f2399e62581ac/packages/agent/src/harness/pico3/harness.ts#L150) 默认时钟为 Date.now，227 起按 untilMs 与 Date.now 的差等待；job.ts 的 initial/poll 使用该毫秒时钟。notBefore 是 epoch 毫秒，every 是毫秒时长，不能将“没有时区字段”表述成“日历时区默认 UTC/上海/系统时区”。

**OpenCode 使用外部调度时区。** [github.mdx:124](https://github.com/anomalyco/opencode/blob/2fa3363c924c5c3e367b84a87ae478296a0ed59b/packages/web/src/content/docs/github.mdx#L124) 的官方例子注明 UTC；[github.handler.ts:401](https://github.com/anomalyco/opencode/blob/2fa3363c924c5c3e367b84a87ae478296a0ed59b/packages/opencode/src/cli/cmd/github.handler.ts#L401) 消费 schedule 事件，handler 与 action.yml 没有独立时区参数。同日重新核对 [GitHub Actions schedule 文档](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)：默认 UTC，也允许可选 IANA timezone。该默认值归属 GitHub，不是 OpenCode Runtime 的时区契约。

**Codex 的公开资料不足以确定默认来源。** [plugin.rs:777](https://github.com/openai/codex/blob/d42056091aded7feb1d88ac7e83972108b2aa478/codex-rs/app-server-protocol/src/protocol/v2/plugin.rs#L777) 的 ScheduledTaskSummary/ScheduledTaskSchedule 未声明 timezone；同次检查 core-plugins/src、app-server/src/request_processors/plugins.rs、history/src/heartbeat.rs，所见为元数据与来源投影，未见时区解析。OpenAI Docs 的 [Scheduled tasks](https://learn.chatgpt.com/docs/automations) 同日重新搜索并读取，公开自定义计划和 RRULE，但未规定 timezone 字段是否必填或默认来源，不能用未公开细节支持 Claw 默认上海或节点时区。

这些证据说明不存在统一行业默认时区。当前 Claw 仅支持 Cron，timezone 可省略并默认保存、回显 Asia/Shanghai；绝对时刻响应统一 UTC、秒级，精确规则由[配置契约 §3.4](configuration.md#34-时区选择与确认边界)维护。其他基线的 at/every 字段保留历史证据归属，不进入 Claw 当前契约。本节仅静态读取源码和官方契约，未执行产品任务或时区测试。

<a id="runtime-time-format-evidence"></a>

### 8.4 既有 Session 与完整事件的时间表示

2026-09-30 重读已登记的 Java `553dcd5e2ff682f9684810a043b442b37a02e54a` 快照及当前设计契约，仅核验以下时间生成和响应格式；未更新上游快照，不称为当次最新实现，未运行 HTTP 产品测试。

| 范围 | 已观察事实 | 路径与关键符号 |
|---|---|---|
| Session 创建 | 字段为 createdAt，服务端以 UTC 生成，VO 使用 OffsetDateTime 并按字符串序列化；所查创建链路未固定三位小数 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionService.java` · newSession（117）、now（138）；同 runtimeapi 根 `session/RuntimeSessionResponseAssembler.java` · createView（30）、`vo/CreateSessionResponseVO.java` · createdAt（37） |
| 2026-09-30 创建契约 | 示例为 `2026-08-15T11:30:00Z`，表示 UTC；该例不证明禁止小数秒，也不证明固定毫秒 | [01-create-session.json](../01-CampusClaw多Agent运行时/接口契约/操作/01-create-session.json) · result.createdAt（58）；[Session 接口展示](../01-CampusClaw多Agent运行时/chat-api-review.html) |
| 固定快照的完整公共事件实现 | 实现通过 appendInstant(3) 输出 UTC 三位毫秒；当前目标契约已改为秒级 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/CommittedEventProjection.java` · EVENT_TIME_FORMATTER（68）、project（91） |

Claw 的目标已统一为秒级：包含 Session createdAt/updatedAt、完整事件 createdAt 和定时任务时间。源码中的毫秒规范化与输出仍需调整；共同的写入、回读和存储边界由[秒级时间一致性](../01-CampusClaw多Agent运行时/time-contract.md)维护，不能把本节历史源码观察改写为已实现目标。

<a id="claude-time-precision-evidence"></a>

### 8.5 Claude 时间格式的公开证据

2026-10-02 重新读取公开 Beta [Create Session](https://platform.claude.com/docs/en/api/http/beta/sessions/create) 与 [Create Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/create)。两者 created_at/updated_at 示例均使用 `2026-03-15T10:00:00Z`，未给出固定毫秒位数或只支持秒级的保证。没有调用实际 API，也没有公开服务端源码或数据库精度证据。CampusClaw 借鉴整秒表示并明确秒级限制，属于产品约束；不得据示例断言 Claude 的内部存储也是秒级。

<a id="target-file-evidence"></a>

### 8.6 名称、Cron 范围、文件与执行目标（2026-10-04）

本节仅升级名称/时间类型、定时 Session 目标和 Claw 文件链路。开源仓均当日确认默认分支并隔离 fetch/按明确 commit 读取；托管产品重新读取官方文档，不推断内部实现。其他小节的提交与路径保留历史归属。本次静态核验未运行产品任务或上传端到端测试。

| 基线 | 前次相关证据 → 本次基线 | 核验范围与变化 |
|---|---|---|
| Claw | main `553dcd5e2ff682f9684810a043b442b37a02e54a` → 同提交 | 当日重新 fetch；只升级文件引用、上传入口检索、前端附件、Read 与旧 CronPayload 的证据日期；其余 Cron/Runtime 观察仍属原小节 |
| pi | main `ee602414c703be8da722ec56de7f2399e62581ac` → `200387122ca450d6387f033949423114a270b96c` | 旧 pico3/kinds/job.ts 已不存在；本次读取 agent-session-runtime.ts、agent-session.ts 与 packages/durable。不能替换旧链接 SHA 后继续宣称旧 Job 为现行实现 |
| DeepSeek Harness | master `639ed015397290b3745d163aafe02ffee4aa3f84` → `5badb15009ae1756c3afe0ae0cef1faafc290ccc` | 版本 `0.2.1-alpha.1`；工具入口拆分为 packages/schedule/tool-schedule/src/index.ts；核验原 Session 绑定及冷 Session 恢复投递，不升级其他恢复策略 |
| OpenCode | dev `2fa3363c924c5c3e367b84a87ae478296a0ed59b` → `907b3bc518fa48e90e8ec24dd327d13eee71c36c` | GitHub 文档、Action inputs、handler、Session 协议四条路径无 diff；默认 dev 快照不等于稳定发布 |
| Claude Managed Agents | 官方文档 2026-10-04；Beta | [Create Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/create)、[Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)、[Upload File](https://platform.claude.com/docs/en/api/http/beta/files/upload)：name maxLength=256；可空 schedule 只声明 cron；每次新 Session；POST /v1/files 独立上传，Deployment 文件资源引用 file_id |
| OpenAI 宿主 Scheduled tasks | [官方文档](https://learn.chatgpt.com/docs/automations)，2026-10-04 | 明确独立任务每次新聊天、聊天内计划使用原上下文；支持从 Codex 聊天配置。证明宿主产品两种模式，不证明开源 harness 有同形 HTTP target 或自有调度器；本节未更新 Codex 开源证据 |

**定时目标不是统一的二选一契约。**

| 来源、路径与符号 | 已观察行为及参考边界 |
|---|---|
| DSH [tool-schedule/src/index.ts:475](https://github.com/deepseek-ai/deepseek-harness/blob/5badb15009ae1756c3afe0ae0cef1faafc290ccc/packages/schedule/tool-schedule/src/index.ts#L475)；[schedule/src/index.ts:228](https://github.com/deepseek-ai/deepseek-harness/blob/5badb15009ae1756c3afe0ae0cef1faafc290ccc/packages/schedule/schedule/src/index.ts#L228) · ScheduleService.create（256 写 sessionId） | 工具把 agent.session.id 作为可信目标传入，模型请求不能另选一个 Session |
| DSH [runtime.ts:101](https://github.com/deepseek-ai/deepseek-harness/blob/5badb15009ae1756c3afe0ae0cef1faafc290ccc/packages/schedule/schedule/src/runtime.ts#L101) · resolveAgent/followup/flush；[README:157](https://github.com/deepseek-ai/deepseek-harness/blob/5badb15009ae1756c3afe0ae0cef1faafc290ccc/packages/schedule/schedule/README.md#L157) | 到期解析/恢复 task.sessionId，将 reminder 投递到原 Session；明确不支持跨 Session 投递或每次新建。持久 inbox 投递不表示业务完成；alpha 不能当作稳定企业调度规范 |
| OpenCode [github.handler.ts:501](https://github.com/anomalyco/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/cli/cmd/github.handler.ts#L501) · githubRun/sessionSvc.create；[github/action.yml:7](https://github.com/anomalyco/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/github/action.yml#L7) | GitHub schedule 每次创建新 Session 再 chat；Action 输入没有目标 Session 字段 |
| OpenCode [groups/session.ts:129](https://github.com/anomalyco/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/protocol/src/groups/session.ts#L129) · makeSessionGroup（205 为 prompt） | 普通会话创建和指定 Session prompt 是即时能力，不是定时 target；已查 server/session/tool/schema/protocol 范围未发现同形用户定时配置，v2 仍按源码范围陈述 |
| pi [agent-session-runtime.ts:196](https://github.com/badlogic/pi-mono/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/agent-session-runtime.ts#L196) · switchSession/newSession（226）；[agent-session.ts:2180](https://github.com/badlogic/pi-mono/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/agent-session.ts#L2180) · followUp | 普通会话新建、恢复与后续输入机制；不等于 Cron target 二选一 |
| pi [durable/src/harness/scheduler.ts:160](https://github.com/badlogic/pi-mono/blob/200387122ca450d6387f033949423114a270b96c/packages/durable/src/harness/scheduler.ts#L160) | Harness 内持久任务推进器；所查 core、experimental、durable 与调度相关路径未发现 CampusClaw 式 Cron 配置资源与目标联合类型 |

**Claw fileId 引用不等于文件上传或内容读取。** 以下路径均为 Java `553dcd5e2ff682f9684810a043b442b37a02e54a`；R 表示 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。

| 相对路径与符号 | 已观察能力或缺口 |
|---|---|
| R/runtimeapi/vo/UserMessageContentRequestVO.java · FileRequestVO（71）；UserMessageEventRequestVO.java（35）；modules/common/src/main/java/com/campusclaw/common/constant/ClawConstants.java（122） | 已有 type=file/fileId 引用，32 位十六进制，最多四个、不重复；文本如有须第一块 |
| R/runtimeapi/event/RuntimeEntryCodec.java · userEntry/toUserMessage/toAgentPrompt（377）、文件 ID 文本拼接（421）；RuntimeCommittedEventFactory.java · userMessage（50） | 保存 file_ids 并回显引用；模型输入仅是包含 [File IDs] 的 TextContent，没有下载、解析、文件存在性或长期权限检查 |
| frontend/src/components/ComposerBox.vue（138） | 附件按钮 disabled，提示“暂未接入附件上传” |
| modules、campusclaw、frontend；Runtime/ControlPlane Controller 路由 | MultipartFile、RequestPart、multipart/form-data、upload 检索及控制器映射未发现 Claw 专用上传 HTTP 接口；不推断外部公司文件服务能力 |
| R/tool/read/ReadTool.java · execute（107） | 受管工作区 path 的 UTF-8 文件读取，非 fileId 下载/上传服务 |
| modules/cron/src/main/java/com/campusclaw/cron/model/CronPayload.java · AgentPrompt（21） | 旧 Cron 输入仅 agentId/prompt；新定时消息及附件读取链路待实现 |

同时读取 [M09 附件设计 3.1.0](../../02-服务与接口/01-CampusMate附件服务/README.md)全文及 attachment-api.openapi.yaml 的文件 ID/解析约束：目标上传归属 mate-service，文件不可变绑定单个 Session，跨 Session resolve 拒绝，设计 ID 为 file_<26 alnum>。它标记待实现，外部服务当前实现未核验；与现行 Runtime ID 格式、新建 Session 反复引用同一文件存在未解决的接入差距。本次只记录差距，不修改附件权威契约。

CampusClaw 每次运行固定新建 Session，复用 Agent 定义和纯文本 prompt，首版只接受文本，不提供 target 或定时附件。普通 Session 的文件引用及 M09 上传职责保持；定时跨 Session 文件访问、授权读取和生命周期衔接留待后续附件设计。名称上限 256、仅 Cron 是当前产品约束；Spring 六字段和默认上海时区继续有效，不声称已与 Claude 完全兼容。其他基线的目标差异仅作有日期的事实对照，不改变本产品范围。

<a id="creation-response-evidence"></a>

### 8.7 固定新 Session 与创建响应（2026-10-04）

再次确认 Java 上游默认 main 并隔离 fetch 至 refs/codex-evidence/schedule-response-20261004，提交仍为 `553dcd5e2ff682f9684810a043b442b37a02e54a`。以下只重核 Session 工厂和 HTTP 创建返回，不升级其他模块的历史实现状态。R 为 modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/。

| 路径与关键符号 | 已观察实现及目标含义 |
|---|---|
| R/session/AgentSessionFactory.java · create（69–104）、configureAgent（107–120） | prepare 已有 request.agentId，每次创建独立 Agent 执行对象和 ManagedAgentSession；不是创建 Agent 定义资源 |
| R/tool/cron/ManagedCronSessionRunner.java · execute（53–72） | 每次由 Session 工厂创建并关闭内存会话；未在该链生成可查询 Runtime Session/Run 关联，新配置调度接线待实现 |
| R/runtimeapi/web/RuntimeSessionController.java · create（56–65）、get（68–77）、update（80–91） | create 返回 201、Location、Content-Language 和 ResultBean；未把内部 View 的 ETag 写入 Header，只有 GET/更新对外返回 ETag |
| R/runtimeapi/session/RuntimeSessionResponseAssembler.java · createView（30–41）；SessionEtagFactory.java（22–27） | 内部创建 View 已生成不透明 ETag，但不能据此宣称客户端创建响应含该 Header；当前目标不对外传递标签，既有实现差距见 §8.12 |
| R/runtimeapi/session/RuntimeSessionService.java · create（64–72）、newSession（117–129）、now（138–139） | 使用既有 agentId，生成新 Session ID、内部 resourceVersion=1；创建/更新时间相同，保存后返回内存快照；当前取时未截秒，秒级仍为目标差距 |
| R/runtimeapi/vo/CreateSessionResponseVO.java（20–38）；SuccessResponseVO.java（19–32）；result/StandaloneResultBeanAdapter.java（17–18） | 创建 Session 返回自身资源和公司包装，没有对外 version。Schedule 当前响应不含 revision；Session 内部版本不构成新增公共字段的依据，见 §8.8 |

同日重新读取 Claude Beta [Create Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/create)、[Deployment 模型](https://platform.claude.com/docs/en/api/http/beta/deployments)和[Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)：

- 创建参考页成功码为 200，返回 Deployment；Agent 引用包含 id/type/version。配置可复用，每次运行创建新的 Session。不能将资源 agent 字段理解为每次新增一个 Agent 定义。
- schedule 响应模型除 type/expression/timezone 外还声明可选 last_run_at、upcoming_runs_at；后者最多五个计划时刻，暂停时仍可表示假设恢复后的匹配，归档为空，不是准点启动承诺。
- last_run_at 文本称最近一次定时运行实际开始时间，手动运行不更新；同段还写“Null until one completes”，公开文本未在此明确该完成点的内部写入机制，不能推导为业务成功时间。自动生成创建示例中的非空历史时间或 paused_reason 不代表新资源必须具有运行历史。
- status 为 active/paused，归档由 archived_at 区分；普通响应不采用公司 ResultBean。没有据此推断 Claude 服务端是否使用内部版本或幂等机制。

当前 Claw 固定新会话是已确认的产品范围；移除 target 及其策略类/配置列，运行后生成的 sessionId 仍保留在 Run。创建响应及时间摘要以[创建响应对齐](configuration.md#creation-response-review)为准，公开基线补充见 §8.8。创建配置不创建 Session，不返回运行关联；本节未执行产品 API 或端到端测试。

<a id="creation-metadata-credentials-evidence"></a>

### 8.8 创建摘要、元数据与凭据（2026-10-04）

本节当次重新读取下列 Claude Managed Agents 公开 Beta 文档，并重核下述 Claw 凭据链路；只升级响应、metadata 与凭据引用的证据，也不推断服务端表结构、内部版本、加密存储、缓存或代理拓扑。未调用实际 API、保存凭据或执行产品测试。

| 官方来源 | 已核实的公开契约与边界 |
|---|---|
| [Deployment 模型](https://platform.claude.com/docs/en/api/http/beta/deployments) · BetaManagedAgentsCronSchedule、BetaManagedAgentsDeploymentStatus | 响应 schedule 含只读 last_run_at、upcoming_runs_at。前者指最近定时运行实际开始时间，手动运行不更新，归档后保留；其“Null until one completes”用语不能推导为 Agent 业务完成。后者最多五个计划时刻，暂停时仍展示假设恢复后的匹配，归档后为空；不保证准点执行。status 仅 active/paused，归档仍可返回 active，由 archived_at 区分。 |
| [Create Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/create) | metadata 为可选字符串键值映射，最多16组、键最长64、值最长512；示例缺省为 {}。vault_ids 可选、最多50个，绑定新建 Session 可用的已存凭据；不要求创建 Deployment 时重传 secret。公开响应未声明 revision，不证明服务端没有内部并发控制。 |
| [Update Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/update) | metadata 按 key patch：字符串更新、null 删除 key、省略字段保留；vault_ids 整体替换，省略保留，[]/null 清空。文档没有明确 Deployment 改换引用列表是否影响已经创建的 Session，不能与凭据本身轮转混为同一更新语义。 |
| [Create Vault](https://platform.claude.com/docs/en/api/http/beta/vaults/create)、[Create Credential](https://platform.claude.com/docs/en/api/http/beta/vaults/credentials/create)、[Get Credential](https://platform.claude.com/docs/en/api/http/beta/vaults/credentials/retrieve) | Vault 与 Credential 独立管理；auth 支持 mcp_oauth、static_bearer、environment_variable。token/access_token/refresh_token/client_secret/secret_value 为敏感写入值，不在读取响应返回；创建记录不等于已验证下游认证成功。 |
| [Authenticate with vaults](https://platform.claude.com/docs/en/managed-agents/vaults) | workspace 作用域，不等于业务用户隔离；MCP 按 mcp_server_url 匹配并注入。环境变量在沙箱内为不透明占位符，出站时替换真实 secret，当前不支持 self-hosted sandbox。凭据周期重新解析，轮转/归档/删除传播到运行中 Session，无需重启，但未承诺即时撤销或延迟上界。OAuth 配置 refresh 后可刷新，失败有事件。Vault 归档保留审计记录、清除 secret，未来引用失败；现有 Session 继续运行不表示后续仍永久拥有原凭据。 |
| [Credential 模型](https://platform.claude.com/docs/en/api/http/beta/vaults/credentials)、[Update Credential](https://platform.claude.com/docs/en/api/http/beta/vaults/credentials/update) | 环境变量可限制 allowed_hosts 及 header/body 注入位置；unrestricted 仍受 Environment 网络策略约束。secret 可轮转，凭据类型及 MCP URL/secret name 等结构绑定不能任意修改。 |
| [Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments) | 不可恢复的 Session 创建错误，例如归档 Vault，记录失败 Run 并自动暂停；这与 Session 内下游认证失败不同，不能把保存凭据成功或 Deployment 创建成功当作业务授权验证。 |

**Claw 凭据链路重新核验。** 2026-10-04 以 `ls-remote --symref origin HEAD` 确认默认分支 main，隔离 fetch 后完整 commit 仍为 `553dcd5e2ff682f9684810a043b442b37a02e54a`；旧新提交相同，只重核下表及所列目录，未运行产品测试。R 表示 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。

| 仓库相对路径与符号 | 已观察行为 |
|---|---|
| R/runtimeapi/web/RuntimeRequestContext.java:45 · mateCredentials；R/common/client/mate/MateCredentials.java:7；R/runtimeapi/event/RuntimeEventService.java:58 · submit | user.message 捕获本次四 Header 的不可变快照；不验证真实性，确认/中断等不替换原执行凭据；空快照和安全 toString 已有 |
| R/runtimeapi/runtime/RuntimeSessionEngineRegistry.java:205 · createSession；R/tool/mate/MateRemoteToolHandler.java:40 · execute | 凭据进入本次 Session/Child 快照，只在实际工具调用时传给 MateToolClient |
| R/common/client/HttpMateToolClient.java:307、356 · invokeTool/toHeaderInfo；R/common/util/MateRestUtil.java:111 · newRequestBuilder | execute 映射原四 Header；仅发送非空值，不补值、不解析 JWT；发现不带本次业务凭据，最终业务认证由 Mate 决定 |
| R/tool/cron/ManagedCronSessionRunner.java:53 · execute | Cron 与其 Child 明确 MateCredentials.empty()，未保存或借用创建时凭据 |
| modules/ai/src/main/java/com/campusclaw/ai/provider/mate/CampusMateProvider.java:105、143 · auth/eventFlux；R/runtimeapi/model/MateRuntimeModelManager.java:31 · resolveModel；docs/decisions/0109-use-campusmate-only-provider.md | 当前仅内部 CampusMate Provider，ProviderAuth.none()；模型请求不透传业务凭据，上游厂商认证归 CampusMate |

在当次 `modules/coding-agent-cli/src/main/java` 和 `modules/cron/src/main/java` 范围未发现 credentialRef、vaultId 或受管 Vault 链路；2026-10-05 的 Mate 示例补充核验见[§8.17](#schedule-engineering-evidence)，不能外推生产凭据能力。现行 [M03 凭据规则](../02-CampusClaw工具系统/README.md#mate-credential-forwarding)与 [M01 HTTP 凭据规则](../01-CampusClaw多Agent运行时/chat-http-v1-design.md#credential-forwarding)区分普通请求 Header 快照与 Mate 提供的定时执行凭据：秘密只用于本次实际执行，不持久化、不混入发现或模型链路；Mate 新接口待实现。

字段命名专项同日再次重新读取 [Create Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/create)与 [Vaults](https://platform.claude.com/docs/en/managed-agents/vaults)：vault_ids 一项是 Vault ID，Vault 内包含多份 Credential，并非直接 Credential ID 的别名。Java 再次确认默认 main 并隔离 fetch，仍为上述完整提交；相关 modules 范围没有受管凭据资源。credentialIds 属于 Claw 已确认的架构简化，收益是精确选择独立凭据，代价是首版没有集合成员批量管理；这是目标决定，不是当前源码能力。

本节读取的 [RFC 9110 §8.8.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.1)与[§13.1.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.1)只证明 HTTP 强验证器与条件请求的标准语义，不要求产品采用该机制。Schedule 当前不提供 ETag、If-Match 或客户端请求幂等键；数据库更新与重试边界见 §8.12，不据此推断 Claude 的内部机制。

CampusClaw 当前目标（待实现）：schedule 响应加入 lastRunAt/upcomingRunsAt，只读字段不进入创建输入；status 使用小写；响应不提供 revision。metadata 的精确规则由[配置契约](configuration.md#creation-response-review)维护；2026-10-13 起配置不保存凭据引用（移除 credentialIds），不引入 Vault 集合资源。Mate 负责凭据保管、主体授权和按可信目标解析，Claw 只保存引用；[内部接口草案](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md)维护配套 ID、冲突及调用边界，不代表已发布生产接口。

任务不持凭据引用，由 Mate 可信边界按 Agent 绑定、授权主体和目标解析、注入，避免把 secret 写进任务消息、metadata、模型输入或响应；这是 CampusClaw 的架构变更与企业安全约束。已有请求凭据与 Cron 空凭据事实见 §4/J20 和 §2/J08，不证明已有长期委托、刷新或 Vault。保存时校验引用，触发时重新验证当前授权，实际 execute 前按可信目标取用凭据；服务间认证身份不等于业务执行凭据，不能把创建当天的短期登录 Token 当作长期调度凭据。

<a id="schedule-read-evidence"></a>

### 8.9 Schedule 详情、列表与 Run 读取边界（2026-10-04）

本次以 `git ls-remote --symref origin HEAD` 重新确认 Claw 默认分支为 main，并隔离 fetch 到 `refs/codex-evidence/schedule-read-20261004`，完整 commit 仍为 `553dcd5e2ff682f9684810a043b442b37a02e54a`。旧新提交相同；只重核 Cron get/list、Runtime Session get、ListEvents、相关 Controller/VO/Mapper 与错误投影，不改变其他模块的证据日期。未修改实现工作树或运行产品测试。以下 R 表示 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。

| 仓库相对路径与符号 | 已观察实现及读取契约的差距 |
|---|---|
| [modules/cron/src/main/java/com/campusclaw/cron/CronService.java:72](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/CronService.java#L72) · listJobs/getJob；[store/CronStore.java:54](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/store/CronStore.java#L54) · load/getJob（108） | Service 读取本 Host 的 jobs.json，get 全量加载后按 ID 查找；没有分页、条件排序、HTTP 状态或 ETag。文件不存在与读取失败均可得到空列表；新 HTTP 不能据此把存储故障包装成空结果或 404。 |
| [modules/cron/src/main/java/com/campusclaw/cron/tool/CronTool.java:193](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/tool/CronTool.java#L193) · list/status（218）/requireOwnedJob（238）/ownedByCurrentAgent（246）；R/tool/cron/AgentScopedCronToolFactory.java · create（28） | list 仅按绑定 agentId 过滤，输出 id/name/enabled 文本；status 输出 enabled/totalRuns/nextRunAtMs。不限制为 enabled，不提供页码、total、名称筛选或显式排序；其他 Agent 的 Job 与不存在均报相同工具错误。该过滤不证明租户、用户或园区权限。 |
| [modules/cron/src/main/java/com/campusclaw/cron/model/CronJob.java:17](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/model/CronJob.java#L17)；model/CronJobState.java（15） | Job 使用 enabled、createdAtMs 及毫秒运行状态；没有新目标的 metadata、credentialIds、UTC 时间字符串或 upcomingRunsAt。既有模型不是新 Schedule 公共响应 VO。 |
| [R/runtimeapi/web/RuntimeSessionController.java:68](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeSessionController.java#L68) · get；R/runtimeapi/vo/GetSessionResponseVO.java（20） | 已有 GET /campusclaw-service/v1/sessions/{sessionId}，校验标识后返回 200、ResultBean、no-store、ETag 和 Content-Language。VO 含 sessionId/agentId/displayName/modelId/state/thinking/mode/lifetimeUsage/createdAt/updatedAt，不返回内部版本。 |
| [R/runtimeapi/session/RuntimeSessionService.java:89](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionService.java#L89) · get；R/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java · find（70）、beginDeletion（452）；[modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml:41](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml#L41) · findSession | 按 ID 只读查询 t_sessions 与 t_session_stats，不要求 idle 或当前 Agent enabled，也不触发目录 prepare。SQL 没有租户/owner 谓词，不证明上游已授权；已删除主行不再可读。详情查询不依赖启动执行资格，可作为职责边界参考。 |
| [R/runtimeapi/session/RuntimeSessionResponseAssembler.java:44](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionResponseAssembler.java#L44) · getView；R/runtimeapi/session/SessionEtagFactory.java · create（22） | 既有 Session 标签根据 sessionId/resourceVersion 生成，内部版本不透出。Schedule 当前不提供 ETag，不能将现有标签方案当作其目标；Session 的实现迁移差距见 §8.12。 |
| [R/runtimeapi/web/RuntimeExceptionHandler.java:51](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeExceptionHandler.java#L51) · handleRuntimeError/handleUnexpectedError（108）/response（124）/identifierErrorCode（224）；R/runtimeapi/error/RuntimeErrorCode.java（19、23、58）；R/runtimeapi/web/RuntimeRequestContext.java · locale | Session 无效 ID 为 400，缺失为 404，未处理异常为 500；错误保持稳定码和真实 HTTP 状态。该 GET 链未实现租户鉴权；错误响应未统一设置 no-store，现有语言缺省为 en-US，均不能当作 Schedule 候选规则已落地。 |
| modules 中 Controller 路由检索；[R/controlplane/api/RuntimeController.java:56](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/controlplane/api/RuntimeController.java#L56) · schedule；R/controlplane/api/ScheduleRuntimeResponseVO.java（18）；R/runtimeapi/mapper/RuntimeSessionMapper.java | 所查范围无 Schedule 配置详情/列表 HTTP，也无 Session 集合列表方法。已有 /api/v1/runtimes/schedule 选择执行节点并返回 nodeId/host/port/reason，不是定时配置。下述 ListEvents 是某 Session 的事件集合，不证明已有 Session 集合列表。 |

**既有 ListEvents 分页依据。** 同一源码快照的 GET /campusclaw-service/v1/sessions/{sessionId}/events 已采用整数页码；可借鉴分页请求和响应形式，不能把事件排序、Session 存在性或内部历史游标直接移作 Schedule 规则。

| 仓库相对路径与符号 | 已观察实现及复用边界 |
|---|---|
| [R/runtimeapi/web/RuntimeEventController.java:80](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java#L80) · list；[modules/common/src/main/java/com/campusclaw/common/constant/ClawConstants.java:158](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/common/src/main/java/com/campusclaw/common/constant/ClawConstants.java#L158) · DEFAULT_EVENT_PAGE_LIMIT/MAX_EVENT_PAGE_LIMIT | Query 只有本方法声明的可选 limit（Integer）与 page（Long）；page 默认1且至少1，limit 默认50、范围1～200。没有公开 after 或不透明游标参数。成功返回 200、ResultBean、no-store、Content-Language，不生成列表 ETag。 |
| [R/runtimeapi/vo/ListSessionEventsResponseVO.java:18](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/vo/ListSessionEventsResponseVO.java#L18)；[R/runtimeapi/vo/SessionEventResponseVO.java:28](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/vo/SessionEventResponseVO.java#L28) | result 仅含 events 数组及 nextPage（Long，可为 null），没有 total、page、limit 或快照字段。事件元素为 eventId/type/createdAt 加按类型平铺的业务字段，Java details 使用 JsonUnwrapped，不对外套 details/payload；这不是 Schedule 元素模型。 |
| [R/runtimeapi/event/CommittedEventQueryService.java:40](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/CommittedEventQueryService.java#L40) · list/pageOf（57）、normalizeLimit（65）、normalizePage（73）、calculateOffset（81）、nextPage（99） | 计算 offset=(page−1)×limit，多取 limit+1 条；只投影前 limit 条，有额外记录时 nextPage=page+1，否则为 null。不存在 Session 为404；存在 Session 的空集或越界页成功返回 events=[]、nextPage=null；范围错误及整数溢出为400 INVALID_EVENT_LIST_QUERY。分页不依赖 total 查询。 |
| [R/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java:268](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java#L268) · findEventPage；[R/runtimeapi/mapper/RuntimeSessionMapper.java:79](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/mapper/RuntimeSessionMapper.java#L79) · listCommittedEvents；[modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml:191](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml#L191) · listCommittedEvents | 单次读取使用只读 REPEATABLE_READ 事务，先查 Session、检查事件投影完整性，再按 session_id 查询 t_session_events，ORDER BY event_seq 升序、OFFSET/LIMIT。完整性计数不是分页 total；SQL 不含调用者可见范围谓词，也没有跨 HTTP 请求快照。相邻 listTimelineEntries 的 afterSeq/upperBound 属于内部历史读取，不是公开 ListEvents 参数。 |
| [R/runtimeapi/event/CommittedEventProjection.java:91](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/CommittedEventProjection.java#L91) · project；R/runtimeapi/web/RuntimeExceptionHandler.java · handleInvalidParameterType（89）、isEventListRequest（205）；R/runtimeapi/error/RuntimeErrorCode.java（35～36） | 事件经过类型化公共投影；未知类型、映射不完整或读取/投影异常不降为空列表，而返回500 EVENT_LIST_FAILED。查询类型转换或数值范围错误返回400。现有事件 createdAt 仍用 appendInstant(3) 输出毫秒，不能据分页复用把历史实现误写为统一秒级目标已落地。 |

静态读取 [CommittedEventQueryServiceTest.java:65](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/test/java/com/campusclaw/codingagent/runtimeapi/event/CommittedEventQueryServiceTest.java#L65) 的下一页、越界空页、缺失 Session、非法范围和算术溢出断言；本次未运行这些测试。Schedule 候选采用 page/limit 与 result.schedules/nextPage，保留相同的默认50、上限200与 limit+1 判断方式，无需 total；Schedule 的可见范围、筛选和排序仍由配置专题单独确定。

**Claude 公开读取契约。** 下列官方条目本次于 2026-10-04 重新读取；均为 Managed Agents HTTP Beta 文档，没有服务端源码 commit。只记录公开请求和响应，不推断表结构、租户实现、内部排序算法或缓存机制。

| 官方来源 | 公开行为与未声明边界 |
|---|---|
| [Get Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/retrieve) | GET /v1/deployments/{deployment_id} 返回完整 Deployment，包含任务配置、状态及 schedule 摘要；不是一次运行结果。该操作页未声明 ETag/304 或归档后详情读取的具体行为，不据此断言支持或不支持。 |
| [List Deployments](https://platform.claude.com/docs/en/api/http/beta/deployments/list) | GET /v1/deployments；参数为 agent_id、created_at[gte/lte]、include_archived（默认 false）、status（active/paused）、limit（默认20、上限100）及不透明 page。status 不能与 include_archived 组合。响应 data 中每项是完整 Deployment，并返回 next_page；无 total，也未给出默认排序及跨页快照保证。 |
| [List Deployment Runs](https://platform.claude.com/docs/en/api/http/beta/deployment_runs/list)、[Get Deployment Run](https://platform.claude.com/docs/en/api/http/beta/deployment_runs/retrieve) | GET /v1/deployment_runs 与 /v1/deployment_runs/{deployment_run_id} 独立观察 Run。Run 表达 Session 创建结果，不能把它当作 Agent 业务完成状态；配置详情和列表不取代后续 Session 结果读取。 |

**CampusClaw 读取目标（待实现）。** Schedule 详情与列表每个元素均完整返回同一资源模型，包含 prompt、metadata 及 schedule 摘要；删除后详情为404，列表排除，不提供 archivedAt 或 includeArchived。可以复用 HTTP 包装、只读 DTO/VO 投影及异常框架，但可信访问范围、过滤后的分页与下一页判断、确定性排序、删除与读取一致性、动态摘要一致性均需新增接线及验收；当前接口不提供 ETag 或条件读取。既有 Agent 过滤不是鉴权，已有接口只能提供局部实现基础，不能代替定时读取授权与分页接线。读取已保存配置不应启动模型、调用业务工具或换取执行凭据；不返回凭据，执行资格失效与读取资格分开判断。新读取形状由[配置专题](configuration.md)维护，本节不把设计升级为已发布实现。

Run 读取仅作边界记录：现有 CronService.getRecentRuns 与 [CronRunLog.java:70](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/store/CronRunLog.java#L70) 读取本地 JSONL 尾部并反转，读取失败返回空列表；CronTool.runs（225）默认 limit=10、允许1～100并输出文本。这不是新 Run HTTP 的分页、结果关联或可靠性证明；本节不扩写 Run 精确接口。以上为静态源码与官方契约证据，未执行 HTTP、数据库或权限联调测试。

<a id="schedule-type-pause-reason-evidence"></a>

### 8.10 资源类型与暂停原因（2026-10-04）

本次通过 `git ls-remote --symref origin HEAD` 重新确认 Java 默认分支为 main，隔离 fetch 到 `refs/codex-evidence/schedule-type-pause-reason-20261004`，完整 commit 为 `553dcd5e2ff682f9684810a043b442b37a02e54a`，与上次相同。仅复核下列 Session VO 与 Cron 状态；未覆盖工作树、修改实现或运行测试。R 表示 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。

| 仓库相对路径与符号 | 已观察实现及目标差距 |
|---|---|
| [R/runtimeapi/vo/CreateSessionResponseVO.java:20](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/vo/CreateSessionResponseVO.java#L20)；[R/runtimeapi/vo/GetSessionResponseVO.java:20](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/vo/GetSessionResponseVO.java#L20) | 现有 Session 创建与详情 VO 无顶层 type；这是既有资源风格，不禁止新的 Schedule 资源显式标识类型。本次仅补 Schedule 字段，不改写 Session 已发布形状。 |
| [modules/cron/src/main/java/com/campusclaw/cron/model/CronJob.java:17](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/model/CronJob.java#L17)；[model/CronJobState.java:15](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/model/CronJobState.java#L15) | Job 使用 enabled，状态包含运行时间、lastRunStatus、consecutiveErrors 和 totalRuns；没有独立暂停原因，也没有新 Schedule 公共资源 type。 |
| [modules/cron/src/main/java/com/campusclaw/cron/CronService.java:80](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/CronService.java#L80) · enableJob/disableJob（90）；[engine/CronEngine.java:239](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/engine/CronEngine.java#L239) · recordJobOutcome | 手动禁用与连续错误自动禁用均最终写 enabled=false，没有持久区分人工暂停和错误暂停。不能通过 enabled 或当前错误次数可靠还原任务为何处于暂停状态。 |
| [modules/cron/src/main/java/com/campusclaw/cron/model/CronRunRecord.java:17](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/model/CronRunRecord.java#L17) | errorCode/errorMessage 归属单次运行；它们不等价于任务当前暂停原因，不能把最后一个 Run 的错误直接冒充 pausedReason。 |

**Claude 公开契约。** 2026-10-04 重新核验 [Deployment 模型](https://platform.claude.com/docs/en/api/http/beta/deployments)、[创建参考页](https://platform.claude.com/docs/en/api/http/beta/deployments/create)及[调度指南](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)。这些是 Managed Agents HTTP Beta 官方文档，没有服务端源码 commit，不证明内部存储或暂停事务实现。

- Deployment 顶层 type 固定为 deployment，是资源类型标识，与 schedule.type 的 cron 及初始事件 type 的 user.message 分属不同层。
- 模型说明 paused_reason 仅在 status 为 paused 时非 null；原因分 manual 和 error，自动暂停的 error 对象表达导致暂停的错误，其类型对应 Deployment Run 的 error.type。恢复会清空 paused_reason；这不表示历史 Run 错误也被清除。
- 创建参考页包含 status=active 却同时给出 manual 暂停原因的示例，与模型条件和调度指南的恢复语义冲突。该示例不能作为 active 时返回非空暂停原因的设计依据；也不能据此断言真实服务会返回这个组合。

**CampusClaw 已确认目标（待实现）。** 创建、详情、列表元素和更新使用同一完整资源，顶层增加只读 type，固定值为 schedule；增加只读 pausedReason。新建 active 时 pausedReason=null，手动暂停为 manual 判别对象，error 判别对象用于表达错误暂停并包含安全 error 对象，恢复 active 后清空原因；是否由运行失败自动触发整个 Schedule 暂停仍待确认，不能从响应形状推导自动状态转换。请求不能写入这两个资源只读字段；message.type 和 schedule.type 的原有输入语义不变。

type 属于资源表达的产品约束，便于脱离请求路径识别资源，不表示增加调度种类。pausedReason 补齐暂停原因的可观察性，是状态模型的架构增量：应随当前暂停状态保存并投影，不以普通 GET 临时拼接最后一次 Run 错误，也不返回原始异常、凭据或敏感业务参数。精确响应由[配置专题](configuration.md#creation-response-review)维护；是否自动暂停的决策与错误映射分开，当前不继承旧 Cron 连续失败三次自动禁用。Schedule 删除成功返回完整配置回执及最后暂停原因，随后不再提供读取；不另设归档原因模型。

<a id="schedule-update-evidence"></a>

### 8.11 配置更新与字段省略（2026-10-04）

本次通过 `git ls-remote --symref origin HEAD` 重新确认 Java 默认分支 main，隔离 fetch 到 `refs/codex-evidence/schedule-update-20261004`，完整 commit 仍为 `553dcd5e2ff682f9684810a043b442b37a02e54a`。旧新提交相同；只核验下列 Session 更新、Cron 存储与相关路由，不改变其他范围的证据日期。未覆盖工作树、修改实现或运行测试。R 表示 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。

| 仓库相对路径与符号 | 已观察实现及 Schedule 复用边界 |
|---|---|
| [R/runtimeapi/web/RuntimeSessionController.java:80](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeSessionController.java#L80) · update；R/runtimeapi/session/RuntimeSessionResponseAssembler.java · getView（44） | POST /campusclaw-service/v1/sessions/{sessionId} 接收 If-Match 与 UpdateSessionRequestVO；成功为200，返回完整 GetSessionResponseVO、ETag、no-store、Content-Language 和 ResultBean。此链没有 Idempotency-Key 结果保存或重放机制。 |
| [R/runtimeapi/vo/UpdateSessionRequestVO.java:26](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/vo/UpdateSessionRequestVO.java#L26) · readDisplayName/readModelId/readThinking/readMode、rejectUnknownField（85）、isNonEmptyUpdate（91） | 仅接收 displayName/modelId/thinking/mode；Submitted 标记区分省略，拒绝显式 null、类型错误、重复/未知字段与空请求。可复用字段出现性识别；Schedule 的 description/schedule 清空、metadata 按键删除和数组替换需单独实现。 |
| [R/runtimeapi/session/RuntimeSessionUpdateService.java:98](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionUpdateService.java#L98) · update/prepare（117）、requireStrongEtag（190）、requireObservedVersion（207）；R/runtimeapi/error/RuntimeErrorCode.java（23～46） | 先检查请求、单个强 If-Match、资源存在与当前标签，再准备配置；缺标签428、格式错误400、不匹配412、资源缺失404。拒绝弱标签、标签列表与 * 覆盖。业务/未知失败保持真实 HTTP 状态；本链不是 Schedule 的鉴权或幂等实现。 |
| [R/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java:341](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java#L341) · updateSession/rejectUnifiedUpdate（368）、mergeUpdate（382）、markConfigurationUpdated（645）；[modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml:63](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml#L63) · lockSessionForUpdate、updateSessionConfiguration（284） | 事务内 FOR UPDATE 后重查版本并合并；实际变化一次更新配置、版本和时间并追加配置事件。同值返回 UNCHANGED，不改版本/时间。提交执行配置要求 Session idle，仅改名称没有该限制；不能据此规定 Schedule 有在途 Run 就不允许改配置。 |
| [R/runtimeapi/session/SessionEtagFactory.java:22](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/SessionEtagFactory.java#L22) · create | 既有标签基于 sessionId/resourceVersion，不公开内部版本数字；该实现不再是 Schedule 目标，当前无客户端条件令牌及请求回执重放规则见 §8.12。 |
| [modules/cron/src/main/java/com/campusclaw/cron/store/CronStore.java:112](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/store/CronStore.java#L112) · updateJob/saveUnsafe（141）；modules/cron/src/main/java/com/campusclaw/cron/tool/CronTool.java · INPUT_SCHEMA（42）；modules/cron/src/main/java/com/campusclaw/cron/CronService.java（58～101） | Store 按 ID 整条替换 CronJob 并重写文件，不是公共部分更新，不定义省略/null、版本冲突或找不到回执；写入 IOException 仅记录。CronTool 没有 update action，Service 的 enable/disable 不构成配置更新契约。 |

在 `modules/coding-agent-cli/src/main/java` 与 `modules/cron/src/main/java` 所查路由中仍无新 Schedule HTTP。R/controlplane/api/RuntimeController.java 的 schedule（56）是 /api/v1/runtimes/schedule 执行节点选择，不是定时配置更新。

**Claude 公开更新契约。** 2026-10-04 重新读取 [Update Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/update)：POST /v1/deployments/{deployment_id} 省略字段保留，成功200返回完整 Deployment。agent 字符串重新绑定当时最新版本，不能为 null；description 空值/null 清除；initial_events 与 schedule 整体替换，schedule:null 移除自动计划。metadata 按 key patch，但其顶层类型虽然允许 null，正文没有明确 null 的效果，不把它解释为清空所有键；vault_ids 用 [] 或 null 清空。该 Beta 页面未声明 If-Match 或 Idempotency-Key；这不证明其内部没有保护。响应示例中的 active/manual 组合与模型条件冲突，沿用 §8.10 的证据边界，不照搬该组合；不推断服务端事务或表结构。

**CampusClaw 更新目标（待实现）。** 精确契约由[配置专题 §4.5](configuration.md#update-schedule-review)维护，沿用完整资源、只读字段和无客户端条件令牌规则。更新在数据库事务内锁定最新记录、合并本次提交字段并提交，不进行客户端版本比较或成功请求回执重放；重试边界见 §8.12。上述 Session 能力只提供锁内合并等局部基础；Schedule 权限、原子写入及与暂停/到期受理的协调仍需新增接线，源码比较不等于更新接口已经实现。

<a id="schedule-header-free-contract"></a>

### 8.12 无客户端条件令牌与数据库更新边界（2026-10-04）

**CampusClaw 已确认的产品约束（待实现）。** 所有 Schedule 接口均不要求或提供 If-Match、Idempotency-Key 及配套 ETag，不在 body/query 中换名提供 version、revision、requestId 等承担相同职责的客户端令牌。该取消范围覆盖创建、详情、列表、更新及后续暂停、恢复、删除、手动运行和 Run 读取；真实资源关联 ID 与内部运行去重键不属于被取消的客户端请求令牌。同一产品约束也适用于其他 Claw 接口，既有 Session 源码中的条件更新应作为迁移差距记录，不能因本节更新而声称代码已完成迁移。

正常修改以数据库记录为权威：在可信调用范围内开启短事务，锁定当前任务，重新检查其可变状态，只合并本次实际提交的字段并校验完整结果，然后原子写入配置、内部代次与必要的调度状态。未提交字段保留事务取得的最新值；同一字段由数据库串行化后较晚成功提交的更新生效。此规则不拒绝“用户页面打开后别人改过”的请求，也不允许把事务外读取的旧对象整行覆盖回去。暂停、恢复与到期受理仍须在同一权威记录上协调，不能把取消 HTTP 前置条件误解为取消状态准入、事务或数据完整性约束。

请求超时后不承诺按同一次请求标识恢复原回执。更新方可读取详情核对当前配置，但当前值不能证明某次历史提交是否成功；创建请求重试可能产生新 Schedule，手动运行重试可能产生新 Run，应先读取可见资源或运行记录核对，不因观察超时自动重复写入。查询结果也不构成不存在未知在途提交的证明。内部 revision 继续用于识别配置代次和调度竞态；自动触发 occurrence 与已生成 runId 的内部受理去重继续保留，不依赖客户端传入请求键，也不承诺整个外部业务的 exactly-once。

**当前源码事实。** 2026-10-04 重新执行 `git ls-remote --symref origin HEAD` 确认默认 main，隔离 fetch 到 `refs/codex-evidence/schedule-header-free-20261004`；完整 commit 为 `553dcd5e2ff682f9684810a043b442b37a02e54a`，与 §8.11 相同。仅升级本节读取范围，未修改实现仓工作树或运行产品测试。R 表示 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。

| 仓库相对路径与关键符号 | 已观察实现与目标差距 |
|---|---|
| [R/runtimeapi/web/RuntimeSessionController.java:68](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeSessionController.java#L68) · get/update（80） | GET 和更新响应仍设置 ETag；更新从 If-Match 读取字符串交给 Service，Controller 的 required=false 不代表业务允许缺省。创建未返回 ETag。 |
| [R/runtimeapi/session/RuntimeSessionUpdateService.java:98](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionUpdateService.java#L98) · update/prepare（117）、requireStrongEtag（190）、requireObservedVersion（207） | 仍强制标签并比较：缺失428、不匹配412；prepare 将读取时的 resourceVersion 写入内部 specification。当前源码不是无条件更新，不能只删 Controller 入参就认为数据库和客户端语义已迁移。 |
| [R/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java:341](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java#L341) · updateSession/rejectUnifiedUpdate（368）、mergeUpdate（382）；[modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml:63](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml#L63) · lockSessionForUpdate | 事务中 SELECT FOR UPDATE 后读取最新记录，继续检查 expectedVersion，再合并出现字段与原值。锁内读取/合并可参考；版本拒绝属于既有条件更新机制，不能当作取消 HTTP 令牌后自动适配完成。 |
| [frontend/src/composables/useRuntimeApi.ts:234](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/frontend/src/composables/useRuntimeApi.ts#L234) · changeSetting；同文件 renameSession（258，Header 在264） | 两条设置更新路径仍发送 If-Match；移除后端契约时，调用方标签保存及冲突处理也需同步迁移。这里只记录差距，不修改前端。 |

在 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi` 与上述前端文件中检索 If-Match、Idempotency-Key、idempotencyKey 和 ETag 设置，并读取以上命中链路；未观察 Session 更新的客户端幂等键持久化或原结果回放。其他入口中出现拒绝/清除这些 Header 的代码，不等于支持该机制；此范围也不证明外部网关无独立去重。

**Claude 公开契约边界。** 同日重新读取 [Create Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/create)和 [Update Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/update) 的 Headers、cURL 及响应示例：两页均未声明 If-Match、Idempotency-Key 或 ETag 条件写入流程；同日重读 [Update Session](https://platform.claude.com/docs/en/api/beta/sessions/update) 的 Headers 与 cURL，同样未声明这两个请求头。此次只核对这些 Managed Agents HTTP Beta 公开操作页，没有实际调用服务，也没有可归因的服务端源码 commit；不能将“未声明”扩大为内部没有锁、版本检查或去重，更不能据此为 Claw 承诺重复创建会自动返回同一资源。

取舍为降低客户端协议与服务端请求回执存储的复杂度，同时明确接受同字段后一次成功修改生效及创建/手动运行重试可能产生新资源。数据库事务、内部配置代次和运行受理去重仍承担各自一致性责任；精确接口以[配置专题](configuration.md#update-schedule-review)为准。

<a id="schedule-deletion-evidence"></a>

### 8.13 直接删除与 Claude 归档的生命周期差异（2026-10-04）

**公开 Beta 契约。** 本次于2026-10-04重新读取 Claude [操作目录及模型](https://platform.claude.com/docs/en/api/http/beta/deployments)、[Archive](https://platform.claude.com/docs/en/api/http/beta/deployments/archive)、[List](https://platform.claude.com/docs/en/api/http/beta/deployments/list)、[Get](https://platform.claude.com/docs/en/api/http/beta/deployments/retrieve)及[生命周期指南](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)。操作目录提供 archive，没有列出 DELETE/unarchive；Archive 为 `POST /v1/deployments/{deployment_id}/archive`，无业务正文，成功200返回完整 Deployment。归档是不可恢复终态，计划终止且配置不可修改；archived_at 表示归档，模型明确归档对象也报告 status:active；upcoming_runs_at 为空，last_run_at 保留。include_archived 默认 false，不能与 status 组合。

同日再次读取 Archive 的 Returns 与 Response200，确认其响应模型为完整 BetaManagedAgentsDeployment；并核对 [Delete Session](https://platform.claude.com/docs/en/api/http/beta/sessions/delete)：该操作为 DELETE、成功200，但返回的是 `{id,type:"session_deleted"}` 精简回执。两种形状属于不同操作；Claw 已选择参考 Deployment 归档的完整资源返回形状，不将 Session 删除回执替换为本产品目标。

公开页面未明确归档 ID 的 GET 状态、重复归档行为、归档后在途 Session/Run 的处理和保留期限；指南只对暂停明确不停止在途 Session。Archive 的自动生成200示例仍含 archived_at:null、非空 upcoming_runs_at，以及 active 与 manual 暂停原因并存，不能以这些占位值覆盖模型/指南约束。本次未调用实际 API、无服务端源码，不能推断其数据库、锁或删除清理方式。

**Java 当次快照。** 2026-10-04 用 `git ls-remote --symref` 确认上游默认 main，并在临时 bare 仓库隔离 fetch；完整 commit 为 `553dcd5e2ff682f9684810a043b442b37a02e54a`，与 §8.12 相同。下表仅升级实际读取的删除链路。C 表示 `modules/cron/src/main/java/com/campusclaw/cron/`，R 表示 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/`。

| 仓库相对路径与关键符号 | 已观察行为及参考边界 |
|---|---|
| [C/CronService.java:67](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/CronService.java#L67) · deleteJob；[C/engine/CronEngine.java:163](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/engine/CronEngine.java#L163) · unscheduleJob、executeAndReschedule（185）、executeJob（216） | 先 cancel(false) 本地 ScheduledFuture，再移除 Job，不主动中断已开始执行。回调已取得 Job 时，删除返回后仍可能开始执行；结束后重读不到则不重排。不能作为删除提交后禁止新受理的保证。 |
| [C/store/CronStore.java:94](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/store/CronStore.java#L94) · removeJob、updateJob（112）、saveUnsafe（141） | 本地写锁保护 jobs.json 元素移除，找不到返回 false；保存吞 IOException，true 不严格证明持久删除。后续 updateJob 只替换既有元素，不复活删除的 Job。 |
| [C/tool/CronTool.java:207](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/tool/CronTool.java#L207) · delete、runs、requireOwnedJob（238）；[C/store/CronRunLog.java:55](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/store/CronRunLog.java#L55) · appendRun/getRecentRuns | 删除保留 jobId.jsonl，Service 可按 ID 读取，工具却先要求 Job 存在且匹配当前 Agent，因此无法读取已删 Job 历史。Agent 过滤不证明企业租户授权。 |
| [C/model/CronRunRecord.java:17](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/model/CronRunRecord.java#L17)；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/cron/ManagedCronSessionRunner.java:53](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/cron/ManagedCronSessionRunner.java#L53) · execute | Run 无 sessionId，Runner 创建并关闭内存 ManagedAgentSession，不走 Runtime Session Repository；现有 Cron 不提供 Schedule→Run→可查询 HTTP Session 关联。 |
| [R/web/RuntimeSessionController.java:95](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeSessionController.java#L95) · delete；[R/session/RuntimeSessionService.java:96](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionService.java#L96) · delete | DELETE 无正文，204/空体/no-store；不存在及重复删除同样204，BUSY 为409，不隐式停止执行。这是 Session 行为，不能直接推导 Schedule 应拒绝在途 Run。 |
| [R/persistence/MyBatisRuntimeSessionRepository.java:452](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java#L452) · beginDeletion、completeCleanup（479）、create（59）；[modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml:305](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml#L305) | 事务锁行，非 idle 拒绝；原子写墓碑/清理任务并删 Session 主记录，后台重试清理且保留墓碑，禁止复用已删除 ID。未知 ID 的无操作删除不新建墓碑。 |

所查 modules/cron、Runtime Controller/Service/Repository/Mapper/SQL 范围未提供 Schedule HTTP、Schedule/Run 数据表或关联删除契约，新增能力仍为待实现。已阅读现有 Cron 删除成功/不存在/跨 Agent 拒绝及 Session 204/busy409 的测试材料，未运行测试；没有发现能证明 Cron 删除与到期执行无竞争的验收证据。

**CampusClaw 已确认目标（待实现）。** 删除 Schedule 及其所有 Run，保留已经生成的 Session；不提供归档资源、归档操作、archivedAt、includeArchived 或 archived 状态。存在的 Schedule 仍为 active/paused，删除成功200、ResultBean.result 返回完整 Schedule；删除生效后的新读取中，Schedule 和关联 Run 详情返回404，各自列表排除这些记录。删除不是先转为 paused，也不保留可恢复的配置或Run归档；Session按自身生命周期和当前权限独立管理，不依赖已删除的Schedule/Run授权。精确操作由[配置专题 §4.6](configuration.md#delete-schedule-review)维护，受理竞态和在途执行规则见[执行专题](execution.md)。

**删除与执行边界（待实现）。** 完整回执与 HTTP 错误由[配置契约](configuration.md#delete-schedule-review)维护。删除与最终受理在同一 Schedule 权威上串行化：删除先提交则不得受理，受理先提交则保留原 Session 并继续由 Runtime 管理；删除本身不自动取消已受理执行，停止由 Session 入口单独发起。晚到结果不得复活 Schedule/Run。进行中或结果未知执行所需的最小内部协调归原根执行生命周期，不能变成完整配置或 Run 的永久归档。单独删除 Session 时，只要 Schedule 仍存续，原 Run 保留真实受理事实；原 sessionId 不构成会话仍可读取的保证。不能用当前 Cron 文件删除或 Session busy409 直接兑现这些规则，也不能把 Claude 未声明的行为写成其保证。

**差异分类与代价。** 删除Schedule及关联Run、保留Session是产品约束及生命周期架构选择：减少归档字段、筛选和任务侧历史管理，代价是原配置、触发来源及没有Session的失败Run不再可查。已生成对话不因任务删除而丢失，读取与删除继续按Session自身当前权限执行；删除配置不请求取消已受理执行，后续读取、停止和删除由 Session 入口按当前权限独立管理。执行收尾只能完成Runtime及必要的内部协调，不得复活已删Schedule、Run或计划。已确认的完整Schedule回执及无客户端条件/请求键规则保持不变，不引入新 Maven 依赖。

<a id="schedule-actions-evidence"></a>

### 8.14 立即运行、暂停与取消暂停（2026-10-05）

**公开Beta契约。** 当日重新读取[Run](https://platform.claude.com/docs/en/api/http/beta/deployments/run)、[Pause](https://platform.claude.com/docs/en/api/http/beta/deployments/pause)、[Unpause](https://platform.claude.com/docs/en/api/http/beta/deployments/unpause)、[Deployment模型](https://platform.claude.com/docs/en/api/http/beta/deployments)、[Run模型](https://platform.claude.com/docs/en/api/beta/deployment_runs)、[Run列表](https://platform.claude.com/docs/en/api/beta/deployment_runs/list)和[调度指南](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)。三操作均POST /v1/deployments/{deployment_id}/{run|pause|unpause}，无业务Body/Query参数，成功200；run返回DeploymentRun，pause/unpause返回完整Deployment。未实际调用服务，没有服务端源码commit；未声明Body不等于证明服务端拒绝{}。

| 公开事实 | 本次参考范围与未说明项 |
|---|---|
| Run顶层为type/id/agent/created_at/deployment_id/error/session_id/trigger_context；error与session_id恰好一个非空 | 持久记录Session创建结果，不含queued/running/completed生命周期；成功Run不等于Agent工作完成。agent为已解析版本快照，Claw只有agentId不能伪造版本固定能力 |
| 手动run的trigger_context为{type:manual}；有规则或manual-only均可运行 | 创建独立Session并提交初始事件，不需要先启用计划；手动运行不更新schedule.last_run_at；并发/去重/全部失败HTTP映射未完整说明 |
| pause抑制后续自动触发，既有Session继续，手动运行仍允许 | status为paused、paused_reason为manual；Cron预览可保持非空，反映假设恢复后的计划；不推断内部调度锁或取消实现 |
| unpause从下一次计划继续，不补漏触发，清空paused_reason | status恢复active；重复调用的状态/时间效果、是否覆盖自动暂停原因及恢复资格检查未逐项声明 |
| Run.error为{type,message}，有16个公开错误分支；自动暂停原因中的error仅含type | 不能混用两个嵌套Schema，也不将手动失败必然自动暂停视作基线；Claw错误集合及精确映射另审，不照搬不存在的Environment/Vault资源 |

官方自动生成示例仍有冲突：run同时填入非空error/session_id且使用schedule触发分支，pause/unpause同时填active与manual原因；应以字段约束和指南为准。Run页面的毫秒占位示例也不改变Claw已确认的秒级规则。暂停期间手动运行及取消暂停不补跑有明确公开依据；重复pause/unpause、精确更新时间和手动重叠策略仍属未公开边界。

**Java当次快照。** 2026-10-05用git ls-remote --symref确认默认分支main，临时bare仓库隔离fetch得到`553dcd5e2ff682f9684810a043b442b37a02e54a`，与2026-10-04旧快照相同；只重核下表范围，不升级其他模块或Agent历史证据。C代表modules/cron/src/main/java/com/campusclaw/cron/，R代表modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/。

| 路径、符号及行号 | 已观察实现及差距 |
|---|---|
| [C/CronService.java:80](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/CronService.java#L80) · enableJob、disableJob（90）、triggerJob（97） | enable整体保存true后重排，重复调用无no-op分支；disable取消本地句柄后整体保存false；不存在时两者无操作；未提供结构化HTTP回执或暂停原因 |
| [C/engine/CronEngine.java:163](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/engine/CronEngine.java#L163) · unscheduleJob、triggerJob（177）、executeAndReschedule（185）、executeJob（216） | cancel(false)不终止在途；手动直接执行、不检查enabled、tickLock或runningAt。自动才检查运行标记，手动和自动可能竞争；不能宣称已有Schedule级busy准入 |
| [C/engine/CronEngine.java:239](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/engine/CronEngine.java#L239) · recordJobOutcome、recordJobException（272）、computeNextDelay（301） | 结果更新lastRunAt、次数和错误数并清nextRunAt；手动不满足新目标“自动时间摘要不变”。Cron恢复按当前时刻next，无未来值时没有明确恢复失败回执；旧At/Every不外推为新Cron行为 |
| [C/store/CronStore.java:112](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/store/CronStore.java#L112) · updateJob、saveUnsafe（141） | 本地锁内整条替换，读取/判断/写入不在同一锁内；保存吞IOException。结合recordJobOutcome可推导：运行持有enabled=true旧对象→disable保存false→运行收尾覆写true→自动重排；此为源码推导，未运行复现测试 |
| [C/tool/CronTool.java:42](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/tool/CronTool.java#L42) · INPUT_SCHEMA、create（181）、trigger（212）、requireOwnedJob（238） | action仅create/list/delete/trigger/status/runs，无pause/unpause；创建要求规则，不能因trigger不读schedule而声称已支持null规则；仅Agent过滤不足以证明企业授权 |
| [C/engine/CronJobExecutor.java:39](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/engine/CronJobExecutor.java#L39) · execute；[ManagedCronSessionRunner.java:53](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/cron/ManagedCronSessionRunner.java#L53) · execute/prompt.join（70） | 同步等模型完成、提取文本并关闭内存Session；RUNNING/终态为JSONL两行，同runId尚未归并，无持久HTTP Session关联 |
| [R/session/RuntimeSessionService.java:64](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionService.java#L64) · create/get；[R/persistence/RuntimeExecutionPersistenceService.java:70](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/RuntimeExecutionPersistenceService.java#L70) · acceptMessage | 创建空Session与受理消息是分离入口；后者可原子建首消息/根执行/segment，但未与新Session、ScheduleRun一并协调 |
| [R/event/RuntimeMessageEventService.java:131](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeMessageEventService.java#L131) · submitLocked/startAccepted（190）；[R/event/RuntimeExecutionCoordinator.java:91](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java#L91) · start；[R/event/RuntimeEventOutput.java:35](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventOutput.java#L35) · persistenceOnly | 普通路径prepare→accept→start，Coordinator异步推进；无浏览器输出抽象可复用，但旧Cron未接线，不能用串联两次HTTP代替同库受理 |
| [R/event/CommittedEventQueryService.java:40](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/CommittedEventQueryService.java#L40) · list；[R/persistence/MyBatisRuntimeSessionRepository.java:268](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java#L268) · findEventPage | Session完整事件可分页查询；未提供ScheduleRun详情/列表、无响应Run的超时核对或企业作用域接线 |

**目标与原因。** Claw已确认立即运行采用200 Run记录受理结果，已记录的失败在error，请求/权威失败仍用4xx或5xx；八字段Run、pause/unpause完整资源、同值操作不改时间/游标、恢复前资格检查及同一任务不重叠已确认；精确错误及动作行为由配置专题维护，同库受理实现见执行专题；运行失败是否自动暂停整个 Schedule 仍待确认。新Run只说明是否可靠受理新Session及首消息，不追踪业务完成，避免复用旧SUCCESS把触发与业务结果混为一体。数据库最新行状态修改、暂停与最终自动受理协调以及收尾不覆盖人工状态，是架构增量；企业调用资格、执行身份和安全错误投影是产品约束/安全边界。代价是新增持久Run、受理接线和独立历史查询，而非简单包装三个旧Service方法。

只读检查了相关CronService/Engine/Tool测试材料，未运行Maven、GaussDB、多实例或身份联调；没有验证暂停竞争、手动busy、原子Session关联或新HTTP成功/错误体。没有新增Maven依赖；继续复用已有Spring/Jackson/MyBatis及Runtime，传递图未重跑。

<a id="schedule-run-read-evidence"></a>

### 8.15 Run 查询与配置删除后的历史边界（2026-10-05）

**公开 Beta 契约。** 当日重新核对 [List Deployment Runs](https://platform.claude.com/docs/en/api/http/beta/deployment_runs/list)、[Get Deployment Run](https://platform.claude.com/docs/en/api/http/beta/deployment_runs/retrieve)、[Run 模型](https://platform.claude.com/docs/en/api/beta/deployment_runs)、[调度指南](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)和 [Archive](https://platform.claude.com/docs/en/api/http/beta/deployments/archive)。没有服务端源码或实测请求，不据公开字段推断内部表、锁或清理实现。

| 公开契约 | 参考范围与未说明项 |
|---|---|
| GET /v1/deployment_runs；deployment_id 可选，省略查询工作区全部，不存在的筛选 ID 返回200空 data | Run 是独立查询资源，不以父 Deployment 路径嵌套；不能由此证明归档后永久可读 |
| has_error、trigger_type，以及 created_at[gt/gte/lt/lte] 可选 | true/false 对应 error/session_id 非空；manual/schedule 是触发来源；不是模型或业务执行成败筛选 |
| limit 默认20、最多1000；page 为不透明游标，无效或过期400；返回 data/next_page | 与 Deployment 配置列表的最多100不同；未声明默认排序、同秒排序键、跨页快照或游标有效期 |
| GET /v1/deployment_runs/{deployment_run_id}，无业务 Query/Body，200完整 Run | 官方 Get 链接为 retrieve；具体不存在/越权错误条件没有逐项声明 |
| 两个读取与 run 动作复用八字段 Run；session_id/error 恰好一个非空 | Run 为追加式会话创建结果；不追踪 Session 生命周期；示例同时填非空 error/session_id 与明确约束冲突，不能照抄 |
| 手动 trigger_context 只有 type:manual；自动为 type:schedule 和 scheduled_at | scheduled_at 为 Cron 命中的 UTC 时刻、抖动前，同 Deployment/计划时刻至多一条；created_at 为记录持久化时间，两者不同 |
| Deployment 终态操作是归档；主要 Agent 失效的自动归档分支可能不生成 Run | 所读页面没有声明 Run 保留期限、物理清理级联或 Session 删除后的 Run 字段处理；Claw 的直接删除与历史保留必须独立决定 |

**Java 当次快照。** 2026-10-05 重新确认上游默认分支 main，并在临时 bare 仓库隔离 fetch；完整提交仍为 `553dcd5e2ff682f9684810a043b442b37a02e54a`，与 §8.14 相同。仅增量核验下表范围，不把其他模块历史结论升级。C 代表 modules/cron/src/main/java/com/campusclaw/cron/，R 代表 modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/，X 代表 modules/coding-agent-cli/src/main/resources/mapper/session/。

| 仓库相对路径、符号与行号 | 已观察实现及差距 |
|---|---|
| C/tool/CronTool.java:225 · runs、requireOwnedJob（238）；C/CronService.java:101 · getRecentRuns | 工具仅接受 job_id/limit，默认10、最大100，返回文本；必须先找到现存 Job 并检查当前 Agent；无独立 Run HTTP 详情或企业历史授权 |
| C/store/CronRunLog.java:70 · getRecentRuns；C/engine/CronJobExecutor.java:39 · execute | 读整个 JSONL，取最近 limit 行并逆序，同 runId 的 RUNNING 和终态各占一行；坏行跳过、I/O失败变空列表，不能作为新列表的完整性或故障语义 |
| C/model/CronRunRecord.java:17；C/store/CronRunLog.java:55 · appendRun | 执行日志含 startedAtMs/status/output 等，无 sessionId/agentId/triggerContext；写失败仅记日志，不能包装成新八字段、可靠持久化 Run |
| R/web/RuntimeEventController.java:80 · list；modules/common/src/main/java/com/campusclaw/common/constant/ClawConstants.java:158 | ListEvents 的整数 page 可选且>=1，limit默认50、最大200；成功200、ResultBean、no-store及语言响应 |
| R/event/CommittedEventQueryService.java:40 · list/pageOf、calculateOffset（81）、nextPage（99）；R/vo/ListSessionEventsResponseVO.java:18 | 默认 page=1，offset=(page-1)*limit，多取一条，nextPage=page+1或null，无total；long乘加溢出显式拒绝，不是游标协议 |
| R/persistence/MyBatisRuntimeSessionRepository.java:266 · findEventPage；X/RuntimeSessionMapper.xml:191 · listCommittedEvents | 单请求只读 REPEATABLE_READ，先查Session及投影完整性，按 event_seq ASC分页；无跨HTTP页快照，不证明最新在前Run列表也有稳定位置 |
| C/CronService.java:67 · deleteJob；C/store/CronStore.java:94 · removeJob；C/tool/CronTool.java:238 | 删除配置未删除Run日志，但工具历史入口依赖仍存在的Job；日志残留不证明删除后历史可授权读取 |
| R/session/RuntimeSessionService.java:89 · get、delete（96）；R/persistence/MyBatisRuntimeSessionRepository.java:450 · beginDeletion、completeCleanup（477） | Session删除主记录并保存墓碑/清理任务，后续详情及事件查询404；残留事件不继续公开，Run若保留关联不能据Session404改写原受理结果 |
| R/dto/RuntimeSessionDTO.java:18；X/RuntimeSessionMapper.xml:41；runtimeapi/web 与所查 QueryService/Repository 范围 | 未观察到ScheduleRun路由、独立Run数据或可信租户/园区读过滤；源码只按Session ID查询，执行凭据提取不构成历史读取授权 |

源码链接基址为 [pi-mono-java 固定快照](https://github.com/superheromeZzh/pi-mono-java/tree/553dcd5e2ff682f9684810a043b442b37a02e54a)。只读取源码及有关测试材料，未运行 Maven、数据库、多实例或公司身份联调。无新增 Maven 依赖；旧 Cron 日志与新 Run 的语义不等价，不能通过 DTO 包装宣称已实现。

**Claw 的已确认生命周期（待实现）。** 删除 Schedule 及其所有 Run，保留已生成 Session，不提供归档查询或恢复。删除生效后的 Run 详情返回404，列表排除相关记录；代价是没有 Session 的启动失败和任务侧触发来源不再可查。删除不自动取消已受理执行，Session 凭自身可信归属和当前权限独立读取、停止与删除；单独删除 Session 保留原 Run 的受理事实。删除与受理共享数据库权威，临时内部协调不能变成完整配置或 Run 的永久软归档。两个 GET 的路径、筛选和分页由[运行读取边界](configuration.md#schedule-run-read-lifecycle)维护；Run404或空列表不证明此前没有成功受理。

**归档后显示的核验限制。** 同日进一步读取[Deployment列表](https://platform.claude.com/docs/en/api/http/beta/deployments/list)、[Build in Console](https://platform.claude.com/docs/en/managed-agents/onboarding)及[官方发布说明](https://claude.com/blog/whats-new-in-claude-managed-agents)。include_archived=true明确支持列表包含归档配置；Run模型的persistent/append-only和独立查询是另一层契约。上述资料未明确归档后控制台Run/Session列表的显示规则，也未给出保留时长。本次未登录控制台或执行归档实验，不能把API结构推测当作界面实测；不声称归档后所有执行必然持续可见。

<a id="schedule-delete-baselines"></a>

### 8.16 其他基线的任务删除、运行历史与会话关系（2026-10-05）

本专项分别确认上游默认分支，并在临时目录隔离 shallow fetch 后读取固定提交；没有覆盖用户工作树。下表只升级定时删除与关联历史的核验范围，不升级此前工具、执行恢复或其他模块的历史结论。默认分支最新源码不等于最新稳定发布；Claude 和 Codex 宿主只能按当日官方公开文档判断，不能推断未公开的数据库或控制台行为。

| 基线 | 前次相关快照 → 本次默认分支完整提交 | 本次范围与成熟度 |
|---|---|---|
| OpenClaw | 本专题新增辅助基线；main `6636dd6709bdbace1b6b72c3a86ff664bbdec244` | package.json版本2026.9.8；读取当前删除、SQLite运行历史、会话清理及测试，不把旧JSONL实现当现行行为，也不宣称该HEAD就是已发布稳定版 |
| DeepSeek Harness | master `5badb15009ae1756c3afe0ae0cef1faafc290ccc` → 同提交 | 0.2.1-alpha.1；新增读取delete/history、投递与删除串行化、删除历史测试 |
| pi | main `200387122ca450d6387f033949423114a270b96c` → 同提交 | 当前包目录、内置工具、coding-agent/server/protocol/durable相关入口；pi-durable明确Experimental |
| OpenCode | dev `907b3bc518fa48e90e8ec24dd327d13eee71c36c` → 同提交 | 开发分支；GitHub schedule入口、Session API与存储，未观察到同形原生Schedule/Run管理资源 |
| Codex harness | 前次调度专项main `d42056091aded7feb1d88ac7e83972108b2aa478` → `afb436df8b70bb5bc57b86d9a3e829968988cd21` | 当前插件任务模板、heartbeat输入来源与独立Thread删除；未取得桌面Automation删除实现，不将新增元数据当完整调度服务 |

**可直接比较的两种删除模型。** Run、投递回执和模型执行结果不是同一资源，必须先说明各自含义。

| 基线 | 删除配置后任务侧历史 | 对会话的影响 | 对已在途执行的影响 |
|---|---|---|---|
| OpenClaw | 保留独立运行历史，之后受保留清理策略约束；物理保留不保证所有调用者仍可查 | 删除任务专用的复用base session；不会因这次删除批量删除每次运行的`:run:<id>`会话，也不删除共享main会话 | 操作者删除请求取消活动运行；已受理任务自行删除自己的配置是例外。活动运行结束后才做延后清理，返回取消请求不等于执行已停止 |
| DSH alpha Schedule | 任务行内的deliveryHistory随配置行一起删除，history返回schedule_not_found | 保留原Session、已有事件和已入队消息；本身向原会话投递，不是每次新建Session | delete不调用Agent.cancel，不撤回已入队消息；投递与删除共用FIFO，先进入的投递可能在删除提交前完成 |

**OpenClaw源码与可见性。** [官方CLI文档](https://docs.openclaw.ai/cli/cron)明确说明运行历史保留、操作者删除请求取消和任务自删例外。对应源码为下列固定快照，不能把删除基础会话误写为清空全部运行对话。

| 仓库相对路径与符号 | 已观察行为 |
|---|---|
| [src/cron/service/ops-mutations.ts:421](https://github.com/openclaw/openclaw/blob/6636dd6709bdbace1b6b72c3a86ff664bbdec244/src/cron/service/ops-mutations.ts#L421) · remove | 持久移除配置并停止后续调度；提交后处理活动运行，isolated/current目标登记base session清理；有活动运行则返回sessionCleanup:pending，待inactive再清理 |
| [src/cron/store/row-codec.ts:623](https://github.com/openclaw/openclaw/blob/6636dd6709bdbace1b6b72c3a86ff664bbdec244/src/cron/store/row-codec.ts#L623) · deleteCronJobRowInDatabase；[active-jobs.ts:350](https://github.com/openclaw/openclaw/blob/6636dd6709bdbace1b6b72c3a86ff664bbdec244/src/cron/active-jobs.ts#L350) · noteActiveCronJobRemoval | 删除Job及scratch、撤销该Job授权，不删task_runs；活动运行标记保留至真实结束，操作者取消与任务自删分支明确分开 |
| [src/cron/service.remove-session-cleanup.test.ts:164](https://github.com/openclaw/openclaw/blob/6636dd6709bdbace1b6b72c3a86ff664bbdec244/src/cron/service.remove-session-cleanup.test.ts#L164) · removes only the deleted isolated job's base session | 测试明确断言base会话删除、同任务run会话保留、其他任务会话保留；这是已读断言，本次未执行 |
| [src/cron/session-reaper.ts:68](https://github.com/openclaw/openclaw/blob/6636dd6709bdbace1b6b72c3a86ff664bbdec244/src/cron/session-reaper.ts#L68) · removeCronJobBaseSession；resolveRetentionMs（40）、reaper（115） | base清理与过期每run会话清理是不同入口；每run默认按updatedAt超过24小时判定，可配置或禁用，不从删除Job时刻倒计时。清理有忙执行保护与节流，移除会话登记并归档transcript，其物理内容清理另有策略，不是24小时必然抹除全部内容 |
| [src/cron/store/run-history.kernel.ts:19](https://github.com/openclaw/openclaw/blob/6636dd6709bdbace1b6b72c3a86ff664bbdec244/src/cron/store/run-history.kernel.ts#L19) · retention常量与历史读取 | 当前运行历史采用独立存储；终态通常7天、lost类24小时，每Job/历史类别另有2000条上限。清理还有未终结协调记录等保护，不把常量解释为到秒准时删除保证 |
| [src/gateway/server-methods/cron-runs.ts:137](https://github.com/openclaw/openclaw/blob/6636dd6709bdbace1b6b72c3a86ff664bbdec244/src/gateway/server-methods/cron-runs.ts#L137) · cronRunsHandler；[cron-history.ts:55](https://github.com/openclaw/openclaw/blob/6636dd6709bdbace1b6b72c3a86ff664bbdec244/src/gateway/server-methods/cron-history.ts#L55) · assertAllowed | 无调用范围/会话可见性限制的操作者可读已删Job历史；受限调用者仍检查存续Job，Job内查询额外传agentId也要求匹配存续Job。物理保留不等于原来所有调用者都可见，不能直接复制成Claw独立租户授权；对应测试cron.runs.test.ts:648已读未执行 |
| [ui/src/pages/cron/cron-page.ts:555](https://github.com/openclaw/openclaw/blob/6636dd6709bdbace1b6b72c3a86ff664bbdec244/ui/src/pages/cron/cron-page.ts#L555) · 删除后的运行筛选刷新 | 删除当前选中Job后切换总运行历史并重新读取；最终可见性仍依赖API权限及保留结果。本次仅核对UI源码，未启动界面实测 |

**DSH源码与测试。** [ScheduleService.history/delete](https://github.com/deepseek-ai/deepseek-harness/blob/5badb15009ae1756c3afe0ae0cef1faafc290ccc/packages/schedule/schedule/src/index.ts#L295)方法分别在303、326行；delete校验原Session绑定后执行tasks.delete。任务[存储模型](https://github.com/deepseek-ai/deepseek-harness/blob/5badb15009ae1756c3afe0ae0cef1faafc290ccc/packages/schedule/schedule/src/storage.ts#L36)把deliveryHistory与配置放在同一行，因此它们同删。history先查该行，删除后不存在；没有从Session日志重建任务侧历史。

[delivery-history.spec.ts:189](https://github.com/deepseek-ai/deepseek-harness/blob/5badb15009ae1756c3afe0ae0cef1faafc290ccc/packages/schedule/schedule/tests/delivery-history.spec.ts#L189)断言删除后任务、history、list/catalog均不存在，但原Session对象仍在，snapshotEvents完全不变；214行的重启测试继续断言任务与历史不恢复、后续不再投递。已读测试，未运行。[runtime.ts:101](https://github.com/deepseek-ai/deepseek-harness/blob/5badb15009ae1756c3afe0ae0cef1faafc290ccc/packages/schedule/schedule/src/runtime.ts#L101)的followup/flush证明其历史是持久收件回执，不证明模型完成。index.ts:155的runtime事务与delete共用serialize；runtime.ts:54的drive若先进入，删除要等它退出，即使此前尚在恢复Session。该先后关系来自源码推演，未做真实并发实验。

**不能强行填成保留或级联删除的基线。**

| 基线 | 实际核验范围与证据边界 |
|---|---|
| pi | [README:74](https://github.com/badlogic/pi-mono/blob/200387122ca450d6387f033949423114a270b96c/README.md#L74)当前包目录无mom，聊天自动化指向外部pi-chat，本次未核验该外部仓；[TaskScheduler:159](https://github.com/badlogic/pi-mono/blob/200387122ca450d6387f033949423114a270b96c/packages/durable/src/harness/scheduler.ts#L159)是实验持久任务执行器。所读内置工具、coding-agent/server/protocol/durable入口没有可等同Schedule→Run→Session的删除契约；不能外推整个pi生态没有定时能力 |
| OpenCode | [github.handler.ts:149](https://github.com/anomalyco/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/cli/cmd/github.handler.ts#L149)消费GitHub Actions schedule事件，501行创建Session，finally不显式删除Session；删除workflow的历史策略属于外部平台，临时runner存储也不能假设永久保留。本次检索opencode/core/protocol/schema并读取独立[Session.remove:606](https://github.com/anomalyco/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/session/session.ts#L606)，后者不是删除定时任务的语义 |
| Codex | [plugin.rs:757](https://github.com/openai/codex/blob/afb436df8b70bb5bc57b86d9a3e829968988cd21/codex-rs/app-server-protocol/src/protocol/v2/plugin.rs#L757)有scheduled_tasks模板， [history/heartbeat.rs:24](https://github.com/openai/codex/blob/afb436df8b70bb5bc57b86d9a3e829968988cd21/codex-rs/history/src/heartbeat.rs#L24)识别宿主定时输入；所查app-server/protocol/state及Rust定时入口未找到完整Automation删除服务。[官方Scheduled tasks](https://learn.chatgpt.com/docs/automations)说明两类会话模式和独立归档运行，没有明确删除配置后的级联规则；不能拿[thread_delete_response](https://github.com/openai/codex/blob/afb436df8b70bb5bc57b86d9a3e829968988cd21/codex-rs/app-server/src/request_processors/thread_delete.rs#L31)替代该证据 |
| Claude Managed Agents Beta | 当日重读[调度指南](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)和Run模型。归档是停止未来触发的终态，Run为独立追加记录；所读页面仍未明确归档后的Run/Session清理与控制台显示规则，沿用§8.15的未核验边界 |

**对Claw的设计含义。** OpenClaw作为删除生命周期的辅助基线，Claude继续作为公共调度API主基线。保留独立运行历史与删除任务侧历史均有具体实现参照；DSH证明删历史不必删对话，OpenClaw证明保留历史仍可同时请求取消当前执行。Claw已确认删除Schedule及所有对应Run、保留已生成Session；这是产品约束及生命周期架构选择，参考DSH的资源关系但不等同其投递回执语义。Session 继续独立授权和管理；Claw 删除 Schedule 不自动取消已受理执行，由 Session 入口单独停止，反向删除 Session 不抹去原 Run 受理事实。这是本产品选择，不外推为上述所有基线共同规则。所列基线事实保持原核验范围；源码阅读不等于产品实测，未运行上游测试、创建或删除任何真实定时任务。

<a id="schedule-engineering-evidence"></a>

### 8.17 执行策略、Mate 边界与 coding-agent 合并（2026-10-05）

本节只更新 CampusClaw Java 与 Mate 示例的工程核验。分别重新确认上游默认分支并隔离 fetch：Claw 为 `main@553dcd5e2ff682f9684810a043b442b37a02e54a`，Mate 为 `main@4b957a3a846659f5b7569c9d6133abc070cd2e3c`。Claw 与前次同 SHA；Mate 与 §8 的历史本地样例 SHA 相同，但本次已验证远端默认分支，不把旧本地记录当作最新证明。用户实现工作树未修改；外部 Agent 的日期、SHA 与公开文档结论沿用前文各专项，不声称本节重新核验 Claude、OpenClaw、DSH、pi、Codex 或 OpenCode。

以下 Claw 的 R 表示 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`，C 表示 `modules/cron/src/main/java/com/campusclaw/cron/`；链接固定到本节 Claw commit。Mate 路径相对于上述 Mate 示例快照，不代表生产工程部署或完整公司认证系统。

| 范围 | 仓库相对路径与关键符号 | 已观察实现、目标差距与理由 |
|---|---|---|
| 物理模块与启动权威 | Claw [pom.xml:17](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/pom.xml#L17)、`modules/cron/pom.xml`、`modules/coding-agent-cli/pom.xml`；C/CronService.java:29/42 · SmartLifecycle；C/engine/CronEngine.java:62/121 · start/scheduleJob | 独立 cron 有15个生产 Java、7个测试 Java、无独立资源目录；仓内制品消费者只有 coding-agent。旧 SmartLifecycle 自动启动本地 JSON 调度；合并物理模块不能与新 SQL 调度器双跑，也不等于已经实现数据库受理。 |
| 模型工具与 Runtime 装配 | R/tool/cron/AgentScopedCronToolFactory.java:24；R/runtimeapi/runtime/RuntimeSessionEngineRegistry.java:61/207；R/session/AgentSessionFactory.java:67；R/tool/builtin/DefaultBuiltInToolFactory.java:59 | Registry 装配 CronTool，旧工具工厂依赖 CronService。若新 Service/Dispatcher 又直接依赖 Registry，会形成构造环；应拆开管理/受理与异步推进，不用 `@Lazy` 隐藏职责环。 |
| 旧失败与运行路径 | C/engine/CronEngine.java:239/302/337 · recordJobOutcome/computeNextDelay/cleanStaleRunning；C/engine/CronJobExecutor.java:39；R/tool/cron/ManagedCronSessionRunner.java:53 | 旧实现连续失败3次禁用、Every退避、2小时后清 running，runner 使用空凭据和内存 Session 同步等待完成。这些是旧实现事实，不能作为新无重跑、不补跑、未知保持占用或自动暂停政策的实现证据。 |
| 非交互门禁 | [R/runtimeapi/runtime/RuntimeActiveExecution.java:177](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/runtime/RuntimeActiveExecution.java#L177) · beforeToolCall/authorizePreparedQuestion；R/tool/question/PreparedQuestionInvocation.java:16；R/runtimeapi/runtime/RuntimeToolPermissionPolicy.java:70 | 交互识别同时涉及内置工具、可信权限 ASK 和自定义 PreparedQuestionInvocation；自定义问题即使为 ALLOW 也需要交互。只从 Cron profile 删除 AskUserQuestion/ExitPlanMode 不能覆盖全部入口；定时 Host 终止策略待实现。 |
| 工具错误与根终态 | R/tool/builtin/BuiltInToolProperties.java:37；[modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java:112](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java#L112) · runTurns/runToolPhase | 现有 Cron profile 不含提问/审核工具；AgentLoop 在工具结果后继续模型轮。普通工具异常或 isError 不等于结束根执行，需 Host 明确终止原因并阻止继续推进；参数失败仍保留下一轮模型修参，不自动重放。 |
| Mate 已有样例能力 | Mate `README.md:42`；`src/main/java/com/huawei/hicampus/mate/agentdefinition/controller/AgentDefinitionController.java:38/61` · getRuntimeAgent；同根 `service/impl/AgentDefinitionServiceImpl.java`、`src/main/resources/mapper` 与 `src/main/resources/db/schema.sql` | README 和 Controller 明确可运行示例；Agent 目录/runtime 入口存在。所查 `src/main/java`、resources 与 POM 未观察凭据存储/解析或 `/runtime/tools` 服务端；另有 LlmChatController，不应误称整仓只有一个 Controller。示例已有 Agent 元数据不证明生产凭据或租户授权完整。 |
| Mate 客户端不等于服务端 | Claw R/common/client/HttpMateToolClient.java:133/153/174/307 · queryToolIdsByAgentId/queryToolIdsBySkillId/queryToolMetaByIds/invokeTool；`modules/coding-agent-cli/src/main/resources/application.yml:109` | 客户端配置已有工具定义查询与 execute 调用，发现不带本次业务凭据，实际执行才映射 Header。客户端端点只证明消费者预期，不证明上述 Mate 示例已实现对应服务端。 |
| 合并与依赖维护 | Claw `scripts/sync-campusclaw.sh:41` · MODULES；`.github/CODEOWNERS:9`；根 `pom.xml:43/99` · jobrunr.version/dependencyManagement | 同步脚本和所有权仍引用 cron；corporate 是生成镜像，应从 modules 迁移后生成。全仓 POM/生产 import 未见 JobRunr 实际消费者，只有未消费版本占位；删除它不等于降低当前运行包体。 |

**CampusClaw 当前目标（待实现）。** 权威规则由[执行专题](execution.md)维护：不补停机漏跑，活动任务遇忙跳过，不为本次失败或故障重建 Run/Session、重发首消息或重复可能已执行业务；结果未知保持任务占用并只读对账。可靠记录已确定终态的重试不是业务重跑。首版无持久等待：按 M03 五阶段先准备可信目标和校验参数，再判断权限；意外 ASK、提问或计划审核阻止待确认业务、记录原因并结束根执行，不能默认批准。失败是否自动暂停整个 Schedule 仍待确认，不继承旧连续失败3次禁用，也不把未答复写成永不自动暂停。

Mate 拥有可信接口定义、执行授权和按 Agent 绑定的凭据解析，Claw 只保存非秘密授权依据；每次触发与实际工具执行重新校验当前资格，秘密仅在本次内存和实际 execute 使用。发现不带业务凭据，服务间认证身份与业务执行凭据分开。普通交互 Session 仍沿用本次 Header 快照；[Mate 配套内部契约](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md)是待实现草案，公司服务认证及生产凭据部署未核验。

删除 Schedule 和全部 Run 不自动取消已受理执行；Session 保持独立归属、授权、观察和停止入口，回调只收尾原根执行。反向删除 Session 保留仍存续 Schedule 下的 Run 受理事实。首版定时输入仅文本，普通 Session 文件引用不受影响。这些是产品约束及安全边界，不从 Claude 归档或其他基线的删除行为推断。

**模块及依赖取舍。** 定时能力并入 `modules/coding-agent-cli` / `campusclaw-coding-agent`，实现包收敛到 `com.campusclaw.codingagent.schedule`，薄模型适配保留在 `.tool.cron`，保持 agent-core/ai 单向依赖。HTTP 与工具共用应用服务，异步 Dispatcher 接既有 Runtime；旧两处工具 Schema、15个生产类/7个测试、POM、同步脚本与 CODEOWNERS 一起迁移，不能只搬入口类。该架构变更减少独立制品与同库受理的跨模块接线，代价是 coding-agent 承担配置、调度和生命周期编排，须通过包职责与无环装配维持边界。

不新增外部依赖，复用 JDK21、Spring Boot3.4.5/Spring6.2.6、Jackson、MyBatis Starter3.0.4 与既有数据库驱动。已读取本机对应版本的缓存 POM：spring-context 依赖 spring-aop/beans/core/expression、micrometer-observation；Jackson databind 依赖 annotations/core；MyBatis Starter 依赖 Boot/JDBC、autoconfigure、mybatis/mybatis-spring。coding-agent 已有这些运行库，必要时显式声明 spring-context 仅调整依赖归属；完整冲突消解后的 dependency tree 和 corporate NativeParent 未核验，不能声称传递图或公司镜像构建已通过。

本节只读核验源码与既有测试材料，没有运行 Maven、GaussDB、多副本、凭据轮转或无人值守业务测试。实施验收至少覆盖 ASK/自定义问题不得执行业务、参数错误可修正、不默认批准、正常迟到与恢复不补跑区别、故障不重放、未知不释放占用、删除/受理竞争及反向 Session 删除保留 Run；上线初值与容量验证见[执行专题](execution.md#deployment-defaults)，默认数值不是性能结论。

<a id="schedule-time-summary-evidence"></a>

### 8.18 计划时间摘要与接口范围（2026-10-08）

本节仅重新核对 Claude Managed Agents 公开 Beta [Deployment 操作目录及模型](https://platform.claude.com/docs/en/api/beta/deployments)和[定时 Deployment 指南](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)，不升级 Java 或其他 Agent 的历史源码快照。

| 已读取公开契约 | 证据边界 |
|---|---|
| Deployment 操作目录 | 列出 create/list/get/update/archive/run/pause/unpause，未列出接受未保存规则的独立时间预览操作；仅证明当前公开目录，不能据此断言 Console 内部没有校验能力 |
| schedule.upcoming_runs_at | 最多五个未来 Cron 时刻，active/paused 均可返回，paused 表示假设恢复后的计划；指南以保存后的 Deployment 响应确认配置时间，不等于独立预览接口 |

CampusClaw 当前目标不提供未保存规则的独立预览。创建、更新在保存时校验规则，完整 Schedule 响应继续包含 upcomingRunsAt；详情、列表及启停响应沿既有规则计算计划摘要。该范围选择属于产品约束：减少额外接口及保存前后两条交互路径，代价是调用方必须保存后才能取得服务端计算的计划时间；有效计划保存即参与自动调度，不新增试保存、预览 token 或默认暂停流程。规则失败不保存，现有 lastRunAt、时区和暂停语义保持。目标接口仍待实现；本次修改设计、生成器和展示，不作为产品代码删除或执行验收证据。

<a id="schedule-console-evidence"></a>

### 8.19 Console 触发方式与前端映射（2026-10-08）

同日通过本机Chrome观察Claude创建Deployment的Manual/Schedule、频率菜单、自定义Cron和未来五次时间；重读官方Scheduled deployments，仍为Beta。完整观察、默认主线Java `769e86592285f4a25b0febaf551eddea6bc7212c` 的前端入口核验，以及旧功能提交 `2b93cbea90b3e876f5a87a8905c816f0e33b8f47` 的ScheduleForm.vue/requestPreview差异统一见[M07证据](../../07-前端设计/source-evidence.md#schedule-console-evidence)。只升级页面映射范围，不把主线前端组件缺席外推为后端缺陷，也不改写旧Cron/受理源码证据。

目标仍用schedule:null表达仅手动；没有新增trigger配置枚举，active/paused保持独立，Run来源取单次记录。界面采用分区和显式模式；旧前端独立preview须移除，权威时间来自保存/读取后的upcomingRunsAt。原型与页面要求由[M07场景09](../../07-前端设计/场景/09-配置与管理定时任务/README.md)唯一维护。

<a id="failure-doc-structure-evidence"></a>

### 8.20 基线设计文档的失败处理写法（2026-10-11）

2026-10-11 在临时目录隔离 clone 各默认分支最新快照，只读设计文档如何组织失败处理，用于[定时任务设计 §5.2.1](design-restructured.md#failure-recovery)；不升级本文其他节的实现结论或历史 SHA。

| 基线 | 默认分支与完整提交 | 仓库相对路径与位置 | 已观察的写法 |
|---|---|---|---|
| pi | main `cdaf6c227d4718a72b59ccd02152c9614df44cfc` | `packages/durable/docs/spec.md` §1、§5.2、§10.1、§12 | 规范性文档；先列不变量，§10.1 按错误类型各给一条规则，§5.2 用意图—外部动作—结果三段提交处理结果未知，§12 列 API footguns |
| DeepSeek Harness | master `d743267388641bc76f17c45ce8b4c231aed1d32c`（alpha） | `.agents/notes/README.md`；`.agents/notes/implemented/architecture/2026-09-16-host-schedule-storage.md`；`.agents/skills/dsh-error-handling/SKILL.md` | Agent Note 固定 Problem / Decision / Alternatives considered / Consequences；失败与非保证写在 Decision 和 Consequences 中；错误处理规范要求写清处理方、影响范围、副作用状态（absent/partial/committed/unknown）、清理责任和可见的下一步 |
| OpenCode | dev `e31136bdbdb43e934d8bbd81e75a2065a2625699` | `specs/v2/README.md`；`specs/v2/session.md`；`specs/v2/tools.md` | 当前契约以陈述式定律作标题，如 Retry Is Narrow And Observable、Recovery Boundaries Stay Explicit；明确不保证 exactly-once |
| Codex harness | main `8c0f7011674145da7e10627769fb221c74fbf7a0` | `docs/`、`codex-rs/docs/` | 所查范围只有使用文档，未发现设计文档 |

Claude Managed Agents 本次未核对。

## 9. 文档验收

2026-10-08 的接口范围检查通过：配置清单与HTML一致为10个Claw操作、2个Mate草案，全仓无独立预览路径或操作标识残留，原有JSON示例保持一致。API技能检查通过4份Markdown、4份SVG及HTML脚本；仓库图检查通过36专题、132块、53时序图、0错误，managed_session_compaction的既有3条件组范围提示不变，图索引重新生成后无差异。浏览器检查覆盖共享样式、操作归属及版本、折叠状态、响应/语言切换、360px和无JavaScript回退；类图已查看1282×1382原尺寸与840px文档宽度，职责链保持。生成同步和git diff --check通过；未执行产品或数据库测试。

2026-10-05 的0.28.0在HEAD加本任务文件的隔离快照完成校验，保留无关工作树修改。M10与Mate共享配置两个专题的API技能检查通过（共7份Markdown、5份SVG，无OpenAPI/HTML适用项）；仓库check-diagrams.py --render通过（36专题、132块、53时序图、0错误），图索引重新生成。既有managed_session_compaction三个条件组的范围提示沿用原解释，本次未修改该图。24个JSON示例、489个本地文件目标与图源块锚点通过；6个完整Schedule示例字段集合、纯文本输入和状态/原因一致，2个Run示例保持八字段及sessionId/error互斥。实际仓库git diff --check通过，补足隔离快照不是Git仓库而跳过的检查。

本专题4张SVG由PlantUML生成并检查原尺寸与840px文档宽度：自动流程1474×1113、全局类图1282×1382、保存643×659、手动运行1255×889；职责链、凭据解析时点、删除返回路径和非交互约束一致，无裁切或标签遮挡。全局图与自动流程缩放后文字较密，保留原尺寸入口；稳定块起始行为1/62/166/203。只合入本专题索引变化。未运行产品、Maven、GaussDB或多副本测试；自动暂停Schedule的策略仍待决，Mate新增HTTP为草案，文档验收不代表运行能力已实现。

2026-10-05 的 0.27.0 同步删除Schedule及全部关联Run、保留Session的目标，两个读取接口和在途取消仍按各自确认范围维护。沿用当日§8.15～§8.16已核验的源码与公开文档，不新增基线实现结论。HEAD加任务文件的隔离快照通过API技能检查（3份Markdown、4份SVG）、仓库图示检查（36专题、132块、53时序图、0错误）和图索引生成；既有managed_session_compaction三个条件组的范围提示沿用原解释。19个JSON示例、290个本地文件目标及图源块锚点检查通过，实际工作树git diff --check通过；隔离快照不是Git工作树，该项在实际仓库补检。

四份SVG已重新生成，ASCII、XML和生成同步通过，稳定块起始行为1/57/138/172。逐图查看原尺寸和840px文档宽度：自动运行图1289×1064、全局目标类图1192×1238、配置保存图630×609、立即运行图1133×839；新增文字与返回路径无裁切，完整职责链及既有类图布局保持。840px自动运行图及类图文字较密，保留原尺寸入口。图索引仅合入本专题尺寸与图源锚点变化，保留无关修改。没有产品代码、数据库或实际删除实验，未新增Maven依赖；文档校验不代表删除、授权或并发规则已实现。

2026-10-05 的 0.26.0 只补充五份Markdown中的删除基线证据与取舍，不改变已确认接口或把历史候选改为正式规则。HEAD加任务文件的隔离快照通过API技能检查（3份Markdown、4份SVG）、仓库图示检查（36专题、132块、53时序图、0错误）和图索引生成；保留既有managed_session_compaction三个条件组的范围提示。19个JSON示例、290个本地文件链接及20个新增GitHub提交/路径/行号目标核对通过，新增锚点存在；四份SVG与图索引再生成均等于HEAD，无图源和布局修改、无新增视觉验收。实际工作树git diff --check通过。基线测试仅阅读断言，没有运行产品测试或实际删除实验；未引入产品代码、API字段或Maven依赖。

2026-10-05 的 0.25.0 只更新五份 Markdown，登记两个Run读取条件入口及删除历史范围，未把未确认的保留方案写成正式能力。HEAD加本任务文件的隔离快照通过API技能校验（3份Markdown、4份SVG）、仓库图示检查（36专题、132块、53时序图、0错误）及图索引生成；既有managed_session_compaction的三个条件组提示沿用原边界解释。19个JSON示例、285个本地文件链接及新锚点检查通过；图源未改，四份SVG和图索引再生成与HEAD一致，没有新增布局或视觉验收。实际工作树git diff --check通过；没有产品代码、产品测试或新增Maven依赖。独立历史是否保留仍待决定，两个GET的参数、错误和完整响应尚未冻结。

2026-10-05 的 0.24.0 校验采用 HEAD 加本任务文件的隔离快照，保留无关工作树修改。本专题 API 技能校验通过（3份 Markdown、4份 SVG）；仓库 `check-diagrams.py --render` 通过（36专题、132块、53时序图、0错误），图索引已重新生成。既有 managed_session_compaction 的三个条件组提示沿用原边界解释。配置专题19个 JSON 示例可解析，六个完整 Schedule 示例字段集合一致，两个 Run 示例字段集合一致且 sessionId/error 恰好一个非空；暂停和取消暂停的状态、原因及五次计划预览通过检查。

PlantUML ASCII、SVG XML、图源生成同步、Markdown图路径及源码锚点检查通过，稳定块起始行为1/53/131/165。新增立即运行图1133×823及调整后的全局目标类图1192×1188均已实际查看原尺寸和840px文档宽度，检查职责链、文字、箭头、分支与返回路径；配置保存图仅随前序块变化更新源行元数据。实际工作树 `git diff --check` 通过。没有新增 OpenAPI、Maven 依赖或产品代码，未运行产品测试；校验仅证明设计材料一致，不代表候选语义已确认或运行、暂停竞态已实现。

2026-10-04 的 0.23.0 同步删除成功200完整 Schedule 回执及其候选取值、重复删除404，与创建/读取/更新复用字段形状。HEAD 加五份任务 Markdown 的隔离快照通过 API 技能校验（3份 Markdown、3份 SVG）、仓库 `check-diagrams.py --render`（36专题、131块、52时序图、0错误）及图索引再生成；14个 JSON 示例可解析，创建、列表元素、更新和删除的四个完整资源示例字段集合一致，删除回执计划数组为空且无新增删除字段。保留既有 managed_session_compaction 的三个条件组提示及其边界解释。图源未修改，三份 SVG 与图索引再生成后均与 HEAD 一致，无新增视觉布局；工作树 `git diff --check` 通过。只校验设计材料，没有产品实现或运行测试，候选细节不因此变为已确认。

2026-10-04 的 0.22.0 将当前目标统一为直接删除，清理配置、主设计和架构对比中的归档候选并同步根导航。隔离快照通过本专题 API 技能校验、仓库 `check-diagrams.py --render`（36专题、131块、52时序图、0错误）、图索引生成；既有 managed_session_compaction 的三个条件组提示保持原边界解释。五份修改 Markdown 的13个 JSON 示例、300个本地链接及锚点校验通过；创建、列表元素和更新资源字段集合一致，无新增归档/删除响应字段；错误体仍为两字段，DELETE候选204无正文。全仓检索未发现仍生效的归档候选枚举、错误码或恢复入口，Claude公开事实、历史版本记录及无关专题的归档用语保留。

本次只修改既有 scheduled_run_sequence 的删除准入检查与候选在途说明，PlantUML ASCII、生成同步和 SVG XML 通过，原尺寸1214×998及840px文档宽度的文字、箭头和返回路径已实际检查；未重构全局类图，稳定块锚点仍为1/53/130。图索引只合入本图尺寸变化，保留无关修改；实际工作树 `git diff --check` 通过。没有新增依赖、产品代码或产品测试；校验不代表删除整项操作已确认，也不证明数据库竞态、权限或历史清理已实现。

2026-10-04 的 0.21.0 删除/归档候选只修改四份 Markdown，未变更公共接口实现、图源或 SVG。HEAD 加本任务文件的隔离快照通过仓库 `check-diagrams.py --render`（36专题、131块、52时序图、0错误），本专题 API 技能校验（3份 Markdown、3份 SVG）及图索引再生成；索引与既有生成物一致。保留既有 managed_session_compaction 的三个条件组提示及其边界解释，未新增复杂度或重新视觉验收未改图形。四份文档的12个 JSON 示例、184个本地链接目标及新增锚点检查通过，实际工作树 `git diff --check` 通过；没有 OpenAPI、产品测试或新增 Maven 依赖。此结果只验证候选记录与证据引用，不代表生命周期选择已确认或新能力已实现。

2026-10-04 的 0.20.0 验收在 HEAD 加本任务文件的隔离快照完成，保留无关工作树修改。所有 Claw 接口取消客户端条件与请求键协议的变更同步到 Runtime catalog、配置契约、命令、计划模式、前端及 Mate 协作说明；历史实现与冻结 HTTP 1.37 测试资料保留其版本归属，附件对象存储 ETag 不属于本次移除对象。

`plantuml -tsvg diagram.puml`、仓库级 `check-diagrams.py --render`、Runtime 与本专题 API 技能校验及图索引生成通过：36 个专题、131 个块、52 张时序图，0 错误。唯一复杂度提示为既有 managed_session_compaction 的三个条件组，沿用[时序图规范](../../时序图规范.md#3-从总览下钻)中的边界解释，未修改该图。已检查 PlantUML ASCII、SVG XML、生成同步、Markdown 图路径及源码块锚点；24 份修改 Markdown 的14个 JSON 示例及本地链接检查通过，实际工作树 `git diff --check` 通过。

Runtime `validate-chat-api.py --full` 通过，包括十项当前操作、73项 Python 测试与事件契约负向校验；设计门禁确认当前操作无这两个请求头、配套 ETag、412/428 或等价 body/query 令牌。`test_chat_api.cjs` 的十接口 Header/响应/语言切换、重开状态与无 JavaScript 回退检查通过。实际浏览器查看 Session 读取、更新和 Command 的桌面1440px及360px页面，无横向溢出；更新页面禁用 JavaScript 后原生展开仍可读取作用、请求、成功与错误。生成的 Runtime/Help 页面与精确 JSON 同步。

本专题创建资源与列表元素逐字段一致，更新响应字段集合一致，更新示例仅改变提交的 description/schedule/metadata 及 updatedAt；错误示例保持两字段，09:00 上海时间正确投影为01:00Z。定时全局图1050×1188、保存图630×609已检查原尺寸与840px；Session、命令、计划和前端的受影响图也已完成原尺寸及文档宽度检查。计划全景类图在840px用于浏览完整职责布局，细节通过原尺寸入口阅读；本次没有重排或缩减其结构。混合修改的计划图源和根图索引仅提交本任务差异。

没有新增 OpenAPI，相关检查不适用；没有产品代码修改、产品测试或新增 Maven 依赖。上述结果只证明设计契约、展示与图源的一致性，不能替代数据库并发、公司身份、凭据轮转或无人值守调度验收。源码基线和仍待实施的服务端/前端迁移见 §8.12。

## 10. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.35.0 | 2026-10-13 | 任务内容 message 改为纯文本 prompt，移除 credentialIds，业务凭据改由 Mate 按 Agent 绑定在运行时决定。 |
| 0.34.0 | 2026-10-12 | 登记四个基线设计文档的失败处理写法，供模板重构稿引用。 |
| 0.32.0 | 2026-10-10 | 定时表及 Session 扩展归入 Claw 全库数据库设计，原文件仅保留导航。 |
| 0.31.0 | 2026-10-10 | 登记 PR #332 数据库专项证据入口，保留其他源码与官方契约的历史归属。 |
| 0.30.0 | 2026-10-08 | 重核Console触发方式并引用M07页面映射及新旧前端源码范围。 |
| 0.29.0 | 2026-10-08 | 重核Claude公开操作目录与计划时间摘要，记录无独立预览的当前产品范围及代价。 |
| 0.28.0 | 2026-10-05 | 核验 Mate 示例和 coding-agent 合并边界，确定非交互、不补跑、不重跑及独立 Session 生命周期的实施差距。 |
| 0.27.0 | 2026-10-05 | 明确删除Schedule及关联Run、保留Session的目标，区分独立授权、临时协调与在途取消待定。 |
| 0.26.0 | 2026-10-05 | 核验OpenClaw与DSH不同删除关系，区分历史保留、会话清理和在途取消及其他基线证据边界。 |
| 0.25.0 | 2026-10-05 | 核验Claude Run列表/详情与既有数字分页，明确删除后日志残留不等于独立历史读取能力。 |
| 0.24.0 | 2026-10-05 | 核验Claude三个动作与Run模型，并对照旧Cron同步触发、启停竞争及Runtime受理查询缺口。 |
| 0.23.0 | 2026-10-04 | 核验 Claude 两种成功响应并采用 Deployment 完整资源形状，明确删除回执及重试语义边界。 |
| 0.22.0 | 2026-10-04 | 明确 Schedule 直接删除的已确认范围及与 Claude 归档的差异，保留精确删除响应和历史运行处理为候选。 |
| 0.21.0 | 2026-10-04 | 核验 Claude 归档公开契约及未知边界，对照 Cron 删除竞争、历史读取和 Session 墓碑机制。 |
| 0.20.0 | 2026-10-04 | 明确所有 Schedule 接口取消客户端条件及幂等请求头，保留数据库更新与内部运行去重并记录 Session 迁移差距。 |
| 0.19.0 | 2026-10-04 | 核验 Session 条件更新与 Cron 存储边界，补充 Claude 更新规则及 Schedule 更新候选的复用限制。 |
| 0.18.0 | 2026-10-04 | 补充 Schedule 类型与暂停原因的已确认目标、Java 实现差距及 Claude 创建示例的语义冲突。 |
| 0.17.0 | 2026-10-04 | 核验 Cron、Session 与 ListEvents 读取基础及 Claude Deployment 契约，区分已确认完整资源与候选分页和 Run 观察边界。 |
| 0.16.0 | 2026-10-04 | 记录 credentialIds 直接引用的已确认目标，凭据权威和多目标匹配仍为实现缺口。 |
| 0.15.0 | 2026-10-04 | 重核 Vault 与 Credential 的资源层级，区分已确认凭据能力与待定引用字段。 |
| 0.14.0 | 2026-10-04 | 补充创建时间摘要、小写状态、元数据边界与 Vault 凭据引用的公开证据。 |
| 0.13.0 | 2026-10-04 | 核验新 Session 与 Agent 定义边界，并补充 Claw 和 Claude 创建响应的准确差异。 |
| 0.12.0 | 2026-10-04 | 重核名称与仅 Cron 契约，补充文件上传边界及五个基线的定时会话目标证据。 |
| 0.11.0 | 2026-10-02 | 核对 Claude 时间示例边界，区分既有毫秒实现与 Claw 统一秒级目标。 |
| 0.10.0 | 2026-09-30 | 补充既有 Session 与完整事件时间证据，明确调度响应采用 UTC 并固定三位毫秒。 |
| 0.9.0 | 2026-09-30 | 同步已确认的 Cron 默认上海及绝对时间输入规则，保留旧实现和基线时区证据。 |
| 0.8.0 | 2026-09-30 | 核验四个辅助基线的时区字段及默认来源，同步已确认的整数秒与固定起点行为。 |
| 0.7.0 | 2026-09-30 | 明确 Claw 创建 every 时缺省首次等待一个间隔，保持精确取时与基线实现的证据边界。 |
| 0.6.0 | 2026-09-30 | 区分 Claw 已确定的可选 startAt 与尚待确定的首次时间默认方案，保留原基线核验范围。 |
| 0.5.0 | 2026-09-30 | 核对五个基线的首次触发与间隔基准，明确 DSH 固定时间表、pi 固定延迟及托管调度的公开证据边界。 |
| 0.4.0 | 2026-09-30 | 明确 Spring 六字段及固定、动态调度证据边界，同步单条消息输入与两种 Session 目标。 |
| 0.3.0 | 2026-09-29 | 重核 Claw 配置边界及 Claude 创建语义，区分历史版本能力缺口、文本范围和 Cron 成本选择。 |
| 0.2.0 | 2026-09-29 | 核对前端调试边界、Mate Agent 配置样例和 Claw 保存行为，补充独立配置 API 的证据与差距。 |
| 0.1.0 | 2026-09-29 | 核对 Claude 调度公开契约、当前 Cron 与持久化 Runtime 基础，明确两类执行目标及实现差距。 |

<a id="mate-boundary-review"></a>

## 9. Mate / Claw 身份职责专项（2026-10-10）

范围：按用户明确的职责划分检查 PR #332 中用户、范围、会话归属、权限与配额的传播及其必要消费者；不是该 PR 全部 434 个变更文件的完整质量审查。设计起点为 `pi-mono-java-design@6ec8fd2b43a209b582b1a8b726f23757a2dafab2`；当日重新 fetch `main` 和 PR，head 为 `e9d31e8888a81b7fe95071e705482bb16fa10476`，base 与实际 merge-base 均为 `769e86592285f4a25b0febaf551eddea6bc7212c`。没有修改实现工作树。外部 Agent 及 Mate 服务端未重核，不更新历史基线结论。

当前有效规则由[数据库身份边界](../../03-数据与存储/Claw数据库设计.md#mate-ownership)和[Mate 归属交接](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md#session-ownership)维护。下面的偏差针对当前职责修正；旧设计也曾要求 Claw 保存范围和 owner，不能把设计失当全部归责于实现作者。各项为待修改的架构偏差，不据此声称已发生生产越权。

实现源码公共根 `J = modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`，资源根 `R = modules/coding-agent-cli/src/main/resources/`；下表路径均相对 `pi-mono-java`，均绑定上述 head。

| 编号 | 已观察源码与触发路径 | 当前影响与修正落点 |
|---|---|---|
| B1：持久化身份副本 | `R/db/gaussdb/install/session_schema.sql:37–38,618–631,657,696–697`；`J/runtimeapi/schedule/ScheduledRuntimeAdmissionService.newSession/encodeContext` 将范围及会话 owner 写入 Session 与 execution JSON；`ScheduleApplicationService.applyBinding/createLocked` 保存 Schedule 的范围、操作者和 owner | 删 Session 两列不足以消除身份副本。同步撤销 Schedule 的三项身份列、Run 的 scope、DTO/Mapper/安装注释及执行 JSON；用户归属在 Mate 按技术资源 ID 维护。公司 SQL 由 canonical 同步生成，不能只改单边。两条 Session COMMENT 已存在，位置在调度表后，不是缺注释。 |
| B2：Claw 本地资源权限与用户配额 | `J/schedule/application/ScheduleAccessPolicy.java:32–49` 按 subject 与本地 scope 判断可见；`ScheduleRunService.getRun/listRuns` 延续同样规则；`R/mapper/schedule/ScheduleMapper.xml:16,39–48,74` 按 scope 计数、过滤与分组；`ScheduleApplicationService.requireQuota/page` 读取范围配额、写查询范围 | Mate 维护当前用户权限、资源集合、审计和范围配额；Claw 校验服务授权结果，只按获准资源 ID 查询且先过滤再分页。删除 scope 后须同时改查询、索引、配额及公平轮转，不能去掉 WHERE 后直接查询全库。实例容量、任务互斥和数据库领取仍留 Claw。 |
| B3：通用执行对象承载 Cron 用户主体 | `J/runtimeapi/runtime/RuntimeActiveExecution.java:68,94–100` 保存 `ScheduleSubjectDTO`；`RuntimeExecutionContextFactory.java:85,102` 捕获主体；`HttpRuntimeScheduleSubjectProvider.currentSubject` 从 Servlet 认证桥读取；`RuntimeSessionEngineRegistry.java:232` 交给 `AgentScopedCronToolFactory.create` 和 CronTool | 为 Cron 将用户权限主体传播到普通 Runtime。移除该具体主体与捕获链；Cron 适配器只传当前 Session/执行、Agent、目标资源及操作，向 Mate 请求授权，不由通用 Runtime 保存用户归属。保留 Host 工具 allow/deny/ask、参数校验及非交互约束，它们不是用户目录。 |
| B4：会话 owner 被当成操作者 | `J/schedule/mate/MateScheduleAuthorizationAdapter.refresh:60–65` 从持久 scope/operator 重建主体并比较 owner；`MateScheduleContextClient.query:90` 接收 owner，`resolveCredentials:97` 将 owner 放进 `ScheduleSubjectDTO.operatorRef`；`ScheduledRuntimeAdmissionService.prepare:129` 也做该转换 | 会话归属、配置操作者和后台授权主体被 Claw 自行拼装，Mate 无法独占其政策。查询只携带服务身份、固定资源/执行和不透明 authorizationRef，由 Mate 解析并检查当前授权；响应不返回 owner/scope。增加 Mate 独立 Session 归属登记与未知结果核对，不能只删赋值后让空主体通过。 |

**保留项及反例。** `claim_owner`、dispatch.owner 和 `schedule_start_owner` 是实例领取权，不是用户；revision、epoch、lease、Session/execution 父子关系和实际开始时间是运行一致性数据。`authorizationRef` 可作为 Mate 记录定位引用，`credentialIds` 可作为资源引用，但均不代表持有即授权。对 Mate 响应的类型、有效期及可信 toolId 校验可保留；这些协议与执行校验不等于 Claw 维护用户权限系统。

**最小实施顺序。** 先实现 Mate 的资源关联、管理授权与 Session 登记/核对能力，定义获准集合和操作结果如何绑定可信服务请求；再移除 Claw 身份字段、SQL/DTO/Mapper 与 Runtime 主体链，同步重写 Schedule 查询和配额；最后生成公司镜像并修改对应测试。首版仅维护完整安装 DDL，不引入假设的存量迁移。

**验收。** 覆盖管理用户与会话归属主体不同、Mate 中权限变更后不更新 Claw 行仍按当前权限判断、资源 ID 篡改、授权为空/过期/服务不可用、空获准集合、权限过滤先于分页、后台无浏览器主体、Cron 不借用 owner 作为操作者；覆盖 Mate 登记失败/响应未知、登记成功而 Claw 回滚、Claw 提交成功但回执丢失、删除 Schedule 后 Session 仍能独立授权及停止。均不得新建重复会话或重放任务。

**验证范围。** 本次执行静态源码与文档核验、相关 XML 解析和 diff 检查；Mate 客户端既有测试仍断言返回 owner/scope，只能证明旧契约，不能证明修正后的边界。未运行 Java/数据库/真实 Mate 联调，不将 PR 作者报告的测试结果当作本次验证。其余规范及无关功能保留未核验。

**显式坏味道检查。** 重复职责为 B1/B2（归属存储和本地范围判断）；大类/职责边界为 B3（不以文件行数判定，具体问题是 Runtime 依赖 Cron 主体）；基本类型语义混用为 B4（owner 与 operator 被互换，而非仅因使用 String）；Java 方法长度未做全 PR AST 计数，标为未核验，不宣称代码规范全面通过。各项集中按上述根因修正，不另报重复严重性。
