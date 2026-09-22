# Mate Chat API 待决事项

[返回主设计](../README.md)

版本 0.4.0 · 2026-09-22

本页维护尚未进入公共契约的要求与跨模块差距。当前字段、报文和机器评审状态归 operation JSON；已整合的决定不在此重复维护。目录保留原路径，具体任务分工和交接过程通过 Git 历史追溯。

| 编号 | 状态 | 当前问题与边界 |
|---|---|---|
| [C-001](#c-001) | 要求已确认，完整方案待定 | 一基数字页码与现有固定快照分页如何结合 |
| C-002 | 展示方案待定 | 公司 Swagger 不能展示 text/event-stream，真实 HTTP 媒体类型保持 SSE；另行选择准确的展示方式 |
| C-003 | 公共 operation 待定 | 创建与配置 Chat 的方法、字段、默认值、状态准入、响应和错误尚未整合为契约 |
| [C-004](#c-004) | Runtime 目标已明确，实施/桥接待对齐 | Claw 已选择原子 Session POST，Mate 公共配置入口仍未定稿 |
| [C-005](#c-005) | 标识约束待校准 | Provider 与 Runtime 的 modelId 长度/字符集不同，不能直接复制任一方为全系统规则 |
| [C-007](#c-007) | 显式任务事件已确认，公共精确模型待整合 | 后端输出完整 todos，补齐公共原消息关联与保存后发布 |
| [C-006](#c-006) | 公共与内部事件待桥接 | 中断目标、工具结果、错误字段、分页和流生命周期存在已知差异 |
| [C-008](#c-008) | Redis 目标已形成，HTTP 增量 proposed | Claw 独立只读观察、Mate 首帧完整预览、稳定身份映射与恢复能力需整合精确模型 |

<a id="c-001"></a>

## 数字页码与快照

已确认要求是 page/nextPage 使用 1、2、3 等一基数字，不使用 opaque cursor。现有公共模型仍用游标保存过滤条件、固定上界与续读位置，数字本身不能表达这些上下文。

原候选为数字页码加 snapshotEventId，并在后续请求重传过滤条件；快照标识、完整 Query/响应和错误尚未确认。该候选保持 proposed，不能因 Runtime 已采用普通分页就取消公共快照保证。先完成这项整体决定，再同步 JSON、OpenAPI、HTML、客户端恢复和校验。

<a id="c-004"></a>

## Chat 配置与 Runtime 原子更新

modelId 和思考设置属于 Chat/Session 配置，不进入 user.message；消息被接受时固定执行配置，运行中配置变化不追溯已有执行。公共创建/配置接口的具体形状仍待确定。

[Runtime Session 更新](../../../01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md#session-update) 已确认用 POST 原子更新 displayName/modelId/thinking/mode，按字段决定 busy 准入并要求 If-Match。原先“只能拆成两次 PUT 或增加原子操作”的目标选择已经解决；实际组合事务仍为 待实现，不能让 Mate 顺序调用旧 PUT 假装原子成功。

原冲突的实际源码基线为 Java c9d858bc8261bf07f5585f545b53495bf2226a56：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/` 下 `web/RuntimeSessionConfigurationController.java#changeModel/changeThinking`、`session/RuntimeSessionConfigurationService.java#changeModel/changeThinking` 和 `persistence/MyBatisRuntimeSessionRepository.java#updateModel/updateThinking` 分别提供独立更新与事务。新的专项证据由 Runtime 主设计 §8.1 维护，未将旧差距延伸为最新实现审计。

<a id="c-005"></a>

## modelId 跨边界约束

Model 模块定义大小写敏感的 1–64 字符不透明标识；Runtime 的配置规则沿用 1–128 和限定字符集。公共 Chat 配置在校准前不选取任一方作为共同约束。

证据：本仓 [Model 主设计](../../03-Model/README.md)；Java c9d858bc 的 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/RuntimeApiConstants.java#MODEL_ID_PATTERN` 及 `vo/ChangeModelRequestVO.java#modelId`。此处记录契约差异，不推断底层模型目录已经统一。

<a id="c-006"></a>

## 公共与内部事件衔接

| 边界 | 公共 Chat 目标 | Runtime Session 目标 | 所需设计工作 |
|---|---|---|---|
| 中断关联 | user.interrupt 无业务目标字段 | 必填 targetEventId 绑定原消息 | 明确公共动作如何固定原目标及跨执行竞争，不能动态中断最新任务 |
| 工具结果 | content 字符串，失败 errorCode 按条件可选 | content 文本块数组，失败码必填 | 明确安全转换和稳定错误映射 |
| 请求输出 | POST JSON 回执，GET stream 跨多轮 | POST 回执与对应执行段 SSE，idle 关闭 | bridge 维护独立观察和输出范围，不转发底层连接生命周期 |
| 历史 | createdAt 固定快照，数字分页要求待整合 | 因果追加顺序，普通整数 page | 公共历史必须有自己的投影与读取契约，不能透传内部页码 |

以上两侧均来自本仓当前精确模型，不是服务端实现事实。本文不新增字段或隐式兼容规则；公共事件 ID、权限与工具名称也需在 bridge 验收中逐项对齐。

<a id="c-007"></a>

## 后端显式任务更新

当前确认目标由 [TodoUpdate 主设计](../../../01-总体架构/06-CampusClaw计划模式/todo-update.md) 维护。Runtime 共享事件源已经登记 `agent.todo_updated`；Mate 公共精确模型尚未包含该类型和 sourceEventId，本条属于待整合的目标要求，不是服务端实现结论。

公共桥接保持 `type=agent.todo_updated`，直接返回完整 todos（内容、状态、列表顺序与 Runtime 权威快照一致），无 phase；toolCallId 沿用 Mate 公开工具身份。为每条内部权威事件建立一次稳定的公共 eventId 映射，sourceEventId 引用同一 Chat 中原始公共 user.message.eventId，不能改成确认回执 ID，也不能透传内部 sessionId。该原消息关联是新增公共事件字段要求，后端据此隔离多轮清单；前端不通过工具名、调用参数或结果文本判断进度。

读取已提交 Runtime 事件后，Mate 先保存公共投影与身份映射，再向自己的 live 流发布；重读同一内部 eventId 不能重复创建公共事件。通过现有 Runtime 历史补齐断流期间已提交的任务事件，不重发 TODO 工具或用户输入。公共 SSE/历史共享同一完整快照，旧历史不能覆盖更晚实时记录；按既有公共查询边界完成对账后替换列表。类型过滤、Schema 联合、OpenAPI、HTML、前端解码及契约测试必须同批登记；首次任务事件生产前读取端先支持新类型。

差异分类为架构变更：后端承担进度语义与原消息关联；不引入 TODO CRUD、任务表或 Agent/Tool/Skill 元数据字段。代价是增加公共类型及一次快照保存。Mate 当前实现未核验；Runtime 的固定 Java 09b32d8e、多事件事务和三基线证据见 [专项 §6](../../../01-总体架构/06-CampusClaw计划模式/source-evidence.md#6-todo-update-基线与接入证据)。实施验收覆盖两跳重复/断线、公共根消息映射、无工具记录时仍可显示进度，以及保持公共流跨多轮、Runtime 请求流按段结束的差异。

<a id="c-008"></a>

## Redis 快照与可恢复观察

[Redis 主设计](../../../01-总体架构/01-CampusClaw多Agent运行时/redis-stream-recovery.md)唯一维护目标结构、数据一致性与失败边界。选用 Claw 事件源侧 Hash 快照 + Streams，保留数据库控制与完整历史；不能只缓存 Mate 收到的 best-effort 增量后声称前缀完整。

推荐内部新增只读 Session stream，公共沿用现有 GET stream 并增加 `chat.preview_snapshot` 首帧。快照整体替换未完成预览，后续继续 delta，历史 completed 优先。该首帧不进入历史，不携带内部 sessionId/Redis cursor；两跳任一重连都建立新公共连接，不重放 POST。

HTTP 增量尚未进入 operation JSON/OpenAPI/HTML，不能标记已确认或已实现。R1 须完成两侧联合类型、availability/预算、Header 前错误、读取授权、公共身份映射、前端 generation 和完整事件对账测试后一起启用。现有公共类型清单与精确模型保留，不从 Markdown 草案自动发布新事件；C-001/C-006/C-007 的其他门禁仍分别有效。

## 维护方式

修改一侧契约时同步核对本表及受影响模型。确认结果先整合到唯一契约源，再生成页面、校验与检查图文；未完成的产品选择保留明确状态。新的源码结论必须绑定实际分析提交、仓库路径及符号。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.4.0 | 2026-09-22 | 登记 Redis 快照恢复的两跳只读接口、身份映射及精确模型接入门禁。 |
| 0.3.0 | 2026-09-15 | 登记显式任务快照与公共原消息关联的桥接要求。 |
| 0.2.0 | 2026-09-14 | 集中维护未整合要求和桥接差距，更新 Runtime 原子配置目标状态。 |
| 0.1.1 | 2026-09-03 | 登记接口共享决定与跨模块冲突。 |
