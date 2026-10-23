# 工具系统源码证据

[返回工具系统主设计](README.md)

版本：1.12.0；整理日期：2026-10-23。以下结论只适用于各行记录的源码提交，保留原核验范围；设计仓整理基线为 `9f83dc1771500ace26360c0982cb1954e2f37de4`。旧提交差距不代表最新实现状态。活动工具的历史主线状态见 §4，三项退役工具的源码删除边界见 §5，工具展示名的来源与实现范围见 §6；注册与发现的历史专项见 §8，文档组织与图形选择见 §10，参数纠正与用户展示见 §11，参数校验、确认与执行的顺序见 §12，SearchTools 最新基线和 PR #323 进度见 §13；Read 文本读取边界见 §14，Schema 校验器与依赖见 §15，[§16](#subagent-depth-evidence)只升级本次 Subagent 深度和装配范围。

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
| 当前 Subagent 同时存在 `spawn_agent` 与 `invoke_agent` 两条路径，后者通过 Session after-hook 执行 | `subagent/tool/SpawnAgentTool.java`、`tool/delegation/InvokeAgentTool.java`、`session/AgentSession.java` |
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
| `tool/builtin/BuiltInToolName.java`；`BuiltInToolProperties.java` · runtime/cron/childAgent；`DefaultBuiltInToolFactory.java` · create | 共 11 个活动名称；Runtime 默认依次包含八项基础工具、ExitPlanMode、TodoUpdate、AskUserQuestion；Cron/Subagent 缺省不含后三项。显式 profile 完全替换默认值。 |
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

当前目标：按主设计 §12.4 完全删除三项工具及专属代码，保留有效公共消费者、智能体本地目录发布和部署脚本。删除前的主线仍有这些类，因此“已不装配”不等于“源码已删除”；实现状态与分支验证结果单独登记，不把未合入开发分支表述为主线完成。

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
| R `runtime/AgentRuntimeManager.java` · writeSkills/writeResources/loadSkill/containsForbiddenEntry | 写入 SKILL.md、skill.json、references 和 templates；拒绝聚合 tools.json；未从绑定生成单工具定义文件 | 证明普通 Skill 资源能力与工具定义没有既有生成链；当前目标改为 §13 的 SearchTools，不再补单工具 JSON |
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java` · validateArguments；R `runtimeapi/runtime/RuntimeToolPermissionPolicy.java` · from/decide | Pipeline 按 AgentTool.parameters 校验；权限策略合并可信绑定，但只特殊识别 CallMateTool，其他工具名直接 ALLOW | 代理须进入同一权限判断，CallTool 须校验内部业务参数；仅改名称或增加实例不足以完成接入 |
| R `session/compaction/CompactionPromptBuilder.java` · appendMessage/TOOL_RESULT_MAX_CHARS | 提交摘要的单条工具结果最多保留 2,000 字符 | 一次 List 或 Read 不能保证定义长期在场；文件按需披露提供重读能力，不保证模型永不遗忘 |

### 8.2 基线行为与采用边界

下列路径相对各自仓库，并绑定上表本次提交。

| 基线 / 源码路径与符号 | 已观察行为 | CampusClaw 采用边界 |
|---|---|---|
| OpenCode `packages/opencode/src/tool/skill.ts` · SkillTool；`tool/read.ts` | skill 只有 name 参数；返回正文、基础目录、最多 10 个抽样文件绝对路径，排除 SKILL.md 并提示抽样，不展开文件内容或提供资源简介；后续资源由普通 read 读取 | Skill 工具的直接行为基线；智能体本地目录与可信绑定限制仍属 CampusClaw 产品约束 |
| OpenCode `packages/opencode/src/mcp/catalog.ts` · convertTool；`session/tools.ts` · MCP 工具装配；`session/llm.ts` · streamText | 普通模式从远端定义创建通用动态工具，execute 调用 client.callTool，并将工具集合交给模型；实验性 Code Mode 是独立分支 | Agent 直接工具元数据代理的结构参考；不要求 Mate 改用 MCP，也不照搬全量暴露 Skill 工具 |
| DSH `packages/skill/tool-skill/src/index.ts` · apply；`packages/skill/skill/src/index.ts` · renderSkillContent/renderResourceHint | skill(name) 加载正文和资源基础位置，不列目录；资源按需读取，资源位置可为 directory/url/opaque | 支持加载指令与读取资源分工；未采用其多提供方资源协议，不能描述为 DSH 同样返回 10 个文件 |
| DSH `packages/mcp/mcp-client/src/tools.ts` · syncTools/createMcpToolDefinition | 从 MCP 工具定义构造通用代理并注册到 ToolRuntime，执行转发远端；与 skill 加载独立 | 证明通用代理无需每业务工具单独实现；不照搬其工具同步与替换生命周期 |
| Codex `codex-rs/ext/skills/src/catalog_prompt.rs`；`tools/read.rs` · ReadArgs/ReadTool；`tools/mod.rs` · skill_tools | 本地 Skill 走文件读取；executor/orchestrator 资源通过有条件提供的 skills.read(package,resource?,cursor?) 逐项读取，不一次加载全部资源 | 不能把专用读取工具描述为 Codex 对所有本地 Skill 的统一默认入口 |
| Codex `codex-rs/core/src/tools/handlers/mcp.rs` · McpHandler；`handlers/tool_search.rs` · search_output_tools；`tools/spec_plan.rs` · search_tool_enabled | MCP 通过通用 Handler 承载定义；延迟搜索返回可加载定义，启用依赖模型 supports_search_tool 与 Provider namespace_tools | 代理与延迟暴露是独立策略；当前目标采用返回定义数据的 SearchTools，不引入搜索后的逐工具动态注册 |
| pi `packages/coding-agent/src/core/skills.ts` · formatSkillsForPrompt | 初始只呈现 Skill 名称、描述、位置，提示按需使用 read（或配置的 bash）读取 Skill；相对资源基于 Skill 目录解析 | 保留元数据→正文→所需资源的披露层次；不引入 Bash 或可执行脚本 |

### 8.3 目标决策与验收边界

当前有效方案为：Agent 直接关联的业务工具以 `MateToolAdapter` 实例进入模型工具集合；Skill 关联的业务工具经 `Skill → SearchTools → CallTool` 按需使用。SearchTools 按唯一工具名返回单个完整定义数据，不增加代理、权限或后续模型请求中的工具；`ListMateTools` 退出模型工具列表。SearchTools 与 CallTool 复用可信解析职责并保持披露和校验定义一致，工具身份与权限仍由可信绑定决定；两种执行入口共用业务执行、参数校验与授权规则。精确契约由[主设计](README.md)维护。

这是 **CampusClaw 架构变更**：借鉴 OpenCode 的 Skill 加载入口、OpenCode Code Mode 的固定搜索入口和基线的远端代理结构，但 Skill 关联的业务工具仍通过固定 CallTool 执行，搜索结果不成为动态模型工具。该选择保留逐工具披露，并避免跨轮维护已注入工具集合；定义结果仍可能被压缩，需要按需重搜，不能声称已证明比文件读取或动态注入更快。无 Bash、受管边界与可信权限属于产品约束及安全加固。

实现状态：本节的 `fb842b1` 旧快照尚无新入口；PR #323 最新进度由 §13 单独核验。SearchTools、发现与校验的一致性及相应 profile 接线为 **待实现**。验收重点为初始集合仅含框架工具与 Agent 直接业务代理、Skill/SearchTools 无注册副作用、搜索不展开整个 Skill、CallTool 只解析 Skill 关联的业务工具，以及两入口的 ALLOW/ASK/DENY 和参数错误一致。元数据同步、刷新与版本一致性另行设计，本节不冻结其策略。

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

<a id="argument-recovery-evidence"></a>

## 11. 本地参数纠正与用户展示（2026-09-22）

本节设计仓起点为 `dd834ecf6ec91657b30fb7df64fa2b6de128388c`。CampusClaw 读取开发工作树 `/private/tmp/pi-mono-java-tool-progressive` 的固定提交 `c9a2340f87bda6dff6bbd352f6995f8551206bb5`；以下文件与该提交一致，不将其表述为最新主线或已合入版本。§8 的 `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12` 保留原观察，本节只更新已实际读取的 CallTool、代理、业务校验、结果回传和展示链路。

pi 上游 `https://github.com/badlogic/pi-mono.git` 于 2026-09-22 通过 `git ls-remote --symref ... HEAD` 确认默认分支 `main`，在隔离 bare 仓库 fetch 后读取 `95fbc04997eaee961eb673fa7923e9220609ebd5`。`packages/agent/package.json` 版本为 `0.87.0`；这是当次默认分支源码快照，不是稳定发布保证。相对 §10 的 `890f920884f6d21fc7617d236ef9e1cc5d7a0ef8`，本次仅比较以下三个恢复相关路径：`validation.ts` 无差异；`agent-loop.ts` 增加请求准备及 `finishTurn` 结束/继续决策，校验失败转结果的路径不变；`agent-session.ts` 的消息持久化仍覆盖 `toolResult`，新增 Entry ID 追踪等其他 Session 变化不在本节升级范围。§1—§10 其他 SHA、版本及验收结论保持原归属。

### 11.1 CampusClaw 已观察行为

Java 前缀 R 为 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`；其余路径相对 `pi-mono-java`。行号均属于上述 `c9a2340f`。

| 路径 / 关键符号 | 已观察行为 | 对参数纠正的影响 |
|---|---|---|
| R `tool/skill/SkillTool.java:93` · execute、`:156` · format；`skill/SkillPromptFormatter.java` · format | Skill 按直接可见名称读取 SKILL.md 并返回正文及最多 10 个资源路径；初始提示只列名称、描述与读取规则；不展开资源内容 | Skill 基本加载已在本开发提交实现；本节当时采用 Read 定义文件，当前目标已由 §13 的 SearchTools 替代 |
| R `tool/mate/CallTool.java:54` · parameters、`:78` · execute；`MateToolAdapter.java:38` · 构造器、`:68` · parameters | CallTool 只向模型声明外层 tool/args；Agent 代理直接声明业务 Schema；两者调用同一 MateToolExecutor | §8 中的新执行入口已在本分支实现，不能把整个渐进披露方案继续记为待实现；错误回传的增量单独记录 |
| R `tool/mate/MateToolResolver.java:68` · resolveSkill、`:125` · findMetadata、`:139` · resolved | 先按直接 Skill 的可信绑定查找，再按 ID/name 匹配元数据，返回绑定与定义组成的 ResolvedTool；缺失 Schema 拒绝解析 | 回传定义有可信来源，可以使用本次实际参与校验的定义，不需要让模型重读文件后决定权限或执行 ID |
| R `tool/mate/MateToolExecutor.java:67` · execute、`:80` · validateArguments；`MateToolExecutionException.java` | 业务参数校验在 client.callTool 前完成；失败文本含字段错误，但没有完整 Schema；参数错误、无效 Schema 和远端业务错误使用同一异常类型 | 参数错误时尚未请求 Mate 业务执行；当前异常不能直接区分可修复参数错误与其他失败，完整定义回传为待实现 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java:49` · execute、`:250` · validateArguments、`:291` · failureResult；同目录 `ToolArgumentsInvalidException.java` | 外层 Schema 校验先于 before hook；执行异常转 isError=true；StableErrorCode 异常仅输出稳定错误码 content，其他异常输出消息文本 | 框架外层错误和业务内层错误必须保留区别；仅把新增恢复异常实现为 StableErrorCode 会使模型只看到错误码，须明确保留恢复正文 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java:112` · runTurns、`:146` · runToolPhase；`modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateChatRequestMapper.java:118` · appendToolResult | 工具结果加入上下文，随后继续模型请求；Mate Chat 将工具结果 content 写成 role=tool，不发送 details | 模型继续纠正的 Loop 已实现；Schema 与字段错误必须进入模型可见 content，仅写 details 不足以完成恢复 |
| R `runtimeapi/event/RuntimeEntryCodec.java:197` · toolResultEntry、`:545` · toolResultMessage；`RuntimeCommittedEventFactory.java:152` · agentToolResult、`:283` · appendToolContent、`:299` · toolErrorCode | 工具 Entry 保存 content、is_error 和可选 error_code；不通用保存 details。公共失败内容替换成稳定错误码对应的本地化文案，未知错误码回退 TOOL_EXECUTION_FAILED | 模型结果正文和公共展示原本已有不同投影；新增失败分类须贯穿持久化与历史恢复，不能只放在不会重载的内存 details 中 |
| `frontend/src/projectors/runtimeEventProjector.ts:23` · projectRuntimeEvents、`:118` · matchingToolResult；`frontend/src/components/ToolActivity.vue:9` · statusLabel、`:50` · details | 结果按 sourceEventId＋toolCallId 匹配，isError 一律投影为 error；错误显示“执行失败”，默认展开；后续不同调用的成功不会覆盖前次失败 | 可恢复中间过程的低干扰展示尚未实现；不能只增加后端 Schema 回传就宣称用户已无失败感知 |

### 11.2 pi 的恢复语义与采用边界

下列路径相对 pi，行号属于 `95fbc04997eaee961eb673fa7923e9220609ebd5`。

| 路径 / 关键符号 | 已观察行为 | CampusClaw 采用边界 |
|---|---|---|
| `packages/ai/src/utils/validation.ts:317` · validateToolArguments、`:282` · formatValidationPath | 根据实际工具 parameters 校验；异常正文含字段路径、错误说明和收到的参数，没有附回完整 Schema | 采用明确字段错误；完整目标定义回传是 CampusClaw 为 CallTool 渐进披露补充的设计，不描述为 pi 既有能力 |
| `packages/agent/src/agent-loop.ts:703` · prepareToolCall、`:773` · executePreparedToolCall、`:863` · createErrorToolResult | 校验失败返回 immediate、isError=true 的文本结果，不进入 tool.execute；普通错误结果不设置 terminate | 保留“参数拒绝尚未执行业务”和真实错误结果，不通过改成成功来降低 UI 噪音 |
| 同文件 `:527` · executeToolCallsSequential、`:583` · executeToolCallsParallel、`:880` · createToolResultMessage、`:162` · runLoop | 两种调度均生成工具结果；runLoop 将结果写入上下文，通常继续下一次模型请求。批次 terminate、finishTurn 结束决策及取消等仍可结束执行 | 延续工具失败可由模型纠正的 Loop 语义，不新增服务端自行猜参数重试或忽略终止条件的循环 |
| `packages/coding-agent/src/core/agent-session.ts:894` · _handleAgentEvent | message_end 分支将 toolResult 与其他普通模型消息交给 SessionManager.appendMessage | 历史保留失败尝试与下一次调用；前端折叠是展示选择，不删除或篡改原记录。本节未核验 pi UI，不据此断言 pi 默认隐藏失败 |

### 11.3 目标决策、实现差距与验收

当前目标由[工具系统主设计](README.md)统一维护：CallTool 在首次业务参数本地校验失败时，即把本次可信完整目标定义、字段错误和“业务尚未执行”的说明返回模型，供下一次调用纠正；定义来自同次解析及校验使用的元数据，不以文件内容、模型猜测或另一次发现替代。若错误位于 CallTool 外层，只能提供外层参数修正信息，不为无法可信解析的目标伪造业务定义。授权、业务失败、无效 Schema 和网络等失败不自动归类为参数纠正。

前端将可恢复参数纠正作为低干扰过程保留，默认折叠详情；失败记录仍保持真实 isError 语义，后续成功保留自身独立结果。最终未能完成和真实业务失败必须明确展示，不能让未解决的纠正状态永久表现为仍在执行。公共展示不靠解析模型正文识别类别，恢复正文及持久化投影按各自边界处理。

完整定义反馈属于 **CampusClaw 架构变更**：在 pi 的“错误作为工具结果进入后续模型上下文”基础上，减少模型再次查找定义的步骤。可恢复过程展示属于**产品约束**，减少用户阅读中间失败的负担；可信绑定、权限保持原有产品约束及安全边界。每次补回定义会增加上下文和等待成本，准确率、减少轮次数及用户体验改善仍需实际验收，不能作为已证明效果。

实现状态：在本节核验的 `c9a2340f` 上，本地业务参数拒绝、Pipeline 外层稳定参数错误码、工具错误入上下文与后续 Loop 已实现，完整定义反馈等增量尚未实现；PR #323 后续提交的进度由 §13 更新。实时/历史前端低干扰展示仍为 **待实现**。本节仅静态源码核验和设计证据补充，未运行 pi、Java、真实模型或 Mate 联调测试。后续验收至少覆盖首次失败即回传同次完整定义、业务执行次数为零、模型下一次请求收到恢复正文、修正后沿原权限链执行、失败记录与成功记录均保留、重新读取历史保持相同分类，以及最终未修复和真实失败不会被隐藏。

<a id="tool-validation-order-evidence"></a>

## 12. 参数校验、确认与执行顺序（2026-09-22）

本节只核验工具调用从参数进入到业务执行的先后关系。2026-09-22 重新确认 pi 默认分支为 `main`，隔离 fetch 后读取 `95fbc04997eaee961eb673fa7923e9220609ebd5`，`packages/agent/package.json` 版本为 `0.87.0`；该提交与 §11 相同，本次重新读取相关符号。DeepSeek Harness 默认分支为 `master`，隔离 fetch 后读取 `c36a83ff6bb95e3f82cf79f9be7c724270a8aa61`，`packages/core/tools/package.json` 版本为 `0.1.7-alpha.1`。两者均为当日默认分支源码快照，不等于稳定发布。

CampusClaw 继续读取开发提交 `c9a2340f87bda6dff6bbd352f6995f8551206bb5`，不把开发分支行为表述为 main 已实现。Java 前缀 R 为 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`；其余路径相对 `pi-mono-java`。

### 12.1 已观察顺序

| 基线与源码符号 | 已观察顺序 | 设计含义 |
|---|---|---|
| pi `packages/agent/src/agent-loop.ts` · `prepareToolCallArguments`、`prepareToolCall`、`executePreparedToolCall`；`packages/ai/src/utils/validation.ts` · `validateToolArguments` | 可选参数准备 → 注册 Schema 校验与转换 → `beforeToolCall` → `tool.execute` → `afterToolCall`；校验异常直接形成 `isError=true` 结果，不进入 before hook | pi 明确提供“参数有效后再执行 hook”的主基线；其 `prepareArguments` 只返回参数，未解决 CampusClaw 动态代理需要固定业务目标的问题 |
| DeepSeek Harness `packages/core/tools/src/index.ts` · `ToolRuntime.prepareExecution`、`dispatchToolBody`；`packages/core/tools/src/schema.ts` · `defineTool` | 创建执行快照 → `tools/pre-execute` policy/ask → dispatch → `defineTool.execute` 包装器校验参数 → 用户业务实现；参数无效时用户业务实现不运行，但 ask 已可能发生 | 当前 alpha 实现证明基线间没有统一固定顺序；其注册表、policy 与工具包装器边界不能直接作为 CampusClaw 的强制规范 |
| CampusClaw `modules/agent-core/.../ToolExecutionPipeline.java` · `execute`、`validate`、`applyBeforeHook` | 注册工具 Schema 校验 → before hook → `tool.execute` → after hook | Agent 直接代理的完整业务 Schema 在确认前校验，符合目标主顺序 |
| CampusClaw R `runtimeapi/runtime/RuntimeActiveExecution.java` · `beforeToolCall`；`RuntimeToolPermissionPolicy.java` · `decide` | before hook 按 `CallTool.arguments.tool` 得到 ALLOW/ASK/DENY；ASK 会进入确认处理 | hook 只检查可信绑定与权限，不校验 `args` 的业务 Schema |
| CampusClaw R `tool/mate/CallTool.java` · `execute`；`MateToolExecutor.java` · `executeSkill`、`execute`、`validateArguments` | `CallTool` 外层 Schema 校验 → Host 权限/确认 → `CallTool.execute` → 可信解析与业务参数校验 → Mate execute | 业务参数虽然在远端请求前拒绝，但无效调用可能先产生用户确认；这与本次目标顺序存在明确实现差距 |

### 12.2 CampusClaw 目标与原因

CampusClaw 选择 pi 的前置校验顺序作为 Runtime 主基线，并增加适合动态业务代理的不可变准备结果：

1. Pipeline 校验已注册工具的外层或完整 Schema；
2. 工具准备本次调用。`CallTool` 只在当前 Session 的直接 Skill 绑定内解析业务目标，使用可信 Schema 校验 `args`，生成包含目标 ID、定义版本和参数的不可变 `PreparedToolInvocation`；
3. 参数失败直接向模型返回 `isError=true`、字段错误及同次可信定义，不创建用户确认，不发送 Mate execute；
4. 参数有效后，Host 依据准备结果中的可信目标执行 ALLOW/ASK/DENY；
5. 放行后执行同一个准备结果，结果进入既有 after hook、模型上下文和持久化投影。

该顺序不是声称所有 Agent 都如此，而是 **pi 主基线 + CampusClaw ToB 产品约束 + 安全加固**。业务参数明显无效时不应打扰园区运维人员；确认前后复用同一不可变目标和参数，避免等待期间重新解析造成身份、Schema 或参数漂移。准备阶段不得携带执行凭据、调用 Mate execute、接受模型提供的 ID/URL/Schema，未知或不可见名称也不得借错误反馈泄露定义。

### 12.3 实现差距与验收

在本节核验的 `c9a2340f` 上，`AgentTool` 只有 `execute`，`ToolExecutionPipeline` 没有工具准备阶段，`MateToolExecutor` 把解析、校验和远端执行放在同一个私有 `execute` 中；因此这些能力在该快照上属于实现差距。PR #323 后续提交已补齐的范围由 §13 更新，不能继续用本节旧快照判断当前开发分支状态。

实现验收至少覆盖：外层错误不解析业务目标；业务缺必填、类型或枚举错误不创建确认记录且 Mate execute 为零；合法 ASK 只确认一次；批准后只执行准备时固定的工具 ID 和参数；确认等待期间刷新或元数据变化不替换本次快照；拒绝和取消不执行；参数错误的模型反馈保留 `isError=true` 与同次定义；未知目标、无效 Schema、权限拒绝和远端失败保持各自分类。本节为静态源码核验，未运行 pi、DSH、Java、真实模型或 Mate 联调测试。

<a id="search-tools-evidence"></a>

## 13. SearchTools 目标与当前开发分支（2026-09-22）

本节只更新 Skill 工具发现方式和 PR #323 的实现进度。OpenCode 上游 `https://github.com/anomalyco/opencode.git` 通过 `git ls-remote --symref` 确认默认分支为 `dev`，隔离 fetch 后读取 `fe3f3a41f79ad292cc3c7c629567385a20ec5130`；Codex 上游 `https://github.com/openai/codex.git` 的默认分支为 `main`，隔离 fetch 后读取 `ac7634b9f73ec1bf96466be7a5869f0949d20b30`。两者都是当日默认分支源码快照，不等于稳定发布保证。OpenCode Code Mode 是独立 package，Codex tool_search 的可用性受 Provider、模型能力和配置约束，不能将二者写成所有 Agent 的统一机制。

### 13.1 基线观察

| 基线 / 路径与符号 | 已观察行为 | 对 CampusClaw 的边界 |
|---|---|---|
| OpenCode `packages/codemode/src/tool-runtime.ts` · `prepare`、`makeSearchTool`、`searchIndex`；`packages/codemode/README.md` · Discovery | Code Mode 以预算内联部分完整签名，固定注册 `tools.$codemode.search`；搜索返回 path、description 和完整 signature，底层工具树不因搜索而改变。精确路径命中只返回一个，普通查询确定性加权并分页。 | 借鉴固定发现入口和完整定义结果；CampusClaw 采用唯一名称精确匹配，不采用模糊排序或 Code Mode 解释器，返回 JSON Schema，并继续通过 CallTool 执行。 |
| OpenCode `packages/opencode/src/tool/skill.ts` · `SkillTool` | 普通 Skill 仍只加载正文、基础目录和最多 10 个抽样资源路径，普通资源由 read 读取。 | 保留 Skill 正文与普通资源行为；SearchTools 是 CampusClaw 宿主扩展，不写入标准 Skill 包。 |
| Codex `codex-rs/core/src/tools/handlers/tool_search.rs` · `ToolSearchHandler/get_or_build/search`；`tool_search_spec.rs` · `create_tool_search_tool`；`tools/registry.rs` · `ToolExposure` | 对 deferred 工具建立 BM25 搜索，结果是可加载 ToolSpec；工具说明明确匹配定义会暴露给下一次模型调用。Handler 缓存按 registry source 变化重建。 | 证明延迟工具搜索可以由专用入口实现；CampusClaw 不采用“搜索后把业务工具加入下一次模型 tools”的语义，以避免模型工具集合随会话变化。 |

### 13.2 CampusClaw PR #323 已观察实现

实现仓工作树 `/private/tmp/pi-mono-java-tool-progressive` 的 PR #323 head 为 `ae6645caaade3b9520220a34af940210850ef36a`，base 为 `1d66e52d1ce6cfc40cd6e37f5341e06dd23b50b0`。该 PR 为 Draft；GitHub `build` 检查在 2026-09-22 成功。本次只做静态源码核验与远端检查读取，没有重跑本地 Java、前端、真实模型或 Mate 联调。

| 路径 / 关键符号 | 已观察实现 | 与当前目标的差距 |
|---|---|---|
| `modules/agent-core/.../AgentTool.java` · `prepare`；`PreparedToolInvocation.java`；`ToolExecutionPipeline.java` · `prepare/failureResult/recoveryContent` | Pipeline 在 before hook 前建立不可变调用；参数失败保留 `isError=true`、稳定错误码和模型可见的同次定义。 | 确认前准备与模型恢复反馈已经实现，不再标为待实现。 |
| `modules/coding-agent-cli/.../tool/mate/CallTool.java` · `prepare`；`MateToolExecutor.java` · `prepareSkill/executePrepared`；`RuntimeToolPermissionPolicy.java` · `decide` | CallTool 在确认前解析和校验，Host 按 prepared target 决策，放行后执行同一目标和参数。 | 执行顺序已与目标一致；SearchTools 需要复用可信解析并保持披露和校验定义一致。 |
| 同模块 `tool/mate/MateToolResolver.java` · `resolveAgentTools/resolveSkill/loadSkillTool/merge/validateCrossScopeNames`；`MateToolsetFactory.java` · `createSession` | Resolver 按 Agent 或扁平 Skill 工具名称解析元数据并缓存，已有同名同 ID 合并和同名不同 ID 拒绝；Skill 与 Agent 定义读取分别缓存。 | 可复用既有名称解析建设 SearchTools；需补发现输出与校验定义一致性接线，不能把现有缓存当作跨版本同步方案。 |
| 同模块 `tool/builtin/BuiltInToolName.java`、`DefaultBuiltInToolFactory.java`、`BuiltInToolProperties.java` | 当前框架清单无 SearchTools。 | 新工具枚举、工厂、默认 Runtime/Cron/Subagent profile、严格名称测试和公司镜像均待实现。 |
| 同模块 `tool/skill/SkillTool.java`、`skill/SkillPromptFormatter.java`；`CallTool.java` · `description/parameters` | Skill 返回正文和普通资源路径；CallTool 文案仍指引读取定义文件。 | 宿主提示和 CallTool 文案需改为按需调用 SearchTools，且不得要求 Skill 正文引用平台工具文件。 |

### 13.3 当前目标与验收边界

CampusClaw 采用 `Skill → SearchTools → CallTool`：Skill 正文引用唯一业务工具名，SearchTools 是固定并行工具，只接收 `{tool}` 并返回该名称对应的单个完整定义。名称与可信绑定精确匹配，不模糊检索、不自动注册、不增加后续模型请求的 tools。Agent 直接工具仍以代理提供定义。发现、代理和调用复用可信解析职责，保持已披露定义与校验一致；确认后执行同一准备结果。

这是相对 PR #323 的 **待实现架构变更**。正常流程应证明：模型从正文识别准确工具名，取得完整定义，CallTool 按一致定义校验并经 Host 授权后执行。失败流程应证明：未知、未绑定、不可披露、冲突、无效及超大定义明确失败；不猜测相似工具；参数失败不确认、不执行并带同次定义；多轮发现不改模型工具集合。定义的来源接入、全量或按需加载、缓存与失效、刷新、跨节点同步、版本切换和恢复一致性均由后续专题设计，不以完整 Session 定义快照作为本版前提。

### 13.4 精确名称与同步设计边界核验（2026-09-22）

设计仓修订起点为 `82032c5c53abcef6fd592c7be9aa0ca5e873a039`。本次重新读取 PR #323 固定开发提交 `ae6645caaade3b9520220a34af940210850ef36a` 的上述 MateToolResolver、CallTool、MateToolExecutor 及同目录 MateToolSessionState 全文；不宣称该固定提交是最新主线或已合入版本。`resolveSkill` 按名称查可信绑定，`merge/validateCrossScopeNames` 拒绝不同身份重名；`prepareSkill` 使用解析结果校验后生成 PreparedToolInvocation，执行时复用已准备参数。该证据支持精确发现复用现有解析职责，无需新增模糊检索或全量目录类。

产品约束为工具名称唯一、Skill 正文引用业务工具名；架构变更为固定 SearchTools 精确披露，发现和执行共用可信解析。数据加载及同步策略为待设计依赖；名称索引和调用准备已存在，不代表同步已解决。此次设计制品校验不包含 Java、远端 Mate、真实模型或跨版本联调验收。

外部基线于 2026-09-22 再次确认默认分支并隔离 fetch：OpenCode `dev@fe3f3a41f79ad292cc3c7c629567385a20ec5130` 未变，重读 `packages/opencode/src/tool/skill.ts#SkillTool` 与 `packages/codemode/src/tool-runtime.ts#prepare/makeSearchTool/make`；精确路径命中返回单个定义的分支保持。Codex 从 §13.1 的 `ac7634b9f73ec1bf96466be7a5869f0949d20b30` 更新至 `main@89a7298aff55db29f9cb2ad2430e3efe02b7a454`，重读 `codex-rs/core/src/tools/handlers/tool_search.rs#ToolSearchHandler/ToolSearchHandlerCache::get_or_build/search`、`tool_search_spec.rs#create_tool_search_tool` 和 `tools/registry.rs#CoreToolRuntime/ToolExposure`（重导出）；上述路径与 BM25、可加载定义、缓存来源比较的结论保持。默认分支源码快照不等于稳定发布；本次只升级工具发现证据，pi/DSH 的参数顺序仍引用 §12 的历史核验。

<a id="read-text-only-evidence"></a>

## 14. Read 文本读取边界（2026-10-08）

本节读取 pi-mono-java 本地固定提交 `553dcd5e2ff682f9684810a043b442b37a02e54a`，以下文件与该提交一致；不声明为最新远端版本。本次只核验 Read 的描述、字节读取、文本解码与输出，不升级其他工具、Provider 或外部 Agent 基线。当前契约仅包含已实现的 UTF-8 文本读取，不包含图片读取与缩放。

下列路径相对 `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/`：

| 路径 / 符号 | 已观察实现 |
|---|---|
| `tool/read/ReadTool.java` · `description/execute/readText` | 描述明确为 UTF-8 文本；读取字节后直接调用 readText，仅构造 TextContent，没有图片识别、解码、缩放或 ImageContent 输出分支。 |
| `tool/read/ReadTool.java` · `decodeText` | 空字节或严格 UTF-8 解码失败时抛出 WorkspaceAccessException，消息为 Unsupported binary file。 |
| `tool/ops/ReadOperations.java` · `readFile`；`tool/ops/LocalReadOperations.java` · `readFile` | 接口返回 byte[]，本地实现调用 Files.readAllBytes；字节读取不代表支持图片内容块。 |
| `tool/builtin/BuiltInToolContracts.java` · `description` | READ 的统一描述也是 Read the contents of a UTF-8 text file.，与实际工具一致。 |

这是契约描述与已观察实现的对齐，不新增图片能力，也不将图片处理列为已确认的待实现增量。工具分层、调用顺序和 Agent 架构对比结论不变，既有 PlantUML 与 SVG 无需修改。验证限于源码静态核验和文档检查，未运行 Java 测试或真实模型调用。

<a id="tool-schema-validator-evidence"></a>

## 15. Schema 校验器与 json-schema-validator 依赖（2026-10-17）

本节读取 pi-mono-java `main@1446c58564539eb320fa3c6b495be34e5f985394`（2026-10-17 fetch），只核验工具参数校验的调用点、Schema 关键字用量和依赖树；networknt 行为读取 `json-schema-validator-1.5.2-sources.jar`。结论支撑[主设计 §9.7](README.md#tool-schema-subset)。

### 15.1 CampusClaw 已观察实现

| 路径 / 符号 | 已观察实现 |
|---|---|
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolSchemaValidator.java` · `validate`（:28、:38）、`validateDefinition`（:71）、`toError`（:93） | 唯一使用 networknt API 的类。每次调用 `schemaFactory.getSchema` 重新解析定义；`validateDefinition` 用空对象试校验来判断定义能否加载；`required` 错误把字段名补进路径，其他错误用 networknt 的实例位置；错误文案直接取 `ValidationMessage.getMessage()` |
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java` · 字段 `schemaFactory`（:42）、`validate` | 用 `JsonSchemaFactory.getInstance(V202012)` 校验全部已注册工具（框架工具与 Agent 直接代理）；`ToolSchemaInvalidException` 记日志后转为错误结果 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/MateToolExecutor.java` · 字段 `schemaFactory`（:47）、`validateArguments`、`validateDefinition` | Mate 业务工具同样按 2020-12 校验；定义无效转为 `InvalidDefinitionException`（`TOOL_DEFINITION_INVALID`），日志 `validationReason=INVALID_TOOL_SCHEMA` |
| `modules/ai/pom.xml`（:61） | 声明了 `json-schema-validator`，`ai` 模块源码没有使用 |
| `modules/agent-core/pom.xml`（:41）、`campusclaw/pom.xml`（:106）、根 `pom.xml`（:34、:75） | compile scope 依赖；版本 1.5.2 由根 POM 管理 |

框架工具定义的关键字用量（统计 `modules/*/src/main` 下 Java 源码中带引号的关键字，例如 `CronTool`、`ReadTool`、`AskUserQuestionTool`、`BuiltInToolContracts`）：`type`、`properties`、`required`、`additionalProperties`（全部为 `false`）、`enum`、`const`、`minLength`（`CronTool`、`ExitPlanModeTool`、`AskUserQuestionTool`、`BuiltInToolContracts`、`SearchTools`、`TodoUpdateTool`）、`maxLength`、`minItems`、`maxItems`（`AskUserQuestionTool`、`TodoUpdateTool`）、`pattern`（作为关键字仅 `AskUserQuestionTool` 的问题 ID；`GrepTool`、`FindTool` 中的 `pattern` 是参数名）、`items`、`oneOf`（仅 `CronTool`）、`description`、`$schema`（仅 `AskUserQuestionTool`，取 2020-12）。没有 `integer`、类型数组、`title`、`default`、`examples`、`minimum`、`maximum`、`format` 或 `$ref`。Mate 现网工具定义的关键字用量未核验。

`campusclaw-coding-agent` 的 `dependency:tree` 中，`json-schema-validator` 1.5.2 带入 `com.ethlo.time:itu` 1.10.2 和 `jackson-dataformat-yaml` 2.18.3，三者都只经它引入；本地 jar 大小分别为 576,375、53,903、55,579 字节，合计约 686 KB。`snakeyaml` 2.3 另由 `spring-boot-starter` 引入。源码中没有其他 `dataformat.yaml` 或 `com.ethlo` 使用者。公司父 POM 下的依赖树未核验。

### 15.2 networknt 1.5.2 默认行为

| 源码路径 · 符号 | 观察 | 对设计的影响 |
|---|---|---|
| `com/networknt/schema/format/BaseFormatJsonValidator.java` · `isFormatAssertionVocabularyEnabled`；`FormatValidator.java` · `validate` | 2020-12 下只有元 Schema 声明 `format-assertion` 词表或显式开启时才断言 `format`；默认元 Schema 下 `format` 只是注解 | 子集丢弃 `format`，不校验，校验结果与现状一致 |
| `com/networknt/schema/resource/DefaultSchemaLoader.java`；`resource/UriSchemaLoader.java` · `load` | 默认加载器链包含按 URL `openConnection` 的加载器 | 外部定义里的远程 `$ref` 可能在校验时触发网络请求；未做联网复现。子集丢弃 `$ref`，不解析也不加载 |
| `com/networknt/schema/SchemaValidatorsConfig.java` · `getLocale` | 未配置时返回 `Locale.getDefault()` | 现状错误文案随部署环境语言变化；目标改为固定模板 |
| `com/networknt/schema/regex/JDKRegularExpression.java` · `matches` | 默认用 `java.util.regex` 的 `find()` | 子集沿用相同正则引擎与部分匹配语义 |
| `com/networknt/schema/MinLengthValidator.java`、`MaxLengthValidator.java` | 按码点计数长度 | 子集按码点计数，与现状一致 |

### 15.3 外部基线

2026-10-17 确认默认分支并隔离浅克隆，只读文件、不运行代码：

| 基线 | 提交 | 路径 · 符号 | 观察 |
|---|---|---|---|
| pi | `main@8efd314fa3d3232ce197d8d7a6a5660530b9d83e` | `packages/ai/src/utils/validation.ts` · `validateToolArguments`；`packages/agent/src/agent-loop.ts` · `prepareToolCall`；`packages/coding-agent/src/extensions/mcp/tools.ts` · `toParameters` | 用 TypeBox 1.3.27 校验全部工具（含 MCP），校验前做大量类型转换；MCP Schema 原样透传，不限关键字；失败信息带路径列表和收到的参数，作为错误结果回给模型。TypeBox 实际支持的关键字范围未核验 |
| Codex | `main@3b8f43a06bb3105e81406b35ff69f94977d18ae4` | `codex-rs/tools/src/json_schema/types.rs` · `JsonSchema`；`codex-rs/tools/src/json_schema.rs` · `sanitize_json_schema`；`codex-rs/core/src/mcp_tool_call.rs` · `handle_mcp_tool_call` | 工具定义收敛到固定结构（保留 `$ref`、`type`、`enum`、`items`、`minItems`、`properties`、`required`、`additionalProperties`、`anyOf`、`oneOf`、`allOf`、`$defs` 等），其余关键字静默丢弃；本地不按 Schema 校验参数，MCP 参数只要求是合法 JSON，由服务端校验 |
| OpenCode | `dev@65932e870ca50d21886f9d0ee89c6603bac34a65` | `packages/core/src/tool/runtime.ts` · `validateInput`、`formatInputIssues`；`packages/core/src/tool/mcp.ts` | MCP Schema 转成 Effect Schema 后校验，转换失败就跳过校验；错误最多列 5 条并提示重新调用 |
| DeepSeek Harness | `master@1517a4dbca0a2789ff1d41ba439600f8547d23fa` | `packages/core/tools/src/json-schema.ts` · `assertSupportedJsonSchema`、`validateJsonSchemaValue`；`packages/mcp/mcp-client/src/tools.ts` · `createMcpToolDefinition` | 自写严格子集：`type`、`oneOf`、`properties`、`required`、`additionalProperties`（仅布尔）、`items`、`enum`、`const` 及四个注解，其余关键字拒绝；`oneOf` 至少两个分支且不许有同级关键字，`required` 的字段必须出现在 `properties`。只用于自有工具，MCP 输入 Schema 原样透传且本地不校验 |

DeepSeek Harness 的子集规则比 CampusClaw 更严：`CronTool` 在 `oneOf` 旁边还有同级 `properties` 和 `required`，分支内 `required` 的字段也不在分支 `properties` 中，按 DSH 规则会被拒绝，所以 §9.7 不照搬这两条限制。

<a id="subagent-depth-evidence"></a>

## 16. Subagent 深度与工具披露（2026-10-23）

本次重新 fetch 公共实现仓默认分支 `main@e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2`，在保留用户工作树的前提下按明确提交核验下列范围。主设计[§10.1](README.md#subagent-depth)的服务配置、整树上限与逐级披露为**待实现**；只升级这些 Java 符号，不重新核定其他工具或外部 Agent 基线。

| 源码路径与符号 | 已观察实现与差距 |
|---|---|
| [tool/agent/SubagentExecutionService.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/agent/SubagentExecutionService.java#L41) · MAX_CHILD_DEPTH/execute/requireAvailableDepth | 最大深度是固定常量 1，执行时检查 context.depth；没有服务配置或根 maxDepth 快照，新的内部原因码与受理复核仍待实现 |
| 同文件 [runChild](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/agent/SubagentExecutionService.java#L83)；[session/AgentSessionFactory.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSessionFactory.java#L82) · create | Subagent 创建请求不提供 agentToolFactory；工厂把 Host 提供的工具工厂交给装配上下文，嵌套需要同时调整可信上下文与工厂接线，不能只放大常量 |
| 同文件 [resolveChildModel](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/agent/SubagentExecutionService.java#L130) | 查询当前 Subagent 自身目录快照和模型绑定，调用默认模型解析，不以父模型作自动回退；多级执行继续复用 Model 规则，不新增另一套模型来源 |
| [tool/builtin/BuiltInToolProperties.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/builtin/BuiltInToolProperties.java#L47) · childAgent/toolsFor；[DefaultBuiltInToolFactory.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/builtin/DefaultBuiltInToolFactory.java#L73) · contextualTool | 现有 Subagent 默认清单无 Agent，缺 Host 工厂时构造 unavailable 工具；目标改为候选包含、按实际剩余额度与可信能力过滤，原始显式空配置语义不变 |
| [tool/agent/SubagentExecutionContext.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/agent/SubagentExecutionContext.java#L30) · root；[SubagentExecutionService.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/agent/SubagentExecutionService.java#L157) · requireNoCycle/requireNotSelfBound | 根 depth=0、祖先集含当前 Agent；源码仍拒自身绑定及祖先 ID。自身默认免绑定委派是另一个已定待实现目标，不把这些拒绝继续当有效目标；更大深度不自动允许非自身跨 Agent 祖先回指 |

配置不进入模型参数、Agent 目录或数据库身份副本；每次新建 Session 与内部关系仍走统一历史的原六字段。未运行 Java 或真实模型测试，没有新增 Maven 依赖；同轮独立持久化缺口见[统一历史证据](../01-CampusClaw多Agent运行时/unified-event-persistence-evidence.md#session-kind-evidence)。
