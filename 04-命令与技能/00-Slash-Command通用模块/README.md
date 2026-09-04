# CampusClaw Slash Command 通用模块设计

[返回命令与技能导航](../README.md)

| 属性 | 值 |
|---|---|
| 文档版本 | 1.3.0 |
| 更新日期 | 2026-09-04 |
| 设计仓基线 | `0eaa70ff365bf4d4e328b3473809341ca4cfc58d` |
| CampusClaw 分析基线 | `d84dd3d6a306b7587c70b29e0100e741dacef989` |
| 初始 Command 发现候选 | `0bb794f222273e12fc24fe98d6ab4e9013ac8599`（PR #210） |
| 最新前置 PR #210 | `9d0d76f4a571b559dc77ae52736caebbcc8fad88`，未合并；828 模块行 / 1656 总代码行 |
| Command GET 候选 | `7759481a1722422395d46564129827c6ee6df204`（未发布） |
| 状态 | 用户确认的目标设计；公开实现为 target-only |

## 1. 当前目标

Runtime HTTP v1 只公开 `help`、`status`、`name`、`model`、`thinking`、
`compact`、`skills` 七个 Builtin。GET 命令清单按名称稳定字典序返回，
POST Command 使用普通 ResultBean JSON；Skill Command 执行另立后续设计。

`/` 只在交互层使用。POST 只接收 `name + arguments`，不接收附件或整段 Slash 文本。
普通 POST Events 不解析 Slash，既有请求级 SSE 行为不变。
本期不生成公开 commandId，也不持久化通用命令生命周期或 Name 边车历史。

![目标分层](设计图/target_slash_command_boundaries.svg)

[PlantUML 源码](设计图/diagram.puml#L1)

## 2. 源码证据与差距

下表路径均相对 pi-mono-java 仓库；只把候选 PR 中已存在的符号标成候选行为，不当作 main 已实现。

| 基线与路径 | 观察行为 | 目标差距 |
|---|---|---|
| d84dd3d6：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/command/SlashCommandRegistry.java` | 旧原型用可变 Map 并解析整段 Slash；未接入生产 HTTP | 最终 HTTP PR 删除旧原型 |
| 0bb794f2：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/CompositeCommandRegistry.java`，`resolve` | 合并所有 Source 为一次请求的 Catalog | 调用 Source 前按 CommandKind 过滤 |
| 0bb794f2：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/CommandDefinition.java` | 只有发现元数据，没有 Handler | Skill 仅展示；Builtin 携带准入与 Handler |
| 0bb794f2：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/ResolvedCommandCatalog.java` | 固定请求内 list/find 视图 | Help、准入、执行共用同一快照 |
| 7759481a：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeCommandController.java` | 未发布 GET 候选依赖 Catalog Service | GET/POST 在最终 PR 同时发布 |
| d84dd3d6：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionConfigurationService.java` | Model/Thinking 与 HTTP If-Match 绑定 | 提取可选 expectedVersion 的窄服务 |
| d84dd3d6：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java`；`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/runtime/RuntimeSessionHolder.java` | 活动执行、控制队列与清理已存在 | Compact 复用生命周期，单独完成 JSON Future |

最新前置候选 `9d0d76f4`（非 main）已将发现数据改为
`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/ResolvedCommandDTO.java`
与同包 `SkillCommandSnapshotDTO.java`，并由 InputDTO 复制 suggestions、Catalog 复制外层列表。
`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/skill/SkillNamePatterns.java`
已集中兼容/严格正则字符串、编译模式和长度上限；SkillNameValidator 与旧展示 DTO 已删除。
来源过滤、可执行 Builtin 定义和七个 Contributor 仍属于后续核心 PR，不因前置发现层存在而视为已实现。

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
共享快照只固定 Definition 身份和元数据；状态变更必须在数据库行锁或 Runtime 操作锁内重新准入。

![请求级 Catalog](设计图/target_command_resolution_classes.svg)

[PlantUML 源码](设计图/diagram.puml#L43)

- `resolve(context, BUILTIN)` 在调用 Source 前过滤类型，Builtin 查询不调用 SkillCommandSource。
- 七个 Contributor 各自贡献元数据、准入策略和 Handler；启动期重名直接失败。
- Skill Definition 只供展示，不安装抛错的伪 Handler。
- 新增命令不修改中央名称 switch；结果类型分派只能出现在 DTO→VO 组装器。
- 内部结果使用 DTO，响应使用只读 `@Getter` 与 final 字段的独立 VO。
- 参数缺省只在 Service 归一；标准输入约束放在请求 VO/API 参数并实际触发 Jakarta 校验。

## 4. 执行顺序与恢复

Application 依次完成 Session 访问检查、arguments 归一、单次 Catalog 解析、名称精确查找、
参数与预览准入、锁内重新检查、Handler 和结果组装。合法但未注册名称为 COMMAND_NOT_FOUND；
skill:* 不符合本期名称格式，返回 INVALID_COMMAND_REQUEST。

![权威状态](设计图/authoritative_command_state.svg)

[PlantUML 源码](设计图/diagram.puml#L71)

Help/Status/Skills 不写 Entry；Name 只保存当前名称与版本；Model/Thinking/Compact
复用现有领域 Entry。同值、查询和空历史压缩不写 Entry。
Compact 断线不取消，调用方通过 GET Session/Events 对账，不自动重放不确定的 POST。
Mate Header 不记录、不持久化、不进入 Prompt；Compact 仅在本次 Active Holder 中保留到排队续跑结束。

## 5. 实施与验收

精确 HTTP 契约见操作
[12](../../01-总体架构/01-CampusClaw多Agent运行时/接口契约/操作/12-list-session-commands.json)、
[13](../../01-总体架构/01-CampusClaw多Agent运行时/接口契约/操作/13-execute-session-command.json)。
实施顺序和命令矩阵见[内置命令](../01-内置命令/README.md)。

每个实现 PR 非文档新增代码最多 2000 行，模块侧最多 850 行；
同步 campusclaw 后总量超过 1800 行不发布。前一 PR 合并后再创建下一分支，不堆叠。
测试覆盖来源过滤、稳定排序、重名启动失败、单次解析、无 DTO 泄漏、并发准入和无通用命令历史。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.3.0 | 2026-09-04 | Builtin-only 普通 JSON；Skill 执行延期；单次 Catalog、窄服务、无通用命令历史和串行 PR 预算。 |
| 1.2.0 | 2026-09-03 | 重做 Slash Command 目标类图：分别表达分层与对象生命周期、注册解析与扩展关系；明确 Controller/Application/Command Core/Runtime Adapter 边界、请求级清单快照、凭据生命周期、DTO/VO 隔离和无中央分派约束 |
| 1.1.0 | 2026-09-03 | 复核 `3004419a` 发现层与 `fb49e86d` GET 清单；引入单次请求 `ResolvedCommandCatalog` 快照和只读执行上下文，移除 Source 级别 find 职责，并明确 Definition 不直接封装可变 Descriptor DTO |
| 1.0.4 | 2026-09-01 | 命令相关表述只使用“命令清单”；Skill 文件位置统一表述为“文件夹”，避免再次引入文件系统含义 |
| 1.0.3 | 2026-09-01 | Skill 名称对齐 Agent Skills 的完整规则；参数上限明确为复用普通消息的 UTF-16 输入限制，不再表述为 Harness 通用规范 |
| 1.0.2 | 2026-08-31 | 全文改为短句、动作式表格和先结论后细节的结构；不改变已确认行为 |
| 1.0.1 | 2026-08-31 | 澄清 Command Catalog 是按 Session 上下文解析的逻辑注册表；面向用户和 HTTP 文案统一使用“命令清单”，避免被理解为文件路径 |
| 1.0.0 | 2026-08-31 | 建立 Builtin/Skill 两类命令、可组合注册、结构化 HTTP、双层可用性、命令事件和 sidecar 持久化的唯一公共定义 |
