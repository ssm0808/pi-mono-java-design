# CampusClaw 设计仓工作指引

## 目标类图设计方法

### 适用时机

- 当一个设计涉及多个分层、扩展点、组合关系或类生命周期，且只用文字不容易看清整体结构时，主动提供目标类图。
- 设计文档只提供“推荐目标类图”。当前实现统一用源码证据表和差距说明表达，不维护当前实现类图；迁移对比也使用差距表，不再增加现状类图。
- 单类修改、简单字段增删或不涉及结构关系的设计不强制使用类图。

### 必须表达的关系

- 优先展示 Web/API 边界、Application Service、领域或核心抽象、Adapter 与持久化/运行时边界。
- 标明关键接口、实现类、组合或聚合、多重性和主要依赖方向；不要把类图画成只有类名的目录。
- 显式检查 Controller 越层、DTO/VO 穿透、可变对象泄漏、重复职责、隐藏中央分支和依赖环。
- 区分 Spring 单例、请求范围快照、Session 执行对象和持久化对象；生命周期会影响并发或一致性时必须说明。
- 对清单与执行、预览与权威记录等需一致的行为，画出共享的解析快照或权威对象，避免两条路径各自重新解析。
- 共享解析快照只固定结构、对象身份和相应元数据。变更操作仍必须在所属事务或锁内重新检查可变权威状态，不把清单预览的可用性当作最终准入结果。

### 可读性和落地

- 目标类图只保留帮助决策的结构骨架；对重复的 Contributor、Handler 或 Adapter 可以分组汇总，并用表格列出精确映射。
- 图过密或跨层连线过多时，拆成总览类图和子域类图，不通过缩小文字强行塞入一张图。
- 每个 target-only 类或关系都必须明确标识，并将目标类图中的核心依赖转换为实施切片和验收项。
- 类图后的文字优先解释“为什么这样分层”、“避免了什么依赖或一致性问题”和“实现时先落哪个骨架”，不重复朗读图中类名。

## Agent Runtime 参考基线

### 适用范围

设计、评审或修改以下内容时，必须应用本节：

- Agent Loop、Turn、Step、Message 和 Tool 生命周期；
- Session 上下文、分支、压缩、持久化与恢复；
- Provider 流式适配和 Agent 领域事件；
- HTTP、SSE、WebSocket、JSONL、CBOR 等运行时传输契约；
- mate-service 公共 Chat API、浏览器实时展示和断线对账；
- 多 Agent 的父子 Session、Thread 或子 Agent 事件投影。

### 基线使用原则

- 五个基线是分层证据集，不是同层、同权重的竞品列表，不得以“多数实现如此”代替设计理由。
- 先确定待决策属于 Runtime 内核、Provider 适配、公共 API、客户端展示还是持久化层，再选择对应主基线。
- 传输格式不等于事件语义。比较 SSE、WebSocket、JSONL 或 CBOR 时，必须另行比较事件作用域、权威边界、持久化、排序、背压和断线恢复。
- 必须区分 Provider 原始增量、Harness 内部事件、公共 API 事件、客户端 preview 和持久化权威记录，不得将它们合并为一层。
- 每份代码对齐设计必须记录实际分析的 commit、仓库相对路径和符号。下面的固定 commit 是已确认的参考点，不得在未记录的情况下静默漂移到新版本。
- 公开文档只能证明公开契约；没有服务端源码时，不得据此推断内部数据表、调度器、ID 算法或持久化实现。
- CampusClaw 的公司认证、租户隔离、凭据传递、审计、`ResultBean` 和数据保留要求是产品约束；不得因参考基线没有对应概念而删除。

### 一级基线

#### pi：Runtime 内核与 Session 语义

- 上游仓库：`https://github.com/badlogic/pi-mono.git`；固定源码基线：`5cd93f688aaab89dbb6dfa4aca535f21796ae185`。
- 使用范围：Agent Loop、Message/Tool 生命周期、Steer、FollowUp、Abort、Session 分支、压缩和最终消息持久化。
- 必读证据：
  - `packages/ai/src/types.ts`：`AssistantMessageEvent`；
  - `packages/agent/src/types.ts`：`AgentEvent`；
  - `packages/agent/src/agent-loop.ts`：`streamAssistantResponse`；
  - `packages/coding-agent/src/core/agent-session.ts`：`_handleAgentEvent`；
  - `packages/coding-agent/src/core/session-manager.ts`：Session Entry 树和当前分支恢复；
  - `packages/protocol/src/schemas.ts`：`TranscriptProgressSchema` 和 `SessionSnapshotSchema`；
  - `packages/server/src/sessions.ts`：`handleRuntimeEvent` 和 `broadcastSnapshot`。
- 设计要求：只要以 pi 为迁移或行为基线，就必须提供 pi 源码证据，不得只引用二手设计文档。
- 不得直接照搬：pi 的进程内事件、CLI JSONL、本地 Session 文件和传输中立 CBOR 协议不等于 CampusClaw 的企业 HTTP 公共契约。

#### Claude Managed Agents：公共 Session API 与断线恢复

- 事实基线：Anthropic Managed Agents 官方公开文档，核对日期 `2026-09-01`；没有可归因的公开服务端源码 commit。
- 官方入口：
  - `https://platform.claude.com/docs/en/managed-agents/events-and-streaming`；
  - `https://platform.claude.com/docs/en/api/beta/sessions/events/list`。
- 使用范围：提交事件与读取流分离、Session/Thread 事件流、持久化 Event History、preview 对账和断线恢复。
- 已确认的公开语义：`event_start/event_delta` 是 best-effort 临时 preview，不持久化、不重放；完整 `agent.message` 是权威记录；断线后重开流并查询 Event History 对账。
- 不得直接照搬：Anthropic 的 Agent、Environment、Vault、Memory Store、Thread 资源和 beta 事件名不是 CampusClaw 已确认目标模型。

#### Codex harness：Provider 适配与 Turn/Item 生命周期

- 上游仓库：`https://github.com/openai/codex.git`；固定源码基线：`d58d0e5841e0de08e251673db2d5af8cf3a1ad51`。
- 官方入口：`https://learn.chatgpt.com/docs/app-server`。
- 使用范围：Provider Responses SSE 解析、typed `ResponseEvent`、Agent 领域事件投影、Turn/Item 生命周期和客户端通知。
- 必读证据：
  - `codex-rs/codex-api/src/common.rs`：`ResponseEvent`；
  - `codex-rs/codex-api/src/sse/responses.rs`：`process_responses_event`；
  - `codex-rs/app-server-protocol/src/protocol/common.rs`：`ServerNotification`；
  - `codex-rs/app-server-protocol/src/protocol/event_mapping.rs`：内部事件到 App Server 通知的映射；
  - `codex-rs/app-server/README.md`：Thread、Turn、Item 和通知顺序。
- 设计要求：学习“Provider 原始增量 → typed event → 稳定 Agent 生命周期”的分层，不得因底层是 OpenAI Responses SSE 就把 `response.*` 直接暴露为 CampusClaw 公共契约。
- 不得直接照搬：Codex App Server 的 JSON-RPC、JSONL/WebSocket/Unix socket 传输和 Codex 专属 Item 类型。

### 二级对照基线

#### OpenCode：多客户端实时事件与可恢复 Session 流

- 上游仓库：`https://github.com/anomalyco/opencode.git`；固定源码基线：`849c2598abc7d2b40261e74b5826bc74ffc78308`。
- 官方公开入口：`https://opencode.ai/docs/server/`。
- 使用范围：实例级 live event bus、多客户端通知、Session durable event stream、按 sequence 回放和 live/durable 事件分类。
- 必读证据：
  - `packages/opencode/src/server/routes/instance/httpapi/handlers/event.ts`：实例级 SSE 与 `server.connected`；
  - `packages/protocol/src/groups/session.ts`：`session.history` 和 `session.events`；
  - `packages/schema/src/session-event.ts`：`DurableDefinitions`、`Text.Delta`、`Reasoning.Delta` 和各类 `Ended` 事件。
- 证据边界：当前官方 Server 文档公开的是 `/event` 实例级 SSE；固定源码中的 `/api/session/:sessionID/event?after=...` 属于 v2 源码证据。在它进入公开稳定文档前，不得将其描述为 OpenCode 已稳定发布的公共契约。
- 不得直接照搬：向企业浏览器暴露未按租户和 Session 投影的全局事件总线。

#### DeepSeek Harness：完整事件溯源上限

- 上游仓库：`https://github.com/deepseek-ai/deepseek-harness.git`；固定源码基线：`0a53fb55bea101816fa226bb964ae2bed71c343b`（`dsh-0.1.2-alpha.2`）。
- 使用范围：append-only `SessionEvent` 日志、连续 sequence、token 级回放、日志派生模型历史、WebSocket Remote Journal 的重连和 gap repair。
- 必读证据：
  - `packages/core/agent-loop/src/agent.ts`：`AgentLoop.step`中 `assistant/chunk` 与 `assistant/message` 追加；
  - `packages/core/session/src/types.ts`：`SessionEventMap`；
  - `docs/subsystems/session.md`：派生历史与 durability contract；
  - `packages/api/session-controller/README.md`：`SessionEventStream` 与断线 gap repair；
  - `packages/api/gateway/README.md`：WebSocket Remote stream 和 `RemoteJournalStream`。
- 证据边界：该固定版本为 alpha；使用它时必须标注成熟度，不得将未稳定的存储格式当作行业定论。
- 不得默认照搬：持久化每个 `assistant/chunk`。只有在产品明确需要 token 级完整重放，并评估存储量、写放大、隐私、审计、保留周期和版本兼容后，才能将它提升为目标设计。

### 按问题选择基线

| 设计问题 | 主基线 | 辅助对照 |
|---|---|---|
| Agent Loop、Tool Loop、Steer、FollowUp、Abort | pi | Codex harness、DeepSeek Harness |
| Provider 流式事件归一化 | Codex harness | pi、DeepSeek Harness |
| Session 分支、压缩和上下文重建 | pi | DeepSeek Harness |
| 公共 HTTP 事件提交和读取 | Claude Managed Agents | OpenCode |
| SSE preview、权威消息和断线对账 | Claude Managed Agents | OpenCode、pi SessionSnapshot |
| 多客户端订阅与 sequence 回放 | OpenCode | Claude Managed Agents、DeepSeek Harness |
| token 级日志和完整事件溯源 | DeepSeek Harness | OpenCode |
| Thread/Turn/Item 客户端生命周期 | Codex harness | Claude Managed Agents |

### 对 CampusClaw 的默认参考姿势

- Runtime 内核优先保持 pi 行为语义，任何差异必须分类为产品约束、安全加固或架构变更。
- Provider 增量先转换为 CampusClaw 领域事件，再投影到公共 API；不默认字节透明转发 Provider 事件。
- 临时 delta 默认用于实时 preview，完整 Assistant、Tool Result 和经确认的领域 Entry 才作为权威恢复记录。
- 写请求已被接受后，不得因观察流断开而自动重放写请求；必须通过持久化历史或可恢复读流对账。
- 如果提案引入“提交与观察分离”、Session 读取流、`afterEntrySeq` 或 token 级持久化，必须明确标注为已实现行为、已确认目标设计或 target-only 方案，不得混写。

### 基线更新与完成检查

- 使用比上述固定 commit 更新的源码时，在当次设计文档中同时记录新 commit、旧 commit、变化的路径/符号和影响的设计结论。
- 引用 Claude Managed Agents 或其他托管产品时，重新核对官方文档，并在设计文档中记录核对日期。
- 在结论中分别列出已观察源码行为、公开契约、CampusClaw 目标决策与具体设计理由。
- 若某基线的相关部分已废弃、尚未公开或仍处于 experimental/alpha/beta，必须明确报告，不得以稳定能力表述。
