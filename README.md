# CampusClaw / pi-mono-java 设计仓库

> 导航版本：2.6.8<br>
> 更新日期：2026-09-14<br>
> 各模块的设计版本、源码基线和实现状态由模块主设计及架构对比条目分别记录。

本仓库维护 CampusClaw Runtime、mate-service 边界、pi-mono-java 目标设计，
以及相关源码和产品研究。这是设计与契约资料仓库，不是产品源码仓库。

设计以模块为长期维护单位。[模块索引](#module-index)定位主设计，
[Agent 架构对比](./01-总体架构/07-Agent架构对比/README.md)集中解释与各基线的差异、理由、代价和实现进度，
用于设计讨论、架构答辩和面试准备。

## 1. 按问题快速找文档

| 我想了解 | 首选入口 | 继续阅读 |
|---|---|---|
| CampusClaw 整体如何运行 | [多 Agent Runtime 总体设计](./01-总体架构/01-CampusClaw多Agent运行时/README.md) | [HTTP API 设计](./01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md)、[HTTP API 评审页](./01-总体架构/01-CampusClaw多Agent运行时/chat-api-review.html) |
| CampusClaw 与各 Agent 基线有什么架构和实现差异 | [Agent 架构对比](./01-总体架构/07-Agent架构对比/README.md) | [按模块定位主设计](#module-index)、对比条目的源码证据与讲解要点 |
| 如何设计计划、审核方案并跟踪实施进度 | [计划模式目标设计](./01-总体架构/06-CampusClaw计划模式/README.md) | [完整交互](./01-总体架构/06-CampusClaw计划模式/plan_mode_end_to_end.svg)、[提示词](./01-总体架构/06-CampusClaw计划模式/plan-policy.md)、[TodoUpdate 设计](./01-总体架构/06-CampusClaw计划模式/todo-update.md)、[接口增量](./01-总体架构/06-CampusClaw计划模式/interface-delta.md)、[全局目标类图](./01-总体架构/06-CampusClaw计划模式/plan_mode_target_classes.svg) |
| Tool 如何装配、发现和执行 | [CampusClaw 工具系统](./01-总体架构/02-CampusClaw工具系统/README.md) | [内置工具精确契约](./01-总体架构/02-CampusClaw工具系统/built-in-tool-contracts.md) |
| 前端如何展示 Runtime 状态 | [CampusClaw 前端体验设计](./01-总体架构/04-CampusClaw前端体验/README.md) | [前端评审页](./01-总体架构/04-CampusClaw前端体验/frontend-review.html)、[Slash Command 前端专项](./04-命令与技能/00-Slash-Command通用模块/前端设计/README.md) |
| 文件、配置和 Model Manager 边界 | [服务与接口导航](./02-服务与接口/README.md) | 附件服务、共享配置、Provider 契约和 HTTP 测试 Agent |
| 全产品测试与质量门禁 | [CampusClaw TDD 测试 Agent](./02-服务与接口/05-CampusClaw-TDD测试Agent/README.md) | 能力注册表、实时门禁、nightly 维护和测试防弱化 |
| Session、Agent 元数据如何持久化 | [数据与存储导航](./03-数据与存储/README.md) | 会话记忆、Agent 元数据和通用数据库模式 |
| Command 和 Skill Command 如何设计 | [Slash Command 通用模块](./04-命令与技能/00-Slash-Command通用模块/README.md) | [Slash 前端设计与交互评审稿](./04-命令与技能/00-Slash-Command通用模块/前端设计/README.md)、[内置命令](./04-命令与技能/01-内置命令/README.md)、[技能命令](./04-命令与技能/02-技能命令/README.md) |
| 公共聊天命令清单与待评审边界 | [mate-service 聊天命令 API](./02-服务与接口/06-mate-service聊天命令API/README.md) | [公共 HTTP 评审页](./02-服务与接口/06-mate-service聊天命令API/chat-command-v1-review.html)、[内部 Runtime 契约](./01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md) |
| `/help` 介绍什么、元数据从哪里来 | [已确认 Help 使用指南](./04-命令与技能/01-内置命令/Help-Agent使用指南/README.md) | [专项评审页](./04-命令与技能/01-内置命令/Help-Agent使用指南/help-review.html)、[Slash 完整全局目标类图](./04-命令与技能/00-Slash-Command通用模块/设计图/target_slash_command_global_classes.svg) |
| 浏览器如何提交、观察和恢复普通 Chat | [mate-service 通用对话 Events API](./02-服务与接口/07-mate-service通用对话API/README.md) | [三接口契约页](./02-服务与接口/07-mate-service通用对话API/chat-events-v1-review.html)、[OpenAPI 3.1](./02-服务与接口/07-mate-service通用对话API/chat-events-v1.openapi.yaml)、[operation models](./02-服务与接口/07-mate-service通用对话API/接口契约/操作/) |
| 查看 pi 或主流 Agent 平台证据 | [研究资料导航](./05-研究资料/README.md) | 配置生成 Tool/Agent、Anthropic、pi Session 和官方文档 |
| 查看 Agent / Tool / Skill 元数据草案 | [元数据草案导航](./06-元数据草案/README.md) | 三份 JSON 草案 |

## 2. 目录地图

```text
.
├── 01-总体架构/             # Runtime、工具、并发、前端、日志
├── 02-服务与接口/           # 附件、共享配置、Provider、测试与质量
├── 03-数据与存储/           # Session 记忆、Agent 元数据、数据库模式
├── 04-命令与技能/           # Slash 通用模块、内置命令与 Skill Command
├── 05-研究资料/             # 源码分析、产品模型和官方资料
└── 06-元数据草案/           # Agent、Tool、Skill JSON 草案
```

一级目录的数字只用于固定阅读顺序；二级目录是可独立理解的设计专题。
每个专题优先从 `README.md` 进入，再按需查看 `设计图/`、`接口契约/`、
`操作/`、`页面资源/` 或 `示例/`。文件名中保留产品名、协议名和稳定的机器契约名，
以避免破坏生成脚本和外部语义。

Session 名称、模型、思考与模式采用部分更新，前端每次单项提交，接口允许组合；契约见[Runtime Session POST](01-总体架构/01-CampusClaw多Agent运行时/chat-api-review.html#updateSession)，其与各 Agent 基线的取舍见[架构对比 A04](01-总体架构/07-Agent架构对比/README.md#a04)。

<a id="module-index"></a>

### 2.1 模块索引

模块编号是稳定的引用标识，不对应 Maven 制品，也不要求移动现有目录。
主设计维护模块职责与目标，关联专题承接细节；研究资料提供证据，架构对比解释取舍。

| 模块 | 主设计 | 关联专题与维护边界 |
|---|---|---|
| M01 · Agent Runtime 与多 Agent 编排 | [多 Agent Runtime](./01-总体架构/01-CampusClaw多Agent运行时/README.md) | Loop、Turn、执行生命周期及父子 Session；[计划模式](./01-总体架构/06-CampusClaw计划模式/README.md)维护规划/实施 Prompt、审核、续跑及仅 build 实施阶段的 TODO 增量；工具装配引用 M03，HTTP 投影引用 M06 |
| M02 · 模型与 Provider | [模型管理 Provider 契约](./02-服务与接口/03-模型管理Provider契约/README.md) | 默认仅内置 CampusMate、Provider 扩展与模型预置削减；[共享客户端配置](./02-服务与接口/02-CampusMate共享客户端配置/README.md)维护服务连接配置 |
| M03 · Tool 与受管执行环境 | [工具系统](./01-总体架构/02-CampusClaw工具系统/README.md) | [内置工具契约](./01-总体架构/02-CampusClaw工具系统/built-in-tool-contracts.md)、工具发现、执行权限与 Session 隔离 |
| M04 · Session 上下文与持久化 | [会话记忆 GaussDB](./03-数据与存储/01-会话记忆GaussDB/README.md) | 分支、压缩、恢复与存储；[pi 上下文研究](./05-研究资料/03-pi会话上下文/README.md)是证据入口，客户端事件历史归 M06 |
| M05 · Command 与 Skill | [Slash Command 通用模块](./04-命令与技能/00-Slash-Command通用模块/README.md) | [Builtin](./04-命令与技能/01-内置命令/README.md)、[Skill Command](./04-命令与技能/02-技能命令/README.md)与[Help](./04-命令与技能/01-内置命令/Help-Agent使用指南/README.md)分别维护行为 |
| M06 · 事件契约与服务边界 | [Session Events](./01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md) | 内部[请求级 SSE](./01-总体架构/01-CampusClaw多Agent运行时/chat-events-stream-design.md)与[历史](./01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md)；[Mate 公共 Chat](./02-服务与接口/07-mate-service通用对话API/README.md)单独维护公共权威契约 |
| M07 · 前端与渠道 | [前端体验](./01-总体架构/04-CampusClaw前端体验/README.md) | [Slash 交互](./04-命令与技能/00-Slash-Command通用模块/前端设计/README.md)、[飞书渠道](./01-总体架构/01-CampusClaw多Agent运行时/channel-feishu-v1-design.md)；消费 M06，不另定义事件权威语义 |
| M08 · Agent 元数据与配置 | [Agent 元数据 GaussDB](./03-数据与存储/02-Agent元数据GaussDB/README.md) | 身份、版本、Agent 默认 mode 及模型/Tool/Skill 绑定；[数据库模式研究](./03-数据与存储/03-Agent数据库模式/README.md)和[元数据草案](./06-元数据草案/README.md)不自动成为已实现契约 |
| M09 · 附件与文件服务 | [CampusMate 附件服务](./02-服务与接口/01-CampusMate附件服务/README.md) | 文件上传、扫描、解析与删除；Runtime 文件引用边界由 M01/M06 引用 |
| M10 · 调度与并发治理 | [工具系统](./01-总体架构/02-CampusClaw工具系统/README.md)中的 Cron 与执行入口 | Runtime 准入及控制事务归 M06；[并发图源](./01-总体架构/03-虚拟线程并发管理/diagram.puml)补充容量与背压结构 |
| M11 · 可观测性与测试 | [TDD 测试 Agent](./02-服务与接口/05-CampusClaw-TDD测试Agent/README.md) | [调用日志](./01-总体架构/05-CampusClaw调用日志/README.md)、[Runtime HTTP 测试](./02-服务与接口/04-Runtime-HTTP测试Agent/README.md)；区分验收要求、已有测试与实测结果 |

认证、租户隔离、凭据传递和审计是跨模块产品约束，按实际权威边界在 M06、M03、M09、M11 中定义并交叉引用。
新增专题先确定所属模块；多个模块共同变更时分别更新主设计，并在架构对比中关联同一差异条目。

## 3. Runtime 契约权威顺序

1. [当前接口清单](./01-总体架构/01-CampusClaw多Agent运行时/接口契约/catalog.json) 唯一登记当前接口及其精确 JSON 源；首页不重复维护接口数量。
2. [统一接口页](./01-总体架构/01-CampusClaw多Agent运行时/chat-api-review.html) 是唯一当前接口详情入口；确认状态与实施边界在所属模块维护。
3. [统一维护规则](./01-总体架构/01-CampusClaw多Agent运行时/chat-api-index.md) 管理权威顺序、生成、校验及旧入口退役。Markdown 负责设计原因与源码证据，不维护平行报文。
4. 废弃的 Claw v1/v2 评审页直接删除，不保留迁移页或跳转占位；历史仅从 Git 追溯。Runtime HTTP 测试 Agent 的旧清单仅为固定提交的历史实现回归，不能证明当前 v2 已实现。

Runtime HTTP V1 不维护 OpenAPI。CampusMate 附件服务仍维护独立的
[`attachment-api.openapi.yaml`](./02-服务与接口/01-CampusMate附件服务/attachment-api.openapi.yaml)，
两者不可混用。

mate-service 聊天命令只保留已确认的 GET Descriptor 投影；公共边界与执行协议待独立重审。
旧 POST SSE 的模型、正文与图已删除，不保留可调用历史副本。
入口为 [Mate GET 设计](./02-服务与接口/06-mate-service聊天命令API/README.md)，
共享字段由 Slash 专题维护，Help 专项页面从 Runtime 契约直接生成。

mate-service 通用对话 Events API 已确认事件提交、Chat 级 live SSE 和固定快照历史三个
operation；standalone HTML 是主要人类契约，OpenAPI 3.1 是同步的机器契约，均位于
[`02-服务与接口/07-mate-service通用对话API/`](./02-服务与接口/07-mate-service通用对话API/)。

## 4. 文档维护约定

- 新专题先确定模块归属及主设计，再选择一级中文分类和中文专题目录；不再向根目录平铺设计文件。
- 专题入口统一使用 `README.md`，根 README 和所属分类 README 同时增加导航。
- 模块内容、架构对比及同步要求见 [工作指引](AGENTS.md#按模块维护设计与-agent-架构对比)；每次架构变更同步维护受影响的比较条目。
- 设计图使用 PlantUML，每个图纸专题保留一份 `diagram.puml`，并提交生成后的 SVG。
- `.puml` 内容只使用英文 ASCII；中文路径在源证据注释中使用 URL 百分号编码。
- 代码对齐的设计必须记录源码 commit、仓库相对路径以及相关符号或基线行号。
- 明确区分已观察源码行为、目标设计、产品约束、安全加固和架构改造。
- 数据库表使用 `t_` 前缀和小写 snake_case；SQL `COMMENT ON` 使用中文。

## 5. 维护命令

Runtime HTTP 契约变更后：

```bash
cd '01-总体架构/01-CampusClaw多Agent运行时'
python3 render_chat_api.py
python3 validate-chat-api.py --full
```

单个图纸专题变更后，在其 `diagram.puml` 所在目录执行：

```bash
plantuml -tsvg diagram.puml
```

## 6. 已废弃方案

当前目标不再使用浏览器 WebSocket、AsyncAPI、连接级 resume、公开 Run、Run Events、
RunRecord 或历史 Run-based Channel 模型。旧内容只用于 Git 历史追溯，新实现不得恢复这些模型。

## 7. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.6.8 | 2026-09-14 | 元数据模块维护 Agent 默认 mode，Session 创建复制后独立维护当前模式。 |
| 2.6.7 | 2026-09-14 | 模型模块入口纳入 CampusMate 命名统一、AI 削减与架构对比。 |
| 2.6.6 | 2026-09-14 | 增加计划模式整体交互与提示词入口，明确 TODO 仅跟踪实施进度。 |
| 2.6.5 | 2026-09-14 | 增加 TodoUpdate 工具、事件恢复与基线取舍入口。 |
| 2.6.4 | 2026-09-14 | 计划模式导航明确审核通过事件恢复。 |
| 2.6.3 | 2026-09-14 | 导航补充 Session 部分更新与前端单项调用边界。 |
| 2.6.2 | 2026-09-14 | 同步 Session 更新承载 plan/build 的设计入口。 |
| 2.6.1 | 2026-09-14 | 增加 DeepSeek 计划模式设计、接口增量和全局类图入口。 |
| 2.6.0 | 2026-09-14 | 建立稳定模块索引与独立 Agent 架构对比入口，并明确随模块设计同步维护。 |
| 2.5.3 | 2026-09-07 | 新增 Slash Command 前端专项导航：独立 Composer 状态、目录、草稿、临时结果、错误恢复、可访问性、交互评审页与生产协议门禁。 |
| 2.5.2 | 2026-09-07 | Runtime Command 响应对齐既有 Session/Models 资源；Help 保留三个业务字段，相关专题和派生页面同步，全局类图不变。 |
| 2.5.1 | 2026-09-07 | 清除废止与重复文档，明确专题单一维护职责；Help 派生展示，Mate 仅保留有效 GET 投影和待评审边界。 |
| 2.5.0 | 2026-09-07 | 整合遗漏的轻量 GET 字段设计，保留后续 Help/POST/Events；增加未合入分支的语义核查记录。 |
| 2.4.6 | 2026-09-07 | 删除四个废弃 Claw 评审页，不保留跳转占位；统一入口与现行契约不变，历史测试改用固定 Git 来源。 |
| 2.4.5 | 2026-09-07 | CampusClaw 当前十项接口统一入口、源清单与校验；旧评审页停止展示报文，Events 部分确认状态保留。 |
| 2.4.4 | 2026-09-07 | Slash/Builtin 恢复 06bea56 完整版全局主图入口，Help 专题仅提供下钻图；同步全局图维护规则，契约和统一实施责任不变。 |
| 2.4.3 | 2026-09-05 | Builtin 与 Skill Command 改由用户统一设计、实现和集成；同步当前职责、实施验收及契约说明，旧分工仅作历史。 |
| 2.4.2 | 2026-09-04 | 同步 Runtime 1.45.0 与已确认 Help Agent 元数据指南入口；不改变其他命令或 Mate 公共契约。 |
| 2.4.1 | 2026-09-04 | 澄清 Builtin/Skill 并行开发分工；旧版 Skill 延期解释不再有效，公共命令接口在发布前合并双方契约。 |
| 2.4.0 | 2026-09-04 | 收敛 Runtime 1.44.0 与七个 Builtin 分层设计；采用普通 JSON、延期 Skill 执行、去除通用生命周期与 Name 边车；旧公共命令提案标为历史，记录串行 PR 门禁。 |
| 2.3.8 | 2026-09-02 | 为 mate-service 通用对话 Events 实时流补充“用户同意后执行端口隔离”的完整工具交互示例。 |
| 2.3.7 | 2026-09-02 | 为 mate-service 通用对话 Events 提交接口补充“允许工具调用”的完整成功响应示例，并与拒绝示例并列展示。 |
| 2.3.6 | 2026-09-02 | 整体润色 mate-service 通用对话 Events 三接口的说明与示例，统一为真实、连贯的园区巡检场景；字段、Schema 和行为不变。 |
| 2.3.5 | 2026-09-02 | 优化 mate-service 通用对话 Events 提交接口的示例摘要，以业务场景描述请求和成功响应；契约字段与行为不变。 |
| 2.3.4 | 2026-09-02 | mate-service 通用对话 Events 的 POST 成功响应改为在 `result.event` 返回完整、已持久化的用户事件，并与历史事件复用同一 Schema。 |
| 2.3.3 | 2026-09-02 | mate-service 通用对话 Events 的 `toolCallId` 改为直接使用 OpenAI Responses `call_id` / Chat Completions `tool_calls[].id`；与独立公共 `eventId` 分离，并同步三接口契约。 |
| 2.3.2 | 2026-09-02 | 修正 mate-service 通用对话 Events 的 Swagger 请求头表达：`X-HW-ID` 和 `access-token` 作为三个 operation 的必需 header parameter，JWT 与 APPKEY 作为二选一 security scheme，Mate 不声明 `Accept-Language`。 |
| 2.3.1 | 2026-09-02 | 为 mate-service 通用对话 Events 三接口增加 OpenAPI 3.1；提交事件使用联合 Schema 和命名示例展示 message、interrupt 与 tool confirmation。 |
| 2.3.0 | 2026-09-02 | 确认 mate-service 通用对话 Events 三接口：POST 提交、Chat 级 live SSE 和固定快照历史；同步事件类型、字段、错误与断线对账入口。 |
| 2.2.0 | 2026-09-01 | 新增 `POST /mate-service/v1/chats/{chatId}/events` 单 operation 评审入口；路径已确认，公共事件命名、序列身份、Thinking 和 Tool 投影仍待确认。 |
| 2.1.4 | 2026-09-01 | Slash Command 统一使用“命令清单”，Skill 文件位置统一表述为“文件夹”，并同步 Runtime HTTP 1.43.4。 |
| 2.1.3 | 2026-09-01 | Skill 名称对齐 Agent Skills 完整规则，参数限制改为引用普通消息输入约束，并同步 Runtime HTTP 1.43.3。 |
| 2.1.2 | 2026-08-31 | 简化 Slash Command 全套文档表述，同步 Runtime HTTP 1.43.2 导航。 |
| 2.1.1 | 2026-08-31 | 将 Slash Command 用户文案统一为“命令清单”，并同步 Runtime HTTP 1.43.1 导航。 |
| 2.1.0 | 2026-08-31 | 新增 Slash Command 通用模块、Builtin/Skill 新设计、Runtime HTTP 1.43 和 mate-service 公共聊天命令 API 导航。 |
| 2.0.0 | 2026-08-26 | 建立六个中文分类、中文专题目录和分类导航；将根目录平铺文档收敛到专题目录；同步更新契约、图纸和脚本路径 |
