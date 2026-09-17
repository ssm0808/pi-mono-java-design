# 模型与 Provider：源码证据与实现差距

版本：1.1.0 · 2026-09-17。返回[模块主设计](README.md)。

本文件只记录实际分析过的提交及其范围。目标方案和验收由主设计维护；旧提交的差距不代表最新实现状态。

## 1. 当前专项核验

### 1.1 pi 最新默认分支

查询日期：2026-09-17。上游默认分支：`main`。最新提交：`16235fd93521f9f96164f5891beea62e6bea5b18`；前次固定参考点为 `5cd93f688aaab89dbb6dfa4aca535f21796ae185`。本次只重新核验模型配置、Provider 组合和默认模型选择，不升级 pi 的 Agent Loop、Session 或事件结论。

| 仓库相对路径与符号 | 最新已观察行为 | 对当前设计的影响 |
|---|---|---|
| `packages/coding-agent/src/core/model-runtime.ts`：`ModelRuntime.create/providerIds/rebuildProviders` | 默认读取 Agent Dir 下的 `models.json`，组合内置 Provider、JSON 配置和扩展 Provider，并维护模型可用性快照。 | pi 最新实现仍把全局模型文件和扩展 Provider 作为目录来源；CampusClaw 不采纳该边界。 |
| `packages/coding-agent/src/core/model-config.ts`：`ModelConfig.load` | 缺失 `models.json` 时返回空配置；存在时解析并校验 Provider、模型和 override。 | 证明 pi 的 JSON 是真实配置能力，不是日志占位；CampusClaw 删除对应能力属于产品约束。 |
| `packages/coding-agent/src/core/agent-session-services.ts`：`createAgentSessionServices` | `ModelRuntime` 使用 `agentDir/models.json`，`SettingsManager` 独立提供 `defaultProvider/defaultModel`。 | pi 的默认选择设置与模型目录分离；不能用 pi 的 `settings.json` 推导 CampusClaw 应保留 `models.json`。 |
| `packages/ai/src/models.ts`：`ModelsImpl`、`createProvider` | Provider 同时发布模型并提供流实现，支持静态、动态和按 API 分派。 | CampusClaw 仅保留调用抽象，模型权威改由业务 Agent 已发布设置承担。 |

### 1.2 CampusClaw 最新 main

实现仓默认分支 `main` 与远端同步，提交为 `21c3f59be033e7bdd5506a2d9d48baa2581bc3c7`。本次静态核验未修改实现仓，也未运行产品测试。

| 编号 | 仓库相对路径与符号 | 已观察行为 | 当前目标与差距 |
|---|---|---|---|
| J-AI-N01 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/AgentRuntimeManager.java`：`prepare/loadSnapshot/validSettings/toSettings` | 从业务 Agent `.campusclaw/settings.json` 读取 `defaultModel/bindingModels`，校验默认值属于绑定列表，并生成 `PreparedAgentRuntime`。 | 已具备唯一模型权威的主链；实现清理后需验证没有其他来源旁路。 |
| J-AI-N02 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/agent/AgentDirectorySnapshots.java`：`from/validModels`；`runtimeapi/model/MateRuntimeModelManager.java`：`resolveModel/listAvailableModels` | 同一次 Agent 准备生成不可变模型快照；默认 Manager 只校验快照允许列表并构造 `Provider.CAMPUSMATE` Model。 | 保留；默认模型、切换、压缩、Child/Cron 应继续复用这条链。 |
| J-AI-N03 | `modules/ai/src/main/java/com/campusclaw/ai/model/ModelRegistry.java`：`init/loadFromClasspathResource/loadFromUserFile/loadFromJsonStream` | Spring Bean 启动时仍探测 `/campusclaw-models.json` 和用户 `models.json`，并保留 INFO/DEBUG/WARN 加载日志。 | 与唯一模型来源冲突，目标删除整个目录 Bean、加载入口、日志和对应测试。 |
| J-AI-N04 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/model/ModelCatalogService.java`：`getAvailableModels`；`runtimeapi/model/CatalogRuntimeModelManager.java`：`resolveModel/listAvailableModels` | 仍可把全局注册表和环境凭据过滤组合成另一套 Runtime 模型解析。默认配置未装配该 Manager。 | 即使不是默认 Bean，也构成被保留的第二模型来源，目标删除。 |
| J-AI-N05 | `modules/ai/src/main/java/com/campusclaw/ai/CampusClawAiService.java`：构造器、`getModelRegistry`；`provider/mate/MateChatSseParser.java`：`parseUsage` | AI Service 仍依赖注册表；SSE Parser 只使用其中的静态成本计算。 | 移除 Service 目录依赖；成本计算迁至实际使用者或窄职责工具，不为单一工具方法保留全局目录类。 |

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

pi 的 `Usage` 在流开始时初始化为全零，收到上游 usage 后覆盖；上游不返回 usage 时无法区分
“未报告”与“真实为零”。本设计严格沿用该语义，不新增 `reported` 字段。

## 3. Java 历史模型调用与产品范围

下表实际核对 `pi-mono-java@f61906b9136246ca60f333704b6fc92b5420d0ec`；路径相对实现仓根目录。
与前次 `56be8eee59415a5f86658d6635a7b7e8891263d3` 相比，相关客户端已读取统一 `campusmate`
配置。该局部复核不覆盖 Usage SQL、公共 API 或其他模块的验收。固定提交里的旧类名和
路径保留原样，不能替换成尚不存在的目标类。

| 编号 | 仓库相对路径与符号 | 已观察行为 | 目标与该提交的差距 |
|---|---|---|---|
| J-AI-01 | `modules/ai/src/main/java/com/campusclaw/ai/CampusClawAiService.java`：`stream/streamSimple/resolveManagedProvider/resolveProvider`；`provider/AiProviderRegistry.java`、`provider/ApiProviderRegistry.java`（均位于同一 `ai/` 包下）：构造器、`getProvider/register/unregister` | 优先按 ProviderId 查通用 Provider，未命中再按 API 查适配器；两个注册表均允许空集合。 | 保留路由及扩展接口，默认仅装配 CampusMate；空 API 注册表不得导致启动失败。 |
| J-AI-02 | `modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateServiceModelManagerProvider.java`：`PROVIDER_ID/streamSimple/eventFlux/createWebClient` | ID 为 `mate-model-manager`；使用 WebClient/Reactor Netty，无 OpenAI SDK；读取 `campusmate.base-url/endpoints/model`。 | 改名为 `CampusMateProvider`，ID 改为 `campusmate`；独立 HTTP 调用链保留。 |
| J-AI-03 | `modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateChatRequestMapper.java`：`map/appendOptions`；`MateChatSseParser.java`：`accept/parseReasoning/parseUsage/finish`；`MateReasoningSignature.java`：`encode/decode`（后两者同目录） | 已有独立 Chat JSON 映射、文本/工具/推理 SSE、Usage、签名重放与取消终态。 | 保留这些实现；不再要求从待删除的 OpenAI Provider 提取 Mapper。 |
| J-AI-04 | `modules/ai/src/main/java/com/campusclaw/ai/provider/anthropic/AnthropicProvider.java`、`provider/openai/OpenAICompletionsProvider.java`、`provider/openai/OpenAIResponsesProvider.java`、`provider/mistral/MistralProvider.java`（后三者相对同一 `ai/` 包）：类声明及 `stream/streamSimple` | 四个 Spring API 适配器仍随产品源码交付。 | 删除四个适配器及专属测试；保留 `ApiProvider` 抽象。 |
| J-AI-05 | `modules/ai/src/main/java/com/campusclaw/ai/model/ModelRegistry.java`：`init/builtInModels/register/getAllModels/loadFromJsonFile/calculateCost`；`types/Provider.java`、`types/Api.java`（相对同一 `ai/` 包）：enum | 自动加载第三方模型预置，再加载 classpath 与用户 JSON；Provider/API 仍为 enum。 | 当前目标删除预置、全局注册表和外部 JSON；只把仍有消费者的成本计算迁到窄职责位置，Provider/API enum 不因本次模型来源收敛而改造。 |
| J-AI-06 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/model/MateRuntimeModelManager.java`：`resolveModel/listAvailableModels`；`runtimeapi/RuntimeApiConfiguration.java`：`mateRuntimeModelManager`（同一 `codingagent/` 包） | Runtime 使用 Agent 快照中的模型 ID 构造 Mate Model，未通过第三方预置目录选择模型。 | 沿用模型来源，构造 `Provider.CAMPUSMATE`；不新增目录 HTTP 调用。 |
| J-AI-07 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEntryCodec.java`：`assistantEntry/assistantMessage`；`session/compaction/SessionCompactor.java`：`sameModel`；`tool/agent/SubagentExecutionService.java`、`tool/cron/ManagedCronSessionRunner.java`：模型匹配（均相对同一 `codingagent/` 包） | 历史 `_provider` 保存字符串；压缩、Child/Cron 有按 Provider 与模型 ID 的匹配。 | 新写入统一使用 `campusmate`；旧历史保留原值，不做同身份归一或匹配兼容。 |
| J-AI-08 | `pom.xml`、`modules/ai/pom.xml`、`campusclaw/pom.xml`：LLM SDK dependencies；`scripts/sync-campusclaw.sh`：镜像同步 | canonical 与公司镜像均声明两个 SDK，镜像 Java 从 modules 生成。 | 同步移除 SDK 声明和版本管理；更改后生成镜像并单独编译验证。 |

在该提交中，Mate 调用链已存在；Provider 改名、删除适配器及预置数据仍是 target-only。最新实现未在本次文档整理中重新验收。

## 4. Mate Chat 服务端

mate-service 基线 `956b547f` 已实现 Chat 调用：

- `src/main/java/com/huawei/hicampus/mate/agentdefinition/modelmanager/controller/LlmChatController.java:35-55`
  以 `CHAT_PATH` 实现 `POST /mate-service/v1/LLM/chat`；
- `LlmChatController.createChat` 接收 JSON，成功返回 `text/event-stream`，并由
  `LlmChatService` 创建上游调用；
- 模型目录接口 1-3 未在该基线发现，当前设计也不再引入这些接口；
- Mate 内部上游路由、凭据和 Usage 持久化仍不由本文规定。

Chat 服务端行为已在该提交观察到，精确契约已冻结；模型目录由业务 Agent 设置快照承担，不新增目录接口。

## 5. Thinking 与 Usage 的独立核验范围

- Thinking：`pi-mono-java@4cc8dd86f601417c22cf9306e52152acbb59bb60`，`modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateChatSseParser.java` 的 `parseReasoning/appendReasoningText/finishThinking`；可读文本与签名分别输出，Runtime 展示差距见[Thinking 主设计](../../01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md#thinking-original-text)。
- Usage SQL：`pi-mono-java@d649866a6cae967ace18ceaeb9597edd47e5721e`，`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEntryCodec.java` 的 `assistantEntry/assistantMessage`、`persistence/MyBatisRuntimeSessionRepository.java` 的 `appendLocked`（同一 `runtimeapi/` 包）、`modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql`；该提交集中式投影丢失 Usage，尚无 Record/Stats 写入链。此历史差距不作为最新实现缺陷，目标事务与验收见[Usage 设计](usage-persistence.md)。

## 6. 概念下钻

- [身份关系图](provider_identity_model.svg)：Provider、模型与协议身份的区别；[PlantUML 源码：`provider_identity_model`](diagram.puml#L1) · [原尺寸 SVG](provider_identity_model.svg)。
- [职责边界图](generic_provider_boundary.svg)：Runtime 选择与持久化、AI 适配、Mate 调用的边界；[PlantUML 源码：`generic_provider_boundary`](diagram.puml#L32) · [原尺寸 SVG](generic_provider_boundary.svg)。

## 7. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.1.0 | 2026-09-17 | 核验最新 pi 与 Java 模型来源，记录业务 Agent 设置唯一权威及旧全局目录删除差距。 |
| 1.0.0 | 2026-09-14 | 集中模型与 Provider 固定源码证据和实现差距。 |
