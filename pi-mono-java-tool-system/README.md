# pi-mono-java 工具系统设计

| 属性 | 值 |
|---|---|
| 文档版本 | 1.0.0 |
| 状态 | 目标设计，待实现 |
| 更新日期 | 2026-08-22 |
| 设计仓分析基线 | `b902de281d9ab0ddfdcfec2ff8616279e5c421a1` |
| pi-mono-java 源码基线 | `d0efb2fd18f2f2a7db121a1cbd4f039348a8094a` |
| pi-mono 对照基线 | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` |
| OpenCode 对照基线 | `849c2598abc7d2b40261e74b5826bc74ffc78308` |
| 精确工具契约 | [12 个内置工具契约](built-in-tool-contracts.md) |

## 1. 设计结论

CampusClaw 首版工具系统收敛为一个关闭的内置工具集合，不再提供动态工具注册或 Java
Extension 执行框架。模型只看到以下 12 个区分大小写的 PascalCase 名称：

```text
Read
Bash
Edit
Write
Glob
Grep
ListDirectory
Loop
Cron
ListMateTools
CallMateTool
Agent
```

CLI、HTTP Runtime、Cron 和 Child Agent 使用同一个轻量 `AgentSession` 类型和同一条
`AgentSessionFactory` 装配链，但每次执行得到不同的 Session 实例。四个入口一致的是
模型约束、系统提示词解析、工具装配、hook、错误、事件与取消语义；不一致且不应进入
公共 Session 的是消息持久化、CLI JSONL、模板、`/reload`、Loop Controller、HTTP
active execution 注册、Cron Job 生命周期和宿主关闭策略。

因此，“四入口的 AgentSession 是否一致”的精确定义是：**实现与执行语义一致，实例、
状态、profile 和 Host 生命周期不相同**。HTTP Session 只在一次 active execution 期间
存在；它从数据库恢复消息，执行结束立即关闭，不是常驻内存 Session。

![工具系统目标架构](tool_system_architecture.svg)

[PlantUML 源码：`tool_system_architecture`](diagram.puml#L1)

## 2. 范围与权威边界

### 2.1 本设计是工具系统唯一主设计

本专题负责以下契约：

- 内置工具名、参数、输出、可用条件与并发模式；
- 四入口的工具配置、Session 装配与 Host 责任；
- 受管 Agent/Skill/Child 目录、缓存优先 prepare 与显式 refresh；
- Mate 工具发现与调用；
- Child Agent Execution；
- Loop、Cron 与模型绑定边界；
- 从当前实现迁移到目标架构时需要删除或替换的组件。

Runtime HTTP 的资源、ResultBean、SSE、Entry 和数据库契约仍由
[Manager 驱动的多 Agent Runtime 设计](../pi-mono-java-manager-driven-multi-agent-runtime/README.md)
维护。两份文档交叉时，工具与 Agent 目录装配以本设计为准。

### 2.2 明确不在首版范围

- 自定义工具、动态注册、运行时插件工具和公共 Extension SDK；
- 旧工具名别名或 payload 兼容执行器；
- 跨 JVM Child、ACP Child、HTTP Child、A2A Child 或常驻 Subagent worker pool；
- 本地 allow/ask/deny 审批 UI；
- Runtime 节点租约、Redis active execution、粘性路由和跨节点取消；
- 版本驱动、TTL、watcher 或 Mate 推送触发的目录自动刷新；
- 远端工具清单的本地持久化；
- Cron 旧 payload 迁移和 Extension manifest 兼容。

这些内容不是“待实现的隐含能力”。需要引入时必须建立新的专题和版本决策。

## 3. 源码观察、目标决策与差异分类

### 3.1 pi-mono-java 观察证据

以下事实来自本页记录的 pi-mono-java commit，不代表目标状态：

| 观察事实 | 源码路径与符号 |
|---|---|
| `AgentTool` 当前没有逐工具并发声明 | `modules/agent-core/src/main/java/com/campusclaw/agent/tool/AgentTool.java`，`AgentTool` |
| Pipeline 当前先运行 before hook，再在调用工具时校验 Schema；整批调用共用一个 mode | `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java`，`execute`、`executeAll`、`validateArguments` |
| CLI `AgentSession` 同时承担会话、工具目录、Skill 激活、reload 和委派接线 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSession.java`，`initialize`、`configureRuntimeTools`、`reload` |
| 工具通过 Spring 与 Extension 进入 `ToolCatalog` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/catalog/ToolCatalog.java`、`DefaultToolCatalog.java` |
| HTTP Runtime 独立装配执行引擎且硬编码 `Read` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/runtime/RuntimeSessionEngineRegistry.java` |
| HTTP 目录解析器维护另一套 `settings.json/SYSTEM.md` 读取链 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/agent/FileAgentDirectoryResolver.java` |
| 当前 Manager 缓存优先，但原地写 `agentId.json/setting.json/systemPrompt.md` 和 `references/tools.json` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtime/AgentRuntimeManager.java`，`prepare`、`materialize` |
| 当前 Mate 列表工具接受 `agent_id/skill_id` 并输出自然语言 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/ListMateTool.java`，`parameters`、`execute` |
| 当前 Mate client 以两个 nullable ID 组成一个 `listTools` 接口 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/mate/MateToolClient.java`，`listTools` |
| 当前 Child 有 `spawn_agent`、ACP/HTTP Backend 和 after-hook 委派路径 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/subagent/tool/SpawnAgentTool.java`、`runtime/TransientAgentRunner.java`、`tool/delegation/InvokeAgentTool.java` |
| 当前 Loop 依赖进程级 `LoopManager` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/loop/LoopManager.java`、`LoopTool.java` |
| 当前 Cron payload 可以保存 model、system prompt 和 allowed tools | `modules/cron/src/main/java/com/campusclaw/cron/model/CronPayload.java`、`engine/CronJobExecutor.java`、`tool/CronTool.java` |
| `FileMutationQueue` 由应用级配置共享 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/ops/ToolOpsConfig.java` |

### 3.2 pi 与 OpenCode 仅作对照

pi 的 coding-agent 提供可复用的 `AgentSession`，但其公开的 Subagent 是 Extension 示例，
示例通过独立 `pi` CLI 子进程隔离消息和工作目录。它没有 CampusClaw 的 CLI、HTTP、Cron、
Child 四入口 Host 模型，因此不能据此推导四个入口共享同一个内存 Session。对照源码：
[pi Subagent 示例](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/examples/extensions/subagent/index.ts)，
本地证据为 `packages/coding-agent/src/core/agent-session.ts` 的 `AgentSession`、
`packages/coding-agent/src/core/agent-session-runtime.ts` 和
`packages/coding-agent/examples/extensions/subagent/index.ts` 的 `runSingleAgent`。

OpenCode 的 `TaskTool` 会为 Child 创建独立 Session，适合作为“父子消息隔离和取消传播”的
对照，但它的工具注册、权限和持久化不直接成为 CampusClaw 契约。对照源码：
[OpenCode Task](https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/tool/task.ts)，
本地证据为 `packages/opencode/src/tool/task.ts` 的 `TaskTool`。

### 3.3 目标差异分类

| 分类 | 目标差异 | 设计原因 |
|---|---|---|
| 产品约束 | 只保留 12 个内置工具，硬切 PascalCase | 首版冻结可测试的模型能力面，不承担旧名兼容 |
| 架构改造 | 删除 `ToolCatalog`、动态注册和 Java Extension 工具框架 | 工具能力改由配置 profile 与工厂显式装配 |
| 架构改造 | 四入口共用轻量 Session 与工厂 | 防止模型、hook、工具和取消语义漂移 |
| 架构改造 | 逐工具并发模式和串行 barrier | 允许只读吞吐，不让写操作跨越顺序边界 |
| 安全加固 | Schema 在 hook 前校验，未知字段被拒绝 | hook 和执行器只处理已验证结构 |
| 安全加固 | 受管目录使用同级临时树、完整校验和发布事务 | 不向 Session 暴露半成品，刷新失败保留旧版本 |
| 产品约束 | Child 只能按直接绑定名称调用，默认最大深度 1 | 保持调用面可解释，避免隐式全局发现和递归爆炸 |
| 架构改造 | `ListMateTools` 实时查询且不落盘 | Mate 持有实时绑定和元数据，本地只保存身份映射 |
| 产品约束 | 不在本地执行 permission，也不要求 list-before-call | Mate 是授权和凭据最终责任方 |
| 架构改造 | Loop 状态移到 CLI Host，Cron payload 绑定受管 Agent | 公共 Session 不持有入口专属生命周期状态 |

## 4. 关闭的公共接口

### 4.1 名称与入口枚举

目标新增：

```java
public enum BuiltInToolName {
    READ("Read"),
    BASH("Bash"),
    EDIT("Edit"),
    WRITE("Write"),
    GLOB("Glob"),
    GREP("Grep"),
    LIST_DIRECTORY("ListDirectory"),
    LOOP("Loop"),
    CRON("Cron"),
    LIST_MATE_TOOLS("ListMateTools"),
    CALL_MATE_TOOL("CallMateTool"),
    AGENT("Agent");
}

public enum ToolEntryPoint {
    CLI,
    RUNTIME,
    CRON,
    CHILD_AGENT
}
```

`BuiltInToolName` 是配置解析、工厂分派和模型名的唯一映射。不得用
`Enum.valueOf` 的 Java 常量名替代模型名，也不得做大小写归一化。

### 4.2 工具配置

```yaml
campusclaw:
  tools:
    cli:
      - Read
      - Bash
      - Edit
      - Write
      - Glob
      - Grep
      - ListDirectory
      - Loop
      - Cron
      - ListMateTools
      - CallMateTool
      - Agent
    runtime:
      - Read
      - Glob
      - Grep
      - ListDirectory
      - ListMateTools
      - CallMateTool
      - Agent
    cron:
      - Read
      - Glob
      - Grep
      - ListDirectory
      - ListMateTools
      - CallMateTool
      - Agent
    child-agent:
      - Read
      - Glob
      - Grep
      - ListDirectory
      - ListMateTools
      - CallMateTool
      - Agent
```

四个键各自遵守以下规则：

1. 键缺失时使用上例缺省值；
2. 显式 `[]` 表示该入口无工具；
3. 非空列表完全替换缺省值，不做 merge；
4. 未知名、重复名、旧名或大小写错误使应用启动失败；
5. 配置只在应用启动期绑定和验证；`/reload` 不重新读取该配置；
6. CLI 参数、Agent `settings.json`、Cron payload 和 Child 文件不能扩大或缩小 profile；
7. profile 决定模型可见能力，不承担运行时上下文检查。

### 4.3 工具装配接口

```java
public interface ConfiguredToolAssembler {
    List<AgentTool> assemble(ToolEntryPoint entryPoint, ToolAssemblyContext context);
}

public interface BuiltInToolFactory {
    AgentTool create(BuiltInToolName name, ToolAssemblyContext context);
}
```

`ToolAssemblyContext` 是不可变值对象，至少固化：入口、Session cwd、受管 Agent 身份、
Skill 名称索引、Child 名称索引、执行深度与 ancestry、模型快照、取消域，以及可选的
`SessionLoopController` 和 Cron 上下文。文件 operations、Bash executor、Mate client、
`FileMutationQueue`、Cron Service 等应用级协作者可以共享，但 `AgentTool` 实例必须由
Factory 为每个 Session 新建。

任何工具实现都不得把 Session 的 agentId、cwd、凭据、绑定列表或 Loop 状态写入 Spring
单例。共享协作者必须线程安全；`FileMutationQueue` 保持进程级，确保跨 Session 的同路径
写操作仍串行。

## 5. 公共轻量 AgentSession

### 5.1 装配与身份

![四入口 Session 装配](agent_session_assembly.svg)

[PlantUML 源码：`agent_session_assembly`](diagram.puml#L86)

`AgentSessionFactory.create` 每次执行以下固定步骤：

1. 对受管入口调用 `AgentRuntimeManager.prepare(agentId)`；
2. 解析当前 Agent 的 SYSTEM、cwd、Skill 和 Child 名称索引；
3. 用 `bindingModels` 与 Model Manager 当前可用凭据求可用模型集合；
4. 构造不可变 `ToolAssemblyContext`；
5. 按入口 profile 顺序为每个名称创建新的工具实例；
6. 安装有序不可变 hook 链；
7. 创建新的轻量 `AgentSession`、`AgentState`、消息队列和取消域；
8. 把 Session 返回给 Host，由 Host 恢复消息、订阅事件并管理关闭。

首版生产 before/after hook 链为空，但接口保留。链在 Session 创建时复制为不可变列表，
Session 运行期间不得注册、移除或重排 handler。单次工具调用内按列表顺序执行；不同并行
工具调用可以同时进入同一 handler，因此 handler 必须线程安全。

### 5.2 Host 责任

| Host | 创建时机 | Host 持有 | 关闭时机 |
|---|---|---|---|
| CLI | 启动交互、one-shot 或 `/reload` 成功后 | JSONL、模板、消息、thinking、模型选择、`SessionLoopController`、reload 事务 | CLI 会话退出或被新轻量 Session 替换 |
| HTTP Runtime | 接受一次 active execution 时 | 数据库 Session/Entry、SSE 投影、active execution 注册、Steer/FollowUp/Abort 协调 | active execution 结束或取消后立即关闭 |
| Cron | Job 触发时 | Job/Run 持久化、调度器、当前 Agent ID | 单次 Job execution 结束 |
| Child | `Agent` 工具通过全部检查后 | `SubagentExecutionContext`、进度投影、父取消桥 | 单次 Child execution 结束 |

HTTP 创建执行 Session 时必须调用 `prepare(agentId)`；完整缓存命中不访问 Mate，冷目录则
在请求执行前完成准备。目标实现删除 `FileAgentDirectoryResolver` 的独立契约，也不再由
`RuntimeSessionEngineRegistry` 硬编码 `Read`。

节点常驻、Redis active execution、租约和粘性路由不属于本设计。当前 Host 仍只控制本
JVM 的 active execution；跨节点治理另立专题。

## 6. Pipeline、hook 与批量调度

### 6.1 逐工具并发模式

`AgentTool` 增加缺省方法：

```java
default ToolExecutionMode executionMode() {
    return ToolExecutionMode.SEQUENTIAL;
}
```

`Read`、`Glob`、`Grep`、`ListDirectory`、`ListMateTools` 覆盖为 `PARALLEL`；其余七个
工具使用默认 `SEQUENTIAL`。`isConcurrencySafe` 不成为配置、目录字段或模型可见元数据。

![逐工具批量调度](tool_batch_scheduling.svg)

[PlantUML 源码：`tool_batch_scheduling`](diagram.puml#L316)

Batch planner 保持模型调用原始顺序，把连续 `PARALLEL` 调用组成一个并行段，用虚拟线程
执行并等待整段完成；每个 `SEQUENTIAL` 调用是 barrier，必须等待之前的并行段，之后的
调用也必须等待它。结果永远按模型调用原始顺序回填，而不是按完成时间排序。

### 6.2 单次调用顺序

每个调用固定经过：

```text
resolve configured tool
  -> validate arguments against JSON Schema
  -> run ordered before hooks
  -> emit execution start
  -> execute tool
  -> run ordered after hooks
  -> emit execution end
  -> project ToolResultMessage
```

Schema 错误不进入 before hook。before hook 阻断、hook 异常、工具异常和 after hook 异常
都转换为文本结果及 `isError=true`，不使完整 Agent loop 因单个工具失败而异常退出。
取消信号仍可以终止当前 execution，并由 Session/Host 投影统一取消终态。

## 7. 统一受管目录

### 7.1 目录契约

```text
agent/{agentId}/.campusclaw/
├── agent.json
├── settings.json
├── SYSTEM.md
├── agents/{agentName}.json
└── skills/{skillName}/
    ├── skill.json
    ├── SKILL.md
    ├── references/
    └── templates/
```

目录是 `AgentRuntimeManager` 的只读发布物。除 `prepare` 首次创建和显式 `refresh` 外，
Session、工具、Skill loader 和 Host 都不得修改它。

`agent.json` 只保存当前 Agent 身份，不复制 bindings：

```json
{
  "schemaVersion": 1,
  "id": "agent-0123456789abcdef0123456789abcdef",
  "name": "planner",
  "displayName": "Planner",
  "description": "Plans and coordinates work.",
  "version": "7"
}
```

`settings.json` 保存模型绑定快照：

```json
{
  "schemaVersion": 1,
  "defaultModel": "provider/model",
  "bindingModels": ["provider/model", "provider/fallback"]
}
```

`agents/{agentName}.json` 表示一个可直接调用的 Child 身份与固定版本：

```json
{
  "schemaVersion": 1,
  "id": "agent-fedcba9876543210fedcba9876543210",
  "name": "researcher",
  "displayName": "Researcher",
  "description": "Collects source evidence.",
  "version": "3",
  "enabled": true
}
```

它不保存 Child 的完整运行配置或嵌套 bindings。调用时按 ID 准备 Child 自己的
`.campusclaw` 根目录。

`skills/{skillName}/skill.json` 保存稳定身份：

```json
{
  "schemaVersion": 1,
  "id": "skill-0123456789abcdef0123456789abcdef",
  "name": "research",
  "version": "5"
}
```

每个 `name` 必须与其文件或目录名逐字符一致。Agent 内 Skill 名和 Child 名分别唯一；
名称重复、路径不一致、ID 重复、Schema 版本未知、固定版本缺失或文件解析失败都会使目录
不完整。扫描结果生成不可变的 `skillName -> skillId` 和 `agentName -> BoundAgent` 索引。

不生成、不读取 `references/tools.json`。Skill references 只保存实际参考资料，远端 Mate
工具列表永不落盘。

### 7.2 Skill 渐进加载

PackageManager 只保留 Skill 包发现，不发现工具、命令或 Java Extension。Session 初始
提示词只放置直接绑定 Skill 的 name、description 和 `SKILL.md` 路径。模型需要完整说明时
调用 `Read` 读取 `SKILL.md`；references 和 templates 继续按需读取。

目标删除 `activate_skill`。读取 Skill 不改变工具列表，Skill 也不能声明或激活本地工具。
需要远端能力时，模型调用 `ListMateTools({skillName})` 实时查询。

## 8. 缓存优先 prepare 与显式 refresh

![受管目录准备与刷新](managed_runtime_refresh.svg)

[PlantUML 源码：`managed_runtime_refresh`](diagram.puml#L141)

### 8.1 `prepare(agentId)`

`prepare` 采用纯缓存优先：

1. 校验 Agent ID 和目标路径；
2. 完整读取并验证现有 `.campusclaw`；
3. 完整时直接返回不可变 `PreparedAgentRuntime`，不访问 Mate；
4. 缺失或不完整时取得该 Agent 的 JVM 内锁，再次检查缓存；
5. 仍不完整才访问 Mate，拉取当前 Agent、直接 Skill 和直接 Child；
6. 在同一 Agent 父目录创建唯一同级临时树；
7. 写完后验证文件、名称、ID、版本、引用、模型设置和目录边界；
8. 在持锁状态下发布完整树并返回；失败时删除临时树，旧目录不变。

不比较远端版本，不设置 TTL，不后台刷新，不在 Child 版本不匹配时自愈。版本不匹配是
明确执行错误，只有管理动作或 `/reload` 可以刷新。

### 8.2 `refresh(agentId)` 与 `/reload`

`refresh` 忽略现有目录的新旧判断，强制拉取远端并构建候选树。首次发布可以直接使用同
文件系统的原子 move；替换已有树时，发布器在 per-agent 写锁内保留 previous sibling，
依次切换完整目录。所有应用读取都受同一读写边界保护，因此 Session 只能看到旧树或新
树，不能看到切换间隙或半成品。

`refresh(agentId)` 返回包含新 runtime 和回滚句柄的 `RefreshResult`。受管 CLI `/reload`
在删除 previous 前完成以下事务：

1. 用候选 runtime 重建轻量 Session；
2. 保留原消息、thinking 与 `SessionLoopController`；
3. 当前模型仍在新 `bindingModels` 且当前有凭据时继续使用；
4. 否则切换到新 Agent 的可用 default model，并向用户提示；
5. 没有可用 default、Session 创建失败或迁移失败时调用 rollback，恢复旧目录和旧 Session；
6. 全部成功后 commit 并清理 previous。

工具 profile 来自启动配置，`/reload` 不更新。任一 refresh 失败均不终止旧 Session，也
不清空消息、thinking 或 Loop。

## 9. Mate 工具发现与执行

### 9.1 `ListMateTools`

![Mate 工具实时发现](list_mate_tools_sequence.svg)

[PlantUML 源码：`list_mate_tools_sequence`](diagram.puml#L210)

模型输入只有可选 `skillName`：无参数查询当前 Agent，有名称时通过本地 `skill.json`
索引解析 ID。模型不能提交 agentId、skillId 或 toolId。

`MateToolClient` 目标接口拆分为：

```java
List<MateToolMeta> listAgentTools(String agentId);

List<MateToolMeta> listSkillTools(String skillId);

ToolResult callTool(String tool, Map<String, Object> args, MateCredentials credentials);
```

两个 list 方法内部先获取有序 binding tool IDs，再批量查询元数据，以内部 ID 关联并恢复
绑定顺序。投影到模型时只保留：

```json
{
  "scope": {"type": "agent"},
  "tools": [
    {
      "name": "ExampleTool",
      "description": "Example description",
      "inputSchema": {"type": "object", "properties": {}}
    }
  ]
}
```

Skill scope 为 `{"type":"skill","name":"<skillName>"}`。输出不包含 ID、permission、
`outputSchema` 或并发属性。每次调用均实时请求 Mate，不缓存结果；空列表是成功。

### 9.2 `CallMateTool`

`CallMateTool({tool,args?})` 无状态转发。`ListMateTools` 是模型使用指引，不是调用前置
事务；本地不记住 list 结果、不验证 tool 必须已列出、不执行 allow/ask/deny。Mate 根据
当前 Agent 调用上下文、实时绑定和凭据做最终授权与执行。

缺少受管 Agent、Mate client 或执行上下文时返回 unavailable。Mate 服务错误和异常进入
统一文本错误语义，不泄露凭据或原始内部信封。

## 10. Bound Child Agent Execution

![Child Agent Execution](subagent_execution_sequence.svg)

[PlantUML 源码：`subagent_execution_sequence`](diagram.puml#L265)

模型只使用：

```json
{
  "agentName": "researcher",
  "task": "Collect the implementation evidence for the tool pipeline."
}
```

`agentName` 只能来自当前目录 `agents/{agentName}.json` 的直接绑定。Factory 按当前索引
生成动态 enum；执行时仍重新校验，不能信任模型看到 Schema 时的旧候选。

产品文案统一称“Bound Subagent”，代码中的动作和生命周期统一使用 Execution 术语：

| 组件 | 职责 |
|---|---|
| `BoundAgentTool` | 实现模型工具 `Agent`，做参数转换、进度桥接和结果投影 |
| `AgentBindingResolver` | 按精确名称解析直接绑定并校验 enabled、version、depth、ancestry |
| `SubagentExecutionContext` | 固化父子 ID、深度、ancestry、父模型、thinking、取消和进度 sink |
| `SubagentExecutionService` | 协调准备、模型选择、运行和取消 |
| `OneShotSubagentRunner` | 创建一次性 Child Session，提交 task，提取最终 Assistant 文本 |

每次调用启动一个同 JVM 的新 Child Session：消息从空集合开始，cwd 指向 Child Agent 根，
SYSTEM、Skill 和 `child-agent` profile 全部来自 Child runtime。Child 有可用 default model
时优先，否则继承父执行的 model 与 thinking；任何模型最终都必须位于 Child 的
`bindingModels` 且当前具备凭据。

默认最大深度为 `1`，可以通过应用配置收窄或扩大；首版产品验收按 `1`。每跳检查自绑定、
ancestry 循环、深度、enabled 和固定版本。Child 可以内部运行多个 LLM turn，但父侧只
看到目标、工具开始/结束、完成等高层进度，不能看到 reasoning 或完整历史。父取消必须
取消 Child，成功结果只返回最终非空 Assistant 文本。

目标删除 Simon 路径引入的 `AgentAuthorizationPolicy` placeholder、`PERMIT_ALL`、
`LocalChildAgentMetadataSource` 远端回退、nullable tenant/conversation placeholder、
Session after-hook 特殊委派和 registry cancellation hook。授权边界由受管直接绑定、固定
版本、模型绑定和 Mate/Host 的既有身份上下文共同组成。

## 11. Loop、Cron 与模型策略

### 11.1 Loop

当前进程级 `LoopManager` 改为 CLI Host 为每个逻辑交互 Session 创建的
`SessionLoopController`。Controller 持有自己的提交队列、scheduler 和 Loop map；不同
交互 Session 互不影响。关闭 Session 时停止全部 Loop，`/reload` 只替换轻量
`AgentSession`，不替换 Controller。其他入口或非交互 CLI 调用 `Loop` 返回 unavailable。

### 11.2 Cron

`Cron` 工具保留 `create/list/delete/trigger/status/runs`，删除 `model`、
`system_prompt` 和 `tools` 参数。Job 内部 payload 自动保存当前受管 `agentId + prompt`
及调度元数据；模型不能选择别的 Agent。所有管理操作按当前 Agent 过滤，不能读取、触发
或删除其他 Agent 的 Job。

执行触发时调用 `prepare(agentId)`，使用此时 Agent 的 SYSTEM、Skills、default model 和
`cron` profile，而不是 Job 创建时的工具或模型快照。不提供旧 payload 迁移或读取兼容。

### 11.3 四入口模型白名单

可用模型统一定义为：

```text
usableModels = settings.bindingModels
               intersect Model Manager available models
               intersect models with currently usable credentials
```

- CLI 显式 `-m` 只能选择 `usableModels`；
- HTTP 创建和修改 Session 只能使用 `usableModels`；
- Cron 每次触发选择该 Agent 当时可用的 default；
- Child 优先自身 default，否则继承父 model 与 thinking，但仍校验 Child 白名单；
- `/reload` 按第 8.2 节保留当前模型或切换新 default；
- 无可用模型时，创建或 reload 失败，不回退到 Agent 未绑定模型。

## 12. 实现迁移

### 12.1 拆分当前大型 CLI Session

迁移不是在当前 `AgentSession` 上继续增加入口判断，而是按责任移动：

| 当前责任 | 目标归属 |
|---|---|
| Agent loop、消息队列、工具 pipeline、取消 | 公共轻量 `AgentSession` |
| 模型、SYSTEM、tool、hook 的统一构造 | `AgentSessionFactory` |
| 工具筛选和实例取得 | `ConfiguredToolAssembler` + `BuiltInToolFactory` |
| CLI JSONL、模板、自定义交互命令 | CLI Host |
| `/reload` 与消息/Loop 迁移 | CLI Host + `AgentRuntimeManager.refresh` |
| Loop 调度与提交队列 | `SessionLoopController` |
| HTTP 数据库恢复与 SSE | HTTP Host |
| Cron Job/Run 与调度器 | Cron Host |
| Child 绑定、进度与父取消 | `SubagentExecutionService` |

### 12.2 删除和替换清单

| 删除或停止使用 | 替代 |
|---|---|
| `ToolCatalog`、`DefaultToolCatalog`、`ToolSelection` 动态目录 | 启动期严格 profile + 关闭工厂 |
| Java `Extension`、`ExtensionRegistry`、`ExtensionPoint` 和 manifest tools/commands | 无；PackageManager 只发现 Skill |
| `activate_skill` 与 Skill 工具激活 | `Read(SKILL.md)` + 实时 `ListMateTools` |
| `spawn_agent`、`invoke_agent` 和旧 Agent delegation 接线 | `Agent` + `SubagentExecutionService` |
| ACP、HTTP、A2A Subagent Backend | 首版同 JVM Child Session |
| `EditDiff` | `Edit` |
| `references/tools.json` | `skill.json` 名称到 ID 索引 + Mate 实时列表 |
| `FileAgentDirectoryResolver` 独立契约 | `AgentRuntimeManager.prepare` |
| HTTP 硬编码 `Read` | `runtime` profile |
| 进程级 `LoopManager` | CLI Session 级 `SessionLoopController` |
| Cron model/system_prompt/tools payload | 触发时按受管 Agent 解析 |

### 12.3 模块与生成镜像

实现只修改 `modules/*` 主源码。`mate-campusclaw/` 是生成镜像，不做双份手工维护；实现
完成后运行：

```bash
scripts/sync-mate-campusclaw.sh
```

同步后的镜像必须与主模块一起测试，但生成镜像中的差异不能反向成为设计权威。

## 13. 实现验收场景

### 13.1 配置与装配

- 四入口缺省 profile 精确匹配第 4.2 节；
- 任一入口显式空数组时模型无工具；
- 未知、重复、旧名或大小写错误阻止启动；
- `/reload` 不改变应用工具 profile；
- 同一入口连续创建两个 Session，每个内置工具实例不同；
- operations、Mate client 和 `FileMutationQueue` 可以安全共享。

### 13.2 Pipeline

- Schema 校验发生在 before hook 前；
- 多个 before/after handler 保持固定顺序；
- 并行调用可以同时进入线程安全 handler；
- `P,P,S,P,P` 按两个并行段和一个 barrier 执行；
- 结果按模型原始顺序返回；
- Schema、hook、工具异常均成为文本和 `isError=true`。

### 13.3 目录与刷新

- 完整缓存命中不访问 Mate；
- 冷目录用同级临时树完整创建并发布；
- 半成品、名称/路径不一致、Skill 或 Child 重名、固定版本缺失均拒绝；
- 发布前失败保留旧目录；
- `/reload` Session 创建或模型选择失败时回滚目录和 Session；
- 成功 reload 保留消息、thinking、Loop Controller；
- 任意目录不存在 `references/tools.json`；
- HTTP 冷目录创建调用 `prepare`，不走独立 resolver。

### 13.4 Mate、Child、Cron 与 Loop

- `ListMateTools` 无参数查当前 Agent，有参数按 Skill 名解析；
- 每次列表调用均访问 Mate，输出只含 scope/name/description/inputSchema；
- Mate 元数据乱序时恢复 binding 顺序；
- `CallMateTool` 未先 list 也可调用，最终授权由 Mate 执行；
- Child 的 cwd、消息、SYSTEM、Skill 和工具与父隔离；
- Child 校验直接绑定、固定版本、深度、ancestry 循环和父取消；
- Child 进度不包含 reasoning，结果只含最终文本；
- Cron Job 按 Agent 隔离，触发时使用当前 default 和 `cron` profile；
- 不接受旧 Cron `model/system_prompt/tools`；
- 两个 CLI 交互 Session 的 Loop 完全隔离，关闭只停止本 Session Loop；
- Runtime、Cron、Child 调用 Loop 返回 unavailable；
- CLI、HTTP、Cron、Child 的所有模型选择都受 `bindingModels` 与凭据可用性约束。

## 14. 文档治理与实现顺序

建议按依赖顺序实施：

1. 冻结 `BuiltInToolName`、配置绑定和 12 个 Schema；
2. 增加逐工具 execution mode 并改造 Pipeline；
3. 实现工厂、不可变上下文和公共轻量 Session；
4. 迁移 CLI 与 HTTP Host；
5. 统一目录、prepare/refresh 和模型解析；
6. 实现 Mate 名称发现；
7. 迁移 Child Execution、Cron 和 Loop；
8. 删除动态目录、Extension、旧委派和兼容代码；
9. 同步 `mate-campusclaw` 并完成全量回归。

本设计为 target-only，不能因为文档完成就把目标能力标为已实现。每个实现 PR 都应引用
本页基线，列出实际落地的目标项和仍存在的源码差异。

## 15. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-08-22 | 冻结 12 个内置工具、四入口轻量 Session、严格 profile、统一受管目录、缓存优先与显式 refresh、Mate 实时发现、同 JVM Child Execution、Cron/Loop Host 边界和迁移清单。 |
