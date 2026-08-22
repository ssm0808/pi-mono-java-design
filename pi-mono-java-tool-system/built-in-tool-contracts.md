# CampusClaw 内置工具契约

| 属性 | 值 |
|---|---|
| 文档版本 | 1.1.0 |
| 状态 | 目标设计，待实现 |
| 更新日期 | 2026-08-22 |
| pi-mono-java 源码基线 | `d0efb2fd18f2f2a7db121a1cbd4f039348a8094a` |
| 上位设计 | [工具系统主设计](README.md) |

## 1. 契约总则

首版只向模型暴露下表中的 12 个内置工具。`name` 使用区分大小写的 PascalCase，
实现、配置、模型请求和事件中的工具名必须完全一致，不提供旧名别名。

| Name | Description | 执行模式 | 成功输出 |
|---|---|---|---|
| `Read` | `Read the contents of a file. For image files, the content is returned as an image.` | `PARALLEL` | 带行号的文本或图片 ContentBlock |
| `Bash` | `Execute a bash command in the working directory.` | `SEQUENTIAL` | 标准输出、标准错误和退出信息文本 |
| `Edit` | `Make exact text replacements in a file. Use oldText/newText for one replacement, or edits for multiple disjoint replacements.` | `SEQUENTIAL` | 修改完成摘要文本 |
| `Write` | `Create or overwrite a file with the given content.` | `SEQUENTIAL` | 写入完成摘要文本 |
| `Glob` | `Find files by glob pattern. Results are sorted by modification time, most recent first.` | `PARALLEL` | 匹配路径文本 |
| `Grep` | `Search file contents using regular expressions.` | `PARALLEL` | 匹配位置和内容文本 |
| `ListDirectory` | `List directory contents with file type, size, and modification time.` | `PARALLEL` | 目录项文本 |
| `Loop` | `Manage recurring prompts in the current interactive session.` | `SEQUENTIAL` | Loop 状态或操作结果文本 |
| `Cron` | `Manage persistent scheduled tasks bound to the current managed Agent.` | `SEQUENTIAL` | Job 或 Run 摘要文本 |
| `ListMateTools` | `List live Mate tools for the current Agent or one directly bound Skill.` | `PARALLEL` | 稳定 JSON 文本 |
| `CallMateTool` | `Call a tool provided by Mate.` | `SEQUENTIAL` | Mate 返回文本及可选内部 details |
| `Agent` | `Run one directly bound child Agent and return its final answer.` | `SEQUENTIAL` | Child 最终 Assistant 文本 |

所有输入 Schema 都是 JSON Schema 2020-12 的对象 Schema，并显式设置
`additionalProperties: false`。默认值由工具实现或 Service 归一化，不在 Schema 中写
`default`。Pipeline 必须先完成 Schema 校验，再进入 before hook、执行、after hook和
事件投影。

所有工具最终统一产生 `ToolResultMessage`：

- 成功时 `isError=false`，`content` 为工具定义的 ContentBlock 列表；
- Schema、可用性、hook 或执行异常均转换为可供模型处理的文本，`isError=true`；
- 不定义跨工具的业务错误 DTO；
- `details` 是 Runtime 内部扩展位，不属于模型可依赖的稳定公共契约；
- 配置决定工具是否暴露，可用条件只在调用时检查。已配置但缺少上下文的工具返回
  `unavailable` 错误，不从本轮工具列表中消失。

每个受管 Session 必须持有由 `PreparedAgentRuntime.agentRoot()` 构造的不可变
`AgentWorkspaceBoundary`。其本地文件边界精确为整个 `agent/{agentId}`；模型、Host
或工具参数不能改写该 root。

## 2. 文件与命令工具

### 2.1 `Read`

```json
{
  "type": "object",
  "properties": {
    "path": {"type": "string", "description": "The file path to read, relative to cwd or absolute within the allowed boundary."},
    "offset": {"type": "integer", "description": "Starting line number, 1-indexed."},
    "limit": {"type": "integer", "description": "Maximum number of lines to read."}
  },
  "required": ["path"],
  "additionalProperties": false
}
```

可用条件：Session 具有 `AgentWorkspaceBoundary` 和 `ReadOperations`。文本输出
保留当前行号与截断形式；图片输出使用图片 ContentBlock。

Read 路径边界固定如下：

- 读取根是整个 `agent/{agentId}`，包含其 `.campusclaw` 子树；
- 相对路径基于该根解析，绝对路径仅在归一化后仍位于该根内时可用；
- 任何路径分量为符号链接、真实路径越界、指向其他 Agent 目录或目标不是可读
  普通文件时拒绝；
- 越界结果使用稳定的当前工作区错误文本和 `isError=true`，不回显其他 Agent
  ID、其他根目录或解析后物理路径；
- Child Session 从 Child 自己的 `agent/{childAgentId}` 构造新边界，不继承父边界。

`Glob`、`Grep`、`ListDirectory`、`Edit` 和 `Write` 使用相同的边界解析器，从而
保证该规则是 Agent 本地工作区隔离，而不是 `Read` 的孤立特例。详见
[Read 工作区隔离设计](README.md#44-agent-工作区边界与-read)。

### 2.2 `Bash`

```json
{
  "type": "object",
  "properties": {
    "command": {"type": "string", "description": "The bash command to execute."},
    "timeout": {"type": "integer", "description": "Timeout in seconds; omitted means no tool-level timeout."}
  },
  "required": ["command"],
  "additionalProperties": false
}
```

可用条件：Session 具有 `cwd` 和 Bash executor。输出继续执行当前的合并、截断、退出码
和取消语义。该工具可以改变进程外状态，因此固定为 `SEQUENTIAL`。

首版四入口缺省 profile 均不包含 `Bash`。仅设置子进程 cwd 不是文件系统沙箱；
在独立 Bash 沙箱设计和验收完成前，受管 Agent 的生产配置不得显式启用该工具。

### 2.3 `Edit`

```json
{
  "type": "object",
  "properties": {
    "path": {"type": "string", "description": "The file path to edit."},
    "oldText": {"type": "string", "description": "The exact text to replace in single-edit mode."},
    "newText": {"type": "string", "description": "The replacement text in single-edit mode."},
    "edits": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "properties": {
          "oldText": {"type": "string"},
          "newText": {"type": "string"}
        },
        "required": ["oldText", "newText"],
        "additionalProperties": false
      },
      "description": "Disjoint replacements matched against the original file."
    }
  },
  "required": ["path"],
  "oneOf": [
    {
      "required": ["oldText", "newText"],
      "not": {"required": ["edits"]}
    },
    {
      "required": ["edits"],
      "not": {"anyOf": [{"required": ["oldText"]}, {"required": ["newText"]}]}
    }
  ],
  "additionalProperties": false
}
```

可用条件：Session 具有 `cwd`、`EditOperations` 和进程级共享的
`FileMutationQueue`。输出为修改完成摘要；未匹配、重复匹配、交叠编辑或路径错误返回
`isError=true`。即使不同 Session 同时编辑同一路径，也由共享队列串行化。

### 2.4 `Write`

```json
{
  "type": "object",
  "properties": {
    "path": {"type": "string", "description": "The file path to create or overwrite."},
    "content": {"type": "string", "description": "The complete content to write."}
  },
  "required": ["path", "content"],
  "additionalProperties": false
}
```

可用条件：Session 具有 `cwd`、`WriteOperations` 和共享 `FileMutationQueue`。成功输出
`Wrote <path>` 形式的文本；父目录按既有实现自动创建。

### 2.5 `Glob`

```json
{
  "type": "object",
  "properties": {
    "pattern": {"type": "string", "description": "Glob pattern to match files, for example **/*.java."},
    "path": {"type": "string", "description": "Starting directory; omitted means cwd."}
  },
  "required": ["pattern"],
  "additionalProperties": false
}
```

可用条件：Session 具有 `cwd` 和文件遍历能力。输出按修改时间从新到旧排列；无匹配返回
正常空结果文本。该工具只读，因此为 `PARALLEL`。

### 2.6 `Grep`

```json
{
  "type": "object",
  "properties": {
    "pattern": {"type": "string", "description": "Regular expression pattern to search for."},
    "path": {"type": "string", "description": "File or directory to search; omitted means cwd."},
    "glob": {"type": "string", "description": "Glob filter, for example *.ts."},
    "type": {"type": "string", "description": "File type filter, for example js, py, or java."}
  },
  "required": ["pattern"],
  "additionalProperties": false
}
```

可用条件：Session 具有 `cwd` 和内容检索能力。输出继续沿用现有匹配位置、截断和
`glob`/`type` 过滤语义。该工具只读，因此为 `PARALLEL`。

### 2.7 `ListDirectory`

```json
{
  "type": "object",
  "properties": {
    "path": {"type": "string", "description": "Directory path to list."}
  },
  "required": ["path"],
  "additionalProperties": false
}
```

可用条件：Session 具有 `cwd` 和目录读取能力。输出目录优先、名称排序，并保留当前
条目上限和空目录文本。目标名称是 `ListDirectory`，不保留旧模型名 `ls` 或 `Ls`。

## 3. Session 与调度工具

### 3.1 `Loop`

```json
{
  "type": "object",
  "properties": {
    "action": {"type": "string", "enum": ["start", "stop", "stop_all", "list"]},
    "prompt": {"type": "string", "description": "Prompt to repeat for start."},
    "interval_ms": {"type": "integer", "description": "Interval for start; omitted means 600000 ms."},
    "id": {"type": "string", "description": "Loop ID for stop."}
  },
  "required": ["action"],
  "oneOf": [
    {"properties": {"action": {"const": "start"}}, "required": ["prompt"]},
    {"properties": {"action": {"const": "stop"}}, "required": ["id"]},
    {"properties": {"action": {"const": "stop_all"}}},
    {"properties": {"action": {"const": "list"}}}
  ],
  "additionalProperties": false
}
```

可用条件：仅 CLI Host 为当前逻辑交互 Session 提供 `SessionLoopController` 时可用。
Runtime、Cron、Child 或没有 Controller 的 CLI 调用返回 unavailable。Controller 的队列、
调度器和 Loop 集合不进入公共 `AgentSession`；关闭交互 Session 时停止其全部 Loop，
`/reload` 重建轻量 Session 时保留同一个 Controller。

### 3.2 `Cron`

```json
{
  "type": "object",
  "properties": {
    "action": {"type": "string", "enum": ["create", "list", "delete", "trigger", "status", "runs"]},
    "name": {"type": "string", "description": "Job name for create."},
    "description": {"type": "string", "description": "Optional job description for create."},
    "prompt": {"type": "string", "description": "Prompt for create."},
    "schedule_type": {"type": "string", "enum": ["at", "every", "cron"]},
    "schedule_value": {"type": "string", "description": "ISO timestamp, interval milliseconds, or cron expression."},
    "timezone": {"type": "string", "description": "Optional timezone for a cron expression."},
    "job_id": {"type": "string", "description": "Job ID for delete, trigger, status, or runs."},
    "limit": {"type": "integer", "description": "Run count for runs; omitted means 10."}
  },
  "required": ["action"],
  "oneOf": [
    {
      "properties": {"action": {"const": "create"}},
      "required": ["name", "prompt", "schedule_type", "schedule_value"]
    },
    {"properties": {"action": {"const": "list"}}},
    {"properties": {"action": {"const": "delete"}}, "required": ["job_id"]},
    {"properties": {"action": {"const": "trigger"}}, "required": ["job_id"]},
    {"properties": {"action": {"const": "status"}}, "required": ["job_id"]},
    {"properties": {"action": {"const": "runs"}}, "required": ["job_id"]}
  ],
  "additionalProperties": false
}
```

相对当前实现，目标契约删除 `model`、`system_prompt` 和 `tools`，且不接受兼容字段。
创建 Job 时由 Host 写入当前受管 `agentId`；模型不能指定或覆盖 Agent。所有管理动作都
以该 Agent 为作用域。触发时重新 `prepare(agentId)`，使用 Agent 当时的 default model、
SYSTEM、skills 和 `cron` 工具 profile，不使用创建时的模型或工具快照。

可用条件：当前 Session 具有受管 Agent 身份和 Agent 隔离的 Cron 上下文；否则返回
unavailable。输出沿用 Job/Run 文本摘要，不引入全局结果 DTO。

## 4. Mate 工具

### 4.1 `ListMateTools`

```json
{
  "type": "object",
  "properties": {
    "skillName": {"type": "string", "description": "Exact name of one Skill directly bound to the current Agent."}
  },
  "additionalProperties": false
}
```

无 `skillName` 时调用 `MateToolClient.listAgentTools(currentAgentId)`；有值时先用本地
`skill.json` 名称索引解析 Skill ID，再调用 `listSkillTools(skillId)`。未知名称、非直接
绑定、索引冲突或远端错误返回 `isError=true`。空工具集合是成功结果。

成功输出必须是可稳定解析的 JSON 文本，字段和顺序如下：

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

Skill 查询时 `scope` 固定为：

```json
{"type": "skill", "name": "research"}
```

输出不得包含 Agent ID、Skill ID、tool ID、`permission`、`outputSchema`、并发属性或
Mate 原始信封。实现先取得按绑定顺序排列的内部 tool ID，再批量查询元数据，以 ID
关联并恢复绑定顺序，最后丢弃 ID。每次调用实时查询，不保存 Session 缓存或磁盘缓存。

可用条件：当前 Session 具有受管 Agent 身份、有效名称索引和 Mate 查询能力。

### 4.2 `CallMateTool`

```json
{
  "type": "object",
  "properties": {
    "tool": {"type": "string", "description": "Mate tool name to call."},
    "args": {"type": "object", "description": "Arguments passed unchanged to the selected Mate tool."}
  },
  "required": ["tool"],
  "additionalProperties": false
}
```

`args` 缺省时按空对象处理。工具无状态，不要求本 Session 先成功调用
`ListMateTools`，也不维护本地 allowlist。Mate 根据当前 Agent 调用上下文和实时绑定做
最终授权、凭据处理、参数校验与执行。成功输出 Mate 文本；Mate 错误转换为
`isError=true`。

可用条件：当前 Session 具有受管 Agent 调用上下文和 Mate 执行能力。

## 5. Child Agent 工具

### 5.1 `Agent`

每个 Session 根据 `.campusclaw/agents/*.json` 的直接绑定生成 `agentName.enum`；枚举
值区分大小写，按名称稳定排序。没有直接绑定时仍可装配工具，但为保持 JSON Schema
合法，省略空 `enum`，任何调用都在执行阶段返回 unavailable。

```json
{
  "type": "object",
  "properties": {
    "agentName": {
      "type": "string",
      "enum": ["researcher", "reviewer"],
      "description": "Exact name of one directly bound child Agent."
    },
    "task": {"type": "string", "description": "Complete task for the child Agent."}
  },
  "required": ["agentName", "task"],
  "additionalProperties": false
}
```

单次调用只创建一个 `SubagentExecution`。执行使用同 JVM 的全新轻量
`AgentSession`，并具有独立的消息、cwd、SYSTEM、Skill 和 `child-agent` profile。
Child 有可用 default model 时优先使用；没有时继承父执行的 model 和 thinking，但仍须
通过 Child 的 `bindingModels` 与当前凭据可用性校验。

执行前按顺序校验：精确直接绑定、自绑定、enabled、固定版本、最大深度、祖先路径
循环、目标运行目录完整性和模型可用性。最大深度可配置，首版默认 `1`。版本不匹配直接
失败，不触发隐式 refresh。

父侧只接收目标、工具开始/结束和完成等高层进度，不接收 Child 推理、消息历史或完整
事件流。父取消必须传播并终止 Child；成功结果只返回最后一条非空 Assistant 文本。

可用条件：当前 Session 具有受管 Agent 身份、直接 Child 索引、未超过深度且
`SubagentExecutionService` 可用。

## 6. 配置 profile 与可用性矩阵

缺省 profile 如下；应用配置显式数组会完全替换对应行。

| 工具 | CLI | Runtime | Cron | Child |
|---|:---:|:---:|:---:|:---:|
| `Read` | ✓ | ✓ | ✓ | ✓ |
| `Bash` |  |  |  |  |
| `Edit` | ✓ |  |  |  |
| `Write` | ✓ |  |  |  |
| `Glob` | ✓ | ✓ | ✓ | ✓ |
| `Grep` | ✓ | ✓ | ✓ | ✓ |
| `ListDirectory` | ✓ | ✓ | ✓ | ✓ |
| `Loop` | ✓ |  |  |  |
| `Cron` | ✓ |  |  |  |
| `ListMateTools` | ✓ | ✓ | ✓ | ✓ |
| `CallMateTool` | ✓ | ✓ | ✓ | ✓ |
| `Agent` | ✓ | ✓ | ✓ | ✓ |

表中的勾选只表示缺省暴露，不表示调用一定可用。例如 CLI 未携带受管 Agent 时，
`ListMateTools`、`CallMateTool`、`Agent` 和 `Cron` 仍在缺省工具列表中，但调用返回
unavailable；非交互 CLI 的 `Loop` 同理。

`Bash` 保留为内置契约但本版默认全部禁用。任何重新启用必须先改变安全设计，
不能被视为不影响 Agent 隔离的普通 profile 调整。

## 7. 源码观察与目标差异

| 分类 | 基线事实或目标差异 |
|---|---|
| 源码观察 | `AgentTool` 当前只有 `name/label/description/parameters/execute`，没有逐工具 `executionMode()`。 |
| 源码观察 | 当前模型名为小写或 lowerCamelCase，目录工具为 `ls`，子 Agent 同时存在 `spawn_agent` 与 `invoke_agent` 路径。 |
| 源码观察 | 当前 `ToolExecutionPipeline` 在 before hook 后才校验 Schema，并以一个全局 mode 执行整批调用。 |
| 源码观察 | 当前 `CronTool` 接受 `model/system_prompt/tools`，`ListMateTool` 接受 `agent_id/skill_id` 并输出自然语言。 |
| 源码观察 | 当前 `ReadTool` 使用自身 cwd 做路径边界，其他文件工具没有 Session 级公共边界对象。 |
| 源码观察 | 当前 `BashExecutor` 只设置子进程 cwd，不是文件系统沙箱。 |
| 架构改造 | 增加 `AgentTool.executionMode()`，默认 `SEQUENTIAL`，并改为逐工具规划相邻并行段与串行 barrier。 |
| 架构改造 | 工具名硬切 PascalCase，Schema 校验移到 before hook 之前，12 个 Schema 成为唯一模型契约。 |
| 产品约束 | 只允许直接绑定 Child；不提供全局枚举、旧工具名、旧 Cron payload 或 Java Extension 兼容。 |
| 安全加固 | 所有工具拒绝未知字段；受管目录名称、ID、版本与调用 ancestry 在执行前校验。 |
| 安全加固 | 本地文件工具共用 `agent/{agentId}` 边界，拒绝符号链接和任何越界路径。 |
| 产品约束 | 四入口缺省 profile 均禁用未沙箱化 `Bash`，避免绕过 Agent 工作区边界。 |

主要证据路径：

- `modules/agent-core/src/main/java/com/campusclaw/agent/tool/AgentTool.java`：`AgentTool`；
- `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java`：
  `execute`、`executeAll`、`validateArguments`；
- `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/**`：现有本地工具；
- `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/loop/LoopTool.java`：`LoopTool`；
- `modules/cron/src/main/java/com/campusclaw/cron/tool/CronTool.java`：`CronTool`；
- `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/ListMateTool.java`：
  `ListMateTool`；
- `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/CallMateTool.java`：
  `CallMateTool`。

## 8. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.1.0 | 2026-08-22 | 将 Read 与本地文件工具边界固定为整个 `agent/{agentId}`，新增跨 Agent 路径、符号链接、非普通文件、错误脱敏和 Child 独立根契约；四入口默认禁用未沙箱化 Bash。 |
| 1.0.0 | 2026-08-22 | 冻结 12 个 PascalCase 内置工具的输入、输出、可用条件、缺省 profile 和逐工具并发模式。 |
