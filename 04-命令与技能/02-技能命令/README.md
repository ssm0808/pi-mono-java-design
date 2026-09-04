# CampusClaw Skill Command 设计

[返回命令与技能导航](../README.md) ·
[通用模块](../00-Slash-Command通用模块/README.md)

| 属性 | 值 |
|---|---|
| 文档版本 | 3.0.5 |
| 设计日期 | 2026-09-04 |
| CampusClaw 指定源码基线 | `c1311f69f504e7e799fa2467fd6a9d95b3f91b99` |
| CampusClaw 复核 HEAD | `94abd2abcb03943daef5118115e4b4a21f1c4d5f` |
| Skill 名称专项复核 | `0300541fbbe3db8b05ffa1ac953f15f01df74b3e`（2026-09-04，本地源码提交；只复核名称规则与消费者） |
| pi 基线 | `4af9d21d3b4d664e4a29fcabfec85171077248e3` |
| 设计状态 | target-only；当前 Skill 仅支持受管文件加载与模型自动发现，没有 HTTP Skill Command |

## 1. 结论

Skill 命令格式：

```text
/skill:<name> [request]
```

| 规则 | 结论 |
|---|---|
| HTTP `name` | `skill:<name>`，不含 `/` |
| Skill 名称 | 1～64 个字符；只使用小写字母、数字和连字符；连字符不能位于首尾或连续出现 |
| 名称与文件夹 | `SKILL.md` 的 `name` 必填，并与所在文件夹同名 |
| 命名冲突 | 与 Builtin 分属不同命名空间，不设置优先级 |
| Session 状态 | 仅 `idle` 时可执行；`running` 时仍显示但标记不可用 |
| 参数 | 可选；长度限制与普通用户消息相同 |
| 附件 | 可选；数量和校验规则与普通用户消息相同 |

名称的精确格式为：

```regex
^[a-z0-9]+(?:-[a-z0-9]+)*$
```

`skill:` 是 CampusClaw 的命令命名空间，不属于 Skill 包名称。HTTP 层移除该前缀后，
复用 Skill 域的同一套严格规则。规则对齐
[Agent Skills specification](https://agentskills.io/specification)。正则本身没有 64 字符上限，
必须同时校验长度。以下规则是 2026-09-04 已确认目标，名称专项复核源码仍有第 7 节所列差距：

- `SkillNamePatterns` 只保留一份严格正则字符串、编译后的 Pattern 和长度上限，加载、
  命令发现和执行全部引用；移除 LEGACY 常量和方法，不在 HTTP/Command 包中另建名称 Validator。
- 非法名称在加载时就拒绝，不进入已加载 Skill 集合或模型发现提示词；命令发现和执行同样
  拒绝。禁止保留“加载可用、命令隐藏”的兼容分支。
- `SKILL.md` 的 `name` 必须是非空字符串，与所在文件夹及绑定元数据逐字符一致；缺少名称
  不回退到文件夹名，也不通过字符串强制转换、裁剪、替换连字符或自动改名修正非法值。
- 单文件加载失败沿用 `SkillLoadException`；批量扫描可以沿用跳过无效文件的行为，但不能
  把无效 Skill 加入返回集合。存量非法名称必须修正后重新加载。

取消宽松加载是已确认产品约束与安全加固。旧代码或兼容测试只能证明曾经接受过非法名称，
不能建立产品迁移要求。统一规则避免同一 Skill 能进入模型发现、却不能通过命令发现或执行。

![Skill 名称统一严格校验目标](设计图/skill_name_validation.svg)

[PlantUML 源码：`skill_name_validation`](设计图/diagram.puml#L93)

## 2. 命令清单如何生成

每次查询命令清单时，`SkillCommandSource`：

1. 从 Session 取不变 `agentId`。
2. 通过 `AgentRuntimeManager.prepareCached(agentId)` 读取最新 complete 版本，不触发远程刷新。
3. 校验 `SKILL.md` 名称、所在文件夹名称和绑定元数据一致，再按名称稳定排序并生成
   `skill:<name>` Descriptor。
4. 只返回名称、描述、可用性和输入提示；不返回正文、路径、Skill ID 或版本。

`PreparedAgentRuntime.skills()` 和 `findSkill()` 已支持精确名称查找。目标设计在其上建立
动态 Source，不把每个 Skill 注册成 Spring Bean。

![Skill 命令清单解析](设计图/skill_catalog.svg)

[PlantUML 源码：`skill_catalog`](设计图/diagram.puml#L1)

## 3. 调用时快照

### 3.1 为什么不能只保存 Skill ID

Agent 刷新会替换 Skill 版本、正文和资源，也可能删除绑定。历史若只记录 Skill ID 或
文件路径，重放时就可能读取到不同内容。

因此每次调用都把完整快照写入 `t_session_records(type='skill.snapshot')`，不跨调用去重。
快照至少包含：

```text
commandId
agentId
agentVersion
skillId
skillVersion
name
description
skillMarkdown
references[]: name, fileType, content
templates[]: name, fileType, content
capturedAt
```

快照使用 `lane='main'`、`run_id=commandId`。`record_seq` 与 Entry 共享 Session 序列，
但快照不进入 GET Events 或公共 SSE。因此公开 `entrySeq` 可以有缺口；调用方只能排序，
不能补号或推断缺口内容。

### 3.2 原子接受顺序

Skill 调用按以下顺序接受；全部成功后才建立 SSE：

1. 在 Agent 锁内读取最新 complete 版本的元数据、`SKILL.md` 和资源；随后释放 Agent 锁。
2. 锁定 Session，校验 idle、命令参数、附件与快照完整性。
3. 写入包含 `commandId`、`commandName`、原始 `arguments` 和 `fileIds` 的活动 `user.message`。
4. 写入私有 `skill.snapshot` Record。
5. 写入锚定在新 User Entry 的 `command.started` sidecar。
6. 将 Session 置为 running，`active_leaf_id` 指向新 User Entry。

任一步失败都回滚，并在流建立前返回 ResultBean。不能先写用户消息，再检查 Skill 正文。

![Skill 原子接受](设计图/skill_acceptance.svg)

[PlantUML 源码：`skill_acceptance`](设计图/diagram.puml#L21)

## 4. 模型请求分层

`ModelRequestAssembler` 不得把 `SKILL.md + arguments + fileIds` 拼成一段文本，必须保留三层：

| 层 | 来源 | 信任语义 | 恢复来源 |
|---|---|---|---|
| Skill instruction | 调用时 `skill.snapshot` | 受管、已验证的 Skill 指令层 | 私有 Record |
| User text | 结构化 `arguments` | 不可信 User 输入层 | `user.message` |
| User files | `fileIds` | 普通用户附件层 | `user.message` |

这是相对 pi `agent-session.ts:1331-1334` 的安全加固，避免把用户参数当成受信任指令。

命令关联的 `user.message` 只把 `arguments + fileIds` 放入 User 层。UI 使用的
`/skill:<name>` 不进入模型内容；Skill 指令由快照投影器单独注入。

![Skill 信任分层](设计图/skill_trust_layers.svg)

[PlantUML 源码：`skill_trust_layers`](设计图/diagram.puml#L49)

## 5. `disable-model-invocation`

CampusClaw `SkillLoader.java:134-137` 已解析 `disable-model-invocation`，
`RuntimeAgentPromptLoader.java:67-72` 已将该 Skill 排除在模型自动发现提示词外。

该字段只禁止模型自动发现和调用，不禁止用户显式调用。当前 Agent 直接绑定且快照完整的
Skill 都出现在命令清单中。这与 pi `skills.ts:347-356` 的语义一致。

## 6. 执行、断线和恢复

- Skill Handler 完成接受事务后，用新的 `user.message` 作为活动分支叶子，
  并发起一次标准 Agent 执行。
- Assistant、Thinking、Tool 和 Compaction 事件复用现有 Runtime 领域投影；
  Skill 不建立专属消息模型。
- `command.completed.sourceEventSeq` 指向最终 `assistant.message.completed`。
- HTTP 断线不取消已接受执行；调用方不重放 POST，通过 GET Events 恢复。
- Agent 刷新、Skill 修改或删除后，恢复只读取 `skill.snapshot`，不读当前文件。
- 历史恢复时找不到调用快照属于数据完整性错误，不允许回退到当前 Skill。

![Skill 快照重放](设计图/skill_replay.svg)

[PlantUML 源码：`skill_replay`](设计图/diagram.puml#L73)

## 7. 源码证据和差异分类

### 7.1 名称专项复核

本节保留旧分支 `3004419a467b77bac08d0f2b3dad21f8815568c5` 的证据，并追加本地源码提交
`0300541fbbe3db8b05ffa1ac953f15f01df74b3e` 的名称专项复核。后者没有替代其余章节的历史
基线，也不表示本文已复核所有 Command 实现。以下 Java 路径均相对 `pi-mono-java` 仓库。

| 分类 / 基线 | 源码路径与符号 | 结论 |
|---|---|---|
| 旧实现 / `3004419a` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/skill/Skill.java`：`NAME_PATTERN`；同目录 `SkillLoader.java`：`validateName` | 加载使用宽松 `^[a-z0-9-]+$` |
| 旧实现 / `3004419a` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/SkillNameValidator.java`：`isValid`；同目录 `SkillCommandSource.java`：`descriptor`、`skillNameOf` | 命令路径使用独立严格规则，和加载路径不一致 |
| 复核实现 / `0300541f` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/skill/SkillNamePatterns.java:15-49` | 规则已迁到 Skill 域，但仍有 LEGACY/STRICT 两套正则、Pattern 和判定方法；集中位置没有消除策略分裂 |
| 复核实现 / `0300541f` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/skill/SkillLoader.java`：`parseSkillFile:110-118`、`validateName:138-150` | 缺少名称仍回退文件夹名；加载仍使用 `SkillNamePatterns.LEGACY` |
| 复核实现 / `0300541f` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/service/command/SkillCommandSource.java`：`resolved` | 命令发现使用 `SkillNamePatterns.isStrictValid`；`-pdf`、`pdf-`、`pdf--tools` 仍形成加载与发现差异 |
| pi 对照 / `4af9d21d` | `packages/coding-agent/src/core/skills.ts`：`validateName`、`loadSkillFromFile:320-344` | 检查首尾及连续连字符，但名称错误仅记录 warning，描述有效时仍加载；CampusClaw 不采用此容忍行为 |
| 已确认目标 / 产品约束与安全加固 | Skill 域唯一严格规则；所有消费者一致拒绝 | 删除兼容分支，让加载、模型发现、命令发现与执行共享相同名称边界；执行仍属 target-only |

### 7.2 其余历史基线与目标差异

下表“观察到的行为”均指文首原有基线，不是名称专项复核提交的全量现状。

| 分类 | 证据或决策 |
|---|---|
| 观察到的 CampusClaw 行为 | `RuntimeApiConstants.java:18` 定义普通消息上限 `262144`，`UserEventRequestVO.java:28` 通过 `@Size` 使用该上限；当前没有 Skill Command 参数上限实现 |
| 观察到的 CampusClaw 行为 | `Skill.java:25,34` 定义 64 字符和宽松正则；`SkillLoader.java:104-111,140-150` 在缺少 frontmatter 名称时使用 `SKILL.md` 所在文件夹名称，且未拒绝首尾或连续连字符 |
| 观察到的行为 | `AgentRuntimeManager.java:194-253,323-363` 已校验并重建 Skill 元数据和完整 Markdown |
| 观察到的行为 | `PreparedAgentRuntime.java:57-95` 已提供绑定 Skill 索引和精确名称查找 |
| 观察到的行为 | `t_session_records` 已有私有 Record lane，但当前 `type` 只说明支持 usage；`skill.snapshot` 是目标扩展 |
| pi 对照 | pi `4af9d21d` 的 `skills.ts:92-111` 校验 64 字符、首尾和连续连字符，并使用 `/skill:name`；没有 `262144` 参数上限 |
| OpenCode 对照 | OpenCode `849c2598` 的 `skill/index.ts:37-58` 只要求名称为字符串；没有严格命名规则或 `262144` 参数上限 |
| DeepSeek Harness 对照 | DeepSeek Harness `141eb6fe` 没有 Agent Skill 包或 Skill Command 约定，不能作为这两个限制的依据 |
| Codex Harness 对照 | Codex `be33f80b` 的 `core-skills/src/loader.rs:126,759-807` 有 64 字符上限，但字符规则更宽松；没有 `262144` 参数上限 |
| Claude Managed Agents 对照 | 2026-09-01 的 [Skills 文档](https://platform.claude.com/docs/en/managed-agents/skills) 使用 Agent Skills 格式，但没有 Slash 调用参数上限 |
| 目标设计 | 动态 SkillCommandSource、共享 Handler、调用快照、附件与断线恢复均未在当前 CampusClaw 实现 |
| 安全加固 | 名称按 Agent Skills 完整规则校验；受信任 Skill 指令、User 参数和附件分层；快照缺失时禁止回退到当前文件 |
| 产品约束 | 只有 `skill:` 命名空间；`arguments` 复用普通消息上限；不开放 pi 的 Prompt/Extension 或 OpenCode 的裸 Skill 名称 |

## 8. 验收清单

- Skill 与 Builtin 即使底层名称相同也不冲突。
- 加载、命令发现和执行使用同一组名称样例，统一接受 `a`、`0`、`pdf-tools` 和长度恰为 64 的合法名称；统一拒绝空值、空字符串、65 字符、`-pdf`、`pdf-`、`pdf--tools`、`PDF`、`pdf_tools`、空白及换行。
- 单文件加载拒绝缺少、非字符串的 frontmatter 名称及文件夹名称不一致；批量扫描返回集合、模型发现提示词和命令清单均不包含非法 Skill，直接执行也不能绕过校验。
- Skill 域只保留一份严格正则字符串、编译后的 Pattern 和长度上限；不存在 LEGACY 加载分支、Command 专用第二套正则或“非法名称加载成功”的兼容测试。
- 运行中命令清单仍返回 Skill，但执行在流建立前返回 `SESSION_BUSY`。
- 快照不存在、不完整或与绑定名称不符时，用户 Entry、Record、command.started
  和 running 状态均不提交。
- `arguments` 与 `fileIds` 保持 User 输入层，Skill 正文保持受信任指令层。
- 快照不跨调用去重；修改或删除 Skill 后仍按原快照恢复。
- `disable-model-invocation=true` 的绑定 Skill 仍可由用户显式调用。
- SSE 断线后执行继续，最终 Assistant 事件与 `command.completed/failed` 可恢复。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 3.0.5 | 2026-09-04 | 确认加载、命令发现和执行统一严格名称校验，移除存量兼容例外；追加 `0300541f` 名称专项源码证据、pi warning 差异、目标校验图和一致性验收矩阵 |
| 3.0.4 | 2026-09-01 | 命令相关表述只使用“命令清单”；Skill 文件位置统一表述为“文件夹” |
| 3.0.3 | 2026-09-01 | Skill 名称对齐 Agent Skills 完整规则；参数和附件改为引用普通消息限制，并补齐五类 Harness 的依据边界 |
| 3.0.2 | 2026-08-31 | 使用规则表和动作式短句简化命名、发现、快照与信任分层说明；不改变 Skill 行为 |
| 3.0.1 | 2026-08-31 | 面向读者统一使用“命令清单”，明确 Skill 命令发现不依赖磁盘扫描 |
| 3.0.0 | 2026-08-31 | 废弃旧的本地资源扩展和 Reload 交互设计，收敛为 HTTP `/skill:name`、最新 Agent 解析、调用快照、信任分层和可恢复执行 |
