# CampusClaw 内置工具契约

| 属性 | 值 |
|---|---|
| 文档版本 | 3.4.0 |
| 状态 | 目标设计；Skill、CallTool、Agent 代理、确认前可信准备与模型参数恢复反馈已在 PR #323 开发提交 ae6645ca 实现；SearchTools、发现与校验的一致性接线及前端可恢复展示待实现，其余状态见源码证据 |
| 更新日期 | 2026-09-22 |
| CampusClaw 注册与发现核验基线 | `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12` |
| 设计仓分析基线 | `e641fefdc9b58adb0054d6e548d313d01a69b94d` |
| CampusClaw PR 167 基线 | `f60cc3e78bb8b700527ac082c7c8e10524ede095` |
| CampusClaw merge base | `d649866a6cae967ace18ceaeb9597edd47e5721e` |
| CampusClaw 凭据透传核对基线 | `320d790726a70aada6100052952d5494d2a378ac` |
| CampusClaw 压缩修订前基线 | `a7f78fed345a289833970cd7b78399f0e8e51d32` |
| pi 对照基线 | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` |
| OpenCode 对照基线 | `fe3f3a41f79ad292cc3c7c629567385a20ec5130`（`dev`，2026-09-22） |
| Codex 对照基线 | `89a7298aff55db29f9cb2ad2430e3efe02b7a454`（`main`，2026-09-22） |
| 上位设计 | [工具系统主设计](README.md) |

目标框架工具共 12 项，Agent 直接关联的业务工具代理不计入此数量。`Skill` 负责加载工作流，`SearchTools` 取代 `ListMateTools` 的模型发现职责，`CallTool` 替代 `CallMateTool` 执行业务操作。Skill、CallTool、代理装配与后端参数恢复已在 PR #323 开发提交 `ae6645ca` 实现；SearchTools 与发现和校验的一致性接线待实现。三个交互工具的精确契约由 [ExitPlanMode](../06-CampusClaw计划模式/README.md#43-exitplanmode-模型契约)、[TodoUpdate](../06-CampusClaw计划模式/todo-update.md#2-模型工具契约) 和下方 AskUserQuestion 专题维护；主线 `8c5fda1dde51675859bc9c07e145dbe253656dea` 已有三个工具及枚举、工厂、Runtime 默认 profile，见[源码证据 §4](source-evidence.md#4-活动工具与主线实现状态2026-09-18)。

提问工具的精确 Schema、问题/答案与等待边界见 [AskUserQuestion](../06-CampusClaw计划模式/ask-user-question.md)。Runtime 默认在 ExitPlanMode、TodoUpdate 后追加它；Child/Cron 不装配，两模式工具定义相同。

## 1. 契约总则

基础工具契约包含下表中的 9 个框架工具；另外三个已实现的交互工具契约见上方链接。框架工具 `name` 使用区分大小写的 PascalCase，实现、配置、模型请求和事件中的工具名必须完全一致，不提供旧名别名。业务工具保留可信元数据中的名称与 Schema，不强制转换大小写。

| Name | Description | 执行模式 | 成功输出 |
|---|---|---|---|
| `Read` | `Read the contents of a file. Supports text files and images.` | `PARALLEL` | 原始文本或图片 ContentBlock |
| `Find` | `Search for files by glob pattern.` | `PARALLEL` | 相对搜索目录的匹配路径文本 |
| `Grep` | `Search file contents for a pattern.` | `PARALLEL` | 带路径和行号的匹配文本 |
| `Ls` | `List directory contents.` | `PARALLEL` | 排序后的目录项文本 |
| `Cron` | `Manage scheduled tasks bound to the current managed Agent.` | `SEQUENTIAL` | Job 或 Run 摘要文本 |
| `Skill` | `Load instructions and resource paths for an available Skill by name.` | `PARALLEL` | 正文、基础目录、抽样资源绝对路径 |
| `SearchTools` | `Get one complete business tool definition by its exact unique name within the current Agent's trusted Skill bindings. This does not register or execute the tool.` | `PARALLEL` | 单个完整业务工具定义 |
| `CallTool` | `Call a managed business tool available through a directly bound Skill. Use SearchTools when its definition is needed.` | `SEQUENTIAL` | 业务工具执行结果文本 |
| `Agent` | `Run one directly bound child Agent and return its final answer.` | `SEQUENTIAL` | Child 最终 Assistant 文本 |

框架工具输入 Schema 均为 JSON Schema 2020-12 对象 Schema，并显式设置
`additionalProperties: false`。默认值由工具或 Service 统一归一化，不在 Schema 中写
`default`。Pipeline 先校验当前模型工具的输入 Schema；动态入口再完成可信目标准备和业务参数校验，之后才进入 before hook、执行、after hook 和事件投影。Agent 代理的注册 Schema 已是完整业务 Schema；`CallTool` 还必须在 hook 前校验所选业务工具的 `args`。

所有工具最终统一产生 `ToolResultMessage`：

- 成功时 `isError=false`，`content` 为工具定义的 ContentBlock 列表；
- Schema、可用性、hook 或执行异常都转换为可供模型处理的文本，`isError=true`；
- 不定义跨工具的业务错误 DTO；
- `details` 是 Runtime 内部扩展位，不属于模型可依赖的稳定公共契约；
- 配置决定工具是否暴露，运行条件只在调用时检查；已暴露但缺少上下文时返回
  `unavailable`，不临时改变本轮工具列表。

模型工具集合由当前入口的框架工具和 Agent 直接关联的业务工具的代理组成。仅由 Skill 关联的业务工具不展开为独立模型工具；同一工具同时与 Agent 直接关联时，已有一个常驻代理。`Skill`、`SearchTools` 和 `Read` 均不增加工具或改变授权。注册与发现的职责见[主设计 §9](README.md#9-工具注册与发现)。

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

## 4. Skill 与受管业务工具

Skill、CallTool、代理、确认前准备与模型参数恢复已在 PR #323 开发提交 `ae6645ca` 实现；SearchTools 及其共用解析接线待实现。定义一致性是调用约束；全量或按需加载、缓存、刷新、版本切换与跨节点同步为后续待设计依赖，见[主设计 §9.2.1](README.md#tool-definition-consistency)。

### 4.1 `Skill`

```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string", "description": "Exact name of an available Skill directly bound to the current Agent."}
  },
  "required": ["name"],
  "additionalProperties": false
}
```

宿主在初始提示词中提供可见 Skill 的名称和描述；模型匹配任务后调用 `Skill`。工具只解析当前 Agent 直接绑定且对模型可见的 Skill，返回其正文、基础目录和资源路径；不读取所有资源内容，也不展开业务工具 Schema。

成功输出采用以下文本结构，正文不包含 YAML frontmatter：

```xml
<skill_content name="facility-operations">
# Skill: facility-operations
Skill instructions...

Base directory for this skill: /.../.campusclaw/skills/facility-operations
Relative resource paths are relative to this base directory.
Note: file list is sampled.

<skill_files>
<file>/.../.campusclaw/skills/facility-operations/references/alarm-handling-guide.md</file>
</skill_files>
</skill_content>
```

资源清单只列 Skill 目录内的普通资源文件绝对路径，排除 `SKILL.md`，最多 10 条并明确提示 sampled；不生成用途简介。扫描沿用工作区边界且不跟随符号链接。清单不完整时模型可以使用 `Ls`、`Find`、`Grep` 定位其余普通资源，再用 `Read` 读取。受管目录不生成工具定义 JSON；工具发现统一由 `SearchTools` 承担。

`Skill`、`Read` 都不建立“已激活”状态，也不修改模型 `tools`。Skill 正文在对应业务步骤中引用唯一工具名，例如“使用 `query-device-alarm` 查询设备告警”；不需要写入参数 Schema、内部 ID 或 SearchTools/CallTool 的平台协议。模型识别正文中的名称，宿主提示指导模型在需要完整参数定义时调用 `SearchTools`；宿主不新增从正文猜测名称的解析器。

未知名称、不可见或非直接绑定、目录或文件不可读返回 `isError=true`；没有资源文件仍是成功结果。可用条件：当前受管 Agent、可见的直接 Skill 索引、工作区边界和取消域。

### 4.2 `SearchTools`

```json
{
  "type": "object",
  "properties": {
    "tool": {
      "type": "string",
      "minLength": 1,
      "description": "Exact unique business tool name referenced by the Skill instructions."
    }
  },
  "required": ["tool"],
  "additionalProperties": false
}
```

`tool` 与 `CallTool.tool` 使用相同的业务技术名。宿主在当前 Agent 直接绑定 Skill 的可信工具范围内核对名称和可披露性，按原名精确匹配；拒绝纯空白名称，不改写大小写、不模糊匹配、不自动选择相似名称。工具名称唯一，同名同 ID 合并来源，同名不同 ID 明确失败。输入不接受 skillName、query、limit、内部 ID 或 URL。

成功结果是一个模型可见的 JSON 文本对象，不增加 matches 数组或分页字段：

```json
{
  "name": "query-device-alarm",
  "description": "查询园区设备告警",
  "inputSchema": {
    "type": "object",
    "properties": {"deviceId": {"type": "string", "description": "园区设备唯一标识"}},
    "required": ["deviceId"],
    "additionalProperties": false
  }
}
```

输出包含完整的 `name`、`description` 和 `inputSchema`（包括所需引用依赖），不包含工具 ID、Skill ID、版本、权限、凭据或快照 ID。该定义只进入模型上下文，不注册代理、不改变后续 `tools`，也不建立激活或授权状态。上下文已有完整定义时可以直接调用；定义遗忘后可以按同一精确名称重新取得。

名称未知、未绑定或不可披露均返回安全的名称不可用错误与 `isError=true`，不泄露其他工具清单；冲突、元数据不可取得和 Schema 无效也明确失败。单个完整定义超过工具结果预算时返回 `TOOL_DEFINITION_TOO_LARGE` 与 `isError=true`，不得截断 Schema 或引导模型反复查询同一超大定义。

SearchTools 与 CallTool 复用可信解析职责，保证已披露定义与本次校验定义一致；具体数据加载、缓存、失效和版本同步机制由后续设计确定，本版不要求完整 Session 目录或全量预加载。可用条件：当前受管 Agent、可信 Skill 工具绑定、定义解析能力和取消域。

### 4.3 `CallTool`

```json
{
  "type": "object",
  "properties": {
    "tool": {"type": "string", "description": "Exact unique business tool name available through a directly bound Skill."},
    "args": {"type": "object", "description": "Arguments for the selected business tool; omitted means an empty object."}
  },
  "required": ["tool"],
  "additionalProperties": false
}
```

`args` 缺省时归一化为空对象。宿主按可信绑定解析当前 Agent 直接绑定 Skill 的工具；模型不传 Skill、scope、tool ID 或 URL。不解析仅与 Agent 直接关联的业务工具，不转发 `Read`、`Skill`、`Agent` 等框架工具；同一工具同时属于 Agent 和 Skill 时仍须满足 Skill 关联的业务工具范围。

权限与确认继续由 Host before hook 执行；两种入口使用同一可信绑定和 `RuntimeToolPermissionPolicy`。`CallTool` 在进入 hook 前复用可信解析层完成目标解析，使用与已披露定义一致的业务 Schema 校验参数，生成不可变的准备快照；hook 只对该快照中的目标作出决定，放行后 `MateToolExecutor` 使用同一工具 ID、定义版本和参数调用 Mate。未知名称、歧义名称、未绑定、无效 Schema 或参数错误均返回 `isError=true`，且不触发用户确认或 Mate execute；权限拒绝发生在参数有效之后。不能依据模型传入的搜索结果扩展可调用范围。是否已加载 Skill 或搜索定义不作为授权条件。

准备阶段只能在当前 Agent 的可信绑定内解析工具定义。它不能接受模型提供的 ID、URL 或 Schema，不能调用业务 execute，也不能在确认等待后重新解析目标。该阶段及 `PreparedToolInvocation` 已在 PR #323 开发提交 `ae6645ca` 实现；`MateToolResolver` 已有按名称解析及缓存能力，SearchTools 复用接线待实现，当前缓存不代表完整同步与版本一致性已经解决。

实际 Mate execute 只发出一次；超时、断线或业务失败不自动重放。可用条件：当前受管 Agent、可信直接 Skill 工具绑定、共享 Mate 执行能力及当前 Host execution 上下文。

<a id="call-tool-recovery-result"></a>

#### 4.3.1 参数错误的模型反馈

本节后端行为已在 PR #323 开发提交 `ae6645ca` 实现，前端低干扰展示待实现。首次本地参数校验失败返回 `isError=true`，模型可见的文本 `content` 包含以下 JSON；它是工具反馈，不是公共 HTTP ResultBean 或 `agent.tool_result` 的新增字段：

```json
{
  "code": "TOOL_ARGUMENTS_INVALID",
  "tool": "query-device-alarm",
  "execution": "not_started",
  "errors": [{"path": "/deviceId", "message": "缺少必填的设备标识"}],
  "definitionComplete": true,
  "definition": {
    "name": "query-device-alarm",
    "description": "查询园区设备告警",
    "inputSchema": {
      "type": "object",
      "properties": {"deviceId": {"type": "string", "description": "园区设备唯一标识"}},
      "required": ["deviceId"],
      "additionalProperties": false
    }
  }
}
```

`errors[].path` 使用相对当前被校验参数对象的 JSON Pointer，根路径为空字符串；错误文案保留字段与约束，不复制原始敏感参数值。`definition` 必须来自本次校验使用的已注册定义或可信业务解析结果，不能重新查询另一版本。业务 `args` 失败使用业务名称和 Schema；`CallTool` 外层失败使用 `tool="CallTool"` 及固定外层定义，不解析未经准入的业务目标。

完整定义包含必要的字段说明和引用依赖。若错误反馈超出工具输出预算，省略 `definition`，令 `definitionComplete=false` 并附非空 `message`。仅在所选业务工具属于 SearchTools 可披露范围且单独定义能完整返回时，指引按精确工具名调用 SearchTools；框架工具、仅由 Agent 直接绑定的工具或单独定义也超限时，不指引走不可用的发现入口，明确说明限制并停止盲目重试。不能截断 Schema 或将片段标记为完整。成功结果不回传定义，名称不存在、权限拒绝、Schema 自身无效和远端调用失败不返回本格式。

`details.errorCode` 同时保留既有 `TOOL_ARGUMENTS_INVALID`，用于 Runtime 公开错误分类；恢复 JSON 必须进入模型可见的 `content`。公开流与历史仍按既有安全规则生成本地化错误正文，不复制本段 JSON。保存和恢复模型历史应保留这些修正依据。框架统一异常路径须保留错误状态与恢复内容，不能只输出错误码或把携带定义的返回当作成功。

宿主调用说明要求模型根据反馈重新构造参数，不猜测字段、不原样重试；定义未完整提供时按反馈中的可用恢复路径处理。自动反馈不触发自动执行，不新增发现凭证、help 模式或调用字段；完整执行及展示规则见[主设计 §9.6](README.md#tool-argument-recovery)。

### 4.4 Agent 直接工具代理

宿主通过 `MateToolsetFactory` 对 Agent 直接关联的每个业务工具实例化同一种 `MateToolAdapter implements AgentTool`，以实际 `name`、`description`、`inputSchema` 加入模型工具集合。业务 Schema 保留原义，不套用 `CallTool` 的 `tool/args` 外壳，也不为每个业务工具新增 Java 类或本地业务实现。

代理与 `CallTool` 共享 `MateToolExecutor` 的可信解析、业务 Schema 校验和 Mate 调用；两者都在参数有效后接入 Host before hook，默认串行执行。框架名称保留，同名同 ID 的业务工具可去重，同名不同 ID 或与框架重名必须明确失败，不能静默覆盖或自动改名。仅由 Skill 关联的业务工具不创建模型代理；加载 Skill 或调用 SearchTools 不触发注册。

### 4.5 凭据边界

代理和 `CallTool` 只在实际 execute HTTP 请求中读取本次 POST Events execution 的不可变瞬态快照，原名透传已提供的 `X-HW-ID`、`Authorization`、`X-HW-APPKEY` 和 `access-token`；不生成缺失值，不改写为 `X-Access-Token`。所有 Agent binding、Skill binding 和 Tool metadata 请求都不得携带这些凭据。

凭据不进入发现、模型或其他出站请求，不写日志、Session、Prompt、ToolResult 或持久化存储，execution 结束即丢弃。快照允许全部或部分缺失，不因此隐藏工具或返回 unavailable；实际请求由 Mate 校验，不在 Claw 构造最低完整性错误。精确边界和验收见[主设计凭据边界](README.md#mate-credential-forwarding)。

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

配置项缺失时使用下表默认值；显式 `[]` 时完全不向模型提供工具，模型请求的 `tools=[]`；非空数组完全替换框架工具缺省值，并在装配开关与绑定约束允许时追加当前 Agent 直接关联的业务工具代理，该装配已在开发提交 `c9a2340` 实现。完整配置规则见[主设计 §4.2](README.md#42-工具配置)。

| 工具 | Runtime | Cron | Child Agent |
|---|:---:|:---:|:---:|
| `Read` | ✓ | ✓ | ✓ |
| `Find` | ✓ | ✓ | ✓ |
| `Grep` | ✓ | ✓ | ✓ |
| `Ls` | ✓ | ✓ | ✓ |
| `Cron` | ✓ |  |  |
| `Skill` | ✓ | ✓ | ✓ |
| `SearchTools` | ✓ | ✓ | ✓ |
| `CallTool` | ✓ | ✓ | ✓ |
| `Agent` | ✓ | ✓ |  |
| `ExitPlanMode` | ✓ |  |  |
| `TodoUpdate` | ✓ |  |  |
| `AskUserQuestion` | ✓ |  |  |

未知值、重复值、旧名或大小写错误必须阻止应用启动。配置只控制模型暴露面，不绕过工具
调用时的 Agent、工作区、凭据、深度或 Host 上下文检查。

## 7. 禁用和删除项

`Bash`、`Edit`、`Write` 不属于公共枚举、配置、工厂或模型契约，其工具源码和专属支撑完全删除，
不保留未装配实现、别名或隐藏开关；删除边界和验收由[主设计 §12.4](README.md#124-删除禁用与替换)维护。
目标保留 12 项框架契约，`ListMateTools` 和 `CallMateTool` 从枚举、配置、工厂与模型入口移除，不保留别名；底层元数据获取和 Mate 执行能力复用。`SearchTools` 只返回定义数据，不恢复 ListMateTools 的整组枚举结果或来源缓存副作用。`Loop`、`activate_skill`、`EditDiff`、`spawn_agent`、`invoke_agent`、旧动态 `ToolCatalog` 和 Extension 工具入口属于迁移删除项，不为这些名称保留 Schema、别名或兼容执行器；Agent 直接关联的业务工具的元数据代理是本版新增目标，不恢复旧目录激活机制。

## 8. 源码观察与目标差异

[工具系统源码证据](source-evidence.md)按实际 commit 维护实现事实，[主设计 §3](README.md#3-依据与设计理由)维护差异分类与理由。本文只维护模型可见的名称、Schema、结果、运行条件和 profile，不另存源码差距副本。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 3.4.0 | 2026-09-22 | SearchTools 仅接收 tool 并返回单个完整定义，移除模糊搜索与全量快照前提。 |
| 3.3.0 | 2026-09-22 | 增加固定 SearchTools 契约，以同一 Session 定义快照支持有界发现和 CallTool 执行。 |
| 3.2.0 | 2026-09-22 | CallTool 业务参数校验前移到交互确认之前，并以不可变准备快照衔接授权与执行。 |
| 3.1.0 | 2026-09-22 | 定义本地参数校验失败的模型恢复结果，保留公共错误分类与业务未执行边界。 |
| 3.0.2 | 2026-09-21 | 业务工具关系统一表述为关联，执行权限规则保持独立。 |
| 3.0.1 | 2026-09-21 | 明确显式空配置完全不提供模型工具，配置项缺失采用默认值。 |
| 3.0.0 | 2026-09-20 | Agent 直接工具采用元数据代理，Skill 工具经 Skill、Read 与 CallTool 按需发现调用。 |
| 2.7.0 | 2026-09-19 | CallMateTool 区分执行上下文与可为空的凭据，取消凭据完整性可用条件。 |
| 2.6.0 | 2026-09-18 | 明确删除 Bash/Edit/Write 本体及专属支撑，不再保留未装配代码。 |
| 2.5.0 | 2026-09-18 | 登记三个已实现交互工具及十一项 Runtime 默认清单。 |
| 2.4.0 | 2026-09-15 | 登记 AskUserQuestion 工具契约与 Runtime 默认装配边界。 |
| 2.3.3 | 2026-09-14 | 工具实现证据统一引用主设计，保留八项精确输入输出契约。 |
| 2.3.2 | 2026-09-14 | 登记计划与 TODO 目标工具的契约入口，基础工具字段保持稳定。 |
| 2.3.1 | 2026-08-31 | 明确 Slash Command 由独立 HTTP 模块提供，命令不属于模型工具。 |
| 2.3.0 | 2026-08-27 | 执行凭据仅随实际 Mate execute 传递，发现操作不携带凭据。 |
| 2.2.0 | 2026-08-24 | 压缩只追踪 Read，路径排序去重并跨摘要继承。 |
| 2.1.0 | 2026-08-24 | 补充公共压缩、Read 追踪和未注册 Slash 核心边界。 |
| 2.0.0 | 2026-08-23 | 统一三入口的八项工具契约、Agent 工作区与 Session 缓存。 |
| 1.1.0 | 2026-08-22 | 扩展初版工具与执行入口契约。 |
| 1.0.0 | 2026-08-22 | 定义初版内置工具契约。 |
