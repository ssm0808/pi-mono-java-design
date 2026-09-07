# ListEvents v2 历史查询设计

| 属性 | 值 |
|---|---|
| 文档版本 | 0.2.7 |
| 状态 | L1～L10 已确认；剩余问题改为 B01～B15 批量评审，整体未确认，target-only |
| 更新日期 | 2026-09-08 |
| 设计仓变更前基线 | `c16ed3f904a85d01d69deb1a3575e2c52cdaa958` |
| L5 字段确认前设计仓基线 | `7349cdf2e037700ddf4917eebef0e19799252f47`；沿用下述实现证据，本轮未重新核对实现 |
| L6 字段确认前设计仓基线 | `050bda2579004b630021300986881ac61ba7142e`；沿用下述实现证据，本轮未重新核对实现 |
| L7 字段确认前设计仓基线 | `019b2dbfbc85edb23d94ffbda7b4963237286f7e`；Mate 适配补充核对见 §2.1，既有 HTTP 证据不整体升级 |
| L9 字段确认前设计仓基线 | `33a7344ff3b98e143e98894f6105f53160ab0734`；复核同一 dfb90ca 的 CallMateTool.name/parameters/execute，其他源码证据不变 |
| L10 字段确认前设计仓基线 | `0f3f58f2f203fe4fe88c308032e1815b1622683b`；沿用工具结果源码证据，本轮只确认 HTTP 目标字段 |
| 实现核对基线 | `pi-mono-java@dfb90cac4e233e09a0b8f047f7e9f4682f5ad238` |
| 原 HTTP 核对基线 | `918005ee8ccc88d179fc31a0de17a92b4a01383b`；下述查询、编码、游标和 Mapper 四个文件无变化 |
| 官方公共契约核对 | Claude Managed Agents，2026-09-06，Beta；只证明公开行为 |

## 1. 本次修改与契约入口

用户明确要求开始修改查看对话历史接口，因此从 POST 切换到 ListEvents 评审。
这不是 POST 整体通过：其已确认决定与未决项继续保留。
用户进一步确认从旧到新、普通 `page/nextPage` 数字页码，并在解释取舍后明确采用
普通分页。该决定替代上一版跨页固定快照与不透明游标方案，不影响事件身份和写入顺序。
用户本轮选择 `L2-page-size=B-default50-max200` 和
`L3-page-metadata=A-events-nextPage-only`：默认 50、上限 200，result 不返回 total。
2026-09-07 用户选择 `L4-out-of-range-page=A-empty-success`，确认合法超范围页返回空成功响应。
同日用户选择 `L5-agent-message-content=A-string`，确认 Agent 完整回答使用字符串。
这一字段决定按既有完整事件同形规则同步 POST SSE。
用户随后选择 `L6-tool-call-arguments=A-object`，确认工具调用参数使用 JSON 对象；
2026-09-08 用户选择 `L7-tool-result-content=A-content-blocks`，确认工具结果使用内容块数组，
并询问 Mate 工具的返回设计。用户随后明确当前工具只返回文本，记录为 L8；
用户随后选择 `L9-mate-tool-identity=A-runtime-wrapper`，确认保留 Mate 调用的 Runtime
工具名与参数包装；同日选择 `L10-tool-result-outcome=A-is-error`，确认每条工具结果返回
isError 布尔值。用户随后明确要求集中确认剩余问题，不再逐项提问；本轮按 §8 的 B01～B15 批量对齐。

- 当前 [ListEvents 评审页](chat-api-review.html#listSessionEvents)，唯一精确源为
  [02-list-session-events.json](接口契约-v2/操作/02-list-session-events.json)。
- [POST 保留评审页](chat-api-review.html#submitSessionEvent) 与
  [请求级 SSE 设计](chat-events-v2-stream-design.md) 继续有效。
- 只修改 CampusClaw 内部目标契约；当前十项接口由统一清单管理，运行时代码和 Mate
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
应用到 ListEvents；L5 完整正文字符串、L6 工具调用参数 JSON 对象、L7 内容块数组与 L8 工具结果仅文本已确认，其他具体内容字段保留原有评审状态，
不因复制示例而获得批准。

| 事件 | 历史投影 | 读取意义 |
|---|---|---|
| `user.message` | 完整 `eventId/type/createdAt/content[]` | 已接受的消息；拒绝的 M2 不在这里 |
| `user.interrupt` | 完整中断回执 | 已接受停止请求，不表示实际退出 |
| `user.tool_confirmation` | 完整确认回执，保留 `toolCallId` | 与对应工具调用关联 |
| `agent.message` | 仅 `phase=completed`；`content` 字符串已确认 | 用完整正文覆盖同 eventId 的预览 |
| `agent.thinking` | 仅允许公开的 `phase=completed` | 候选沿用 Session thinking 过滤，不披露原始推理 |
| `agent.tool_call` / `agent.tool_result` | 完整事件，保留各自 eventId 与共同 toolCallId；调用的 `arguments` JSON 对象、结果的 `content` 文本块数组已确认 | 调用与结果分别计数；缺少结果不能伪造成功 |
| `session.status_idle` | 完整权威结束记录，同 eventId 只保留一条 | 必须结合对应交互理解，不是当前准入状态 |

不返回 delta、心跳或连接结束标记，不公开 `entryId/entrySeq/runId/executionId`。
同一事件在 POST 完整帧与 GET 历史中保持相同身份、时间和业务字段；序列化、脱敏与
可见性投影不能各实现一套。历史数组不按 `createdAt` 重新排序。

L5 是已确认的目标产品约束：完整回答的 `content` 使用 JSON 字符串。它保留当前候选的
正文表达，调用方可直接用完整正文替换预览，不增加内容块解析。既有示例已使用字符串，
因此本轮只收敛字段状态，不改变示例值；不新增附件输出块，也不改变已确认的
`user.message.content[]`。空内容、长度、thinking、delta 及其他事件字段仍按各自状态评审。
这不是 Java 或 pi 已实现该 v2 字段的声明，不升级源码基线，也不改变图中的结构和生命周期。

L6 是已确认的目标产品约束：`agent.tool_call.arguments` 使用 JSON 对象，调用方可直接
读取字段，避免二次 JSON 解析。GET 与 POST 使用相同的脱敏投影；对象内部字段仍由对应
工具契约决定，本次不统一各工具参数，也不确认其他工具字段或工具结果。现有示例已为
对象，因此只收敛确认状态，不修改示例值、Runtime 实现或图中结构。

L7 是已确认的目标产品约束：`agent.tool_result.content` 使用内容块数组。既有字符串示例
同步包装为一个 `{"type":"text","text":"原文本"}` 块，成功与失败使用同一容器，不改变
既有示例的成败标记与错误码值；isError 已由 L10 确认，errorCode 仍候选。保留数组是用户已确认的字段结构，当前一个文本结果
可直接包装为一个块；不是以本期存在图片或结构化 JSON 输出为前提。

L8 是用户进一步明确的本期产品约束：当前工具只返回文本，公共 content[] 仅包含
`type=text` 与字符串 `text`，Mate 亦如此。不提供 JSON 块、图片块或自动类型识别；文本即使
是 JSON 字符串也仍是文本。此前用 Read 图片说明本期数组必要性的理由撤回，不能从
[旧工具目标契约](../02-CampusClaw工具系统/built-in-tool-contracts.md#1-契约总则)的图片设计
推导当前 HTTP 支持图片。本轮只收敛接口输出范围，不修改 Runtime 工具实现或重做 Read
工具专题。空文本、块数量、大小与保留规则仍待评审；内部 details 或 ContentBlock 扩展字段
不直接进入公共 HTTP VO。

八类基础事件不是封闭的最终清单。已有模型/思考配置变更、压缩及 Usage 的 v2 映射
仍须补齐；其他进度与子 Agent 投影另审。不能以本页未举例为由删除既有能力，也不能
把旧 `entryId/entrySeq` 报文直接混进 v2。迁移验收前必须为每种持久化记录明确
映射或有依据的可见性规则；未知记录不能静默丢弃后宣称历史完整。

公开事件历史与模型上下文恢复是两种投影：后者仍由内部消息、工具结果及压缩边界
恢复，不能直接将 `user.interrupt`、idle 或显示摘要当作模型消息。本轮不修改 Runtime
内核及 pi 语义，未从其他产品的公开接口推断内部持久化模型。

### 2.1 Mate 工具的文本返回与源码边界

2026-09-08 重新读取 `pi-mono-java@dfb90cac4e233e09a0b8f047f7e9f4682f5ad238`
的下列实现；这是对相同 commit 的 Mate 返回链路补充核对，不替换旧工具专题的其他结论。
以下路径均相对各自仓库根目录。

| 源码证据 | 已观察行为 |
|---|---|
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/HttpMateToolClient.java:340` · `toToolResult` | Claw 客户端读取 `resCode/resMsg/result`；仅 `resCode` 文本值为 `0` 时成功，把非空 result 用 `JsonNode.toString()` 序列化，metadata 为 null。result 缺失或 null 时当前返回空字符串；这不是本轮确认的空结果规则。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/mate/MateToolClient.java` · `ToolResult` | 内部结果是 `String content`、`Map metadata`、`boolean isError`，没有保留原始 JSON 节点或图片块。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/CallMateTool.java:46` · `name/parameters/execute` | 工具名为 CallMateTool；Schema 的 tool 为业务工具名，args 为对象且可省略，执行时缺省为 Map.of()。L9 只固定公开包装，不在本轮额外确认省略 args 的事件归一方式。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/CallMateTool.java:101` · `execute` | 成功时包装一个 TextContent；metadata 进入 AgentToolResult.details。错误时抛出 MateToolExecutionException。 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java` · `invokeTool/failureResult/toToolResultMessage` | 普通执行异常转成文本块和 isError=true，最终 ToolResultMessage 保留工具调用关联、内容块及内部 details；after hook 仍可调整结果。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/ListMateToolsTool.java` · `stableJson/textResult` | 工具发现的 scope/tools 清单也序列化为一个文本块，只保留 name/description/inputSchema，不返回内部工具 ID 或 outputSchema。 |
| `pi@5cd93f688aaab89dbb6dfa4aca535f21796ae185` · `packages/ai/src/types.ts:449` · `ToolResultMessage`；`packages/agent/src/agent-loop.ts:777` · `createToolResultMessage` | 内核工具结果是 TextContent/ImageContent 数组，details 独立保留。这是内核语义证据，不能据此照搬 pi 的 Base64 图片字段作为企业 HTTP 契约。 |

本地 `mate-service@956b547f5ca12ca89e68f73012f92a4406b0c9fa` 的 `src/main/java`
未检索到对应 `/runtime/tools/{toolId}/execute` 服务端实现；上述信封只证明 Claw 客户端
当前如何消费响应，不声称已核对 Mate 执行服务端的全部返回类型、业务错误或图片能力。
本轮不修改 Mate 公共接口。

对于 Mate 返回的结构化成功 result，当前适配得到的是“一个 text 块内放 JSON 文本”。
它符合 L7 的数组容器与 L8 的文本约束，不自动把 JSON 中的 URL、Base64 或 `content` 字段识别为其他类型的块。
`details/metadata` 也不因此进入公共历史或 SSE；既有工具契约将 details 定位为内部扩展位。
L9 已确认公开调用保留 Runtime `CallMateTool({tool,args})` 包装；既有直接业务工具名示例
已同步替换。isError 已由 L10 确认；稳定错误码及脱敏文案映射仍保留原有评审状态。

用户明确仅文本后，尚未确认的独立 JSON 块候选撤回。Mate 返回复用现有文本结果；调用方
展示 text，不把某段恰好可解析的 JSON 当作稳定跨工具业务对象。没有公共 `structuredContent`，
也不新增 Mate 原始 ResultBean 信封。Mate result 为字符串时当前 `JsonNode.toString()` 会保留
JSON 字符串的引号与转义；原始 result 的服务端形状和文本归一细节尚未核对，不隐式改变解包规则。

L9 是已确认的目标产品约束：Mate 调用的 `toolName=CallMateTool`，arguments 保留
`{tool,args}`，与实际调用及 Schema 一致。业务工具名只放在 `arguments.tool`，原业务参数
移入 `arguments.args`；示例的 eventId、toolCallId、参数值、确认标记与结果内容不变。
该方式无需再把 Runtime 工具名称替换成业务工具名称，调用方可从 arguments.tool 展示
具体业务能力；公共事件不新增内部 toolId，也不将一个 Runtime 工具注册为多个模型工具。
结果仍通过原 toolCallId 关联；本次不增加 tool_result.toolName 或确认其他结果字段。
公共 VO 继续经既有共享完整事件投影产生，L9 不改变图中的分层、关联和生命周期。

L10 是已确认的目标产品约束：每条完整工具结果必须带 `isError` 布尔值，成功为 false，
失败为 true。既有示例已使用该字段，因此本轮只确认字段契约，不改变示例值。该表示
沿用 Java ToolResultMessage 与固定 pi 的 isError 语义，调用方无需解析文本判断成败；
不增加 status 枚举或执行中状态。GET 与 POST 共用同一结果投影，失败仍返回文本块，
具体错误码、文案、空文本和块数量规则继续待评审。

失败错误码、空文本与 Mate 归一等剩余语义统一纳入 §8 的批量建议；原 L11 单字段问卷撤下。现有 TOOL_CALL_DENIED 示例仍为候选，不能当作错误码集合已确认。

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
6. L7/L8 验收工具结果 content 为仅含 text 块的数组、GET 与 POST 同一完整结果逐字段相等；
   JSON 文本仍放在 text 中，不变为 JSON 或图片块，不把内部 details 或 Mate 原始信封顺带暴露。
   空文本和块数量约束仍须确认后补齐验收。
7. L9 验收 Mate 调用的 toolName 为 CallMateTool、arguments 保留 tool/args 包装；
   GET 与 POST 不发生二次展开，关联 ID 和业务参数值不变，不公开内部 toolId。
8. L10 验收每条完整工具结果均带布尔 isError，成功 false、失败 true；缺失、null、
   数字或字符串不符合该字段契约，不能以 status 或错误文本替代。

当前交付是契约示例与静态验证，不包含上述运行时测试的通过声明。完整字段、扩展事件、
其他错误及保留期确认后，才能将本操作标为整体通过并替换 v1。

## 8. 剩余问题一次批量确认（待确认建议）

批次 `2026-09-08.1`。用户明确要求一起确认，替代逐项提问；L1～L10 保持已确认。
精确问题和选项由当前 ListEvents JSON 的 `review.questions` / `review.batchReview` 维护，
统一 HTML 显示四组问题，可一次提交或直接回复“全部按推荐；Bxx 改为……”。默认选中不是批准。
本批确认列出的产品语义；确认后统一补齐报文、错误码表、示例和验收，再整体核对，不再逐字段提问。

范围是 `/campusclaw-service/v1` 下的 GET/POST `/sessions/{sessionId}/events` 及其配置、
Skill 联动；不修改 Mate 公共 API。下表都是 target-only 建议，尚未改变现有示例或原契约。
B09 增加控制目标/输出关联字段、B13 为 Skill 选择 SSE 是需要明确确认的架构变更；
B01 脱敏、B14 信任和访问复核是安全加固，其余公开行为为产品约束。新建议没有对应已实现声明。
依据是本页 §2/§5 的已核对 Java/pi 证据、当前 POST 流设计，以及
[已确认 Builtin 请求](接口契约/操作/13-execute-session-command.json)、
[通用命令设计](../../04-命令与技能/00-Slash-Command通用模块/README.md) 和
[Skill 待实现边界](../../04-命令与技能/02-技能命令/README.md)。本轮不升级实现源码基线或托管产品核对日期。

| 编号 | 需要决定的内容 | 推荐方案（未确认） |
|---|---|---|
| B01 | 失败错误码 | 失败时必有稳定 errorCode，成功时省略；区分用户拒绝、参数错误、工具不存在、超时和执行失败。文案放在 text，使用脱敏可展示信息；不透传 Mate 原始错误码、异常栈或凭据。 |
| B02 | 空文本与大小 | 工具结果至少一个 text 块，允许 text=""，不强制只有一块；没有正文时不伪造 Agent 回答。沿用工具自身的有说明截断；HTTP 不静默截断完整事件。大小上限由实现校准，超限必须明确失败或断流并可查历史。 |
| B03 | Mate 文本归一 | CallMateTool 缺省 args 在公开事件中补 {}；Mate result 为字符串时直接作为文本，对象/数组变为 JSON 文本，null 为 ""。这是待确认的适配调整，当前客户端对字符串使用 JSON 序列化的实现将有变化。 |
| B04 | 时间与增量 | 完整事件 createdAt 使用 Claw 形成该权威记录时的 UTC 毫秒时间，保存一次，GET/POST 复用；delta 使用 content 字符串，只含新增文本，沿用同一 eventId，不带 createdAt。completed 覆盖预览，之后忽略迟到 delta。 |
| B05 | Thinking 展示 | 只展示可公开摘要，不暴露原始推理。thinking 开关决定后续执行是否产生摘要；之后关闭开关不隐藏此前已公开的历史摘要，读取仍受当前权限约束。此项替换尚未确认的“按当前开关过滤历史”候选。 |
| B06 | 工具确认标记 | 每个完整 agent.tool_call 都带 requiresConfirmation 布尔值；本期顺序发出需确认调用，同一执行一次只挂起一个待确认 toolCallId。允许/拒绝后分别续跑，拒绝产生 isError=true 的工具结果。 |
| B07 | 结束原因 | session.status_idle.reason 固定 done、failed、terminated、confirming；confirming 只结束当前 SSE，Session 继续 running。failed 携带稳定 errorCode 和可展示 message；工具失败可由 Agent 继续处理，不自动等同于整轮 failed。 |
| B08 | 控制请求竞争 | 确认与中断在同一执行的事务内重检；停止请求先提交，则拒绝确认；确认先提交，中断仍可停止续跑。重复/过期确认返回 409，不重复执行工具；等待超时不伪造已停止。 |
| B09 | 防止误停下一轮 | 建议给 user.interrupt 增加必填 targetEventId，引用原 user.message 的 eventId；不匹配当前执行时返回 409。agent.* 和 idle 用 sourceEventId 引用同一原消息，便于历史对账。复用已有事件身份，不新增 runId/executionId；这是需要你确认的字段扩展。 |
| B10 | 断线与回执丢失 | 保留无自动写重试的方案：没有收到首帧时显示“提交结果不确定”，不靠相同文本猜测成功，不新增幂等键。收到回执后按 eventId 和 B09 的关联补读历史；断流本身不取消执行，也不代表失败。 |
| B11 | HTTP 故障与心跳 | 接受前：非法参数 400、不存在 404、状态冲突 409、容量/依赖暂不可用 503、内部失败 500，统一 ResultBean；接受后不得伪装成未接受。SSE 已开始则不改成 JSON，能保存权威失败则发送 failed，否则断流并对账。采用 : ping 注释心跳；慢客户端可丢 preview，完整帧不能入队则断开。 |
| B12 | 配置、压缩与用量 | 模型/思考配置变更和压缩保留独立完整事件，映射到统一 v2；Usage 放在对应完整 Agent 消息，Session 保留累计用量。不新增通用 command 生命周期、进度或子 Agent 公共事件；已有内部记录逐类标明公开映射或不公开理由。 |
| B13 | Skill 请求与响应 | 共享 POST /sessions/{sessionId}/command：Skill 用 name="skill:<name>"、arguments 字符串和可选 fileIds；Skill 执行返回与消息一致的 SSE，Builtin 保持普通 JSON。Skill 遵循同一 Session 单消息准入，首帧回执为展开前的 user.message，随后普通 Agent/Tool/idle 事件，不新增 commandId。 |
| B14 | Skill 快照与恢复 | 受理前解析完整 Agent/Skill 快照并重检绑定、权限和容量，受理后本次执行固定快照；Skill 正文按资源内容处理，不提升为系统权限。内部恢复所需内容沿用 Session 持久化与保留策略，公共历史只展示用户调用和执行结果，不另建 Skill 全文审计副本。 |
| B15 | 数据保留 | 沿用部署统一的数据保留策略，不为 Events 或 Skill 另定天数；没有已配置策略时不新增自动清理。保留范围变化后重新从第 1 页加载，不能承诺永久可恢复。若已有公司保留期限，请在同一份答复中补充。 |

B09 的原因是只凭 Session “当前执行”无法区分迟到的旧中断与新一轮；复用原消息 eventId
可以拒绝错误目标，也让 GET 历史中的终态可归属。B10 仍承认首回执丢失的不确定性，
B09 不能代替尚不存在的请求幂等机制。B13 将 Skill 视为触发一次 Agent 执行，复用
普通事件及恢复规则；Builtin 已确认 JSON 行为不因此改变。具体联合 VO 和错误码表在本批确认后整稿同步。

以下是实现校准项，不再要求用户逐个拍数值：数据库表字段/约束与索引、轮询周期/批次、
心跳周期、工具/停止等待超时、事件与缓冲上限。需要依据实际 GaussDB、网关和容量测试确定；
不得把候选 500 毫秒或 15 秒当作本批默认批准。错误/超时的可观察语义仍需遵循 B02/B07～B11。
B15 不编造公司保留天数；已有策略可在同一答复补充，缺少配置不新增自动删除。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.2.7 | 2026-09-08 | 确认 L10：每条工具结果必有布尔 isError，成功 false、失败 true；同步 POST；按用户要求撤下 L11 单字段问题，集中 B01～B15 为一次批量评审。沿用 dfb90ca/pi 证据，建议未确认，图不变。 |
| 0.2.6 | 2026-09-08 | 确认 L9 Mate 调用保留 CallMateTool/{tool,args}，同步 GET/POST 示例；复核同一源码基线的工具名及 Schema。继续 L10 成败标记评审，结果仅文本及既有决定不变，图不变。 |
| 0.2.5 | 2026-09-08 | 确认 L7 内容块数组与 L8 本期仅文本并同步 POST；撤回 JSON/图片块候选及图片动机。补充 dfb90ca 的 Mate 返回链路与固定 pi 证据；L9 工具身份映射、其他细节及整体仍待评审，图不变。 |
| 0.2.4 | 2026-09-07 | 确认 L6 工具调用参数 JSON 对象并同步 POST；继续 L7 工具结果内容结构评审，结合 Read 图片目标说明取舍。其他字段、图片传输与整体未确认；实现证据和图不变。 |
| 0.2.3 | 2026-09-07 | 确认 L5 Agent 完整正文字符串并同步 POST；移除该选择，继续 L6 工具参数结构评审。其他字段及整体未确认；实现证据与 PlantUML 结构不变。 |
| 0.2.2 | 2026-09-07 | 确认 L4 合法超范围页返回 200 空列表和 nextPage=null；移除已确认选择，补齐不掩盖参数/读取错误的边界。仅改设计，源码基线 dfb90ca 不变。 |
| 0.2.1 | 2026-09-06 | 确认 L2 默认 50/上限 200、L3 仅 events/nextPage，不返回 total；同步默认值、示例、图和验收。L4 空页响应待评审，未整体确认，源码基线 dfb90ca 不变。 |
| 0.2.0 | 2026-09-06 | 确认从旧到新、普通整数 page/nextPage，取消跨页固定快照、快照标识及加密游标；保留同形与顺序，移除 L1 选择，改评审每页数量与 total；补齐普通分页变化边界与目标图。 |
| 0.1.0 | 2026-09-06 | 按用户要求开启 ListEvents 修改：完整事件与 POST 对齐、固定分支/提交上界候选、两页与中断/确认示例、源码差距、目标图及验收；POST 未决项保留。 |
