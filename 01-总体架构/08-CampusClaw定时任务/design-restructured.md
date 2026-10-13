# CampusClaw 定时任务设计（模板重构稿）

[模块索引](../../README.md#module-index) · [原主设计 README](README.md) · [Claw 数据库设计（定时增量）](../../03-数据与存储/Claw数据库设计.md#schedule) · [Claw 接口专题](configuration.md) · [执行专题](execution.md) · [接口 HTML 展示](schedule-api-review.html) · [源码与官方证据](source-evidence.md)

> 本文是按“评审记录 / 概述 / 整体方案 / 详细设计 / 接口协议 / 架构指标 / 质量保证 / 基建规范 / 其他补充”模板重组的草稿，设计内容与 [README 0.36.0](README.md)、[configuration.md 0.31.0](configuration.md)、[execution.md 0.6.0](execution.md) 一致，未新增或改变设计决策。原文件保持不变。标注 **【缺口】** 的位置表示现有材料不足以填写，需要补充，不应由本文推断。

| 属性 | 值 |
|---|---|
| 文档版本 | 0.36.0-restructure（结构重组稿，设计行为同 README 0.36.0） |
| 更新日期 | 2026-10-12 |
| 模块 | M10 · 调度与并发治理 |
| 设计状态 | 三张调度表、Mapper、同库受理与启动控制已在 Java PR #332 实现，尚未合并，差距见[数据库实现差距](../../03-数据与存储/Claw数据库设计.md#gaps)；Mate 授权与归属登记、调度扫描及其余新增能力待实现；main 上已观察实现仅为进程内 Cron |
| 源码基线 | Claw Java main `553dcd5e2ff682f9684810a043b442b37a02e54a`（2026-10-05 隔离 fetch）；PR #332 `e9d31e8888a81b7fe95071e705482bb16fa10476`（2026-10-10 核验，见[数据库源码基线](../../03-数据与存储/Claw数据库设计.md#source-baseline)）。均沿用原文核验，本次重组未重新读取源码，也未得出新的代码结论 |
| 主基线 | Claude Managed Agents Scheduled deployments 公开 Beta 契约，最近核对 2026-10-08；无服务端源码 |

## 评审记录

### 评审结论

评审中。评审人：Lotus；评审开始日期：2026-10-11；适用版本：0.35.0-restructure。结论待逐项评审完成后填写。

### 评审 Todo

以下是原文明确记为未决或需联调校准的事项，可作为评审 Todo 的初始清单；负责人 **【缺口】**。

| # | 事项 | 负责人 | 来源 |
|---|---|---|---|
| T1 | 运行失败是否自动暂停整个 Schedule（不能默认继承旧 Cron 连续三次失败自动禁用） | | [README §6](README.md#failure-interaction-recovery)、[配置 §4.1.1](configuration.md#schedule-type-paused-reason) |
| T2 | Mate 新增上下文查询与凭据解析接口的路径/VO 仍为内部草案，企业身份适配、凭据保管、Mate 归属登记、授权 TTL 需联调 | | [README §12](README.md#implementation-calibration) |
| T3 | 数据库链路已在 PR #332 实现但未合并，与目标设计仍有差距（含本地身份链路） | | [数据库实现差距](../../03-数据与存储/Claw数据库设计.md#gaps) |
| T4 | 原子受理、启动 fencing、取消终态与多副本故障测试须在实现阶段验证 | | [README §12](README.md#implementation-calibration) |
| T5 | 完整 Maven 依赖树与 corporate NativeParent 未核验 | | [执行专题](execution.md#module-merge) |
| T8 | Mate 管理入口在调用 Claw 前后的处理逻辑（权限、配额、任务与用户关联等）尚未确定；Claw 侧逻辑已确认 | | 本次评审 |
| T7 | Mate 获准集合传递、任务配额准入和 Session 归属登记的内部契约待实现 | | [配置 身份与权限边界](configuration.md#mate-access-boundary) |
| T6 | 每实例 8 个活动执行上限在多副本下会放大总并发，部署阶段需按实例数与下游配额核对 | | [部署初始值](execution.md#deployment-defaults) |

### 需求信息

需求来源：安全 Agent 场景四“配置空间安全管理规则”，其中视频巡逻检查规则需要按设定时刻自动执行，由定时任务承载。场景四目前没有需求文档。**【缺口】** 需求编号、优先级和目标版本。

## 1. 概述

### 1.1 术语解释

| 术语 | 含义 |
|---|---|
| Claw | CampusClaw Agent 服务，本设计的实现方 |
| Mate | 用户、组织、租户、资源归属与权限的维护方，也是可信接口定义、执行资格、Session 归属和凭据的最终决定方；运营人员通过 Mate 管理入口操作定时任务 |
| Schedule | 长期保存的任务配置：Agent 绑定、纯文本 prompt、可选 Cron 规则 |
| Run | 一次自动或手动触发的受理记录；只表示是否成功创建 Session，不表示业务成败 |
| Session | 每次 Run 新建的独立会话，承载消息、工具结果与根执行 |
| 根执行（root execution） | Session 内本次运行的顶层执行，是执行终态的最终决定方 |
| occurrence | 一个具体的自动计划时刻，以 `(schedule_id, scheduled_at)` 唯一标识 |
| 受理（acceptance） | 在同一数据库事务内创建 Session、首条消息、根执行并写入 Run 关联 |
| activeRunId | 同一 Schedule 当前占用执行槽的 Run，保证同任务仅一条活动执行 |
| claimEpoch / 扫描代次 | 领取者与扫描协调者的代次，用于 fencing 旧领取者和区分恢复边界 |
| pausedReason | 当前暂停原因，`manual` 或保留的 `error` 形状；恢复后清空 |
| Spring 六字段 Cron | 秒、分、时、日、月、星期；不接受五字段 POSIX 或年字段 |

### 1.2 需求整理

**【缺口】** 没有原始需求文档。下表是从原文“已确认”决策反推的需求清单，供评审确认是否与原始需求一致，不代表需求来源已核实。

| 编号 | 需求 | 类型 | 来源 |
|---|---|---|---|
| R1 | 运营人员可创建、查看、修改、删除定时任务配置，浏览器无需保持打开 | 功能 | README §1、§3 |
| R2 | 时间规则仅支持 Spring 六字段 Cron，timezone 省略时默认 Asia/Shanghai；可省略规则表示仅手动运行 | 功能 | 配置 §3 |
| R3 | 每次自动或手动运行新建独立 Session，复用绑定的 Agent 定义，不追加到已有会话 | 功能 | README §7 |
| R4 | 支持立即运行、暂停、取消暂停；暂停只阻止未来自动受理 | 功能 | 配置 §4.7～§4.9 |
| R5 | 用户能看到下一次计划时间、每次是否成功启动、执行结果入口和失败原因 | 功能 | README §1、配置 §3.3、§4.11 |
| R6 | 删除 Schedule 同时删除其 Run，保留已生成的 Session；删除不取消已受理执行 | 功能 | 配置 §4.6、§4.11 |
| R7 | 不补漏跑、遇忙跳过、失败与故障不重跑 | 约束 | 执行专题 |
| R8 | 首版只支持文本输入、无需人工交互的任务；ASK 结束本次根执行 | 约束 | 执行专题 noninteractive |
| R9 | 业务凭据由 Mate 按 Agent 绑定在运行时决定，Claw 不保存凭据引用或秘密 | 安全 | README §8 |
| R10 | 多副本部署下同一 occurrence 只受理一次 | 稳定性 | README §5、执行专题 |
| R11 | 用户、资源归属与权限由 Mate 维护；Claw 不保存用户范围或 owner，新 Session 受理前由 Mate 登记归属 | 安全 | README §8 |

## 2. 整体方案

### 2.1 业务用例

园区里有些 Agent 工作需要在设定时刻反复执行，例如视频巡逻检查，不能依赖有人在线发起；运营人员还要能确认每次是否执行、结果如何、失败原因是什么。定时任务让运营人员保存“时间规则 + 要完成的任务”，由服务端按时交给绑定的 Agent 执行，并保留每次运行的记录和结果入口。

| 编号 | 参与者 | 业务目标 | 业务结果 |
|---|---|---|---|
| BU1 | 园区运营人员 | 设置一个“每天 22:00 执行一次园区视频巡逻检查”的定时任务 | 任务保存并启用；能看到实际生效的时间规则和时区（未填时区时为 Asia/Shanghai）以及最多五个未来计划时刻，据此确认下一次何时运行 |
| BU2 | 园区运营人员 | 修改任务内容或时间规则 | 保存后看到更新后的规则和计划时刻；之后的运行按新配置执行，已开始的运行不受影响 |
| BU3 | 园区运营人员 | 到点自动执行视频巡逻检查，无需人工值守 | 每次到点生成一个新会话，由安全 Agent 完成本次巡逻检查 |
| BU4 | 园区运营人员 | 立即试跑一次，验证任务内容 | 立刻得到本次运行记录和会话入口 |
| BU5 | 园区运营人员 | 临时停止、之后恢复自动运行 | 暂停期间不再自动运行，恢复后从下一个计划时刻继续 |
| BU6 | 园区运营人员 | 查看已有任务、每次运行及其结果 | 看到任务列表与下一次计划时间；运行记录链接到对应会话，从会话读取巡逻结论和工具证据 |
| BU7 | 园区运营人员 | 不再需要该任务 | 任务及运行记录删除，已生成的会话保留 |

### 2.2 整体时序

场景：运营人员配置“每天 22:00 执行一次园区视频巡逻检查”，从配置任务开始，经过一次 22:00 自动运行，到查看该次巡逻结果结束。覆盖 BU1、BU3、BU6；状态：目标设计，待实现。图只画正常流程，每个阶段的内部细节见对应的详细时序。

| 参与者 | 职责 | 映射 |
|---|---|---|
| 运营人员 | 园区运营人员 | 通过 Mate 管理入口操作 |
| Mate | 管理入口；用户权限、资源归属、执行授权与凭据 | 外部服务，以可信服务调用 Claw；授权、归属与凭据的最终决定方；管理入口的内部处理待定（T8） |
| Claw | coding-agent 服务：定时任务管理、到期扫描、受理协调，以及创建 Session 并推进 Agent 与工具 | `codingagent.schedule` 与既有 Session 运行时，同一进程，见 §3.3～§3.6 |
| GaussDB | 调度与 Session 存储，调度状态的最终决定方 | 同库事务资源 |

![定时任务整体时序](scheduled_task_overview.svg)

[原尺寸 SVG](scheduled_task_overview.svg) · [PlantUML 源码](diagram.puml#L267)

| 阶段 | 详细时序 |
|---|---|
| 步骤 1～8：配置定时任务 | [§3.3 配置定时任务的详细时序](#save-sequence) |
| 步骤 9～20：运行定时任务 | [§3.5 运行定时任务的详细时序](#scheduled-run-sequence)，其中受理部分见 [§3.6 共用受理的详细时序](#run-admission-sequence) |
| 步骤 21～26：查看巡逻结果 | 无详细时序：运行记录读取为单次查询，规则见[配置 §4.11](configuration.md#schedule-run-read-lifecycle)；会话读取沿用 M06 既有接口 |

<a id="key-decisions"></a>

### 2.3 关键设计决策

CampusClaw 的基线集合为 Claude Managed Agents、Codex harness、OpenCode、pi、DeepSeek Harness（DSH）；本模块以 Claude Managed Agents 为主基线，按问题选择相关基线。在已登记快照中，pi 只有实验性进程 Job（pico3），Codex harness 只有插件计划元数据，二者都没有可直接对照“用户定时任务”的实现。基线事实均引用 [A14](../07-Agent架构对比/README.md#a14) 与[源码证据](source-evidence.md)中已登记的日期和提交，本稿未重新 fetch；Claude 为公开 Beta 契约，DSH 为 alpha，OpenCode 为 dev 分支。

| # | 要解决的问题 | 基线怎么做 | 园区业务约束 | 我们的选择 | 代价 |
|---|---|---|---|---|---|
| D1 | 怎样让用户分清“任务启动了”和“业务做完了”？ | Claude 把 Deployment（配置）、DeploymentRun（一次触发）、Session（执行内容）分开，Run 只记录 Session 创建结果；现有 CampusClaw CronEngine 是 JSON Job 加 JSONL 运行日志 | 模型自然结束不等于巡检或工单处理成功，业务结论必须来自 Session 里的输出和工具证据 | 采用三类资源分离：Schedule / Run / Session；Run 只回答“是否成功受理” | 多一层资源，看业务结果要从 Run 跳到 Session |
| D2 | 每次定时运行放进哪个会话？ | Claude 每次新建 Session；OpenCode 的 GitHub schedule 入口每次新建 Session；DSH 的提醒固定投递回创建它的原 Session；OpenAI 宿主 Scheduled tasks 支持新聊天和继续原聊天两种模式 | 同一任务每天产生独立结论，要避免与人工聊天争用同一会话；多一种目标模式就多一套绑定、忙闲和授权规则 | 每次新建独立 Session，复用绑定的 Agent 定义，不提供 target / sessionId | 不能延续聊天上下文，需要昨日结论时必须显式查询业务记录 |
| D3 | 谁决定“这次该不该跑”，多副本下如何不重复？ | Claude 未公开内部实现；OpenCode 把计时交给外部 GitHub Actions；DSH 和 pi pico3 都在单进程内计时（DSH 用串行队列处理投递与删除） | 企业部署多副本；Session 创建和首条消息必须与 Run 一起成功或一起失败，崩溃后要能对账 | GaussDB 是调度状态的最终决定方，定时器只负责唤醒扫描；同库事务内原子受理 Run、Session、首条消息和根执行 | 首版要求 Schedule、Run 与 Runtime 同库；单扫描领跑者的吞吐需要压测 |
| D4 | 进程崩溃、停机或回执丢失后，这次要不要补跑或重跑？ | Claude 公开资料未给出完整重叠与故障策略；DSH 的固定间隔只取最新到期项，不逐个补历史；pi pico3 在进程结束后按当前时间加间隔推进 | 工单、门禁、告警处置等工具有真实副作用，重复执行比漏执行更危险 | 不补漏跑、遇忙跳过、失败与故障不重跑；结果未知时保持占用并对账 | 故障时可能漏跑一次；结果未知需要对账或人工处置 |
| D5 | 用户用什么方式描述“什么时候跑”？ | Claude 只支持五字段 POSIX Cron，时区必填；DSH 支持 Cron（时区必填）、单次与固定间隔；pi pico3 只有毫秒级 notBefore/every，没有日历时区；OpenCode 用 GitHub Actions 的五字段 Cron，默认 UTC | 园区任务以“工作日 08:00”这类日历规则为主，主要在中国时区；Java 工程已有 Spring CronExpression，不希望新增依赖 | 仅支持 Spring 六字段 Cron；timezone 可省略，默认 Asia/Shanghai 并保存回显 | 不支持单次任务和严格固定间隔；Claude 表达式不能直接复制，日与星期组合语义也不同 |
| D6 | 删除任务时，运行记录、会话和在途执行怎么处理？ | Claude 采用归档；DSH 删除任务及投递历史，保留原 Session，不取消在途；辅助基线 OpenClaw 保留运行历史，操作者删除时请求取消 | 用户不想为了删任务再逐条清理运行记录；已生成的对话和园区业务结果要独立保留；取消在途执行可能留下半完成的业务操作 | 同删 Schedule 和 Run，保留 Session，不取消已受理执行，停止由 Session 入口单独发起 | 删除后无法再查启动失败和触发来源，尤其是没有生成 Session 的失败 |
| D7 | 无人值守时遇到权限确认或提问怎么办？ | 无可对照实现（已登记基线没有定时场景下的交互处理） | 定时执行时没有人在线回答；默认批准会绕过园区业务权限 | 首版只支持无需人工交互的任务；Host 遇 ASK 时阻止业务调用并结束本次根执行 | 需要人工确认的任务暂时不能定时执行 |
| D8 | 任务运行时使用 Agent 的哪个版本？ | Claude 在创建或显式更新 Deployment 时固定 Agent 版本 | 现有 Agent 目录没有可解析的历史定义，只保存一个版本号兑现不了版本固定 | 只绑定 agentId，每次使用当时已发布的定义 | Agent 发布新版本后，后续运行行为可能改变，无法复现历史运行；这是能力缺口，不是字段简化 |

逐字段的完整 Claude 对照见[配置 §7](configuration.md#claude-tradeoffs)；时间、执行目标和删除的多基线对照见 [A14](../07-Agent架构对比/README.md#a14) 和[删除基线证据](source-evidence.md#schedule-delete-baselines)。

## 3. 详细设计

<a id="system-use-cases"></a>

### 3.1 系统用例

前 10 项为 HTTP 操作，由 Mate 管理入口以可信服务调用发起（Mate 内部处理待定，见 T8）；后 3 项为后台作业。BU6 还需读取 M06 既有 Session 接口，不在本模块新增。

| 用例 | 对应业务用例 | 触发者 | 前置条件 | 主成功结果 | 关键约束 |
|---|---|---|---|---|---|
| UC1 创建配置 | BU1 | Mate 管理入口 | Mate 已授权的操作与目标 | 201 完整 Schedule，status=active | 不调用模型或 Session 工厂；未接线运行能力前不发布自动运行承诺 |
| UC2 列表 | BU6 | Mate 管理入口 | Mate 获准资源集合 | 200 分页完整资源 | 分页前按获准集合约束，空集合返回空；不换取凭据 |
| UC3 详情 | BU6 | Mate 管理入口 | 读取资格 | 200 完整资源 | Agent 或凭据失效不妨碍读取 |
| UC4 部分更新 | BU2 | Mate 管理入口 | 管理资格 | 200 完整资源 | 锁最新行合并提交字段；不触发执行、不改暂停状态 |
| UC5 删除 | BU7 | Mate 管理入口 | 管理资格 | 200 完整 Schedule 回执 | 同删 Run，保留 Session，不取消已受理执行 |
| UC6 立即运行 | BU4 | Mate 管理入口 | 运行资格；active 或 paused | 200 Run（sessionId 与 error 二选一） | 先预留共用任务槽，再走共用受理；不移动计划游标 |
| UC7 暂停 | BU5 | Mate 管理入口 | 管理资格 | 200 完整 Schedule，paused/manual | 同值操作不改时间与游标 |
| UC8 取消暂停 | BU5 | Mate 管理入口 | 管理资格、执行资格 | 200 完整 Schedule，active/null | 只从未来匹配继续，不补跑 |
| UC9 Run 列表 | BU6 | Mate 管理入口 | Mate 获准资源集合 | 200 runs/nextPage | 分页前按获准集合约束；不含已删除任务的 Run |
| UC10 Run 详情 | BU6 | Mate 管理入口 | 读取资格 | 200 八字段 Run | 任务或 Run 已删除时 404 |
| UC11 自动扫描与受理 | BU3 | 调度器 | 持有扫描租约 | 新 Session 受理并启动 | 不补漏跑、遇忙跳过；受理前须完成 Mate 归属登记 |
| UC12 结果对账 | BU3 | 调度器 | 已受理 Run | 投影摘要并释放 activeRunId | 已删除任务只收尾 Session，不复活资源 |
| UC13 运行超时停止 | BU3 | 调度器 | 单次运行超过 30 分钟 | 向原根执行请求停止 | 停止未确认前保持停止中或未知 |

### 3.2 数据模型

表结构、约束、索引与数据库事务由 [Claw 数据库设计（定时增量）](../../03-数据与存储/Claw数据库设计.md#schedule)唯一维护，本文不再维护另一份表模型。范围是三张调度表 `t_schedule`、`t_schedule_run`、`t_schedule_dispatch_state`，以及既有 Session/根执行表的扩展。Java PR #332 已实现这些表、Mapper、同库受理与启动控制，尚未合并；与目标设计的差距见[实现差距](../../03-数据与存储/Claw数据库设计.md#gaps)。

业务生命周期：Schedule 保存长期配置，Run 保存一次受理事实，Session 与原根执行保存实际执行结果。删除 Schedule 同时删除 Run，保留已受理的 Session 且不自动取消；单独删除 Session 不改写历史 Run 的受理事实。数据库关联与竞争顺序见[事务和删除约束](../../03-数据与存储/Claw数据库设计.md#transactions)。Claw 只保存资源关联、凭据引用和不透明 authorizationRef，不保存用户范围、owner 或操作者副本，见[Mate 归属边界](../../03-数据与存储/Claw数据库设计.md#mate-ownership)。

全局目标类图（分层、依赖与生命周期）：

![定时任务全局目标类图](scheduled_task_architecture.svg)

[原尺寸 SVG](scheduled_task_architecture.svg) · [PlantUML 源码](diagram.puml#L45)

| 层次 | 责任 |
|---|---|
| 边界与入口 | `ScheduleController` 收发 RequestVO/ResponseVO；`CronToolAdapter` 传入 Host 已绑定的 Session/执行和目标资源 |
| 绑定解析 | `ScheduleBindingResolver` 只读检查 Agent 绑定；MateAdapter 从 Mate 取得可信定义、执行授权、Session 归属登记与凭据 |
| 应用编排 | `ScheduleApplicationService` 管理规则与 VO/DTO 转换；`ScheduleRunPreparation` 与受理服务承接共享入口；`ScheduleDispatcher` 推进已受理执行 |
| 策略与准备 | `ScheduleTimePolicy` 统一校验与计划计算；`ScheduleAuthorizationPort` 调用 Mate 的授权与归属登记，不是 Claw 的用户权限策略；`PreparedScheduleRunDTO` 每次准备的不可变快照 |
| 持久化 | `ScheduleRepository` 委托 `ScheduleMapper`，只收发 DTO |
| Runtime 适配 | `ScheduledRunAcceptanceService` 在同库短事务中受理；`RuntimeExecutionCoordinator` 事务后启动、投影与关闭 |

<a id="save-sequence"></a>

### 3.3 配置定时任务的详细时序（UC1、UC4）

展开整体时序的“配置定时任务”阶段。场景：保存视频巡逻检查任务，从调用 Claw 到返回持久化结果。状态：待实现。

![Claw 配置保存](schedule_configuration_save.svg)

[原尺寸 SVG](schedule_configuration_save.svg) · [PlantUML 源码](diagram.puml#L151)

**正常调用如何完成：** Mate 管理入口以可信服务调用 Claw（Mate 内部处理待定，见 T8）→ Claw 核验服务来源、获准操作与目标资源，校验请求形状 → 事务外向 Mate 只读检查 Agent、凭据绑定与管理授权 → 事务内插入（创建）或锁定最新行合并提交字段（更新），校验合并结果 → 一次写入并提交 → 按已保存结果返回完整资源与计划时间摘要。

完整规则见[配置 §5](configuration.md#reliable-write-flow)。

### 3.4 立即运行的详细时序（BU4、UC6）

独立对应业务用例，不展开整体时序的阶段：它与“运行定时任务”共用受理路径，只是触发方式不同。场景：手动触发一次视频巡逻检查，从请求到返回 Run 回执。状态：待实现。

![立即运行与Run回执](schedule_manual_run.svg)

[原尺寸 SVG](schedule_manual_run.svg) · [PlantUML 源码](diagram.puml#L184)

**正常调用如何完成：** 核验 Mate 服务、获准操作和目标 → 短事务读取当前任务，预留一个手动 Run 并占用共用任务槽，不改自动计划 → 进入[共用受理流程](#run-admission-sequence) → 返回 200 和带 sessionId 的 Run，不等待业务完成。

<a id="scheduled-run-sequence"></a>

### 3.5 运行定时任务的详细时序（UC11、UC12）

展开整体时序的“运行定时任务”阶段。场景：每天 22:00 为“视频巡逻检查”创建一个新 Session，从一次到期扫描开始，到新 Session 根执行终态入库结束；前提是任务为 active 且身份策略可用。状态：目标设计，待实现。

图中调度器映射 `ScheduleDispatcher`，负责分发、启动和对账；定时任务管理映射 M10 应用服务，负责认领、准备与受理；Session 运行时映射执行协调器与公共 Session；存储是同一 GaussDB 事务边界。它们是职责映射，不表示独立进程或远程调用。“准备并受理”阶段在 [§3.6](#run-admission-sequence) 展开。

![独立会话定时运行](scheduled_run_sequence.svg)

[原尺寸 SVG](scheduled_run_sequence.svg) · [PlantUML 源码](diagram.puml#L1)

五个步骤如下（来源 [README §5](README.md#normal-acceptance)、[执行专题](execution.md)）：

1. **分配 occurrence。** 扫描器按 upcoming_run_at/id 有界、稳定扫描，不按用户或租户分组；短事务锁定 Schedule，复核未删除、active、revision、到期时间与 activeRunId；插入唯一 Run、推进游标、占用执行槽。忙时记录 `SKIPPED_OVERLAP`，不排队。
2. **可信准备与归属登记。** 事务外向 Mate 核验执行授权，解析 Agent 已发布目录、模型、CRON profile、工作区，固定 `PreparedScheduleRunDTO`；固定拟建 Session ID，由 Mate 独立登记归属并确认；不持数据库行锁调用远端。
3. **原子受理。** 同一事务复核存在性、状态/revision、领取 owner/代次与租约、授权有效期、容量与派发期限；创建 Session、首条用户消息（prompt）、根执行/segment，写 Run 关联。任一步失败整体回滚。
4. **事务后启动。** 原 Runtime 实例以 READY→STARTING 的启动 CAS 取得执行权，使用 `RuntimeEventOutput.persistenceOnly()` 保存完整事件，不伪造 SSE 连接。Runtime、Cron 与 Child 共用受理原语与执行协调器，规则见[统一执行历史](../01-CampusClaw多Agent运行时/unified-event-persistence.md)。
5. **结果对账。** 读取固定根执行的终态（以根执行为准）；Schedule/Run 仍存续时幂等更新摘要并释放 activeRunId；已删除时只收尾 Session 与根执行。

<a id="run-admission-sequence"></a>

### 3.6 共用受理的详细时序（UC6、UC11）

展开 §3.4 和 §3.5 中的“共用受理流程”。场景：一次视频巡逻检查 Run 已预留并占用自己的任务槽，从核验执行授权开始，到受理结果提交结束，不包含模型执行。自动和手动入口共用此流程；自动还检查 active 与派发期限，手动允许 paused 且不推进自动游标。状态：待实现；PR #332 已实现同库受理部分，Mate 归属登记待实现。

![共用受理流程](schedule_run_admission.svg)

[原尺寸 SVG](schedule_run_admission.svg) · [PlantUML 源码](diagram.puml#L220)

**正常调用如何完成：** 向 Mate 核验本次 Run 的执行授权并解析可信定义 → 固定拟建 Session ID，由 Mate 按资源 ID 和授权登记 Session 归属（Claw 不提供用户、租户或 owner）→ Session 运行时只准备 Agent、模型和 CRON 上下文，不执行业务 → 一个短事务内复核任务、认领、授权、时间和容量，创建 Session、首条消息、根执行并写入 Run 关联。

Mate 登记与 Claw 受理之间没有跨库事务；准备成功只固定本次上下文，最终事务仍复核可变状态。登记被拒或结果未知的处理见 [F14](#failure-recovery)，详细规则见 [Mate 会话归属](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md#session-ownership)。

### 3.7 删除任务配置的详细时序（BU7、UC5）

独立对应业务用例，不展开整体时序的阶段。**【缺口】** 删除没有独立时序图，规则分散在[配置 §4.6、§4.11](configuration.md#schedule-run-read-lifecycle)。删除与最终受理的竞态（删除先提交则不受理；受理先提交则保留 Session 并删除 Run）是本模块最容易出错的交互之一，建议补一张详细时序图。

## 4. 接口协议

基础路径 `/campusclaw-service/v1`，ResultBean 包装 `resCode/resMsg/result`，lowerCamelCase，UTC 秒级时间，不使用 If-Match、Idempotency-Key 或 ETag。字段、报文、错误码与示例的唯一维护源是 [configuration.md](configuration.md)，可读版本见 [HTML 展示](schedule-api-review.html)。

| 操作 | 方法与路径 | 成功结果 | 详细契约 |
|---|---|---|---|
| 创建配置 | POST `/schedules` | 201 完整资源及 Location | [§4.1](configuration.md#creation-response-review) |
| 列表 | GET `/schedules` | 200 分页完整资源 | [§4.4](configuration.md#list-schedules-review) |
| 详情 | GET `/schedules/{scheduleId}` | 200 完整资源 | [§4.3](configuration.md#get-schedule-review) |
| 部分更新 | POST `/schedules/{scheduleId}` | 200 完整资源 | [§4.5](configuration.md#update-schedule-review) |
| 删除配置 | DELETE `/schedules/{scheduleId}` | 200 完整 Schedule 回执 | [§4.6](configuration.md#delete-schedule-review) |
| 立即运行 | POST `/schedules/{scheduleId}/run` | 200 Run | [§4.7](configuration.md#run-schedule-review) |
| 暂停 | POST `/schedules/{scheduleId}/pause` | 200 完整 Schedule | [§4.8](configuration.md#pause-schedule-review) |
| 取消暂停 | POST `/schedules/{scheduleId}/unpause` | 200 完整 Schedule | [§4.9](configuration.md#unpause-schedule-review) |
| 运行列表 | GET `/schedule-runs` | 200 runs/nextPage | [§4.11](configuration.md#schedule-run-read-lifecycle) |
| 运行详情 | GET `/schedule-runs/{runId}` | 200 八字段 Run | [§4.11](configuration.md#schedule-run-read-lifecycle) |

Mate 侧新增的内部接口见 [Mate 定时执行接口草案](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md)。

## 5. 架构指标

### 5.1 安全性

- 用户、组织、租户、资源归属与权限由 Mate 维护并执行。Claw 不解析或保存用户、scope、owner、operator，收到 Mate 可信服务请求后只校验服务来源、具体操作和目标资源，再检查自己的输入与状态，规则见[配置 身份与权限边界](configuration.md#mate-access-boundary)。
- 列表在分页前应用 Mate 决定的获准资源集合；空集合返回空，不退化为全部，也不先取全库一页再过滤。
- 后台通过资源 ID 与不透明 authorizationRef 向 Mate 查询当前执行资格；引用不能当令牌，也不能解码出用户。授权结果缺失、过期或 Mate 不可用时不受理，不因请求来自内网放行。
- 新 Session 在受理前由 Mate 独立登记归属；登记失败或结果未知时不启动，删除 Schedule/Run 不删除该归属。
- Claw 不持久化凭据引用或 Token/JWT/APPKEY，业务凭据由 Mate 按 Agent 绑定在执行时解析；秘密只在受限执行内存中使用，不进入模型、metadata、Schedule/Run、事件或日志。
- metadata 不进入模型输入，不作为身份、权限或凭据依据。
- 资源级不可见统一返回 404，不泄露存在性。
- 已知差距：PR #332 仍有本地身份链路，见[职责核验](source-evidence.md#mate-boundary-review)；获准集合传递、配额准入与归属登记的内部契约待实现（T7）。

### 5.2 稳定性

<a id="failure-recovery"></a>

#### 5.2.1 失败处理与恢复

**不变量**（任何失败都不能破坏）：

1. 受理事务提交前不调用模型或业务工具；远端调用不持有数据库行锁。
2. 同一 Schedule 最多一条活动执行，结果未知也占用。
3. 已受理的运行不会因失败、重启或回执丢失而重建 Session、重发首条消息或重放工具。
4. 根执行是执行终态的最终决定方；Run 只表示受理结果，不表示业务成败。
5. 晚到的回调与对账不得复活已删除的 Schedule 或 Run。
6. 秘密不进入模型、Schedule/Run、事件或日志。
7. 未取得 Mate 的 Session 归属登记确认前，不受理、不启动 Session。

**失败分类**：副作用状态取“未发生 / 部分发生 / 已提交 / 未知”之一。

| # | 失败 | 发生阶段 | 副作用状态 | 处理方 | 系统处置 | 用户可见结果与下一步 | 不保证项 |
|---|---|---|---|---|---|---|---|
| F1 | 字段或规则无效（含无未来匹配的 Cron、空白 prompt） | 保存 | 未发生 | 配置服务 | 400 字段错误，不写入 | 按错误码改正后重新提交 | — |
| F2 | 身份、授权或存储等最终决定方不可用 | 保存、运行、暂停/恢复、读取 | 未发生 | 配置服务 | 503，不受理 | 稍后重试 | — |
| F3 | 保存或删除事务失败、响应丢失 | 保存、删除 | 未知（超时不证明事务失败） | 调用方核对 | 5xx；不保存请求键或原响应 | 先读取详情或列表核对，再决定是否重提 | 重复创建可能生成第二个任务；列表未找到不证明未提交 |
| F4 | 准备被拒（Agent 禁用、授权、凭据、容量、准备超时） | 受理前 | 未发生，无 Session | 调度器 | 记录 Run.error，释放执行槽，不重试 | Run 显示失败原因；手动运行仍返回 200 Run；自动任务等下一计划 | 是否因此自动暂停 Schedule 待定（T1） |
| F5 | 上一次运行未结束（含结果未知） | 领取 | 未发生 | 调度器 | 记录跳过 Run，前移游标 | Run 显示跳过原因 | 不排队，不补跑 |
| F6 | 停机、租约接管或扫描停顿超过 5 秒容差 | 领取 | 未发生 | 调度器 | 以数据库当前时刻建立新扫描代次，跳过恢复边界前的计划 | 停机期间没有 Run，只有运营指标和日志 | 不补跑；瞬时停顿按 5 秒容差处理，不承诺零时延 |
| F7 | 已受理但可证明未取得启动权，原拥有者已被 fencing | 启动前 | 受理已提交，执行未发生 | 调度器 | CAS 结束为未能启动，不转交新节点执行 | 【缺口】Run 与 Session 如何展示“未能启动”未定义 | 不由新节点重跑 |
| F8 | 取得启动权后失联、回执丢失或工具结果不明 | 执行中 | 未知 | 调度器，必要时人工 | 保持“结果未知”，保持占用，只读对账 | 运营视图标注未知；需对账或经授权的人工处置 | 不保证 exactly-once；可能漏执行一次 |
| F9 | 模型或业务执行失败 | 执行中 | 部分发生（已执行的业务不回滚） | Runtime | 保存根执行真实终态，释放执行槽，不重跑 | 从 Session 查看失败；下一计划照常 | 不回滚已发生的园区业务；是否自动暂停待定（T1） |
| F10 | 遇到权限 ASK、提问或计划审核 | 执行中 | 待确认调用未执行，此前操作已发生 | Host | 阻止该调用，结束本次根执行，记录需人工处理的原因 | Session 中可见原因；需改为非交互任务 | 不创建等待卡，不默认批准 |
| F11 | 删除与最终受理竞争 | 受理 | 删除先提交：未发生；受理先提交：Session 已创建 | 数据库行锁 | 删除先提交则不受理；受理先提交则保留 Session、删除 Run | Run 与 Schedule 404，从 Session 入口查看或停止 | 删除不取消已受理执行 |
| F12 | 单次运行超过 30 分钟 | 执行中 | 部分发生 | 调度器 | 向原根执行请求停止 | 停止未确认前显示停止中或未知 | 停止请求不等于已终止 |
| F13 | 删除后晚到的完成或失败回调 | 收尾 | 已提交（Session 侧） | 调度器 | 条件更新影响 0 行即视为资源已删，只收尾 Session 与根执行 | 无 | — |
| F14 | Mate 归属登记被拒或结果未知 | 受理前 | 被拒：未发生；未知：Mate 侧可能已登记，Claw 未受理 | 调度器 | 停止本次受理，按固定 Run 与 Session ID 只读核对；不新建 Session、不重放 | Run 显示未受理原因；结果未知时保持占用直至核对完成 | 无跨库事务，Mate 侧可能留下待核对的登记 |

参数校验失败不属于本表：它保持 `isError=true`，向模型返回字段错误和同次可信定义以便修正，不确认、不执行业务、不结束根执行，规则见 [M03](../02-CampusClaw工具系统/README.md#tool-argument-recovery)。

#### 5.2.2 容量与限流

- 不新增服务进程：定时任务运行在现有 coding-agent 进程内，多副本都能承载执行，只有持有扫描租约的一个副本负责分配到期的自动运行。
- 数据库是调度状态的最终决定方，定时器、执行线程、扫描缓存和本地租约计时均可丢弃；单扫描领跑者、任务行锁与 occurrence 唯一约束防止重复分配。
- 首版部署初始值由部署配置控制，不新增 Schedule 公共字段，未经压测，不代表容量：

| 配置 | 初始值 |
|---|---:|
| 扫描周期 / 派发容差 / 批量 | 1 秒 / 5 秒 / 100 条 |
| 扫描租约 / 心跳 | 15 秒 / 5 秒 |
| 每任务并发 | 1 |
| Mate 每管理范围任务数 | 100（由 Mate 配额准入维护，Claw 不计数） |
| 每实例定时活动执行上限 | 8（同时须取得既有 Runtime 容量） |
| 受理准备期限 / 单次运行上限 | 10 秒 / 30 分钟 |
| Run 保留 / 清理 | 30 天 / 每小时 500 条 |

- 瓶颈：自动扫描由单个领跑者负责，扫描吞吐是上限；多副本只扩展执行，不扩展扫描。
- 限流：每实例 8 个上限在多副本下会放大总并发；需要全局硬上限时复用 Runtime 已有的全局准入；跨租户公平策略归 Mate，不用各实例内存计数器冒充集群限流（T6）。
- **【缺口】** 容量目标：全园区预计任务总数、整点等高峰时刻集中触发的数量、可接受的派发延迟。
- **【缺口】** 压测计划：原文明确尚无压测，扩容前需按数据库延迟、扫描容差、下游配额与交互任务资源竞争测试，在此之前不写“支持多少任务/并发”。

#### 5.2.3 监控告警

原文已有的要求：停机漏跑只推进游标并输出非敏感运营指标与日志；结果未知在运营视图明确标注，不显示为成功或失败；控制台能定位授权与执行失败；日志不含凭据。

**【缺口】** 原文没有成体系的指标与告警设计。下列为建议项，待评审确认：

| 建议指标 | 为什么需要 | 建议告警 |
|---|---|---|
| 计划触发数与成功受理数之差 | D4 选择不补跑，漏跑必须可见，否则成为静默故障 | 差值持续大于 0 |
| 跳过次数（按原因：忙、超容差、权限、容量） | 区分“任务太长”与“系统过载” | 同一任务连续跳过 |
| 派发延迟（计划时刻到受理） | 验证 5 秒容差是否合理 | 接近或超过容差 |
| 结果未知的数量与持续时长 | 未知会一直占用任务，后续全部遇忙跳过 | 存在超过单次运行上限的未知 |
| 扫描租约丢失与代次切换次数 | 每次切换都会建立恢复边界并跳过之前的计划 | 频繁切换 |
| 活动执行数 / 每实例上限 | 判断容量是否接近配额 | 持续接近上限 |

#### 5.2.4 应急预案

原文已有：扫描领跑者失效后，其他副本在租约（15 秒）到期后接管，建立新扫描代次；结果未知的运行只有取得根执行终态、可靠未启动证据，或经独立授权的人工处置后才解除占用；切换到新调度器前必须停止旧 CronEngine 并核对旧在途执行。

**【缺口】** 人工处置结果未知的操作入口、权限与审计；数据库长时间不可用时的处置步骤；需要紧急停用全部自动调度时的开关。

### 5.3 兼容性

- 旧进程内 CronEngine（JSON Job / JSONL Run）在新 SQL 调度器启用前必须停止，两套调度不得并行。
- 旧 At/Every 任务不静默转换为 Cron；迁移时由 Mate 建立任务授权关联，缺时区或 Mate 授权的旧 Job 迁移后保持禁用等待补全。
- 现有 CronTool 与 BuiltInToolContracts 各有一份旧 Schema，迁移时同步处理；Cron 工具与 HTTP 委托同一应用服务。
- 普通 Session 的消息、文件引用和 Header 快照契约不因定时入口改变。
- Cron 方言采用 Spring 六字段，与 Claude 五字段 POSIX 不兼容，表达式不能直接复制。

## 6. 质量保证

### 6.1 灰度能力

**【缺口】** 原文没有灰度方案。需要注意一个约束冲突：执行专题要求“旧 JSON 调度不得与新 SQL 调度并行”，因此不能按实例或流量比例新旧并跑；灰度只能按 Mate 授权范围分批迁移，或先只开放配置接口、不开放自动执行。需要评审决定。

### 6.2 回滚能力

**【缺口】** 原文没有回滚方案。待回答的问题：模块合并后能否回退到独立 campusclaw-cron；旧 Job 迁移到 SQL 后能否回写 JSON；新调度器停用后在途 Session 如何收尾。

### 6.3 自动化测试

原文给出的验收要求（均未实施）：

- 确定性时间测试：可控时钟验证 08:00:01 正常受理、恢复代次不补 08:00:00、超容差跳过、忙时不排队、DST 缺失跳过与重复钟面按不同 UTC occurrence。
- 故障注入：准备前、提交前、提交后、启动 CAS 前后、业务调用后，确认无重复 Session、无重复首消息、未知不伪失败、重启不重放。
- 并发：2 副本竞争仅一次受理；暂停/修改/删除与最终受理竞态可线性判定。
- 接口：10 个操作的成功与错误报文、字段边界、分页前按 Mate 获准集合约束且空集合返回空，详见[配置 §8](configuration.md#implementation-acceptance)。
- 安全：越权目标资源被拒、旧 claimEpoch 拒绝、未登记归属不受理、ASK 不被自动放行、日志与历史中无凭据。
- 工程：reactor verify、corporate 镜像布局、GaussDB 集成与 2 副本联调。

实施切片（S1 独立任务管理 → S2 后台原子受理 → S3 持久调度与恢复 → S4 结果与运营 → S5 旧 Cron 入口迁移）见 [README §11](README.md#implementation-slices)。

### 6.4 QA 流程

**【缺口】** 原文没有 QA 流程（提测标准、测试环境、准出条件）。原文只区分了“单元测试存在、确定性测试通过、真实 GaussDB/多副本/企业身份联调”三类证据需分别记录。

## 7. 基建规范

- 包结构：`codingagent.schedule`（application、dispatch、persistence、config 子包）、`codingagent.tool.cron`、`codingagent.runtimeapi`；避免 `Registry → CronToolFactory → ScheduleService → Dispatcher → Registry` 构造环，不以 `@Lazy` 掩盖。
- 依赖：不新增外部 Maven 依赖，复用 JDK 21、Spring CronExpression、Jackson、MyBatis Spring Boot Starter 3.0.4 与既有数据库驱动；不引入 Quartz、XXL-JOB、Redis 锁。
- 对象：Controller 使用 RequestVO/ResponseVO 与 ResultBean；Service 处理默认值、合并与 VO/DTO 转换；Mapper 只收发 DTO，不引入 PO/DO/Entity。
- 数据库：遵循 [Claw 数据库设计](../../03-数据与存储/Claw数据库设计.md#schedule)；`t_` 表名、中文 COMMENT、`TIMESTAMPTZ(0)`、与 [秒级时间一致性](../01-CampusClaw多Agent运行时/time-contract.md) 对齐。
- 工程同步：迁移源码与测试后更新根 POM、`scripts/sync-campusclaw.sh` 的 MODULES、CODEOWNERS，并用同步脚本生成 corporate 包树。
- 文档：HTML 展示页由 `python3 scripts/render-schedule-api.py` 生成，`--check` 校验同步，不手工修改 HTML。

## 8. 其他补充

### 8.1 基线对照材料

关键决策已在 [§2.3](#key-decisions) 中说明；逐项对照留在专题文件：Claude 字段级取舍见[配置 §7](configuration.md#claude-tradeoffs)，多基线调度边界见 [A14](../07-Agent架构对比/README.md#a14)，源码与官方证据见 [source-evidence.md](source-evidence.md)。

<a id="failure-doc-references"></a>

### 8.2 失败处理写法参考

2026-10-11 隔离 clone 各默认分支最新快照，只读设计文档的组织方式，不据此得出新的实现结论；证据登记见[源码证据 §8.20](source-evidence.md#failure-doc-structure-evidence)：

| 基线 | 分支与提交 | 文档与位置 | 借鉴点 |
|---|---|---|---|
| pi | main `cdaf6c227d4718a72b59ccd02152c9614df44cfc` | `packages/durable/docs/spec.md` §1 不变量、§5.2 Effect sandwich、§10.1 Failures、§12 API footguns | 先列不变量；每类错误一条规则；用“意图—外部动作—结果”处理结果未知 |
| DSH | master `d743267388641bc76f17c45ce8b4c231aed1d32c`（alpha） | `.agents/notes/README.md`（问题 / 决策 / 放弃的方案 / 后果）、`.agents/notes/implemented/architecture/2026-09-16-host-schedule-storage.md`、`.agents/skills/dsh-error-handling/SKILL.md` | 每种失败写清处理方、影响范围、副作用状态、清理责任和用户可见的下一步；把限制写成“明确限制而非完成承诺” |
| OpenCode | dev `e31136bdbdb43e934d8bbd81e75a2065a2625699` | `specs/v2/session.md`（Retry Is Narrow And Observable、Recovery Boundaries Stay Explicit）、`specs/v2/tools.md` | 失败规则直接作为章节标题陈述；明确不保证 exactly-once |
| Codex harness | main `8c0f7011674145da7e10627769fb221c74fbf7a0` | `docs/`、`codex-rs/docs/` | 只有使用文档，未发现设计文档 |

Claude Managed Agents 本次未核对。

### 8.3 Spring 调度背景

固定注解 `@Scheduled` 与编程式 `TaskScheduler + CronTrigger` 的适用场景、当前 CronEngine“Spring 算时间、JDK 安排执行”的实现，见 [README §4.2～§4.3](README.md#spring-scheduling)。

### 8.4 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.36.0-restructure | 2026-10-13 | 任务内容 message 改为纯文本 prompt，移除 credentialIds，业务凭据改由 Mate 按 Agent 绑定在运行时决定。 |
| 0.35.0-restructure | 2026-10-12 | 合入 README 0.35.0 的 Mate 用户归属与权限、独立数据库设计和共用受理流程，时序图改用中文并只画正常流程。 |
| 0.30.2-restructure | 2026-10-11 | 按评审模板重组 README 0.30.2 的内容，增加关键设计决策、整体时序与稳定性下的失败处理、容量、监控和预案，并标注缺失章节。 |
