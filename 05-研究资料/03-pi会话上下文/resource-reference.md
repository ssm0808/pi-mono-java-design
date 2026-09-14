# pi 资源目录与解析规则

> 源码基线：`badlogic/pi-mono@fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc`；原核验日期：2026-07-24；文档整理：2026-09-14。
> 本文记录该固定提交的源码行为，不代表最新 pi 或 CampusClaw 目标设计。

[返回研究入口](./README.md) · [源码证据索引](./README.md#12-源码证据索引)

## 3. 两个关键根目录

### 3.1 `cwd`

CLI 从 `process.cwd()` 取得启动目录；恢复历史会话时，最终运行目录可能改成会话 header 里的 `cwd`。源码先选定 `SessionManager`，然后才基于 `sessionManager.getCwd()` 创建 cwd-bound 服务，避免从错误项目加载 `.pi` 资源。

源码证据：

- [`main.ts:486-489`](https://github.com/badlogic/pi-mono/blob/fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc/packages/coding-agent/src/main.ts#L486-L489)
- [`main.ts:568-578`](https://github.com/badlogic/pi-mono/blob/fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc/packages/coding-agent/src/main.ts#L568-L578)
- [`main.ts:741-745`](https://github.com/badlogic/pi-mono/blob/fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc/packages/coding-agent/src/main.ts#L741-L745)

### 3.2 `agentDir`

默认值是：

```text
~/.pi/agent
```

可通过环境变量 `PI_CODING_AGENT_DIR` 覆盖。`getAgentDir()` 的源码位于 `packages/coding-agent/src/config.ts:514-521`。

后文用 `$AGENT_DIR` 表示最终解析后的 `agentDir`，用 `$CWD` 表示最终会话工作目录。

## 4. 完整目录与文件清单

下面按用户级资源、跨 Agent 技能、项目级资源、祖先指令和会话持久化分区展示。大部分文件都是可选的；文件不存在时，pi 会使用默认值或跳过对应资源。

### 4.1 目录约定

| 变量 | 默认值或来源 | 作用域 |
|---|---|---|
| `$AGENT_DIR` | `~/.pi/agent`，可被 `PI_CODING_AGENT_DIR` 覆盖 | 用户级配置、模型、资源和默认会话存储 |
| `$CWD` | 最终 AgentSession 的有效工作目录 | 项目级配置、资源和上下文指令 |
| `<filesystem-root>` | 当前文件系统根目录 | 祖先指令扫描的起点 |

目录树只表达“可能出现在哪里”；文件作用、读取条件和是否进入模型请求统一放在 4.7 节表格中。

### 4.2 用户级目录

```text
$AGENT_DIR/
├── settings.json
├── trust.json
├── auth.json
├── models.json
├── models-store.json
├── AGENTS.md | AGENTS.MD | CLAUDE.md | CLAUDE.MD
├── SYSTEM.md
├── APPEND_SYSTEM.md
├── extensions/
│   ├── *.ts
│   ├── *.js
│   └── <extension>/index.ts | index.js | package.json
├── skills/
│   ├── *.md
│   └── <skill>/SKILL.md
├── prompts/
│   └── *.md
├── themes/
│   └── *.json
├── npm/node_modules/<package>/
├── git/<host>/<path>/
└── sessions/
```

这里保存跨项目共享的设置、凭据、模型配置和资源。`sessions/` 是默认会话根目录；CLI 参数或 `settings.json` 可以把会话存储改到其他位置。

### 4.3 跨 Agent 技能目录

```text
~/.agents/skills/
└── <skill>/SKILL.md
```

该目录遵循 Agent Skills 约定，只递归发现 `SKILL.md`，不把根目录普通 Markdown 自动视为技能。

### 4.4 项目级目录

```text
$CWD/
├── AGENTS.md | AGENTS.MD | CLAUDE.md | CLAUDE.MD
├── .agents/
│   └── skills/
│       └── <skill>/SKILL.md
└── .pi/
    ├── settings.json
    ├── SYSTEM.md
    ├── APPEND_SYSTEM.md
    ├── extensions/
    ├── skills/
    ├── prompts/
    ├── themes/
    ├── npm/node_modules/<package>/
    └── git/<host>/<path>/
```

项目级 `.pi` 资源和 `.agents/skills` 受项目信任状态控制。项目不可信时，最终运行时不会采用这些项目资源。

### 4.5 祖先目录指令

指令文件不只从 `$CWD` 读取。pi 还会读取 `$AGENT_DIR` 中的全局指令，并从文件系统根目录一路扫描到 `$CWD`：

```text
$AGENT_DIR/
└── AGENTS.md | AGENTS.MD | CLAUDE.md | CLAUDE.MD

<filesystem-root>/
└── .../
    ├── AGENTS.md | AGENTS.MD | CLAUDE.md | CLAUDE.MD
    └── .../
        └── $CWD/
            └── AGENTS.md | AGENTS.MD | CLAUDE.md | CLAUDE.MD
```

最终 `agentsFiles` 的顺序是：

```text
用户级全局指令
→ 高层祖先目录指令
→ 低层祖先目录指令
→ 当前目录指令
```

同一目录最多读取一份，候选优先级为：

```text
AGENTS.md > AGENTS.MD > CLAUDE.md > CLAUDE.MD
```

### 4.6 会话持久化目录

默认会话目录单独展示，因为它是 pi 自动维护的数据，不是资源配置：

```text
$AGENT_DIR/sessions/
└── --<encoded-cwd>--/
    └── <timestamp>_<session-id>.jsonl
```

例如：

```text
~/.pi/agent/sessions/
└── --work-acme-backend--/
    └── 2026-07-24T08-00-00-000Z_01-example.jsonl
```

### 4.7 文件读取总表

| 文件或目录 | 读取者 | 读取后结果 | 对模型请求的影响 | 条件 |
|---|---|---|---|---|
| `$AGENT_DIR/settings.json` | `SettingsManager` | 全局 `Settings` | 选择模型、思考等级、工具参数、资源路径等 | 始终尝试 |
| 启动 cwd 的 `.pi/settings.json` | startup `SettingsManager` | 启动阶段项目 `Settings` | 主要用于 sessionDir 选择 | CLI 当前实现会先读取；见下方边界说明 |
| 最终 session cwd 的 `.pi/settings.json` | runtime `SettingsManager` | 项目 `Settings` | 覆盖或补充全局设置 | 最终运行时仅项目可信 |
| `$AGENT_DIR/trust.json` | `ProjectTrustStore` | 最近祖先目录的 `boolean` 决策 | 决定是否读取项目 `.pi` 和项目 `.agents/skills` | 项目存在需信任资源时 |
| `$AGENT_DIR/auth.json` | `ModelRuntime` / `AuthStorage` | provider 到 credential 的映射 | 决定模型是否可用和请求认证 | 创建时读取；不存在会创建 `{}` |
| `$AGENT_DIR/models.json` | `ModelRuntime` / `ModelConfig` | 自定义 provider、model、override | 决定模型目录和 provider 参数 | 可选；不存在视为空 |
| `$AGENT_DIR/models-store.json` | `FileModelsStore` | 动态 provider 模型目录缓存 | 补充模型目录 | 按 provider 读取；不存在会按存储逻辑初始化 |
| session `*.jsonl` | `SessionManager` | append-only 消息树 | 当前叶子分支转换为 `messages` | 恢复、继续、fork 时 |
| `$AGENT_DIR` 和根目录至 `$CWD` 的指令文件 | `loadProjectContextFiles()` | `{path, content}[]` | 正文原样进入 `<project_context>` | 未使用 `--no-context-files` |
| `SYSTEM.md` | `DefaultResourceLoader` | `customPrompt` | 替换 pi 默认 system prompt，再附加 context/skills/cwd | CLI 优先；项目文件需可信 |
| `APPEND_SYSTEM.md` | `DefaultResourceLoader` | `appendSystemPrompt[]` | 追加到 system prompt | CLI 优先；项目文件需可信 |
| `extensions/**/*.ts|js` | extension loader | handler、tool、command、provider 等注册表 | 工具 schema、提示片段和 hook 可改变请求 | 项目扩展需可信 |
| `skills/**/*.md` | skill loader | `Skill` 元数据 | 启动时只把名称、描述、路径加入 system prompt | `read` 工具启用；项目技能需可信 |
| `prompts/*.md` | prompt-template loader | `PromptTemplate` | 启动时不进上下文；调用 `/name` 后替换 user message | 项目模板需可信 |
| `themes/*.json` | theme loader | `Theme` | 只影响 TUI，不进入 LLM context | 项目主题需可信 |
| package `package.json` | `DefaultPackageManager` | `pi.extensions/skills/prompts/themes` 路径 | 间接加载上述资源 | 项目 package 需可信 |
| `.gitignore`、`.ignore`、`.fdignore` | package/skill 扫描器 | ignore pattern | 决定哪些资源不被发现 | 扫描对应目录时 |

## 6. 每类文件内容、解析结果和例子

以下例子均为脱敏的说明性内容，不是本机真实配置。

### 6.1 settings.json

全局和项目级配置示例见[示例集](./file-examples.md#481-agent_dirsettingsjson)。一般设置按 deep merge 合并，项目同名配置覆盖全局值。

资源与 package 使用额外汇总逻辑：PackageManager 分别读取 global/project settings，并把两边资源加入候选集合，不是直接丢弃全局数组。

JSON 原文不进入 system prompt；它们控制模型选择、资源目录、压缩、队列、网络和工具行为。

### 6.2 trust.json

文件格式示例见[示例集](./file-examples.md#483-agent_dirtrustjson)。

查询 `/work/acme/backend` 时会逐级向上找最近的记录，因此 `/work/acme: true` 能信任其子目录。

`trust.json` 不进入模型上下文，只控制项目资源能否加载。

### 6.3 auth.json

文件格式示例见[示例集](./file-examples.md#484-agent_dirauthjson)。

类型是：

```ts
Record<string, ApiKeyCredential | OAuthCredential>
```

读取后保存为 credential store。API key 可继续解析环境变量或其他配置值。`AuthStorage` 首次使用时会创建父目录和内容为 `{}` 的文件，并将权限设置为 `0600`。

安全边界：

- `auth.json` 原文和密钥不进入 system prompt/messages；
- 只在发请求时解析所选 provider 的认证；
- 文档、日志和示例不应复制真实 token。

### 6.4 models.json

文件格式示例见[示例集](./file-examples.md#485-agent_dirmodelsjson)。

读取后：

1. JSON comments 被剥离；
2. TypeBox schema 校验 `providers`；
3. 每个 provider 被 clone、deep-freeze；
4. 与内建 provider/model 合并；
5. `modelOverrides` 可覆盖已知 model；
6. schema 错误被保存为 diagnostic，不把无效 provider 加入 map。

该 JSON 不原文进入 LLM context。解析出的 `Model` 决定 provider、API、上下文窗口、最大输出和兼容参数。

### 6.5 models-store.json

文件格式示例见[示例集](./file-examples.md#486-agent_dirmodels-storejson)。

读取后按 provider 返回 `ModelsStoreEntry`。它影响模型目录，但不进入 prompt。

### 6.6 AGENTS.md / CLAUDE.md

文件格式示例见[示例集](./file-examples.md#487-agentsmdagentsmdclaudemdclaudemd)。

单个目录的文件名优先级严格是：

```text
AGENTS.md
AGENTS.MD
CLAUDE.md
CLAUDE.MD
```

每个目录最多取第一个成功读取的候选。

假设 `$CWD=/work/acme/backend`，存在：

```text
$AGENT_DIR/AGENTS.md
/work/AGENTS.md
/work/acme/AGENTS.md
/work/acme/backend/CLAUDE.md
```

加载顺序是：

```text
1. $AGENT_DIR/AGENTS.md
2. /work/AGENTS.md
3. /work/acme/AGENTS.md
4. /work/acme/backend/CLAUDE.md
```

注意：

- 全局 context file 最先；
- 项目祖先按 root 到 cwd 排列；
- 不会把 `AGENTS.md` 与同目录 `CLAUDE.md` 同时加载；
- 文件正文原样保留；
- buildSystemPrompt 时会包装为：

```xml
<project_context>

Project-specific instructions and guidelines:

<project_instructions path="/work/acme/AGENTS.md">
# Repository instructions

- Use Java 21.
</project_instructions>

</project_context>
```

这类文件是最直接的 system prompt 内容来源。

### 6.7 SYSTEM.md

文件格式示例见[示例集](./file-examples.md#488-systemmd)。

发现优先级：

```text
--system-prompt 的参数
  > 可信项目 $CWD/.pi/SYSTEM.md
  > $AGENT_DIR/SYSTEM.md
  > pi 内建默认 system prompt
```

`--system-prompt` 参数如果指向存在的文件，会读取文件；否则把参数本身当作 literal prompt。

`SYSTEM.md` 的语义是**替换默认 prompt**，不是追加。但即使使用 custom prompt，后面仍会追加：

1. APPEND_SYSTEM；
2. AGENTS/CLAUDE project context；
3. 可见技能元数据；
4. current working directory。

### 6.8 APPEND_SYSTEM.md

文件格式示例见[示例集](./file-examples.md#489-append_systemmd)。

发现优先级：

```text
--append-system-prompt 的参数列表
  > 可信项目 $CWD/.pi/APPEND_SYSTEM.md
  > $AGENT_DIR/APPEND_SYSTEM.md
  > 无追加内容
```

CLI 可提供多段 append source；每段同样按“存在的路径则读文件，否则按 literal”解释，最后以空行连接。

### 6.9 skill 文件

文件格式示例见[示例集](./file-examples.md#4811-skillsskillskillmd)。

标准目录示例：

```text
$CWD/.pi/skills/release/
├── SKILL.md
├── scripts/release.sh
└── references/checklist.md
```

创建时 loader 会读取整个文件，但只把 frontmatter 解析为：

```ts
{
  name: "release-check",
  description: "Checks release metadata and artifacts before publishing.",
  filePath: "/work/acme/backend/.pi/skills/release/SKILL.md",
  baseDir: "/work/acme/backend/.pi/skills/release",
  disableModelInvocation: false
}
```

如果 active tools 包含 `read`，system prompt 只得到元数据：

```xml
<available_skills>
  <skill>
    <name>release-check</name>
    <description>Checks release metadata and artifacts before publishing.</description>
    <location>/work/acme/backend/.pi/skills/release/SKILL.md</location>
  </skill>
</available_skills>
```

**SKILL.md 正文不会在启动时全部注入 system prompt。**只有：

- 模型主动使用 `read` 读取该路径；或
- 用户执行 `/skill:release-check ...`

时才读取/展开正文。显式 skill command 会去掉 frontmatter，并包装为 user message 中的 `<skill>` 块。

自动发现规则：

- `.pi/skills`、`$AGENT_DIR/skills`：根目录 `.md` 是独立技能；递归发现 `SKILL.md`；
- `.agents/skills`：忽略根目录普通 `.md`；递归发现 `SKILL.md`；
- 某目录一旦包含 `SKILL.md`，该目录作为一个技能根，不再递归其中的子技能；
- 缺少 description 的技能不加载；
- `disable-model-invocation: true` 的技能不出现在 system prompt，但仍可用显式命令调用。

### 6.10 prompt template 文件

文件格式示例见[示例集](./file-examples.md#4812-promptsreviewmd)。

读取后形成：

```ts
{
  name: "review",
  description: "Review one module",
  argumentHint: "<module>",
  content: "Review module $1. Focus on correctness, security, and missing tests.",
  filePath: "/work/acme/backend/.pi/prompts/review.md"
}
```

它**不进入初始 system prompt**。用户输入：

```text
/review payment
```

后才展开为：

```text
Review module payment. Focus on correctness, security, and missing tests.
```

并作为本轮 user message 进入上下文。默认 `prompts/` 自动发现是非递归的；子目录必须通过 settings 或 package manifest 显式加入。

### 6.11 extension 文件

最小 extension：

```ts
import { Type } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "ticket_lookup",
    label: "Ticket lookup",
    description: "Look up one ticket",
    promptSnippet: "Look up issue details by ticket id",
    parameters: Type.Object({
      id: Type.String(),
    }),
    async execute(_callId, params) {
      return {
        content: [{ type: "text", text: `Ticket ${params.id}` }],
        details: {},
      };
    },
  });
}
```

读取方式不是 `readFileSync()` 后保留文本，而是：

```ts
const module = await jiti.import(extensionPath, { default: true });
const factory = module as ExtensionFactory;
await factory(api);
```

执行后得到注册表对象。上例的影响是：

- `ticket_lookup` tool schema 加入 `agent.state.tools`；
- `promptSnippet` 可能进入默认 system prompt 的 “Available tools”；
- tool execute 输出会成为 tool-result message；
- extension 还可以通过 `before_agent_start` 每轮修改 system prompt；
- `context` hook 可以在 provider 请求前修改 messages；
- `resources_discover` 可以在绑定阶段追加技能、模板和主题路径。

扩展拥有代码执行能力，因此项目扩展受 trust gate 控制。

### 6.12 theme 文件

文件格式示例见[示例集](./file-examples.md#4813-themesacme-darkjson)。

读取后解析为 `Theme` 并用于 TUI。theme 的名称、颜色和 JSON 原文都不会进入 `systemPrompt`、`messages` 或 `tools`。

### 6.13 package.json

文件格式示例见[示例集](./file-examples.md#4814-package-根目录的-packagejson)。

如果没有 `pi` manifest，则使用约定目录：

```text
extensions/
skills/
prompts/
themes/
```

安装路径：

| package 类型 | 用户级 | 项目级 |
|---|---|---|
| npm | `$AGENT_DIR/npm/node_modules/<name>` | `$CWD/.pi/npm/node_modules/<name>` |
| git | `$AGENT_DIR/git/<host>/<path>` | `$CWD/.pi/git/<host>/<path>` |
| local | settings 文件所在 baseDir 相对路径或绝对路径 | settings 文件所在 baseDir 相对路径或绝对路径 |

package.json 本身不进模型上下文。它只决定后续应读取哪些 extension/skill/prompt/theme 文件。

### 6.14 session JSONL

文件格式示例见[示例集](./file-examples.md#4816-session-jsonl)。

读取后：

```ts
{
  messages: [
    {
      role: "user",
      content: [{ type: "text", text: "Explain the payment flow" }],
      timestamp: 1784880060000
    }
  ],
  model: {
    provider: "openai",
    modelId: "gpt-5.6-sol"
  },
  thinkingLevel: "medium"
}
```

JSONL header、entry id、parentId、timestamp、label、session info 等不会作为文本发给模型。它们用于选择分支和恢复运行状态。

## 9. 容易误判但实际不会直接进入上下文的内容

| 内容 | 实际行为 |
|---|---|
| `settings.json` 原文 | 只转成运行参数 |
| `auth.json` 原文或 token | 只用于 provider 认证 |
| `models.json` 原文 | 只转成 provider/model 对象 |
| `models-store.json` 原文 | 只作为模型目录缓存 |
| extension TypeScript 源码 | 执行并形成注册表，不作为 prompt 文本 |
| skill 正文 | 启动时只提取 frontmatter；正文按需读取 |
| prompt template 正文 | 只有调用 `/template` 才成为 user message |
| theme JSON | 只影响 TUI |
| package.json | 只解析资源路径 |
| session header 和控制 entry | 用于树、分支、model/thinking 恢复 |
| `custom` session entry | 扩展持久状态，不进入 LLM context |
| sibling branch | 当前 leaf 路径以外不进入 messages |
| compaction 前被摘要替代的旧消息 | 不再直接进入 messages |
