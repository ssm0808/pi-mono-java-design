# CampusClaw 内置工具契约

| 属性 | 值 |
|---|---|
| 文档版本 | 2.3.3 |
| 状态 | 目标设计；Mate 工具 Schema 不变，凭据可见边界收紧 |
| 更新日期 | 2026-09-14 |
| 设计仓分析基线 | `e641fefdc9b58adb0054d6e548d313d01a69b94d` |
| CampusClaw PR 167 基线 | `f60cc3e78bb8b700527ac082c7c8e10524ede095` |
| CampusClaw merge base | `d649866a6cae967ace18ceaeb9597edd47e5721e` |
| CampusClaw 凭据透传核对基线 | `320d790726a70aada6100052952d5494d2a378ac` |
| CampusClaw 压缩修订前基线 | `a7f78fed345a289833970cd7b78399f0e8e51d32` |
| pi 对照基线 | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` |
| OpenCode 对照基线 | `849c2598abc7d2b40261e74b5826bc74ffc78308` |
| 上位设计 | [工具系统主设计](README.md) |

计划能力的 target-only 增量由 [ExitPlanMode](../06-CampusClaw计划模式/README.md#43-exitplanmode-模型契约) 和 [TodoUpdate](../06-CampusClaw计划模式/todo-update.md#2-模型工具契约) 维护；正式接入时统一登记枚举、工厂和 Runtime profile。本文以下八项基础契约不因新增 TODO 改变字段，新增工具并非当前源码已实现。

## 1. 契约总则

基础工具契约包含下表中的 8 个内置工具；计划专题的目标追加项见上方链接。`name` 使用区分大小写的 PascalCase，
实现、配置、模型请求和事件中的工具名必须完全一致，不提供旧名别名。

| Name | Description | 执行模式 | 成功输出 |
|---|---|---|---|
| `Read` | `Read the contents of a file. Supports text files and images.` | `PARALLEL` | 原始文本或图片 ContentBlock |
| `Find` | `Search for files by glob pattern.` | `PARALLEL` | 相对搜索目录的匹配路径文本 |
| `Grep` | `Search file contents for a pattern.` | `PARALLEL` | 带路径和行号的匹配文本 |
| `Ls` | `List directory contents.` | `PARALLEL` | 排序后的目录项文本 |
| `Cron` | `Manage scheduled tasks bound to the current managed Agent.` | `SEQUENTIAL` | Job 或 Run 摘要文本 |
| `ListMateTools` | `List live Mate tools for the current Agent or one directly bound Skill.` | `PARALLEL` | 稳定 JSON 文本 |
| `CallMateTool` | `Call a Mate tool by name.` | `SEQUENTIAL` | Mate 执行结果文本 |
| `Agent` | `Run one directly bound child Agent and return its final answer.` | `SEQUENTIAL` | Child 最终 Assistant 文本 |

所有输入 Schema 均为 JSON Schema 2020-12 对象 Schema，并显式设置
`additionalProperties: false`。默认值由工具或 Service 统一归一化，不在 Schema 中写
`default`。Pipeline 必须先完成 Schema 校验，再进入 before hook、执行、after hook 和
事件投影。

所有工具最终统一产生 `ToolResultMessage`：

- 成功时 `isError=false`，`content` 为工具定义的 ContentBlock 列表；
- Schema、可用性、hook 或执行异常都转换为可供模型处理的文本，`isError=true`；
- 不定义跨工具的业务错误 DTO；
- `details` 是 Runtime 内部扩展位，不属于模型可依赖的稳定公共契约；
- 配置决定工具是否暴露，运行条件只在调用时检查；已暴露但缺少上下文时返回
  `unavailable`，不临时改变本轮工具列表。

`Read`、`Find`、`Grep`、`Ls` 共用由 `PreparedAgentRuntime.agentRoot()` 创建的不可变
`AgentWorkspaceBoundary`。其根精确为当前 `agent/{agentId}`，不是进程 cwd，也不是
`.campusclaw` 子目录。

公共 Session 压缩、Usage 和 Slash Command 不增加或改变模型工具契约。压缩的
`FileOperationTracker` 只识别精确 PascalCase `Read` ToolCall，按路径去重、排序，并在
重复压缩时继承旧摘要的 `<read-files>`；它不改变 Read 的输入、输出或执行模式。
Slash Command 是独立应用模块，所有命令都不会出现在模型工具清单中。命令的注册、
HTTP 和执行规则见 [Slash Command 通用模块](../../04-命令与技能/00-Slash-Command通用模块/README.md)。

## 2. 本地只读工具

### 2.1 公共工作区规则

四个文件工具必须在访问文件系统前使用同一边界组件完成校验：

1. 相对路径以当前 Agent 根为基准；绝对路径只有在规范化后仍位于根内才允许；
2. 路径各分量和最终目标都不得为符号链接；
3. 已存在目标的 `realpath` 必须仍在 `realRoot` 内；遍历过程不得跟随符号链接；
4. `Read` 只接受可读普通文件，`Ls` 只接受可读目录，`Find` 和 `Grep` 只遍历边界内目标；
5. 拒绝跨 Agent、`..` 越界、符号链接和 realpath 越界；错误不泄露兄弟 Agent ID、
   外部根或解析后的物理路径；
6. Child Session 使用 Child 自己的根，不继承父 Agent 边界。

该规则是相对 pi cwd 语义的安全加固。工具的参数与正常输出尽量对齐 pi；工作区边界、
禁止运行期下载辅助二进制和错误脱敏是 CampusClaw 的产品安全约束。

### 2.2 `Read`

```json
{
  "type": "object",
  "properties": {
    "path": {"type": "string", "description": "Path to the file to read, relative or absolute within the current Agent workspace."},
    "offset": {"type": "number", "description": "Line number to start reading from, 1-indexed."},
    "limit": {"type": "number", "description": "Maximum number of lines to read."}
  },
  "required": ["path"],
  "additionalProperties": false
}
```

对齐 pi `read` 的主体语义：文本默认最多返回 2,000 行或 50 KB，以先达到者为准；模型
可用 `offset` 和 `limit` 继续读取。文本 ContentBlock 返回文件原文，不增加行号前缀，
换行与截断提示不伪装成文件内容。若首行本身超过 50 KB，返回该行可容纳的头部并明确
标记首行截断，不建议或调用 `Bash` 绕过限制。

支持 jpg、png、gif、webp、bmp 图片。图片读取为 ImageContent，默认按 pi 的处理规则将
尺寸缩放到最长边不超过 2,000 像素；模型不支持图片时附加说明。二进制但非受支持图片
返回错误。

可用条件：Session 具有 `AgentWorkspaceBoundary`、`ReadOperations` 和取消域。

### 2.3 `Find`

```json
{
  "type": "object",
  "properties": {
    "pattern": {"type": "string", "description": "Glob pattern to match files, for example '*.java' or '**/*.json'."},
    "path": {"type": "string", "description": "Directory to search in; omitted means the current Agent workspace root."},
    "limit": {"type": "number", "description": "Maximum number of results; omitted means 1000."}
  },
  "required": ["pattern"],
  "additionalProperties": false
}
```

`Find` 取代旧 `Glob`，参数和输出对齐 pi `find`：按 glob 查找文件，遵守适用的
`.gitignore`，默认最多 1,000 项或 50 KB，返回相对搜索目录且使用 `/` 分隔的路径；目录
以 `/` 结尾。无匹配是成功结果并返回稳定的无文件文本。

目标实现使用应用随包提供且启动期验证的文件查找能力，或受边界约束的 Java
`FindOperations`；不得在 Agent 调用期间下载 `fd`，不得回退到 shell。遍历不跟随符号
链接，并在取消时立即停止。

可用条件：Session 具有 `AgentWorkspaceBoundary`、`FindOperations` 和取消域。

### 2.4 `Grep`

```json
{
  "type": "object",
  "properties": {
    "pattern": {"type": "string", "description": "Search pattern, interpreted as a regular expression unless literal is true."},
    "path": {"type": "string", "description": "Directory or file to search; omitted means the current Agent workspace root."},
    "glob": {"type": "string", "description": "Optional glob filter for searched files."},
    "ignoreCase": {"type": "boolean", "description": "Whether matching is case-insensitive; omitted means false."},
    "literal": {"type": "boolean", "description": "Whether to treat pattern as a literal string; omitted means false."},
    "context": {"type": "number", "description": "Lines shown before and after a match; omitted means 0."},
    "limit": {"type": "number", "description": "Maximum matches to return; omitted means 100."}
  },
  "required": ["pattern"],
  "additionalProperties": false
}
```

输出对齐 pi `grep`：每个匹配包含相对路径、1-based 行号和内容，可按 `context` 附带
上下文。默认最多 100 个匹配；调用方可显式提高 `limit`，实现上限为 1,000。总输出最多
50 KB，单行最多 500 个字符；所有截断都带明确提示。搜索遵守适用的 `.gitignore`。

目标实现直接调用应用随包提供、启动期已验证的 `rg`，参数通过 argv 传递，不经 shell；
也可以注入受同一边界约束的 `GrepOperations`。不得运行期下载二进制或回退到 `Bash`。
搜索结果再次校验真实路径，防止扫描期间的符号链接替换造成越界。

可用条件：Session 具有 `AgentWorkspaceBoundary`、`GrepOperations` 和取消域。

### 2.5 `Ls`

```json
{
  "type": "object",
  "properties": {
    "path": {"type": "string", "description": "Directory to list; omitted means the current Agent workspace root."},
    "limit": {"type": "number", "description": "Maximum number of entries; omitted means 500."}
  },
  "additionalProperties": false
}
```

输出对齐 pi `ls`：包含 dotfile，按名称不区分大小写排序，目录名追加 `/`；不输出虚假的
权限、大小或修改时间。默认最多 500 项，显式 `limit` 的实现上限为 1,000，总输出最多
50 KB。空目录是成功结果并返回 `(empty directory)`。

可用条件：Session 具有 `AgentWorkspaceBoundary`、`LsOperations` 和取消域。

## 3. `Cron`

```json
{
  "type": "object",
  "properties": {
    "action": {"type": "string", "enum": ["create", "list", "delete", "trigger", "status", "runs"]},
    "name": {"type": "string", "description": "Job name for create."},
    "description": {"type": "string", "description": "Optional Job description for create."},
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

目标契约不接受 `model`、`system_prompt`、`tools` 或 `agentId`。创建 Job 时由 Runtime Host
写入当前受管 Agent；所有查询和管理动作都以该 Agent 为作用域。触发时重新
`prepare(agentId)`，使用触发时的 Agent default model、SYSTEM、skills 和 `cron`
profile，不采用创建时的模型或工具快照。

`Cron` 只出现在 Runtime profile。Job 持久化、集群调度、租约、misfire 和保留策略由
Cron Host 独立设计；当前 JSON 存储、进程内 scheduler 和 OS CLI 调度是遗留源码观察，
不属于本契约。

可用条件：Runtime Session 具有受管 Agent 身份和 Agent 隔离的 Cron 管理上下文。

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

无 `skillName` 时实时查询当前 Agent 工具；有值时先通过本地 `skill.json` 索引解析直接
绑定 Skill ID，再实时查询该 Skill 工具。未知名称、非直接绑定、名称冲突或远端错误返回
`isError=true`；空集合是成功结果。

成功输出是键顺序稳定的 JSON 文本：

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

输出不得包含 Agent ID、Skill ID、tool ID、`permission`、`outputSchema`、并发属性或 Mate
原始信封。`MateToolClient.listAgentTools(agentId)` 和 `listSkillTools(skillId)` 先获得按
绑定顺序排列的内部 tool ID，再批量查询元数据，以 ID 关联并恢复顺序，最后丢弃 ID。

每次 List 都访问 Mate，不使用查询结果缓存。成功后只更新该来源在当前 Session 的
名称到 ID 缓存快照，以便 Call 复用；不得清空其他 Agent/Skill 来源。
所有 Agent binding、Skill binding 和 Tool metadata 发现 HTTP 请求都不得携带
`X-HW-ID`、`Authorization`、`X-HW-APPKEY` 或 `access-token`。

可用条件：Session 具有当前受管 Agent、直接 Skill 索引、Mate 查询能力和 Session 缓存。

### 4.2 `CallMateTool`

```json
{
  "type": "object",
  "properties": {
    "tool": {"type": "string", "description": "Exact Mate tool name to call."},
    "args": {"type": "object", "description": "Arguments passed unchanged to the selected Mate tool."}
  },
  "required": ["tool"],
  "additionalProperties": false
}
```

`args` 缺省时归一化为空对象。模型只给出工具名，不传 Skill、scope 或 tool ID。调用流程：

1. 在当前 Session 的完整有效名称到 ID 快照中查找 `tool`；
2. 命中则直接调用 Mate；
3. 未命中时通过 Session 内 single-flight 实时发现当前 Agent 与所有直接绑定 Skill 的
   完整工具集合；
4. 同名同 ID 合并，同名不同 ID 使刷新失败；所有来源成功后原子替换完整快照；
5. 再查一次名称；仍未命中则返回未知工具错误；
6. 命中后只调用一次 Mate execute。

自动刷新只重试发现，不重放实际工具调用。Mate execute 一旦发出，无论超时、连接断开、
业务失败或返回未知工具，都不进行自动重试，避免副作用重复。Mate 继续负责最终授权、
凭据、参数校验与执行。

`CallMateTool` 只在实际 execute HTTP 请求中读取本次 POST Events execution 的
不可变瞬态快照，并原名透传其中已提供的 `X-HW-ID`、`Authorization`、
`X-HW-APPKEY` 和 `access-token`。不生成缺失值，不改写为 `X-Access-Token`，不将
快照传给发现、模型或其他出站请求。快照不写日志、Session、Prompt、
ToolResult 或持久化存储，execution 结束即丢弃。

可用条件：Session 具有当前受管 Agent、完整直接 Skill 索引、`MateToolClient`、当前 Host execution 凭据、
Session 缓存和 single-flight 协调器。

## 5. `Agent`

每个 Runtime 或 Cron Session 根据 `.campusclaw/agents/*.json` 的直接绑定生成
`agentName.enum`；值区分大小写并稳定排序。没有直接绑定时省略空 `enum`，任何调用都在
执行阶段返回 unavailable。

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

单次调用创建一个 Child Execution。`SubagentExecutionService` 通过公共
`AgentSessionFactory` 为 Child 创建独立 `AgentSession` 实例；父子使用同一 Session 类型、
装配接口、工具 pipeline、hook、错误与取消语义，但消息、工作区、SYSTEM、Skill、工具
实例、缓存和 Execution 上下文隔离。运行位置是实现部署细节，不属于工具契约。

执行前依次校验精确直接绑定、自绑定、enabled、固定版本、最大深度、祖先路径循环、
目标运行目录完整性和模型可用性。首版最大深度为 1，`child-agent` profile 因而不暴露
`Agent`。版本不匹配直接失败，不触发隐式目录 refresh。

Child 有可用 default model 时优先使用；否则继承父 Execution 的 model 和 thinking，且
仍须通过 Child `bindingModels` 与当前凭据可用性校验。父侧只接收目标、工具开始/结束和
完成等高层进度，不接收 Child 推理、消息历史或完整事件流。父取消传播到 Child；成功
结果只返回最后一条非空 Assistant 文本。

可用条件：Session 具有当前受管 Agent、直接 Child 索引、有效深度/ancestry、
`SubagentExecutionService` 和取消域。

## 6. 缺省 profile

应用配置显式数组完全替换对应缺省值；显式空数组表示该入口无模型工具。

| 工具 | Runtime | Cron | Child Agent |
|---|:---:|:---:|:---:|
| `Read` | ✓ | ✓ | ✓ |
| `Find` | ✓ | ✓ | ✓ |
| `Grep` | ✓ | ✓ | ✓ |
| `Ls` | ✓ | ✓ | ✓ |
| `Cron` | ✓ |  |  |
| `ListMateTools` | ✓ | ✓ | ✓ |
| `CallMateTool` | ✓ | ✓ | ✓ |
| `Agent` | ✓ | ✓ |  |

未知值、重复值、旧名或大小写错误必须阻止应用启动。配置只控制模型暴露面，不绕过工具
调用时的 Agent、工作区、凭据、深度或 Host 上下文检查。

## 7. 禁用和删除项

`Bash`、`Edit`、`Write` 不属于公共枚举、配置、工厂或模型契约；其底层源码可暂时保留，
但任何入口都不得装配。`Loop`、`activate_skill`、`EditDiff`、`spawn_agent`、
`invoke_agent`、动态 `ToolCatalog` 和 Extension 工具入口属于迁移删除项。本节仅记录迁移
边界，不为这些名称保留 Schema、别名或兼容执行器。

## 8. 源码观察与目标差异

[工具系统源码证据](source-evidence.md)按实际 commit 维护实现事实，[主设计 §3](README.md#3-依据与设计理由)维护差异分类与理由。本文只维护模型可见的名称、Schema、结果、运行条件和 profile，不另存源码差距副本。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.3.3 | 2026-09-14 | 工具实现证据统一引用主设计，保留八项精确输入输出契约。 |
| 2.3.2 | 2026-09-14 | 登记计划与 TODO 目标工具的契约入口，基础工具字段保持稳定。 |
| 2.3.1 | 2026-08-31 | 明确 Slash Command 由独立 HTTP 模块提供，命令不属于模型工具。 |
| 2.3.0 | 2026-08-27 | 执行凭据仅随实际 Mate execute 传递，发现操作不携带凭据。 |
| 2.2.0 | 2026-08-24 | 压缩只追踪 Read，路径排序去重并跨摘要继承。 |
| 2.1.0 | 2026-08-24 | 补充公共压缩、Read 追踪和未注册 Slash 核心边界。 |
| 2.0.0 | 2026-08-23 | 统一三入口的八项工具契约、Agent 工作区与 Session 缓存。 |
| 1.1.0 | 2026-08-22 | 扩展初版工具与执行入口契约。 |
| 1.0.0 | 2026-08-22 | 定义初版内置工具契约。 |
