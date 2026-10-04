# CampusClaw 定时任务设计

[模块索引](../../README.md#module-index) · [架构对比 A14](../07-Agent架构对比/README.md#a14) · [源码与官方证据](source-evidence.md)

| 属性 | 值 |
|---|---|
| 文档版本 | 0.15.0 |
| 更新日期 | 2026-10-04 |
| 模块 | M10 · 调度与并发治理 |
| 产品范围 | 每次自动或手动触发均创建新的独立 Session，复用配置绑定的 Agent 定义；不选择或追加已有 Session |
| 设计状态 | 五个 Claw 配置接口形成推荐目标，待实现；不定义 Mate 接口或页面；到期执行、重叠、补跑和故障恢复部分为待细化候选，不作为已冻结实施规则；无人值守身份待确定 |
| 已观察实现 | Java main `553dcd5e2ff682f9684810a043b442b37a02e54a` 已有进程内 Cron、JSON Job/JSONL Run 和公共 Session 工厂；不等于已具备企业调度能力 |
| 主基线 | Claude Managed Agents Scheduled deployments，2026-10-04 重核名称、Cron 与执行目标，Beta；仅引用公开契约，无服务端源码 commit |

## 1. 要解决什么问题

优先定义[Claw 配置接口](configuration.md)：创建、列表、详情、部分更新和时间预览，明确请求、持久化成功、版本冲突和同键重试；该专题是新增 Claw 配置接口的唯一规则源，不定义 Mate 路由或页面实现。[与 Claude 的取舍](configuration.md#claude-tradeoffs)区分能力缺口、产品扩展和实现成本。本文 §5～§7、§9～§12 的到期运行结构和恢复策略需在执行专题继续论证；配置交付不据此冻结忙时跳过、同库受理或失联不接管策略。

园区运营人员配置“每天 08:00 汇总设备告警、检查未关闭工单”，保存后由服务端按时发起 Agent 工作，无需浏览器保持打开。用户能看见下一次计划时间、每次是否成功启动、执行结果和失败原因，并能暂停后续运行。

正常情况下，调度器发现到期任务，持久化一条触发记录，核对 Agent 与执行资格，再把该记录与一次新 Session 的首条消息原子关联。事务提交后才运行模型与工具；运行内容进入既有 Session 历史，任务页链接到本次结果。

失败时先区分发生在哪一层：规则无效则不保存；未受理则记录原因；受理后执行失败则保留原 Session 和根执行；结果未知则对账，不重新发起业务写入。暂停只阻止未来受理，停止已运行任务使用既有定向取消机制。

每次运行使用同一任务绑定的 Agent 定义，新建的是承载这次执行的 Session 和运行实例，不创建新的 Agent 定义资源。不同运行不自动继承聊天历史；需要昨日告警结论时，任务应明确查询业务记录。该范围对齐 Claude Deployment，代价是不能把定时消息追加到已有会话中。

## 2. 职责、边界与基线取舍

M10 拥有时间规则、任务生命周期、触发身份、到期领取、受理关联和运行摘要。M01/M04/M06 继续拥有 Session、消息历史、根执行、准入、工具结果和停止；M03 继续拥有工具可信解析、校验、权限及公共工厂；Mate 继续拥有公司认证、租户与 Chat 授权和公共安全投影。

定时任务管理页面与现有 `Cron` 模型工具是不同入口，最终应委托同一应用服务。调度器不嵌入 AgentLoop，也不通过模型反复检查现在几点。M10 不新增一套对话历史、通用工作流 DAG、Agent 历史版本仓库或消息通知渠道。

| 决策 | CampusClaw 目标与理由 | 与 Claude 的关系 |
|---|---|---|
| 定义、触发、执行分离 | Schedule 保存长期规则，Run 保存一次触发/受理，Session 保存内容与根执行；避免“启动成功”被当成业务完成 | 采用 Deployment / DeploymentRun / Session 的职责分离；公开 Run 本身只表示 Session 创建结果 |
| 执行会话 | 每次新建独立 Session；配置不提供 target 或 sessionId | 采用 Scheduled deployments 的固定新会话语义；减少已有会话绑定、忙闲和上下文竞争规则 |
| Agent 选择 | 新会话每次 `prepare(agentId)`，固定这次实际取得的已发布目录快照；不会自动刷新 Mate 最新定义 | 保留现有产品约束；Claude 在创建/显式更新 Deployment 时固定 Agent 版本 |
| 时间表达 | 仅支持 cron，沿用 Spring 六字段；timezone 可省略，默认保存并回显 Asia/Shanghai；不提供绝对单次或任意起点间隔 | 采用 Claude 的仅 Cron 范围取舍；方言与时区默认值为 CampusClaw 产品约束 |
| 重叠与恢复 | 同一任务仅一条未完成受理链；过期窗口跳过，结果未知保持占用；不自动重放已接受输入 | 产品约束和安全加固；Claude 公开资料未给出完整重叠/故障接管策略 |
| 部署与存储 | GaussDB 是调度权威，定时器只唤醒扫描；与 Runtime 受理使用同库事务 | CampusClaw 架构变更；不推断 Claude 的表、锁、队列或部署拓扑 |

Claude 公开契约、最新变化与未说明项见[证据](source-evidence.md#claude-evidence)。[官方创建接口](https://platform.claude.com/docs/en/api/beta/deployments/create)固定 Agent 版本；[Run 查询](https://platform.claude.com/docs/en/api/beta/deployment_runs/list)把触发记录与 Session 后续执行分开。其他 Agent 基线保留 A14 的历史核验范围，本设计不据此升级它们的实现结论。

## 3. 使用与管理

配置动作的当前推荐设计、字段与接口以[配置专题](configuration.md)为准。已确认 schedule 可省略，省略时只保存、不立即执行；填写有效规则后保存即参与自动调度，无需显式启用；试运行是独立的显式操作。输入为一条 `user.message`，内容复用现有文本和文件引用格式；附件长期保留与执行时访问规则待确定。已确认响应 status 小写、新建 active、非空 schedule 内返回 lastRunAt/upcomingRunsAt、移除公开 revision，并加入 metadata；完整生命周期、其余字段和整项操作仍为 proposed。创建处理器不调用模型、prepare 或旧 Cron create。Claw 校验可信范围与绑定，原子保存配置和幂等结果。运行未接线不能对外发布可自动运行的成功承诺；旧 Cron 已有能力不能被直接标为新配置管理已实现。

任务列表展示名称、Agent、状态、规则与时区、下一计划时间、最近一次触发和执行摘要。任务详情提供运行列表；每条记录明确区分“未启动、已受理、执行中、执行结束、需要处理”。模型自然结束不等于设施巡检或工单操作业务成功，业务结论来自对应 Session 的输出与工具证据。

| 管理动作 | 有效行为 |
|---|---|
| 创建、修改 | 校验可信 Agent 绑定、时间规则和提示内容，展示规范化规则及未来时间预览；保存内部配置代次（不进入公共 JSON）；不在保存时执行模型 |
| 暂停 | 阻止尚未完成受理的自动触发；已受理 Run 继续；允许有权限的显式手动运行 |
| 恢复 | 重新检查资格并计算严格晚于恢复时刻的下一次运行；不补暂停期间任务 |
| 手动运行 | 产生新的 manual Run，使用相同授权、互斥、受理和审计；不移动正常计划游标 |
| 归档 | 终止未来计划，不再允许修改、恢复或手动运行；保留 Run 与历史引用；不隐含停止已受理执行 |
| 停止一次执行 | 固定 Run 绑定的 Session 和根 execution，提交取消请求；收到真实终态前保持“停止中” |

配置候选状态为 `active / paused / archived`；没有自动计划或没有未来匹配时 `nextFireAt` 为空，不假装仍有下次运行。归档终态枚举尚待生命周期审阅；Claude 的 `archived_at` 与 active/paused 表达方式不同。

创建 active 资源不要求额外启用动作；后续暂停/恢复是独立生命周期操作。现有 Cron 工具契约保持原参数面；其适配、delete 到归档的映射和 trigger 回执须在迁移切片中一并对齐，未接线前不宣称新 API 与旧工具已共用存储。每个写入动作使用带配置 revision 的可信快照，在事务中重新检查可变状态；修改冲突不覆盖另一人的更新。

配置的 proposed HTTP 路由、VO、错误码和幂等规则由[Claw 配置专题](configuration.md#2-claw-接口清单)维护，不是已发布 API。显式试运行能力已确定，其路径与回执、启停、Run 和执行结果契约另行设计。响应继续遵守公司 `ResultBean`，服务边界须验证可信调用范围；不在此扩写 Mate 公共契约。

## 4. 时间规则

配置的输入、空值、预览与回显以[配置专题 §3](configuration.md#3-配置字段与时间规则)为准。非空 schedule 仅支持 cron，采用 Spring 六字段；timezone 可省略，默认保存并回显 Asia/Shanghai。省略 schedule 只保存配置，显式手动运行仍独立提供；新 HTTP 不接收 at/every/intervalSeconds/startAt。仅 Cron 的能力代价与旧工具边界见[配置专题 §3.2](configuration.md#32-仅-cron-的范围与代价)。

时间响应统一 UTC 且不含小数秒；本节涉及的 maxLateness、补跑窗口、gap 与到期游标属于运行候选，不作为创建配置的必填字段或已确定策略。

### 4.1. 六字段表达什么

CampusClaw 沿用 Spring 六字段 Cron，顺序为“秒、分、时、日、月、星期”。例如 `0 0 8 * * MON-FRI` 配合 `Asia/Shanghai`，表示周一至周五 08:00:00；它不自动识别法定节假日。完整字段范围、秒位示例和匹配规则由[配置契约](configuration.md#spring-cron-contract)唯一维护。

“支持秒字段”表示能配置计划时间的秒位，不表示普通 Java 应用保证在该秒准时开始，更不表示 Agent 必须在一秒内完成。线程排队、系统负载和 JVM 暂停都可能带来延迟；JDK 调度器明确不提供硬实时启动保证。表达式能力与产品允许的最小执行频率分别确定。[JDK 调度说明](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ScheduledThreadPoolExecutor.html)

界面可在后续设计中提供日/周时间选择与自然语言预览，高级表达式应明确标识 Spring 六字段。现有 Cron 工具的可选 timezone 在迁移时必须归一化成明确存储值，具体默认来源随工具契约切片确定，不静默采用运行节点时区。

<a id="spring-scheduling"></a>

### 4.2. 固定任务与用户动态任务如何使用 Spring

园区告警汇总可以有两种配置来源：开发人员预先为系统定义统一任务，或运营人员通过页面持续新增、修改、暂停自己的任务。两者都可以使用 Spring 六字段，区别在于任务如何注册和管理；Spring 的 Cron 解析器、触发器及调度注解均由已有 `spring-context` 提供，无需为六字段另加 Maven 依赖。

| 场景 | 常用方式 | 适用边界 |
|---|---|---|
| 应用预先定义的固定任务 | `@EnableScheduling` + Spring Bean 上的 `@Scheduled` | 适合固定的统计、清理或轮询方法；Cron 可来自配置属性，但普通注解绑定不等于提供用户任务的运行期增删改 |
| 用户运行期创建、修改、取消任务 | 编程式 `TaskScheduler` + `CronTrigger` | 服务读取已保存配置，动态注册任务，保存本地句柄用于取消或重建；`ThreadPoolTaskScheduler` 底层使用 JDK 调度线程池 |
| 不依赖 Spring 的延迟或周期任务 | JDK `ScheduledExecutorService` | 支持延迟一次、固定频率和固定延迟，不直接解析 Cron；日历表达式需由其他组件计算 |
| 只校验规则或预览未来时刻 | Spring `CronExpression.parse(...).next(...)` | 只负责计算，不注册线程、不持久化配置，也不调用业务方法 |

固定任务示例：配置类开启 `@EnableScheduling`，在 Spring 管理的 Bean 中定义以下方法。这里的 `alarmService` 是业务服务示意，不是 CampusClaw 新增接口。

```java
@Scheduled(cron = "0 0 8 * * MON-FRI", zone = "Asia/Shanghai")
public void summarizeAlarms() {
    alarmService.summarizeLast24Hours();
}
```

固定间隔也可通过注解表达：`fixedRate = 10000` 以每 10 秒一次为目标频率；`fixedDelay = 10000` 则在上一次方法完成后再等 10 秒。若方法耗时 3 秒，后者两次开始约隔 13 秒。固定频率不保证任务在过载时仍能准点执行，也不能由此推断同一任务会自动并发。[Spring 调度文档](https://docs.spring.io/spring-framework/reference/integration/scheduling.html)

动态任务的正常流程是“保存并校验配置 → 调度服务读取规则 → 注册或重新计算下一次时间 → 到期执行业务入口”；修改或暂停时调整对应注册或调度游标。规则不合法应在保存时返回字段错误；服务重启后需要从持久化配置恢复，取消本地定时句柄不能代替任务状态、运行记录或停止在途执行。

### 4.3. CampusClaw 当前实现与目标边界

已观察的 `CronEngine` 采用 **Spring 算时间、JDK 安排执行**：`computeNextDelay` 使用 `CronExpression`，`scheduleJob` 使用 `ScheduledExecutorService.schedule`，`executeAndReschedule` 执行后重新安装计划。它没有使用 `TaskScheduler + CronTrigger`；上节展示的是可用的 Spring 编程方式，不是已经完成的项目重构。[源码与框架证据](source-evidence.md#spring-scheduling-evidence)

用户配置通过统一应用服务和持久化规则管理，不为每条任务新增一个带 `@Scheduled` 的方法。固定注解可以用于应用自己的周期扫描，但不会自动解决多实例重复触发、持久化、漏跑、权限或执行结果对账。本节确定六字段及动态管理边界；是否复用当前逐任务定时器、改为扫描唤醒、如何领取和恢复，继续在执行专题确定。

### 4.4. 到期与恢复候选

计算与预览共用 `ScheduleTimePolicy` 和同一规则快照、时区、时区库版本；实际准入仍需事务检查。候选方案使用数据库时间决定到期和租约，存储 `scheduledAt`、`acceptedAt`、`startedAt`，不把预览时间当实际启动保证。`maxLateness` 的来源、上限及是否进入管理配置待确定；候选规则为超过窗口记 `SKIPPED_MISFIRE`。运行时间长不会改变后续 occurrence。

夏令时目标按钟面匹配：不存在的本地时刻跳过，重复时刻对应两个不同 UTC occurrence。该目标须通过当前 JDK/Spring 版本的边界测试后验收；并非已验证结论。时间库升级需比较下一次预览，保留已分配 occurrence 的 UTC 身份，不重算历史。

停机恢复从数据库游标检查：窗口内最新到期 occurrence 可受理一次，更早的过期 occurrence 以 MISFIRE、窗口内被合并的 occurrence 以 COALESCED 分别压缩记录到 `t_schedule_gap`，不逐条补跑。gap 保存首末计划时刻、原 revision、原因和可计算的数量；无法精确计算时不伪造计数。历史查询把 gap 与具体 Run 区分。首次无未来匹配的表达式拒绝创建；既有规则耗尽则清空游标并显示原因。

本模块不引入 Claude 的 jitter 或部署数量上限。扫描批量、每租户任务数、全局/租户执行并发、最小频率、maxLateness 上限和运行期限是待压测的部署策略，上线前必须配置并验证，不能把默认值写成容量结论。

## 5. 正常触发与受理事务

场景是“每天 08:00 创建新的设备告警汇总会话”。从一次到期扫描开始，到新 Session 的根执行终态入库结束；前提是任务已启用且身份策略可用。以下为推荐目标，新增后台受理链待实现。图中 Store 表示同一 GaussDB 事务边界，Host 表示可信执行准备与授权；Scheduler 映射到 ScheduleDispatcher，Runtime 映射到受理服务及执行协调器，AgentLoop 由公共 Session 推进。它们是职责映射，不暗示独立进程或远程调用。

![独立会话定时运行](scheduled_run_sequence.svg)

[原尺寸 SVG](scheduled_run_sequence.svg) · [PlantUML 源码](diagram.puml#L1)

1. **分配 occurrence。** 扫描器按租户有界轮转批次，任务按 nextFireAt/id 稳定扫描，使用短事务，锁定 Schedule，复核 active、revision、到期时间和 activeRunId；插入唯一 Run，推进下一次游标，同时占用本任务。重叠触发记录为 `SKIPPED_OVERLAP`，不排无限队列。暂停/归档操作与领取竞争同一行锁。
2. **可信准备。** 事务外解析 Agent 已发布目录、模型、CRON profile、工作区及执行资格，固定一次 `PreparedScheduleRunDTO`。准备可以失败，但不调用模型或执行业务工具。远端授权检查不能持有数据库行锁。
3. **原子受理。** 新增 `ScheduledRunAcceptanceService` 在同一事务复核 Schedule 状态/revision、Run 领取 owner/代次及 lease_until、授权断言有效期与容量；自动触发还用数据库当前时间复核 maxLateness；创建新 Session、首条 user.message、根 execution/segment，并写回 Run 的唯一关联。任一步失败整体回滚。已有配置更新或暂停先提交时，旧自动 Run 结束为跳过；受理先提交时，在途沿用原快照。
4. **事务后启动。** 受理不等待 Agent 完成。持有本次完整准备快照的原 Runtime 实例，以持久化的单次启动 CAS 标记由 READY 转为 STARTING 后启动公共执行链，使用 `RuntimeEventOutput.persistenceOnly()` 保存完整事件。后台执行不需要伪造浏览器 SSE 连接。
5. **结果对账。** 按 Run 固定的根 execution 读取权威终态，幂等更新摘要和释放 activeRunId；既有根执行是终态权威，任务页读取到更晚终态时可立即展示；根终态与任务摘要不在同事务时，通过重读根 execution 修复。后续人在同一 Session 继续聊天不会改写该 Run 的结论。

第一阶段限定 Schedule、Run 与 Runtime 受理记录位于同一事务资源。现有 HTTP 创建 Session 和提交消息不提供此受理原子性，不能串联它们并在断连后重复 POST。跨数据库或独立外部调度服务的受理协议不在此实现切片内，需另行设计受理键和只读对账能力。

自动受理要求 active；手动受理允许 active/paused，拒绝 archived，不移动计划游标、不应用自动 occurrence 的迟到窗口。未受理 Run 的失败/跳过必须在收尾事务中按 scheduleId、runId、claimEpoch 条件释放自己的 activeRunId；重叠跳过不得覆盖或释放另一条活动 Run。

同一任务 activeRunId 的检查、占用和释放都受行锁保护；唯一 Run 键防重复分配，启动 CAS 防重复调用入口。租约仅允许接替“尚未受理”的领取者；旧领取者提交时必须匹配 owner 与递增 claimEpoch。不能把这些边界宣传为外部业务 exactly-once：工具副作用仍受下游业务幂等和已执行结果对账约束。

## 6. 失败、交互与恢复

Run 分开保存 `dispatchState`（PENDING、PREPARING、ACCEPTED、FAILED、SKIPPED）与 `executionState`（未启动、运行、等待处理、完成、失败、取消、未知）；精确枚举由契约切片固定。只有 ACCEPTED 才绑定根执行，触发层终态不冒充执行终态。

| 条件 | 本次处理 | 后续处理 |
|---|---|---|
| 表达式、提示或 Agent 绑定不合法 | 保存前拒绝，返回具体字段错误 | 由用户修改，不猜参 |
| Agent 不可用、配置或长期执行资格失效 | 未受理 Run 失败，任务自动暂停并记录原因 | 修复后显式恢复 |
| 准入限流或当前容量不足 | Run 失败，记录 `ADMISSION_REJECTED` | 等下一 occurrence；不自动重试本次写入 |
| 已有活动 Run | 跳过并记录 overlap，不排无限队列 | 等下一 occurrence；手动运行返回明确冲突 |
| 数据库领取失败 | 未提交则无成功回执；下次扫描同一游标 | 数据库唯一键和事务决定是否存在 Run |
| 尚未受理时节点失联 | 租约到期后可重新准备同一 Run，增加 claimEpoch | 不另建 Run；受理前再次复核 |
| 受理或启动回执丢失 | 按 runId 只读查询；不得新建 Session 重发 prompt | 已受理永远复用关联；无权威结果显示未知 |
| STARTING/运行中节点失联 | 不因租约过期再次调用模型/工具；保留 activeRunId | 权威对账或人工处理；不能只清标记继续 |
| 模型或工具执行失败 | 原根执行记录错误，Run 摘要引用该结果 | 不自动重放本轮；业务补偿独立授权 |
| 取消超时 | 保持停止中或未知 | 实际终止后才能释放任务占用 |

READY 仅表示尚无人取得启动权，首版只允许持有原准备快照的活实例经 CAS 启动；该实例丢失时，即使尚未启动，也不能靠 Run 中的版本摘要恢复同一配置与凭据，转未知等待处置。取得 STARTING 后，同样不依赖猜测重启。跨进程恢复启动需要另行设计可恢复的不可变快照与重新授权协议，不能用重新 prepare 偷换已接受输入。此选择以可能漏执行换取避免重复副作用，必须把“执行状态未知”暴露给运营人员。人工解除未知占用需要明确证据或接受重复风险的显式决策，并记录操作者和原因；不能伪装成自动恢复。

无人值守仍执行“可信目标解析 → 参数校验 → 权限/必要确认 → 业务执行 → 结果回传”。参数错误保持 `isError=true`，返回同次可信定义给模型且不触发业务请求，公共投影隐藏定义与敏感字段，引用 [M03 规则](../02-CampusClaw工具系统/README.md#tool-argument-recovery)。本设计不复制或改写其 Schema。

首版不建立无人审批队列：任务启用不是对所有业务操作的永久 ALLOW。Host 遇到需要交互的 ASK、提问或计划审核时停止本根执行，标记需要人工处理的失败原因，不自动批准、不静默换工具绕过权限。CRON profile 继续不默认提供交互工具；即使误配可见，运行期门禁仍要拒绝。需要审批的业务改由有明确授权的人工执行，或后续独立设计持久等待与通知。

## 7. 每次运行新建 Session

| 边界 | 当前目标 |
|---|---|
| 配置绑定 | Agent 身份、单条 user.message、可选 Cron 规则；不接收 target、sessionId 或 chatId |
| Agent 与 Session | 复用已绑定的 Agent 定义，每次自动或手动运行新建独立 Session 与运行实例；不新建 Agent 定义资源 |
| 消息上下文 | 新建空历史，再接受首条 user.message；不自动复制其他 Run 的聊天历史，共享受管资源和业务状态仍遵守各自边界 |
| 模型与模式 | 当前已发布 Agent default，thinking=OFF，CRON profile，build 入口；精确后台准入继续由运行专题定义 |
| 受理事务 | 新建 Session、首消息、根 execution 和 Run 关联；ScheduledRunAcceptanceService 直接协调既有 Runtime 持久化边界 |
| 配置刷新 | 使用本次 prepare 的不可变快照，不以新建 Session 承诺 Agent 版本固定或每次远端最新 |
| 准备失败 | 记录 Agent 或授权等准备错误；自动暂停等生命周期策略继续按运行候选细化 |
| 对其他聊天的影响 | 不向已有 Session 追加定时输入；新 Session 完成后可供有权限的用户继续聊天，但不成为后续定时触发目标 |

Cron 的 build 表示非计划执行模式；首版继续使用该入口的 basePrompt，不因后台持久化而自动追加交互 BUILD 提示词，当前实现依据见[证据 J10](source-evidence.md#java-evidence)。不能直接复用现有 HTTP 创建默认 thinking=true 的入口覆盖上述策略。

固定新会话使受理路径无需目标策略分支；应用受理服务仍与 Runtime 持久化和执行协调器分层。每个 Run 固定本次首消息与根执行的关联，后续人工聊天不改写该次运行的结果。创建配置只保存任务；创建响应不返回尚未产生的 Session 或 Run，字段对齐见[创建响应审阅](configuration.md#creation-response-review)。

## 8. 身份、授权与公共投影

公司身份和租户授权由 Mate 权威确认，任务管理权限与业务执行权限分别判断。Schedule 保存可信租户/管理作用域、Agent 绑定和授权引用；这些值不能从模型 prompt 或任意客户端字段推导。已有源码只做 Agent 范围过滤，不证明已实现租户隔离。

`ScheduleAuthorizationPort` 是待实现的宿主能力：创建/修改时校验管理资格，启用和每次受理前校验执行资格、撤销状态及范围。授权断言绑定 tenant、schedule、revision、Agent 与有效期，通过受信内部通道传递。新建 Session 的归属由本次可信任务范围确定；数据库记录 scope 不是认证凭据。授权服务不可用时不受理。

[Claude 凭据参考与方案边界](configuration.md#credential-reference-proposal)采用“独立保管、任务只存授权引用、运行时由可信 Adapter 使用”的候选方向；凭据引用字段及其权威服务尚待确定。公开 metadata 只是标签，不是凭据存储或授权来源；任务配置不保存原始 secret。已有普通消息捕获当前执行 Header、Cron 使用空凭据、内部模型 Provider 无模型 API Key 的核验见[本次证据](source-evidence.md#creation-metadata-credentials-evidence)。

**无人值守业务身份待确定。** 可选专门服务身份或创建人长期委托、执行前换取短期凭据；推荐服务身份并限制租户、Agent、业务工具范围。该推荐尚不构成已确认的凭据来源，更不是当前实现。公司身份系统的签发、刷新、撤销与审计契约需要在启用依赖凭据的园区任务前明确。

在身份方案确定前，继续遵守 [HTTP 凭据规则](../01-CampusClaw多Agent运行时/chat-http-v1-design.md#credential-forwarding)：Cron 不从创建会话保存、恢复或借用 Header；无 Host 凭据时使用空快照，业务权限由 Mate 判断，不宣称可完成需要登录身份的工具调用。新增凭据来源必须同步 M03/M06 权威规则；本版不存 Token、JWT、APPKEY 原文，不把凭据写入提示词、Run、历史或日志。

公共任务详情使用公共任务/Run 标识与 Chat 链接，Mate 异步幂等建立新 Session 的私有 Chat 映射；映射未完成显示“结果入口准备中”，不能重复触发任务。映射失败不更改已接受执行。Run 可记录内部 sessionId、executionId 供后台对账，公共安全投影不暴露它们。独立任务结果归属和可见人群跟随已确定的任务授权范围；跨租户访问拒绝。

## 9. 持久化与生命周期

以下是逻辑模型，具体 DDL、Mapper DTO 和索引 SQL 待实施切片冻结，不伪称已安装。使用 `t_` 表名、UTC 时间和中文 SQL COMMENT；精确类型沿用所属 GaussDB/运行时规范。

| 权威对象 | 关键数据及约束 |
|---|---|
| `t_schedule` | id、可信 scope、agent_id、单条 user.message 配置、cron_expression/timezone、status、内部 revision、metadata、last_run_at、next_fire_at、候选 max_lateness、active_run_id、授权引用、创建/修改审计；消息存储形状及文件引用生命周期待定，修改/受理在行锁内复核 |
| `t_schedule_run` | id、schedule_id、配置 revision 与安全配置快照、trigger_type、scheduled_at/manual_request_key、dispatch/execution 摘要、claim_owner/claim_epoch/lease_until、session_id/root_execution_id、实际 Agent 发布版本/摘要、关键时间和安全错误；不存完整消息与凭据 |
| `t_schedule_gap` | schedule_id、revision、from/to、reason、可选准确数量及记录时间；只说明未创建执行的跳过范围，不合并已接受 Run |
| 既有 Session/执行表 | 消息、工具结果、根执行/segment、等待和终态的权威；复用 M04/M06，不重建相同数据 |

自动触发唯一约束为 `(schedule_id, scheduled_at)`，UTC instant 区分夏令时重复钟面；配置修改不能让同一 occurrence 再次自动执行。manual 采用 `(schedule_id, manual_request_key)` 唯一约束，相同键仅返回原 Run，内容不一致报冲突。管理创建/更新以调用方请求键去重；内部配置代次服务于调度竞态，完整表示 ETag 服务于条件更新，精确规则由配置契约维护；不把现有 HTTP 描述成已有幂等能力。

定时器、执行线程、扫描缓存和本地租约计时都可丢弃；数据库游标、Run 关联与根执行不可被它们覆盖。Spring 单例服务只保存线程安全基础设施，不保存可变租户上下文；准备快照、凭据和执行对象按每次 Run 隔离。

归档任务不级联删除 Run 或 Session。Session 依既有删除流程 tombstone 后，Run 保留脱敏审计与“结果已删除”的链接状态；定时任务不能借旧引用重新读取已删除内容。保留周期、个人数据删除和大 prompt 快照清理由公司策略配置，清理条件不得删除进行中/未知 Run 的去重证据；归档后的审计清理仍须防止 ID/请求键被复用。

定时任务时间列目标为 `TIMESTAMPTZ(0)`，应用先规范化再写入；具体列尚待 DDL 实施。与 Session、完整事件共用[秒级时间一致性](../01-CampusClaw多Agent运行时/time-contract.md)，不自动改变内部租约与计时精度。

## 10. 全局目标类图与依赖

本图是 M10 的 Claw 完整目标骨架：从 Claw HTTP/模型工具入口到应用服务、时间与授权策略、数据库、新建 Session 的受理服务，再到既有 Runtime 和 Session 工厂。所有新增节点和连线均为待实现；标识为既有的 Runtime 类仍需后台入口扩展。上游页面与 Mate 内部设计不在图中定义。

![定时任务全局目标类图](scheduled_task_architecture.svg)

[原尺寸 SVG](scheduled_task_architecture.svg) · [PlantUML 源码](diagram.puml#L53)

| 层次 | 责任与生命周期 |
|---|---|
| Claw 边界与入口 Adapter | `ScheduleController` 接受可信上下文和 RequestVO、返回 ResponseVO；`CronToolAdapter` 传入 Host 已绑定作用域，不能绕过授权；不规定上游页面和 Mate 路由 |
| 绑定解析 | `ScheduleBindingResolver` 只读检查 Agent 绑定，管理调用不发布运行目录；端口及公司身份适配待实现 |
| 应用编排 | `ScheduleApplicationService` 负责管理规则与 VO/DTO 转换；`ScheduleDispatcher` 负责到期领取与准备，均为 Spring 单例 |
| 策略与准备 | `ScheduleTimePolicy` 统一预览/计算；`ScheduleAuthorizationPort` 对接 Mate；`PreparedScheduleRunDTO` 每次准备创建不可变快照，不代替事务内可变状态检查 |
| 持久化 | `ScheduleRepository` 实现委托 `ScheduleMapper`，Mapper 只收发 DTO；Schedule/Run/gap 是持久化权威，不引入 PO/DO/Entity 类型 |
| Runtime 适配 | `ScheduledRunAcceptanceService` 直接协调既有 Session/执行存储，在同库短事务中新建 Session 并关联首消息和 Run；`RuntimeExecutionCoordinator` 事务后启动、投影与关闭；每次独立 `ManagedAgentSession` 由公共工厂创建 |

优先定义五个 Claw 配置接口与唯一持久化边界，再独立设计生命周期、到期触发和执行恢复。配置服务不调用 Session 工厂或执行协调器；全局图中的后续运行关系为待细化的结构方向。Controller 不直接调用 Mapper 或模型，模型与外部 I/O 不进入配置数据库事务。

## 11. 实施切片与验收

当前实施入口为[配置专题 §8](configuration.md#8-实施与验收)。下表是后续完整运行能力的候选拆分，不能将其受理原子性、跳过和接管策略当作本次配置设计已确认的前提。

| 切片 | 交付与通过条件 |
|---|---|
| S1：独立任务管理 | 固定 M06 管理/Run 契约、DTO/VO、DDL和授权范围；规则预览、完整表示条件冲突、暂停/恢复/归档及审计可验证；用户能确认时区与每次新建会话的行为 |
| S2：后台原子受理 | 新 Session/首消息/根执行/Run 同事务；故障注入覆盖提交前、提交后和回执丢失；重复 Run 键只返回原关联；明确 build/CRON、工具权限与 persistenceOnly 接线 |
| S3：持久调度与恢复 | 两副本竞争仅一条受理；暂停/修改竞态可线性判定；崩溃恢复不重放 STARTING；时钟、DST、Cron 未来匹配、漏跑 gap、重叠及限流有确定性验证 |
| S4：结果与运营 | 后台完整 Session 历史可读、公共 Chat 映射可重试对账、取消指向原根、未知不显示成功；控制台能定位授权和执行失败 |
| S5：旧 Cron 入口迁移 | 按可信 scope 迁移 Job，缺租户、时区或授权信息的记录保持禁用等待补全；切换时确保旧扫描器停用且旧在途任务已核对，不能双写双执行；Run 历史保留来源 |

S1～S4 是每次新建会话能力的候选拆分；S5 的时机取决于是否需要保留既有模型管理入口。已有进程内 Cron 能力不能等价为上述切片已完成。没有业务执行身份、可靠受理或结果对账时，不验收需要凭据的园区无人值守任务。

验收还须覆盖不同 Run 关联不同 Session、固定 Agent 身份而非新建定义、五阶段工具顺序、无效参数不确认/不执行业务、ASK 不被自动放行、租户篡改、旧 claimEpoch 拒绝、手动触发与自动互斥、单次根执行摘要不受后续聊天覆盖、运行取消与真实结束区别、日志/历史中无凭据。单元测试存在、确定性测试通过、真实 GaussDB/多副本/企业身份联调分别记录，本文未运行实现测试或压测。

## 12. 依赖与待定事项

本方案不因 Cron 方言新增外部 Maven 依赖：复用 JDK 时间 API、项目已有 `spring-context` 中的 `CronExpression`；固定与动态使用场景见[§4.2](#spring-scheduling)，六字段契约见[配置规则](configuration.md#spring-cron-contract)。其他基础能力复用 Jackson、MyBatis/GaussDB 和 Runtime 事件持久化。`modules/cron` 目前没有 MyBatis 依赖，数据库 Adapter 放在已有持久化宿主层，通过端口接入；若实施时迁移制品边界，先列出新增直接依赖及其传递图。

当前不引入 Quartz、XXL-JOB、Redis 分布式锁或新的 Cron 解析库。已有依赖足以表达推荐的扫描与同库事务方案，代价是本项目必须实现并验证领取、去重和状态对账；未来需要统一外部调度平台或跨库部署时重新评估。未重跑完整 Maven dependency tree，不声称已完成传递依赖审计。

仍需在实施前确定：无人值守采用服务身份还是创建人委托；企业身份接口与公共任务可见范围；配额/运行期限/保留配置；M06 精确契约与旧工具迁移默认值。这些未决项不改变“每次新建独立 Session、复用 Agent 定义”的产品范围，但决定上线验收边界。

## 13. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.15.0 | 2026-10-04 | 配置响应采用小写状态、时间摘要和 metadata，内部版本不外露，并明确凭据引用的待定边界。 |
| 0.14.0 | 2026-10-04 | 每次运行固定新建独立 Session，移除已有会话目标和策略分支，并补充创建响应审阅入口。 |
| 0.13.0 | 2026-10-04 | 配置仅支持 Cron，名称上限对齐 256，并澄清附件和会话目标的能力边界。 |
| 0.12.0 | 2026-10-02 | 定时任务时间统一秒级，并引用 Session 与完整事件共用的时间一致性规则。 |
| 0.11.0 | 2026-09-30 | 绝对时刻响应统一 UTC 并固定三位毫秒，输入精度继续由配置契约细化。 |
| 0.10.0 | 2026-09-30 | 明确 Cron 默认上海时区及 at/startAt 的输入偏移量，区分已定字段与待定输出规范。 |
| 0.9.0 | 2026-09-30 | 明确整数秒及固定起点的保存、更新与校验，时区默认值保持候选并补充基线入口。 |
| 0.8.0 | 2026-09-30 | 创建 every 时省略 startAt 默认先等待一个完整间隔，精确取时与更新规则继续细化。 |
| 0.7.0 | 2026-09-30 | every.startAt 可选，默认首次时间与更新规则由配置契约继续细化。 |
| 0.6.0 | 2026-09-30 | every 采用不随任务耗时漂移的固定时间表，首次触发与运行恢复细节继续独立定义。 |
| 0.5.0 | 2026-09-30 | 明确三种时间类型均在支持范围，区分间隔重复能力与尚待确定的起点、触发和恢复细节。 |
| 0.4.0 | 2026-09-30 | 明确 Spring 六字段、秒级计划边界及固定注解与动态编程式调度的适用场景，同步已定输入和创建行为。 |
| 0.3.0 | 2026-09-29 | 配置设计收敛到 Claw 接口及 Claude 取舍，创建登记自动计划，已有目标使用 Session 标识。 |
| 0.2.0 | 2026-09-29 | 优先建立配置页面至 Mate/Claw 持久化的完整闭环，执行与恢复策略保留待细化边界。 |
| 0.1.0 | 2026-09-29 | 建立以 Claude Scheduled deployments 为主基线的两类定时执行目标，优先设计独立会话与持久受理。 |
