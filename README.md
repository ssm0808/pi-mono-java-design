# CampusClaw 设计仓库

导航版本 3.13.0 · 2026-09-17

本仓维护 CampusClaw、mate-service 的目标设计、精确契约与源码研究。先读模块主设计了解当前方案，再按需查看契约、证据和专项流程；实现状态以具体源码核验范围为准。

[Agent 架构对比](01-总体架构/07-Agent架构对比/README.md) · [全部设计图](设计图索引.html) · [工作指引](AGENTS.md)

<a id="module-index"></a>

## 1. 模块索引

模块按职责、权威状态和依赖划分。编号是稳定引用，不对应 Maven 制品；沿用现有专题路径，主设计负责导航到下钻内容。

| 模块 | 主设计 | 关联专题与维护边界 |
|---|---|---|
| M01 · Agent Runtime 与多 Agent 编排 | [多 Agent Runtime](./01-总体架构/01-CampusClaw多Agent运行时/README.md) | Loop、Turn、执行生命周期及父子 Session；[计划模式](./01-总体架构/06-CampusClaw计划模式/README.md)维护方案载体、[PLAN.md](./01-总体架构/06-CampusClaw计划模式/PLAN.md)/[BUILD.md](./01-总体架构/06-CampusClaw计划模式/BUILD.md)、[业务模式覆盖](./01-总体架构/06-CampusClaw计划模式/plan-policy.md#11-业务文件优先与独立回退)、审核与续跑；[结构化提问](./01-总体架构/06-CampusClaw计划模式/ask-user-question.md)维护问题、答案与原执行等待；[显式任务事件](./01-总体架构/06-CampusClaw计划模式/todo-update.md)仅用于 build 实施进度；工具装配引用 M03，HTTP 投影引用 M06 |
| M02 · Model | [Model](./02-服务与接口/03-Model/README.md) | Provider 身份、业务 Agent `settings.json` 唯一模型来源与流式适配；[共享客户端配置](./02-服务与接口/02-CampusMate共享客户端配置/README.md)维护服务连接配置 |
| M03 · Tool 与受管执行环境 | [工具系统](./01-总体架构/02-CampusClaw工具系统/README.md) | [内置工具契约](./01-总体架构/02-CampusClaw工具系统/built-in-tool-contracts.md)、工具发现、执行权限与 Session 隔离；AskUserQuestion 的等待生命周期归 M01 |
| M04 · Session 上下文与持久化 | [会话记忆 GaussDB](./03-数据与存储/01-会话记忆GaussDB/README.md) | 分支、压缩、恢复与存储；[pi 上下文研究](./05-研究资料/03-pi会话上下文/README.md)是证据入口，客户端事件历史归 M06 |
| M05 · Command 与 Skill | [Slash Command 通用模块](./04-命令与技能/00-Slash-Command通用模块/README.md) | [Builtin](./04-命令与技能/01-内置命令/README.md)、[Skill Command](./04-命令与技能/02-技能命令/README.md)、[使用统计与 Codex 研究](./04-命令与技能/03-Skill加载统计/README.md)与[Help](./04-命令与技能/01-内置命令/Help-Agent使用指南/README.md)分别维护行为 |
| M06 · 事件契约与服务边界 | [Session Events](./01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md) | 内部[请求级 SSE](./01-总体架构/01-CampusClaw多Agent运行时/chat-events-stream-design.md)、[历史](./01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md)与[三类决定消费终态](./01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md#46-已接受决定的消费终态)；[Mate 公共 Chat](./02-服务与接口/07-mate-service通用对话API/README.md)单独维护公共权威契约 |
| M07 · 前端体验 | [前端体验](./01-总体架构/04-CampusClaw前端体验/README.md) | [工具 displayName 展示](./01-总体架构/04-CampusClaw前端体验/README.md#mate-tool-display)； [开发者设置与热更新](./01-总体架构/04-CampusClaw前端体验/runtime-workbench-alignment.md)、[Build/Plan 与逐题交互](./01-总体架构/04-CampusClaw前端体验/plan-interaction.md)、[问答、计划与命令工作台](./01-总体架构/04-CampusClaw前端体验/plan-workbench.html)；[Slash 交互](./04-命令与技能/00-Slash-Command通用模块/前端设计/README.md)；消费 M06，不另定义事件权威语义 |
| M08 · Agent 元数据与配置 | [Agent 元数据 GaussDB](./03-数据与存储/02-Agent元数据GaussDB/README.md) | 身份、版本、Agent 默认 mode 及模型/Tool/Skill 绑定；[数据库模式研究](./03-数据与存储/03-Agent数据库模式/README.md)和[元数据草案](./06-元数据草案/README.md)不自动成为已实现契约 |
| M09 · 附件与文件服务 | [CampusMate 附件服务](./02-服务与接口/01-CampusMate附件服务/README.md) | 文件上传、扫描、访问与删除；Runtime 文件引用边界由 M01/M06 引用 |
| M10 · 调度与并发治理 | [工具系统](./01-总体架构/02-CampusClaw工具系统/README.md)中的 Cron 与执行入口 | Runtime 准入及控制事务归 M06；[并发图源](./01-总体架构/03-虚拟线程并发管理/diagram.puml)补充容量与背压结构 |
| M11 · 可观测性与测试 | [TDD 测试 Agent](./02-服务与接口/05-CampusClaw-TDD测试Agent/README.md) | [调用日志](./01-总体架构/05-CampusClaw调用日志/README.md)、[Runtime HTTP 测试](./02-服务与接口/04-Runtime-HTTP测试Agent/README.md)；区分验收要求、已有测试与实测结果 |

## 2. 按阅读目的下钻

| 目的 | 入口与维护边界 |
|---|---|
| 了解架构取舍 | [Agent 架构对比](01-总体架构/07-Agent架构对比/README.md)：基线做法、差异原因、代价和实现状态，复用模块主图 |
| 核对 Runtime HTTP 报文 | [统一接口页](01-总体架构/01-CampusClaw多Agent运行时/chat-api-review.html)；[catalog](01-总体架构/01-CampusClaw多Agent运行时/接口契约/catalog.json) 指定唯一精确源 |
| 核对公共 Chat 契约 | [Mate Chat](02-服务与接口/07-mate-service通用对话API/README.md)：公共流与历史独立维护；未整合要求见其待决事项 |
| 查看图与源文件 | [设计图索引](设计图索引.html)：按专题检索、适配文档宽度或查看原尺寸，直接定位 PlantUML |
| 追溯源码事实 | 各模块的源码证据；[研究资料](05-研究资料/README.md)提供基线分析，不能把研究候选当作当前产品决定 |
| 查看元数据草案 | [元数据草案](06-元数据草案/README.md)：标明草案用途，以所属模块契约决定生效范围 |

## 3. 目录与维护

[总体架构](01-总体架构/README.md) · [服务与接口](02-服务与接口/README.md) · [数据与存储](03-数据与存储/README.md) · [命令与技能](04-命令与技能/README.md) · [研究资料](05-研究资料/README.md)

物理目录保留稳定分类；不按需求批次、会话或 PR 增加长期目录。主文只陈述当前方案、理由与必要差距；精确报文由契约源维护，图由同专题 diagram.puml 生成，旧方案与交付过程通过 Git 追溯。完整约定见 [AGENTS.md](AGENTS.md)，Runtime 生成流程见 [接口维护](01-总体架构/01-CampusClaw多Agent运行时/chat-api-index.md)。

更新图源后在所属目录运行 `plantuml -tsvg diagram.puml`，再在仓库根运行 `python3 scripts/render-diagram-index.py` 更新图索引。图形校验须结合原尺寸与文档缩放的视觉检查。

## 4. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
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
