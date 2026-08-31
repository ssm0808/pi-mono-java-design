# mate-service 聊天命令 API 设计

| 属性 | 值 |
|---|---|
| 文档版本 | 1.0.0 |
| 状态 | 两个公共 operation 已确认；target-only design |
| 精确契约源 | [`接口契约/common.json`](接口契约/common.json) 与 [`接口契约/操作/`](接口契约/操作) |
| 人类评审契约 | [`chat-command-v1-review.html`](chat-command-v1-review.html)，由精确契约源生成 |
| 设计仓分析基线 | `27484974eb106a7e43910d8e542de52a72c58102` |
| mate-service 源码基线 | `956b547f5ca12ca89e68f73012f92a4406b0c9fa` |
| CampusClaw Slash 行为基线 | `c1311f69f504e7e799fa2467fd6a9d95b3f91b99` |
| CampusClaw 当前核对头 | `94abd2abcb03943daef5118115e4b4a21f1c4d5f` |
| CampusClaw 内部 HTTP 契约 | `1.43.0` |
| 更新日期 | 2026-08-31 |

## 1. 结论与边界

mate-service 面向登录用户开放两个公共 HTTP operation：

| Method | Path | 响应 | 作用 |
|---|---|---|---|
| `GET` | `/mate-service/v1/chats/{chatId}/commands` | ResultBean | 查询当前 Chat 对应 Session 的命令目录 |
| `POST` | `/mate-service/v1/chats/{chatId}/command` | 请求范围 SSE | 执行结构化 Builtin 或 Skill Command |

当前 mate-service 源码没有 Chat 资源、Chat→Runtime 映射、CampusClaw Runtime client 或
命令 Controller，因此本设计全部属于 target-only design，不能描述为已实现行为。
源码基线中 `AgentDefinitionController` 只提供 Agent 定义及 Runtime 配置读取；
`LlmChatController` 的 `/mate-service/v1/LLM/chat` 是 Model Manager 兼容流接口，
`LlmChatService`/`UpstreamChatCall` 可以透明转发模型响应体，但它既不解析 CampusClaw
领域事件，也不承担 Chat 权限和 Session 映射，不能复用为本 API 的字节转发实现。

`/name` 修改的是 CampusClaw 持久化 Session 的 `displayName`。mate-service 只维护
`chatId -> sessionId` 稳定一对一映射，不保存名称副本，不把名称更新改写成本地 Chat
元数据操作。

## 2. 目标组件

![公共聊天命令边界](设计图/public_command_boundary.svg)

[PlantUML 源码：`public_command_boundary`](设计图/diagram.puml#L1)

目标职责如下：

- `ChatCommandController` 只处理公共 VO、登录用户上下文和 HTTP/SSE 适配；
- `ChatSessionResolver` 在完成 Chat 权限判断后解析稳定的一对一 `sessionId`，不得由客户端提交；
- `CampusClawCommandClient` 以独立内部鉴权契约调用 Runtime 1.43，不透传浏览器
  `Authorization`；
- `PublicCommandEventProjector` 解析每一条内部 SSE，检查类型与字段，移除内部标识和
  私有数据，再编码公共事件；
- `PublicCommandErrorMapper` 把内部失败映射为稳定公共错误，不泄露 Session、Agent、Skill
  版本、文件路径、Provider 或数据库细节。

公共和内部鉴权是两个边界。浏览器的 `Authorization: Bearer <USER_ACCESS_TOKEN>` 只用于
mate-service 用户认证和 Chat 权限；mate-service 调用 CampusClaw 时重新构造公司内部
调用上下文及执行级 Header。任何一层都不能把 `chatId` 或 `sessionId` 当作凭据。

## 3. 交互层解析

交互层只有在文本第一个字符就是 `/` 时尝试 Slash 解析：

1. 命令名截取到第一个空白字符，严格匹配目录中的小写 `name`；
2. 剩余参数保持原始内容，包括内部换行，不做 trim 后重组；
3. 目录成功且精确命中时，调用结构化 Command API；
4. 目录成功但未命中时，整段文本按普通消息发送；
5. 目录失败时保留 Slash 草稿并显示错误，禁止静默降级为普通消息。

`/` 只是交互层展示符号，HTTP `name` 不包含 `/`。直接调用结构化 API 时，未知名称
严格返回 `COMMAND_NOT_FOUND`，不能沿用交互层“未命中按普通消息”的规则。

目录返回七个 Builtin 和当前 Agent 绑定的 `skill:<name>`。已知命令即使暂时不可用
仍返回；`available` 表示无参数调用，`input.available` 表示有参数提交，两者不得合并。
精确字段和 running 示例见
[`01-list-chat-commands.json`](接口契约/操作/01-list-chat-commands.json)。

## 4. 请求与执行语义

请求体固定为：

```json
{
  "name": "skill:pdf",
  "arguments": "分析附件并总结",
  "fileIds": ["file-550e8400e29b41d4a716446655440010"]
}
```

`arguments` 和 `fileIds` 省略时由 Service 统一归一为空字符串和空列表；请求 VO 不设置
字段默认值并拒绝未知字段。Builtin 不接受附件；Skill 复用普通消息的 262144 字符和
32 个附件上限。mate-service 不自行解释 Skill 正文、模型参数或 Session 状态，只执行
公共输入校验并让 CampusClaw 成为命令目录与 Admission Policy 的权威。

每次 CampusClaw 已接受调用都会返回 `command-<32 位小写十六进制 UUID>`。公共层保留
该不透明关联 ID，但不构造或重写它。通用完成结果只有 `text` 与可选
`sourceEventSeq`；不引入通用 Block 模型或命令专属公共 Response VO。

## 5. SSE 投影与错误

![公共 SSE 重新投影](设计图/public_sse_projection.svg)

[PlantUML 源码：`public_sse_projection`](设计图/diagram.puml#L23)

mate-service 必须按事件解析内部流，不能字节透明转发。公共投影规则为：

| 内部字段或事件 | 公共处理 |
|---|---|
| `sessionId`、`entryId`、Agent/Skill ID 与版本、受管路径 | 删除 |
| `skill.snapshot`、完整 Skill 正文、私有 Record | 永不公开 |
| `entrySeq` | 重命名为公共 `eventSeq`，供流内排序和历史对账；私有 Record 会造成合法缺口，公共层不得重编号 |
| `sourceEventSeq` | 保留，指向同一公共序列空间中的权威结果事件 |
| `command.started/completed/failed`、安全领域事件 | 校验后投影 |
| Assistant、Tool 与 Session 状态事件 | 复用已确认公共字段子集，不透明字段删除 |
| 未知内部事件或字段形状 | 不猜测；终止公共流并映射为安全错误 |

流建立前失败使用真实 HTTP status 和 `resCode/resMsg` ResultBean。公共鉴权错误由
mate-service 产生；内部 `SESSION_NOT_FOUND` 不直接泄露，映射为 Chat 侧语义。Skill
快照等内部可用性原因统一映射为 `COMMAND_UNAVAILABLE`。流建立后若执行失败，先投影
持久化 `command.failed`，再发送 `stream.error` 并关闭，不发送 `stream.end`。

Skill 或 Compact 被接受后，浏览器断线不自动中止 CampusClaw 执行。公共层不得因网络
异常重放 POST；重新加载后应从公共持久化历史判断是否已有 terminal event。只有现有
Stop/Abort 操作可以取消执行。

精确请求、成功流、流前错误和流内错误见
[`02-execute-chat-command.json`](接口契约/操作/02-execute-chat-command.json)。

## 6. 源码证据与设计理由

| 分类 | 证据或决策 |
|---|---|
| 观察到的 mate-service 行为 | `src/main/java/com/huawei/hicampus/mate/agentdefinition/controller/AgentDefinitionController.java:39-67` 只暴露 Agent 定义与 Runtime 配置查询，没有 Chat 或 Session bridge |
| 观察到的 mate-service 行为 | `.../modelmanager/controller/LlmChatController.java:34-56` 固定路径 `/mate-service/v1/LLM/chat` 并返回 `StreamingResponseBody`；`LlmChatService.java:57-126` 与 `UpstreamChatCall.java:19-31` 直接代理 Model Manager 流，不解析 CampusClaw 事件 |
| 观察到的 CampusClaw 行为 | `c1311f69` 的 `SlashCommandRegistry.java:21-67` 和 `NameCommand.java:10-39` 仍是未接入生产 HTTP 的宿主无关原型；当前 `t_sessions` 没有名称列 |
| 目标设计 | 新增 `ChatCommandController`、`ChatSessionResolver`、`CampusClawCommandClient`、`PublicCommandEventProjector` 与 `PublicCommandErrorMapper`；这些符号在源码基线中不存在 |
| 设计理由 | Chat 权限属于公共产品边界，Session 命令及名称属于 Runtime 领域；稳定映射让两者解耦且避免双写名称 |
| 安全加固 | 公共和内部鉴权独立；公共 SSE 必须解析和重新投影，禁止浏览器凭据、内部资源 ID、Skill 正文或私有路径跨边界 |
| 架构变化 | 现有 `UpstreamChatCall` 的透明流转适合 Model Manager 兼容代理，不适合需要字段过滤、错误映射与持久化序列对账的 CampusClaw 领域事件 |

Slash 模块、Builtin、Skill 和内部 Runtime 契约分别见
[通用模块](../../04-命令与技能/00-Slash-Command通用模块/README.md)、
[内置命令](../../04-命令与技能/01-内置命令/README.md)、
[技能命令](../../04-命令与技能/02-技能命令/README.md) 与
[CampusClaw HTTP 1.43](../../01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md)。

## 7. 验收

- GET 对 running Session 返回双层可用性，并保留暂不可用命令；
- 目录失败保留 Slash 草稿，目录成功但未命中才按普通消息发送；
- POST 拒绝未知命令、非法参数、Builtin 附件与未知字段；
- Chat 权限拒绝发生在 Session 解析和内部调用之前；
- 公共和内部鉴权 Header 不互相透传；
- 内部 SSE 的 `sessionId`、`entryId`、Skill ID/版本/路径和私有快照不出现在公共流；
- `entrySeq -> eventSeq` 与 `sourceEventSeq` 保持可验证关联；
- 流内失败有 `command.failed` 和 `stream.error`，无 `stream.end`；
- Skill/Compact 断线继续执行，重新加载可用 terminal event 对账且不重放 POST；
- `/name` 更新只改变 CampusClaw Session，mate-service 无名称副本。

## 8. 生成与校验

```bash
python3 render_chat_command_v1.py
python3 validate-chat-command-v1.py --full
```

校验覆盖 source-first 契约、生成 HTML 字节同步、无脚本内容、JavaScript 语法、移动端
样式、lowerCamelCase、内部字段泄露、PlantUML ASCII/SVG/XML/链接/行锚点同步、无
Mermaid 与 `git diff --check`。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-08-31 | 首次确认公共命令目录与结构化命令执行、ChatSessionResolver、独立鉴权、SSE 重新投影和 target-only 实现边界。 |
