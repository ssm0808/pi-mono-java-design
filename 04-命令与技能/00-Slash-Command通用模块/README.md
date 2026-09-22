# CampusClaw Slash Command 通用模块设计

[返回命令与技能导航](../README.md)

| 属性 | 值 |
|---|---|
| 文档版本 | 1.12.2 |
| 更新日期 | 2026-09-22 |
| 设计仓基线 | `0eaa70ff365bf4d4e328b3473809341ca4cfc58d` |
| CampusClaw 分析基线 | `d84dd3d6a306b7587c70b29e0100e741dacef989` |
| Help 专项源码基线 | `53eff85c7f41de23eb434e027782f5085a8b8e45`；Help 缓存、Agent 级锁、查询、响应与统一 POST 已实现，不替换其他行为的历史证据点 |
| 初始 Command 发现候选 | `0bb794f222273e12fc24fe98d6ab4e9013ac8599`（PR #210） |
| 发现层前置证据 | `9d0d76f4a571b559dc77ae52736caebbcc8fad88`；已通过 a8192e047f4061bd385297d3dc6c4358362d0d49 合并 |
| Command GET 候选 | `7759481a1722422395d46564129827c6ee6df204`（未发布） |
| 状态 | 用户确认的目标设计；Help 公开实现已落地，其他范围按本文各自证据状态跟踪 |

前端 Composer、命令清单、独立草稿、临时结果和错误恢复由
[Slash Command 前端专项](../../07-前端设计/技术设计/命令/README.md)统一维护；本文件继续维护共享 Command 核心与 HTTP 语义，
不在两处重复定义交互状态机。[打开前端交互评审稿](../../07-前端设计/原型/slash-command-review.html)。

## 1. 职责与目标

Builtin 实现切片覆盖 `help`、`status`、`name`、`model`、`thinking`、
`compact`、`skills` 七个 Builtin。共享 GET 按固定 Builtin 顺序与 Skill 名称顺序返回轻量清单，
POST Command 按类别返回：Builtin 普通 ResultBean JSON，Skill 请求级 SSE。

Builtin 与 Skill Command 由用户统一负责设计、实现和集成。共享 GET 的轻量描述符、两类命令合并、固定排序与状态过滤已确认；Builtin 来源过滤只适用于内部 Builtin 专属解析，不是共享 GET 的全局限制。POST 保留已确认 Builtin JSON 契约；Skill 请求联合类型、SSE 和恢复语义已由 B13/B14 确认，精确契约与 Events 已同步。

`/` 只在交互层使用。Builtin POST 只接收 `name + arguments`，不接收附件或整段 Slash 文本。
普通 POST Events 不解析 Slash，既有请求级 SSE 行为不变。
本期不生成公开 commandId，也不持久化通用命令生命周期或 Name 边车历史。

### Skill 统计职责

[Skill 使用统计](../03-Skill加载统计/README.md)维护 M05 的使用信号、根执行/Skill 去重、累计/日表及批量 POST 查询（F19 已对齐 PR #295，排名、趋势暂缓）；[Codex 专项](../03-Skill加载统计/codex-skill-counting.md)维护固定源码机制。显式输入受理提交后与通用 Read 最终成功观察共用执行级 Tracker，三张统计表独立事务且失败不影响主执行。首版 Runtime，目标已确认、待实现；精确口径、权限、失败和 Child/Cron 接入前提由该专题维护。

### 1.1 全局目标类图

`/` 展示命令清单；已确认的 `/help` 无参展示当前 Agent 的用途和场景。
主图以设计仓 `06bea56c7a725bb749cffb6682bcf98a8f51884a` 的完整版为结构与排版基线，
保留 Web、Application、Command Core、Builtin 委派和 Runtime/持久化的完整关系。
主图完整表达 Help 元数据查询、Builtin 委派、Skill 执行和共享消息接受链。
主图中 Help 的 Contributor/Handler 委派、AgentHelpQueryService、AgentRuntimeManager 和响应投影关系已实现；
其他装配关系的状态仍按各专题源码证据确定。分组仅归并重复实现，不把 Handler、业务服务、Coordinator 和 Repository 合成一个对象。

![Slash Command 完整全局目标类图](设计图/target_slash_command_global_classes.svg)

[PlantUML 源码](设计图/diagram.puml#L95) · [展开原尺寸 SVG](设计图/target_slash_command_global_classes.svg)

文档内缩略图用于定位整体分层；阅读类名、箭头和多重性时展开原尺寸 SVG，不通过缩小图中文字适配窄页面。

Builtin 直接引用这份主图；Help 专题只补充元数据、缓存与结果投影，不再替代全局视图。
分组框表达协作关系而非 Java 包：AgentHelpQueryService 和其他窄业务服务仍属于应用 Service 层。
七个 Contributor/Handler 的精确命令映射见[内置命令服务表](../01-内置命令/README.md#2-全局目标与核心扩展)。

| 主图保留的职责关系 | 不能合并的原因 |
|---|---|
| CommandDefinition → BuiltinCommandDefinition；Catalog → Definition | 通用发现抽象和可执行 Builtin 不是同一职责；请求内固定 Definition 身份 |
| Contributor → Handler → 窄业务服务 | 分别负责装配、命令适配和业务约束；新增命令不修改中央名称 switch |
| 窄业务服务 → Coordinator → Holder/Session/Projector → Repository | 区分执行协调、执行范围对象与持久化；最终准入仍在所属锁内完成 |
| Help Contributor 内 Handler lambda → AgentHelpQueryService → AgentRuntimeManager | Help 消费同一完整 Agent 元数据快照，不反向依赖命令清单 |

通用命令抽象的历史证据仍保留 pi-mono-java `d8e22562`。Help 专项已在
`53eff85c7f41de23eb434e027782f5085a8b8e45` 复核 `HelpCommandContributor.definition`、
`AgentHelpQueryService.query`、`AgentRuntimeManager.prepareCached/toIdentity/toRuntime/withAgentLock`、
`CommandResponseAssembler.help` 和 `RuntimeCommandController.execute`；这些符号证明 Help 完整装配已存在。

Help 的结果精确为 displayName/description/useCases，字段和缓存规则见
[Help 专项设计](../01-内置命令/Help-Agent使用指南/README.md)。其他命令不变。

![补充分层视图](设计图/target_slash_command_boundaries.svg)

[PlantUML 源码](设计图/diagram.puml#L1)

## 2. 源码证据与差距

下表路径均相对 pi-mono-java 仓库；只把候选 PR 中已存在的符号标成候选行为，不当作 main 已实现。

| 基线与路径 | 观察行为 | 目标差距 |
|---|---|---|
| d84dd3d6：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/command/SlashCommandRegistry.java` | 旧原型用可变 Map 并解析整段 Slash；未接入生产 HTTP | 最终 HTTP PR 删除旧原型 |
| 0bb794f2：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/CompositeCommandRegistry.java`，`resolve` | 合并所有 Source 为一次请求的 Catalog | 调用 Source 前按 CommandKind 过滤 |
| 0bb794f2：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/CommandDefinition.java` | 只有发现元数据，没有 Handler | Skill 仅展示；Builtin 携带准入与 Handler |
| 0bb794f2：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/ResolvedCommandCatalog.java` | 固定请求内 list/find 视图 | 清单、准入、执行共用 Definition 身份；Help 内容不来自清单 |
| 7759481a：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeCommandController.java` | 未发布 GET 候选依赖 Catalog Service | GET/POST 在最终 PR 同时发布 |
| d84dd3d6：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionConfigurationService.java` | Model/Thinking 与 HTTP If-Match 绑定 | 提取可选 expectedVersion 的窄服务 |
| d84dd3d6：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java`；`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/runtime/RuntimeSessionHolder.java` | 活动执行、控制队列与清理已存在 | Compact 复用生命周期，单独完成 JSON Future |

已合并的前置实现 `9d0d76f4`（main 合并点 `a8192e04`）已将发现数据改为
`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/ResolvedCommandDTO.java`
与同包 `SkillCommandSnapshotDTO.java`，并由 InputDTO 复制 suggestions、Catalog 复制外层列表。
`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/skill/SkillNamePatterns.java`
已集中兼容/严格正则字符串、编译模式和长度上限；SkillNameValidator 与旧展示 DTO 已删除。
其中加载宽松、发现严格的策略分裂是必须整改的差距，不是已确认的存量兼容要求。
来源过滤、可执行 Builtin 定义和七个 Contributor 仍属于后续核心 PR，不因前置发现层存在而视为已实现。

上述结论限于旧证据点，不再用于判断 Help 当前实现状态。
Help 在 `d1cdb708e3e124cae009b10b985f5832b6dbde01` 已实现同一链路，但场景字段当时误名为 `userCases`；
`53eff85c7f41de23eb434e027782f5085a8b8e45` 已将该字段在缓存、DTO、VO 和调用方统一为 `useCases`。具体路径、符号和验收边界见
[Help 源码证据](../01-内置命令/Help-Agent使用指南/README.md#5-源码证据与设计理由)。

### 外部基线

| 基线 | 源码观察 | Java 决策与理由 |
|---|---|---|
| pi `4af9d21d3b4d664e4a29fcabfec85171077248e3` | `packages/coding-agent/src/modes/interactive/interactive-mode.ts` 本地分派；`packages/coding-agent/src/core/agent-session.ts` 的 `_tryExecuteExtensionCommand` 直接调用 Handler；`packages/coding-agent/src/core/session-manager.ts` 保存领域 Entry | 保留 Session 领域语义，不照搬 CLI 入口（产品约束） |
| OpenCode `849c2598abc7d2b40261e74b5826bc74ffc78308` | `packages/opencode/src/server/routes/session.ts` 的 command POST 返回 JSON，事件流独立 | 普通 JSON 与命令调用结果相匹配，不需要通用生命周期存储（架构变更） |
| Codex `be33f80bc65159c094ecd06bf155afa3061ce23d` | `codex-rs/app-server-protocol/src/protocol/common.rs` 定义结构化 Thread/Skill 操作 | 学习结构化边界，不复制 JSON-RPC 通知（架构选择） |
| DeepSeek Harness `141eb6fef83422698aef7a981029e843e8161534` | `packages/interaction/commands/src/index.ts` 的 CommandExecution 与命令日志 | 当前产品不需要通用命令日志（产品约束） |

设计仓固定 pi 基线是 `5cd93f688aaab89dbb6dfa4aca535f21796ae185`，本次同时记录
`4af9d21d` 对照；Command/Session 核心语义未改变。Codex 原固定
`d58d0e5841e0de08e251673db2d5af8cf3a1ad51` 和 DeepSeek 原固定
`0a53fb55bea101816fa226bb964ae2bed71c343b` 保留为历史参考点，本次只使用表中明确标注的新快照；
DeepSeek 仍是 alpha 对照，不视为行业稳定契约。

## 3. 分层与生命周期

| 层 | 职责 |
|---|---|
| Web | 请求/响应 VO、Jakarta 校验、Locale/Header 捕获和 ResultBean |
| Application | Session 授权、输入归一、一次 Catalog 解析、准入、执行和 DTO→VO |
| Core | Definition、来源过滤、Contributor、Admission Policy、Handler 和不可变 Catalog |
| Domain Service | Name、Model、Thinking、Compact 等窄职责业务 |
| Infrastructure | Repository、操作锁、容量、Active Holder、Projector 和控制队列 |

Controller 不依赖 Repository、Registry、Holder 或内部 DTO。Spring 单例无请求状态。
每个 GET/POST 只解析一个不可变 ResolvedCommandCatalog，Help 不反向注入 Registry。
Catalog 用于找到 Help Definition 与执行上下文；Help 内容由 AgentHelpQueryService 从一份完整 PreparedAgentRuntime 投影，
不再依赖 CommandHelpFormatter。缓存读取与发布共用 Agent 级锁，不占 Session 执行容量。
共享快照只固定 Definition 身份和元数据；状态变更必须在数据库行锁或 Runtime 操作锁内重新准入。

![请求级 Catalog](设计图/target_command_resolution_classes.svg)

[PlantUML 源码](设计图/diagram.puml#L43)

- `resolve(context, BUILTIN)` 仅用于内部 Builtin 专属解析，在调用 Source 前过滤类型；共享 GET 使用完整来源解析，不套用此快路径。
- 七个 Contributor 各自贡献元数据、准入策略和 Handler；启动期重名直接失败。
- 当前发现层的 Skill Definition 只供展示，不安装抛错的伪 Handler；真实执行定义纳入统一实施计划，不强制复用 Builtin 类型。
- 新增命令不修改中央名称 switch；结果类型分派只能出现在 DTO→VO 组装器。
- 内部结果使用 DTO，响应使用只读 `@Getter` 与 final 字段的独立 VO。
- 参数缺省只在 Service 归一；标准输入约束放在请求 VO/API 参数并实际触发 Jakarta 校验。

### 3.1 Skill 名称统一规则

Skill 名称必须匹配 `^[a-z0-9]+(?:-[a-z0-9]+)*$`，同时单独校验 1～64 字符长度。
`SkillNamePatterns` 只保留一份严格正则字符串、编译后的 Pattern 和长度上限；加载、
命令发现和执行全部引用，不保留 LEGACY 分支，也不在 HTTP/Command 包中另设名称 Validator。
非法名称在加载时就拒绝，不能进入已加载集合、模型发现提示词或命令清单；执行不得绕过。
`SKILL.md` 的 `name` 必须是非空字符串且与文件夹同名，不能通过回退、裁剪或自动改名接受。

这是已确认产品约束与安全加固，同时适用于 Skill 执行；Builtin 的来源过滤不改变该规则。
名称专项源码证据和完整验收见 [Skill 设计](../02-技能命令/README.md#3-名称统一严格校验)。

<a id="31-get-轻量清单已确认"></a>

### 3.2 GET 轻量清单（已确认）

Runtime GET 的精确模型见[当前接口](../../01-总体架构/01-CampusClaw多Agent运行时/chat-api-review.html#listSessionCommands)；
Mate GET 同步相同 Descriptor，但公共认证、bridge、错误映射与 POST 发布仍需独立评审。

| 字段 | 必填 | 契约 |
|---|---|---|
| name | 是 | 不带前导 /；Builtin 裸名或 `skill:<name>` |
| kind | 是 | builtin 或 skill |
| description | 是 | 命令用途的非空说明 |
| input | 否 | 缺失表示当前仅允许无参数、无附件调用；不返回 null 或空对象 |
| input.hint | input 存在时必填 | 非空展示文本；`[x]` 为可选输入、`<x>` 为必填输入，不参与参数校验 |
| input.acceptsFiles | 否 | 只在 true 时输出，缺失为 false；Builtin 一律省略 |

删除的七项为 available、unavailableCode、input.mode、input.available、input.unavailableCode、
input.placeholder、input.suggestions；不以 allowedValues、catalogVersion 或其他候选值字段替代。

| 命令 | idle 的 input | running 的 input / 可见性 |
|---|---|---|
| help | 无 | 无，保留；不恢复 [command] |
| status | 无 | 无，保留 |
| name | hint=[displayName] | 不变 |
| model | hint=[modelId] | 省略 input，仅查询 |
| thinking | hint=[on\|off] | 省略 input，仅查询 |
| compact | 无 | 整项省略 |
| skills | 无 | 无，保留 |
| `skill:<name>` | hint=[request]，acceptsFiles=true | 整项省略 |

Builtin 固定按 help、status、name、model、thinking、compact、skills 排列，再追加按 name
升序排列的 Skill。过滤后保留相对顺序；服务端控制显示顺序，客户端不重新排序。
同一次 GET 必须先取得完整 Agent 缓存并解析完整来源，即使 running 会隐藏 Skill 也不返回
残缺的 Builtin 列表；无完整缓存返回 503 AGENT_NOT_AVAILABLE，保留 Retry-After: 3。
不得自动刷新、远程补拉或调用模型。完整缓存中的空 Skill 绑定是成功，不等于缓存缺失。

这是展示投影，不是执行授权凭据或预约。保留内部 Admission Policy/DTO 的状态字段供服务端使用，
DTO→VO 时执行过滤与省略规则；不能把内部 DTO 直接序列化。
每个 POST 重新解析独立 Catalog，在所属事务或锁内复核可变状态、绑定与参数。
Builtin POST 的 400/404/409/422/500/503 和普通 JSON 保持后续已确认契约，特别是 Help 无缓存仍为 422；
GET 需按 operation 映射 503，不能全局修改同名错误的 422 映射。Skill POST 以 B13/B14 的明确确认生效，不能由 GET 示例自动确认。

交互层遇到 Slash 时，先按清单精确匹配。清单失败、命令未命中或形态不支持时保留草稿并提示，
绝不把未匹配 Slash 自动当成普通消息；直接普通消息 API 仍不解析 Slash。
清单读取后 Session 状态可能变化，POST 拒绝时刷新清单，不自动重放副作用请求。

### 3.3 发现层证据与验收

发现层证据固定于 `pi-mono-java@6f52fddc87a03c20916fc7b6ef1de87f6a7a8cf5` 核对发现层，
不把旧 d84dd3d6/d8e22562 的差距表当作当前全部实现状态。
以下均为实现仓相对路径：

| 源码 / 符号 | 本次观察 | 目标差距 |
|---|---|---|
| modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/service/command/CompositeCommandRegistry.java · resolve | 全来源解析与 CommandKind 过滤均存在，TreeMap 按名称排序 | 共享 GET 用全来源；VO 投影改为固定 Builtin 顺序，不改变内部快路径 |
| modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/catalog/ResolvedCommandCatalog.java · list/findDefinition | 请求快照保存发现 DTO 与 Definition 身份 | 保留请求级身份，不把 GET 快照跨请求当作授权 |
| modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/dto/command/ResolvedCommandDTO.java · InputDTO | 内部仍有 mode、双层 available、placeholder、suggestions | 允许内部保留，禁止泄漏进轻量响应 VO |
| modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/service/command/SkillCommandSource.java · list/resolved | prepareCached 缺失返回空清单；running 生成不可用标记 | 共享 GET 在组装前区分缓存缺失与完整空绑定，缺失整体 503；running 整项过滤 |
| modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/service/command/BuiltinCommandSource.java · definitions/list | Contributor 来源已装配，内部按名称排序 | 在 Application 投影固定显示顺序；不集中按名称执行 |
| modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/ | 该固定 commit 无 RuntimeCommandController | GET 轻量 HTTP 尚为 待实现，不宣称设计合入即已上线 |

本表仅保留 `6f52fddc87a03c20916fc7b6ef1de87f6a7a8cf5` 的发现层历史快照。
对 Help 而言，`53eff85c7f41de23eb434e027782f5085a8b8e45` 已有 RuntimeCommandCatalogController、RuntimeCommandController
及三字段响应投影，不能继续用上表的“无 Controller”快照推导 Help 尚未实现。

pi 固定基线仍用 `5cd93f688aaab89dbb6dfa4aca535f21796ae185`：
`packages/coding-agent/src/core/slash-commands.ts` 的 BuiltinSlashCommand 为 name/description/可选
argumentHint，支持轻量提示的结构参考；它不定义 CampusClaw 的 HTTP、状态过滤或缓存 503。
此证据表不更新其他 Harness 基线，也不据公开文档推断服务端实现。

差异分类：字段减法、固定顺序和 Help 无参属于产品约束；共享 GET 完整性前置与 DTO→VO
投影属于架构变更；不返回内部路径、正文和凭据属于安全边界。
原因是让前端只解释当前调用形态，同时让执行的权威校验留在后端。

实施先后及验收：

1. 保留全局主图骨架与 Definition 身份；实现共享完整缓存解析和独立 Builtin 专属解析。
2. 增加只读轻量 Response VO 与投影，覆盖 idle/running、完整空 Skill、无完整缓存 503，
   禁止内部字段与建议值输出，保证固定 Builtin 顺序及 Skill 顺序。
3. 两跳 GET 的 Descriptor 必须逐项等值；公共协议未确认部分保持待评审标记。
4. POST 重新准入、Help 无参三个业务字段、Name 无历史、JSON 返回和 Events v2 不回退；
   交互层验证 Slash 未命中保留草稿、无普通消息 fallback。
5. 文档门禁同时检查两套 JSON、HTML 和负向变异，防止后续 Help/POST 改动重新带回旧 GET。

### 3.4 Skill 执行链（B13/B14 已确认）

共享 Registry 解析的 SkillCommandDefinition 组合 CommandAdmissionPolicy 与真实 SkillCommandHandler；
Handler 委派 SkillExecutionService，再经 SessionEventApplicationService 复用普通消息的接受、
凭据和运行生命周期。PreparedSkillInvocationDTO 固定正文、元数据和版本；同一请求的发现与
执行用同一 Definition 身份，绑定/权限/容量仍在所属事务或锁内重检。不能把 DTO 穿透 Controller。

CommandExecutionService 返回内部 Builtin/Skill 结果联合 DTO，由 CommandResponseAssembler
转为只读 JSON VO 或请求级事件流响应对象；Controller 只按已类型化结果选择 JSON/SSE，不按
命令名称新增中央 switch。共享事件 VO 与 EventStream 由 Events 模块维护，避免命令再造一套事件。
Skill 详情、源码基线 dfb90ca 与 pi 5cd93f 证据见[Skill 专题 §4](../02-技能命令/README.md#4-统一实施与集成要求)。

新增主图依赖对应实施切片：先补 Skill 定义与 Handler，再补快照/重检应用服务，接着复用消息
接受与投影，最后联合 HTTP 与恢复验收。保持 Help/Builtin Handler、窄业务服务与 Coordinator
独立，类图不得用一个大框遮盖其分层。不新增 Maven 依赖。

## 4. 执行顺序与恢复

Application 依次完成 Session 访问检查、arguments 归一、单次 Catalog 解析、名称精确查找、
参数与预览准入、锁内重新检查、Handler 和结果组装。合法但未注册名称为 COMMAND_NOT_FOUND；
Builtin 名称格式不覆盖 skill:*；公共入口不能据此拒绝 Skill 名称。

![权威状态](设计图/authoritative_command_state.svg)

[PlantUML 源码](设计图/diagram.puml#L74)

Help/Status/Skills 不写 Entry；Name 只保存当前名称与版本；Model/Thinking/Compact
复用现有领域 Entry。同值、查询和空历史压缩不写 Entry。
成功响应复用既有 Session/Models 资源及对应 ETag，不建立独立 Slash 回执。
Help/Compact/Skills 无对应独立 API，只保留最小业务结果；所有成功 result 删除 command、changed、sourceEventSeq。
精确映射、6f52fddc 源码证据与同源快照要求统一见 [Builtin §8](../01-内置命令/README.md#8-json-与错误)。
全局主图的响应投影边界不变，不增加七个命令 VO 或重排主图。
Compact 断线不取消，调用方通过 GET Session/Events 对账，不自动重放不确定的 POST。
Mate Header 不记录、不持久化、不进入 Prompt；Compact 仅在本次 Active Holder 中保留到本次执行结束。
独立控制接口退役后本期不接受排队续跑；停止与 Events 的绑定见[内置命令 §7](../01-内置命令/README.md#7-compact-生命周期)，
[FollowUp 未来专题](../../01-总体架构/01-CampusClaw多Agent运行时/chat-follow-up-future-design.md) 仅记录方向，不启用。

## 5. 实施与验收

精确 HTTP 契约见操作
[12](../../01-总体架构/01-CampusClaw多Agent运行时/接口契约/操作/12-list-session-commands.json)、
[13](../../01-总体架构/01-CampusClaw多Agent运行时/接口契约/操作/13-execute-session-command.json)。
实施顺序和命令矩阵见[内置命令](../01-内置命令/README.md)。

统一实施计划由用户负责，按依赖拆分提交：

| 实施项 | 完成条件 |
|---|---|
| 共享核心 | 两类命令复用来源过滤、不可变解析快照和分层边界；分别定义发现与执行职责 |
| Builtin | 按各命令证据跟踪实施；Help 元数据指南已实现，不代表其他 Builtin 自动验收 |
| Skill Command | 补齐执行契约、真实执行定义、快照与绑定重检、失败恢复及专项验收 |
| 共享 HTTP 集成 | 统一对齐两类命令的命名、清单、请求类型、结果与错误，完成发现到执行的集成验收后发布 |

Skill 的已确认执行语义按[Skill 实施要求](../02-技能命令/README.md#4-统一实施与集成要求)实施；
操作 12/13 当前保留的七个 Builtin 示例是已确认部分，不能代替两类命令的最终整体验收。

单次开发、提交和 PR 均不设新增代码行数上限，模块与公司镜像不设配套预算。
按职责、依赖和可独立验证的交付边界划分批次，完整实现与必要测试可以共同交付；不因行数强制拆分。
前一 PR 合并后再创建下一分支，不堆叠。

交付规则分析基线为 `pi-mono-java@09b32d8ea4a4b43b34be302d8b2745bdc417c9a2`：
`.github/workflows/ci.yml:17-24` 仍调用 `scripts/check-commit-additions.sh` 及其测试，
脚本的 `MAX_ADDED_LINES` / `check_pull_request` 汇总 PR 非文档新增行并限制为 2000。
取消额度属于产品约束调整；实现仓需删除相应 CI 步骤、脚本和专用测试，合入前 CI 仍可能执行旧规则。
该调整仅涉及交付规模，不改变本专题的命令架构、运行时语义或 Agent 架构对比结论。

测试覆盖来源过滤、稳定排序、重名启动失败、单次解析、无 DTO 泄漏、并发准入和无通用命令历史。
Help 额外覆盖无参描述符、三个业务字段、空数组、显示名回退、useCases 缓存往返与显式刷新旧缓存；
GET 只表达空参入口可用，不能据此绕过 POST 的 Agent 完整快照检查。

图的提交验收额外运行 `python3 validate-global-class-view.py`，检查全局主图入口和不可折叠的职责关系；
该脚本不证明视觉可读性，仍须查看实际 SVG，核对原尺寸与文档缩放下的文字、连线和标签。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
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
