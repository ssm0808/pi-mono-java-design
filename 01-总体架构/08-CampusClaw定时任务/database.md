# 定时任务数据库设计

[模块主设计](README.md) · [执行流程](execution.md) · [HTTP 契约](configuration.md) · [数据与存储索引](../../03-数据与存储/README.md)

版本：0.1.0；日期：2026-10-10。

## 1. 业务问题与维护边界

园区每天 08:00 的设备告警汇总需要分别保存长期任务配置、这一次触发的受理事实，以及实际执行的会话历史。数据库还要保证多实例不会重复受理同一个计划时刻，删除任务后已经受理的会话仍能独立完成。

正常流程是：保存 Schedule；到期领取 Run 并占用任务；事务外准备可信执行上下文；在同一数据库事务中创建 Session、首消息和根执行并关联 Run；提交后取得一次启动权；最终按原根执行对账并释放任务占用。准备失败只结束本次 Run；提交结果或执行结果未知时先对账，不重发首消息或业务调用。完整流程由[执行设计](execution.md)维护。

**本文是 M10 数据库设计的唯一维护入口**，负责表职责、字段字典、约束、索引、数据库事务、删除和保留边界。主设计负责模块职责与目标类图，执行设计负责调度策略，配置设计负责公共报文；它们引用本文，不再各维护一份表模型。Session 的通用结构仍归 [M04](../../03-数据与存储/01-会话记忆GaussDB/README.md)，本文只维护定时入口对既有表的扩展。

本文区分有效目标与代码证据：§2、§7 为目标约束；§3～§6 列出 PR #332 已实现的物理结构及其用途，不能据此认定所有历史目标均已完成；差距和验收见 §8。不在设计仓复制另一份可执行安装 SQL，实施 SQL 由实现仓维护并与本文核对。

<a id="source-baseline"></a>

### 源码基线

2026-10-10 重新读取 PR 元数据，并在隔离仓库 fetch 当前 head 与 base，计算实际 merge-base；设计仓同时 fetch `origin/main`。没有切换或覆盖实现仓工作树。

| 对象 | 本次快照与范围 |
|---|---|
| 设计仓 main | `24a042a0bf1c6aceb3dd8885d27de083d37f6218`；作为本次文档整理起点 |
| 实现 PR | [pi-mono-java #332](https://github.com/superheromeZzh/pi-mono-java/pull/332)，Draft、未合并；分支 `codex/scheduled-task-backend`，head `e9d31e8888a81b7fe95071e705482bb16fa10476` |
| PR base / merge-base | `main@769e86592285f4a25b0febaf551eddea6bc7212c`；实际 merge-base 同此提交 |
| 旧证据 | 原文 `main@553dcd5e2ff682f9684810a043b442b37a02e54a` 的 JSON Cron 结论保留历史归属；不用于否定本 PR 已有 SQL 实现 |
| 核验范围 | 下列安装 DDL、Schedule Mapper、配置与受理事务、Runtime 启动 CAS；不升级外部 Agent 基线或未读取模块的结论 |

所有实现路径均属于 `pi-mono-java`。下表链接固定到上述 PR head，字段长度、可空性和索引以 S1 为证据。

| 编号 | 仓库相对路径与关键符号 | 证明范围 |
|---|---|---|
| S1 | [modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql](https://github.com/superheromeZzh/pi-mono-java/blob/e9d31e8888a81b7fe95071e705482bb16fa10476/modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql#L616)；`t_schedule`、`t_schedule_run`、`t_schedule_dispatch_state`，以及 `t_sessions`、`t_session_executions` | 三张新表、既有表扩展、CHECK、外键与索引；是新环境完整安装脚本 |
| S2 | [modules/coding-agent-cli/src/main/resources/mapper/schedule/ScheduleMapper.xml](https://github.com/superheromeZzh/pi-mono-java/blob/e9d31e8888a81b7fe95071e705482bb16fa10476/modules/coding-agent-cli/src/main/resources/mapper/schedule/ScheduleMapper.xml)；`lockSchedule`、`lockDispatchState`、`updateRun`、`releaseActiveRun`、`listRuns`、`deleteExpiredRuns` | 行锁、领取身份条件更新、查询与清理；`now` 使用数据库 `clock_timestamp()` |
| S3 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/schedule/application/ScheduleApplicationService.java](https://github.com/superheromeZzh/pi-mono-java/blob/e9d31e8888a81b7fe95071e705482bb16fa10476/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/schedule/application/ScheduleApplicationService.java)；`createLocked`、`update`、`delete`、`pause`、`unpause` | 配额协调、最新行合并、配置及 Run 同事务删除 |
| S4 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/schedule/dispatch/ScheduleRunCoordinator.java](https://github.com/superheromeZzh/pi-mono-java/blob/e9d31e8888a81b7fe95071e705482bb16fa10476/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/schedule/dispatch/ScheduleRunCoordinator.java)；`claim`、`accept`、`requireAcceptance`、`reconcilePersisted` | 领取、事务外准备、事务内复查与原根执行对账 |
| S5 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/schedule/ScheduledRuntimeAdmissionService.java](https://github.com/superheromeZzh/pi-mono-java/blob/e9d31e8888a81b7fe95071e705482bb16fa10476/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/schedule/ScheduledRuntimeAdmissionService.java)；`accept`、`start`、`recoverExpiredStarts`、`encodeContext` | 同事务创建会话、提交后启动、配置删除后的独立收尾与最小上下文 |
| S6 | [modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeExecutionControlMapper.xml](https://github.com/superheromeZzh/pi-mono-java/blob/e9d31e8888a81b7fe95071e705482bb16fa10476/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeExecutionControlMapper.xml#L26)；`saveExecutionContext`、`claimScheduledStart`、`fenceExpiredScheduledStart` | 数据库启动期限、READY→STARTING / FENCED 的条件更新 |

JSON 编码和省略值另核对 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/schedule/application/ScheduleJsonCodec.java` 的 `write/metadata/credentials` 与同目录 `ScheduleConfigurationMerger.java` 的 `merge/message/metadata/credentials`；同一 PR head。临时上下文清理检索范围为 `modules/coding-agent-cli/src/main` 中上述扩展列的写入及 Mapper 更新。

## 2. 表职责与关联

| 表 | 权威职责 | 关联及生命周期 |
|---|---|---|
| `t_schedule` | 当前任务配置、自动计划游标、同任务唯一占用 | 一条配置对应多条 Run；删除时与其 Run 同事务退出 |
| `t_schedule_run` | 一次触发是否受理，以及受理时固定的 Session/根执行身份 | `schedule_id` 外键指向配置并级联删除；Session/根执行为逻辑引用 |
| `t_schedule_dispatch_state` | 自动扫描领跑者、代次、租约和恢复边界 | 全局一条约定协调记录，不是 Run 队列或漏跑历史 |
| `t_sessions` | 会话及其独立归属 | 不受 Schedule/Run 删除级联；后续对话不会改变原 Run 的关联 |
| `t_session_executions` | 原根执行控制、实际开始时间和一次启动权 | 按 `(session_id, execution_id)` 定位；删除配置后仍能处理已受理执行 |

业务上的一对一受理关联由同库事务与状态检查维持，PR 没有为 Run 的 `session_id` 或 `execution_id` 建立唯一约束或外键。`active_run_id` 也没有反向外键；占用、释放和清理由事务规则维护，避免与配置级联删除形成循环依赖。

不新增 `t_schedule_gap`、请求去重表、可恢复的 Schedule/Run 墓碑或隐藏归档。停机期间未观察到的计划只推进游标；已观察到的忙跳过可以形成一条明确未受理的 Run。不同手动请求独立分配 runId，不能根据相同内容合并。

## 3. t_schedule：任务配置

下表“可空”描述 PR DDL；各列没有数据库 DEFAULT，由应用负责赋值。表名统一 `t_` 小写蛇形，SQL 对象注释使用中文。

| 字段 | SQL 类型 | 可空 | 含义 |
|---|---|---|---|
| id | VARCHAR(41) | 否，主键 | `schedule-` 加 32 位 UUID 十六进制 |
| scope_ref | TEXT | 否 | 企业认证桥确认的管理范围引用 |
| operator_ref | TEXT | 否 | 最近配置操作的可信主体 |
| agent_id | VARCHAR(38) | 否 | 已绑定 Agent 身份 |
| name | VARCHAR(256) | 否 | 任务名称 |
| description | VARCHAR(2048) | 是 | 任务描述 |
| message | TEXT | 否 | 单条文本 user.message 的 JSON，不是裸提示词列 |
| cron_expression | TEXT | 是 | Spring 六字段表达式；仅手动时为空 |
| timezone | TEXT | 是 | 与 Cron 成对保存的时区；默认值由服务归一化 |
| status | VARCHAR(16) | 否 | `active` / `paused` |
| paused_reason | VARCHAR(16) | 是 | 当前暂停原因；有效值及转换由配置契约定义 |
| metadata | TEXT | 否 | 附加元数据的 JSON 对象，无值时应用写入 `{}` |
| credential_ids | TEXT | 否 | 凭据引用的 JSON 数组，无值时应用写入 `[]`，不保存秘密 |
| authorization_ref | TEXT | 否 | Mate 提供的非秘密授权引用，不是访问令牌 |
| session_owner_ref | TEXT | 否 | 新 Session 的可信独立归属引用 |
| revision | BIGINT | 否 | 内部配置代次，创建时为 1；不作为公共条件更新字段 |
| active_run_id | VARCHAR(36) | 是 | 唯一进行中或待对账 Run；为空才可新占用 |
| last_run_at | TIMESTAMPTZ(0) | 是 | 最近自动运行的实际开始时刻；手动、准备失败和跳过不更新 |
| next_fire_at | TIMESTAMPTZ(0) | 是 | 下一自动计划时刻；仅手动、暂停或规则无后续时刻时为空 |
| created_at | TIMESTAMPTZ(0) | 否 | 创建时间 |
| updated_at | TIMESTAMPTZ(0) | 否 | 配置更新时间；实际开始时间投影不修改它 |

数据库 CHECK 已限制 status 枚举、active 时暂停原因为空、paused 时暂停原因非空，以及 Cron/timezone 同空或同非空。具体暂停原因枚举、Cron 可解析性、JSON 结构、引用资格和配置代次有效性由应用校验；不能把 NOT NULL 或 TEXT 类型当作这些校验已经由数据库保证。

暂停原因与 status 在同一事务修改，精确值、清空条件和响应投影引用[配置契约](configuration.md#schedule-type-paused-reason)；历史 Run 错误和独立审计不代替当前暂停原因，也不因恢复而删除。

资源 `type` 是响应常量，不落库；`upcomingRunsAt` 从已保存规则计算，不存五个未来时间列。当前 TEXT JSON 存储是 PR 的实现选择，不据此宣称优于 JSONB；本文没有新增 JSON 查询或索引要求。

## 4. t_schedule_run：一次受理事实

各列无数据库 DEFAULT。Run 的内部协调状态和 Session 的业务执行状态分开，不把 `FINISHED` 当成园区业务成功。

| 字段 | SQL 类型 | 可空 | 含义 |
|---|---|---|---|
| id | VARCHAR(36) | 否，主键 | `run-` 加 32 位 UUID 十六进制 |
| schedule_id | VARCHAR(41) | 否 | 所属配置；外键 `ON DELETE CASCADE` |
| scope_ref | TEXT | 否 | 领取时的可信范围 |
| agent_id | VARCHAR(38) | 否 | 本次绑定的 Agent 身份 |
| revision | BIGINT | 否 | 领取使用的配置代次，最终受理时复查 |
| trigger_type | VARCHAR(16) | 否 | `manual` / `schedule` |
| scheduled_at | TIMESTAMPTZ(0) | 是 | 自动触发的 UTC occurrence；手动必须为空 |
| state | VARCHAR(16) | 否 | DDL 允许 `PREPARING`、`READY`、`STARTING`、`FINISHED` |
| error_type | VARCHAR(64) | 是 | 未受理的稳定安全错误；不承载模型或工具业务终态 |
| session_id | VARCHAR(40) | 是 | 已受理的历史 Session ID，不设会话外键 |
| execution_id | VARCHAR(64) | 是 | 本次首消息的固定根执行 ID |
| root_event_id | VARCHAR(64) | 是 | 原始 user.message 的事件 ID |
| segment_id | VARCHAR(64) | 是 | 受理创建的执行段 ID |
| claim_owner | VARCHAR(64) | 否 | 本次准备所属实例 |
| claim_epoch | BIGINT | 否 | 自动扫描代次；手动为 0 |
| lease_until | TIMESTAMPTZ(3) | 否 | 准备受理期限，不是已启动执行的强制释放期限 |
| created_at | TIMESTAMPTZ(0) | 否 | Run 创建时间 |
| finished_at | TIMESTAMPTZ(0) | 是 | 内部协调完成时间，用于已结束 Run 清理 |

数据库已建立以下约束：

- `UNIQUE(schedule_id, scheduled_at)` 防止重复分配自动 occurrence；UTC instant 区分夏令时重复钟面。手动 `scheduled_at=NULL`，每次单独分配 ID；目标数据库对唯一约束中 NULL 的行为须纳入集成验收。
- trigger CHECK 要求 manual 的 scheduled_at 为空、schedule 的 scheduled_at 非空。
- `CHECK(session_id IS NULL OR error_type IS NULL)` 只保证两者不能同时非空；PREPARING 阶段允许两者都空。它不保证“必有一个结果”，最终公共受理结果由应用和查询投影保证。
- 其余关联字段成组完整、scope 与父配置一致、Run 与 active_run_id 对应，依靠事务内应用校验；PR DDL 未建立相应复合外键或 CHECK。

PR 当前正常状态写入为 `PREPARING → READY → FINISHED`，未受理失败从 PREPARING 结束；SQL 虽允许 Run.STARTING，当前领取启动权写入的是根执行的 `schedule_start_state`，不能混为同一状态机。实际业务状态和错误从原 Session/根执行读取。

单独删除 Session 不清空 Run.session_id、不级联删除 Run，也不把已成功受理改成失败；原会话链接可以返回 404。

## 5. t_schedule_dispatch_state：扫描协调

| 字段 | SQL 类型 | 可空 | 含义 |
|---|---|---|---|
| id | VARCHAR(32) | 否，主键 | 应用约定固定为 `scheduled-dispatch` |
| owner | VARCHAR(64) | 是 | 当前扫描领跑者 |
| epoch | BIGINT | 否 | 当前自动调度代次 |
| lease_until | TIMESTAMPTZ(3) | 是 | 数据库时间确定的协调租约期限 |
| completed_at | TIMESTAMPTZ(3) | 是 | 上次完整扫描游标 |
| recovery_boundary | TIMESTAMPTZ(3) | 是 | 新代次跳过未受理历史计划的固定边界 |

安装 SQL 插入 `('scheduled-dispatch', 0)`，其余列初始为空；列本身无 DEFAULT。单行由安装及 Mapper 的固定 ID 约定保证，DDL 主键本身不禁止其他 ID。协调行不存在时不能退化为各实例独立扫描。

该记录仅决定未来自动触发的分配权；租约失效不意味着旧 Run 已终止，也不授权新节点重新执行旧会话。恢复与不补漏跑策略引用[执行规则](execution.md#no-catch-up)。

## 6. 既有表扩展及索引

### 6.1 Session 与根执行扩展

下列列在 PR DDL 中均可空、无数据库 DEFAULT，以允许普通交互入口不携带定时上下文；定时受理时必须由可信服务写入必要值。

| 表与字段 | SQL 类型 | 用途 |
|---|---|---|
| t_sessions.scope_ref | TEXT | Session 自己的可见范围，不依赖任务仍然存在 |
| t_sessions.session_owner_ref | TEXT | Mate 确认的 Session 归属 |
| t_session_executions.started_at | TIMESTAMPTZ(3) | 原根执行持久化的实际开始时间；不能从启动权推断 |
| t_session_executions.execution_context_json | TEXT | 最小非秘密调度来源和授权引用 |
| t_session_executions.schedule_start_state | VARCHAR(16) | 应用使用 `READY`、`STARTING`、`FENCED`，DDL 未设枚举 CHECK |
| t_session_executions.schedule_start_owner | VARCHAR(64) | 持有同次准备快照的原实例 |
| t_session_executions.schedule_start_deadline | TIMESTAMPTZ(3) | 数据库受理时设置的一次启动截止时间 |

`execution_context_json` 当前编码 `scheduleId`、`runId`、`agentId`、`scopeRef`、`sessionOwnerRef`、`authorizationRef`、`credentialIds`。不保存完整任务配置、浏览器 Header 或业务秘密；它不是重新创建任务或重放业务的材料。安全收尾后的临时上下文清理是目标要求，当前差距见 §8。

定时业务时间遵守[统一秒级规则](../01-CampusClaw多Agent运行时/time-contract.md)，应用先规范化再写入；内部租约、根执行控制及启动期限保留毫秒精度。不能笼统把所有 TIMESTAMPTZ 列都改成秒级。根执行实际开始时间投影到 `last_run_at` 时按公共秒级约定处理。

### 6.2 已有索引与查询目的

以下名称、顺序和谓词来自 S1，不是新的性能承诺；主键和自动 occurrence 唯一约束另产生对应约束索引。

| 索引 | 列 / 条件 | 支持的访问 |
|---|---|---|
| idx_schedule_due | t_schedule `(status, next_fire_at, id)` | active 到期扫描及恢复推进 |
| idx_schedule_scope_list | t_schedule `(scope_ref, updated_at DESC, id)` | 范围内配置列表 |
| idx_schedule_run_list | t_schedule_run `(scope_ref, created_at DESC, id DESC)` | Run 范围与时间排序访问的候选索引 |
| idx_schedule_run_retention | t_schedule_run `(state, finished_at, id)` | FINISHED 且超过保留期的批量清理 |
| idx_t_session_executions_schedule_start | t_session_executions `(session_id, execution_id, schedule_start_deadline)`；仅 `schedule_start_state='READY' AND started_at IS NULL AND state IN ('RUNNING','STOPPING')` | 独立扫描过期且未启动根执行，包括任务已删除的情形 |

`listRuns` 实际按父配置 `s.scope_ref` 过滤并 JOIN 配置，不能仅凭 `idx_schedule_run_list` 存在就宣称该查询有效使用它。名称子串查询、跨范围轮转窗口、Run 过滤和清理均须在真实 GaussDB 数据规模下查看执行计划；尚无此性能验收结论。

<a id="transactions"></a>

## 7. 事务、删除与保留约束

| 操作 | 必须原子维持的数据库不变量 | PR 对应证据 |
|---|---|---|
| 配置创建/修改/暂停/恢复 | 最新配置与 revision、状态/原因、游标一起提交；远端授权准备在锁外，锁内重新检查其适用性 | S3；创建还锁协调行后检查范围配额 |
| 领取自动/手动 Run | 锁 Schedule，检查 active_run_id；插入 Run 与任务占用同事务，自动触发同时推进游标；忙跳过不释放他人占用 | S2/S4 |
| 最终受理 | 自动入口先验证协调 owner/epoch/lease；锁 Schedule、Run，复查 revision、领取身份、期限与授权；Session、首消息、根执行/segment、Run 关联一起提交 | S4/S5；Runtime.accept 要求已有事务 |
| 提交后启动 | 原实例以固定根身份和 owner 做 READY→STARTING CAS，数据库时间未超过 deadline、state=RUNNING、started_at 为空才可取得启动权 | S5/S6；模型及业务执行不进入受理事务 |
| 未启动过期收尾 | 仅对 READY、started_at 为空且已过期的根执行围栏；与真实终态提交配合，STOPPING 保留取消原因；不接管重跑 | S5/S6；独立根扫描不依赖 Schedule/Run 存在 |
| 根终态对账 | 固定原 execution，不读取 Session 后续聊天作为本次结果；Run 更新核对 owner/epoch，释放只匹配自身 active_run_id | S2/S4；未知或 STARTING 失联不因租约到期释放 |
| 删除配置 | 锁 Schedule，在同一事务删除 Run 和 Schedule；若受理先提交则保留 Session，若删除先提交则拒绝旧准备结果 | S2/S3/S4；外键级联为一致性兜底，应用也显式删除 Run |

删除不请求取消、不回滚已发生的园区业务；已受理会话通过自身权限和停止入口管理。删除后的回调只能条件更新仍存在的记录，影响行数为零时不 upsert、不重新插入。内部协调归原根执行生命周期，不能永久保留完整配置或提供隐藏 Run 历史。

Run 保留时长、清理频率和批量由[部署初始值](execution.md#deployment-defaults)唯一维护。清理只删除已明确 FINISHED 且超期的记录，不删除未知占用，不级联 Session；删除 Schedule 则立即删除全部对应 Run，不等待保留期。Session 的保留策略归自身模块。

定时器、线程、本地扫描缓存及本地租约计时均不是权威状态，不能覆盖数据库游标、Run 关联或根执行。Spring 单例只持有线程安全基础设施，不共享可变租户上下文；准备快照、凭据与执行对象按本次 Run 隔离。

单扫描协调行便于确定恢复边界，同库受理避免半个会话关联；代价是协调热点、事务耦合及数据库故障时停止准入。此处沿用既有 CampusClaw 架构选择，不新增依赖或跨库协议，也不承诺外部业务 exactly-once。

<a id="gaps"></a>

## 8. 实现差距与验收

| 项目 | 状态与边界 |
|---|---|
| 三张调度表、Mapper 与受理/启动控制 | **PR #332 已实现、未合入 main**；本次为指定源码范围的静态核验，不代表已安装或企业部署完成 |
| 安全配置快照、实际 Agent 发布版本/摘要 | 原主设计包含这些目标；PR Run 表没有对应列，最小根上下文也未保存发布版本。**待实现**，具体载体与字段需进一步设计；本文不为填齐目标擅自增列，也不把 revision 当作完整快照 |
| 根执行内部上下文清理 | 目标要求安全收尾后清理必要临时协调；已核验启动与围栏 SQL，未见所列字段的独立清理动作。该清理接线**待实现**，Session 自身最终删除不等同于已实现收尾清理 |
| 标识长度对齐 | PR Run 的 session_id 为 40、execution/root/segment 为 64，而既有根表对应列为 128；当前物理长度如实保留，跨入口 ID 上限与未来兼容性仍须核验，不能默认为完全对齐 |
| GaussDB 安装及并发 | **未验收**；本次未运行数据库测试。PR 报告的 PostgreSQL 验证不代替真实 GaussDB 的 NULL 唯一性、部分索引、时间函数与锁竞争验证 |
| 存量升级 | S1 明确是会 DROP 并重建的全量安装脚本，不是 ALTER 升级方案；存量迁移脚本不在当前首版范围，不能直接用于保留数据的升级 |

实施至少验证：同一自动 occurrence 并发只受理一次、手动与自动互斥、更新/暂停/删除与受理竞争、事务中途失败全回滚、重复内部通知不创建第二个 Session、启动 CAS 与过期围栏互斥、未知执行不释放、删除配置后根执行仍可收尾、删除 Session 后 Run 保留受理事实，以及历史清理不删除会话。真实 GaussDB 的执行计划、两副本故障注入和企业身份联调分别记录，文档校验不能替代它们。

文档校验：三张新表 45 列及既有表 7 个扩展列的类型、可空性已与 S1 核对；新增/修改链接及接口 HTML 同步通过。仓库图源检查为 37 个专题、136 个图块、0 错误；图源和 SVG 未修改，图索引再生成无差异，沿用既有压缩图复杂度说明，不新增视觉验收结论。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.0 | 2026-10-10 | 集中维护定时任务表、Session 扩展、约束索引与事务生命周期，并记录 PR #332 的实现和验收边界。 |
