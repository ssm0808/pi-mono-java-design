# Runtime 源码证据与实现差距

版本：1.3.0；整理日期：2026-09-19。

本文集中保存 Runtime / HTTP 主设计使用的源码观察。**每项结论仅适用于所标提交和路径**；旧实现的差距不自动延伸到当前实现。目标契约见 [HTTP 设计](chat-http-v1-design.md)，Events、Command、工具和计划模式的专项证据由所属专题维护。

本次文档整理基于设计仓 `6026ba48e58449e6d64e6e91688b04a2fdd562e2`。除 §4 所列三个文件外，本次沿用已有源码分析，不将整个 Runtime 标为重新核验。`modules/` 与 `campusclaw/` 按各条证据原路径引用，不推断二者在某一提交必然互斥；省略路径的早期记录保留其证据局限，不能作为最新源码定位。

## 1. 已分析基线

| 分析范围 | 固定提交或边界 |
|---|---|
| CampusClaw Slash 行为基线 | `c1311f69f504e7e799fa2467fd6a9d95b3f91b99` |
| CampusClaw 早期专项核对头 | `c9d858bc8261bf07f5585f545b53495bf2226a56` |
| pi-mono Slash 对比基线 | `4af9d21d3b4d664e4a29fcabfec85171077248e3` |
| CampusClaw PR 167 审查头 | `bf28e72f94f29acd316eb872a250893ed54e3632` |
| CampusClaw PR 167 对齐实现 | `bd26e7f81bac8f68be0c3523efe23b51f96c52e4` |
| pi-mono-java 字段命名核对基线 | `304eda06ff603fc9b6bbcaad0c296cc151a7defb`（`codex/runtime-http-contract-v137`） |
| pi-mono-java 凭据透传核对基线 | `320d790726a70aada6100052952d5494d2a378ac` |
| Runtime 凭据入口延迟失败复核 | `pi-mono-java@21c3f59be033e7bdd5506a2d9d48baa2581bc3c7`；`RuntimeRequestContext.mateCredentials`、`RuntimeEventService.requireCredentials`、`MateCredentials.isComplete`、`HttpMateToolClient.invokeTool` |
| Builtin 实现分析基线 | `d84dd3d6a306b7587c70b29e0100e741dacef989`；PR #210 最终实现 `9d0d76f4a571b559dc77ae52736caebbcc8fad88` 已通过 `a8192e047f4061bd385297d3dc6c4358362d0d49` 合并 |
| OpenCode 源码基线 | `849c2598abc7d2b40261e74b5826bc74ffc78308` |
| DeepSeek Harness 源码基线 | `141eb6fef83422698aef7a981029e843e8161534` |
| Codex Harness 源码基线 | `be33f80bc65159c094ecd06bf155afa3061ce23d` |
| Anthropic TypeScript SDK 源码基线 | `64a1e8e285bbcc4cef2b15ebcadccd8e5f6987ff` |
| Builtin 实现分析基线 | `d84dd3d6a306b7587c70b29e0100e741dacef989` |
| Help 元数据专项源码基线 | `d8e22562e22ac41ef4bb5cc6b36b576139417bd9`；无参、空数组与缓存迁移已确认；1.48.0 去除 command 后保留三个业务字段，仍为 待实现 |
| Command 响应复用源码基线 | `6f52fddc87a03c20916fc7b6ef1de87f6a7a8cf5`；既有 Session/Models 资源投影；源码路径与差距由 Builtin §8 维护 |
| Session Events 合并传输核对 | `918005ee8ccc88d179fc31a0de17a92b4a01383b`；对比原 `a8192e0` 的七个 HTTP/事件文件无变化，目标变化见 Session Events §4.2 |
| Session Events 历史查询补充核对 | 同一 `dfb90ca`；查询、编码、游标与 Mapper 四文件相对 `918005e` 不变，见 [历史设计](chat-events-history-design.md)；本次变更前设计 `c16ed3f904a85d01d69deb1a3575e2c52cdaa958` |
| CampusClaw PR 167 基线 | `f60cc3e78bb8b700527ac082c7c8e10524ede095` |
| CampusClaw merge base | `d649866a6cae967ace18ceaeb9597edd47e5721e` |
| CampusClaw 压缩修订前基线 | `a7f78fed345a289833970cd7b78399f0e8e51d32` |
| Session 重命名补充核对 | `pi-mono-java@510d882ca45541e0086586dab89c429c5a18cf20`；`SessionNamingService` 与 `RuntimeSessionRepository.updateName` 已实现，但只由 `/name` Command 暴露 |
| Registry 初始候选 | `0bb794f222273e12fc24fe98d6ab4e9013ac8599` |
| GET 候选实现 | `7759481a1722422395d46564129827c6ee6df204`，未发布，不能作为已上线契约 |


## 2. HTTP、Session 与上下文证据

下表中的“已实现”均指该行固定版本。公开托管产品的记录是当时公开契约；具体比较与最新核对日期见 [Agent 架构对比](../07-Agent架构对比/README.md)。

| 分类 | 证据或决策 |
|---|---|
| Command / Help / Skill 证据 | 统一引用 [Slash 源码证据](../../04-命令与技能/00-Slash-Command通用模块/README.md#2-源码证据与差距)、[GET 最新核对](../../04-命令与技能/00-Slash-Command通用模块/README.md#33-发现层证据与验收)与 [Help 专项证据](../../04-命令与技能/01-内置命令/Help-Agent使用指南/README.md#5-源码证据与设计理由)，不另复制旧 Registry 和元数据差距。 |
| 观察到的行为 | PR 167 在 `f60cc3e` 删除 `modules/coding-agent-cli/.../command/` 中 Slash Registry、`ModelCommand`、`ThinkingCommand`、`CompactCommand`、`NameCommand`，同时删除 `.../compaction/Compactor`、`FileOperationTracker` 与旧大型 `AgentSession`；该删除按包边界发生，未先迁移入口无关能力 |
| 观察到的行为 | PR 167 新增 `modules/coding-agent-cli/.../session/ManagedAgentSession.java` 和 `AgentSessionFactory.java`，但基线 Session 只持有 Runtime、入口、Agent 和工具，不包含阈值/溢出压缩、Usage 累计或 Host 无关 Slash 操作端口 |
| 观察到的行为 | pi-mono `packages/coding-agent/src/core/agent-session.ts` 基线 `5cd93f6` 中的 `compact()`、`autoCompact()`、`setModel()`、`setThinkingLevel()` 与 Session Entry 写入证明压缩及配置变更是 Agent Session 能力，不依赖终端绘制组件 |
| 观察到的行为 | pi-mono-java `a7f78fed` 已恢复超大末条消息保留，但 `ManagedAgentSession`、`SessionCompactor` 和 `ContextOverflowDetector` 尚未完整实现 pi 的成功 STOP 不重试、Usage/失效边界、recoverable length、split-turn、重复摘要、结构化请求和瞬态摘要重试 |
| 观察到的行为 | pi-mono-java `bf28e72f` 已从在线压缩候选移除可重试 `LENGTH`，但 `RuntimeEntryCodec.effectiveContextEntries` 仅按 `firstKeptEntryId` 恢复，重载会重新注入该响应；`Agent.buildStreamOptions` 也未把模型上限传给公共请求，两个 OpenAI provider 的 32000 缺省值可能与 recoverable length 判定不一致 |
| 已实现架构改造 | pi-mono-java `bd26e7f8` 在 compaction payload 内保存 `_discardedEntryId`，恢复时按 ID 排除且公共投影过滤；公共 Agent 无覆盖时显式请求 `model.maxTokens`，并由 completed → retry → reload 与大输出模型测试锁定 |
| 观察到的行为 | pi-mono `packages/coding-agent/src/core/agent-session.ts::_checkCompaction/_runAutoCompaction`、`core/compaction/compaction.ts::estimateContextTokens/findCutPoint/prepareCompaction/compact` 与 `packages/ai/src/utils/overflow.ts` 基线 `5cd93f6` 明确区分三类自动压缩，并固定安全切点、摘要选项和单次溢出恢复 |
| 观察到的行为 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ServerMode.java` 基线 285-307：当前使用 WebSocket Upgrade，其余请求交给 RouterFunctions Adapter |
| 观察到的行为 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ChatWebSocketHandler.java` 基线 115-227、422-459：v1 命令、断线生命周期和累计消息更新 |
| 观察到的行为 | `modules/ai/src/main/java/com/campusclaw/ai/stream/AssistantMessageEvent.java` 基线 44-164：结构化 provider 流事件 |
| 观察到的行为 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ServerMode.java` 基线 237-307、340-344：当前 HTTP 路由未安装入站认证 Adapter，CORS 仅放行 Authorization Header |
| 观察到的行为 | `modules/agent-core/src/main/java/com/campusclaw/agent/subagent/a2a/A2aAgentBackend.java` 基线 40-62、226-238：出站 A2A 请求已使用 `X-HW-ID + X-HW-APPKEY`，但它不是入站验证实现 |
| 观察到的行为 | pi-mono `packages/protocol/src/schemas.ts` 基线 38-45、241-258：协议 `SessionSnapshot` 顶层包含 `phase`、`thinkingLevel`、完整 `transcript`、连接相对 `attached` 和 live Runtime `locked` |
| 观察到的行为 | pi-mono `packages/protocol/src/schemas.ts` 基线 26-35：`ThinkingLevel` 取 `off/minimal/low/medium/high/xhigh/max`，表达推理强度 |
| 观察到的行为 | pi-mono `packages/coding-agent/src/core/agent-session.ts` 基线 1586-1600、1684-1730：`setModel` 校验模型凭据、持久化模型变更并按新模型能力收敛 `thinkingLevel`；`setThinkingLevel` 将请求推理强度限制到模型支持范围并持久化变更 |
| 观察到的行为 | pi-mono `packages/ai/src/types.ts` 基线 793-809 与 `packages/ai/src/models.ts` 基线 900-910：Model descriptor 包含 provider、reasoning、input、cost、contextWindow、maxTokens 等内部能力；支持的推理强度由 `off/minimal/low/medium/high/xhigh/max` 与模型映射共同决定 |
| 观察到的行为 | pi-mono-java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ChatWebSocketHandler.java` 基线 289-363：现有 WebSocket 命令支持 set model、list models 和 set thinking level；模型列表还暴露 contextWindow、maxTokens、cost 和 hasCredentials，thinking level 取 Java `ThinkingLevel` 推理强度 |
| 观察到的行为 | pi-mono-java `modules/ai/src/main/java/com/campusclaw/ai/types/Model.java` 基线 34-47 与 `ThinkingLevel.java` 基线 16-42：Java Model 同样包含 baseUrl、cost、headers、apiKey 等不适合公共 HTTP 的内部字段；Java 推理强度当前为 `off/minimal/low/medium/high/xhigh` |
| 观察到的行为 | Anthropic TypeScript SDK `src/resources/beta/sessions/sessions.ts` 基线 638-710：Managed Agents 的 Session 是控制面资源，包含 Agent 快照、环境/资源、预算/用量、标题/元数据和状态，但不内嵌 transcript 或 active Run 恢复快照 |
| 观察到的行为 | Anthropic [Session event stream](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)：Managed Agents 的交互是事件驱动；`user.message` 启动或继续工作，事件在更早事件之后排队时 `processed_at=null`，中止通过 `user.interrupt` 表达 |
| 观察到的行为 | Anthropic [Send Events API](https://platform.claude.com/docs/en/api/cli/beta/sessions/events/send)：`POST /v1/sessions/{session_id}/events` 返回服务端已接收的事件及其 `event_id`，普通 Session 交互没有独立的 Session Run ID |
| 观察到的行为 | Anthropic [Start a session](https://platform.claude.com/docs/en/managed-agents/sessions) 与 [Session operations](https://platform.claude.com/docs/en/managed-agents/session-operations)：Session 维护跨多次交互的历史，事件驱动 `idle/running/rescheduling/terminated` 状态；`initial_events` 可让新 Session 直接进入 running |
| 观察到的行为 | Anthropic [Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)：Deployment Run 是 Deployment 触发的追加记录，只跟踪 Session 创建成功或失败；成功后通过 `session_id` 转到 Session Event Stream，不跟踪 Session 执行生命周期 |
| 观察到的行为 | pi-mono `packages/coding-agent/src/core/agent-session.ts` 基线 789-805：`AgentSession.dispose()` 中止重试、压缩、分支、bash 和 Agent 运行，断开扩展并释放内存资源；它未定义 HTTP 逻辑删除或持久化 tombstone |
| 观察到的行为 | pi-mono `packages/coding-agent/src/modes/interactive/components/session-selector.ts` 基线 598-630：交互模式删除直接将 Session JSONL 移入回收站，失败时回退为 unlink；这是本地文件行为，不是服务端删除事务 |
| 观察到的行为 | pi-mono-java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/SessionPool.java` 基线 143-157、204-274：`remove()` 只从内存 Map 移除并关闭 `SessionManager`；JSONL 可在后续创建时恢复，闲置淘汰也只释放内存对象 |
| 观察到的行为 | pi-mono-java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ChatWebSocketHandler.java` 基线 168-210 与 `modules/agent-core/src/main/java/com/campusclaw/agent/AgentSession.java` 基线 165-177：断连或 abort 能停止流和子 Agent，但当前没有 DeleteSession HTTP 操作 |
| 观察到的行为 | pi-mono `packages/coding-agent/src/core/agent-session.ts` 基线 609-680、1063-1074、1116-1273：`prompt` 构造文本和可选 inline image 的 UserMessage，等待 Agent 执行，并在 `message_end` 将消息追加到 SessionManager；没有独立 HTTP Run 资源、`run_id` 或持久化幂等结果 |
| 观察到的行为 | pi-mono `packages/agent/src/types.ts` 基线 430-443 与 `packages/agent/src/agent-loop.ts` 基线 767-795：`AgentEvent` 将 `message_start/update/end` 和 `tool_execution_start/update/end` 分层；工具执行结束后再生成并发送 ToolResult Message |
| 观察到的行为 | pi-mono `packages/coding-agent/src/core/agent-session.ts` 基线 781-806：Tool execution start/update/end 继续传给扩展层；CampusClaw 将 update 收窄为不含参数、可丢弃的 `tool.execution.delta`，并以持久化 `tool.result` 承载权威结果 |
| 观察到的行为 | pi-mono `packages/coding-agent/src/core/agent-session.ts` 的 `PromptOptions` 基线 2629-2649：单次 prompt 可带 images；`expandPromptTemplates`、`streamingBehavior`、`source` 和 preflight callback 是 CLI/RPC Runtime 控制，不是通用业务消息字段；`model_id/thinking` 不在该参数中 |
| 观察到的行为 | pi-mono `packages/coding-agent/src/core/agent-session.ts` 基线 1336-1404、1516-1556：`steer` 在当前 Assistant Turn 和工具调用后、下一次模型调用前入队；`followUp` 在 Agent 原本将停止时入队；`clearQueue` 清空两类队列，`abort` 取消运行并等待 idle |
| 观察到的行为 | pi-mono `packages/agent/src/agent.ts` 基线 275-319、350-390、456-492：Steer/FollowUp 使用独立队列，默认 `one-at-a-time`；Steer 在 FollowUp 之前 drain；`abort` 取消当前进程内 active run |
| 观察到的行为 | pi-mono `packages/coding-agent/src/modes/rpc/rpc-mode.ts` 基线 418-430：RPC 已分别暴露 `steer`、`follow_up` 和 `abort` 命令，但没有 CampusClaw HTTP、ResultBean 或 Session scope 契约 |
| 观察到的行为 | pi-mono-java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ChatWebSocketHandler.java` 基线 199-210、275-288 与 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSession.java` 基线 165-177、240-251：WebSocket 已有 text-only `steer` 和 `abort`，Steer 当前立即写 JSONL UserMessage，Abort 级联取消子 Agent；尚无 FollowUp 命令或三个 HTTP operation |
| 观察到的行为 | pi-mono `packages/agent/src/agent.ts` 基线 347-358、486-535：`activeRun` 是进程内执行对象，同一 Agent 已有 activeRun 时拒绝新 prompt，finally 清理；它不是持久化、可查询的 RunRecord |
| 观察到的行为 | pi-mono-java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ChatHandler.java` 基线 140-160：现有 HTTP POST 直接将消息、工具开始/结束和 done 映射为 SSE；现有名称与负载较窄，目标契约重命名并补充分离的持久化 ToolResultEntry |
| 观察到的行为 | pi-mono-java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ChatWebSocketHandler.java` 基线 252-273 与 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSession.java` 基线 153-177：WebSocket prompt 只接受非空文本，先追加 JSONL UserMessage 再调用 prompt，并以 `isStreaming` 拒绝并发；没有附件 ID、Run ID 或幂等存储 |
| 已实现行为 | pi-mono-java 实现提交 `8691e880` 的 `CampusClawApplication` 和 `CampusClawCliLauncher`：默认启动 Spring Boot MVC，显式 `cli` 子命令启动非 Web CLI 上下文 |
| 已实现行为 | 同提交的 `RuntimeSessionController`、`RuntimeEventController`、`RuntimeSessionConfigurationController` 和 `RuntimeSessionControlController`：11 个已确认 HTTP+SSE operation 均已落地 |
| 已实现行为 | 同提交的 `MyBatisRuntimeSessionRepository` 与 `session_schema.sql`：Session、当前分支 Entry、严格 `entry_seq`、tombstone 和清理任务已在 openGauss 实现 |
| 已实现行为 | pi-mono-java `1f801dbb` 的 `RuntimeRequestAuthenticator`：只校验双凭据 Header 形状；真实性和授权由上游 mate-service 完成，凭据 ID 不作为 Session owner |
| 已实现行为 | pi-mono-java 实现提交 `972f98ca`：`FileAgentDirectoryResolver` 直接返回 `agent/{agent_id}/.campusclaw/` 真实运行根目录；`RuntimeEventService`、`RuntimeEventQueryService`、`RuntimeExecutionCoordinator` 分别承担事件提交、历史查询和执行协调 |
| 基线实现差异 | pi-mono-java `1f801dbb` 的 `RuntimeApiConstants` 16-18 行仍定义旧 Agent 格式和通用 `SESSION_ID_PATTERN`；`RandomSessionIdGenerator.nextId` 20-27 行仍生成无前缀的 26 位 Crockford Base32；`RuntimeSessionService.newSession` 仍调用 `setThinking(false)` |
| 基线实现差异 | 同基线 `modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql` 的 `t_sessions.agent_id` 仍为 `VARCHAR(30)`，无法存储 38 字符的新 Agent ID；实现前必须迁移为至少 38 字符，本设计推荐与元数据存储统一为 `VARCHAR(64)` |
| 历史实现差异 | pi-mono-java `1f801dbb` 的 `RuntimeWebMvcConfiguration.addInterceptors` 27-30 行曾在进入 Controller 前把认证拦截器应用到 `/campusclaw-service/v1/**` 全路径；该专项核对头 `c9d858bc` 已删除该拦截器和 `RuntimeRequestAuthenticator`，也未把相同校验搬入 Controller |
| 基线 Java 行为 | CampusClaw `c9d858bc` 的 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeRequestContext.java:45-50` 从 POST 请求读取 `X-HW-ID`、`X-HW-APPKEY`、`Authorization` 与 `access-token`；`common/client/mate/MateCredentials.java:21-90` 保存四个不透明字符串，仅在 Mate tool execute 前检查最低完整性，不解析用户凭据 ID 或 Bearer 内容 |
| 基线 Java 行为 | 同基线 `common/client/HttpMateToolClient.java:134-193` 的三个发现调用不附带凭据；`invokeTool/toHeaderInfo` 298-370 行只在实际 Mate tool execute 时发送本次执行持有的四项 Header |
| 基线实现差异 | 字段命名核对基线 `304eda06`：`RuntimeSessionController`、`RuntimeEventController`、`RuntimeSessionConfigurationController` 和 `RuntimeSessionControlController` 的映射仍使用 `{agent_id}` / `{session_id}`；`CreateSessionResponseVO`、`GetSessionResponseVO`、`AvailableModelsResponseVO`、`EventPageResponseVO`、`ControlMessageAcceptedResponseVO`、`ChangeModelRequestVO`、`UserEventRequestVO` 以及 `RuntimeEntryCodec` / `RuntimeEventProjector` 仍显式读写 snake_case。1.38 lowerCamelCase 是相对该实现的架构变更 |
| 观察到的行为 | 同基线 `modules/ai/.../AssistantMessageEvent.java` 29-56、92-117 行定义内部 `thinking_start/thinking_delta/thinking_end`；`RuntimeEventType` 13-23 行没有公开 thinking 类型，`RuntimeEventProjector.projectMessageUpdate` 128-140 行只投影文本 delta |
| 观察到的行为 | 同基线 `RuntimeEntryCodec` 35-39、211-223 行明确并实际过滤 `ThinkingContent`；当前 Runtime SSE 与 GET Events 均不披露原始思考内容 |
| 观察到的行为 | pi-mono-java `modules/agent-core/src/main/java/com/campusclaw/agent/Agent.java` 基线 183-194、218-268：`startExecution` 通过 executionLock 保证单次 current execution，并在虚拟线程执行结束时清理；没有共享数据库 active-run 唯一约束或执行任务 |
| 观察到的行为 | pi-mono `packages/coding-agent/src/core/session-manager.ts` 基线 46-156、1057-1149、1260-1303：Session Entry 使用 `id/parentId` 组成 append-only tree，`getBranch()` 返回当前 leaf 路径，`getEntries()` 返回全部 Entry；Entry 类型还包含模型、thinking、compaction、branch summary 和扩展状态 |
| 观察到的行为 | pi-mono-java `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/SessionEntry.java` 基线 18-38 与 `SessionManager.java` 基线 188-296：JSONL Entry 保留 `id/parentId/type/message`，当前恢复主要线性提取 Message；没有 HTTP 分页、`entry_seq` 或不透明 page |
| 观察到的行为 | Anthropic [List Events API](https://platform.claude.com/docs/en/api/beta/sessions/events/list)：`GET /v1/sessions/{session_id}/events` 通过不透明 `page/next_page` 分页，并按 `processed_at` 排序；公开响应没有固定快照水位 |
| 已实现行为 | GET Session Models 以 `string[]` 实时返回 Agent allowlist 与当前可用模型交集中的 `modelId` 值，不分页；目标字段 `currentModelId` 允许因管理面后续停用而不在 `models` 中 |
| 已实现行为 | PR 167 基线的 PUT Model 和 PUT Thinking 只允许 idle Session 并要求强 `If-Match`；成功返回完整 SessionResource 和 ETag，相同值按无变化成功返回 |
| 基线 Java 行为 | `pi-mono-java@510d882ca45541e0086586dab89c429c5a18cf20` 的 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/service/command/SessionNamingService.java`规范化并校验名称，`service/command/contributor/NameCommandContributor.java`将 `/name` 声明为 idle/running 均可用；`persistence/RuntimeSessionRepository.java#updateName` 和 `persistence/MyBatisRuntimeSessionRepository.java#updateName` 在行锁内更新名称与版本 |
| 基线实现差距 | Java 09b32d8e 的 RuntimeSessionController 仅 create/get/delete；ConfigurationController 仍提供独立模型与思考 PUT。统一 POST、组合事务和 mode 尚待实现，详见下表专项证据。 |
| 目标设计与理由 | 统一 Session POST 复用 `/name` 的名称规范化，但组合持久化由配置应用服务协调；HTTP 适配器要求 expectedVersion；这是避免两套命名规则的架构变更及保护浏览器并发编辑的安全加固，不宣称为已实现行为 |


## 3. Runtime 装配的补充证据

Session Entry、生命周期、HTTP 入口、凭据和字段命名的事实已集中在 §2。装配专题继续引用 [工具源码证据](../02-CampusClaw工具系统/source-evidence.md)和 [Slash 源码证据](../../04-命令与技能/00-Slash-Command通用模块/README.md#2-源码证据与差距)，避免在 Runtime 总览重复维护旧目录、硬编码工具和 Registry 差距。

## 4. Session 创建与 HTTP 入口核对

实际分析 `pi-mono-java@f61906b9136246ca60f333704b6fc92b5420d0ec`。与旧证据表分别记录，不覆盖未检查的其他模块。源码前缀为 `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/`。

| 路径与符号 | 已观察行为 | 设计边界 |
|---|---|---|
| `runtimeapi/session/RuntimeSessionService.java` · create/newSession/get/delete | create 校验目录和默认模型后持久化 idle Session；不创建 Agent 执行对象，thinking 初始为 true；get 查询持久化资源；delete 调用 beginDeletion | 创建与执行装配分开；Agent.mode 复制仍按元数据与计划专题标记 待实现 |
| `runtimeapi/web/RuntimeSessionController.java` · create/get/delete | Controller 包装 ResultBean；GET 返回同源 ETag，DELETE 返回 204；没有统一更新路由 | 统一 Session POST 的目标与差距见 [HTTP §8.1](chat-http-v1-design.md#81-统一-session-更新源码核对) |
| `runtimeapi/web/RuntimeEventController.java` · submit/list | POST 绑定独立 SseEmitter，完成/超时/错误调用 detach；GET 接受 limit/page | 只证明入口与绑定结构，不能证明全部事件语义、数据库并发与恢复已验收 |

未运行产品集成测试。文档、精确契约和图形整理不改变运行时代码。

## 5. Session Events 固定源码核验

下表沿用 `pi-mono-java@c9d858bc8261bf07f5585f545b53495bf2226a56` 的专项分析；后续小节分别标记追加核验的提交。外部公共契约记录的核对日期为 2026-09-04，不表示在文档整理时重新检查所有页面。

| 分类 | 源码证据 | 结论 |
|---|---|---|
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java:39-91` · `RuntimeEventController.submit/list` | POST 创建 `SseEmitter` 并返回 `text/event-stream`；GET 只接收 `limit/page` |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeRequestContext.java:45-50` · `mateCredentials`；`campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/common/client/mate/MateCredentials.java:21-74` | 该基线实现把 `X-HW-ID` 作为不透明 Header 值读入执行凭据，只检查非空，不解析其业务身份 |
| 已观察实现 | `campusclaw/src/test/java/com/huawei/hicampus/claw/codingagent/runtimeapi/web/RuntimeSessionRoutesTest.java:69-93` · `createWithJwtReturnsConfirmedResultBean/getWithAppKeyReturnsEtagAndNoStore`；`RuntimeEventRoutesTest.java:88-120,193-197` · `postStreamsNamedEventsWithoutResultBean/authenticated` | 该基线测试使用 `credential-jwt`、`credential-appkey`、`Bearer opaque-token`、`opaque-appkey` 和 `opaque-access-token` 等非生产字面值；本设计复用它们作为具体示例，但不据此增加格式约束 |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventService.java:76-139` · `submit/prepareAndSubmit/acceptUserEntry` | 只接受 `user.message`，要求 idle，持久化后直接启动内部执行并返回其 EventStream |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventStream.java:22-159` · `attach/detachInternal` | EventStream 属于一次执行且最多一个 subscriber；断线会清空该流缓冲 |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventQueryService.java:53-99` · `list/pageOf` | page 只携带 afterSeq 与 thinking，没有固定历史快照水位 |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionControlService.java:59-132` · `steer/followUp/abort/prepareAbort` | Abort 是独立接口行为；Steer 与 FollowUp 使用执行内队列 |
| 已观察实现 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java:57-120` · `acceptUserEvent/listCurrentBranch` | `user.message` 在事务内追加并将 Session 标为 running；历史按 afterSeq 开放读取 |
| 目标架构 | [Events 主设计与目标图](chat-events-design.md) | 提交和对应 SSE 合并到 POST，GET 历史保留；多类型输入与请求输出绑定为 待实现 |
| 产品约束 | [Events 资源模型](chat-events-design.md#1-资源模型与职责) | 无公共 Run/Execution；mate 公共边界只暴露 `chatId` 和公共事件身份 |
| 产品约束 | `X-HW-ID` | 标识当前请求对应的用户凭据；不是公司、服务或应用调用方标识 |
| 目标设计（待实现） | Runtime 凭据 Header | `X-HW-ID`、`Authorization`、`X-HW-APPKEY` 与 `access-token` 均可缺省；Claw 只捕获并透传已提供值，不检查凭据组合或最低完整性，由 Mate execute 返回成功或失败。当前 Java `RuntimeEventService.requireCredentials`、`CallMateTool.execute` 与 `HttpMateToolClient.invokeTool` 仍有本地检查，属于待移除的实现差距 |
| 安全加固 | POST 凭据处理 | 凭据从请求读入后只在内存中保留到本次 Agent 执行结束，只在必要的实际 Mate tool execute 使用，不进入持久化、日志、SSE 或历史 |

### 5.1 事件顺序

本节核对 `pi-mono-java@a8192e047f4061bd385297d3dc6c4358362d0d49`，下表路径均相对
实现仓。与原基线 `c9d858bc8261bf07f5585f545b53495bf2226a56` 比较，下表五个文件均无
变化；新增的是对这些符号的排序证据分析，不是切换其他主题的实现结论。

| 分类 | 仓库相对路径与符号 | 已观察行为与边界 |
|---|---|---|
| 已观察实现 | `campusclaw/src/main/java/com/huawei/hicampus/claw/agent/Agent.java:294-306` · `emit` | 在当前线程依次通知 listener；这不是多来源的全局因果排序器 |
| 已观察实现 | `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/RuntimeEventProjector.java:105-116,238-254,382-385` · `onEvent/persistAssistant/emitPersisted` | 同一 Projector 同步处理回调，持久化完成后发送完整事件；不能由此推断不同 Projector 或其他写入入口已共同检查前置依赖 |
| 已观察实现 | `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java:55-87,208-218` · `acceptUserEvent/appendEntry/appendLocked` | 事务锁定 Session，再取序号、插入和递增；保存到达该写入边界的顺序，并不自动恢复上游乱序 |
| 已观察实现 | `campusclaw/src/main/resources/mapper/session/RuntimeSessionMapper.xml:47-75,132-164` · `lockSessionForUpdate/lockNextSequence/insertEntry/listCurrentBranch` | 使用行锁；历史 SQL 按 `entry_seq` 排序，不按 `timestamp` 排序 |
| 已观察实现 | `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/RuntimeEventQueryService.java:53-60,90-99` · `list/pageOf` | 保留查询结果顺序，以最后一项内部序号生成不透明下一页游标；尚非 Session Events 的整数页码 |
| 架构变更（待实现） | [Events 有序追加](chat-events-design.md#31-事件处理写入与展示顺序) 与 `SessionEventAppender` 推荐边界 | 所有来源共同遵守前置依赖和有序提交；ListEvents 读取已提交顺序，时间戳只作展示。需按 [Events 实施验收](chat-events-design.md#5-实施切片与验收) 落地并测试，不能把数据库行锁当作全部保证 |

pi 固定基线中的 Agent Loop、Message/Tool 生命周期继续作为 Runtime 内核行为参考；
本次不把 pi 的进程内事件、本地 Session 文件或 CLI 传输直接当成 CampusClaw HTTP 契约。

[Anthropic Managed Agents 的 Events and streaming](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)
与 [List Events](https://platform.claude.com/docs/en/api/beta/sessions/events/list) 用于校验
“提交与观察分离、preview 非权威、断线后查询事件历史”的公共边界；这些页面只能证明
公开契约，不能证明其内部存储或调度实现。
[OpenCode 官方 Server 文档](https://opencode.ai/docs/server/) 当前公开的是实例级
`/event` SSE，因此这里只作多客户端通知对照，不把其源码中的 Session durable stream
描述成公开稳定契约。

### 5.2 POST 与流生命周期

该专项实际分析 `pi-mono-java@918005ee8ccc88d179fc31a0de17a92b4a01383b`。
以下路径前缀均为
`campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/`。
这七个文件相对旧 `a8192e047f4061bd385297d3dc6c4358362d0d49` 均无 diff；
变化的是目标设计，不是把本次方案误说成已实现。

| 相对上述前缀的路径 / 符号 | 已观察行为与新目标差距 |
|---|---|
| `web/RuntimeEventController.java:61-91` · submit/list | 当前 POST 返回 SSE、GET 返回历史，无独立 GET stream；新方案复用传输方向 |
| `event/RuntimeEventService.java:101-141` · prepareAndSubmitLocked/acceptUserEntry | 当前只接收消息，保存后发送 user.message 并启动；三类输入和完整 Session Events 回执仍需改造 |
| `event/RuntimeEventStream.java:84-159` · complete/attach/detachInternal | 单 subscriber、有界缓冲、断线清缓冲，不自行 abort；尚无控制 POST 的独立绑定 |
| `web/RuntimeSseEmitterSubscriber.java:33-49` · onEvent/onComplete | 当前 named SSE 和可选 id，完成后 emitter.complete；目标 data-only 不等于当前格式 |
| `event/RuntimeExecutionCoordinator.java:154-168` · completeExecution | 当前收尾持久化、发送终态、complete 流；已确认目标中的等待确认分段关闭不能据此宣称已有 |
| `event/RuntimeTerminalEventFactory.java:34-57` · emit | 当前成功/中断发 session.status.idle + stream.end，失败发 stream.error；目标已确认收到对应 idle 后关闭，reason 与失败处理已按 B07/B11 确认，尚未实现 |
| `event/RuntimeEventQueryService.java:53-99` · list/pageOf | 当前按内部序号生成下一页游标；Session Events 目标改为普通整数页码 |

本次不修改 pi Agent Loop、Tool Loop 或 Session 内核语义，也不以 pi 的进程内事件
证明 HTTP 合并设计。原 pi 固定基线仅保留为其他 Runtime 设计的证据范围。

### 5.3 进程内执行定位

本节继续核对 `pi-mono-java@918005ee8ccc88d179fc31a0de17a92b4a01383b`；
下表路径相对 §5.2 的 runtimeapi 前缀。这里观察的是该基线的独立 Abort 实现，
不是声称目标 `user.interrupt` POST SSE 已实现。

| 已观察源码 / 符号 | 事实 |
|---|---|
| `runtime/RuntimeSessionEngineRegistry.java` · sessions/register/find/complete | 活跃 RuntimeSessionHolder 保存在当前进程的 ConcurrentHashMap 中；find 只查询本实例内存，完成后移除 |
| `session/RuntimeSessionControlService.java` · prepareAbortLocked/requireRunningHolder | 读取持久化 Session 状态，再从本地 registry 查执行对象；running 状态下本地缺少对象时抛出 SESSION_EXECUTION_UNAVAILABLE |

由此推导的多实例情形（不是已验证的部署拓扑）：同一个服务部署实例 A、B，
消息 POST 被交给 A，Agent 执行对象和原 SSE 在 A；后来的中断是另一个 HTTP 请求，
可能被分给 B。即使 B 从共享数据库读到 Session 正在运行，也没有 A 内存中的执行对象，
不能仅凭 sessionId 在本地停止它。共享数据库记录不等于共享正在执行的 Java 对象。

“路由问题”是让第二次请求或其控制指令到达执行所在实例，不是 SSE 的每一帧会重新
分配实例。单实例没有此跨实例问题。概念上可把请求送到 A，或让 B 把控制指令交给 A；
当前目标采用 [Events 数据库控制](chat-events-design.md#44-数据库停止请求与实例批量检查) 的数据库交接方案，本期不依赖上述两类直接路由。
该目标不证明最新 Java 已完成分布式中断；故障自动接管仍在范围外，工具确认交接由 Events 主设计单独维护。

<a id="credential-forwarding-evidence"></a>

## 6. 凭据判断下沉到 Mate（2026-09-19）

设计修订起点为 `pi-mono-java-design@86abd68`。实现核验固定于本地明确快照
`pi-mono-java@21c3f59be033e7bdd5506a2d9d48baa2581bc3c7`，不声明为最新上游或已部署版本。
源码前缀 R 为 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`；
下列读取没有升级其他模块和外部 Agent 的历史证据。

| 路径与符号 | 已观察实现 | 目标差距 |
|---|---|---|
| R `runtimeapi/web/RuntimeRequestContext.java` · mateCredentials | 按四个固定 Header 名取值，缺失为 null，创建 MateCredentials | 读取本身已允许缺省，保留 |
| R `common/client/mate/MateCredentials.java` · record / empty / isComplete | 不可变四值与空快照已存在；isComplete 要求 ID、access-token 及 JWT/APPKEY 至少一种 | 保留载体与空快照，完整性结果不再作为 Claw 准入条件 |
| R `runtimeapi/event/RuntimeEventService.java` · submit / requireCredentials | 五类事件分派前拒绝不完整凭据；仅 message 分支向执行传入快照 | 移除前置凭据检查，保留资源与事件业务校验，控制请求不换原快照 |
| R `tool/mate/CallMateTool.java` · execute | 解析工具前检查 isComplete，缺失即抛错 | 移除此检查；保留解析、取消、确认及失败转换 |
| R `common/client/HttpMateToolClient.java` · invokeTool / toHeaderInfo / toToolResult | 不完整时不请求 Mate；toHeaderInfo 已能把 null 归为空快照；resCode 非 0 转为失败，调用异常转通用失败 | 移除提前返回，让空/部分快照也实际发出 execute；复用结果通道，不新增远端响应模型 |
| R `common/dto/RequestHeaderInfo.java` · toHeaders；R `common/util/MateRestUtil.java` · newRequestBuilder | 使用原 Header 名，跳过 null 和空字符串，不按 JWT/APPKEY 组合判断 | 保留省略与协议构造行为；测试必须观察出站 Header，而非仅检查入站 DTO |

当前三处本地检查尚在，移除增量为**待实现**；Header 捕获、不可变载体、出站映射和工具失败转换已有实现。
目标与理由由 [HTTP §7](chat-http-v1-design.md#credential-forwarding)维护，工具可用条件由
[M03 §9.2](../02-CampusClaw工具系统/README.md#mate-credential-forwarding)维护。
不修改 Java，不新增依赖；未运行真实 Mate 或产品集成测试，不能把静态契约通过当作空凭据请求已联调成功。

设计验收：在排除无关工作树修改的交付副本运行 `validate-chat-api.py --full`，十项接口及附属测试通过；事件校验拒绝 114 个 POST、57 个历史及其他专项负向变体，新增反例覆盖本地完整性判断、旧必填说明与重复 current 字段。14 个图形专题重新生成并逐字节比较通过；90 份 Markdown 无 Mermaid、35 份 PUML 为 ASCII、124 份 SVG 为有效 XML，图像链接和图源行锚点有效。凭据 HTTP 与工具执行两张 SVG 已对照修改前图，检查原尺寸与 840 px 文档宽度；发现/缓存及 Host/工具分层不变。前端图形无需结构调整，沿用原刷新门禁。`git diff --check` 通过；以上不包含 Java 或真实认证、Mate 验收。
