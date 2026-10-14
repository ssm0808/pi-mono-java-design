# CampusClaw 定时任务设计

[模块索引](../../README.md#module-index) · [Claw 数据库设计（定时任务表）](../../03-数据与存储/Claw数据库设计.md#schedule) · [Claw 接口协议](configuration.md) · [接口 HTML 展示](schedule-api-review.html) · [架构对比 A14](../07-Agent架构对比/README.md#a14) · [源码与官方证据](source-evidence.md)

本文是定时任务模块的主设计，按“评审记录 / 概述 / 整体方案 / 详细设计 / 接口协议 / 架构指标 / 质量保证 / 基建规范 / 其他补充”组织。接口字段与报文由 [configuration.md](configuration.md) 维护，表结构由 [Claw 数据库设计](../../03-数据与存储/Claw数据库设计.md#schedule) 维护，本文不复制。标注 **【缺口】** 的位置表示现有材料不足，需要补充。

| 属性 | 值 |
|---|---|
| 文档版本 | 0.48.0 |
| 更新日期 | 2026-10-14 |
| 模块 | M10 · 调度与并发治理 |
| 产品范围 | 每次自动或手动触发均创建新的独立 Session，复用配置绑定的 Agent 定义；不选择或追加已有 Session |
| 设计状态 | 目标设计，待实现。Java PR #332 已实现调度表、Mapper 与同库受理，尚未合并，与目标的差异见[数据库 PR #332 差异](../../03-数据与存储/Claw数据库设计.md#schedule-pr-diff)；Mate 授权与归属登记、调度扫描及其余能力待实现；main 上已观察实现仅为进程内 Cron |
| 源码基线 | Claw Java main `553dcd5e2ff682f9684810a043b442b37a02e54a`（2026-10-05 隔离 fetch）；PR #332 `e9d31e8888a81b7fe95071e705482bb16fa10476`（2026-10-10 核验，见[数据库源码证据](../../03-数据与存储/Claw数据库设计.md#source-baseline)） |
| 主基线 | Claude Managed Agents Scheduled deployments 公开 Beta 契约，最近核对 2026-10-08；无服务端源码 |

## 评审记录

### 评审结论

评审中。评审人：Lotus；评审开始日期：2026-10-11。结论待逐项评审完成后填写。

### 评审 Todo

负责人 **【缺口】**。

| # | 事项 | 负责人 | 来源 |
|---|---|---|---|
| T1 | 运行失败是否自动暂停整个 Schedule（不能默认继承旧 Cron 连续三次失败自动禁用） | | [失败处理](#failure-recovery)、[配置 §4.1.1](configuration.md#schedule-type-paused-reason) |
| T2 | Mate 新增的定时 access-token 接口与归属登记仍为内部草案；Claw 与 Mate 的服务认证机制、统一账号的配置与 Token 有效期需联调 | | [实施校准](#implementation-calibration) |
| T3 | PR #332 已实现但未合并，与目标设计仍有差异（含本地身份链路） | | [数据库 PR #332 差异](../../03-数据与存储/Claw数据库设计.md#schedule-pr-diff) |
| T4 | 原子受理、受理后失联、取消终态与多副本故障测试须在实现阶段验证 | | [自动化测试](#auto-tests) |
| T5 | 完整 Maven 依赖树与 corporate NativeParent 未核验 | | [模块与依赖](#module-merge) |
| T6 | 每实例 8 个活动执行上限在多副本下会放大总并发，部署阶段需按实例数与下游配额核对 | | [部署初始值](#deployment-defaults) |
| T7 | Mate 任务配额准入和 Session 归属登记的内部契约待实现（列表首版由 Mate 拉取全部后自行过滤，不传获准集合） | | [配置 身份与权限边界](configuration.md#mate-access-boundary) |
| T8 | Mate 管理入口在调用 Claw 前后的处理逻辑（权限、配额、任务与用户关联等）尚未确定；Claw 侧逻辑已确认 | | 本次评审 |
| <a id="todo-t9"></a>T9 | 实例宕机后执行卡在运行中：会话无法继续对话，定时任务一直被占用、后续计划全部遇忙跳过。候选方案（Runtime 通用能力，定时任务复用）：① 实例心跳表与执行所属实例，心跳超时约 30 秒后把执行标为中断、写入中断事件、结束 Run 并释放任务；② 执行期写入与工具调用前检查执行未终止，防止卡死后恢复的旧实例继续执行；③ 工具调用携带幂等键（executionId + toolCallId），并在会话中显示中断时所在的工具调用 | | 本次评审（2026-10-13） |
| <a id="todo-t10"></a>T10 | 是否在 Claw 的 t_schedule（及 Run、Session）增加 userId，使列表直接按用户查询；需先确定任务仅创建者可见还是同范围共享，以及与 Mate 归属的同步规则。首版按方法 A 由 Mate 拉取全部后过滤 | | 本次评审（2026-10-13） |

### 需求信息

需求来源：安全 Agent 场景四“配置空间安全管理规则”，其中视频巡逻检查规则需要按设定时刻自动执行，由定时任务承载。场景四目前没有需求文档。**【缺口】** 需求编号、优先级和目标版本。

页面行为与原型见 [M07 场景09](../../07-前端设计/场景/09-配置与管理定时任务/README.md)：Manual 映射 schedule:null，Schedule 映射完整 Cron；触发方式、active/paused 和单次 Run 结果分别展示，保存后读取权威计划时间。Console 核验范围见[专项证据](source-evidence.md#schedule-console-evidence)。

<a id="problem"></a>

## 1. 概述

### 1.1 术语解释

| 术语 | 含义 |
|---|---|
| Claw | CampusClaw Agent 服务，本设计的实现方 |
| Mate | 用户、组织、租户、资源归属与权限的维护方，也是可信接口定义、Session 归属和定时执行统一账号凭据的提供方；运营人员通过 Mate 管理入口操作定时任务 |
| Schedule | 长期保存的任务配置：Agent 绑定、纯文本 prompt、可选 Cron 规则 |
| Run | 一次自动或手动触发的受理记录；只表示是否成功创建 Session，不表示业务成败 |
| Session | 每次 Run 新建的独立会话，承载消息、工具结果与根执行 |
| 根执行（root execution） | Session 内本次运行的顶层执行，是执行终态的最终决定方 |
| occurrence | 一个具体的自动计划时刻，以 `(schedule_id, scheduled_at)` 唯一标识 |
| 计划游标 | `upcoming_run_at`，下一次自动计划时刻；领取或跳过一次后推进到下一次 |
| 派发容差 | 计划时刻与数据库当前时刻之差的上限，首版 5 秒；超过则不运行、不补跑 |
| 受理（acceptance） | 在同一数据库事务内创建 Session、首条消息、根执行并写入 Run 关联 |
| 未结束 Run | finished_at 为空的 Run；同一 Schedule 至多一条，由运行表部分唯一约束保证同任务不并发 |
| lease_until | Run 的受理准备期限，过期后不得受理并由清理结束 |
| pausedReason | 当前暂停原因，`manual` 或保留的 `error` 形状；恢复后清空 |
| Spring 六字段 Cron | 秒、分、时、日、月、星期；不接受五字段 POSIX 或年字段 |

### 1.2 需求整理

**【缺口】** 没有原始需求文档。下表是从已确认决策反推的需求清单，供评审确认是否与原始需求一致。

| 编号 | 需求 | 类型 | 来源 |
|---|---|---|---|
| R1 | 运营人员可创建、查看、修改、删除定时任务配置，浏览器无需保持打开 | 功能 | 配置 §2 |
| R2 | 时间规则仅支持 Spring 六字段 Cron，timezone 省略时默认 Asia/Shanghai；可省略规则表示仅手动运行 | 功能 | 配置 §3 |
| R3 | 每次自动或手动运行新建独立 Session，复用绑定的 Agent 定义，不追加到已有会话 | 功能 | [§3.9](#new-session-per-run) |
| R4 | 支持立即运行、暂停、取消暂停；暂停只阻止未来自动受理 | 功能 | 配置 §4.7～§4.9 |
| R5 | 用户能看到下一次计划时间、每次是否成功启动、执行结果入口和失败原因 | 功能 | 配置 §3.3、§4.11 |
| R6 | 删除 Schedule 同时删除其 Run，保留已生成的 Session；删除不取消已受理执行 | 功能 | 配置 §4.6、§4.11 |
| R7 | 不补漏跑、遇忙跳过、失败与故障不重跑 | 约束 | [§3.8](#no-catch-up) |
| R8 | 首版只支持文本输入、无需人工交互的任务；ASK 结束本次根执行 | 约束 | [§3.10](#noninteractive) |
| R9 | 定时执行统一使用 Mate 配置的同一个账号，运行时向 Mate 取 access-token；Claw 不保存凭据引用或秘密 | 安全 | [§5.1](#security) |
| R10 | 多副本部署下同一 occurrence 只受理一次 | 稳定性 | [§3.5](#scheduled-run-sequence) |
| R11 | 用户、资源归属与权限由 Mate 维护；Claw 不保存用户范围或 owner，新 Session 受理前由 Mate 登记归属 | 安全 | [§5.1](#security) |

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
| Mate | 管理入口；用户权限、资源归属与定时执行凭据 | 外部服务，以可信服务调用 Claw；配置授权、归属与统一账号 access-token 的提供方；管理入口的内部处理待定（T8） |
| Claw | coding-agent 服务：定时任务管理、到期扫描、受理协调，以及创建 Session 并推进 Agent 与工具 | `codingagent.schedule` 与既有 Session 运行时，同一进程，见 §3.3～§3.6 |
| GaussDB | 调度与 Session 存储，调度状态的最终决定方 | 同库事务资源 |

![定时任务整体时序](scheduled_task_overview.svg)

[原尺寸 SVG](scheduled_task_overview.svg) · [PlantUML 源码](diagram.puml#L295)

| 阶段 | 详细时序 |
|---|---|
| 步骤 1～8：配置定时任务 | [§3.3 配置定时任务的详细时序](#save-sequence) |
| 步骤 9～20：运行定时任务 | [§3.5 运行定时任务的详细时序](#scheduled-run-sequence)，其中受理部分见 [§3.6 共用受理的详细时序](#run-admission-sequence) |
| 步骤 21～26：查看巡逻结果 | 无详细时序：运行记录读取为单次查询，规则见[配置 §4.11](configuration.md#schedule-run-read-lifecycle)；会话读取沿用 M06 既有接口 |

<a id="key-decisions"></a>

### 2.3 关键设计决策

CampusClaw 的基线集合为 Claude Managed Agents、Codex harness、OpenCode、pi、DeepSeek Harness（DSH）；本模块以 Claude Managed Agents 为主基线，按问题选择相关基线。在已登记快照中，pi 只有实验性进程 Job（pico3），Codex harness 只有插件计划元数据，二者都没有可直接对照“用户定时任务”的实现。基线事实均引用 [A14](../07-Agent架构对比/README.md#a14) 与[源码证据](source-evidence.md)中已登记的日期和提交；Claude 为公开 Beta 契约，DSH 为 alpha，OpenCode 为 dev 分支。

| # | 要解决的问题 | 基线怎么做 | 园区业务约束 | 我们的选择 | 代价 |
|---|---|---|---|---|---|
| D1 | 怎样让用户分清“任务启动了”和“业务做完了”？ | Claude 把 Deployment（配置）、DeploymentRun（一次触发）、Session（执行内容）分开，Run 只记录 Session 创建结果；现有 CampusClaw CronEngine 是 JSON Job 加 JSONL 运行日志 | 模型自然结束不等于巡检或工单处理成功，业务结论必须来自 Session 里的输出和工具证据 | 采用三类资源分离：Schedule / Run / Session；Run 只回答“是否成功受理” | 多一层资源，看业务结果要从 Run 跳到 Session |
| D2 | 每次定时运行放进哪个会话？ | Claude 每次新建 Session；OpenCode 的 GitHub schedule 入口每次新建 Session；DSH 的提醒固定投递回创建它的原 Session；OpenAI 宿主 Scheduled tasks 支持新聊天和继续原聊天两种模式 | 同一任务每天产生独立结论，要避免与人工聊天争用同一会话；多一种目标模式就多一套绑定、忙闲和授权规则 | 每次新建独立 Session，复用绑定的 Agent 定义，不提供 target / sessionId | 不能延续聊天上下文，需要昨日结论时必须显式查询业务记录 |
| D3 | 谁决定“这次该不该跑”，多副本下如何不重复？ | Claude 未公开内部实现；OpenCode 把计时交给外部 GitHub Actions；DSH 和 pi pico3 都在单进程内计时（DSH 用串行队列处理投递与删除） | 企业部署多副本；Session 创建和首条消息必须与 Run 一起成功或一起失败，崩溃后要能对账 | GaussDB 是调度状态的最终决定方，定时器只负责唤醒扫描；各副本并行扫描，以行锁和唯一约束防重；同库事务内原子受理 Run、Session、首条消息和根执行 | 首版要求 Schedule、Run 与 Runtime 同库；查询量随副本数增加，需要压测 |
| D4 | 进程崩溃、停机或回执丢失后，这次要不要补跑或重跑？ | Claude 公开资料未给出完整重叠与故障策略；DSH 的固定间隔只取最新到期项，不逐个补历史；pi pico3 在进程结束后按当前时间加间隔推进 | 工单、门禁、告警处置等工具有真实副作用，重复执行比漏执行更危险 | 不补漏跑、遇忙跳过、失败与故障不重跑；结果未知时保持占用并对账 | 故障时可能漏跑一次；结果未知需要对账或人工处置，自动恢复见 T9 |
| D5 | 用户用什么方式描述“什么时候跑”？ | Claude 只支持五字段 POSIX Cron，时区必填；DSH 支持 Cron（时区必填）、单次与固定间隔；pi pico3 只有毫秒级 notBefore/every，没有日历时区；OpenCode 用 GitHub Actions 的五字段 Cron，默认 UTC | 园区任务以“工作日 08:00”这类日历规则为主，主要在中国时区；Java 工程已有 Spring CronExpression，不希望新增依赖 | 仅支持 Spring 六字段 Cron；timezone 可省略，默认 Asia/Shanghai 并保存回显 | 不支持单次任务和严格固定间隔；Claude 表达式不能直接复制，日与星期组合语义也不同 |
| D6 | 删除任务时，运行记录、会话和在途执行怎么处理？ | Claude 采用归档；DSH 删除任务及投递历史，保留原 Session，不取消在途；辅助基线 OpenClaw 保留运行历史，操作者删除时请求取消 | 用户不想为了删任务再逐条清理运行记录；已生成的对话和园区业务结果要独立保留；取消在途执行可能留下半完成的业务操作 | 同删 Schedule 和 Run，保留 Session，不取消已受理执行，停止由 Session 入口单独发起 | 删除后无法再查启动失败和触发来源，尤其是没有生成 Session 的失败 |
| D7 | 无人值守时遇到权限确认或提问怎么办？ | 无可对照实现（已登记基线没有定时场景下的交互处理） | 定时执行时没有人在线回答；默认批准会绕过园区业务权限 | 首版只支持无需人工交互的任务；Host 遇 ASK 时阻止业务调用并结束本次根执行 | 需要人工确认的任务暂时不能定时执行 |
| D8 | 任务运行时使用 Agent 的哪个版本？ | Claude 在创建或显式更新 Deployment 时固定 Agent 版本 | 现有 Agent 目录没有可解析的历史定义，只保存一个版本号兑现不了版本固定 | 只绑定 agentId，每次使用当时已发布的定义 | Agent 发布新版本后，后续运行行为可能改变，无法复现历史运行；这是能力缺口，不是字段简化 |
| D9 | 首版任务列表和 Run 列表如何按用户过滤？ | Claude 按 workspace 范围列出，无用户级过滤 | 用户与任务的关联在 Mate；Claw 不保存用户范围或 owner | 方法 A：Claw 返回全部记录，Mate 拉取全部页后按用户过滤、排序和分页；单任务的 Run 由 Mate 先确认可见再带 scheduleId 查询 | 读取量随全部任务与 Run 增长，Claw 页码只用于分批拉取；Claw 加 userId 见 T10 |
| D10 | 定时执行时没有用户请求，Claw 用什么权限调用业务工具？ | Claude 部署引用 workspace 范围的 Vault 凭据；普通对话由用户请求带 Header | 用户登录 Token 会过期，且没有确认过的刷新或代签接口；不能保存用户密码 | 用户权限只在配置时由 Mate 检查；运行时统一使用 Mate 配置的同一个账号，模型每批需要凭据的工具调用前，Claw 无入参向 Mate 取一次 access-token（2026-10-13 评审确定） | 所有任务权限相同；创建者失去权限或离职后任务仍照常运行；每批工具调用多一次 Mate 请求 |

时间、执行目标和删除的多基线对照见 [A14](../07-Agent架构对比/README.md#a14) 和[删除基线证据](source-evidence.md#schedule-delete-baselines)。

<a id="claude-tradeoffs"></a>

### 2.4 与 Claude Managed Agents 的逐项取舍

本节比较公开 Beta [创建](https://platform.claude.com/docs/en/api/http/beta/deployments/create)、[更新](https://platform.claude.com/docs/en/api/http/beta/deployments/update)和[定时 Deployment](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)契约，不推断服务端实现。字段与报文以 [configuration.md](configuration.md) 为准；读取、删除的报文差异分别在配置 §4.3～§4.4、§4.6。

| 决策 | Claude 公开契约 | Claw 目标、理由与代价 | 分类 |
|---|---|---|---|
| 名称长度 | name 的 maxLength 为 256 | 名称上限同为 256，不增加缺少业务依据的限制；Java 字符计数不声明为已验证的跨语言 Unicode 等价 | 参考基线 |
| 配置资源 | Deployment 绑定 Agent、环境、初始事件和可选规则 | Schedule 绑定 Agent、纯文本 prompt 和可选规则；保留配置与 Session 执行分离，范围聚焦现有调度领域，不建设完整部署平台 | 架构范围 |
| 创建即登记计划 | 提供 schedule 后自动触发，新建示例为 active | 同样登记自动计划；创建处理器不直接运行。不能因为先开发配置就永久默认 paused；运行未接线应限制发布 | 参考基线，无额外启用流程 |
| 执行目标 | 每次触发创建新 Session | 每次运行固定新建 Session，不提供 target；减少原会话授权、模式、忙闲状态及多任务竞争的规则，代价是不自动延续原会话上下文 | 参考基线、产品范围 |
| Agent 版本 | 字符串固定当时最新版本，亦可指定历史版本 | 只绑定 agentId，使用执行时实际取得的已发布目录；现有 prepare 可命中缓存，非每次远端最新。目录刷新后未来行为可能变，暂缺固定版本可复现保证 | 现有能力缺口 |
| 运行环境 | 显式 environment_id | 不提供空壳 environmentId，沿现有 Host/Agent 目录装配；减少资源模型，但失去独立环境选择与复用 | 架构范围 |
| 初始输入 | initial_events 支持多事件及受约束事件类型 | 一段纯文本 prompt，运行时作为首条用户消息提交；不支持附件、多初始事件、system.message 或 user.define_outcome，亦不支持交互等待；普通 Session 文件引用契约保持 | 产品范围、实现差距 |
| 时间表达 | 五字段 POSIX Cron，IANA 时区 | 采用 Spring 六字段，复用现有解析器且不新增 Maven 依赖；代价是 Claude 表达式不能直接复制，日/周组合语义也不同，见 [Spring 调度背景](#spring-scheduling) | 产品约束（方言选择）、实现成本取舍 |
| 时间精度 | 创建 Session/Deployment 示例为整秒 UTC；公开文档未保证只支持秒级或披露数据库精度 | Claw 明确仅支持秒级，Session、完整事件与定时任务一致；降低展示和存储差异，代价是放弃这些字段的亚秒时间差。见[时间证据](source-evidence.md#claude-time-precision-evidence) | 产品约束 |
| Cron 时区 | timezone 必填，使用 IANA 名称 | timezone 可省略，默认 Asia/Shanghai，保存并回显有效值；适配主要园区场景，代价是调用方需了解省略时采用的产品预设，不能继承运行节点默认值。其他基线也没有统一默认值：DSH 必填、GitHub Actions 默认 UTC、pi 无日历时区，见[时区证据](source-evidence.md#timezone-evidence) | 产品约束 |
| 时间类型范围 | schedule 模型只声明 cron | 同样只接受 cron，减少一次性任务耗尽、间隔起点和更新重置等规则；代价是不支持未来指定时刻只执行一次，也不支持从任意起点按固定秒数重复：`0 0 8 1 10 *` 每年匹配 10 月 1 日，`0 */7 * * * *` 每小时重新匹配，不能冒充严格每隔 7 分钟 | 产品约束（范围收敛） |
| 更新 | 省略保持、schedule:null 清除、初始事件/规则整体替换 | 沿用；Claw 的 prompt/schedule 整体替换，metadata 逐 key 更新，不引入通用深层合并 | 参考基线 |
| 立即运行 | POST run，无业务正文，200 返回 DeploymentRun，记录 Session 创建结果 | 200 返回 ScheduleRun，可靠记录的失败在 Run.error；新 Session 与首消息受理分开于业务完成，不等待模型结束；ResultBean 和无 Agent 版本固定沿既有约束 | 参考基线、公司契约与受理架构增量 |
| 暂停/取消暂停 | POST pause/unpause，200 完整资源；暂停允许手动运行，恢复不补跑 | 采用同样入口与完整 Schedule；暂停受理屏障、同值调用不改时间/游标和恢复资格校验需新增实现与验收 | 参考基线、企业授权与一致性设计 |
| 并发与重试 | 官方配置操作未声明客户端版本或请求键协议，内部实现未公开 | 不引入此类公共协议；数据库锁最新记录、合并部分字段并原子写入。简化调用和存储，代价是允许同字段后写生效、创建重提可能生成重复资源，且不提供原回执恢复 | 产品约束、数据库一致性设计 |
| 运行与计划时间摘要 | schedule 内有 last_run_at/upcoming_runs_at | 同样返回最近自动开始与最多五次计划；ResultBean、lowerCamelCase、UTC 秒级是公司/产品规则；动态摘要只用于显示，不参与客户端更新准入 | 参考基线、公司契约 |
| 状态与版本 | active/paused，另有 archived_at；未声明 revision | 新建 active、存续资源 active/paused；不保存配置版本；删除成功返回最后配置回执，随后读取 404，无归档时间字段 | 参考基线、边界明确 |
| 删除配置 | POST archive，200 完整资源，以 archived_at 表示不可恢复终态 | 直接删除及 200 完整 Schedule 回执、随后 GET 404 且列表排除；重复删除 404。Schedule 和 Run 同删，Session 保留；简化任务侧历史生命周期，代价是无法再查询已删任务的受理失败和来源记录 | 产品约束、生命周期架构选择 |
| 资源类型 | 顶层 type 固定为 deployment | 顶层 type 固定为 schedule，完整响应统一返回；便于识别资源，代价是增加一个恒定字段，不扩展现有 Session 契约 | 产品约束 |
| 暂停原因 | paused_reason 为 null 或 manual/error 原因对象，恢复后清空 | pausedReason 保留相同职责，随状态持久化并安全投影；增加当前原因维护成本，不能用最后一个 Run 错误替代，error 形状保留，是否自动暂停整个 Schedule 待定（T1） | 参考基线、架构增量 |
| metadata | 最多 16 对字符串，键最多 64、值最多 512 | 支持可选 map，采用同样限制；不进模型，不作身份、权限或凭据依据 | 参考基线、产品约束 |
| 凭据 | vault_ids 引用 workspace 范围 Vault，运行时使用其中凭据 | 不保存凭据引用；所有定时任务统一使用 Mate 配置的同一个账号，每批工具调用前无入参取 access-token（D10）。实现最简单，代价是所有任务权限相同、用户权限只在配置时检查 | 企业产品约束 |

固定 Agent 版本是最显著的能力差距，不应包装成单纯“字段简化”。未来若要求长期告警策略可重复审计，需要先建设可解析的历史定义与资源绑定，再开放 agentVersion；只保存一个 version 数字不能兑现版本固定。Spring 六字段的理由是复用 Java 现有能力与降低维护成本，不是园区业务天然要求秒级执行。

## 3. 详细设计

<a id="system-use-cases"></a>

### 3.1 系统用例

前 10 项为 HTTP 操作，由 Mate 管理入口以可信服务调用发起（Mate 内部处理待定，见 T8）；后 3 项为后台作业。BU6 还需读取 M06 既有 Session 接口，不在本模块新增。

| 用例 | 对应业务用例 | 触发者 | 前置条件 | 主成功结果 | 关键约束 |
|---|---|---|---|---|---|
| UC1 创建配置 | BU1 | Mate 管理入口 | Mate 已授权的操作与目标 | 201 完整 Schedule，status=active | 不调用模型或 Session 工厂；未接线运行能力前不发布自动运行承诺 |
| UC2 列表 | BU6 | Mate 管理入口 | Mate 已确认用户身份 | 200 分页完整资源 | Claw 返回全部存续任务，Mate 拉取全部页后按用户过滤、排序和分页；不换取凭据 |
| UC3 详情 | BU6 | Mate 管理入口 | 读取资格 | 200 完整资源 | Agent 或凭据失效不妨碍读取 |
| UC4 部分更新 | BU2 | Mate 管理入口 | 管理资格 | 200 完整资源 | 锁最新行合并提交字段；不触发执行、不改暂停状态 |
| UC5 删除 | BU7 | Mate 管理入口 | 管理资格 | 200 完整 Schedule 回执 | 同删 Run，保留 Session，不取消已受理执行 |
| UC6 立即运行 | BU4 | Mate 管理入口 | 运行资格；active 或 paused | 200 Run（sessionId 与 error 二选一） | 先占用任务，再走共用受理；不移动计划游标 |
| UC7 暂停 | BU5 | Mate 管理入口 | 管理资格 | 200 完整 Schedule，paused/manual | 同值操作不改时间与游标 |
| UC8 取消暂停 | BU5 | Mate 管理入口 | 管理资格、执行资格 | 200 完整 Schedule，active/null | 只从未来匹配继续，不补跑 |
| UC9 Run 列表 | BU6 | Mate 管理入口 | Mate 已确认用户身份 | 200 runs/nextPage | 单任务时 Mate 先确认可见再带 scheduleId 查询；跨任务时 Mate 拉取全部后过滤；不含已删除任务的 Run |
| UC10 Run 详情 | BU6 | Mate 管理入口 | 读取资格 | 200 八字段 Run | 任务或 Run 已删除时 404 |
| UC11 自动扫描与受理 | BU3 | 调度器 | 任务到期 | 新 Session 受理并启动 | 不补漏跑、遇忙跳过；受理前须完成 Mate 归属登记 |
| UC12 结果对账 | BU3 | 调度器 | 已受理 Run | 写入 Run.finished_at 释放任务 | 已删除任务只收尾 Session，不复活资源 |
| UC13 运行超时停止 | BU3 | 调度器 | 单次运行超过 30 分钟 | 向原根执行请求停止 | 停止未确认前保持停止中或未知 |

<a id="persistence-lifecycle"></a>

### 3.2 数据模型

表结构、约束、索引与数据库事务由 [Claw 数据库设计（定时任务表）](../../03-数据与存储/Claw数据库设计.md#schedule)唯一维护。目标只有两张表 `t_schedule`、`t_schedule_run`，不修改既有 Session 与根执行表；PR #332 中需要撤销或改名的结构集中在 [PR #332 差异](../../03-数据与存储/Claw数据库设计.md#schedule-pr-diff)。

业务生命周期：Schedule 保存长期配置，Run 保存一次受理事实，Session 与原根执行保存实际执行结果。删除 Schedule 同时删除 Run，保留已受理的 Session 且不自动取消；单独删除 Session 不改写历史 Run 的受理事实。数据库关联与竞争顺序见[事务、删除与保留](../../03-数据与存储/Claw数据库设计.md#transactions)。Claw 只保存资源关联，不保存凭据、授权引用、用户范围、owner 或操作者副本，见 [Mate 归属边界](../../03-数据与存储/Claw数据库设计.md#mate-ownership)。

<a id="class-diagram"></a>

全局目标类图（分层、依赖与生命周期）：所有新增节点和连线均为待实现；标识为既有的 Runtime 类仍需后台入口扩展。Mate 表示外部权威边界，其内部实现不在本图展开。

![定时任务全局目标类图](scheduled_task_architecture.svg)

[原尺寸 SVG](scheduled_task_architecture.svg) · [PlantUML 源码](diagram.puml#L45)

| 层次 | 责任与生命周期 |
|---|---|
| 边界与入口 | `ScheduleController` 收发 RequestVO/ResponseVO；`CronToolAdapter` 传入 Host 已绑定的 Session/执行和目标资源，不能绕过授权 |
| 绑定解析 | `ScheduleBindingResolver` 只读检查 Agent 绑定，管理调用不发布运行目录；MateAdapter 从 Mate 取得可信定义、Session 归属登记与统一账号 access-token |
| 应用编排 | `ScheduleApplicationService` 管理规则与 VO/DTO 转换；`ScheduleRunPreparation` 与受理服务承接共享入口；`ScheduleDispatcher` 推进已受理执行；均为 Spring 单例 |
| 策略与准备 | `ScheduleTimePolicy` 统一校验与计划计算；`ScheduleAuthorizationPort` 调用 Mate 的归属登记，不是 Claw 的用户权限策略；`ScheduledAccessTokenPort` 在每批工具调用前取 access-token；`PreparedScheduleRunDTO` 每次准备的不可变快照，不代替事务内可变状态检查 |
| 持久化 | `ScheduleRepository` 委托 `ScheduleMapper`，只收发 DTO，不引入 PO/DO/Entity |
| Runtime 适配 | `ScheduledRunAcceptanceService` 在同库短事务中受理；`RuntimeExecutionCoordinator` 事务后启动、投影与关闭；每次独立 `ManagedAgentSession` 由公共工厂创建 |

管理路径不调用 Session 工厂或执行协调器，立即运行入口委托运行服务复用准备与受理。Controller 不直接调用 Mapper 或模型，模型与外部 I/O 不进入配置数据库事务。

<a id="save-sequence"></a>

### 3.3 配置定时任务的详细时序（UC1、UC4）

展开整体时序的“配置定时任务”阶段。场景：保存视频巡逻检查任务，从调用 Claw 到返回持久化结果。状态：待实现。

![Claw 配置保存](schedule_configuration_save.svg)

[原尺寸 SVG](schedule_configuration_save.svg) · [PlantUML 源码](diagram.puml#L182)

保存步骤、并发语义与结果不确定时的处理见[配置 §5](configuration.md#reliable-write-flow)。

<a id="manual-run-sequence"></a>

### 3.4 立即运行的详细时序（BU4、UC6）

独立对应业务用例，不展开整体时序的阶段：它与“运行定时任务”共用受理路径，只是触发方式不同。场景：手动触发一次视频巡逻检查，从请求到返回 Run 回执。状态：待实现。

![立即运行与Run回执](schedule_manual_run.svg)

[原尺寸 SVG](schedule_manual_run.svg) · [PlantUML 源码](diagram.puml#L215)

**正常调用如何完成：** 核验 Mate 服务、获准操作和目标 → 短事务锁定任务，插入一条未结束的手动 Run 占用任务，不改自动计划 → 进入[共用受理流程](#run-admission-sequence) → 返回 200 和带 sessionId 的 Run，不等待业务完成。

<a id="scheduled-run-sequence"></a>
<a id="normal-acceptance"></a>

### 3.5 运行定时任务的详细时序（UC11、UC12）

展开整体时序的“运行定时任务”阶段。场景：每天 22:00 为“视频巡逻检查”创建一个新 Session，从一次到期扫描开始，到新 Session 根执行终态入库结束；前提是任务为 active 且身份策略可用。状态：目标设计，待实现。

<a id="sequence-roles"></a>

图中角色表示职责，不代表独立进程，同一角色在配置、自动触发、手动运行和受理下钻中含义相同：

| 角色 | 负责的交互 | 实现映射 |
|---|---|---|
| 调度器 | 发起到期扫描、提交后启动及原根执行结果对账 | `ScheduleDispatcher`；各副本并行扫描，不选领跑者 |
| 定时任务管理 | 管理配置；领取 Run，协调可信准备和原子受理 | `ScheduleApplicationService`、`ScheduleRunPreparation`、`ScheduledRunAcceptanceService` 等 M10 应用职责，不要求实现为一个大 Service |
| Mate | 提供可信绑定与配置授权，登记 Session 归属，提供统一账号的 access-token | `MateScheduleAdapter` 对接外部 Mate |
| Session 运行时 | 准备 Agent/模型/工具上下文；受理后推进模型与工具，保存根执行结果 | 既有 `AgentSessionFactory.create`、`RuntimeExecutionCoordinator.start` 和运行时持久化能力；后台准备与非交互 Host 策略待实现 |
| 存储 | 原子保存任务、Run、Session/首消息/根执行，以及执行事件与终态 | 同一 GaussDB 事务资源；通过 Repository 与 Runtime 持久化协作者访问 |

受理事务由 `ScheduledRunAcceptanceService` 协调，并调用既有 Runtime 持久化能力参与同一事务；Runtime 执行器不拥有 Schedule 的生命周期判断。准备阶段只调用 Runtime 的准备能力，不启动模型；提交后的执行推进由调度器发起。Host 的工具权限判断留在 Runtime 内，Mate 的外部授权单独画出，两者不能互相替代。

![独立会话定时运行](scheduled_run_sequence.svg)

[原尺寸 SVG](scheduled_run_sequence.svg) · [PlantUML 源码](diagram.puml#L1)

1. **分配 occurrence。** 各副本每秒按 upcoming_run_at/id 有界扫描，不按用户或租户分组；以 `FOR UPDATE SKIP LOCKED` 锁定到期的 Schedule 行，锁内复核未删除、active 与游标仍是本次计划时刻。任务无未结束 Run 时插入一条未结束 Run（部分唯一约束即占用）并推进游标；已有未结束 Run 时插入一条已结束的忙跳过 Run，不排队。超过 5 秒派发容差的处理见 [§3.8](#no-catch-up)。
2. **归属登记与准备。** 先固定拟建 Session ID，由 Mate 独立登记归属并确认；再在事务外解析 Agent 已发布目录、模型、CRON profile、工作区，固定 `PreparedScheduleRunDTO`；不持数据库行锁调用远端，不调用模型或业务工具。
3. **原子受理。** 同一事务锁定 Schedule 与 Run，复核任务存在且状态允许、任务 agent_id 等于 Run.agent_id、Run 未结束且 lease_until 未过与容量；创建 Session、首条用户消息（使用锁内读到的最新 prompt）、根执行，写 Run 关联，自动运行同时写 last_run_at 为数据库当前时间。任一步失败整体回滚。
4. **事务后启动。** 受理不等待 Agent 完成。原实例在进程内直接启动一次，调度上下文（scheduleId、runId、agentId 及非交互策略）只在内存中传给 Runtime 和子 Agent，使用 `RuntimeEventOutput.persistenceOnly()` 保存完整事件，不伪造 SSE 连接。模型每次返回需要凭据的工具调用时，向 Mate 取一次统一账号 access-token，本批工具共用（[D10](#key-decisions)）。Runtime、Cron 与 Child 共用受理原语与执行协调器，规则见[统一执行历史](../01-CampusClaw多Agent运行时/unified-event-persistence.md)。
5. **结果对账。** 读取受理时固定的根执行终态（以根执行为准）；Schedule/Run 仍存续时写入 Run.finished_at 释放任务；已删除时只收尾 Session 与根执行，不重新插入 Run 或配置。用户在同一 Session 后续发起的对话不改写本次结果。

自动和手动受理均要求配置存在；自动受理要求 active 并检查派发期限，手动受理允许 active/paused，不移动计划游标，也不更新 last_run_at。暂停或 Agent 绑定变更先提交时，已领取的自动 Run 不受理；仅修改 prompt 或时间规则不取消已领取的这次运行，受理使用最新 prompt。删除先提交则不受理；受理先提交则保留 Session 并删除 Run。

首版限定 Schedule、Run 与 Runtime 受理记录位于同一事务资源。现有 HTTP 创建 Session 和提交消息不提供这种原子性，不能串联它们并在断连后重复 POST。自动 occurrence 唯一约束防止重复分配，同一 runId 的受理复用原关联；这些内部机制不合并不同手动调用，也不等于外部业务 exactly-once，工具副作用仍受下游业务幂等和已执行结果对账约束。

<a id="run-admission-sequence"></a>

### 3.6 共用受理的详细时序（UC6、UC11）

展开 §3.4 和 §3.5 中的“共用受理流程”。场景：一次视频巡逻检查 Run 已领取并占用任务，从登记 Session 归属开始，到受理结果提交结束，不包含模型执行。自动和手动入口共用此流程；自动还检查 active 与派发期限，手动允许 paused 且不推进自动游标。状态：待实现；PR #332 已实现同库受理部分，Mate 归属登记待实现。

![共用受理流程](schedule_run_admission.svg)

[原尺寸 SVG](schedule_run_admission.svg) · [PlantUML 源码](diagram.puml#L251)

**正常调用如何完成：** 固定拟建 Session ID，由 Mate 按资源 ID 登记 Session 归属（Claw 不提供用户、租户或 owner）→ Session 运行时只准备 Agent、模型和 CRON 上下文，不执行业务 → 一个短事务内复核任务、Run、时间和容量，创建 Session、首条消息、根执行并写入 Run 关联。

本图只画正常受理。用户执行权限只在配置任务时由 Mate 检查，运行时不再查询。Mate 归属登记未确认和 Runtime 准备失败分别属于跨服务持久登记和本地准备，核对责任不同，处理见 [F4、F14](#failure-recovery)。Mate 登记与 Claw 受理之间没有跨库事务，详细规则见 [Mate 会话归属](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md#session-ownership)。

准备成功只固定本次上下文，最终事务仍复核可变状态。Runtime 准备与既有 `AgentSessionFactory.create` 的内存对象装配有关，不等于已创建持久 Session，也不等于已发送模型请求。提交结果未知或存储不可用时不伪造确定回执，不执行、不重放。

### 3.7 删除任务配置的详细时序（BU7、UC5）

独立对应业务用例，不展开整体时序的阶段。**【缺口】** 删除没有独立时序图，规则分散在[配置 §4.6、§4.11](configuration.md#schedule-run-read-lifecycle)与[数据库事务](../../03-数据与存储/Claw数据库设计.md#transactions)。删除与最终受理的竞态（删除先提交则不受理；受理先提交则保留 Session 并删除 Run）是本模块最容易出错的交互之一，建议补一张详细时序图。

<a id="no-catch-up"></a>

### 3.8 时间规则与不补跑

Cron 字段、timezone 默认值与校验以[配置 §3](configuration.md#3-配置字段与时间规则)为准。支持秒位不表示服务在该秒准时开始，线程排队、系统负载和 JVM 暂停都可能带来延迟。

**是否运行只看计划时刻与数据库当前时刻之差。** 各副本每秒扫描 upcoming_run_at 不晚于数据库当前时刻的 active 任务：

- 差值不超过 5 秒派发容差，按正常派发处理。例如计划 08:00:00、08:00:01 才扫描到，仍正常受理，不算补跑。
- 差值超过 5 秒（停机、扫描停顿或数据库不可用后恢复），不运行、不记录 Run，直接把游标推进到当前时刻之后的下一次计划；不补最近一次，也不逐个补造历史计划。
- 机会因繁忙、容量不足或权限失败而未受理时，记录对应 Run 并前移游标，不为同一 occurrence 入队或重试。

不维护扫描领跑者、全局扫描代次或恢复边界：锁内复核游标后推进，其他副本拿不到锁或看到游标已推进就跳过，`UNIQUE(schedule_id, scheduled_at)` 是最终防重。GaussDB 不支持 `SKIP LOCKED` 时退回 `FOR UPDATE`，只多等待锁。代价是每个副本每秒扫描一次，查询量随副本数增加，扫描走 `idx_schedule_due`。

准备中、从未受理且 lease_until 已过的 Run，由清理在锁内写入 finished_at 并记录未能受理，不由其他副本重新准备执行；其他副本接替的是未来调度，不是旧执行。恢复后的副本不能删除或重发已受理的 Session。

夏令时目标为缺失钟面跳过、重复钟面对应两个不同 UTC occurrence；须以当前 JDK/Spring 边界测试验收。首次无未来匹配拒绝保存；既有规则耗尽时清空游标。

<a id="new-session-per-run"></a>

### 3.9 每次运行新建 Session

| 边界 | 当前目标 |
|---|---|
| 配置绑定 | Agent 身份、纯文本 prompt、可选 Cron 规则；不接收 target、sessionId 或 chatId |
| Agent 与 Session | 复用已绑定的 Agent 定义，每次自动或手动运行新建独立 Session 与运行实例；不新建 Agent 定义资源 |
| 消息上下文 | 新建空历史，再把 prompt 作为首条用户消息提交；不复制其他 Run 的聊天历史，共享受管资源和业务状态仍遵守各自边界 |
| 模型与模式 | 当前已发布 Agent default，thinking=OFF，CRON profile，build 入口；不能复用现有 HTTP 创建默认 thinking=true 的入口 |
| 配置刷新 | 使用本次 prepare 的不可变快照，不承诺 Agent 版本固定或每次远端最新 |
| 对其他聊天的影响 | 不向已有 Session 追加定时输入；新 Session 完成后可供有权限的用户继续聊天，但不成为后续定时触发目标，也不改写本次 Run 的结果 |

Cron 的 build 表示非计划执行模式；首版继续使用该入口的 basePrompt，不因后台持久化而自动追加交互 BUILD 提示词，依据见[证据 J10](source-evidence.md#java-evidence)。

<a id="noninteractive"></a>

### 3.10 无需人工交互的执行范围

首版定时执行仅支持无需人工交互的工作，工具调用仍按“可信目标解析→参数校验→权限判断→业务执行→结果回传”推进。框架默认不装配提问和计划审核工具；Host 还须识别业务权限 ASK、自定义问题准备结果及误配的交互工具，不能仅按工具名屏蔽。需要人工处理时，先阻止待确认业务调用，记录真实失败结果与原因，再结束本次根执行；不创建等待卡、不返回默认答案或批准，也不允许模型改名重试绕过。

参数错误不属于人工交互：仍在权限判断前返回同次可信定义与 isError=true，保持 [M03](../02-CampusClaw工具系统/README.md#tool-argument-recovery) 的修参规则。结束执行不回滚此前已发生的业务操作；可靠终态提交后释放任务占用，本次失败不自动重跑。

非交互限制沿根执行传递到其 Child 执行，不能通过子会话或工具别名绕过。根执行结束按既有取消域收尾已启动子任务；未确认终止的调用仍按停止中或未知处理。业务配置应只选择输入完整、权限已具备且无需人工决定的任务；创建时可发现的明显不支持项应拒绝，运行时仍按可信能力和实际权限兜底。首版不新增持久等待检查点、交互恢复器或无人审批队列。

附件首版不支持：prompt 是纯文本，无法携带文件，也不保存 fileId。普通 Session 既有文件引用契约不受影响；附件长期授权和跨 Session 复用留待 M09 单独设计。

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

<a id="security"></a>

### 5.1 安全性

- 用户、组织、租户、资源归属与权限由 Mate 维护并执行。Claw 不解析或保存用户、scope、owner、operator，收到 Mate 可信服务请求后只校验服务来源、具体操作和目标资源，再检查自己的输入与状态，规则见[配置 身份与权限边界](configuration.md#mate-access-boundary)。
- 首版列表由 Mate 拉取全部后按用户过滤、排序和分页（D9）；Claw 加 userId 见 T10。
- 用户权限只在配置任务时由 Mate 检查；运行时所有定时任务统一使用 Mate 配置的同一个账号，不再按用户查询执行资格（D10）。
- 新 Session 在受理前由 Mate 独立登记归属；登记失败或结果未知时不启动，删除 Schedule/Run 不删除该归属。
- Claw 不持久化凭据引用或 Token。模型一次返回中有需要凭据的工具调用，并且至少一个通过可信解析、参数校验和权限判断时，执行 Adapter 无入参向 Mate 取一次统一账号的 `access-token`，本批共用，只透传这一项；只含无凭据工具、参数错误或权限 ASK 时不取。取 Token 失败时本批需要凭据的工具都不执行，按工具失败返回模型。秘密只在受限执行内存中使用，不进入模型、metadata、Schedule/Run、事件或日志。普通 HTTP 消息仍沿用 [M06 当次 Header 快照规则](../01-CampusClaw多Agent运行时/chat-http-v1-design.md#credential-forwarding)。
- metadata 不进入模型输入，不作为身份、权限或凭据依据。
- 资源级不可见统一返回 404，不泄露存在性。
- Mate 公共展示边界（非本次 Claw 契约）：公共任务详情使用公共任务/Run 标识与 Chat 链接，Run 的内部 sessionId、executionId 不直接暴露；映射未完成显示“结果入口准备中”，不能重复触发任务。
- 已知差距：PR #332 仍有本地身份链路，见[职责核验](source-evidence.md#mate-boundary-review)；配额准入与归属登记的内部契约待实现（T7）。

### 5.2 稳定性

<a id="failure-recovery"></a>
<a id="failure-interaction-recovery"></a>

#### 5.2.1 失败处理与恢复

**不变量**（任何失败都不能破坏）：

1. 受理事务提交前不调用模型或业务工具；远端调用不持有数据库行锁。
2. 同一 Schedule 最多一条未结束 Run，结果未知也占用。
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
| F4 | 准备被拒（Agent 禁用、容量、准备超时） | 受理前 | 未发生，无 Session | 调度器 | 记录 Run.error 并结束 Run，不重试 | Run 显示失败原因；手动运行仍返回 200 Run；自动任务等下一计划 | 是否因此自动暂停 Schedule 待定（T1） |
| F5 | 上一次运行未结束（含结果未知） | 领取 | 未发生 | 调度器 | 记录已结束的忙跳过 Run，前移游标 | Run 显示跳过原因 | 不排队，不补跑 |
| F6 | 停机或扫描停顿使计划时刻超过 5 秒容差 | 领取 | 未发生 | 调度器 | 不运行，游标推进到当前之后的下一次计划 | 停机期间没有 Run，只有运营指标和日志 | 不补跑；不超过 5 秒的延迟按正常派发处理 |
| F7 | 已受理，原实例在执行开始前失联 | 启动前 | 受理已提交，执行可能未发生 | 调度器，必要时人工 | 与 F8 相同，按结果未知保持占用，不转交新节点执行 | 运营视图标注未知 | 不持久化启动权，无法自动证明未启动；自动恢复见 T9 |
| F8 | 执行开始后失联、回执丢失或工具结果不明 | 执行中 | 未知 | 调度器，必要时人工 | 保持“结果未知”，保持占用，只读对账 | 运营视图标注未知；需对账或经授权的人工处置 | 不保证 exactly-once；可能漏执行一次 |
| F9 | 模型或业务执行失败 | 执行中 | 部分发生（已执行的业务不回滚） | Runtime | 保存根执行真实终态，结束 Run 释放任务，不重跑 | 从 Session 查看失败；下一计划照常 | 不回滚已发生的园区业务；是否自动暂停待定（T1） |
| F10 | 遇到权限 ASK、提问或计划审核 | 执行中 | 待确认调用未执行，此前操作已发生 | Host | 阻止该调用，结束本次根执行，记录需人工处理的原因 | Session 中可见原因；需改为非交互任务 | 不创建等待卡，不默认批准 |
| F11 | 删除与最终受理竞争 | 受理 | 删除先提交：未发生；受理先提交：Session 已创建 | 数据库行锁 | 删除先提交则不受理；受理先提交则保留 Session、删除 Run | Run 与 Schedule 404，从 Session 入口查看或停止 | 删除不取消已受理执行 |
| F12 | 单次运行超过 30 分钟 | 执行中 | 部分发生 | 调度器 | 向原根执行请求停止 | 停止未确认前显示停止中或未知 | 停止请求不等于已终止 |
| F13 | 删除后晚到的完成或失败回调 | 收尾 | 已提交（Session 侧） | 调度器 | 条件更新影响 0 行即视为资源已删，只收尾 Session 与根执行 | 无 | — |
| F14 | Mate 归属登记被拒或结果未知 | 受理前 | 被拒：未发生；未知：Mate 侧可能已登记，Claw 未受理 | 调度器 | 停止本次受理，按固定 Run 与 Session ID 只读核对；不新建 Session、不重放 | Run 显示未受理原因；结果未知时保持占用直至核对完成 | 无跨库事务，Mate 侧可能留下待核对的登记 |

不重跑不等于不对账：只读查询已有结果、幂等落地已确认终态、清理已结束资源可以继续重试，它们不调用模型或产生新的园区业务请求。未知执行不得因固定期限到期就写入 Run.finished_at，必须取得根执行终态或经独立授权的人工处置才解除占用。若根执行现有枚举不包含“未知”，运营视图须明确标注，不能把 Run 的受理错误冒充 Session 业务终态。

#### 5.2.2 容量与限流

- 不新增服务进程：定时任务运行在现有 coding-agent 进程内，多副本都能承载执行，也都扫描到期任务，以行锁和唯一约束防止重复分配。
- 数据库是调度状态的最终决定方，定时器、执行线程、扫描缓存和本地计时均可丢弃。

<a id="deployment-defaults"></a>

首版部署初始值由部署配置控制，不新增 Schedule 公共字段，未经压测，不代表容量：

| 配置 | 初始值 | 语义 |
|---|---:|---|
| 自动扫描周期 | 1 秒 | 期望扫描频率，不是精确启动承诺 |
| 自动派发容差 | 5 秒 | 计划时刻与数据库当前时刻之差的上限；超限不运行、不排队、不补跑，游标推进到下一次 |
| 扫描批量 | 100 条 | upcoming_run_at/id 有序、有界扫描；不按用户/租户分组，跨租户公平策略归 Mate |
| 每任务并发 | 1 | 自动和手动共享；结果未知也占用 |
| Cron 时间分辨率 | 1 秒 | 沿用六字段能力；不承诺每秒任务均有容量 |
| Mate 每管理范围任务数 | 100 个 | 由 Mate 配额准入维护，Claw 不计数 |
| 每实例定时活动执行上限 | 8 个 | 独立调度配额，且必须同时取得既有 Runtime 容量，不能绕过交互任务容量保护 |
| 受理准备期限 | 10 秒 | 准备超时只记本次失败；自动受理取它与 scheduled_at 加 5 秒中较早者，即 Run.lease_until |
| 单次运行上限 | 30 分钟 | 到期向原根执行请求停止；停止未确认仍保持停止中或未知 |
| Run 保留 | 30 天 | 只清理已结束的 Run；未结束 Run 不因到期删除；删除 Schedule 立即删除对应 Run |
| 清理频率 / 批量 | 每小时 / 500 条 | 有界删除；不级联 Session 或正在协调的根执行 |

- 瓶颈：各副本每秒扫描一次，数据库查询量随副本数线性增加；行锁竞争需在多副本下压测。
- 限流：每实例 8 个上限在多副本下会放大总并发（T6）；需要全局硬上限时复用 Runtime 已有的全局准入，不用各实例内存计数器冒充集群限流。
- Run 保留期不决定 Session 的保留期，Session 按所属模块策略管理。
- **【缺口】** 容量目标：全园区预计任务总数、整点等高峰时刻集中触发的数量、可接受的派发延迟。
- **【缺口】** 压测计划：扩容前需按数据库延迟、扫描容差、下游配额与交互任务资源竞争测试，在此之前不写“支持多少任务/并发”。

#### 5.2.3 监控告警

已有要求：停机漏跑只推进游标并输出非敏感运营指标与日志；结果未知在运营视图明确标注，不显示为成功或失败；控制台能定位授权与执行失败；日志不含凭据。

**【缺口】** 没有成体系的指标与告警设计。下列为建议项，待评审确认：

| 建议指标 | 为什么需要 | 建议告警 |
|---|---|---|
| 计划触发数与成功受理数之差 | D4 选择不补跑，漏跑必须可见，否则成为静默故障 | 差值持续大于 0 |
| 跳过次数（按原因：忙、超容差、权限、容量） | 区分“任务太长”与“系统过载” | 同一任务连续跳过 |
| 派发延迟（计划时刻到受理） | 验证 5 秒容差是否合理 | 接近或超过容差 |
| 结果未知的数量与持续时长 | 未知会一直占用任务，后续全部遇忙跳过 | 存在超过单次运行上限的未知 |
| 超容差跳过的计划数 | 停机或扫描停顿造成的漏执行 | 持续出现 |
| 活动执行数 / 每实例上限 | 判断容量是否接近配额 | 持续接近上限 |

#### 5.2.4 应急预案

已有要求：某副本失效后其余副本继续扫描，无需接管；结果未知的运行只有取得根执行终态，或经独立授权的人工处置后才解除占用；切换到新调度器前必须停止旧 CronEngine 并核对旧在途执行。

**【缺口】** 人工处置结果未知的操作入口、权限与审计；数据库长时间不可用时的处置步骤；需要紧急停用全部自动调度时的开关。

### 5.3 兼容性

- 旧进程内 CronEngine（JSON Job / JSONL Run）在新 SQL 调度器启用前必须停止，两套调度不得并行。
- 旧 At/Every 任务不静默转换为 Cron；迁移时由 Mate 建立任务授权关联，缺时区或 Mate 授权的旧 Job 迁移后保持禁用等待补全。
- 现有 CronTool 与 BuiltInToolContracts 各有一份旧 Schema，迁移时同步处理；Cron 工具与 HTTP 委托同一应用服务。现有工具的可选 timezone 在迁移时必须归一化成明确存储值，不静默采用运行节点时区。
- 普通 Session 的消息、文件引用和 Header 快照契约不因定时入口改变。
- Cron 方言采用 Spring 六字段，与 Claude 五字段 POSIX 不兼容，表达式不能直接复制。

## 6. 质量保证

### 6.1 灰度能力

**【缺口】** 没有灰度方案。约束冲突：旧 JSON 调度不得与新 SQL 调度并行，因此不能按实例或流量比例新旧并跑；灰度只能按 Mate 授权范围分批迁移，或先只开放配置接口、不开放自动执行。需要评审决定。

### 6.2 回滚能力

**【缺口】** 没有回滚方案。待回答的问题：模块合并后能否回退到独立 campusclaw-cron；旧 Job 迁移到 SQL 后能否回写 JSON；新调度器停用后在途 Session 如何收尾。

<a id="auto-tests"></a>

### 6.3 自动化测试

验收要求（均未实施）：

- 确定性时间测试：可控时钟验证 08:00:01 正常受理、08:00:06 发现 08:00:00 时跳过、超容差跳过、忙时不排队、DST 缺失跳过与重复钟面按不同 UTC occurrence。
- 故障注入：准备前、提交前、提交后、启动前后、业务调用后，确认无重复 Session、无重复首消息、未知不伪失败、重启不重放。
- 并发：2 副本竞争仅一次受理；手动与自动互斥；暂停/修改/删除与最终受理竞态可线性判定。
- 接口：10 个操作的成功与错误报文、字段边界、Mate 拉取全部后过滤分页，详见[配置 §8](configuration.md#implementation-acceptance)。
- 安全：越权目标资源被拒、每批需要凭据的工具调用只取一次 Token 且只透传 access-token、取 Token 失败时本批不执行、lease_until 过期后拒绝受理、未登记归属不受理、ASK 不被自动放行、日志与历史中无凭据。
- 删除：删除后 Schedule/Run 不可见，Mate 中原 Session 归属仍在且可按当前权限读取，晚到回调不复活资源，Run 清理不删除 Session。
- 工程：reactor verify、corporate 镜像布局、GaussDB 集成与 2 副本联调。

<a id="implementation-slices"></a>

实施切片（均待实现，已有进程内 Cron 不能等价为切片完成）：

| 切片 | 交付与通过条件 |
|---|---|
| S0：模块合并 | 迁移物理模块与包，旧模块/GAV 引用清零、Spring 构造无环、corporate 镜像布局一致；不以搬包替代新运行能力 |
| S1：独立任务管理 | 管理与 Run 契约、DTO/VO、DDL；规则校验与计划时间摘要、最新行字段合并、暂停/恢复/删除可验证；删除后 Schedule 及 Run 404、Session 独立保留 |
| S2：后台原子受理 | 新 Session/首消息/根执行/Run 同事务；故障注入覆盖提交前、提交后和回执丢失；明确 build/CRON、工具权限与 persistenceOnly 接线 |
| S3：持久调度与恢复 | 两副本竞争仅一条受理；暂停/修改/删除与受理竞态可线性判定；时钟、DST、Cron 未来匹配、无补跑、重叠及限流有确定性验证 |
| S4：结果与运营 | 后台完整 Session 历史可读、取消指向原根、未知不显示成功；控制台能定位授权和执行失败 |
| S5：旧 Cron 入口迁移 | 由 Mate 建立任务授权关联；切换时确保旧扫描器停用且旧在途任务已核对，不能双写双执行 |

没有业务执行身份、可靠受理或结果对账时，不验收需要凭据的园区无人值守任务。单元测试存在、确定性测试通过、真实 GaussDB/多副本/企业身份联调分别记录。

### 6.4 QA 流程

**【缺口】** 没有 QA 流程（提测标准、测试环境、准出条件）。已有要求只区分了“单元测试存在、确定性测试通过、真实 GaussDB/多副本/企业身份联调”三类证据需分别记录。

## 7. 基建规范

- 依赖：不新增外部 Maven 依赖，复用 JDK 21、Spring CronExpression、Jackson、MyBatis Spring Boot Starter 3.0.4 与既有数据库驱动；不引入 Quartz、XXL-JOB、Redis 锁或另一 Cron 解析器。
- 对象：Controller 使用 RequestVO/ResponseVO 与 ResultBean；Service 处理默认值、合并与 VO/DTO 转换；Mapper 只收发 DTO，不引入 PO/DO/Entity。
- 数据库：遵循 [Claw 数据库设计](../../03-数据与存储/Claw数据库设计.md#schedule)；`t_` 表名、中文 COMMENT、`TIMESTAMPTZ(0)`、与[秒级时间一致性](../01-CampusClaw多Agent运行时/time-contract.md)对齐。

<a id="module-merge"></a>

### 7.1 模块与依赖方向

定时能力合并进 `modules/coding-agent-cli`，制品继续使用 `campusclaw-coding-agent`。根 Reactor 保留 common、ai、agent-core、coding-agent-cli 四个模块，不再发布独立 campusclaw-cron，也不新增服务进程。

| 位置 | 职责 |
|---|---|
| `codingagent.schedule` | Schedule/Run 应用规则、时间计算、受理准备、扫描派发、结果对账及数据库访问；按职责拆分 application、dispatch、persistence、config 子包 |
| `codingagent.tool.cron` | 将模型工具调用和当前 Agent、Session/执行及目标资源 ID 转换为相同应用服务请求，不保存另一份任务或调度状态 |
| `codingagent.runtimeapi` | HTTP Controller、请求/响应 VO 和既有 Runtime 受理边界；Controller 不直接使用 Mapper、调度线程或模型 |
| `codingagent.session` 与既有 Runtime | Session 创建、根执行、工具权限、终态与消息持久化；定时模块不重做 AgentLoop |
| `agent-core` / `ai` | 保持对宿主的单向依赖，不反向依赖 coding-agent 的定时或企业身份实现 |

RuntimeSessionEngineRegistry 为交互会话装配 CronTool 时，只需要薄管理/受理服务，不注入调度推进器。不得形成 `Registry → CronToolFactory → ScheduleService → Dispatcher → Registry` 构造环，也不以 `@Lazy` 掩盖。

当前独立 cron 有 15 个生产 Java 文件、7 个测试 Java 文件，无独立资源目录。合并时迁移源码和测试，删除根 POM 中模块条目、campusclaw-cron 版本管理项和 coding-agent 对其依赖；更新 `scripts/sync-campusclaw.sh` 的 MODULES、旧 CODEOWNERS 路径和工程文档，再用同步脚本生成 corporate 包树，不双份手工维护。

旧 CronService 是自动启动的 SmartLifecycle。新 SQL 调度器启用前，必须停止旧 CronEngine 和 JSON/JSONL 写入，完成旧在途执行核对。现有 CronTool 和 BuiltInToolContracts 各有一份旧 at/every/cron Schema，迁移需同步处理，不把旧 at/every 数据静默转换成所谓等价 Cron。

coding-agent 已直接依赖 agent-core、Jackson 和测试 Starter，Spring context 由既有依赖提供；如按“直接使用直接声明”补充 spring-context，只调整已有依赖归属。根 POM 的 JobRunr 7.3.1 只是无消费者的版本占位，可在实施全仓复查后清理，不能据此宣称运行包体减少。

<a id="implementation-calibration"></a>

### 7.2 实施校准

Mate 新增接口路径/VO 仍为内部草案，Claw 与 Mate 的服务认证、统一账号配置、Token 有效期与 Mate 归属登记需联调校准（T2）；DDL、原子受理、取消终态和多副本故障测试必须在实现阶段验证（T4）。完整 Maven 依赖树及 corporate NativeParent 尚未核验（T5），不把局部 POM 读取称为依赖审计完成。

<a id="html-maintenance"></a>

### 7.3 HTML 展示页维护

修改 `configuration.md` 后，在仓库根重新生成页面，不手工修改 HTML：

```bash
python3 scripts/render-schedule-api.py
python3 scripts/render-schedule-api.py --check
```

生成器复用 Runtime 接口页的共享渲染器、样式和按操作展开交互，只用 Python 标准库；`--check` 对比完整生成内容。生成同步不等于接口已实施验收。

## 8. 其他补充

### 8.1 基线对照材料

关键决策见 [§2.3](#key-decisions)，Claude 逐项取舍见 [§2.4](#claude-tradeoffs)；多基线调度边界见 [A14](../07-Agent架构对比/README.md#a14)，源码与官方证据见 [source-evidence.md](source-evidence.md)。

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

<a id="spring-scheduling"></a>

### 8.3 Spring 调度背景

固定任务与用户动态任务都可以使用 Spring 六字段，区别在于任务如何注册和管理；Cron 解析器、触发器及调度注解均由已有 `spring-context` 提供，无需另加 Maven 依赖。

| 场景 | 常用方式 | 适用边界 |
|---|---|---|
| 应用预先定义的固定任务 | `@EnableScheduling` + Spring Bean 上的 `@Scheduled` | 适合固定的统计、清理或轮询方法；普通注解绑定不提供用户任务的运行期增删改 |
| 用户运行期创建、修改、取消任务 | 编程式 `TaskScheduler` + `CronTrigger` | 服务读取已保存配置，动态注册任务并保存本地句柄；`ThreadPoolTaskScheduler` 底层使用 JDK 调度线程池 |
| 不依赖 Spring 的延迟或周期任务 | JDK `ScheduledExecutorService` | 支持延迟一次、固定频率和固定延迟，不直接解析 Cron |
| 只校验规则或计算未来时刻 | Spring `CronExpression.parse(...).next(...)` | 只负责计算，不注册线程、不持久化配置 |

固定任务示例（`alarmService` 是业务服务示意，不是 CampusClaw 新增接口）：

```java
@Scheduled(cron = "0 0 8 * * MON-FRI", zone = "Asia/Shanghai")
public void summarizeAlarms() {
    alarmService.summarizeLast24Hours();
}
```

`fixedRate = 10000` 以每 10 秒一次为目标频率；`fixedDelay = 10000` 则在上一次方法完成后再等 10 秒。固定频率不保证过载时仍准点执行。[Spring 调度文档](https://docs.spring.io/spring-framework/reference/integration/scheduling.html) · [JDK 调度说明](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ScheduledThreadPoolExecutor.html)

已观察的 `CronEngine` 采用 **Spring 算时间、JDK 安排执行**：`computeNextDelay` 使用 `CronExpression`，`scheduleJob` 使用 `ScheduledExecutorService.schedule`，`executeAndReschedule` 执行后重新安装计划，见[源码与框架证据](source-evidence.md#spring-scheduling-evidence)。目标不为每条用户任务注册定时器，而是以数据库为权威、由固定周期扫描唤醒（[§3.8](#no-catch-up)）；固定注解本身不解决多实例重复触发、持久化、漏跑、权限或结果对账。

### 8.4 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.48.0 | 2026-10-14 | §3.5 第 2 步改为先登记归属再准备，与受理图一致；第 4 步补每批工具调用取 access-token；术语补计划游标与派发容差。 |
| 0.47.0 | 2026-10-14 | 全局目标类图按入口、应用、端口与适配器、Runtime 分包，补主要职责，删去与正文重复的业务规则图例，去掉已撤销的分发状态表。 |
| 0.46.0 | 2026-10-13 | 去重：§3.3 删除与配置 §5 重复的步骤摘要；§3.8 的 Cron 字段说明改为链接配置 §3；§3.4 增加锚点供配置文档引用。 |
| 0.45.0 | 2026-10-13 | 评审确认 Session 归属登记保留在 Mate；登记接口路径与 VO 仍待定。 |
| 0.44.0 | 2026-10-13 | 定时执行改为统一账号：配置时由 Mate 检查用户权限，运行时每批工具调用前向 Mate 无入参取 access-token；撤销运行时执行资格查询与 authorizationRef。 |
| 0.43.0 | 2026-10-13 | 按评审模板重组为唯一主设计，并入原执行专题与 Claude 逐项取舍，删除重复的重组稿、执行专题与数据库入口文件。 |
| 0.42.0 | 2026-10-13 | 按评审模板重组，补充关键设计决策、整体时序与稳定性章节，新增待定 T9、T10。 |
| 0.41.0 | 2026-10-13 | 首版列表由 Mate 拉取全部后自行过滤分页，Claw 不保存 userId；Claw 加 userId 列为待定 T10。 |
| 0.40.0 | 2026-10-13 | 撤销 PR 在 t_session_executions 上新增的 started_at、execution_context_json 与 schedule_start_*：受理后由原实例在进程内直接启动；lastRunAt 改为受理时刻；受理后任何时刻失联统一按结果未知处理。 |
| 0.39.0 | 2026-10-13 | 撤销扫描协调表与领跑者：各副本并行扫描，行锁与唯一约束防重；超过5秒派发容差的计划直接推进到下一次。 |
| 0.38.0 | 2026-10-13 | Run 撤销 state 与 claim_owner/claim_epoch，未结束由 finished_at 为空表达，受理以 lease_until 防失效准备者。 |
| 0.37.0 | 2026-10-13 | 撤销配置版本 revision 与 activeRunId；同任务不并发改由运行表部分唯一约束保证，受理锁内复核状态与 Agent 绑定并使用最新 prompt。 |
| 0.36.0 | 2026-10-13 | 任务内容 message 改为纯文本 prompt，移除 credentialIds，业务凭据改由 Mate 按 Agent 绑定在运行时决定。 |
| 0.35.0 | 2026-10-10 | 用户归属与权限回归 Mate，Claw 仅维护调度及运行数据并补齐会话登记边界。 |
| 0.34.0 | 2026-10-10 | 定时表及 Session 扩展归入 Claw 全库数据库设计，原文件仅保留导航。 |
| 0.33.0 | 2026-10-10 | 数据库设计独立维护字段、约束、索引和事务，登记 PR #332 的局部实现状态。 |
| 0.32.0 | 2026-10-10 | Cron 与 Child 统一持久 Runtime 链路，Skill 统计复用完整工具结果。 |
| 0.31.2 | 2026-10-09 | 用本次定时运行的执行记录解释根执行，明确会话后续追问不改变任务结果。 |
| 0.31.1 | 2026-10-09 | 按职责归属、权威记录及理由与代价组织定时任务边界说明。 |
| 0.31.0 | 2026-10-08 | 引用定时任务前端场景与Console核验，明确触发方式和生命周期的独立映射。 |
| 0.30.3 | 2026-10-08 | 统一定时图的职责与调用归属，分离触发、共用受理及Runtime执行。 |
| 0.30.2 | 2026-10-08 | 清理Mate独立展示链接，定时任务HTML继续仅展示Claw操作。 |
| 0.30.1 | 2026-10-08 | 定时任务HTML仅展示Claw操作，Mate上下文与凭据接口移至独立页面。 |
| 0.30.0 | 2026-10-08 | 移除独立时间预览，同步接口展示、目标类图及保存后计划时间摘要的验收。 |
| 0.29.2 | 2026-10-08 | 定时接口HTML复用仓库现有接口渲染器、操作折叠和响应状态/语言切换。 |
| 0.29.1 | 2026-10-08 | 增加从现有Claw契约和Mate草案生成的HTML展示入口及同步检查。 |
| 0.29.0 | 2026-10-05 | 确定非交互、无补跑和不重跑策略，明确Mate权威、删除不取消与coding-agent模块合并。 |
| 0.28.0 | 2026-10-05 | 删除Schedule及对应Run并保留Session，明确删除后的读取与收尾边界。 |
| 0.27.0 | 2026-10-05 | 补充其他基线的配置、运行历史及会话删除关系，区分数据清理与执行取消。 |
| 0.26.0 | 2026-10-05 | 区分删除任务配置与清理Run/Session，登记独立历史查询的条件入口和授权边界。 |
| 0.25.0 | 2026-10-05 | 补充手动运行及暂停生命周期入口，明确Run返回受理结果与管理状态/执行状态分离。 |
| 0.24.0 | 2026-10-04 | 删除成功以200返回完整配置回执，区分终止快照、后续读取404与重复删除候选。 |
| 0.23.0 | 2026-10-04 | 配置采用直接删除并退出公开读取，保留内部墓碑及删除与受理协调的候选边界。 |
| 0.22.0 | 2026-10-04 | 增加删除与归档的生命周期审阅入口，区分 Claude 公开归档和 Claw 在途执行候选。 |
| 0.21.0 | 2026-10-04 | Schedule 接口采用独立创建与最新行字段合并，保留内部调度去重并明确超时核对边界。 |
| 0.20.0 | 2026-10-04 | 明确部分配置更新入口、状态保持和完整响应，区分既有 Session 更新基础与新增能力。 |
| 0.19.0 | 2026-10-04 | 完整任务资源增加类型与当前暂停原因，明确状态原子更新及持久化归属。 |
| 0.18.0 | 2026-10-04 | 配置列表与详情返回完整任务资源，明确读取权限、故障处理与独立 Run 观察边界。 |
| 0.17.0 | 2026-10-04 | 定时任务通过 credentialIds 直接绑定独立凭据，集合管理不进入首版范围。 |
| 0.16.0 | 2026-10-04 | 明确凭据绑定属于产品范围，并区分独立凭据和集合引用的命名候选。 |
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
