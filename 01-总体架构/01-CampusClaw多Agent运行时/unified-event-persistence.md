# 统一执行历史与事件持久化

版本：1.7.0 · 2026-10-24 · 状态：Runtime 与 Cron 主会话持久化已实现；Subagent 独立历史、父子关联与公开隔离待实现；通用工具去重及 Skill 统计增强独立维护。

[Runtime 主设计](README.md) · [Claw 数据库设计](../../03-数据与存储/Claw数据库设计.md#pending-changes) · [源码证据](unified-event-persistence-evidence.md#shared-storage-evidence) · [定时任务](../08-CampusClaw定时任务/README.md#normal-acceptance) · [Skill 统计](../04-CampusClaw命令系统/03-Skill加载统计/README.md) · [Session 存储](../../03-数据与存储/01-会话记忆GaussDB/README.md)

## 1. 要解决的业务问题

园区巡检 Agent 汇总设备告警后调用设备诊断 Subagent。运营人员排查问题时，需要查清子任务收到什么、调用哪些工具、得到什么结果，不能只剩父会话中的一句“诊断完成”。本设计为每次委派保存独立完整历史，同时让父模型继续只接收最终报告。

正常流程是：父 Agent 的工具调用记录保存后，为本次委派新建一个独立 Session，与父调用关系一同提交。Subagent 复用现有 Runtime 保存自己的消息、工具调用、结果、压缩和终态；子结果及终态提交后，父会话保存自己的 Agent 工具摘要。两端历史按各自 sessionId 分开，不复制全文，也不共用执行对象。

失败时保留已提交历史。写入失败必须反馈 Host，不能报告可靠完成；已发业务请求但结果未知时保留未知，不伪造成功或失败，不重新执行业务来补历史。数据库回滚也不能撤销外部副作用。

“完整”指已形成的完整消息、工具结果及解释和恢复它们所需的控制、配置和压缩记录，不等于每个 token、原始网络包、凭据或尚未产生的结果。硬崩溃前未提交的内存内容仍可能丢失；历史可读不等于业务执行可自动续跑。

## 2. 当前事实、范围与参考

| 范围 | 已观察实现 | 本次设计 |
|---|---|---|
| Runtime | 个人 main `bc031ed8` 的 Coordinator 安装 Projector，Repository 同事务保存 Entry、公共事件与投影；主会话已有数据库历史 | 复用现有持久化与恢复机制，不重写通用工具协议 |
| Cron | 同一提交已由 ScheduledSessionStarter 受理并在提交后调用 Coordinator，支持新建和关联主会话 | 保持既有机制；关联目标增加主 Session 校验 |
| Subagent | 仍直接创建内存 ManagedAgentSession，返回进度和最后文本后 close | 增加独立持久 Session、六字段关系、公开隔离和子执行写入失败反馈，均待实现 |
| 独立通用目标 | 工具结果按调用唯一约束、通用 commitCall/commitResult 和 Skill 统计另有目标 | 保留于 §6 及所属专题；不作为 Subagent 留档前置，不列入本次实施和验收 |
| 外部历史基线 | pi 普通示例以 --no-session 运行；Codex/OpenCode 有各自独立历史机制 | 保留各自已记录 SHA、日期及成熟度边界；2026-10-24 未重新核验外部上游 |

2026-10-24 已重新 fetch 公共 main `e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2` 与个人 main `bc031ed8aa82dac700421163a4cce25d9f023e6b`，本次源码影响面以个人 main 为准，完整路径和符号见[证据](unified-event-persistence-evidence.md#shared-storage-evidence)。共表复用属于架构选择；独立授权、安全投影、非交互 Cron、公开隔离和不重放是产品约束。源码快照不代表部署或数据库验收。

## 3. 三种入口，一套持久化执行链

| 入口 | 特有职责 | 共同路径 |
|---|---|---|
| 用户消息 / Skill Command | 现有 HTTP 校验、授权、会话准入和回执 | 受理消息与 execution → 提交 → Coordinator → ManagedAgentSession → 既有追加 |
| Cron 自动 / 手动 Run | Schedule 互斥、配置、Mate 凭据和 Run 关联 | 同库事务受理 Session、首消息、execution/segment 与 Run；提交后启动 |
| Agent 工具启动 Subagent | 可信绑定、版本/深度/循环、模型、父取消域 | 同库事务受理子 Session、首消息、execution/segment 与父子关系；提交后一次启动 |

AgentSessionFactory 保持只装配对象、工具和 hooks，不访问数据库。Subagent 受理在短事务中组合现有原语，不能用嵌套 REQUIRES_NEW 拆开子 Session 与关系。查询 Mate、准备目录、运行模型和工具均在事务外。后台使用 RuntimeEventOutput.persistenceOnly()，只表示没有网络输出，不表示跳过持久化。

<a id="storage-options"></a>

### 3.1 存储方案比较

| 方案 | 表与复用方式 | 收益 | 代价与选择 |
|---|---|---|---|
| A 全部共表＋关系 | 子 Session 写既有主表、历史及执行表；只新增 t_session_execution_links | 复用现有追加、序号、投影、Usage、执行和恢复；不新增旧表物理列 | **选定**；公共单会话入口校验主 Session，跨会话 PAGE/COUNT 同条件排除子；关系保留承担分类责任 |
| B 只分离主表 | 新增 t_subagent_sessions，其他历史、执行表共用，并保留父子关系 | 旧入口查询 t_sessions 时自然看不到子主行 | 内部创建、读取、行锁、进入运行、推进末端、回到空闲这六类会话元数据操作须路由；MyBatisRuntimeSessionRepository 与 MyBatisRuntimeExecutionControlRepository 两处实现需适配，清理也须选对主表；不是零旧代码修改 |
| C 独立记录型 | 独立任务/执行记录表与有序消息表；父关联可随任务记录保存，共两表，若保留独立 links 则三表 | 子历史与主会话物理隔离，可按记录型任务独立保留 | 需自行维护写入、状态、序号、恢复与失败反馈，不能直接继承完整 Runtime Session 能力；不选用。复制整套十六张会话运行表是更大实现，不是独立留档的必要条件 |

A 的“改动最少”只表示当前源码改动面判断：现有主 Session 已能在没有新增去重列的情况下保存和恢复完整消息，接入子执行比拆写入路径更直接。没有实测代码行数、性能或容量数据，不把表数或粗估当交付承诺。B 的现有表没有指向 t_sessions 的外键阻止它，但内部 Repository 的硬编码访问仍必须适配。

### 3.2 全局职责与生命周期

下图覆盖三入口、运行对象、记录和公开读取边界；新增子受理、关联及隔离接线标为待实现。通用工具结果提交协议与统计的独立目标不进入这张主图。

![统一持久化职责](设计图/统一事件持久化/unified_execution_history_classes.svg)

[原尺寸](设计图/统一事件持久化/unified_execution_history_classes.svg) · [PlantUML 源码](设计图/统一事件持久化/diagram.puml#L1)

应用服务与 Repository 为单例；ManagedAgentSession、Projector 和消息上下文按执行独立；数据库资源独立保留。无新增 Maven 依赖，复用 JDK、Spring 事务、Jackson、MyBatis Starter 3.0.4 和已有驱动；不引入 MQ 或第二套数据库。

## 4. Subagent 的身份、授权与生命周期

parent_tool_call_entry_id 引用父 Session **已保存工具调用 Entry 的 id**，不是 Assistant 消息 ID，也不是 Provider toolCallId。父同一消息的多次调用各有调用 Entry；关系表保存所引用的那条记录。本设计不要求 t_session_entries 新增 tool_call_entry_id，也不新设通用 Assistant＋内容位置的重试协议。

受理前按既有工具目标顺序完成可信目标解析、参数校验和权限/必要确认。父调用记录必须已经保存；短事务复核父固定 execution、未停止、调用存在且尚未关联子任务、容量和当前授权。受理与父停止争用同一父 execution 的既有锁；事务内创建子 Session、初始 task、execution/segment 及六字段关系，失败全部回滚。

同父调用的重复内部通知按关系唯一约束读取原子任务，不再次创建或 prompt；提交结果未知时先只读核对。父端可为主 Session，也可为仍有委派额度的 Subagent。授权快照仅限本次内存执行，不能因持有父 ID 就读取子历史；Mate 当前授权和秘密边界沿用[数据库约定](../../03-数据与存储/Claw数据库设计.md#mate-ownership)。

### 4.1 一个子诊断任务如何完成

下图是已完成参数和权限检查后的实现下钻，从父工具调用进入 Host，到父收到已提交摘要；各参与者表示同一 CampusClaw 进程内的职责，不暗示父子之间的远程调用。子受理与持久化接线待实现，失败规则在 §7 维护。

![独立子会话与父侧摘要](设计图/统一事件持久化/unified_child_history.svg)

[原尺寸](设计图/统一事件持久化/unified_child_history.svg) · [PlantUML 源码](设计图/统一事件持久化/diagram.puml#L61)

子上下文只从自己的 task 开始，不继承父全文。模型、目录、可配置深度与循环限制遵循[M03](../02-CampusClaw工具系统/README.md#subagent-depth)。每级只向直接父调用回传最后非空 Assistant 文本及许可进度；关系不另存正文、结果或终态副本，不在公共工具 JSON 增加内部 ID。父子 Usage 各自累计，父摘要不重复计入子用量。

子完整结果与真实终态先提交，父 Agent ToolResult 后提交，两者不放进一个长事务。父提交失败不删除或重跑已经完成的子任务。内存对象 close 不等于数据库删除或执行终态；实际退出并保存终态后才释放对应容量。

<a id="subagent-visibility"></a>

### 4.2 公开入口隔离

分类只由关系表决定：存在 child_session_id 等于本 Session ID 的 incoming link，才是 Subagent；存在 Session 且没有 incoming link，才是主 Session。不能按是否有下级、父资源是否仍存在、执行是否结束或可变 metadata 判断。完整规则由[数据库设计](../../03-数据与存储/Claw数据库设计.md#session-kind)维护；旧锚点继续兼容，不表示新增分类列。

| 范围 | 改造方式 |
|---|---|
| get、配置、消息提交、事件/轮次读取、命令目录与执行、控制 | 公共应用入口共用主 Session 校验；写操作在所属事务和既有锁内复核。不要逐条复制同一过滤 |
| 按 Agent 查询用户请求 | listAgentEvents 与 countAgentEvents 使用相同 NOT EXISTS 子端关系条件，过滤在分页和计数前完成 |
| Cron 关联 Session | 预检、关联配置与每次受理只接受主 Session；新建仍走既有根会话路径 |
| DELETE | 子 ID 视为不可见，沿用 204，不进入实际删除与清理流程 |
| 内部追加、恢复、固定执行控制、结果读取与受控清理 | 保持主/子通用；不得给通用 find/lock/结果 SQL 全局加“仅主会话”条件 |

公开读取与控制对子 ID 返回既有 SESSION_NOT_FOUND；没有新公共子查询、续聊或 UI 展开能力。关联查询和分页不能泄漏子 ID，父流也不混入子原始事件。公开主会话校验不是对子历史的授权；内部读取仍逐资源检查 Mate 权限。

## 5. Subagent 保存哪些记录

| 既有表 | 子执行保存内容 | 本次结构改动 |
|---|---|---|
| t_sessions | 独立会话元数据、状态和末端 | 无新增物理列 |
| t_session_entries | 初始任务、完整 Assistant/调用/结果、压缩摘要与既有恢复信息 | 无新增物理列，复用现有类型和 payload |
| t_session_events / t_session_event_projection | 本 Session 安全事件和精确投影标记 | 复用既有规则；不公开不等于全部写零 |
| executions / segments / 段事件关联 | 固定执行、结果段、停止与真实终态 | 复用 |
| records / stats / sequences / materialized | 本 Session Usage、序号与汇总 | 复用，父统计口径不变 |
| t_session_execution_links | 六字段不可变父调用关系 | 唯一新增表，见[DDL](../../03-数据与存储/01-会话记忆GaussDB/unified-event-persistence.sql) |

完整 Assistant、调用记录、工具最终结果和压缩写入接入既有追加服务；子 Host 必须得到每次写入完成或失败的明确反馈。若现有监听隔离异常，接线时使用仅子入口启用的窄等待回调或等价完成结果，不能把挂上 Agent.subscribe 当作可靠记录。写入失败停止子任务推进、保留已提交记录，不发布可靠完成；压缩记录未提交时保留旧上下文，终态提交前检查历史写入完成。

该要求限定在子执行留档接线，不以统一改造主会话/Cron 所有工具、引入通用 commitCall/commitResult 或新增工具结果唯一列为前置。父工具调用记录仍须先于子受理保存；每个子最终结果及终态成功提交后才回父，父摘要保存失败按原记录对账，不用业务重放补历史。

<a id="independent-enhancements"></a>

## 6. 独立通用工具与 Skill 目标

以下保留既有独立目标，不属于本次 Subagent 实施、结构增量或验收前置。通用工具按调用去重与 Skill 统计切换应在各自专题独立设计和交付；本次不改旧表、不切换统计写入链，也不宣称它们已经实现。

### 6.1 通用工具结果可靠提交与去重

新增工具结果提交 DTO 固定 `sessionId/executionId/toolCallEntryId/resultEntryId`、最终 content/isError/errorCode、可信 skillId（仅 Skill）、origin、schemaVersion 和结果形成时间；公共投影继续采用现有字段。内部 `tool.result` 的 payload 保留 `tool_call_id/tool_name/content/is_error` 并增受控恢复元数据；对应结构见[独立通用目标](../../03-数据与存储/Claw数据库设计.md#tool-result)。`content` 是经工具规则处理后给模型的完整结果；公共结果从它安全投影。仅白名单恢复字段可保存，不把全部 `details` 原样序列化。

下面是**目标内部结果**的简化样例，不是公共 API 报文，也不代表现有数据库已具备新增字段：

```json
{
  "session_id": "child-session-01",
  "id": "result-entry-08",
  "type": "tool.result",
  "tool_call_entry_id": "call-entry-07",
  "timestamp": "2026-10-10T00:00:03Z",
  "payload": {
    "schema_version": 1,
    "execution_id": "child-execution-01",
    "origin": "LIVE",
    "tool_call_id": "provider-call-3",
    "tool_name": "Skill",
    "skill_id": "skill-0123456789abcdef0123456789abcdef",
    "content": [{"type": "text", "text": "设备诊断 Skill 的受管指引正文"}],
    "is_error": false
  }
}
```

此样例省略已有 entry_seq/parent_id；它们由追加器维护。公共投影省略 execution_id、origin、skill_id 等内部字段，并按既有 Skill 安全规则隐藏私有正文；统计从内部可信结果读取。

工具结果关联列、唯一索引与受控 payload 增量集中于[数据库目标](../../03-数据与存储/Claw数据库设计.md#tool-result)，当前待实现；事务校验被引用的同 Session 调用存在、属于固定 execution、工具身份与准备绑定一致。同次结果重试沿用固定 resultEntryId、时间和全部载荷；已有结果在执行结束后仍可授权只读对账，新追加才要求固定 owner/代次及可收尾状态。先查既有结果，内容一致返回既有提交，内容不同报一致性冲突，不能覆盖或再次计数。结果去重不依赖已删除的统计流水。

`origin=LIVE` 表示当前真实执行，`COPY` 表示会话复制的既有历史；恢复、重放读取、压缩和复制都不生成新的 LIVE 结果，也不增加统计。复制保留原事件时间与语义；按现有 M04 复制设计保留内部 Entry ID，新 session_id 隔离身份，调用关联只能引用副本内对应调用；复制走独立受控复制事务、不经过 LIVE 结果提交端口；普通持久化重试只查询原记录。调用 Entry 的现有内部名 tool.execution.started 不能作为实际执行成功或已产生副作用的证据，它可能在模型调用定稿时产生。

#### 通用工具结果提交顺序

一次设备工单调用必须依次完成：可信目标解析 → 参数校验/固定准备快照 → Host 权限或确认 → Pipeline 协调业务执行 → 后置处理形成最终结果 → 权威提交 → 回传模型/输出。校验错误保持 isError=true，字段错误和同次可信定义只给模型，不弹确认、不发业务请求、不自动猜参。失败结果也经过同一提交点，成功统计只是其中的条件投影。

场景是单个业务工具从模型请求到最终结果回传；图中 Session 表示应用级历史提交职责，其内部短事务在后文展开，非远程服务。

![工具调用与结果提交](设计图/统一事件持久化/unified_tool_commit.svg)

[原尺寸](设计图/统一事件持久化/unified_tool_commit.svg) · [PlantUML 源码](设计图/统一事件持久化/diagram.puml#L101)

关键改造是**最终结果形成后、进入模型上下文或允许下一步推进前的必达提交端口**。不能只给 Agent.subscribe 增加监听器：当前监听异常被隔离，Projector 还会捕获错误；也不能只消费 End，因为校验/prepare/before 拒绝可以直接返回错误而没有 End。内核定义通用 `ToolHistoryCommitPort`（commitCall / commitResult）。Assistant 完整消息须先提交，调用身份及其安全调用投影也必须在确认展示或业务执行前成功提交；commitCall 失败不得继续业务，不能仅依赖会吞异常的消息监听。Host 还必须等待完整消息和压缩的统一追加结果：纯文本回答也只能在完整消息提交后发布完成或终态，不能绕过检查向用户报告成功。所有正常、前置拒绝与后置处理后的最终结果都汇聚该端口，Host 提供 Runtime 实现；端口接收内核结果及本次调用句柄，由 Host 组装 ToolOutcomeCommitDTO，内核不依赖该企业 DTO、数据库或 Skill 服务。纯内存测试/库宿主可显式使用内存实现，产品三入口必须装持久实现。

提交异常在业务工具异常归一化之外传播，作为持久化故障停止推进，不改写真实 isError，不把它交给模型自动修参。并行工具各自提交自己的最终结果；一个提交失败阻止启动新的调用并请求停止同批未结束调用，已执行的副作用不承诺撤销。TurnEnd 只汇总/核对已提交结果，不再重复写入。取消前已形成最终结果应先尝试提交；尚无可靠最终结果只保存控制/未知状态，不合成 tool success。

STOP_REQUESTED 不拒绝同一原执行已在途调用的真实结果；实际终态提交前仍可按固定身份收尾，旧 owner/代次或终态之后不得写入。

短事务按固定执行身份重检和 Session 锁、共享序号分配器、Entry、公共投影/关联、Skill 累计的顺序提交；单个结果涉及至多一个 skillId。网络输出只在提交后。多结果不是等全批完成后才落一笔事务；配置组合更新等原有多 Entry 原子语义保持。

### 6.2 Skill 累计目标

直接消费统一提交的 `tool.result`，仅 `origin=LIVE && tool_name=Skill && is_error=false` 且有可信 skillId 时加一。skillId 从同次可信 Skill 绑定保存，不能从正文、路径、hash、模型参数中的 ID 或可改写 details 猜测；后置 hook 最终改成错误则不计，正文变了但最终仍成功仍计。没有可信绑定的成功 Skill 结果属于持久化不变量错误，不能静默丢计或用名字代替 ID。

保留一张累计表，是因为 Session 删除后仍要保留累计次数。若只做 COUNT(entries)，它只能回答“当前保留历史中的次数”。累计表的唯一加一时机是**新 LIVE 成功结果首次插入的同一事务**；重复提交和历史读取不进入更新。去掉专用 Observer、observationId、队列、独立统计事实表及统计所需 JSONL/执行血缘，不删除真正的执行控制与授权关系。

这会把一条累计更新带入工具历史事务：任一写失败则全部回滚并停止推进，增加锁等待和工具延迟；它不再是允许队列丢失的 best-effort 方案。该耦合换来没有第二套投递/重试/对账。热点 Skill 与数据库故障必须压测；如果将来要求统计故障完全隔离，需要另行评估持久增量投影和清理水位，不能悄悄退回易丢内存队列。详细查询、删除和切换规则由 [M05](../04-CampusClaw命令系统/03-Skill加载统计/README.md)维护。

## 7. 保留、停止与失败处理

父子独立授权和保留。删除父会话不级联子会话；子仍有 t_sessions 行时，其 incoming link **绝不能先删除**，父被删除也不改变子分类。关系清理须同时满足子 Session 已不存在、两端历史已实际删除或清理完成且原执行明确收尾；可保留仅含 ID 的占位。子删除后父摘要仍在；清理关系不使旧调用可再次受理，不删除 Agent 共享目录。查询分类不 JOIN 父 Session 的存在性。

父取消或失败按 links 的原 child_execution_id 定向停止直接 Subagent，并逐级传播。每级父提交终态前等待直接下级真实收尾；等待在事务外，不持数据库锁。stop、超时、失联不等于已结束；未知保留待对账和对应占用，不能强置 idle。已形成结果先尝试保存，不把取消当作丢弃结果或合成成功的理由。

| 阶段 | 副作用状态 | 处理方 | 系统处置 | 用户可见结果与下一步 | 不保证项 |
|---|---|---|---|---|---|
| 子受理明确回滚 | 未发生 | 子受理服务 | 子 Session、首消息、execution 与 links 一并回滚，不启动 | 父收到真实失败 | 无孤立资源，不自动重放 |
| 子受理提交结果未知 | 未知 | Host | 按原父调用关系只读核对 | 待对账 | 不因超时推断回滚，不另建任务 |
| 消息/结果/压缩保存失败 | 部分发生或未知 | 子 Host | 停止推进，保留已提交历史，不报告可靠完成 | 失败或待对账 | 不撤销外部副作用，不保证崩溃前未提交内容 |
| 子终态已提交，父摘要保存失败 | 已提交 | 父 Host | 读取原子结果与父历史核对 | 子已完成，父待核对 | 不删除或重跑子任务 |
| 取消或失联 | 部分发生或未知 | Host | 停止原固定执行，等待真实收尾 | 取消处理中或待对账 | 不把请求停止当实际终止，不自动续跑 |
| 公开请求携带子 ID | 未发生 | 公共应用服务 | 按主会话边界拒绝，DELETE 204 且不清理 | 既有不可见资源语义 | 不扩展子授权或公开续聊 |

Schedule/Run 与 Session 的既有独立保留规则不变。Skill 历史缺口和累计的独立目标由 M05 维护，不在本次 Subagent 清理中切换统计模型。备份与恢复包含会话、历史、执行和 links 的同一一致点；从已提交记录恢复读取，不自动接管或重新执行园区业务。

## 8. 实施顺序与验收

| 切片 | 实施内容 | 必须证明 |
|---|---|---|
| U1 | 复用现有受理/追加，新增六字段 links | 父调用已保存；子 Session、首消息、execution/segment 与关系原子提交；同父调用不重复建子 |
| U2 | 子执行接 Coordinator 与历史写入完成反馈 | task、Assistant、调用、结果、压缩独立保存；错误向 Host 传播，不仅订阅吞错事件；子结果及终态先于父摘要 |
| U3 | 公共主 Session 校验、跨会话查询过滤 | list/count 同条件，命令可选 sessionId 与 Cron 关联目标覆盖；子读取/控制拒绝、DELETE 204 且不删；内部子追加与结果读取正常 |
| U4 | 定向停止、容量、保留及数据库验证 | 父删子留、incoming link 不先于子主行清理；父先删除不使子成为主；未知不重放；既有锁顺序和恢复边界正确 |

实现和数据库验证仍待执行。安装设计只新增关系表，必须合入相应新环境完整安装材料；不执行生产 SQL 或存量迁移。通用工具/Skill 独立增强不列为本次通过条件。设计制品的历史验证见[验证页](unified-event-persistence-validation.md)，不能据旧记录宣称本版已验收。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.7.0 | 2026-10-24 | Subagent 复用全部会话表、仅新增父子关系，通过子端关系隔离公开入口并与通用工具和统计增强分开。 |
| 1.6.0 | 2026-10-23 | 委派深度引用服务配置权威，内部关系支持逐级委派、结果回传和定向取消，公共可见范围保持。 |
| 1.5.0 | 2026-10-23 | 增加主会话与 Subagent 的显式分类、公共入口隔离和内部授权边界，并核实既有 Runtime/Cron 持久化状态。 |
| 1.4.0 | 2026-10-15 | 定时受理服务改名为 `ScheduledSessionStarter`。 |
| 1.3.0 | 2026-10-15 | 父 Agent 通过 `Agent` 工具调用的 Agent 统一称为 Subagent。 |
| 1.2.0 | 2026-10-14 | 根执行终态提交增加事务内终态扩展点，供定时任务结束 Run。 |
| 1.1.0 | 2026-10-10 | 父子关联与工具结果结构归入 Claw 数据库设计，执行和提交流程继续独立维护。 |
| 1.0.0 | 2026-10-10 | Runtime、Cron、Child 统一保存独立完整历史，逐工具原子提交并复用成功结果维护 Skill 累计。 |
