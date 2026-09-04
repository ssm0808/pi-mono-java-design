# CampusClaw / pi-mono-java 设计仓库

> 导航版本：2.4.0<br>
> 整理日期：2026-09-04<br>
> Slash Command 设计基线：`0eaa70ff365bf4d4e328b3473809341ca4cfc58d`<br>
> 通用对话 Events 三接口设计前基线：`743eca488ad559387706b5df54e2248a4124e5ef`<br>
> 变更性质：Builtin 分层、普通 JSON 与串行 PR；Skill 执行延期

本仓库维护 CampusClaw Runtime、mate-service 边界、pi-mono-java 目标设计，
以及相关源码和产品研究。这是设计与契约资料仓库，不是产品源码仓库。

## 1. 按问题快速找文档

| 我想了解 | 首选入口 | 继续阅读 |
|---|---|---|
| CampusClaw 整体如何运行 | [多 Agent Runtime 总体设计](./01-总体架构/01-CampusClaw多Agent运行时/README.md) | [HTTP API 设计](./01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md)、[HTTP API 评审页](./01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-review.html) |
| Tool 如何装配、发现和执行 | [CampusClaw 工具系统](./01-总体架构/02-CampusClaw工具系统/README.md) | [内置工具精确契约](./01-总体架构/02-CampusClaw工具系统/built-in-tool-contracts.md) |
| 前端如何展示 Runtime 状态 | [CampusClaw 前端体验设计](./01-总体架构/04-CampusClaw前端体验/README.md) | [前端评审页](./01-总体架构/04-CampusClaw前端体验/frontend-review.html) |
| 文件、配置和 Model Manager 边界 | [服务与接口导航](./02-服务与接口/README.md) | 附件服务、共享配置、Provider 契约和 HTTP 测试 Agent |
| 全产品测试与质量门禁 | [CampusClaw TDD 测试 Agent](./02-服务与接口/05-CampusClaw-TDD测试Agent/README.md) | 能力注册表、实时门禁、nightly 维护和测试防弱化 |
| Session、Agent 元数据如何持久化 | [数据与存储导航](./03-数据与存储/README.md) | 会话记忆、Agent 元数据和通用数据库模式 |
| Command 和 Skill Command 如何设计 | [Slash Command 通用模块](./04-命令与技能/00-Slash-Command通用模块/README.md) | [内置命令](./04-命令与技能/01-内置命令/README.md)、[技能命令](./04-命令与技能/02-技能命令/README.md) |
| 公共聊天命令历史与重审入口 | [mate-service 聊天命令 API](./02-服务与接口/06-mate-service聊天命令API/README.md) | [公共 HTTP 评审页](./02-服务与接口/06-mate-service聊天命令API/chat-command-v1-review.html)、[内部 Runtime 1.44.0](./01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md) |
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

## 3. Runtime 契约权威顺序

1. [`接口契约/common.json`](./01-总体架构/01-CampusClaw多Agent运行时/接口契约/common.json) 和 [`接口契约/操作/`](./01-总体架构/01-CampusClaw多Agent运行时/接口契约/操作/) 是唯一可编辑的精确契约源。
2. [`chat-http-v1-review.html`](./01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-review.html) 是由契约源生成的主要人类评审界面。
3. [`chat-http-v1-design.md`](./01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md) 只维护源码证据、目标差异和设计理由。
4. [Runtime HTTP 测试 Agent](./02-服务与接口/04-Runtime-HTTP测试Agent/README.md) 消费已确认契约，维护分层回归测试。

Runtime HTTP V1 不维护 OpenAPI。CampusMate 附件服务仍维护独立的
[`attachment-api.openapi.yaml`](./02-服务与接口/01-CampusMate附件服务/attachment-api.openapi.yaml)，
两者不可混用。

mate-service 聊天命令旧 SSE 提案已废止，仅保留历史 target-only 契约，不能作为实现依据。
新公共命令协议需独立重审，不由 Runtime Builtin JSON 决策推导；历史源与生成页位于
[`02-服务与接口/06-mate-service聊天命令API/`](./02-服务与接口/06-mate-service聊天命令API/)。

mate-service 通用对话 Events API 已确认事件提交、Chat 级 live SSE 和固定快照历史三个
operation；standalone HTML 是主要人类契约，OpenAPI 3.1 是同步的机器契约，均位于
[`02-服务与接口/07-mate-service通用对话API/`](./02-服务与接口/07-mate-service通用对话API/)。

## 4. 文档维护约定

- 新专题先选择一级中文分类，再建立中文专题目录；不再向根目录平铺设计文件。
- 专题入口统一使用 `README.md`，根 README 和所属分类 README 同时增加导航。
- 设计图使用 PlantUML，每个图纸专题保留一份 `diagram.puml`，并提交生成后的 SVG。
- `.puml` 内容只使用英文 ASCII；中文路径在源证据注释中使用 URL 百分号编码。
- 代码对齐的设计必须记录源码 commit、仓库相对路径以及相关符号或基线行号。
- 明确区分已观察源码行为、目标设计、产品约束、安全加固和架构改造。
- 数据库表使用 `t_` 前缀和小写 snake_case；SQL `COMMENT ON` 使用中文。

## 5. 维护命令

Runtime HTTP 契约变更后：

```bash
cd '01-总体架构/01-CampusClaw多Agent运行时'
python3 render_chat_http_v1.py
python3 validate-chat-http-v1.py --full
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
