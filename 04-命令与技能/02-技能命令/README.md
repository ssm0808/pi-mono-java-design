# CampusClaw Skill Command 设计

[返回导航](../README.md) · [通用模块](../00-Slash-Command通用模块/README.md)

| 属性 | 值 |
|---|---|
| 文档版本 | 4.0.1 |
| 更新日期 | 2026-09-14 |
| 设计仓基线 | `0eaa70ff365bf4d4e328b3473809341ca4cfc58d` |
| Skill 发现候选 | `9d0d76f4a571b559dc77ae52736caebbcc8fad88`（PR #210，已通过 a8192e047f4061bd385297d3dc6c4358362d0d49 合并） |
| Skill 名称专项复核 | `0300541fbbe3db8b05ffa1ac953f15f01df74b3e`（2026-09-04，本地源码提交；只复核名称规则与消费者） |
| 状态 | Builtin 与 Skill Command 由用户统一负责设计、实现和集成；B13/B14 语义已确认，精确契约已定稿，可进入实现，执行仍 target-only |

## 1. 职责与当前目标

Builtin 与 Skill Command 由用户统一负责设计、实现和集成。共享 GET 的轻量描述符、两类命令合并、固定排序与状态过滤已确认；Builtin 来源过滤只适用于内部 Builtin 专属解析，不是共享 GET 的全局限制。POST 保留已确认 Builtin JSON 契约；Skill 请求联合类型、SSE 执行结果和 Events 集成按 B13/B14 已确认语义实施。
PR #210 的动态 SkillCommandSource 可保留，但 Registry 必须在调用 Source 前按来源过滤。
内部 Builtin 专属解析不读取 Skill 来源；共享 GET 必须取得完整 Agent 快照，不触发刷新，无完整快照整体返回 503。
现有 Skill 发现定义只展示，不安装伪 Handler；用户统一补齐真实执行定义。

![发现与执行边界](设计图/skill_catalog.svg)

[PlantUML 源码](设计图/diagram.puml#L1) · [原尺寸 SVG](设计图/skill_catalog.svg)

## 2. 源码证据

PR #210 的 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/SkillCommandSource.java`
读取 Prepared Agent 元数据并生成描述符，没有执行 Handler。
同基线 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/skill/SkillNamePatterns.java`
已集中兼容/严格策略的正则字符串、编译模式与长度上限，Loader 仍使用兼容策略。
这是已观察到的实现差距，不是允许保留的产品兼容要求；必须按第 3 节统一严格校验。
旧候选 `0bb794f2` 的 SkillNameValidator 已删除；发现结果使用只读 DTO，并复制建议列表。
这些是前置 PR 已合并的发现行为，不是已发布 HTTP 执行能力。

pi `4af9d21d3b4d664e4a29fcabfec85171077248e3` 的
`packages/coding-agent/src/core/skills.ts` 提供 Skill 发现，而
`packages/coding-agent/src/core/agent-session.ts` 有本地展开/执行语义；
这不是 CampusClaw 的企业 HTTP 契约。完整外部基线和差异分类见[通用模块](../00-Slash-Command通用模块/README.md)。

### 2.1 名称专项复核

本节保留旧分支 `3004419a467b77bac08d0f2b3dad21f8815568c5` 的证据，并追加本地源码提交
`0300541fbbe3db8b05ffa1ac953f15f01df74b3e` 的名称专项复核。后者没有替代其余章节的历史
基线，也不表示本文已复核所有 Command 实现。以下 Java 路径均相对 `pi-mono-java` 仓库。

| 分类 / 基线 | 源码路径与符号 | 结论 |
|---|---|---|
| 旧实现 / `3004419a` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/skill/Skill.java`：`NAME_PATTERN`；同包 `SkillLoader.java`：`validateName` | 加载使用宽松 `^[a-z0-9-]+$` |
| 旧实现 / `3004419a` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/SkillNameValidator.java`：`isValid`；同包 `SkillCommandSource.java`：`descriptor`、`skillNameOf` | 命令路径使用独立严格规则，和加载路径不一致 |
| 复核实现 / `0300541f` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/skill/SkillNamePatterns.java:15-49` | 规则已迁到 Skill 域，但仍有 LEGACY/STRICT 两套正则、Pattern 和判定方法；集中位置没有消除策略分裂 |
| 复核实现 / `0300541f` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/skill/SkillLoader.java`：`parseSkillFile:110-118`、`validateName:138-150` | 缺少名称仍回退文件夹名；加载仍使用 `SkillNamePatterns.LEGACY` |
| 复核实现 / `0300541f` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/service/command/SkillCommandSource.java`：`resolved` | 命令发现使用 `SkillNamePatterns.isStrictValid`；`-pdf`、`pdf-`、`pdf--tools` 仍形成加载与发现差异 |
| pi 对照 / `4af9d21d` | `packages/coding-agent/src/core/skills.ts`：`validateName`、`loadSkillFromFile:320-344` | 检查首尾及连续连字符，但名称错误仅记录 warning，描述有效时仍加载；CampusClaw 不采用此容忍行为 |
| 已确认目标 / 产品约束与安全加固 | Skill 域唯一严格规则；所有消费者一致拒绝 | 删除兼容分支，让加载、模型发现、命令发现与执行共享相同名称边界；执行仍属 target-only |

## 3. 名称统一严格校验

```regex
^[a-z0-9]+(?:-[a-z0-9]+)*$
```

`name` 指 Skill 包名称，不含命令命名空间前缀。入口解析命令前缀后，
必须复用 Skill 域的同一套严格规则；共享 HTTP 联合类型已由 B13 确认。规则对齐
[Agent Skills specification](https://agentskills.io/specification)。正则本身没有 64 字符上限，
必须同时校验长度为 1～64 个字符。以下规则是 2026-09-04 已确认目标，名称专项复核源码仍有第 2 节所列差距：

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

[PlantUML 源码：`skill_name_validation`](设计图/diagram.puml#L35)

## 4. 统一实施与集成要求

共享 GET 的 Skill 名称为 `skill:<name>`，idle 时排在固定 Builtin 顺序之后并按 name 排序；
running 时整项省略。仅返回 name/kind/description 与
`input: {"hint":"[request]","acceptsFiles":true}`，不输出 Skill ID、版本、正文、路径或建议值。
完整规则与最新源码差距见[共享 GET 契约](../00-Slash-Command通用模块/README.md#31-get-轻量清单已确认)。
这些是已确认的发现投影，不等于 Skill POST 已实现或已发布。

B13/B14 已确认共享 `POST /sessions/{sessionId}/command`。精确联合请求、错误与 SSE 示例见
[当前命令契约](../../01-总体架构/01-CampusClaw多Agent运行时/chat-api-review.html#executeSessionCommand)。
Builtin 保持 JSON；Skill 使用 name="skill:<name>"、arguments 与可选 fileIds，成功返回请求级
SSE。普通 Events 不解析 Slash；Skill 的首帧 user.message 保留展开前调用，随后复用普通 Agent、
Tool 和 idle 事件。无 commandId/通用生命周期；user.message.eventId 即本次根消息，
sourceEventId 和 targetEventId 支撑确认、中断与历史归属。

全局目标类图复用[通用模块主图](../00-Slash-Command通用模块/设计图/target_slash_command_global_classes.svg)，
不维护一张割裂的 Skill 总图。SkillCommandDefinition 显式组合准入策略和真实 Handler；
Handler 委派 SkillExecutionService，后者使用普通消息接受/执行应用服务，不越层调用 Controller。

![Skill 快照与执行下钻](设计图/target_skill_execution.svg)

[PlantUML 源码](设计图/diagram.puml#L71) · [原尺寸 SVG](设计图/target_skill_execution.svg)

受理前从一份完整缓存解析绑定、定义和 Skill 正文，固定成不可变请求快照；GET 和 POST 是独立
快照，不能把先前清单当作授权。POST 在所属锁/事务内重检绑定、权限和容量，原子接受根消息并
将 Session 改为 running；接受失败不写成功历史，不回退普通消息。Skill 只作为用户选择的资源
上下文，不提升为系统权限，不将包内指令当作认证或工具授权。

内部 Session 记录保留恢复模型上下文所需的展开内容和绑定版本（不是新增独立 Skill 审计副本），
公开投影只显示原调用和执行结果。恢复不得重新读取新 Skill 正文悄悄改变旧任务；凭据仍只存在
Active Holder 内存，实例丢失不自动恢复凭据或重放副作用工具。引用文件依然通过原有 Skill
资源解析边界读取，本次快照承诺只覆盖已解析正文和元数据，不虚构所有外部文件均被冻结。
参数/附件复用普通消息上限；展开后的输入预算在接受前检查，不截断 Skill 正文后继续。
B15 沿用部署统一保留策略，未配置时不新增自动清理；删除按根消息及必要引用保持对账完整。
不新增 Maven 依赖，继续使用现有缓存、JDK/Jackson 与 Session 组件。

### 4.1 执行源码证据与差异

设计基线 `9096f1e9ae445e67292c5e7d5a9e0d2ac10d8f5d`；Java 固定
`dfb90cac4e233e09a0b8f047f7e9f4682f5ad238`，只补充下面符号，不覆盖 §2 的历史名称专项证据。

| 仓库 / 相对路径与符号 | 已观察行为 | 已确认目标与理由 |
|---|---|---|
| pi-mono-java · modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/service/command/SkillCommandSource.java · list/resolved/hasSkillMarkdown | prepareCached 后产生发现 DTO 和 SkillCommandSnapshotDTO，包含内部 Skill 身份、版本与内容；使用 ClawConstants.Skill.isValidName，检查规范位置；不执行 Skill | 保留发现事实，增加真实执行 Definition/Handler 与共享消息接受链；不能将发现实现当成 HTTP Skill 执行已发布 |
| pi-mono · packages/coding-agent/src/core/agent-session.ts · _expandSkillCommand/prompt，固定 5cd93f688aaab89dbb6dfa4aca535f21796ae185 | /skill:name 查本地 Skill 并展开正文；找不到或读失败可返回原文本；扩展后作为模型输入 | 学习展开语义；HTTP 精确匹配失败必须拒绝、不回退；正文不进公共回执。产品约束与安全加固，不复制 CLI 文件路径或内存排队 |
| pi-mono-java · modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEntryCodec.java · userEntry/toAgentMessages | 公开 user payload 与模型恢复已有不同方法，但 userMessage 目前仅按公开文本/附件重建 | 需增加内部展开输入与公开原调用的独立投影，恢复不能重新解释不同版本 Skill；target-only 架构变更 |

上一版的 pi 4af9d21d 对照仍保留在历史证据；Skill 展开证据使用项目固定 5cd93f，不静默漂移。
现有源码缺口是执行接入、快照事务及安全恢复，不是改一个 HTTP Content-Type 即可完成。

## 5. 实施验收

先落 SkillCommandDefinition/Handler 与 SkillExecutionService 骨架，再复用 SessionEventApplicationService、
共享投影和响应绑定；最后接入联合 VO。验收 Skill 正常 SSE、确认分段、原消息中断、根 ID 对账，
以及解析失败不接受、受理前绑定变更拒绝、受理后版本固定、展开预算超限拒绝、公开历史不泄露正文，
恢复不换版本、丢失凭据不自动重跑。Builtin JSON 和 GET 轻量清单必须保持现有行为。


统一验收同时覆盖 Builtin 与 Skill Command。Builtin 专项验证来源视图只含七项、Builtin Registry 不调用 SkillCommandSource；
Skill 专项验证发现、真实执行与失败恢复；最终共享清单和请求联合类型覆盖两类命令，不能以 POST skill:* 必须失败作为整体验收。
skills Builtin 只展示最新完整绑定快照中的名称/描述，不等于发布 Skill Command。

名称规则的共享验收覆盖加载与命令消费者，执行入口校验也由用户统一补齐：

- 加载、命令发现和执行使用同一组名称样例，统一接受 `a`、`0`、`pdf-tools` 和长度恰为 64 的合法名称；统一拒绝空值、空字符串、65 字符、`-pdf`、`pdf-`、`pdf--tools`、`PDF`、`pdf_tools`、空白及换行。
- 单文件加载拒绝缺少、非字符串的 frontmatter 名称及文件夹名称不一致；批量扫描返回集合、模型发现提示词和命令清单均不包含非法 Skill，直接执行也不能绕过校验。
- Skill 域只保留一份严格正则字符串、编译后的 Pattern 和长度上限；不存在 LEGACY 加载分支、Command 专用第二套正则或“非法名称加载成功”的兼容测试。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 4.0.1 | 2026-09-14 | 按发现、名称与执行职责整理说明，并分阶段呈现执行和恢复时序。 |
| 4.0.0 | 2026-09-08 | Skill 通过共享 Command SSE 执行，复用快照、绑定重检和历史恢复。 |
| 3.2.0 | 2026-09-07 | GET 投影轻量描述符并在 running 时过滤 Skill。 |
| 3.1.3 | 2026-09-05 | Builtin、Skill 与共享 HTTP 统一实施及验收。 |
| 3.1.2 | 2026-09-04 | 加载、发现和执行统一严格名称校验。 |
| 3.1.1 | 2026-09-04 | Skill 发现与执行分别维护职责边界。 |
| 3.1.0 | 2026-09-04 | 发现骨架与执行 Handler 分离，历史复用领域记录。 |
| 3.0.4 | 2026-09-01 | 命令相关表述只使用“命令清单”；Skill 文件位置统一表述为“文件夹” |
| 3.0.3 | 2026-09-01 | Skill 名称遵循 Agent Skills 规则，参数和附件复用普通消息限制。 |
| 3.0.2 | 2026-08-31 | 以规则表说明名称、发现、快照和信任分层。 |
| 3.0.1 | 2026-08-31 | 面向读者统一使用“命令清单”，明确 Skill 命令发现不依赖磁盘扫描 |
| 3.0.0 | 2026-08-31 | 定义 HTTP Skill 命令、调用快照与可恢复执行。 |
