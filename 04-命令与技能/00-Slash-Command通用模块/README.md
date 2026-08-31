# CampusClaw Slash Command 通用模块设计

[返回命令与技能导航](../README.md)

| 属性 | 值 |
|---|---|
| 文档版本 | 1.0.0 |
| 设计日期 | 2026-08-31 |
| 设计仓基线 | `27484974eb106a7e43910d8e542de52a72c58102` |
| CampusClaw 指定源码基线 | `c1311f69f504e7e799fa2467fd6a9d95b3f91b99` |
| CampusClaw 复核 HEAD | `94abd2abcb03943daef5118115e4b4a21f1c4d5f` |
| 交付范围 | 目标设计与 HTTP 契约；不修改 CampusClaw 或 mate-service 产品代码 |

## 1. 结论

Slash Command v1 只开放 Builtin Command 和 Skill Command，不开放
Extension Command 和 Prompt Command。这是 CampusClaw 的产品分类，不是六个
Harness 共享的行业模型。

CampusClaw 唯一执行入口保持 HTTP。`/`只是交互层的表示和解析
符号；内外两层 HTTP 均提交结构化 `name + arguments + fileIds`，
`name` 不含 `/`。`POST /events` 继续把以 `/` 开头的文本当作普通
`user.message`，Runtime 不在消息入口做第二次 Slash 解析。

`/name` 由 CampusClaw 持久化 Session 领域拥有。CampusClaw 负责
`displayName`、`resourceVersion`、复制继承和 `session.name.changed`；
mate-service 只维护 Chat 到 Session 的稳定一对一映射，不保存名称副本。
当前 `NameCommand` 源码的类注释恰好做了相反分配，因此本结论是明确的
架构变更，不是对现有能力的描述。

![Slash Command 目标架构](设计图/slash_command_architecture.svg)

[PlantUML 源码：`slash_command_architecture`](设计图/diagram.puml#L1)

## 2. 基线判断与纠偏

### 2.1 CampusClaw 现状

| 分类 | 源码证据 | 结论 |
|---|---|---|
| 观察到的行为 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/command/SlashCommandRegistry.java:21-67` 使用可变 `LinkedHashMap`，内部解析整段 Slash 文本 | 有原型代码，但未被 Spring 管理，也未接入 Runtime Controller |
| 观察到的行为 | `SlashCommandSession.java:19-32` 同时暴露 Model、Thinking、Compact 和 Name 修改 | 这是宽泛可变 Session 门面，不适合作为模块扩展边界 |
| 观察到的行为 | `NameCommand.java:10-39` 声明名称由未来宿主适配 mate-service | 这是本设计要替换的旧边界 |
| 观察到的行为 | Runtime 只有 Spring `@RestController`路由；`SlashCommandRegistry` 无生产调用点 | “当前对外执行入口只有 HTTP”判断正确 |
| 观察到的行为 | `RuntimeSessionMapper.xml:132-190` 只递归查询 `active_leaf_id` 祖先 | 当前没有 sidecar Entry 查询语义 |
| 观察到的行为 | `AgentRuntimeManager.java:81-112,275-293,425-433` 在 Agent 锁内发布和读取 complete 快照 | Skill 调用应复用这个原子快照边界 |

`c1311f69` 与复核 HEAD `94abd2ab` 之间，上述 Command 文件、Session
配置服务、Agent Runtime 快照与 Session Mapper 的关键符号仍存在。
复核 HEAD 的 `RuntimeEventProjector` 有后续变更，所以设计同时记录指定
基线和当前复核 HEAD，不把后发符号归给早期 commit。

### 2.2 Harness 比较

| 基线 | 观察到的源码行为 | 对 CampusClaw 的判断 |
|---|---|---|
| pi `4af9d21d` | `interactive-mode.ts:675-772` 合并 Builtin、Prompt、Extension 和 `skill:*`；`agent-session.ts:1315-1343` 展开 Skill；`3005-3012` 把名称写入 Session Entry；`rpc-mode.ts:657-708` 用结构化 RPC 设置名称和获取命令 | 四类可作产品词汇，但不应整体照搬；`skill:` 命名空间和 Session 名称归属值得采用 |
| OpenCode `849c2598` | `command/index.ts:65-169` 把 command、MCP prompt 和 Skill 放入一个名称表，Skill 重名时跳过；`session.ts:693-710,755-757` 由 Session 持久化 title 和 fork title | 证明 Session 拥有 title；裸 Skill 名称和隐式优先级不适合 CampusClaw |
| DeepSeek Harness `141eb6fe` | `packages/interaction/commands/src/index.ts:53-123,245-300,328-437` 分离 Definition、Descriptor、Invocation、Registry 与 Handler，保存 command lifecycle；`packages/session/session-title/src/index.ts:343-383` 由 Session title 服务持久化用户重命名 | 接口分层方向正确；但 CampusClaw HTTP 不接收未解析 `line`，名称超限拒绝而非截断 |
| Codex Harness `be33f80b` | `codex-rs/tui/src/chatwidget/slash_dispatch.rs:134-157,245-280,900-965` 在 TUI 集中解析和分支；App Server `codex-rs/app-server-protocol/src/protocol/common.rs:528-532,577-581,657-661` 分别开放 `thread/name/set`、`thread/compact/start`、`skills/list` | TUI 中央分支不适用 HTTP 模块；App Server 的结构化边界支持本设计 |
| Claude Managed Agents（2026-08-31） | 官方 [Sessions](https://platform.claude.com/docs/en/managed-agents/sessions)、[Events and streaming](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)、[Skills](https://platform.claude.com/docs/en/managed-agents/skills) 和 [Session operations](https://platform.claude.com/docs/en/managed-agents/session-operations) 展示版本化 Agent、持久化 Session Event 与 Session Skill | 可参考 Session/Event/Skill 所有权，但没有统一 Slash Command 或 Session rename 协议 |

Codex App Server 的官方定位参见 [Codex App Server](https://learn.chatgpt.com/docs/app-server)；
精确 method 名和字段以上表固定的开源基线为证据。

## 3. 模块设计

### 3.1 核心类型

```text
CommandDefinitionSource.list(context)
CommandDefinitionSource.find(context, name)
CommandHandler.execute(invocation) -> CompletionStage<CommandResultDTO>
```

- `CommandDefinition` 组合无 Handler 的 `CommandDescriptor`、`CommandAdmissionPolicy`
  和 `CommandHandler`。
- `BuiltinCommandContributor` 每个命令一个；Spring 启动时一次收集，
  验证 `[a-z0-9-]+`，构建不可变索引，重名立即启动失败。
- `SkillCommandSource` 是单一动态 Source，从当前 Agent 快照生成
  `skill:[a-z0-9-]+`；所有 Skill 共用一个 `SkillCommandHandler`。
- `CompositeCommandRegistry` 只做组合和精确查找，不持有命令分支。
- `CommandInvocation` 是不可变值，只包含 `commandId`、Session/Agent 必要标识、
  已归一化 `arguments`、`fileIds`、locale 和调用上下文。
- Handler 只注入窄职责 Application Service；不依赖 Controller，不发起
  对自身的 HTTP 调用，不获得宽泛可变 Session 门面。

因此新增 Builtin 只需新增 Contributor、Definition、Handler 和相应窄服务；
不修改中央 `switch`、Controller 或其他命令的 Handler。

![注册与分发](设计图/command_registration.svg)

[PlantUML 源码：`command_registration`](设计图/diagram.puml#L35)

### 3.2 目录与可用性

Descriptor 字段固定为：

```text
name
kind: builtin | skill
description
available
unavailableCode
input.mode: none | optional | required
input.available
input.unavailableCode
input.acceptsFiles
input.placeholder
input.suggestions
```

`available` 表示无参调用在当前状态是否成立；`input.available` 表示是否
允许提交参数。例如 Session 运行中的 `model` 仍可查询，所以
`available=true`；但不可切换，所以 `input.available=false` 且
`input.unavailableCode=SESSION_BUSY`。已知但暂时不可用的命令仍在目录中；
未知名称不进入目录。

### 3.3 Admission Policy

Admission 在 Handler 前统一完成：

1. 验证命令存在、名称和调用种类。
2. 由 Service 将省略的 `arguments` 归一为空字符串，`fileIds` 归一为空列表。
3. 复用 `RuntimeApiConstants.MAX_MESSAGE_CHARACTERS=262144` 和
   `MAX_FILE_IDS=32`；不创建命令私有上限。
4. Builtin 一律拒绝非空 `fileIds`；Skill 按普通用户消息的附件规则接受。
5. 根据无参/有参两层可用性校验 Session 状态。
6. 仅在全部校验成功后生成 `command-<32位小写十六进制UUID>`
   并写入 `command.started`。

## 4. 交互层解析

- 只有文本第一个字符是 `/` 才尝试 Slash 解析。
- 命令名截取到第一个空白字符，严格匹配目录中的小写名称。
- 参数保持除命令分隔符外的原始剩余内容，包括内部换行；HTTP 不再解析。
- 成功取得目录且精确命中时调用 Command API。
- 成功取得目录但未命中时，按普通消息发送。这是交互产品回退，
  不适用于直接结构化 API 调用。
- 目录请求失败时保留 Slash 草稿并显示错误，不得静默降级为普通消息。
- 直接调用 Command API 但 `name` 未知时严格返回 `COMMAND_NOT_FOUND`。

![交互层路由](设计图/interaction_routing.svg)

[PlantUML 源码：`interaction_routing`](设计图/diagram.puml#L79)

## 5. HTTP 与执行契约

| 边界 | 目录 | 执行 |
|---|---|---|
| mate-service 公共 API | `GET /mate-service/v1/chats/{chatId}/commands` | `POST /mate-service/v1/chats/{chatId}/command` |
| CampusClaw 内部 API | `GET /campusclaw-service/v1/sessions/{sessionId}/commands` | `POST /campusclaw-service/v1/sessions/{sessionId}/command` |

GET 成功和流建立前错误使用公司 `ResultBean` 与真实 HTTP status。
POST 成功建立请求范围 SSE；流建立后失败不能改写 status，必须先持久化
`command.failed`，再发 `stream.error` 并关闭，不再发 `stream.end`。

Skill 可执行 Mate Tool，因此内部 POST Command 与已有 POST Events 一样要求
`access-token`，并只将调用上下文 Header 作为本次 Skill 执行的瞬时快照；
不持久化、不记录，仅实际 Mate execute 传递。这是安全加固。Builtin 与
Skill 共用一个 POST operation，调用方不得通过缺失凭据让 Runtime 根据
命令名选择不同认证强度。

精确内部契约见 [Runtime HTTP 设计](../../01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md)
与 [Runtime API 评审页](../../01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-review.html)。
精确公共契约见 [mate-service 聊天命令 API](../../02-服务与接口/06-mate-service聊天命令API/README.md)。

## 6. 结果和事件

Handler 通用成功结果只有：

```text
text
sourceEventSeq (optional)
```

不增加通用 Block 模型，也不为每个命令创建专属响应 DTO。

| 事件 | 持久化 | 进入模型上下文 | 说明 |
|---|---|---|---|
| `command.started` | 是 | 否 | 已通过 Admission 并开始 Handler |
| `command.completed` | 是 | 否 | 保存 `text` 和可选 `sourceEventSeq` |
| `command.failed` | 是 | 否 | 保存稳定错误码，不保存未脱敏异常 |
| `session.name.changed` | 是 | 否 | 名称领域事件 |
| 现有 Model/Thinking/Compaction/Assistant/Tool 事件 | 按现有契约 | 按现有投影 | 权威领域结果 |

`sourceEventSeq` 指向权威结果事件：Name 指向 `session.name.changed`，
Model/Thinking 指向对应配置变化，Compact 指向
`session.compaction.completed`，Skill 指向最终
`assistant.message.completed`。查询命令和同值更新没有对应领域变化时省略。

## 7. 分支历史与 sidecar

`command.*` 与运行中产生的 `session.name.changed` 写入
`t_session_entries`，但是“锚定而不推进”的 sidecar：

- 每次提交使用事务内实际 `active_leaf_id` 作为锚点；空 Session 的锚点为空。
- sidecar 分配与其他 Entry 共享的 `entry_seq`，但绝不改写 `active_leaf_id`。
- GET Events 先计算当前活动路径，再并入锚定在该路径上的 sidecar，
  最后按 `entry_seq` 排序；切换分支后，旧分支专属 sidecar 不可见。
- 模型上下文投影器忽略 `command.*` 和 `session.name.changed`。
- `skill.snapshot` 不是公共 Entry，而是 `t_session_records` 的私有运行记录。

![sidecar 历史](设计图/sidecar_history.svg)

[PlantUML 源码：`sidecar_history`](设计图/diagram.puml#L109)

## 8. 故障、断线与恢复

- 流建立前：不写 `command.started`，返回 ResultBean 与真实 HTTP status。
- 流建立后：Handler 失败写 `command.failed`，发 `stream.error` 并关闭。
- Skill 和 Compact 被接受后，HTTP 断线不自动中止执行；只有现有 Stop/Abort API 可取消。
- 调用方断线后通过 GET Events 读取 `command.completed` 或 `command.failed`；
  不得盲目重放可变 POST。

## 9. 设计验收

- Builtin 重名启动失败；Skill 与 Builtin 无名称冲突；新增命令不修改中央分派。
- Catalog 精确匹配，已知不可用命令仍可见，运行中双层可用性正确。
- 目录失败不降级；结构化 API 未知命令、非法参数和 Builtin 附件在流前失败。
- sidecar 不改变 active leaf，分支切换后查询顺序与可见性正确。
- 公共/内部 JSON、SSE 和错误投影存在聚焦契约测试。

## 10. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-08-31 | 建立 Builtin/Skill 两类命令、可组合注册、结构化 HTTP、双层可用性、命令事件和 sidecar 持久化的唯一公共定义 |
