# Slash Command 通用模块源码证据

[返回主设计](README.md)

本文件只记录源码与外部基线的核验事实，设计结论以 [主设计](README.md) 为准。各节按核验日期和提交独立保留，旧提交的差距不延伸为当前实现缺陷。Java 路径均相对 `pi-mono-java` 仓库。

<a id="agent-catalog-evidence"></a>

## 1. 清单归属核验（2026-10-16）

### 1.1 CampusClaw 实现

2026-10-16 fetch `pi-mono-java` 默认分支 `main`，核验 `fd4310026be808a16f471c550dff4b024ce91e24`。下表路径相对 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/`；前端路径相对仓库根目录。

| 源码 / 符号 | 已观察行为 | 与目标设计的差距 |
|---|---|---|
| `web/RuntimeCommandCatalogController.java:42-52` · list | 路由为 `GET /sessions/{sessionId}/commands`，校验 sessionId 后调用 `CommandCatalogService.list(sessionId)`，响应 `no-store` | 改为 `GET /agents/{agentId}/commands`，sessionId 改为可选查询参数；参数校验改用 Agent 标识规则，带 sessionId 时另校验会话标识与归属，待实现 |
| `service/command/CommandCatalogService.java:44-63` · list / completeSnapshot | 先查 Session（不存在为 SESSION_NOT_FOUND），再用 Session 的 agentId 调 `AgentRuntimeManager.prepareCached`；缓存缺失或异常为 AGENT_NOT_AVAILABLE（经异常处理改为 503） | 不再读取 Session；改用 `prepare(agentId)`，不存在为 AGENT_NOT_FOUND、不可用为 AGENT_NOT_AVAILABLE，待实现 |
| `service/command/CompositeCommandRegistry.java:63-71` · resolveComplete | 要求 Session 的 agentId 与快照一致，按全部来源解析，并把 `CommandSessionSnapshotDTO.from(session)` 传给每个 Definition | 清单解析只接收 Agent 快照；会话状态只在执行准入时使用，待实现 |
| `command/definition/CommandDefinition.java:16-17` · describe | `describe(CommandSessionSnapshotDTO session)`：描述依赖会话快照 | 拆为与会话无关的描述和会话级准入，待实现 |
| `service/command/SkillCommandSource.java:90-104` · descriptor | 按会话是否 idle 计算 `available`、`input.available` 和 SESSION_BUSY 原因 | 清单不再携带会话可用性；运行中能否执行由 POST 准入和前端状态规则决定，待实现 |
| `service/command/CommandDiscoveryResponseAssembler.java:27-36,53-62` · assemble / input | 过滤 `available=false` 的命令；输出旧 `input{hint, acceptsFiles}` | 不再按会话过滤；字段改为 type/hints（原有待实现增量） |
| `service/command/contributor/` | 七个 Contributor：Compact、Help、Model、Name、Skills、Status、Thinking | mode Contributor 仍待实现（原有增量） |
| `frontend/src/composables/useRuntimeApi.ts:74,432-451` · path / listCommands | 清单请求复用会话路径 `/sessions/{sessionId}/commands`；同一 Agent 的不同会话各自读取 | 改用当前会话的 agentId 读取，同一 Agent 复用页面内清单，待实现 |
| `frontend/src/composables/useRuntimeApi.ts:157-161` · createSession | 创建会话已使用 `/agents/{agentId}/sessions` | 说明前端已持有 agentId，无需新增来源 |
| `runtime/AgentRuntimeManager.java:95-112` · prepare / prepareCached | prepare 在 Agent 锁内优先使用完整缓存，缺失时重建；prepareCached 只读缓存、不访问 Mate | 清单改用 prepare，与创建会话一致 |
| `runtimeapi/agent/FileAgentDirectoryResolver.java:31-55` · resolve | prepare 的 IllegalArgumentException 映射 AGENT_NOT_FOUND，AgentRuntimeException 映射 AGENT_NOT_AVAILABLE | 清单沿用同一映射 |

本次只读源码，未运行 Java 或前端测试。

### 1.2 外部基线

2026-10-16 隔离 fetch 各默认分支。这是当日源码快照，不等于稳定发布。

| 基线与相对路径 / 符号 | 已观察实现 | CampusClaw 取舍 |
|---|---|---|
| OpenCode `dev@e25b7abf8955a4fa1b02b935964cb47db4c3a02a` · `packages/protocol/src/groups/command.ts` · `command.list` | `GET /api/command`，按可选 `location.directory` 定位实例，返回 `Command.Info` 数组；不带 sessionID；该路由组标注为 Experimental | 借鉴“清单归属配置来源而不是会话”；CampusClaw 的配置来源是 Agent |
| Codex `main@6b991972c5b539198dcea9bac4fc14e57559c3af` · `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs` · `SkillsListParams` | `skills/list` 按 `cwds` 列出技能，空时取当前会话工作目录，可 `force_reload` | 同样以配置位置为范围；CampusClaw 不提供强制刷新入口 |
| pi `main@4954d760504c11df9b2cbdc040346107b6a8153d` · `packages/coding-agent/src/modes/rpc/rpc-mode.ts:680-711` · `get_commands` | 在 RPC 会话进程内汇总扩展命令、Prompt 模板和 Skill；一个 RPC 进程对应一个会话 | pi 的会话即进程，不区分 Agent 级与会话级清单；不照搬 |

<a id="2-源码证据与差距"></a>

## 2. 早期核心实现快照

下表按所列提交保留历史快照，不代表当前实现。

| 基线与路径 | 观察行为 | 当时的目标差距 |
|---|---|---|
| d84dd3d6：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/command/SlashCommandRegistry.java` | 旧原型用可变 Map 并解析整段 Slash；未接入生产 HTTP | 最终 HTTP PR 删除旧原型 |
| 0bb794f2：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/CompositeCommandRegistry.java`，`resolve` | 合并所有 Source 为一次请求的 Catalog | 调用 Source 前按 CommandKind 过滤 |
| 0bb794f2：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/CommandDefinition.java` | 只有发现元数据，没有 Handler | Skill 仅展示；Builtin 携带准入与 Handler |
| 0bb794f2：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/ResolvedCommandCatalog.java` | 固定请求内 list/find 视图 | 清单、准入、执行共用 Definition 身份；Help 内容不来自清单 |
| 7759481a：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeCommandController.java` | 未发布 GET 候选依赖 Catalog Service | GET/POST 在最终 PR 同时发布 |
| d84dd3d6：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionConfigurationService.java` | Model/Thinking 与 HTTP If-Match 绑定 | 提取锁内读取最新配置的窄服务 |
| d84dd3d6：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java`；`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/runtime/RuntimeSessionHolder.java` | 活动执行、控制队列与清理已存在 | Compact 复用生命周期，单独完成 JSON Future |

已合并的前置实现 `9d0d76f4`（main 合并点 `a8192e04`）将发现数据改为同包 `ResolvedCommandDTO.java` 与 `SkillCommandSnapshotDTO.java`，并由 InputDTO 复制 suggestions、Catalog 复制外层列表；`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/skill/SkillNamePatterns.java` 当时集中兼容/严格两套正则。Help 在 `d1cdb708e3e124cae009b10b985f5832b6dbde01` 已实现同一链路，场景字段当时误名为 `userCases`，`53eff85c7f41de23eb434e027782f5085a8b8e45` 统一为 `useCases`，见 [Help 源码证据](01-内置命令/Help-Agent使用指南/README.md#5-源码证据与设计理由)。

### 2.1 执行与持久化外部基线（历史）

| 基线 | 源码观察 | Java 决策与理由 |
|---|---|---|
| pi `4af9d21d3b4d664e4a29fcabfec85171077248e3` | `packages/coding-agent/src/modes/interactive/interactive-mode.ts` 本地分派；`packages/coding-agent/src/core/agent-session.ts` 的 `_tryExecuteExtensionCommand` 直接调用 Handler；`packages/coding-agent/src/core/session-manager.ts` 保存领域 Entry | 保留 Session 领域语义，不照搬 CLI 入口（产品约束） |
| OpenCode `849c2598abc7d2b40261e74b5826bc74ffc78308` | `packages/opencode/src/server/routes/session.ts` 的 command POST 返回 JSON，事件流独立 | 普通 JSON 与命令调用结果相匹配，不需要通用生命周期存储（架构变更） |
| Codex `be33f80bc65159c094ecd06bf155afa3061ce23d` | `codex-rs/app-server-protocol/src/protocol/common.rs` 定义结构化 Thread/Skill 操作 | 学习结构化边界，不复制 JSON-RPC 通知（架构选择） |
| DeepSeek Harness `141eb6fef83422698aef7a981029e843e8161534` | `packages/interaction/commands/src/index.ts` 的 CommandExecution 与命令日志 | 当前产品不需要通用命令日志（产品约束）；alpha 对照 |

设计仓固定 pi 基线 `5cd93f688aaab89dbb6dfa4aca535f21796ae185` 同时保留；Codex `d58d0e5841e0de08e251673db2d5af8cf3a1ad51` 和 DeepSeek `0a53fb55bea101816fa226bb964ae2bed71c343b` 是历史参考点。

<a id="command-descriptor-baseline"></a>

## 3. 命令描述符专项基线（2026-09-22）

已确认默认分支并隔离 fetch：pi `main@d201760ffee16564aa8d9a759e0c85b70db33674`，OpenCode `dev@fe3f3a41f79ad292cc3c7c629567385a20ec5130`。仅覆盖命令发现、请求形态和展示边界。

| 基线与相对路径 / 符号 | 已观察实现 | CampusClaw 取舍 |
|---|---|---|
| pi · `packages/coding-agent/src/modes/rpc/rpc-types.ts` · RpcSlashCommand / RpcCommand；`packages/coding-agent/src/modes/rpc/rpc-mode.ts` · get_commands | 描述符为 name、description、source、sourceInfo，无 input；Skill 通过 prompt.message 与可选 images 调用；模型/思考使用独立类型化请求 | 借鉴发现与执行分工；不公开来源路径，不复制 JSONL RPC。type 是本产品分类字段 |
| pi · `packages/coding-agent/src/core/agent-session.ts` · prompt / _expandSkillCommand | Skill 正文展开后与消息参数、图片进入处理链；未知 Skill 可以保留原文 | CampusClaw 显式命令精确匹配失败就拒绝，不回退普通消息（安全加固） |
| OpenCode · `packages/opencode/src/command/index.ts` · Info / hints | 实例命令描述含 source、template、hints；hints 提取参数占位符，Skill 可为 [] | 保留轻量提示概念，不公开模板；空 hints 不代表不允许参数 |
| OpenCode · `packages/opencode/src/session/prompt.ts` · CommandInput / command；`packages/opencode/src/server/routes/instance/httpapi/groups/session.ts` · CommandPayload | HTTP 命令请求为 command、arguments 与可选 parts/agent/model/variant/messageID；sessionID 来自路径 | CampusClaw 使用 name/arguments/fileIds 与既有 JSON/SSE |

OpenCode `/api/command` v2 当时在源码中标为 experimental。四字段投影、Skill 附件规则与状态矩阵是 CampusClaw 产品约束，不是统一行业协议。

<a id="mode-command-evidence"></a>

## 4. 模式命令增量证据（2026-09-22）

| 基线与核对范围 | 已观察行为 | CampusClaw 决策与代价 |
|---|---|---|
| pi 默认 main `d192bd6dcae78fb87cf5c1c5e2af2790a0296278`；`packages/coding-agent/src/core/slash-commands.ts#BUILTIN_SLASH_COMMANDS` | Builtin 列表含 model/thinking 与 argumentHint，未含 mode/plan/build | 新增产品自己的 mode；不宣称为 pi 原生行为 |
| OpenCode 默认 dev `fe3f3a41f79ad292cc3c7c629567385a20ec5130`；`packages/opencode/src/agent/agent.ts#Agent.state` | build/plan 是两个 primary Agent，并有不同权限 | 保留同一绑定 Agent，以 Session.mode 切换模式；不复制双 Agent 权限结构 |
| Java `53eff85c7f41de23eb434e027782f5085a8b8e45`；路径见 [Builtin §6.1](01-内置命令/README.md#mode-command) | Session 更新已有 mode 及 requested 事件，命令 Contributor 和前端命令映射尚无 mode | 新命令及共享规则抽取待实现 |

<a id="33-发现层证据与验收"></a>

## 5. 发现层快照（6f52fddc）

`pi-mono-java@6f52fddc87a03c20916fc7b6ef1de87f6a7a8cf5` 的发现层历史快照：

| 源码 / 符号 | 当时观察 | 当时目标差距 |
|---|---|---|
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/service/command/CompositeCommandRegistry.java` · resolve | 全来源解析与 CommandKind 过滤均存在，TreeMap 按名称排序 | 共享 GET 用全来源；VO 投影改为固定 Builtin 顺序 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/catalog/ResolvedCommandCatalog.java` · list/findDefinition | 请求快照保存发现 DTO 与 Definition 身份 | 保留请求级身份，不把 GET 快照跨请求当作授权 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/dto/command/ResolvedCommandDTO.java` · InputDTO | 内部仍有 mode、双层 available、placeholder、suggestions | 允许内部保留，禁止泄漏进轻量响应 VO |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/service/command/SkillCommandSource.java` · list/resolved | prepareCached 缺失返回空清单；running 生成不可用标记 | 区分缓存缺失与完整空绑定 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/service/command/BuiltinCommandSource.java` · definitions/list | Contributor 来源已装配，内部按名称排序 | 在 Application 投影固定显示顺序 |

pi 固定基线 `5cd93f688aaab89dbb6dfa4aca535f21796ae185` 的 `packages/coding-agent/src/core/slash-commands.ts` 中 BuiltinSlashCommand 为 name/description/可选 argumentHint，是轻量提示的结构参考。

<a id="331-清单字段与语言专项核对"></a>

## 6. 清单字段与描述语言（53eff85c）

核对 `pi-mono-java@53eff85c7f41de23eb434e027782f5085a8b8e45`，路径相对 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/`。

| 源码 / 符号 | 已观察行为 | 结论与边界 |
|---|---|---|
| `vo/CommandListResponseVO.java` · DescriptorResponseVO / InputResponseVO | 公开 input 只有 hint、acceptsFiles；null input 与 false acceptsFiles 通过 Jackson 省略 | 仍为 kind/input 旧形态；type/hints 投影待实现 |
| `web/RuntimeCommandCatalogController.java` · list；`service/command/CommandCatalogService.java` · list | Controller 设置 Content-Language；清单服务未接收 Locale | 响应 Header 不证明命令描述已本地化 |
| `service/command/CommandDiscoveryResponseAssembler.java` · descriptor / input | 原样投影 command.description()；hint 使用固定常量 | 不会按 zh-CN 切换 Builtin 描述 |
| `service/command/contributor/HelpCommandContributor.java`、`NameCommandContributor.java` · definition | 描述固定为英文 | 与契约中文示例不一致；Builtin 描述本地化待实现 |
| `service/command/SkillCommandSource.java` · resolved | 读取 skill.description() | 作者元数据不因中文示例自动具有翻译能力 |

前端 `frontend/src/runtime/commands.ts` 的 decodeCatalog/freezeCommandArguments 在该提交仍据 kind 分派、据 input 判断参数能力。

<a id="command-patterns-evidence"></a>

## 8. 设计模式与转换命名（2026-10-19）

CampusClaw 核对实现 PR #364 的 `pi-mono-java@22310e66e93b2cd3f7bcacf91958231b8bbe7816`（待合并），路径相对 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/`。

| 源码 / 符号 | 已观察行为 |
|---|---|
| `command/builtin/BuiltinCommandContributor.java` · definition；`service/command/BuiltinCommandSource.java` · 构造器 | 各 Builtin 以 Spring 组件贡献 Definition，Source 注入全部 Contributor 并查重 |
| `service/command/CompositeCommandRegistry.java` · resolve | 遍历 `List<CommandDefinitionSource>`，按类别过滤后平铺合并，重名抛出 IllegalStateException；没有嵌套来源 |
| `command/builtin/BuiltinCommandDefinition.java` · 构造器 | 组合 `CommandAdmissionPolicy`、`CommandHandler` 与可选 `CommandValuesProvider`，校验 options 命令与取值逻辑一一对应 |
| `service/command/CommandExecutionService.java` · executeBuiltin；`service/command/CommandValuesService.java` · listValues | 按名称取 Definition 后只调用接口，不按命令名分支 |
| `service/command/CommandListResponseAssembler.java` · assemble / toBuiltinDescriptor | 按 `BUILTIN_ORDER` 排序，用 `COMMAND_BUILTIN_<NAME>_DESCRIPTION` 读取本地化描述 |

实现仓 `AGENTS.md`（同一提交）“文件、注释与命名”一节把 `Assembler` 列为约定类名后缀，转换方法用 `toXxx`，并规定 Mapper 使用 DTO（MyBatis 持久化）。

外部基线于 2026-10-19 确认默认分支并隔离浅克隆：

| 基线 | 提交 | 源码 / 符号 | 已观察行为 |
|---|---|---|---|
| pi | `badlogic/pi-mono` main `1402973a9dbe8c627341e04c9744c54953e285ca` | `packages/coding-agent/src/modes/rpc/rpc-mode.ts:680-711` · `get_commands`；`rpc-types.ts:81` · `RpcSlashCommand` | 在 RPC 分支内依次遍历扩展命令、提示模板和 Skill，直接拼出响应对象，没有单独的转换类 |
| OpenCode | `anomalyco/opencode` dev `fede5ddda5e389bb072cb68fd380ec31f41f9929` | `packages/server/src/handlers/command.ts:7` · `command.list` | 处理器直接返回 `Command.Service.list()` 的结果，没有独立投影层 |
| Codex | `openai/codex` main `89461ea6833832b0551ce24ee32205824d5c108d` | `codex-rs/app-server-protocol/src/protocol/mappers.rs` · `impl From<v1::ExecOneOffCommandParams> for v2::CommandExecParams`；`event_mapping.rs:30` · `item_event_to_server_notification`；`item_builders.rs:70-117` · `build_*_item`；`codex-rs/tui/src/slash_command.rs:93` · `SlashCommand::description` | 内外模型转换用 `From` 实现、`xxx_to_yyy` 函数和 `build_xxx` 函数，按模块命名为 mappers / mapping / builders |

这些是默认分支快照，不代表稳定发布；本节只用于命名与结构对照，不改变 M05 的架构比较结论。

## 7. 交付规则

`pi-mono-java@09b32d8ea4a4b43b34be302d8b2745bdc417c9a2` 的 `.github/workflows/ci.yml:17-24` 调用 `scripts/check-commit-additions.sh`，`MAX_ADDED_LINES` / `check_pull_request` 限制 PR 非文档新增行 2000；取消额度后实现仓需删除相应 CI 步骤、脚本和专用测试。
