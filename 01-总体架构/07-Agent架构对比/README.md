# CampusClaw 与 Agent 基线的架构对比

[返回总体架构](../README.md) · [模块索引](../../README.md#module-index)

| 属性 | 值 |
|---|---|
| 文档版本 | 1.103.0 |
| 更新日期 | 2026-10-16 |
| 文档职责 | 按模块解释架构取舍与实现差距，支撑设计讨论、架构答辩和面试 |
| 工具状态专项基线 | 2026-09-18 已 fetch Java 默认分支 main，核验 `8c5fda1dde51675859bc9c07e145dbe253656dea`；仅更新 A03/A05/A08 及 A07 提问展示子集，路径与符号见[§12](../06-CampusClaw计划模式/source-evidence.md#12-主线实现状态核验2026-09-18)，不升级外部基线或其他模块结论 |
| 退役工具专项基线 | A10 单独采用 Java `8c5fda1dde51675859bc9c07e145dbe253656dea` 与 pi main `e4ce7b449f4d91589c8760d6fbfa6eaaf82b05fe`；仅更新工具组合与删除边界，其他条目的历史证据不变 |
| 设计依据 | 当前各模块主设计；M02 采用 Model 主设计 2.11.0，具体入口见各条目 |
| CampusClaw 局部源码基线 | `pi-mono-java@f61906b9136246ca60f333704b6fc92b5420d0ec`；仅证明证据表所列文件与符号，不代表最新远端或全部模块 |
| 模型来源专项基线 | A06 于 2026-09-17 核验 pi 默认分支 `main` 的 `16235fd93521f9f96164f5891beea62e6bea5b18` 与 Java `main` 的 `21c3f59be033e7bdd5506a2d9d48baa2581bc3c7`；只升级模型配置、Provider 组合和业务 Agent 设置链结论 |
| 历史计划模式专项基线 | A03/A05 的提示词专项于 2026-09-17 更新至 Codex `b0659c53`、OpenCode `88c6c7ab`、DeepSeek `0d1f5000`、pi `e4c75a73`；业务覆盖再次确认四个上游 HEAD 不变，Java 装配/发布读取本地 `21c3f59b`，完整 SHA、路径及差距见[§11](../06-CampusClaw计划模式/source-evidence.md#11-业务-agent-模式提示词覆盖) |
| 计划参数预览专项基线 | A03/M01/M02：2026-10-09 确认默认分支并隔离 fetch pi main `f1b2e77f5b13b2a199b1052cb79c235451afe7d7`；Java 实现 `a1e6450427abeabaa1af04d5964f371dbbf4cf68`（PR #336）；完整路径、新旧差异和验证见[§16](../06-CampusClaw计划模式/source-evidence.md#plan-generic-json-evidence)。其他基线保留 §15 历史归属 |
| 前端专项基线 | A07：Java `1d08f98eb04f8ea6e01bcfbfd4008c1b638391c4` 的体验差距见[新核验](../../07-前端设计/source-evidence.md#experience-evidence)，前次验证见[实现证据](../../07-前端设计/source-evidence.md#current-implementation)；Codex 固定 `d58d0e58`，既有官方核对日期为 2026-09-15 |
| 历史提问专项基线 | A08：问答闭环验证为 Java 9f785bea3ffff8f6566cd1b2727285af46a2aead；新增交互核验为 Java 1d08f98e、Codex d58d0e58 与 OpenCode 849c2598，见[逐题交互证据 §9](../06-CampusClaw计划模式/source-evidence.md#9-buildplan-与逐题交互核验)；DeepSeek 0a53fb55、pi 5cd93f68、Claude 官方文档 2026-09-15 的原范围不变 |
| 工具发现专项基线 | A11：2026-09-22 fetch OpenCode `dev@fe3f3a41f79ad292cc3c7c629567385a20ec5130`、Codex `main@ac7634b9f73ec1bf96466be7a5869f0949d20b30`；沿用 DSH `master@c36a83ff6bb95e3f82cf79f9be7c724270a8aa61`。仅升级 Skill、固定搜索、延迟工具暴露与远端工具适配结论；默认分支快照不等于稳定发布，其他模块历史证据不变 |
| 参数恢复专项基线 | A11：2026-09-22 确认 pi `main@95fbc04997eaee961eb673fa7923e9220609ebd5`、DSH `master@c36a83ff6bb95e3f82cf79f9be7c724270a8aa61`；CampusClaw PR #323 开发提交从 `c9a2340f87bda6dff6bbd352f6995f8551206bb5` 更新到 `ae6645caaade3b9520220a34af940210850ef36a`，只升级确认前准备、模型恢复反馈和 SearchTools 差距，见[M03 专项证据](../02-CampusClaw工具系统/source-evidence.md#search-tools-evidence) |
| Command 状态专项基线 | M05：用户指定 Java `53eff85c7f41de23eb434e027782f5085a8b8e45`；只复核 Runtime 命令、严格名称、展开文本恢复与 Slash 交互，见[当前实现](../04-CampusClaw命令系统/README.md#current-runtime-status)；不升级外部基线或统计结论 |
| 统一历史专项基线 | A09/A15：2026-10-10 核验四仓最新默认分支，完整 SHA 与范围见[统一证据](../01-CampusClaw多Agent运行时/unified-event-persistence-evidence.md)；只升级三入口历史与计数投影，不升级其他专题历史结论 |
| Skill 统计历史基线 | A09：2026-10-10 核验 #335 `dad4433d38fcb4104bd8d093f844ea2afc9612ee` 的工具、三入口、采集及事务；隔离 fetch pi `main@42a3497d03ad17e308a2299fa824727894f2c0ec` 只更新 Start/End、后置 hook 与订阅结论，Codex/OpenCode 保留历史研究 |
| 决定消费终态专项基线 | A03/M06：Java `74f1b8314c9a5eb3d1659dfed2ab90b787dd647f` 的共享枚举、三类领取 SQL、markTerminal 与安装 DDL；仅新增内部 CANCELED 目标，不升级其他条目或外部基线结论 |
| 线性历史专项基线 | A12：pi main `1a584a7a56eb5e7b4ff8ccbd46430f1533282eed`，2026-09-22 已确认默认分支并隔离 fetch；Java 本地 `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12`；只升级分支索引与 Session 历史读取结论 |
| Redis 观察专项基线 | A13：2026-09-22 确认并隔离 fetch OpenCode dev `fe3f3a41f79ad292cc3c7c629567385a20ec5130`，仅事件协议、live/durable 定义与实例监听；Java 本地 `53eff85c7f41de23eb434e027782f5085a8b8e45` 的投影/流/控制/终态/依赖范围；新能力待实现，v2 仍为 experimental |
| 调度专项基线 | A14 完整职责表保留2026-09-22开源证据及2026-09-29 Claude/Java范围；首次时间与周期推进于2026-09-30单独核验 DSH master `639ed015397290b3745d163aafe02ffee4aa3f84`、pi main `1b347794e2a630e4359f2584f4eea388145d0ddf`、OpenCode dev `2fa3363c924c5c3e367b84a87ae478296a0ed59b`、Codex main `bcd6d9ab6b9f26f85d76d0c680b3f88b367bffa0`，并重读 Claude/OpenAI 官方调度文档；旧新提交、路径及证据边界见[M10 首次触发专项](../08-CampusClaw定时任务/source-evidence.md#first-fire-evidence)，不批量升级其余模块结论 |
| 核验范围 | A07 的模式入口、TUI 实施选择、方案/任务/问题分离、Slash 协同与前端接入范围；M01 的 Loop/控制消息扩展点、M06 的 Controller/分派/回执/流缓冲与配置更新源码；A04 的五基线接口边界；Claude 公共 Session/Agent/流与历史文档；A03 的计划文件/正文载体；A05 的三基线显式任务事件、Java 多事件事务与客户端消费接入点；A03/A05 的计划与实施提示词；A06 的 M02 Provider 身份、业务 Agent 设置唯一模型来源及旧全局目录差距；M08 的 Agent 默认 mode、目录快照、Session 初始化与元数据组合查询顺序 |
| 验证边界 | A08 已补充固定开发分支的 Runtime/数据库/前端确定性验证；其余条目保留各自静态核验范围，企业接入与真实模型行为不在已验证范围 |

Claw Session、完整事件与定时任务的[统一秒级目标](../01-CampusClaw多Agent运行时/time-contract.md)属于产品约束，尚待实现；Claude 2026-10-02 的公开示例为整秒，但不构成其内部精度保证。其他基线的历史证据保持原归属。

Claw 各模块的数据库结构集中于[全库设计](../../03-数据与存储/Claw数据库设计.md)，包含 main、PR 与待实现增量的独立状态及模块映射。此组织调整不改变外部 Agent 比较结论，也不升级其历史源码。

## 1. 阅读方式与权威边界

先从模块问题理解 CampusClaw 的职责，再比较同层基线，最后看实现状态和验证边界。
各模块主设计维护当前方案、主图、精确契约入口和验收；本文维护比较结论及其出处。
正文中的“目标”不等于已经上线，代码存在也不等于通过集成验收。

比较必须区分 Provider 增量、Agent 内部事件、服务 API、客户端预览和持久化记录。
不同系统都使用 SSE，不能证明它们具有相同的事件范围、恢复或取消语义。
完整模块归属与主设计只在[模块索引](../../README.md#module-index)登记；这里维护比较问题与覆盖状态。

## 2. 基线登记与证据范围

基线选择与每次更新规则来自 [Agent Runtime 参考基线](../../AGENTS.md#agent-runtime-参考基线)。下表是各专题的历史核验登记；A03/A05 的提示词证据、A06 的模型来源证据与 A11 的工具发现证据分别按各自专项升级，不能将其余条目一并标为最新。
下表登记的 commit 不是全量核验声明。使用其他 commit 时，条目必须同时记录旧值、新值和受影响结论。

| 基线 | 固定参考点 | 用于哪些问题 | 本文证据状态 |
|---|---|---|---|
| pi | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` | Runtime 内核、消息/Tool 生命周期、Session 分支与压缩 | A01 已核对 Loop 和 Agent 类型，A04 已核对配置 RPC，A05 核对 todo 示例的工具结果恢复；A06 的模型配置和 Provider 组合已专项升级到 `16235fd9`；A12 单独核验最新 SQLite 分支索引，完整协议快照仍待专项核验 |
| Claude Managed Agents | 公共 Session 文档核对日期 `2026-09-14`；A14 调度文档单独更新至 `2026-09-29`；无服务端源码 commit | 公共 Session API、preview、历史对账与平台调度 | A02/A04/A05 保留公开流、List Events、Session 更新、配置限制和通用 custom tool 交互的原核验范围；A14 对照 Scheduled deployments。仍为 Beta，只证明公开契约 |
| Codex harness | `d58d0e5841e0de08e251673db2d5af8cf3a1ad51` | Provider typed event、Turn/Item 客户端生命周期 | A04 已核对配置协议，A05 核对指定模型的 update_plan 指令及 Handler；A07 核对 TUI 方案实施与 plan Item/TODO 分离；A09 核对 Skill 触发/身份/两级去重/指标/上报；Provider 与其余 M07 生命周期仍待专项核验 |
| OpenCode | `849c2598abc7d2b40261e74b5826bc74ffc78308` | 多客户端、live/durable 分类与 sequence 回放 | A04 已核对 Session 配置/消息/v2 操作，A05 核对 todowrite 描述与模型提示词；事件流仍待专项核验；v2 源码能力不能自动视为稳定公开契约 |
| DeepSeek Harness | `0a53fb55bea101816fa226bb964ae2bed71c343b`，`dsh-0.1.2-alpha.2` | 计划模式；完整事件溯源与 token 级回放的成本上限 | A03/A04/A05 已核对计划插件、preset、Session 配置接口和 todo_write 完整列表；完整日志仍待 M04/M06 专项核验；保留 alpha 成熟度边界 |

没有同层、同范围证据时填“未核验”或说明“不适用”的理由，不以功能勾选或总分给系统排名。
公司认证、租户隔离、凭据传递、审计和数据保留是 CampusClaw 产品约束，不能因为基线没有相同名词就删除。

## 3. 按模块维护的对比问题

| 模块 | 需要解释的架构问题 | 主基线及辅助对照 | 条目与待补证范围 |
|---|---|---|---|
| M01 · Runtime 与多 Agent | Loop 扩展能力如何与产品准入分离；父子执行如何隔离和终止 | pi；计划审核采用 DeepSeek，预览对照 Codex | [A01](#a01)覆盖 Loop 与消息准入；[A03](#a03)覆盖模式接入、参数承载计划预览与审核、Subagent 模式传递，其他父子生命周期待补证 |
| M02 · Model | 如何让业务 Agent 设置成为唯一模型权威；Provider 调用与模型选择如何分层；原始事件在哪层归一化 | 模型目录差异采用 pi；事件归一化专项采用 Codex | [A06](#a06)覆盖 CampusMate 身份、业务 Agent 设置、旧全局目录删除和 SDK 削减；Codex 事件归一化对比及完整取消链仍待专项核验 |
| M03 · Tool 与受管环境 | 工具发现、参数校验、权限、执行和副作用重试分别由谁负责 | pi；其他基线按具体执行问题选择 | [A03](#a03)覆盖稳定工具定义与计划 Prompt；[A05](#a05)覆盖 TODO 工具及事件边界；[A08](#a08)覆盖结构化提问；[A10](#a10)覆盖通用命令与写工具删除边界；[A11](#a11)覆盖远端代理与 Skill 工具按需披露 |
| M04 · 上下文与持久化 | 模型上下文、历史、分支与压缩如何区分；哪些事件值得保存 | pi；DeepSeek 辅助 | [A03](#a03)覆盖模式/审核恢复；[A12](#a12)覆盖单条时间线与非递归读取，其他上下文比较待补证，不默认 token 全量落盘 |
| M05 · Command 与 Skill | 清单、资源发现、执行与使用统计分别维护什么权威状态 | pi；发现参照 OpenCode/DSH，统计接入参照 pi 事件，Codex/OpenCode 保留历史研究 | [A09](#a09)覆盖 Skill 成功调用次数、公共观察、有界写入与 #335 差距；[A11](#a11)覆盖 Skill 加载与具体工具定义披露；[当前 Command 状态](../04-CampusClaw命令系统/README.md#current-runtime-status)区分 Runtime 已实现与版本快照、统计、Mate 增量 |
| M06 · 事件与服务边界 | 写入与观察是否分离；流绑定谁；断线如何恢复；控制状态谁权威 | Claude；OpenCode，必要时 pi/DeepSeek | [A02](#a02)覆盖既有 Claw/Mate 流范围；[A13](#a13)覆盖 Redis 快照与短期增量恢复；[A03](#a03)维护数据库确认交接；[A04](#a04)覆盖 Session 配置更新；[A05](#a05)覆盖后端显式任务事件；[A16](#a16)覆盖按 Agent 跨会话查询用户事件与按事件读取轮次 |
| M07 · 前端体验 | preview 何时被权威内容替换；Turn/Item 与产品 UI 如何映射 | Codex；Claude 辅助 | [A05](#a05)保留旧提交的事件合并与根执行证据；当前计划/TODO/问答前端实现见[A07](#a07)及[A08](#a08)，公共 Mate 接入仍为目标设计 |
| M08 · 元数据与配置 | 定义、发布快照和运行对象如何分离；刷新如何影响活动执行 | pi；托管产品仅对照公开资源 | Agent.mode 专项已核对 Mate 956b547f / Runtime 09b32d8e；默认值链为 待实现，见 A03 和元数据主设计；元数据组合查询顺序另在 Mate `9dd5d85e` 核对，见 J06；发布事务一致性仍待补证 |
| M09 · 附件与文件 | 文件服务与 Agent 工作区是什么关系；何时解析与授权 | pi；托管产品公开文件契约按需核对 | 待补证；明确企业产品约束 |
| M10 · 调度与并发 | 定时触发如何受理为独立执行，如何区分调度结果与根执行结果，暂停、失联和重复触发如何处理 | Claude Managed Agents 为调度主基线；其他四基线保留分层历史对照 | [定时任务主设计](../08-CampusClaw定时任务/README.md)仅支持 cron，名称上限 256；接口配置的任务每次运行新建 Session，复用同一 Agent 定义，对话中由 Cron 工具创建的任务在原会话追加一轮；[A14](#a14)维护取舍，Java 已核验范围与待实现增量见[M10 证据](../08-CampusClaw定时任务/source-evidence.md) |
| M11 · 可观测性与测试 | 日志、审计历史与模型上下文如何分开；如何证明差异可接受 | 按验证对象选基线，不设统一主基线 | 待补证；区分测试存在、测试运行和生产观测 |

M05 的 53eff85c 专项只更新 CampusClaw 实现状态：Builtin、Runtime Skill 执行、严格名称、
展开文本恢复与前端 Slash 已存在；统一 Skill 扩展结构、完整版本快照和统计仍待实现，Mate 公共接入独立确认。
这不改变原有产品约束、安全加固或架构取舍；实现映射与测试未重跑边界由主设计维护。
外部基线历史 SHA 与比较结论保持原核验范围，不把进度校正描述为新的上游比较。
M05/M07 的[参数控件与附件边界](../../07-前端设计/技术设计/命令/README.md#command-input-controls)的分层：Runtime 提供命令清单与按会话的可选值（模型、深度思考、工作模式），Mate 为清单补 argumentType 并通过命令选项接口返回 currentValue 与 value/label 候选（模型名称取自 Mate 模型管理），前端按 argumentType 统一组装命令参数，不按命令名写取数逻辑。占位提示与可选值分开，与 pi 的 argumentHint 加按会话补全一致。此项为接口架构变更，不改变全局类图结构。

M05 描述符专项于 2026-09-22 重新确认默认分支并 fetch pi `main@d201760ffee16564aa8d9a759e0c85b70db33674`
与 OpenCode `dev@fe3f3a41f79ad292cc3c7c629567385a20ec5130`，只更新命令发现和请求边界；默认分支快照不等于稳定发布。
pi 的 RpcSlashCommand 与 OpenCode 的 Command.Info 均将发现描述和实际调用分开，后者 hints 仅为占位提示。
CampusClaw 采用 name/type/description 与可选 argumentHint：与 pi 的 argumentHint 和 OpenCode 的 hints 一样只是占位提示，可选值由 Runtime 按会话单独查询（对应 pi 的 get_available_thinking_levels）；按类别统一附件，按会话状态限制修改。
收益是固定选项由接口给出且文案留在界面层，代价是前端需集中维护并验证命令状态规则，POST 始终最终准入。
Java 53eff85c 的 VO/组装器及前端仍用 kind/input，新投影与客户端迁移待实现；未运行产品测试。
相对路径、符号、旧新提交范围及差异理由见[专项证据](../04-CampusClaw命令系统/source-evidence.md#command-descriptor-baseline)，其余比较不升级。

M05 清单作用域于 2026-10-16 核对 OpenCode `dev@e25b7abf`（按工作目录查询，实验接口）、Codex `main@6b991972`（`skills/list` 按 cwds 查询）与 pi `main@4954d760`（每个会话进程 `get_commands`）。
CampusClaw 的命令清单改为按 Agent 查询 `GET /agents/{agentId}/commands`，sessionId 为可选查询参数（待评审 · 待实现），不按会话状态过滤；这是接口架构变更：不带 sessionId 只返回 help、skills 与技能命令，供尚无会话的新对话使用，带 sessionId 返回完整命令；代价是运行中的禁用改由前端状态规则表展示、POST 终判。
证据见 [Agent 清单作用域核对](../04-CampusClaw命令系统/source-evidence.md#agent-catalog-evidence)。

待补证项是持续维护范围，不能用于讲述已经实现的能力。涉及该模块的新设计应补齐受影响的问题，
不要求一次设计把所有基线全部重做，也不能用“待补证”略过本次实际改变的架构结论。

<a id="a01"></a>

M05/M07 模式命令增量：pi 于 2026-09-22 从前次 `d201760ffee16564aa8d9a759e0c85b70db33674` 更新至默认 main `d192bd6dcae78fb87cf5c1c5e2af2790a0296278`，Builtin 列表含 model/thinking 而不含 mode；OpenCode dev 仍为 `fe3f3a41f79ad292cc3c7c629567385a20ec5130`，plan/build 是不同 primary Agent。CampusClaw 通过 `/mode` 切换同一 Session 的模式，复用既有配置事务并禁止在运行/审核等待时切换，不引入双 Agent 权限模型。属于产品入口扩展和共享规则的架构变更；Java `53eff85c` 已有 Session 模式更新，mode 命令和前端适配待实现。收益是保留上下文与权威状态，代价是新增命令映射、选择控件和一致性验收；完整路径、符号与源码成熟度见[模式专项证据](../04-CampusClaw命令系统/source-evidence.md#mode-command-evidence)。

## 4. A01 · Loop 的扩展能力与产品消息准入分离

| 维度 | 结论 |
|---|---|
| 所属模块与主设计 | M01/M06；[Runtime 总体设计 §1、§3.2](../01-CampusClaw多Agent运行时/README.md)、[请求级 SSE §1、§4](../01-CampusClaw多Agent运行时/chat-events-stream-design.md) |
| 同一架构问题 | 内核能够接收运行中控制消息，是否意味着 HTTP 必须开放排队与 Steer/FollowUp？ |
| pi 已观察行为 | `runLoop` 通过 `getSteeringMessages` 在下一次模型调用前加入控制消息，并在原本将结束时读取 `getFollowUpMessages`；`AgentEvent` 区分 Agent、Turn、Message 与 Tool 生命周期。[P01、P02](#source-evidence) |
| CampusClaw 目标 | 内核与产品入口分层；当前 Session 消息 M1 未完成前拒绝 M2，不隐式排队。停止经 `user.interrupt`，实际停止后才能新提交，FollowUp 不在本期产品能力内。 |
| CampusClaw 已观察实现 | `AgentLoop` 保留 steering/follow-up 队列与 supplier；模型增量转换成 `MessageStart/Update/EndEvent`，工具阶段交给 `ToolExecutionPipeline`。HTTP 消息服务先检查 Session idle，再调用持久化接受服务，并在回执入队后启动执行。[J01、J04](#source-evidence) |
| 关键差异 | pi 的内核扩展点是行为参考；CampusClaw 的产品接口选择更窄的运行中消息准入。Java 保留内核队列接口不能证明 HTTP 支持排队，两者不矛盾。 |
| 差异分类 | 产品约束：本期单消息、不排队；架构变更：将 HTTP 准入、持久化接受和内核循环分层。不是宣称 Java 与固定 pi 所有 Loop 细节完全一致。 |
| 具体理由 | 固定当前输入与执行归属，避免用户误以为运行中提交已被接受；控制事件按自己的状态条件处理，不能都当作下一条普通消息。 |
| 收益与代价 | 产品交互与执行归属更明确；用户不能直接排队追加，调用方要处理 busy、等待确认和停止收敛。对时延、吞吐的影响没有实测结论。 |
| 重新评估条件 | 产品明确需要运行中排队或转向时，先设计接受回执、顺序、取消、持久化和跨实例交接，再决定如何使用内核扩展点；不能直接把现有队列暴露成公共能力。 |
| 设计状态 / 实现状态 | 已有目标设计 / 局部源码已核验；未核验数据库接受事务、多实例并发以及队列配置是否在全部入口禁用，不能标记端到端完成。 |
| 验收重点 | 两实例同时提交同 Session 只能接受一条；确认等待不释放普通消息准入；停止真实结束后才接受下一条；内核、HTTP 和持久化测试分别证明各自边界。具体规则仍由主设计维护。 |

**讲解要点。** CampusClaw 参考 pi 的 Agent/Turn/Message/Tool 分层，把模型调用和工具循环放在内核。
产品入口则限制为一个 Session 一次处理一条用户消息。保留内核的 Steer/FollowUp 扩展点不等于对用户开放消息队列。
这个取舍让执行归属更明确，代价是不能运行中排队；目前核对到了 Loop 与 HTTP 接受编排，分布式准入仍需事务和并发验证。

<a id="a02"></a>

## 5. A02 · 同为 SSE，连接范围与恢复边界不同

所属模块为 M06，并关联 M07。主设计为 [Claw 请求级 SSE](../01-CampusClaw多Agent运行时/chat-events-stream-design.md)
和 [Mate 通用对话 API](../../02-服务与接口/07-mate-service通用对话API/README.md)。
它们各自维护内部与公共契约，不能相互覆盖。

本节保留既有精确契约的比较；新的浏览器草稿恢复推荐目标由 [A13](#a13)补充。新增独立读取与快照首帧仍为 proposed，不能把下表“重开流并查历史”当作已具备未完成正文恢复。

| 比较维度 | Claude Managed Agents 公开契约 | CampusClaw 内部目标 | Mate 公共 Chat 目标 |
|---|---|---|---|
| 提交与观察 | 发送事件、读取流与历史分离 | 同一 POST 接受事件并返回对应 SSE；另有 GET 历史 | POST 返回完整用户事件 JSON；独立 GET Chat live SSE；另有 GET 历史 |
| 连接绑定 | 提供 Session 及 Thread 的读取流 | 绑定本次请求对应的执行段或控制结果；对应 idle 后关闭，含 confirming | Chat 级连接可跨执行与空闲；idle 不关闭连接 |
| 增量与权威 | preview 临时且不重放，完整消息用于对账 | delta 作预览，完整事件用于历史对账 | 同 ID completed 替换 preview，完整公共历史用于对账 |
| 断线恢复 | 重开流并查询历史 | 查询历史；不恢复已经断开的 POST，不自动重发已接受写入 | 重开公共流并查询历史，不自动重发 POST |
| 证据性质 | 2026-09-14 核对的 Beta 文档；不证明服务端内部实现 | 主设计目标；J02/J03/J04/J05 仅证明下述局部实现 | Mate 公共目标契约；数字分页与快照仍待整合；未核对 mate-service 源码 |

Claude 的比较依据为官方 [Session event stream](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)
与 [List Events](https://platform.claude.com/docs/en/api/beta/sessions/events/list)。这里只采纳流与权威记录的公开边界，
不推断内部调度、数据库或游标算法。三者的完整事件字段与分页规则不因上表的相似点而相同。

**已观察的 CampusClaw 实现。** J02 的 `RuntimeEventController.submit/list` 已分别提供 POST SSE 和 GET 历史入口；
J03 的 `RuntimeEventService.submit` 已分派 message、interrupt、tool confirmation 三类 VO。
J04 的 `accept/startAccepted` 检查回执容量、调用持久化接受服务，再将回执入队并启动执行。
J05 的 `RuntimeEventStream` 限制单 subscriber，按事件数和字节数限缓冲，区分必需事件与 best-effort 事件，
`detachInternal` 清空该流的缓冲并调用清理动作。这些源码证明了局部结构，不能单凭它们证明
完整终态持久化、取消传播、每个事件的丢弃策略或全部恢复链已经通过验收。

**差异分类与理由。** Claw 采用请求对应的 SSE 属于架构变更：调用方随请求消费这一段输出，
等待工具确认后以新的确认请求继续下一段，连接不跨后续无关执行。
Mate 的 Chat 身份、授权和公共投影属于产品约束及安全边界；它需要把内部执行交互转换成浏览器使用的公共流。
参考 Claude 的 preview/权威历史分离，不要求照搬它的全部连接模型。

**收益与代价。** Claw 的请求和输出归属清晰，但客户端必须支持 POST 流式读取，
断线后需要历史对账。Mate 的公共流与内部请求流生命周期不同，需要显式桥接和授权投影；
不能字节透明转发，也不能假定内部连接结束就应关闭公共 Chat 流。桥接的多客户端分发、恢复、
背压和确认续跑仍需独立设计与实际 mate-service 源码证据，本文不补造其内部实现。

**重新评估条件。** 如果内部调用方需要脱离写请求独立订阅、多客户端共同观察或可恢复读流，
应重新评估连接范围、权威事件来源和恢复契约；这会改变架构边界，不能仅增加一个 GET 路径就视为完成。

**实现状态与验收。** 两份目标各自有效；Claw 为局部源码已核验，Mate 保持 待实现。
应分别验证回执先行、确认分段、中断结果绑定、慢连接、无首帧结果不确定和断线历史对账；
再验证公共流跨内部执行段持续存在，以及公共身份与权限投影。验收通过前不能宣称“两跳已全部实现”。

**讲解要点。** SSE 只规定流式响应格式。CampusClaw 内部把连接绑定到本次请求的执行段，
Mate 公共层把连接绑定到 Chat；Claude 是公开流与历史对账的参考。
我们采纳临时 preview 与权威记录的区分，同时保留自己的产品边界。
代价是两跳需要明确的事件桥接；内部入口代码已经存在，公共桥接还不能用设计文档冒充实现证据。

**企业凭据专项（2026-09-19，M03/M06）。** Claw 只捕获和透传四项可选 Header，空或部分快照不触发工具 unavailable，实际 execute 的凭据判断归 Mate；[HTTP §7](../01-CampusClaw多Agent运行时/chat-http-v1-design.md#credential-forwarding)维护精确边界，[M03 §9.2](../02-CampusClaw工具系统/README.md#mate-credential-forwarding)维护工具条件。此为 CampusClaw 产品约束及职责调整，不由外部 Agent 的认证机制推导，也不改变本节 SSE 比较。收益是避免在 Claw 重复维护 Mate 凭据规则，代价是缺失凭据到工具实际调用时才反馈；固定 Java `21c3f59b` 三处本地检查仍待移除，路径与符号见[专项证据](../01-CampusClaw多Agent运行时/source-evidence.md#credential-forwarding-evidence)。不新增外部基线结论、不升级历史 SHA；Mate 联调与空/部分 Header 出站验收待实现测试证明。

<a id="a03"></a>

## 6. A03 · Agent 默认模式、Session 当前模式与计划审核

| 维度 | 结论 |
|---|---|
| 所属模块与主设计 | M01/M03/M04/M06/M08，关联 M07；[计划模式主设计](../06-CampusClaw计划模式/README.md)集中维护目标结构、接口增量、恢复及验收，复用其中唯一全局类图 |
| 架构问题 | 如何让 Agent 提供默认工作模式、Session 独立维护当前模式，同时保持 Tool/Skill 元数据稳定并支持方案审核？ |
| DeepSeek 已观察行为 | 最新核验 `4878cdab` 的 PlanModeController 保持稳定退出工具，required plan 直接承载完整 Markdown，审核 detail 使用 args.plan；批准后在下一 accepted in-turn pre-step 提交模式变化。当前 package 为 `0.2.0-rc.1`，不是稳定发布；不据此声称其提供 CampusClaw 参数预览。完整提交、路径与旧 alpha 范围见[专项证据 §15](../06-CampusClaw计划模式/source-evidence.md#plan-argument-streaming-evidence)。 |
| CampusClaw 已观察实现 | `a1e6450427abeabaa1af04d5964f371dbbf4cf68`（PR #336）已接入完整 plan 参数、AI 通用部分 JSON 快照、及时工具身份和内部最终诊断；Runtime 只投影可信计划前缀，完整调用经校验/prepare 后绑定审核事务。批准后原执行应用 build，再继续模型与工具循环；精确范围见 §16，其他历史核验不升级 |
| CampusClaw 目标 | Agent 默认 mode 只初始化新 Session，Session 独立维护当前模式；模式更新复用统一 Session POST。完整方案一次写入 ExitPlanMode({plan})，后端从可信调用的参数生成计划预览；完整校验后以事件身份审核，沿用原执行与数据库确认交接，批准后以 build 指令续跑；Tool/Skill 定义跨模式稳定。精确规则归计划与元数据主设计。 |
| 差异分类 | 产品约束：Agent 默认 mode 与 Session 当前模式分离、Tool/Skill 元数据稳定、当前模式由 Session 更新、只允许 idle 主动切换、Subagent 调用时继承模式；架构变更：在既有配置服务增加 Session 更新，并将进程内审核接入 HTTP 和已有数据库执行控制；安全加固：精确目标、单次消费、停止竞争和两跳身份校验。 |
| 提示词依据 | DeepSeek standard preset 明确禁止规划期 todo_write；CampusClaw 同样仅在 build 记录实施进度。模式资源仅 PLAN.md / BUILD.md；Main Agent/Subagent 用一行角色区分 PLAN 内规则的适用范围，批准后重组为短 BUILD。通用执行、验证和交付归基础 SYSTEM，进度细则归工具描述；不能以其他 Agent 的模式文件短推断其总规则少。精确正文、BASE 发布前提和矩阵见[提示词设计](../06-CampusClaw计划模式/plan-policy.md)，最新源码及代价见[专项证据 §10](../06-CampusClaw计划模式/source-evidence.md#10-两份模式提示词的最新上游核验)。 |
| 业务模式覆盖 | pi 有 SYSTEM 文件优先级，DeepSeek 有部署提供的 plan:policy，Codex 有模式目录/调用文本覆盖；OpenCode agent.prompt 覆盖基础模板但模式提醒仍独立。CampusClaw 按业务 `.campusclaw/PLAN.md`、`BUILD.md` 分别完整替换，缺失回退预制；执行固定快照、Subagent 读自身目录、refresh 保留可选文件。属于架构扩展；代价是目录发布一致性和自定义正文评估，详见[覆盖证据](../06-CampusClaw计划模式/source-evidence.md#11-业务-agent-模式提示词覆盖)。 |
| 具体理由 | 模式已有明确的 Session 资源归属，更新操作复用其身份、版本与事务，统一四类属性入口，并明确组合原子性。混合查询与变更工具不能依靠新增一个静态只读字段准确表达每次调用用途；稳定字段与工具定义让规划规则独立演进。公共审核需要可对账的事件身份，原有工具权限不能表示对整份方案的批准。展示恢复与锁内接受分离，沿用既有工具确认方式，避免 Session 响应随具体交互增加指针。 |
| 默认值证据与代价 | Mate 956b547f 的 Agent DTO/VO/DefinitionColumns 无 mode；Runtime 09b32d8e 的 prepare 复用目录、refresh 强制发布、create 从解析快照初始化，均无 mode。目标增加字段传播与创建复制，修改 Agent 后须先完成目录发布，不能宣称新 Session 即时读取远端最新值；既有 Session 不被重置。这是产品配置扩展，不是 DeepSeek/Claude 同名字段。完整路径及符号见[专项证据](../../03-数据与存储/02-Agent元数据GaussDB/README.md#23-mode-专项源码核对)。 |
| 收益与代价 | 不扩充工具元数据、不增加第二套 Loop 或 Session 待审字段；需要新增模式和审核事件、确认记录及客户端卡片。刷新必须补齐相关事件，缺页或状态矛盾时禁用审核；跨请求读取仍可能过期，确认始终在服务端重新校验。提示词约束不提供服务端强制只读保证；进程失联自动接管不在该功能承诺中。 |
| 备选与重新评估条件 | 本期不采用副作用白名单、独立 Plan CRUD、Cordis 插件容器或 token 全量日志。若产品要求规划期绝不产生副作用，应单独设计可执行的权限边界，不能将 Prompt 遵循率当作保证。 |
| 设计 / 实现状态 | 参数流式及通用解析在 PR #336 已实现、未合入 main；确定性回归见 §16。两文件覆盖等其他能力仍保留各自历史证据；BASE 业务发布、企业桥接与真实模型验收不因本次测试而完成 |
| 验收重点 | 见[主设计 §8](../06-CampusClaw计划模式/README.md#8-实施切片与验收)：模式与消息接受竞争、工具定义稳定、eventId 精确审核、跨实例单次领取、中断与恢复、Subagent 模式及提示词场景评估。 |

**计划长度（2026-10-09，M02/M03/M06）。** pi main `f1b2e77f5b13b2a199b1052cb79c235451afe7d7` 的 AI 参数解析不设通用字符上限；DeepSeek master `5badb15009ae1756c3afe0ae0cef1faafc290ccc` 的 ExitPlanMode 参数定义和执行检查也不设正文最大长度（plan-mode 0.2.1-alpha.1，非稳定发布）。CampusClaw 取消计划专属 maxLength、UTF-16 数量校验、预览长度门禁与历史读取门禁，保留必填、类型、标题、完整 Unicode、来源绑定和审核事务。这样长巡检方案不会因无基线依据的固定字符数而失败；通用预览预算和编码帧容量仍是独立资源约束，并非承诺无限输入。最新实现与旧新基线的限定升级范围见[证据 §17](../06-CampusClaw计划模式/source-evidence.md#plan-length-baseline)。

**通用参数解析与计划专用预览（2026-10-09，M01/M02/M03/M06/M07）。**

| 维度 | 结论 |
|---|---|
| 最新来源 | 本次只升级 pi AI/Loop 的相关源码快照 `f1b2e77f…`；DeepSeek/Codex 的计划载体比较保留 §15 历史归属。新旧完整提交、路径与符号见[证据 §16](../06-CampusClaw计划模式/source-evidence.md#plan-generic-json-evidence) |
| 基线行为 | pi 在 AI 层累积工具 JSON，通过通用 `parseStreamingJson` 生成部分对象，支持嵌套结构并修复部分非法输入；完成时也使用该容错函数，partial 为可变对象。它提供内部参数预览参考，不提供 CampusClaw 的公共计划卡与企业审核事务 |
| 已观察 Java | Mate 每调用使用 StreamingJsonParser，发布及时身份和深度只读 partial；结束时独立按既有规则解析完整原始参数，并发出不序列化的 ToolArgumentJsonStatus。Runtime 的 PlanArgumentPreview 只投影可信 plan 前缀，不缓存或重解析 raw arguments |
| 目标与差异 | AI 通用 JSON 属于架构调整，避免 Runtime 再维护业务专用 JSON 词法器；Java 继续使用不可变事件快照和独立完整解析，不采用修复结果执行。只公开计划正文属于产品约束；INVALID 原始诊断阻止计划审核属于安全加固，不全局改变普通工具的接受行为 |
| 可信性与失败 | 可信目标解析与完整参数校验/prepare 在 Host 交互之前，同次快照用于确认和执行。计划绑定检查来源、唯一调用与原始诊断；审核事务后才 completed。预览预算/语法失败只停预览；最终非法或截断 JSON 仍失败，不猜参、不自动重放。普通业务仍按可信解析→校验→权限/确认→执行→结果回传推进 |
| 收益与代价 | 通用能力归 AI，计划层仅表达业务投影，普通工具最终行为保持；代价是状态机维护、深快照复制及一次完整诊断扫描。每调用预览预算不等于全响应内存上限，不宣称端到端线性或已改善首字时延。复用 JDK/Jackson，无新增依赖 |
| 状态与验收 | 实现位于 PR #336，未合入 main；[Model 主设计](../../02-服务与接口/03-Model/README.md#streaming-json)维护通用机制，[计划专题](../06-CampusClaw计划模式/plan-streaming.md)维护投影与审核。单元/组件、真实 JAR/openGauss 与前端证据分别记录，企业 Mate、真实模型和生产 GaussDB 仍未验收 |

**决定消费终态专项。** M06 的数据库交接新增[统一 CANCELED 状态](../01-CampusClaw多Agent运行时/chat-events-design.md#46-已接受决定的消费终态)：工具确认、计划审核、问题答案只在根执行可靠终态事务中收尾未领取记录，保留用户已接受的事实。Java `74f1b831` 已有三类领取和停止条件，终态未更新决定行；新增状态在该基线为 待实现，具体源码路径与验收见主设计。这里改变的是 CampusClaw 持久化消费模型，属于架构变更；不声称 pi、DeepSeek 或托管服务有同名数据库状态。收益是记录本身可区分待领取与不再消费，代价是三表约束和终态事务增加更新；不增加公共事件、依赖或独立清扫任务。既有 Agent Loop 与工具结果参考结论不变，旧 A03 模式实现核对点也不代表当前模块整体尚未实现。

**讲解要点。** DeepSeek 提供了计划模式与工具元数据解耦的参考。CampusClaw 保留这一边界，
以统一 Session POST 更新承载工作模式，把计划审核接入已有 Session Events 和数据库确认续跑。方案一次放入退出工具参数，后端逐步展示已识别的计划字符串，完整校验后才形成审核候选；工具授权继续独立执行。
新的代价集中在参数增量解码、可信身份和最终快照一致性；审核持久化已存在，提示词约束与失联执行恢复仍有各自边界。


计划载体并非统一为文件：OpenCode、Claude Code 使用计划文件，已核验 DeepSeek/Codex/pi 路径可直接承载正文或 Session Entry；Managed Agents 公开文档另建议分两次 Session 编排。CampusClaw 完整方案持久化与取舍见[主设计 §1.3](../06-CampusClaw计划模式/README.md#13-完整方案保存在哪里)，固定路径与边界见[证据 §8](../06-CampusClaw计划模式/source-evidence.md#8-计划文件与方案载体)。

<a id="a04"></a>

## 6.1 A04 · Session 属性统一更新，业务准入按字段区分

| 维度 | 结论 |
|---|---|
| 所属模块与主设计 | M06/M02，关联 M01/M07；[HTTP 主设计 §2.4](../01-CampusClaw多Agent运行时/chat-http-v1-design.md#24-模型目录与统一-session-更新)维护契约理由、唯一目标类图与组合事务验收 |
| 架构问题 | 名称、模型、思考和工作模式同属 Session 时，如何通过一个入口更新且保留不同的生效约束？ |
| CampusClaw 目标 | 统一 Session POST；字段可选、支持单字段或组合修改，一笔事务、一个内部资源版本。当前前端每次操作仅提交对应一个字段。名称单独修改允许 running，执行配置要求 idle；元数据字段保持稳定。精确模型只由 Runtime catalog 维护。 |
| CampusClaw 已观察实现 | 2026-10-04 重新核验 Java main `553dcd5e2ff682f9684810a043b442b37a02e54a`：统一 POST、字段省略识别、锁内合并、状态检查与同值处理已存在；Controller/Service 仍要求 If-Match 并返回 ETag，前端仍保存及发送标签。取消客户端令牌及对应消费者迁移待实现；路径、符号与取回范围见[专项证据](../08-CampusClaw定时任务/source-evidence.md#schedule-header-free-contract)。 |
| 差异分类 | API 架构变更：合并写入入口及事务；产品约束：可变 Session 模型、boolean 思考、plan/build、名称 running 可改、执行配置 idle、稳定元数据；并发安全：锁内读取最新记录、复核状态并合并提交字段，不按页面快照整行覆盖。 |
| 具体理由 | 当前四个控件共享一种资源更新与对账流程；前端单项调用不构成服务端字段互斥的理由。接口接收字段组合时，按最终目标模型校验思考并整笔提交；不要求页面提供批量保存，也不新增通用属性更新框架。 |
| 收益与代价 | 调用方共享业务字段更新流程，无需保存标签或请求键；仍需处理字段组合、模型能力与整笔失败。接受同字段后一次成功提交生效，数据库行锁不检测旧页面编辑意图；不同字段基于最新值合并，模型与 thinking 仍遵守能力归一及完整校验。 |
| 备选边界 | 基线有独立命令不等于 HTTP 必须分拆；Claude 有 Session POST 也不等于其允许当前会话切换模型。若未来允许运行中改配置，应另定生效快照边界，不能从统一入口自动推导。 |
| 设计 / 实现状态 | 四类统一 POST 已实现；取消 HTTP 条件及配套 ETag 为已确认目标，服务端与消费者迁移待实现。静态核对未代替 Java/数据库/跨实例测试。 |
| 验收重点 | 单字段与组合请求；目标模型不支持显式 thinking=true 时全不变；省略 thinking 的自动归一；running 名称例外；同值不升版本；不同字段并发合并、同字段提交顺序、插入历史失败回滚；旧目标写入口不回流。 |

同层 API 组织的证据如下，不能按“多数基线如此”投票决定接口：

| 基线与实际核对点 | 已观察接口组织 | 采纳范围与边界 |
|---|---|---|
| Claude Managed Agents，官方 Beta 文档，2026-09-14 | [Update Session](https://platform.claude.com/docs/en/api/beta/sessions/update) 使用资源 POST；title/metadata/budget/agent 可选，公开契约未列出单字段互斥限制，主示例只提交 title；模型/effort 在可版本化 Agent 配置中，已有 Session 不能中途修改模型配置，见[Session operations](https://platform.claude.com/docs/en/managed-agents/session-operations) | 参考资源级部分更新及单字段主示例；字段集合、null 与原子性由 CampusClaw 定义，不迁入 Agent 版本快照与会话模型不可变约束；无服务端源码，不能推断其数据库事务 |
| DeepSeek Harness 0a53fb55bea101816fa226bb964ae2bed71c343b，alpha | [packages/api/session-controller/src/commands.ts](https://github.com/deepseek-ai/deepseek-harness/blob/0a53fb55bea101816fa226bb964ae2bed71c343b/packages/api/session-controller/src/commands.ts) 的 selectModel 合并模型与 reasoningEffort，rename 独立；[packages/plan/plan-mode/src/index.ts](https://github.com/deepseek-ai/deepseek-harness/blob/0a53fb55bea101816fa226bb964ae2bed71c343b/packages/plan/plan-mode/src/index.ts) 注册 plan 命令 | 借鉴模型与能力关联、计划机制；其 Remote RPC 及后续 step 切换时机不决定 CampusClaw HTTP 形状 |
| pi 5cd93f688aaab89dbb6dfa4aca535f21796ae185 | [packages/coding-agent/src/modes/rpc/rpc-types.ts](https://github.com/badlogic/pi-mono/blob/5cd93f688aaab89dbb6dfa4aca535f21796ae185/packages/coding-agent/src/modes/rpc/rpc-types.ts) 的 set_model/set_thinking_level/set_session_name 是独立 JSONL 命令；[core/agent-session.ts](https://github.com/badlogic/pi-mono/blob/5cd93f688aaab89dbb6dfa4aca535f21796ae185/packages/coding-agent/src/core/agent-session.ts) 的 setModel/setThinkingLevel 提供能力归一 | 参考 Runtime 行为；进程命令无 PUT/POST 含义，不能直接推出公共 API 需要属性专用端点 |
| Codex d58d0e5841e0de08e251673db2d5af8cf3a1ad51 | [codex-rs/app-server-protocol/src/protocol/v2/thread.rs](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/app-server-protocol/src/protocol/v2/thread.rs) 的 ThreadSettingsUpdateParams 合并后续 Turn 配置；[app-server/README.md](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/app-server/README.md) 区分 thread/name/set 与当前 Turn 的 settings/update | 参考合并配置与生效范围分离；两种 settings/update 为 experimental，不照搬 JSON-RPC 或运行中切换功能 |
| OpenCode 849c2598abc7d2b40261e74b5826bc74ffc78308 | [packages/opencode/src/server/routes/instance/httpapi/groups/session.ts](https://github.com/anomalyco/opencode/blob/849c2598abc7d2b40261e74b5826bc74ffc78308/packages/opencode/src/server/routes/instance/httpapi/groups/session.ts) 的 UpdatePayload 包含 title 等属性；[packages/opencode/src/session/prompt.ts](https://github.com/anomalyco/opencode/blob/849c2598abc7d2b40261e74b5826bc74ffc78308/packages/opencode/src/session/prompt.ts) 的 PromptInput 随消息选择 model/agent/variant；[packages/protocol/src/groups/session.ts](https://github.com/anomalyco/opencode/blob/849c2598abc7d2b40261e74b5826bc74ffc78308/packages/protocol/src/groups/session.ts) 的 switchModel/switchAgent 又提供独立 v2 操作 | v2 明确为 experimental，不能混成一套稳定公开契约；CampusClaw 使用独立于发送消息的 Session 更新 |

**讲解要点。** CampusClaw 将用户编辑会话属性的动作统一为一次资源更新，借鉴 Claude 的资源组织和其他基线的配置边界，同时保留自己的运行约束。难点在组合状态而非 HTTP 方法：目标模型决定思考是否有效，数据库行锁下的最新状态和完整业务校验决定整笔更新能否提交；名称更新不触碰执行快照。同字段并发修改依提交顺序生效，超时后只读核对不等于找回某次请求回执。统一更新骨架已存在，HTTP 令牌及前端标签依赖仍需迁移。

<a id="a05"></a>

## 6.2 A05 · 后端显式任务更新与恢复

| 维度 | 结论 |
|---|---|
| 所属模块与主设计 | M03/M06/M07，关联 M01/M04；[TodoUpdate](../06-CampusClaw计划模式/todo-update.md) 维护工具、提交与恢复，复用计划模式全局目标类图 |
| 架构问题 | 如何让前端直接获得执行清单，同时保持工具与 Session 元数据稳定、断线后恢复相同进度？ |
| Claude 公开契约 | 官方 Beta 文档 2026-09-15 核对：通用自定义工具事件与持久化历史；未公开原生 TodoUpdate 或同名更新事件。只借鉴权威历史与对账，不推断内部 TODO 实现。 |
| DeepSeek 源码 | 固定 0a53fb55 的 tool-todo 追加 todo/write 全量快照，下一 turn/start 清空投影；采用显式快照思路，不照搬 alpha 日志格式。 |
| OpenCode / Codex 源码 | OpenCode 849c2598 的 SessionTodo.update 替换表后发布 todo.updated（固定 v2 源码）；Codex d58d0e58 的 PlanHandler 发 PlanUpdate，App Server 文档定义 turn/plan/updated。两者证明任务更新可由后端显式发布，不能混称同一公共传输协议。Codex 同提交在 Plan 模式拒绝 update_plan，CampusClaw 采用同样的执行前拒绝。 |
| pi 源码 | 固定 5cd93f68 的 todo 示例从工具结果 details 恢复；这是另一种客户端派生方案，不作为当前 CampusClaw 进度消费方式。 |
| CampusClaw 已观察实现 | Java 09b32d8e 的 persistToolResults 已在批次结果边界提交；appendEntry 接收事件列表，仓库记录实际投影数量；该旧提交尚无 TODO 工具与专用事件/面板；后续实现和确定性验证见[问答证据](../06-CampusClaw计划模式/ask-user-question.md#2-基线与已观察实现)，不将旧差距扩展为当前状态。 |
| CampusClaw 目标 | build 根执行使用 TodoUpdate，plan 阶段调用在执行前被拒绝（`BUILD_MODE_REQUIRED`），不记录调研进度；成功工具结果同事务生成 agent.todo_updated。前端直接消费 todos；新消息隔离清单，审核续跑保持原根。 |
| 调用时机约束 | TodoUpdate description 集中规定任务实际完成并验证后立即更新，同次可完成上一项并开始下一项；BUILD 仅提示按工具描述跟踪进度，不再复写时机细则。通用验证与诚实交付由 BASE 负责；值校验不证明业务完成，模型仍可能漏调用。最新提示词证据见[§10](../06-CampusClaw计划模式/source-evidence.md#10-两份模式提示词的最新上游核验)。 |
| 差异分类 | 架构变更：后端负责将最终工具结果映射为公共任务事件，复用现有一 Entry 多事件事务。产品约束：build 实施（工具定义不随模式变化，plan 调用由执行前门禁拒绝）、单进行中、原根作用域、Agent/Tool/Skill 元数据不因 TODO 扩展。 |
| 理由与代价 | 前端无需识别工具名或解析结果文本，事件历史可直接恢复面板；代价是新增公共类型及每次更新的一份持久化快照，读取端需先升级；仍等待批次结果提交。 |
| 备选与重新评估条件 | 不新增 TODO CRUD、Session todos 或 TODO 表；如需独立任务身份、多人编辑、调度依赖或工具方法返回即发布，应另评估资源与提交边界。 |
| 设计 / 实现状态 | Java `8c5fda1d` 已实现 TodoUpdate、显式任务事件及前端消费、工具描述集中维护和两文件迁移，见工具状态专项证据；2026-10-12 在 main `769e8659` 复核，plan 模式门禁待实现（[PR #338](https://github.com/superheromeZzh/pi-mono-java/pull/338)），见[§18](../06-CampusClaw计划模式/source-evidence.md#todo-build-mode-gate)；Mate 桥接待实现，真实模型行为未核验，不将代码存在表述为验收通过。 |
| 验收与证据 | [T1～T4](../06-CampusClaw计划模式/todo-update.md#6-实施切片与验收)：同源同事务、失败无更新、缺工具记录也可展示、分页/live 对账、跨根与两跳身份；固定路径与符号见[§6](../06-CampusClaw计划模式/source-evidence.md#6-todo-update-基线与接入证据)。 |

**讲解要点。** 方案是待批准的完整设计，TODO 是实施进度。CampusClaw 用后端任务事件让前端直接展示清单，并把该事件与模型工具结果一起提交，避免两次写入不一致。它增加一份事件快照，但不增加元数据字段或任务表；完成状态仍是 Agent 报告，不代替业务验证和执行终态。

<a id="a06"></a>

## 6.3 A06 · 业务 Agent 绑定与 Mate 模型能力

| 维度 | 结论 |
|---|---|
| 模块与主设计 | M02，关联 M08/M11；[Model 主设计 §3、§5](../../02-服务与接口/03-Model/README.md#provider)维护命名、削减及依赖边界；复用其[唯一全局目标类图](../../02-服务与接口/03-Model/model-classes.svg)。 |
| 架构问题 | 企业产品只通过 CampusMate 调用模型时，如何保证每个业务 Agent 的默认模型和允许列表只有一个权威来源，同时避免进程级配置跨 Agent 注入模型？ |
| pi 模型来源历史观察 | 2026-09-17 核验默认分支 `main` 的 `16235fd93521f9f96164f5891beea62e6bea5b18`：`packages/coding-agent/src/core/model-runtime.ts` 的 `ModelRuntime.create/rebuildProviders` 默认读取 Agent Dir `models.json` 并组合内置、JSON 与扩展 Provider；`core/model-config.ts#ModelConfig.load` 校验 JSON；`core/agent-session-services.ts#createAgentSessionServices` 将模型目录和 `SettingsManager` 的默认选择分开。`packages/ai/src/models.ts#ModelsImpl/createProvider` 让 Provider 同时发布模型并流式调用。 |
| pi 能力最新观察 | 2026-09-19 确认并 fetch main `36b60d2e8985899743c4cf5bd5f8929832a3f05d`；`packages/coding-agent/src/core/provider-composer.ts#modelFromJson` 对自定义模型缺省填 128000/16384；`packages/ai/src/types.ts#Model` 具有逐模型 contextWindow/maxTokens；`packages/ai/src/api/simple-options.ts#buildBaseOptions/clampMaxTokensToContext` 合成请求额度；`packages/coding-agent/src/core/compaction/compaction.ts#createSummarizationOptions` 仍设置摘要额度。再次 fetch SHA 未变，新增核验摘要路径。只更新这组字段与消费路径，不把前次目录结论改挂新 SHA；默认分支快照不是稳定发布验收。 |
| CampusClaw 目标 | 唯一内置实现为 CampusMateProvider；Agent settings 只维护绑定/默认选择，每个新执行锁外查询当前模型的 contextWindow，锁内复核后固定执行快照；工具循环和原根续跑复用。Mate 自主控制普通调用及摘要输出，Claw 不消费或转发输出上限。移除统一 128000/8192；删除 ModelRegistry、外部 JSON 和第二目录，Provider SPI 只适配调用。 |
| CampusClaw 已观察实现 | Java `21c3f59b` 的 `AgentRuntimeManager#loadSnapshot/validSettings`、`AgentDirectorySnapshots#from` 和 `MateRuntimeModelManager#resolveModel/listAvailableModels` 已形成业务 Agent 设置主链；但 `ModelRegistry#init` 仍自动探测两处 JSON，`ModelCatalogService/CatalogRuntimeModelManager` 仍保留另一套目录解析，`CampusClawAiService` 仍注入注册表。Mate 本地 `4b957a3a` runtime 只返回模型 ID，路由配置未含两个能力数值；Java 仍使用全局默认值。完整路径见主设计源码证据 J-AI-N01～J-AI-N05 与[能力专项](../../02-服务与接口/03-Model/source-evidence.md#model-capability-evidence)。 |
| 差异分类 | 产品约束：CampusMate 唯一出口与输出权威，Agent 绑定唯一授权；架构变更：信息按新执行读取而非发布到目录、锁外查询及锁内复核、前置上下文检查；安全加固：禁止进程级外部模型来源。 |
| 理由与代价 | 窗口随新执行刷新，避免路由能力长期陈旧；执行内固定，避免工具循环期间预算漂移。代价是每根一次网络往返、元数据故障阻止新执行；查询后仍可能发生上游变化。Claw 放弃独立摘要额度和基于输出上限的 LENGTH 判断，保留显式 overflow 的有界恢复。 |
| 备选与重新评估条件 | 不保留旧 JSON 加载作为隐藏开关，也不以空目录日志冒充兼容。只有产品明确重新引入非 CampusMate 模型时，才重新设计模型身份、凭据、租户隔离、发布和回滚，不能直接恢复全局文件扫描。 |
| 设计状态 / 实现状态 | 已确认目标；业务绑定、执行准入和压缩骨架已存在。每执行信息查询、准入拆分、输出策略移交、前置预算和旧目录删除待实现；未修改产品代码或运行回归测试。 |
| 验收与证据 | 主设计 S0～S4、模型信息 C1～C4：每根一次查询、原根续跑复用、模型/版本竞争、查询失败无接受记录、普通与摘要请求无额度、窗口缩小及摘要无收益有界失败；modules/公司镜像一致。 |

**讲解要点。** pi 在 Harness 内维护模型能力及调用/摘要额度；CampusClaw 将输出控制集中到 Mate，自己按新执行读取窗口并管理上下文。绑定快照决定能用什么模型，执行快照决定本次按什么窗口压缩。收益是权威清晰且更新及时，代价是读取延迟、故障依赖及较少的本地输出控制；上述增量待实现。

<a id="a07"></a>

## 6.4 A07 · Codex 交互风格与 CampusClaw 计划语义

| 维度 | 结论 |
|---|---|
| 模块与主设计 | M07，关联 M01/M06；[前端主设计](../../07-前端设计/README.md)及[计划交互](../../07-前端设计/技术设计/plan-interaction.md)，复用前端唯一全局组件图。 |
| 架构问题 | 如何采用 Codex 的工作区密度、完整方案与轻量进度展示，同时保持 CampusClaw 的审核续跑和企业边界？ |
| Codex 观察 | 固定 d58d0e58 的 plan_implementation.rs / selection_view_params 提供实施、清上下文实施、继续规划；实施发起带 Default mode 的用户消息。PlanHandler::handle_call 在 Plan mode 拒绝 update_plan，另发 PlanUpdate；App Server 区分方案 Item、任务更新与提问。完整路径与官方 2026-09-15 公开证据见[专项 §1](../../07-前端设计/技术设计/plan-interaction.md#1-源码与交互依据)。TUI 不证明桌面像素布局；官方提问及固定版本方案增量保留实验性边界。 |
| CampusClaw 目标 | Composer 显示 Build/Plan；统一开发者设置按环境保存 IP/Header 并热应用；模式及会话菜单复用独立浮层；工具使用安全结构 viewer。问题每次显示一题、末题整批提交，专用卡吸收提问工具日志；完整方案正式批准后续跑原执行，进度与工具权限独立。 |
| 前次实现验证 | Java 开发分支 `9f785bea3ffff8f6566cd1b2727285af46a2aead` 已有计划审核、显式任务、结构化问题和标签式 Slash，恢复、Composer 停止与 DEV Token 助手也已实现；交互补齐提交 `fcae53829c2884ea1d3cc522c183f5a125a67f45` 已实现模式菜单、卡片折叠与复制、Dock 协同和 Sidebar 操作；189 项前端测试及浏览器验收的路径、符号和范围集中见[实现证据 §5](../../07-前端设计/source-evidence.md#current-implementation)。旧提交或未提交工作树不再用于判断这些能力是否存在。 |
| 历史体验核验 | Java `1d08f98e` 的 DebugHeaders/useDebugAuth 仍仅内存、Vite 使用启动 env、QuestionCard 一次展示所有题，projector 未吸收 AskUserQuestion；侧栏菜单缺删除/外点关闭、绝对菜单在 overflow 祖先内。完整路径、符号及限制见[体验证据 §6](../../07-前端设计/source-evidence.md#experience-evidence)。 |
| 新对照证据 | 固定 Codex d58d0e58 的 `codex-rs/tui/src/bottom_pane/request_user_input/mod.rs` 使用 current_question/go_next_or_submit/submit_answers；固定 OpenCode 849c2598 的 `packages/opencode/src/agent/agent.ts` 和 `packages/app/src/pages/session/composer/session-question-dock.tsx` 提供 build/plan 与逐题导航。公开 [Agents](https://opencode.ai/docs/agents/) 于 2026-09-15 核对；不据此推断 Codex 桌面像素或迁移 OpenCode 权限。 |
| 差异分类 | 产品约束：常驻模式按钮、O1 暖灰、结构化提问及无工具降级、无清上下文执行/运行中排队、不复制 Codex `/plan` 与 `/approve`；架构变更：审核事件绑定方案并续跑原执行、公共两跳映射；安全加固：缺页禁审、服务端目标复核、写入不自动重放。 |
| 理由与代价 | 逐题降低同时阅读量，整批提交复用已实现控制事务；隐藏重复工具 JSON 保留模型配对。持久化减少重复配置，但增加本机数据暴露面、配置版本与环境隔离维护；独立浮层增加定位/焦点工作。开发设置与生产身份分离，提示词规划不构成只读沙箱。 |
| 备选与重评条件 | 不直接复刻 Codex JSON-RPC、clear-context 选项或其品牌。若需要新执行/上下文选择，先重新确定审核目标、凭据、历史与启动权威。 |
| 设计状态 / 实现状态 | Java `8c5fda1d` 已实现逐题展示、整批提交和提问工具日志汇聚；`1d08f98e` 的相关缺口仅为历史证据。开发设置持久化的局部新核验见下方开发认证专项；浮层等其他体验未重核验；Mate 公共集成待实现，原型与静态源码不证明部署或回归通过。 |
| 验收 | [PF1～PF6](../../07-前端设计/技术设计/plan-interaction.md#6-组件与接入切片)：模式回执、精确方案、修订新身份、任务完整快照、终态独立、两跳与恢复；浏览器视觉与原型状态分别验证。 |

**讲解要点。** 参考 Codex 的输入邻近设置、方案与进度分离，让用户在同一工作区读方案、做决定、看实施进展。CampusClaw 的审核决定续跑原执行，不照搬 Codex 的新消息实施路径。这个差异保留执行归属，但增加事件映射与恢复要求；内部前端按已实现代码验收，企业集成另行对齐公共契约。

**工具名称专项（2026-09-19，M03/M06/M07）。** 本次 fetch 并核验 pi 默认 main `36b60d2e8985899743c4cf5bd5f8929832a3f05d`：AgentTool 有 label，工具执行事件仍不携带 label/displayName；该结论从名称专项旧基线 `5a3a03a7f5db43692915d6ae45e6d96497ea248d` 更新，其他基线与 UI 历史观察不随之升级。CampusClaw 在 Host 将实际工具 label 与已加载 Agent/Skill 绑定中的业务展示名写入调用事件，前端和历史直接使用保存值；来源由[M03](../02-CampusClaw工具系统/README.md#tool-display-name)、快照由[M06](../01-CampusClaw多Agent运行时/chat-events-design.md#tool-display-snapshot)、展示由[M07](../../07-前端设计/技术设计/内容渲染.md#mate-tool-display)维护。工具只有启停变化，因此取展示名不调用远程发现，不新增调用级执行 ID 绑定或解析失败缓存；实际执行继续校验可用性。该产品可读性约束与事件投影架构扩展避免前端另查目录及历史标题变化，代价是名称按已准备的元数据快照展示，并同步各消费端字段。Runtime/前端已有 PR #313 的分支实现，元数据读取修订与验收范围见[专项证据](../02-CampusClaw工具系统/source-evidence.md#tool-display-binding-evidence)；公共 Mate bridge 待实现。模型参数、确认身份与既有工具执行链保持，复用现有全局主图。

**开发认证专项（2026-09-19，M07）。** 这是 CampusClaw 开发环境的产品约束与前端编排变更，不引入新的外部 Agent 比较。Java 默认 `main@840d04405d2bcc80a41b9d3b3f16606cc4845338` 已有统一设置、持久化与手动获取；`App.vue` 六类写动作仍直接调用 `snapshotHeaders`。Claw 接口的可选凭据不改变此 DEV 工作台准备策略。目标由[工作台 §6](../../07-前端设计/技术设计/runtime-workbench-alignment.md#6-发送前自动获取-token)唯一维护：每次先重新获取，成功后提交，失败不回退旧 Token。代价是认证往返与故障依赖；后端不可变执行凭据不随确认/回答更新，不能保证长任务续期。精确路径、旧新基线影响及真实认证未验收边界见[源码证据 §8](../../07-前端设计/source-evidence.md#token-refresh-evidence)。复用工作台全局目标图；自动门禁待实现，其他外部基线与体验结论不升级。

## 6.5 A08 · 结构化提问与原执行续跑

<a id="a08"></a>

| 维度 | 结论 |
|---|---|
| 模块与主设计 | M01/M03/M06/M07；[AskUserQuestion](../06-CampusClaw计划模式/ask-user-question.md)，复用计划交互全局类图与独立问答时序。 |
| 架构问题 | 如何显式关联问题和答案、驱动前端控件，并在回答后继续同一根任务？ |
| 基线证据与行为 | DeepSeek 固定 0a53fb55（alpha）的 tool-ask-user apply/execute、UserQuestionService.ask、types.ts：问题 id、selected/custom、根上下文校验、等待后返回工具结果。pi 固定 5cd93f68 的 runLoop 将工具结果送入下一次模型请求。Claude Managed Agents 官方 Tools/Events 2026-09-15 核对（Beta）：应用提供自定义工具结果和权威历史；无同名原生问题事件声明。完整路径和链接见主设计 §2。 |
| CampusClaw 目标 | AskUserQuestion 在 plan/build 保持相同定义；后端 agent.question 驱动前端，user.question_answer 经现有 POST Events 回答全部问题；UI 一次一题、末题才提交，问题卡吸收精确关联的工具日志；原根/模式/凭据保持，plan 无调研 TODO，build 不重置清单。 |
| 已观察实现 | Java 开发分支 `9f785bea3ffff8f6566cd1b2727285af46a2aead` 已实现第十一项 AskUserQuestion、三类互斥等待、五输入及答案事务，调试前端从显式问题/答案恢复卡片。核验路径及符号见[主设计 §2](../06-CampusClaw计划模式/ask-user-question.md#2-基线与已观察实现)；RuntimeActiveExecution 直接实现工具窄端口，RuntimePendingInteraction 管理先绑定输出再唤醒的交接。 |
| 差异分类 | 架构变更：显式公共事件、GaussDB 答案交接及统一三类待交互槽；产品约束：1～3题、全部作答、仅交互根、独立计划审核；安全加固：闭合字段、目标/选项/分支锁内复核与停止优先。 |
| 理由与代价 | 问答恢复无需解析消息或工具文本，build 中澄清保留任务归属；代价是两种新事件、控制表及客户端同步发布。保留无工具普通消息降级；不承诺进程崩溃接管或模型必定提问。 |
| 备选边界 | 不复制 DeepSeek Cordis、plan-review intent 或空答案跳过；不新增问卷 CRUD、Session 指针、元数据字段或通用工作流。逐题翻页不构成部分提交；若需 Subagent 直接提问/部分提交/持久化草稿，重新确定交互归属与控制边界。 |
| 设计状态 / 实现状态 | Java `8c5fda1d` 主线已实现问答闭环、逐题导航、整批提交、工具日志汇聚和模式提示词装配；原 PR #301 测试结果仍只证明原提交。Mate 桥接待实现，业务 SYSTEM 发布、优先一题等真实模型遵循未核验，本次未重跑测试。 |
| 验收 | Q1～Q5 对应 clean verify 2085 项、独立数据库 140 项及前端 172 项通过；实际 JAR HTTP 继续/竞争/中断、214 契约样例、10 投影场景和浏览器 18 项检查通过。公司 NativeParent 缺失、外部 Mate 与真实模型未验证；完整环境边界见主设计 §2。 |

**讲解要点。** 借鉴 DeepSeek 的工具式提问，将 UI 等待接入 CampusClaw 已有执行段和控制事务。用户回答成为原调用结果，前端消费显式问题；计划批准与工具权限保持独立。获得精确关联和原根续跑的同时，需要维护答案交接与恢复，元数据结构保持稳定。

**同批位置专项（2026-10-13，M03/M01）。** 问题：一次响应里先更新进度、再请求现场确认，能否一起执行？本次 fetch 各默认分支：Codex main `90f00bd89ed3263b4d5993849cccb795f4330449` 的 `codex-rs/core/src/tools/handlers/request_user_input.rs#handle_call` 不检查同批调用，未声明并行时由 `tools/router.rs#tool_supports_parallel` 与 `tools/parallel.rs` 的执行锁串行处理；OpenCode dev `c1615b1db9c2e7a955f2be1024e84bb74c90cc6b` 的 `packages/core/src/tool/plugin/question.ts` description 与执行均无同批约束；DeepSeek Harness master `d743267388641bc76f17c45ce8b4c231aed1d32c`（0.2.1-alpha.2）的 `packages/interaction/tool-ask-user/src/index.ts` 与 `packages/plan/plan-mode/src/index.ts#exit_plan_mode` 同样不限制，调度见 `packages/core/agent-loop/src/tool-calls.ts`。Claude Code 未开源，本次不作证据。三者都把提问当作普通串行调用，排在后面的调用会在拿到答案前执行。CampusClaw 规定提问与用户确认 Tool 必须是本批最后一个调用、每批最多一个，ExitPlanMode 仍须单独调用，违规时在执行前整批拒绝；这是产品约束，避免依赖答案的动作先行，同时放行 TodoUpdate 等前序调用。代价是批次规划前置一次只读交互识别，违规时多一次模型往返。Java main `2b3bad05416c5ef67c6a6e085b210319d1f1b34a` 仍要求唯一调用且在调用自身 before hook 检查，目标待实现；规则、源码差距与验收由 [M03 §7.1](../02-CampusClaw工具系统/README.md#interactive-tool-batch) 维护，只升级本专项范围。

<a id="a09"></a>

## 6.6 A09 · Skill 计数复用统一结果

| 维度 | 结论 |
|---|---|
| 所属模块 | M05 [成功调用统计](../04-CampusClaw命令系统/03-Skill加载统计/README.md)，共用 [A15](#a15) 的执行与持久化链 |
| 问题 | 三入口已有真实工具结果，是否还需要第二套统计事件、日志和投递？ |
| 基线 | pi main 42a3497d 的最终工具结果与后置处理支持成功判定，但没有本产品累计表；本次新核验见[证据](../01-CampusClaw多Agent运行时/unified-event-persistence-evidence.md) |
| 已观察实现 | Java main 与 #335 分别记录在[M05 证据](../04-CampusClaw命令系统/03-Skill加载统计/source-evidence.md)；#335 仍有正文/hash/来源及独立统计链，不等于已落地统一历史 |
| 目标 | 新 LIVE 成功 Skill 工具结果首次写入时，同事务加一；结果唯一关联负责防重，不增加独立统计流水、Observer 或队列 |
| 理由与代价 | 直接复用权威事实避免双写对账；一张累计表保留删除后的 lifetime。代价是累计写入影响结果事务，热点及故障必须验收；不能再承诺统计故障不阻断推进 |
| 产品边界 | 每次调用计数，失败/Read/正文注入/恢复/复制不计；删除不扣累计；精确范围和日表仍待核实 |
| 状态与验收 | 统一结果及投影待实现；三入口、并发重复、回滚、清理、缺口、Provider ID 复用和真实 GaussDB 验收见主设计 |

**设计表达。** 工具历史就是统计事实，累计只是同事务投影；基线帮助确定结果语义，企业保留和统计一致性由 CampusClaw 自己选择。

<a id="a10"></a>

## 6.7 A10 · 删除通用命令与文件写入工具

| 维度 | 结论 |
|---|---|
| 所属模块与主设计 | M03；[工具系统 §12.4](../02-CampusClaw工具系统/README.md#124-删除禁用与替换)维护删除边界，复用既有全局工具类图；图中本就没有三项退役工具，本次不改变分层与关系 |
| 架构问题 | 已不装配的 Bash/Edit/Write 是否仍作为备用实现保留在发布源码和镜像中？ |
| pi 已观察行为 | 2026-09-18 更新默认 main 到 `e4ce7b449f4d91589c8760d6fbfa6eaaf82b05fe`；`packages/coding-agent/src/core/tools/index.ts` 的 createCodingTools 组合 read/bash/edit/write，createReadOnlyTools 组合 read/grep/find/ls，createTool 仍提供三个写/执行工具；不是上游废弃。只升级该范围，默认分支不等于稳定发布。 |
| CampusClaw 已观察实现 | Java `8c5fda1dde51675859bc9c07e145dbe253656dea` 的 BuiltInToolName/Factory 已排除三工具，但 tool/bash、tool/edit、tool/write 及专属 operations/队列仍存在；精确路径和有效消费者见[源码证据 §5](../02-CampusClaw工具系统/source-evidence.md#5-basheditwrite-源码删除边界2026-09-18) |
| 已确认目标 | 完全删除三工具、专属支撑和生成镜像副本；不保留兼容、隐藏开关或独立执行器。保留其他既有活动工具及 Agent 子代理；A11 另行增加 SearchTools。仍有消费者的只读/截断/路径/目录发布能力保留 |
| 分类、理由与代价 | 产品约束：企业 Runtime 不提供通用本机命令或文件写入模型工具；安全加固：减少重新接入面与无产品用途的维护负担。代价是放弃三工具实现复用；删除不意味着 Mate/Cron 无副作用，也不替代各自权限控制 |
| 备选与重新评估 | 仅禁用或不注册不满足源码删除目标；若未来重新需要本地写入/命令执行，须独立设计授权、工作区和取消/审计边界，不恢复旧代码作为开关 |
| 实现状态与验收 | 活动 profile 排除已实现；开发分支 `1b35422c61d471e11b9e1c126b57a82ef808ced2` 已删除源码，[Draft PR #315](https://github.com/superheromeZzh/pi-mono-java/pull/315) 待合入。2009 项测试、退役类缺席与三入口拒绝检查通过；公司编译因 NativeParent 不可解析未验证，完整范围见[证据 §5](../02-CampusClaw工具系统/source-evidence.md#5-basheditwrite-源码删除边界2026-09-18)，不把分支完成写成主线完成 |

**讲解要点。** pi 面向通用 coding 保留执行和写入工具；CampusClaw 的产品能力更窄，因此不仅不注册，还删除无用实现。保留仍有消费者的公共能力，避免把模型写工具退役扩大成整个系统禁止文件写入。

<a id="a11"></a>

## 6.8 A11 · 远端工具代理与 Skill 按需披露

| 维度 | 结论 |
|---|---|
| 模块与主设计 | M03/M05；[工具注册与发现](../02-CampusClaw工具系统/README.md#9-工具注册与发现)维护契约、全局目标类图及验收；本条只解释基线与差异。 |
| 架构问题 | 远端业务工具如何复用执行能力，同时让 Agent 常规工具直接可用、Skill 工具定义按实际步骤披露？ |
| OpenCode 观察 | 最新 `dev@fe3f3a4` 的普通 `SkillTool` 仍只返回正文、基础目录和最多 10 个抽样资源路径，后续资源由 read 获取。独立 Code Mode package 的 `prepare/makeSearchTool/searchIndex` 使用固定 `tools.$codemode.search`：预算只影响内联签名，搜索返回完整 path/description/signature，底层工具树不因搜索改变。它不是普通 Skill 的默认工具发现协议。 |
| Codex 观察 | 2026-09-22 核验 `main@89a7298a` 的 `ToolSearchHandler` 对 deferred 工具建立 BM25 搜索，搜索结果形成可加载 ToolSpec，并按说明暴露给下一次模型调用；缓存按 registry source 变化重建。其 Provider/模型能力和配置条件不构成所有 Agent 的统一规范，CampusClaw 不采用搜索后的动态 tools 暴露。 |
| DSH 观察 | `apply` 注册 skill(name)，`renderSkillContent` 返回正文与资源基础位置，不枚举文件；`syncTools/createMcpToolDefinition` 将 MCP 定义注册为工具并统一远端调用。校验顺序专项的 `0.1.7-alpha.1` 中，`ToolRuntime.prepareExecution` 先运行 policy/ask，`defineTool.execute` 包装器在 dispatch 后校验参数再进入用户实现。它仍是开发预览；这里只采纳职责分离并作为顺序差异证据，不迁入 Cordis 或 MCP 协议。 |
| CampusClaw 已观察实现 | PR #323 head `ae6645ca` 已实现 Skill 正文及抽样路径、Agent 元数据代理、CallTool、共用 MateToolExecutor、确认前可信准备和模型参数恢复反馈；GitHub build 成功。当前无 SearchTools，CallTool 文案仍指向 Read；MateToolResolver 按可信名称解析和缓存，已有重名冲突检查，尚未接入 SearchTools 的定义披露。前端低干扰展示仍待实现。完整路径见[SearchTools 专项证据](../02-CampusClaw工具系统/source-evidence.md#search-tools-evidence)。 |
| 已确认目标 | Agent 直接工具以代理提供模型 Schema；Skill 正文引用唯一业务工具名。需要定义时用 SearchTools({tool}) 精确取得单个完整定义，再由 CallTool 执行。发现只返回数据、不注册工具；复用可信解析，保证披露与校验定义一致，确认后执行同一准备结果。全量或按需加载、缓存与版本同步不在本版指定。 |
| 差异分类 | 产品约束：不引入 Bash 或可执行脚本，Skill 工具按需披露，无效业务参数不触发园区用户确认。架构变更：采用 OpenCode Code Mode 的固定搜索入口思路，但保留独立 CallTool；不采用 Codex 搜索后向下一次请求暴露匹配工具的语义。安全加固：发现和执行按可信绑定解析，校验定义与披露一致，确认前后固定目标与参数。名称精确匹配属于 CampusClaw 产品约束，不照搬基线的模糊搜索。 |
| 收益与代价 | 初始工具集合保持“框架工具＋Agent 直接代理”，多次发现不会累积代理，也不依赖工具定义文件。唯一名称可复用已有解析能力；代价是 Skill 正文需准确引用工具名，定义首次获取仍增加一次模型工具调用，结果仍可能被压缩，加载与同步还需独立设计。没有已验证的时延或准确率收益。 |
| 范围与重评 | 数据同步、刷新及版本一致性另行设计。若未来 Provider 原生延迟工具暴露具有明确的工具上限、替换语义和跨轮回收保证，再评估 Codex 式动态暴露；当前不把搜索结果加入模型 tools。 |
| 状态与验收 | Skill、CallTool、Agent 代理、确认前准备和模型参数反馈已在上述 Draft PR 实现，不能据此声称主线或端到端验收完成；SearchTools、定义一致性接线、profile/提示词和前端展示待实现。验收应证明多轮搜索不改工具集合、搜索与调用定义一致、参数失败不确认不执行、确认后使用同一准备快照，以及两类执行入口共用授权规则；文档校验不代表产品验收。 |

**讲解要点。** CampusClaw 保留 Skill 正文加载与工具定义披露的分工。正文说明准确工具名，需要时通过固定 SearchTools 取得单个定义，再通过 CallTool 执行。它借鉴固定发现入口，但采用自身的唯一名称约束，无需模糊搜索或动态注入；数据同步另行设计，不能把共享解析等同于全量快照。

**参数恢复专项。** pi 在 §12 核验的默认 main `95fbc04997eaee961eb673fa7923e9220609ebd5` 的 `prepareToolCall` 先准备和校验参数，再进入 `beforeToolCall`；校验错误作为 `isError=true` 的工具结果加入上下文，通常继续模型循环。DSH 在 §12 核验的默认 master `c36a83ff6bb95e3f82cf79f9be7c724270a8aa61` 则先运行 policy/ask，再由 `defineTool` 包装器校验后进入用户实现，表明不存在一条所有基线共同采用的固定顺序。两者都阻止无效参数进入实际业务实现，但只有 pi 的顺序满足 CampusClaw“无效参数不触发交互确认”的目标。完整证据见[M03 证据 §12](../02-CampusClaw工具系统/source-evidence.md#tool-validation-order-evidence)。

CampusClaw 采用 pi 的前置校验顺序，并为动态 CallTool 增加不可变准备快照；这是 Runtime 架构变更和 ToB 产品约束。PR #323 已实现准备阶段和[首次失败的定义反馈](../02-CampusClaw工具系统/README.md#tool-argument-recovery)；前端将明确未执行业务的参数错误[中性折叠展示](../../07-前端设计/技术设计/内容渲染.md#tool-argument-recovery-display)，该展示仍待实现。保留失败事实、独立调用身份和后续正常权限检查，不自动改参数重试。代价是额外定义文本、模型轮次与展示分类；准确率和时延收益未实测。

**用户确认分派专项。** M03/M08 采用可信 `metadata.is_confirmation_tool` 标记选择本地用户确认适配器，避免 Tool 改名依赖固定分派常量；权限仍由宿主检查，标记不等于授权。此为 CampusClaw 架构变更，代价是定义加载链需传递、验证标记，发布前需补齐既有确认 Tool 数据。2026-10-08 读取本地 Java `553dcd5e2ff682f9684810a043b442b37a02e54a` 的 `BusinessToolDispatcher#assembled/#select`、`MateToolExecutor#prepare`、`MateToolMeta`、`BusinessConfirmationAdapter` 与 `RuntimeActiveExecution#authorizePreparedQuestion`：当前按 confirm_with_user 名称分派，本地适配与 allow 准入已观察到；字段驱动接入待实现，未重跑产品验收。具体路径、旧行为、目标及验收由[Tool 主设计](../02-CampusClaw工具系统/README.md#confirmation-tool-metadata)维护；只升级这一局部核验范围，A11 的外部基线和其他 Tool 状态保留原历史归属，不推断外部 Agent 具有同一标记。

<a id="source-evidence"></a>

<a id="a12"></a>

## 6.9 A12 · 单条追加时间线与非递归历史读取

| 维度 | 结论 |
|---|---|
| 所属模块与主设计 | M04/M06；[Session 主设计](../../03-数据与存储/01-会话记忆GaussDB/README.md)维护线性不变量、事务和存量准入；[ListEvents](../01-CampusClaw多Agent运行时/chat-events-history-design.md#51-单条追加时间线源码与实施差距)维护公共分页；复用两处目标图 |
| 架构问题 | 不开放对话编辑或分支操作时，如何消除历史长度对数据库递归深度的依赖，同时保持完整事件和模型恢复？ |
| pi 已观察行为 | main `1a584a7a56eb5e7b4ff8ccbd46430f1533282eed` 的 `packages/session-backends/sqlite-node/src/sqlite/session/branch-entries.ts`：`appendEntryToBranchIndex` 写分支成员，`createDivergentBranchForEntry` 复制前缀或共享 compaction 片段，`scanBranchSegments` 按序号分页；`storage.ts#applyCommit` 同事务写 Entry 与索引。它没有逐 Entry 递归 CTE，但片段元数据读取和分叉复制仍有代价。 |
| CampusClaw 已观察实现 | Java `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12` 的 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java#appendLocked/findEventPage` 已有锁内追加和单请求一致性；`modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml` 的三个当前路径查询仍递归。Runtime Web 与命令入口未发现最近对话编辑/分支切换。 |
| CampusClaw 目标与差异分类 | 产品约束：只追加，不提供最近对话编辑、回退或分支。架构简化：按 Session/序号直接读取，不复制 pi 分支索引，也不新增当前路径成员表。并发加固：创建和追加事务维持单链；投影完整性不放宽。面向新建环境，不设计存量迁移。 |
| 理由、收益与代价 | 产品不产生替代路径，全部合法 Entry 自然属于同一时间线；消除递归上限与路径解析，不增加写侧索引维护。代价是不能在原 Session 改写对话或选择旧分支；深页 OFFSET 与全量校验仍需性能验证。 |
| 备选与重新评估条件 | 保留多路径时应重新考虑路径索引。未来开放编辑不能只增加修改 active_leaf_id 的入口。 |
| 实现与验收 | 尾部追加、数字分页和独立公共事件表已实现；三个非递归查询与长历史验收待实现。测试须覆盖超过 200/1000/10000 条 Entry、多事件投影、序号空洞、并发追加、压缩恢复与非法追加拒绝。 |
| 基线更新范围 | 原 M04 pi 基线 `f0deb8dd8e9611e89b5bc4145ca92c03ae6ed4ee` 的 `packages/storage/.../branch-cache.ts` 更新为上述 session-backends 路径；七表与 branch_tips 不再代表当前 pi。只升级本条分支索引结论，不覆盖其他模块旧 SHA；上游默认分支不是稳定发布承诺。 |
| 讲解要点 | pi 为多分支维护读取索引；CampusClaw 明确只追加，直接使用已提交序号读取。线性是写入事务保证的数据不变量，不是靠查询时忽略分支实现。 |

<a id="a13"></a>

## 6.10 A13 · Redis 快照与短期增量恢复

| 维度 | 结论 |
|---|---|
| 模块与主设计 | M06，关联 M01/M04/M07；[Redis 主设计](../01-CampusClaw多Agent运行时/redis-stream-recovery.md)维护完整目标类图、数据结构、两跳恢复、依赖和验收，本节不复制图 |
| 架构问题 | 浏览器关闭后落到另一副本，如何恢复尚未 completed 的完整前缀并接着流式输出，而不重新执行用户消息？ |
| OpenCode 已观察范围 | dev `fe3f3a41f79ad292cc3c7c629567385a20ec5130`：`packages/protocol/src/groups/session.ts#makeSessionGroup` 定义按 after 读取和回放 durable 的 experimental v2；`packages/schema/src/session-event.ts#Text.Delta/Reasoning.Delta/DurableDefinitions` 将 delta 排除在 durable 外；`packages/opencode/src/server/routes/instance/httpapi/handlers/event.ts#eventResponse` 先监听后发送 connected。该范围不证明使用 Redis或持久化全部 token。 |
| Java 已观察范围 | `53eff85c7f41de23eb434e027782f5085a8b8e45` 的 `RuntimeEventProjector` 经 emitBestEffort 发 preview，`RuntimeEventStream` 可拒绝/淘汰预览，`RuntimeResultBackedEventOutput` 只用数据库补读完整结果；控制轮询和先提交终态已有代码。完整仓库相对路径与符号见主设计 §10，不将旧差距扩展为当前未实现结论。 |
| CampusClaw 目标 | 在可丢弃 HTTP 队列之前写 Redis Hash 快照和有界 Stream；任何授权读取副本先取得快照 C，再读 C 之后的数据。Mate 通过内部只读 API 安全投影，公共 ID 稳定，完整历史优先。 |
| 差异分类与理由 | 架构变更：增加生成中内容的短期共享恢复，而非仅 completed 对账；产品约束：浏览器重开不重跑写入，企业 Chat/Session 边界不变；安全加固：缓存不保存凭据，读取须重新授权，不按订阅次数启动执行。 |
| 收益与代价 | 正常浏览器断线可恢复前缀并继续输出，读取不需粘性会话；代价为 Redis HA/内存/连接、快照原子边界、两跳新契约、缓存失效与降级处理。不宣称降低整体生成耗时或任意故障零丢失。 |
| 替代方案 | 仅数据库完整历史不能恢复半截正文；仅 Pub/Sub 不能补读；全量 token 永久日志超过本需求。数据库控制事务继续保留，Redis 不取代执行状态或自动接管 Java 对象。 |
| 状态与验收 | 推荐设计已形成；Redis 和新读取骨架待实现，HTTP 增量 proposed、精确契约待整合，Mate 实现未核验。R1～R6 覆盖跨副本浏览器重开、快照/增量竞争、重复/裁剪、库成功缓存失败、主从回退与执行 Pod 丢失；本次只有设计验证。 |

基线更新只从登记点 `849c2598abc7d2b40261e74b5826bc74ffc78308` 升级上述 OpenCode 三处事件范围，不更换 A04/A05 等历史证据，也不称默认分支快照为稳定版本。Redis 的命令与失败语义来自当日官方文档，来源集中在主设计 §10。

讲解要点：数据库负责正式结果，Redis 快照负责恢复当前草稿，Stream 负责接着读；恢复的是观察，不是重新执行。最重要的代价是明确缓存丢失时如何退回完整历史，而不是承诺“用了 Redis 就永不丢字”。

<a id="a14"></a>

## 6.11 A14 · Cron、定时提醒与独立 Agent 运行的调度边界

| 维度 | 结论 |
|---|---|
| 所属模块与主设计 | M10 [定时任务主设计](../08-CampusClaw定时任务/README.md)，关联 M01/M03/M04/M06/M08 及 [Mate 执行上下文](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md)；本文维护基线差异与理由，具体规则、全局目标类图、实施切片和验收由主设计唯一维护 |
| 架构问题 | 到期时间由谁拥有，定时器只是唤醒还是执行权威；到期后是回到同一 Session、创建新的 Agent Run，还是由外部平台重新启动进程；重启、空闲、暂停和失败如何对账？ |
| CampusClaw 目标 | [配置契约](../08-CampusClaw定时任务/README.md#interface)维护完整接口，[定时任务受理流程](../08-CampusClaw定时任务/README.md#normal-acceptance)维护受理与恢复：有 schedule 保存即登记自动计划，省略时只保存，试运行显式触发；接口配置的任务每次运行新建 Session 并复用 Agent，对话中由 Cron 工具创建的任务关联当前会话、每次在该会话追加一轮，会话忙则跳过，删除会话时一起删除，创建、修改、删除需用户确认（参考 DSH 投递回原会话）。首版仅文本、无人工交互，不补跑、遇忙跳过、本次失败/故障不重跑；删除 Schedule/Run 不自动取消已受理执行，Session 独立管理。定时实现合并 coding-agent；失败是否自动暂停整个 Schedule 仍待确认。 |
| CampusClaw 实现 | 2026-10-10 核验 PR #332 `e9d31e8888a81b7fe95071e705482bb16fa10476`：三张调度表、Mapper、同库受理与根执行启动控制已实现、未合并；完整 head/base/merge-base、字段及差距由[Claw 数据库设计（定时增量）](../../03-数据与存储/Claw数据库设计.md#schedule)维护。其他历史段落仍归原核验提交，不能外推为当前 PR 无实现；真实 GaussDB、多实例与企业部署未验收。 |
| 基线分工 | Claude Managed Agents 是平台调度主基线，触发独立 Deployment Run 和新 Session；DeepSeek Harness、pi Pico v3、OpenCode、Codex 分别保留 Session 内提醒、通用 Task、外部 Workflow 和宿主调度的历史对照。没有统一的“Agent Cron 实现”，不以这些基线的多数行为代替产品决定。 |
| 成熟度边界 | pi Pico v3 的所引文档标为 design under discussion（不等同于无实验源码），DeepSeek Harness `dsh-0.1.7-alpha.1` 仍为 alpha，OpenCode 当前核对的是 `dev` 分支，Claude Managed Agents 仍要求 beta header；Codex Scheduled Tasks 以官方产品文档为公开契约，未取得服务端实现源码。 |

数据库职责与既有架构取舍保持；本次仅集中数据库文档并更新 CampusClaw 局部实现状态，没有新增或升级外部 Agent 基线比较结论。

首次触发与周期推进采用2026-09-30重新获取的源码和官方资料，见下表；其余完整调度职责表保留各行的历史快照，不把这次有界核验外推为所有运行、权限和恢复结论已更新。

### 计划时间摘要与管理接口范围（2026-10-08 专项）

当日重读 Claude Managed Agents Beta 的 Deployment 操作目录与调度指南：公开目录没有独立时间预览，schedule.upcoming_runs_at 在已保存资源响应中提供最多五次未来计划时间；不推断 Console 的内部校验接口。核验范围及链接见[M10 计划时间摘要证据](../08-CampusClaw定时任务/source-evidence.md#schedule-time-summary-evidence)，其他源码基线保留原核验日期。

CampusClaw 同样仅通过完整 Schedule 响应提供未来计划时间，创建、更新在保存时校验规则；不提供未保存规则的独立预览。该产品范围减少额外操作及两条交互路径，代价是服务端计划时间须保存后取得；有效 Cron 保存即自动调度，不能把保存当作无副作用的预览。配置校验、UTC 秒级、默认上海时区及暂停后的假设计划继续按[配置契约 §3.3](../08-CampusClaw定时任务/README.md#433-计划时间与最近运行摘要)维护，目标待实现，不新增默认暂停或试保存流程。

### 首次触发与周期推进（2026-09-30 专项）

| 基线与适用范围 | 首次时间 | 后续周期 | 对 Claw 的参考边界 |
|---|---|---|---|
| DSH 0.2.0-rc.2；默认关闭的实验 Schedule | every_seconds 从创建调用取样时间加一个完整间隔，没有 startAt/anchorAt；取样早于串行队列与持久化完成 | 固定时间表；晚到取最新到期项，耗时不改变相位 | 仅保留间隔语义历史研究，不进入 Claw 当前仅 Cron 契约 |
| pi experimental/pico3 进程 Job | notBefore 可选；省略时在激活与准入满足后立即执行，即使提供 every 也不先等待间隔 | 观察进程退出并记录后，以当前时间加 every，属于固定延迟；两个时间值均为毫秒 | 属于进程 Job，不进入 Claw 当前仅 Cron 契约 |
| Claude Managed Agents Beta Deployment | Cron 规则给出未来计划，资源返回 upcoming_runs_at；没有 every/startAt | 五字段日历匹配，实际开始存在 jitter；即时运行通过显式 run | 可参考配置/试运行分离，不能用它确定 every 默认首次时间 |
| OpenCode 官方 GitHub 入口 | GitHub Actions 根据 Cron 触发；OpenCode 消费 schedule 事件 | 外部五字段 Cron，非 Runtime 的 every 计算 | 不提供可直接对齐的 every/startAt 用户任务契约 |
| Codex 宿主 Scheduled tasks | 官方支持 RRULE 和聊天内分钟间隔；没有公开与 Claw 同形的首次默认公式 | 本次文档与开源元数据不足以证明具体间隔推进算法 | 不把插件计划摘要或 turn_trigger 标记当作调度器实现 |

完整提交、源码符号、单位与返回形状见[M10 首次触发证据](../08-CampusClaw定时任务/source-evidence.md#first-fire-evidence)。这些基线没有统一的首次执行默认值；当前 Claw 仅提供 Cron，历史每间隔任务研究不构成当前输入范围。下文历史表中“当前”均只指对应固定快照；2026-10-04 的目标专项另行列出，不覆盖未重核的生命周期证据。

### 时区字段与默认来源（2026-09-30 专项）

| 基线 | 时区规则 | Claw 取舍 |
|---|---|---|
| DSH experimental Schedule | Cron 的 time_zone 必填，无默认；at 字符串自带 offset，本地对象则要求 time_zone；every 无时区字段 | 日历周期需要解释时区，绝对时刻与固定间隔不必机械增加 timezone |
| pi experimental/pico3 | notBefore 是 epoch 毫秒，every 是毫秒时长，没有日历时区字段 | 不能据此认定默认 UTC、上海或系统时区 |
| OpenCode GitHub 入口 | GitHub Actions 默认 UTC，允许可选 IANA timezone；Runtime 只消费事件 | 可以参考显式默认值，但不能把它归为 OpenCode 自有调度器行为 |
| Codex | 所查开源摘要无 timezone，OpenAI Docs 未规定时区默认来源 | 本次未能核验默认值，不作为 Claw 默认时区的依据 |

本专项重新确认默认分支并 fetch：DSH master `639ed015397290b3745d163aafe02ffee4aa3f84`、pi main `ee602414c703be8da722ec56de7f2399e62581ac`、OpenCode dev `2fa3363c924c5c3e367b84a87ae478296a0ed59b`、Codex main `d42056091aded7feb1d88ac7e83972108b2aa478`。pi/Codex 相对前项的所查文件无变化；完整路径、符号、旧新范围及官方文档见[M10 时区证据](../08-CampusClaw定时任务/source-evidence.md#timezone-evidence)，不升级其余历史表。Claude 的 Cron 必填 IANA 时区已由配置契约记录；Claw 已确认 timezone 可省略并默认保存、回显 Asia/Shanghai，属于面向主要园区场景的产品约束。当前 Claw 不提供 at/startAt 输入，绝对时刻响应为 UTC 秒级且无小数秒，Session 与完整事件同步采用这一目标，精确规则见[接口契约 §4.3.4](../08-CampusClaw定时任务/README.md#timezone-rules)。

### 定时执行目标与文件能力（2026-10-04 专项）

| 基线 | 当次核验结论 | 与 CampusClaw 固定新会话的关系 |
|---|---|---|
| Claude Managed Agents Beta | Deployment 每次新建 Session；name 最长 256；schedule 只支持 Cron | 每次新建 Session 的主基线；没有 Deployment 已有会话选项 |
| OpenAI 宿主 Scheduled tasks | 官方产品文档明确每次新聊天和继续原聊天两种模式 | 保留原会话是该宿主的额外能力，Claw 当前不采用；不能推断同形 HTTP 契约或开源 harness 实现 |
| DSH `0.2.1-alpha.1` | 提醒目标固定为创建它的原 Session，Host 可恢复后投递 followup | 是继续原会话的直接参照；不支持每次新建或任选另一个 Session |
| OpenCode 默认 dev 快照 | 官方 GitHub schedule 每次无条件创建 Session，Action 没有 target 选择 | 外部调度配合新 Session；普通 Session prompt 不能证明定时绑定能力 |
| pi 默认 main 快照 | 普通 Session 新建/切换/followUp；旧 Pico3 Job 路径已不存在 | 不构成用户定时任务选择 Session 的证据；新 durable scheduler 是 Harness 任务推进器 |

完整默认分支、旧新 SHA、路径和符号由[M10 目标与文件证据](../08-CampusClaw定时任务/source-evidence.md#target-file-evidence)维护。CampusClaw 采用 Claude 每次新建 Session 的范围，复用任务绑定的 Agent 定义，创建和更新不提供 target/sessionId 选择。收益是每次作业的历史与结果独立，减少既有 Session 绑定、忙闲和上下文竞争规则；代价是接口配置的任务不能延续某个已有聊天；2026-10-16 起对话中创建的任务改为关联原会话，见 [M10 §3.13](../08-CampusClaw定时任务/README.md#chat-created-schedule)。精确字段与运行行为由配置/执行专题维护，创建响应逐字段对比见[响应审阅](../08-CampusClaw定时任务/README.md#creation-response-review)。

Claw 同日重核 Java main `553dcd5e2ff682f9684810a043b442b37a02e54a`：fileId 引用已可保存、回显，但模型输入只有 ID 文本；所查 Claw/前端范围无上传链路，附件按钮禁用。首版定时输入仅文本，明确拒绝附件，不因能保存引用而宣称能读取内容；普通 Session 的文件引用不受此产品范围限制。M09 目标由 Mate 提供上传，其单 Session 绑定与长期授权仍须单独衔接；Claude Files API 的上传及资源挂载不能证明 Claw 已具备这些能力。名称上限256、仅 Cron 不引入新依赖；六字段和默认上海时区保留。

### 创建响应与凭据引用（2026-10-04 专项）

Claude 官方 Beta Deployment 的 schedule 提供 last_run_at/upcoming_runs_at，status 使用 active/paused，归档以 archived_at 表达；metadata 为受限字符串 map。CampusClaw 响应采用对应 lowerCamelCase 时间摘要、小写状态并去除公开 revision，支持可选 metadata。计划时间只是估计，不等于业务完成；内部调度游标继续存在。动态时间摘要仅供展示，不构成更新前置条件；Claw 采用直接删除，资源不增加归档字段或状态。

Claude 通过 vault_ids 引用独立管理的凭据，敏感值只写不回读，运行时按 MCP 目标或受控出站规则使用。CampusClaw 定时任务不保存凭据引用，所有定时任务统一使用 Mate 配置的同一个账号：模型每批需要凭据的工具调用前，Claw 无入参向 Mate 取一次该账号的 `access-token`。相比 Claude 按部署挑选 Vault，收益是任务配置不承载秘密选择、实现最简单；代价是所有任务权限相同，用户权限只在配置时检查，创建者失去权限后任务仍照常运行。普通 Session 继续使用本次请求 Header 快照，定时执行的 Token 仅在本批内存供实际 execute 使用，发现不带业务凭据，服务身份不冒充业务凭据。现有 Java Cron 仍使用空凭据，Mate 示例也未实现凭据接口；生产能力未核验。[Mate 配套草案](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md)与接线均待实现，首版不引入 Vault 集合或完整 sandbox 出站替换体系。

公开契约、源码路径与限制见[M10 响应与凭据证据](../08-CampusClaw定时任务/source-evidence.md#creation-metadata-credentials-evidence)，精确创建报文和待决项仍由[配置接口](../08-CampusClaw定时任务/README.md#creation-response-review)维护；不扩写其他模块的历史 SHA 或声称已有长期执行凭据。

CampusClaw 已确认完整 Schedule 响应增加只读 type:schedule 与 pausedReason。前者对齐 Claude type:deployment 的资源识别职责，以一个恒定字段换取脱离路径仍可辨认资源；后者对齐 paused_reason 的人工/错误暂停及恢复清空语义，使运营人员能判断任务为何停止自动执行。当前原因需要随状态持久化，不能由最后一个 Run 错误推断；是否由运行失败自动暂停整个 Schedule 仍待确认，响应中的 error 形状不代表所有失败均触发暂停；不继承旧 Cron 连续失败3次禁用。现有 Session 响应不因此扩展字段；当前 Cron 的 enabled 也不能提供等价原因。已确认目标与源码差距见[M10 专项证据](../08-CampusClaw定时任务/source-evidence.md#schedule-type-pause-reason-evidence)，字段精确定义由[配置契约](../08-CampusClaw定时任务/README.md#schedule-type-paused-reason)唯一维护；删除成功的完整回执保留最后状态与原因，随后不再提供 Schedule 读取。

### 配置停用后的可读取性（2026-10-04 专项）

2026-10-04 当次重新读取 Claude Managed Agents Beta [操作目录](https://platform.claude.com/docs/en/api/http/beta/deployments)与 [Archive](https://platform.claude.com/docs/en/api/http/beta/deployments/archive)：其公开归档使用 POST、无业务正文、200 完整 Deployment，以 archived_at 表示不可恢复的终态；公开目录未列出 DELETE，列表可通过 include_archived 包含归档资源。公开资料未明确重复归档、归档 GET 或在途 Session/Run 处理，不能将 Claw 的选择写成 Claude 保证，也不能推断其内部存储。

CampusClaw 已确认删除 Schedule 及其所有 Run，保留已经生成的 Session；不提供归档操作、archivedAt、includeArchived 或 archived 状态。存在的 Schedule 仍为 active/paused；删除生效后的新读取中，Schedule 和关联 Run 详情返回404，各自列表排除这些记录。这属于产品约束及生命周期架构选择，减少任务侧历史维护，代价是原配置、触发来源及没有 Session 的受理失败记录不再可查。Session 按自身当前权限读取和删除，授权不依赖已经删除的 Schedule 或 Run。

[删除契约](../08-CampusClaw定时任务/README.md#delete-schedule-review)采用 DELETE200 与 ResultBean 完整 Schedule 回执，借鉴 Deployment archive 的返回形状；回执不构成删除后的读取入口。删除与最终受理共享数据库权威：删除先提交则不能受理，受理先提交则原 Session 继续由 Runtime 管理。删除不自动取消已受理执行，停止由 Session 入口单独发起；反向删除 Session 保留存续 Schedule 下的 Run 受理事实。必要内部协调归根执行生命周期，不能变成长久完整配置/Run 归档，晚到收尾不得恢复已删资源。

同日确认并隔离 fetch Java 默认 main，仍为 `553dcd5e2ff682f9684810a043b442b37a02e54a`；当前 Cron 取消本地定时器后删 jobs.json，保留 Run 日志却不能通过旧工具读取已删任务历史，也缺少删除与运行受理的统一事务。现有 Runtime Session DELETE 的墓碑/后台清理可作为机制参考，但其拒绝忙会话不能直接复制给仅拥有配置的 Schedule。源码路径、符号、公开资料及未验收项见[M10 删除证据](../08-CampusClaw定时任务/source-evidence.md#schedule-deletion-evidence)；本段不升级其他基线历史结论。

### 立即运行与自动计划启停（2026-10-05 专项）

重新核对Claude Beta的[Run](https://platform.claude.com/docs/en/api/http/beta/deployments/run)、[Pause](https://platform.claude.com/docs/en/api/http/beta/deployments/pause)、[Unpause](https://platform.claude.com/docs/en/api/http/beta/deployments/unpause)及Run模型：三个操作均POST、无业务正文、200；run返回Session创建结果记录，pause/unpause返回完整Deployment。暂停不终止在途Session并允许手动运行，取消暂停从下一次计划继续且不补跑。重复启停、精确更新时间、手动重叠及各失败HTTP映射未完整公开；自动生成示例中的manual/schedule和状态/原因冲突不能替代字段约束。

CampusClaw的[三个动作](../08-CampusClaw定时任务/README.md#run-schedule-review)沿用这些职责与入口；已确认可靠记录的受理结果采用200 Run，已记录失败在error，请求认证/范围/存储故障仍用4xx或5xx。暂停/取消暂停采用200完整Schedule；保留秒级UTC、ResultBean、agentId和无客户端请求键。Run与业务执行分离，避免把“新会话已建立”误报成园区工单处理完成；代价是调用方须检查Run.error并继续观察Session。单任务不重叠、重复启停不重置时间/游标和恢复前检查资格已确认；首消息/根执行的同库受理、错误投影与 Mate 可信身份接线由[定时任务受理流程](../08-CampusClaw定时任务/README.md#normal-acceptance)维护，均待实现。

当日确认默认main并隔离fetch，Java仍为`553dcd5e2ff682f9684810a043b442b37a02e54a`。旧trigger同步等待模型完成，绕过手动busy检查；disable取消本地句柄后整体保存旧对象，运行收尾可能覆盖暂停；enable重复调用会重排。新HTTP、持久化Run/Session关联及数据库状态屏障待实现，不能包装旧方法直接兑现新契约。具体路径、符号、源码推导与未验收项见[动作证据](../08-CampusClaw定时任务/source-evidence.md#schedule-actions-evidence)。本次只升级该范围，未重新核验其他Agent基线。

### Run读取与删除历史范围（2026-10-05 专项）

Claude Beta的[Run列表](https://platform.claude.com/docs/en/api/http/beta/deployment_runs/list)与[详情](https://platform.claude.com/docs/en/api/http/beta/deployment_runs/retrieve)使用独立资源，复用八字段会话创建结果；列表deployment_id可省略，默认limit20、最多1000，page为不透明游标。Claw建议使用独立Run列表/详情并复用已确认的受理模型，分页沿ListEvents整数风格；这属于客户端一致性的产品取舍，不能复制事件尾部追加的稳定位置前提。

Claw 删除 Schedule 及其所有 Run，Session 独立保留；删除后的 Run 读取不包含这些记录。配置删除不自动取消已受理执行，因此 DELETE200、Run404 或空列表不能证明业务已停止或此前未受理；停止与观察归 Session 入口。反向删除 Session 不删除仍存续 Schedule 下的 Run，保留历史受理事实，但不承诺原会话仍可读。Claude 公开归档资料未声明对应保留期限或级联关系，不能作为该取舍的保证；精确读取契约由[M10 读取边界](../08-CampusClaw定时任务/README.md#schedule-run-read-lifecycle)维护。

当日隔离fetch Java默认main仍为`553dcd5e2ff682f9684810a043b442b37a02e54a`：旧Cron按JSONL行读最近记录，缺Run详情和持久Session关联；删除Job后工具入口不能读取残留日志。Runtime ListEvents已实现默认50/最多200、limit+1和单请求一致分页，可参考协议；新Run与独立授权读取待实现。源码路径、符号及未运行的测试见[Run读取证据](../08-CampusClaw定时任务/source-evidence.md#schedule-run-read-evidence)，不升级其他Agent历史快照。

### 其他基线的删除关系（2026-10-05 专项）

OpenClaw为本专题新增的删除生命周期辅助基线，Claude仍是公共调度API主基线。本次重新确认并隔离获取默认分支；完整SHA、旧新范围、源码及测试见[M10删除基线证据](../08-CampusClaw定时任务/source-evidence.md#schedule-delete-baselines)。

| 基线 | 删除配置后的历史与会话 | 在途处理与参考边界 |
|---|---|---|
| OpenClaw main源码 | 保留独立Run历史及每run会话；清理任务专用复用base会话，共享main会话保留；Run和会话分别按保留策略清理 | 操作者删除请求取消，任务自删例外；不能把请求取消等同已停止。无范围限制操作者可查已删Job历史，受限读取仍依赖存续Job；不能照搬为企业租户历史授权 |
| DSH 0.2.1-alpha.1 | 物理删除任务及其内嵌投递历史，保留原Session及已入队消息；history随后not found | 删除不主动取消对话；投递与删除共用FIFO。它投递原Session，history是收件回执，不是新Session受理Run |
| Codex、OpenCode、pi | 本次所查源码或公开文档不足以确定同形定时配置的级联关系 | 分别涉及宿主定时产品、GitHub外部Workflow、实验持久任务执行器；普通Thread/Session删除不等于定时配置删除 |

Claw采用删除配置及所有Run、保留Session的已确认方案，降低任务侧历史维护成本，代价是失去无Session的失败记录及任务侧来源查询。该数据关系可参考DSH，但Claw的Run记录新Session受理，DSH的history记录向原会话投递，两者不能等同；OpenClaw提供了保留任务侧历史的不同取舍。Session 继续按独立生命周期和当前权限管理，Claw 不因删除配置自动请求取消；反向删除 Session 保留原 Run 的受理事实，精确规则由[配置生命周期](../08-CampusClaw定时任务/README.md#schedule-run-read-lifecycle)维护。

### 配置读取与运行观察（2026-10-04 专项）

Claude Beta 的 Deployment 详情和列表元素均返回完整配置，列表采用不透明 page 游标与 data/next_page；公开页未声明默认排序、ETag 或固定分页快照。CampusClaw 已确认列表元素与详情同形，包含纯文本任务内容（prompt），不含凭据引用；采用同一完整资源降低客户端模型差异，代价是分页传输全部任务内容。分页参考既有 ListEvents 的整数 page/nextPage、无 total 方式，建议沿用默认50/最多200；与 Claude 不透明游标同名但不同义，统一 Claw 客户端风格且无需总数查询。任务可变而事件在尾部追加，不能复制事件顺序及稳定位置前提；深页和并发编辑带来的重复/遗漏仍是代价。

Claw 读取以当前可信可见范围为准，不以 Agent/凭据当前可执行性阻止查看故障配置，不换取或回显 secret，也不创建 Session；这是企业产品约束与安全边界。2026-10-04 重新 fetch Java 默认 main 仍为 `553dcd5e2ff682f9684810a043b442b37a02e54a`：Cron get/list 是本地 JSON 与文本工具输出，没有新 Schedule HTTP；Runtime Session 已有单条 GET、ResultBean/no-store/ETag，但没有集合分页，也未在所查读取链观察到可信租户授权。新接口与相关接线待实现，不能把旧 Cron 读失败返回空值作为企业读取契约。

双方均区分配置与 Run 观察；Claude Run 只表示 Session 创建结果，Claw 的根执行结果由原 Session/根 execution 维护，内部对账只关联该根，不用后续新对话改写结果。精确字段、筛选和读取错误由[读取接口](../08-CampusClaw定时任务/README.md#get-schedule-review)维护；最新路径、符号和官方链接见[读取证据](../08-CampusClaw定时任务/source-evidence.md#schedule-read-evidence)。其他基线的历史结论不因该专项升级。

### 部分配置更新（2026-10-04 专项）

Claude Deployment 的 POST 更新区分省略保持与显式清空，事件/规则整体替换，metadata 按 key 修改，200 返回完整资源；agent 字符串还会重新固定最新版本。Claw 推荐沿用部分更新和完整响应，以既定可写字段限定范围：任务内容为纯文本 prompt，运行时作为新 Session 的第一条用户消息，不含凭据字段，Agent 只绑定身份；不将修改配置隐含为恢复、立即执行或修改历史运行。metadata 逐 key patch 是特例，不对规则做任意深层合并。Claude 以 vault_ids 在配置中引用凭据并区分两种清空值；Claw 不在配置中保存凭据，也就无需凭据清空语义，凭据变化随 Agent 绑定在 Mate 生效；这是产品约束。

Claw 全部接口采用无客户端条件及请求键的产品约束，不返回配套 ETag，也不在请求体或查询参数中换名设置令牌。服务端在短事务内锁定最新记录、合并本次提交字段并校验；不同字段相互保留，同一字段由较晚成功提交的更新生效。收益是降低客户端协议和回执存储复杂度，代价是不能拒绝旧页面上的同字段覆盖，创建或手动运行重试也可能产生新资源。自动触发唯一约束和 Run 受理去重继续保留。Claude 创建/更新公开页未声明这两个请求头，不据此推断其内部事务或去重。Java main 同日重新 fetch 仍为 `553dcd5e2ff682f9684810a043b442b37a02e54a`，Session 实际仍有 If-Match/ETag 及前端依赖，需同步迁移，Cron 没有公开部分更新。精确接口由[M10 更新契约](../08-CampusClaw定时任务/README.md#update-schedule-review)维护，证据及重试边界见[无客户端令牌专项](../08-CampusClaw定时任务/source-evidence.md#schedule-header-free-contract)；具体可写字段和错误由配置专题唯一维护，不在对比中复制接口。

### 1. 调度职责和权威状态

| 基线 | 调度入口与时间模型 | 权威状态与唤醒方式 | 到期后的执行边界 | 失败、重启与暂停 |
|---|---|---|---|---|
| pi Pico v3 | `Task.notBefore` 是最早执行时间；`Scheduler` 通过 `drive`/`resume` 检查依赖、时间、permit、取消和执行占用。`pi.job` 还支持 `notBefore` 与 `every` 毫秒间隔；未发现 Cron 表达式解析或用户级 Cron 管理入口。 | Task 记录持久化在 Session；`Scheduler` 的 `invocations`、AbortController 和 waiter 是进程内执行投影。未来时间可等待，外部事件或 permit 可使 drive 暂停。 | Scheduler 只保留通用生命周期，不理解 Prompt 或业务参数；Job 的 handler 负责等待、启动进程、轮询、重复和结果通知。 | 重启保留 pending/running checkpoint，重新 `drive` 后由任务定义决定 retry/adopt/interrupted；关闭不写取消。文档明确打开 Session 不自动启动任务，不能把恢复误解成自动 Cron。 |
| DeepSeek Harness | `schedule_create` 支持 `after`、绝对 `at` 和至少 300 秒的固定 `every`；明确不支持 Calendar/Cron。每个 record 保存 UTC `scheduledAt`，固定间隔保持创建时锚点。 | `schedule/change` Session 事件日志是唯一持久化权威；Projection 只是 active 视图；`ScheduleRuntime` 从 Session fold 重新计算并用有界 `setTimeout` 分段唤醒。 | 只对 live root Agent 生效；先等待 Agent idle，取得 maintenance claim，再向同一会话 `followup`，最后追加 dispatch 事件。正在运行的 turn 不被打断；一次性提醒优先，多个固定间隔提醒批量投递。 | Session 冷却时只保留 overdue；恢复 live root 后重新计算，固定间隔只投递最新到期 occurrence，不补发 backlog。创建/删除/dispatch 都有 persistence barrier；barrier 失败返回 `persistence_uncertain` 或让 runtime 停止，不能把内存 timer 当成功凭证。 |
| Claude Managed Agents | Deployment 的 `schedule` 是 5 字段 POSIX Cron + 必填 IANA timezone，粒度到分钟；服务返回 `upcoming_runs_at`。jitter 窗口为调度间隔的 15%，最少 5 秒、最多 9 分钟。 | Deployment 及 Deployment Run 由托管 API 管理；Run 记录 Session 创建尝试的结果。公开文档没有说明内部落库顺序、timer、分布式锁或数据库实现，不能推断必须先落 Run 再创建 Session。 | 每次调度创建新 Session，并发送 Deployment 配置的 initial_events；成功 Run 关联 `session_id`，只表示 Session 创建结果，Agent 执行结果另查 Session 事件。 | 一般创建失败记录 Run；主 Agent 被归档或删除时存在不落 Run 的例外。限流错误不重试、等下次 occurrence；不可恢复错误可自动 pause。pause 不取消在途 Session，unpause 从下一次 occurrence 继续且不补发；archive 终止调度。DST 按本地墙上时间匹配，春跳不存在的时间不触发，秋回重复时间触发两次。 |
| OpenCode | 当前 `dev` Runtime 没有 Cron/Schedule 模块；`BackgroundJob` 是 `Effect` 作用域内的进程内 job registry，不是日期调度器。官方 GitHub 集成把 `on.schedule` 的 Cron 交给 GitHub Actions。 | Runtime 的 BackgroundJob 只存 `SynchronizedRef<Map>`；官方 GitHub Actions、Runner 和仓库事件是外部权威，OpenCode 本身不保存 Schedule record。 | GitHub Actions runner checkout 后调用 `anomalyco/opencode/github@latest`；scheduled event 必须提供 prompt，输出进入日志/PR。它不是同一常驻 Session 的内部提醒。 | BackgroundJob 注释明确进程重启或 owner scope 关闭会丢失状态并中断工作；GitHub Actions 的重试、并发和失败结果由外部平台承担，当前 OpenCode Runtime 没有对应恢复协议。 |
| Codex | 开源 harness 未发现 Cron 解析、调度表或调度 loop。当前协议有 `ScheduledTaskSummary`，它是 PluginDetail 中的插件声明元数据；`TurnStartOptions.turn_trigger` 仅记录如 `automation_cron_scheduled` 的来源。旧 `agent_jobs` 表在 migration 0042 被删除。 | Codex Scheduled Tasks 是宿主/服务能力，不是 `openai/codex` 仓库内核。官方文档公开了 standalone task 与回到现有 chat 的 task、后台运行、worktree/local project 选择、运行记录和 RRULE 高级编辑；没有公开服务端存储和抢占实现。 | Standalone 每次新建 chat；chat 内任务回到既有上下文。Codex CLI 和 IDE 没有 Scheduled 管理界面，桌面 app 处理本地项目时要求机器和 app 保持运行。 | 官方文档要求使用 Scheduled 查看最近运行；无人值守任务使用默认 sandbox/权限策略。内核只接收宿主送入的 turn 并记录 trigger，不能据此推断 Codex harness 自己负责 Cron 恢复。 |

### 2. 正常调用与失败处理的主流程

这些基线处理的对象包含 Agent 会话、提醒与外部进程，不能把它们合并为同一种定时执行；下面保留各自注明日期的历史流程。按职责还原主流程如下：

1. **托管平台 Cron（Claude）**：创建 Deployment，绑定 Agent、Environment、initial event 和 Cron → 到期尝试创建新 Session 并投递 initial event → 通过 Run 查看创建结果，通过 Session event stream/webhook 观察 Agent 执行。该流程描述公开资源关系，不断言内部持久化先后。一般创建失败有 Run；主 Agent 归档或删除是无 Run 的例外。限流等到下一次 occurrence，不可恢复错误可使 Deployment pause。
2. **Session 内提醒（DeepSeek）**：工具校验规则和时间 → 等待持久化 flush → append `schedule/change:create` → 再次 flush 后确认 → runtime timer 唤醒并重新 fold → idle maintenance claim → `followup` 入队 → append dispatch → flush。任一步持久化不确定都不能返回“已成功”；运行中的 Agent 不被打断。
3. **通用 Task（pi）**：调用方先持久化 pending Task → 外部或本地 `drive` 扫描 covered scope → Scheduler 在 commit 中检查依赖、`notBefore`、permit、取消与单任务 claim → handler 通过 checkpoint 驱动阶段 → 结果与 successor 一起 settlement。它把“何时允许推进”和“业务如何恢复”分开，调用方仍负责在进程外重新 drive。
4. **外部 Workflow（OpenCode）**：GitHub Actions Cron → Runner checkout → OpenCode GitHub Action → Agent 执行 → 日志/PR。调度、运行隔离和失败语义主要由 GitHub Actions 承担；OpenCode BackgroundJob 只解决当前进程内并行工作和观察。
5. **宿主调度（Codex）**：Scheduled task 服务/桌面 app 按规则创建 standalone 或既有 chat run → 将 prompt、项目/worktree 和权限上下文交给 harness → harness 只处理普通 turn，并记录 `turn_trigger`。服务端的持久化、去重、抢占与失败重试未公开，必须标为未核验。

### 3. CampusClaw 的采纳与差异

[配置专题](../08-CampusClaw定时任务/README.md#claude-tradeoffs)定义可省略 schedule、有规则保存即启用和独立试运行；任务内容为纯文本 prompt，运行时作为新 Session 的第一条用户消息，首版不支持附件、多初始事件、system.message 或 user.define_outcome。名称上限256、仅 Cron 借鉴 Claude；Spring 六字段和默认上海时区复用现有能力，不新增外部依赖，代价是与 Claude 五字段及日/周组合语义不兼容。[固定注解与动态调度](../08-CampusClaw定时任务/README.md#spring-scheduling)各有适用场景，表达式秒粒度不保证准时开始。每次固定新建 Session，不提供 target/sessionId/chatId，也不新建 Agent 定义。Claw 没有可选 Environment 或可执行历史 Agent pin，已有元数据 version 不等于历史执行绑定；prepare 使用已发布快照，不保证每次远端最新。保存不调用可能发布目录的 prepare；执行策略与 Mate 配套契约另由所属专题维护。

下述执行与工程目标由[定时任务受理流程](../08-CampusClaw定时任务/README.md#normal-acceptance)维护，均待实现。失败自动暂停已定（M10 D12）：首版不自动暂停，任何运行失败只记录失败 Run，Agent 启停用与数据一致性另开设计（M10 T11）；DSH 失败只记日志、不暂停，pi、OpenCode 无产品内定时任务，Codex 调度器未开源（2026-10-14 核验）。

园区每日设备告警汇总、设施巡检和能耗报表首先需要独立的执行与结果记录，因此主线参考 Claude 的平台调度资源分层。正常流程由 Schedule 到期产生 Run，经可信绑定和规则校验、执行授权与 Runtime 准入后创建独立 Session；Run 保留受理结果，业务终态以原 Session/根执行为准，内部对账只更新协调摘要并释放所属占用。失败时先区分未受理、明确失败与已受理但结果未知，避免把 Session 创建成功当成业务完成，或因观察失败重复产生业务请求。

| CampusClaw 目标 | 差异分类 | 理由与代价 |
|---|---|---|
| 接口配置的任务每次自动或手动运行新建 Session，复用任务绑定的 Agent 定义；对话中创建的任务在原会话追加一轮 | 参考 Claude、DSH、产品约束 | 独立会话便于隔离每日作业上下文与结果，并减少目标绑定和忙闲规则；代价是不能直接延续已有聊天，跨次结论需要通过任务输入或业务记录提供 |
| Run 表达受理结果，Session/根执行表达业务终态 | 参考 Claude、架构变更 | 受理成功不等于园区业务完成；根执行终态与 Run 结束同事务提交并释放占用（M10 D11），代价是 Runtime 新增事务内终态扩展点，公开 Run 不复制完整消息或伪装业务结果 |
| GaussDB 作为 Schedule/Run 权威，同库内部事务关联 Runtime 受理；单任务不重叠 | 架构变更、安全加固 | 多实例或进程重启时不能仅靠内存 timer；现有非幂等 HTTP 创建/提交不能反复重试来代替原子受理。代价是新增数据库锁、唯一约束与事务集成，跨任务容量仍由运行时治理 |
| 不补漏跑、遇忙跳过、本次失败及故障不重跑，未知保持占用 | 安全加固、产品约束 | 防止重复创建 Session、重发首消息或重复可能已执行业务；下一自然计划是新触发。代价是故障可能漏执行，未知需对账或独立人工处置，可靠终态写入重试不等于重跑业务 |
| 每次触发使用已发布 Agent 快照、build 与 cron profile；首版非交互 | 产品约束、安全加固 | 缓存命中不保证 Mate 数据库最新；真实 ASK、自定义问题和审核必须由 Host 结束本根，不能只移除工具名或默认批准。代价是需要人工决定的任务不适用；参数校验错误仍可由模型修正，不自动重放 |
| 仅支持 Spring 六字段 Cron，名称最长 256；Cron 默认上海时区 | 产品约束（范围与方言选择） | 采用 Claude 的名称上限与仅 Cron 范围，减少单次耗尽、间隔起点及其更新规则；代价是不能表达未来指定时刻单次执行或任意起点固定间隔。复用已有 spring-context；旧 Cron At/Every 的调用者仍需迁移核验，不因新 HTTP 收敛而直接删实现 |

Mate 负责可信接口定义、授权和凭据来源的决定已明确；[配套接口](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md)仍是待实现草案，生产公司服务身份与授权接线未核验。Claw 不保存凭据引用或秘密，定时运行统一使用 Mate 配置的同一个账号取 access-token，普通 Session 的本次 Header 规则保持；不能据此推导已有长期凭据、完整租户隔离或固定 Agent 历史版本。

上述新增调度能力为**待实现**。实施与验收集中于[M10 主设计](../08-CampusClaw定时任务/README.md)，重点包括多实例重复触发、受理事务故障、暂停/删除竞争、未知不重放、忙跳过、时区/DST、新 Session 关联及 ASK/自定义提问终止；本条没有运行产品或 GaussDB 测试。现有代码与目标增量分别见[M10 源码证据](../08-CampusClaw定时任务/source-evidence.md)，不以主设计完成代替实现验收。

### 执行策略与 coding-agent 合并（2026-10-05 工程核验）

这次增量只重核 Java 默认 `main@553dcd5e2ff682f9684810a043b442b37a02e54a` 和 Mate 示例默认 `main@4b957a3a846659f5b7569c9d6133abc070cd2e3c`，与各自前次 SHA 相同；完整路径、符号与范围见[M10 工程证据](../08-CampusClaw定时任务/source-evidence.md#schedule-engineering-evidence)。Claude 等外部基线保留前述历史日期，不以本次工程设计冒充重新核验的上游事实。

| CampusClaw 取舍 | 分类、收益与代价 | 已观察差距 |
|---|---|---|
| Mate 提供可信接口、配置时授权与统一账号 access-token | 架构变更、安全加固；避免持久化浏览器登录凭据或由模型选择秘密，代价是新增内部授权/凭据接线；服务间身份与业务凭据分开 | Mate 示例已有 Agent 目录/runtime Controller，未观察凭据或 `/runtime/tools` 服务端；Claw 客户端已有地址不证明 Mate 已实现它们，生产工程未核验 |
| 首版仅文本、无需人工交互 | 产品约束；无需持久等待/跨进程交互恢复，代价是需确认或附件的作业不适用；意外 ASK、提问、审核结束本根，不默认批准 | Cron profile 已不含 AskUserQuestion/ExitPlanMode，但权限 ASK、自定义问题和普通工具错误仍需 Host 专门处理，不能仅靠工具清单或 isError |
| 停机不补跑、忙跳过、失败故障不重跑 | 产品约束、安全加固；避免积压和副作用重放，代价是可能漏执行、未知结果持续占用；首版不自动暂停（D12），代价是 Agent 不可用时失败 Run 持续累积、需人工暂停 | 旧 Cron 的本地 timer、失败退避、3次失败禁用和2小时 running 清理不能兑现该目标，数据库扫描、原子受理和对账待实现 |
| 定时代码合并 coding-agent，保留设计职责边界 | 架构变更；共用 Runtime 与同库受理，减少独立 Maven 制品，代价是宿主职责增多；管理/受理和 Dispatcher 分离以避免 Registry 构造环 | 旧 cron 独立模块及15个生产类/7个测试、两处工具 Schema、POM、同步脚本、CODEOWNERS 均需迁移；不新增外部依赖，不把无消费者 JobRunr 占位当成现有运行库 |

精确执行、故障与上线初值见[定时任务受理流程](../08-CampusClaw定时任务/README.md#normal-acceptance)，Mate 路径和字段见[内部契约草案](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md)。模块合并、同库受理与凭据链均待实现；本次没有运行产品、GaussDB 或多实例测试，也不据部署默认数值宣称容量。

### 4. 源码与官方契约证据

| 基线 | 本条核验提交或官方日期 | 仓库相对路径、关键符号与证据范围 |
|---|---|---|
| pi | `main@95fbc04997eaee961eb673fa7923e9220609ebd5`，2026-09-22 | [`packages/agent/src/harness/pico3/scheduler.ts`](https://github.com/badlogic/pi-mono/blob/95fbc04997eaee961eb673fa7923e9220609ebd5/packages/agent/src/harness/pico3/scheduler.ts#L84-L197) 的 `Scheduler#resume/drive/drain/reserveEligible`；[`packages/agent/src/harness/pico3/kinds/job.ts`](https://github.com/badlogic/pi-mono/blob/95fbc04997eaee961eb673fa7923e9220609ebd5/packages/agent/src/harness/pico3/kinds/job.ts#L4-L187) 的 `JobInput`、`initial`、`waiting`、`poll`；[`packages/agent/docs/pico-v3.md`](https://github.com/badlogic/pi-mono/blob/95fbc04997eaee961eb673fa7923e9220609ebd5/packages/agent/docs/pico-v3.md#L964-L1020) 的 timing/permit/drive 约束。该历史条目未核验 package export，不能以讨论稿标签否定实验源码存在；产品入口和实验能力须分别核验。 |
| Codex harness | `main@a1f40f3f1326eff7c81b860a4f4e27c1be186e10`，2026-09-22 | [`codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`](https://github.com/openai/codex/blob/a1f40f3f1326eff7c81b860a4f4e27c1be186e10/codex-rs/app-server-protocol/src/protocol/v2/plugin.rs#L773-L822) 的 `ScheduledTaskSummary/ScheduledTaskSchedule` 仅为 PluginDetail 元数据；[`codex-rs/core/src/session/turn_input.rs`](https://github.com/openai/codex/blob/a1f40f3f1326eff7c81b860a4f4e27c1be186e10/codex-rs/core/src/session/turn_input.rs#L131-L176) 的 `TurnStartOptions.turn_trigger` 只记录触发来源；[`codex-rs/state/migrations/0042_drop_agent_jobs.sql`](https://github.com/openai/codex/blob/a1f40f3f1326eff7c81b860a4f4e27c1be186e10/codex-rs/state/migrations/0042_drop_agent_jobs.sql) 删除旧批处理 Agent Job 表。Codex Scheduled Tasks 的宿主契约核对[官方文档](https://learn.chatgpt.com/docs/automations)，日期 2026-09-22；服务端实现未公开。 |
| OpenCode | `dev@fe3f3a41f79ad292cc3c7c629567385a20ec5130`，2026-09-22 | [`packages/core/src/background-job.ts`](https://github.com/anomalyco/opencode/blob/fe3f3a41f79ad292cc3c7c629567385a20ec5130/packages/core/src/background-job.ts#L113-L188) 明确 registry 是 process-local、非 durable；`BackgroundJob.start/extend/wait/cancel` 在同一进程作用域内工作；[`packages/opencode/src/background/job.ts`](https://github.com/anomalyco/opencode/blob/fe3f3a41f79ad292cc3c7c629567385a20ec5130/packages/opencode/src/background/job.ts#L17-L35) 按 InstanceState 装配。已检查 `packages/opencode/src`、`packages/core/src`、`packages/protocol/src`，未发现 Cron/Schedule 模块。官方 GitHub 调度入口见[OpenCode GitHub 文档](https://dev.opencode.ai/docs/github)，核对日期 2026-09-22。 |
| DeepSeek Harness | `master@c36a83ff6bb95e3f82cf79f9be7c724270a8aa61`，`dsh-0.1.7-alpha.1`，2026-09-22 | [`packages/schedule/schedule/src/types.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/c36a83ff6bb95e3f82cf79f9be7c724270a8aa61/packages/schedule/schedule/src/types.ts#L40-L120) 的 durable record/dispatch/view；[`src/runtime.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/c36a83ff6bb95e3f82cf79f9be7c724270a8aa61/packages/schedule/schedule/src/runtime.ts#L83-L338) 的 `ScheduleRuntime#driveOnce`；[`src/index.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/c36a83ff6bb95e3f82cf79f9be7c724270a8aa61/packages/schedule/schedule/src/index.ts#L41-L147) 的插件装配与 root Agent 生命周期；[`packages/schedule/schedule/README.md`](https://github.com/deepseek-ai/deepseek-harness/blob/c36a83ff6bb95e3f82cf79f9be7c724270a8aa61/packages/schedule/schedule/README.md#L76-L125) 的事件权威、flush barrier、idle delivery 和 latest-only catch-up。 |
| Claude Managed Agents | 官方文档核对日期由 2026-09-22 更新为 2026-09-29；Beta，暂无服务端源码 commit | [Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments) 的 Cron、timezone、jitter、Deployment Run、pause/unpause、failure 和 manual run；[Create Deployment API](https://platform.claude.com/docs/en/api/http/beta/deployments/create) 的 `BetaManagedAgentsScheduleParams`。更新 jitter 窗口、Run 创建结果含义及主 Agent 归档/删除的无 Run 例外；只证明公开托管契约，不推断内部落库顺序、scheduler、锁或数据库。 |
| CampusClaw Java | 2026-09-29 确认默认分支并 fetch `main@553dcd5e2ff682f9684810a043b442b37a02e54a` | 本次新增 M10 的 Cron 时间解析、存储/调度、Host 装配及 Runtime 受理源码核验；完整仓库相对路径、关键符号、旧新范围和实现差距统一见[M10 源码证据](../08-CampusClaw定时任务/source-evidence.md)，不将该 SHA 批量替换其他模块的历史证据。 |

**讲解要点。** 园区定时作业采用 Claude 的平台调度分层，每次创建独立 Session；每次触发既看是否受理，也看对应根执行是否结束。CampusClaw 用 GaussDB 与既有 Runtime 准入约束重复执行，保留发布快照和无人交互规则，因此要承担事务集成与结果对账的成本。Agent 定义保持任务绑定，Mate 提供可信执行身份与凭据，定时首版只接受无需交互的文本工作，新增能力待实现；其余基线只提供各自职责层次的历史参照。

### Mate 与 Claw 的资源归属边界（2026-10-10）

本项是 CampusClaw 产品约束与架构修正，不新增外部 Agent 比较事实：用户、组织、资源归属与权限由 Mate 维护，Claw 只保存调度和运行数据。收益是归属变更和撤权只有一个权威；代价是 Mate 必须完成会话独立登记、列表授权集合以及跨服务失败对账，登记确认前不得启动。

本次重新 fetch PR #332 `e9d31e8888a81b7fe95071e705482bb16fa10476`，base/merge-base 为 `769e86592285f4a25b0febaf551eddea6bc7212c`。已观察其 Session/Schedule/Run 身份列、Runtime 主体捕获及本地 scope 权限链路；这些实现须按[数据库职责边界](../../03-数据与存储/Claw数据库设计.md#mate-ownership)撤销，具体路径/符号见[M10 职责核验](../08-CampusClaw定时任务/source-evidence.md#mate-boundary-review)。保留实例 owner、租约、资源关系和不透明授权查询引用；不把“Claw 不维护用户”解释为免除服务认证或运行状态校验。Mate 服务端未核验，接线待实现；其他基线维持各自历史日期和成熟度。

### A14 / M07 · 触发方式的页面投影

| 维度 | 结论 |
|---|---|
| 参照与范围 | 2026-10-08本机Chrome实际观察Claude创建Deployment，并重读官方Scheduled deployments；仍为Beta，无服务端commit。Console有Manual/Schedule、频率与时区、Cron编辑和未来五次时间；详细证据见[M07专项](../../07-前端设计/source-evidence.md#schedule-console-evidence)。 |
| 目标与差异 | [M07场景09](../../07-前端设计/场景/09-配置与管理定时任务/README.md)采用同页分区和显式模式，Agent在基本信息可见，表单不含凭据（由Mate按Agent绑定决定）；Manual派生自schedule:null，Schedule派生自Cron，status和Run来源保持独立；六字段、默认上海、没有Environment/Budget/Vault及保存后权威时间继续遵守M10。 |
| 分类、理由与代价 | 产品交互约束：让触发方式及执行身份显式可见，避免仅手动被误读为paused；复用已有API而不增加配置枚举。保存前只显示规则与未保存提示，减少独立解析权威，代价是保存后才取得服务端时间且有效计划随保存生效。 |
| 实现状态 | 旧功能提交2b93cbea已有自动/仅手动及预设，仍依赖preview；最新默认main769e8659的App.vue/组件树范围无该工作区。新增页面目标待实现；不以旧分支、原型或历史430项测试证明部署。其他后端历史范围不升级。 |
| 验收 | 显式null清除旧计划、暂停状态保持、复杂Cron无损、修改规则时旧时间失效、未知写不重放、高低保真保留草稿和窄屏可操作；权威契约与原型职责分别由M10/M07维护，现有全局图依赖关系无变化。 |

<a id="a15"></a>

## 6.12 A15 · 三入口统一历史与独立子会话

| 维度 | 结论 |
|---|---|
| 模块与主设计 | M01/M03/M04/M06/M10；[统一执行历史](../01-CampusClaw多Agent运行时/unified-event-persistence.md)唯一维护受理、父子关系、完整记录、逐工具提交和失败边界，复用其完整目标类图 |
| 问题 | 定时巡检调用子诊断 Agent，如何让主/子过程均可追溯，同时避免为统计再造执行历史？ |
| 最新基线 | 2026-10-10 隔离 fetch：pi main 42a3497d、Codex main 322bbf4d、OpenCode dev 055d95bb、Java main 769e8659；完整 SHA、旧新范围及路径符号见[证据](../01-CampusClaw多Agent运行时/unified-event-persistence-evidence.md) |
| pi | 普通示例 --no-session，消息放回工具 details；experimental durable 另建 conversation。不能将两者合并成“Subagent 不留历史” |
| Codex / OpenCode | 非 ephemeral child thread 的独立 rollout；Task 的子 Session 与消息/Part 持久化。父侧摘要与子完整历史并不冲突；不借此推断所有 delta 都持久化 |
| CampusClaw 已观察 | Runtime Coordinator 有数据库 Projector；Cron/Subagent 直接 Factory+prompt，缺共同持久受理；TurnEnd 才写结果有故障窗口 |
| CampusClaw 目标 | Cron 每 Run、Subagent 每调用均独立 Session；共用受理、Coordinator、逐工具提交；父只保存摘要。Entry/公共投影/Skill 累计同事务，模型推进等待提交 |
| 差异类别 | 架构变更：统一持久宿主和结果提交端口；产品约束：子历史独立授权、取消定向、Cron 非交互和未知不重放；安全加固：内部恢复记录与公共安全投影分开 |
| 理由与代价 | 完整排障和复用统计来源；增加子会话存储、关联/保留协调及提交延迟，仍无法使外部副作用和本库 exactly-once |
| 状态与验收 | 待实现；按 U1–U5 验收三入口、防重/取消/清理竞争、失败窗口和数据库故障，不宣称已经支持浏览器子历史展开 |

**设计表达。** Subagent 是独立的持久会话，父调用保存关系与摘要。Cron 只改变发起方式，历史写入不随入口另造实现；Skill 次数从这些已提交结果派生。

<a id="a16"></a>

## 6.13 A16 · 按 Agent 查看用户事件与轮次

| 维度 | 结论 |
|---|---|
| 模块与主设计 | M01/M06；[Agent 用户事件与轮次查询](../01-CampusClaw多Agent运行时/agent-user-events-design.md)唯一维护接口、轮次解析、游标与失败边界 |
| 问题 | 开发运维人员在 Trace 中要查看某个 Agent 一段时间内收到的用户请求，并展开其中一轮的执行轨迹，Claw 应提供怎样的读取边界？ |
| 最新基线 | 2026-10-12 隔离 fetch：Codex main 42705224、OpenCode dev 4d9678a7、pi main a9b08151、DeepSeek Harness master d7432673（开发者预览）；Claude Managed Agents 公开 Beta 文档同日重读；Java main 769e8659。完整 SHA、路径与符号见主设计 §8.1、§8.2 |
| Claude Managed Agents | 事件按会话列出，支持 created_at 区间、types[] 与不透明 page；跨会话只能按 agent_id 列会话，没有跨会话事件列表；轮次以 session.status_idle 结束，无轮次 ID |
| Codex | Turn 有显式 ID 与状态，`thread/items/list` 用 thread_id + turn_id 取整轮条目；没有跨线程条目查询，也没有从条目 ID 反查轮次 |
| OpenCode / pi / DeepSeek | OpenCode 以 idle 标记切分轮次、消息按会话列出；pi 的 turn 只是一次模型回复加工具结果；DeepSeek 有整数 turn 与内部全文检索。均无按 Agent 跨会话的用户事件查询 |
| CampusClaw 已观察 | 事件只能按会话读取；根执行与结果段关联已经把一条用户消息及其续跑、输出和终态绑定在一起；停止请求只经 targetEventId 关联；执行内自动压缩未关联结果段 |
| CampusClaw 目标 | 按 Agent 与时间返回五种 user.* 事件；以 sessionId + eventId 定位并复用根执行作为轮次；两个接口都用由公开字段组成的透明 keyset 游标；事件表冗余 agent_id 并建部分索引 |
| 差异类别 | 产品约束：跨会话聚合、透明游标、权限由 Mate 判断；架构变更：复用根执行作为轮次身份、事件表冗余 agent_id |
| 理由与代价 | 复用已有的根执行记录，不新增轮次表；透明游标可读、可构造且不受深页与删除影响。代价是游标字段成为公开契约、需校验调用方构造的游标、开放时间窗口可能漏读晚提交事件，以及多一列与一个索引的写入开销 |
| 状态与验收 | 待实现；按主设计 §6.3 验收游标、轮次解析、删除隔离与执行计划 |

**设计表达。** 没有基线直接提供这两个接口。CampusClaw 借 Claude Managed Agents 的事件类型与时间过滤、Codex 的显式轮次分组，用已有根执行表达“一轮”，跨会话聚合与权限分工是 Trace 场景的产品约束。

## 7. 源码证据与更新边界

P01/P02 使用 pi 固定 commit `5cd93f688aaab89dbb6dfa4aca535f21796ae185`；
J01～J05 使用 Java commit `f61906b9136246ca60f333704b6fc92b5420d0ec`。
路径均相对各自仓库根目录，链接固定到对应 commit。

| 编号 | 仓库相对路径 | 已分析符号与证明范围 |
|---|---|---|
| P01 | [packages/agent/src/agent-loop.ts](https://github.com/badlogic/pi-mono/blob/5cd93f688aaab89dbb6dfa4aca535f21796ae185/packages/agent/src/agent-loop.ts) | `runLoop`、`streamAssistantResponse`：控制消息读取时点、模型消息转换与内部事件发出 |
| P02 | [packages/agent/src/types.ts](https://github.com/badlogic/pi-mono/blob/5cd93f688aaab89dbb6dfa4aca535f21796ae185/packages/agent/src/types.ts) | `AgentLoopConfig`、`AgentEvent`：内核扩展契约与生命周期类型 |
| J01 | [modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java](https://github.com/superheromeZzh/pi-mono-java/blob/f61906b9136246ca60f333704b6fc92b5420d0ec/modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java#L112) | `runTurns`、`runToolPhase`、`invokeModel`、`drainNextControlMessages`：Loop、工具委托、事件转换与队列读取 |
| J02 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java](https://github.com/superheromeZzh/pi-mono-java/blob/f61906b9136246ca60f333704b6fc92b5420d0ec/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java#L63) | `submit/list`：POST SSE 与 GET 历史入口、响应关闭时调用 detach |
| J03 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventService.java](https://github.com/superheromeZzh/pi-mono-java/blob/f61906b9136246ca60f333704b6fc92b5420d0ec/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventService.java#L53) | `submit`：三类用户事件分派；不证明被调用服务的全部事务与取消语义 |
| J04 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeMessageEventService.java](https://github.com/superheromeZzh/pi-mono-java/blob/f61906b9136246ca60f333704b6fc92b5420d0ec/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeMessageEventService.java#L173) | `requireIdleSession`、`accept`、`startAccepted`：idle 预检查、持久化接受调用及回执先于启动；不证明数据库事务实现 |
| J05 | [modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventStream.java](https://github.com/superheromeZzh/pi-mono-java/blob/f61906b9136246ca60f333704b6fc92b5420d0ec/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventStream.java#L174) | `attach`、`emit`、`emitBestEffort`、`detachInternal`：单订阅者、有界缓冲及输出解绑 |
| J06 | Mate `9dd5d85e2ed6561ad654b11f817ef572cc8bac7c` · `src/main/java/com/huawei/hicampus/mate/agentdefinition/service/impl/AgentDefinitionServiceImpl.java` | `getRuntimeAgent` 顺序读取四类绑定；更正原图的并行表达，未据此推断跨查询快照一致性；详见[元数据证据](../../03-数据与存储/02-Agent元数据GaussDB/README.md#2-来源证据与设计边界) |

请求级 SSE 主设计的旧实现核对点为 `918005ee8ccc88d179fc31a0de17a92b4a01383b`。
在本文的新核对点，J02/J03/J04 已出现新的请求 VO、三事件分派和回执启动顺序；
因此[旧基线证据](../01-CampusClaw多Agent运行时/source-evidence.md#52-post-与流生命周期)中的“三输入联合请求和完整首帧还需改造”只适用于原基线，不能直接用于判断新提交。
这不改变目标方案，也不自动关闭该模块其余实现差距；完整差距表的复核仍需扩大到持久化、控制和集成测试。

## 8. 条目格式与维护检查

新增对比条目使用稳定编号和锚点，并具备以下信息：

| 字段 | 维护要求 |
|---|---|
| 模块与主设计 | 模块编号、权威文档及章节；跨模块条目标明各自责任 |
| 架构问题 | 用一个具体问题固定比较范围，明确是内核、Provider、API、客户端还是存储 |
| 基线证据 | 固定 commit、仓库相对路径、符号或行号；托管产品用官方链接、核对日期与成熟度 |
| 基线行为 | 只陈述已经核验的行为，不能把资料入口写成实现证据 |
| CampusClaw 目标 | 引用模块当前有效方案，说明继承与差异，不重复完整契约 |
| CampusClaw 实现 | 单独列出源码观察、基线、测试证据及未覆盖范围 |
| 差异分类 | 有意差异分为产品约束、安全加固、架构变更；意图不明的实现差距保留待核验 |
| 理由与代价 | 具体触发场景、所解问题、收益、额外复杂度与不适用条件；不用“更先进”等无证据评价 |
| 备选边界 | 说明为何不直接沿用基线，以及什么条件变化时需要重新评估 |
| 验收与讲解 | 指向模块实施验收；简短讲解覆盖问题、参考、差异、原因、代价与实现进度 |

设计状态和实现状态分别记录：

- **设计状态**：待决策、已确认目标、非本期范围。提议新增但没有对应实现的方案标记 待实现。
- **实现状态**：未核验、已核验且无对应实现、局部已核验、已核验并完成所列验收。
  明确源码范围内确认尚无实现时标记“待实现”；未取得或尚未重核对源码证据时标记“未核验”，两者不能混用。测试通过情况单独记录。

每次模块设计变更，检查相关条目的问题、目标、差异分类、代价和验收是否变化；
每次实现进度更新，先读新源码并记录新旧基线，不能只改状态文字。
基线升级只更新受影响结论，正文保留当前有效比较；历史变化通过 Git 和一句话版本记录追溯。
对比图如确有必要，遵守仓库 PlantUML 规则；已有目标类图通过主设计复用，不在本文复制另一套图。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.103.0 | 2026-10-16 | M05/M07 选项型命令的候选与显示名改由 Mate 命令选项接口提供，前端按 argumentType 统一处理；hints 改为 argumentHint 占位字符串，可选值改由 Runtime 会话查询提供，与 pi 对齐。 |
| 1.102.0 | 2026-10-16 | M05 CampusClaw 的 hints 改为固定参数值列表（thinking on/off、mode plan/build），与 OpenCode 的占位提示 hints 区分；清单增加可选 sessionId 决定范围。 |
| 1.101.0 | 2026-10-16 | A14 同步 M10：对话中由 Cron 工具创建的任务关联原会话运行，接口配置的任务仍每次新建 Session。 |
| 1.100.0 | 2026-10-16 | M05 命令清单改为按 Agent 查询，登记 OpenCode/Codex/pi 的清单作用域基线；其余比较不升级。 |
| 1.99.0 | 2026-10-15 | A14 同步 M10 D12：定时任务首版不自动暂停，Agent 启停用另开设计。 |
| 1.98.0 | 2026-10-14 | 合入 main：A05 增加 plan 模式拒绝 TodoUpdate 的执行前门禁及 Codex 对照（main 原记为 1.92.0）。 |
| 1.97.0 | 2026-10-14 | 合入 main：A08 增加交互工具同批位置对比，提问与用户确认须为末位调用、计划提交须单独调用（main 原记为 1.91.0）。 |
| 1.96.0 | 2026-10-14 | A14 补失败自动暂停结论：按错误类型区分，参考 Claude。 |
| 1.95.0 | 2026-10-14 | M10 Run 改为与根执行终态同事务结束，取代内部对账。 |
| 1.94.0 | 2026-10-13 | 清理定时执行“按 Agent 绑定解析凭据”的旧表述，改为统一账号。 |
| 1.93.0 | 2026-10-13 | M10 定时执行改为统一账号 access-token，更新凭据取舍与代价。 |
| 1.92.0 | 2026-10-13 | M10 去掉内部配置代次与扫描代次说法，与定时任务撤销 revision 和扫描协调表一致。 |
| 1.91.0 | 2026-10-13 | M10 定时任务移除 credentialIds，凭据改由 Mate 按 Agent 绑定在运行时决定。 |
| 1.90.1 | 2026-10-12 | A16 的问题改为 Trace 场景。 |
| 1.90.0 | 2026-10-12 | 新增 A16，对比按 Agent 跨会话查询用户事件与按事件读取轮次的基线做法。 |
| 1.89.0 | 2026-10-10 | A14 明确 Mate 独立维护资源归属和权限，记录 PR #332 的身份职责偏差及交接代价。 |
| 1.88.0 | 2026-10-10 | 关联 Claw 全库数据库设计，按表区分主线、PR 和待实现增量。 |
| 1.87.0 | 2026-10-10 | M10 引用独立数据库设计并登记 PR #332 的表、受理和启动控制实现范围。 |
| 1.86.0 | 2026-10-10 | 对比最新子 Agent 持久化基线，统一三入口历史并由结果同事务维护 Skill 累计。 |
| 1.85.0 | 2026-10-10 | A09 按 Skill 成功调用计数，补充公共观察、有界写入与 #335 对比及最新 pi 事件证据。 |
| 1.84.0 | 2026-10-09 | 依据最新 pi 与 DeepSeek 长度核验取消计划字符上限，区分正文规则和传输容量。 |
| 1.83.0 | 2026-10-09 | 以最新 pi AI 部分 JSON 为基线，说明通用预览、独立完整解析与计划审核的边界和兼容代价。 |
| 1.82.0 | 2026-10-08 | 补充Claude Console触发方式与M07页面投影的理由、代价和源码范围。 |
| 1.81.1 | 2026-10-08 | A11用户确认元数据说明统一使用 Tool。 |
| 1.81.0 | 2026-10-08 | A11增加用户确认工具的元数据分派取舍及固定名称实现差距。 |
| 1.80.0 | 2026-10-08 | A14采用保存后的计划时间摘要，记录无独立预览的接口范围及交互代价。 |
| 1.79.0 | 2026-10-05 | A14同步非交互、不补跑、不重跑与独立Session生命周期，补充Mate凭据权威和coding-agent合并取舍。 |
| 1.78.0 | 2026-10-05 | A14采用删除Schedule及关联Run、保留Session的生命周期，明确读取影响与在途取消待定。 |
| 1.77.0 | 2026-10-05 | A14比较OpenClaw保留运行历史与DSH删除投递历史，明确会话保留及在途取消差异。 |
| 1.76.0 | 2026-10-05 | A14区分Run独立查询、页码取舍与配置删除后的历史生命周期，不把归档契约推定为保留保证。 |
| 1.75.0 | 2026-10-05 | A14 增加三个运行管理动作对照，区分Run受理结果、配置启停与既有Cron的同步执行及状态竞争。 |
| 1.74.0 | 2026-10-04 | A14 对齐删除成功200完整资源回执，区分 Claude 返回形状与 Claw 删除生命周期。 |
| 1.73.0 | 2026-10-04 | A14 明确直接删除的生命周期选择及配置不可回读的代价，区分已确认范围与删除响应和历史运行候选。 |
| 1.72.0 | 2026-10-04 | A14 比较配置归档与删除的可读取性和历史成本，核实 Claude 公开范围与现有 Cron 删除差距。 |
| 1.71.0 | 2026-10-04 | A04/A14 统一无客户端条件及请求键协议，明确数据库合并更新、重试代价和现有 Session 迁移差距。 |
| 1.70.0 | 2026-10-04 | A14 比较部分更新、凭据清空与 Agent 版本语义，并明确条件更新和幂等回执的成本。 |
| 1.69.0 | 2026-10-04 | A14 补充资源类型与暂停原因的基线对应、状态归属及实现差距。 |
| 1.68.0 | 2026-10-04 | A14 对齐完整配置读取，补充分页取舍、读取授权和独立 Run 观察的证据边界。 |
| 1.67.0 | 2026-10-04 | A14 明确 credentialIds 直接凭据引用，相比 Claude 不增加 Vault 集合层。 |
| 1.66.0 | 2026-10-04 | A14 明确 Claw 支持凭据绑定，区分直接凭据与 Claude Vault 集合的引用层级。 |
| 1.65.0 | 2026-10-04 | A14 对齐创建响应时间摘要、小写状态及 metadata，并说明凭据引用和可信注入的收益与缺口。 |
| 1.64.0 | 2026-10-04 | A14 固定每次新建 Session，说明 Agent 定义复用与已有会话能力的范围取舍，并链接创建响应对齐。 |
| 1.63.0 | 2026-10-04 | A14 收敛名称与 Cron 范围，补充会话目标及文件引用和上传的能力差异。 |
| 1.62.0 | 2026-10-02 | Claw 时间统一秒级，区分 Claude 公开示例、现有毫秒实现与产品目标。 |
| 1.61.0 | 2026-09-30 | A14 同步调度绝对时刻响应采用 UTC 并固定三位毫秒的产品约束。 |
| 1.60.0 | 2026-09-30 | A14 明确 Cron 默认上海的产品取舍及 at/every 不另设时区的边界。 |
| 1.59.0 | 2026-09-30 | A14 增加时区字段与默认来源对比，同步固定起点和整数秒的已定契约。 |
| 1.58.0 | 2026-09-30 | A14 明确 Claw 创建 every 时缺省先等待一个完整间隔，精确取时与更新仍待细化。 |
| 1.57.0 | 2026-09-30 | A14 明确 Claw 的 startAt 可选，省略后的首次时间保持待定。 |
| 1.56.0 | 2026-09-30 | A14 增加五基线首次触发专项对比，区分固定时间表、固定延迟和托管调度未公开细节，并校正 pi 时间单位。 |
| 1.55.0 | 2026-09-30 | A14 明确 every 使用固定时间表及相对旧完成时间基准的迁移差异。 |
| 1.54.0 | 2026-09-30 | A14 明确 at/every 是已定产品范围，间隔基准和字段细节仍待确定，并统一两种会话目标的交付边界。 |
| 1.53.0 | 2026-09-30 | A14 明确 Spring 六字段与动态调度边界，并同步单条用户消息和可选计划的创建语义。 |
| 1.52.0 | 2026-09-29 | 按 Claw 五接口说明 Claude 采纳项，明确版本固定缺口、Cron 成本及已有 Session 扩展。 |
| 1.51.0 | 2026-09-29 | 增加 Claude 配置资源与现有 Mate/Claw 前后端边界的映射，运行策略保留待细化状态。 |
| 1.50.0 | 2026-09-29 | M10 以 Claude 为主基线明确独立会话优先、两阶段调度及受理与执行结果分离，并更新调度公开契约和 Java 证据范围。 |
| 1.49.0 | 2026-09-28 | 采用完整 plan 参数与计划专用预览，更新审核基线并区分已实现 marker 与待实现参数增量。 |
| 1.48.0 | 2026-09-22 | 比较 mode 命令与 pi 配置命令、OpenCode primary Agent 的模式边界。 |
| 1.47.0 | 2026-09-22 | 比较 pi/OpenCode 的命令发现与执行边界，明确 type/hints 的产品约束和迁移差距。 |
| 1.46.0 | 2026-09-22 | A11 收敛为唯一工具名精确披露，保留调用一致性约束并将加载和同步机制留给后续设计。 |
| 1.45.0 | 2026-09-22 | A11 采用固定 SearchTools 返回定义数据，并与 CallTool 共用不可变 Session 定义快照。 |
| 1.44.1 | 2026-09-22 | M05 按 53eff85c 更新命令实现状态，保留结构、版本快照、统计与公共桥接差距。 |
| 1.44.0 | 2026-09-22 | 增加 A14 调度基线对比，区分托管 Cron、Session 内提醒、持久化 Task 和外部 Workflow。 |
| 1.43.0 | 2026-09-22 | 对比 pi 与 DSH 的校验顺序，固定 CallTool 确认前准备、确认后执行同一快照。 |
| 1.42.0 | 2026-09-22 | 对比 pi 错误结果循环与 CampusClaw 首次参数失败的定义反馈及可恢复展示。 |
| 1.41.0 | 2026-09-22 | 增加 Redis 草稿恢复与 OpenCode live/durable 事件边界的 A13 对比。 |
| 1.40.0 | 2026-09-22 | 增加 pi 分支索引与 CampusClaw 单条追加时间线的范围、代价和实现差距。 |
| 1.39.1 | 2026-09-21 | A11 采用“关联的业务工具”表述配置关系，架构与权限结论不变。 |
| 1.39.0 | 2026-09-20 | 增加 Agent 远端代理与 Skill 工具按需披露的 A11 对比，明确 CallTool 及独立同步边界。 |
| 1.38.0 | 2026-09-19 | 计划标记由后端解析，公共事件采用 delta/completed 并保留审核事务边界。 |
| 1.37.0 | 2026-09-19 | A06 对比 Mate 输出权威与按执行查询窗口，记录生命周期、故障代价及 pi 摘要差异。 |
| 1.35.0 | 2026-09-19 | A06 增加 Mate 逐模型能力查询与快照，比较可选输出上限与 pi 默认补值的差异。 |
| 1.34.0 | 2026-09-19 | 对照正文流与参数承载两类计划机制，明确同响应绑定及前端合并的目标差异。 |
| 1.33.0 | 2026-09-19 | 区分 Mate 凭据判断、工具上下文可用性与 DEV 工作台刷新门禁。 |
| 1.32.0 | 2026-09-19 | 工具展示名复用本地绑定元数据，与执行时 ID 解析分离，并更新 pi 事件字段证据。 |
| 1.31.0 | 2026-09-19 | M07 开发写动作提交前自动获取 Token，明确已实现配置基础与待实现门禁及运行期限制。 |
| 1.30.1 | 2026-09-18 | 登记三项退役工具的开发分支实现、回归结果和公司编译限制。 |
| 1.30.0 | 2026-09-18 | 增加 Bash/Edit/Write 完全删除与公共消费者保留的 A10 对比。 |
| 1.29.0 | 2026-09-18 | 同步交互工具、模式提示词和提问展示的主线实现状态，并统一待实现标记。 |
| 1.28.0 | 2026-09-18 | A09 查询采用批量 POST，排名和趋势暂缓，上游证据范围不变。 |
| 1.27.0 | 2026-09-17 | 对比 pi/Claude 的名称边界，统一框架 label 与业务 displayName 的事件快照设计。 |
| 1.26.0 | 2026-09-17 | 工具展示优先 displayName，登记元数据、事件传递和历史快照的目标差距。 |
| 1.25.0 | 2026-09-17 | M07 增加具体工具标题的产品约束与局部实现差距，外部基线对比结论不变。 |
| 1.24.2 | 2026-09-17 | M02 统一命名为 Model，架构比较结论与源码基线不变。 |
| 1.24.1 | 2026-09-17 | 更新模型模块的文档与图入口，架构比较结论和源码基线不变。 |
| 1.24.0 | 2026-09-17 | 对比 pi 最新模型目录与业务 Agent 设置唯一权威，登记旧全局目录及日志删除差距。 |
| 1.23.0 | 2026-09-17 | 对比 Agent 自定义与模式覆盖机制，明确业务同名文件回退和目录发布一致性。 |
| 1.22.1 | 2026-09-17 | 提示词角色采用 Main Agent/Subagent，基线分工与架构结论保持不变。 |
| 1.22.0 | 2026-09-17 | 按最新上游提示词证据将模式资源收敛为 PLAN.md / BUILD.md，并明确基础 SYSTEM 与工具描述的职责。 |
| 1.21.0 | 2026-09-17 | 明确三类决定取消消费属于 CampusClaw 持久化架构变更，并登记终态专项源码与验收边界。 |
| 1.20.0 | 2026-09-16 | 对比 Codex 使用信号与 CampusClaw 根去重、独立事务和失败隔离。 |
| 1.19.0 | 2026-09-16 | 对比 Build/Plan 逐题交互与模型工具结果，登记开发设置持久化及浮层展示差距。 |
| 1.18.0 | 2026-09-15 | 同步 Claw 前端实现与交互验收范围，分离 Mate 公共接入目标。 |
| 1.17.0 | 2026-09-15 | 对比 Codex 完整计数链与 Runtime 来源事实、三表事务和入口覆盖。 |
| 1.16.1 | 2026-09-15 | 同步结构化问答的实现证据、独立验证和外部接入边界。 |
| 1.16.0 | 2026-09-15 | 更新计划前端源码范围，比较问题卡与 Slash 等待交互及共享恢复边界。 |
| 1.15.0 | 2026-09-15 | 对比 Codex/OpenCode 的 Skill 调用观测，区分分析事件、计数器与统计权威。 |
| 1.14.0 | 2026-09-15 | 增加 Skill 加载汇总、采集职责与管理查询的架构取舍。 |
| 1.13.0 | 2026-09-15 | 对比工具式提问与权威事件，明确问题回答和原执行续跑的取舍。 |
| 1.12.0 | 2026-09-15 | 移除飞书渠道对比与待补证范围，M07 聚焦前端体验。 |
| 1.11.0 | 2026-09-15 | 对比 Codex 方案与进度交互，明确 CampusClaw 原执行审核续跑和前端接入边界。 |
| 1.10.0 | 2026-09-15 | 对比计划文件与正文载体，并采用后端显式任务更新事件。 |
| 1.9.0 | 2026-09-14 | 对比引用模块权威内容，登记公共分页待整合与渠道无回执恢复边界。 |
| 1.8.0 | 2026-09-14 | 区分 Agent 默认 mode 与 Session 当前模式，并记录目录发布的生效边界。 |
| 1.7.0 | 2026-09-14 | 补充 CampusMate 唯一内置 Provider 的裁剪取舍、身份切换、源码证据与依赖验收。 |
| 1.6.0 | 2026-09-14 | 明确规划与实施提示词分工，TODO 仅跟踪 build 实施且逐项更新。 |
| 1.5.0 | 2026-09-14 | 补充 TODO 复用 Claude 风格通用工具结果的架构取舍、源码差距和验收。 |
| 1.4.0 | 2026-09-14 | 计划审核沿用事件恢复与执行内校验，不扩充 Session 待审字段。 |
| 1.3.1 | 2026-09-14 | 明确 Claude 资源部分更新的采纳范围与前端单项调用的区别。 |
| 1.3.0 | 2026-09-14 | 补齐五基线配置接口对比，说明统一 Session POST 的事务与生效边界。 |
| 1.2.0 | 2026-09-14 | 明确 plan/build 由 Session 资源更新承载，复用既有配置服务并区分工作模式与执行状态。 |
| 1.1.0 | 2026-09-14 | 增加 DeepSeek 计划模式与 CampusClaw 稳定元数据、审核续跑的跨模块对比。 |
| 1.0.0 | 2026-09-14 | 建立按模块维护的基线对比、证据与状态格式，并补充 Loop 准入和两跳事件流的局部核验条目。 |
