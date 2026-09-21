# 工具系统源码证据

[返回工具系统主设计](README.md)

版本：1.6.3；整理日期：2026-09-21。以下结论只适用于各行记录的源码提交，保留原核验范围；设计仓整理基线为 `12244d49576d17239e21c6e75e542fd61c69b826`。旧提交差距不代表最新实现状态。活动工具的历史主线状态见 §4，三项退役工具的源码删除边界见 §5，工具展示名的来源与实现范围见 §6；注册与发现的专项核验见 §8，文档组织与图形选择见 §10。

| 基线 | 提交 |
|---|---|
| 设计仓分析基线 | `e641fefdc9b58adb0054d6e548d313d01a69b94d` |
| CampusClaw PR 167 基线 | `f60cc3e78bb8b700527ac082c7c8e10524ede095` |
| CampusClaw merge base | `d649866a6cae967ace18ceaeb9597edd47e5721e` |
| CampusClaw 压缩修订前基线 | `a7f78fed345a289833970cd7b78399f0e8e51d32` |
| CampusClaw PR 167 审查头 | `bf28e72f94f29acd316eb872a250893ed54e3632` |
| CampusClaw PR 167 对齐实现 | `bd26e7f81bac8f68be0c3523efe23b51f96c52e4` |
| CampusMate 地址配置复核基线 | `56be8eee59415a5f86658d6635a7b7e8891263d3` (`origin/main`) |
| CampusClaw 凭据透传核对基线 | `320d790726a70aada6100052952d5494d2a378ac` |
| 本次设计仓修订基线 | `79f9818c1b99788eeb8b7ff2dfb8f212f0217581` |
| pi-mono 对照基线 | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` |
| OpenCode 对照基线 | `849c2598abc7d2b40261e74b5826bc74ffc78308` |

## 1. CampusClaw（pi-mono-java）观察证据

以下事实来自本页记录的 CampusClaw commit，不代表目标状态：

| 观察事实 | 源码路径与符号 |
|---|---|
| `AgentTool` 尚无逐工具执行模式；Pipeline 由调用方为整批传入一个 mode | `modules/agent-core/src/main/java/com/campusclaw/agent/tool/AgentTool.java`，`AgentTool`；`ToolExecutionPipeline.java`，`executeAll` |
| 大型 CLI `AgentSession` 聚合 ToolCatalog、Skill 激活、reload 和 delegation after-hook | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSession.java`，`initialize`、`configureRuntimeTools`、`handleAfterToolCall` |
| 工具由 Spring、Extension 和会话本地工厂进入目录 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/catalog/DefaultToolCatalog.java`、`SpringAgentToolSource.java`、`ExtensionToolSource.java` |
| HTTP Runtime 使用独立 Agent 目录解析和 Session engine 组装 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/agent/FileAgentDirectoryResolver.java`、`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/runtime/RuntimeSessionEngineRegistry.java` |
| Manager 缓存优先但仍原地写旧文件名及 `references/tools.json` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/AgentRuntimeManager.java`，`prepare`、`materialize` |
| 当前本地模型工具包含小写 `read/glob/grep/ls`、写工具、`EditDiff`、`loop` 和控制工具 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/**`、`loop/LoopTool.java` |
| 当前 Mate 工具以 `listMateTool/callMateTool` 暴露，List 刷新会话 name-to-ID 缓存，Call 强制先 List | `tool/mate/ListMateTool.java`、`CallMateTool.java`、`MateToolSessionCache.java` |
| 当前缓存每次刷新先清空平面 Map，最近一次 Agent/Skill List 会覆盖此前来源 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/MateToolSessionCache.java`，`refresh` |
| 当前执行端点按 `toolId` 调用并要求完整的原三项 Mate 凭据 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/HttpMateToolClient.java`，`invokeTool/toHeaderInfo`，基线 `320d7907` 303-373 行 |
| 当前 Agent、Skill 与 Tool metadata 发现也透传原三项 Mate 凭据 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/HttpMateToolClient.java:134-185`，`queryToolIdsByAgentId/queryToolIdsBySkillId/queryToolMetaByIds`，基线 `320d7907` |
| Runtime 当前未捕获入站 `access-token`，既有 `RequestHeaderInfo.accessToken` 对应的是 `X-Access-Token` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java:61-69`、`RuntimeRequestContext.java:45-49`、`common/dto/RequestHeaderInfo.java:81-90`，基线 `320d7907` |
| 当前 Tool 客户端从 `mate.innerGWSerive` 读取独立地址，而它的 Agent、Skill、Tool 元数据和执行路径都位于 `/mate-service/...` | `modules/coding-agent-cli/src/main/resources/application.yml:129-140`、`config/MateToolAutoConfiguration.java:31-81`、`common/client/HttpMateToolClient.java:41-83,132-320` |
| Runtime 与 Tool 客户端分别配置 `campusmate.runtime.skill-info-query-path-template` 和 `mate.endpoints.skill-tools-query-path-prefix`，但两者规范化后都是 `GET /mate-service/v1/skill/query/{skillId}` | `runtime/MateServiceClient.java:43-113`、`common/client/HttpMateToolClient.java:145-166`、`common/dto/SkillInfoResult.java:12-20` |
| 当前部署脚本只把 Campus 内网服务地址导出为 `MATE_INNERGWSERIVE` | `mate-campusclaw/scripts/install_value.sh:27-38` |
| 当前 Child 同时存在 `spawn_agent` 与 `invoke_agent` 两条路径，后者通过 Session after-hook 执行 | `subagent/tool/SpawnAgentTool.java`、`tool/delegation/InvokeAgentTool.java`、`session/AgentSession.java` |
| 当前 Cron payload 接受 model、system prompt 和 allowed tools，并依赖本地存储与 OS/进程调度 | `modules/cron/src/main/java/com/campusclaw/cron/tool/CronTool.java`、`model/CronPayload.java`、`engine/CronEngine.java` |
| 当前 `ReadTool` 自行使用 cwd 做路径边界，`BashExecutor` 只设置子进程 cwd | `tool/read/ReadTool.java`、`util/PathUtils.java`、`tool/bash/BashExecutor.java` |
| PR 167 按 TUI/CLI 包树删除了同时承载入口无关压缩和 Slash Command 的源码 | PR 167 `f60cc3e` 相对 merge base 的 `modules/coding-agent-cli/.../session`、`command`、`modes` 删除差异 |
| 修订前公共压缩已恢复“至少保留末条消息”，但溢出、Usage、split-turn、重复摘要和摘要请求细节仍未完整对齐 pi | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/ManagedAgentSession.java`、`session/compaction/SessionCompactor.java`，基线 `a7f78fed` |
| 审查头在内存中排除了可重试 `LENGTH`，但压缩 Entry 只保存首条保留边界，重载会重新注入被丢弃响应；公共 Agent 也未显式传递模型输出上限 | `RuntimeEntryCodec.effectiveContextEntries`、`RuntimeEventProjector.projectCompactionCompleted`、`Agent.buildStreamOptions`，基线 `bf28e72f` |
| 对齐实现持久化内部重试候选 Entry ID、重载时精确排除，并在无调用方覆盖时把 `model.maxTokens` 传入实际 Agent 请求 | 同上符号及 `RuntimeEventProjectorTest.reloadExcludesLengthResponseDiscardedBeforeCompactionRetry`，基线 `bd26e7f8` |

## 2. pi 与 OpenCode 对照

pi 内置的 `read`、`grep`、`find` 和 `ls` 是本地只读工具语义的对照。pi 的 Subagent
是 Extension 示例，支持独立上下文、进度和取消，但其用户/项目 Agent、独立进程、
cwd/model/tool override、parallel/chain 参数不成为 CampusClaw 契约。源码证据：
`packages/coding-agent/src/core/tools/read.ts`、`grep.ts`、`find.ts`、`ls.ts`，以及
[pi Subagent 示例](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/examples/extensions/subagent/index.ts)。

公共压缩以 pi `packages/coding-agent/src/core/agent-session.ts` 的
`_checkCompaction/_runAutoCompaction`、`packages/coding-agent/src/core/compaction/compaction.ts`
的 `estimateContextTokens/findCutPoint/prepareCompaction/compact/generateSummaryWithUsage`、
`packages/coding-agent/src/core/compaction/utils.ts` 的 `serializeConversation/extractFileOpsFromMessage`
及 `packages/ai/src/utils/overflow.ts` 的 `isContextOverflow/isRecoverableLength` 为强制证据。

OpenCode `TaskTool` 仅用于对照父子消息隔离、进度和取消，不继承它的权限、Session
持久化或工具注册模型。源码证据：
[OpenCode Task](https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/tool/task.ts)。


<a id="tool-display-evidence"></a>

## 3. 工具展示名称历史核验（2026-09-17）

本节独立记录本次读取，不升级前两节的旧观察。设计起点 `dab7226`；Java 本地 `main` 固定快照 `21c3f59be033e7bdd5506a2d9d48baa2581bc3c7`，不是最新远端声明。以下路径均相对 `pi-mono-java`，本次读取的文件与该提交一致。

| 路径 / 符号 | 已观察行为与目标差距 |
|---|---|
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/AgentTool.java` · label；`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/read/ReadTool.java` · label | 框架有 label；Read 返回 Read。普通工具 label 映射为外部 displayName 尚未实现。 |
| 同模块 `tool/mate/CallMateTool.java` · label / execute | 外层 label 为 Call Mate Tool；执行按 arguments.tool 解析内部 ID。目标改用具体业务元数据命名此调用，保留执行参数。 |
| 同模块 `common/dto/ToolInfo.java` · displayName；`common/client/HttpMateToolClient.java` · toMeta；`common/client/mate/MateToolMeta.java` · record | 网关 display_name 已能进入 ToolInfo，但 toMeta 和 MateToolMeta 丢失该字段。 |
| 同模块 `tool/mate/MateToolSessionCache.java` · CacheState / toNameIndex；`MateToolDiscovery.java` · resolveToolId | 当前索引仅 name-to-ID；目标让单次解析同时固定 ID 和可选展示名，执行与事件复用。 |
| 同模块 `runtimeapi/runtime/RuntimeToolPermissionPolicy.java` · decide；`runtimeapi/event/RuntimeEventProjector.java` · persistFinalizedToolCall / persistToolCall | ALLOW/DENY 调用可在 Assistant 完整响应时先持久化，不能等 execute 或 tool_execution_start 再补名称；ASK 路径也须在首次调用事件前固定。权限决定仍独立。 |
| 同模块 `runtimeapi/event/RuntimeCommittedEventFactory.java` · agentToolCall；`runtimeapi/dto/CommittedEventDTO.java` · payload；`runtimeapi/event/CommittedEventProjection.java` · projectToolCall；`runtimeapi/vo/SessionEventResponseVO.java` · AgentToolCallResponseVO | 现有 JSON payload 与共享投影可承载快照，当前 factory/VO/projection 均无 displayName；新增字段为 待实现。 |
| `frontend/src/runtime/protocol.ts` · fields / only；`frontend/src/types/runtime.ts` · RuntimeEvent | 工具事件类型和字段白名单未含 displayName，需与服务端新增字段同步更新。 |

pi 上游为 `https://github.com/badlogic/pi-mono.git`。2026-09-17 通过 `ls-remote --symref ... HEAD` 确认默认分支 `main`，在隔离 bare 仓库 fetch 后读取 `5a3a03a7f5db43692915d6ae45e6d96497ea248d`；这是当次默认分支源码快照，不声明为稳定发布。前次名称讨论使用 `42cd371ba49ac2cd398de6a37bb06542792cf613`，专题历史总基线 `5cd93f688aaab89dbb6dfa4aca535f21796ae185` 继续保留。仅复核以下路径，名称结论未变，未升级其他工具或压缩结论：

- `packages/agent/src/types.ts` · AgentTool.label（405～407 行）、AgentEvent（460～462 行）：定义有供 UI 使用的 label，但 start/update/end 事件没有 label/displayName。
- `packages/coding-agent/src/modes/interactive/interactive-mode.ts` · getRegisteredToolDefinition（2025 行）：按 toolName 取得定义与 renderer。
- `packages/coding-agent/src/modes/interactive/components/tool-execution.ts` · createCallFallback（152 行）：通用回退显示技术 toolName，不能表述为 pi 自动把 label 放进事件或统一渲染 label。

Claude Managed Agents 的[工具事件模型](https://platform.claude.com/docs/en/api/beta/sessions/events/list)与[事件流](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)于 2026-09-17 重新核对，仍为 Beta。公开 `agent.custom_tool_use` 提供 name/input，没有通用 displayName；文档不能证明 Console 的标题实现，不推断私有服务端或 UI。

本节保留当日字段缺口与外部基线证据，不能用于推断后续分支仍无实现。当前名称来源、执行边界和分支验收由 §6 维护；历史上提出的调用级执行 ID 绑定不属于现行展示设计。

## 4. 活动工具与主线实现状态（2026-09-18）

通过 `git ls-remote --symref origin HEAD` 确认 pi-mono-java 默认分支为 main，fetch 后显式读取 `8c5fda1dde51675859bc9c07e145dbe253656dea`。本次只核验三个交互工具、装配、事件和模式资源，不将前文其他旧基线升级为当前结论。相对旧工具接入点 `699f929f6826b595ed1d0162f6def66e2f84760b` 和前次本地 `21c3f59be033e7bdd5506a2d9d48baa2581bc3c7`，当前已包含结构化问答及两文件提示词装配。

下列 Java 路径均相对 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。

| 路径 / 符号 | 已核验实现 |
|---|---|
| `tool/builtin/BuiltInToolName.java`；`BuiltInToolProperties.java` · runtime/cron/childAgent；`DefaultBuiltInToolFactory.java` · create | 共 11 个活动名称；Runtime 默认依次包含八项基础工具、ExitPlanMode、TodoUpdate、AskUserQuestion；Cron/Child 缺省不含后三项。显式 profile 完全替换默认值。 |
| `tool/plan/ExitPlanModeTool.java` · execute；`runtimeapi/runtime/RuntimeActiveExecution.java` · await、claimAndResumePlanReview | 校验完整计划、等待审核并返回真实决定；领取批准后应用 build 提示词再完成等待。 |
| `tool/todo/TodoUpdateTool.java` · execute；`runtimeapi/event/RuntimeTodoEventMapper.java` · map；`RuntimeEventProjector.java` · persistToolResults、toolResultEvents | 校验完整列表，从最终成功结果生成任务快照；ToolResult 与 agent.todo_updated 同一次 appendEntry 提交。 |
| `tool/question/AskUserQuestionTool.java` · execute；`runtimeapi/event/RuntimeEventProjector.java` · beginQuestion；`runtimeapi/runtime/RuntimeActiveExecution.java` · await、claimAndResumeQuestionAnswer | 发布问题并等待答案，接续同一执行；三个交互类型共享 RuntimePendingInteraction。 |
| `runtimeapi/runtime/RuntimeSessionEngineRegistry.java` · createSession | 为审核和提问创建绑定当前执行的工具；工具通过窄端口等待，不直接依赖 HTTP 或数据库。 |
| 资源 `modules/coding-agent-cli/src/main/resources/application.yml` · campusclaw.tools | 实际默认配置包含上述 11 项，与枚举/工厂一致。 |

模式资源、逐题前端、历史证据与剩余边界集中见[计划源码证据 §12](../06-CampusClaw计划模式/source-evidence.md#12-主线实现状态核验2026-09-18)。本次是源码静态核验与设计校验，未重跑 Java、数据库、浏览器或真实模型测试；旧测试数量仍只归属于原提交。Mate 公共桥接待实现，不能据此将三个 Runtime 工具标为待实现。

## 5. Bash/Edit/Write 源码删除边界（2026-09-18）

设计修订基线为 `b5ed15ba5582d500a7095c93f16061cfe4863ab0`。当日重新确认 Java 与 pi 上游默认分支均为 main 并 fetch，显式读取下列提交，不改动原工作树。Java `8c5fda1dde51675859bc9c07e145dbe253656dea` 与 §4 相同；pi 工具组合证据从历史 `5cd93f688aaab89dbb6dfa4aca535f21796ae185` 专项更新到 `e4ce7b449f4d91589c8760d6fbfa6eaaf82b05fe`，仅升级本节工具组合结论。该 pi 快照的 package version 为 0.85.1，默认分支 HEAD 不等于稳定发布保证；其他基线证据不升级。

Java 路径前缀 R 为 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`，对应生成镜像位于 `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/`。

| 路径 / 关键符号 | 已观察事实 | 删除或保留依据 |
|---|---|---|
| R `tool/builtin/BuiltInToolName.java` · fromExternalName；`BuiltInToolProperties.java`；`DefaultBuiltInToolFactory.java` · create | 已有 11 项闭合活动工具，无 Bash/Edit/Write 枚举和工厂分支 | 删除源码不改变活动工具集合和三入口配置语义；非法名称继续拒绝 |
| R `tool/bash/BashTool.java` · execute；`BashExecutor.java`；`ShellResolver.java`；R `tool/ops/{BashOperations,LocalBashOperations}.java` | 旧 Bash 类及命令执行支撑仍存在，BashTool.name 返回小写 bash | 目标完全删除，不保留独立执行器或备用 shell 工具入口 |
| R `tool/edit/EditTool.java` · execute、performEdit、performMultiEdit；`{DiffUtils,FuzzyMatch,EditToolDetails}.java`；R `tool/write/WriteTool.java` · execute | 旧 edit/write 实现仍可完成替换/覆盖；使用 EditOperations/WriteOperations 和 FileMutationQueue | 删除这三项模型能力及只为它们服务的实现、结果类型和专属测试 |
| R `tool/ops/{EditOperations,LocalEditOperations,WriteOperations,LocalWriteOperations}.java`；R `util/FileMutationQueue.java` | 主源码引用集中于旧 Edit/Write；EditOperations 继承 ReadOperations/WriteOperations | 删除专属写接口和队列，但 ReadOperations 不随继承方删除 |
| R `util/PathUtils.java` · resolveToCwd、resolveReadPath | 主源码仅 EditTool/WriteTool 调用 resolveToCwd，resolveReadPath 无主源码消费者；其余引用为专属测试 | 随无消费者辅助代码删除，不影响活动工具使用的 WorkspacePathResolver |
| R `tool/read/{ReadTool,ReadToolDetails}.java`；R `tool/ls/LsTool.java` | 仍使用 TruncationUtils | 保留共享截断及测试，不按旧工具依赖树一并删除 |
| `modules/coding-agent-cli/pom.xml` | 旧工具依赖 JDK 和现有 Jackson、SLF4J 等共享组件，无三工具专属直接 Maven 声明 | 不新增依赖；删除前复核其他消费者，本节未声称完整传递依赖图已验证 |
| pi `packages/coding-agent/src/core/tools/index.ts` · createCodingTools、createReadOnlyTools、createTool、ToolName | coding 组合为 read/bash/edit/write；只读组合为 read/grep/find/ls；bash/edit/write 仍有工厂与类型导出 | CampusClaw 删除为产品约束及安全加固，不是上游已废弃或 pi 无此能力 |

当前目标：按主设计 §12.4 完全删除三项工具及专属代码，保留有效公共消费者、受管目录发布和部署脚本。删除前的主线仍有这些类，因此“已不装配”不等于“源码已删除”；实现状态与分支验证结果单独登记，不把未合入开发分支表述为主线完成。

实现状态：开发分支 `codex/remove-retired-write-tools` 的 `1b35422c61d471e11b9e1c126b57a82ef808ced2` 已实现源码删除，[Draft PR #315](https://github.com/superheromeZzh/pi-mono-java/pull/315) 待合入 main；活动 profile 排除三项工具原本已实现。该分支删除 21 个主源码类和 13 个专属测试，并同步公司镜像，不改变 11 项活动工具及三入口缺省集合。

验证：JDK 21 `./mvnw clean verify` 的 2009 项测试无失败、错误或跳过；Checkstyle 和 Spotless 通过。新增三入口 × 六种退役名称的 18 项拒绝组合，以及 21 类 classpath 不存在检查。父任务复核源码/镜像变更一致、最终 class/JAR 无上述退役类、修改测试的版权与方法长度检查通过；保留能力的回归包含在本次 Reactor 测试中，不等同真实模型或部署环境验证。公司镜像布局及 pre-push 同步检查通过；公司编译因无法解析 `com.huawei.hicampus:NativeParent:26.0.0-SNAPSHOT` 未验证，使用脚本允许的 `--no-verify` 完成生成同步。验收边界见主设计 §13.1.1。

<a id="tool-display-binding-evidence"></a>

## 6. 工具展示名来源与执行职责（2026-09-19）

本次设计修订起点为 `12244d49576d17239e21c6e75e542fd61c69b826`，交付前同步设计主线 `91b5bd2c9b3a83ee69264262eb96e6abd8a3cf21` 并保留其凭据职责规则。Java 默认分支 main 已 fetch，读取 `561d732ad591ba1f6aabbbc8590fc1d262c2c583`；PR #313 的原实现为 `9ea89f0ff5bc2c197117ec9dd80ba74c3e56e258`，同步 main 的 merge commit 为 `50db636c1e0b19d74db9e7bf5ada3b76681a8966`。以下路径均相对 `pi-mono-java`，Java 前缀 R 为 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。

| 范围与符号 | 已观察行为 | 当前设计依据 |
|---|---|---|
| main：R `runtime/MateServiceClient.java` · BoundTool | 已有 id/name/displayName/permission/version 等字段 | 业务展示名已有可信绑定来源，不需要为取名称新增远程发现 |
| main：R `runtime/AgentRuntimeManager.java` · writeRuntimeTree/toSettings/toRuntime/AgentSettings/SkillManifest | Agent bindingTools 写入并读回 settings.json；直接 Skill bindingTools 写入并读回 skill.json；mode 已存在于 AgentSettings | 文件职责为身份与运行配置分开；绑定元数据跟随同一次运行准备，文件名不决定所属 Agent/Skill |
| main：R `runtimeapi/runtime/RuntimeToolPermissionPolicy.java` · from/decide | 从当前 PreparedAgentRuntime 的 Agent/Skill 绑定构造权限判定 | 名称读取复用相同范围的可信元数据，但不修改权限决定 |
| main：R `tool/mate/CallMateTool.java` · execute；MateToolDiscovery · resolveToolId | 实际执行时按名称通过既有 Session 缓存和发现机制解析工具 ID | 展示功能保留该执行时点、原失败语义及发现恢复能力 |
| PR 原实现：R `runtimeapi/runtime/RuntimeToolCallSnapshotResolver.java` · resolveDisplayName；R `tool/mate/CallMateTool.java` · bindInvocation/resolve | 取名时解析并按 toolCallId 保留执行 ID，连解析异常也保存 | 这部分由纯展示名读取替代；产品中的工具只会启停，不为假设的同名改绑新增调用状态 |
| PR 原实现：R `runtimeapi/event/RuntimeCommittedEventFactory.java` · agentToolCall；CommittedEventProjection · projectToolCall；`frontend/src/runtime/protocol.ts` 与工具活动/确认卡 | displayName 的调用事件保存、实时/历史投影及前端展示已在分支实现 | 保留这些展示能力；公共 Mate bridge 不在该实现仓中，仍按所属模块记录待实现 |

现行目标是 Host 从本次 `PreparedAgentRuntime.metadata().bindingTools()` 与直接 `skills().bindingTools()` 读取 `BoundTool.displayName`，普通工具使用实际实例 `label()`。取名不访问网络、不改变发现缓存、不绑定执行目标或缓存解析失败；名称随调用事件保存，后续确认与历史读取沿用该值。工具启停、绑定、凭据与权限仍由实际执行链路作最终检查。业务名称长度 `varchar(256)` 与仅启停的生命周期是本次明确的产品约束，不从模拟的超长名称或动态改绑场景推导额外功能。

pi 上游默认分支在本次通过 `ls-remote --symref ... HEAD` 确认为 main，并在隔离仓库 fetch `36b60d2e8985899743c4cf5bd5f8929832a3f05d`，包版本为 0.85.1；这是默认分支源码快照，不声明为稳定发布验证。相对名称专项旧提交 `5a3a03a7f5db43692915d6ae45e6d96497ea248d`，重新读取 `packages/agent/src/types.ts` 的 `AgentTool.label`（408 行）与 `AgentEvent`（461–463 行）：label 存在，三类工具执行事件仍没有 label/displayName。仅升级此字段边界，不升级历史 TUI、Claude 或其他模块结论。CampusClaw 的外部展示字段仍是产品可读性约束和事件投影架构扩展。

实现状态：PR #313 的 `40f4dd964dbb091eda6a33a0173a8d40342a4a7a` 已按上述目标实现，尚未合入 main。R `runtimeapi/runtime/RuntimeToolCallSnapshotResolver.java` 的 from/indexMateBindings/resolveDisplayName 从当前运行绑定建立只读名称索引；`RuntimeSessionEngineRegistry#createHolder` 传入同一个 session.runtime。`CallMateTool`、`MateToolDiscovery`、`MateToolSessionCache`、`HttpMateToolClient` 和 `MateToolMeta` 与上述 main 基线内容一致；名称功能没有改写原执行与发现职责。

验证：JDK 21 下展示与执行相关测试 63 项、绑定元数据来源回归 87 项通过，零失败、错误或跳过；覆盖普通 label、Agent 与直接 Skill、空白和冲突降级、ASK/ALLOW/DENY 取名零发现调用、确认续跑只取名一次以及发现失败后再次调用可恢复。前端 4 个相关文件共 100 项测试、类型检查与构建通过；Spotless、Checkstyle、Java 方法长度与版权/布局检查、补充测试质量检查及人工核对通过。公司镜像已按脚本同步，因本机无法解析企业 NativeParent 未验证镜像编译。本次未运行真实 Mate、openGauss 或 Java HTTP 端到端联调；390×844 和 1440×1000 的本地模拟服务浏览器验收仅归属于原 `9ea89f0`，本次未重跑。

图中 Host、工具执行与持久化职责不变，不新增目标类或关系。工具系统、事件设计与前端主题的现有 PlantUML 已重新生成，SVG 无差异；已检查工具系统主图的原尺寸和文档缩放显示。设计契约脚本、Markdown/图源链接、PUML ASCII、SVG XML 与 diff 检查通过。

<a id="credential-forwarding-evidence"></a>

## 7. 空凭据快照与工具可用性（2026-09-19）

固定实现 `21c3f59be033e7bdd5506a2d9d48baa2581bc3c7` 的读取、三个本地检查、Header
构造与失败转换证据统一见[Runtime 凭据专项](../01-CampusClaw多Agent运行时/source-evidence.md#credential-forwarding-evidence)。
`CallMateTool.execute` 仍在解析前检查 `MateCredentials.isComplete`，
`HttpMateToolClient.invokeTool` 仍会在出站前返回失败，取消两处检查为待实现。
目标不再把凭据完整性当成工具可用条件；空快照不等于 Host 执行上下文缺失。
复用既有 `MateToolClient.callTool(toolId, args, MateCredentials)`，不引入额外调用上下文类型。
执行时序图只调整出站条件和结果归属，其他工具发现与缓存规则不变；不升级名称展示或外部 Agent 基线。

<a id="skill-tool-discovery-evidence"></a>

## 8. Agent 工具代理与 Skill 渐进披露（2026-09-20）

本节只核验工具注册、Skill/资源发现及调用边界。设计起点为 `a2f3f9d05c97495d8917d84c0ca2018a7112671c`；Java 读取本地固定快照 `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12`，不将其表述为当日上游最新。外部基线已重新确认默认分支并在隔离仓库 fetch；以下为默认分支源码快照，不是稳定发布保证。

| 基线 / 默认分支 | 历史登记或前次快照 → 本次提交 | 本次升级范围 |
|---|---|---|
| OpenCode / `dev` | `849c2598abc7d2b40261e74b5826bc74ffc78308` → `ebb7b76eca82342642c78645109e865614533827` | 新增 Skill 加载与普通 MCP 适配证据；不升级旧 Task、事件或实验性 Code Mode 结论 |
| DSH / `master` | `0a53fb55bea101816fa226bb964ae2bed71c343b` → `ddefc45fbc7f8e46dd73185e68295696d1297887` | 新增 Skill 与 MCP 注册证据；当前 `0.1.6-alpha.2` 为开发预览，不升级旧事件溯源结论 |
| Codex / `main` | `d58d0e5841e0de08e251673db2d5af8cf3a1ad51` → `5c5308fc9a9ee789049d646ef11e5400384b9c6f` | 核验来源分流、专用资源读取及 MCP 适配；Skill 当前路径为 `codex-rs/ext/skills/src/`，不能沿用旧 `core/src/skills/` 定位 |
| pi / `main` | `d1230ea2000d876b479a69b8b061f9d670f262f5` → `19451accdeec671c1f4da9eafac8fc270f510ef4` | `core/skills.ts` 与 `core/agent-session.ts` 两文件无差异，元数据目录＋按需读取结论不变；包版本 `0.86.1`，不升级工具事件等旧证据 |

前三项历史登记未覆盖本节完整链路，本节按新提交独立核验，不据此断言这些能力首次出现的版本。前文其他专题的旧 SHA 和验收结果保持原归属。

### 8.1 CampusClaw 已观察实现与差距

Java 前缀 R 为 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`；其余路径相对 `pi-mono-java`。

| 路径 / 关键符号 | 已观察行为 | 目标差距 |
|---|---|---|
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/AgentTool.java` · name/description/parameters；同模块 `loop/AgentLoop.java` · invokeModel/toLlmTools | 每次模型请求从当前 AgentTool 集合生成名称、描述和 Schema；实例可承载不同元数据 | 可复用接口构造 Agent 直接工具代理，不需要 Java 反射代理或业务工具专属类 |
| R `tool/builtin/DefaultConfiguredToolAssembler.java` · assemble；`DefaultBuiltInToolFactory.java` · create | 仅把 profile 中的内置名称转换成实例，包含 ListMateTools/CallMateTool；没有 Skill 工具或业务代理装配 | 新增 Skill、CallTool 与 Agent 直接工具装配为待实现 |
| R `skill/SkillPromptFormatter.java` · format；`tool/read/ReadTool.java` · execute | 目录只提供名称、描述、位置并指示 Read；Read 只读取文件，不注册工具 | 改为 Skill 读取正文和资源入口、Read 读取具体参考文件为待实现；读取不激活工具的边界可保留 |
| R `runtimeapi/service/command/skill/SkillCommandExecutionService.java` · expand | 用户 Skill 命令按可信绑定展开正文和用户参数，没有基础目录/文件清单包装 | 显式命令与模型加载路径需要复用内容装配，不增加业务工具注册副作用 |
| R `tool/mate/ListMateToolsTool.java` · execute/stableJson；`CallMateTool.java` · parameters/execute | List 返回一个来源的全部 name/description/inputSchema 文本；Call 接收 tool/args 并请求 Mate | 业务 Schema 当前不是模型独立工具声明；移除 List 模型入口、Call 改为 CallTool 并限制 Skill 来源为待实现 |
| R `tool/mate/MateToolDiscovery.java` · resolveToolId/loadAllSources；`MateToolSessionCache.java` · CacheState/toNameIndex | 缓存仅存来源及名称到 ID；miss 可在后端完整发现 Agent 和直接 Skill，但不会把定义重新返回模型 | 后端能解析 ID 不等于模型知道参数；Skill 单工具文件提供按需重读入口 |
| R `runtime/MateServiceClient.java` · BoundTool；`common/client/mate/MateToolMeta.java`；`HttpMateToolClient.java` · queryToolMetaByIds | 可信绑定已有 ID/name/displayName/permission 等信息，但不含 inputSchema；独立工具元数据已有 inputSchema | 代理与文件内容均需要完整元数据；本节不决定同步、生成及刷新流程 |
| R `runtime/AgentRuntimeManager.java` · writeSkills/writeResources/loadSkill/containsForbiddenEntry | 写入 SKILL.md、skill.json、references 和 templates；拒绝聚合 tools.json；未从绑定生成单工具定义文件 | 单工具 JSON 资源与资源清单为待实现；不移动 skill.json，不把已有普通资源写入能力称为工具定义生成已实现 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java` · validateArguments；R `runtimeapi/runtime/RuntimeToolPermissionPolicy.java` · from/decide | Pipeline 按 AgentTool.parameters 校验；权限策略合并可信绑定，但只特殊识别 CallMateTool，其他工具名直接 ALLOW | 代理须进入同一权限判断，CallTool 须校验内部业务参数；仅改名称或增加实例不足以完成接入 |
| R `session/compaction/CompactionPromptBuilder.java` · appendMessage/TOOL_RESULT_MAX_CHARS | 提交摘要的单条工具结果最多保留 2,000 字符 | 一次 List 或 Read 不能保证定义长期在场；文件按需披露提供重读能力，不保证模型永不遗忘 |

### 8.2 基线行为与采用边界

下列路径相对各自仓库，并绑定上表本次提交。

| 基线 / 源码路径与符号 | 已观察行为 | CampusClaw 采用边界 |
|---|---|---|
| OpenCode `packages/opencode/src/tool/skill.ts` · SkillTool；`tool/read.ts` | skill 只有 name 参数；返回正文、基础目录、最多 10 个抽样文件绝对路径，排除 SKILL.md 并提示抽样，不展开文件内容或提供资源简介；后续资源由普通 read 读取 | Skill 工具的直接行为基线；宿主受管目录与可信绑定限制仍属 CampusClaw 产品约束 |
| OpenCode `packages/opencode/src/mcp/catalog.ts` · convertTool；`session/tools.ts` · MCP 工具装配；`session/llm.ts` · streamText | 普通模式从远端定义创建通用动态工具，execute 调用 client.callTool，并将工具集合交给模型；实验性 Code Mode 是独立分支 | Agent 直接工具元数据代理的结构参考；不要求 Mate 改用 MCP，也不照搬全量暴露 Skill 工具 |
| DSH `packages/skill/tool-skill/src/index.ts` · apply；`packages/skill/skill/src/index.ts` · renderSkillContent/renderResourceHint | skill(name) 加载正文和资源基础位置，不列目录；资源按需读取，资源位置可为 directory/url/opaque | 支持加载指令与读取资源分工；未采用其多提供方资源协议，不能描述为 DSH 同样返回 10 个文件 |
| DSH `packages/mcp/mcp-client/src/tools.ts` · syncTools/createMcpToolDefinition | 从 MCP 工具定义构造通用代理并注册到 ToolRuntime，执行转发远端；与 skill 加载独立 | 证明通用代理无需每业务工具单独实现；不照搬其工具同步与替换生命周期 |
| Codex `codex-rs/ext/skills/src/catalog_prompt.rs`；`tools/read.rs` · ReadArgs/ReadTool；`tools/mod.rs` · skill_tools | 本地 Skill 走文件读取；executor/orchestrator 资源通过有条件提供的 skills.read(package,resource?,cursor?) 逐项读取，不一次加载全部资源 | 不能把专用读取工具描述为 Codex 对所有本地 Skill 的统一默认入口 |
| Codex `codex-rs/core/src/tools/handlers/mcp.rs` · McpHandler；`handlers/tool_search.rs` · search_output_tools；`tools/spec_plan.rs` · search_tool_enabled | MCP 通过通用 Handler 承载定义；延迟搜索返回可加载定义，启用依赖模型 supports_search_tool 与 Provider namespace_tools | 代理与延迟暴露是独立策略；本设计不引入模型工具搜索和逐工具动态注册 |
| pi `packages/coding-agent/src/core/skills.ts` · formatSkillsForPrompt | 初始只呈现 Skill 名称、描述、位置，提示按需使用 read（或配置的 bash）读取 Skill；相对资源基于 Skill 目录解析 | 保留元数据→正文→所需资源的披露层次；不引入 Bash 或可执行脚本 |

### 8.3 目标决策与验收边界

当前有效方案为：Agent 直接关联的业务工具以 `MateToolAdapter` 实例进入模型工具集合；Skill 关联的业务工具经 `Skill → Read references/<tool-name>.json → CallTool` 按需使用，读取操作不增加代理或权限；`ListMateTools` 退出模型工具列表。单工具文件仅提供 name/description/inputSchema，工具身份与权限由可信绑定决定；两种入口共用业务执行、参数校验与授权规则。精确契约由[主设计](README.md)维护。

这是 **CampusClaw 架构变更**：借鉴 OpenCode 的 Skill 加载入口和基线的远端代理结构，但 Skill 关联的业务工具通过固定 CallTool 执行、Schema 留在资源文件中，是为逐工具披露作出的产品选择，并非上游标准 Skill/MCP 行为。代价是普通读取结果可能被压缩，需要按需重读；不能声称该方案已证明比动态注入更快。无 Bash、受管边界与可信权限属于产品约束及安全加固。

实现状态：新入口、代理装配及对应权限接入均为 **待实现**；本次仅静态核验源码，未运行 Java、真实模型或 Mate 联调。验收重点为初始集合仅含框架工具与 Agent 直接业务代理、Skill/Read 无注册副作用、资源清单不展开定义、CallTool 只解析 Skill 关联的业务工具，以及两入口的 ALLOW/ASK/DENY 和参数错误一致。元数据同步、文件生成与刷新、执行版本一致性另行设计，本节不冻结其策略。

<a id="sequence-evidence"></a>

## 9. 时序交互与生命周期核验（2026-09-21）

本节仅支撑中文时序图的表达修正，沿用并重新读取 Java 固定快照 `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12`；没有升级外部 Agent 基线，也不将该本地快照称为上游最新。图示使用现行目标设计，不调整 Cron、Subagent 或元数据同步方案。类图与架构对比结论不变。

| 路径 / 符号（行号归属上述提交） | 已观察行为与图示边界 |
|---|---|
| R `session/AgentSessionFactory.java:69` · create；`:105` · configureAgent；`:121` · applyPrompt | 公共 Factory 已实现；Factory 调用 prepare，校验 runtime，解析模型与上下文，装配工具并配置 Agent，最后创建 ManagedAgentSession。图从 Host 已确定入口后开始，不把 prepare 迁给 Host。 |
| R `tool/builtin/DefaultConfiguredToolAssembler.java:32` · assemble；`DefaultBuiltInToolFactory.java:56` · create | profile 到框架实例的映射已实现；宿主相关工具通过上下文回调创建。Skill、CallTool、直接 Agent 代理和名称冲突校验仍待实现，空 profile 不追加工具。 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java:146` · runToolPhase；`:179` · invokeModel；`:278` · resolveToolCallsSafe | AgentLoop 先解析已注册工具实例并执行，结果进入后续模型请求。发现图把运行时作为整体，模型返回 tool_call，运行时执行后再请求模型，不画成模型直接调用 Java 对象。 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java:49` · execute；`:87` · applyBeforeHook；`:107` · invokeTool；`:133` · applyAfterHook | 注册 Schema 校验先于 before hook；校验失败或 before hook 拒绝/异常直接返回，不调用工具和 after hook。普通执行异常转错误后进入 after hook；取消向上抛出，由 execution 统一处理，不画成普通失败返回。 |
| R `runtimeapi/runtime/RuntimeActiveExecution.java:155` · beforeToolCall；`RuntimeToolPermissionPolicy.java:41` · decide | ALLOW/ASK/DENY 与确认属于 Host，和 Pipeline 分开表示；新增业务入口的策略识别及各入口接线状态按 §8 判断，不用本图宣称已完成迁移。 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java:161` · executePlanned；`:192` · executeInParallel | 连续并行段、虚拟线程提交、按输入顺序收集 future，以及串行屏障已实现。批次图用异步提交和重叠激活表示并发，乱序完成示例不改变结果顺序；新工具入口的并发模式接线待实现。 |
| R `tool/read/ReadTool.java:96` · execute；`:106` · readText | Read 返回文件文本及必要的截断提示，不自动把 JSON 变成工具定义对象。图选择目标文件已在抽样清单内的首次成功读取场景，重读、查找和失败边界在图前后说明。 |

本次只进行设计与静态源码核验；未执行 Java 或远端 Mate 测试。图形校验验证 PlantUML、SVG 与文档引用，不替代功能验收。

<a id="documentation-style-evidence"></a>

## 10. 文档组织与图形选择的基线证据（2026-09-21）

本次逐仓通过 `git ls-remote --symref` 确认默认分支，在 `/tmp` 隔离仓 fetch 后按提交读取。四仓均与同日上一轮文档调查的提交相同，相关路径无快照变化；下表仅用于文档呈现比较，不升级 §1—§9 的历史运行时结论，也不将默认分支 HEAD 等同于稳定发布。

| 基线 | 默认分支 | 本次及同日上一轮完整提交 |
|---|---|---|
| Codex | `main` | `774d64258260f94628cc9fc55cfabd59a668571c` |
| OpenCode | `dev` | `c10134729dd2ce00beb18604ec91f10319f59a78` |
| DeepSeek Harness | `master` | `ddefc45fbc7f8e46dd73185e68295696d1297887`；根版本 `0.1.6-alpha.2` |
| pi | `main` | `890f920884f6d21fc7617d236ef9e1cc5d7a0ef8` |

| 实际读取的文档样本 | 已观察呈现方式与对应源码 | 对本模块的借鉴及边界 |
|---|---|---|
| Codex [协议示例流程](https://github.com/openai/codex/blob/774d64258260f94628cc9fc55cfabd59a668571c/codex-rs/docs/protocol_v1.md#example-flows) | 先定义对象，再以 UI、Daemon、Model 分组；正常交互与中断分别画时序，并明确省略不重要事件。文首声明可能与代码不完全一致。 | 借鉴场景拆分与参与者分组。该文仍使用源码已无的 `Op::ConfigureSession`，且 TurnComplete 的描述与 `codex-rs/protocol/src/protocol.rs:2147` · `TurnCompleteEvent` 不一致，不能据此更新现行协议。 |
| Codex [App Server 附件契约示例](https://github.com/openai/codex/blob/774d64258260f94628cc9fc55cfabd59a668571c/codex-rs/app-server/README.md#example-manage-stored-thread-attachments) | 方法列表、JSON 请求/响应/通知、顺序与幂等边界配合说明。`codex-rs/app-server/src/request_processors/thread_attachments.rs:36` · `thread_attachment_add` 对应先响应后通知，重复添加不通知。 | 精确调用形式用代码示例和契约表表达；无需把每项规则都塞进时序。`codex-rs/core/README.md` 主要说明 crate、测试及依赖，不是架构时序范本。 |
| DSH [Agent 生命周期](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/docs/agent-lifecycle.md)与[工具流水线](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/docs/tool-execution-pipeline.md) | 前者以运行时职责为参与者画时序，后者用流程图表达许可、钩子、执行及结果分支；分别对应 `packages/core/agent-loop/src/agent.ts:353` · `ReactLoopAgent.step` 与 `packages/core/tools/src/index.ts:1348` · `ToolRuntime.execute`。 | 生命周期与单次工具流水线分别表达。两图由 `scripts/gen-doc-graphs.ts:1394` · `renderLifecycle`、`:1487` · `renderToolPipeline` 的手工编排模板生成，文档明确标注 curated；不是从源码自动抽取的完整时序，alpha 实现也不作为行业规范。 |
| OpenCode [Skills 页](https://github.com/anomalyco/opencode/blob/c10134729dd2ce00beb18604ec91f10319f59a78/packages/web/src/content/docs/skills.mdx) | 目录与 frontmatter 约束、完整 SKILL.md 示例、目录 XML、`skill({ name: "git-release" })` 调用、权限配置和表格，无时序图。`packages/opencode/src/tool/skill.ts:12` · `SkillTool` 对应正文加载及资源路径输出。 | 发现与调用主要用小型代码示例表达。该页把目录位置描述为工具说明，而当前 `packages/opencode/src/session/system.ts:107` · `SystemPrompt.skills` 负责组装 Skill 提示；这里只借鉴表达形式，不照搬该位置描述。 |
| pi [Agent Event Flow](https://github.com/badlogic/pi-mono/blob/890f920884f6d21fc7617d236ef9e1cc5d7a0ef8/packages/agent/README.md#event-flow) | 普通 prompt 与带工具调用分别用文本事件树，配事件表和并发顺序说明；`packages/agent/src/agent-loop.ts:162` · `runLoop`、`:829` · `emitToolExecutionEnd` 对应事件发出点。 | 关注可观察事件顺序时，事件列举比展开内部对象更直接；不把事件树推导成所有内部调用的同步关系。 |

本模块据此选择职责清单、调用示例和少量具体场景图，图中只保留解释该场景所需的参与者；分支和顺序以当前源码证据及目标契约为准。上游使用的图形语法不构成格式要求，本仓仍使用 PlantUML。此次仅调整文档组织与图形表达，不改变工具注册、Skill 渐进式披露、CallTool、权限或同步方案，也不新增运行时机制。
