# CampusClaw / pi-mono-java 设计仓库

> 导航版本：2.1.0<br>
> 整理日期：2026-08-31<br>
> Slash Command 设计基线：`27484974eb106a7e43910d8e542de52a72c58102`<br>
> 变更性质：新增 Slash Command 通用模块及内部/公共 HTTP 契约

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
| 浏览器如何调用聊天命令 | [mate-service 聊天命令 API](./02-服务与接口/06-mate-service聊天命令API/README.md) | [公共 HTTP 评审页](./02-服务与接口/06-mate-service聊天命令API/chat-command-v1-review.html)、[内部 Runtime 1.43](./01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md) |
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

mate-service 聊天命令 API 采用相同的 source-first 维护方式，但保持独立公共认证和
SSE 投影契约；其精确源与生成页位于
[`02-服务与接口/06-mate-service聊天命令API/`](./02-服务与接口/06-mate-service聊天命令API/)。

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
| 2.1.0 | 2026-08-31 | 新增 Slash Command 通用模块、Builtin/Skill 新设计、Runtime HTTP 1.43 和 mate-service 公共聊天命令 API 导航。 |
| 2.0.0 | 2026-08-26 | 建立六个中文分类、中文专题目录和分类导航；将根目录平铺文档收敛到专题目录；同步更新契约、图纸和脚本路径 |
