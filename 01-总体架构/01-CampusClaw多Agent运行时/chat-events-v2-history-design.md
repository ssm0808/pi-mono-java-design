# ListEvents v2 历史查询设计

| 属性 | 值 |
|---|---|
| 文档版本 | 0.1.0 |
| 状态 | 当前 operation 评审中，target-only；不代表已实现或整体确认 |
| 更新日期 | 2026-09-06 |
| 设计仓变更前基线 | `76d39c2603fc2a402d16545d35793ddcc97cc687` |
| 实现核对基线 | `pi-mono-java@dfb90cac4e233e09a0b8f047f7e9f4682f5ad238` |
| 原 HTTP 核对基线 | `918005ee8ccc88d179fc31a0de17a92b4a01383b`；下述查询、编码、游标和 Mapper 四个文件无变化 |
| 官方公共契约核对 | Claude Managed Agents，2026-09-06，Beta；只证明公开行为 |

## 1. 本次修改与契约入口

用户明确要求开始修改查看对话历史接口，因此从 POST 切换到 ListEvents 逐项评审。
这不是 POST 整体通过：其已确认决定与未决项继续保留。

- 当前 [ListEvents 评审页](chat-events-v2-review.html)，唯一精确源为
  [02-list-session-events.json](接口契约-v2/操作/02-list-session-events.json)。
- [POST 保留评审页](chat-events-v2-submit-review.html) 与
  [请求级 SSE 设计](chat-events-v2-stream-design.md) 继续有效。
- 只修改 CampusClaw 内部目标契约；v1 十三个接口仍是迁移基线，运行时代码和 Mate
  公共接口不变。内部 `sessionId` 不直接暴露给浏览器。

```http
GET /campusclaw-service/v1/sessions/{sessionId}/events?limit=2
Accept: application/json
X-HW-ID: credential-jwt
Authorization: Bearer opaque-token
```

GET 是一次普通 JSON 读取，不是 SSE，也不是已撤销的 GET stream。结果沿用
`ResultBean {resCode,resMsg,result:{events,nextPage}}`；失败不带 `result`。
两种 Header 模式保留用户凭据 ID 的含义及具体非生产值。不要求 `access-token`，
不创建执行凭据、不调用 Mate 工具，不把任何凭据写进事件、游标或日志。
上游认证、授权和隔离边界仍有效，Claw 不新增 JWT/APPKEY 解析或互斥校验。

## 2. 历史返回什么

身份、完整事件同形、已提交顺序和固定快照沿用已确认目标决定。下表将这些决定
应用到 ListEvents；具体内容字段继承 POST 的候选状态，不因复制示例而获得批准。

| 事件 | 历史投影 | 读取意义 |
|---|---|---|
| `user.message` | 完整 `eventId/type/createdAt/content[]` | 已接受的消息；拒绝的 M2 不在这里 |
| `user.interrupt` | 完整中断回执 | 已接受停止请求，不表示实际退出 |
| `user.tool_confirmation` | 完整确认回执，保留 `toolCallId` | 与对应工具调用关联 |
| `agent.message` | 仅 `phase=completed` | 用完整内容覆盖同 eventId 的预览 |
| `agent.thinking` | 仅允许公开的 `phase=completed` | 候选沿用 Session thinking 过滤，不披露原始推理 |
| `agent.tool_call` / `agent.tool_result` | 完整事件，保留各自 eventId 与共同 toolCallId | 调用与结果分别计数；缺少结果不能伪造成功 |
| `session.status_idle` | 完整权威结束记录，同 eventId 只保留一条 | 必须结合对应交互理解，不是当前准入状态 |

不返回 delta、心跳或连接结束标记，不公开 `entryId/entrySeq/runId/executionId`。
同一事件在 POST 完整帧与 GET 历史中保持相同身份、时间和业务字段；序列化、脱敏与
可见性投影不能各实现一套。历史数组不按 `createdAt` 重新排序。

八类基础事件不是封闭的最终清单。已有模型/思考配置变更、压缩及 Usage 的 v2 映射
仍须补齐；其他进度与子 Agent 投影另审。不能以本页未举例为由删除既有能力，也不能
把旧 `entryId/entrySeq` 报文直接混进 v2。迁移验收前必须为每种持久化记录明确
映射或有依据的可见性规则；未知记录不能静默丢弃后宣称历史完整。

公开事件历史与模型上下文恢复是两种投影：后者仍由内部消息、工具结果及压缩边界
恢复，不能直接将 `user.interrupt`、idle 或显示摘要当作模型消息。本轮不修改 Runtime
内核及 pi 语义，未从其他产品的公开接口推断内部持久化模型。

## 3. 固定快照怎样分页

以下是落实固定快照的目标方案，具体游标字段、期限和方向尚待评审：

1. 首次不传 `page`。在一致的数据库短读事务中，读取当前分支叶节点、已提交的
   内部顺序上界与可见性策略版本。它们必须属于同一个数据库可见状态。
2. 只在该叶节点的祖先链内、上界以内读取完整可见事件。候选按内部顺序从旧到新，
   过滤后取 `limit+1` 条判断是否还有下一页；`limit` 计事件，不计消息轮次。
3. 有下一页时返回不透明 `nextPage`，封装 Session、固定分支、上界、上次返回位置、
   可见性和投影版本、方向、到期时间。调用方原样回传，不能用 eventId 替代。
4. 后续页仍查询固定分支和上界；期间新消息、迟到提交或当前分支切换，不混入这一轮。
   同一有效 page 重读应得到相同记录；不跨 HTTP 请求持有数据库事务或行锁。
5. 每页在读取边界重新检查 Session 存续及适用的授权/可见性条件。thinking 开关改变、
   策略撤回或原分支数据清理导致快照不可用时，旧 page 失效；不能继续返回已撤权内容，
   也不能偷偷切回最新分支。候选返回 `400 / INVALID_EVENT_LIST_QUERY`，Session
   不存在/删除沿用 `404 / SESSION_NOT_FOUND`。统一错误不回显内部 token 或标识。

游标需防篡改、不泄露内部字段，并在允许访问同一 Session 的服务实例间可验证；不能
把当前缺省的进程随机密钥当作生产多实例方案。密钥轮换兼容窗口、过期时间、投影版本
升级和数据保留期一并评审。新增表如确有必要仍使用 `t_` 命名，本轮不冻结 DDL。

`nextPage=null` 仅表示本快照读完，不表示执行结束。活动执行的后续完整事件需要
从不带 page 的第一页创建新快照读取。这里只提供可靠历史补读，不声称可重放 token
或用 eventId 在独立 SSE 上断点续传。

当前 L1 只询问分页方向：推荐沿用旧到新，便于顺序读取和对账；另一候选先返回最近
一页、再向前加载，每页内部仍按旧到新。默认 `limit=100`、上限 `200`、跨页改 limit
规则和游标期限未冻结；暂不增加 `before/after/order` 等未经选择的新参数。

## 4. 断线、确认和中断怎样展示

面向内部调用方的对账建议，Mate 的具体客户端协议仍需独立确认：

- 使用 Session 范围内的 `eventId` 合并，同一完整事件只显示一次；完整内容覆盖预览，
  晚到 delta 不能再追加到已完成事件。多个独立示例场景不能拼成同一 Session 历史。
- 原消息 SSE 与中断 SSE 收到的是同一个停止 idle；历史只返回一份。中断回执不能
  被展示为“已经停止”；实际停止记录才可说明对应目标结束。
- 等待工具确认的 idle 只结束对应 HTTP 交互；M1 仍占用 `running`，不可接受 M2。
  历史中的旧 done/terminated 也不是当前状态；提交是否允许仍以数据库原子准入为准。
- 固定快照补读时，不删除还未出现在该快照中的实时内容。保留独立实时尾部，等新的
  权威快照覆盖后再合并定序；不凭时间戳或 eventId 猜测跨通道顺序。
- 缺少首帧时不能按“文本相同”唯一识别提交；空历史、超时或本轮快照缺少某条事件
  都不证明 POST 未接受。不得自动重发。若需要自动判定某次提交或跨执行终态归属，
  还须单独确认关联机制，本轮不擅自增加请求 ID、执行 ID 或幂等键。

## 5. 源码证据与差距

Java 文件相对根路径为
`campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/`。
下表记录上述 `dfb90ca` 基线，不代表旧设计中的所有基线整体升级。

| 相对路径与符号 | 已观察行为 | 目标差异 / 理由 |
|---|---|---|
| `web/RuntimeEventController.java` · `list` | GET 返回普通 ResultBean，不创建 Mate 执行凭据 | 保留 JSON 读取边界；不是再建实时长连接 |
| `event/RuntimeEventQueryService.java` · `list/pageOf` | 默认 100、上限 200；每页读取 Session，afterSeq 分页 | 新增一致快照解析；数值作为沿用候选，不误标为新确认 |
| `event/RuntimeEventCursorCodec.java` · `encode/decode` | AES-GCM page 绑定 Session、afterSeq、thinking 和到期时间；无固定分支/上界；未配置 secret 时用进程随机密钥 | 补齐快照绑定和多实例密钥约束，避免换实例即失效 |
| `event/RuntimeEntryCodec.java` · `toHistoryEvent/toSseData` | 旧类型、entryId/entrySeq，用户 message/fileIds；工具调用嵌在 Assistant 内容中 | 共用完整事件投影；工具调用身份要持久化或稳定映射，不能每次读取生成新 ID |
| `vo/EventPageResponseVO.java` | events 为 `List<Map<String,Object>>`，另有 nextPage | 目标使用只读类型化事件 Response VO，DTO 不穿透 HTTP |
| `campusclaw/src/main/resources/mapper/session/RuntimeSessionMapper.xml` · `listCurrentBranch` | 每页从当前 active_leaf_id 递归；只按 afterSeq 下界与旧类型白名单查询、按 entry_seq 升序 | 固定首查分支及已提交上界；新增控制、工具调用、结束记录的完整投影 |
| `event/RuntimeEventQueryService.java` · `restoreHistory`；`event/RuntimeEntryCodec.java` · `toAgentMessages` | 模型上下文恢复与公开列表已有不同路径 | 保留职责分离，避免把控制历史回灌模型 |

分类：JSON ResultBean、公司上下文、M1 准入是产品约束；凭据不落盘与游标访问复核是
安全加固；固定分页快照、共享完整事件投影和新增可恢复记录是 target-only 架构变更。

[Claude 官方事件流文档](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)
区分不持久化的 preview 与权威完整事件，并用历史补齐断线期间的记录；
[List Events 官方参考](https://platform.claude.com/docs/en/api/beta/sessions/events/list)
是公开读取契约。本次只借鉴该边界；Beta 文档不能证明其服务端表结构、ID 算法、
事务、调度或固定快照实现。Claw 的 POST 合并、type + phase、thinking 策略及游标
是本项目目标决定/候选，不声称与 Claude 完全相同。

## 6. 推荐目标类图与查询时序

![共享权威事件投影与固定读取快照](设计图/事件历史查询/target_event_history_classes.svg)

[PlantUML 源码：target_event_history_classes](设计图/事件历史查询/diagram.puml#L1)

无状态单例 `CommittedEventProjection` 只接收已提交且完成可见性处理所需的 DTO，产出
不可变 Response VO；POST 的完整帧与 GET 复用它。它不接收原始 Provider delta，
也不承担追加事务。查询快照按请求解析、跨页通过不透明 page 延续，不是保存数据库
连接的长生命周期对象；执行侧的 `SessionEventProjector` 仍是每执行对象，负责归一化
与追加，不能与这个无状态投影器混为同一职责。

![固定快照分页与并发追加](设计图/事件历史查询/target_event_history_paging.svg)

[PlantUML 源码：target_event_history_paging](设计图/事件历史查询/diagram.puml#L58)

## 7. 实施切片与验收

1. 先补完整记录的稳定身份和共享投影骨架。POST 与 GET 同一完整事件逐字段相等；
   保留三种用户回执、工具关联及唯一停止记录，不泄露内部 ID 或凭据。
2. 再实现快照查询 DTO、游标编解码与 Mapper。并发追加、分支切换不混页；上界以前
   不允许后来填入已对外提交顺序的空洞。保留写侧已确认的因果依赖与短事务串行规则。
3. 接入类型化只读 Response VO；请求 Request VO 用标准 Jakarta 校验，默认值在
   Service 归一，内部 Mapper 仅传 DTO。不得把原 Map/存储对象直接交给 Controller。
4. 验收过滤计数、空页、页尾、重复查询、过期/篡改/跨 Session page、密钥轮换、
   thinking 变化、删除与保留期清理；多实例使用同一有效 page 的结果一致。
5. 场景验收完整事件覆盖预览、迟到 delta、中断双响应去重、等待确认仍 running，
   以及没有回执时不自动重发。工具无结果不伪造，未知持久化类型不静默丢弃。

当前交付是契约示例与静态验证，不包含上述运行时测试的通过声明。完整字段、扩展事件、
分页方向、数值及保留期确认后，才能将本操作标为整体通过并替换 v1。

## 8. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.0 | 2026-09-06 | 按用户要求开启 ListEvents 修改：完整事件与 POST 对齐、固定分支/提交上界候选、两页与中断/确认示例、源码差距、目标图及验收；POST 未决项保留。 |
