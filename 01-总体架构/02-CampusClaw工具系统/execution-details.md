# 工具系统执行细节

| 属性 | 值 |
|---|---|
| 文档版本 | 1.0.0 |
| 更新日期 | 2026-09-21 |
| 主设计 | [CampusClaw 工具系统设计](README.md) |
| 源码基线 | `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12`，具体路径与符号见[源码证据 §9](source-evidence.md#sequence-evidence) |
| 实现状态 | 公共 Session 工厂、Pipeline 与分段调度已有实现；Skill / CallTool、Agent 业务代理及共用执行适配待实现 |

本页展开主设计的执行顺序，依次说明 Session 创建、工具装配、单次调用、业务执行与批次调度。图中待实现部分均有标记；工具配置、权限、凭据、工作区和名称解析规则仍由主设计及[精确契约](built-in-tool-contracts.md)维护。

阅读顺序：[Session 创建](#session-creation) → [工具装配](#tool-assembly) → [单次调用](#tool-invocation)。[业务执行](#business-execution)展开一次 `tool.execute`，[批次调度](#batch-scheduling)说明多个调用如何组合；它们不是重复执行的额外阶段。

<a id="session-creation"></a>

## 1. Session 创建

场景从 Host 已确定入口和 Agent 后开始，到 `AgentSessionFactory` 返回新的 Session 为止。`prepare` 由 Factory 调用；入口选择、历史恢复和执行关闭由 Host 负责，不在本图展开。图示为创建成功路径。

![公共 Session 创建](agent_session_assembly.svg)

[PlantUML 源码：`agent_session_assembly`](diagram.puml#L140) · [原尺寸 SVG](agent_session_assembly.svg)

`AgentSessionFactory.create` 先调用 `AgentRuntimeManager.prepare(agentId)`，取得受管运行时快照，再校验运行条件、解析可用模型并准备工作区与工具装配上下文。工具列表由下节的装配过程返回；Factory 随后配置 Agent 的模型、工具、SYSTEM 和 hook，创建独立的 `ManagedAgentSession` 并交还 Host。

工具装配或运行条件校验失败时，创建失败并返回 Host，不继续发起模型请求。创建成功后，消息恢复、事件订阅和最终关闭仍由 Host 接续；各入口的职责边界见[主设计 §6](README.md#6-公共轻量-agentsession)。

<a id="tool-assembly"></a>

## 2. 工具装配

本图展开 `ConfiguredToolAssembler.assemble`。输入是已准备的入口和 `ToolAssemblyContext`，输出是本 Session 的工具实例列表；共享工厂和协作者不等于共享带有 Agent 状态的工具实例。

![初始工具集合装配](tool_set_assembly.svg)

[PlantUML 源码：`tool_set_assembly`](diagram.puml#L195) · [原尺寸 SVG](tool_set_assembly.svg)

装配器读取入口 profile。显式空列表直接返回空工具集合；其他路径先检查目标名称冲突，再经 `BuiltInToolFactory` 创建框架工具，并按当前 Agent 直接绑定调用 `MateToolsetFactory` 创建业务代理。冲突使装配失败，不返回部分列表。框架工厂仍可通过上下文中的 Host 工厂回调创建宿主相关工具。

返回的列表用于配置 Agent 并提供给模型。仅由 Skill 绑定的业务工具不在这里展开 Schema 或创建代理；同时被 Agent 直接绑定的工具按直接绑定路径装配。读取 Skill 正文或定义文件不触发本图再次装配。业务代理及新增框架入口的装配接线待实现，具体 profile 与冲突规则见[主设计 §4](README.md#4-关闭的公共接口与配置)。

<a id="tool-invocation"></a>

## 3. 单次调用

场景从 `AgentLoop` 已解析本次调用的工具实例后开始，到 Pipeline 返回一条 `ToolResultMessage` 为止。Pipeline 管理调用生命周期，Host hook 处理权限与必要确认；图示包含已安装权限 hook 的路径，各入口的实际支持范围见源码证据。

![单次工具调用生命周期](tool_invocation_pipeline.svg)

[PlantUML 源码：`tool_invocation_pipeline`](diagram.puml#L552) · [原尺寸 SVG](tool_invocation_pipeline.svg)

Pipeline 先校验已注册工具的输入 Schema，再调用 before hook；允许执行后才发出执行开始事件并调用 `tool.execute`。工具返回结果或抛出普通执行异常后，Pipeline 归一化结果，进入 after hook，最后发出结束事件并返回结果。

Schema 校验失败在 before hook 前返回；before hook 拒绝或出错在工具执行前返回。这两条提前返回路径均不进入 after hook。普通工具执行错误仍进入 after hook；取消向上终止当前 execution，不作为普通工具失败继续处理。

Agent 业务代理的注册 Schema 包含完整业务参数；`CallTool` 在此只校验固定外层参数，其内部业务参数在下一节的执行器中校验。后者只保证发生在远端请求之前，不改变 Host 的确认顺序；规则见[主设计 §7](README.md#7-pipelinehook-与批量调度)。

<a id="business-execution"></a>

## 4. 业务执行

本图展开上节的一次 `tool.execute`，输入是 Pipeline 已放行的业务调用，输出是工具结果或交还 Pipeline 的普通执行异常。`tool : AgentTool` 表示本次调用的单个真实实例，可能是 `MateToolAdapter`，也可能是 `CallTool`。

![业务工具共用远端执行](call_mate_tool_sequence.svg)

[PlantUML 源码：`call_mate_tool_sequence`](diagram.puml#L413) · [原尺寸 SVG](call_mate_tool_sequence.svg)

代理使用已绑定的业务名称和直接参数；`CallTool` 解析外层名称与参数。两者分别携带 Agent 直接绑定范围、直接 Skill 绑定范围，委托同一个 `MateToolExecutor` 完成可信目标解析、业务 Schema 校验和 Mate 调用。解析或校验失败时返回错误，不进入 HTTP 执行；成功时由 Mate client 发出请求并返回结果。

该共用执行适配待实现。执行器不接管 Host 的权限与确认，不把模型读到的定义文件作为执行目标或权限依据。精确调用范围、参数、失败处理和[凭据](README.md#mate-credential-forwarding)由[主设计 §9.2](README.md#92-calltool-与-agent-代理)及工具契约维护。

<a id="batch-scheduling"></a>

## 5. 批次调度

本图从有序的五个工具调用开始，到得到同序的五个结果为止。示例依次为 `Read`、`Grep`、`CallTool`、`Find`、`Ls`；图中每个任务内部都执行上文的完整 Pipeline。

![批次并行与串行屏障](tool_batch_scheduling.svg)

[PlantUML 源码：`tool_batch_scheduling`](diagram.puml#L610) · [原尺寸 SVG](tool_batch_scheduling.svg)

调度器把连续 `PARALLEL` 调用组成并行段，等待整段完成后再执行后续调用；每个 `SEQUENTIAL` 调用构成屏障。因此前两个调用可并行，`CallTool` 等待它们完成后执行，最后两个调用再组成新的并行段。工具模式的权威清单见[主设计 §7](README.md#7-pipelinehook-与批量调度)。

图中异步任务及其 Future 合并表示：任务 #2 可以先于 #1 完成并保存结果，但调度器先等待 Future #1，再读取 Future #2 的已完成结果。第二段同理；任务完成顺序不会改变返回结果的输入顺序。分段调度已在核验提交实现，`CallTool` 等新入口的接入待实现。
