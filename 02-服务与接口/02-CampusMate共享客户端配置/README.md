# CampusMate 统一配置与 Endpoint 目录设计

| 属性 | 值 |
|---|---|
| 文档版本 | 2.2.0 |
| 状态 | 目标设计；统一配置与“发现无凭据、仅 Tool execute 透传”待实现 |
| 设计日期 | 2026-08-27 |
| pi-mono-java 源码基线 | `320d790726a70aada6100052952d5494d2a378ac` |
| mate-service 源码基线 | `956b547f5ca12ca89e68f73012f92a4406b0c9fa` |
| 设计仓分析基线 | `e641fefdc9b58adb0054d6e548d313d01a69b94d` |
| 适用边界 | CampusClaw -> CampusMate Model Manager、受管 Runtime 与 Tool 接口 |

## 1. 结论

Mate 和 CampusMate 是同一个服务。目标配置不能再用顶层 `mate` 表达第二套服务身份，
也不能把同一个 HTTP operation 分散为两个路径配置。所有连接与路径统一归入一个
`campusmate` 配置树：

```yaml
campusmate:
  base-url: ${CAMPUSMATE_BASE_URL}
  endpoints:
    model-chat-path: ${CAMPUSMATE_MODEL_CHAT_PATH:/mate-service/v1/LLM/chat}
    agent-info-path-template: ${CAMPUSMATE_AGENT_INFO_PATH_TEMPLATE:/mate-service/v1/agents/%s}
    agent-runtime-path-template: ${CAMPUSMATE_AGENT_RUNTIME_PATH_TEMPLATE:/mate-service/v1/agents/%s/runtime}
    skill-info-path-template: ${CAMPUSMATE_SKILL_INFO_PATH_TEMPLATE:/mate-service/v1/skill/query/%s}
    tool-metadata-query-path: ${CAMPUSMATE_TOOL_METADATA_QUERY_PATH:/mate-service/v1/runtime/tools/query}
    tool-execute-path-template: ${CAMPUSMATE_TOOL_EXECUTE_PATH_TEMPLATE:/mate-service/v1/runtime/tools/%s/execute}
  model:
    api: ${CAMPUSMATE_MODEL_API:openai-completions}
    connect-timeout: ${CAMPUSMATE_MODEL_CONNECT_TIMEOUT:PT10S}
    response-timeout: ${CAMPUSMATE_MODEL_RESPONSE_TIMEOUT:PT10M}
    context-window: ${CAMPUSMATE_MODEL_CONTEXT_WINDOW:128000}
    max-output-tokens: ${CAMPUSMATE_MODEL_MAX_OUTPUT_TOKENS:8192}
    reasoning: ${CAMPUSMATE_MODEL_REASONING:true}
  runtime:
    agents-root: ${CAMPUSCLAW_AGENTS_ROOT:agent}
    connect-timeout: ${CAMPUSMATE_RUNTIME_CONNECT_TIMEOUT:PT10S}
    request-timeout: ${CAMPUSMATE_RUNTIME_REQUEST_TIMEOUT:PT30S}
    success-code: ${CAMPUSMATE_SUCCESS_CODE:0}
    max-response-bytes: ${CAMPUSMATE_MAX_RESPONSE_BYTES:4194304}
  tool:
    enabled: ${CAMPUSMATE_TOOL_ENABLED:true}
```

目标状态具有三个硬约束：

1. `campusmate.base-url` 是唯一 origin 权威；
2. `campusmate.endpoints` 是唯一出站路径目录；
3. 模型协议、能力与传输参数只放在 `campusmate.model`；
4. 目标配置中不存在顶层 `mate`、`mate.endpoints`、`mate.tool` 或
   `campusmate.model-manager`。

这是一项 **架构改造**。HTTP method、path、请求/响应、SSE 和超时语义不因
配置归并而改变。凭据边界按 Runtime HTTP 1.42 另行收紧：Agent、Skill 与 Tool
metadata 发现无凭据，仅 Tool execute 透传 POST Events execution 快照中已提供的
`X-HW-ID`、`Authorization`、`X-HW-APPKEY` 和 `access-token`。

## 2. 源码观察

### 2.1 当前地址与命名空间分裂

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

### 2.2 Endpoint 去重结果

盘点范围是三个出站客户端当前实际构造的 URL。把路径前缀与 `%s` 模板统一规范化后，
当前共有 7 个路径配置，但只有 6 个唯一 HTTP operation：

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

### 2.3 mate-service 服务端证据

mate-service 基线 `956b547f` 已观察到：

- `LlmChatController.CHAT_PATH` 实现 `POST /mate-service/v1/LLM/chat`；
- `AgentDefinitionController` 实现 `GET /mate-service/v1/agents/{agentId}` 和
  `GET /mate-service/v1/agents/{agentId}/runtime`；
- 同一 Controller 还实现 Agent list 与 update，但当前三个出站客户端不消费它们，
  因此不纳入本次客户端 endpoint 目录；
- 该基线未发现 Skill query、Tool metadata query 或 Tool execute Controller。

所以 Chat 与两个 Agent operation 是 **已实现服务端行为**；Skill 与 Tool 三个 operation
是 pi-mono-java 客户端已经依赖、但在所分析 mate-service 仓库中未找到对应 Controller 的
契约。后者必须标为服务端待补齐，不能写成已实现行为。

## 3. 修改前后可视化

![CampusMate 配置与 Endpoint 去重](campusmate_shared_base_url_configuration.svg)

[PlantUML 源码：`campusmate_shared_base_url_configuration`](diagram.puml#L1)

图中的关键变化是：三个服务身份收敛为一个 `campusmate`，模型配置分组从组件式命名
`model-manager` 简化为能力式命名 `model`，7 个路径配置收敛为 6 个唯一 endpoint；Runtime
与 Tool 客户端共同引用唯一 Skill path。

## 4. 配置责任

| 配置 | 责任 | 禁止事项 |
|---|---|---|
| `campusmate.base-url` | CampusMate scheme、host、port | 子模块覆盖 origin |
| `campusmate.endpoints.*` | 当前 CampusClaw 消费的 6 个 HTTP operation path | 完整 URL、重复 operation、客户端私有副本 |
| `campusmate.model.*` | API 适配、模型能力默认值、SSE 传输参数 | 保存 URL 或 path |
| `campusmate.runtime.*` | 本地缓存、短请求超时、成功码与响应上限 | 保存 URL 或 path |
| `campusmate.tool.enabled` | 是否装配 Tool 能力 | 决定 URL 或 path |

共享配置不意味着共享 HTTP Client 实例或 DTO。Model Manager 保留 WebClient/SSE；Runtime
保留 JDK HttpClient、响应大小限制与完整 Skill DTO；Tool 客户端保留发现缓存，但发现请求不接收执行凭据；仅 execute 方法接收执行快照
和轻量 Skill 投影。两个客户端可以用不同 DTO 读取同一个 Skill operation，但不能各自
维护其 path。

`ListMateTools`、`CallMateTool`、`MateToolClient` 等名称是既有模型/Java 契约，不是
Spring 服务命名空间。本主题不为了配置归并破坏工具名；若产品需要把模型可见工具改名，
应独立评审 Schema、提示词与兼容性。

## 5. URL 与 Path 规则

`campusmate.base-url` 在启动时本地校验：

1. 必须是绝对 URI，scheme 只能为 `http` 或 `https`；
2. 必须有 host，不允许 user-info、query 或 fragment；
3. path 必须为空或 `/`；
4. 规范化只移除末尾 `/`，不改写 host 或 port；
5. 无产品级默认值，部署必须显式提供。

每个 endpoint path 必须：

1. 以 `/mate-service/` 开头；
2. 不是完整 URL；
3. `{agentId}`、`{skillId}`、`{toolId}` 对应的配置统一使用一个 `%s`；
4. 不能包含 query、fragment、`..` 或第二个 origin；
5. 同一 method + 规范化 path 只能有一个配置键。

终端地址固定为：

```text
endpoint = normalized(campusmate.base-url) + validated(campusmate.endpoints.<operation>)
```

这些规则属于 **安全加固**，防止某一客户端通过 path 配置改道到其他主机。

## 6. 配置迁移

| 当前配置 | 目标配置 | 处理 |
|---|---|---|
| `campusmate.model-manager.base-url` / `CAMPUSMATE_MODEL_MANAGER_BASE_URL` | `campusmate.base-url` / `CAMPUSMATE_BASE_URL` | 删除独立地址 |
| `campusmate.runtime.base-url` / `CAMPUSMATE_RUNTIME_BASE_URL` | `campusmate.base-url` / `CAMPUSMATE_BASE_URL` | 删除独立地址 |
| `mate.innerGWSerive` / `MATE_INNERGWSERIVE` | `campusmate.base-url` / `CAMPUSMATE_BASE_URL` | 删除历史拼写与顶层 `mate` |
| `campusmate.model-manager.chat-path` | `campusmate.endpoints.model-chat-path` | 路径移入统一目录 |
| `campusmate.model-manager.api` / `CAMPUSMATE_MODEL_MANAGER_API` | `campusmate.model.api` / `CAMPUSMATE_MODEL_API` | 配置分组改为模型能力语义；不保留兼容别名 |
| `campusmate.model-manager.connect-timeout` / `CAMPUSMATE_MODEL_MANAGER_CONNECT_TIMEOUT` | `campusmate.model.connect-timeout` / `CAMPUSMATE_MODEL_CONNECT_TIMEOUT` | 同步迁移模型连接超时 |
| `campusmate.model-manager.response-timeout` / `CAMPUSMATE_MODEL_MANAGER_RESPONSE_TIMEOUT` | `campusmate.model.response-timeout` / `CAMPUSMATE_MODEL_RESPONSE_TIMEOUT` | 同步迁移模型流响应超时 |
| `campusmate.model-manager.context-window` / `CAMPUSMATE_MODEL_MANAGER_CONTEXT_WINDOW` | `campusmate.model.context-window` / `CAMPUSMATE_MODEL_CONTEXT_WINDOW` | 同步迁移模型能力默认值 |
| `campusmate.model-manager.max-output-tokens` / `CAMPUSMATE_MODEL_MANAGER_MAX_OUTPUT_TOKENS` | `campusmate.model.max-output-tokens` / `CAMPUSMATE_MODEL_MAX_OUTPUT_TOKENS` | 同步迁移模型能力默认值 |
| `campusmate.model-manager.reasoning` / `CAMPUSMATE_MODEL_MANAGER_REASONING` | `campusmate.model.reasoning` / `CAMPUSMATE_MODEL_REASONING` | 同步迁移推理能力开关 |
| `mate.endpoints.agent-info-path-prefix` | `campusmate.endpoints.agent-info-path-template` | 移入统一目录并用 `%s` 模板 |
| `campusmate.runtime.agent-runtime-path-template` | `campusmate.endpoints.agent-runtime-path-template` | 路径移入统一目录 |
| `campusmate.runtime.skill-info-query-path-template` | `campusmate.endpoints.skill-info-path-template` | 与下一项合并 |
| `mate.endpoints.skill-tools-query-path-prefix` | `campusmate.endpoints.skill-info-path-template` | 删除重复键并用 `%s` 模板 |
| `mate.endpoints.tool-metadata-query-path` | `campusmate.endpoints.tool-metadata-query-path` | 只改服务命名空间 |
| `mate.endpoints.tool-execute-path-template` | `campusmate.endpoints.tool-execute-path-template` | 只改服务命名空间 |
| `mate.tool.enabled` | `campusmate.tool.enabled` | Tool 能力归入 CampusMate |

不保留旧键优先级或 fallback。否则配置仍可分流或让重复 Skill path 产生不同值。
部署平台若继续提供 `CAMPUSINNERGWSERVICE_DOMAIN_NAME_URL`，只能在安装边界转换成
`CAMPUSMATE_BASE_URL`；若两者同时存在且不同，部署校验必须失败。

## 7. Java 目标映射

| 当前符号 | 目标调整 |
|---|---|
| `MateServiceModelManagerProvider` | 注入 `${campusmate.base-url}`、`${campusmate.endpoints.model-chat-path}` 及 `campusmate.model` 下的 API/超时参数；Provider 协议语义不变 |
| `MateModelManagerProperties` | 绑定前缀从 `campusmate.model-manager` 改为 `campusmate.model`；类名表达 Model Manager 组件，可保留 |
| `AgentRuntimeProperties` | 删除 `baseUrl`；只绑定 `campusmate.runtime` 的非 endpoint 参数 |
| `MateServiceClient` | 注入共享 base URL，以及统一目录中的 Agent Runtime 与 Skill path |
| `MateToolAutoConfiguration` | 条件键改为 `campusmate.tool.enabled`；读取共享 base URL 和统一 endpoint 目录，不再读取任何 `mate.*` |
| `HttpMateToolClient` | Agent 与 Skill 前缀参数改为 `%s` path template；Skill path 与 Runtime client 读同一配置键；Agent/Skill/metadata 发现方法不接收凭据，仅 execute 接收不可变的四项 execution 凭据快照 |
| `MateToolProperties` | 绑定前缀改为 `campusmate.tool`；类名可保留以避免无关 Java API 改名 |
| `MateRestUtil` | 参数和诊断术语改为 CampusMate base URL；传输行为不变 |
| canonical YAML 与镜像 properties | 只保留一个 `campusmate` 根和一个 Skill endpoint 键 |
| 配置与客户端测试 | 断言 7 个旧路径配置归并为 6 个唯一 operation，并拒绝旧 `mate.*` 绑定 |

不同 Maven 模块不必为了共享一个属性对象形成反向依赖；它们可以分别注入相同的
`campusmate.*` 属性。唯一权威是配置键与启动校验，不是某个客户端类。

## 8. 差异分类

| 分类 | 目标差异 | 原因 |
|---|---|---|
| 产品约束 | Mate 与 CampusMate 只表达一个服务身份。 | 部署中不存在第二个 Mate 服务 origin。 |
| 架构改造 | 删除顶层 `mate`，全部配置统一到 `campusmate`。 | 避免服务命名和地址权威分裂。 |
| 架构改造 | 模型参数从 `campusmate.model-manager` 改为 `campusmate.model`。 | 配置树描述能力域，不重复暴露 Model Manager 组件名。 |
| 架构改造 | 建立 `campusmate.endpoints`，把 7 个配置归并为 6 个唯一 operation。 | path 属于服务契约，不属于某个客户端。 |
| 架构改造 | Runtime 与 Tool client 共享一个 Skill endpoint 配置。 | 两者调用相同 method/path 与响应契约。 |
| 安全加固 | base URL 只允许 HTTP(S) origin，path 不能携带 origin。 | 防止单客户端改道。 |
| 安全加固 | Agent/Skill/metadata 发现无凭据，仅 Tool execute 透传 POST Events execution 快照。 | 将凭据可见面限制到真正执行工具的单一端点。 |
| 产品约束 | 模型可见 Mate Tool 名称暂不改。 | 工具契约与服务配置命名是不同兼容边界。 |

## 9. 实施顺序

1. 增加统一 `campusmate.base-url`、`campusmate.endpoints`、`campusmate.model` 与启动校验；
2. 同一提交让 Model Manager、Runtime 和 Tool 三类客户端切换到新键，并将全部
   `CAMPUSMATE_MODEL_MANAGER_*` 环境变量迁移为 `CAMPUSMATE_MODEL_*`；
3. 合并 Skill path 消费点，Agent/Skill ID 路径统一改用 `%s` 模板；
4. 将 `mate.tool.enabled` 迁入 `campusmate.tool.enabled`；
5. 删除 `mate.*`、三个旧地址变量、旧 path 变量和部署脚本转换；
6. 同步 canonical YAML、镜像 properties、README、DTO 注释和配置/客户端测试；
7. 补充端到端断言：三个客户端 origin 相同、Skill endpoint 只解析一次且两种消费均成功。

## 10. 验收标准

- 目标配置源中只有一个顶层 `campusmate`，不存在顶层 `mate`；
- 模型参数只存在于 `campusmate.model.*`，目标配置和环境变量中不存在
  `campusmate.model-manager.*` 或 `CAMPUSMATE_MODEL_MANAGER_*`；
- 只有 `campusmate.base-url` / `CAMPUSMATE_BASE_URL` 能决定 CampusMate origin；
- 只有 `campusmate.endpoints` 能决定当前 6 个出站 operation path；
- `GET /mate-service/v1/skill/query/{skillId}` 只有一个配置键，并由 Runtime 与 Tool client 共用；
- `GET /agents/{agentId}` 与 `GET /agents/{agentId}/runtime` 保持两个独立 operation；
- `mate.innerGWSerive`、`mate.endpoints.*`、`mate.tool.enabled` 及所有 `MATE_*` 应用变量删除；
- canonical YAML 与镜像 properties 绑定等价；
- base URL 或 path 非法时启动失败且不发送网络请求；
- Chat、Runtime、Tool 请求使用相同 scheme、host、port；
- HTTP method/path、请求/响应、SSE、超时与 execute 不重放语义保持不变；
- Agent、Skill 和 Tool metadata 发现请求不含四项 execution Header；
- 仅 Tool execute 透传 POST Events 快照中已提供的四项 Header，且 `access-token`
  不被改写为 `X-Access-Token`；
- 服务端尚未实现的 Skill/Tool Controller 仍明确标记为待补齐，不因客户端配置存在而宣称已实现。

## 11. 文档同步范围

本主题同步修订：

- [模型管理 Provider 契约](../03-模型管理Provider契约/README.md)：Chat path 改读统一 endpoint 目录，并更新 mate-service Chat 已实现证据；
- [CampusClaw 工具系统](../../01-总体架构/02-CampusClaw工具系统/README.md)：Tool 配置统一到 `campusmate`，Skill path 与 Runtime 去重，并固定发现无凭据、仅 execute 透传；
- 仓库根 README：将主题描述更新为统一配置与 endpoint 去重。

Model Manager operation JSON 没有变化。Runtime POST Events operation JSON 与 HTML 因新增
`access-token` Header 已在 Runtime HTTP 1.42 中重新生成。

## 12. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.2.0 | 2026-08-27 | 同步 Runtime HTTP 1.42 的凭据边界：Agent/Skill/Tool metadata 发现无凭据，只有 Tool execute 原名透传 POST Events execution 快照中已提供的四项 Header。 |
| 2.1.0 | 2026-08-26 | 将目标模型配置分组从 `campusmate.model-manager` 简化为 `campusmate.model`，同步 `CAMPUSMATE_MODEL_*` 环境变量、Java 绑定、迁移规则和可视化；Model Manager 组件名与 `mate-model-manager` Provider ID 不变。 |
| 2.0.0 | 2026-08-26 | 按 Mate 与 CampusMate 是同一服务的约束删除顶层 `mate`；新增统一 `campusmate.endpoints`，将 7 个路径配置归并为 6 个唯一 operation，并去重 Skill 查询路径。 |
| 1.1.0 | 2026-08-26 | 将 `mate.innerGWSerive` 纳入共享 base URL，但仍保留顶层 `mate.endpoints`。 |
| 1.0.0 | 2026-08-26 | 新增 CampusMate 统一 `campusmate.base-url` 设计。 |
