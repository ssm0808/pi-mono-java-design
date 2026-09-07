# ListEvents v2 历史查询设计

| 属性 | 值 |
|---|---|
| 文档版本 | 0.2.2 |
| 状态 | L1～L4 分页决定已确认，含超范围 200 空列表；其他字段及整体仍评审，target-only |
| 更新日期 | 2026-09-07 |
| 设计仓变更前基线 | `c16ed3f904a85d01d69deb1a3575e2c52cdaa958` |
| 实现核对基线 | `pi-mono-java@dfb90cac4e233e09a0b8f047f7e9f4682f5ad238` |
| 原 HTTP 核对基线 | `918005ee8ccc88d179fc31a0de17a92b4a01383b`；下述查询、编码、游标和 Mapper 四个文件无变化 |
| 官方公共契约核对 | Claude Managed Agents，2026-09-06，Beta；只证明公开行为 |

## 1. 本次修改与契约入口

用户明确要求开始修改查看对话历史接口，因此从 POST 切换到 ListEvents 逐项评审。
这不是 POST 整体通过：其已确认决定与未决项继续保留。
用户进一步确认从旧到新、普通 `page/nextPage` 数字页码，并在解释取舍后明确采用
普通分页。该决定替代上一版跨页固定快照与不透明游标方案，不影响事件身份和写入顺序。
用户本轮选择 `L2-page-size=B-default50-max200` 和
`L3-page-metadata=A-events-nextPage-only`：默认 50、上限 200，result 不返回 total。
2026-09-07 用户选择 `L4-out-of-range-page=A-empty-success`，确认合法超范围页返回空成功响应。

- 当前 [ListEvents 评审页](chat-events-v2-review.html)，唯一精确源为
  [02-list-session-events.json](接口契约-v2/操作/02-list-session-events.json)。
- [POST 保留评审页](chat-events-v2-submit-review.html) 与
  [请求级 SSE 设计](chat-events-v2-stream-design.md) 继续有效。
- 只修改 CampusClaw 内部目标契约；v1 十三个接口仍是迁移基线，运行时代码和 Mate
  公共接口不变。内部 `sessionId` 不直接暴露给浏览器。

```http
GET /campusclaw-service/v1/sessions/{sessionId}/events?page=1&limit=2
Accept: application/json
X-HW-ID: credential-jwt
Authorization: Bearer opaque-token
```

GET 是一次普通 JSON 读取，不是 SSE，也不是已撤销的 GET stream。结果沿用
`ResultBean {resCode,resMsg,result:{events,nextPage}}`；失败不带 `result`。
两种 Header 模式保留用户凭据 ID 的含义及具体非生产值。不要求 `access-token`，
不创建执行凭据、不调用 Mate 工具，不把任何凭据写进事件或日志。
上游认证、授权和隔离边界仍有效，Claw 不新增 JWT/APPKEY 解析或互斥校验。

## 2. 历史返回什么

身份、完整事件同形和已提交顺序沿用已确认目标决定；固定快照已被普通分页替代。下表将这些决定
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

## 3. 已确认：普通数字页码

`page=1、2、3……`，省略按第一页处理；有后续页时返回整数 `nextPage=page+1`，
没有下一页时返回 `null`。不使用加密游标，不额外增加快照标识、密钥、过期时间或
服务端翻页会话。页码是记录位置，不是 eventId 或内部事件序号。

每页读取该次查询可见的当前分支完整记录，不冻结首次查询的分支或提交上界。
查询可在 `idle` 或 `running` 时进行，不抢占消息执行名额，也不要求暂停执行。
同一轮翻页保持 `limit` 不变；改变大小时从第一页重新读取。
`limit` 省略时默认 50，显式取值范围为 1～200；默认值由 Service 归一。
用户、正文、思考、工具及状态等每条可见完整事件分别计数，不按消息轮次计数。

目标实现按可见事件集合计算 `offset=(page-1)*limit`，先按权限和事件类型过滤，
再按内部顺序升序分页；多取一条判断是否还有下一页。若一个内部记录映射为多条
公开事件，分页必须作用于映射后的稳定完整事件集合，不能先分页 Entry 再随意拆分。
内部数据类型映射与完整事件身份是先决条件，不能把 delta 算入页大小。
Service 校验页码、数量及偏移计算边界，拒绝溢出或无法支持的数值，不允许绕回负数。
每页的分支、可见性和记录读取应来自一致的单次读取边界；这是单请求一致性，不是跨页
固定快照，不跨 HTTP 请求保留数据库事务、连接或锁。

例如第一页查询时有 70 条，按默认大小取前 50 条；其后尾部追加 5 条，第二页可返回第
51～75 条。这不是顺序错误，也不需要把新记录排除。稳定位置的前提是分支、过滤、
保留范围和页大小不变，且新增事件只追加到可见顺序尾部；写侧的依赖检查和有序提交继续有效。

分支切换、thinking 过滤改变、记录清理或可见权限变化可能使已有位置移动。调用方
获知变化后重新从 `page=1` 加载；每页独立复核当前访问边界，不能返回已撤权内容。
没有跨页身份，本接口不承诺自动发现这些变化，也不承诺跨页完全无重复、无遗漏。
eventId 去重只能消除重复，不能弥补漏项；重新加载用于重新建立完整的当前列表。

`nextPage=null` 仅表示本次查询没有下一页，不表示执行结束或未来不会增加记录。
若读完后又有新增事件，客户端需要再次查询或合并其已收到的完整 SSE 事件；重新补读
可从第一页开始按 eventId 合并，不凭页尾 null 自动重发 POST。

L2/L3 已确认：默认 `limit=50`、上限 `200`，成功 result 只保留 `events/nextPage`，
不返回 `total`，也不为这个响应增加总数统计查询。L4 已确认：合法但超出当前记录范围
的页码返回 `200`，`result.events=[]`、`result.nextPage=null`；不返回 `204` 或空正文，
也不因没有记录而报 `INVALID_EVENT_LIST_QUERY`。此产品约束表示查询成功但没有匹配记录，
不表示 Session 执行完成。前提是 Session 存在、访问检查通过且查询成功；不能把不存在、
非法参数或读取失败转成空成功。非法页码或 limit 的 `400 / INVALID_EVENT_LIST_QUERY`
及其他错误细节继续待评审，不存在游标解密/过期错误。

## 4. 断线、确认和中断怎样展示

面向内部调用方的对账建议，Mate 的具体客户端协议仍需独立确认：

- 使用 Session 范围内的 `eventId` 合并，同一完整事件只显示一次；完整内容覆盖预览，
  晚到 delta 不能再追加到已完成事件。多个独立示例场景不能拼成同一 Session 历史。
- 原消息 SSE 与中断 SSE 收到的是同一个停止 idle；历史只返回一份。中断回执不能
  被展示为“已经停止”；实际停止记录才可说明对应目标结束。
- 等待工具确认的 idle 只结束对应 HTTP 交互；M1 仍占用 `running`，不可接受 M2。
  历史中的旧 done/terminated 也不是当前状态；提交是否允许仍以数据库原子准入为准。
- 普通分页补读时，不删除尚未读到的实时内容。按 eventId 合并完整事件；尚未出现在
  读取结果中的实时尾部保留独立顺序，后续补读再对账，不凭时间戳猜测跨通道顺序。
- 缺少首帧时不能按“文本相同”唯一识别提交；空历史、超时或本次查询缺少某条事件
  都不证明 POST 未接受。不得自动重发。若需要自动判定某次提交或跨执行终态归属，
  还须单独确认关联机制，本轮不擅自增加请求 ID、执行 ID 或幂等键。

## 5. 源码证据与差距

Java 文件相对根路径为
`campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/`。
下表记录上述 `dfb90ca` 基线，不代表旧设计中的所有基线整体升级。

| 相对路径与符号 | 已观察行为 | 目标差异 / 理由 |
|---|---|---|
| `web/RuntimeEventController.java` · `list` | GET 返回普通 ResultBean，不创建 Mate 执行凭据 | 保留 JSON 读取边界；不是再建实时长连接 |
| `event/RuntimeEventQueryService.java` · `list/pageOf/parseLimit` | 默认 100、上限 200；每页读取 Session，afterSeq 分页 | 用户已确认默认改为 50、上限仍为 200；普通整数页码与默认值尚未落入实现，不能将当前 100 当作目标值 |
| `event/RuntimeEventCursorCodec.java` · `encode/decode` | AES-GCM page 绑定 Session、afterSeq、thinking 和到期时间；无固定分支/上界；未配置 secret 时用进程随机密钥 | 此编码器退出 v2 ListEvents 读取链路，不为普通页码增加密钥或签名；v1 实现目前未改 |
| `event/RuntimeEntryCodec.java` · `toHistoryEvent/toSseData` | 旧类型、entryId/entrySeq，用户 message/fileIds；工具调用嵌在 Assistant 内容中 | 共用完整事件投影；工具调用身份要持久化或稳定映射，不能每次读取生成新 ID |
| `vo/EventPageResponseVO.java` | events 为 `List<Map<String,Object>>`，另有 nextPage | 目标使用只读类型化事件 Response VO，DTO 不穿透 HTTP |
| `campusclaw/src/main/resources/mapper/session/RuntimeSessionMapper.xml` · `listCurrentBranch` | 每页从当前 active_leaf_id 递归；只按 afterSeq 下界与旧类型白名单查询、按 entry_seq 升序 | 保留每次读取当前分支；以可见完整事件为分页单位，用页码计算偏移；新增控制、工具调用、结束记录的完整投影 |
| `event/RuntimeEventQueryService.java` · `restoreHistory`；`event/RuntimeEntryCodec.java` · `toAgentMessages` | 模型上下文恢复与公开列表已有不同路径 | 保留职责分离，避免把控制历史回灌模型 |

分类：JSON ResultBean、公司上下文、M1 准入是产品约束；凭据不落盘与每页访问复核是
安全加固；普通数字页码取代不透明游标是用户明确的产品约束，取消跨页固定快照是
架构简化；默认 50/上限 200 与只返回 events/nextPage 是本轮已确认产品约束；共享完整
事件投影和新增可恢复记录仍是 target-only 架构变更。

[Claude 官方事件流文档](https://platform.claude.com/docs/en/managed-agents/events-and-streaming)
区分不持久化的 preview 与权威完整事件，并用历史补齐断线期间的记录；
[List Events 官方参考](https://platform.claude.com/docs/en/api/beta/sessions/events/list)
是公开读取契约。本次只借鉴该边界；Beta 文档不能证明其服务端表结构、ID 算法、
事务、调度或分页实现。Claw 的 POST 合并、type + phase、thinking 策略及普通页码
是本项目目标决定/候选，不声称与 Claude 完全相同。

## 6. 推荐目标类图与查询时序

![共享权威事件投影与普通分页查询](设计图/事件历史查询/target_event_history_classes.svg)

[PlantUML 源码：target_event_history_classes](设计图/事件历史查询/diagram.puml#L1)

无状态单例 `CommittedEventProjection` 只接收已提交且完成可见性处理所需的 DTO，产出
不可变 Response VO；POST 的完整帧与 GET 复用它。它不接收原始 Provider delta，
也不承担追加事务。`HistoryPageQueryDTO` 只保存单次查询的页码、大小和安全计算后的
偏移等内部参数；没有跨页快照对象或游标编解码器。执行侧的 `SessionEventProjector` 仍是每执行对象，负责归一化
与追加，不能与这个无状态投影器混为同一职责。

![普通分页与尾部追加](设计图/事件历史查询/target_event_history_paging.svg)

[PlantUML 源码：target_event_history_paging](设计图/事件历史查询/diagram.puml#L56)

## 7. 实施切片与验收

1. 先补完整记录的稳定身份和共享投影骨架。POST 与 GET 同一完整事件逐字段相等；
   保留三种用户回执、工具关联及唯一停止记录，不泄露内部 ID 或凭据。
2. 再实现页码归一、查询 DTO 与 Mapper。尾部追加不移动已有位置；分支/过滤变化后
   重读第一页，不承诺跨页快照。保留写侧已确认的因果依赖与短事务串行规则。
3. 接入类型化只读 Response VO；请求 Request VO 用标准 Jakarta 校验，默认值在
   Service 归一，内部 Mapper 仅传 DTO。不得把原 Map/存储对象直接交给 Controller。
4. 验收 page=1/2、默认第一页、limit 省略为 50、显式 1/200 边界、非法整数、limit 越界、偏移溢出、过滤后计数、空页、
   超出范围、页尾、追加后续读和运行中读取；同一数据库可见数据与策略下不同实例结果一致。
   另外覆盖 thinking/分支变化后重载、删除和保留期清理，不测试已取消的游标期限或密钥。
   成功 result 精确包含 events/nextPage，不新增 total，也不触发为 total 服务的 COUNT 查询。
   合法超范围页必须为 200、events=[]、nextPage=null；不得返回 204、null 数组或分页错误，
   也不得把 Session 不存在或存储查询异常当作空页。
5. 场景验收完整事件覆盖预览、迟到 delta、中断双响应去重、等待确认仍 running，
   以及没有回执时不自动重发。工具无结果不伪造，未知持久化类型不静默丢弃。

当前交付是契约示例与静态验证，不包含上述运行时测试的通过声明。完整字段、扩展事件、
其他错误及保留期确认后，才能将本操作标为整体通过并替换 v1。

## 8. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.2.2 | 2026-09-07 | 确认 L4 合法超范围页返回 200 空列表和 nextPage=null；移除已确认选择，补齐不掩盖参数/读取错误的边界。仅改设计，源码基线 dfb90ca 不变。 |
| 0.2.1 | 2026-09-06 | 确认 L2 默认 50/上限 200、L3 仅 events/nextPage，不返回 total；同步默认值、示例、图和验收。L4 空页响应待评审，未整体确认，源码基线 dfb90ca 不变。 |
| 0.2.0 | 2026-09-06 | 确认从旧到新、普通整数 page/nextPage，取消跨页固定快照、快照标识及加密游标；保留同形与顺序，移除 L1 选择，改评审每页数量与 total；补齐普通分页变化边界与目标图。 |
| 0.1.0 | 2026-09-06 | 按用户要求开启 ListEvents 修改：完整事件与 POST 对齐、固定分支/提交上界候选、两页与中断/确认示例、源码差距、目标图及验收；POST 未决项保留。 |
