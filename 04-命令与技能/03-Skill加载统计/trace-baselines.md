# Skill 调用观测与统计基线

版本 1.2.0 · 2026-09-16。本页维护基线概览；Codex 完整机制见[专项研究](codex-skill-counting.md)，CampusClaw 已确认目标由[主设计](README.md)维护。研究事实不代表目标方案已经实施。

## 1. 结论

Codex 固定基线已经实现 Skill 调用计数器及带 Thread/Turn 关联的分析事件。OpenCode 把 Skill 加载建模为显式工具调用，工具记录可用于派生调用统计。pi 的所查路径提供 Skill 展开和通用工具生命周期，未发现对应的 Skill 专用计数器。三者不是同一种统计口径，也不能证明已有统一的“Skill 业务执行成功次数”。

Trace 表示一次执行及其步骤关系，span 表示其中一个操作；metric 是聚合指标，analytics event 是分析事实。计数器、分析事件和工具历史都可提供观测依据，但不能统称为已经持久化、无损、可重放的 trace。

## 2. 固定源码与已观察行为

沿用设计仓固定提交，不升级其他模块的核验范围：

| 基线 | 完整提交 | 本页范围 |
|---|---|---|
| Codex | `d58d0e5841e0de08e251673db2d5af8cf3a1ad51` | Skill 调用认定、计数器、分析事件与队列 |
| OpenCode | `849c2598abc7d2b40261e74b5826bc74ffc78308` | Skill 工具、工具调用成功/失败记录 |
| pi | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` | Skill 命令展开及 Agent 工具生命周期 |

### 2.1 Codex：已实现专用计数与关联事件

| 源码路径 / 符号 | 已观察行为 | 解读边界 |
|---|---|---|
| `codex-rs/core/src/skills.rs:38` · `emit_explicit_skill_invocations` | `codex.skill.injected` 加 1；标签含 status、skill、invoke_type=explicit、plugin_id、model_slug、reasoning_effort。成功注入的 Skill 另提交分析事件 | 显式计数器包含注入失败 status=error；不能不筛选状态就称成功次数 |
| `codex-rs/core/src/skills.rs:121` · `maybe_emit_implicit_skill_invocation` | 识别隐式调用；Turn 内 HashSet 按 Skill 身份去重，然后加计数器、发分析事件 | 属于该隐式入口的 Turn 去重，不是全部入口的根任务全局去重 |
| `codex-rs/skills/src/invocation.rs:26` · `detect_implicit_skill_invocation_for_command`；`codex-rs/ext/skills/src/invocation.rs:17` | 静态识别读取已知 Skill 文档或运行 Skill scripts 下的脚本；关联可用 Skill 快照 | 不累加文件行覆盖，不证明正文全部读完或脚本成功 |
| `codex-rs/core/src/tools/handlers/unified_exec/exec_command.rs:231` | 实际命令执行之前调用隐式识别 | 这是尝试/识别信号，不能据 status=ok 推导命令结果成功 |
| `codex-rs/ext/skills/src/tools/read.rs:277` · `ReadTool.handle` | 请求主提示资源、没有 cursor、成功构造首屏输出时发隐式调用事件；允许 next_cursor 非空，续页不在此分支计数 | 首屏加载即可形成信号，不要求 SKILL.md 全文覆盖；辅助资源不在此分支计数 |
| `codex-rs/ext/skills/src/tools/mod.rs:127` · `SkillAnalytics.track_skill_invocation` | 为资源 Skill 写入计数器及分析事实 | 计数器在调用点递增，后续分析事件去重不会回退计数器；两者不能承诺恒等 |
| `codex-rs/analytics/src/reducer.rs:1211` · `ingest_skill_invoked` | 输出 `event_type=skill_invocation`，包含 skill_id、skill_name、thread_id、turn_id、invoke_type 等；资源类隐式事件按 Turn/resource 去重 | 是分析事件，不是源码已证明的标准 Skill span 或数据库报表 |
| `codex-rs/analytics/src/client.rs:185` · `AnalyticsEventsQueue.try_send` | 有界队列 try_send 失败时丢弃分析事件并记日志 | 不能把这一发送链称作无损统计账本 |
| `codex-rs/ext/skills/src/telemetry.rs` · `SkillTurnMetrics.finish` | 记录 `codex.skill.turn.duration_seconds`，按本 Turn 使用的 plugin 与模型/状态归因 | 这是 Turn 总耗时的归因，不是单个 Skill 的独立执行耗时 |

分析事件典型字段已经由 `codex-rs/analytics/src/analytics_client_tests.rs:4159` 的 `reducer_ingests_skill_invoked_fact` 校验。本次读取该测试作为事实证据，没有重新运行 Codex 测试或验证其服务端存储。

### 2.2 OpenCode：显式 Skill 工具提供可计数事实

`packages/opencode/src/tool/skill.ts:12` 的 `SkillTool` 定义工具 `skill`。固定提交的参数是 `name`；execute 解析 Skill、检查权限、返回正文，并在 metadata 中保留 name 和 dir。

`packages/opencode/src/session/processor.ts:160` 的 `completeToolCall` 将工具 Part 更新为 completed，保留调用 input、output、metadata 和起止时间；失败分支记录 error。`tool-call` / `tool-result` 按调用 ID 关联。由此可以筛选 `tool=skill` 并按调用身份、名称、状态聚合，这是对已观察记录的可行推导。

本次未发现或核验 OpenCode 已提供“累计/按日 Skill 排行 API”，也未把工具 Part 当成 OpenTelemetry span。[当前官方 Skill 文档](https://opencode.ai/v2/docs/skills)于 2026-09-15 核对，使用参数 id；它与固定源码的 name 不同，不能混写成同一版本的精确 Schema。本页统计结论以固定源码为证据。

### 2.3 pi：可用事件扩展，但没有在所查路径提供专用计数

`packages/coding-agent/src/core/agent-session.ts:1320` 的 `_expandSkillCommand` 读取正文、去 frontmatter 并展开成模型输入；该函数没有 Skill 统计写入。

`packages/agent/src/types.ts:428` 的 `AgentEvent` 提供 message 与 tool_execution_start/end，工具事件具有 toolCallId、toolName、args/result、isError。可以在应用层识别受管 Skill 访问，但这是 CampusClaw 需要设计的归因逻辑，不能说 pi 已经实现 Skill 调用统计。此核验不覆盖整个 pi 的所有扩展或遥测。

### 2.4 通用 tracing 参照

[OpenAI Agents SDK tracing 官方文档](https://openai.github.io/openai-agents-python/tracing/)于 2026-09-15 核对：Runner、Agent、模型、函数工具等形成 trace/span，并允许 custom span。它证明通用工具可跟踪，不证明任意 SKILL.md 都会自动成为 Skill span，也不作为 Codex harness 私有实现的证据。

## 3. 从设计仓推导 CampusClaw 的边界

设计依据为 `pi-mono-java-design@761b7640f76b74162423c0372496cdef0b88d708`，其中 M05/M06/M03 和元数据职责约束是推导起点；产品目标与实现对照分开记录。

| 所属设计与具体位置 | 已有约束 | 对统计的影响 |
|---|---|---|
| `04-命令与技能/02-技能命令/README.md` §4；Slash 主设计 §3.4 | Skill 通过不可变快照及共享消息受理链执行；内部保留恢复所需正文，公共投影保留原调用 | 显式选用在 Skill 应用服务可观测，无需假装它经历 Read |
| `01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md` §2、B09/B14 | sourceEventId 关联原 user.message，确认续跑不换根；完整事件权威、preview 不持久化 | 先复用业务关联，不能为每次采集生成一个无关联 UUID 冒充任务身份 |
| `01-总体架构/02-CampusClaw工具系统/built-in-tool-contracts.md` §1、§2.2、§7 | Read 是通用工具；模型通过 offset/limit 分页；activate_skill 属于删除边界 | 不为统计改成 Skill 专用 Read，也不因 OpenCode 有 skill 工具就直接恢复新工具 |
| `01-总体架构/05-CampusClaw调用日志/README.md` §3.2 | 现有简化日志未建设 traceId/MDC、完整成功访问日志或采集平台 | 不能宣称已有 trace 库可直接 COUNT；增加 tracing 属于架构扩展，应单独识别依赖、采样、权限和保留代价 |
| `03-数据与存储/02-Agent元数据GaussDB/README.md` §2.2、§4.1、§5.3 | Skill 身份由所属元数据服务产生，绑定引用它；该专题不新增多租户字段 | 身份复用；“本专题不加租户字段”不等于统计已获部署级访问授权，权限仍需独立确定 |

## 4. 推荐推导顺序

1. **先定义可观测的 Skill 调用事实。** 区分显式选用、隐式识别、注入/交付成功与失败，关联既有 Session、根消息及适用的 Tool Call。Skill ID 来自已验证快照。实际 trace/span ID 可作为诊断关联，不能替代业务身份；本页不新增公开 trace Header 或事件 Schema。
2. **再定义投影。** 调用次数按合格调用身份计数；采用任务数按 `(根任务身份, skillId)` 去重。一次任务调用某 Skill 三次，两个指标分别可以是 3 和 1。存储若过早按任务去重，就无法恢复调用次数；仅保留无身份计数器，也无法计算采用任务数。
3. **最后选持久化方式。** 先核对能否复用已有权威执行记录及其索引、保留策略，再决定是否需要独立调用事实表与汇总表。仅有累计/日加一的两张表不能提供追溯和重新去重，但这不意味着必须照搬 PR 的逐次全文事件表。
4. **明确统计可靠性。** Trace 可能被关闭、采样、丢弃或提前过期。全量可靠记录可以作为报表来源；采样 trace 的条数只能描述样本，不能直接冒充完整累计。观测、指标和权威业务记录应在同一语义源上关联，可靠性要求不同则分别投影。

主设计采用按根执行去重的使用信号：usageCount 对同一 sessionId/rootEventId/skillId 至多计 1，显式与 Read 统一，部分正文即可。三张统计表独立短事务，失败不阻断主执行但可能漏计；首版 scope=runtime，累计及近 7/30 天按首次入账信号归日。该目标已确认、target-only；它不提供逐次 Read 数，也不能证明模型实际采用。Codex 的不同入口去重和异步投递仅是参考，不是本产品的完整口径。

## 5. 验证范围

已逐段读取所列固定源码、Codex 测试样例及设计仓相关约束，并核对两份官方文档。未运行三个基线、没有访问其分析后台、没有验证其服务端数据库或新 CampusClaw 统计 SQL。本页没有新增 Maven 依赖；目标类图与来源提交时序由主设计统一维护，本页不复制另一套当前实现图。
