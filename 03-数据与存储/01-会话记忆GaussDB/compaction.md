# Session 压缩与恢复

版本：1.1.0；日期：2026-09-19。

[返回 Session 主设计](./README.md)

## 1. 职责与配置

`session.compaction.*` 是内部事件与固定实现符号；[公共事件投影](../../01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md)只输出完整 `session.compacted`，不公开摘要、内部边界或 started/failed。

压缩属于 `ManagedAgentSession`，不属于已删除的 TUI Host。默认配置沿用
`enabled=true`、`reserveTokens=16384`、`keepRecentTokens=20000`；`enabled=false` 同时关闭
阈值和溢出自动压缩。摘要瞬态重试默认开启、最多 3 次、基础退避 2000ms。手工压缩原因
`manual` 供 `/compact` Handler 使用。该命令通过通用 `POST /command` 执行，
不增加专用 Compact operation。

## 2. 触发与单次恢复

自动判定对齐 pi `agent-session.ts::_checkCompaction/_runAutoCompaction`、
`compaction.ts::estimateContextTokens/prepareCompaction/compact` 和
`overflow.ts::isContextOverflow/isRecoverableLength`：只接受当前 provider/model 且晚于最新
压缩边界的 Assistant。优先使用最后一条有效 Usage；不可用时估算后续消息，文本和 JSON
参数使用 `ceil(chars/4)`，image 按 4800 chars。只有 Token 严格大于
`contextWindow-reserveTokens` 才触发阈值压缩。

正常 `STOP` 但 Usage 已越界表示模型调用成功：压缩完整上下文后保留并返回该答案，绝不
重放。`ERROR`、`LENGTH`、显式 provider overflow 或可恢复 length 才从候选中排除失败
Assistant，压缩成功后重试一次；第二次仍溢出发 `session.compaction.failed`，不再压缩重试。
从数据库恢复出的未处理失败溢出在接受下一条 prompt 前先完成恢复压缩。

模型窗口和可选输出上限从 Mate 查询后发布到 Agent 快照，字段与消费规则唯一维护于[Model 能力专题](../../02-服务与接口/03-Model/model-capabilities.md#4-可选-maxtokens-的消费规则)，该增量待实现。模型上限未知时普通 Chat 不自动填输出额度，跳过依赖该上限的 LENGTH 启发式；仍保留基于 contextWindow 的阈值及明确 overflow 信号。已知上限时按该次调用实际期望额度判断，不能忽略显式小预算而误判需要压缩。

## 3. 安全窗口与摘要

自动压缩先 prepare；没有安全可压缩窗口时静默跳过，不发送 started/failed。安全切点只允许
User 或 Assistant，ToolResult 不能成为第一条保留消息；单独超过 `keepRecentTokens` 的末条
Assistant 仍必须保留。同轮前缀单独摘要并与历史摘要合并 Usage/Cost；重复压缩更新旧摘要、
继承排序后的 `<read-files>`，并把 `firstKeptEntryId` 映射到当前上下文第一条保留消息。

摘要使用固定结构和 `<conversation>/<previous-summary>` 标签，包含 thinking 与 tool JSON
参数，单个 ToolResult 最多 2000 字符。请求不带工具、cache 为 none、使用新的 routing
session ID；历史和 turn-prefix 输出上限分别为 reserve 的 80% 和 50%，且不超过模型
maxTokens（已知时）；未知上限时保留摘要自身预算，不伪造模型能力。只对瞬态摘要失败执行有界退避。摘要为空、包含 ToolCall、失败或取消时不发布
新上下文，已经持久化的历史 Entry 一律不删除。`FileOperationTracker` 只跟踪 PascalCase
`Read`；Bash/Edit/Write 均未装配，也不参与追踪。

## 4. 持久化、取消与重载一致性

只有 prepare 成功后才投影 `session.compaction.started`。`session.compaction.failed` 固定为
`reason/willRetry/aborted/message`，其中 `aborted=true` 只表示压缩或父执行被取消；它不持久化。
`session.compaction.completed` 保存完整摘要、边界、压缩前后 Token 和本次 Usage，并原子累计
Session lifetime Usage。`willRetry=true` 时，持久化 payload 还包含不公开的
`_discardedEntryId`：它精确标识已从在线重试上下文移除、但仍留在 append-only 历史中的
`ERROR/LENGTH` Assistant。恢复投影必须排除该 ID，再加入压缩后成功的重试 Assistant，保证
在线上下文与重载上下文一致；GET Events 和 SSE 均不得输出该内部字段。旧 Entry 缺少该字段
时，只允许回退识别压缩完成前最后一条可重试 Assistant。


## 5. 固定源码证据与范围

本专题承接 Runtime HTTP 原 §2.2.1 的有效规则；不是一次重新制定压缩算法。源码核验日期为 2026-09-14，复核下列既有固定提交，不将旧提交的差距延伸为最新实现缺陷。

| 基线 | 仓库相对路径与符号 | 证据与边界 |
|---|---|---|
| pi `5cd93f688aaab89dbb6dfa4aca535f21796ae185` | `packages/coding-agent/src/core/agent-session.ts` · `_checkCompaction`、`_runAutoCompaction`；`packages/coding-agent/src/core/compaction/compaction.ts` · `estimateContextTokens`、`findCutPoint`、`prepareCompaction`、`compact`；`packages/ai/src/utils/overflow.ts` · `isContextOverflow`、`isRecoverableLength` | Runtime 内核参考：成功 STOP 保留与失败恢复分开，安全切点和有界重试。 |
| Java `bd26e7f81bac8f68be0c3523efe23b51f96c52e4` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/ManagedAgentSession.java` · `compactBeforePrompt`、`compactAfterExecution`、`runPreparedCompaction`、`finishCompaction` | 自动压缩先 prepare；只在需要恢复且压缩成功后继续一次；取消与摘要失败不替换消息。 |
| 同上 | 同目录 `compaction/SessionCompactor.java` · `decide`、`prepare`、`summaryOptions`、`summaryMaxTokens`；`CompactionProperties.java`；`CompactionTokenEstimator.java`；`CompactionPromptBuilder.java` | 默认参数、Token 估算、安全窗口、拆分摘要、请求选项和结构化摘要。 |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEntryCodec.java` · `compactionEntry`、`effectiveContextEntries`、`discardedEntryId`、`appendCompactionPayload` | 保存并按 ID 排除 `_discardedEntryId`；公共投影不带该字段。该提交公开事件名和字段仍属历史实现，不替代当前 Events 契约。 |
| 同上 | `modules/agent-core/src/main/java/com/campusclaw/agent/Agent.java` · `buildStreamOptions` | 没有调用方覆盖时将 `model.maxTokens` 传入模型请求。 |

已有实现差距证据仍保留其作用范围：`a7f78fed345a289833970cd7b78399f0e8e51d32` 对 pi 压缩规则尚不完整；`bf28e72f94f29acd316eb872a250893ed54e3632` 的在线失败候选已排除，但重载和模型输出上限仍有差距；`bd26e7f8` 已修复这两项。对应更早 PR 167 基线 `f60cc3e78bb8b700527ac082c7c8e10524ede095`、merge base `d649866a6cae967ace18ceaeb9597edd47e5721e` 仅用于追溯，不定义当前行为。

与 pi 的差异分类：公共事件隐藏摘要和内部字段属于产品约束与安全加固；持久化精确丢弃 ID、统一在线与重载上下文属于架构变更；摘要算法和单次恢复优先保持 pi 语义。该整理不引入 Maven 依赖。

2026-09-19 可选上限增量的静态源码核验见[Model 证据](../../02-服务与接口/03-Model/source-evidence.md#model-capability-evidence)：当前 Model.maxTokens 仍为 int，相关改造待实现；不升级本节其他算法和持久化历史证据。

## 6. 验收

- 成功 STOP 越界只压缩、不重试；ERROR/LENGTH 恢复最多一次，且始终保留历史 Entry。
- 输出上限未知时无自动普通 Chat 额度、无依赖该值的 LENGTH 恢复；摘要预算仍生效；已知上限与显式小额度不发生误判。
- 阈值等值不触发；旧模型或旧压缩边界的 Usage 不触发错误恢复；无安全窗口无 started/failed。
- 超大末条 Assistant、ToolResult 切点、拆分轮次、重复摘要及 Read 路径继承均符合 §3。
- 摘要请求无 tools、cache=none、独立 routing session ID，两个输出上限和瞬态重试界限准确。
- 摘要失败、空摘要、ToolCall 和取消均不发布新上下文；completed 与 lifetime Usage 同次提交。
- 对 completed → retry → reload 比较在线与重载消息集合，确认失败 Assistant 不重新出现；旧 Entry 回退范围准确。
- 公共 SSE 和 GET 均无 `_discardedEntryId`、摘要正文及内部边界；公开类型以 Events 契约为准。

## 7. 版本记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.1.0 | 2026-09-19 | 支持 Mate 快照中未知输出上限，明确普通调用、LENGTH 判断与摘要预算边界。 |
| 1.0.0 | 2026-09-14 | 将压缩算法、取消、用量与重载一致性集中到 Session 模块。 |
