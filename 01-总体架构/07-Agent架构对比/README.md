# CampusClaw 与 Agent 基线的架构对比

[返回总体架构](../README.md) · [模块索引](../../README.md#module-index)

| 属性 | 值 |
|---|---|
| 文档版本 | 1.0.0 |
| 更新日期 | 2026-09-14 |
| 文档职责 | 按模块解释架构取舍与实现差距，支撑设计讨论、架构答辩和面试 |
| 设计依据 | `pi-mono-java-design@b07db4dfe0bdc6229b7294bc04ebbde9184b77ec`，具体主设计见各条目 |
| CampusClaw 局部源码基线 | `pi-mono-java@f61906b9136246ca60f333704b6fc92b5420d0ec`；仅证明证据表所列文件与符号，不代表最新远端或全部模块 |
| 核验范围 | M01 的 Loop/控制消息扩展点、M06 的 Controller/分派/回执/流缓冲源码；Claude 公共流与历史文档 |
| 验证边界 | 静态源码与文档核对，未执行产品集成测试；其余模块与基线的专项差异待补证 |

## 1. 阅读方式与权威边界

先从模块问题理解 CampusClaw 的职责，再比较同层基线，最后看实现状态和验证边界。
各模块主设计维护当前方案、主图、精确契约入口和验收；本文维护比较结论及其出处。
正文中的“目标”不等于已经上线，代码存在也不等于通过集成验收。

比较必须区分 Provider 增量、Agent 内部事件、服务 API、客户端预览和持久化记录。
不同系统都使用 SSE，不能证明它们具有相同的事件范围、恢复或取消语义。
完整模块归属与主设计只在[模块索引](../../README.md#module-index)登记；这里维护比较问题与覆盖状态。

## 2. 基线登记与证据范围

固定参考点与选用原则来自 [Agent Runtime 参考基线](../../AGENTS.md#agent-runtime-参考基线)。
下表登记的 commit 不是全量核验声明。使用其他 commit 时，条目必须同时记录旧值、新值和受影响结论。

| 基线 | 固定参考点 | 用于哪些问题 | 本文证据状态 |
|---|---|---|---|
| pi | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` | Runtime 内核、消息/Tool 生命周期、Session 分支与压缩 | A01 已核对 Loop 和 Agent 类型；Session、协议快照等未在本文重新核验 |
| Claude Managed Agents | 官方文档，核对日期 `2026-09-14`；无服务端源码 commit | 公共 Session API、preview 与历史对账 | A02 已核对公开流与 List Events；仍为 Beta，只证明公开契约 |
| Codex harness | `d58d0e5841e0de08e251673db2d5af8cf3a1ad51` | Provider typed event、Turn/Item 客户端生命周期 | 已登记，待 M02/M07 专项源码核验 |
| OpenCode | `849c2598abc7d2b40261e74b5826bc74ffc78308` | 多客户端、live/durable 分类与 sequence 回放 | 已登记，待 M06 专项源码核验；v2 源码能力不能自动视为稳定公开契约 |
| DeepSeek Harness | `0a53fb55bea101816fa226bb964ae2bed71c343b`，`dsh-0.1.2-alpha.2` | 完整事件溯源与 token 级回放的成本上限 | 已登记，待 M04/M06 专项源码核验；保留 alpha 成熟度边界 |

没有同层、同范围证据时填“未核验”或说明“不适用”的理由，不以功能勾选或总分给系统排名。
公司认证、租户隔离、凭据传递、审计和数据保留是 CampusClaw 产品约束，不能因为基线没有相同名词就删除。

## 3. 按模块维护的对比问题

| 模块 | 需要解释的架构问题 | 主基线及辅助对照 | 条目与待补证范围 |
|---|---|---|---|
| M01 · Runtime 与多 Agent | Loop 扩展能力如何与产品准入分离；父子执行如何隔离和终止 | pi；Codex、DeepSeek 辅助 | [A01](#a01)覆盖 Loop 与消息准入边界；父子生命周期待补证 |
| M02 · 模型与 Provider | Provider 原始事件在哪一层归一化；模型目录与调用权威归谁 | Codex；pi 辅助 | 待核对适配器、领域事件、取消链及错误投影 |
| M03 · Tool 与受管环境 | 工具发现、参数校验、权限、执行和副作用重试分别由谁负责 | pi；其他基线按具体执行问题选择 | 待补证，不用工具数量代替执行模型比较 |
| M04 · 上下文与持久化 | 模型上下文、历史、分支与压缩如何区分；哪些事件值得保存 | pi；DeepSeek 辅助 | 待补证；不得默认 token 全量落盘 |
| M05 · Command 与 Skill | 清单和执行如何共享解析；命令、Skill 与 Tool 的边界是什么 | pi | 待补证；不从存在 SKILL.md 推导相同执行机制 |
| M06 · 事件与服务边界 | 写入与观察是否分离；流绑定谁；断线如何恢复；控制状态谁权威 | Claude；OpenCode，必要时 pi/DeepSeek | [A02](#a02)覆盖 Claw/Mate 分层与流范围；数据库、跨实例控制和回放专项待补证 |
| M07 · 前端与渠道 | preview 何时被权威内容替换；Turn/Item 与产品 UI 如何映射 | Codex；Claude 辅助 | 待核对实际客户端 reducer、恢复及取消行为 |
| M08 · 元数据与配置 | 定义、发布快照和运行对象如何分离；刷新如何影响活动执行 | pi；托管产品仅对照公开资源 | 待补证；不推断托管产品内部表结构 |
| M09 · 附件与文件 | 文件服务与 Agent 工作区是什么关系；何时解析与授权 | pi；托管产品公开文件契约按需核对 | 待补证；明确企业产品约束 |
| M10 · 调度与并发 | Session 准入、Tool 并行和全局容量分别如何限制 | pi；OpenCode/DeepSeek 按问题补充 | 待核验并发设计与实测依据；不声称虚拟线程自动解决容量问题 |
| M11 · 可观测性与测试 | 日志、审计历史与模型上下文如何分开；如何证明差异可接受 | 按验证对象选基线，不设统一主基线 | 待补证；区分测试存在、测试运行和生产观测 |

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

| 比较维度 | Claude Managed Agents 公开契约 | CampusClaw 内部目标 | Mate 公共 Chat 目标 |
|---|---|---|---|
| 提交与观察 | 发送事件、读取流与历史分离 | 同一 POST 接受事件并返回对应 SSE；另有 GET 历史 | POST 返回完整用户事件 JSON；独立 GET Chat live SSE；另有 GET 历史 |
| 连接绑定 | 提供 Session 及 Thread 的读取流 | 绑定本次请求对应的执行段或控制结果；对应 idle 后关闭，含 confirming | Chat 级连接可跨执行与空闲；idle 不关闭连接 |
| 增量与权威 | preview 临时且不重放，完整消息用于对账 | delta 作预览，完整事件用于历史对账 | 同 ID completed 替换 preview，完整公共历史用于对账 |
| 断线恢复 | 重开流并查询历史 | 查询历史；不恢复已经断开的 POST，不自动重发已接受写入 | 重开公共流并查询历史，不自动重发 POST |
| 证据性质 | 2026-09-14 核对的 Beta 文档；不证明服务端内部实现 | 主设计目标；J02/J03/J04/J05 仅证明下述局部实现 | Mate 文档 1.5.0 的 target-only 契约；未核对 mate-service 源码 |

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

**实现状态与验收。** 两份目标各自有效；Claw 为局部源码已核验，Mate 保持 target-only。
应分别验证回执先行、确认分段、中断结果绑定、慢连接、无首帧结果不确定和断线历史对账；
再验证公共流跨内部执行段持续存在，以及公共身份与权限投影。验收通过前不能宣称“两跳已全部实现”。

**讲解要点。** SSE 只规定流式响应格式。CampusClaw 内部把连接绑定到本次请求的执行段，
Mate 公共层把连接绑定到 Chat；Claude 是公开流与历史对账的参考。
我们采纳临时 preview 与权威记录的区分，同时保留自己的产品边界。
代价是两跳需要明确的事件桥接；内部入口代码已经存在，公共桥接还不能用设计文档冒充实现证据。

<a id="source-evidence"></a>

## 6. 源码证据与更新边界

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

请求级 SSE 主设计的旧实现核对点为 `918005ee8ccc88d179fc31a0de17a92b4a01383b`。
在本文的新核对点，J02/J03/J04 已出现新的请求 VO、三事件分派和回执启动顺序；
因此该主设计 §6 中“三输入联合请求和完整首帧还需改造”的旧差距只适用于原基线，不能直接用于判断新提交。
这不改变目标方案，也不自动关闭该模块其余实现差距；完整差距表的复核仍需扩大到持久化、控制和集成测试。

## 7. 条目格式与维护检查

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

- **设计状态**：待决策、已确认目标、非本期范围。提议新增但没有对应实现的方案标记 target-only。
- **实现状态**：未核验、已核验且无对应实现、局部已核验、已核验并完成所列验收。
  target-only 必须同时说明是未取得源码证据，还是在明确源码范围内确认不存在；不能将两者混用。

每次模块设计变更，检查相关条目的问题、目标、差异分类、代价和验收是否变化；
每次实现进度更新，先读新源码并记录新旧基线，不能只改状态文字。
基线升级只更新受影响结论，正文保留当前有效比较；历史变化通过 Git 和一句话版本记录追溯。
对比图如确有必要，遵守仓库 PlantUML 规则；已有目标类图通过主设计复用，不在本文复制另一套图。

## 8. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-09-14 | 建立按模块维护的基线对比、证据与状态格式，并补充 Loop 准入和两跳事件流的局部核验条目。 |
