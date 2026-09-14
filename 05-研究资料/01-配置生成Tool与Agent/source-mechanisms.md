# 配置生成 Tool 与 Agent：逐项目证据

> 资料核验日期：2026-07-18；固定源码提交逐项登记。文档整理日期：2026-09-14。
> 各产品事实限于原核验范围；本专题的候选规范不属于 CampusClaw 已确认设计。

[返回研究入口](./README.md)

## 4. 逐项目研究结果

### 4.1 Anthropic 产品族：Claude Code、Claude API 与 Managed Agents

**观察到的 Tool 行为**

- Claude API 的 Tool 定义包含名称、描述和 `input_schema`，但这只是模型与应用之间的调用契约。官方明确区分客户端 Tool 与服务端 Tool：客户端 Tool 由应用执行，服务端 Tool 由 Anthropic 基础设施执行。[How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works)、[Tool reference](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-reference)
- Managed Agents 的 custom tool 同样只产生结构化调用；官方文档明确写明应用在外部执行后回传结果。[Managed Agents tools](https://platform.claude.com/docs/en/managed-agents/tools)
- Claude Code 的自定义外部 Tool 主要通过 MCP 增加；`.mcp.json`/CLI 配置负责连接 stdio 或 HTTP Server，Server 才是执行者。[Claude Code MCP](https://code.claude.com/docs/en/mcp)
- 类图中的 `AnthropicClientToolContract` 是依据上述公开字段建立的**归一化概念类**，不是 Claude Code 源码中的类型，也不是 Anthropic 官方公布的类名。Claude Code 的公开仓库采用 proprietary/commercial 条款，不能据此声称已获得其内部 Tool 实现源码。[Claude Code repository](https://github.com/anthropics/claude-code)、[license](https://github.com/anthropics/claude-code/blob/main/LICENSE.md)

**观察到的 Agent 行为**

- Claude Code 扫描 `~/.claude/agents/` 和 `.claude/agents/`。文件为 YAML frontmatter + Markdown body，body 成为 system prompt；frontmatter 可含 `name`、`description`、`tools`、`disallowedTools`、`model`、`permissionMode`、`mcpServers`、`hooks`、`maxTurns`、`skills`、`memory`、`effort`、`background`、`isolation` 等。[Claude Code subagents](https://code.claude.com/docs/en/sub-agents)
- `--agents` 可用 JSON 在单次会话中注入同一组字段；`--agent` 可让一个定义成为主会话 Agent。
- Managed Agents 把 `name`、`model`、`system`、`tools`、`mcp_servers`、`skills`、`multiagent`、`description`、`metadata` 保存为有 ID 和递增 version 的资源。[Define your agent](https://platform.claude.com/docs/en/managed-agents/agent-setup)
- Managed MCP 设计把可复用的 Server URL 声明留在 Agent，把认证留在 Session/vault，这直接支持本文的 Manifest/Binding 分层。[Managed Agents MCP connector](https://platform.claude.com/docs/en/managed-agents/mcp-connector)

**结论**

- Claude Code Agent：达到 A1；外部任意 Tool 通过 MCP 达到 T2。
- Managed Agents：达到 A2；托管 Tool 达到 T4。
- Anthropic 客户端 Custom Tool：描述本身只有 T0，应用仍须执行。该契约不能当作 Claude Code 内部 `ToolDefinition` 的源码证据。

### 4.2 Codex

**观察到的 Tool 行为**

- `DynamicToolFunctionSpec` 只保存 `name`、`description`、`input_schema` 和 `defer_loading`。[源码：dynamic_tools.rs](https://github.com/openai/codex/blob/315195492c80fdade38e917c18f9584efd599304/codex-rs/protocol/src/dynamic_tools.rs#L10-L27)
- Dynamic Tool handler 把描述注册成模型工具，但调用发生后会创建 pending request 并等待 App Server 客户端回传 `DynamicToolResponse`；它没有从 metadata 推导业务逻辑。[源码：dynamic.rs](https://github.com/openai/codex/blob/315195492c80fdade38e917c18f9584efd599304/codex-rs/core/src/tools/handlers/dynamic.rs#L113-L177)
- App Server 文档也明确要求客户端响应 `item/tool/call`。因此它是“host-provided dynamic callback”，不是 metadata-only executor。[App Server dynamic tool calls](https://github.com/openai/codex/blob/315195492c80fdade38e917c18f9584efd599304/codex-rs/app-server/README.md#dynamic-tool-calls-experimental)
- MCP Tool 则由 Codex 自动适配为模型 Tool，再转发给已存在的 MCP Server。

**观察到的 Agent 行为**

- Codex 从配置层的 `agents` 目录发现 TOML role 文件，合并同名角色的低优先级缺省值，并验证描述。[源码：load_agent_roles](https://github.com/openai/codex/blob/315195492c80fdade38e917c18f9584efd599304/codex-rs/core/src/config/agent_roles.rs#L19-L115)
- 独立 role 文件含 `name`、`description`、`nickname_candidates`，并 flatten 完整 `ConfigToml`；因此模型、推理强度、sandbox、MCP、skills 等普通 Codex 配置可作为 role 覆盖层。独立发现的文件必须含非空 `developer_instructions`。[源码：parse_agent_role_file_contents](https://github.com/openai/codex/blob/315195492c80fdade38e917c18f9584efd599304/codex-rs/core/src/config/agent_roles.rs#L218-L315)

**结论**

- Agent：达到 A1。
- Tool：dynamic metadata 只有 T0 + host callback；MCP 为 T2。若要纳入统一平台，应把 App Server 客户端回调建模为 `artifact` 或 `hostCallback` driver，而不是误称纯元数据执行。

### 4.3 OpenCode

**观察到的 Tool 行为**

- Tool Definition 要求 `id`、`description`、参数 Schema 和 `execute`；plugin Tool 最终也调用插件提供的 `def.execute`。[源码：tool.ts](https://github.com/anomalyco/opencode/blob/3a1c6df9e24672f0761a6ced18e1315d89334baf/packages/opencode/src/tool/tool.ts#L55-L64)、[源码：registry.ts](https://github.com/anomalyco/opencode/blob/3a1c6df9e24672f0761a6ced18e1315d89334baf/packages/opencode/src/tool/registry.ts#L120-L175)
- JS/TS 文件可以被动态导入为 Tool，但那是代码插件；MCP 配置可创建协议代理。

**观察到的 Agent 行为**

- Agent Schema 包含 `model`、`variant`、temperature、top_p、prompt、tools、description、mode、hidden、steps 和 permission 等。[源码：agent.ts schema](https://github.com/anomalyco/opencode/blob/3a1c6df9e24672f0761a6ced18e1315d89334baf/packages/core/src/v1/config/agent.ts#L12-L88)
- OpenCode 发现 `{agent,agents}/**/*.md` 与旧 mode 路径，解析 YAML frontmatter，并把 Markdown body 注入 system/prompt 配置。[源码：config plugin](https://github.com/anomalyco/opencode/blob/3a1c6df9e24672f0761a6ced18e1315d89334baf/packages/core/src/config/plugin/agent.ts#L20-L24)
- Runtime 把配置转成 Agent Info，并提供 list/get/default 选择。[源码：agent runtime](https://github.com/anomalyco/opencode/blob/3a1c6df9e24672f0761a6ced18e1315d89334baf/packages/opencode/src/agent/agent.ts#L35-L55)

**结论**

- Agent：A1。
- Tool：T1；MCP 时 T2。OpenCode 证明 Markdown Agent Manifest 很实用，但没有通用声明式 Tool driver。

### 4.4 Cline

**观察到的 Tool 行为**

- Cline SDK 明确把 Tool descriptor 与实现分开：`AgentToolDefinition` 只有 `name`、`description`、`inputSchema`；`AgentTool` 在此基础上增加 `execute`。[源码：sdk shared agent.ts](https://github.com/cline/cline/blob/c564045d8135c0c1c330b21d47b68b74917ce614/sdk/packages/shared/src/agent.ts#L146-L186)
- 这给出了最直接的反例：descriptor 可注册给模型，但若没有实现对象就不能执行。MCP 仍属于 T2。

**观察到的 Agent 行为**

- Configured Agent 文件使用 Markdown/YAML frontmatter，字段包括 `name`、`description`、`tools`、`skills`、`providerId`、`modelId`、`maxIterations`，body 是 system prompt。[源码：configured-agent-config.ts](https://github.com/cline/cline/blob/c564045d8135c0c1c330b21d47b68b74917ce614/sdk/packages/core/src/extensions/tools/team/configured-agent-config.ts#L8-L28)
- Loader 解析并加载这些定义；`configured-agent-tool.ts` 再把 Agent 配置变成一个 subagent Tool，Tool 的 `execute` 创建并运行委派 Agent。[源码：configured-agent-tool.ts](https://github.com/cline/cline/blob/c564045d8135c0c1c330b21d47b68b74917ce614/sdk/packages/core/src/extensions/tools/team/configured-agent-tool.ts#L113-L138)
- Agent Runtime 可接收已构建模型，或根据 provider/model 配置创建模型。[源码：agent-runtime.ts](https://github.com/cline/cline/blob/c564045d8135c0c1c330b21d47b68b74917ce614/sdk/packages/agents/src/agent-runtime.ts#L82-L118)

**结论**

- Agent：A1。
- Tool：T1/T2。值得复用的设计是 `AgentManifest -> AgentProxyDriver -> Tool`，而不是把 Agent 的全部字段复制进 Tool。

### 4.5 Qwen Code

**观察到的 Tool 行为**

- 普通 Declarative Tool 仍有 builder/build 与执行代码。[源码：tools.ts](https://github.com/QwenLM/qwen-code/blob/0ecba4b3c709d271a17faa5ac9537bf1b102eaf1/packages/core/src/tools/tools.ts#L155-L245)
- MCP Tool 由 `DiscoveredMCPTool` 适配并转发到 MCP client `callTool`，属于 T2。[源码：mcp-tool.ts](https://github.com/QwenLM/qwen-code/blob/0ecba4b3c709d271a17faa5ac9537bf1b102eaf1/packages/core/src/tools/mcp-tool.ts#L349-L373)
- 关键机制是 Tool Discovery：平台执行 `discoveryCommand`，读取一组 function declarations，再注册 `DiscoveredTool`；调用时把 Tool 名称作为参数，并把 JSON arguments 写入 `callCommand` stdin。[源码：tool-registry.ts](https://github.com/QwenLM/qwen-code/blob/0ecba4b3c709d271a17faa5ac9537bf1b102eaf1/packages/core/src/tools/tool-registry.ts#L42-L181)、[配置文档](https://github.com/QwenLM/qwen-code/blob/0ecba4b3c709d271a17faa5ac9537bf1b102eaf1/docs/users/configuration/settings.md#L315-L331)
- 这已经是通用 Command Driver。开发人员仍要提供一个可执行程序，但不用为每个 Tool 编写 Qwen 插件适配代码。

**观察到的 Agent 行为**

- `SubagentConfig` 覆盖名称、描述、工具 allow/deny、审批、system prompt、模型、运行参数、颜色、后台、权限、max turns、MCP servers 和 hooks。[源码：types.ts](https://github.com/QwenLM/qwen-code/blob/0ecba4b3c709d271a17faa5ac9537bf1b102eaf1/packages/core/src/subagents/types.ts#L51-L175)
- `SubagentManager` 解析 Markdown YAML frontmatter；每个 Agent 可独立覆盖 MCP Server，并触发启动和 Tool discovery。[源码：subagent-manager.ts](https://github.com/QwenLM/qwen-code/blob/0ecba4b3c709d271a17faa5ac9537bf1b102eaf1/packages/core/src/subagents/subagent-manager.ts#L1359-L1560)

**结论**

- Tool：Command 路径达到 T3，MCP 路径 T2。
- Agent：A1/A3。Qwen 的 `discoveryCommand/callCommand` 应直接成为统一规范的 `command` implementation driver。

### 4.6 Kiro CLI

**观察到的 Tool 行为**

- Agent Profile 的 `tools` 选择的是类别标签、内置 Tool 或 MCP Tool；`mcpServers` 可内联定义 stdio/HTTP Server。[Kiro v3 Agent config](https://kiro.dev/docs/cli/v3/agent-config/)
- MCP 配置提供 command/args/env 或 URL/headers/OAuth，Kiro 负责生命周期与热重载；实际 Tool 由 MCP Server 暴露。[Kiro MCP configuration](https://kiro.dev/docs/cli/mcp/configuration/)
- 因此“增加一个任意 Tool”不能只写 Tool descriptor；必须是内置 Tool 或已有 MCP Server。

**观察到的 Agent 行为**

- v3 Profile 是 YAML frontmatter + Markdown body，也可用等价 JSON；示例字段包括 `description`、`model`、工具类别、内联 MCP、`resources`、`permissions`、`welcomeMessage`。
- 工作区目录为 `.kiro/agents/`，用户目录为 `~/.kiro/agents/`；嵌套路径形成 Agent 名称。权限规则采用 capability/effect/match，默认未命中为 ask。[Kiro v3 Agent config](https://kiro.dev/docs/cli/v3/agent-config/)

**结论**

- Agent：A1，且权限模型适合借鉴。
- Tool：T2；没有独立的 metadata-only arbitrary Tool driver。

### 4.7 Amp

**观察到的 Tool 行为**

- `amp.registerTool` 的定义同时包含 `name`、`description`、`inputSchema` 和 `execute`；插件是 Bun 执行的 TS/JS 程序。[Amp Plugin API](https://ampcode.com/manual/plugin-api)
- Amp 也支持 MCP 配置，因此已有 MCP Server 的 Tool 可以自动接入，但仍是 T2。

**观察到的 Agent 行为**

- `createAgent` 的 `CreateAgentConfig` 包含 `name`、`model`、`instructions`、tools include/exclude、reasoning effort 和 display；返回的 handle 可 `run` 或 `createThread`。[Amp Plugin API](https://ampcode.com/manual/plugin-api)
- Custom Agent 目前在 Plugin 程序中创建；注册主 Agent mode 还要求静态 `@amp-agent-mode` 元数据注释与 runtime registration 一致。它是结构化定义，但不是完全独立的 YAML/JSON 数据文件。
- 官方示例也展示了把 custom Agent 包装成 Tool：Tool `execute` 内调用 `reviewer.run(...)`。[Custom Agents](https://ampcode.com/news/custom-agents)

**结论**

- Agent：代码辅助的 A1。
- Tool：T1/T2。Amp 的 Agent handle 适合映射到本文的 `agentProxy` driver，但其 Plugin 本身仍是代码制品。

### 4.8 Grok Build

**观察到的 Tool 行为**

- xAI 源码要求每个注册 Tool 同时实现 runtime `Tool` 和 metadata `ToolMetadata`。`ToolMetadata` 的必需方法是 `kind`、`tool_namespace`、`description_template`；只读性与依赖表达式有默认实现。它不直接定义名称和参数 Schema。[源码：tool_metadata.rs](https://github.com/xai-org/grok-build/blob/8adf9013a0929e5c7f1d4e849492d2387837a28d/crates/codegen/xai-grok-tools/src/types/tool_metadata.rs#L1-L10)
- `versioned_definition` 的默认实现接收运行时导出的 `input_schema`，渲染描述模板并生成 `ToolDefinition`；因此 Grok 的模型可见定义来自 metadata 与 runtime Args Schema 的组合。[源码：tool_metadata.rs](https://github.com/xai-org/grok-build/blob/8adf9013a0929e5c7f1d4e849492d2387837a28d/crates/codegen/xai-grok-tools/src/types/tool_metadata.rs#L75-L102)
- `Tool` trait 通过关联类型 `Args`/`Output` 以及 `id`、`description`、`capabilities`、`should_list`、`execute`、`run` 提供模型契约和运行行为；因此 metadata 不会自行执行。[源码：tool.rs](https://github.com/xai-org/grok-build/blob/8adf9013a0929e5c7f1d4e849492d2387837a28d/crates/common/xai-tool-runtime/src/tool.rs#L32-L110)

**观察到的 Agent 行为**

- `.grok/agents/*.md` 被注释为 portable, version-control contract。配置覆盖名称、描述、prompt mode、Tool、capability、permission、skills、继承、effort、max turns、isolation、background、MCP、hooks、memory、model 和 completion requirement。[源码：config.rs](https://github.com/xai-org/grok-build/blob/8adf9013a0929e5c7f1d4e849492d2387837a28d/crates/codegen/xai-grok-agent/src/config.rs#L706-L817)
- Builder 从定义或代码配置构造 Agent；discovery 处理项目/用户范围与优先级。[源码：builder.rs](https://github.com/xai-org/grok-build/blob/8adf9013a0929e5c7f1d4e849492d2387837a28d/crates/codegen/xai-grok-agent/src/builder.rs#L24-L41)

**结论**

- Agent：A1/A3。
- Tool：T1/T2。`ToolMetadata`/`Tool` 的显式分离证明描述生成和运行行为是不同责任；本文再将它归一化为跨产品的 `descriptor`/`implementation`，这是目标设计而不是 Grok 原生字段映射。

### 4.9 OpenClaw

**观察到的 Tool 行为**

- Plugin registry 可以读取 manifest 的 `contracts.tools` 做静态所有权和发现检查，但 runtime 仍要求插件 factory 实际注册 Tool；静态 contract 与 runtime registration 不一致会被检查。[源码：registry registrar](https://github.com/openclaw/openclaw/blob/55bb6cfa2ec4863b5ece006aee70b5de6d967709/src/plugins/registry-registrars-tools-hooks.ts#L243-L293)、[Plugin manifest 文档](https://github.com/openclaw/openclaw/blob/55bb6cfa2ec4863b5ece006aee70b5de6d967709/docs/plugins/manifest.md#L568-L632)
- Agent Tool 的运行类型包含 `execute`，所以 manifest contract 是发现/治理元数据，不是实现。[源码：common.ts](https://github.com/openclaw/openclaw/blob/55bb6cfa2ec4863b5ece006aee70b5de6d967709/src/agents/tools/common.ts#L28-L69)

**观察到的 Agent 行为**

- `AgentConfig` 包含 `id`、default、名称/描述、workspace、agentDir、model、thinking、skills、memory、identity、subagents、sandbox、params、tools 和 runtime。[源码：types.agents.ts](https://github.com/openclaw/openclaw/blob/55bb6cfa2ec4863b5ece006aee70b5de6d967709/src/config/types.agents.ts#L18-L166)
- `agents.list` 定义多个隔离 Agent；每个 Agent 有独立 workspace、agentDir/auth 和 session store，并通过 bindings 做消息路由。[Multi-agent routing](https://github.com/openclaw/openclaw/blob/55bb6cfa2ec4863b5ece006aee70b5de6d967709/docs/concepts/multi-agent.md#L9-L35)

**结论**

- Agent：A3，是 Manifest/Binding 分离的重要参考，但 OpenClaw 当前配置仍把一部分 workspace/runtime binding 放在同一对象中。
- Tool：T1/T2；manifest ownership 不能替代 runtime factory。

### 4.10 Goose

**观察到的 Tool 行为**

- `ExtensionConfig` 是 discriminated union，源码序列化标签包括 `stdio`、已废弃的 `sse`、`builtin`、`platform`、`streamable_http`、`frontend` 和 `inline_python`。stdio/HTTP 是 MCP client 配置；inline Python 虽可写在配置中，但 `code` 本身就是实现代码，不属于纯描述元数据。[源码：extension.rs](https://github.com/aaif-goose/goose/blob/d6345f75dba4f43afe705e045414edf173e40af4/crates/goose/src/agents/extension.rs#L159-L295)
- Extension Manager 向各 client 调用 `list_tools`，并在执行时调用对应 client 的 `call_tool`，这是一条标准 T2 代理链路。[源码：extension_manager.rs](https://github.com/aaif-goose/goose/blob/d6345f75dba4f43afe705e045414edf173e40af4/crates/goose/src/agents/extension_manager.rs#L1391-L1485)

**观察到的 Agent 行为**

- Recipe 是 YAML/JSON 可复用配置，字段包括 version、title、description、instructions/prompt、extensions、settings、activities、parameters、response schema、sub-recipes 和 retry。[源码：recipe/mod.rs](https://github.com/aaif-goose/goose/blob/d6345f75dba4f43afe705e045414edf173e40af4/crates/goose/src/recipe/mod.rs#L41-L86)
- settings 可选择 provider/model/temperature/max turns；sub-recipe 会自动注入 summon extension。官方将 Recipe 定义为可共享并可启动的配置。[Recipe reference](https://github.com/aaif-goose/goose/blob/d6345f75dba4f43afe705e045414edf173e40af4/documentation/docs/guides/recipes/recipe-reference.md#L11-L56)

**结论**

- Agent：A1，准确地说是“配置生成 Agent Session/Workflow”，不是持久化的独立 Agent identity。
- Tool：MCP T2；inline Python 是携带代码的 T1。

### 4.11 Coze Studio

**观察到的 Tool 行为**

- `PluginManifest` 定义 schema version、模型/人类名称与描述、认证、Logo、API 和 common params。[源码：plugin_manifest.go](https://github.com/coze-dev/coze-studio/blob/22275b1c2661d35344a7493cffe401e8cc61cf8e/backend/crossdomain/plugin/model/plugin_manifest.go#L34-L44)
- 产品元数据引用 Manifest、OpenAPI 文件和 Tool 的 method/sub_url。Loader 校验 Manifest 和 OpenAPI，再把 operation 映射为 ToolInfo。[源码：load_plugin.go](https://github.com/coze-dev/coze-studio/blob/22275b1c2661d35344a7493cffe401e8cc61cf8e/backend/domain/plugin/conf/load_plugin.go#L40-L55)、[operation 映射](https://github.com/coze-dev/coze-studio/blob/22275b1c2661d35344a7493cffe401e8cc61cf8e/backend/domain/plugin/conf/load_plugin.go#L151-L249)
- `ExecuteTool` 构建通用 executor、获取认证并执行；`httpCallImpl` 根据 operation、server URL、method 和参数构造 HTTP 请求并发送。[源码：exec_tool.go](https://github.com/coze-dev/coze-studio/blob/22275b1c2661d35344a7493cffe401e8cc61cf8e/backend/domain/plugin/service/exec_tool.go#L45-L93)、[源码：invocation_http.go](https://github.com/coze-dev/coze-studio/blob/22275b1c2661d35344a7493cffe401e8cc61cf8e/backend/domain/plugin/service/tool/invocation_http.go#L59-L155)
- 这是完整的 `OpenAPI metadata -> ToolInfo -> generic HTTP driver -> result`，达到 T3。

**观察到的 Agent 行为**

- `SingleAgent` 持久化身份、版本、模型、Prompt、Plugin、Knowledge、Workflow、Database 等配置。[源码：single_agent.go](https://github.com/coze-dev/coze-studio/blob/22275b1c2661d35344a7493cffe401e8cc61cf8e/backend/crossdomain/agent/model/single_agent.go#L56-L82)
- `StreamExecute` 取出版本化 Agent 后调用 `BuildAgent`；builder 解析 persona/variables、构建 knowledge retriever、model、plugin/workflow/database tools，并创建 ReAct Agent。[源码：single_agent_impl.go](https://github.com/coze-dev/coze-studio/blob/22275b1c2661d35344a7493cffe401e8cc61cf8e/backend/domain/agent/singleagent/service/single_agent_impl.go#L93-L127)、[源码：agent_flow_builder.go](https://github.com/coze-dev/coze-studio/blob/22275b1c2661d35344a7493cffe401e8cc61cf8e/backend/domain/agent/singleagent/internal/agentflow/agent_flow_builder.go#L60-L181)
- Agent 的 Plugin Tool adapter 从 OpenAPI operation 生成模型 Schema，并把运行调用转回统一 Plugin service。[源码：node_tool_plugin.go](https://github.com/coze-dev/coze-studio/blob/22275b1c2661d35344a7493cffe401e8cc61cf8e/backend/domain/agent/singleagent/internal/agentflow/node_tool_plugin.go#L45-L147)

**结论**

- Tool：T3，是本文 OpenAPI driver 的主要源码基线。
- Agent：A2/A3，是持久化 Agent metadata 经 runtime factory 生成可执行实例的完整案例。

### 4.12 Continue

**观察到的 Tool 行为**

- 内置 Tool 的名称和实现是代码注册；dispatcher 根据 Tool URI 转发 HTTP 或 MCP，或调用内置实现。[源码：callTool.ts](https://github.com/continuedev/continue/blob/d0a3c0b626b5bebc3bef4742eec05a0242be0bab/core/tools/callTool.ts#L28-L109)、[内置 dispatch](https://github.com/continuedev/continue/blob/d0a3c0b626b5bebc3bef4742eec05a0242be0bab/core/tools/callTool.ts#L187-L250)
- `config.yaml` 的 `mcpServers` 负责启动/连接 Server；真正 Tool 仍由 MCP 提供。[Continue config reference](https://docs.continue.dev/reference)

**观察到的 Agent 行为**

- Continue 官方把 `config.yaml` 定义为 Agent 配置；顶层包含 name/version/schema、models、context、rules、prompts、docs、mcpServers、data。[Continue config.yaml reference](https://docs.continue.dev/reference)
- 源码 Zod schema 与此一致，并支持 `uses/with/override` 组合 registry blocks。[源码：schemas/index.ts](https://github.com/continuedev/continue/blob/d0a3c0b626b5bebc3bef4742eec05a0242be0bab/packages/config-yaml/src/schemas/index.ts#L100-L167)
- 另有 Markdown Agent 文件格式，但源码明确标注 experimental/internal；当前字段为 `name`、description、model、tools、rules 和 body prompt。[源码：agentFiles.ts](https://github.com/continuedev/continue/blob/d0a3c0b626b5bebc3bef4742eec05a0242be0bab/packages/config-yaml/src/markdown/agentFiles.ts#L5-L20)
- CLI subagent Tool 从模型服务获取这些 Agent，并在 `run` 中调用 `executeSubAgent`。[源码：subagent.ts](https://github.com/continuedev/continue/blob/d0a3c0b626b5bebc3bef4742eec05a0242be0bab/extensions/cli/src/tools/subagent.ts#L15-L114)

**结论**

- 主 Agent config：A1。
- Markdown subagent：A1，但应标注实验性，不宜直接作为稳定跨平台标准。
- Tool：T1/T2；HTTP URI 路径是有限通用驱动，但没有完整 OpenAPI operation 编译层。

### 4.13 Devin

**观察到的 Tool 行为**

- Devin 可以连接 MCP，也通过官方 Devin MCP 把 session、playbook、knowledge、schedule 等平台能力暴露给其他 Agent。[Devin MCP](https://docs.devin.ai/work-with-devin/devin-mcp)
- 对调用方而言这是 T2；执行实现是 Devin 托管服务，不是调用方根据描述元数据生成。

**观察到的 Agent 行为**

- Create Session API 以 `prompt` 为必填，并可绑定 playbook、knowledge、repos、secret refs、ACU limit、平台、结构化输出 Schema、tags 和 title。[Create Session API](https://docs.devin.ai/api-reference/v3/sessions/post-organizations-sessions)
- Playbook 是可复用、版本化的任务提示模板，但不是完整 runtime identity；Knowledge 和 repo skills 提供上下文。[Creating Playbooks](https://docs.devin.ai/product-guides/creating-playbooks)、[Devin Skills](https://docs.devin.ai/product-guides/skills)
- 用户可选择 Devin agent mode/预置 Agent，但公开 API 没有暴露一个像 Claude Managed Agent 那样可任意声明 model/tools/runtime factory 的通用 AgentManifest。

**结论**

- “配置启动一个 Devin Agent Session”可以，属于 A0/A2。
- “只配元数据创建任意新 Agent 类型”目前证据不足，应标记为产品约束，而不是宣称已支持。

### 4.14 Pi

**观察到的 Tool 行为**

- `ToolDefinition` 同时要求 name、label、description、TypeBox parameters 与 `execute`；`registerTool` 把整个定义注册到 extension runtime。[源码：extension types](https://github.com/earendil-works/pi/blob/216e672e7c9fc65682553394b74e483c0c9e47f7/packages/coding-agent/src/core/extensions/types.ts#L435-L485)、[源码：loader.ts](https://github.com/earendil-works/pi/blob/216e672e7c9fc65682553394b74e483c0c9e47f7/packages/coding-agent/src/core/extensions/loader.ts#L222-L244)
- Agent runtime 的 `AgentTool` 也要求 `execute`。[源码：agent types](https://github.com/earendil-works/pi/blob/216e672e7c9fc65682553394b74e483c0c9e47f7/packages/agent/src/types.ts#L372-L396)
- Pi package manifest 只负责发现 extensions/skills/prompts/themes，extension 是具备完整系统权限的 TS 代码。[源码：README](https://github.com/earendil-works/pi/blob/216e672e7c9fc65682553394b74e483c0c9e47f7/packages/coding-agent/README.md#L401-L448)

**观察到的 Agent 行为**

- Pi 核心明确采用极简、代码扩展哲学，默认没有 MCP、subagents、permission popup 或 plan mode；这些能力由 extension 自建。[源码：README philosophy](https://github.com/earendil-works/pi/blob/216e672e7c9fc65682553394b74e483c0c9e47f7/packages/coding-agent/README.md#L488-L500)
- 社区/示例 extension 可以读取 Agent 文件并拉起新 Pi 进程，但这不是核心稳定 Agent Manifest 合约。

**结论**

- Tool：T1。
- Agent：A0/代码扩展。Pi 是“元数据与执行代码必须明确分开”的好基线，但不是“纯配置生成 Agent”的基线。

### 4.15 MCP 2025-11-25

**观察到的 Tool 行为**

- `Tool` 包含 name/title/description、`inputSchema`、可选 `outputSchema`、`execution.taskSupport`、annotations 和 `_meta`。[官方 Schema](https://modelcontextprotocol.io/specification/2025-11-25/schema)、[固定源码](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/26897cc322f356487da89113451bd16b520b9288/schema/2025-11-25/schema.ts#L1244-L1297)
- `ToolAnnotations` 的 readOnly/destructive/idempotent/openWorld 都只是 hint，规范明确要求客户端不要把来自不可信 Server 的 hint 当作授权依据。[固定源码](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/26897cc322f356487da89113451bd16b520b9288/schema/2025-11-25/schema.ts#L1168-L1222)
- 客户端通过 `tools/list` 得到描述，通过 `tools/call` 发送 name/arguments，Server 返回内容；因此 Tool 描述与 Server 执行端是一个完整协议对。[固定源码](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/26897cc322f356487da89113451bd16b520b9288/schema/2025-11-25/schema.ts#L1080-L1156)

**结论**

- MCP 是统一平台 `mcp` driver 的协议基线，达到 T2。
- MCP 本身不定义 AgentManifest；不能用 MCP Tool Schema 代替 Agent 元数据。

## 5. 源码与文档基线

开源项目使用固定 commit，闭源产品使用官方文档并记录访问日期。源码行号基于下表 commit；后续仓库变化不影响本次结论的可复核性。

| 项目 | 基线 | 证据等级 | 重点路径或官方资料 |
|---|---|---|---|
| Codex | `315195492c80fdade38e917c18f9584efd599304` | 源码确认 | [`dynamic_tools.rs`](https://github.com/openai/codex/blob/315195492c80fdade38e917c18f9584efd599304/codex-rs/protocol/src/dynamic_tools.rs#L10-L27)、[`dynamic.rs`](https://github.com/openai/codex/blob/315195492c80fdade38e917c18f9584efd599304/codex-rs/core/src/tools/handlers/dynamic.rs#L113-L177) |
| OpenCode | `3a1c6df9e24672f0761a6ced18e1315d89334baf` | 源码确认 | [`tool.ts`](https://github.com/anomalyco/opencode/blob/3a1c6df9e24672f0761a6ced18e1315d89334baf/packages/opencode/src/tool/tool.ts#L55-L64)、`packages/opencode/src/agent/agent.ts` |
| Cline | `c564045d8135c0c1c330b21d47b68b74917ce614` | 源码确认 | [`agent.ts`](https://github.com/cline/cline/blob/c564045d8135c0c1c330b21d47b68b74917ce614/sdk/packages/shared/src/agent.ts#L146-L186)、configured agent runtime |
| Qwen Code | `0ecba4b3c709d271a17faa5ac9537bf1b102eaf1` | 源码确认 | [`tool-registry.ts`](https://github.com/QwenLM/qwen-code/blob/0ecba4b3c709d271a17faa5ac9537bf1b102eaf1/packages/core/src/tools/tool-registry.ts#L42-L181)、`packages/core/src/subagents/*` |
| Grok Build | `8adf9013a0929e5c7f1d4e849492d2387837a28d` | 源码确认 | [`tool_metadata.rs`](https://github.com/xai-org/grok-build/blob/8adf9013a0929e5c7f1d4e849492d2387837a28d/crates/codegen/xai-grok-tools/src/types/tool_metadata.rs#L1-L10)、[`tool.rs`](https://github.com/xai-org/grok-build/blob/8adf9013a0929e5c7f1d4e849492d2387837a28d/crates/common/xai-tool-runtime/src/tool.rs#L32-L110) |
| OpenClaw | `55bb6cfa2ec4863b5ece006aee70b5de6d967709` | 源码确认 | [`registry-registrars-tools-hooks.ts`](https://github.com/openclaw/openclaw/blob/55bb6cfa2ec4863b5ece006aee70b5de6d967709/src/plugins/registry-registrars-tools-hooks.ts#L243-L293)、[`common.ts`](https://github.com/openclaw/openclaw/blob/55bb6cfa2ec4863b5ece006aee70b5de6d967709/src/agents/tools/common.ts#L28-L69) |
| Goose | `d6345f75dba4f43afe705e045414edf173e40af4` | 源码确认 | [`extension.rs`](https://github.com/aaif-goose/goose/blob/d6345f75dba4f43afe705e045414edf173e40af4/crates/goose/src/agents/extension.rs#L159-L295)、[`extension_manager.rs`](https://github.com/aaif-goose/goose/blob/d6345f75dba4f43afe705e045414edf173e40af4/crates/goose/src/agents/extension_manager.rs#L1391-L1485) |
| Coze Studio | `22275b1c2661d35344a7493cffe401e8cc61cf8e` | 源码确认 | [`load_plugin.go`](https://github.com/coze-dev/coze-studio/blob/22275b1c2661d35344a7493cffe401e8cc61cf8e/backend/domain/plugin/conf/load_plugin.go#L151-L249)、[`invocation_http.go`](https://github.com/coze-dev/coze-studio/blob/22275b1c2661d35344a7493cffe401e8cc61cf8e/backend/domain/plugin/service/tool/invocation_http.go#L59-L155) |
| Continue | `d0a3c0b626b5bebc3bef4742eec05a0242be0bab` | 源码确认 | [`callTool.ts`](https://github.com/continuedev/continue/blob/d0a3c0b626b5bebc3bef4742eec05a0242be0bab/core/tools/callTool.ts#L28-L109)、`packages/config-yaml/src/*` |
| Pi | `216e672e7c9fc65682553394b74e483c0c9e47f7` | 源码确认 | [`extensions/types.ts`](https://github.com/earendil-works/pi/blob/216e672e7c9fc65682553394b74e483c0c9e47f7/packages/coding-agent/src/core/extensions/types.ts#L435-L485)、`packages/agent/src/types.ts` |
| MCP | `26897cc322f356487da89113451bd16b520b9288` | 协议定义 | [`schema.ts`](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/26897cc322f356487da89113451bd16b520b9288/schema/2025-11-25/schema.ts#L1244-L1297) |
| Claude Code | 官方资料，访问 2026-07-17 | 行为文档 | [MCP](https://code.claude.com/docs/en/mcp)、[subagents](https://code.claude.com/docs/en/sub-agents)、[public repository license](https://github.com/anthropics/claude-code/blob/main/LICENSE.md) |
| Anthropic API / Managed Agents | 官方资料，访问 2026-07-17 | API 契约文档 | [Managed Agents tools](https://platform.claude.com/docs/en/managed-agents/tools)、[Tool reference](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-reference)、[Agent setup](https://platform.claude.com/docs/en/managed-agents/agent-setup) |
| Kiro CLI | 官方资料，访问 2026-07-17 | 行为文档 | [Agent configuration](https://kiro.dev/docs/cli/custom-agents/configuration-reference/)、[MCP configuration](https://kiro.dev/docs/cli/mcp/configuration/) |
| Amp | 官方资料，访问 2026-07-17 | API 契约文档 | [Plugin API](https://ampcode.com/manual/plugin-api)、Custom Agents |
| Devin | 官方资料，访问 2026-07-17 | 行为文档 | [Devin MCP](https://docs.devin.ai/work-with-devin/devin-mcp)、Session API、Playbooks、Skills |
