# Claw 数据库设计

[仓库首页](../README.md) · [数据与存储](README.md)

版本：1.15.0 · 日期：2026-10-14 · 范围：CampusClaw 服务自身的集中式 GaussDB 数据库。

## 1. 职责、读取方式与源码基线

园区告警处置会产生会话、模型和工具历史、人工决定及执行终态；定时巡检还要保存计划和每次受理记录。数据库设计需要在一个地方说明这些记录如何关联、谁是权威、哪些记录可以删除，避免不同模块各自扩展同一张表而互相遗漏。

正常调用由应用在短事务内提交输入与固定执行身份，事务外执行模型和园区业务，再将完整结果与公共投影提交；统计只在其所属事务规则下更新。失败时数据库事务回滚，已发生的外部业务不会随之回滚；未知结果先读持久记录对账，不自动重放业务。各模块继续解释流程、接口和权限，本文统一维护其数据库结构。

**本文是 Claw 数据库设计的唯一主文件。** 表清单、字段、主外键、约束、索引、数据生命周期及结构增量集中于此。各业务文档双向链接到对应表或增量章节；SQL 文件作为对应版本的实施材料或待实现片段关联，不能代替全库设计，也不能各自定义另一套有效结构。现有图继续由所属模块维护，本文复用链接，不另画一套实现类图。

### 1.1 核验快照

2026-10-10 确认实现仓默认分支为 main，隔离 fetch main 与 PR #332 head，并核对 PR 元数据及实际 merge-base；设计仓同时 fetch main。未覆盖用户实现工作树。

| 证据 | 完整提交与范围 |
|---|---|
| 当前主线 M | pi-mono-java `main@769e86592285f4a25b0febaf551eddea6bc7212c`；完整安装 DDL 19 张表，§4 为该快照的字段字典 |
| 定时任务 PR S | #332 / `codex/scheduled-task-backend@e9d31e8888a81b7fe95071e705482bb16fa10476`，Draft、未合并；base 与实际 merge-base 均为 `769e86592285f4a25b0febaf551eddea6bc7212c`；新增 3 表及既有表扩展，见 §5 |
| 设计整理起点 | pi-mono-java-design `main@6ec8fd2b43a209b582b1a8b726f23757a2dafab2` |
| 待实现 D | 本仓统一历史、Skill 累计与秒级时间目标；按 §3、§6 独立标识，不冒充 main 或 PR 的已实现结构 |

核验“当前”是上述源码快照，不表示已经安装到生产数据库；数据库验收另列。外部 Agent 基线和 Mate 源码未重新核验，保留关联文档自己的日期与状态。

### 1.2 代码与设计材料

| 编号 | 文件与关键符号 | 作用 |
|---|---|---|
| M1 | [modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql](https://github.com/superheromeZzh/pi-mono-java/blob/769e86592285f4a25b0febaf551eddea6bc7212c/modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql)；`CREATE TABLE / ALTER TABLE / CREATE INDEX` | 主线完整物理结构，含执行、控制、历史、清理与统计 |
| M2 | [modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml](https://github.com/superheromeZzh/pi-mono-java/blob/769e86592285f4a25b0febaf551eddea6bc7212c/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml)；`lockSessionForUpdate / lockNextSequence / listTimelineEntries / listCommittedEvents / countUnmappedTimelineEntries / markSkillHistoryPruned` | Session 锁、序号、非递归查询与现有删除投影 |
| M3 | [modules/coding-agent-cli/src/main/resources/mapper/session/SkillLoadMapper.xml](https://github.com/superheromeZzh/pi-mono-java/blob/769e86592285f4a25b0febaf551eddea6bc7212c/modules/coding-agent-cli/src/main/resources/mapper/session/SkillLoadMapper.xml)；`insert / incrementTotal / incrementDaily / query` | 当前三表统计读写；不代表统一结果目标已落地 |
| M4 | [modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_privileges.sql](https://github.com/superheromeZzh/pi-mono-java/blob/769e86592285f4a25b0febaf551eddea6bc7212c/modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_privileges.sql)；`GRANT` | 主线 19 表的运行身份 DML 授权 |
| M5 | [modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_initial_data.sql](https://github.com/superheromeZzh/pi-mono-java/blob/769e86592285f4a25b0febaf551eddea6bc7212c/modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_initial_data.sql)；`BEGIN / COMMIT` | 主线没有静态业务种子，每会话事务初始化自身行 |

定时任务代码证据 S1～S6 见 §5.7。目标 SQL 的适用状态与所属设计见 §8；新环境完整安装脚本与局部示意不能互换。

<a id="table-index"></a>

## 2. 全库表清单与模块关联

名称可直接定位字段字典。M 表示已在本次主线 DDL 中存在；S 表示仅本次 PR 新增；D 表示目标待实现。M 与 D 同时出现时，表示现有表另有目标变更，不能把整张表标成未实现。

| 表 | 职责 | 状态 | 对应设计文件 |
|---|---|---|---|
| [t_sessions](#t_sessions) | 会话主表，保存会话元数据和单条时间线末端 | M；有 D 增量 | [Session 职责与恢复](01-会话记忆GaussDB/README.md) |
| [t_session_entries](#t_session_entries) | 会话历史记录表，按提交顺序保存单条只追加时间线 | M；有 D 增量 | [Session 职责与恢复](01-会话记忆GaussDB/README.md) |
| [t_session_sequences](#t_session_sequences) | 会话序号表，为 Entry 和内部 Record 分配严格递增的持久化顺序号 | M | [Session 职责与恢复](01-会话记忆GaussDB/README.md) |
| [t_session_records](#t_session_records) | 会话内部运行记录表，保存不参与消息时间线的 Usage 等记录 | M | [Session 职责与恢复](01-会话记忆GaussDB/README.md) |
| [t_session_stats](#t_session_stats) | 会话生命周期消息数、Token 和费用累计统计表 | M | [Session 职责与恢复](01-会话记忆GaussDB/README.md) |
| [t_session_materialized](#t_session_materialized) | 会话汇总表，保存单条时间线等可重建的物化数据 | M | [Session 职责与恢复](01-会话记忆GaussDB/README.md) |
| [t_session_events](#t_session_events) | 会话公共事件权威表，保存 GET 历史与 POST 完整帧共享的安全投影 | M | [事件契约](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md) · [历史查询](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md) |
| [t_session_event_projection](#t_session_event_projection) | 会话 Entry 公共事件投影完整性记录，用精确数量区分完整映射和显式私有记录 | M | [事件契约](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md) · [历史查询](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md) |
| [t_session_executions](#t_session_executions) | 消息根执行状态表，保存跨实例控制所需的固定执行身份 | M | [Runtime](../01-总体架构/01-CampusClaw多Agent运行时/README.md) · [执行与控制](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md) |
| [t_session_execution_segments](#t_session_execution_segments) | 执行结果段表，每次初始消息或确认续跑固定一个段 | M | [Runtime](../01-总体架构/01-CampusClaw多Agent运行时/README.md) · [执行与控制](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md) |
| [t_session_execution_segment_events](#t_session_execution_segment_events) | 执行段与已提交公共事件的内部关联表 | M | [Runtime](../01-总体架构/01-CampusClaw多Agent运行时/README.md) · [执行与控制](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md) |
| [t_session_tool_confirmations](#t_session_tool_confirmations) | 工具确认决定表，由原执行实例至多消费一次 | M | [Runtime](../01-总体架构/01-CampusClaw多Agent运行时/README.md) · [执行与控制](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md) |
| [t_session_plan_confirmations](#t_session_plan_confirmations) | 计划审核决定表，由原执行实例至多消费一次 | M | [计划审核](../01-总体架构/06-CampusClaw计划模式/README.md) |
| [t_session_question_answers](#t_session_question_answers) | 用户问题答案交接表，只引用已提交回执，由原执行实例至多消费一次 | M | [结构化提问](../01-总体架构/06-CampusClaw计划模式/ask-user-question.md) |
| [t_session_tombstone](#t_session_tombstone) | 会话永久删除墓碑表，只保留不可复用的会话标识和删除时间 | M | [Session 生命周期](01-会话记忆GaussDB/README.md#65-删除-session) |
| [t_session_cleanup_task](#t_session_cleanup_task) | 会话逻辑删除后用于异步物理清理的短期可重试任务表 | M | [Session 生命周期](01-会话记忆GaussDB/README.md#65-删除-session) |
| [t_skill_usage](#t_skill_usage) | 每次 Skill 工具成功返回正文的调用事实；同一次调用重复投递不更新来源或时间 | M；有 D 增量 | [Skill 统计](../04-命令与技能/03-Skill加载统计/README.md) |
| [t_skill_usage_stats](#t_skill_usage_stats) | Skill 工具成功调用累计次数；删除执行事实不减计数 | M；有 D 增量 | [Skill 统计](../04-命令与技能/03-Skill加载统计/README.md) |
| [t_skill_usage_daily_stats](#t_skill_usage_daily_stats) | 按 Asia/Shanghai 自然日归属的工具成功调用汇总，与事实及累计同事务提交 | M；有 D 增量 | [Skill 统计](../04-命令与技能/03-Skill加载统计/README.md) |
| [t_schedule](#t_schedule) | 任务配置与自动计划游标 | S；有 D 修改 | [定时任务](../01-总体架构/08-CampusClaw定时任务/README.md) |
| [t_schedule_run](#t_schedule_run) | 一次触发是否受理及原根执行关联，同任务唯一未结束 Run | S；有 D 修改 | [定时任务](../01-总体架构/08-CampusClaw定时任务/README.md) |
| [t_schedule_dispatch_state](#t_schedule_dispatch_state) | PR 的扫描协调表，目标撤销整表 | S；目标撤销 | [PR #332 差异](#schedule-pr-diff) |
| [t_session_execution_links](#child-links) | 一次父调用与独立子会话首执行关联 | D | [统一执行历史](../01-总体架构/01-CampusClaw多Agent运行时/unified-event-persistence.md) |

Agent、Tool、Skill、Model 的定义由 Mate/目录权威提供，Claw 保存其引用及必要执行快照；[Agent 元数据的五张表](02-Agent元数据GaussDB/README.md)属于 Mate 数据库设计，不在上面 Claw 安装表数中。凭据秘密由 Mate 保管；附件对象及 Chat 映射也各归所属服务，不为统一文档擅自复制到 Claw 库。

<a id="global-rules"></a>

## 3. 全库有效约束

| 维度 | 当前设计要求 | 本次实现状态 |
|---|---|---|
| 命名与描述 | 表名为 t_ 加小写 snake_case；SQL COMMENT 使用中文 | 已有主线与 PR 安装结构遵循此表名前缀；字段字典不代替缺失的部署注释 |
| 时间 | Session created_at/updated_at、Entry/Record timestamp、公共事件 created_at 统一 UTC 秒级，应用先截断；内部控制期限和租约保留必要精度 | main 的上述 5 列为 TIMESTAMPTZ(3)，PR #332 改为 (0)；Skill 目标另见 §6.3；[时间契约](../01-总体架构/01-CampusClaw多Agent运行时/time-contract.md)维护公共语义 |
| 标识与并发 | 内部 resource_version/revision 用于数据库一致性；不据此生成公共 If-Match、ETag 或请求幂等令牌 | PR 修正 Session 版本注释，主线旧注释不是有效公共接口要求；具体 HTTP 由契约文件维护 |
| 历史 | Session 线性追加，按提交序号读取；parent_id/active_leaf_id 用于完整性；内部完整结果与公共安全投影分开 | M2 的三个时间线/事件/完整性查询已非递归；无损坏自动截断或跳过保证 |
| JSON | payload 保存类型相关内容，结构校验由受控写入与恢复端负责；数据库 JSONB 校验不能替代权限和业务校验 | Schedule 在 PR 使用 TEXT JSON，不能把二者的类型支持混写 |
| 权限与秘密 | Mate 独立维护用户、资源归属和权限；Claw 只存运行数据及允许的资源引用，不存身份副本和业务 secret，见 §3.1 | PR 的归属列及本地权限链路须撤销；Mate 接线待实现 |
| 事务资源 | Run/Child 受理须与新 Session、首消息、根执行同库提交；网络授权准备及模型/工具执行在事务外 | Schedule 见 §5；统一 Child 与逐工具统计事务仍待实现 |
| 删除与恢复 | 清理按所属对象生命周期执行，停止请求不等于真实终态；不得因历史清理重置累计、复活配置或重放业务 | 具体既有表和待实现差距分别在 §4～§7；没有全库统一 ON DELETE CASCADE 策略 |

<a id="mate-ownership"></a>

### 3.1 Mate 与 Claw 的身份边界

**当前目标：用户、组织、租户、资源归属与权限由 Mate 维护，Claw 不保存这些信息或其引用副本。** Claw 保存 Schedule、Run、Session 和 execution 的技术标识、内容及执行状态；Mate 保存这些资源标识与用户、管理范围、授权政策的关联。资源独立存续不要求 Claw 复制用户归属。

- Claw 的 Session、Schedule、Run、DTO、Mapper、执行上下文及通用 Runtime 均不保存 `scope_ref` / `scopeRef`、`session_owner_ref` / `sessionOwnerRef`；Schedule 的 `operator_ref` / `operatorRef` 同步移出。不能改名为 tenant、owner、subject 或藏入 JSON 延续相同职责。
- Mate 对会话读取、继续对话、停止、删除以及任务管理执行当前权限检查。Claw 校验可信服务来源、具体操作和资源约束，再检查自己的业务状态；缺少或失效的 Mate 授权结果时拒绝，不退化为任意内部调用均可访问。单个资源授权不能扩展到其他资源。
- 任务/Run 列表的可见范围由 Mate 决定，Claw 不得自己推导。首版（2026-10-13 评审确定）由 Mate 拉取 Claw 的全部存续记录后按用户过滤、排序和分页，Claw 不接收获准集合、不保存 userId；读取量随全部记录增长。Claw 增加 userId 列为待定 T10。
- 定时任务不保存授权引用或凭据引用：用户权限只在配置任务时由 Mate 检查，运行时统一账号的 access-token 由 Mate 按批次签发，Claw 不落库。用户审计与租户配额在 Mate；Claw 保留技术执行审计、实例容量和任务互斥。
- PR 中的扫描 `owner`、`schedule_start_owner` 表示执行实例，不是用户；两者已随扫描协调表和启动权一并目标撤销。`agent_id`、父子 Session/execution 关系同样是运行关联，不代替用户授权。

正常定时受理先固定同次 Run 的拟建 Session ID，由 Mate 确认并持久登记该 ID 的归属，再执行 Claw 的同库受理；未确认归属不得启动模型或业务。Mate 关联失败或结果未知时不受理，先按固定 ID 只读核对，不另建会话或重放任务。Mate 已登记而 Claw 事务失败时，该关联不代表会话已存在，须按 Claw 权威状态核对后清理；未知提交不能直接清理。具体交接及生命周期由 [Mate 专项](../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md#session-ownership)维护，接线**待实现**，不宣称跨库原子提交。

删除 Schedule/Run 不删除 Mate 中已经建立的 Session 归属；Session 后续操作只依赖其自身关联和当前权限。删除 Session 成功后 Mate 才关闭其访问映射；响应丢失先核对。公共 Chat 映射可以稍后补齐，不能用它的异步完成代替受理前归属登记。

此划分是 CampusClaw 的产品约束与架构修正；PR #332 的身份副本和本地权限链路是待修改实现，证据见 [职责专项](../01-总体架构/08-CampusClaw定时任务/source-evidence.md#mate-boundary-review)。Mate 实际表名、现有认证 SDK 和服务端实现本次未核验，不在 Claw 数据库中为其新增占位表。

<a id="current-schema"></a>

## 4. 主线物理结构与目标差异

以下类型、可空性、默认值、主键、索引和约束均来自 M1，完整列出 19 张表；每张表后的“目标边界”说明已定但尚未体现在该快照中的差异。可空为“否”包含主键隐含的非空；“—”表示没有数据库 DEFAULT，不表示应用不会初始化。字段中文含义依据 SQL 注释与 M2/M3，缺省初始化由所属应用服务负责。

<a id="t_sessions"></a>

### 4.1 t_sessions

会话主表，保存会话元数据和单条时间线末端。对应：[Session 职责与恢复](01-会话记忆GaussDB/README.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| id | VARCHAR(128) | 否 | — | 会话的唯一 ID，用于关联该会话的历史记录、序号和汇总数据 |
| agent_id | VARCHAR(64) | 否 | — | 创建会话时固定且不可变的 Agent 标识 |
| display_name | VARCHAR(80) | 是 | — | 用户设置的当前会话名称；未设置时为空，最多 80 个 UTF-8 字节 |
| model_id | VARCHAR(128) | 否 | — | 后续用户事件默认使用的当前模型标识 |
| state | VARCHAR(16) | 否 | — | 会话粗粒度运行状态，仅允许 idle 或 running |
| thinking | BOOLEAN | 否 | — | 后续用户事件是否启用深度思考 |
| mode | VARCHAR(16) | 否 | `'build'` | 后续交互的工作模式，仅允许 build 或 plan |
| resource_version | BIGINT | 否 | — | 内部一致性版本；主线旧注释与当前公共契约差异见下文 |
| created_at | TIMESTAMPTZ(3) | 否 | — | 创建这个会话的时间 |
| updated_at | TIMESTAMPTZ(3) | 否 | — | 会话配置或运行状态最后更新时间 |
| cwd | VARCHAR(512) | 否 | — | 创建会话时使用的工作目录；可用于按工作目录筛选会话 |
| parent_session_id | VARCHAR(128) | 是 | — | 当前会话复制自哪个来源会话；没有来源时为空，不表示会话内部分支 |
| metadata | JSONB | 是 | — | 创建会话时由调用方提供的附加信息 JSON；未提供时为 SQL NULL |
| active_leaf_id | VARCHAR(128) | 是 | — | 单条时间线最新历史记录的 ID；空会话时为空，读取不依赖父链回溯 |

主键：`(id)`。

| 索引 | 规则 |
|---|---|
| idx_t_sessions_created_at | `(created_at DESC)` |
| idx_t_sessions_cwd | `(cwd)` |
| idx_t_sessions_parent | `(parent_session_id)` |

数据库约束（保持 M1 的精确条件）：

- `CONSTRAINT ck_t_sessions_state CHECK (state IN ('idle', 'running'))`
- `CONSTRAINT ck_t_sessions_mode CHECK (mode IN ('build', 'plan'))`
- `CONSTRAINT ck_t_sessions_resource_version CHECK (resource_version > 0)`
- `CONSTRAINT ck_t_sessions_display_name CHECK (display_name IS NULL OR octet_length(display_name) BETWEEN 1 AND 80)`

目标边界：目标中 resource_version 仅作内部一致性版本，不暴露 ETag 或客户端条件更新；主线 SQL 注释仍含旧 ETag 用途，不作为有效接口规则。created_at/updated_at 的秒级目标及 PR 归属见 §3；不增加用户范围或归属列，PR 偏差见 §5.5。

<a id="t_session_entries"></a>

### 4.2 t_session_entries

会话历史记录表，按提交顺序保存单条只追加时间线。对应：[Session 职责与恢复](01-会话记忆GaussDB/README.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 这条历史记录属于哪个会话；对应 t_sessions.id |
| id | VARCHAR(128) | 否 | — | 这条历史记录的 ID；在同一个会话内唯一 |
| entry_seq | BIGINT | 否 | — | 这条历史记录在会话中的持久化顺序号；从 1 开始且严格递增，允许因共享序号分配产生空洞 |
| parent_id | VARCHAR(128) | 是 | — | 这条历史记录的前一条 Entry ID；首条记录为空，仅用于写入完整性检查 |
| type | VARCHAR(64) | 否 | — | 这条历史记录的种类；新写入不接受 leaf、branch_summary 和 label |
| timestamp | TIMESTAMPTZ(3) | 否 | — | 这条历史记录产生时携带的事件时间；不是数据库保存该行的时间 |
| payload | JSONB | 否 | — | 这条历史记录的类型相关 JSON 内容；ID、父记录、事件时间和类型分别保存在其他字段中 |

主键：`(session_id, id)`。

| 索引 | 规则 |
|---|---|
| idx_t_session_entries_session_seq | 唯一 `(session_id, entry_seq)` |
| idx_t_session_entries_session_parent | `(session_id, parent_id)` |
| idx_t_session_entries_session_type | `(session_id, type)` |

目标边界：parent_id 只用于末端完整性，当前主线 Mapper 已按 entry_seq 顺序读取，不能沿用历史“递归查询待实现”的全局结论。工具结果关联的未落地设计见 §6.1。

<a id="t_session_sequences"></a>

### 4.3 t_session_sequences

会话序号表，为 Entry 和内部 Record 分配严格递增的持久化顺序号。对应：[Session 职责与恢复](01-会话记忆GaussDB/README.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 这行序号记录属于哪个会话；对应 t_sessions.id，每个会话一行 |
| next_seq | BIGINT | 否 | — | 下一条 Entry 或内部 Record 要使用的顺序号；新建会话时为 1，每次成功追加后加 1 |

主键：`(session_id)`。

目标边界：新 Session 由应用写入 next_seq=1，无数据库 DEFAULT。Entry、Record 和公共事件共享分配器，序号允许空洞，不得以 seq-1 推导前驱。

<a id="t_session_records"></a>

### 4.4 t_session_records

会话内部运行记录表，保存不参与消息时间线的 Usage 等记录。对应：[Session 职责与恢复](01-会话记忆GaussDB/README.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 这条运行记录属于哪个会话；对应 t_sessions.id |
| id | VARCHAR(128) | 否 | — | 这条运行记录的 ID；在同一个会话内唯一 |
| record_seq | BIGINT | 否 | — | 这条运行记录与 Entry 共享的会话持久化顺序号 |
| lane | VARCHAR(32) | 否 | — | 运行记录所属执行通道；当前固定为 main |
| run_id | VARCHAR(128) | 否 | — | 产生这条运行记录的已接受用户执行 ID |
| type | VARCHAR(64) | 否 | — | 运行记录类型；当前支持 usage |
| timestamp | TIMESTAMPTZ(3) | 否 | — | 产生这条运行记录的事件时间 |
| payload | JSONB | 否 | — | 运行记录的类型相关 JSON 内容 |

主键：`(session_id, id)`。

| 索引 | 规则 |
|---|---|
| idx_t_session_records_session_seq | 唯一 `(session_id, record_seq)` |
| idx_t_session_records_session_run | `(session_id, run_id, record_seq)` |
| idx_t_session_records_session_type | `(session_id, type, record_seq)` |
| idx_t_session_records_session_lane | `(session_id, lane, record_seq)` |

<a id="t_session_stats"></a>

### 4.5 t_session_stats

会话生命周期消息数、Token 和费用累计统计表。对应：[Session 职责与恢复](01-会话记忆GaussDB/README.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 这份累计统计属于哪个会话；对应 t_sessions.id，每个会话一行 |
| message_count | BIGINT | 否 | — | 已持久化的用户、助手和工具结果消息总数 |
| cached_tokens | BIGINT | 否 | — | 模型调用命中缓存的 Token 累计数 |
| uncached_tokens | BIGINT | 否 | — | 模型调用输入与缓存写入 Token 的累计数 |
| total_tokens | BIGINT | 否 | — | 模型调用上报的总 Token 累计数 |
| input_tokens | BIGINT | 否 | — | 模型调用上报的非缓存输入 Token 累计数 |
| output_tokens | BIGINT | 否 | — | 模型调用上报的输出 Token 累计数 |
| cache_read_tokens | BIGINT | 否 | — | 模型调用上报的缓存读取 Token 累计数 |
| cache_write_tokens | BIGINT | 否 | — | 模型调用上报的缓存写入 Token 累计数 |
| cost_input | NUMERIC(24,8) | 否 | — | 模型调用输入 Token 的 USD 费用累计额 |
| cost_output | NUMERIC(24,8) | 否 | — | 模型调用输出 Token 的 USD 费用累计额 |
| cost_cache_read | NUMERIC(24,8) | 否 | — | 模型调用缓存读取 Token 的 USD 费用累计额 |
| cost_cache_write | NUMERIC(24,8) | 否 | — | 模型调用缓存写入 Token 的 USD 费用累计额 |
| cost_total | NUMERIC(24,8) | 否 | — | 模型调用费用的累计总额 |

主键：`(session_id)`。

数据库约束（保持 M1 的精确条件）：

- `CONSTRAINT ck_t_session_stats_nonnegative CHECK ( message_count >= 0 AND cached_tokens >= 0 AND uncached_tokens >= 0 AND total_tokens >= 0 AND input_tokens >= 0 AND output_tokens >= 0 AND cache_read_tokens >= 0 AND cache_write_tokens >= 0 AND cost_input >= 0 AND cost_output >= 0 AND cost_cache_read >= 0 AND cost_cache_write >= 0 AND cost_total >= 0 )`

<a id="t_session_materialized"></a>

### 4.6 t_session_materialized

会话汇总表，保存单条时间线等可重建的物化数据。对应：[Session 职责与恢复](01-会话记忆GaussDB/README.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 这份汇总属于哪个会话；对应 t_sessions.id，每个会话一行 |
| payload | JSONB | 否 | — | 会话汇总 JSON；可保存时间线名称、模型和思考级别等可重建视图，不保存 Usage |

主键：`(session_id)`。

目标边界：当前 Runtime 以空 JSON 对象初始化，Usage 权威为 t_session_records/t_session_stats。旧基础示意中的 lifetimeUsage 不能成为另一份并行累计权威；activePath 只是沿用的汇总键名，不意味着 Session 支持分支。

<a id="t_session_events"></a>

### 4.7 t_session_events

会话公共事件权威表，保存 GET 历史与 POST 完整帧共享的安全投影。对应：[事件契约](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md) · [历史查询](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 这条公共事件属于哪个会话；对应 t_sessions.id |
| event_id | VARCHAR(128) | 否 | — | 对外公开且永不复用的稳定事件标识 |
| event_seq | BIGINT | 否 | — | 公共事件与 Entry、内部 Record 共享的会话提交顺序号 |
| anchor_entry_id | VARCHAR(128) | 否 | — | 公共事件所属的 Entry 标识，用于投影完整性和数量校验 |
| type | VARCHAR(64) | 否 | — | 完整公共事件的 v2 类型字面值 |
| created_at | TIMESTAMPTZ(3) | 否 | — | 形成权威公共记录时保存一次的 UTC 毫秒时间 |
| payload | JSONB | 否 | — | 只包含该公共事件安全业务字段的 v2 JSON 对象 |

主键：`(session_id, event_id)`。

| 索引 | 规则 |
|---|---|
| idx_t_session_events_session_seq | 唯一 `(session_id, event_seq)` |
| idx_t_session_events_session_anchor | `(session_id, anchor_entry_id, event_seq)` |

<a id="t_session_event_projection"></a>

### 4.8 t_session_event_projection

会话 Entry 公共事件投影完整性记录，用精确数量区分完整映射和显式私有记录。对应：[事件契约](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md) · [历史查询](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 被核验 Entry 所属的会话标识 |
| anchor_entry_id | VARCHAR(128) | 否 | — | 已完成公共投影核验的 Entry 标识 |
| event_count | INTEGER | 否 | — | 该 Entry 应有的完整公共事件精确数量；零表示经确认不公开 |

主键：`(session_id, anchor_entry_id)`。

数据库约束（保持 M1 的精确条件）：

- `CONSTRAINT ck_session_event_projection_count CHECK (event_count >= 0)`

<a id="t_session_executions"></a>

### 4.9 t_session_executions

消息根执行状态表，保存跨实例控制所需的固定执行身份。对应：[Runtime](../01-总体架构/01-CampusClaw多Agent运行时/README.md) · [执行与控制](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 执行所属的 Session 标识 |
| execution_id | VARCHAR(128) | 否 | — | 只在服务内部使用且不向调用方公开的固定执行标识 |
| root_event_id | VARCHAR(128) | 否 | — | 原始 user.message 的公共 eventId，续跑与终态始终引用该值 |
| state | VARCHAR(16) | 否 | — | 执行控制状态：RUNNING、CONFIRMING、STOPPING 或 TERMINAL |
| current_segment_id | VARCHAR(128) | 否 | — | 当前初始执行段或确认续跑段的内部标识 |
| pending_tool_call_id | TEXT | 是 | — | 当前唯一等待确认的原始 Tool Call 标识，不限制提供商长度 |
| pending_plan_event_id | VARCHAR(128) | 是 | — | 当前计划审核等待的 agent.plan 公共事件标识；工具权限等待时为空 |
| pending_question_event_id | VARCHAR(128) | 是 | — | 当前等待回答的 agent.question 公共事件标识；其他等待类型时为空 |
| stop_event_id | VARCHAR(128) | 是 | — | 已经提交的 user.interrupt 公共 eventId；没有停止请求时为空 |
| terminal_event_id | VARCHAR(128) | 是 | — | 实际执行结束时唯一 session.status_idle 的公共 eventId |
| terminal_reason | VARCHAR(16) | 是 | — | 实际执行结束原因：done、failed 或 terminated |
| created_at | TIMESTAMPTZ(3) | 否 | — | 根执行接受并持久化的时间 |
| updated_at | TIMESTAMPTZ(3) | 否 | — | 执行控制状态最后更新时间 |
| terminal_at | TIMESTAMPTZ(3) | 是 | — | 实际执行终态提交时间；未结束时为空 |

主键：`(session_id, execution_id)`。

| 索引 | 规则 |
|---|---|
| idx_t_session_executions_root | 唯一 `(session_id, root_event_id)` |
| idx_t_session_executions_active | 唯一 `(session_id) WHERE state <> 'TERMINAL'` |
| idx_t_session_executions_state | `(session_id, state, updated_at)` |

数据库约束（保持 M1 的精确条件）：

- `CONSTRAINT ck_t_session_executions_state CHECK (state IN ('RUNNING', 'CONFIRMING', 'STOPPING', 'TERMINAL'))`
- `CONSTRAINT ck_t_session_executions_terminal CHECK ((state = 'TERMINAL') = (terminal_event_id IS NOT NULL AND terminal_reason IS NOT NULL AND terminal_at IS NOT NULL))`
- `CONSTRAINT ck_t_session_executions_pending_interaction CHECK ( NOT (pending_plan_event_id IS NOT NULL AND pending_question_event_id IS NOT NULL) AND (state <> 'CONFIRMING' OR pending_tool_call_id IS NOT NULL) AND (pending_plan_event_id IS NULL OR (state = 'CONFIRMING' AND pending_tool_call_id IS NOT NULL)) AND (pending_question_event_id IS NULL OR (state = 'CONFIRMING' AND pending_tool_call_id IS NOT NULL)) AND (pending_tool_call_id IS NULL OR state IN ('CONFIRMING', 'STOPPING')) )`
- `CONSTRAINT fk_t_session_executions_pending_question FOREIGN KEY (session_id, pending_question_event_id) REFERENCES t_session_events (session_id, event_id)`

<a id="t_session_execution_segments"></a>

### 4.10 t_session_execution_segments

执行结果段表，每次初始消息或确认续跑固定一个段。对应：[Runtime](../01-总体架构/01-CampusClaw多Agent运行时/README.md) · [执行与控制](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 结果段所属的 Session 标识 |
| execution_id | VARCHAR(128) | 否 | — | 结果段所属的固定根执行标识 |
| segment_id | VARCHAR(128) | 否 | — | 结果轮询与本地等待登记使用的固定段标识 |
| segment_ordinal | INTEGER | 否 | — | 同一根执行中的段序号，从 1 开始递增 |
| trigger_event_id | VARCHAR(128) | 否 | — | 启动该段的 user.message 或 user.tool_confirmation 公共 eventId |
| trigger_event_seq | BIGINT | 否 | — | 启动事件的 Session 内部已提交顺序号 |
| state | VARCHAR(16) | 否 | — | 结果段状态：OPEN 或 CLOSED |
| terminal_event_id | VARCHAR(128) | 是 | — | 结束该 HTTP 结果段的 session.status_idle 公共 eventId |
| terminal_event_seq | BIGINT | 是 | — | 结束事件的 Session 内部已提交顺序号 |
| terminal_reason | VARCHAR(16) | 是 | — | 结果段结束原因，包含 confirming 或实际执行终态原因 |
| created_at | TIMESTAMPTZ(3) | 否 | — | 结果段创建时间 |
| updated_at | TIMESTAMPTZ(3) | 否 | — | 结果段状态最后更新时间 |

主键：`(session_id, execution_id, segment_id)`。

| 索引 | 规则 |
|---|---|
| idx_t_session_execution_segments_ordinal | 唯一 `(session_id, execution_id, segment_ordinal)` |
| idx_t_session_execution_segments_trigger | 唯一 `(session_id, trigger_event_id)` |

数据库约束（保持 M1 的精确条件）：

- `CONSTRAINT ck_t_session_execution_segments_state CHECK (state IN ('OPEN', 'CLOSED'))`
- `CONSTRAINT ck_t_session_execution_segments_terminal CHECK ((state = 'CLOSED') = (terminal_event_id IS NOT NULL AND terminal_event_seq IS NOT NULL AND terminal_reason IS NOT NULL))`
- `CONSTRAINT ck_t_session_execution_segments_sequence CHECK (segment_ordinal > 0 AND trigger_event_seq > 0 AND (terminal_event_seq IS NULL OR terminal_event_seq >= trigger_event_seq))`

<a id="t_session_execution_segment_events"></a>

### 4.11 t_session_execution_segment_events

执行段与已提交公共事件的内部关联表。对应：[Runtime](../01-总体架构/01-CampusClaw多Agent运行时/README.md) · [执行与控制](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 公共事件所属的 Session 标识 |
| execution_id | VARCHAR(128) | 否 | — | 公共事件所属的固定根执行标识 |
| segment_id | VARCHAR(128) | 否 | — | 公共事件所属的固定结果段标识 |
| event_id | VARCHAR(128) | 否 | — | 已提交公共事件的 eventId |
| event_seq | BIGINT | 否 | — | 已提交公共事件的 Session 内部顺序号 |

主键：`(session_id, event_id)`。

| 索引 | 规则 |
|---|---|
| idx_t_session_execution_segment_events_seq | 唯一 `(session_id, execution_id, segment_id, event_seq)` |

数据库约束（保持 M1 的精确条件）：

- `CONSTRAINT ck_t_session_execution_segment_events_seq CHECK (event_seq > 0)`

<a id="t_session_tool_confirmations"></a>

### 4.12 t_session_tool_confirmations

工具确认决定表，由原执行实例至多消费一次。对应：[Runtime](../01-总体架构/01-CampusClaw多Agent运行时/README.md) · [执行与控制](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 确认决定所属的 Session 标识 |
| execution_id | VARCHAR(128) | 否 | — | 确认决定所属的固定根执行标识 |
| confirmation_event_id | VARCHAR(128) | 否 | — | user.tool_confirmation 的公共 eventId |
| previous_segment_id | VARCHAR(128) | 否 | — | 进入确认等待时已经关闭的结果段标识 |
| segment_id | VARCHAR(128) | 否 | — | 本次确认续跑使用的新结果段标识 |
| tool_call_id | TEXT | 否 | — | 原始 Tool Call 标识，不限制提供商长度 |
| result | VARCHAR(8) | 否 | — | 确认决定：allow 或 deny |
| deny_message | TEXT | 是 | — | 拒绝决定携带的可选用户说明；允许决定时为空 |
| state | VARCHAR(16) | 否 | — | 一次消费状态：PENDING 待领取、CLAIMED 已领取、COMPLETED 已处理、CANCELED 因根执行结束而取消消费 |
| created_at | TIMESTAMPTZ(3) | 否 | — | 确认决定与回执提交的时间 |
| claimed_at | TIMESTAMPTZ(3) | 是 | — | 原执行实例取得决定的时间 |
| completed_at | TIMESTAMPTZ(3) | 是 | — | 决定处理完成或因根执行结束而取消消费的时间 |

主键：`(session_id, confirmation_event_id)`。

| 索引 | 规则 |
|---|---|
| idx_t_session_tool_confirmations_segment | 唯一 `(session_id, execution_id, segment_id)` |
| idx_t_session_tool_confirmations_pending | `(session_id, execution_id, state, created_at)` |

数据库约束（保持 M1 的精确条件）：

- `CONSTRAINT ck_t_session_tool_confirmations_result CHECK (result IN ('allow', 'deny'))`
- `CONSTRAINT ck_t_session_tool_confirmations_state CHECK (state IN ('PENDING', 'CLAIMED', 'COMPLETED', 'CANCELED'))`
- `CONSTRAINT ck_t_session_tool_confirmations_message CHECK (result = 'deny' OR deny_message IS NULL)`
- `CONSTRAINT ck_t_session_tool_confirmations_claim CHECK ((state = 'PENDING' AND claimed_at IS NULL AND completed_at IS NULL) OR (state = 'CLAIMED' AND claimed_at IS NOT NULL AND completed_at IS NULL) OR (state = 'COMPLETED' AND claimed_at IS NOT NULL AND completed_at IS NOT NULL) OR (state = 'CANCELED' AND claimed_at IS NULL AND completed_at IS NOT NULL))`

<a id="t_session_plan_confirmations"></a>

### 4.13 t_session_plan_confirmations

计划审核决定表，由原执行实例至多消费一次。对应：[计划审核](../01-总体架构/06-CampusClaw计划模式/README.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 审核决定所属的 Session 标识 |
| execution_id | VARCHAR(128) | 否 | — | 审核决定所属的固定根执行标识 |
| confirmation_event_id | VARCHAR(128) | 否 | — | user.plan_confirmation 的公共 eventId |
| target_event_id | VARCHAR(128) | 否 | — | 被审核 agent.plan 的公共 eventId |
| previous_segment_id | VARCHAR(128) | 否 | — | 进入审核等待时已经关闭的结果段标识 |
| segment_id | VARCHAR(128) | 否 | — | 本次审核续跑使用的新结果段标识 |
| tool_call_id | TEXT | 否 | — | 产生被审核计划的 ExitPlanMode 调用标识 |
| result | VARCHAR(8) | 否 | — | 审核决定：approve 或 revise |
| feedback | TEXT | 是 | — | 退回修改时携带的可选用户意见 |
| state | VARCHAR(16) | 否 | — | 一次消费状态：PENDING 待领取、CLAIMED 已领取、COMPLETED 已处理、CANCELED 因根执行结束而取消消费 |
| created_at | TIMESTAMPTZ(3) | 否 | — | 审核决定与回执提交的时间 |
| claimed_at | TIMESTAMPTZ(3) | 是 | — | 原执行实例取得决定的时间 |
| completed_at | TIMESTAMPTZ(3) | 是 | — | 决定处理完成或因根执行结束而取消消费的时间 |

主键：`(session_id, confirmation_event_id)`。

| 索引 | 规则 |
|---|---|
| idx_t_session_plan_confirmations_target | 唯一 `(session_id, target_event_id)` |
| idx_t_session_plan_confirmations_segment | 唯一 `(session_id, execution_id, segment_id)` |
| idx_t_session_plan_confirmations_pending | `(session_id, execution_id, state, created_at)` |

数据库约束（保持 M1 的精确条件）：

- `CONSTRAINT ck_t_session_plan_confirmations_result CHECK (result IN ('approve', 'revise'))`
- `CONSTRAINT ck_t_session_plan_confirmations_state CHECK (state IN ('PENDING', 'CLAIMED', 'COMPLETED', 'CANCELED'))`
- `CONSTRAINT ck_t_session_plan_confirmations_feedback CHECK (result = 'revise' OR feedback IS NULL)`
- `CONSTRAINT ck_t_session_plan_confirmations_claim CHECK ((state = 'PENDING' AND claimed_at IS NULL AND completed_at IS NULL) OR (state = 'CLAIMED' AND claimed_at IS NOT NULL AND completed_at IS NULL) OR (state = 'COMPLETED' AND claimed_at IS NOT NULL AND completed_at IS NOT NULL) OR (state = 'CANCELED' AND claimed_at IS NULL AND completed_at IS NOT NULL))`

<a id="t_session_question_answers"></a>

### 4.14 t_session_question_answers

用户问题答案交接表，只引用已提交回执，由原执行实例至多消费一次。对应：[结构化提问](../01-总体架构/06-CampusClaw计划模式/ask-user-question.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 答案所属的 Session 标识 |
| execution_id | VARCHAR(128) | 否 | — | 答案所属的固定根执行标识 |
| answer_event_id | VARCHAR(128) | 否 | — | 已提交 user.question_answer 的公共 eventId |
| target_event_id | VARCHAR(128) | 否 | — | 被回答 agent.question 的公共 eventId |
| previous_segment_id | VARCHAR(128) | 否 | — | 进入问题等待时已经关闭的结果段标识 |
| segment_id | VARCHAR(128) | 否 | — | 本次答案续跑使用的新结果段标识 |
| tool_call_id | TEXT | 否 | — | 产生被回答问题的 AskUserQuestion 调用标识 |
| state | VARCHAR(16) | 否 | — | 一次消费状态：PENDING 待领取、CLAIMED 已领取、COMPLETED 已处理、CANCELED 因根执行结束而取消消费 |
| created_at | TIMESTAMPTZ(3) | 否 | — | 答案回执提交的时间 |
| claimed_at | TIMESTAMPTZ(3) | 是 | — | 原执行实例取得答案的时间 |
| completed_at | TIMESTAMPTZ(3) | 是 | — | 答案处理完成或因根执行结束而取消消费的时间 |

主键：`(session_id, answer_event_id)`。

| 索引 | 规则 |
|---|---|
| idx_t_session_question_answers_target | 唯一 `(session_id, target_event_id)` |
| idx_t_session_question_answers_segment | 唯一 `(session_id, execution_id, segment_id)` |
| idx_t_session_question_answers_pending | `(session_id, execution_id, state, created_at)` |

数据库约束（保持 M1 的精确条件）：

- `CONSTRAINT fk_t_session_question_answers_execution FOREIGN KEY (session_id, execution_id) REFERENCES t_session_executions (session_id, execution_id)`
- `CONSTRAINT fk_t_session_question_answers_answer_event FOREIGN KEY (session_id, answer_event_id) REFERENCES t_session_events (session_id, event_id)`
- `CONSTRAINT fk_t_session_question_answers_target_event FOREIGN KEY (session_id, target_event_id) REFERENCES t_session_events (session_id, event_id)`
- `CONSTRAINT fk_t_session_question_answers_previous_segment FOREIGN KEY (session_id, execution_id, previous_segment_id) REFERENCES t_session_execution_segments (session_id, execution_id, segment_id)`
- `CONSTRAINT fk_t_session_question_answers_segment FOREIGN KEY (session_id, execution_id, segment_id) REFERENCES t_session_execution_segments (session_id, execution_id, segment_id)`
- `CONSTRAINT ck_t_session_question_answers_state CHECK (state IN ('PENDING', 'CLAIMED', 'COMPLETED', 'CANCELED'))`
- `CONSTRAINT ck_t_session_question_answers_claim CHECK ((state = 'PENDING' AND claimed_at IS NULL AND completed_at IS NULL) OR (state = 'CLAIMED' AND claimed_at IS NOT NULL AND completed_at IS NULL) OR (state = 'COMPLETED' AND claimed_at IS NOT NULL AND completed_at IS NOT NULL) OR (state = 'CANCELED' AND claimed_at IS NULL AND completed_at IS NOT NULL))`

<a id="t_session_tombstone"></a>

### 4.15 t_session_tombstone

会话永久删除墓碑表，只保留不可复用的会话标识和删除时间。对应：[Session 生命周期](01-会话记忆GaussDB/README.md#65-删除-session)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 已删除且永不复用的会话 ID |
| deleted_at | TIMESTAMPTZ(3) | 否 | — | 会话完成逻辑删除的时间 |

主键：`(session_id)`。

<a id="t_session_cleanup_task"></a>

### 4.16 t_session_cleanup_task

会话逻辑删除后用于异步物理清理的短期可重试任务表。对应：[Session 生命周期](01-会话记忆GaussDB/README.md#65-删除-session)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| session_id | VARCHAR(128) | 否 | — | 需要清理 Runtime 数据的会话 ID |
| state | VARCHAR(16) | 否 | — | 清理任务状态：PENDING、RUNNING 或 RETRY |
| attempt_count | INTEGER | 否 | — | 已经执行清理的次数 |
| created_at | TIMESTAMPTZ(3) | 否 | — | 清理任务创建时间 |
| updated_at | TIMESTAMPTZ(3) | 否 | — | 清理任务状态最后更新时间 |
| next_attempt_at | TIMESTAMPTZ(3) | 是 | — | 失败后允许再次执行的最早时间 |
| last_error | VARCHAR(512) | 是 | — | 最近一次清理失败的脱敏摘要 |

主键：`(session_id)`。

| 索引 | 规则 |
|---|---|
| idx_t_session_cleanup_due | `(state, next_attempt_at, updated_at, created_at)` |

数据库约束（保持 M1 的精确条件）：

- `CONSTRAINT ck_t_session_cleanup_state CHECK (state IN ('PENDING', 'RUNNING', 'RETRY'))`
- `CONSTRAINT ck_t_session_cleanup_attempt CHECK (attempt_count >= 0)`

<a id="t_skill_usage"></a>

### 4.17 t_skill_usage

每次 Skill 工具成功返回正文的调用事实；同一次调用重复投递不更新来源或时间。对应：[Skill 统计](../04-命令与技能/03-Skill加载统计/README.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| owner_id | VARCHAR(128) | 否 | — | Runtime 家族使用 Session ID，Cron 家族使用实际 Agent 与 Job 组合标识 |
| execution_id | VARCHAR(128) | 否 | — | 宿主真实执行标识；Child 使用已保存的父 Agent 工具调用事件标识 |
| parent_execution_id | VARCHAR(128) | 是 | — | Child 的直接父执行标识；根执行为空 |
| session_id | VARCHAR(128) | 是 | — | Runtime 家族的 Session ID；Cron 家族为空，用于删除和迟到写入准入 |
| root_execution_id | VARCHAR(128) | 否 | — | Runtime 根执行 ID 或 Cron runId；父子共享关联，各次工具调用独立计数 |
| source_event_id | VARCHAR(128) | 否 | — | 本次 Skill 工具调用的持久化来源事件标识；不使用提供商原始调用 ID |
| agent_id | VARCHAR(64) | 否 | — | Agent 标识 |
| skill_id | VARCHAR(64) | 否 | — | 可信 Skill 标识 |
| skill_version | TEXT | 否 | — | 实际 Skill 版本 |
| entry_point | VARCHAR(16) | 否 | — | RUNTIME / CRON / CHILD_AGENT 来源 |
| content_sha256 | CHAR(64) | 否 | — | 当前实现的正文 SHA-256 |
| signal_type | VARCHAR(16) | 否 | — | 当前固定 SKILL |
| loaded_at | TIMESTAMPTZ(3) | 否 | — | 工具成功结束时固定的 UTC 毫秒时间，不随数据库等待改变 |

主键：`(owner_id, execution_id, source_event_id, skill_id)`，约束名 `pk_skill_usage`。

| 索引 | 规则 |
|---|---|
| idx_skill_usage_skill_time | `(skill_id, loaded_at)` |
| idx_skill_usage_session | `(session_id)` |

数据库约束（保持 M1 的精确条件）：

- `CONSTRAINT ck_skill_usage_agent CHECK (agent_id ~ '^agent-[0-9a-fA-F]{32}$')`
- `CONSTRAINT ck_skill_usage_skill CHECK (skill_id ~ '^skill-[0-9a-fA-F]{32}$')`
- `CONSTRAINT ck_skill_usage_version CHECK (skill_version ~ '[^[:space:]]')`
- `CONSTRAINT ck_skill_usage_entry CHECK (entry_point IN ('RUNTIME', 'CRON', 'CHILD_AGENT'))`
- `CONSTRAINT ck_skill_usage_signal CHECK (signal_type = 'SKILL')`
- `CONSTRAINT ck_skill_usage_hash CHECK (content_sha256 ~ '^[0-9a-f]{64}$')`
- `CONSTRAINT ck_skill_usage_runtime CHECK (entry_point <> 'RUNTIME' OR session_id IS NOT NULL)`
- `CONSTRAINT ck_skill_usage_child CHECK (entry_point <> 'CHILD_AGENT' OR parent_execution_id IS NOT NULL)`

目标边界：主线及 PR #332 仍有此独立事实表；统一结果目标改为复用 tool.result，切换与删除条件见 §6.3。本文列出现有结构不表示重新采纳独立统计流水。

<a id="t_skill_usage_stats"></a>

### 4.18 t_skill_usage_stats

Skill 工具成功调用累计次数；删除执行事实不减计数。对应：[Skill 统计](../04-命令与技能/03-Skill加载统计/README.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| skill_id | VARCHAR(64) | 否 | — | 可信 Skill 标识 |
| activation_count | BIGINT | 否 | — | 成功调用累计次数 |
| last_loaded_at | TIMESTAMPTZ(3) | 否 | — | 已累计调用的最大结果时间 |
| pruned_from | TIMESTAMPTZ(3) | 是 | — | 已清理事实的最早时间；与 pruned_to 共同保护精确范围查询 |
| pruned_to | TIMESTAMPTZ(3) | 是 | — | 已清理事实的最晚时间；跨越清理区间的查询返回不可用 |

主键：`(skill_id)`。

数据库约束（保持 M1 的精确条件）：

- `activation_count CHECK (activation_count > 0)`

目标边界：当前毫秒结构与目标秒级累计投影分别记录；目标字段约束和唯一写入来源见 §6.3。

<a id="t_skill_usage_daily_stats"></a>

### 4.19 t_skill_usage_daily_stats

按 Asia/Shanghai 自然日归属的工具成功调用汇总，与事实及累计同事务提交。对应：[Skill 统计](../04-命令与技能/03-Skill加载统计/README.md)。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| stat_date | DATE | 否 | — | Asia/Shanghai 自然日 |
| skill_id | VARCHAR(64) | 否 | — | 可信 Skill 标识 |
| activation_count | BIGINT | 否 | — | 成功调用累计次数 |
| last_loaded_at | TIMESTAMPTZ(3) | 否 | — | 已累计调用的最大结果时间 |

主键：`(stat_date, skill_id)`。

数据库约束（保持 M1 的精确条件）：

- `activation_count CHECK (activation_count > 0)`

目标边界：当前实现仍写日表；精确区间与日表需求待核实，不能因统一计数目标而直接删除现有表或接口。

<a id="schedule"></a>

## 5. 定时任务表

定时任务只新增 `t_schedule` 与 `t_schedule_run` 两张表，不修改 §4 的 Session 与根执行表，不计入 §4 的主线表数。下文表格只列目标结构；PR #332 中需要撤销或改名的列、表和索引集中在 [§5.5](#schedule-pr-diff)。身份字段遵守 §3.1：用户、范围和 Session 归属由 Mate 维护，Claw 不保存。

### 5.1 表职责与关联

| 表 | 权威职责 | 关联及生命周期 |
|---|---|---|
| `t_schedule` | 当前任务配置与自动计划游标 | 一条配置对应多条 Run；删除时与其 Run 同事务删除 |
| `t_schedule_run` | 一次触发是否受理、受理时的 Session 与根执行身份，以及同任务唯一未结束 Run | `schedule_id` 外键指向配置并级联删除；`session_id`、`execution_id` 为逻辑引用，不设外键 |
| `t_sessions`、`t_session_executions` | 已受理会话与根执行，结构不变 | 不受 Schedule/Run 删除级联；用户在定时会话中继续对话不改变原 Run 的关联 |

一次受理对应一个 Session 和一个根执行，由同库事务与锁内检查维持，不靠唯一约束或外键。同任务不并发由 `t_schedule_run` 的部分唯一索引表达，`t_schedule` 不保存指向 Run 的列，避免与级联删除形成循环依赖。

不新增 gap 表、请求去重表、扫描协调表、可恢复的墓碑或隐藏归档。停机期间错过的计划只推进游标；任务忙时跳过会形成一条已结束且未受理的 Run。不同手动请求各自分配 runId，内容相同也不合并。

<a id="t_schedule"></a>

### 5.2 t_schedule：任务配置

各列没有数据库 DEFAULT，由应用赋值。表名统一 `t_` 小写蛇形，SQL 对象注释使用中文。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| id | VARCHAR(41) | 否 | — | `schedule-` 加 32 位 UUID 十六进制 |
| agent_id | VARCHAR(38) | 否 | — | 任务绑定的 Agent 标识；每次运行按它新建 Session，修改后只影响之后的运行 |
| name | VARCHAR(256) | 否 | — | 任务名称 |
| description | VARCHAR(2048) | 是 | — | 任务描述 |
| prompt | TEXT | 否 | — | 纯文本任务内容，受理时作为首条用户消息提交 |
| cron_expression | TEXT | 是 | — | Spring 六字段表达式；仅手动运行的任务为空 |
| timezone | TEXT | 是 | — | 与 Cron 成对保存的时区，缺省值由服务归一化 |
| status | VARCHAR(16) | 否 | — | `active` / `paused` |
| paused_reason | VARCHAR(16) | 是 | — | 当前暂停原因：手动暂停，另预留错误暂停；取值与转换见[配置契约](../01-总体架构/08-CampusClaw定时任务/configuration.md#schedule-type-paused-reason) |
| metadata | TEXT | 否 | — | 附加元数据 JSON 对象，无值时写 `{}` |
| last_run_at | TIMESTAMPTZ(0) | 是 | — | 最近一次自动运行的受理时刻，在受理事务中写数据库当前时间；手动、准备失败和忙跳过不更新 |
| upcoming_run_at | TIMESTAMPTZ(0) | 是 | — | 下一次自动运行的计划时刻，即扫描游标；到期领取后推进；仅手动、暂停或规则无后续时刻时为空 |
| created_at | TIMESTAMPTZ(0) | 否 | — | 创建时间 |
| updated_at | TIMESTAMPTZ(0) | 否 | — | 配置更新时间；写 last_run_at 不改它 |

主键：`id`。

| 索引 | 规则 | 支持的访问 |
|---|---|---|
| idx_schedule_due | `(status, upcoming_run_at, id)` | 各副本每秒扫描 active 且到期的任务 |
| idx_schedule_list | `(updated_at DESC, id)` | 按更新时间返回全部任务，由 Mate 分批拉取后按用户过滤 |

数据库约束：

- status 只能是 `active` / `paused`。
- active 时 paused_reason 为空，paused 时非空。
- cron_expression 与 timezone 同空或同非空。

暂停原因的具体枚举、Cron 可解析性、JSON 结构与引用资格由应用校验。资源 `type` 是响应常量，不落库；`upcomingRunsAt` 由保存的规则计算，不存多个未来时刻。JSON 以 TEXT 保存，不新增 JSON 查询或索引。

<a id="t_schedule_run"></a>

### 5.3 t_schedule_run：一次触发记录

各列没有数据库 DEFAULT。Run 只记录是否受理，不代表园区业务成功；业务状态和错误从原 Session 与根执行读取。

| 字段 | SQL 类型 | 可空 | 数据库默认值 | 含义 |
|---|---|---|---|---|
| id | VARCHAR(36) | 否 | — | `run-` 加 32 位 UUID 十六进制 |
| schedule_id | VARCHAR(41) | 否 | — | 所属任务；外键 `ON DELETE CASCADE` |
| agent_id | VARCHAR(38) | 否 | — | 领取时任务绑定的 Agent；受理时与任务当前值不同则不受理 |
| trigger_type | VARCHAR(16) | 否 | — | `manual` / `schedule`，投影为 triggerContext.type |
| scheduled_at | TIMESTAMPTZ(0) | 是 | — | 自动触发的计划时刻（UTC）；手动为空 |
| error_type | VARCHAR(64) | 是 | — | 未受理原因，投影为 error.type；error.message 按请求语言生成，不落库 |
| session_id | VARCHAR(40) | 是 | — | 受理时创建的 Session |
| execution_id | VARCHAR(64) | 是 | — | 本次首消息的根执行，内部对账用，不公开 |
| lease_until | TIMESTAMPTZ(3) | 否 | — | 受理准备期限，内部使用。领取时写入：手动为领取时刻加 10 秒；自动取该值与 scheduled_at 加 5 秒中较早者。受理和清理都在行锁内与数据库当前时间比较，过期未受理的 Run 不得受理 |
| created_at | TIMESTAMPTZ(0) | 否 | — | 创建时间 |
| finished_at | TIMESTAMPTZ(0) | 是 | — | 结束时间，不公开；为空表示仍占用任务 |

主键：`id`。外键：`schedule_id → t_schedule(id) ON DELETE CASCADE`。

| 索引 | 规则 | 支持的访问 |
|---|---|---|
| 自动触发唯一 | 唯一 `(schedule_id, scheduled_at)` | 同一计划时刻只领取一次；UTC 区分夏令时重复钟面 |
| uk_schedule_run_unfinished | 唯一 `(schedule_id) WHERE finished_at IS NULL` | 同一任务至多一条未结束 Run，即不并发 |
| idx_schedule_run_list | `(schedule_id, created_at DESC, id DESC)` | 按任务或时间倒序查询 Run，from/to 走同一索引 |
| idx_schedule_run_retention | `(finished_at, id)` | 批量删除超过保留期的已结束 Run |
| uk_schedule_run_execution | 唯一 `(execution_id)`，空值不参与 | 根执行终态提交时按 execution_id 结束本次 Run；一个根执行至多对应一条 Run |

数据库约束：

- manual 的 scheduled_at 为空，schedule 的 scheduled_at 非空。
- session_id 与 error_type 不能同时非空；准备中两者都空。

**阶段由列推出，不保存状态列。**

| 阶段 | finished_at | session_id | error_type | 占用任务 |
|---|---|---|---|---|
| 准备中 | 空 | 空 | 空 | 是 |
| 已受理，执行中或结果未知 | 空 | 非空 | 空 | 是 |
| 已受理，根执行已结束 | 非空 | 非空 | 空 | 否 |
| 未受理（准备失败、过期、任务忙） | 非空 | 空 | 非空 | 否 |

忙跳过在插入时即带 finished_at，不占用任务。受理后由原实例在进程内直接启动；之后任何时刻失联都按结果未知处理，Run 保持未结束，自动恢复见[待定 T9](../01-总体架构/08-CampusClaw定时任务/README.md#todo-t9)。

公开接口（[Run 查询](../01-总体架构/08-CampusClaw定时任务/configuration.md#411-run-查询与删除后的历史待实现)）只返回 session_id 与 error_type 恰好一个非空的记录，投影 id、schedule_id、agent_id、trigger_type、scheduled_at、session_id、error_type、created_at。列表可按 scheduleId、triggerType、hasError 与 createdAt 区间 `[from, to)` 筛选，按 `created_at DESC, id DESC` 页码分页；triggerType、hasError 只有两个值，不单独建索引。

单独删除 Session 不清空 Run.session_id，不级联删除 Run，也不把已受理改成失败；原会话链接可能返回 404。

<a id="transactions"></a>

### 5.4 事务、删除与保留

| 操作 | 同一事务内维持的不变量 |
|---|---|
| 创建、修改、暂停、恢复任务 | 最新配置、状态与暂停原因、游标一起提交，不保存配置版本；暂停不结束在途 Run；远端授权准备在锁外，锁内复查 |
| 领取 Run | 锁 Schedule；任务无未结束 Run 时插入未结束 Run，有则插入带 finished_at 的忙跳过 Run；自动触发同时推进游标 |
| 受理 | 锁 Schedule 与 Run，复查任务存在且 active、任务 agent_id 等于 Run.agent_id、Run 未结束且 lease_until 未过、授权有效；首消息用锁内读到的最新 prompt；Session、首消息、根执行、Run 关联与自动运行的 last_run_at 一起提交 |
| 受理后启动 | 原实例在进程内启动，不写启动权；模型与业务执行不在受理事务内 |
| 根执行终态提交 | Runtime 写根执行终态的同一事务内，按 execution_id 条件更新本次 Run 的 finished_at，释放任务；Run 已删除时更新 0 行；只看本次根执行，会话后续聊天不改写；终态写不进（结果未知）不释放，见 T9 |
| 清理过期准备 | 锁 Run，只对 session_id、error_type 都为空且 lease_until 已过的 Run 写 finished_at 与错误 |
| 保留期清理 | 按 `(finished_at, id)` 批量删除超期的已结束 Run，不级联 Session，不删除未结束 Run |
| 删除任务 | 锁 Schedule，同事务删除 Run 与 Schedule；受理先提交则保留 Session，删除先提交则拒绝旧准备结果；外键级联作兜底 |

删除不取消、不回滚已发生的园区业务；已受理会话由自身权限与停止入口管理。删除后的回调只条件更新仍存在的记录，影响行数为零时不重新插入。

Run 保留 30 天；清理频率与批量见[部署初始值](../01-总体架构/08-CampusClaw定时任务/README.md#deployment-defaults)。Session 的保留策略归其自身模块。

定时业务时间遵守[统一秒级规则](../01-总体架构/01-CampusClaw多Agent运行时/time-contract.md)；内部的 lease_until 保留毫秒。定时器、线程、本地缓存与本地计时都不是权威状态，不能覆盖数据库游标、Run 关联或根执行。

<a id="schedule-pr-diff"></a>
<a id="t_schedule_dispatch_state"></a>

### 5.5 PR #332 差异

PR #332 已实现定时任务表，未合入 main。下表列出它与 §5.2–§5.4 目标结构的全部差异，实施时按此修改 PR，不以 PR 结构为准。

| 对象 | PR #332 | 目标 | 原因 |
|---|---|---|---|
| t_schedule.scope_ref、operator_ref | 保存管理范围与操作者 | 撤销 | 范围、操作者与审计在 Mate |
| t_schedule.session_owner_ref | 保存会话归属 | 撤销 | Session 归属在 Mate |
| t_schedule.credential_ids | 保存凭据引用 | 撤销 | 运行时统一使用 Mate 账号的 access-token，不落库 |
| t_schedule.message | 单条 user.message 的 JSON | 改为 `prompt` TEXT | 只保存纯文本任务内容 |
| t_schedule.revision、t_schedule_run.revision | 配置版本，受理时比较 | 撤销 | 受理改为锁内比较 agent_id |
| t_schedule.active_run_id | 指向在途 Run，实现同任务占用 | 撤销 | 改用 `uk_schedule_run_unfinished` |
| t_schedule.next_fire_at | 自动计划游标 | 改名 `upcoming_run_at` | 与接口字段一致 |
| t_schedule_run.scope_ref | Run 范围 | 撤销 | 同 Schedule |
| t_schedule_run.state | PREPARING / READY / STARTING / FINISHED | 撤销 | 阶段由 finished_at、session_id、error_type 推出 |
| t_schedule_run.claim_owner、claim_epoch | 领取实例与代次 | 撤销 | 锁内检查 lease_until 已足以阻止失效准备者受理 |
| t_schedule_run.root_event_id、segment_id | 首消息事件与初始段 | 撤销 | 可由 `t_session_executions` 与初始段按 execution_id 查到 |
| t_schedule_dispatch_state | 单行表：领跑者、代次、租约、恢复边界 | 撤销整表 | 各副本以 `FOR UPDATE SKIP LOCKED` 并行扫描，锁内复查游标；超过 5 秒的计划直接推进，见[不补跑](../01-总体架构/08-CampusClaw定时任务/README.md#no-catch-up)；GaussDB 不支持 SKIP LOCKED 时退回 FOR UPDATE |
| t_sessions.scope_ref、session_owner_ref | 会话范围与归属 | 撤销 | 归属在 Mate，按 sessionId 维护 |
| t_session_executions.started_at | 实际开始时刻 | 撤销 | last_run_at 改为受理时刻 |
| t_session_executions.execution_context_json | 编码 scheduleId、runId、agentId、范围、归属、授权、凭据 | 撤销 | 调度上下文只在原实例内存中传给 Runtime 与子 Agent；反查用 Run.execution_id |
| t_session_executions.schedule_start_state、owner、deadline 及 idx_t_session_executions_schedule_start | 一次性启动权：READY→STARTING，过期置 FENCED | 撤销 | 只在受理的原实例上执行；失联按结果未知处理，代价是该窄窗口不能自动释放任务，见 T9 |
| idx_schedule_scope_list | `(scope_ref, updated_at DESC, id)` | 改为 `idx_schedule_list(updated_at DESC, id)` | 去掉 scope 前缀 |
| idx_schedule_run_list | `(scope_ref, created_at DESC, id DESC)` | 改为 `(schedule_id, created_at DESC, id DESC)` | 按任务查询 |
| idx_schedule_run_retention | `(state, finished_at, id)` | 改为 `(finished_at, id)` | state 已撤销 |
| uk_schedule_run_unfinished | 无 | 新增 | 同任务不并发 |
| uk_schedule_run_execution | 无 | 新增 | 终态提交时按 execution_id 结束 Run |

<a id="gaps"></a>

### 5.6 实现差距与验收

| 项目 | 状态与边界 |
|---|---|
| PR 结构差异 | **待修改**：按 §5.5 修改 DDL、Mapper、受理与扫描逻辑，JSON 编解码相应简化 |
| 安全配置快照、Agent 发布版本 | 原主设计包含这些目标，PR 与目标表都没有对应列。**待设计**，本文不为此擅自增列；Run.agent_id 只用于受理比较 |
| 标识长度 | Run.session_id 为 40、execution_id 为 64，既有根表对应列为 128；跨入口 ID 上限须核验，不能默认已对齐 |
| GaussDB 能力 | **未验收**：NULL 参与唯一约束、部分唯一索引、SKIP LOCKED、时间函数与锁竞争须在真实 GaussDB 上验证；PR 报告的 PostgreSQL 验证不能替代 |
| 查询性能 | 首版由 Mate 拉取全部任务或 Run 后过滤，全量读取耗时须联调并查看 GaussDB 执行计划；索引存在不等于查询已使用它 |
| 存量升级 | S1 是会 DROP 并重建的全量安装脚本，不是升级方案；存量迁移不在首版范围 |

实施至少验证：同一自动计划并发只受理一次、手动与自动互斥、更新/暂停/删除与受理竞争、事务中途失败全回滚、重复内部通知不创建第二个 Session、受理后失联保持未知且不释放任务、删除任务后根执行仍可收尾、删除 Session 后 Run 保留受理事实、历史清理不删除会话。真实 GaussDB 执行计划、两副本故障注入和企业身份联调分别记录，文档校验不能替代。

<a id="source-baseline"></a>

### 5.7 定时源码证据

所有实现路径均属于 `pi-mono-java`，链接固定到 PR #332 head；§5.5 中 PR 一列的字段长度、可空性和索引以 S1 为证据。

| 编号 | 仓库相对路径与关键符号 | 证明范围 |
|---|---|---|
| S1 | [modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql](https://github.com/superheromeZzh/pi-mono-java/blob/e9d31e8888a81b7fe95071e705482bb16fa10476/modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql#L616)；`t_schedule`、`t_schedule_run`、`t_schedule_dispatch_state`，以及 `t_sessions`、`t_session_executions` | 三张新表、既有表扩展、CHECK、外键与索引；是新环境完整安装脚本 |
| S2 | [modules/coding-agent-cli/src/main/resources/mapper/schedule/ScheduleMapper.xml](https://github.com/superheromeZzh/pi-mono-java/blob/e9d31e8888a81b7fe95071e705482bb16fa10476/modules/coding-agent-cli/src/main/resources/mapper/schedule/ScheduleMapper.xml)；`lockSchedule`、`lockDispatchState`、`updateRun`、`releaseActiveRun`、`listRuns`、`deleteExpiredRuns` | 行锁、领取身份条件更新、查询与清理；`now` 使用数据库 `clock_timestamp()` |
| S3 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/schedule/application/ScheduleApplicationService.java](https://github.com/superheromeZzh/pi-mono-java/blob/e9d31e8888a81b7fe95071e705482bb16fa10476/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/schedule/application/ScheduleApplicationService.java)；`createLocked`、`update`、`delete`、`pause`、`unpause` | 配额协调、最新行合并、配置及 Run 同事务删除 |
| S4 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/schedule/dispatch/ScheduleRunCoordinator.java](https://github.com/superheromeZzh/pi-mono-java/blob/e9d31e8888a81b7fe95071e705482bb16fa10476/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/schedule/dispatch/ScheduleRunCoordinator.java)；`claim`、`accept`、`requireAcceptance`、`reconcilePersisted` | 领取、事务外准备、事务内复查与原根执行对账 |
| S5 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/schedule/ScheduledRuntimeAdmissionService.java](https://github.com/superheromeZzh/pi-mono-java/blob/e9d31e8888a81b7fe95071e705482bb16fa10476/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/schedule/ScheduledRuntimeAdmissionService.java)；`accept`、`start`、`recoverExpiredStarts`、`encodeContext` | 同事务创建会话、提交后启动、配置删除后的独立收尾与最小上下文 |
| S6 | [modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeExecutionControlMapper.xml](https://github.com/superheromeZzh/pi-mono-java/blob/e9d31e8888a81b7fe95071e705482bb16fa10476/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeExecutionControlMapper.xml#L26)；`saveExecutionContext`、`claimScheduledStart`、`fenceExpiredScheduledStart` | 数据库启动期限、READY→STARTING / FENCED 的条件更新 |

JSON 编码和省略值另核对 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/schedule/application/ScheduleJsonCodec.java` 的 `write/metadata/credentials` 与同目录 `ScheduleConfigurationMerger.java` 的 `merge/message/metadata/credentials`；同一 PR head。临时上下文清理检索范围为 `modules/coding-agent-cli/src/main` 中上述扩展列的写入及 Mapper 更新。

<a id="pending-changes"></a>

## 6. 已有目标中的结构增量

本节承接已存在的设计增量，不借数据库文档整理新增业务行为。main 和 PR #332 未包含下列统一历史结构，实施状态为**待实现**；具体接口、执行流程与待决项仍由关联模块维护。

<a id="tool-result"></a>

### 6.1 工具最终结果关联

[统一执行历史](../01-总体架构/01-CampusClaw多Agent运行时/unified-event-persistence.md)要求同一次真实调用的最终结果只能首次提交一次，统计复用该结果。现有目标 SQL 片段为 [unified-event-persistence.sql](01-会话记忆GaussDB/unified-event-persistence.sql)，不能直接当成生产升级脚本。

| 对象 | 已有目标定义 | 状态 |
|---|---|---|
| t_session_entries.tool_call_entry_id | VARCHAR(128)，可空；仅 tool.result 必填，其余类型为空 | 待实现；main/PR 的通用 Entry 表目前均为 §4 所列 7 列 |
| idx_session_tool_result_once | UNIQUE(session_id, tool_call_entry_id) | 待实现；NULL 唯一行为须在实际 GaussDB 验证 |
| ck_session_tool_result_ref | type='tool.result' 与引用非空对应；其他类型引用为空 | 待实现；引用的调用存在、属于相同执行且工具绑定一致由事务检查 |
| tool.result.payload | 既有 tool_call_id/tool_name/content/is_error；受控增加 schema_version、execution_id、origin=LIVE/COPY 和 Skill 专属 skill_id | 待实现；不增加公共 HTTP 字段，不把任意 details 原样落库 |

服务端调用身份与 Provider toolCallId 分开；普通结果重试复用固定结果 ID、时间与载荷，已有内容不同则拒绝，不覆盖、不重复累计。origin 和可信 Skill 身份由写入端生成，不接受客户端或模型自报。以上是现有目标片段的归属登记，不表示新列已经加入实现 DDL；结构调整须同步本文、关联 SQL 和恢复消费者。

<a id="child-links"></a>

### 6.2 t_session_execution_links：父子执行关联

目标用途是关联一次父 Agent 工具调用与独立子会话首执行；不复用 t_sessions.parent_session_id 的历史复制含义。流程、授权与取消归[统一执行历史](../01-总体架构/01-CampusClaw多Agent运行时/unified-event-persistence.md#4-child-的身份授权与生命周期)。

| 字段 | SQL 类型 | 可空 | 用途 |
|---|---|---|---|
| child_session_id | VARCHAR(128) | 否，主键 | 本次委派创建的子会话 |
| child_execution_id | VARCHAR(128) | 否 | 子会话首执行，后续聊天不能替换 |
| parent_session_id | VARCHAR(128) | 否 | 发出调用的父会话 |
| parent_execution_id | VARCHAR(128) | 否 | 固定父执行，用于受理与定向取消 |
| parent_tool_call_entry_id | VARCHAR(128) | 否 | 服务端父调用身份，同次委派复用 |
| created_at | TIMESTAMPTZ(0) | 否 | 关联创建的 UTC 秒级时间 |

无数据库 DEFAULT。`UNIQUE(parent_session_id,parent_tool_call_entry_id)` 保证同次父调用至多一条关系；`CHECK(parent_session_id <> child_session_id)` 禁止直接自关联；`idx_session_child_parent_execution(parent_session_id,parent_execution_id)` 用于按父执行查找。更深的循环与深度约束由受理流程校验。

不设父子 Session 级联删除，不存正文或秘密。父子独立保留，关系只在两端历史均可清理且实际执行已收尾后删除；任何后续受理仍须证明原父资源和调用存在，不能因关联已清理而重建旧 Child。字段及约束来自同一[待实现 SQL](01-会话记忆GaussDB/unified-event-persistence.sql)。

<a id="skill-target"></a>

### 6.3 Skill 累计投影目标

[M05](../04-命令与技能/03-Skill加载统计/README.md)已将计数来源收敛为新 LIVE、最终成功、具有可信 Skill 身份的 tool.result；在结果首次插入的同一事务内累计，不另造统计事实流。§4 的 t_skill_usage 和日表仍是当前实现，不能在新链路验收前直接删除。

目标 t_skill_usage_stats 字段如下，由 [schema.sql](../04-命令与技能/03-Skill加载统计/schema.sql)提供待实现片段；普通读取不到一行可由查询投影为零，不预建 activation_count=0 的行。

| 字段 | SQL 类型 | 可空 | 约束与含义 |
|---|---|---|---|
| skill_id | VARCHAR(64) | 否，主键 | 匹配 `^skill-[0-9a-fA-F]{32}$`，来自可信结果 |
| activation_count | BIGINT | 否 | >0，已提交真实成功调用累计，Session 删除不扣减 |
| last_loaded_at | TIMESTAMPTZ(0) | 否 | 已累计成功结果的最大形成时间 |
| pruned_from | TIMESTAMPTZ(0) | 是 | 已删除成功历史的最早时间 |
| pruned_to | TIMESTAMPTZ(0) | 是 | 已删除成功历史的最晚时间 |

无数据库 DEFAULT。pruned_from/pruned_to 要么都为空，要么都非空且起点不晚于终点。该范围是保守历史缺口，不是日汇总；区间 COUNT 与缺口相交时不能声称完整。累计表不设置 Session 级联外键。追加与清理在同一生命周期权威下排序，恢复、复制、重复提交和公共事件读取均不重复计数。

精确 from/to 与日表需求仍待核实；既有接口去留不由本文件代替用户决定。[record-usage.sql](../04-命令与技能/03-Skill加载统计/record-usage.sql)是目标事务写入片段，真实 GaussDB UPSERT 与热点锁等待未验收。若已存在部署数据，切换前还须核对旧口径和实际保留范围，不能把不同口径累计直接混算。

<a id="agent-user-events"></a>

### 6.4 按 Agent 查询用户事件的索引

[Agent 用户事件查询](../01-总体架构/01-CampusClaw多Agent运行时/agent-user-events-design.md)需要按 Agent 和时间范围跨会话读取 user.* 事件。目标在 t_session_events 冗余保存会话固定的 agent_id 并建部分索引；状态**待实现**，DDL 未冻结。

| 对象 | 目标定义 | 状态 |
|---|---|---|
| t_session_events.agent_id | VARCHAR(64) NOT NULL；追加事务从已锁定的 t_sessions 行取得，写入后不变 | 待实现；面向新建环境，不含存量回填 |
| idx_t_session_events_agent_user_time | `(agent_id, created_at, session_id, event_seq) WHERE type IN 五种 user.*` | 待实现；GaussDB 部分索引支持与执行计划未验证，不支持时去掉 WHERE |

查询必须连接 t_sessions：删除事务立即删除会话行，事件行由清理任务稍后删除，连接保证已删除会话不再返回。该列不是用户归属，不参与授权判断（§3.1）。

<a id="lifecycle"></a>

## 7. 跨表事务与生命周期

| 场景 | 数据库边界 | 对应规则 |
|---|---|---|
| 创建与追加 Session | Session、共享序号、Entry、Record、公共事件/投影与适用 Usage 在所属事务提交；先检查固定执行和生命周期，再按既定顺序锁 Session/序号 | [Session 写入](01-会话记忆GaussDB/README.md#6-事务与并发协议)；M2 已有表访问，完整业务事务以 Repository 为准 |
| 用户消息、确认、停止 | 根执行、结果段、触发/终止事件关联及决定交接一起维持固定执行身份；一个 Session 只允许一个非 TERMINAL 根执行 | [执行控制](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md)；§4 列出实际约束，不能仅凭索引证明所有竞争已验收 |
| 公共历史与恢复 | Entry 与安全事件各自按序号读；投影记录保存期望数量，零表示显式私有；缺失/数量不符失败，不返回伪造空历史 | [ListEvents](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md)；M2 的非递归实现已核验 |
| Session 删除 | 当前主线先写不可复用 ID 墓碑与清理任务，记录已清理 Skill 事实范围；关联数据按依赖清理，不假设所有表都有 Session 外键或级联 | [Session 生命周期](01-会话记忆GaussDB/README.md#65-删除-session)；M2 的墓碑/任务/清理 DML 已核验，后台清理重试不是重跑园区业务 |
| 调度受理与删除 | Schedule/Run 与 Session/根执行同库受理；删 Schedule/Run 保留已受理 Session；晚到回调不复活资源 | [调度数据库事务](#transactions)；S 增量 |
| Child 受理与删除 | 父调用关系与子 Session/首消息/根执行同事务；双方独立授权与保留，未知不能冒充终态 | [父子关系](#child-links)；D 增量 |
| Skill 统计与清理 | 当前主线用独立事实及累计/日表；目标改为完整结果与累计同事务，删除登记历史缺口但不扣累计 | [目标及切换](#skill-target)；两条写入路径不可同时累计同一指标 |

内部 Entry、公共事件、根执行和各类统计不能互相冒充权威：公共安全投影不足以重建全部模型上下文，Run 受理成功不表示业务成功，Session 汇总不是另一份 Skill 事实。备份与恢复必须覆盖当前启用方案涉及的事件、关系、累计和缺口的同一一致点。

<a id="sql-files"></a>

## 8. SQL 文件、部署与验收

| 文件 | 维护边界与状态 |
|---|---|
| 实现仓 session_schema.sql（M1 / S1） | 完整新环境安装脚本，含 DROP 重建；分别固定 main/PR 版本，不是保留存量数据的升级脚本 |
| 实现仓 session_initial_data.sql / session_privileges.sql | 初始化及应用角色权限与同版本完整表清单配套；运行身份只需相应 DML，不让服务启动自动建表 |
| 实现仓 campusclaw/scripts/install/initdb_gaussdbv5.sql | 公司安装镜像由同步脚本生成；不能单独手工修改并与 canonical DDL 脱节；本次未验收公司安装 |
| [Session 基础 schema.sql](01-会话记忆GaussDB/schema.sql) | 历史四表基础示意，只有 17 个字段；保留关联供理解与历史核对，不是全库定义或部署入口 |
| [统一历史增量 SQL](01-会话记忆GaussDB/unified-event-persistence.sql) | §6.1/§6.2 的待实现片段，需随目标核对后合入完整安装结构 |
| [Skill 目标 schema.sql](../04-命令与技能/03-Skill加载统计/schema.sql) / [写入片段](../04-命令与技能/03-Skill加载统计/record-usage.sql) | §6.3 的待实现结构与 DML，不授权直接删除主线流水或日表 |
| [Mate Agent schema.sql](02-Agent元数据GaussDB/schema.sql) | 外部元数据数据库的独立设计材料，不加入 Claw 安装脚本 |

库表整理不新增 Maven 依赖、数据库插件、RLS、跨库事务或部署迁移。继续使用项目既有 Spring/MyBatis/JDBC；表中的 VARCHAR 长度、时间精度和 JSON 类型不是容量承诺，索引是否满足真实查询须按 GaussDB 执行计划验证。

验收分三层：文档检查覆盖全表/全列、类型可空性、约束索引与链接；实现检查覆盖 Mapper 消费、原子提交与错误处理；数据库和企业部署另验收 NULL 唯一性、外键清理顺序、部分索引、UPSERT、行锁竞争、恢复与权限。本文只完成源码和文档核对，不声称真实 GaussDB、多副本及企业身份联调通过。

物理快照核对覆盖 main 的 19 表 155 列、PR 新增 3 表 45 列及其类型与可空性；这些计数保留 PR 现状证据，不表示被撤销的身份列仍属目标。职责修正已检查受影响 Markdown 的本地文件链接、相关 Mapper XML、接口页面生成同步及 git diff --check。仓库图源检查为 37 专题、136 图块、0 错误；M10 五张图已重新生成并在原尺寸及文档宽度检查，图索引同步。受理图三个分支分别表示授权、归属登记和 Runtime 准备失败，保留原因见主设计；既有压缩图提示不受本次修改影响。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.15.0 | 2026-10-14 | t_schedule.agent_id 说明改为“任务绑定的 Agent 标识”，写明用途与修改影响。 |
| 1.14.0 | 2026-10-14 | Run 在根执行终态的同一事务内结束：新增 uk_schedule_run_execution，事务表“根终态对账”改为“根执行终态提交”。 |
| 1.13.0 | 2026-10-13 | §5.5 credential_ids 撤销原因改为统一账号。 |
| 1.12.0 | 2026-10-13 | 定时执行改为统一账号：目标 t_schedule 删除 authorization_ref 列（PR #332 无此列，不进 §5.5 差异表）；运行时 access-token 不落库。 |
| 1.11.0 | 2026-10-13 | §5 改为只列目标结构：两张表按字段、主键、索引、约束分开展示，Run 阶段改为表格；PR #332 待撤销或改名的列、表与索引集中到 §5.5 差异表；执行规则链接改指主设计。 |
| 1.10.0 | 2026-10-13 | 首版列表由 Mate 拉取全部后自行过滤：Claw 不接收获准集合，恢复 idx_schedule_list(updated_at DESC, id)；Claw 加 userId 列为待定 T10。 |
| 1.9.2 | 2026-10-13 | 任务列表不建 idx_schedule_list：由 Mate 按用户过滤出获准任务 ID 集合，Claw 不保存 userId。 |
| 1.9.1 | 2026-10-13 | §5.6 补充 last_run_at 随受理提交、过期准备与保留期清理行。 |
| 1.9.0 | 2026-10-13 | 撤销 PR 在 t_session_executions 上新增的 started_at、execution_context_json 与 schedule_start_*：受理后由原实例在进程内直接启动；lastRunAt 改为受理时刻；受理后任何时刻失联统一按结果未知处理。 |
| 1.8.0 | 2026-10-13 | 撤销 t_schedule_dispatch_state：各副本并行扫描，以 Schedule 行锁、游标推进和 occurrence 唯一约束防重；超过派发容差的计划直接推进到下一次。 |
| 1.7.1 | 2026-10-13 | 明确 lease_until 的取值与使用规则。 |
| 1.7.0 | 2026-10-13 | t_schedule_run 撤销 state、claim_owner、claim_epoch；未结束由 finished_at IS NULL 表达并用于同任务不并发约束。 |
| 1.6.0 | 2026-10-13 | t_schedule_run 按 Run 接口对齐：撤销 root_event_id、segment_id，state 收为 PREPARING/ACCEPTED/FINISHED，列表索引改为 (schedule_id, created_at DESC, id DESC) 并支持 triggerType 与时间范围筛选。 |
| 1.5.0 | 2026-10-13 | 撤销 t_schedule.revision、active_run_id 及 t_schedule_run.revision；同任务不并发改由运行表部分唯一索引 uk_schedule_run_unfinished 保证，受理比较 Agent 绑定并使用最新 prompt。 |
| 1.4.0 | 2026-10-13 | t_schedule 的下次计划时刻列 next_fire_at 改名为 upcoming_run_at，明确正常为未来时刻、允许派发容差。 |
| 1.3.0 | 2026-10-13 | 定时任务 message 改为纯文本 prompt，撤销 credential_ids，凭据改由 Mate 按 Agent 绑定决定。 |
| 1.2.0 | 2026-10-12 | 登记按 Agent 查询用户事件所需的事件表 agent_id 列与部分索引目标。 |
| 1.1.0 | 2026-10-10 | 会话归属与权限由 Mate 维护，撤销 Claw 身份副本并明确跨服务受理及失败边界。 |
| 1.0.0 | 2026-10-10 | 统一维护 Claw 全库表、字段、约束索引、PR 与目标增量，并双向关联各模块及 SQL 文件。 |
