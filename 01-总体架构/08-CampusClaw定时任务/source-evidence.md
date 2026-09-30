# 定时任务源码与官方证据

[主设计](README.md) · [Agent 架构对比](../07-Agent架构对比/README.md#a14)

| 属性 | 值 |
|---|---|
| 文档版本 | 0.10.0 |
| 核验日期 | 2026-09-30；各节保留实际核验日期与范围 |
| 产品范围 | 新建独立会话与绑定已有会话均需支持，优先支持独立会话；不据此预设已有会话的拒绝契约或交付阶段 |
| 状态边界 | 进程内 Cron 已实现；数据库调度、持久化后台受理与两类目标的调度接线待实现；企业身份系统未核验 |

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
| J15 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java#L116)；`acceptUserEventLocked`；[modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml#L63)；`lockSessionForUpdate` | 数据库行锁内重新检查 Session idle、plan 可用性，再追加消息并置 running。本地检查不代替数据库准入；这可复用于已有会话竞争，但不证明已有会话调度绑定已实现。 |
| J16 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventOutput.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventOutput.java#L35)；`persistenceOnly`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/PersistenceOnlyRuntimeEventOutput.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/PersistenceOnlyRuntimeEventOutput.java#L20) | 已有无响应流输出策略；Projector 先持久化，该策略丢弃事件工厂，不构造 SSE、不持有连接/缓冲，也不拥有执行取消权。可用于后台执行，当前 Cron runner 尚未使用。 |
| J17 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java#L91)；`start`、`scheduleTimeout`（154）、`commitTerminal`（271）、`retryTerminal`（341） | 订阅投影、安装确认处理器、启动 Agent、处理超时并提交唯一终态；终态写入失败保留执行并重试。可复用生命周期；不等于已有跨进程模型执行接管、启动 CAS 或 Run 对账。 |
| J18 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeContextHistoryService.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeContextHistoryService.java#L34)；`restoreHistory`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/CommittedEventQueryService.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/CommittedEventQueryService.java#L40)；`list` | 按权威线性历史恢复模型上下文，按公共事件分页读取。两种调度目标都可沿用消息权威；不需再在 Run 保存一份完整聊天文本。 |
| J19 | [modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql#L26)；`t_sessions`（26）、`t_session_executions`（81）、活动执行唯一索引（118）、segments（146）、entries（363）、events（426） | 已有 Session、根执行、段、内部历史和公共事件存储；Session 同时只能存在一条非终态根执行。当前 DDL 无 schedule/run/claim 表，Session 状态只有 idle/running；不能用它表示调度领取或未知运行状态。 |

推荐复用既有存储与投影，新增 `ScheduledRunAcceptanceService` 组织同库短事务，并把后台 profile、persistenceOnly 输出和 Run 关联接入公共执行链。该服务、启动权持久 CAS、Run 终态对账均为待实现。不能通过依次调用“创建 Session HTTP + POST 消息 HTTP”宣称获得原子受理，不能在回执丢失时再次创建会话重发 prompt。

两种执行目标均属于已确认产品范围，独立会话优先。候选受理结构分别为：NEW_SESSION 关联新 Session、首消息、根执行与 Run；EXISTING_SESSION 检查原 Session 的可信绑定、授权与运行状态，再追加消息并关联 Run。具体事务、忙时准入与恢复策略仍需运行专题论证；已有 Session 的行锁、历史恢复、公共事件查询是基础能力，不等于两种调度目标已经实现，也不构成首版必须拒绝已有会话的依据。

## 4. 身份、权限与交互证据

| 编号 | 源码路径与定位 | 已观察行为与未核验边界 |
|---|---|---|
| J20 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeRequestContext.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeRequestContext.java#L45)；`mateCredentials`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/mate/MateCredentials.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/mate/MateCredentials.java#L7) | 从请求取得 X-HW-ID、X-HW-APPKEY、Authorization、access-token；凭据对象明确说明 Runtime 不验证真实性、组合或最低完整性，执行时交 Mate 授权，不持久化。不能推断已有长期委托或 Token 刷新。 |
| J21 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/question/BusinessConfirmationAdapter.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/question/BusinessConfirmationAdapter.java#L90)；`requireAvailable`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/BusinessToolDispatcher.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/BusinessToolDispatcher.java#L31)；`assembled` | 公共工厂绑定业务确认适配器；适配器只允许 RUNTIME，CRON/CHILD 返回入口不支持，缺问题端口也失败。当前不存在 Cron 无人审批等待队列。 |
| J22 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/dto/RuntimeSessionDTO.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/dto/RuntimeSessionDTO.java#L19)；Session 字段；[modules/cron/src/main/java/com/campusclaw/cron/model/CronJob.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/main/java/com/campusclaw/cron/model/CronJob.java#L19)；Job 字段 | 这两类对象及 J19 DDL 无 tenantId/ownerId/长期授权引用；读取范围内没有证明可信租户 scope 的解析与仓储约束。通用 RequestHeaderInfo 出现 agentTenantId 字段不足以证明当前链路已隔离。Mate 服务端与公司认证集成未核验。 |

目标的 `ScheduleAuthorizationPort`、可信管理作用域、授权撤销与无人值守身份取得均待实现/待公司契约确定。每次触发仍需可信解析、参数校验、权限判断；任务启用不等于永久批准任意业务工具。遇到 ASK 或需用户交互时按主设计失败并转人工处理；不得从创建请求持久化 Header，不自动批准或猜参重放。工具参数错误与公共安全投影规则由 M03 唯一维护。

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
| RuntimeMessageEventService | 受理时传入计划审核工具可用性，启动时应用已接受模式 | 既有会话调度必须遵守权威 mode，不能默默把 plan 改 build |
| CronTool 与其他旧结论 | 已读取当前 Schema/Agent 绑定实现；旧表未核验的基线与模块保持原证据归属 | 只更新本专题证据，不批量替换 M01～M09 的历史 SHA，也不以旧缺口推断当前 main |

## 6. 测试证据与未执行项

实际阅读的测试断言包括：

- [modules/coding-agent-cli/src/test/java/com/campusclaw/codingagent/tool/cron/ManagedCronSessionRunnerTest.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/test/java/com/campusclaw/codingagent/tool/cron/ManagedCronSessionRunnerTest.java#L71)：`preparesAgentAndUsesCronProfileAtTriggerTime` 断言 CRON、Agent、空凭据及模型解析；`usesPublishedDefaultWhenItIsNotFirstBinding` 断言使用明确 default model，不取第一条 binding。测试 mock 公共工厂，不能据此证明真实集群、持久化或身份链路。
- [modules/cron/src/test/java/com/campusclaw/cron/engine/CronJobExecutorTest.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/cron/src/test/java/com/campusclaw/cron/engine/CronJobExecutorTest.java#L36)：`failureRecordCarriesStableErrorCodeInsteadOfDiagnosticText`、`uncodedFailureUsesGenericStableCodeWithoutDiagnosticText` 断言稳定错误码与不泄露诊断文本。

另定位了 `CronEngineTest`、`CronStoreTest`、`CronRunLogTest`、`CronToolTest`、`CronScheduleTest`，其存在仅说明已有测试材料。2026-09-29 的源码核验没有运行 Maven 测试、编译、真实 GaussDB、多副本故障注入、DST 边界测试、企业身份联调或压测。主设计新增原子受理、唯一触发、租约代次、启动 CAS、未知执行对账、已有会话调度与无人值守权限均仍需实施与验收，不能因静态证据或旧测试存在而写成已通过。2026-09-30 的表达式边界小验证单独记录在[Spring 与 JDK 证据](#spring-scheduling-evidence)。

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
| [Pause](https://platform.claude.com/docs/en/api/http/beta/deployments/pause)、[Unpause](https://platform.claude.com/docs/en/api/http/beta/deployments/unpause)、[Archive](https://platform.claude.com/docs/en/api/http/beta/deployments/archive) | 生命周期各自为管理操作；暂停仍可手动运行，归档不可恢复。指南没有明确说明归档是否终止在途，因此主设计“归档不取消”为 CampusClaw 自己的目标选择。 |
| [Deployment 模型](https://platform.claude.com/docs/en/api/http/beta/deployments) | 状态是 active/paused，归档另由 archived_at 表达；预览最多五项，暂停时可保留假设恢复后的预览。不能把 CampusClaw 的 ARCHIVED 枚举说成照搬原 Schema。 |
| [Authenticate with vaults](https://platform.claude.com/docs/en/managed-agents/vaults) | Vault/凭据以 workspace 为作用域，Deployment 通过引用关联；运行期解析与更新。公开 workspace 访问模型不证明 CampusClaw 的公司租户/用户隔离或委托授权，不能直接存聊天 Token 替代它。 |

相对 A14 的 2026-09-22 证据，本次只更新 Claude 调度范围：将旧“最多 10 秒 jitter”校正为当前比例窗口；明确 Run 的创建结果含义、主 Agent 归档/删除不落 Run 的例外及固定版本语义。未重核的 Claude Session/preview/工具文档仍保留各专题原日期；其他四个开源 Agent 基线保留 A14 原 SHA 与成熟度。

公开 API 的自动生成示例可能同时填入 session_id/error 等占位值，不能用此覆盖字段约束。主设计依据字段文字与指南，并明确区分 CampusClaw 的额外状态与可靠性目标。

<a id="configuration-evidence"></a>

## 8. Claw 配置接口的源码核验

2026-09-29 收敛接口时再次确认 Claw 上游默认 main 并 fetch，仍为 `553dcd5e2ff682f9684810a043b442b37a02e54a`；重读 CronSchedule/CronPayload、CronService/CronEngine、AgentRuntimeManager/MateServiceClient、RuntimeSessionController、AgentDirectorySnapshotDTO 与 UserMessageContentRequestVO。旧新提交未变。下表实现观察保留该快照；目标解释按当前已确认的单条 user.message、可选 schedule 和两种 Session 目标更新，不把目标决定写成已有实现。

C01～C07 保留此前对前端和本地 Mate 示例的历史观察，不构成本版待实现接口清单。Mate 当时读取的是本地 `4b957a3a846659f5b7569c9d6133abc070cd2e3c`，不是当日最新上游或完整生产部署；其 README 定位为待集成的可运行示例。历史 `956b547f5ca12ca89e68f73012f92a4406b0c9fa` 的其他结论不随此升级。本次不新增 Mate 路由、页面、公共 Chat 映射或 Agent 目录契约。

| 编号 | 仓库相对路径与符号 | 已观察实现与配置设计影响 |
|---|---|---|
| C01 | Claw `frontend/README.md`；`frontend/src/App.vue` · configuredAgentId；`frontend/src/components/AppSidebar.vue` | 前端是内部 Runtime 工作台，Agent 从环境变量/开发设置取得；Agent 中心禁用，无定时任务页。新增正式配置客户端不能复用内部直连作为后备路径。 |
| C02 | Claw `frontend/src/composables/useRuntimeApi.ts` · API_PATH/request/createSession/changeSetting | 固定 `/campusclaw-service/v1`；使用 ResultBean 形状、ETag/If-Match 与 no-store。能参考交互模式，不能证明已有 Mate 公共接入。 |
| C03 | Claw `frontend/src/composables/useWorkbenchSessions.ts`；`frontend/package.json` | 会话索引按后端/Agent/caller 本地隔离，草稿留内存；无定时配置列表、请求幂等恢复、vue-router 或表单库。仅保留观察，不在 Claw 契约规定页面存储方式。 |
| C04 | Mate `src/main/java/com/huawei/hicampus/mate/agentdefinition/controller/AgentDefinitionController.java` · listAgents/getAgent/getRuntimeAgent/updateAgent | 已有 `/mate-service/v1/agents` 及详情/runtime/更新；未观察 Schedule 或公共 Chat Controller。只有这些接口存在，不证明完整权限链。 |
| C05 | Mate 同包 `vo/ListAgentRequestVO.java`、`vo/ListAgentResponseVO.java`；`service/impl/AgentDefinitionServiceImpl.java` · listAgents；`src/main/resources/mapper/AgentDefinitionMapper.xml` | 列表 pageIndex 默认1、pageSize默认20上限100；data/total/pageIndex；按 name/displayName/enabled/version 过滤。没有可信操作者/租户范围过滤，不能把 enabled=true 当授权。 |
| C06 | Mate 同包 `vo/AgentInfoResponseVO.java`；`service/impl/AgentDefinitionServiceImpl.java` · buildAgentInfo | 管理聚合含 SYSTEM、permission 和全部绑定。普通候选需授权后安全摘要，不能让浏览器收到管理聚合再隐藏。 |
| C07 | Mate 同包 `vo/ApiSuccessResponseVO.java`、`vo/ApiErrorResponseVO.java`；`controller/ApiExceptionHandler.java` | 示例模拟 ResultBean，更新空 result 被省略；错误是稳定码与文案，无 fieldErrors。Agent 异常未设置 Content-Language。新配置完整资源回显与语言 Header 是新增契约。 |
| C08 | Claw `modules/cron/src/main/java/com/campusclaw/cron/CronService.java` · createJob；`store/CronStore.java` · saveUnsafe/updateJob | create 存储后立即 schedule；文件保存异常仅日志，无配置版本及数据库事务。不能直接包装此方法声称配置 API 已可靠提交。 |
| C09 | Claw `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/AgentRuntimeManager.java` · prepare/rebuild/publish | 完整缓存命中不拉取 Mate，缺失则拉 Agent/Skill、写 staging 并发布目录。配置保存不调用 prepare；元数据校验与目录发布分离。 |
| C10 | Claw 同 codingagent 根 `runtimeapi/agent/AgentDirectorySnapshotDTO.java`、`AgentDirectorySnapshots.java`；`runtime/MateServiceClient.java` · getAgentRuntime/AgentRuntime；`runtime/AgentRuntimeManager.java` · AgentIdentity | Runtime 元数据及目录身份有 version，但当前装配快照不含版本选择；远端查询仅按 agentId，无历史版本解析或 Environment 选择契约。缺的是可执行历史绑定，不是整个系统没有版本字段。 |
| C11 | Claw 同根 `runtimeapi/web/RuntimeSessionController.java`；`session/RuntimeSessionUpdateService.java`；`persistence/MyBatisRuntimeSessionRepository.java` · updateSession | 既有 Session 更新使用 ETag/If-Match、428/412 与数据库锁内版本重验。Schedule 借鉴该模式；Mate Agent 更新仍为锁行后最后写入生效，不宣称全系统已经统一。 |
| C12 | Claw `modules/common/src/main/java/com/campusclaw/common/constant/ClawConstants.java` · RuntimeApi.MAX_MESSAGE_CHARACTERS；同 codingagent 根 `runtimeapi/vo/UserMessageContentRequestVO.java` · TextRequestVO/FileRequestVO；`modules/cron/src/main/java/com/campusclaw/cron/model/CronPayload.java` · AgentPrompt | 普通文本上限262144，Runtime 已有文本和文件引用块，严格类型与未知字段检查。已确认配置输入为单条 user.message，可包含文本和现有文件引用；不扩成多初始事件或 system.message。旧 CronPayload 仍只有 agentId/prompt，输入保存与运行接线须迁移，不能直接宣称已支持调度附件。配置更新另须保留省略/null差异。 |
| C13 | Claw `modules/cron/src/main/java/com/campusclaw/cron/model/CronSchedule.java` · At/Every/CronExpr；`engine/CronEngine.java` · computeNextDelay | 三类型已有，Cron 采用 Spring CronExpression；已确认继续使用 Spring 六字段，精确规则见[配置契约](configuration.md#spring-cron-contract)。原 every 按完成/创建时间计算，固定 startAt 仍是目标改动。六字段复用既有依赖，但不表示可以直接接收 Claude 五字段，亦不构成硬实时保证。 |
| C14 | Claw 同 codingagent 根 `runtimeapi/web/RuntimeSessionController.java` · get/update/create | Claw 资源使用 sessionId；已有会话目标对应 existingSession/sessionId，不引入 Mate 的 chatId。两种目标均需支持，独立会话优先；现有 Session 201/Location 与 ETag/If-Match 可作接口风格依据。 |

此前在 Mate 示例 Controller/Service/Mapper、`src/main/java`、resources 与 POM 范围，未观察公司认证适配、租户范围、Chat 映射或调度配置服务；这是历史样例边界，不推断其他部署。当前 [Claw 配置设计](configuration.md) 只要求其自身取得可信调用范围并校验绑定，具体适配待接线，不用读取 Header 代替认证证据。

配置主基线采用 2026-09-29 重读的 Claude [Create Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/create)、[Update Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/update)及 [Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)。当前已确认目标是：schedule 可省略，省略时只保存配置；提供 schedule 后创建即登记自动计划；运行由显式试运行或后续定时触发发起，保存本身不执行。输入为单条 user.message，内容支持文本和现有文件引用；Cron 采用 Spring 六字段。省略保持、schedule:null 清除与嵌套整体替换沿用配置规则；缺少环境选择及历史版本 pin 仍是能力差距。ACTIVE 的自动运行承诺需以运行链路可用为发布前提。幂等/ETag 是本产品的候选可靠性契约，不从公开文档缺少描述推断 Claude 内部没有保护。

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

临时片段未保存为仓库测试，以上不是完整方言兼容、DST、实际定时精度或产品集群验收。已确认的是沿用 Spring 六字段；@Scheduled 固定任务与 TaskScheduler 动态任务是可用的框架方式，当前源码仍采用 JDK 调度器。后续多实例领取、持久游标、重叠与恢复机制尚未冻结，不能从时间解析器的选择推导这些运行策略。

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

对 Claw 的影响：every 固定时间表、整数秒 intervalSeconds、可选 startAt、创建缺省先等一个间隔及固定起点保存/回显均已确认；更新省略起点重新起算，新设起点必须未来，回传当前保存的旧起点允许，具体规则由[配置契约 §3.2](configuration.md#32-三种类型的边界与待定细节)维护。DSH 的首次等待可作参照，但它没有显式 every 起点；pi 的首次立即与固定延迟也不能被当作同一语义。Claw 的取时点、重叠和补跑仍待确定，不能把产品选择归为基线统一规则。

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

这些证据支持按时间类型决定是否需要时区，不支持统一行业默认值。Claw 已确认 Cron 时区可省略并默认保存、回显 Asia/Shanghai，at/startAt 须携带 Z 或数值偏移，at/every 不另设 timezone；这是面向主要园区场景的产品约束。绝对时刻响应统一 UTC 且固定三位毫秒已确认，输入精度仍待确认，精确规则只由[配置契约 §3.4](configuration.md#34-时区选择与确认边界)维护。本节仅静态读取源码和官方契约，未执行产品任务或时区测试。

<a id="runtime-time-format-evidence"></a>

### 8.4 既有 Session 与完整事件的时间表示

2026-09-30 重读已登记的 Java `553dcd5e2ff682f9684810a043b442b37a02e54a` 快照及当前设计契约，仅核验以下时间生成和响应格式；未更新上游快照，不称为当次最新实现，未运行 HTTP 产品测试。

| 范围 | 已观察事实 | 路径与关键符号 |
|---|---|---|
| Session 创建 | 字段为 createdAt，服务端以 UTC 生成，VO 使用 OffsetDateTime 并按字符串序列化；所查创建链路未固定三位小数 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionService.java` · newSession（117）、now（138）；同 runtimeapi 根 `session/RuntimeSessionResponseAssembler.java` · createView（30）、`vo/CreateSessionResponseVO.java` · createdAt（37） |
| 创建契约 | 示例为 `2026-08-15T11:30:00Z`，表示 UTC；该例不证明禁止小数秒，也不证明固定毫秒 | [01-create-session.json](../01-CampusClaw多Agent运行时/接口契约/操作/01-create-session.json) · result.createdAt（58）；[Session 接口展示](../01-CampusClaw多Agent运行时/chat-api-review.html) |
| 完整公共事件 | createdAt 明确为 UTC、固定三位毫秒；实现通过 appendInstant(3) 格式化绝对时刻 | [事件共享契约](../01-CampusClaw多Agent运行时/事件契约/common.json) · 时间规则；`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/CommittedEventProjection.java` · EVENT_TIME_FORMATTER（68）、project（91） |

定时任务已确认沿用 Session 创建接口的 UTC 时间响应，并参考完整事件格式固定输出三位毫秒；表示方式不会改变 Cron 按保存时区计算的计划。固定三位毫秒是新增调度接口的目标约束，不能反推现有 Session 创建契约已规定同样精度；输入可接受精度及超出精度时的处理另定。精确规则由[配置契约 §3.4](configuration.md#34-时区选择与确认边界)维护，调度实现仍待实现。

## 9. 文档验收

2026-09-30 的 0.4.0 文档校验已执行：PlantUML 生成、API 技能校验、仓库级 `check-diagrams.py --render` 与 `git diff --check` 通过；36 个专题、131 个块、52 张时序图，0 错误。唯一复杂度提示仍为既有 managed_session_compaction 的三个条件组，职责解释沿用[时序图规范](../../时序图规范.md#3-从总览下钻)。三个 JSON 示例解析通过，Spring 示例与拒绝边界见 §8.1；未运行产品 Maven 测试或集群验收。当前无 OpenAPI/HTML 精确契约，相关校验不适用。

图索引通过 HEAD 加本任务文件的隔离快照生成，未带入无关工作树变更。当前配置保存图为 726×737、全局目标类图为 1302×1205；实际查看原尺寸及 840px 文档宽度，确认角色、分支、文字、箭头与返回路径。图结构延续 Claw 配置边界，图例说明无规则只保存，两个 Session 目标不再预定交付阶段。以下保留 2026-09-29 的历史验收范围，不混用当时的尺寸与本轮结果。

2026-09-29 执行 `plantuml -tsvg diagram.puml`、API 技能的 `validate_api_design.py`、`python3 scripts/check-diagrams.py --render` 与 `git diff --check`。仓库级检查覆盖36个专题、131个块、52张时序图，0错误；包括 Mermaid 禁用、ASCII、SVG XML、图源/SVG同步、SVG路径和 PlantUML 行锚点。唯一复杂度提示来自既有 managed_session_compaction 的三分支，职责说明见[时序图规范 §3](../../时序图规范.md#3-从总览下钻)。配置专题没有新增 OpenAPI/HTML 契约，相关检查为不适用，不能据此声称机器契约已交付。

新增配置保存时序图为938×660，更新的全局类图为1302×1329；均实际查看原尺寸和840px文档宽度，核对职责链、文字、箭头、分支与返回路径。图索引由 `render-diagram-index.py` 在 HEAD 加本任务文件的隔离快照生成，避免带入既有未提交文档删除。三个 JSON 报文示例解析通过，配置文档本地链接存在；两次独立设计校对修正了时间往返、Agent定点回显、状态反馈和刷新恢复边界。

这些检查证明文档与图源交付质量，不替代前端产品、GaussDB、公司认证或调度执行验收；本次没有修改实现代码或运行上述产品测试。

## 10. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
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
