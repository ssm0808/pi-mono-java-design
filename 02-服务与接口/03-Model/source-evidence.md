# Model：源码证据与实现差距

版本：1.4.0 · 2026-10-16。返回[模块主设计](README.md)。

本文集中保存已读取的源码证据。每项结论仅适用于对应提交与核验范围；目标规则和验收见主设计。独立核验范围分别记录；本次未运行产品测试。

## 1. 模型来源专项（2026-09-17）

### 1.1 pi

核验时上游默认分支为 `main`，提交为 `16235fd93521f9f96164f5891beea62e6bea5b18`，前次参考点为 `5cd93f688aaab89dbb6dfa4aca535f21796ae185`。更新范围仅为模型配置、Provider 组合和默认模型选择；Agent Loop、Session 与事件证据仍属于 §2 的固定提交。

| 仓库相对路径与符号 | 已观察行为 |
|---|---|
| `packages/coding-agent/src/core/model-runtime.ts`：`ModelRuntime.create/providerIds/rebuildProviders` | 读取 Agent Dir 下的 `models.json`，组合内置 Provider、JSON 配置和扩展 Provider，维护模型可用性快照。 |
| `packages/coding-agent/src/core/model-config.ts`：`ModelConfig.load` | 缺失文件时返回空配置；存在时解析并校验 Provider、模型和 override。 |
| `packages/coding-agent/src/core/agent-session-services.ts`：`createAgentSessionServices` | `ModelRuntime` 使用 `agentDir/models.json`，`SettingsManager` 独立提供 `defaultProvider/defaultModel`。 |
| `packages/ai/src/models.ts`：`ModelsImpl`、`createProvider` | Provider 同时发布模型并提供流实现，支持静态、动态和按 API 分派。 |

### 1.2 CampusClaw

核验时实现仓 `main` 与远端同步，提交为 `21c3f59be033e7bdd5506a2d9d48baa2581bc3c7`。以下为静态源码证据。

| 编号 | 仓库相对路径与符号 | 已观察行为与差距 |
|---|---|---|
| J-AI-N01 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/AgentRuntimeManager.java`：`prepare/loadSnapshot/validSettings/toSettings` | 从业务 Agent `.campusclaw/settings.json` 读取 `defaultModel/bindingModels`，校验默认值属于绑定列表，生成 `PreparedAgentRuntime`；主链已有设置校验。 |
| J-AI-N02 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/agent/AgentDirectorySnapshots.java`：`from/validModels`；`runtimeapi/model/MateRuntimeModelManager.java`：`resolveModel/listAvailableModels` | 同一次准备生成不可变模型快照；默认 Manager 校验允许列表并构造 `Provider.CAMPUSMATE` Model。 |
| J-AI-N03 | `modules/ai/src/main/java/com/campusclaw/ai/model/ModelRegistry.java`：`init/loadFromClasspathResource/loadFromUserFile/loadFromJsonStream` | 启动时仍探测 `/campusclaw-models.json` 和 `~/.campusclaw/agent/models.json`，保留 INFO/DEBUG/WARN 加载日志；唯一模型来源目标尚未完全落地。 |
| J-AI-N04 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/model/ModelCatalogService.java`：`getAvailableModels`；`runtimeapi/model/CatalogRuntimeModelManager.java`：`resolveModel/listAvailableModels` | 全局注册表加环境凭据过滤仍可构成第二模型来源；默认配置未装配该 Manager。 |
| J-AI-N05 | `modules/ai/src/main/java/com/campusclaw/ai/CampusClawAiService.java`：构造器、`getModelRegistry`；`provider/mate/MateChatSseParser.java`：`parseUsage` | AI Service 仍依赖注册表；SSE Parser 只使用其中的静态成本计算，清理目录需处理这两处消费者。 |

<a id="model-capability-evidence"></a>

## 1.3 模型能力专项（2026-09-19）

pi 当次通过 ls-remote 确认默认分支 main，并在临时仓库 fetch 得到 `36b60d2e8985899743c4cf5bd5f8929832a3f05d`。前次模型来源证据为 `16235fd93521f9f96164f5891beea62e6bea5b18`；本次仅增量核验以下能力字段及消费路径，旧模型目录组合观察仍归属于前次提交。源码 package 版本为 0.85.1；默认分支快照不等于稳定发布验收。

| 仓库 / 完整提交 | 仓库相对路径与符号 | 已观察行为 |
|---|---|---|
| pi `36b60d2e8985899743c4cf5bd5f8929832a3f05d` | `packages/ai/src/types.ts` · Model；`packages/coding-agent/src/core/provider-composer.ts` · modelFromJson | Model 有 contextWindow/maxTokens；自定义模型未填写时补 128000/16384。能力构造证据定位到 provider-composer.ts，不用旧目录入口替代该字段核验。 |
| 同上 | `packages/ai/src/api/simple-options.ts` · buildBaseOptions/clampMaxTokensToContext；`packages/coding-agent/src/core/compaction/compaction.ts` · shouldCompact | 普通 options 优先显式额度再取模型值，并按剩余窗口及 4096 安全余量收紧；压缩阈值为 contextWindow-reserveTokens。CampusClaw 本专题不迁移该安全余量算法。 |
| CampusClaw 本地 `21c3f59be033e7bdd5506a2d9d48baa2581bc3c7` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/model/MateModelManagerProperties.java`、`MateRuntimeModelManager.java` · resolveModel | 所有绑定模型共用 128000/8192 配置默认值；这是实际行为，不是 Mate 返回的能力。 |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/AgentRuntimeManager.java` · rebuild/toSettings/loadSnapshot/publish；`MateServiceClient.java` · AgentRuntime；`runtimeapi/agent/AgentDirectorySnapshotDTO.java`（同 codingagent 包） | 只取得模型 ID 列表；目录 staging/完整性校验/原子发布已有骨架，settings 和请求快照均无逐模型能力。 |
| 同上 | `modules/ai/src/main/java/com/campusclaw/ai/types/Model.java`、`SimpleStreamOptionsFactory.java`；`modules/agent-core/src/main/java/com/campusclaw/agent/Agent.java` · buildStreamOptions | Model.maxTokens 为 int；工厂存在直接算术，Agent 无显式额度时填模型值；输出控制移交需要清理整条消费链。 |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/compaction/SessionCompactor.java` · overflowDecision/summaryMaxTokens；`modules/ai/src/main/java/com/campusclaw/ai/utils/ContextOverflowDetector.java` · isRecoverableLength | 模型上限用于 LENGTH 恢复比较和摘要预算；移交 Mate 后不能只删除配置而保留消费假设。 |
| Mate 本地 `4b957a3a846659f5b7569c9d6133abc070cd2e3c` | `src/main/java/com/huawei/hicampus/mate/agentdefinition/vo/RuntimeAgentResponseVO.java`；`service/impl/AgentDefinitionServiceImpl.java` · getRuntimeAgent/buildRuntimeAgent（同 agentdefinition 包） | runtime 返回 bindingModels ID 数组，未提供 token 能力；当前查询组合模型、Tool、Skill 和 Agent 绑定。 |
| 同上 | `src/main/java/com/huawei/hicampus/mate/agentdefinition/modelmanager/config/ModelManagerProperties.java` · ModelRoute；`service/ConfiguredModelRouteResolver.java` · resolve；`vo/LlmChatRequestVO.java`；`service/LlmChatService.java` · rewriteMaxOutputTokens（后三者同 modelmanager 包） | 路由包含 endpoint/上游 ID/凭据/输出字段名，没有 contextWindow/maxTokens 数值；Chat 输出参数为可选正整数，按路由改名或删除；没有证据证明可直接复用现成能力目录。 |

| pi 同一 main 提交 | `packages/coding-agent/src/core/compaction/compaction.ts` · createSummarizationOptions/generateSummaryWithUsage/generateTurnPrefixSummary | 摘要仍显式设置 maxTokens，历史/前缀取 reserve 的 80%/50% 并受模型上限限制；Claw 将全部输出控制交给 Mate 是有意差异。 |
| Java 同一 `21c3f59b` 提交 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeMessageEventService.java` · submitPrepared/submitLocked/prepare；`session/RuntimeSessionModelReconciler.java` · reconcile（同 runtimeapi 包） | 消息准备在 withOperationLock 内，reconcile 可提交模型校准；新增远程信息查询必须拆成观察、锁外读取与锁内复核，不能直接插入现有锁内路径。 |
| 同上 | `runtimeapi/event/RuntimeExecutionContextFactory.java` · create/createPreparedMessage；`session/AgentSessionFactory.java` · create（均在 modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent 下） | 执行工厂收到已解析 Model，公共 Session 工厂服务 Runtime/Subagent/Cron；当前没有执行前信息查询和独立能力 DTO。 |
| 同上 | `modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateChatRequestMapper.java` · appendOptions | options.maxTokens 非空就写 max_output_tokens；目标需要删除该映射，包括摘要与显式 options 的入口。 |

2026-09-19 再次确认上游默认分支并 fetch，pi 仍为上述 `36b60d2e8985899743c4cf5bd5f8929832a3f05d`；新增核验摘要输出策略，其他历史范围不升级。Java 与 Mate 为本地明确提交的静态核验，未声称已更新其远端。Mate `src/main/java` 未发现独立信息查询 Controller。目标为新执行锁外查询 contextWindow、固定执行快照，普通调用及摘要均由 Mate 控制输出；查询/准入拆分、前置预算检查和输出策略迁移待实现。与 pi 保留本地额度及摘要预算的差异属于产品约束和架构变更，代价与验收见[模型信息专题](model-capabilities.md)。

<a id="http-transport-evidence"></a>

## 1.4 模型 HTTP 传输与并发专项（2026-10-16）

2026-10-16 隔离 fetch 各仓库默认分支，只读源码，结论只适用于下表提交与路径。对应设计见[主设计 §5](README.md#http-transport)。

| 来源与提交 | 仓库相对路径 · 符号 | 观察结论 |
|---|---|---|
| Java `main@1acbbf3f046932872af06868c600bb5d9498d8b6` | `modules/ai/src/main/java/com/campusclaw/ai/provider/mate/CampusMateProvider.java` · createWebClient、eventFlux、subscribe、cancel | 唯一使用 Reactor Netty 的生产代码：`HttpClient.create().disableRetry(true)`、`CONNECT_TIMEOUT_MILLIS`、`responseTimeout`，包成 `ReactorClientHttpConnector`；没有显式连接池或并发上限 |
| 同上 | `modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateChatSseParser.java` · transportErrorCode | 按 `TimeoutException`、`SocketTimeoutException`、类名含 Timeout、`ConnectException`、`WebClientRequestException` 分类，不依赖 Netty 类型 |
| 同上 | `modules/ai/src/test/java/com/campusclaw/ai/provider/mate/CampusMateProviderTest.java` | 测试构造 WebClient 时直接使用 `reactor.netty.http.client.HttpClient`；没有连接超时或事件间隔超时测试 |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/runtime/RuntimeExecutionProperties.java` · maxActive；`RuntimeSessionEngineRegistry.java` · capacity | 执行准入默认每实例 100，用 Semaphore 控制；`schedule/config/ScheduleProperties.java` · instanceExecutionLimit 默认 8；没有模型调用级上限 |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/MateServiceClient.java`、`common/util/MateRestUtil.java` | Runtime 侧 Mate 客户端已使用 JDK `java.net.http.HttpClient` |
| 同上，`./mvnw dependency:tree` | `campusclaw-coding-agent` 依赖树 | Netty 只经 `campusclaw-ai` → `reactor-netty-http:1.2.5` 引入：`reactor-netty-core` 与 17 个 `io.netty:4.1.119.Final` 构件，本地 jar 合计约 5.5 MB |
| Reactor Netty `1.2.5` 源码包 | `reactor/netty/resources/ConnectionProvider.java` · DEFAULT_POOL_MAX_CONNECTIONS、DEFAULT_POOL_ACQUIRE_TIMEOUT、DEFAULT_POOL_MAX_IDLE_TIME；`PooledConnectionProvider.java` · pendingAcquireMaxCount；`reactor/netty/http/client/HttpClient.java` · responseTimeout；`HttpClientOperations.java` · ReadTimeoutHandler | 默认最多 `max(CPU 核数, 8) × 2` 条连接，排队上限为其 2 倍，排队最多 45 秒，空闲不按时间关闭；`responseTimeout` 是两次网络读之间的最大间隔 |
| Spring Framework `6.2.6`（spring-web jar） | `org.springframework.http.client.reactive.JdkClientHttpConnector` · JdkClientHttpConnector(HttpClient)、setReadTimeout | Spring 自带 JDK 连接器，可包装自建 HttpClient 并设置响应超时 |
| OpenJDK `jdk21u` `master@bb6b279495ceff8442dbd0225756b92d466d5309`（更新分支源码，运行时为 21.0.12，未逐行比对） | `src/java.net.http/share/classes/jdk/internal/net/http/ConnectionPool.java` · returnToPool、MAX_POOL_SIZE；`HttpClientImpl.java` · DEFAULT_KEEP_ALIVE_TIMEOUT；`MultiExchange.java` · retryOnFailure、canRetryRequest | 连接池属于 HttpClient 实例；空闲 30 秒关闭；`connectionPoolSize` 默认 0 不限制；`ConnectException` 默认重试一次，非 GET/HEAD 请求在连接过期时不重试 |
| pi `main@4dd2b149d155d7369de16ea4dc77c84e9f5ffb24` | `packages/ai/src/api/openai-completions.ts` · stream、createClient | 每次 `stream` 调用新建 OpenAI SDK 客户端，传入可选 `fetch`，未配置连接池、预热或并发上限 |
| Codex `main@4eb4a65407d98cebc4c83bf13be440b9fbc78a7c` | `codex-rs/core/src/client.rs` · stream_responses_http、build_api_transport；`codex-rs/login/src/auth/default_client.rs` · create_client_for_route | HTTP 流式请求每次经 `build_api_transport` 构造 reqwest 客户端，未见模型请求并发上限 |
| 同上 | `codex-rs/core/src/client.rs` 模块注释（第 11–26 行）、`ModelClient.cached_websocket_session`、`prewarm_auth` | 每轮开始以 `generate=false` 的 `response.create` 预热 Responses WebSocket，本轮后续请求复用该连接与 `previous_response_id`；连接在会话内缓存，认证归属变化时丢弃 |
| 同上 | `codex-rs/core/src/config/mod.rs` · DEFAULT_AGENT_MAX_THREADS | 默认最多 6 个 Agent 线程，间接限制并发模型请求 |
| Java `main@1acbbf3f046932872af06868c600bb5d9498d8b6` | 全仓 `*.java`、`*.xml`、`*.yml`、`*.properties` 检索 redis、lettuce、redisson | 没有 Redis 依赖或代码；命中项只是 `requireDisplay` 等无关字符串。Redis 只出现在 `docs/designs` 中“不新增 Redis”的说明 |
| Spring Boot `3.4.5` `spring-boot-dependencies` POM | `jedis.version`、`lettuce.version`、`commons-pool2.version` | 管理 Jedis 5.2.0、Lettuce 6.4.2.RELEASE、commons-pool2 2.12.1 |
| Maven Central `io.lettuce:lettuce-core:6.4.2.RELEASE` POM | 非可选编译依赖 | `netty-common`、`netty-handler`、`netty-transport`、`reactor-core`；采用 Lettuce 会让 Netty 回到产物 |
| Maven Central `redis.clients:jedis:5.2.0` POM 与 jar | 非可选编译依赖 | `slf4j-api`、`commons-pool2`、`org.json:json:20240303`、`gson:2.11.0`，无 Netty；jedis 约 980 KB，加 commons-pool2、json、gson 四个 jar 合计约 1.5 MB |
| Maven Central `org.redisson:redisson` 3.37.0、4.8.0 POM 与 jar；`io.netty` 4.1.119 POM | 非可选编译依赖 | 两个版本都直接依赖 7 个 Netty 构件（common、codec、buffer、transport、resolver、resolver-dns、handler），再经 `netty-handler`、`netty-resolver-dns` 传递带入 `netty-transport-native-unix-common`、`netty-codec-dns`，共 9 个，本地 jar 合计约 2.7 MB；另依赖 reactor-core、rxjava、kryo、byte-buddy、jodd-util、snakeyaml，不依赖 reactor-netty。4.8.0 主 jar 约 3.1 MB，许可证 Apache 2.0；`redisson-parent` 的编译目标为 Java 8 |
| Maven Central `redisson-spring-data-34` 版本列表；`redisson-spring-boot-starter` 3.37.0、4.8.0 POM | 依赖与适配版本 | `redisson-spring-data-34` 有 3.40.0～3.52.0 与 4.0.0～4.8.0；starter 3.37.0 依赖 `spring-boot-starter-actuator` 和 `redisson-spring-data-33`，4.8.0 依赖 `spring-boot-actuator` 和 `redisson-spring-data-41`，都不直接适配 Boot 3.4.5 |
| Maven Central `redisson-parent` 3.52.0、4.0.0、4.6.1、4.7.0、4.8.0 POM；`redisson` jar 发布时间 | `netty-bom` 版本 | 3.52.0（2025-09-25，3.x 最后一版）用 Netty 4.1.127；4.0.0（2025-12-16）用 4.2.9；4.6.1、4.7.0、4.8.0（2026-10-02）分别用 4.2.15、4.2.16、4.2.18 |
| Redisson `redisson-4.8.0`、`redisson-3.52.0` 标签 | `redisson/src/main/java/org/redisson/connection/ServiceManager.java` 导入；`CHANGELOG.md` 4.0.0、4.8.0 节 | 4.8.0 导入 Netty 4.2 才有的 `MultiThreadIoEventLoopGroup`、`io.netty.channel.uring.*`，3.52.0 只用 `NioEventLoopGroup`、`EpollEventLoopGroup`；4.0.0 有若干不兼容改动（如 `RScript.ReturnType` 改名），4.8.0 修复了连接池许可统计、AUTH 建连顺序等问题 |
| Redisson `redisson-4.8.0` 标签 | `redisson/src/main/java/org/redisson/RedissonPermitExpirableSemaphore.java` · tryAcquireAsync、updateLeaseTimeAsync、trySetPermitsAsync | 租约到期时间由客户端 `System.currentTimeMillis()` 计算后传入脚本；可用数存在单独计数 key，key 不存在时申请返回空；`updateLeaseTime` 只更新仍存在的许可；等待通过 Pub/Sub 频道通知后重试 |

原型验证（临时 worktree，不是交付代码）：在 Java `1acbbf3f` 上把 `createWebClient` 和测试改为 `JdkClientHttpConnector`，删除 `modules/ai/pom.xml` 的 `reactor-netty-http`，并给 SSE 响应体加 `Flux.timeout`。`./mvnw -pl :campusclaw-ai -am test` 通过，`campusclaw-ai` 366 个测试 0 失败；`campusclaw-coding-agent` 依赖树不再含 `io.netty` 或 `reactor-netty`。首轮全量测试出现 1 次 Reactor `onErrorDropped` 日志，后续两次全量运行未复现，原因未定位；回调线程为 `ForkJoinPool.commonPool`。许可机制（含 Redis 脚本）未做原型，并发与容量结论均未压测。

## 2. pi 历史固定行为基线

固定提交：`5cd93f688aaab89dbb6dfa4aca535f21796ae185`。

| 证据 | 观察行为 |
|---|---|
| `packages/ai/src/models.ts`：`Provider`、`MutableModels`、`ModelsImpl`、`createProvider` | Provider 注册和调用按 `provider.id`；Provider 持有认证、目录和 stream 能力。 |
| `packages/ai/src/types.ts`：`Model`、`SimpleStreamOptions`、`ToolChoice`、`Usage` | Model 同时携带 Provider/API；通用 `toolChoice` 为 `auto/none`；Usage 始终存在。 |
| `packages/agent/src/agent-loop.ts`：`runLoop`、`streamAssistantResponse` | 普通 Loop 不计算 `toolChoice`；收到 Assistant ToolCall 后执行工具并继续下一轮。 |
| `packages/coding-agent/src/core/compaction/compaction.ts`：`completeSummarization` | 摘要调用显式使用 `toolChoice: "none"`，避免调用工具。 |
| `packages/ai/src/api/openai-completions.ts`：`stream`、`convertMessages` | Chat Provider 处理 system/user/assistant/tool、ToolCall、reasoning 扩展和 usage chunk。 |
| `packages/agent/src/harness/session/types.ts`：`UsageRecord`、`SessionStats` | Usage 是独立 Record，可关联 assistant、compaction、branch summary 和 deferred fetch。 |
| `packages/session-backends/sqlite-node/src/sqlite/migrations/001_initial.sql` | SQL 后端把 `entries`、`records` 和 `session_stats` 分表保存。 |
| `packages/session-backends/sqlite-node/src/sqlite/repo.ts`：`appendRecord` | Usage Record 插入后，同一串行写路径增量更新 Stats。 |
| `packages/session-backends/sqlite-node/src/sqlite/storage/session-stats.ts` | 汇总 cached、uncached、total tokens 和总费用。 |

pi 的 `Usage` 在流开始时初始化为全零，收到上游 usage 后覆盖；无法区分“未报告”与“真实为零”。

## 3. Java 历史模型调用与产品范围

固定提交为 `pi-mono-java@f61906b9136246ca60f333704b6fc92b5420d0ec`。相较前次 `56be8eee59415a5f86658d6635a7b7e8891263d3`，客户端已读取统一 `campusmate` 配置。下表保留该提交的类名及路径，范围不含 Usage SQL 和公共 API。

| 编号 | 仓库相对路径与符号 | 已观察行为与差距 |
|---|---|---|
| J-AI-01 | `modules/ai/src/main/java/com/campusclaw/ai/CampusClawAiService.java`：`stream/streamSimple/resolveManagedProvider/resolveProvider`；`provider/AiProviderRegistry.java`、`provider/ApiProviderRegistry.java`（均位于同一 `ai/` 包下）：构造器、`getProvider/register/unregister` | ProviderId 路由优先，未命中再按 API；两个注册表允许空集合。 |
| J-AI-02 | `modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateServiceModelManagerProvider.java`：`PROVIDER_ID/streamSimple/eventFlux/createWebClient` | ID 仍为 `mate-model-manager`；使用 WebClient/Reactor Netty，无 OpenAI SDK；读取 `campusmate.base-url/endpoints/model`。 |
| J-AI-03 | `modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateChatRequestMapper.java`：`map/appendOptions`；`MateChatSseParser.java`：`accept/parseReasoning/parseUsage/finish`；`MateReasoningSignature.java`：`encode/decode`（后两者同目录） | 已有独立 JSON 映射、文本/工具/推理 SSE、Usage、签名重放与取消终态。 |
| J-AI-04 | `modules/ai/src/main/java/com/campusclaw/ai/provider/anthropic/AnthropicProvider.java`、`provider/openai/OpenAICompletionsProvider.java`、`provider/openai/OpenAIResponsesProvider.java`、`provider/mistral/MistralProvider.java`（后三者相对同一 `ai/` 包）：类声明及 `stream/streamSimple` | 四个厂商适配器仍随产品交付，尚未按 CampusMate 单出口裁剪。 |
| J-AI-05 | `modules/ai/src/main/java/com/campusclaw/ai/model/ModelRegistry.java`：`init/builtInModels/register/getAllModels/loadFromJsonFile/calculateCost`；`types/Provider.java`、`types/Api.java`（相对同一 `ai/` 包）：enum | 加载第三方预置、classpath 与用户 JSON；Provider/API 为 enum。后续目录核验见 J-AI-N03～N05。 |
| J-AI-06 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/model/MateRuntimeModelManager.java`：`resolveModel/listAvailableModels`；`runtimeapi/RuntimeApiConfiguration.java`：`mateRuntimeModelManager`（同一 `codingagent/` 包） | 默认 Runtime 根据 Agent 快照构造 Mate Model，不依赖第三方预置。 |
| J-AI-07 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEntryCodec.java`：`assistantEntry/assistantMessage`；`session/compaction/SessionCompactor.java`：`sameModel`；`tool/agent/SubagentExecutionService.java`、`tool/cron/ManagedCronSessionRunner.java`：模型匹配（均相对同一 `codingagent/` 包） | `_provider` 按字符串持久化；压缩、Subagent/Cron 按 Provider 与 modelId 匹配，身份改名影响这些消费者。 |
| J-AI-08 | `pom.xml`、`modules/ai/pom.xml`、`campusclaw/pom.xml`：LLM SDK dependencies；`scripts/sync-campusclaw.sh`：镜像同步 | canonical 与公司镜像均声明两个 SDK，镜像 Java 从 modules 生成；SDK 裁剪尚未落地。 |

<a id="dependencies"></a>

### 3.1 SDK 依赖记录

该固定基线的源码消费者核验显示，两个 SDK 仅被对应厂商适配器及专属测试使用，公司镜像中有相应副本；消费者范围需在实施删除前重新核对。

`f61906b9136246ca60f333704b6fc92b5420d0ec` 的已有记录包含成功执行的离线 `dependency:tree -Dscope=runtime`：直接依赖为 `com.anthropic:anthropic-java:2.18.0` 和 `com.openai:openai-java:4.29.1`，经各自 `client-okhttp/core` 引入 Kotlin、OkHttp、Jackson 扩展、Swagger 注解和 Victools JSON Schema；Anthropic 路径还包含 Apache HttpClient/Core 5。

当时运行时仲裁版本为 Kotlin `1.9.25`、Jackson `2.18.3`、OkHttp logging interceptor `4.12.0`、Victools `4.38.0`、HttpClient `5.4.3` 与 HttpCore `5.3.4`。这是裁剪前依赖树；公司父 POM 的完整依赖树和裁剪后产物未验证，本次整理未重跑该命令。

## 4. Mate Chat 服务端

mate-service 固定基线 `956b547f`：`src/main/java/com/huawei/hicampus/mate/agentdefinition/modelmanager/controller/LlmChatController.java:35-55` 通过 `CHAT_PATH` 实现 `POST /mate-service/v1/LLM/chat`；`LlmChatController.createChat` 接收 JSON，由 `LlmChatService` 创建上游调用，成功返回 `text/event-stream`。该范围未发现独立模型目录接口，也未核验 Mate 内部路由、凭据或 Usage 持久化。

## 5. Thinking 与 Usage 的独立核验范围

- Thinking：`pi-mono-java@4cc8dd86f601417c22cf9306e52152acbb59bb60`，`modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateChatSseParser.java` 的 `parseReasoning/appendReasoningText/finishThinking`；可读文本与签名分别输出，Runtime 展示差距见[Thinking 主设计](../../01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md#thinking-original-text)。
- Usage SQL：`pi-mono-java@d649866a6cae967ace18ceaeb9597edd47e5721e`，`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEntryCodec.java` 的 `assistantEntry/assistantMessage`、`persistence/MyBatisRuntimeSessionRepository.java` 的 `appendLocked`（同一 `runtimeapi/` 包）、`modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql`；该提交集中式投影丢失 Usage，尚无 Record/Stats 写入链。目标事务与验收见[Usage 设计](usage.md)。

## 6. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.4.0 | 2026-10-16 | 核验 Reactor Netty 使用点与默认连接池、JDK HttpClient 连接复用与重试、Redis 客户端依赖，以及 pi/Codex 的模型 HTTP 客户端做法。 |
| 1.3.0 | 2026-09-19 | 补充执行锁内准备、请求额度映射与 pi 摘要证据，登记按执行读窗口和 Mate 输出权威的差距。 |
| 1.2.0 | 2026-09-19 | 核验 pi 逐模型能力与 Java/Mate 默认值链，登记独立查询、能力快照及未知输出上限的实现差距。 |
| 1.1.2 | 2026-09-17 | 模块统一命名为 Model，源码基线与实现差距不变。 |
| 1.1.1 | 2026-09-17 | 精简重复目标说明和辅助图入口，保留各项源码证据及核验范围。 |
| 1.1.0 | 2026-09-17 | 核验最新 pi 与 Java 模型来源，记录业务 Agent 设置唯一权威及旧全局目录删除差距。 |
| 1.0.0 | 2026-09-14 | 集中 Model 固定源码证据和实现差距。 |
