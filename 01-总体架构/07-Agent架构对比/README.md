# CampusClaw 与 Agent 基线的架构对比

[返回总体架构](../README.md) · [模块索引](../../README.md#module-index)

| 属性 | 值 |
|---|---|
| 文档版本 | 1.46.0 |
| 更新日期 | 2026-09-22 |
| 文档职责 | 按模块解释架构取舍与实现差距，支撑设计讨论、架构答辩和面试 |
| 工具状态专项基线 | 2026-09-18 已 fetch Java 默认分支 main，核验 `8c5fda1dde51675859bc9c07e145dbe253656dea`；仅更新 A03/A05/A08 及 A07 提问展示子集，路径与符号见[§12](../06-CampusClaw计划模式/source-evidence.md#12-主线实现状态核验2026-09-18)，不升级外部基线或其他模块结论 |
| 退役工具专项基线 | A10 单独采用 Java `8c5fda1dde51675859bc9c07e145dbe253656dea` 与 pi main `e4ce7b449f4d91589c8760d6fbfa6eaaf82b05fe`；仅更新工具组合与删除边界，其他条目的历史证据不变 |
| 设计依据 | 当前各模块主设计；M02 采用 Model 主设计 2.10.0，具体入口见各条目 |
| CampusClaw 局部源码基线 | `pi-mono-java@f61906b9136246ca60f333704b6fc92b5420d0ec`；仅证明证据表所列文件与符号，不代表最新远端或全部模块 |
| 模型来源专项基线 | A06 于 2026-09-17 核验 pi 默认分支 `main` 的 `16235fd93521f9f96164f5891beea62e6bea5b18` 与 Java `main` 的 `21c3f59be033e7bdd5506a2d9d48baa2581bc3c7`；只升级模型配置、Provider 组合和业务 Agent 设置链结论 |
| 历史计划模式专项基线 | A03/A05 的提示词专项于 2026-09-17 更新至 Codex `b0659c53`、OpenCode `88c6c7ab`、DeepSeek `0d1f5000`、pi `e4c75a73`；业务覆盖再次确认四个上游 HEAD 不变，Java 装配/发布读取本地 `21c3f59b`，完整 SHA、路径及差距见[§11](../06-CampusClaw计划模式/source-evidence.md#11-业务-agent-模式提示词覆盖) |
| 前端专项基线 | A07：Java `1d08f98eb04f8ea6e01bcfbfd4008c1b638391c4` 的体验差距见[新核验](../../07-前端设计/source-evidence.md#experience-evidence)，前次验证见[实现证据](../../07-前端设计/source-evidence.md#current-implementation)；Codex 固定 `d58d0e58`，既有官方核对日期为 2026-09-15 |
| 历史提问专项基线 | A08：问答闭环验证为 Java 9f785bea3ffff8f6566cd1b2727285af46a2aead；新增交互核验为 Java 1d08f98e、Codex d58d0e58 与 OpenCode 849c2598，见[逐题交互证据 §9](../06-CampusClaw计划模式/source-evidence.md#9-buildplan-与逐题交互核验)；DeepSeek 0a53fb55、pi 5cd93f68、Claude 官方文档 2026-09-15 的原范围不变 |
| 工具发现专项基线 | A11：2026-09-22 fetch OpenCode `dev@fe3f3a41f79ad292cc3c7c629567385a20ec5130`、Codex `main@ac7634b9f73ec1bf96466be7a5869f0949d20b30`；沿用 DSH `master@c36a83ff6bb95e3f82cf79f9be7c724270a8aa61`。仅升级 Skill、固定搜索、延迟工具暴露与远端工具适配结论；默认分支快照不等于稳定发布，其他模块历史证据不变 |
| 参数恢复专项基线 | A11：2026-09-22 确认 pi `main@95fbc04997eaee961eb673fa7923e9220609ebd5`、DSH `master@c36a83ff6bb95e3f82cf79f9be7c724270a8aa61`；CampusClaw PR #323 开发提交从 `c9a2340f87bda6dff6bbd352f6995f8551206bb5` 更新到 `ae6645caaade3b9520220a34af940210850ef36a`，只升级确认前准备、模型恢复反馈和 SearchTools 差距，见[M03 专项证据](../02-CampusClaw工具系统/source-evidence.md#search-tools-evidence) |
| Command 状态专项基线 | M05：用户指定 Java `53eff85c7f41de23eb434e027782f5085a8b8e45`；只复核 Runtime 命令、严格名称、展开文本恢复与 Slash 交互，见[当前实现](../../04-命令与技能/00-Slash-Command通用模块/README.md#current-runtime-status)；不升级外部基线或统计结论 |
| Skill 统计专项基线 | A09：Codex d58d0e58 的完整计数链；Java f61906b9 的 Runtime/Read/Child/Cron 骨架，#295/#298 仅作固定对照，不升级其他 M05 结论 |
| 决定消费终态专项基线 | A03/M06：Java `74f1b8314c9a5eb3d1659dfed2ab90b787dd647f` 的共享枚举、三类领取 SQL、markTerminal 与安装 DDL；仅新增内部 CANCELED 目标，不升级其他条目或外部基线结论 |
| 线性历史专项基线 | A12：pi main `1a584a7a56eb5e7b4ff8ccbd46430f1533282eed`，2026-09-22 已确认默认分支并隔离 fetch；Java 本地 `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12`；只升级分支索引与 Session 历史读取结论 |
| Redis 观察专项基线 | A13：2026-09-22 确认并隔离 fetch OpenCode dev `fe3f3a41f79ad292cc3c7c629567385a20ec5130`，仅事件协议、live/durable 定义与实例监听；Java 本地 `53eff85c7f41de23eb434e027782f5085a8b8e45` 的投影/流/控制/终态/依赖范围；新能力待实现，v2 仍为 experimental |
| 调度专项基线 | A14：2026-09-22 隔离 fetch pi `main@95fbc04997eaee961eb673fa7923e9220609ebd5`、Codex `main@a1f40f3f1326eff7c81b860a4f4e27c1be186e10`、OpenCode `dev@fe3f3a41f79ad292cc3c7c629567385a20ec5130`、DeepSeek Harness `master@c36a83ff6bb95e3f82cf79f9be7c724270a8aa61`；Claude Managed Agents 与 Codex scheduled tasks 仅核对 2026-09-22 官方文档，均无可归因的公开调度器源码 commit |
| 核验范围 | A07 的模式入口、TUI 实施选择、方案/任务/问题分离、Slash 协同与前端接入范围；M01 的 Loop/控制消息扩展点、M06 的 Controller/分派/回执/流缓冲与配置更新源码；A04 的五基线接口边界；Claude 公共 Session/Agent/流与历史文档；A03 的计划文件/正文载体；A05 的三基线显式任务事件、Java 多事件事务与客户端消费接入点；A03/A05 的计划与实施提示词；A06 的 M02 Provider 身份、业务 Agent 设置唯一模型来源及旧全局目录差距；M08 的 Agent 默认 mode、目录快照、Session 初始化与元数据组合查询顺序 |
| 验证边界 | A08 已补充固定开发分支的 Runtime/数据库/前端确定性验证；其余条目保留各自静态核验范围，企业接入与真实模型行为不在已验证范围 |

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
| Claude Managed Agents | 官方文档，核对日期 `2026-09-14`；无服务端源码 commit | 公共 Session API、preview 与历史对账 | A02/A04/A05 已核对公开流、List Events、Session 更新、配置限制和通用 custom tool 交互；仍为 Beta，只证明公开契约 |
| Codex harness | `d58d0e5841e0de08e251673db2d5af8cf3a1ad51` | Provider typed event、Turn/Item 客户端生命周期 | A04 已核对配置协议，A05 核对指定模型的 update_plan 指令及 Handler；A07 核对 TUI 方案实施与 plan Item/TODO 分离；A09 核对 Skill 触发/身份/两级去重/指标/上报；Provider 与其余 M07 生命周期仍待专项核验 |
| OpenCode | `849c2598abc7d2b40261e74b5826bc74ffc78308` | 多客户端、live/durable 分类与 sequence 回放 | A04 已核对 Session 配置/消息/v2 操作，A05 核对 todowrite 描述与模型提示词；事件流仍待专项核验；v2 源码能力不能自动视为稳定公开契约 |
| DeepSeek Harness | `0a53fb55bea101816fa226bb964ae2bed71c343b`，`dsh-0.1.2-alpha.2` | 计划模式；完整事件溯源与 token 级回放的成本上限 | A03/A04/A05 已核对计划插件、preset、Session 配置接口和 todo_write 完整列表；完整日志仍待 M04/M06 专项核验；保留 alpha 成熟度边界 |

没有同层、同范围证据时填“未核验”或说明“不适用”的理由，不以功能勾选或总分给系统排名。
公司认证、租户隔离、凭据传递、审计和数据保留是 CampusClaw 产品约束，不能因为基线没有相同名词就删除。

## 3. 按模块维护的对比问题

| 模块 | 需要解释的架构问题 | 主基线及辅助对照 | 条目与待补证范围 |
|---|---|---|---|
| M01 · Runtime 与多 Agent | Loop 扩展能力如何与产品准入分离；父子执行如何隔离和终止 | pi；Codex、DeepSeek 辅助 | [A01](#a01)覆盖 Loop 与消息准入；[A03](#a03)覆盖计划模式接入与 Child 模式传递，其他父子生命周期待补证 |
| M02 · Model | 如何让业务 Agent 设置成为唯一模型权威；Provider 调用与模型选择如何分层；原始事件在哪层归一化 | 模型目录差异采用 pi；事件归一化专项采用 Codex | [A06](#a06)覆盖 CampusMate 身份、业务 Agent 设置、旧全局目录删除和 SDK 削减；Codex 事件归一化对比及完整取消链仍待专项核验 |
| M03 · Tool 与受管环境 | 工具发现、参数校验、权限、执行和副作用重试分别由谁负责 | pi；其他基线按具体执行问题选择 | [A03](#a03)覆盖稳定工具定义与计划 Prompt；[A05](#a05)覆盖 TODO 工具及事件边界；[A08](#a08)覆盖结构化提问；[A10](#a10)覆盖通用命令与写工具删除边界；[A11](#a11)覆盖远端代理与 Skill 工具按需披露 |
| M04 · 上下文与持久化 | 模型上下文、历史、分支与压缩如何区分；哪些事件值得保存 | pi；DeepSeek 辅助 | [A03](#a03)覆盖模式/审核恢复；[A12](#a12)覆盖单条时间线与非递归读取，其他上下文比较待补证，不默认 token 全量落盘 |
| M05 · Command 与 Skill | 清单、资源发现、执行与使用统计分别维护什么权威状态 | pi；发现参照 OpenCode/DSH，统计参照 Codex/OpenCode | [A09](#a09)覆盖使用信号、根去重、失败隔离与入口范围；[A11](#a11)覆盖 Skill 加载与具体工具定义披露；[当前 Command 状态](../../04-命令与技能/00-Slash-Command通用模块/README.md#current-runtime-status)区分 Runtime 已实现与版本快照、统计、Mate 增量 |
| M06 · 事件与服务边界 | 写入与观察是否分离；流绑定谁；断线如何恢复；控制状态谁权威 | Claude；OpenCode，必要时 pi/DeepSeek | [A02](#a02)覆盖既有 Claw/Mate 流范围；[A13](#a13)覆盖 Redis 快照与短期增量恢复；[A03](#a03)维护数据库确认交接；[A04](#a04)覆盖 Session 配置更新；[A05](#a05)覆盖后端显式任务事件 |
| M07 · 前端体验 | preview 何时被权威内容替换；Turn/Item 与产品 UI 如何映射 | Codex；Claude 辅助 | [A05](#a05)保留旧提交的事件合并与根执行证据；当前计划/TODO/问答前端实现见[A07](#a07)及[A08](#a08)，公共 Mate 接入仍为目标设计 |
| M08 · 元数据与配置 | 定义、发布快照和运行对象如何分离；刷新如何影响活动执行 | pi；托管产品仅对照公开资源 | Agent.mode 专项已核对 Mate 956b547f / Runtime 09b32d8e；默认值链为 待实现，见 A03 和元数据主设计；元数据组合查询顺序另在 Mate `9dd5d85e` 核对，见 J06；发布事务一致性仍待补证 |
| M09 · 附件与文件 | 文件服务与 Agent 工作区是什么关系；何时解析与授权 | pi；托管产品公开文件契约按需核对 | 待补证；明确企业产品约束 |
| M10 · 调度与并发 | Session 准入、Tool 并行和全局容量分别如何限制 | pi；Claude、DeepSeek、OpenCode、Codex 按调度层次补充 | [A14](#a14)覆盖 Cron、固定间隔、对话内提醒、独立运行和失败恢复；CampusClaw 调度器与执行准入仍待核验 |
| M11 · 可观测性与测试 | 日志、审计历史与模型上下文如何分开；如何证明差异可接受 | 按验证对象选基线，不设统一主基线 | 待补证；区分测试存在、测试运行和生产观测 |

M05 的 53eff85c 专项只更新 CampusClaw 实现状态：Builtin、Runtime Skill 执行、严格名称、
展开文本恢复与前端 Slash 已存在；统一 Skill 扩展结构、完整版本快照和统计仍待实现，Mate 公共接入独立确认。
这不改变原有产品约束、安全加固或架构取舍；实现映射与测试未重跑边界由主设计维护。
外部基线历史 SHA 与比较结论保持原核验范围，不把进度校正描述为新的上游比较。
M05/M07 的[参数控件与附件边界](../../07-前端设计/技术设计/命令/README.md#command-input-controls)沿用现有分层：后端提供能力与候选，前端将选择组装为命令参数；hint 不作为控件协议。此项为产品交互约束，不改变上述外部基线结论或全局类图结构。

待补证项是持续维护范围，不能用于讲述已经实现的能力。涉及该模块的新设计应补齐受影响的问题，
不要求一次设计把所有基线全部重做，也不能用“待补证”略过本次实际改变的架构结论。

<a id="a01"></a>

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
| DeepSeek 已观察行为 | 固定 alpha 提交的 `PlanModeController` 根据计划状态提供 `plan:policy`；退出工具持续注册，以完整 Markdown 请求用户审核；批准后在后续 step 退出。`stateVersion=3` 属于投影结构版本，不是业务计划版本。固定链接与符号见[专项源码证据 §2](../06-CampusClaw计划模式/source-evidence.md#2-deepseek-计划模式)。 |
| CampusClaw 已观察实现 | Java `09b32d8e` 已具备统一 Session 工厂、逐轮读取系统 Prompt、确认等待、数据库决定和固定续跑段；本专题相关源码与 `f61906b` 相同。工具确认由前端 executionState/loadHistory 根据事件恢复，Session VO 不暴露待确认工具。该旧提交尚无计划模式及通用 Session 更新；后续 `9f785bea` 的模式、审核、TODO、提问实现与确定性验证见[问答证据](../06-CampusClaw计划模式/ask-user-question.md#2-基线与已观察实现)。历史 `21c3f59b` 提示词装配仍为六份资源且 refresh 不保留额外模式文件，当前 `8c5fda1d` 已修复该差距，见工具状态专项基线；完整路径见[§11](../06-CampusClaw计划模式/source-evidence.md#11-业务-agent-模式提示词覆盖)，未重跑产品测试。 |
| CampusClaw 目标 | Agent 默认 mode 只初始化新 Session，Session 独立维护当前模式；模式更新复用统一 Session POST。计划以完整事件身份审核，沿用原执行与数据库确认交接，批准后以 build 指令续跑；Tool/Skill 定义保持稳定。具体字段、Prompt 和恢复归计划与元数据主设计。 |
| 差异分类 | 产品约束：Agent 默认 mode 与 Session 当前模式分离、Tool/Skill 元数据稳定、当前模式由 Session 更新、只允许 idle 主动切换、Child 调用时继承模式；架构变更：在既有配置服务增加 Session 更新，并将进程内审核接入 HTTP 和已有数据库执行控制；安全加固：精确目标、单次消费、停止竞争和两跳身份校验。 |
| 提示词依据 | DeepSeek standard preset 明确禁止规划期 todo_write；CampusClaw 同样仅在 build 记录实施进度。模式资源仅 PLAN.md / BUILD.md；Main Agent/Subagent 用一行角色区分 PLAN 内规则的适用范围，批准后重组为短 BUILD。通用执行、验证和交付归基础 SYSTEM，进度细则归工具描述；不能以其他 Agent 的模式文件短推断其总规则少。精确正文、BASE 发布前提和矩阵见[提示词设计](../06-CampusClaw计划模式/plan-policy.md)，最新源码及代价见[专项证据 §10](../06-CampusClaw计划模式/source-evidence.md#10-两份模式提示词的最新上游核验)。 |
| 业务模式覆盖 | pi 有 SYSTEM 文件优先级，DeepSeek 有部署提供的 plan:policy，Codex 有模式目录/调用文本覆盖；OpenCode agent.prompt 覆盖基础模板但模式提醒仍独立。CampusClaw 按业务 `.campusclaw/PLAN.md`、`BUILD.md` 分别完整替换，缺失回退预制；执行固定快照、Subagent 读自身目录、refresh 保留可选文件。属于架构扩展；代价是目录发布一致性和自定义正文评估，详见[覆盖证据](../06-CampusClaw计划模式/source-evidence.md#11-业务-agent-模式提示词覆盖)。 |
| 具体理由 | 模式已有明确的 Session 资源归属，更新操作复用其身份、版本与事务，统一四类属性入口，并明确组合原子性。混合查询与变更工具不能依靠新增一个静态只读字段准确表达每次调用用途；稳定字段与工具定义让规划规则独立演进。公共审核需要可对账的事件身份，原有工具权限不能表示对整份方案的批准。展示恢复与锁内接受分离，沿用既有工具确认方式，避免 Session 响应随具体交互增加指针。 |
| 默认值证据与代价 | Mate 956b547f 的 Agent DTO/VO/DefinitionColumns 无 mode；Runtime 09b32d8e 的 prepare 复用目录、refresh 强制发布、create 从解析快照初始化，均无 mode。目标增加字段传播与创建复制，修改 Agent 后须先完成目录发布，不能宣称新 Session 即时读取远端最新值；既有 Session 不被重置。这是产品配置扩展，不是 DeepSeek/Claude 同名字段。完整路径及符号见[专项证据](../../03-数据与存储/02-Agent元数据GaussDB/README.md#23-mode-专项源码核对)。 |
| 收益与代价 | 不扩充工具元数据、不增加第二套 Loop 或 Session 待审字段；需要新增模式和审核事件、确认记录及客户端卡片。刷新必须补齐相关事件，缺页或状态矛盾时禁用审核；跨请求读取仍可能过期，确认始终在服务端重新校验。提示词约束不提供服务端强制只读保证；进程失联自动接管不在该功能承诺中。 |
| 备选与重新评估条件 | 本期不采用副作用白名单、独立 Plan CRUD、Cordis 插件容器或 token 全量日志。若产品要求规划期绝不产生副作用，应单独设计可执行的权限边界，不能将 Prompt 遵循率当作保证。 |
| 设计 / 实现状态 | Java `8c5fda1d` 已实现模式/审核、两份模式资源、业务文件覆盖/执行快照/刷新保留及工具描述收敛；旧 `21c3f59b` 的六份资源和 refresh 缺口不再代表当前实现。BASE 通用规则发布、真实模型及企业验收未核验；Mate 桥接待实现，本次未重跑产品测试。 |
| 验收重点 | 见[主设计 §8](../06-CampusClaw计划模式/README.md#8-实施切片与验收)：模式与消息接受竞争、工具定义稳定、eventId 精确审核、跨实例单次领取、中断与恢复、Child 模式及提示词场景评估。 |

**正文流式专项（2026-09-19，M01/M06/M07）。**

| 维度 | 结论 |
|---|---|
| 最新来源 | 标记专项于 2026-09-19 重新 fetch Java main `fb842b1a` 与 Codex main `78245b47`，均较前次不变；完整 SHA、路径/符号与边界见[证据 §14](../06-CampusClaw计划模式/source-evidence.md#plan-marker-evidence)；pi/DeepSeek/Claude 保留 §13 历史核验，不升级其他范围 |
| 基线行为 | Codex 从模型正文解析 proposed_plan 并发增量，退出由模式指令控制；DeepSeek alpha 的退出工具仍要求完整 plan 参数。不存在“所有基线都是正文后空参数退出”的统一协议；Claude 公开文本 preview 不证明计划工具实现 |
| 已观察 Java | 文本流、完整计划审核与原执行续跑已实现，正文仍在工具参数；无 proposed_plan 解析或计划专用 delta；前端只消费完整计划 |
| 目标与差异 | 同响应唯一计划块后 ExitPlanMode({})；后端解析并发布 agent.plan delta/completed，首非空 delta 建卡，同 ID 完整覆盖，无 started；架构变更。正式审核事务是产品约束，固定来源及完整闭合为一致性/安全边界 |
| 收益与代价 | 生成期即可识别计划，无额外模型轮次与事后换卡；需同步标记解析、最终快照、工具/提示词/联合类型及前端，验证分片/异常/压缩保护；流式不保证整体任务更快 |
| 状态与验收 | 计划标记及两 phase 增量待实现；复用[完整目标类图](../06-CampusClaw计划模式/README.md#3-推荐全局目标类图)，[PS1～PS5](../06-CampusClaw计划模式/plan-streaming.md#6-实施切片与验收)覆盖顺序、恢复、旧数据和真实首字计量；不把文档校验当产品验收 |

**决定消费终态专项。** M06 的数据库交接新增[统一 CANCELED 状态](../01-CampusClaw多Agent运行时/chat-events-design.md#46-已接受决定的消费终态)：工具确认、计划审核、问题答案只在根执行可靠终态事务中收尾未领取记录，保留用户已接受的事实。Java `74f1b831` 已有三类领取和停止条件，终态未更新决定行；新增状态在该基线为 待实现，具体源码路径与验收见主设计。这里改变的是 CampusClaw 持久化消费模型，属于架构变更；不声称 pi、DeepSeek 或托管服务有同名数据库状态。收益是记录本身可区分待领取与不再消费，代价是三表约束和终态事务增加更新；不增加公共事件、依赖或独立清扫任务。既有 Agent Loop 与工具结果参考结论不变，旧 A03 模式实现核对点也不代表当前模块整体尚未实现。

**讲解要点。** DeepSeek 提供了计划模式与工具元数据解耦的参考。CampusClaw 保留这一边界，
以统一 Session POST 更新承载工作模式，把计划审核接入已有 Session Events 和数据库确认续跑；计划正文用事件身份固定，工具授权继续独立执行。
代价是新增审核持久化与客户端交互，同时必须承认提示词约束和失联执行恢复的能力边界。


计划载体并非统一为文件：OpenCode、Claude Code 使用计划文件，已核验 DeepSeek/Codex/pi 路径可直接承载正文或 Session Entry；Managed Agents 公开文档另建议分两次 Session 编排。CampusClaw 完整方案持久化与取舍见[主设计 §1.3](../06-CampusClaw计划模式/README.md#13-完整方案保存在哪里)，固定路径与边界见[证据 §8](../06-CampusClaw计划模式/source-evidence.md#8-计划文件与方案载体)。

<a id="a04"></a>

## 6.1 A04 · Session 属性统一更新，业务准入按字段区分

| 维度 | 结论 |
|---|---|
| 所属模块与主设计 | M06/M02，关联 M01/M07；[HTTP 主设计 §2.4](../01-CampusClaw多Agent运行时/chat-http-v1-design.md#24-模型目录与统一-session-更新)维护契约理由、唯一目标类图与组合事务验收 |
| 架构问题 | 名称、模型、思考和工作模式同属 Session 时，如何通过一个入口更新且保留不同的生效约束？ |
| CampusClaw 目标 | 统一 Session POST；字段可选、支持单字段或组合修改，一笔事务、一个资源版本。当前前端每次操作仅提交对应一个字段。名称单独修改允许 running，执行配置要求 idle；元数据字段保持稳定。精确模型只由 Runtime catalog 维护。 |
| CampusClaw 已观察实现 | Java 09b32d8ea4a4b43b34be302d8b2745bdc417c9a2 的 RuntimeSessionController 没有 update；ConfigurationController 暴露独立模型/思考 PUT；SessionNamingService 经 Command 更新名称。Repository 分别提供 updateModel/updateThinking/updateName，尚无组合原子更新与 mode。路径与符号见[专项证据](../01-CampusClaw多Agent运行时/chat-http-v1-design.md#81-统一-session-更新源码核对)。 |
| 差异分类 | API 架构变更：合并写入入口及事务；产品约束：可变 Session 模型、boolean 思考、plan/build、名称 running 可改、执行配置 idle、稳定元数据；并发安全：锁内复核 ETag/状态，不按页面快照直接写入。 |
| 具体理由 | 当前四个控件共享一种资源更新与对账流程；前端单项调用不构成服务端字段互斥的理由。接口接收字段组合时，按最终目标模型校验思考并整笔提交；不要求页面提供批量保存，也不新增通用属性更新框架。 |
| 收益与代价 | 调用方共享一种更新与对账流程；需要明确省略/null、字段组合、最终模型能力及整笔失败，并改造现有单属性提交代码，不能只换路由注解。 |
| 备选边界 | 基线有独立命令不等于 HTTP 必须分拆；Claude 有 Session POST 也不等于其允许当前会话切换模型。若未来允许运行中改配置，应另定生效快照边界，不能从统一入口自动推导。 |
| 设计 / 实现状态 | 四类统一 POST 为已确认目标；组合事务、mode 与消费者迁移均为 待实现。静态核对未代替 Java/数据库/跨实例测试。 |
| 验收重点 | 单字段与组合请求；目标模型不支持显式 thinking=true 时全不变；省略 thinking 的自动归一；running 名称例外；同值不升版本；ETag 竞争、插入历史失败回滚；旧目标写入口不回流。 |

同层 API 组织的证据如下，不能按“多数基线如此”投票决定接口：

| 基线与实际核对点 | 已观察接口组织 | 采纳范围与边界 |
|---|---|---|
| Claude Managed Agents，官方 Beta 文档，2026-09-14 | [Update Session](https://platform.claude.com/docs/en/api/beta/sessions/update) 使用资源 POST；title/metadata/budget/agent 可选，公开契约未列出单字段互斥限制，主示例只提交 title；模型/effort 在可版本化 Agent 配置中，已有 Session 不能中途修改模型配置，见[Session operations](https://platform.claude.com/docs/en/managed-agents/session-operations) | 参考资源级部分更新及单字段主示例；字段集合、null、If-Match 与原子性由 CampusClaw 定义，不迁入 Agent 版本快照与会话模型不可变约束；无服务端源码，不能推断其数据库事务 |
| DeepSeek Harness 0a53fb55bea101816fa226bb964ae2bed71c343b，alpha | [packages/api/session-controller/src/commands.ts](https://github.com/deepseek-ai/deepseek-harness/blob/0a53fb55bea101816fa226bb964ae2bed71c343b/packages/api/session-controller/src/commands.ts) 的 selectModel 合并模型与 reasoningEffort，rename 独立；[packages/plan/plan-mode/src/index.ts](https://github.com/deepseek-ai/deepseek-harness/blob/0a53fb55bea101816fa226bb964ae2bed71c343b/packages/plan/plan-mode/src/index.ts) 注册 plan 命令 | 借鉴模型与能力关联、计划机制；其 Remote RPC 及后续 step 切换时机不决定 CampusClaw HTTP 形状 |
| pi 5cd93f688aaab89dbb6dfa4aca535f21796ae185 | [packages/coding-agent/src/modes/rpc/rpc-types.ts](https://github.com/badlogic/pi-mono/blob/5cd93f688aaab89dbb6dfa4aca535f21796ae185/packages/coding-agent/src/modes/rpc/rpc-types.ts) 的 set_model/set_thinking_level/set_session_name 是独立 JSONL 命令；[core/agent-session.ts](https://github.com/badlogic/pi-mono/blob/5cd93f688aaab89dbb6dfa4aca535f21796ae185/packages/coding-agent/src/core/agent-session.ts) 的 setModel/setThinkingLevel 提供能力归一 | 参考 Runtime 行为；进程命令无 PUT/POST 含义，不能直接推出公共 API 需要属性专用端点 |
| Codex d58d0e5841e0de08e251673db2d5af8cf3a1ad51 | [codex-rs/app-server-protocol/src/protocol/v2/thread.rs](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/app-server-protocol/src/protocol/v2/thread.rs) 的 ThreadSettingsUpdateParams 合并后续 Turn 配置；[app-server/README.md](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/app-server/README.md) 区分 thread/name/set 与当前 Turn 的 settings/update | 参考合并配置与生效范围分离；两种 settings/update 为 experimental，不照搬 JSON-RPC 或运行中切换功能 |
| OpenCode 849c2598abc7d2b40261e74b5826bc74ffc78308 | [packages/opencode/src/server/routes/instance/httpapi/groups/session.ts](https://github.com/anomalyco/opencode/blob/849c2598abc7d2b40261e74b5826bc74ffc78308/packages/opencode/src/server/routes/instance/httpapi/groups/session.ts) 的 UpdatePayload 包含 title 等属性；[packages/opencode/src/session/prompt.ts](https://github.com/anomalyco/opencode/blob/849c2598abc7d2b40261e74b5826bc74ffc78308/packages/opencode/src/session/prompt.ts) 的 PromptInput 随消息选择 model/agent/variant；[packages/protocol/src/groups/session.ts](https://github.com/anomalyco/opencode/blob/849c2598abc7d2b40261e74b5826bc74ffc78308/packages/protocol/src/groups/session.ts) 的 switchModel/switchAgent 又提供独立 v2 操作 | v2 明确为 experimental，不能混成一套稳定公开契约；CampusClaw 使用独立于发送消息的 Session 更新 |

**讲解要点。** CampusClaw 将用户编辑会话属性的动作统一为一次资源更新，借鉴 Claude 的资源组织和其他基线的配置边界，同时保留自己的运行约束。难点在组合状态而非 HTTP 方法：目标模型决定思考是否有效，行锁与 ETag 决定整笔更新能否提交；名称更新不触碰执行快照。已有窄服务可复用，组合事务和模式能力仍需实现与验证。

<a id="a05"></a>

## 6.2 A05 · 后端显式任务更新与恢复

| 维度 | 结论 |
|---|---|
| 所属模块与主设计 | M03/M06/M07，关联 M01/M04；[TodoUpdate](../06-CampusClaw计划模式/todo-update.md) 维护工具、提交与恢复，复用计划模式全局目标类图 |
| 架构问题 | 如何让前端直接获得执行清单，同时保持工具与 Session 元数据稳定、断线后恢复相同进度？ |
| Claude 公开契约 | 官方 Beta 文档 2026-09-15 核对：通用自定义工具事件与持久化历史；未公开原生 TodoUpdate 或同名更新事件。只借鉴权威历史与对账，不推断内部 TODO 实现。 |
| DeepSeek 源码 | 固定 0a53fb55 的 tool-todo 追加 todo/write 全量快照，下一 turn/start 清空投影；采用显式快照思路，不照搬 alpha 日志格式。 |
| OpenCode / Codex 源码 | OpenCode 849c2598 的 SessionTodo.update 替换表后发布 todo.updated（固定 v2 源码）；Codex d58d0e58 的 PlanHandler 发 PlanUpdate，App Server 文档定义 turn/plan/updated。两者证明任务更新可由后端显式发布，不能混称同一公共传输协议。 |
| pi 源码 | 固定 5cd93f68 的 todo 示例从工具结果 details 恢复；这是另一种客户端派生方案，不作为当前 CampusClaw 进度消费方式。 |
| CampusClaw 已观察实现 | Java 09b32d8e 的 persistToolResults 已在批次结果边界提交；appendEntry 接收事件列表，仓库记录实际投影数量；该旧提交尚无 TODO 工具与专用事件/面板；后续实现和确定性验证见[问答证据](../06-CampusClaw计划模式/ask-user-question.md#2-基线与已观察实现)，不将旧差距扩展为当前状态。 |
| CampusClaw 目标 | build 根执行使用 TodoUpdate，plan 不记录调研进度；成功工具结果同事务生成 agent.todo_updated。前端直接消费 todos；新消息隔离清单，审核续跑保持原根。 |
| 调用时机约束 | TodoUpdate description 集中规定任务实际完成并验证后立即更新，同次可完成上一项并开始下一项；BUILD 仅提示按工具描述跟踪进度，不再复写时机细则。通用验证与诚实交付由 BASE 负责；值校验不证明业务完成，模型仍可能漏调用。最新提示词证据见[§10](../06-CampusClaw计划模式/source-evidence.md#10-两份模式提示词的最新上游核验)。 |
| 差异分类 | 架构变更：后端负责将最终工具结果映射为公共任务事件，复用现有一 Entry 多事件事务。产品约束：build 实施、单进行中、原根作用域、Agent/Tool/Skill 元数据不因 TODO 扩展。 |
| 理由与代价 | 前端无需识别工具名或解析结果文本，事件历史可直接恢复面板；代价是新增公共类型及每次更新的一份持久化快照，读取端需先升级；仍等待批次结果提交。 |
| 备选与重新评估条件 | 不新增 TODO CRUD、Session todos 或 TODO 表；如需独立任务身份、多人编辑、调度依赖或工具方法返回即发布，应另评估资源与提交边界。 |
| 设计 / 实现状态 | Java `8c5fda1d` 已实现 TodoUpdate、显式任务事件及前端消费、工具描述集中维护和两文件迁移，见工具状态专项证据；Mate 桥接待实现，真实模型行为未核验，不将代码存在表述为验收通过。 |
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
| 备选边界 | 不复制 DeepSeek Cordis、plan-review intent 或空答案跳过；不新增问卷 CRUD、Session 指针、元数据字段或通用工作流。逐题翻页不构成部分提交；若需 Child 直接提问/部分提交/持久化草稿，重新确定交互归属与控制边界。 |
| 设计状态 / 实现状态 | Java `8c5fda1d` 主线已实现问答闭环、逐题导航、整批提交、工具日志汇聚和模式提示词装配；原 PR #301 测试结果仍只证明原提交。Mate 桥接待实现，业务 SYSTEM 发布、优先一题等真实模型遵循未核验，本次未重跑测试。 |
| 验收 | Q1～Q5 对应 clean verify 2085 项、独立数据库 140 项及前端 172 项通过；实际 JAR HTTP 继续/竞争/中断、214 契约样例、10 投影场景和浏览器 18 项检查通过。公司 NativeParent 缺失、外部 Mate 与真实模型未验证；完整环境边界见主设计 §2。 |

**讲解要点。** 借鉴 DeepSeek 的工具式提问，将 UI 等待接入 CampusClaw 已有执行段和控制事务。用户回答成为原调用结果，前端消费显式问题；计划批准与工具权限保持独立。获得精确关联和原根续跑的同时，需要维护答案交接与恢复，元数据结构保持稳定。

<a id="a09"></a>

## 6.6 A09 · Skill 使用信号、根执行去重与失败隔离

| 维度 | 结论 |
|---|---|
| 模块与主设计 | M05，协作 M06/M04；[使用统计](../../04-命令与技能/03-Skill加载统计/README.md)维护口径、三表、事务、API 和验收，复用其全局目标类图及提交时序。 |
| 架构问题 | 如何统计哪些根执行接触过 Skill，避免分页和续跑放大次数，同时不让观测故障改变主执行结果？ |
| Codex 观察 | 固定 d58d0e58 有 codex.skill.injected 和 skill_invocation；Host 显式指标包含失败、Shell 执行前识别、资源首屏计数，计数器与分析事件去重位置不同。队列 256 且可能丢弃。身份、字段和路径见[Codex 详解](../../04-命令与技能/03-Skill加载统计/codex-skill-counting.md)。 |
| pi / OpenCode 对照 | pi 固定 5cd93f68 的 Skill 展开和工具生命周期可作归因入口；OpenCode 固定 849c2598 提供显式 Skill 工具记录。它们不能证明已有企业三表或管理统计 API。 |
| CampusClaw 已观察实现 | Java f61906b9 已有 Runtime 根消息、工具调用/结果和短事务；Read details 尚无完整归因证据；Child 为内存执行/进度，Cron runner 未传 job/run。#295 ee2f4dd/#298 3dfd990 仅作全文候选实现对照，未提升为新主线统计。完整路径与符号见[证据](../../04-命令与技能/03-Skill加载统计/source-evidence.md)。 |
| CampusClaw 已确认目标 | 同一 sessionId/rootEventId/skillId 至多计 1；显式受理与最终成功 Skill/Read 共用 Tracker，部分正文即可。三张统计表独立短事务，仅新事实加数；失败不阻断主执行，允许漏计。F19 查询改为 POST + skillIds，返回 activationCount/lastLoadedAt，排名与趋势暂缓；F20 的 Runtime 范围与当前三入口实现仍待单独对齐。 |
| 差异分类 | 产品约束：根执行使用频度、Runtime 首版、既有 Skill 身份；架构变更：统一跨入口去重，独立同步统计替代 Codex 的异步遥测输出；安全加固：可信快照、管理授权与删除准入。 |
| 理由与代价 | 减少分页和重复 Read 对排名的影响；以失败隔离保持受理和工具语义。代价是失去逐次调用明细、允许漏计，仍有同步等待与热门 Skill 行锁；lastUsedAt 仅反映已计使用。 |
| 备选与重评 | 只有累计/日表不能去重，纯 Trace 可能缺失，仅事实表使累计扫描增长。若同步等待实测不达标，再设计有界异步投递、关闭及失败策略；不提前增加 MQ/OTel。 |
| 范围与生命周期 | 确认、问答、审核保持原根，普通新消息换根；活跃根去重键不清理。Child/Cron 先补真实身份与关联再定义去重域；部分事实不能重建累计，三表一致恢复。 |
| 设计状态 / 实现状态 | 目标方案已确认；新增 Tracker/Resolver、独立统计事务、三表及 GET 为 待实现，所查 Java 骨架不证明实现完成，未跑 GaussDB。 |
| 验收 | S1～S4：显式加多次 Read 共 1、新根再计、跨日续跑、部分正文/失败/改写、独立事务回滚与主流程成功、并发首写、删除竞争、查询窗口、权限和端到端等待。 |

**讲解要点。** 借鉴 Codex 在运行时产生结构化使用信号与观测失败隔离。CampusClaw 将显式和 Read 统一到根执行/Skill 去重，使用可信快照和真实根身份，部分正文即可；三张统计表独立事务并允许漏计。它衡量已记录使用信号的根执行数，不证明模型采用，也不是原样复制 Codex 的 Turn 去重或异步队列。

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
| 所属模块与主设计 | M10，关联 M01/M04/M06；本条先登记外部基线行为，CampusClaw 的调度主设计仍待补齐，不新增当前产品契约 |
| 架构问题 | 到期时间由谁拥有，定时器只是唤醒还是执行权威；到期后是回到同一 Session、创建新的 Agent Run，还是由外部平台重新启动进程；重启、空闲、暂停和失败如何对账？ |
| 先给结论 | 没有统一的“Agent Cron 实现”。Claude Managed Agents 是托管平台级 Cron，触发独立 Deployment Run 和新 Session；DeepSeek Harness 是 Session 内固定间隔提醒，事件日志是权威、定时器是临时投影；pi Pico v3 是通用持久化 Task Scheduler 草案，时间条件由 `notBefore` 驱动但没有用户级 Cron 产品；OpenCode 的 Runtime 只有进程内 BackgroundJob，官方定时入口委托给 GitHub Actions；Codex 开源 harness 不包含调度器，Codex 应用层的 Scheduled Tasks 属于宿主/云端能力。 |
| 成熟度边界 | pi Pico v3 文档明确标为 design under discussion，DeepSeek Harness `dsh-0.1.7-alpha.1` 仍为 alpha，OpenCode 当前核对的是 `dev` 分支，Claude Managed Agents 仍要求 beta header；Codex Scheduled Tasks 以官方产品文档为公开契约，未取得服务端实现源码。 |

### 1. 调度职责和权威状态

| 基线 | 调度入口与时间模型 | 权威状态与唤醒方式 | 到期后的执行边界 | 失败、重启与暂停 |
|---|---|---|---|---|
| pi Pico v3 | `Task.notBefore` 是最早执行时间；`Scheduler` 通过 `drive`/`resume` 检查依赖、时间、permit、取消和执行占用。`pi.job` 还支持 `notBefore` 与固定 `every` 秒数；未发现 Cron 表达式解析或用户级 Cron 管理入口。 | Task 记录持久化在 Session；`Scheduler` 的 `invocations`、AbortController 和 waiter 是进程内执行投影。未来时间可等待，外部事件或 permit 可使 drive 暂停。 | Scheduler 只保留通用生命周期，不理解 Prompt 或业务参数；Job 的 handler 负责等待、启动进程、轮询、重复和结果通知。 | 重启保留 pending/running checkpoint，重新 `drive` 后由任务定义决定 retry/adopt/interrupted；关闭不写取消。文档明确打开 Session 不自动启动任务，不能把恢复误解成自动 Cron。 |
| DeepSeek Harness | `schedule_create` 支持 `after`、绝对 `at` 和至少 300 秒的固定 `every`；明确不支持 Calendar/Cron。每个 record 保存 UTC `scheduledAt`，固定间隔保持创建时锚点。 | `schedule/change` Session 事件日志是唯一持久化权威；Projection 只是 active 视图；`ScheduleRuntime` 从 Session fold 重新计算并用有界 `setTimeout` 分段唤醒。 | 只对 live root Agent 生效；先等待 Agent idle，取得 maintenance claim，再向同一会话 `followup`，最后追加 dispatch 事件。正在运行的 turn 不被打断；一次性提醒优先，多个固定间隔提醒批量投递。 | Session 冷却时只保留 overdue；恢复 live root 后重新计算，固定间隔只投递最新到期 occurrence，不补发 backlog。创建/删除/dispatch 都有 persistence barrier；barrier 失败返回 `persistence_uncertain` 或让 runtime 停止，不能把内存 timer 当成功凭证。 |
| Claude Managed Agents | Deployment 的 `schedule` 是 5 字段 POSIX Cron + 必填 IANA timezone，粒度到分钟；服务返回 `upcoming_runs_at`，实际触发可有最多 10 秒 jitter。 | Deployment 及 Deployment Run 由托管 API 管理；每个触发先生成 run 记录，再尝试创建 Session。公开文档没有说明内部 timer、分布式锁或数据库实现。 | 每次 Cron fire 创建一个新的 Session，并发送 Deployment 配置的 initial `user.message`；成功 run 关联 `session_id`，Session 事件另行跟踪。 | 失败触发仍有 run 记录；限流错误不重试、等下次 occurrence；环境/凭据等不可恢复错误会自动 pause；unpause 从下一次 occurrence 继续且不补发；archive 终止调度。DST 按本地墙上时间匹配，春跳不存在的时间不触发，秋回重复时间触发两次。 |
| OpenCode | 当前 `dev` Runtime 没有 Cron/Schedule 模块；`BackgroundJob` 是 `Effect` 作用域内的进程内 job registry，不是日期调度器。官方 GitHub 集成把 `on.schedule` 的 Cron 交给 GitHub Actions。 | Runtime 的 BackgroundJob 只存 `SynchronizedRef<Map>`；官方 GitHub Actions、Runner 和仓库事件是外部权威，OpenCode 本身不保存 Schedule record。 | GitHub Actions runner checkout 后调用 `anomalyco/opencode/github@latest`；scheduled event 必须提供 prompt，输出进入日志/PR。它不是同一常驻 Session 的内部提醒。 | BackgroundJob 注释明确进程重启或 owner scope 关闭会丢失状态并中断工作；GitHub Actions 的重试、并发和失败结果由外部平台承担，当前 OpenCode Runtime 没有对应恢复协议。 |
| Codex | 开源 harness 未发现 Cron 解析、调度表或调度 loop。当前协议有 `ScheduledTaskSummary`，它是 PluginDetail 中的插件声明元数据；`TurnStartOptions.turn_trigger` 仅记录如 `automation_cron_scheduled` 的来源。旧 `agent_jobs` 表在 migration 0042 被删除。 | Codex Scheduled Tasks 是宿主/服务能力，不是 `openai/codex` 仓库内核。官方文档公开了 standalone task 与回到现有 chat 的 task、后台运行、worktree/local project 选择、运行记录和 RRULE 高级编辑；没有公开服务端存储和抢占实现。 | Standalone 每次新建 chat；chat 内任务回到既有上下文。Codex CLI 和 IDE 没有 Scheduled 管理界面，桌面 app 处理本地项目时要求机器和 app 保持运行。 | 官方文档要求使用 Scheduled 查看最近运行；无人值守任务使用默认 sandbox/权限策略。内核只接收宿主送入的 turn 并记录 trigger，不能据此推断 Codex harness 自己负责 Cron 恢复。 |

### 2. 正常调用与失败处理的主流程

这些基线的共同点只有“到期后要进入 Agent 执行”，并不存在统一的权威层。按职责还原主流程如下：

1. **托管平台 Cron（Claude）**：创建 Deployment，绑定 Agent、Environment、initial event 和 Cron → 到期创建 Deployment Run → 创建新 Session → 投递 initial event → 通过 Session event stream/webhook 观察结果。Session 创建失败仍记录 run；可恢复的限流等到下一次 occurrence，资源类不可恢复错误使 Deployment pause。
2. **Session 内提醒（DeepSeek）**：工具校验规则和时间 → 等待持久化 flush → append `schedule/change:create` → 再次 flush 后确认 → runtime timer 唤醒并重新 fold → idle maintenance claim → `followup` 入队 → append dispatch → flush。任一步持久化不确定都不能返回“已成功”；运行中的 Agent 不被打断。
3. **通用 Task（pi）**：调用方先持久化 pending Task → 外部或本地 `drive` 扫描 covered scope → Scheduler 在 commit 中检查依赖、`notBefore`、permit、取消与单任务 claim → handler 通过 checkpoint 驱动阶段 → 结果与 successor 一起 settlement。它把“何时允许推进”和“业务如何恢复”分开，调用方仍负责在进程外重新 drive。
4. **外部 Workflow（OpenCode）**：GitHub Actions Cron → Runner checkout → OpenCode GitHub Action → Agent 执行 → 日志/PR。调度、运行隔离和失败语义主要由 GitHub Actions 承担；OpenCode BackgroundJob 只解决当前进程内并行工作和观察。
5. **宿主调度（Codex）**：Scheduled task 服务/桌面 app 按规则创建 standalone 或既有 chat run → 将 prompt、项目/worktree 和权限上下文交给 harness → harness 只处理普通 turn，并记录 `turn_trigger`。服务端的持久化、去重、抢占与失败重试未公开，必须标为未核验。

### 3. 对 CampusClaw 的适用边界

| 需求 | 适合参考 | 不应直接照搬 |
|---|---|---|
| 园区每日设备告警汇总、设施巡检、能耗报表 | Claude 的 Deployment/Cron/Run 分层；OpenCode 的外部 Runner 边界 | 不把 Session 内 `followup` 当成企业级独立作业；不把 GitHub Actions 的权限模型当成租户权限模型 |
| 同一会话中的“30 分钟后提醒我复查工单” | DeepSeek 的 Session-local durable reminder；pi 的 `notBefore` 与可恢复 checkpoint | DeepSeek 的 live-root 限制和无外部通知是产品选择，不是 CampusClaw 的默认能力 |
| Java Runtime 重启或多实例后不重跑已接受作业 | pi/DeepSeek 的持久化权威 + timer 仅唤醒；Claude 的独立 Run 记录 | 不把 `ScheduledExecutorService`、`setTimeout` 或单机 cron 进程作为唯一权威 |

本次调研不改变 CampusClaw 当前目标；M10 仍是待决策。若进入设计，建议先拆成两类，不共用含义：

- **平台调度作业**：保存 `t_schedule`（规则、时区、Agent/租户绑定、下一次 occurrence）和 `t_schedule_run`（每次触发、受理、Session、终态、错误），到期只产生一次受理请求，再由现有 Runtime 准入和执行链处理。定时器/外部 scheduler 只能唤醒扫描，不能替代数据库权威或重复保护。
- **会话内提醒**：若确有产品需求，再复用 Session 事件和原会话 follow-up；明确它不能在 Session 冷却时向外部渠道送达，也不能隐式打断运行中的执行。

这一区分属于推演方案，不是已实现能力。正式设计至少要补齐可信 Agent/租户绑定、规则与时区校验、下一次 occurrence 计算、到期 claim、Session 接受、并发去重、暂停/恢复、失败分类、审计和历史对账；不能只增加一个 Cron 字符串字段。

### 4. 源码与官方契约证据

| 基线 | 最新核验提交或官方日期 | 仓库相对路径、关键符号与证据范围 |
|---|---|---|
| pi | `main@95fbc04997eaee961eb673fa7923e9220609ebd5`，2026-09-22 | [`packages/agent/src/harness/pico3/scheduler.ts`](https://github.com/badlogic/pi-mono/blob/95fbc04997eaee961eb673fa7923e9220609ebd5/packages/agent/src/harness/pico3/scheduler.ts#L84-L197) 的 `Scheduler#resume/drive/drain/reserveEligible`；[`packages/agent/src/harness/pico3/kinds/job.ts`](https://github.com/badlogic/pi-mono/blob/95fbc04997eaee961eb673fa7923e9220609ebd5/packages/agent/src/harness/pico3/kinds/job.ts#L4-L187) 的 `JobInput`、`initial`、`waiting`、`poll`；[`packages/agent/docs/pico-v3.md`](https://github.com/badlogic/pi-mono/blob/95fbc04997eaee961eb673fa7923e9220609ebd5/packages/agent/docs/pico-v3.md#L964-L1020) 的 timing/permit/drive 约束。文档和源码均属于 Pico v3 讨论稿，不是已发布 package export。 |
| Codex harness | `main@a1f40f3f1326eff7c81b860a4f4e27c1be186e10`，2026-09-22 | [`codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`](https://github.com/openai/codex/blob/a1f40f3f1326eff7c81b860a4f4e27c1be186e10/codex-rs/app-server-protocol/src/protocol/v2/plugin.rs#L773-L822) 的 `ScheduledTaskSummary/ScheduledTaskSchedule` 仅为 PluginDetail 元数据；[`codex-rs/core/src/session/turn_input.rs`](https://github.com/openai/codex/blob/a1f40f3f1326eff7c81b860a4f4e27c1be186e10/codex-rs/core/src/session/turn_input.rs#L131-L176) 的 `TurnStartOptions.turn_trigger` 只记录触发来源；[`codex-rs/state/migrations/0042_drop_agent_jobs.sql`](https://github.com/openai/codex/blob/a1f40f3f1326eff7c81b860a4f4e27c1be186e10/codex-rs/state/migrations/0042_drop_agent_jobs.sql) 删除旧批处理 Agent Job 表。Codex Scheduled Tasks 的宿主契约核对[官方文档](https://learn.chatgpt.com/docs/automations)，日期 2026-09-22；服务端实现未公开。 |
| OpenCode | `dev@fe3f3a41f79ad292cc3c7c629567385a20ec5130`，2026-09-22 | [`packages/core/src/background-job.ts`](https://github.com/anomalyco/opencode/blob/fe3f3a41f79ad292cc3c7c629567385a20ec5130/packages/core/src/background-job.ts#L113-L188) 明确 registry 是 process-local、非 durable；`BackgroundJob.start/extend/wait/cancel` 在同一进程作用域内工作；[`packages/opencode/src/background/job.ts`](https://github.com/anomalyco/opencode/blob/fe3f3a41f79ad292cc3c7c629567385a20ec5130/packages/opencode/src/background/job.ts#L17-L35) 按 InstanceState 装配。已检查 `packages/opencode/src`、`packages/core/src`、`packages/protocol/src`，未发现 Cron/Schedule 模块。官方 GitHub 调度入口见[OpenCode GitHub 文档](https://dev.opencode.ai/docs/github)，核对日期 2026-09-22。 |
| DeepSeek Harness | `master@c36a83ff6bb95e3f82cf79f9be7c724270a8aa61`，`dsh-0.1.7-alpha.1`，2026-09-22 | [`packages/schedule/schedule/src/types.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/c36a83ff6bb95e3f82cf79f9be7c724270a8aa61/packages/schedule/schedule/src/types.ts#L40-L120) 的 durable record/dispatch/view；[`src/runtime.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/c36a83ff6bb95e3f82cf79f9be7c724270a8aa61/packages/schedule/schedule/src/runtime.ts#L83-L338) 的 `ScheduleRuntime#driveOnce`；[`src/index.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/c36a83ff6bb95e3f82cf79f9be7c724270a8aa61/packages/schedule/schedule/src/index.ts#L41-L147) 的插件装配与 root Agent 生命周期；[`packages/schedule/schedule/README.md`](https://github.com/deepseek-ai/deepseek-harness/blob/c36a83ff6bb95e3f82cf79f9be7c724270a8aa61/packages/schedule/schedule/README.md#L76-L125) 的事件权威、flush barrier、idle delivery 和 latest-only catch-up。 |
| Claude Managed Agents | 官方文档核对日期 2026-09-22；Beta，暂无服务端源码 commit | [Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments) 的 Cron、timezone、jitter、Deployment Run、pause/unpause、failure 和 manual run；[Create Deployment API](https://platform.claude.com/docs/en/api/http/beta/deployments/create) 的 `BetaManagedAgentsScheduleParams`。这里只证明公开托管契约，不推断其内部 scheduler、锁或数据库。 |

**讲解要点。** 设计 Cron 时先问“到期后要创建哪一种权威执行”，再问“用什么 timer”。Claude 适合作为独立园区作业的服务级参照，DeepSeek 适合作为同 Session 提醒的持久化与 idle 交接参照，pi 适合作为通用 Task/恢复骨架，OpenCode 说明外部 Workflow 也可以是合理边界，Codex 则提醒我们不要把宿主调度能力误写成 Runtime 内核能力。CampusClaw 仍需以租户、Agent 发布快照、数据库受理和审计要求重新定义这些边界。

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
