# Model：源码证据与实现差距

版本：1.2.0 · 2026-09-19。返回[模块主设计](README.md)。

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
| 同上 | `modules/ai/src/main/java/com/campusclaw/ai/types/Model.java`、`SimpleStreamOptionsFactory.java`；`modules/agent-core/src/main/java/com/campusclaw/agent/Agent.java` · buildStreamOptions | Model.maxTokens 为 int；工厂存在直接算术，Agent 无显式额度时填模型值；可选能力需要消费链改造。 |
| 同上 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/compaction/SessionCompactor.java` · overflowDecision/summaryMaxTokens；`modules/ai/src/main/java/com/campusclaw/ai/utils/ContextOverflowDetector.java` · isRecoverableLength | 模型上限用于 LENGTH 恢复比较和摘要预算；未知上限不能仅删除配置而保留消费假设。 |
| Mate 本地 `4b957a3a846659f5b7569c9d6133abc070cd2e3c` | `src/main/java/com/huawei/hicampus/mate/agentdefinition/vo/RuntimeAgentResponseVO.java`；`service/impl/AgentDefinitionServiceImpl.java` · getRuntimeAgent/buildRuntimeAgent（同 agentdefinition 包） | runtime 返回 bindingModels ID 数组，未提供 token 能力；当前查询组合模型、Tool、Skill 和 Agent 绑定。 |
| 同上 | `src/main/java/com/huawei/hicampus/mate/agentdefinition/modelmanager/config/ModelManagerProperties.java` · ModelRoute；`service/ConfiguredModelRouteResolver.java` · resolve；`vo/LlmChatRequestVO.java`；`service/LlmChatService.java` · rewriteMaxOutputTokens（后三者同 modelmanager 包） | 路由包含 endpoint/上游 ID/凭据/输出字段名，没有 contextWindow/maxTokens 数值；Chat 输出参数为可选正整数，按路由改名或删除；没有证据证明可直接复用现成能力目录。 |

Java 与 Mate 是本地明确提交的静态核验，未声称本次已更新其远端。Mate `src/main/java` 范围搜索未发现独立模型能力查询 Controller。已确认目标为独立查询后发布完整快照、contextWindow 必填、maxTokens 可选；这两项与查询/发布链为待实现。未知上限与 pi 的必填 Model/默认补值不同，属于企业模型权威的产品约束及架构变更；具体代价与验收见[能力专题](model-capabilities.md)。

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
| J-AI-07 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEntryCodec.java`：`assistantEntry/assistantMessage`；`session/compaction/SessionCompactor.java`：`sameModel`；`tool/agent/SubagentExecutionService.java`、`tool/cron/ManagedCronSessionRunner.java`：模型匹配（均相对同一 `codingagent/` 包） | `_provider` 按字符串持久化；压缩、Child/Cron 按 Provider 与 modelId 匹配，身份改名影响这些消费者。 |
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
| 1.2.0 | 2026-09-19 | 核验 pi 逐模型能力与 Java/Mate 默认值链，登记独立查询、能力快照及未知输出上限的实现差距。 |
| 1.1.2 | 2026-09-17 | 模块统一命名为 Model，源码基线与实现差距不变。 |
| 1.1.1 | 2026-09-17 | 精简重复目标说明和辅助图入口，保留各项源码证据及核验范围。 |
| 1.1.0 | 2026-09-17 | 核验最新 pi 与 Java 模型来源，记录业务 Agent 设置唯一权威及旧全局目录删除差距。 |
| 1.0.0 | 2026-09-14 | 集中 Model 固定源码证据和实现差距。 |
