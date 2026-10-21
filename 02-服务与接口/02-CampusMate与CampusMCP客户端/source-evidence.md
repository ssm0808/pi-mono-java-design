# CampusMate 与 CampusMCP 客户端：源码证据

版本：1.0.0 · 2026-09-14。返回[主设计](README.md)。

Java 固定基线为 `320d790726a70aada6100052952d5494d2a378ac`；Mate 服务端为 `956b547f5ca12ca89e68f73012f92a4406b0c9fa`。以下差距只描述相应提交，不能推断最新实现。

## 1. 基线中的客户端配置

| 源码证据 | 已观察行为 |
|---|---|
| `modules/coding-agent-cli/src/main/resources/application.yml:89-108` | Model Manager 和 Runtime 分别声明 `campusmate.model-manager.base-url` 与 `campusmate.runtime.base-url`。 |
| `application.yml:129-140` | Tool 客户端另用顶层 `mate.innerGWSerive` 和 `mate.endpoints.*`。 |
| `modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateServiceModelManagerProvider.java:68-90` | Chat Provider 从 `campusmate.model-manager` 读取专属 base URL、Chat path、API 与传输超时，校验错误也使用该旧前缀。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/model/MateModelManagerProperties.java:17-24` | 模型能力默认值通过 `@ConfigurationProperties(prefix = "campusmate.model-manager")` 绑定。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/AgentRuntimeProperties.java:15-34`、`runtime/MateServiceClient.java:43-69,76-113,184-197` | Runtime 客户端从 `campusmate.runtime` 读取另一 base URL 及 Agent/Skill 路径。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/config/MateToolAutoConfiguration.java:31-81` | Tool 客户端从 `mate.innerGWSerive` 与 `mate.endpoints.*` 注入第三套配置。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/HttpMateToolClient.java:41-87,132-190,299-373` | Agent、Skill、Tool metadata 与 execute 请求都发送到该 Tool 地址；当前发现与 execute 都使用原三项 Mate 凭据。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java:61-69`、`RuntimeRequestContext.java:45-49`、`common/dto/RequestHeaderInfo.java:81-90` | 当前 Runtime 只捕获 `X-HW-ID`、`Authorization`、`X-HW-APPKEY`；既有 access token 出站名是 `X-Access-Token`，与目标 `access-token` 不同且未赋值。 |
| `mate-campusclaw/src/main/resources/application.properties:70-102` | 镜像 properties 重复了相同的三套地址和分散路径配置。 |
| `mate-campusclaw/scripts/install_value.sh:27-38` | 部署变量 `CAMPUSINNERGWSERVICE_DOMAIN_NAME_URL` 被转换为拼写错误的 `MATE_INNERGWSERIVE`。 |

以上均是基线代码的 **已观察行为**。同一 CampusMate 服务在客户端配置中被表达成
`campusmate.model-manager`、`campusmate.runtime` 和顶层 `mate` 三个身份。

## 2. 重复路径的源码依据

盘点范围是三个出站客户端当前实际构造的 URL。把路径前缀与 `%s` 模板统一规范化后，
该基线共有 7 个路径配置，但只有 6 个唯一 HTTP operation：

| Method | 规范化 Path | 当前配置键 | 消费符号 | 判定 |
|---|---|---|---|---|
| `POST` | `/mate-service/v1/LLM/chat` | `campusmate.model-manager.chat-path` | `MateServiceModelManagerProvider.eventFlux` | 唯一 |
| `GET` | `/mate-service/v1/agents/{agentId}` | `mate.endpoints.agent-info-path-prefix` | `HttpMateToolClient.queryToolIdsByAgentId` | 唯一；与 Runtime path 返回用途不同 |
| `GET` | `/mate-service/v1/agents/{agentId}/runtime` | `campusmate.runtime.agent-runtime-path-template` | `MateServiceClient.getAgentRuntime` | 唯一 |
| `GET` | `/mate-service/v1/skill/query/{skillId}` | `campusmate.runtime.skill-info-query-path-template` | `MateServiceClient.querySkillInfo` | **重复项 A** |
| `GET` | `/mate-service/v1/skill/query/{skillId}` | `mate.endpoints.skill-tools-query-path-prefix` | `HttpMateToolClient.queryToolIdsBySkillId` | **重复项 B** |
| `POST` | `/mate-service/v1/runtime/tools/query` | `mate.endpoints.tool-metadata-query-path` | `HttpMateToolClient.queryToolMetaByIds` | 唯一 |
| `POST` | `/mate-service/v1/runtime/tools/{toolId}/execute` | `mate.endpoints.tool-execute-path-template` | `HttpMateToolClient.invokeTool` | 唯一 |

Skill 两项是同一个 operation：method 和规范化 path 完全相同，两个客户端只是从同一
Skill 响应中读取不同字段。`SkillInfoResult` 的类注释也明确把它对齐到
`MateServiceClient.SkillInfo` 的真实契约。因此目标只保留一个
`campusmate.endpoints.skill-info-path-template`，两个客户端共同读取。

`GET /agents/{agentId}` 与 `GET /agents/{agentId}/runtime` 不是重复。前者为 Tool 发现读取
Agent 绑定工具，后者为受管 Runtime 准备读取完整运行配置；不能因为 path 前缀相同而合并。

另有一项源码文档漂移：
`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/dto/SkillBindingTool.java:13`
仍写作 `/skill/info/query/{skillId}`，而实际配置和调用是 `/skill/query/{skillId}`。
实现迁移时应同步修正文档，但不能据此创建第七个 endpoint。

## 3. Mate 服务端范围

mate-service 基线 `956b547f` 已观察到：

- `LlmChatController.CHAT_PATH` 实现 `POST /mate-service/v1/LLM/chat`；
- `AgentDefinitionController` 实现 `GET /mate-service/v1/agents/{agentId}` 和
  `GET /mate-service/v1/agents/{agentId}/runtime`；
- 同一 Controller 还实现 Agent list 与 update，但该基线三个出站客户端不消费它们，
  因此不纳入本次客户端 endpoint 目录；
- 该基线未发现 Skill query、Tool metadata query 或 Tool execute Controller。

所以 Chat 与两个 Agent operation 是 **已实现服务端行为**；Skill 与 Tool 三个 operation
是 pi-mono-java 客户端已经依赖、但在所分析 mate-service 仓库中未找到对应 Controller 的
契约。最新服务端未复核；客户端存在不能证明相应 Controller 已实现。
