# CampusClaw Slash Command 通用模块设计

[返回命令与技能导航](../README.md)

| 属性 | 值 |
|---|---|
| 文档版本 | 1.2.1 |
| 设计日期 | 2026-09-04 |
| 设计仓基线 | `aae23e98014f947dd57e2172d89bc2778ab6c936` |
| CampusClaw 指定源码基线 | `c1311f69f504e7e799fa2467fd6a9d95b3f91b99` |
| CampusClaw `main` 复核基线 | `c9d858bc8261bf07f5585f545b53495bf2226a56` |
| Command 发现层复核提交 | `3004419a467b77bac08d0f2b3dad21f8815568c5` |
| Command 清单 HTTP 复核提交 | `fb49e86dc1bc9761d191ad9b9890afe7909deace` |
| 交付范围 | 目标设计与 HTTP 契约；发现与 GET 清单已有未合入实现，执行仍为 target-only |

## 1. 设计结论

| 设计项 | v1 结论 |
|---|---|
| 命令类型 | 开放 Builtin 和 Skill；不开放 Extension 和 Prompt |
| 执行入口 | 仅 HTTP |
| HTTP 请求 | 提交 `name + arguments + fileIds`，不提交整段 Slash 文本 |
| Skill 名称 | 使用独立的 `skill:<name>` 命名空间 |
| Session 名称 | `/name` 由 CampusClaw 持久化；mate-service 不保存副本 |

`/` 只用于交互层展示和解析。HTTP `name` 不含 `/`。
`POST /sessions/{sessionId}/events` 不解析 Slash 文本；以 `/` 开头的内容在该接口中仍是普通用户消息。

CampusClaw 负责 `displayName`、`resourceVersion`、复制继承和
`session.name.changed`。现有 `NameCommand` 把名称交给 mate-service，目标设计将其改为
CampusClaw Session 能力。这是架构变更，不是现有行为。

![Slash Command 目标架构](设计图/slash_command_architecture.svg)

[PlantUML 源码：`slash_command_architecture`](设计图/diagram.puml#L1)

## 2. 源码判断

### 2.1 CampusClaw 现状

| 源码证据 | 当前判断 |
|---|---|
| `SlashCommandRegistry.java:21-67` 使用可变 `LinkedHashMap` 并解析整段 Slash 文本 | 仅是原型；未被 Spring 管理，也未接入 Runtime Controller |
| `SlashCommandSession.java:19-32` 同时暴露 Model、Thinking、Compact 和 Name 修改 | 门面过宽，不适合作为扩展边界 |
| `NameCommand.java:10-39` 把名称交给未来 mate-service 适配 | 目标设计将名称改归 CampusClaw Session |
| Runtime 只有 Spring `@RestController` 路由；Registry 无生产调用点 | 当前对外执行入口只有 HTTP |
| `RuntimeSessionMapper.xml:132-190` 只查询 `active_leaf_id` 的祖先 | 当前没有 sidecar 查询语义 |
| `AgentRuntimeManager.java:81-112,275-293,425-433` 在 Agent 锁内发布和读取 complete 快照 | Skill 调用应复用该快照边界 |
| `3004419a` 的 `CompositeCommandRegistry.resolve:60-75` 合并 Source 并统一支持 list/find | 发现层已在未合入分支落地；`CommandDefinitionSource.find` 已不再被 Composite 使用 |
| `fb49e86d` 的 `RuntimeCommandController.list:62-75` 已提供 GET 清单 | Controller 仍直接访问 Repository/Registry 并返回内部 DTO，还不是目标边界 |

指定基线 `c1311f69` 和 `main` 复核基线 `c9d858bc` 包含旧 Command 与 Runtime 关键符号。
Command 发现层和 GET 清单分别只存在于未合入的 `3004419a` 和 `fb49e86d`，
本文不把它们回写成 `main` 的已实现行为。

### 2.2 Harness 对比

| 基线 | 可采用 | 不采用 |
|---|---|---|
| pi `4af9d21d` | `skill:` 命名空间；名称归 Session；结构化 RPC 操作 | 同时开放 Builtin、Prompt、Extension、Skill 四类 |
| OpenCode `849c2598` | Session 持久化 title 和 fork title | Skill 使用裸名称并依赖冲突优先级 |
| DeepSeek Harness `141eb6fe` | Definition、Descriptor、Registry、Handler 和生命周期分层 | Registry 接收整段 Slash 文本；名称超限截断 |
| Codex Harness `be33f80b` | App Server 的结构化 `thread/name/set`、`thread/compact/start`、`skills/list` | TUI 中央分派 |
| Claude Managed Agents（2026-08-31） | 持久 Session、Event 和 Skill 所有权 | 没有可直接复用的 Slash 或 Session rename 协议 |

参考文档：[Codex App Server](https://learn.chatgpt.com/docs/app-server)、
[Claude Sessions](https://platform.claude.com/docs/en/managed-agents/sessions)、
[Events](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)、
[Skills](https://platform.claude.com/docs/en/managed-agents/skills) 和
[Session operations](https://platform.claude.com/docs/en/managed-agents/session-operations)。

## 3. 模块设计

核心接口：

```text
CommandDefinitionSource.list(context)
CompositeCommandRegistry.resolve(context) -> ResolvedCommandCatalog
ResolvedCommandCatalog.list()
ResolvedCommandCatalog.find(name)
CommandHandler.execute(invocation, executionContext) -> CompletionStage<CommandResultDTO>
```

| 组件 | 职责 |
|---|---|
| `BuiltinCommandContributor` | 声明一个 Builtin；启动时参与重名检查 |
| `SkillCommandSource` | 按当前 Agent 快照动态生成 Skill 命令 |
| `CompositeCommandRegistry` | 合并来源、检查重名并为单次请求生成一个已验证快照 |
| `ResolvedCommandCatalog` | 持有单次解析的唯一 Definition 映射，同时服务清单和精确执行查找 |
| `CommandDefinition` | 组合稳定元数据、准入规则和 Handler；按 Session 投影 Descriptor，不把可变 Descriptor DTO 当作 Definition 本身 |
| `CommandAdmissionPolicy` | 统一检查参数、附件和 Session 状态 |
| `CommandExecutionContext` | 为本次执行提供只读 Session 快照、Locale 和同一 `ResolvedCommandCatalog` 视图 |
| `CommandHandler` | 调用窄职责 Application Service；需要帮助信息时只读取执行上下文中的清单视图 |
| `CommandExecutionService` | 维护命令生命周期和 SSE |

目标类先按 Web API、Application、Command Core 和 Runtime Adapter 分层。Spring 单例只保留
无请求可变状态的协作对象；请求 VO、Invocation、执行上下文、凭据上下文和解析后的命令清单
都有明确边界与生命周期。

![Slash Command 目标分层与对象生命周期类图](设计图/target_slash_command_boundaries.svg)

[PlantUML 源码：`target_slash_command_boundaries`](设计图/diagram.puml#L35)

这张图固定以下依赖方向：

- Controller 只依赖 Catalog/Execution Service，不直接访问 Repository、Registry 或内部 DTO；
- `CommandCatalogService` 负责把内部 Descriptor 投影为不可变响应 VO；
- `CommandExecutionService` 统一归一输入、解析清单、占用执行容量并维护生命周期；
- 单次 GET 或 POST 只生成一个 `ResolvedCommandCatalog`，Help、准入和分发读取同一视图；
- 原始凭据只存在于本次执行的 `CommandCredentialContext`，不进入日志、持久化、Prompt 或领域事件。

Builtin 在 Spring 启动时生成不可变索引。名称必须匹配 `[a-z0-9-]+`；重名直接启动失败。
Skill 使用 `skill:<name>`，由一个动态 Source 和一个共享 Handler 处理。`<name>` 必须：

- 长度为 1～64 个字符；
- 只包含小写字母、数字和连字符；
- 连字符不能位于首尾或连续出现；
- 与 `SKILL.md` 所在文件夹同名。

精确格式为 `^[a-z0-9]+(?:-[a-z0-9]+)*$`。HTTP 层先移除 `skill:`，再复用同一个
Skill 域名称规则。`SkillNamePatterns` 只保留一份严格正则字符串、编译后的 Pattern 和
64 字符长度上限；加载、命令发现和执行全部引用它，不保留 LEGACY 分支，也不在
HTTP/Command 包中另设名称 Validator。长度必须单独校验，不能只匹配正则。

非法名称在加载时就拒绝，不进入已加载 Skill 集合、模型发现提示词或命令清单；执行入口
也不得绕过严格校验。`SKILL.md` 的 `name` 必须是非空字符串且与文件夹同名，不能通过
回退文件夹名称、裁剪、替换或自动改名接受非法输入。这是已确认产品约束与安全加固。
规则对齐 [Agent Skills specification](https://agentskills.io/specification)。
旧源码中的宽松加载仅是待整改差距，不能作为存量兼容要求；名称专项复核基线、源码路径和
验收矩阵见 [Skill 设计](../02-技能命令/README.md#7-源码证据和差异分类)。

Handler 只接收不可变 `CommandInvocation` 和只读 `CommandExecutionContext`。它不能依赖
Controller、调用自身 HTTP 接口，也不能获得宽泛可变 Session 门面。新增命令只新增
Contributor、Definition、Handler 和窄职责服务，不修改中央 `switch`。

扩展关系单独展开如下。`CommandDefinitionSource` 只列出当前上下文的 Definition。Registry 在单次请求内仅解析一次，
再由 `ResolvedCommandCatalog` 同时提供清单和精确查找。这避免了动态 Skill 快照在展示、准入和
执行之间重新解析，也避免 Source 各自维护两套 list/find 逻辑。该快照只固定
Definition 身份、元数据和 Skill 快照；修改状态的命令仍在所属事务或执行锁内重新检查
Session 状态和执行容量，不把 Descriptor 的预览可用性当作最终准入。

![Slash Command 目标解析与扩展类图](设计图/target_command_resolution_classes.svg)

[PlantUML 源码：`target_command_resolution_classes`](设计图/diagram.puml#L140)

这张图表达扩展时必须保持的约束：

- Builtin 由多个 Contributor 在启动期组成一个不可变 Source，重名直接阻止启动；
- Skill 由一个动态 Source 基于完整 Agent 快照生成，并复用一个 Skill Handler；
- `CommandDefinition` 将稳定元数据、准入和行为组合在一起，Descriptor DTO 只做内部投影；
- Builtin Handler 只调用一个窄职责应用服务；新增命令不修改中央 `switch`；
- `CommandExecutionContext` 只暴露同一次解析得到的只读 `CommandCatalogView`，避免 Help 形成 Bean 依赖环。

## 4. 命令清单与可用性

“命令清单”按 Session、Agent 快照和执行状态生成。它表示当前可以发现的命令及其
可用性，与文件路径或磁盘扫描无关。用户文案统一使用“命令清单”；代码类名可以保留
Catalog。

描述符字段：

| 字段 | 含义 |
|---|---|
| `name` | HTTP 命令名，不含 `/` |
| `kind` | `builtin` 或 `skill` |
| `description` | 简短用途 |
| `available` | 不填参数时能否执行 |
| `unavailableCode` | 不填参数时不能执行的原因 |
| `input.mode` | 参数为 `none`、`optional` 或 `required` |
| `input.available` | 填写参数时能否执行 |
| `input.unavailableCode` | 填写参数时不能执行的原因 |
| `input.acceptsFiles` | 是否接受附件 |
| `input.placeholder` | 参数提示 |
| `input.suggestions` | 参数建议 |

无参和带参数必须分别判断。例如 Session 运行中：

- `/model` 无参仍可查看，所以 `available=true`；
- `/model modelId` 不能切换，所以 `input.available=false`；
- 原因是 `SESSION_BUSY`。

已知但暂时不可用的命令仍返回。未知命令不进入清单。

## 5. 执行前检查

`CommandAdmissionPolicy` 在 Handler 前依次检查：

1. 命令存在且名称合法；
2. Service 将省略的 `arguments` 归一为空字符串，将 `fileIds` 归一为空列表；
3. `arguments` 与普通用户消息使用同一上限：最多 262144 个 UTF-16 代码单元；
   `fileIds` 最多 32 个；
4. Builtin 不接受附件；Skill 按普通用户消息规则接受附件；
5. 当前 Session 状态允许本次不填参数或填写参数的执行；
6. 全部通过后生成 `command-<32位小写十六进制UUID>`，再写入 `command.started`。

`262144` 来自 CampusClaw 现有 `RuntimeApiConstants.MAX_MESSAGE_CHARACTERS` 和
`UserEventRequestVO` 的 `@Size` 校验。它是复用普通消息限制的产品约束，不是 Agent Skills
或各 Harness 的统一标准，也不表示模型上下文一定能够容纳同样长度。

## 6. 交互层解析

| 步骤 | 规则 |
|---|---|
| 识别 | 只有第一个字符是 `/` 才尝试解析 |
| 名称 | 截取到第一个空白字符，严格匹配小写命令名 |
| 参数 | 保留原始剩余内容，包括内部换行 |
| 命中 | 调用结构化 Command API |
| 未命中 | 命令清单获取成功时，按普通消息发送 |
| 清单失败 | 保留草稿并显示错误，不降级为普通消息 |

直接调用结构化 API 时，未知名称返回 `COMMAND_NOT_FOUND`，不能按普通消息处理。

![交互层路由](设计图/interaction_routing.svg)

[PlantUML 源码：`interaction_routing`](设计图/diagram.puml#L240)

## 7. HTTP 契约

| 边界 | 查看命令清单 | 执行命令 |
|---|---|---|
| mate-service 公共 API | `GET /mate-service/v1/chats/{chatId}/commands` | `POST /mate-service/v1/chats/{chatId}/command` |
| CampusClaw 内部 API | `GET /campusclaw-service/v1/sessions/{sessionId}/commands` | `POST /campusclaw-service/v1/sessions/{sessionId}/command` |

GET 成功和流建立前错误使用 ResultBean 与真实 HTTP status。POST 成功后返回请求范围 SSE。
流建立后失败时，服务端写入 `command.failed`，发送 `stream.error` 并关闭；不发送
`stream.end`。

内部 POST Command 与 POST Events 一样要求 `access-token`。Runtime 只在本次执行中保留
调用 Header，且仅在 Skill 实际调用 Mate Tool 时原名传递。Header 不写日志、不持久化、
不进入 Prompt 或 Event。

精确契约见 [Runtime HTTP 设计](../../01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md)、
[Runtime API 评审页](../../01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-review.html) 和
[mate-service 聊天命令 API](../../02-服务与接口/06-mate-service聊天命令API/README.md)。

## 8. 结果与事件

通用成功结果只有：

```text
text
sourceEventSeq (optional)
```

| 事件 | 持久化 | 进入模型上下文 | 作用 |
|---|---|---|---|
| `command.started` | 是 | 否 | 命令开始 |
| `command.completed` | 是 | 否 | 保存结果和可选 `sourceEventSeq` |
| `command.failed` | 是 | 否 | 保存稳定错误码 |
| `session.name.changed` | 是 | 否 | 记录名称变化 |
| Model/Thinking/Compaction/Assistant/Tool 领域事件 | 按既有契约 | 按既有投影 | 保存权威业务结果 |

`sourceEventSeq` 指向权威结果事件：

| 命令 | 指向 |
|---|---|
| `/name` | `session.name.changed` |
| `/model`、`/thinking` | 对应配置变化事件 |
| `/compact` | `session.compaction.completed` |
| `/skill:<name>` | 最终 `assistant.message.completed` |

查询或同值更新没有领域变化时，可以省略 `sourceEventSeq`。

## 9. 历史与恢复

`command.*` 和运行中产生的 `session.name.changed` 使用 sidecar Entry：

- 锚定提交时的 `active_leaf_id`；
- 分配共享 `entrySeq`；
- 不修改 `active_leaf_id`；
- GET Events 只合并当前活动路径上的 sidecar，并按 `entrySeq` 排序；
- 模型上下文忽略 `command.*` 和 `session.name.changed`。

`skill.snapshot` 写入 `t_session_records`，不作为公共 Entry。私有 Record 与 Entry 共享
Session 序列，因此公开 `entrySeq` 可以有缺口，调用方不得重编号或推断缺口内容。

![sidecar 历史](设计图/sidecar_history.svg)

[PlantUML 源码：`sidecar_history`](设计图/diagram.puml#L270)

断线规则：

- 流建立前失败：命令未接受，不写 `command.started`；
- 流建立后失败：写 `command.failed`，发送 `stream.error`；
- Skill 和 Compact 已接受后继续执行；只有现有 Stop/Abort API 可以取消；
- 调用方通过 GET Events 查询最终状态，不重放 POST。

## 10. 验收重点

- Builtin 重名时启动失败；Skill 与 Builtin 不冲突；新增命令不改中央分派；
- Skill 加载、命令发现和执行统一拒绝超过 64 个字符、首尾或连续连字符、缺少 frontmatter 名称和文件夹名称不一致；不保留宽松加载分支；
- 命令清单精确匹配，保留暂时不可用命令，并分别标明不填参数和填写参数时能否执行；
- 清单失败不降级；未知命令、非法参数和 Builtin 附件在流建立前失败；
- sidecar 不改变 active leaf，分支切换后的可见性和顺序正确；
- 公共与内部 JSON、SSE 和错误投影有聚焦契约测试。

## 11. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.2.1 | 2026-09-04 | 确认 Skill 加载、命令发现和执行统一严格校验；由 Skill 域集中维护唯一正则、Pattern 和长度上限，取消宽松加载兼容 |
| 1.2.0 | 2026-09-03 | 重做 Slash Command 目标类图：分别表达分层与对象生命周期、注册解析与扩展关系；明确 Controller/Application/Command Core/Runtime Adapter 边界、请求级清单快照、凭据生命周期、DTO/VO 隔离和无中央分派约束 |
| 1.1.0 | 2026-09-03 | 复核 `3004419a` 发现层与 `fb49e86d` GET 清单；引入单次请求 `ResolvedCommandCatalog` 快照和只读执行上下文，移除 Source 级别 find 职责，并明确 Definition 不直接封装可变 Descriptor DTO |
| 1.0.4 | 2026-09-01 | 命令相关表述只使用“命令清单”；Skill 文件位置统一表述为“文件夹”，避免再次引入文件系统含义 |
| 1.0.3 | 2026-09-01 | Skill 名称对齐 Agent Skills 的完整规则；参数上限明确为复用普通消息的 UTF-16 输入限制，不再表述为 Harness 通用规范 |
| 1.0.2 | 2026-08-31 | 全文改为短句、动作式表格和先结论后细节的结构；不改变已确认行为 |
| 1.0.1 | 2026-08-31 | 澄清 Command Catalog 是按 Session 上下文解析的逻辑注册表；面向用户和 HTTP 文案统一使用“命令清单”，避免被理解为文件路径 |
| 1.0.0 | 2026-08-31 | 建立 Builtin/Skill 两类命令、可组合注册、结构化 HTTP、双层可用性、命令事件和 sidecar 持久化的唯一公共定义 |
