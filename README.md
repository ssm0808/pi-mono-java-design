# CampusClaw 设计仓库

导航版本 3.50.0 · 2026-10-04

本仓维护 CampusClaw、mate-service 的目标设计、精确契约与源码研究。先读模块主设计了解当前方案，再按需查看契约、证据和专项流程；实现状态以具体源码核验范围为准。

实现状态统一使用“已实现”“待实现”“未核验”，测试验收另列。`ExitPlanMode`、`TodoUpdate`、`AskUserQuestion` 已在 Runtime 主线实现，计划生成、参数流与客户端的最新范围见[计划模式证据 §15](01-总体架构/06-CampusClaw计划模式/source-evidence.md#plan-argument-streaming-evidence)，其他工具保留各自核验归属；Mate 公共桥接与未核验范围分别记录。

[Claw 秒级时间规则](01-总体架构/01-CampusClaw多Agent运行时/time-contract.md) · [Agent 架构对比](01-总体架构/07-Agent架构对比/README.md) · [全部设计图](设计图索引.html) · [工作指引](AGENTS.md)

M03 的[工具注册与发现](01-总体架构/02-CampusClaw工具系统/README.md#9-工具注册与发现)区分 Agent 直接工具代理与 Skill 渐进披露：Skill 工具按 `Skill → SearchTools → CallTool` 使用，按唯一工具名精确返回单个定义，不动态增加模型工具。`Skill`、`CallTool`、代理、[确认前准备和参数恢复反馈](01-总体架构/02-CampusClaw工具系统/source-evidence.md#search-tools-evidence)已在 PR #323 开发提交 `ae6645ca` 实现；SearchTools、发现与校验的一致性接线及[前端可恢复展示](07-前端设计/技术设计/内容渲染.md#tool-argument-recovery-display)待实现。工具数据同步另行设计。

<a id="module-index"></a>

## 1. 模块索引

模块按职责、权威状态和依赖划分。编号是稳定引用，不对应 Maven 制品；沿用现有专题路径，主设计负责导航到下钻内容。

| 模块 | 主设计 | 关联专题与维护边界 |
|---|---|---|
| M01 · Agent Runtime 与多 Agent 编排 | [多 Agent Runtime](./01-总体架构/01-CampusClaw多Agent运行时/README.md) | Loop、Turn、执行生命周期及父子 Session；[计划模式](./01-总体架构/06-CampusClaw计划模式/README.md)维护方案载体、[PLAN.md](./01-总体架构/06-CampusClaw计划模式/PLAN.md)/[BUILD.md](./01-总体架构/06-CampusClaw计划模式/BUILD.md)、[业务模式覆盖](./01-总体架构/06-CampusClaw计划模式/plan-policy.md#11-业务文件优先与独立回退)、审核与续跑；[结构化提问](./01-总体架构/06-CampusClaw计划模式/ask-user-question.md)维护问题、答案与原执行等待；[显式任务事件](./01-总体架构/06-CampusClaw计划模式/todo-update.md)仅用于 build 实施进度；工具装配引用 M03，HTTP 投影引用 M06 |
| M02 · Model | [Model](./02-服务与接口/03-Model/README.md) | Provider 身份、业务 Agent 绑定、[Mate 模型信息与执行快照](./02-服务与接口/03-Model/model-capabilities.md)及流式适配；[共享客户端配置](./02-服务与接口/02-CampusMate共享客户端配置/README.md)维护服务连接配置 |
| M03 · Tool 与受管执行环境 | [工具系统](./01-总体架构/02-CampusClaw工具系统/README.md) | [内置工具契约](./01-总体架构/02-CampusClaw工具系统/built-in-tool-contracts.md)、[注册与渐进发现](./01-总体架构/02-CampusClaw工具系统/README.md#9-工具注册与发现)、[校验与确认顺序](./01-总体架构/02-CampusClaw工具系统/source-evidence.md#tool-validation-order-evidence)、[参数恢复反馈](./01-总体架构/02-CampusClaw工具系统/README.md#tool-argument-recovery)、[工具执行细节](./01-总体架构/02-CampusClaw工具系统/execution-details.md)、[展示名称映射](./01-总体架构/02-CampusClaw工具系统/README.md#tool-display-name)、[凭据透传与工具可用条件](./01-总体架构/02-CampusClaw工具系统/README.md#mate-credential-forwarding)、执行权限与 Session 隔离；AskUserQuestion 的等待生命周期归 M01 |
| M04 · Session 上下文与持久化 | [会话记忆 GaussDB](./03-数据与存储/01-会话记忆GaussDB/README.md) | 单条追加时间线、压缩、恢复与存储，不提供最近对话编辑或同 Session 分支；[pi 上下文研究](./05-研究资料/03-pi会话上下文/README.md)是证据入口，客户端事件历史归 M06 |
| M05 · Command 与 Skill | [Slash Command 通用模块](./04-命令与技能/00-Slash-Command通用模块/README.md) | [当前实现与剩余增量](./04-命令与技能/00-Slash-Command通用模块/README.md#current-runtime-status)；[Builtin](./04-命令与技能/01-内置命令/README.md)、[Skill Command](./04-命令与技能/02-技能命令/README.md)、[使用统计与 Codex 研究](./04-命令与技能/03-Skill加载统计/README.md)与[Help](./04-命令与技能/01-内置命令/Help-Agent使用指南/README.md)分别维护行为 |
| M06 · 事件契约与服务边界 | [Session Events](./01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md) | 内部[请求级 SSE](./01-总体架构/01-CampusClaw多Agent运行时/chat-events-stream-design.md)、[历史](./01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md)、[调用名称快照](./01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md#tool-display-snapshot)与[三类决定消费终态](./01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md#46-已接受决定的消费终态)；[Mate 公共 Chat](./02-服务与接口/07-mate-service通用对话API/README.md)单独维护公共权威契约 |
| M07 · 前端体验 | [前端设计](07-前端设计/README.md) | [八个场景与高低保真原型](07-前端设计/原型/index.html)、[公共规范](07-前端设计/公共规范.md)、[技术设计与全局类图](07-前端设计/技术设计/README.md)、[源码证据](07-前端设计/source-evidence.md)、[发送前自动获取 Token](07-前端设计/技术设计/runtime-workbench-alignment.md#61-页面流程)；用户行为按场景维护，服务契约引用 M06 |
| M08 · Agent 元数据与配置 | [Agent 元数据 GaussDB](./03-数据与存储/02-Agent元数据GaussDB/README.md) | 身份、版本、Agent 默认 mode 及模型/Tool/Skill 绑定；[数据库模式研究](./03-数据与存储/03-Agent数据库模式/README.md)和[元数据草案](./06-元数据草案/README.md)不自动成为已实现契约 |
| M09 · 附件与文件服务 | [CampusMate 附件服务](./02-服务与接口/01-CampusMate附件服务/README.md) | 文件上传、扫描、访问与删除；Runtime 文件引用边界由 M01/M06 引用 |
| M10 · 调度与并发治理 | [定时任务](./01-总体架构/08-CampusClaw定时任务/README.md) | [Claw 配置接口与 Claude 取舍](./01-总体架构/08-CampusClaw定时任务/configuration.md)维护创建、列表、详情、更新、预览；名称上限 256，时间规则仅支持 cron；[Spring 六字段与固定/动态任务](./01-总体架构/08-CampusClaw定时任务/README.md#spring-scheduling)解释解析和调度边界，Cron 默认上海，绝对时刻响应统一 UTC 且无小数秒；[执行目标与文件证据](./01-总体架构/08-CampusClaw定时任务/source-evidence.md#target-file-evidence)区分基线会话策略、文件引用与上传；每次运行固定新建 Session，复用 Agent 定义；[创建响应审阅](./01-总体架构/08-CampusClaw定时任务/configuration.md#creation-response-review)对齐计划时间、小写状态和 metadata，内部版本不外露；[凭据引用取舍](./01-总体架构/08-CampusClaw定时任务/configuration.md#credential-reference-proposal)明确 credentialIds 直接绑定独立凭据，并区分已有 Header 转发与待定的无人值守身份，试运行契约及执行恢复待细化；Runtime 准入归 M06，[并发图源](./01-总体架构/03-虚拟线程并发管理/diagram.puml)补充容量结构 |
| M11 · 可观测性与测试 | [TDD 测试 Agent](./02-服务与接口/05-CampusClaw-TDD测试Agent/README.md) | [调用日志](./01-总体架构/05-CampusClaw调用日志/README.md)、[Runtime HTTP 测试](./02-服务与接口/04-Runtime-HTTP测试Agent/README.md)；区分验收要求、已有测试与实测结果 |

## 2. 按阅读目的下钻

| 目的 | 入口与维护边界 |
|---|---|
| 了解架构取舍 | [Agent 架构对比](01-总体架构/07-Agent架构对比/README.md)：基线做法、差异原因、代价和实现状态，复用模块主图 |
| 计划流式生成与审核 | M01 [计划流式输出](01-总体架构/06-CampusClaw计划模式/plan-streaming.md)：完整 plan 参数、专用参数增量与审核绑定；调整待实现；复用已实现的 M06 两 phase 与 M07 卡片，不新增通用工具参数公开流 |
| 核对 Runtime HTTP 报文 | [统一接口页](01-总体架构/01-CampusClaw多Agent运行时/chat-api-review.html)；[catalog](01-总体架构/01-CampusClaw多Agent运行时/接口契约/catalog.json) 指定唯一精确源 |
| 核对公共 Chat 契约 | [Mate Chat](02-服务与接口/07-mate-service通用对话API/README.md)：公共流与历史独立维护；未整合要求见其待决事项 |
| 浏览器重开后继续流式输出 | M06 [Redis 流式恢复](01-总体架构/01-CampusClaw多Agent运行时/redis-stream-recovery.md)：事件源侧快照与短期 Stream、跨副本读取、故障边界及入门解释；接口增量为 proposed，能力待实现 |
| 查看图与源文件 | [设计图索引](设计图索引.html)：按专题检索、适配文档宽度或查看原尺寸，直接定位 PlantUML |
| 追溯源码事实 | 各模块的源码证据；[研究资料](05-研究资料/README.md)提供基线分析，不能把研究候选当作当前产品决定 |
| 查看元数据草案 | [元数据草案](06-元数据草案/README.md)：标明草案用途，以所属模块契约决定生效范围 |

## 3. 目录与维护

[总体架构](01-总体架构/README.md) · [服务与接口](02-服务与接口/README.md) · [数据与存储](03-数据与存储/README.md) · [命令与技能](04-命令与技能/README.md) · [研究资料](05-研究资料/README.md)

物理目录保留稳定分类；不按需求批次、会话或 PR 增加长期目录。主文只陈述当前方案、理由与必要差距；精确报文由契约源维护，图由同专题 diagram.puml 生成，旧方案与交付过程通过 Git 追溯。完整约定见 [AGENTS.md](AGENTS.md)，Runtime 生成流程见 [接口维护](01-总体架构/01-CampusClaw多Agent运行时/chat-api-index.md)。

时序图按[统一表达规范](时序图规范.md)维护：参考 [DSH 的角色协作表达](时序图规范.md#dsh-style)，一图一场景，先说明职责和主流程，再按需下钻；参与者按场景选择，不固定套用类名或角色名单。

更新图源后在所属目录运行 `plantuml -tsvg diagram.puml`，再在仓库根运行 `python3 scripts/render-diagram-index.py` 更新图索引。运行 `python3 scripts/check-diagrams.py --render` 检查图源、生成同步与引用；图形校验须结合原尺寸与文档缩放的视觉检查。

## 4. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 3.50.0 | 2026-10-04 | M10 明确 credentialIds 直接绑定独立凭据，并链接请求、响应及基线取舍。 |
| 3.49.0 | 2026-10-04 | M10 创建响应补齐时间摘要、metadata 与凭据引用取舍入口。 |
| 3.48.0 | 2026-10-04 | M10 固定每次新建 Session，并提供创建响应与 Claude 对齐入口。 |
| 3.47.0 | 2026-10-04 | M10 收敛为仅 Cron，名称上限对齐 256，补充文件与会话目标证据入口。 |
| 3.46.0 | 2026-10-02 | Session、完整事件与定时任务统一秒级时间，并同步存储目标。 |
| 3.45.0 | 2026-09-30 | M10 导航明确绝对时刻响应统一 UTC 并固定三位毫秒。 |
| 3.44.0 | 2026-09-30 | M10 导航明确 Cron 默认上海和绝对时间自带偏移量。 |
| 3.43.0 | 2026-09-30 | M10 增加时区字段与默认来源的基线入口。 |
| 3.42.0 | 2026-09-30 | M10 导航明确创建 every 时省略 startAt 默认先等待一个完整间隔。 |
| 3.41.0 | 2026-09-30 | M10 导航明确 every.startAt 可选且默认首次时间待定。 |
| 3.40.0 | 2026-09-30 | M10 导航明确 every 按固定时间表触发。 |
| 3.39.0 | 2026-09-30 | M10 导航明确 cron、at、every 的支持范围与待定的间隔语义。 |
| 3.38.0 | 2026-09-30 | M10 增加 Spring 六字段及固定注解、动态编程式调度的阅读入口。 |
| 3.37.0 | 2026-09-29 | M10 配置入口限定为 Claw 五接口及 Claude 取舍，不定义 Mate 或页面方案。 |
| 3.36.0 | 2026-09-29 | M10 增加配置页面、公共接口、唯一存储及并发编辑的端到端入口。 |
| 3.35.0 | 2026-09-29 | M10 建立定时任务主设计，按 Claude 分离任务、触发与会话并优先支持独立会话。 |
| 3.34.0 | 2026-09-28 | 计划模式采用完整工具参数与专用流式预览，保持审核接口和其他工具公共边界。 |
| 3.33.0 | 2026-09-22 | M03 的 SearchTools 收敛为精确名称发现，加载与数据同步留给后续专题。 |
| 3.32.0 | 2026-09-22 | M03 的 Skill 工具改用固定 SearchTools 渐进发现并保持模型工具集合不变。 |
| 3.31.1 | 2026-09-22 | M05 增加固定基线下的当前实现与剩余增量状态入口。 |
| 3.31.0 | 2026-09-22 | 时序图规范增加 DSH 角色协作参考、职责映射与适用边界。 |
| 3.30.0 | 2026-09-22 | 全仓时序图按职责级单场景表达，增加统一规范和生成引用检查。 |
| 3.29.0 | 2026-09-22 | M03 固定 CallTool 业务校验、交互确认与不可变快照执行的顺序。 |
| 3.28.0 | 2026-09-22 | M03/M07 增加参数校验失败的模型恢复反馈与前端可恢复展示入口。 |
| 3.27.0 | 2026-09-22 | M06 增加 Redis 快照与短期事件流的浏览器重开恢复设计入口。 |
| 3.26.0 | 2026-09-22 | M04 收敛为单条追加时间线，并同步 M06 非递归历史查询入口。 |
| 3.25.1 | 2026-09-21 | M03 主文增加完整工具场景，Session、Pipeline 与批次时序归入执行细节。 |
| 3.25.0 | 2026-09-20 | M03 增加 Agent 工具代理、Skill 渐进发现与 CallTool 的设计入口。 |
| 3.24.0 | 2026-09-19 | 计划流式专题采用后端标记解析和同身份 delta/completed。 |
| 3.23.0 | 2026-09-19 | 模型窗口按新执行查询，Mate 统一控制普通调用与摘要输出。 |
| 3.21.0 | 2026-09-19 | M02 增加 Mate 按模型能力查询、快照发布及可选输出上限入口。 |
| 3.20.0 | 2026-09-19 | 增加计划正文流式生成、来源消息绑定与审核卡合并的专题入口。 |
| 3.19.0 | 2026-09-19 | 增加 Claw 凭据透传与工具可用条件入口，区分开发工作台刷新策略。 |
| 3.18.0 | 2026-09-19 | M07 增加开发写动作发送前自动获取 Token 与运行期边界入口。 |
| 3.15.0 | 2026-09-18 | 前端设计迁入独立目录，按八个场景提供高低保真原型与行为说明。 |
| 3.14.0 | 2026-09-17 | M03/M06/M07 统一工具名称映射、事件快照与前端展示入口。 |
| 3.13.0 | 2026-09-17 | M07 工具标题入口明确优先展示 displayName。 |
| 3.12.0 | 2026-09-17 | M07 增加 CallMateTool 具体工具标题的设计入口。 |
| 3.11.2 | 2026-09-17 | 模型模块统一命名为 Model，同步目录与导航引用。 |
| 3.11.1 | 2026-09-17 | 模型模块采用简化目录和文档名称，同步所有设计入口。 |
| 3.11.0 | 2026-09-17 | M02 导航明确业务 Agent `settings.json` 是唯一模型来源。 |
| 3.10.0 | 2026-09-17 | M01 导航纳入业务 Agent 模式提示词覆盖规则。 |
| 3.9.0 | 2026-09-17 | M01 导航直接提供 PLAN.md/BUILD.md 两份模式正文。 |
| 3.8.0 | 2026-09-16 | M05 导航同步按根执行去重的 Skill 使用统计。 |
| 3.7.0 | 2026-09-16 | M07 增加统一持久化设置、Build/Plan 与逐题问答导航。 |
| 3.6.0 | 2026-09-15 | M05 导航纳入 Codex 计数机制、调用事实与三表统计方案。 |
| 3.5.0 | 2026-09-15 | 前端导航统一结构化问答、计划审核与 Slash 交互原型。 |
| 3.4.0 | 2026-09-15 | M05 增加 Skill 累计与日统计、排名和趋势设计入口。 |
| 3.3.0 | 2026-09-15 | 模块导航增加结构化提问与原执行续跑。 |
| 3.2.0 | 2026-09-15 | 移除飞书渠道设计及图纸入口，M07 聚焦前端体验。 |
| 3.1.0 | 2026-09-15 | 前端模块增加计划模式、Codex 交互对齐与可操作工作台导航。 |
| 3.0.1 | 2026-09-15 | 计划模式补充方案载体与后端显式任务事件导航。 |
| 3.0.0 | 2026-09-14 | 首页以模块为唯一主导航，契约、证据与图索引按用途下钻。 |
| 2.6.8 | 2026-09-14 | 元数据模块维护 Agent 默认 mode，Session 创建复制后独立维护当前模式。 |
| 2.6.7 | 2026-09-14 | 模型模块入口纳入 CampusMate 命名统一、AI 削减与架构对比。 |
| 2.6.6 | 2026-09-14 | 增加计划模式整体交互与提示词入口，明确 TODO 仅跟踪实施进度。 |
| 2.6.5 | 2026-09-14 | 增加 TodoUpdate 工具、事件恢复与基线取舍入口。 |
| 2.6.4 | 2026-09-14 | 计划模式导航明确审核通过事件恢复。 |
| 2.6.3 | 2026-09-14 | 导航补充 Session 部分更新与前端单项调用边界。 |
| 2.6.2 | 2026-09-14 | 同步 Session 更新承载 plan/build 的设计入口。 |
| 2.6.1 | 2026-09-14 | 增加 DeepSeek 计划模式设计、接口增量和全局类图入口。 |
| 2.6.0 | 2026-09-14 | 建立稳定模块索引与独立 Agent 架构对比入口，并明确随模块设计同步维护。 |
| 2.5.3 | 2026-09-07 | 增加 Slash Command 前端交互、评审页与生产协议校验入口。 |
| 2.5.2 | 2026-09-07 | Command 响应复用 Session/Models 资源与 Help 业务字段。 |
| 2.5.1 | 2026-09-07 | 每项规则集中到所属专题，Help 使用派生展示。 |
| 2.5.0 | 2026-09-07 | GET 命令采用轻量字段并保持清单完整。 |
| 2.4.6 | 2026-09-07 | 删除废弃评审页，历史校验使用固定 Git 来源。 |
| 2.4.5 | 2026-09-07 | 当前 API 使用统一入口、源清单与校验。 |
| 2.4.4 | 2026-09-07 | Slash/Builtin 使用完整全局主图，Help 图作为下钻补充。 |
| 2.4.3 | 2026-09-05 | Builtin 与 Skill 采用统一设计、实施和集成验收。 |
| 2.4.2 | 2026-09-04 | 同步 Runtime 1.45.0 与已确认 Help Agent 元数据指南入口；不改变其他命令或 Mate 公共契约。 |
| 2.4.1 | 2026-09-04 | 明确 Builtin/Skill 的开发与共享发布边界。 |
| 2.4.0 | 2026-09-04 | Builtin 使用普通 JSON 与窄职责领域服务。 |
| 2.3.8 | 2026-09-02 | 增加端口隔离确认后的完整工具交互示例。 |
| 2.3.7 | 2026-09-02 | 增加允许工具调用的完整提交响应示例。 |
| 2.3.6 | 2026-09-02 | 公共 Events 使用连贯的园区巡检说明与示例。 |
| 2.3.5 | 2026-09-02 | 公共 Events 的示例摘要采用业务场景表述。 |
| 2.3.4 | 2026-09-02 | POST 成功响应在 result.event 返回完整用户事件。 |
| 2.3.3 | 2026-09-02 | 公共 toolCallId 使用 OpenAI 调用 ID，并与 eventId 分离。 |
| 2.3.2 | 2026-09-02 | Swagger 分开表达必需上下文 Header 与 JWT/APPKEY 认证选择。 |
| 2.3.1 | 2026-09-02 | 公共 Chat 三接口增加 OpenAPI 3.1。 |
| 2.3.0 | 2026-09-02 | 公共 Chat 分离事件提交、实时流与固定快照历史。 |
| 2.2.0 | 2026-09-01 | 增加公共 Chat Events 提交接口的评审入口。 |
| 2.1.4 | 2026-09-01 | Slash Command 统一使用“命令清单”，Skill 文件位置统一表述为“文件夹”，并同步 Runtime HTTP 1.43.4。 |
| 2.1.3 | 2026-09-01 | Skill 名称对齐 Agent Skills 完整规则，参数限制改为引用普通消息输入约束，并同步 Runtime HTTP 1.43.3。 |
| 2.1.2 | 2026-08-31 | 简化 Slash Command 全套文档表述，同步 Runtime HTTP 1.43.2 导航。 |
| 2.1.1 | 2026-08-31 | 将 Slash Command 用户文案统一为“命令清单”，并同步 Runtime HTTP 1.43.1 导航。 |
| 2.1.0 | 2026-08-31 | 新增 Slash Command 通用模块、Builtin/Skill 新设计、Runtime HTTP 1.43 和 mate-service 公共聊天命令 API 导航。 |
| 2.0.0 | 2026-08-26 | 建立六个分类与专题导航，统一文件、图纸和脚本引用。 |
