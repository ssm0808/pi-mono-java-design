# 配置如何生成 Tool 与 Agent：研究入口

- 文档版本：2.1.0
- 调研日期：2026-07-18
- 当前结论范围：14 个 Agent/平台样本（Claude Code、Codex、OpenCode、Cline、Qwen Code、Kiro CLI、Amp、Grok Build、OpenClaw、Goose、Coze Studio、Continue、Devin、Pi），补充 Anthropic API/Managed Agents 契约，以及 MCP 协议基线
- 文档整理：2026-09-14；原核验日期与源码提交保持不变
- 文档性质：机制研究；候选规范不是 CampusClaw 已确认设计或已实现能力

## 1. 核心结论

“只配置元数据”的可实现边界是：

> 开发人员不为每个 Tool 或 Agent 编写平台接入代码；平台根据声明式 Manifest，选择一个已经安装且受信任的通用驱动或 Agent Runtime Factory，完成注册、校验、权限控制和运行时装配。

不能把它解释为“只有名称、描述和 JSON Schema，系统就能凭空获得任意业务行为”。名称、描述和输入 Schema 只解决了模型如何调用；真正执行还必须来自以下至少一种实现来源：

1. 平台内置实现；
2. 已存在的 MCP Server；
3. OpenAPI/HTTP 通用驱动；
4. 命令、WASM、脚本或容器制品；
5. 已部署工作流；
6. 另一个 Agent Runtime。

调研得到的最直接答案是：

- **Agent 比 Tool 更容易做到纯配置化。** 因为主流产品已经内置了通用 Agent Loop；配置只需选择模型、提示词、工具、技能、记忆、权限和隔离方式。
- **任意 Tool 不能仅靠描述元数据执行。** Cline、Pi、Amp、OpenCode、Grok Build、OpenClaw 的自定义 Tool 最终都要求 `execute`、`run`、factory 或等价代码。
- **Coze Studio 最接近“配置即 Tool”。** 它读取 Plugin Manifest 和 OpenAPI operation，再由平台通用 HTTP 执行器构造请求、注入认证并执行。
- **Qwen Code 提供另一个很有价值的范式。** `discoveryCommand` 负责输出 Tool 描述，`callCommand` 负责接收 Tool 名称和 JSON 参数；平台因此可以用同一个命令驱动注册多种 Tool。
- **MCP 是“配置即代理”，不是“配置即实现”。** 客户端可根据 MCP Server 配置自动发现并生成代理 Tool，但真实行为仍由 Server 的 `tools/call` 实现。
- **推荐的数据模型不是一个巨大 Tool JSON。** 应拆成 `ToolManifest`、`AgentManifest` 与环境专属 `Binding`；Manifest 可版本化和共享，Binding 保存密钥引用、端点、工作区、身份与制品 pin。

候选平台需要 Driver Registry、Manifest Compiler、Agent Runtime Factory 和 Binding Resolver。其字段与失败规则只在[元数据候选规范 V1](./metadata-v1.md)维护；[JSON Schema](./agent-tool-platform.schema.json) 是该候选规范的研究制品。

### 1.1 研究范围、纳入标准与扩展建议

本文是**按 Tool/Agent 实现机制选取的代表性样本**，不是“所有主流 Agent”的穷举榜单。当前样本优先满足四个条件：用户点名；存在可复核的固定源码或官方结构化文档；能补充一种不同的 Tool/Agent 装配机制；在调研截止日仍有活跃产品或可用实现。

| 研究层 | 当前纳入对象 | 用途 |
|---|---|---|
| 交互式编码 Agent | Claude Code、Codex、OpenCode、Cline、Qwen Code、Kiro CLI、Amp、Grok Build、Continue、Pi | 比较本地 Tool registry、插件、MCP、host callback 与 Agent profile |
| Agent 平台/运行时 | OpenClaw、Goose、Coze Studio、Devin、Anthropic Managed Agents | 比较多 Agent、托管资源、通用 Driver、Binding 与隔离 |
| Tool 契约/协议 | Anthropic API Tool contract、MCP | 提取供应商调用契约与跨产品协议基线 |

证据等级在本文中严格区分：`源码确认` 表示固定 commit 的实现证据；`协议定义` 表示固定协议 Schema；`API 契约文档` 表示官方公开字段和调用语义；`行为文档` 表示只能确认产品公开行为，不能反推内部类；`目标设计` 表示本文建议，不能当成现有产品能力。

尚未纳入原核验范围的候选：

| 优先级 | 候选 | 为什么值得增加 | 本版处理 |
|---|---|---|---|
| P0 | [Gemini CLI](https://github.com/google-gemini/gemini-cli)、[Tools reference](https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/tools.md) | Apache 2.0 开源；公开 `ToolRegistry`、`discoveryCommand`、MCP 与 subagent registry，可验证 Google 系 Agent 的原生模型 | 未纳入固定源码基线 |
| P0 | [OpenHands](https://github.com/OpenHands/OpenHands)、[Software Agent SDK custom tool](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/02_custom_tools.py) | 显式 `ToolDefinition`、Action、Observation、Executor 和 Agent Server，能补足“SDK + 远程 Agent 平台”样本 | 未纳入固定源码基线 |
| P1 | [GitHub Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/tool-search) | MCP、custom agent 与延迟 Tool loading 对大规模 Tool catalog 很有参考价值 | 作为闭源兼容性样本，采用官方行为文档 |
| 独立专题 | OpenAI Agents SDK、Claude Agent SDK、LangGraph、AutoGen、CrewAI、Semantic Kernel | 这些是 Agent SDK/框架，不是与 Claude Code/Codex 同层的终端产品；混入同一矩阵会扭曲结论 | 单独建立“Agent SDK/框架元数据”矩阵 |

[Roo Code](https://github.com/RooCodeInc/Roo-Code/blob/main/README.md) 曾经很有代表性，但其官方仓库已归档，README 明确说明扩展于 2026-05-15 停止，因此不应作为“当前主流活跃 Agent”新增到主基线；如需研究其历史设计，应作为兼容/迁移样本单列。

## 2. 判定标准：避免把“Schema”误判成“可执行 Tool”

### 2.1 Tool 实现等级

| 等级 | 含义 | 是否达到“开发人员只配元数据” |
|---|---|---|
| T0 描述符 | 只有 `name`、`description`、`inputSchema` | 否，只能让模型产生结构化调用 |
| T1 代码注册 | 描述符加 `execute/run/factory` 回调 | 否，开发人员仍需写接入代码 |
| T2 协议代理 | 配置 MCP Server，客户端自动发现和代理 | 有条件达到；Server 必须已实现 |
| T3 通用驱动 | OpenAPI、HTTP、Command 等由平台统一解释执行 | 是，限于驱动覆盖的行为类型 |
| T4 托管工具 | 云平台内置并执行 Tool | 是，限于平台预置 Tool |

### 2.2 Agent 实现等级

| 等级 | 含义 | 是否达到“配置即 Agent” |
|---|---|---|
| A0 会话设置 | 仅覆盖当前会话的 model/prompt/tools | 部分，不是可复用 Agent 资源 |
| A1 可复用 Profile | 文件或配置定义模型、提示词、工具与权限 | 是，可编译为 Agent 实例 |
| A2 版本化托管资源 | 服务端创建 Agent ID/version，再启动 Session | 是，治理能力更完整 |
| A3 隔离、路由、多 Agent | 还定义 workspace、identity、binding、subagent/handoff | 是，但环境数据应与 Manifest 分离 |

### 2.3 本文使用的严格测试

一个项目只有同时满足以下链路，才记为“配置可产生 Tool”：

1. 配置被解析为 Tool 描述；
2. 描述被注册进模型可见工具集合；
3. 调用能被路由到确定的执行驱动；
4. 驱动能把参数映射到真实执行端；
5. 结果能被规范化后返回 Agent；
6. 权限、超时、认证和错误路径有明确归属。

如果只能证明第 1、2 步，结论就是 T0；如果第 3 至 5 步依赖用户写回调，则是 T1。

## 3. 总体对比矩阵

“配置产生新 Tool”列判断的是**新增任意业务 Tool**，不是启用已有内置 Tool。

| 项目 | Tool 的主要机制 | 配置产生新 Tool | Agent 的主要机制 | 配置产生 Agent | 最终判定 |
|---|---|---:|---|---:|---|
| Claude Code | 内置 Tool、MCP | 条件式：T2 | `.claude/agents/*.md`、`--agents` JSON | 是，A1 | 公开证据支持 MCP 与 subagent 配置；不声称存在公开的内部 `ToolDefinition` 类 |
| Anthropic API / Managed Agents | 客户端 Custom Tool、服务端托管 Tool | 客户端仅 T0；托管 Tool 为 T4 | Managed Agent 版本化资源 | 是，A2 | Custom Tool 描述产生调用契约，客户端仍须执行并回传结果 |
| Codex | 内置 Tool、MCP、App Server `dynamicTools` | 条件式：T2；dynamic tool 是 host callback | Agent role TOML 与配置层 | 是，A1 | Dynamic metadata 产生调用入口，但客户端必须响应执行 |
| OpenCode | TS/JS Tool `execute`、插件、MCP | 否：T1/T2 | Markdown YAML agent/mode 文件 | 是，A1 | Agent 配置化，Tool 实现代码化 |
| Cline | SDK Tool `execute`、MCP | 否：T1/T2 | Markdown YAML configured agent；可包装为 subagent Tool | 是，A1 | “Agent 变 Tool”链路清楚，但底层仍有执行器代码 |
| Qwen Code | 代码 Tool、MCP、`discoveryCommand + callCommand` | **是：T3** | Markdown YAML subagent | 是，A1/A3 | 命令驱动是候选 Command 驱动的参考 |
| Kiro CLI | 内置 Tool 分类、MCP Tool | 条件式：T2 | v3 Markdown/JSON Agent Profile | 是，A1 | Profile 很完整；新 Tool 仍来自内置或 MCP |
| Amp | Plugin `registerTool` + `execute`、MCP | 否：T1/T2 | Plugin `createAgent` / agent mode | 代码辅助，A1 | Agent 定义结构化，但目前不是独立数据文件 |
| Grok Build | Rust `Tool` + `ToolMetadata`、MCP | 否：T1/T2 | `.grok/agents/*.md` portable identity | 是，A1/A3 | Agent Manifest 强；Tool 明确分 runtime 与 metadata |
| OpenClaw | Plugin manifest contract + runtime factory、MCP | 否：T1/T2 | `agents.list`、workspace、agentDir、routing binding | 是，A3 | Agent 隔离/路由强；manifest 不代替 Tool factory |
| Goose | MCP extensions、built-in/platform、inline Python | 条件式：T2；inline Python 含代码 | Recipe YAML/JSON | 是，A1 | Recipe 可生成 Agent session/workflow，不是独立托管身份 |
| Coze Studio | Plugin Manifest + OpenAPI + 通用 HTTP executor | **是：T3** | 持久化 `SingleAgent` + `BuildAgent` | 是，A2/A3 | 最接近端到端“元数据生成 Tool/Agent” |
| Continue | 内置 Tool、MCP、HTTP/MCP URI dispatcher | 条件式：T2 | `config.yaml`；实验性 Markdown subagent | 是，A1 | 主 Agent 配置成熟；subagent 文件仍标记实验性/内部 |
| Devin | 内置能力、MCP 集成、Devin MCP | 条件式：T2/T4 | Session API + playbook + knowledge + repo/secret refs | 部分，A0/A2 | 能配置并启动 Devin Session，但不是开放的通用 Agent Runtime Manifest |
| Pi | Extension `registerTool` + `execute`；默认无 MCP | 否：T1 | SDK/Extension；核心明确默认无 subagents | 否，A0/代码扩展 | 极简、代码优先；不适合作为纯元数据基线 |
| MCP 2025-11-25 | `tools/list` + `tools/call` | 仅 T2 | 协议无 Agent 资源 | 否 | Tool 互操作基线，不是 Tool 实现或 Agent Manifest 标准 |


## 阅读入口

| 内容 | 入口与职责 |
|---|---|
| 逐项目行为和固定来源 | [源码与公开契约](./source-mechanisms.md)，区分实现、协议、公开行为 |
| Tool 的定义与执行关系 | [图集](./tool-models.md)，一产品一图，沿用同一 diagram.puml |
| 归一化的字段与失败规则 | [元数据候选规范 V1](./metadata-v1.md)，仅供方案评估 |
| Schema 和六份示例 | [规范制品](./metadata-v1.md#10-规范制品和示例)，未经 Runtime 执行验证 |

## 8. 必须补充的安全与治理元数据

MCP 的 annotations 是 hint，不能直接决定授权。候选平台若要从配置装配可用 Tool，平台还必须拥有独立、可执行的安全字段：

1. **实现可信度**：driver allowlist、artifact digest/signature、publisher、SBOM；
2. **副作用**：read-only、destructive、idempotent、open-world 只是输入，还要经过 policy engine；
3. **认证需求**：Manifest 声明所需 credential 名称和 scope，Binding 映射到 vault；
4. **网络边界**：允许的 host、DNS、redirect、egress profile；
5. **文件边界**：workspace root、read/write glob、symlink policy；
6. **进程边界**：command allowlist、container/WASM sandbox、CPU/memory/time；
7. **调用治理**：approval、rate limit、timeout、retry、concurrency、circuit breaker；
8. **审计**：manifest digest、binding revision、resolved driver、actor、arguments redaction、result digest；
9. **版本治理**：不可变版本、兼容性、deprecation、rollout/rollback；
10. **结果治理**：output schema 校验、最大内容大小、敏感数据过滤。

产品约束与安全加固应明确区分：

- “只允许已安装 driver”是**安全加固**；
- “第一版只支持 MCP/OpenAPI/Command”是**产品范围约束**；
- “Manifest/Binding/State 分离”是**架构变更**；
- “已有 Cline/OpenCode Tool 仍需 execute”是**观察到的源码行为**。

## 9. 候选方案验证顺序

### Phase 1：验证通用驱动

1. 实现 `ToolManifest`、`AgentManifest`、`Binding` registry；
2. 只开放 `builtinRef`、`mcp`、`openapi`、`command` 四个 driver；
3. Agent 先支持一个通用 ReAct factory；
4. 完成 schema validation、reference resolution、Ready health check；
5. 默认所有非只读 Tool 为 `ask`；
6. 实现 immutable version 和 resolved-plan digest。

这一步已经能覆盖：内置 Tool、绝大多数 MCP 集成、HTTP API、CLI 工具，以及 Claude/OpenCode/Qwen/Kiro/Grok 风格的 Agent Profile。

### Phase 2：增加组合能力

1. `agentProxy`：Agent 作为 Tool；
2. `workflow`：工作流作为 Tool；
3. Tool selector、alias、allow/deny 和 capability tag；
4. skills、knowledge、memory store；
5. subagent concurrency/depth/budget；
6. hooks 只允许引用已注册 handler，不允许内联任意 shell。

### Phase 3：受控代码制品

1. `artifact` driver 支持 WASM、签名容器、受限 JS/Python；
2. 强制 digest、publisher trust、SBOM 和漏洞策略；
3. 每个制品在隔离环境执行；
4. 禁止把任意代码字符串伪装成普通 metadata；
5. 建立 driver compatibility contract 和 conformance test kit。

## 11. 验收标准

以下是候选方案验收项，尚不表示 CampusClaw 已实现这些能力：

- 新增一个 OpenAPI operation 时，不修改平台代码即可注册、授权并调用；
- 新增一个符合 command protocol 的 executable 时，不修改平台代码即可注册多个 Tool；
- 新增 MCP Server Binding 时，平台自动发现、过滤、命名、调用并处理 list change；
- 只有 descriptor、没有 implementation 的 Tool 必须拒绝进入 Ready；
- 缺失 secret/endpoint/artifact 的 Tool 必须处于 Unbound，而不是运行时才随机失败；
- Agent Manifest 修改 model/tools/policy 后产生新不可变版本；
- 同一 Agent Manifest 可使用不同 Binding 部署到 dev/prod；
- Agent 的 tool allowlist 和 policy 在模型请求前已解析，不能只靠 prompt 约束；
- 所有调用可追溯到 manifest digest、binding revision 和 driver version；
- schema、driver、result 与 policy 错误都有机器可读错误码。

## 12. 制品校验范围

Schema 与示例的静态校验只证明字段符合候选规范，不能证明 Driver 已安装、远端可达、权限正确或 Tool 可执行。原研究记录使用 Draft 2020-12 校验六个示例，并生成十九个 SVG；本专题保留该制品边界，不将其称为可运行实现。

## 13. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.1.0 | 2026-09-14 | 分离研究入口、逐项目证据与图集，候选规范集中维护字段和执行规则。 |
| 2.0.0 | 2026-07-18 | 发布 Tool/Agent Metadata V1 正文与稳定 Schema。 |
| 1.4.0 | 2026-07-17 | 新增 Tool Search 完整 JSON。 |
| 1.3.0 | 2026-07-17 | 废弃跨产品目录式类图。 |
| 1.2.0 | 2026-07-17 | 拆分 Claude Code、Anthropic API 与 Managed Agents 的证据归属。 |
| 1.1.0 | 2026-07-17 | 新增覆盖全部调研项目的四组 ToolDefinition 类图，并同步图源、SVG 与验证结果。 |
| 1.0.0 | 2026-07-17 | 完成 15 个 Agent/平台与 MCP 调研。 |

<details>
<summary>原章节链接定位</summary>

<a id="4-逐项目研究结果"></a>[4. 逐项目研究结果](./source-mechanisms.md#4-逐项目研究结果)

<a id="41-anthropic-产品族claude-codeclaude-api-与-managed-agents"></a>[4.1 Anthropic 产品族：Claude Code、Claude API 与 Managed Agents](./source-mechanisms.md#41-anthropic-产品族claude-codeclaude-api-与-managed-agents)

<a id="42-codex"></a>[4.2 Codex](./source-mechanisms.md#42-codex)

<a id="43-opencode"></a>[4.3 OpenCode](./source-mechanisms.md#43-opencode)

<a id="44-cline"></a>[4.4 Cline](./source-mechanisms.md#44-cline)

<a id="45-qwen-code"></a>[4.5 Qwen Code](./source-mechanisms.md#45-qwen-code)

<a id="46-kiro-cli"></a>[4.6 Kiro CLI](./source-mechanisms.md#46-kiro-cli)

<a id="47-amp"></a>[4.7 Amp](./source-mechanisms.md#47-amp)

<a id="48-grok-build"></a>[4.8 Grok Build](./source-mechanisms.md#48-grok-build)

<a id="49-openclaw"></a>[4.9 OpenClaw](./source-mechanisms.md#49-openclaw)

<a id="410-goose"></a>[4.10 Goose](./source-mechanisms.md#410-goose)

<a id="411-coze-studio"></a>[4.11 Coze Studio](./source-mechanisms.md#411-coze-studio)

<a id="412-continue"></a>[4.12 Continue](./source-mechanisms.md#412-continue)

<a id="413-devin"></a>[4.13 Devin](./source-mechanisms.md#413-devin)

<a id="414-pi"></a>[4.14 Pi](./source-mechanisms.md#414-pi)

<a id="415-mcp-2025-11-25"></a>[4.15 MCP 2025-11-25](./source-mechanisms.md#415-mcp-2025-11-25)

<a id="5-源码与文档基线"></a>[5. 源码与文档基线](./source-mechanisms.md#5-源码与文档基线)

<a id="10-各-agent-tool-的核心定义类图"></a>[10. 各 Agent Tool 的核心定义类图](./tool-models.md#10-各-agent-tool-的核心定义类图)

<a id="101-tooldefinition-内含执行代码"></a>[10.1 ToolDefinition 内含执行代码](./tool-models.md#101-tooldefinition-内含执行代码)

<a id="1011-pi"></a>[10.1.1 Pi](./tool-models.md#1011-pi)

<a id="1012-opencode"></a>[10.1.2 OpenCode](./tool-models.md#1012-opencode)

<a id="1013-amp"></a>[10.1.3 Amp](./tool-models.md#1013-amp)

<a id="1014-openclaw"></a>[10.1.4 OpenClaw](./tool-models.md#1014-openclaw)

<a id="102-描述与执行分离或交由宿主回调"></a>[10.2 描述与执行分离，或交由宿主回调](./tool-models.md#102-描述与执行分离或交由宿主回调)

<a id="1021-cline"></a>[10.2.1 Cline](./tool-models.md#1021-cline)

<a id="1022-grok-build"></a>[10.2.2 Grok Build](./tool-models.md#1022-grok-build)

<a id="1023-anthropic-api--managed-agents"></a>[10.2.3 Anthropic API / Managed Agents](./tool-models.md#1023-anthropic-api--managed-agents)

<a id="1024-codex"></a>[10.2.4 Codex](./tool-models.md#1024-codex)

<a id="103-协议与通用-driver"></a>[10.3 协议与通用 Driver](./tool-models.md#103-协议与通用-driver)

<a id="1031-mcp"></a>[10.3.1 MCP](./tool-models.md#1031-mcp)

<a id="1032-qwen-code"></a>[10.3.2 Qwen Code](./tool-models.md#1032-qwen-code)

<a id="1033-coze-studio"></a>[10.3.3 Coze Studio](./tool-models.md#1033-coze-studio)

<a id="1034-continue"></a>[10.3.4 Continue](./tool-models.md#1034-continue)

<a id="104-以-mcp-或托管服务为执行边界"></a>[10.4 以 MCP 或托管服务为执行边界](./tool-models.md#104-以-mcp-或托管服务为执行边界)

<a id="1041-claude-code"></a>[10.4.1 Claude Code](./tool-models.md#1041-claude-code)

<a id="1042-kiro-cli"></a>[10.4.2 Kiro CLI](./tool-models.md#1042-kiro-cli)

<a id="1043-goose"></a>[10.4.3 Goose](./tool-models.md#1043-goose)

<a id="1044-devin"></a>[10.4.4 Devin](./tool-models.md#1044-devin)

</details>

<a id="6-目标设计怎样真正做到只配置元数据"></a>[6. 目标设计：怎样真正做到“只配置元数据”：见候选规范](./metadata-v1.md)。

<a id="61-四个不可省略的平台组件"></a>[6.1 四个不可省略的平台组件：见候选规范](./metadata-v1.md)。

<a id="62-tool-注册和调用链"></a>[6.2 Tool 注册和调用链：见候选规范](./metadata-v1.md)。

<a id="63-agent-编译链"></a>[6.3 Agent 编译链：见候选规范](./metadata-v1.md)。

<a id="64-manifestbindingstate-三分法"></a>[6.4 Manifest、Binding、State 三分法：见候选规范](./metadata-v1.md)。

<a id="7-随附统一元数据规范"></a>[7. 随附统一元数据规范：见候选规范](./metadata-v1.md)。

<a id="71-schema-文件"></a>[7.1 Schema 文件：见候选规范](./metadata-v1.md)。

<a id="72-可运行示例"></a>[7.2 可运行示例：见候选规范](./metadata-v1.md)。

<a id="73-为什么-agent-和-tool-必须共用-resourceref"></a>[7.3 为什么 Agent 和 Tool 必须共用 ResourceRef：见候选规范](./metadata-v1.md)。

<a id="74-tool-search-元数据设计"></a>[7.4 Tool Search 元数据设计：见候选规范](./metadata-v1.md)。
