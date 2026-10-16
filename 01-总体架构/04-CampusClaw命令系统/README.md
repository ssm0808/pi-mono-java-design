# CampusClaw 命令系统设计

[模块索引](../../README.md#module-index) · [命令与技能导航](../../04-命令与技能/README.md) · [源码证据](source-evidence.md)

本专题即 Slash Command 通用模块，原路径 `04-命令与技能/00-Slash-Command通用模块` 已迁到总体架构；锚点不变。

| 属性 | 值 |
|---|---|
| 文档版本 | 2.1.0 |
| 更新日期 | 2026-10-16 |
| 模块 | M05 · Command 与 Skill · Slash Command 通用模块 |
| 设计状态 | 按 Agent 查询命令清单待实现；七个 Builtin、Skill 执行与前端 Slash 已实现；mode、type/hints 描述符、Skill 统一结构待实现。逐项见 [§8.1](#current-runtime-status) |
| 源码基线 | `pi-mono-java` main `fd4310026be808a16f471c550dff4b024ce91e24`，2026-10-16 核验清单链路；其他能力沿用 [§8.1](#current-runtime-status) 所列核验提交 |
| 主基线 | OpenCode dev `e25b7abf8955a4fa1b02b935964cb47db4c3a02a`（命令清单路由为 Experimental）；辅以 Codex main `6b991972c5b539198dcea9bac4fc14e57559c3af`、pi main `4954d760504c11df9b2cbdc040346107b6a8153d`，均为 2026-10-16 默认分支快照 |

Builtin 的逐命令行为见 [内置命令](../../04-命令与技能/01-内置命令/README.md)，Skill 的名称、快照与恢复见 [技能命令](../../04-命令与技能/02-技能命令/README.md)，Composer 交互见 [Slash Command 前端](../../07-前端设计/技术设计/命令/README.md)。本文维护三者共用的命令清单、执行入口与分层。Builtin 与 Skill Command 由用户统一负责设计、实现和集成。

## 评审记录

### 评审结论

【缺口】本版尚未评审。

### 评审 Todo

| # | 事项 | 负责人 | 来源 |
|---|---|---|---|
| T1 | 确认清单接口改为 `GET /agents/{agentId}/commands`，不再按会话过滤，运行中的限制由前端状态规则和 POST 准入承担 | Lotus | [D1](#key-decisions) |
| T2 | 确认冷缓存时清单按创建会话的方式准备 Agent（可能访问 Mate），错误码与创建会话一致 | Lotus | [D2](#key-decisions) |
| T3 | 确认旧路径直接下线，不保留兼容期 | Lotus | [§5.3](#compatibility) |
| T4 | Mate 公共清单是否同步改为按 Agent 查询；当前公共路径仍是 `/chats/{chatId}/commands` | Lotus | [Mate 聊天命令 API](../../02-服务与接口/06-mate-service聊天命令API/README.md) |
| T5 | Skill 执行错误码设计与实现不一致（缓存不可用、解析失败、事件流背压） | Lotus | [§5.2.1](#failure-recovery) |
| T6 | Builtin 描述按 Accept-Language 本地化的契约 | Lotus | [源码证据 §6](source-evidence.md#331-清单字段与语言专项核对) |

### 需求信息

| 编号 | 来源 | 说明 |
|---|---|---|
| REQ-1 | Lotus，2026-10-16 项目对话 | 重新设计 Slash Command 设计文档，命令清单查询改为基于 agentId |
| REQ-2 | 已确认的 B13/B14 与历史版本 | Builtin JSON、Skill SSE、轻量描述符与状态规则 |

## 1. 概述

### 1.1 术语解释

| 术语 | 含义 |
|---|---|
| Slash 命令 | 用户在输入框首字符输入 `/` 后选择执行的结构化命令；`/` 只在交互层出现，接口里的命令名不带 `/` |
| Builtin | 产品固定提供的八个命令：help、status、name、model、thinking、mode、compact、skills |
| 技能命令 | 以 `skill:<name>` 调用 Agent 绑定的某个 Skill，执行一轮完整的 Agent 处理 |
| 命令清单 | 某个 Agent 可用命令的轻量描述，只用于发现和展示，不是执行授权 |
| 描述符 | 清单中的一项：name、type、description 和可选 hints |
| 完整 Agent 快照 | Agent 定义、系统提示词与绑定 Skill 都已就绪的本地缓存；残缺时不用于生成清单 |
| 命令状态规则 | [§4.2](#command-state-rules) 的表，规定每个命令在会话空闲和运行中允许的调用形态 |

### 1.2 需求整理

| 编号 | 需求 | 类型 | 来源 |
|---|---|---|---|
| R1 | 按 Agent 返回可用命令清单，新对话尚未创建会话时也能查询 | 功能 | REQ-1 |
| R2 | 清单按固定 Builtin 顺序排列，再追加按名称排序的技能命令 | 功能 | REQ-2 |
| R3 | 在会话内执行 Builtin，查询或修改会话设置，返回 JSON 业务结果 | 功能 | REQ-2 |
| R4 | 在会话内执行技能命令，以与普通消息相同的 SSE 返回本轮处理 | 功能 | REQ-2 |
| R5 | 清单不作执行授权；执行时在所属锁或事务内重新检查会话状态、绑定和参数 | 安全 | REQ-2 |
| R6 | 描述符不返回 Skill 正文、路径、版本、内部 ID 或凭据 | 安全 | REQ-2 |
| R7 | 未匹配的 Slash 不回退为普通消息；普通消息接口不解析 Slash | 约束 | REQ-2 |
| R8 | 不生成公开 commandId，不保存通用命令生命周期 | 约束 | REQ-2 |
| R9 | Agent 快照不完整时整体失败，不返回残缺清单 | 稳定性 | REQ-2 |
| R10 | Skill 名称在加载、发现与执行使用同一严格规则 | 约束 | [技能命令 §3](../../04-命令与技能/02-技能命令/README.md#3-名称统一严格校验) |

R1 的“新对话尚未创建会话也能查询”和“同一 Agent 的多个会话共用清单”是从 REQ-1 推导的目标，需在 T1 确认。

## 2. 整体方案

### 2.1 业务用例

园区运维人员在对话中经常要做两类事：调整当前对话的设置（查看状态、切换模型或工作模式、压缩上下文），以及让 Agent 用某项固定技能处理一件业务（例如分析附件里的巡检记录）。靠自然语言描述，模型可能误解意图，用户也记不住 Agent 绑定了哪些技能。Slash 命令让用户输入 `/` 就看到当前 Agent 提供的命令，选择后按确定的方式执行。

| 编号 | 参与者 | 业务目标 | 业务结果 |
|---|---|---|---|
| BU1 | 运维人员 | 查看当前 Agent 提供哪些命令 | 看到内置命令和 Agent 绑定的技能，每项带用途说明和参数提示 |
| BU2 | 运维人员 | 查看或修改当前对话的设置 | 对话的名称、模型、深度思考或工作模式按要求生效，或看到当前值 |
| BU3 | 运维人员 | 用某项技能处理一项业务请求 | Agent 按该技能完成本轮处理，回答逐步显示；对话历史保留用户原始调用 |
| BU4 | 运维人员 | 压缩当前对话的上下文 | 较早的对话被压缩成摘要，后续对话继续可用 |
| BU5 | 运维人员 | 了解当前 Agent 能做什么 | 看到 Agent 的显示名、用途和使用场景 |

### 2.2 整体时序

场景：运维人员在已有对话中输入 `/`，选择 `skill:pdf` 分析附件中的巡检记录。起点是输入 `/`，终点是看到分析结果。前提是该 Agent 已绑定 pdf 技能且对话空闲。按 Agent 查询清单（步骤 2～6）待实现，其余步骤已实现。

| 参与者 | 职责 | 映射 |
|---|---|---|
| 运维人员 | 选择命令并填写请求 | 人 |
| Claw 前端 | Composer、命令清单与状态规则 | `frontend/src/composables/useCommandComposer.ts`、`useRuntimeApi.ts` |
| CampusClaw | 命令清单、命令执行与 Agent 运行 | `RuntimeCommandCatalogController`、`RuntimeCommandController` 及其应用服务 |
| Mate | Agent 定义与绑定技能的发布方 | `AgentRuntimeManager.prepare` 的远端来源 |
| GaussDB | 会话、事件与领域 Entry | `t_sessions`、`t_session_events`、`t_session_entries` |

![用技能分析巡检记录](slash_command_overview.svg)

[原尺寸 SVG](slash_command_overview.svg) · [PlantUML 源码](diagram.puml#L1)

| 阶段 | 详细时序 |
|---|---|
| 步骤 1～8：查询可用命令 | [§3.3](#list-commands-sequence) |
| 步骤 9：选择命令并填写参数 | [前端命令输入](../../07-前端设计/技术设计/命令/README.md#command-input-controls) |
| 步骤 10～19：执行技能命令 | [§3.5](#execute-skill-sequence) |

<a id="key-decisions"></a>

### 2.3 关键设计决策

| # | 要解决的问题 | 基线怎么做 | 业务约束 | 我们的选择 | 代价 |
|---|---|---|---|---|---|
| D1 | 命令清单归属谁 | OpenCode `command.list` 按实例所在的工作位置列出，不带会话；Codex `skills/list` 按工作路径（cwd）列出；pi `get_commands` 在会话进程内，因为一个 RPC 进程就是一个会话 | 命令来源只取决于 Agent：固定 Builtin 加 Agent 绑定的 Skill；新对话在发出第一条消息前就要能展示 `/` 清单；同一 Agent 的多个对话看到相同命令 | 清单归属 Agent：`GET /agents/{agentId}/commands` 返回该 Agent 的全部命令，不读会话状态；执行仍归属会话，`POST /sessions/{sessionId}/command` 在锁内最终准入 | 清单不再隐藏运行中不可执行的 compact 和技能命令，前端必须按 [§4.2](#command-state-rules) 集中限制；运行中用户可能看到禁用项 |
| D2 | 清单遇到本实例没有 Agent 完整缓存时怎么办 | OpenCode、pi 在本地进程启动时加载命令来源，没有远端回源；Codex 可显式 `force_reload` | 按 Agent 查询时可能还没有任何会话，冷缓存是常态；不能返回残缺清单 | 与创建会话共用 `AgentRuntimeManager.prepare`：有完整缓存直接用，缺失时在 Agent 锁内从 Mate 准备一次；不提供强制刷新；错误码与创建会话一致 | 首次查询可能访问 Mate，耗时变长；Mate 暂时不可用时返回 422 而不是可重试的 503，前端提供手动重试 |
| D3 | 清单与执行如何保持一致 | OpenCode 执行时按名称重新取 Command；pi 每次 prompt 重新展开 Skill | 清单可能过期；绑定和会话状态随时变化 | GET 与 POST 各自解析一份请求级快照，共用 Definition 身份；描述与会话无关，准入在执行时按会话检查 | 每次执行都重新解析来源，不能复用 GET 的结果 |
| D4 | Builtin 与技能命令用什么响应 | OpenCode 会话命令 POST 返回 JSON 消息，事件流独立；pi 的 Skill 展开后作为普通 prompt | Builtin 是一次性查询或修改；技能命令会跑完整一轮推理并可能等待确认 | 同一 POST 入口：Builtin 返回 JSON 业务资源，技能命令返回与普通消息相同的请求级 SSE | 调用方要按自己提交的命令区分响应类型 |
| D5 | 是否保存通用命令记录 | DeepSeek Harness 有 CommandExecution 与命令日志（alpha） | 现有会话、领域 Entry 和事件已能对账 | 不生成 commandId，不保存通用命令生命周期；状态变化复用会话和既有领域 Entry | 无法按命令维度审计，需要时只能从领域 Entry 与事件推断 |

完整基线证据见 [源码证据 §1.2](source-evidence.md#agent-catalog-evidence)。差异分类：D1、D2 是架构变更，D3、R5 是安全加固，D4、D5 是产品约束。

## 3. 详细设计

### 3.1 系统用例

| 用例 | 对应业务用例 | 触发者 | 前置条件 | 主成功结果 | 关键约束 |
|---|---|---|---|---|---|
| UC1 查询 Agent 命令清单 | BU1 | Claw 前端或 Mate 桥接 | Agent 已发布 | 返回该 Agent 的全部命令描述符 | 不读会话；快照不完整时整体失败；不返回内部字段 |
| UC2 执行 Builtin | BU2、BU4、BU5 | Claw 前端 | 会话存在 | 返回会话资源、模型清单或最小业务结果 | 只接收 name 和 arguments；锁内复核状态；不写通用命令记录 |
| UC3 执行技能命令 | BU3 | Claw 前端 | 会话空闲且 Agent 绑定该技能 | 受理根消息并以 SSE 返回本轮处理 | 与普通消息共用受理链；精确匹配失败即拒绝 |

### 3.2 数据模型

本模块不新增表。命令清单不持久化，每次请求从 Agent 快照解析。执行写入复用既有表：

| 表 | 关键字段 | 约束与生命周期 |
|---|---|---|
| `t_sessions` | 会话状态、显示名、模型、深度思考、模式 | name/model/thinking/mode 在行锁内合并本次提交；同值不更新 updatedAt |
| `t_session_entries` | Model/Thinking/Mode/Compact 的领域 Entry；技能命令的展开内容 | 只在真实变化时追加；查询、同值修改和空历史压缩不写 |
| `t_session_events` | 技能命令的 user.message（原始调用）及后续事件 | 与普通消息相同，见 [Session Events](../01-CampusClaw多Agent运行时/chat-events-design.md) |

![命令写入的最终状态](authoritative_command_state.svg)

[原尺寸 SVG](authoritative_command_state.svg) · [PlantUML 源码](diagram.puml#L98)

全局目标类图：

![Slash Command 全局目标类图](target_slash_command_global_classes.svg)

[原尺寸 SVG](target_slash_command_global_classes.svg) · [PlantUML 源码](diagram.puml#L119)

缩略图只用于定位分层，阅读类名和多重性请打开原尺寸 SVG。

| 分层 | 职责 | 不能合并的原因 |
|---|---|---|
| Web | 请求/响应 VO、Jakarta 校验、Locale 与 ResultBean | Controller 不依赖 Repository、Registry、Holder 或内部 DTO |
| 应用层 | 清单服务准备 Agent 快照并投影描述符；执行服务读取会话、解析、准入、调用 Handler 并组装结果 | 清单不读会话，执行必须读会话，两者归属不同 |
| 命令核心 | Definition、来源、Contributor、准入策略、Handler 与请求级 Catalog | `describe()` 只描述命令，`admit(session, arguments)` 只在执行时判断；新增命令不改中央 switch |
| 业务服务 | Name、Model、Thinking、Mode、Compact 等窄职责服务；Help 委派 AgentHelpQueryService | 业务约束、执行协调与持久化分开，最终准入在所属锁内完成 |
| 运行时与持久化 | Repository、Agent 运行时、执行协调器与事件投影 | 单例与单次执行对象生命周期不同 |

为什么这样分：清单与会话脱钩后，Definition 的描述不能再依赖会话快照，否则 Agent 级清单无从计算；把“能不能执行”全部收拢到准入策略，既让清单可以跨会话复用，也保证执行入口仍是唯一的最终判断点。实现时先改 `CommandDefinition.describe` 与 `CompositeCommandRegistry.resolve` 的签名，再改清单服务和 Controller，最后迁移前端读取路径。

八个 Contributor/Handler 的精确映射见 [内置命令 §2](../../04-命令与技能/01-内置命令/README.md#2-全局目标与核心扩展)；Help 的元数据与缓存见 [Help 设计](../../04-命令与技能/01-内置命令/Help-Agent使用指南/README.md)。

<a id="list-commands-sequence"></a>

### 3.3 查询可用命令的详细时序（UC1）

展开整体时序步骤 1～8 中的 CampusClaw 部分。待实现。

![查询可用命令的详细时序](list_agent_commands.svg)

[原尺寸 SVG](list_agent_commands.svg) · [PlantUML 源码](diagram.puml#L38)

| 生命线 | 映射 |
|---|---|
| 命令接口 | `RuntimeCommandCatalogController.list(agentId)` |
| 清单服务 | `CommandCatalogService.list(agentId)` |
| Agent 运行时 | `AgentRuntimeManager.prepare(agentId)` |
| 命令注册表 | `CompositeCommandRegistry.resolve(agentSnapshot)`，含 `BuiltinCommandSource` 与 `SkillCommandSource` |

- 准备 Agent 快照与创建会话使用同一个 `prepare`：完整缓存直接返回；缺失时在 Agent 锁内从 Mate 重建，失败时保留原有缓存。不触发强制刷新，不调用模型。
- 完整快照中 Skill 绑定为空是成功，清单只含 Builtin；快照不完整是失败，不返回只有 Builtin 的残缺清单。
- 内部 `ResolvedCommandDTO` 可以保留准入字段，转换描述符时只输出 [§4.1](#31-get-轻量清单已确认) 的四个字段。

### 3.4 执行内置命令的详细时序（UC2）

独立对应 BU2、BU4、BU5，不在整体时序中。已实现（mode 待实现）。

![执行内置命令的详细时序](execute_builtin_command.svg)

[原尺寸 SVG](execute_builtin_command.svg) · [PlantUML 源码](diagram.puml#L67)

| 生命线 | 映射 |
|---|---|
| 命令接口 | `RuntimeCommandController.execute` |
| 命令执行服务 | `CommandExecutionService.executeBuiltinAndAwait` 与 `CommandResponseAssembler` |
| 命令注册表 | `CompositeCommandRegistry.resolve(agentSnapshot, BUILTIN)`：调用来源前按类别过滤，不读 Skill 来源 |
| 命令处理器 | 各 Builtin Contributor 绑定的 Handler |
| 会话业务服务 | `SessionModelConfigurationService`、`SessionThinkingConfigurationService`、`SessionCompactionApplicationService` 等 |

- 执行顺序：读取会话、归一 arguments、单次解析、按名称精确查找、参数准入、锁内复核、调用 Handler、组装结果。合法但未注册的名称为 COMMAND_NOT_FOUND；Builtin 名称正则不覆盖 `skill:*`。
- 成功结果复用 GET Session 或 GET Models 的完整资源；Help、Compact、Skills 没有对应独立接口，只返回最小业务结果。结果不含 command、changed、sourceEventSeq，也不返回 ETag。精确映射见 [内置命令 §8](../../04-命令与技能/01-内置命令/README.md#8-json-与错误)。
- Compact 断线不取消，调用方通过 GET Session/Events 对账，不自动重放；Mate 凭据只在本次 Active Holder 中保留到执行结束，见 [内置命令 §7](../../04-命令与技能/01-内置命令/README.md#7-compact-生命周期)。

<a id="execute-skill-sequence"></a>

### 3.5 执行技能命令的详细时序（UC3）

展开整体时序步骤 10～19。Runtime 执行、原始调用与展开内容分离、恢复已实现；统一 Definition/Handler 与版本快照待实现。下钻图见 [技能命令 §4](../../04-命令与技能/02-技能命令/README.md#4-统一实施与集成要求)。

- 请求为 `name=skill:<name>`、可选 arguments 与最多四个 fileIds；在实际执行的 Agent 快照上找到绑定 Skill，展开为“正文 + 空行 + arguments”作为内部模型输入。
- 受理后首帧是展开前的 `user.message`，其 eventId 即本次根消息；随后复用普通 Agent、工具和 `session.status_idle` 事件。遇到需要确认的工具时发出 `reason=confirming` 后关闭本次 SSE，确认通过 Session Events 继续；断线不取消执行。
- 目标结构：SkillCommandDefinition 组合准入策略与真实 SkillCommandHandler，Handler 委派 SkillExecutionService，经 SessionEventApplicationService 复用普通消息受理；PreparedSkillInvocationDTO 固定正文、元数据和版本。

## 4. 接口协议

| 操作 | 方法与路径 | 成功结果 | 详细契约 |
|---|---|---|---|
| ListAgentCommands | `GET /campusclaw-service/v1/agents/{agentId}/commands` | 200，ResultBean 包裹 `commands` 数组 | [查看 Agent 命令清单](../01-CampusClaw多Agent运行时/chat-api-review.html#ListAgentCommands) |
| ExecuteSessionCommand | `POST /campusclaw-service/v1/sessions/{sessionId}/command` | Builtin 200 JSON；技能命令 200 SSE | [执行会话命令](../01-CampusClaw多Agent运行时/chat-api-review.html#ExecuteSessionCommand) |

<a id="31-get-轻量清单已确认"></a>
<a id="32-get-轻量清单已确认"></a>

### 4.1 描述符与排序

| 字段 | 必填 | 契约 |
|---|---|---|
| name | 是 | 不带前导 `/`；Builtin 裸名或 `skill:<name>`，稳定标识命令 |
| type | 是 | `builtin` 或 `skill`，必须与 name 的命名空间一致；不表示控件或响应类型 |
| description | 是 | 命令用途的非空说明；描述语言待确认（T6） |
| hints | 否 | 有序非空字符串数组；无提示时省略或 `[]`，不返回 null；只用于展示，不是参数 Schema、枚举、必填规则或权限 |

- 排序固定为 help、status、name、model、thinking、mode、compact、skills，再追加按 name 升序的技能命令。服务端控制顺序，客户端只做前缀过滤，不重新排序。理由：内置命令的使用频率和语义分组稳定，技能数量不定，按名称追加最好找。
- 清单只用 agentId 标识，不接受前缀、搜索词或 forceReload。理由：清单规模小，过滤在前端完成；强制刷新会绕过 Agent 发布流程。
- 不返回 kind、input、available、unavailableCode、allowedValues、catalogVersion、acceptsFiles。理由：这些是内部准入或会话相关信息，Agent 级清单无法给出正确值。
- 响应 `Cache-Control: no-store`，不返回 ETag。前端可在页面内存中按 Agent 复用一份清单（见前端 §5），不做持久缓存。
- 技能命令都允许可选附件，Builtin 都不接收附件；不按 Skill 建附件白名单，允许附件不代表任意格式都能处理。

<a id="command-state-rules"></a>

### 4.2 命令状态规则

清单不随会话状态变化；下表是前端限制输入和 POST 准入共同遵循的唯一规则。

| 命令 | hints 示例 | 会话空闲 | 会话运行中 |
|---|---|---|---|
| help | `[]` | 无参查询 | 无参查询 |
| status | `[]` | 无参查询 | 无参查询 |
| name | `["displayName"]` | 查询或改名 | 查询或改名 |
| model | `["modelId"]` | 查询或切换 | 仅无参查询 |
| thinking | `["on\|off"]` | 查询或修改 | 仅无参查询 |
| mode | `["plan\|build"]` | 查询或切换 | 仅无参查询 |
| compact | `[]` | 无参压缩 | 禁止，前端置灰，POST 返回 409 SESSION_BUSY |
| skills | `[]` | 无参查询 | 无参查询 |
| `skill:<name>` | `["request"]` | 可选文本和附件 | 禁止，前端置灰，POST 返回 409 SESSION_BUSY |

- hints 在两种状态下相同，不以缺失或变化表达禁止输入。
- 前端按 type/name 选择控件：model 候选取自 ListSessionModels，thinking 为开启/关闭，mode 为 plan/build，name 与技能命令用文本输入。POST 只提交 name、可选 arguments，技能命令另可提交 fileIds。
- 会话状态未知、恢复中或清单读取失败时暂停提交。状态从空闲变为运行中时保留参数草稿并禁用修改；409 后刷新会话状态，保留草稿，不自动重放或降为查询。
- 交互层遇到 Slash 先按清单精确匹配；清单失败、未命中或形态不支持时保留草稿并提示，不当作普通消息发送。

mode 的业务与事务见 [内置命令 §6.1](../../04-命令与技能/01-内置命令/README.md#mode-command)；选择 build 不批准计划，也不启动执行。

### 4.3 执行请求

- Builtin 只接收 name 与 arguments，arguments 缺省或 null 由服务归一为空串，最多 262144 个 UTF-16 代码单元；拒绝 fileIds 和其他未知字段。
- 技能命令另接收最多四个不重复的 32 位十六进制 fileId；显式 null 拒绝。
- 共享入口先按 name 选定类别，再应用该类别的约束；不得用 Builtin 名称正则全局拒绝 `skill:*`。

## 5. 架构指标

### 5.1 安全性

- Runtime 是内部接口，调用方授权由上游 Mate 或部署边界保证。按 agentId 查询清单与按 agentId 创建会话的信任边界相同，不额外校验会话归属。
- 清单不是授权：任何执行都在 POST 内重新解析并在所属锁或事务内复核绑定、状态和参数。
- 描述符不暴露 Skill 正文、存放路径、版本、内部 ID 或凭据；Skill 正文只进入会话内部模型上下文，不提升为系统权限。
- Builtin 调用方无需发送执行凭据；技能命令可携带四项可选凭据，只随实际 Mate 工具调用发送，不写入会话、事件或日志。

### 5.2 稳定性

<a id="failure-recovery"></a>

#### 5.2.1 失败处理与恢复

**不变量**（任何失败都不能破坏）：

1. 清单要么完整（全部 Builtin 加完整快照中的全部绑定 Skill），要么整体失败。
2. 被拒绝的 POST 不写成功历史，不改变会话状态，不回退为普通消息。
3. 已受理的命令不因断线而取消，也不被自动重放。

| # | 失败 | 发生阶段 | 副作用状态 | 处理方 | 系统处置 | 用户可见结果与下一步 | 不保证项 |
|---|---|---|---|---|---|---|---|
| F1 | agentId 格式错误 | UC1 参数校验 | 未发生 | CampusClaw | 400 INVALID_AGENT_ID | 清单读取失败，保留草稿 | — |
| F2 | Agent 不存在 | UC1 准备快照 | 未发生 | CampusClaw | 404 AGENT_NOT_FOUND | 提示 Agent 不存在 | — |
| F3 | Agent 不可用或从 Mate 准备失败 | UC1 准备快照 | 未发生（失败时保留原有缓存） | CampusClaw | 422 AGENT_NOT_AVAILABLE | 显示“重试清单”，重试只调 GET | Mate 短暂故障也是 422，不带 Retry-After |
| F4 | 会话不存在 | UC2/UC3 读取会话 | 未发生 | CampusClaw | 404 SESSION_NOT_FOUND | 前端刷新会话 | — |
| F5 | 清单显示可用但会话已运行 | UC2/UC3 锁内准入 | 未发生 | CampusClaw | 409 SESSION_BUSY | 刷新会话状态，保留草稿，等待用户再次操作 | 清单与会话状态不是跨请求原子快照 |
| F6 | 命令或技能已不再绑定 | UC2/UC3 解析 | 未发生 | CampusClaw | 404 COMMAND_NOT_FOUND | 前端标记清单过期并重新读取 | — |
| F7 | 参数非法 | UC2/UC3 参数准入 | 未发生 | CampusClaw | 400 INVALID_COMMAND_REQUEST | 保留草稿并提示 | — |
| F8 | Builtin 业务写入失败 | UC2 Handler | 未发生（事务回滚） | CampusClaw | 500 对应业务错误码 | 提示失败，读取会话对账 | — |
| F9 | Compact 或技能命令执行中断线 | UC2/UC3 执行 | 已提交或执行中 | 前端 | 服务端继续执行 | 重连后读 GET Session/Events 对账 | 不自动重放，不恢复断线期间的临时增量 |
| F10 | 技能命令受理后执行失败 | UC3 执行 | 已提交 | CampusClaw | SSE 以 `session.status_idle(reason=failed)` 结束 | 显示失败；可重新提交 | 已执行的工具副作用不回滚 |
| F11 | 技能命令的缓存不可用、解析失败、事件流背压 | UC3 受理前 | 未发生 | CampusClaw | 设计为 503 SKILL_AGENT_UNAVAILABLE、500 SKILL_PREPARATION_FAILED；实现分别返回 422 AGENT_NOT_AVAILABLE、500 COMMAND_EXECUTION_FAILED，背压的 503 也被改成 500（T5） | 提示失败 | 实现修正前无法区分可重试错误 |

#### 5.2.2 容量与限流

- 清单查询不占会话执行容量；Agent 快照的读取与准备在 Agent 级锁内串行，同一 Agent 的并发冷查询只准备一次。
- 回源 Mate 的次数上限约为“每个 Agent × 每个实例一次”，之后命中完整缓存；Agent 发布新版本后的刷新沿用既有显式刷新流程。
- 技能命令与普通消息共用单消息准入与运行容量，超限为 503 RUNTIME_CAPACITY_EXCEEDED。
- 【缺口】未压测，不给出容量数值。

#### 5.2.3 监控告警

| 指标 | 为什么需要 | 告警条件 |
|---|---|---|
| 清单查询触发 Mate 准备的次数与耗时 | D2 接受了首次查询访问 Mate 的代价 | 【缺口】阈值待压测后确定 |
| 清单查询 AGENT_NOT_AVAILABLE 比例 | 区分 Agent 配置问题与 Mate 故障 | 【缺口】 |
| 命令 POST 的 SESSION_BUSY 次数 | D1 把运行中的过滤交给前端，比例升高说明前端状态规则失效 | 【缺口】 |

现有失败日志使用 `campusclaw.failure` 事件与 errorCode 字段，见 [调用日志](../05-CampusClaw调用日志/README.md)。

#### 5.2.4 应急预案

【缺口】未定义。

<a id="compatibility"></a>

### 5.3 兼容性

- `GET /sessions/{sessionId}/commands` 直接改为 `GET /agents/{agentId}/commands`，不双写、不保留兼容期（T3）。理由：Runtime 是内部接口，唯一消费方 Claw 前端在同一实现仓，可同版本切换；Mate 公共清单尚未开放执行。
- 描述符字段从 kind/input 迁移到 type/hints 是已确认的待实现增量，与路径迁移可在同一批次交付，同样不双写。
- 前端需要从当前会话取得 agentId；创建会话已使用 agentId，无需新增来源。

## 6. 质量保证

### 6.1 灰度能力

【缺口】Runtime 与前端同版本发布，无独立灰度开关。

### 6.2 回滚能力

前后端一起回滚到旧版本即可恢复按会话读取清单；不涉及数据迁移。单独回滚其中一端会导致清单读取 404，不允许。

<a id="5-实施与验收"></a>

### 6.3 自动化测试

| 范围 | 覆盖内容 |
|---|---|
| 清单 | 固定顺序、完整空 Skill、冷缓存准备一次、Agent 不存在 404、不可用 422、无内部字段泄漏、不读会话、同一 Agent 并发查询只准备一次 |
| 描述与准入 | `describe()` 不依赖会话；运行中 compact 与技能命令被 POST 拒绝；hints 两种状态相同 |
| 执行 | 来源过滤、重名启动失败、单次解析、Help 三个业务字段、Name 无历史、同值不写 Entry、无通用命令记录 |
| 技能命令 | 正常 SSE、确认分段、原消息中断、公开历史不含正文、解析失败不受理 |
| 前端 | 按 agentId 读取并按 Agent 复用、状态规则集中生效、409 后保留草稿、未命中 Slash 不发普通消息 |
| 设计门禁 | 运行 `validate-global-class-view.py`、`validate-chat-http-v1.py` 与 `check-diagrams.py --render`；这些检查不证明视觉可读性 |

### 6.4 QA 流程

【缺口】未定义。

## 7. 基建规范

- 遵循 Java DTO/VO、方法长度、版权头与中文注释规范；内部结果用 DTO，响应用只读 VO。
- 参数缺省只在 Service 归一；标准输入约束放在请求 VO 或路径参数上。
- 不新增 Maven 依赖。
- 单次开发和 PR 不设新增代码行数上限，按职责和可独立验证的边界划分批次；前一 PR 合并后再开下一个。

## 8. 其他补充

<a id="current-runtime-status"></a>

### 8.1 当前实现与剩余增量

| 能力 | 状态 | 核验提交与证据 |
|---|---|---|
| 按 Agent 查询清单 | 待实现 | `fd431002`：仍为 `/sessions/{sessionId}/commands`，描述依赖会话，见 [源码证据 §1.1](source-evidence.md#agent-catalog-evidence) |
| type/hints 描述符 | 待实现 | `fd431002`：`CommandDiscoveryResponseAssembler` 仍输出 input{hint, acceptsFiles} |
| 七个 Builtin 与业务响应 | 已实现 | `53eff85c`，路径见 [内置命令 §8.3](../../04-命令与技能/01-内置命令/README.md#83-当前-runtime-实现与验收边界) |
| mode Builtin | 待实现 | `fd431002`：Contributor 仍只有七个 |
| 统一 Session POST | 已实现 | `53eff85c`：RuntimeSessionController.update → RuntimeSessionUpdateService.update |
| Skill 严格名称 | 已实现 | `53eff85c`，见 [技能命令 §4.2](../../04-命令与技能/02-技能命令/README.md#42-当前实现剩余增量与测试证据) |
| Skill Runtime POST/SSE 与文本分离 | 已实现 | `53eff85c`；错误码差距见 F11 |
| Skill 统一结构与版本快照 | 待实现 | `53eff85c` |
| Skill 使用统计 | 部分实现 | `dad4433d`，见 [统计源码证据](../../04-命令与技能/03-Skill加载统计/source-evidence.md) |
| Claw 前端 Slash | 已实现 | `53eff85c`；按 agentId 读取待实现 |
| Mate 公共命令 | 待定 | 只确认描述符投影，见 [Mate 聊天命令 API](../../02-服务与接口/06-mate-service聊天命令API/README.md) |

未运行 Java、数据库或前端测试；实现存在不等于契约验收完成。

### 8.2 证据与对比

源码与外部基线核验记录见 [source-evidence.md](source-evidence.md)；跨基线比较见 [Agent 架构对比 M05](../07-Agent架构对比/README.md)。Skill 统计口径由 [Skill 成功调用统计](../../04-命令与技能/03-Skill加载统计/README.md) 维护。

### 8.3 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.1.0 | 2026-10-16 | 专题迁到 `01-总体架构/04-CampusClaw命令系统`，图源与 SVG 平铺到专题根，对齐总体架构的命名与布局；内容不变。 |
| 2.0.0 | 2026-10-16 | 按设计模板重写；命令清单改为按 agentId 查询，运行中的限制交给前端状态规则与执行准入。 |
| 1.18.0 | 2026-10-10 | Skill 统计复用统一最终工具结果，同事务累计且删除会话不扣减。 |
| 1.17.0 | 2026-10-10 | Skill 统计按最终成功调用计数，登记 #335 实现及公共观察改造边界。 |
| 1.16.0 | 2026-10-04 | Slash 响应取消 ETag，配置写入复用数据库锁内最新记录与原子提交。 |
| 1.15.0 | 2026-09-22 | 增加 mode 命令，复用 Session 模式事务并区分查询、切换与计划审核。 |
| 1.14.0 | 2026-09-22 | 命令描述符采用 type 与 hints，分离输入提示、会话状态和附件规则。 |
| 1.13.0 | 2026-09-22 | 明确命令选项交互与 hint 的分工，并统一所有可用 Skill 的附件能力说明。 |
| 1.12.4 | 2026-09-22 | 按 53eff85c 分列当前 Runtime、Skill、前端实现及结构、版本快照和统计增量。 |
| 1.12.3 | 2026-09-22 | 补充命令字段与调用示例入口，并区分中文展示样例和实际描述语言。 |
| 1.12.2 | 2026-09-22 | 按 53eff85c 更正 Help 缓存、查询、响应与统一 POST 的已实现状态。 |
| 1.12.1 | 2026-09-22 | 将 Help Agent 使用场景字段统一为 `useCases`，与 Runtime 命令契约保持一致。 |
| 1.12.0 | 2026-09-18 | Skill 统计查询改为批量 POST，其他命令与采集结论保持原核验范围。 |
| 1.11.0 | 2026-09-16 | 显式与 Read 共用根执行使用统计，受理后独立记录。 |
| 1.10.0 | 2026-09-15 | Skill 调用事实通过共享受理与结果追加事务接入统计。 |
| 1.9.1 | 2026-09-15 | 统计先按 Skill 调用事实与既有模块边界推导。 |
| 1.9.0 | 2026-09-15 | 将 Skill 加载统计归入 M05 并明确与命令清单的职责边界。 |
| 1.8.2 | 2026-09-14 | 清理确认过程叙述并明确公共核心、发现证据与专题分工。 |
| 1.8.1 | 2026-09-14 | 取消开发、PR 及模块/镜像新增行数预算，按职责和验收边界组织交付。 |
| 1.8.0 | 2026-09-08 | Skill 使用请求级 SSE 并复用消息接受链，Builtin 保持 JSON。 |
| 1.7.0 | 2026-09-07 | 定义独立 Slash Composer、草稿、临时结果与恢复边界。 |
| 1.6.0 | 2026-09-07 | Command 成功响应复用业务资源，Help 返回三个业务字段。 |
| 1.5.0 | 2026-09-07 | GET 返回轻量描述符并统一排序、状态过滤与交互路由。 |
| 1.4.3 | 2026-09-07 | 全局主图连贯展示完整职责链，局部图只作补充。 |
| 1.4.2 | 2026-09-07 | Compact 凭据保留至执行结束，完成后按需提交新执行。 |
| 1.4.1 | 2026-09-05 | 统一 Builtin、Skill 与共享 HTTP 的集成验收。 |
| 1.4.0 | 2026-09-04 | Help 委派元数据指南服务，内容不依赖命令清单。 |
| 1.3.2 | 2026-09-04 | Skill 加载、发现和执行采用同一严格名称规则。 |
| 1.3.1 | 2026-09-04 | 区分 Builtin 实施切片与完整 Skill 产品能力。 |
| 1.3.0 | 2026-09-04 | 建立单次清单快照、窄职责服务和领域历史边界。 |
| 1.2.0 | 2026-09-03 | 明确 HTTP、应用、命令核心与 Runtime 适配层及对象生命周期。 |
| 1.1.0 | 2026-09-03 | 通过请求级清单快照共享发现与执行解析结果。 |
| 1.0.4 | 2026-09-01 | 统一命令清单与 Skill 文件夹术语。 |
| 1.0.3 | 2026-09-01 | 名称遵循 Agent Skills 规则，参数复用普通消息限制。 |
| 1.0.2 | 2026-08-31 | 以短句和规则表说明命令行为。 |
| 1.0.1 | 2026-08-31 | 明确命令清单是按 Session 解析的逻辑注册表。 |
| 1.0.0 | 2026-08-31 | 建立 Builtin 与 Skill 的注册、可用性及持久化公共边界。 |
