# CampusClaw Skill Command 设计

[返回导航](../README.md) · [通用模块](../00-Slash-Command通用模块/README.md)

| 属性 | 值 |
|---|---|
| 文档版本 | 3.1.1 |
| 更新日期 | 2026-09-04 |
| 设计仓基线 | `0eaa70ff365bf4d4e328b3473809341ca4cfc58d` |
| Skill 发现候选 | `9d0d76f4a571b559dc77ae52736caebbcc8fad88`（PR #210，已通过 a8192e047f4061bd385297d3dc6c4358362d0d49 合并） |
| 状态 | Skill Command 由其他同事并行开发；本会话只维护 Builtin 与共享核心衔接 |

## 1. 当前开发分工

本会话只负责七个 Builtin；Skill Command 由其他同事并行开发，不是延期或禁用。Builtin 来源视图、参数规则和验收不得提升为整个产品的 Skill 限制。共享 GET/POST 的最终命名、请求联合类型和清单合并需在 HTTP 发布前与 Skill 开发线对齐；本次不代替同事设计 Skill 执行细节。
PR #210 的动态 SkillCommandSource 可保留，但 Registry 必须在调用 Source 前按来源过滤。
Builtin 列表不读取 Skill 快照、不触发 Agent 刷新，不因 Skill 失效而失败。
现有 Skill 发现定义只展示，不安装伪 Handler；同事可独立增加真实执行定义。

![发现与执行边界](设计图/skill_catalog.svg)

[PlantUML 源码](设计图/diagram.puml#L1)

## 2. 源码证据

PR #210 的 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/command/SkillCommandSource.java`
读取 Prepared Agent 元数据并生成描述符，没有执行 Handler。
同基线 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/skill/SkillNamePatterns.java`
已集中兼容/严格策略的正则字符串、编译模式与长度上限，Loader 保持兼容策略。
旧候选 `0bb794f2` 的 SkillNameValidator 已删除；发现结果使用只读 DTO，并复制建议列表。
这些是前置 PR 已合并的发现行为，不是已发布 HTTP 执行能力。

pi `4af9d21d3b4d664e4a29fcabfec85171077248e3` 的
`packages/coding-agent/src/core/skills.ts` 提供 Skill 发现，而
`packages/coding-agent/src/core/agent-session.ts` 有本地展开/执行语义；
这不是 CampusClaw 的企业 HTTP 契约。完整外部基线和差异分类见[通用模块](../00-Slash-Command通用模块/README.md)。

## 3. 并行开发衔接要求

Skill 执行由同事并行设计与实现，不由发现骨架推断为已经发布，也不要求等待 Builtin 全部完成。
双方对齐时需明确普通 JSON 结果、完整快照、绑定重检、容量、信任分层、失败与恢复。
不得重新引入本期已移除的通用 commandId、command.started/completed/failed 或 Name 边车。
若需要私有 Skill 调用快照，必须单独评审其保留期、隐私与恢复用途，不作为当前实现要求。

## 4. 当前验收

本会话验收 Builtin 来源视图只含七项，以及 Builtin Registry 不调用 SkillCommandSource；
不把 POST skill:* 必须失败作为全产品验收。最终公共清单和请求联合类型需覆盖双方命令。
skills Builtin 只展示最新完整绑定快照中的名称/描述，不等于发布 Skill Command。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 3.1.1 | 2026-09-04 | 用户明确 Skill 由其他同事同步开发；撤销 3.1.0 的执行延期与全局拒绝解释，保留发现/执行职责分离。 |
| 3.1.0 | 2026-09-04 | Skill 执行延期；保留发现骨架但从 Builtin HTTP 来源过滤，禁止伪 Handler 与通用命令历史。 |
| 3.0.4 | 2026-09-01 | 命令相关表述只使用“命令清单”；Skill 文件位置统一表述为“文件夹” |
| 3.0.3 | 2026-09-01 | Skill 名称对齐 Agent Skills 完整规则；参数和附件改为引用普通消息限制，并补齐五类 Harness 的依据边界 |
| 3.0.2 | 2026-08-31 | 使用规则表和动作式短句简化命名、发现、快照与信任分层说明；不改变 Skill 行为 |
| 3.0.1 | 2026-08-31 | 面向读者统一使用“命令清单”，明确 Skill 命令发现不依赖磁盘扫描 |
| 3.0.0 | 2026-08-31 | 废弃旧的本地资源扩展和 Reload 交互设计，收敛为 HTTP `/skill:name`、最新 Agent 解析、调用快照、信任分层和可恢复执行 |
