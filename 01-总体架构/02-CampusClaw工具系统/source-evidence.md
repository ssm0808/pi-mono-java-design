# 工具系统源码证据

[返回工具系统主设计](README.md)

版本：1.0.0；整理日期：2026-09-14。以下结论只适用于各行记录的源码提交，保留原核验范围；设计仓整理基线为 `6026ba48`。旧提交差距不代表最新实现状态。

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
