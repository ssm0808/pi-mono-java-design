# 定时任务源码与官方证据

[主设计](README.md) · [Agent 架构对比](../07-Agent架构对比/README.md#a14)

| 属性 | 值 |
|---|---|
| 文档版本 | 0.2.0 |
| 核验日期 | 2026-09-29 |
| 产品范围 | 新建独立会话优先；绑定已有会话为第二阶段，均属于目标范围 |
| 状态边界 | 进程内 Cron 已实现；数据库调度、持久化后台受理与两类目标的调度接线待实现；企业身份系统未核验 |

<a id="java-evidence"></a>

## 1. Java 源码快照与核验范围

实现仓为 `superheromeZzh/pi-mono-java`。当次通过 `git ls-remote --symref origin HEAD` 确认默认分支为 `main`，随后 `git fetch origin main`；远端默认分支与读取工作树均为完整 commit `553dcd5e2ff682f9684810a043b442b37a02e54a`。这表示 2026-09-29 查询时的默认分支源码，不代表稳定发布版本。核验时工作树仅有未跟踪 `.m2/`，未将该目录作为源码证据，也未修改实现仓。

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
| J15 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java#L116)；`acceptUserEventLocked`；[modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml#L63)；`lockSessionForUpdate` | 数据库行锁内重新检查 Session idle、plan 可用性，再追加消息并置 running。本地检查不代替数据库准入；这可复用于第二阶段已有会话竞争，但不证明已有会话调度绑定已实现。 |
| J16 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventOutput.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventOutput.java#L35)；`persistenceOnly`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/PersistenceOnlyRuntimeEventOutput.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/PersistenceOnlyRuntimeEventOutput.java#L20) | 已有无响应流输出策略；Projector 先持久化，该策略丢弃事件工厂，不构造 SSE、不持有连接/缓冲，也不拥有执行取消权。可用于后台执行，当前 Cron runner 尚未使用。 |
| J17 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java#L91)；`start`、`scheduleTimeout`（154）、`commitTerminal`（271）、`retryTerminal`（341） | 订阅投影、安装确认处理器、启动 Agent、处理超时并提交唯一终态；终态写入失败保留执行并重试。可复用生命周期；不等于已有跨进程模型执行接管、启动 CAS 或 Run 对账。 |
| J18 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeContextHistoryService.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeContextHistoryService.java#L34)；`restoreHistory`；[modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/CommittedEventQueryService.java](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/CommittedEventQueryService.java#L40)；`list` | 按权威线性历史恢复模型上下文，按公共事件分页读取。两种调度目标都可沿用消息权威；不需再在 Run 保存一份完整聊天文本。 |
| J19 | [modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql](https://github.com/superheromeZzh/pi-mono-java/blob/553dcd5e2ff682f9684810a043b442b37a02e54a/modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql#L26)；`t_sessions`（26）、`t_session_executions`（81）、活动执行唯一索引（118）、segments（146）、entries（363）、events（426） | 已有 Session、根执行、段、内部历史和公共事件存储；Session 同时只能存在一条非终态根执行。当前 DDL 无 schedule/run/claim 表，Session 状态只有 idle/running；不能用它表示调度领取或未知运行状态。 |

推荐复用既有存储与投影，新增 `ScheduledRunAcceptanceService` 组织同库短事务，并把后台 profile、persistenceOnly 输出和 Run 关联接入公共执行链。该服务、启动权持久 CAS、Run 终态对账均为待实现。不能通过依次调用“创建 Session HTTP + POST 消息 HTTP”宣称获得原子受理，不能在回执丢失时再次创建会话重发 prompt。

NEW_SESSION 第一阶段需把新 Session、首消息、根执行和 Run 绑定一起提交；EXISTING_SESSION 第二阶段需在同一受理事务锁定目标 Session，检查可信绑定、授权、idle 与 build，再追加消息并绑定 Run。已有 Session 的行锁、历史恢复、公共事件查询是基础能力，不等于两种调度目标已经实现。

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

另定位了 `CronEngineTest`、`CronStoreTest`、`CronRunLogTest`、`CronToolTest`、`CronScheduleTest`，其存在仅说明已有测试材料。此次没有运行 Maven 测试、编译、真实 GaussDB、多副本故障注入、DST 边界测试、企业身份联调或压测。主设计新增原子受理、唯一触发、租约代次、启动 CAS、未知执行对账、已有会话调度与无人值守权限均仍需实施与验收，不能因静态证据或旧测试存在而写成已通过。

<a id="claude-evidence"></a>

## 7. Claude Managed Agents 官方契约

2026-09-29 重新读取以下官方页面。Scheduled deployments 属于 Beta，要求 `managed-agents-2026-04-01`；没有可归因的服务端源码 commit。下表只证明公开契约，不能推导内部表、事务顺序、调度器、锁或节点接管算法。

| 来源 | 本次核对的公开行为 |
|---|---|
| [Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments) | Cron 到期创建新 Session；DST 春跳跳过、秋回触发两次。实际启动 jitter 最多为周期的 15%，下限 5 秒、上限 9 分钟。暂停不终止在途，恢复不补暂停期间触发；创建限流不重试，不可恢复错误暂停。主 Agent 归档/删除使 Deployment 归档，此时不产生 Run。指南未定义完整重叠与一般故障补跑策略。 |
| [Create Deployment](https://platform.claude.com/docs/en/api/beta/deployments/create) | Agent 字符串固定创建时最新版本，也可指定版本；initial_events 1～50 条，API 另含受限制的 system.message，不能说只支持 user.message。可不设 schedule，成为仅手动 Deployment；Cron 为五字段 POSIX 与 IANA timezone，不含秒字段。 |
| [Update Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/update) | 再提交 Agent 字符串重新固定最新版本，省略保持；initial_events 整体替换；schedule:null 取消自动计划。更新作用于未来启动，不修改在途 Session。 |
| [List Deployment Runs](https://platform.claude.com/docs/en/api/beta/deployment_runs/list) | Run 是 Session 创建结果，session_id 与 error 二选一；同一 deployment_id/scheduled_at 最多一个 Run，scheduled_at 是 jitter 前 UTC 时间。不表示外部业务恰好执行一次，也不表示任务已完成。 |
| [Run Deployment Now](https://platform.claude.com/docs/en/api/beta/deployments/run) | 手动运行创建 Session，并以 manual 触发记录关联结果；不能以创建成功替代 Session 后续终态。 |
| [Pause](https://platform.claude.com/docs/en/api/http/beta/deployments/pause)、[Unpause](https://platform.claude.com/docs/en/api/http/beta/deployments/unpause)、[Archive](https://platform.claude.com/docs/en/api/http/beta/deployments/archive) | 生命周期各自为管理操作；暂停仍可手动运行，归档不可恢复。指南没有明确说明归档是否终止在途，因此主设计“归档不取消”为 CampusClaw 自己的目标选择。 |
| [Deployment 模型](https://platform.claude.com/docs/en/api/http/beta/deployments) | 状态是 active/paused，归档另由 archived_at 表达；预览最多五项，暂停时可保留假设恢复后的预览。不能把 CampusClaw 的 ARCHIVED 枚举说成照搬原 Schema。 |
| [Authenticate with vaults](https://platform.claude.com/docs/en/managed-agents/vaults) | Vault/凭据以 workspace 为作用域，Deployment 通过引用关联；运行期解析与更新。公开 workspace 访问模型不证明 CampusClaw 的公司租户/用户隔离或委托授权，不能直接存聊天 Token 替代它。 |

相对 A14 的 2026-09-22 证据，本次只更新 Claude 调度范围：将旧“最多 10 秒 jitter”校正为当前比例窗口；明确 Run 的创建结果含义、主 Agent 归档/删除不落 Run 的例外及固定版本语义。未重核的 Claude Session/preview/工具文档仍保留各专题原日期；其他四个开源 Agent 基线保留 A14 原 SHA 与成熟度。

公开 API 的自动生成示例可能同时填入 session_id/error 等占位值，不能用此覆盖字段约束。主设计依据字段文字与指南，并明确区分 CampusClaw 的额外状态与可靠性目标。

<a id="configuration-evidence"></a>

## 8. 配置页面与两跳 API 的源码核验

2026-09-29 再次确认 Claw 上游默认 main 并 fetch，仍为 `553dcd5e2ff682f9684810a043b442b37a02e54a`；本节读取该提交的前端、Cron、目录准备与配置更新模式。另读取本地 `/Users/z/mate-service` 干净工作树 `4b957a3a846659f5b7569c9d6133abc070cd2e3c`，未把它称为当日最新上游或完整生产部署；README 将其定义为待集成的可运行示例。相对历史 Mate `956b547f5ca12ca89e68f73012f92a4406b0c9fa`，只重新确认下列接口及字段，不延伸其他模块结论。

| 编号 | 仓库相对路径与符号 | 已观察实现与配置设计影响 |
|---|---|---|
| C01 | Claw `frontend/README.md`；`frontend/src/App.vue` · configuredAgentId；`frontend/src/components/AppSidebar.vue` | 前端是内部 Runtime 工作台，Agent 从环境变量/开发设置取得；Agent 中心禁用，无定时任务页。新增正式配置客户端不能复用内部直连作为后备路径。 |
| C02 | Claw `frontend/src/composables/useRuntimeApi.ts` · API_PATH/request/createSession/changeSetting | 固定 `/campusclaw-service/v1`；使用 ResultBean 形状、ETag/If-Match 与 no-store。能参考交互模式，不能证明已有 Mate 公共接入。 |
| C03 | Claw `frontend/src/composables/useWorkbenchSessions.ts`；`frontend/package.json` | 会话索引按后端/Agent/caller 本地隔离，草稿留内存；无定时配置列表、请求幂等恢复、vue-router 或表单库。新页面需服务端列表和待确认请求恢复。 |
| C04 | Mate `src/main/java/com/huawei/hicampus/mate/agentdefinition/controller/AgentDefinitionController.java` · listAgents/getAgent/getRuntimeAgent/updateAgent | 已有 `/mate-service/v1/agents` 及详情/runtime/更新；未观察 Schedule 或公共 Chat Controller。只有这些接口存在，不证明完整权限链。 |
| C05 | Mate 同包 `vo/ListAgentRequestVO.java`、`vo/ListAgentResponseVO.java`；`service/impl/AgentDefinitionServiceImpl.java` · listAgents；`src/main/resources/mapper/AgentDefinitionMapper.xml` | 列表 pageIndex 默认1、pageSize默认20上限100；data/total/pageIndex；按 name/displayName/enabled/version 过滤。没有可信操作者/租户范围过滤，不能把 enabled=true 当授权。 |
| C06 | Mate 同包 `vo/AgentInfoResponseVO.java`；`service/impl/AgentDefinitionServiceImpl.java` · buildAgentInfo | 管理聚合含 SYSTEM、permission 和全部绑定。普通候选需授权后安全摘要，不能让浏览器收到管理聚合再隐藏。 |
| C07 | Mate 同包 `vo/ApiSuccessResponseVO.java`、`vo/ApiErrorResponseVO.java`；`controller/ApiExceptionHandler.java` | 示例模拟 ResultBean，更新空 result 被省略；错误是稳定码与文案，无 fieldErrors。Agent 异常未设置 Content-Language。新配置完整资源回显与语言 Header 是新增契约。 |
| C08 | Claw `modules/cron/src/main/java/com/campusclaw/cron/CronService.java` · createJob；`store/CronStore.java` · saveUnsafe/updateJob | create 存储后立即 schedule；文件保存异常仅日志，无配置版本及数据库事务。不能直接包装此方法声称配置 API 已可靠提交。 |
| C09 | Claw `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/AgentRuntimeManager.java` · prepare/rebuild/publish | 完整缓存命中不拉取 Mate，缺失则拉 Agent/Skill、写 staging 并发布目录。配置保存不调用 prepare；元数据校验与目录发布分离。 |
| C10 | Claw 同 codingagent 根 `runtimeapi/agent/AgentDirectorySnapshotDTO.java`、`AgentDirectorySnapshots.java`；`runtime/MateServiceClient.java` | 当前装配快照不含 Agent 版本；Mate 查询按 agentId，未提供 pin 历史版本或 Environment 选择接口。不能伪造这两种前端配置。 |
| C11 | Claw 同根 `runtimeapi/web/RuntimeSessionController.java`；`session/RuntimeSessionUpdateService.java`；`persistence/MyBatisRuntimeSessionRepository.java` · updateSession | 既有 Session 更新使用 ETag/If-Match、428/412 与数据库锁内版本重验。Schedule 借鉴该模式；Mate Agent 更新仍为锁行后最后写入生效，不宣称全系统已经统一。 |
| C12 | Claw `modules/common/src/main/java/com/campusclaw/common/constant/ClawConstants.java` · RuntimeApi.MAX_MESSAGE_CHARACTERS；同 codingagent 根 `runtimeapi/vo/UserMessageContentRequestVO.java` | 普通文本上限262144，严格文本类型与未知字段检查；配置 prompt 复用该边界。配置更新另须保留省略/null差异。 |

在 Mate 示例的 Controller/Service/Mapper、`src/main/java`、resources 与 POM 检索范围，未观察公司认证适配、租户范围、Chat 映射或调度配置服务。这是该源码样例的核验边界，不是对其他 Mate 部署作缺失判断。[配置设计](configuration.md) 将这些能力列为待实现/待公司集成核验。

配置主基线只采用当日重新读取的 Claude [Create Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/create) 与 [Update Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/update)：资源保存 Agent、初始任务、环境和可选时间；更新省略保持，schedule:null清除，嵌套规则整体替换。Claw 选择纯文本任务、六字段现有解析、Mate公开入口和单一配置存储，不复制不存在的环境与历史版本资源；身份和凭据仍按企业边界实现。

本节没有运行前后端产品测试、数据库或身份联调；测试要求见配置文档。现有 Spring/MyBatis/Jackson 可支撑该配置切片，无新增直接依赖；完整传递依赖图未重跑。

## 9. 文档验收

2026-09-29 执行 `plantuml -tsvg diagram.puml`、API 技能的 `validate_api_design.py`、`python3 scripts/check-diagrams.py --render` 与 `git diff --check`。仓库级检查覆盖36个专题、131个块、52张时序图，0错误；包括 Mermaid 禁用、ASCII、SVG XML、图源/SVG同步、SVG路径和 PlantUML 行锚点。唯一复杂度提示来自既有 managed_session_compaction 的三分支，职责说明见[时序图规范 §3](../../时序图规范.md#3-从总览下钻)。配置专题没有新增 OpenAPI/HTML 契约，相关检查为不适用，不能据此声称机器契约已交付。

新增配置保存时序图为938×660，更新的全局类图为1302×1329；均实际查看原尺寸和840px文档宽度，核对职责链、文字、箭头、分支与返回路径。图索引由 `render-diagram-index.py` 在 HEAD 加本任务文件的隔离快照生成，避免带入既有未提交文档删除。三个 JSON 报文示例解析通过，配置文档本地链接存在；两次独立设计校对修正了时间往返、Agent定点回显、状态反馈和刷新恢复边界。

这些检查证明文档与图源交付质量，不替代前端产品、GaussDB、公司认证或调度执行验收；本次没有修改实现代码或运行上述产品测试。

## 10. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.2.0 | 2026-09-29 | 核对前端调试边界、Mate Agent 配置样例和 Claw 保存行为，补充独立配置 API 的证据与差距。 |
| 0.1.0 | 2026-09-29 | 核对 Claude 调度公开契约、当前 Cron 与持久化 Runtime 基础，明确两类执行目标及实现差距。 |
