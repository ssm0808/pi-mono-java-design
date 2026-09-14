# CampusClaw 与 Agent 基线的架构对比

[返回总体架构](../README.md) · [模块索引](../../README.md#module-index)

| 属性 | 值 |
|---|---|
| 文档版本 | 1.9.0 |
| 更新日期 | 2026-09-14 |
| 文档职责 | 按模块解释架构取舍与实现差距，支撑设计讨论、架构答辩和面试 |
| 设计依据 | `pi-mono-java-design@6026ba48e58449e6d64e6e91688b04a2fdd562e2`，具体主设计见各条目 |
| CampusClaw 局部源码基线 | `pi-mono-java@f61906b9136246ca60f333704b6fc92b5420d0ec`；仅证明证据表所列文件与符号，不代表最新远端或全部模块 |
| 计划模式专项基线 | A03 使用 DeepSeek `0a53fb55`、Java `09b32d8e`；旧 Java `f61906b` 与该专项相关源码相同，完整 SHA 与路径见专项证据 |
| 核验范围 | M01 的 Loop/控制消息扩展点、M06 的 Controller/分派/回执/流缓冲与配置更新源码；A04 的五基线接口边界；Claude 公共 Session/Agent/流与历史文档；A05 的 TODO 工具结果、Java 提交和客户端投影接入点；A03/A05 的计划与实施提示词；A06 的 M02 Provider 身份、注册框架、模型预置及 SDK 依赖；M08 的 Agent 默认 mode、目录快照、Session 初始化与元数据组合查询顺序 |
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
| pi | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` | Runtime 内核、消息/Tool 生命周期、Session 分支与压缩 | A01 已核对 Loop 和 Agent 类型，A04 已核对配置 RPC，A05 核对 todo 示例的工具结果恢复，A06 核对 Provider 组合与模型注册；Session 树与完整协议快照仍待专项核验 |
| Claude Managed Agents | 官方文档，核对日期 `2026-09-14`；无服务端源码 commit | 公共 Session API、preview 与历史对账 | A02/A04/A05 已核对公开流、List Events、Session 更新、配置限制和通用 custom tool 交互；仍为 Beta，只证明公开契约 |
| Codex harness | `d58d0e5841e0de08e251673db2d5af8cf3a1ad51` | Provider typed event、Turn/Item 客户端生命周期 | A04 已核对配置协议，A05 核对指定模型的 update_plan 指令及 Handler；Provider 与完整 M07 生命周期仍待专项核验 |
| OpenCode | `849c2598abc7d2b40261e74b5826bc74ffc78308` | 多客户端、live/durable 分类与 sequence 回放 | A04 已核对 Session 配置/消息/v2 操作，A05 核对 todowrite 描述与模型提示词；事件流仍待专项核验；v2 源码能力不能自动视为稳定公开契约 |
| DeepSeek Harness | `0a53fb55bea101816fa226bb964ae2bed71c343b`，`dsh-0.1.2-alpha.2` | 计划模式；完整事件溯源与 token 级回放的成本上限 | A03/A04/A05 已核对计划插件、preset、Session 配置接口和 todo_write 完整列表；完整日志仍待 M04/M06 专项核验；保留 alpha 成熟度边界 |

没有同层、同范围证据时填“未核验”或说明“不适用”的理由，不以功能勾选或总分给系统排名。
公司认证、租户隔离、凭据传递、审计和数据保留是 CampusClaw 产品约束，不能因为基线没有相同名词就删除。

## 3. 按模块维护的对比问题

| 模块 | 需要解释的架构问题 | 主基线及辅助对照 | 条目与待补证范围 |
|---|---|---|---|
| M01 · Runtime 与多 Agent | Loop 扩展能力如何与产品准入分离；父子执行如何隔离和终止 | pi；Codex、DeepSeek 辅助 | [A01](#a01)覆盖 Loop 与消息准入；[A03](#a03)覆盖计划模式接入与 Child 模式传递，其他父子生命周期待补证 |
| M02 · 模型与 Provider | 内置提供方如何削减而保留扩展；模型目录与调用权威归谁；原始事件在哪层归一化 | 本次裁剪/注册采用 pi；事件归一化专项采用 Codex | [A06](#a06)覆盖 CampusMate 身份、注册框架和 SDK 削减；Codex 事件归一化对比及完整取消链仍待专项核验 |
| M03 · Tool 与受管环境 | 工具发现、参数校验、权限、执行和副作用重试分别由谁负责 | pi；其他基线按具体执行问题选择 | [A03](#a03)覆盖稳定工具定义与计划 Prompt；[A05](#a05)覆盖 TODO 工具及事件边界；其他工具问题待补证 |
| M04 · 上下文与持久化 | 模型上下文、历史、分支与压缩如何区分；哪些事件值得保存 | pi；DeepSeek 辅助 | [A03](#a03)覆盖模式/审核恢复；其他上下文与存储比较待补证，不默认 token 全量落盘 |
| M05 · Command 与 Skill | 清单和执行如何共享解析；命令、Skill 与 Tool 的边界是什么 | pi | 待补证；不从存在 SKILL.md 推导相同执行机制 |
| M06 · 事件与服务边界 | 写入与观察是否分离；流绑定谁；断线如何恢复；控制状态谁权威 | Claude；OpenCode，必要时 pi/DeepSeek | [A02](#a02)覆盖 Claw/Mate 分层与流范围；[A03](#a03)补充计划审核所复用的数据库确认交接，完整回放专项待补证；[A04](#a04)覆盖 Session 配置更新；[A05](#a05)覆盖 TODO 复用通用事件 |
| M07 · 前端与渠道 | preview 何时被权威内容替换；Turn/Item 与产品 UI 如何映射 | Codex；Claude 辅助 | [A05](#a05)核对既有事件合并与根执行归属，TODO 投影为 target-only；其余展示与取消行为待补证 |
| M08 · 元数据与配置 | 定义、发布快照和运行对象如何分离；刷新如何影响活动执行 | pi；托管产品仅对照公开资源 | Agent.mode 专项已核对 Mate 956b547f / Runtime 09b32d8e；默认值链为 target-only，见 A03 和元数据主设计；元数据组合查询顺序另在 Mate `9dd5d85e` 核对，见 J06；发布事务一致性仍待补证 |
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

**渠道同步。** [飞书目标设计](../01-CampusClaw多Agent运行时/channel-feishu-v1-design.md#73-不确定结果恢复) 同步采用当前 eventId/sourceEventId，不再依赖已撤销的公开 Entry 水位。无可靠回执时不能由空历史或同文消息证明未接受，因此保留人工对账。这是适配当前契约的安全加固，代价是部分故障不能自动恢复提交；未新增幂等字段、自动接管或副作用重跑能力。

**重新评估条件。** 如果内部调用方需要脱离写请求独立订阅、多客户端共同观察或可恢复读流，
应重新评估连接范围、权威事件来源和恢复契约；这会改变架构边界，不能仅增加一个 GET 路径就视为完成。

**实现状态与验收。** 两份目标各自有效；Claw 为局部源码已核验，Mate 保持 target-only。
应分别验证回执先行、确认分段、中断结果绑定、慢连接、无首帧结果不确定和断线历史对账；
再验证公共流跨内部执行段持续存在，以及公共身份与权限投影。验收通过前不能宣称“两跳已全部实现”。

**讲解要点。** SSE 只规定流式响应格式。CampusClaw 内部把连接绑定到本次请求的执行段，
Mate 公共层把连接绑定到 Chat；Claude 是公开流与历史对账的参考。
我们采纳临时 preview 与权威记录的区分，同时保留自己的产品边界。
代价是两跳需要明确的事件桥接；内部入口代码已经存在，公共桥接还不能用设计文档冒充实现证据。

<a id="a03"></a>

## 6. A03 · Agent 默认模式、Session 当前模式与计划审核

| 维度 | 结论 |
|---|---|
| 所属模块与主设计 | M01/M03/M04/M06/M08，关联 M07；[计划模式主设计](../06-CampusClaw计划模式/README.md)集中维护目标结构、接口增量、恢复及验收，复用其中唯一全局类图 |
| 架构问题 | 如何让 Agent 提供默认工作模式、Session 独立维护当前模式，同时保持 Tool/Skill 元数据稳定并支持方案审核？ |
| DeepSeek 已观察行为 | 固定 alpha 提交的 `PlanModeController` 根据计划状态提供 `plan:policy`；退出工具持续注册，以完整 Markdown 请求用户审核；批准后在后续 step 退出。`stateVersion=3` 属于投影结构版本，不是业务计划版本。固定链接与符号见[专项源码证据 §2](../06-CampusClaw计划模式/source-evidence.md#2-deepseek-计划模式)。 |
| CampusClaw 已观察实现 | Java `09b32d8e` 已具备统一 Session 工厂、逐轮读取系统 Prompt、确认等待、数据库决定和固定续跑段；本专题相关源码与 `f61906b` 相同。工具确认由前端 executionState/loadHistory 根据事件恢复，Session VO 不暴露待确认工具。当前没有计划模式、计划工具或计划事件；RuntimeSessionController 没有通用更新方法，既有配置服务已支持 ETag、idle 和更新结果组装。源码范围见[专项证据 §4](../06-CampusClaw计划模式/source-evidence.md#4-campusclaw-现有接入点)，未运行计划集成测试。 |
| CampusClaw 目标 | Agent 默认 mode 只初始化新 Session，Session 独立维护当前模式；模式更新复用统一 Session POST。计划以完整事件身份审核，沿用原执行与数据库确认交接，批准后以 build 指令续跑；Tool/Skill 定义保持稳定。具体字段、Prompt 和恢复归计划与元数据主设计。 |
| 差异分类 | 产品约束：Agent 默认 mode 与 Session 当前模式分离、Tool/Skill 元数据稳定、当前模式由 Session 更新、只允许 idle 主动切换、Child 调用时继承模式；架构变更：在既有配置服务增加 Session 更新，并将进程内审核接入 HTTP 和已有数据库执行控制；安全加固：精确目标、单次消费、停止竞争和两跳身份校验。 |
| 提示词依据 | DeepSeek standard preset 明确禁止规划期 todo_write；CampusClaw 同样仅在 build 记录实施进度。根与 Child 分别组合审核/返回父结果段，批准后替换为实施与 TODO 段。精确正文与矩阵见[提示词设计](../06-CampusClaw计划模式/plan-policy.md)，固定符号见[专项证据 §7](../06-CampusClaw计划模式/source-evidence.md#7-提示词组合与逐项更新约束)。 |
| 具体理由 | 模式已有明确的 Session 资源归属，更新操作复用其身份、版本与事务，统一四类属性入口，并明确组合原子性。混合查询与变更工具不能依靠新增一个静态只读字段准确表达每次调用用途；稳定字段与工具定义让规划规则独立演进。公共审核需要可对账的事件身份，原有工具权限不能表示对整份方案的批准。展示恢复与锁内接受分离，沿用既有工具确认方式，避免 Session 响应随具体交互增加指针。 |
| 默认值证据与代价 | Mate 956b547f 的 Agent DTO/VO/DefinitionColumns 无 mode；Runtime 09b32d8e 的 prepare 复用目录、refresh 强制发布、create 从解析快照初始化，均无 mode。目标增加字段传播与创建复制，修改 Agent 后须先完成目录发布，不能宣称新 Session 即时读取远端最新值；既有 Session 不被重置。这是产品配置扩展，不是 DeepSeek/Claude 同名字段。完整路径及符号见[专项证据](../../03-数据与存储/02-Agent元数据GaussDB/README.md#23-mode-专项源码核对)。 |
| 收益与代价 | 不扩充工具元数据、不增加第二套 Loop 或 Session 待审字段；需要新增模式和审核事件、确认记录及客户端卡片。刷新必须补齐相关事件，缺页或状态矛盾时禁用审核；跨请求读取仍可能过期，确认始终在服务端重新校验。提示词约束不提供服务端强制只读保证；进程失联自动接管不在该功能承诺中。 |
| 备选与重新评估条件 | 本期不采用副作用白名单、独立 Plan CRUD、Cordis 插件容器或 token 全量日志。若产品要求规划期绝不产生副作用，应单独设计可执行的权限边界，不能将 Prompt 遵循率当作保证。 |
| 设计 / 实现状态 | target-only 推荐设计；在已核验范围确认无对应计划实现，复用能力仅经静态源码核验，尚无计划模式端到端验收。 |
| 验收重点 | 见[主设计 §8](../06-CampusClaw计划模式/README.md#8-实施切片与验收)：模式与消息接受竞争、工具定义稳定、eventId 精确审核、跨实例单次领取、中断与恢复、Child 模式及提示词场景评估。 |

**讲解要点。** DeepSeek 提供了计划模式与工具元数据解耦的参考。CampusClaw 保留这一边界，
以统一 Session POST 更新承载工作模式，把计划审核接入已有 Session Events 和数据库确认续跑；计划正文用事件身份固定，工具授权继续独立执行。
代价是新增审核持久化与客户端交互，同时必须承认提示词约束和失联执行恢复的能力边界。


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
| 设计 / 实现状态 | 四类统一 POST 为已确认目标；组合事务、mode 与消费者迁移均为 target-only。静态核对未代替 Java/数据库/跨实例测试。 |
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

## 6.2 A05 · TODO 进度复用通用工具结果

| 维度 | 结论 |
|---|---|
| 所属模块与主设计 | M03/M06/M07，关联 M01/M04；[TodoUpdate](../06-CampusClaw计划模式/todo-update.md) 维护工具契约、生命周期与验收，复用计划模式唯一全局类图 |
| 架构问题 | 模型持续更新执行步骤时，如何保持公共事件和元数据稳定，并在刷新后恢复相同进度？ |
| Claude 公开契约 | 官方 Beta 文档 2026-09-14 核对：自定义工具复用 agent.custom_tool_use/user.custom_tool_result，等待外部结果用 requires_action；没有公开内置 TODO 工具。只证明通用业务承载方式，无服务端源码与内部存储结论。 |
| DeepSeek 源码 | 固定 0a53fb55 的 tool-todo 通过 todo_write 整份替换 content/status 列表，追加 todo/write 日志，latest snapshot 投影按下一 turn/start 清空；其 alpha 日志格式不成为 CampusClaw 公共协议。 |
| pi 源码 | 固定 5cd93f68 的 todo 示例从工具结果 details 恢复列表，证明进度可以由通用结果重建；示例扩展不等于核心公共 TODO 事件。 |
| CampusClaw 已观察实现 | Java 09b32d8e 已有文本工具结果、TurnEndEvent 批次结果持久化及同形 SSE；前端有 eventId 去重、历史顺序和根消息关联。固定 modules/frontend/src 范围没有 TodoUpdate/TodoWrite 或进度投影；未运行新增工具测试。 |
| CampusClaw 目标 | TodoUpdate 仅用于 build 实施进度；plan 调研和修订不调用。由 Runtime 内置工具执行，成功结果文本返回完整 JSON 清单；只用现有 agent.tool_call/agent.tool_result，客户端从匹配的已提交成功结果派生进度。每个根执行独立，审核续跑保持归属。 |
| 调用时机约束 | DeepSeek DESCRIPTION_TAIL 与 OpenCode todowrite 描述要求完成即更新、不积攒完成；指定 Codex 模板同时允许一次更新多项，不能视为严格一项一次的硬规则。CampusClaw 用固定 description 和 build 提示词要求实际完成及验证后立即更新，同次可完成上一项并启动下一项；代码只验证参数，不证明业务完成。出处见[§7](../06-CampusClaw计划模式/source-evidence.md#7-提示词组合与逐项更新约束)。 |
| 差异分类 | 架构变更：采用 Claude 通用工具承载风格，但保留服务端工具执行和现有事件名；采用成功 ToolResult 作为唯一快照记录，省去 DeepSeek 的独立 TODO 日志。产品约束：元数据与公共外层字段稳定、首版 Runtime 根入口、仅 build 实施进度、单进行中任务。 |
| 理由与代价 | 既有工具结果已经是可恢复完整记录，无需再同步 TODO 表与专用事件；代价是客户端需识别工具内容，且进度等待现有批次结果提交，不能承诺每次 Java 工具返回即推送。完整列表每次都占用上下文，需限制大小。 |
| 备选与重新评估条件 | 当前不新增 TODO CRUD、agent.todo_updated、Session todos 或结构化公共结果字段。若需要独立任务身份、多人编辑、调度依赖或工具完成即刻提交，应重新设计任务资源与提交边界，不能直接扩充显示清单语义。 |
| 设计 / 实现状态 | 已确认方向，target-only；通用复用链局部源码已核验，TodoUpdateTool、枚举/profile 和 deriveTodos/面板待实现。 |
| 验收与证据 | [T1～T4](../06-CampusClaw计划模式/todo-update.md#6-实施切片与验收) 覆盖 plan 不调用、批准后建清单、逐项完成更新、成功提交、失败保留、跨根隔离、分页/断线和两跳关联；固定路径与符号见[专项源码证据 §6](../06-CampusClaw计划模式/source-evidence.md#6-todo-update-基线与接入证据)。 |

**讲解要点。** TODO 描述 Agent 报告的步骤进度，方案审核决定是否继续实施，两者职责不同。CampusClaw 借鉴 Claude 的通用工具事件，将完整任务清单放入成功结果，前端只做可重建的投影。这样保持 API 外层稳定，代价是需要工具级解析和批次提交等待；不能把清单完成当作业务验收或 Runtime 终态。

<a id="a06"></a>

## 6.3 A06 · 只内置 CampusMate，保留 Provider 扩展框架

| 维度 | 结论 |
|---|---|
| 模块与主设计 | M02，关联 M08/M11；[模型与 Provider 主设计 §4](../../02-服务与接口/03-模型管理Provider契约/README.md#4-provider-与配置)维护命名、削减及依赖边界；复用其[唯一全局目标类图](../../02-服务与接口/03-模型管理Provider契约/java_provider_alignment.svg)。 |
| 架构问题 | 企业产品默认只从 CampusMate 调用模型时，是否必须同时删除通用 Provider 注册能力？ |
| pi 已观察行为 | 固定 `5cd93f688aaab89dbb6dfa4aca535f21796ae185` 的 `packages/ai/src/models.ts`：`Provider` 持有身份、认证、目录和流能力；`ModelsImpl.requireProvider` 按身份查找；`createProvider` 组合模型目录与单个/按 API 分派的流实现。`packages/ai/src/providers/anthropic.ts`：`anthropicProvider` 通过该工厂组装厂商能力。源码证明组合与扩展边界，不要求每个产品交付全部厂商。 |
| CampusClaw 已观察实现 | Java `f61906b9136246ca60f333704b6fc92b5420d0ec` 已有独立 Mate WebClient/Mapper/Parser；身份仍为 `mate-model-manager`，四个第三方适配器、第三方模型预置与两个 SDK 仍存在。AI 服务优先身份路由、再查 API；Runtime 从 Agent 快照解析 Mate 模型。精确路径与符号见[Provider 源码证据](../../02-服务与接口/03-模型管理Provider契约/source-evidence.md) J-AI-01～08。 |
| CampusClaw 目标 | 唯一内置实现为 `CampusMateProvider`、ID 为 `campusmate`、enum 为 `CAMPUSMATE`；删除厂商适配器/预置/SDK，保留两种注册表、接口、公共类型和 JSON 加载；不增加目录 HTTP、身份别名或存量迁移。 |
| 差异分类 | 产品约束：提供方集中在 CampusMate，取消开箱厂商直连；产品身份变更：名称直接切换。保留既有双注册表是本次架构边界，不借裁剪引入 ProtocolAdapter 重构。既有网关认证与事件契约保持独立。 |
| 理由与代价 | 删除发布产品不再使用的厂商代码和预置数据，减少 SDK 升级维护范围；代价是旧配置需更新、旧历史 Provider 不归一、直连用户需迁至 CampusMate 或自行提供扩展。通用注册仍有维护成本，未实测包体积或性能收益。 |
| 备选与重新评估条件 | 本次不删除扩展框架，也不只关闭 Spring Bean 后继续携带 SDK。若未来需彻底禁用自定义提供方、恢复厂商直连或兼容存量身份，需重新确定产品入口和迁移边界。 |
| 设计状态 / 实现状态 | 已确认目标、target-only / 局部源码已核验，确认当前范围仍使用旧名称与第三方实现；仅当前 AI 运行时 Maven 依赖树已解析成功，未修改代码、未执行削减后产品测试。 |
| 验收与证据 | 主设计 S1～S4 覆盖新身份、空注册表、自定义扩展、外部 JSON、无隐式 fallback、Mate 协议回归、SDK/镜像及旧历史原值保留；命名后的测试 selector 待实际实现才替换。 |

**讲解要点。** pi 把提供方、模型和协议实现组合起来；CampusClaw 保留这个扩展思路，但企业产品
默认只交付 CampusMate。减掉的是厂商实现、预置和 SDK，通用 AI 消息与注册仍可复用。
代价是失去开箱直连及旧身份兼容；目前独立 Mate 调用链已存在，裁剪和新名称仍待实现验收。

<a id="source-evidence"></a>

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

- **设计状态**：待决策、已确认目标、非本期范围。提议新增但没有对应实现的方案标记 target-only。
- **实现状态**：未核验、已核验且无对应实现、局部已核验、已核验并完成所列验收。
  target-only 必须同时说明是未取得源码证据，还是在明确源码范围内确认不存在；不能将两者混用。

每次模块设计变更，检查相关条目的问题、目标、差异分类、代价和验收是否变化；
每次实现进度更新，先读新源码并记录新旧基线，不能只改状态文字。
基线升级只更新受影响结论，正文保留当前有效比较；历史变化通过 Git 和一句话版本记录追溯。
对比图如确有必要，遵守仓库 PlantUML 规则；已有目标类图通过主设计复用，不在本文复制另一套图。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
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
