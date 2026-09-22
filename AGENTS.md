# CampusClaw 设计仓工作指引

## 按模块维护设计与 Agent 架构对比

本节版本：1.0.0；2026-09-14。

- CampusClaw 设计按模块长期维护；模块以职责、权威状态和依赖边界划分，不以一次需求、一次会话或一个 PR 作为长期目录边界。模块入口与所属专题统一登记在根 README 的模块索引，沿用现有专题路径，避免为整理目录破坏链接和生成脚本。
- 每个模块指定一份主设计，集中描述职责与非职责、入口与依赖、当前目标、关键流程与生命周期、状态及一致性边界、源码证据与实现差距、设计理由与代价、实施切片和验收。跨模块规则由所属模块唯一维护，其他模块引用；HTTP 精确模型仍遵守各专题既有权威顺序。
- 独立维护 [Agent 架构对比](01-总体架构/07-Agent架构对比/README.md)，按模块比较 CampusClaw 与适用 Agent 基线。它解释同一架构问题上的基线做法、CampusClaw 设计与实际实现、差异原因、收益、代价和适用边界，不复制模块主设计、接口报文或目标类图。
- 每次新增或调整模块设计时，同步更新受影响的对比条目、源码核验范围和模块导航；设计决策已定但无对应实现时标记 待实现，不能等待面试准备时再补差异理由。纯排版等不影响架构结论的修改，在交付说明中注明对比无变化即可。
- 对比采用文档中的条目格式和独立状态维度。每个实现结论绑定实际分析的 commit、仓库相对路径及符号；基线登记不等于源码核验，旧提交的差距不自动延伸为最新实现缺陷。未核验必须明示，不用“无差异”或“未实现”代替未知。
- 意图明确的差异归为产品约束、安全加固或架构变更，并记录具体理由与代价；尚未解释的源码差异只登记为待核验差距，不替它编造设计意图。不要求每个模块与全部五个基线机械对齐，基线选择遵守下文的分层原则。
- 对比条目保留可用于设计答辩和面试的简要讲解：解决什么问题、参考了什么、哪里不同、为什么、代价是什么、目前实现到哪里。讲解必须能回到证据和验收，不宣称未经验证的性能、可靠性或产品能力。
- 模块主设计变更、对比结论变更分别更新所在文档版本。图形沿用下文的 PlantUML 与全局目标类图规则；对比通过链接复用主图，不另建一套当前实现类图。

## 正文与版本记录

本节版本：1.1.0；用户确认日期：2026-09-18。

- 未实现功能统一标记“待实现”；尚未核验源码的状态写“未核验”。已实现功能与后续待实现增量分别记录，禁止用历史标签推断当前实现状态。PlantUML 保持英文 ASCII，使用 `Pending implementation` 对应“待实现”；源码核验和测试验收分别注明提交及范围。
- 正文直接描述当前有效方案，保留必要的设计理由、源码依据、实现差距和验收要求。
- 每项规则集中定义，其他专题引用；历次候选、逐轮确认和方案撤销过程通过 Git 历史追溯。
- 已有版本历史每条只用一句话说明变更，例如“明确 Thinking 展示模型返回的原始推理”。
- 重大架构取舍需要长期解释时单独维护 ADR；不把会话记录或交付过程写入设计正文。

## 设计仓交付方式

本节版本：1.0.0；用户于 2026-09-07 确认，替代此前通过 PR / Draft PR 交付设计变更的安排。

- 本规则仅适用于 `pi-mono-java-design` 设计仓，不改变实现仓的 PR、评审和 CI 要求。
- 设计任务完成并通过相关校验后，直接提交或合入 `main`，推送 `origin/main`；默认不开 PR，也不等待用户另行合并。用户对当次任务有明确例外时遵从当次要求。
- 先同步最新主线，只提交本任务的明确文件；保留无关的工作树修改。需要隔离时仍可使用工作树，但最终交付到主分支。
- 不强制推送，不绕过分支保护；推送受阻时报告具体未完成步骤。分支和工作树清理须另有明确授权，不因已合入而自动删除。

## 时序图维护

本节版本：1.0.0；用户确认日期：2026-09-22。

- 执行全局 `Sequence Diagram Presentation` 规则，具体写法与工具入口见[时序图规范](时序图规范.md)。新增与修改时序图均纳入仓库级检查，不只整理当前专题。
- 改图前说明其单一场景和起止，检查原图对应正文与源码证据；保留稳定块名、业务边界及原实现状态，将实现细节交给图后说明或下钻链接。
- 运行 `python3 scripts/check-diagrams.py --render` 检查格式、图源/SVG 同步和链接；复杂度提示逐项解释或调整，不为通过数量检查而合并不同权威职责。
- 运行 `python3 scripts/render-diagram-index.py` 更新图索引，再逐图查看原尺寸和文档宽度。规则、机械检查与视觉检查共同交付，不能用其中一项替代其他两项。

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

- 全局目标类图是主图：在一张图中连贯展示入口、应用编排、核心抽象、扩展实现和运行时/持久化边界，不能让读者拼接多张局部图才能理解整体设计。
- 目标类图只保留帮助决策的结构骨架；对重复的 Contributor、Handler 或 Adapter 可以分组汇总，并用表格列出精确映射。
- 图过密时先合并重复实现、减少字段和方法细节，保留主图的完整职责链；不得把 Handler 与业务服务、执行协调器与 Repository 合并为掩盖分层关系的大框。子域类图只作下钻补充，不得替代或削弱全局主图。
- 跨模块共享同一结构时引用同一份全局图。局部契约或字段调整只改相关节点和关系，不顺带重构整张主图；恢复旧图风格时不得恢复已撤销的业务语义或人员分工。
- 提交前必须实际查看生成的 SVG，并与已确认的完整版对照，检查职责链、文字、箭头、交叉和标签遮挡；同时检查原尺寸与文档缩放视图，并提供原尺寸入口。ASCII、XML、生成同步及链接校验不能替代视觉验收。
- 每个 待实现 类或关系都必须明确标识，并将目标类图中的核心依赖转换为实施切片和验收项。
- 类图后的文字优先解释“为什么这样分层”、“避免了什么依赖或一致性问题”和“实现时先落哪个骨架”，不重复朗读图中类名。

本节全局主图与视觉验收要求由用户于 2026-09-07 再次确认；保留旧设计分支 `06bea56` 的方法，不沿用其已被后续决定替代的 Help 语义和人员分工。

## Agent Runtime 参考基线

本节更新规则版本：1.1.0；用户确认日期：2026-09-17。

### 每次先更新基线

- 每次回答 Agent 基线相关问题或进行相应设计比较，先确认相关上游的默认分支并 fetch 最新 HEAD，再读取问题涉及的源码；记录查询日期、分支、完整 commit、仓库相对路径和关键符号。只有用户明确指定历史版本时才以该版本为主。
- 下列固定 commit 是历史证据点，不再限制后续回答使用旧版本；本次最新提示词核验见 [计划模式证据 §10](01-总体架构/06-CampusClaw计划模式/source-evidence.md#10-两份模式提示词的最新上游核验)。最新源码不等于稳定发布，必须保留 alpha/beta/experimental 边界。
- 不用本地 HEAD、缓存或既有登记冒充最新；优先隔离 fetch/read，不覆盖用户工作树。无法联网或取回时明确报告尚未更新，不能静默退回旧基线并称为最新。
- 托管产品以当次重新读取的官方文档为准，记录日期，不推断未公开实现。源码升级只更新已实际核对的专题结论，同时记录旧、新提交及变化影响；不把其他模块的历史证据批量替换为新 SHA。
- 基线比较服务于用户当次目的；设计讨论按设计任务处理，不自动转成学习课程或写学习笔记。

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
- 每份代码对齐设计必须记录实际分析的 commit、仓库相对路径和符号。下面的 commit 保留历史证据归属；后续按“每次先更新基线”取得新快照，并显式记录升级范围。
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
- 如果提案引入“提交与观察分离”、Session 读取流、`afterEntrySeq` 或 token 级持久化，必须明确标注为已实现行为、已确认目标设计或 待实现 方案，不得混写。

### 基线更新与完成检查

- 每次先取得相关基线的最新源码；在当次设计文档中同时记录新 commit、旧 commit、变化的路径/符号和影响的设计结论，不改写未重核验的历史证据。
- 引用 Claude Managed Agents 或其他托管产品时，重新核对官方文档，并在设计文档中记录核对日期。
- 在结论中分别列出已观察源码行为、公开契约、CampusClaw 目标决策与具体设计理由。
- 若某基线的相关部分已废弃、尚未公开或仍处于 experimental/alpha/beta，必须明确报告，不得以稳定能力表述。
