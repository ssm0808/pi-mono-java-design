# CampusClaw 与 Agent 基线的架构对比

[返回总体架构](../README.md) · [模块索引](../../README.md#module-index)

| 属性 | 值 |
|---|---|
| 文档版本 | 1.13.0 |
| 更新日期 | 2026-09-15 |
| 文档职责 | 按模块解释架构取舍与实现差距，支撑设计讨论、架构答辩和面试 |
| 设计依据 | `pi-mono-java-design@0233763eb846a297cd390eda1f2da05004c91dd7`，具体主设计见各条目 |
| CampusClaw 局部源码基线 | `pi-mono-java@f61906b9136246ca60f333704b6fc92b5420d0ec`；仅证明证据表所列文件与符号，不代表最新远端或全部模块 |
| 计划模式专项基线 | A03 使用 DeepSeek `0a53fb55`、Java `09b32d8e`；旧 Java `f61906b` 与该专项相关源码相同，完整 SHA 与路径见专项证据 |
| 前端专项基线 | A07：Java `29ebec6a8cad99896414211cda28c6fffec71bee`；Codex 固定 `d58d0e58`；官方界面与协议 2026-09-15 核对 |
| 提问专项基线 | A08：Java 开发分支 699f929；DeepSeek 0a53fb55；pi 5cd93f68；Claude 官方文档 2026-09-15；不升级其他条目的旧核验范围 |
| 核验范围 | A07 的模式入口、TUI 实施选择、方案/任务分离与前端接入范围；M01 的 Loop/控制消息扩展点、M06 的 Controller/分派/回执/流缓冲与配置更新源码；A04 的五基线接口边界；Claude 公共 Session/Agent/流与历史文档；A03 的计划文件/正文载体；A05 的三基线显式任务事件、Java 多事件事务与客户端消费接入点；A03/A05 的计划与实施提示词；A06 的 M02 Provider 身份、注册框架、模型预置及 SDK 依赖；M08 的 Agent 默认 mode、目录快照、Session 初始化与元数据组合查询顺序 |
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
| Codex harness | `d58d0e5841e0de08e251673db2d5af8cf3a1ad51` | Provider typed event、Turn/Item 客户端生命周期 | A04 已核对配置协议，A05 核对指定模型的 update_plan 指令及 Handler；A07 核对 TUI 方案实施与 plan Item/TODO 分离；Provider 与其余 M07 生命周期仍待专项核验 |
| OpenCode | `849c2598abc7d2b40261e74b5826bc74ffc78308` | 多客户端、live/durable 分类与 sequence 回放 | A04 已核对 Session 配置/消息/v2 操作，A05 核对 todowrite 描述与模型提示词；事件流仍待专项核验；v2 源码能力不能自动视为稳定公开契约 |
| DeepSeek Harness | `0a53fb55bea101816fa226bb964ae2bed71c343b`，`dsh-0.1.2-alpha.2` | 计划模式；完整事件溯源与 token 级回放的成本上限 | A03/A04/A05 已核对计划插件、preset、Session 配置接口和 todo_write 完整列表；完整日志仍待 M04/M06 专项核验；保留 alpha 成熟度边界 |

没有同层、同范围证据时填“未核验”或说明“不适用”的理由，不以功能勾选或总分给系统排名。
公司认证、租户隔离、凭据传递、审计和数据保留是 CampusClaw 产品约束，不能因为基线没有相同名词就删除。

## 3. 按模块维护的对比问题

| 模块 | 需要解释的架构问题 | 主基线及辅助对照 | 条目与待补证范围 |
|---|---|---|---|
| M01 · Runtime 与多 Agent | Loop 扩展能力如何与产品准入分离；父子执行如何隔离和终止 | pi；Codex、DeepSeek 辅助 | [A01](#a01)覆盖 Loop 与消息准入；[A03](#a03)覆盖计划模式接入与 Child 模式传递，其他父子生命周期待补证 |
| M02 · 模型与 Provider | 内置提供方如何削减而保留扩展；模型目录与调用权威归谁；原始事件在哪层归一化 | 本次裁剪/注册采用 pi；事件归一化专项采用 Codex | [A06](#a06)覆盖 CampusMate 身份、注册框架和 SDK 削减；Codex 事件归一化对比及完整取消链仍待专项核验 |
| M03 · Tool 与受管环境 | 工具发现、参数校验、权限、执行和副作用重试分别由谁负责 | pi；其他基线按具体执行问题选择 | [A03](#a03)覆盖稳定工具定义与计划 Prompt；[A05](#a05)覆盖 TODO 工具及事件边界；[A08](#a08)覆盖结构化提问；其他工具问题待补证 |
| M04 · 上下文与持久化 | 模型上下文、历史、分支与压缩如何区分；哪些事件值得保存 | pi；DeepSeek 辅助 | [A03](#a03)覆盖模式/审核恢复；其他上下文与存储比较待补证，不默认 token 全量落盘 |
| M05 · Command 与 Skill | 清单和执行如何共享解析；命令、Skill 与 Tool 的边界是什么 | pi | 待补证；不从存在 SKILL.md 推导相同执行机制 |
| M06 · 事件与服务边界 | 写入与观察是否分离；流绑定谁；断线如何恢复；控制状态谁权威 | Claude；OpenCode，必要时 pi/DeepSeek | [A02](#a02)覆盖 Claw/Mate 分层与流范围；[A03](#a03)补充计划审核所复用的数据库确认交接，完整回放专项待补证；[A04](#a04)覆盖 Session 配置更新；[A05](#a05)覆盖后端显式任务事件 |
| M07 · 前端体验 | preview 何时被权威内容替换；Turn/Item 与产品 UI 如何映射 | Codex；Claude 辅助 | [A05](#a05)核对既有事件合并与根执行归属，TODO 投影为 target-only；[A07](#a07)覆盖计划交互与 Codex 对齐，[A08](#a08)覆盖问题卡与答案恢复；其他展示仍待补证 |
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

## 6.2 A05 · 后端显式任务更新与恢复

| 维度 | 结论 |
|---|---|
| 所属模块与主设计 | M03/M06/M07，关联 M01/M04；[TodoUpdate](../06-CampusClaw计划模式/todo-update.md) 维护工具、提交与恢复，复用计划模式全局目标类图 |
| 架构问题 | 如何让前端直接获得执行清单，同时保持工具与 Session 元数据稳定、断线后恢复相同进度？ |
| Claude 公开契约 | 官方 Beta 文档 2026-09-15 核对：通用自定义工具事件与持久化历史；未公开原生 TodoUpdate 或同名更新事件。只借鉴权威历史与对账，不推断内部 TODO 实现。 |
| DeepSeek 源码 | 固定 0a53fb55 的 tool-todo 追加 todo/write 全量快照，下一 turn/start 清空投影；采用显式快照思路，不照搬 alpha 日志格式。 |
| OpenCode / Codex 源码 | OpenCode 849c2598 的 SessionTodo.update 替换表后发布 todo.updated（固定 v2 源码）；Codex d58d0e58 的 PlanHandler 发 PlanUpdate，App Server 文档定义 turn/plan/updated。两者证明任务更新可由后端显式发布，不能混称同一公共传输协议。 |
| pi 源码 | 固定 5cd93f68 的 todo 示例从工具结果 details 恢复；这是另一种客户端派生方案，不作为当前 CampusClaw 进度消费方式。 |
| CampusClaw 已观察实现 | Java 09b32d8e 的 persistToolResults 已在批次结果边界提交；appendEntry 接收事件列表，仓库记录实际投影数量；尚无 TODO 工具与专用事件/面板，未运行新增产品测试。 |
| CampusClaw 目标 | build 根执行使用 TodoUpdate，plan 不记录调研进度；成功工具结果同事务生成 agent.todo_updated。前端直接消费 todos；新消息隔离清单，审核续跑保持原根。 |
| 调用时机约束 | 工具描述与 build 提示词要求任务实际完成并验证后立即更新，同次可完成上一项并开始下一项；值校验不证明业务完成，模型仍可能漏调用。基线提示词证据见[§7](../06-CampusClaw计划模式/source-evidence.md#7-提示词组合与逐项更新约束)。 |
| 差异分类 | 架构变更：后端负责将最终工具结果映射为公共任务事件，复用现有一 Entry 多事件事务。产品约束：build 实施、单进行中、原根作用域、Agent/Tool/Skill 元数据不因 TODO 扩展。 |
| 理由与代价 | 前端无需识别工具名或解析结果文本，事件历史可直接恢复面板；代价是新增公共类型及每次更新的一份持久化快照，读取端需先升级；仍等待批次结果提交。 |
| 备选与重新评估条件 | 不新增 TODO CRUD、Session todos 或 TODO 表；如需独立任务身份、多人编辑、调度依赖或工具方法返回即发布，应另评估资源与提交边界。 |
| 设计 / 实现状态 | 已确认 target-only；TodoUpdateTool、后端 Mapper/DTO/VO/事件分支、applyTodoUpdated 与 Mate 桥接待实现。 |
| 验收与证据 | [T1～T4](../06-CampusClaw计划模式/todo-update.md#6-实施切片与验收)：同源同事务、失败无更新、缺工具记录也可展示、分页/live 对账、跨根与两跳身份；固定路径与符号见[§6](../06-CampusClaw计划模式/source-evidence.md#6-todo-update-基线与接入证据)。 |

**讲解要点。** 方案是待批准的完整设计，TODO 是实施进度。CampusClaw 用后端任务事件让前端直接展示清单，并把该事件与模型工具结果一起提交，避免两次写入不一致。它增加一份事件快照，但不增加元数据字段或任务表；完成状态仍是 Agent 报告，不代替业务验证和执行终态。

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

<a id="a07"></a>

## 6.4 A07 · Codex 交互风格与 CampusClaw 计划语义

| 维度 | 结论 |
|---|---|
| 模块与主设计 | M07，关联 M01/M06；[前端主设计](../04-CampusClaw前端体验/README.md)及[计划交互](../04-CampusClaw前端体验/plan-interaction.md)，复用前端唯一全局组件图。 |
| 架构问题 | 如何采用 Codex 的工作区密度、完整方案与轻量进度展示，同时保持 CampusClaw 的审核续跑和企业边界？ |
| Codex 观察 | 固定 d58d0e58 的 plan_implementation.rs / selection_view_params 提供实施、清上下文实施、继续规划；实施发起带 Default mode 的用户消息。PlanHandler::handle_call 在 Plan mode 拒绝 update_plan，另发 PlanUpdate；App Server 区分方案 Item、任务更新与提问。完整路径与官方 2026-09-15 公开证据见[专项 §1](../04-CampusClaw前端体验/plan-interaction.md#1-源码与交互依据)。TUI 不证明桌面像素布局；官方提问及固定版本方案增量保留实验性边界。 |
| CampusClaw 目标 | 配置聚合到 Composer；完整方案内联审核，批准后原执行续跑，方案收起；后端显式任务快照驱动只读进度；工具授权独立。 |
| 已观察实现 | Java 29ebec6a 的 frontend App/Composer 已有草稿与同位置停止，eventStore 已按事件身份/根消息恢复；runtime 类型、projector 与配置客户端尚无计划模式、审核或任务面板。RuntimeSessionController 仍为 create/get/delete。其他特性分支/部署未核验，前端目标按既定计划模式契约定义。 |
| 差异分类 | 产品约束：常驻模式按钮、O1 暖灰、结构化提问及无工具降级、无清上下文执行/运行中排队；架构变更：审核事件绑定方案并续跑原执行、公共两跳映射；安全加固：缺页禁审、服务端目标复核、写入不自动重放。 |
| 理由与代价 | 阅读与决策相邻，方案、审批与任务不混为一个状态；代价是增加审核投影和恢复协调，结构化提问采用 CampusClaw 自有事件契约；新上下文执行不在范围。提示词规划不构成只读沙箱。 |
| 备选与重评条件 | 不直接复刻 Codex JSON-RPC、clear-context 选项或其品牌。若需要新执行/上下文选择，先重新确定审核目标、凭据、历史与启动权威。 |
| 设计状态 / 实现状态 | 已确定目标、target-only / 所列主线范围局部核验；新 HTML 是设计原型，真实 Java 计划能力与 Mate 公共集成未验收。 |
| 验收 | [PF1～PF5](../04-CampusClaw前端体验/plan-interaction.md#6-组件与接入切片)：模式回执、精确方案、修订新身份、任务完整快照、终态独立、两跳与恢复；浏览器视觉与原型状态分别验证。 |

**讲解要点。** 参考 Codex 的输入邻近设置、方案与进度分离，让用户在同一工作区读方案、做决定、看实施进展。CampusClaw 的审核决定续跑原执行，不照搬 Codex 的新消息实施路径。这个差异保留执行归属，但增加事件映射与恢复要求；已核验主线的计划接入仍需实现与集成验收。

## 6.5 A08 · 结构化提问与原执行续跑

<a id="a08"></a>

| 维度 | 结论 |
|---|---|
| 模块与主设计 | M01/M03/M06/M07；[AskUserQuestion](../06-CampusClaw计划模式/ask-user-question.md)，复用计划交互全局类图与独立问答时序。 |
| 架构问题 | 如何显式关联问题和答案、驱动前端控件，并在回答后继续同一根任务？ |
| 基线证据与行为 | DeepSeek 固定 0a53fb55（alpha）的 tool-ask-user apply/execute、UserQuestionService.ask、types.ts：问题 id、selected/custom、根上下文校验、等待后返回工具结果。pi 固定 5cd93f68 的 runLoop 将工具结果送入下一次模型请求。Claude Managed Agents 官方 Tools/Events 2026-09-15 核对（Beta）：应用提供自定义工具结果和权威历史；无同名原生问题事件声明。完整路径和链接见主设计 §2。 |
| CampusClaw 目标 | AskUserQuestion 在 plan/build 保持相同定义；后端 agent.question 驱动前端，user.question_answer 经现有 POST Events 回答全部问题；原根/模式/凭据保持，plan 无调研 TODO，build 不重置清单。 |
| 已观察实现 | Java 开发分支 699f929f6826b595ed1d0162f6def66e2f84760b（代码17dbb20）已有两类互斥等待、计划审核控制事务和四输入；内置列表及根计划 Prompt 尚无结构化提问。核验路径含 RuntimeActiveExecution、RuntimeEventProjector、RuntimeControlEventService、SessionUserEventRequestVO、PlanReviewPort 和 session_schema.sql；只证明开发分支范围，不代表主线已合入。 |
| 差异分类 | 架构变更：显式公共事件、GaussDB 答案交接及统一三类待交互槽；产品约束：1～3题、全部作答、仅交互根、独立计划审核；安全加固：闭合字段、目标/选项/分支锁内复核与停止优先。 |
| 理由与代价 | 问答恢复无需解析消息或工具文本，build 中澄清保留任务归属；代价是两种新事件、控制表及客户端同步发布。保留无工具普通消息降级；不承诺进程崩溃接管或模型必定提问。 |
| 备选边界 | 不复制 DeepSeek Cordis、plan-review intent 或空答案跳过；不新增问卷 CRUD、Session 指针、元数据字段或通用工作流。若需 Child 直接提问/部分提交/持久化草稿，重新确定交互归属与控制边界。 |
| 设计状态 / 实现状态 | 已确定目标、target-only / 所列开发分支已核验且无 AskUserQuestion；本次只做设计与契约校验，没有问答工具运行验收。 |
| 验收 | Q1～Q5：结构与选项校验、问题/答案原子提交、三类互斥、跨实例竞争、停止/超时、前端重连和模式/进度不变。 |

**讲解要点。** 借鉴 DeepSeek 的工具式提问，将 UI 等待接入 CampusClaw 已有执行段和控制事务。用户回答成为原调用结果，前端消费显式问题；计划批准与工具权限保持独立。获得精确关联和原根续跑的同时，需要维护答案交接与恢复，元数据结构保持稳定。

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
