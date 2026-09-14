# pi AgentSession 启动与请求构建

> 源码基线：`badlogic/pi-mono@fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc`；原核验日期：2026-07-24；文档整理：2026-09-14。
> 本文记录该固定提交的源码行为，不代表最新 pi 或 CampusClaw 目标设计。

[返回研究入口](./README.md) · [源码证据索引](./README.md#12-源码证据索引)

## 5. CLI 到 AgentSession 的逐代码链路

本节按实际执行顺序解释，而不是按文件名分类。

### 步骤 1：确定启动目录和全局资源目录

`main()` 的关键代码是：

```ts
const cwd = process.cwd();
const agentDir = getAgentDir();
const bootstrapSettingsManager =
  SettingsManager.create(cwd, agentDir, { projectTrusted: false });
```

对应 [`main.ts:486-489`](https://github.com/badlogic/pi-mono/blob/fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc/packages/coding-agent/src/main.ts#L486-L489)。

逐句含义：

1. `cwd` 先取当前进程目录；
2. `agentDir` 取环境变量覆盖值或 `~/.pi/agent`；
3. bootstrap 阶段显式设置 `projectTrusted: false`，此时只允许读取全局 settings，不能抢先加载项目配置；
4. bootstrap settings 主要用于 HTTP proxy 等最早期全局启动参数。

随后 `main.ts:558` 又创建 `startupSettingsManager = SettingsManager.create(cwd, agentDir)`，未传 `projectTrusted`；而 `SettingsManager` 的默认值是 `true`。因此当前源码会在正式信任判定前读取**启动 cwd** 的 `.pi/settings.json`，用于 sessionDir 查找及启动会话选择。选定最终 session cwd 后，`main.ts:633` 才使用显式 `projectTrusted` 创建 runtime SettingsManager。

这意味着要区分：

- “启动 session 查找是否物理读取项目 settings”：当前实现会；
- “最终 AgentSession 是否采用项目 settings 和项目资源”：由 trust gate 决定。

### 步骤 2：先选择或创建 SessionManager

`createSessionManager()` 位于 `main.ts:264-355`：

| 条件 | 创建方式 | 是否读 JSONL |
|---|---|---|
| `--no-session`、`--help`、`--list-models` | `SessionManager.inMemory()` | 否 |
| `--fork` | `SessionManager.forkFrom()` | 读源会话 |
| `--session` | `SessionManager.open()` | 读指定会话 |
| `--resume` | 列表选择后 `open()` | 扫描并读会话 |
| `--continue` | `continueRecent()` | 扫描并读最近会话 |
| 已有 `--session-id` | `open()` | 读匹配会话 |
| 默认 | `SessionManager.create()` | 新建 header，首次持久化时写文件 |

session 目录优先级在 [`main.ts:573-578`](https://github.com/badlogic/pi-mono/blob/fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc/packages/coding-agent/src/main.ts#L573-L578)：

```text
--session-dir
  > PI_CODING_AGENT_SESSION_DIR
  > settings.json 的 sessionDir
  > $AGENT_DIR/sessions/--<encoded-cwd>--
```

这里“先会话、后项目资源”很关键：若打开的 session 属于另一个项目，后续 `.pi/settings.json`、`.pi/extensions` 和 AGENTS 搜索都以 session 的 `cwd` 为准。

### 步骤 3：根据项目资源决定信任状态

`main.ts:602-633` 创建 `ProjectTrustStore`，并检查目标 cwd 是否包含需信任的项目资源。

需信任资源由 `trust-manager.ts:29-37` 固定为：

```text
.pi/settings.json
.pi/extensions
.pi/skills
.pi/prompts
.pi/themes
.pi/SYSTEM.md
.pi/APPEND_SYSTEM.md
```

此外，cwd 或祖先目录中的 `.agents/skills` 也会触发信任判断。

信任来源依次包括：

1. CLI 单次覆盖；
2. 当前运行缓存；
3. 预信任阶段已加载的全局/CLI extension 对 `project_trust` 事件的决定；
4. `$AGENT_DIR/trust.json` 中 cwd 或最近祖先的决定；
5. 全局 `defaultProjectTrust`；
6. 交互模式中的用户选择。

**重要例外：**根目录至 cwd 的 `AGENTS.md` / `CLAUDE.md` 不在信任资源表中，`loadProjectContextFiles()` 也没有检查 `isProjectTrusted()`。所以项目不可信时，`.pi/*` 不加载，但项目指令文件仍可能进入 system prompt。

### 步骤 4：创建 cwd-bound 服务

[`main.ts:634-677`](https://github.com/badlogic/pi-mono/blob/fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc/packages/coding-agent/src/main.ts#L634-L677) 调用：

```ts
createAgentSessionServices({
  cwd,
  agentDir,
  settingsManager: runtimeSettingsManager,
  resourceLoaderOptions: {
    additionalExtensionPaths,
    additionalSkillPaths,
    additionalPromptTemplatePaths,
    additionalThemePaths,
    noExtensions,
    noSkills,
    noPromptTemplates,
    noThemes,
    noContextFiles,
    systemPrompt,
    appendSystemPrompt,
  },
});
```

这里把 CLI 的资源路径和 `--no-*` 开关交给 ResourceLoader。CLI 路径在启动 cwd 下先解析为绝对路径；即使 `--no-skills` 或 `--no-extensions`，显式 CLI 路径仍保留。

### 步骤 5：创建 ModelRuntime

`createAgentSessionServices()` 在 `agent-session-services.ts:137-152`：

```ts
const modelRuntime = await ModelRuntime.create({
  authPath: join(agentDir, "auth.json"),
  modelsPath: join(agentDir, "models.json"),
});
```

`ModelRuntime.create()` 进一步执行：

1. 用 `auth.json` 创建 credential store；
2. 读取并校验 `models.json`；
3. 在同目录创建 `FileModelsStore(models-store.json)`；
4. 合并内建 provider 与本地模型配置；
5. 执行本地 refresh。AgentSession 服务创建阶段传入 `allowNetwork: false`，不会为了初始构建强制联网；
6. 扩展加载后，再注册扩展 provider，并再次本地 refresh。

源码证据：

- [`agent-session-services.ts:137-180`](https://github.com/badlogic/pi-mono/blob/fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc/packages/coding-agent/src/core/agent-session-services.ts#L137-L180)
- [`model-runtime.ts:133-176`](https://github.com/badlogic/pi-mono/blob/fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc/packages/coding-agent/src/core/model-runtime.ts#L133-L176)

### 步骤 6：ResourceLoader 执行统一 reload

`DefaultResourceLoader.reload()` 是文件资源读取的核心，位于 `resource-loader.ts:338-489`。执行顺序是：

1. 如需交互信任，先在不可信状态加载全局扩展，让全局扩展有机会处理 `project_trust`；
2. 按最终信任状态重新加载 settings；
3. `packageManager.resolve()` 汇总 package、本地和自动发现路径；
4. 解析 CLI extension source；
5. 加载扩展；
6. 加载技能；
7. 加载提示模板；
8. 加载主题；
9. 加载 AGENTS/CLAUDE 指令文件；
10. 解析 SYSTEM 和 APPEND_SYSTEM。

这一步的输出不是一个字符串，而是多组缓存：

```ts
extensionsResult
skills
prompts
themes
agentsFiles
systemPrompt
appendSystemPrompt
```

### 步骤 7：PackageManager 先得到“候选路径”

`DefaultPackageManager.resolve()` 位于 `package-manager.ts:901-953`：

1. 读取 global/project settings；
2. project packages 先加入，global packages 后加入；
3. 相同 package identity 去重时 project 胜出；
4. settings 中的项目资源路径相对 `$CWD/.pi` 解析；
5. settings 中的全局资源路径相对 `$AGENT_DIR` 解析；
6. 加入约定目录的自动发现结果；
7. 返回 `ResolvedPaths`，其中每个路径带 `source`、`scope`、`origin`、`enabled` 元数据。

自动发现目录由 `package-manager.ts:2336-2466` 定义：

| 资源 | 用户级 | 项目级 |
|---|---|---|
| extensions | `$AGENT_DIR/extensions` | `$CWD/.pi/extensions` |
| skills | `$AGENT_DIR/skills`、`~/.agents/skills` | `$CWD/.pi/skills`、cwd 至 git root 各级 `.agents/skills` |
| prompts | `$AGENT_DIR/prompts` | `$CWD/.pi/prompts` |
| themes | `$AGENT_DIR/themes` | `$CWD/.pi/themes` |

项目级四类 `.pi` 资源和项目 `.agents/skills` 都要求项目可信。用户级资源不要求项目信任。

extension 的自动发现还有一层入口规则：

1. 扩展根目录自身的 `package.json` 若声明 `pi.extensions`，使用声明路径；
2. 否则根目录有 `index.ts` 时使用它；
3. 否则根目录有 `index.js` 时使用它；
4. 否则扫描根目录直接子项：直接的 `*.ts`、`*.js`，以及含 manifest/index 的一级子目录；
5. 不递归任意深度搜索所有 TypeScript 文件。

`.agents/skills` 的祖先扫描范围与 AGENTS 文件不同：

- `.agents/skills`：在 git 仓库内扫描至 git root；不在 git 仓库内扫描至文件系统根；
- `AGENTS.md` / `CLAUDE.md`：始终从 cwd 扫描至文件系统根。

### 步骤 8：把候选路径变成内存对象

ResourceLoader 对不同类型执行不同解析：

| 类型 | 解析代码 | 内存结果 |
|---|---|---|
| extension | `extensions/loader.ts:403-427,454-479` | `Extension`：handlers、tools、commands、flags、provider 注册等 |
| skill | `skills.ts:277-325` | `Skill`：name、description、filePath、baseDir、sourceInfo、disable flag |
| prompt | `prompt-templates.ts:104-133` | `PromptTemplate`：name、description、argumentHint、body、filePath |
| theme | `theme.ts:623-626` | `Theme`：解析后的颜色和 sourcePath |
| context file | `resource-loader.ts:67-119` | `{path, content}` |
| SYSTEM | `resource-loader.ts:50-65,966-978` | `string | undefined` |
| APPEND_SYSTEM | `resource-loader.ts:50-65,980-992` | `string[]` |

extension 文件不是作为文本塞给模型，而是通过 `jiti.import()` 执行 default-export factory。扩展可以注册工具、命令、provider 和事件 hook。

### 步骤 9：从会话树恢复 messages、model 和 thinking level

`SessionManager.buildSessionContext()` 位于 `session-manager.ts:461-470`。它先沿 `parentId` 从当前 leaf 回溯到 root，再反转为时间顺序。

处理规则：

1. `message` 转为原始 AgentMessage；
2. `custom_message` 进入模型消息；
3. `branch_summary` 转为摘要消息；
4. `compaction` 转为压缩摘要消息；
5. 普通 `custom`、`label`、`session_info` 不进入模型上下文；
6. 如果存在 compaction，只保留最新 compaction 摘要、`firstKeptEntryId` 之后的保留条目和 compaction 后的新条目；
7. model 取路径上最后的 `model_change` 或 assistant message 元数据；
8. thinking level 取路径上最后的 `thinking_level_change`。

所以恢复会话时不会把整个 JSONL 文件线性发送给模型，也不会发送 sibling branch。

### 步骤 10：SDK 解析模型、思考等级和初始工具

`createAgentSession()` 位于 `sdk.ts:169-398`。

模型选择优先级：

1. 调用方显式 `options.model`；
2. 既有 session 恢复出的 provider/model；
3. settings 的 `defaultProvider/defaultModel`；
4. provider 默认模型。

思考等级优先级：

1. 显式 `options.thinkingLevel`；
2. 既有 session 的 thinking entry；
3. settings 的 `defaultThinkingLevel`；
4. 内建默认值；
5. 最后按模型能力 clamp。

默认 active tools 是：

```text
read, bash, edit, write
```

`--tools`、`--exclude-tools`、`--no-tools`、`--no-builtin-tools` 会修改这个列表。

### 步骤 11：先创建一个“空壳” Agent

SDK 在 [`sdk.ts:294-360`](https://github.com/badlogic/pi-mono/blob/fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc/packages/coding-agent/src/core/sdk.ts#L294-L360) 创建：

```ts
agent = new Agent({
  initialState: {
    systemPrompt: "",
    model,
    thinkingLevel,
    tools: [],
  },
  convertToLlm,
  streamFn,
  transformContext,
  ...
});
```

此时：

- system prompt 还是空字符串；
- tools 还是空数组；
- model/thinking 已确定；
- `transformContext` 已接到 extension runner 引用，但 runner 尚由 AgentSession 建好。

然后：

- 恢复会话时，把 `existingSession.messages` 赋给 `agent.state.messages`；
- 新会话时，把初始 model 和 thinking level 写为 JSONL entry；
- 最后调用 `new AgentSession(...)`。

### 步骤 12：AgentSession 构造函数建立 runtime

`AgentSession` 构造函数位于 `agent-session.ts:375-401`：

1. 保存 Agent、SessionManager、SettingsManager、ResourceLoader、ModelRuntime；
2. 订阅 agent events，用于会话持久化、扩展、压缩和重试；
3. 安装 tool hooks；
4. 安装 next-turn refresh；
5. 调用 `_buildRuntime()`。

它不再自行扫描目录，而是消费 ResourceLoader 已加载的对象。

### 步骤 13：构建工具注册表

`_buildRuntime()` 位于 `agent-session.ts:2551-2602`：

1. 从 settings 读取图片缩放、shell prefix、shell path；
2. 以 cwd 创建所有内建工具定义；
3. 从 ResourceLoader 取得 extension result；
4. 创建 `ExtensionRunner`；
5. 合并 builtin、extension 和 SDK custom tools；
6. 应用 allowed/excluded filters；
7. extension/custom tool 同名时覆盖同名定义；
8. 包装 tool hook；
9. 调用 `setActiveToolsByName()`。

`setActiveToolsByName()` 同时做两件事：

```ts
this.agent.state.tools = tools;
this._baseSystemPrompt = this._rebuildSystemPrompt(validToolNames);
this.agent.state.systemPrompt =
  this._systemPromptOverride ?? this._baseSystemPrompt;
```

因此 tools 的变化会立刻重建 base system prompt。

### 步骤 14：构建 base system prompt

`_rebuildSystemPrompt()` 位于 `agent-session.ts:1021-1055`：

1. 从 active tool 中收集 `promptSnippet`；
2. 收集并去重 `promptGuidelines`；
3. 从 ResourceLoader 取得 SYSTEM、APPEND_SYSTEM；
4. 取得已加载的 skills；
5. 取得 AGENTS/CLAUDE context files；
6. 形成 `BuildSystemPromptOptions`；
7. 调用 `buildSystemPrompt()`。

输入结构是：

```ts
{
  cwd,
  skills,
  contextFiles,
  customPrompt,
  appendSystemPrompt,
  selectedTools,
  toolSnippets,
  promptGuidelines,
}
```

### 步骤 15：绑定运行模式后，扩展还可以补资源

构造函数返回后，print、TUI、RPC 模式分别调用 `session.bindExtensions()`：

- print：`modes/print-mode.ts:71-100`
- TUI：`modes/interactive/interactive-mode.ts:1627-1655`
- RPC：`modes/rpc/rpc-mode.ts:316-340`

`bindExtensions()`：

1. 绑定 UI、命令、abort 等运行模式能力；
2. 发出 `session_start`；
3. 发出 `resources_discover`；
4. 扩展可追加 skill、prompt、theme 路径；
5. 如果追加了资源，ResourceLoader 更新对应缓存；
6. 重新构建 base system prompt。

所以“构造函数结束”并不是资源集合最后一次变化；运行模式绑定完成后才包含扩展动态发现的资源。

### 步骤 16：每一轮发送前允许扩展再改一次

用户调用 `session.prompt()` 时，`agent-session.ts:1114-1264` 依次执行：

1. extension command；
2. `input` hook；
3. `/skill:name` 展开；
4. prompt template 展开；
5. 模型和认证校验；
6. 必要的 compaction；
7. 构造 user message；
8. 合并 pending next-turn message；
9. 发出 `before_agent_start`；
10. 接受扩展新增 custom messages；
11. 接受扩展本轮 system prompt override；
12. 调用 Agent loop。

Agent 取得 `{systemPrompt, messages, tools}` 快照；Agent loop 再执行：

1. extension `context` transform；
2. `convertToLlm()`；
3. 组装 provider `Context`；
4. 解析当前 API key；
5. 发起流式请求。

源码证据：

- [`agent.ts:398-458`](https://github.com/badlogic/pi-mono/blob/fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc/packages/agent/src/agent.ts#L398-L458)
- [`agent-loop.ts:281-312`](https://github.com/badlogic/pi-mono/blob/fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc/packages/agent/src/agent-loop.ts#L281-L312)

## 7. system prompt 的精确拼接顺序

### 7.1 没有 SYSTEM.md

`buildSystemPrompt()` 的顺序是：

```text
pi 内建默认说明
  + active tool snippets
  + tool prompt guidelines
  + pi 文档路径说明
  + APPEND_SYSTEM
  + <project_context> 中的 AGENTS/CLAUDE 正文
  + <available_skills> 中的技能元数据（仅 read active）
  + Current working directory
```

默认 prompt 会根据 active tools 动态变化。例如只有 `read` 时，不会添加 bash 文件操作 guideline。

### 7.2 存在 SYSTEM.md 或 CLI custom prompt

顺序变为：

```text
custom SYSTEM
  + APPEND_SYSTEM
  + <project_context>
  + <available_skills>（仅 read active）
  + Current working directory
```

pi 内建默认说明、默认工具列表、默认 guideline 和 pi 文档路径全部被替换。

### 7.3 每轮 override

base prompt 建好后，`before_agent_start` 可以返回新的 `systemPrompt`，只对当前轮生效。下一轮默认恢复 base prompt，除非 hook 再次覆盖。

## 8. 端到端例子

假设：

```text
$AGENT_DIR=/Users/alice/.pi/agent
$CWD=/work/acme/backend
项目已信任
```

磁盘上有：

```text
/Users/alice/.pi/agent/settings.json
/Users/alice/.pi/agent/auth.json
/Users/alice/.pi/agent/AGENTS.md
/Users/alice/.pi/agent/skills/security/SKILL.md
/work/acme/AGENTS.md
/work/acme/backend/CLAUDE.md
/work/acme/backend/.pi/settings.json
/work/acme/backend/.pi/SYSTEM.md
/work/acme/backend/.pi/APPEND_SYSTEM.md
/work/acme/backend/.pi/extensions/ticket.ts
/work/acme/backend/.pi/prompts/review.md
/work/acme/backend/.pi/themes/acme.json
```

创建结果可以概括为：

```text
SettingsManager
  global settings + project settings

ModelRuntime
  auth credential + selected model

ResourceLoader
  extension: ticket.ts
  skill: security metadata
  prompt template: review
  theme: acme
  context files:
    global AGENTS.md
    /work/acme/AGENTS.md
    backend/CLAUDE.md
  customPrompt: backend/.pi/SYSTEM.md
  appendPrompt: backend/.pi/APPEND_SYSTEM.md

SessionManager
  current leaf messages + restored model/thinking

AgentSession
  tools: read, bash, edit, write, ticket_lookup
  systemPrompt:
    SYSTEM body
    APPEND_SYSTEM body
    three project_instructions blocks
    security skill metadata
    current cwd
```

此时：

- `review.md` 正文尚未进入上下文；
- `security/SKILL.md` 正文尚未进入上下文，只有元数据；
- `acme.json` 不进入上下文；
- `settings.json`、`auth.json`、`models.json` 不进入上下文；
- `ticket.ts` 源码不进入上下文，但它注册的 tool schema 会进入 `tools`，snippet 可进入 system prompt；
- session 当前分支消息进入 `messages`。

如果用户随后输入：

```text
/review payment
```

模板展开后的文本进入 user message。`before_agent_start` 可以同时追加 custom message 或覆盖本轮 system prompt；随后 extension `context` hook 还可以改变发送前的 messages。

最终 provider 收到的逻辑结构类似：

```ts
{
  systemPrompt: "<SYSTEM + APPEND + project context + skill metadata + cwd>",
  messages: [
    ...restoredSessionMessages,
    {
      role: "user",
      content: [
        {
          type: "text",
          text: "Review module payment. Focus on correctness, security, and missing tests."
        }
      ]
    }
  ],
  tools: [
    readTool,
    bashTool,
    editTool,
    writeTool,
    ticketLookupTool
  ]
}
```

## 10. 开关与信任矩阵

| 开关或状态 | 自动资源 | 显式 CLI 资源 | AGENTS/CLAUDE | SYSTEM/APPEND |
|---|---|---|---|---|
| 项目不可信 | 不加载项目 `.pi/*` 和项目 `.agents/skills` | 临时 CLI 资源仍可加载 | 仍加载 | 回退到全局文件 |
| `--no-extensions` | 不加载 settings/package/自动扩展 | `--extension` 仍加载 | 不受影响 | 不受影响 |
| `--no-skills` | 不加载 settings/package/自动技能 | `--skill` 仍加载 | 不受影响 | 不受影响 |
| `--no-prompt-templates` | 不加载自动模板 | `--prompt-template` 仍加载 | 不受影响 | 不受影响 |
| `--no-themes` | 不加载自动主题 | `--theme` 仍加载 | 不受影响 | 不受影响 |
| `--no-context-files` | 不受影响 | 不受影响 | 不加载 | SYSTEM/APPEND 仍可加载 |
| active tools 不含 `read` | 技能仍可被发现 | 技能仍可被发现 | 正常加载 | 技能元数据不拼进 system prompt |

## 11. 直接 SDK 调用与 CLI 调用的区别

直接调用：

```ts
const { session } = await createAgentSession({
  cwd: "/work/acme/backend",
});
```

SDK 自己会创建默认的 ModelRuntime、SettingsManager、SessionManager 和 ResourceLoader，并执行 reload。

CLI 路径在 SDK 外多做了：

- session 查找、resume、fork、continue；
- 项目信任交互；
- CLI 资源路径和 `--no-*` 开关；
- scoped model 解析；
- extension flag 处理；
- print/TUI/RPC 模式绑定；
- 初始 stdin、`@file` 和图片准备。

因此，SDK 的 `createAgentSession()` 是核心组装器，CLI 的 `main()` 是带信任、会话选择和模式生命周期的上层 orchestration。
