# 工具系统源码证据

[返回工具系统主设计](README.md)

版本：1.2.0；整理日期：2026-09-18。以下结论只适用于各行记录的源码提交，保留原核验范围；设计仓整理基线为 `6026ba48`。旧提交差距不代表最新实现状态。活动工具的当前主线状态见 §4。

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

## 3. 工具展示名称专项（2026-09-17）

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

CampusClaw 选择在 Host 外部事件中固定展示名，是产品可读性约束和架构变更，不是照搬 pi/Claude 的既有字段。可选字段、快照存储、缺失元数据降级及公共授权投影是已确认目标，相关 Java/前端改动和端到端回归尚未执行；无新增依赖。主图分层与执行关系不变，本次只补元数据和事件字段。

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
