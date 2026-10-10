# Skill 成功调用次数统计设计

[命令与技能](../README.md) · [M05 主设计](../00-Slash-Command通用模块/README.md) · [源码与差距](source-evidence.md) · [验证](validation.md)

| 属性 | 值 |
|---|---|
| 文档版本 | 4.0.0 |
| 更新日期 | 2026-10-10 |
| 业务目标 | Skill 工具最终成功一次，对应 skillId 使用次数加一；同一任务三次成功调用计三次 |
| 职责 | M05 消费已有工具事件并维护统计；M03 继续决定工具执行结果；M04/M06 不承担统计身份、来源补齐或删除准入 |
| 设计状态 | 成功调用口径由用户指定；本文给出推荐落地方案，有界异步写入和简化持久化待实现 |
| 实现状态 | #335 已实现三入口事件采集及累计查询；本文公共装配、去除追溯前提、有界写入等调整待实现，不把整项功能标为不存在 |
| Java 对照基线 | PR #335 `dad4433d38fcb4104bd8d093f844ea2afc9612ee`；base `769e86592285f4a25b0febaf551eddea6bc7212c` |
| 设计仓起点 | `da81fed06ed9e8964b0dfd0bc0ed612c5be1e543` |
| pi 事件基线 | 2026-10-10 确认默认分支并隔离 fetch：`main@42a3497d03ad17e308a2299fa824727894f2c0ec`；只核验工具生命周期与订阅，不声称 pi 提供此统计 |

## 1. 业务问题、正常处理与失败

园区设备告警处理中，Agent 成功调用“设备告警处置”Skill 两次，子 Agent 又成功调用一次，管理端看到该 skillId 新增三次使用。人工会话、定时任务或子 Agent 只影响任务如何启动，不改变计数规则。

一次调用沿已有工具 Pipeline 完成可信目标解析、参数校验、Host 权限判断及必要确认、工具执行、后置处理与结果回传。CampusClaw 的通用目标是可信绑定解析与参数校验先于交互确认；本统计不调整这些阶段。现有 Java Pipeline 在 schema 校验及 prepare 后执行 before hook，随后发 Start，执行工具、后置 hook，最后发 End。Skill 的受管文件读取由 SkillTool 完成，不经过 Mate。无效调用保持真实错误，由原工具链向模型反馈；统计不猜参、不重放。

统计观察器在 Start 时从本次可信绑定识别 skillId，在 End 且 `isError=false` 时形成一个调用计数记录。记录放入应用级有界队列后，原工具结果立即继续回传；后台独立事务插入幂等记录并原子累加总数。入队不代表已经入账，查询只返回已提交的累计值。

工具失败不计数。统计队列满、写库失败或进程退出允许漏计，诊断计数反映这些丢失，工具仍按原结果返回。本功能是运营统计，沿用已有 best-effort 边界，不承诺无损审计、计费或证明模型遵循了 Skill。

## 2. 唯一计数规则

计数对象是**当前进程真实执行、发出最终成功结束事件的受管 Skill 工具调用**。每次调用权重为一；工具名必须为框架 `Skill`，skillId 必须来自创建该 Agent 时固定的可信绑定。

- 成功以 Pipeline 发布的最终 `ToolExecutionEndEvent.isError=false` 为准，观察器不重新判定工具成功。
- 每次真正的新调用都计数；同一任务、同一 Skill、同一版本均不去重。重复投递同一个 End 不重复入队，同一统计记录重复提交不重复加数。
- 内容改写、正文为空、文件摘要变化，只要工具最终仍报告成功，就按成功调用计数。若产品认为这些是工具失败，由 SkillTool/Pipeline 的功能规则处理，不把失败规则藏进统计器。
- 取消导致没有成功 End 或 End 为错误时不计；成功 End 已发布后发生的取消、Session 结束、后续模型失败不撤销计数。不会在后台写库时再读取变化中的 CancellationToken 或执行状态。
- 仅 Read、显式 `/skill:name` 注入、SearchTools、CallTool、准备/刷新、历史读取、恢复已有消息、SSE 重连不计。显式命令之后模型真的调用 Skill，按该次工具结果计数。
- 不按 Runtime/Cron/Child、Agent、根任务、Skill 版本拆分或去重；部署管理授权保持，不能从凭据 ID 推导租户。

| 行为 | 应提交增量（假定统计可用） |
|---|---:|
| 同一任务三次成功调用 A | A +3 |
| 一次调用失败，模型修正后新调用成功 | A +1 |
| 主执行调用 A 两次，Child 调用 A 一次 | A +3 |
| 两个 Agent 的 Provider call ID 相同，各自成功调用 A | A +2 |
| 后置 hook 保留成功状态，但替换正文或 details | A +1 |
| 后置 hook 改为 `isError=true` | +0 |
| 原 End 重复投递、重复提交同一统计 DTO | 同次调用合计 +1 |
| 同一 Agent 前一次调用结束后，下一次真实调用复用 Provider ID | 新 Start/End 再计 +1 |
| 已入队的成功调用随后 Session 结束或删除 | 后台可入账，不扣减 |

## 3. 公共接入与局部状态

### 3.1 一个装配点

在 `AgentSessionFactory.create` 已得到本次 runtime 和 Agent、首次 prompt 之前，通过现有 `Agent.subscribe` 安装一份 `SkillUsageObserver`。Factory 只构造和连接观察器，不解析正文、不生成执行血缘、不访问数据库。`create(request)` 的签名、请求参数、受理和身份绑定顺序不变；不恢复 `create(request, tracker)`。

Observer 从 `PreparedAgentRuntime.skillIdsByName()` 复制只读映射，依赖应用级 `SkillUsageRecorder` 与 Clock。订阅安装失败要隔离并诊断，不能令 Session 创建失败。一个 Agent 只装一份，确认续跑和多次 prompt 不重装。观察器由 Agent 的监听器集合持有，没有外部按 Session 保存的 registry，不拥有文件、连接或线程；Agent 释放后一起释放。

Runtime、Cron、Child 已经共用此 Factory。验收须分别验证三个入口确实覆盖，但观察器不接受入口类型、Session ID、Cron runId 或父执行身份。无需新增通用事件总线、生命周期 SPI、公共 SSE 字段或 `agent-core` 的统计接口。

推荐包边界如下，不新增 Maven 模块：

| 代码归属 | 内容 |
|---|---|
| `codingagent.skill.usage` | Observer、Recorder、事务写服务；成功计数规则只在这里维护 |
| `codingagent.skill.usage.dto` / `mapper` | 内部观察/计数/查询 DTO 与 SkillLoadMapper；统计写侧不反向依赖 HTTP 包 |
| `codingagent.runtimeapi.web` / `vo` / `service` | 保留查询 Controller、请求/响应 VO 和查询 Service 的转换职责；由 Service 调用统计 Mapper |
| `codingagent.session.AgentSessionFactory` | 仅创建每 Agent 的 Observer 并订阅，不持有统计状态 |

现有 Mapper/内部 DTO 迁入统计所属包时同步 imports 与 XML namespace，公开 VO/接口名称保持。Mapper SQL 资源路径可以沿用，不为路径整齐改动无关资源；不借此搬迁其他 Runtime 持久化类型。

### 3.2 为什么仍需要一个很小的 Map

已有 Start 含 `args`，End 含 `result/isError`，End 不含 Skill 参数。为了不改公共事件和工具执行协议，Observer 在自己的私有 `ConcurrentHashMap` 中暂存：

| 键/值 | 用途 | 生存期 |
|---|---|---|
| `toolCallId` | 在同一 Agent 活动事件流中配对 Start/End | 该次调用结束即移除 |
| `skillId` | 从可信 name → id 绑定解析的统计对象 | 同上 |
| `observationId` | JDK UUID，一次 Start 只分配一次，作为统计幂等键 | 同上，成功后复制到统计 DTO |

这不是保存事件：不保存工具参数、正文、规范业务事件 ID、Session 或父子树。它位于统计消费者内部，不在 RuntimeActiveExecution，也不等待日志落盘。名字建议 `pendingSkillCalls`，不使用“Cron 家族”等不能表达职责的术语。

观察规则：

1. Skill Start：读取经过现有 Pipeline 处理的 `args.name`，精确匹配可信绑定；未命中只诊断。保存 `SkillCallObservationDTO(observationId, skillId)`。其他工具完全忽略。
2. Skill End：原子 `remove(toolCallId)`；没有匹配项不补造调用。移除成功且最终成功时，固定 UTC 毫秒 `completedAt`，提交 `SkillCallCountDTO(observationId, skillId, completedAt)`。失败 End 只清理。
3. 相同 End 的并行或重复回调只有一个能移除成功。已结束后的新 Start 可复用 Provider ID，并生成新的 observationId；不同 Agent 的 Map 隔离。
4. `AgentEndEvent` 清理没有 End 的残留调用；异常和取消路径已有 finally 发布 AgentEnd。已提交的 DTO 与 Observer 不再相互持有，不因 Agent 关闭撤销。

只消费原生 live 事件：依赖同次调用 Start 先于 End、同一 Agent 并行活动调用 ID 可区分。未结束的同 ID Start 属于无法区分重复投递与调用 ID 冲突的观测异常，应把该活动键标为不可计数并诊断，不覆盖成新的调用、不影响工具。这里不建设乱序、历史重放或跨进程事件投递协议；需要这类能力时必须重新确定稳定调用身份，不能宣称此 Map 能解决任意重放。

**observationId 是统计记录的技术键，不是 executionId、traceId 或规范业务事件 ID。** 不向模型、公共 SSE 或用户暴露，也不伪称它能够追溯到 Runtime/Cron/Child 的权威记录。

## 4. 持久化和失败隔离

### 4.1 只保留必要字段

核心模型使用两张表；[schema.sql](schema.sql)是待实现的新建环境设计片段，不是对现有数据库的删除或迁移操作。

| 表 | 字段 | 不变量 |
|---|---|---|
| `t_skill_usage` | `observation_id`、`skill_id`、`loaded_at` | observation_id 唯一；同一次记录重复提交只入账一次；loaded_at 为成功 End 的固定时间 |
| `t_skill_usage_stats` | `skill_id`、`activation_count`、`last_loaded_at` | 数据库原子加一，最近时间取 MAX；合法零值在查询时补齐 |

沿用当前累计表和 HTTP 字段名，避免把内部简化顺带变成未评估的客户端重命名；内部新类型用 call/count/observation 表达含义。`activationCount` 在此表示成功调用数，不表示根任务数。

不存 owner、execution、parent、session、root、source event、entry point、版本、摘要或固定 `signal_type=SKILL`。不与 Session 或远端 Skill 表建立外键；SQL 使用绑定参数。可信 Skill 身份不能由随机 UUID 代替。

保留幂等事实表是为了数据库防重复，并保留有时间的最小事实以等待范围查询决定；不是为了执行审计。只有累计表加一无法在提交回执不确定、同 DTO 重复送达时提供数据库级防重。它的代价是每次成功调用仍写一行；本方案不把“解耦”宣传成零存储成本。

当前统计字段仍沿用现有毫秒精度，时间在 End 固定，不在后台执行时重取。Session/公共事件/定时任务的[秒级规则](../../01-总体架构/01-CampusClaw多Agent运行时/time-contract.md)不在本任务中扩展到统计查询，精确统计时间格式随查询契约核实，不能静默改接口。

### 4.2 数据库事务

`SkillUsageTransaction.record(dto)` 是独立 Spring Bean 的事务入口，在后台工作线程调用。顺序固定为普通 INSERT 幂等事实 → 原子增加累计 → 提交；[record-usage.sql](record-usage.sql)给出 SQL。普通 INSERT 的唯一键冲突使整笔事务回滚，后面的累计更新不得执行；事务代理外只把明确 `pk_skill_usage` 冲突认作重复，其他错误记失败。不能在事务内 catch 后继续累加。

正常提交时一笔记录增加一次；并发不同调用通过数据库原子累加避免丢更新。同 observationId 的合法重复保持原时间与 skillId；不同载荷复用键属于内部缺陷，验收须覆盖且诊断，不通过更新事实纠正。Skill 元数据删除或解除绑定不追溯扣减过去已经成功的调用。

不访问 `t_sessions` 或 `t_session_executions`，不检查根 RUNNING，不获取 Session 行锁。Session 删除不删除统计事实，后台已接受的成功调用仍可入账。统计的备份、保留和治理按自身数据职责维护：没有确认保留策略前不自动清理，不能宣称有限保留的事实可以重建无限累计。未来清理幂等记录必须同时约束最大排队/重投递寿命；不添加一个未经确认的 90 天默认值。

### 4.3 应用级有界写入

推荐一个应用级 `SkillUsageRecorder`，内部使用已有 Spring/JDK 执行器：单工作线程、有界容量初值 256、拒绝策略 `AbortPolicy`。容量可配置并做正数校验；256 是初始工程参数，不是容量或性能结论。Observer 提交的任务只捕获三字段 DTO，不持有 Agent、Session、结果正文或凭据。

- 工具线程只执行关联、取时、非阻塞入队；队列满/关闭时拒绝，捕获拒绝并计入 dropped。禁止 CallerRunsPolicy，不能在过载时退回工具线程写库；不使用默认无界线程池。
- 后台每条执行一次事务。失败增加 failed 并输出受控、限流诊断，不自动重试、不重放工具。提交结果不确定不宣称一定漏计；同技术键的再次提交仍由数据库防重。
- Agent/Session 关闭不关闭共享 Recorder，也不等待队列。应用关闭先停止接受、最多等待 5 秒排空，随后丢弃未开始的任务并申请中断工作线程；中断不等于 JDBC 已终止，连接、语句和网络超时须独立配置和故障验证。5 秒是关闭等待配置，不是 DB 调用总超时承诺。
- 单工作线程最多占一个统计事务连接，复用现有 DataSource；不擅改全局连接池参数影响业务。慢库仍可能占用一个共享连接并使队列丢失，故这是工具线程等待隔离，不是与全进程资源完全隔离。统计专属连接池只有在实测需要时另行评估。
- 监控至少区分 accepted、recorded、duplicate、dropped、failed 和队列积压；不把入队数作为使用次数。按现有日志/监控设施接入，不新增遥测依赖，不记录正文、完整参数或凭据。

此处异步是明确的架构选择：避免已经核实的同步 JDBC 等待拖住工具返回。代价是查询最终一致、满队列/崩溃会漏记，增加一个进程级有界执行器。相比加 MQ、持久化任务队列或业务事件回放，它只解决这一个性能边界。

<a id="6-查询接口"></a>

## 5. 查询范围与未决项

采集口径不决定查询接口必须删什么。现有批量 POST、skillIds 校验、ResultBean、管理授权、零值和错误隔离沿用现行边界；本任务不修改 Runtime catalog、公开 JSON 模型或查询 operation ID。

| 项目 | 已观察实现 / 决策状态 |
|---|---|
| #335 查询 | 只接收 skillIds，返回 queriedAt/items；累计包含已入账历史 |
| 设计仓原查询 | 包含 from/to 精确区间及相应返回字段；见[统一接口页](../../01-总体架构/01-CampusClaw多Agent运行时/chat-api-review.html#QuerySkillLoadStatistics) |
| 是否删除 from/to 与日汇总 | 用户已要求“暂时不确定，先标为待核实”；本方案不记作批准，也不声称两边契约已一致 |
| 本方案异步影响 | 工具成功与查询可见存在延迟；queriedAt 仅为数据库查询时刻，不是所有工具事件已消费的水位 |

若保留精确 `[from,to)` 查询，可以按最小事实的 loaded_at 聚合，不需要执行树；保留范围、清理后错误、时间精度与实际消费者仍须一起验收。若需要独立日表，可作为同事务的第三投影按每次调用加一，不改变 Observer 或 Host；是否继续维护日表待核实。核心两表 SQL 不能直接替代尚未核实的完整发布材料，不在本任务执行 DROP 或现有数据迁移。

## 6. 与 Simon 当前实现的区别

以下“Simon 当前实现”专指 #335 固定 head，包含 #295/#298 遗留能力；不是将所有问题认定为 #335 新引入。

| 方面 | Simon 当前实现 | 本方案（待实现） | 理由 / 代价 |
|---|---|---|---|
| 成功口径 | 最终成功＋绑定摘要一致＋非空完整正文仍在 | 最终成功的 Skill 调用 | 直接回答调用次数，放弃“绑定正文完整交付”指标 |
| 基本事件入口 | 已消费 ToolExecutionEnd | 复用同一结束事件，Start 只用于关联 skillId | 保留正确的公共事件机制，不另造总线 |
| 安装位置 | Runtime/Cron/Child 三个 Host 分别 attach | 公共 Factory 创建 Agent 时装配一次 | 入口自然覆盖；Factory 只承担接线 |
| Factory 协议 | 当前已恢复 create(request) | 保持 create(request)，增加窄装配语句 | 不恢复 Tracker 参数或改变受理逻辑 |
| Runtime 状态 | ActiveExecution 保存规范调用 ID 映射 | 删除统计专用映射及记忆调用 | Observer 私有 Map 仅保存活动 Skill 的两项标量 |
| 子执行 | 传入父身份和来源查询函数，推导 Child 身份 | 不传统计身份、来源函数 | 子 Agent 自己的成功 Skill 调用自然被观察 |
| Cron 日志 | ManagedExecutionLog 保存所有工具开始事实，作为来源前提 | 计数不依赖或补建执行日志 | 日志故障不再额外抑制计数；执行审计另行设计 |
| 幂等身份 | owner/execution/source/skill 组合 | 单次 observationId | 保留防重，不赋予它业务执行含义 |
| 数据 | 调用事实 13 字段及累计表 | 最小事实 3 字段及累计表 | 保留数据库防重和原子累加，降低关联成本 |
| Session 生命周期 | 写入锁 Session、检查根状态；删除清事实 | 统计不读锁 Session，也不随 Session 删除 | 历史计数独立，保留政策需自己管理 |
| 失败隔离 | 同步写库、捕获异常；仍等待 DB | 应用级有界异步写入，满则丢弃 | 工具不等待 JDBC，代价是最终一致与队列生命周期 |
| Read / 命令 | 已不计数 | 保持不计数 | 不扩大采集范围 |
| HTTP / 日表 | 已删除 from/to 和日表 | 删除决定仍待核实 | 不用采集简化替代需求确认 |

旧设计确实提出过真实根、规范来源与 Session 准入，因此本方案是**产品口径收敛与架构调整**，不是只移动几个类的保行为重构。可信身份、参数校验、权限确认、普通工具日志及结果持久化属于原业务职责，不能随统计简化一并删除。

## 7. 目标结构与关键时序

下图只表达本统计模块及其接入、查询边界。已有 Agent/Pipeline 不因新设计改成待实现；标记 Pending implementation 的是统计改造或接线。类名给出推荐职责，实施可以沿用已有 Service/Mapper 名称以减少无意义重命名。

![成功调用统计目标类图](skill_load_statistics_classes.svg)

[PlantUML 源码](diagram.puml#L1) · [原尺寸 SVG](skill_load_statistics_classes.svg)

观察器每 Agent 一份，Recorder 和事务服务是应用单例；不可变 DTO 跨后台线程。Controller 只经查询 Service 到 Mapper。统计代码不反向进入 agent-core，Mapper 不访问 Session 表。图中的类型与职责映射见 §3/§4，核心依赖均对应下节实施切片。

场景是设备告警处置 Skill 已通过原工具链的解析、校验及权限阶段，从开始执行到统计提交结束；前置流程由 §1 和 M03 定义，不在此重画整个工具系统。正常返回与异步统计是独立完成边界；图为待实现方案。

![Skill 成功结束与统计提交](skill_usage_record.svg)

[PlantUML 源码](diagram.puml#L98) · [原尺寸 SVG](skill_usage_record.svg)

图中 ToolPipeline 映射现有 ToolExecutionPipeline 及 Agent 的事件分发，Tools 映射 SkillTool；Observer 映射 SkillUsageObserver，Recorder 映射进程级有界写入与独立事务服务，Database 仅为统计表。Recorder 内部执行器是实际异步边界，入队返回不代表提交成功；工具失败或投递拒绝都不会改写原工具结果。

## 8. 实施切片与验收

| 切片 | 改动范围 | 必须通过的验收 |
|---|---|---|
| S1 · 独立计数存储 | 最小 DTO、两表及事务、现有查询适配 | 同键并发只加一；不同键同 Skill 不丢更新；累计更新或提交失败事实也回滚；MAX 时间正确；无 Session SQL |
| S2 · 公共事件观察 | SkillUsageObserver、Factory 窄装配 | A 调三次计三次；错误不计；并行重复 End 一次；两个 Agent 同 callId 分别计；连续真实调用复用 callId 分别计；未知绑定不伪造 skillId |
| S3 · 有界投递 | 单例 Recorder 与配置、应用关闭 | 慢库时工具线程不执行 JDBC；满队列绝不 CallerRuns；工作线程/任务数有界；关闭不等同 JDBC 已停；记录失败不改变工具结果 |
| S4 · 移除专用侵入 | Tracker、证据、三 Host 接线、来源日志/身份的专用消费者 | Runtime/Cron/Child 都覆盖；确认续跑只订阅一次；没有规范来源、日志不可写仍计；Session 删除不抑制已完成调用；普通执行与日志语义不变 |
| S5 · 查询及发布核实 | 实际管理调用方、时间范围、日表、保留、完整安装及镜像 | pending 需求先收敛；查询最终一致可接受；不把旧根任务累计冒充新口径；公司数据库与部署验证 |

具体删除清单及源码定位见[source-evidence.md](source-evidence.md)。应删除统计专用代码，而非给其改成更宽泛名称继续保留。`ExecutionIdentity`、`ManagedExecutionLog` 和 Cron 传 run 重载在当前核验范围内服务这套追溯；实施前复查最新独立消费者，只删除统计所需链路。真实 CronRunRecord、Runtime 的 ExecutionTargetDTO、Agent 授权/深度/祖先控制及 RuntimeEventProjector 自身持久化映射保留。

新旧采集不可同时向同一累计表写入；按发布开关一次切换，验收防双订阅。统计此前是否已部署仍须核实：未部署可更新全量安装；已有数据不能把旧口径累计静默混入新指标，需另行确认历史保留或重建。本任务只交付设计，没有改产品代码或执行数据库操作。

## 9. 依赖与验收边界

不新增 Maven 直接依赖及其传递依赖；复用 JDK UUID/ConcurrentHashMap/执行器/时间、现有 Spring 事务/生命周期、MyBatis Starter 3.0.4、数据源和 SLF4J。无 MQ、OTel 或新的存储组件。若删除摘要工具类，只移除其独占代码；JDK 摘要不构成一个可删 Maven 依赖。

Java 参考实现、pi 事件证据、制品校验和待实现运行测试分开记录于[source-evidence.md](source-evidence.md)和[validation.md](validation.md)。设计图和 SQL 片段通过静态校验不表示 Java、数据库事务、故障或性能验收通过。

## 版本历史


| 版本 | 日期 | 变更 |
|---|---|---|
| 4.0.0 | 2026-10-10 | 按 Skill 最终成功调用计数，统一事件观察与有界异步入账，移除执行追溯前提并对比 #335。 |
| 3.2.1 | 2026-09-22 | 明确 SearchTools 只发现定义，不增加 Skill 使用统计信号。 |
| 3.2.0 | 2026-09-20 | 模型 Skill 成功正文读取纳入既有 READ 信号及根去重，不增加表或查询协议。 |
| 3.1.0 | 2026-09-18 | F19 对齐现有批量 POST 与 activationCount 响应，排名和趋势延后按需设计。 |
| 3.0.0 | 2026-09-16 | 按根执行统一去重 Skill 使用信号，统计独立短事务且失败不阻断主执行。 |
| 2.0.0 | 2026-09-15 | 基于 Codex 观测机制定义成功调用事实、来源幂等、三表同事务和 Runtime 统计查询。 |
| 1.1.0 | 2026-09-15 | 按设计仓职责补充 Skill 调用观测基线，明确全文加载方案的候选边界。 |
| 1.0.0 | 2026-09-15 | 定义累计与日汇总、直接排名查询、单 Skill 趋势及事务和保留边界。 |
