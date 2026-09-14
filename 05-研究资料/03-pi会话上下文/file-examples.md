# pi 资源文件完整示例

> 源码基线：`badlogic/pi-mono@fc85bdd88be93b1e9a6b6bcfa41c684282ec79cc`；原核验日期：2026-07-24；文档整理：2026-09-14。
> 本文记录该固定提交的源码行为，不代表最新 pi 或 CampusClaw 目标设计。

[返回研究入口](./README.md) · [源码证据索引](./README.md#12-源码证据索引)

### 4.8 可直接参考的完整目录 demo

下面给出一套可落盘的最小示例。假设：

```text
$AGENT_DIR=/Users/alice/.pi/agent
$CWD=/work/acme/backend
```

<details>
<summary>展开完整示例目录</summary>

```text
/Users/alice/.pi/agent/
├── settings.json
├── trust.json
├── auth.json
├── models.json
├── models-store.json
├── AGENTS.md
├── SYSTEM.md
├── APPEND_SYSTEM.md
├── extensions/
│   └── hello.ts
├── skills/
│   └── release-check/
│       └── SKILL.md
├── prompts/
│   └── review.md
├── themes/
│   └── acme-dark.json
├── npm/node_modules/@acme/pi-resources/
│   └── package.json
├── git/github.com/acme/pi-resources/
│   └── package.json
└── sessions/--work-acme-backend--/
    └── 2026-07-24T08-00-00-000Z_01-example.jsonl

/Users/alice/.agents/skills/
└── incident-response/
    └── SKILL.md

/work/acme/
├── AGENTS.md
└── backend/
    ├── CLAUDE.md
    ├── .agents/
    │   └── skills/
    │       └── backend-test/
    │           └── SKILL.md
    └── .pi/
        ├── settings.json
        ├── SYSTEM.md
        ├── APPEND_SYSTEM.md
        ├── extensions/
        │   ├── .gitignore
        │   └── project-policy.ts
        ├── skills/
        │   ├── .ignore
        │   └── java-review/
        │       └── SKILL.md
        ├── prompts/
        │   ├── .fdignore
        │   └── module-review.md
        └── themes/
            └── project-dark.json
```

</details>

以下 demo 同时适用于全局目录和对应的可信项目目录。项目文件只需要把路径从 `$AGENT_DIR/...` 换成 `$CWD/.pi/...`。

#### 4.8.1 `$AGENT_DIR/settings.json`

用途：全局模型、思考等级、session 和资源配置。适合用户手写或通过 pi 设置界面维护。

```json
{
  "defaultProvider": "openai",
  "defaultModel": "gpt-5.6-sol",
  "defaultThinkingLevel": "medium",
  "defaultProjectTrust": "ask",
  "sessionDir": "~/.pi/agent/sessions",
  "compaction": {
    "enabled": true,
    "reserveTokens": 16384,
    "keepRecentTokens": 20000
  },
  "retry": {
    "enabled": true,
    "maxRetries": 3
  },
  "packages": [
    "npm:@acme/pi-resources"
  ],
  "extensions": [
    "extensions/hello.ts"
  ],
  "skills": [
    "skills"
  ],
  "prompts": [
    "prompts"
  ],
  "themes": [
    "themes"
  ]
}
```

全局相对路径以 `$AGENT_DIR` 为基准。

#### 4.8.2 `$CWD/.pi/settings.json`

用途：项目级覆盖和项目资源声明。最终 AgentSession 只在项目可信时采用。

```json
{
  "defaultThinkingLevel": "high",
  "compaction": {
    "reserveTokens": 8192
  },
  "extensions": [
    "extensions/project-policy.ts"
  ],
  "skills": [
    "skills/java-review/SKILL.md"
  ],
  "prompts": [
    "prompts/module-review.md"
  ],
  "theme": "project-dark"
}
```

项目相对路径以 `$CWD/.pi` 为基准。

#### 4.8.3 `$AGENT_DIR/trust.json`

用途：保存项目目录的信任或拒绝决定。通常由 `/trust` 和启动信任界面生成。

```json
{
  "/work/acme": true,
  "/work/untrusted-demo": false
}
```

`/work/acme: true` 会匹配 `/work/acme/backend`。该文件不应存放 prompt 或认证信息。

#### 4.8.4 `$AGENT_DIR/auth.json`

用途：保存 provider credential。通常通过 `/login` 维护，不要在仓库中提交真实密钥。

```json
{
  "openai": {
    "type": "api_key",
    "key": "$OPENAI_API_KEY"
  }
}
```

OAuth credential 的结构示例：

```json
{
  "example-oauth-provider": {
    "type": "oauth",
    "refresh": "<redacted-refresh-token>",
    "access": "<redacted-access-token>",
    "expires": 1784883600000
  }
}
```

真实文件可以同时包含多个 provider；这里分开显示只是为了避免读者把第二段误认为必须覆盖第一段。

#### 4.8.5 `$AGENT_DIR/models.json`

用途：增加自定义 provider/model，或覆盖内建模型属性。适合用户手写。

```json
{
  "providers": {
    "ollama": {
      "name": "Local Ollama",
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false
      },
      "models": [
        {
          "id": "qwen2.5-coder:7b",
          "name": "Qwen 2.5 Coder 7B",
          "reasoning": false,
          "input": ["text"],
          "contextWindow": 128000,
          "maxTokens": 16384,
          "cost": {
            "input": 0,
            "output": 0,
            "cacheRead": 0,
            "cacheWrite": 0
          }
        }
      ]
    }
  }
}
```

#### 4.8.6 `$AGENT_DIR/models-store.json`

用途：缓存动态 provider 返回的模型目录。通常由 pi 自动生成，不建议手工维护。

```json
{
  "dynamic-provider": {
    "models": [
      {
        "id": "dynamic-model-1",
        "name": "Dynamic Model 1",
        "api": "openai-completions",
        "provider": "dynamic-provider",
        "baseUrl": "https://models.example.invalid/v1",
        "reasoning": false,
        "input": ["text"],
        "cost": {
          "input": 0,
          "output": 0,
          "cacheRead": 0,
          "cacheWrite": 0
        },
        "contextWindow": 128000,
        "maxTokens": 16384
      }
    ],
    "lastModified": 1784880000000,
    "checkedAt": 1784880300000
  }
}
```

`models-store.json` 是缓存；自定义模型应写在 `models.json`，不要把两者混用。

#### 4.8.7 `AGENTS.md`、`AGENTS.MD`、`CLAUDE.md`、`CLAUDE.MD`

用途：提供全局、祖先目录或当前项目的长期指令。四个名字的内容格式相同。

```markdown
# Repository instructions

- Use Java 21.
- Keep changes inside the affected Maven module.
- Run focused tests for modified behavior.
- Never edit generated sources manually.
```

同一个目录只需要创建其中一个文件。发现优先级是：

```text
AGENTS.md > AGENTS.MD > CLAUDE.md > CLAUDE.MD
```

例如可以同时存在：

```text
$AGENT_DIR/AGENTS.md
/work/acme/AGENTS.md
/work/acme/backend/CLAUDE.md
```

三份文件会按全局、祖先、当前目录顺序一起进入 `<project_context>`。

#### 4.8.8 `SYSTEM.md`

用途：替换 pi 内建的默认 system prompt。

```markdown
You are Acme's backend coding agent.

Prioritize:

1. Correctness.
2. Backward compatibility.
3. Small, reviewable changes.
4. Focused verification.
```

可放在：

```text
$AGENT_DIR/SYSTEM.md
$CWD/.pi/SYSTEM.md
```

可信项目文件优先于全局文件；CLI `--system-prompt` 又优先于二者。

#### 4.8.9 `APPEND_SYSTEM.md`

用途：在默认或自定义 system prompt 后追加规则。

```markdown
Always report:

- Changed files.
- Focused verification commands.
- Known validation gaps.
```

可放在：

```text
$AGENT_DIR/APPEND_SYSTEM.md
$CWD/.pi/APPEND_SYSTEM.md
```

#### 4.8.10 `extensions/hello.ts`

用途：注册工具、命令、provider 或事件 hook。下面是一个可执行的最小工具扩展。

```ts
import { Type } from "@earendil-works/pi-ai";
import {
  defineTool,
  type ExtensionAPI,
} from "@earendil-works/pi-coding-agent";

const helloTool = defineTool({
  name: "hello",
  label: "Hello",
  description: "Greet one person",
  promptSnippet: "Greet a person by name",
  parameters: Type.Object({
    name: Type.String({ description: "Name to greet" }),
  }),
  async execute(_toolCallId, params) {
    return {
      content: [
        {
          type: "text",
          text: `Hello, ${params.name}!`,
        },
      ],
      details: {
        greeted: params.name,
      },
    };
  },
});

export default function (pi: ExtensionAPI) {
  pi.registerTool(helloTool);
}
```

上面的 TypeScript 内容也可以放在：

```text
extensions/hello/index.ts
```

如果使用 JavaScript 文件，需要去掉 TypeScript 的 type-only import 和参数类型：

```js
import { Type } from "@earendil-works/pi-ai";

export default function (pi) {
  pi.registerTool({
    name: "hello",
    label: "Hello",
    description: "Greet one person",
    parameters: Type.Object({
      name: Type.String(),
    }),
    async execute(_toolCallId, params) {
      return {
        content: [
          {
            type: "text",
            text: `Hello, ${params.name}!`,
          },
        ],
        details: {},
      };
    },
  });
}
```

JavaScript demo 可以放在：

```text
extensions/hello.js
extensions/hello/index.js
```

目录型扩展还可以使用自己的 `package.json` 声明入口：

```json
{
  "name": "@acme/pi-hello-extension",
  "private": true,
  "pi": {
    "extensions": [
      "./src/index.ts"
    ]
  }
}
```

<a id="4811-skillsskillskillmd"></a>
#### 4.8.11 `skills/<skill>/SKILL.md`

用途：声明一个可按需加载的专业工作流。

```markdown
---
name: release-check
description: Checks release metadata, tests, and artifacts before publishing.
---

# Release check

1. Read `references/checklist.md`.
2. Run `scripts/release.sh --dry-run`.
3. Report every failed release gate.
```

这份 demo 可以放在任一技能来源：

```text
$AGENT_DIR/skills/release-check/SKILL.md
~/.agents/skills/release-check/SKILL.md
$CWD/.pi/skills/release-check/SKILL.md
$CWD/.agents/skills/release-check/SKILL.md
```

`$AGENT_DIR/skills` 和 `.pi/skills` 还允许根目录单个 Markdown 技能，例如：

```text
$AGENT_DIR/skills/quick-review.md
```

其内容格式仍使用相同 frontmatter：

```markdown
---
name: quick-review
description: Performs a focused review of the current change.
---

Review the current change for correctness and missing tests.
```

`.agents/skills` 不自动发现这种根目录普通 Markdown 文件，只递归发现 `SKILL.md`。

#### 4.8.12 `prompts/review.md`

用途：注册 `/review` 用户提示模板。

```markdown
---
description: Review one module
argument-hint: "<module> [focus]"
---

Review module $1.

Focus on:

- Correctness.
- Security.
- Missing tests.
- Additional focus: ${2:-general}.
```

调用：

```text
/review payment concurrency
```

展开后的 user message：

```text
Review module payment.

Focus on:

- Correctness.
- Security.
- Missing tests.
- Additional focus: concurrency.
```

#### 4.8.13 `themes/acme-dark.json`

用途：定义 TUI 主题。`colors` 必须提供全部必填 token；下面是一个完整可用 demo。

```json
{
  "$schema": "https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/src/modes/interactive/theme/theme-schema.json",
  "name": "acme-dark",
  "vars": {
    "primary": "#00aaff",
    "secondary": 242,
    "green": "#00ff00",
    "red": "#ff0000",
    "yellow": "#ffff00"
  },
  "colors": {
    "accent": "primary",
    "border": "primary",
    "borderAccent": "#00ffff",
    "borderMuted": "secondary",
    "success": "green",
    "error": "red",
    "warning": "yellow",
    "muted": "secondary",
    "dim": 240,
    "text": "",
    "thinkingText": "secondary",
    "selectedBg": "#2d2d30",
    "userMessageBg": "#2d2d30",
    "userMessageText": "",
    "customMessageBg": "#2d2d30",
    "customMessageText": "",
    "customMessageLabel": "primary",
    "toolPendingBg": "#1e1e2e",
    "toolSuccessBg": "#1e2e1e",
    "toolErrorBg": "#2e1e1e",
    "toolTitle": "primary",
    "toolOutput": "",
    "mdHeading": "#ffaa00",
    "mdLink": "primary",
    "mdLinkUrl": "secondary",
    "mdCode": "#00ffff",
    "mdCodeBlock": "",
    "mdCodeBlockBorder": "secondary",
    "mdQuote": "secondary",
    "mdQuoteBorder": "secondary",
    "mdHr": "secondary",
    "mdListBullet": "#00ffff",
    "toolDiffAdded": "green",
    "toolDiffRemoved": "red",
    "toolDiffContext": "secondary",
    "syntaxComment": "secondary",
    "syntaxKeyword": "primary",
    "syntaxFunction": "#00aaff",
    "syntaxVariable": "#ffaa00",
    "syntaxString": "green",
    "syntaxNumber": "#ff00ff",
    "syntaxType": "#00aaff",
    "syntaxOperator": "primary",
    "syntaxPunctuation": "secondary",
    "thinkingOff": "secondary",
    "thinkingMinimal": "primary",
    "thinkingLow": "#00aaff",
    "thinkingMedium": "#00ffff",
    "thinkingHigh": "#ff00ff",
    "thinkingXhigh": "#ff0000",
    "thinkingMax": "#ff0088",
    "bashMode": "#ffaa00"
  }
}
```

在 settings 中选择：

```json
{
  "theme": "acme-dark"
}
```

#### 4.8.14 package 根目录的 `package.json`

用途：告诉 PackageManager 一个 npm、git 或 local package 包含哪些资源。

```json
{
  "name": "@acme/pi-resources",
  "version": "1.0.0",
  "keywords": [
    "pi-package"
  ],
  "peerDependencies": {
    "@earendil-works/pi-ai": "*",
    "@earendil-works/pi-coding-agent": "*"
  },
  "pi": {
    "extensions": [
      "./extensions"
    ],
    "skills": [
      "./skills"
    ],
    "prompts": [
      "./prompts"
    ],
    "themes": [
      "./themes"
    ]
  }
}
```

同一 package 内容可以位于：

```text
$AGENT_DIR/npm/node_modules/@acme/pi-resources/
$CWD/.pi/npm/node_modules/@acme/pi-resources/
$AGENT_DIR/git/github.com/acme/pi-resources/
$CWD/.pi/git/github.com/acme/pi-resources/
任意 settings 中配置的 local path
```

如果 package 没有 `pi` 字段，Pi 会尝试约定目录：

```text
extensions/
skills/
prompts/
themes/
```

#### 4.8.15 `.gitignore`、`.ignore`、`.fdignore`

用途：资源扫描期间排除不希望自动发现的文件或目录。三种文件使用相同的 ignore pattern 风格。

`$CWD/.pi/extensions/.gitignore`：

```gitignore
legacy.ts
drafts/
```

`$CWD/.pi/skills/.ignore`：

```gitignore
generated/
experimental/**/SKILL.md
```

`$CWD/.pi/prompts/.fdignore`：

```gitignore
drafts/
*.disabled.md
```

ignore 文件应放在正在扫描的资源目录或扫描到的子目录中，pattern 相对对应扫描 root 解释。它只影响自动发现，不会修改或删除文件。

#### 4.8.16 session `*.jsonl`

用途：保存 session header 和 append-only entry tree。通常由 pi 自动生成，不建议手工修改。

```jsonl
{"type":"session","version":3,"id":"01-example","timestamp":"2026-07-24T08:00:00.000Z","cwd":"/work/acme/backend"}
{"type":"model_change","id":"a1","parentId":null,"timestamp":"2026-07-24T08:00:00.010Z","provider":"openai","modelId":"gpt-5.6-sol"}
{"type":"thinking_level_change","id":"a2","parentId":"a1","timestamp":"2026-07-24T08:00:00.011Z","thinkingLevel":"medium"}
{"type":"message","id":"a3","parentId":"a2","timestamp":"2026-07-24T08:01:00.000Z","message":{"role":"user","content":[{"type":"text","text":"Explain the payment flow"}],"timestamp":1784880060000}}
```

这四行分别代表：

1. session header；
2. 初始模型；
3. 初始思考等级；
4. 用户消息。

恢复时只把当前 leaf 路径上能转换为 AgentMessage 的 entry 放入 `messages`。

#### 4.8.17 哪些 demo 应该手写

| 文件 | 建议 |
|---|---|
| `settings.json` | 可以手写，也可以通过设置界面维护 |
| `trust.json` | 通常交给 `/trust` 和信任界面维护 |
| `auth.json` | 通常交给 `/login` 维护；禁止提交真实密钥 |
| `models.json` | 自定义模型时手写 |
| `models-store.json` | 系统缓存，不建议手写 |
| `AGENTS.md` / `CLAUDE.md` | 项目维护者手写 |
| `SYSTEM.md` / `APPEND_SYSTEM.md` | 需要定制 system prompt 时手写 |
| extension `*.ts` / `*.js` | 扩展开发者手写 |
| `SKILL.md` | 技能开发者手写 |
| prompt `*.md` | 用户或团队手写 |
| theme `*.json` | 主题开发者手写 |
| package `package.json` | package 开发者手写 |
| ignore 文件 | 需要控制资源发现时手写 |
| session `*.jsonl` | pi 自动生成，不建议手工修改 |
