# ListEvents v2 历史查询设计

| 属性 | 值 |
|---|---|
| 文档版本 | 0.4.0 |
| 状态 | L1～L10、B01～B15 语义已确认；精确契约已定稿，可进入实现，target-only |
| 更新日期 | 2026-09-09 |
| 设计仓变更前基线 | `c16ed3f904a85d01d69deb1a3575e2c52cdaa958` |
| L5 字段确认前设计仓基线 | `7349cdf2e037700ddf4917eebef0e19799252f47`；沿用下述实现证据，本轮未重新核对实现 |
| L6 字段确认前设计仓基线 | `050bda2579004b630021300986881ac61ba7142e`；沿用下述实现证据，本轮未重新核对实现 |
| L7 字段确认前设计仓基线 | `019b2dbfbc85edb23d94ffbda7b4963237286f7e`；Mate 适配补充核对见 §2.1，既有 HTTP 证据不整体升级 |
| L9 字段确认前设计仓基线 | `33a7344ff3b98e143e98894f6105f53160ab0734`；复核同一 dfb90ca 的 CallMateTool.name/parameters/execute，其他源码证据不变 |
| L10 字段确认前设计仓基线 | `0f3f58f2f203fe4fe88c308032e1815b1622683b`；沿用工具结果源码证据，本轮只确认 HTTP 目标字段 |
| 本批确认前设计仓基线 | `9096f1e9ae445e67292c5e7d5a9e0d2ac10d8f5d`；本批语义确认不表示代码已实现 |
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
- 原 B01～B15 批次只修改 CampusClaw 内部目标契约；2026-09-09 的 Thinking 决定
  同步 Mate 公共 API 与前端设计，运行时代码仍待实现。当前十项内部接口由统一清单管理。内部 `sessionId` 不直接暴露给浏览器。

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

L1～L10 与 B01～B15 已确认。精确字段、条件必填、枚举、错误码和语言文案由
[公共字段源](接口契约-v2/common.json) 的 `eventContract` / `contractSections` 维护，
渲染到 GET/POST 的统一 HTML；两个操作引用同一份定义，不各写一套。

历史读取三类已接受 user.*、完整 agent.message/thinking/tool_call/tool_result、
session.status_idle，以及模型配置、thinking 配置和压缩完整记录。delta、心跳、连接标记不入历史。
每条完整记录有服务端 eventId 与保存一次的 UTC 毫秒 createdAt；按内部已提交顺序展示，
不按时间戳排序。agent.* 和 idle 的 sourceEventId 始终引用原始 user.message.eventId，
确认续跑不换根消息；中断用 targetEventId 指向它。共享终态只保留一条。

Agent 正文是字符串，工具 arguments 是对象，工具结果是至少一个纯文本块；允许空 text
和多个块，禁止 JSON/image 块。真实 Assistant 没有正文可保存 content=""（例如只有工具调用），
客户端不必画空气泡；不能凭空合成一条回答或把工具文本当成模型回答。
已知 Usage 随对应完整 Agent 消息保存，不在 delta、thinking 或各个工具事件重复计数。
无可验证用量时省略而非伪造零；lifetimeUsage 还包括压缩、失败尝试等可计费用量，不能以
公开消息 usage 简单求和代替 Session 的累计权威统计。

Thinking 展示按 §2.2 的原文规则执行：开关控制后续执行，已有思考原文
不会因关闭而隐藏；读取仍受当前授权和保留策略约束。凭据、内部序号、执行 ID、
Skill 私有正文及路径不进入公开投影。GET 的 Accept-Language 只决定本次错误 resMsg，
不重译已保存工具 text 或失败 message；同一事件在 GET 与 POST 必须逐字段相同。

工具失败由 isError=true 和稳定 errorCode 表达，成功必须省略 errorCode；错误文本经过
安全投影后保存。未知 Mate 错误映射通用 TOOL_EXECUTION_FAILED，不能分析原始错误文字猜码。
工具超时只表示调用期限已到，不保证远端副作用停止；整轮失败只有在本地执行确已退出并
可靠保存后，才发送 reason=failed 的权威 idle。HTTP 断流本身不是失败终态。

配置事件保留真实变更的 previous/current 值及既有原因；模型自动回退的 agentRefresh 和
模型能力关闭 thinking 的 modelCapability 不因 v2 改名丢失。配置事件不进入模型上下文，
只在历史展示；自动压缩可在对应执行 SSE 展示，手动 compact 保持 JSON。
压缩摘要和 firstKeptEntryId 等恢复数据留在内部，不把提示词、私有摘要和内部关联直接返回。
全部旧持久化类型必须逐类映射或明确不公开理由；未知持久化类型报 EVENT_LIST_FAILED，
不能静默跳过后声称完整。

### 2.0 既有事件的完整迁移清单

源码基线为 `dfb90cac4e233e09a0b8f047f7e9f4682f5ad238`，以下旧名称来自
`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventType.java`
与同目录 `RuntimeEntryCodec.java` 的各 Entry 工厂及恢复投影。此表描述 target-only 架构变更：
内部原始事件先归一，再经共享完整事件投影供历史与 SSE 使用；旧名称不是兼容 wire 别名。

| 既有内部类型或记录 | v2 目标投影 / 不公开理由 |
|---|---|
| user.message | 完整 user.message；旧存量迁移时生成一次稳定 eventId，保留有序正文与 file 块；内部执行与根消息关联持久化，不能每次查询重新生成 ID |
| assistant.message.started | 不公开；客户端由第一段 delta 或 completed 建立消息 |
| assistant.message.delta / completed | agent.message + delta/completed；只有 completed 入历史，完整正文和已知 Usage 保存一次 |
| assistant.thinking.started | 不公开；不需要额外开始记录 |
| assistant.thinking.delta / completed | 执行 thinking=true 时将可读推理原文映射 agent.thinking；delta 用于预览、completed 保存并供历史读取；不透明签名保留内部 |
| tool.execution.started | 参数收集完成后投影完整 agent.tool_call，保存 toolCallId、参数对象和确认标记 |
| tool.execution.delta / completed | 不单独公开；内部工具进度不构成新的业务历史或通用命令生命周期 |
| tool.result | 完整 agent.tool_result；至少一个 text 块、必填 isError，失败映射稳定安全码 |
| session.model.changed / session.thinking.changed | session.model_changed / session.thinking_changed；保留真实 previous/current 与原有 reason，只进入历史 |
| session.compaction.started / failed | 不单独公开；内部压缩过程与恢复判断保留，最终整轮确实失败时才产生 failed idle；手工 Compact 失败仍按其 JSON 错误契约 |
| session.compaction.completed | 完整 session.compacted；内部摘要、恢复边界和独立 Usage 仍保留供恢复与累计，不进入公共 payload |
| session.status.idle | 对应 session.status_idle；持久化真实 reason/原消息 sourceEventId，确认等待边界与实际执行终态区分 |
| stream.end / stream.error | 连接级信号不入历史；正常 EOF 跟随对应 idle，不能把断线编造成业务失败 |
| 独立 Usage 累计记录、不透明 thinking 签名/Skill 展开上下文、树结构控制记录 | 不作为额外公共事件；分别用于 lifetimeUsage、模型恢复和分支重建，不能重复计费或泄露私有上下文 |

存量未保存的思考文本或精确因果关联不能凭空补造。实现应提供一次可重跑的迁移/兼容读取方案，
对缺少安全映射的历史显式报错并提示迁移处理；不得逐次分配新 ID 或静默丢弃后声称历史完整。
本次静态契约校验不证明旧数据迁移已实现。

### 2.1 Mate 工具的文本返回与源码边界

本批仍复核 `pi-mono-java@dfb90cac4e233e09a0b8f047f7e9f4682f5ad238`：
`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEntryCodec.java`
的 modelChangedEntry/thinkingChangedEntry/compactionEntry/usageRecord/appendPublicPayload
证明当前已有配置、压缩和独立 Usage 存储；当前 appendToolResultPayload 会按读取 locale 生成
errorMessage，时间还会使用模型 timestamp。目标共享投影将其改为固定完整事件时间、保存安全
错误文本、纯文本块、sourceEventId 和已知 usage 归属。这是本批源码差距，不是字段重命名即可完成。
旧 `campusclaw/.../com/huawei/hicampus/claw/...` 证据继续保留，各路径均相对实现仓。


2026-09-08 重新读取 `pi-mono-java@dfb90cac4e233e09a0b8f047f7e9f4682f5ad238`
的下列实现；这是对相同 commit 的 Mate 返回链路补充核对，不替换旧工具专题的其他结论。
以下路径均相对各自仓库根目录。

| 源码证据 | 已观察行为 |
|---|---|
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/HttpMateToolClient.java:340` · `toToolResult` | Claw 客户端读取 `resCode/resMsg/result`；仅 `resCode` 文本值为 `0` 时成功，把非空 result 用 `JsonNode.toString()` 序列化，metadata 为 null。result 缺失或 null 时当前返回空字符串；B03 保留空文本语义，并将字符串 result 改为 asText()，对象/数组仍序列化。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/common/client/mate/MateToolClient.java` · `ToolResult` | 内部结果是 `String content`、`Map metadata`、`boolean isError`，没有保留原始 JSON 节点或图片块。 |
| `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/CallMateTool.java:46` · `name/parameters/execute` | 工具名为 CallMateTool；Schema 的 tool 为业务工具名，args 为对象且可省略，执行时缺省为 Map.of()。L9 固定包装；B03 已确认公共事件中补齐 args={}。 |
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
已同步替换。isError 已由 L10 确认；稳定错误码及脱敏文案按 B01 确认语义和共享错误码表投影。

用户明确仅文本后，尚未确认的独立 JSON 块候选撤回。Mate 返回复用现有文本结果；调用方
展示 text，不把某段恰好可解析的 JSON 当作稳定跨工具业务对象。没有公共 `structuredContent`，
也不新增 Mate 原始 ResultBean 信封。Mate result 为字符串时当前 `JsonNode.toString()` 会保留
JSON 字符串的引号与转义；服务端实现仍未核对；B03 已确认目标适配去掉字符串 result 的 JSON 引号/转义，保留对象/数组为 JSON 文本，差异属于产品约束。

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
错误码、文案、空文本和块数量按 B01/B02 的确认语义落入当前共享表。

B01～B03 已确认失败码、空文本与 Mate 归一；原 L11 单字段问卷不再恢复。错误码的具体字符串和中英文表已按确认语义写入精确契约。

### 2.2 Thinking 原始文本展示（2026-09-09 已确认）

<a id="thinking-original-text"></a>

用户明确要求：**“展示原始推理不再有摘要设计”**。这是已确认的产品约束，适用于
Provider 事件投影、Runtime Events、Mate 公共 Chat API 和产品前端；替代 B05、Mate
1.4.4 及前端 1.6.0 中“只展示公开摘要”的要求。B05 关于后续开关不隐藏既有历史的决定保留。
本节是当前 Thinking 展示的权威设计；以下源码差距仍需实现，本次没有修改运行时代码。

**目标行为。** `agent.thinking.content` 直接使用模型实际返回的可读推理文本，保留文字、
空格、换行及片段顺序。不再设计摘要生成、摘要审核、摘要接口、摘要 DTO 或额外模型调用，
也不再以 `publicSummary` 或等价标记作为展示和持久化门槛。Provider 原始 SSE 仍先转为
类型化领域事件，再由两层 API 各自投影身份和协议；文本原样展示不等于整帧字节透明转发。

- 本次执行的 `thinking=true` 且 Provider 返回可读文本时，发送 `agent.thinking`；
  `delta.content` 只含新增文本，`completed.content` 是同一逻辑思考块的完整原文。
  completed 保存一次，和 delta 复用 eventId；GET 返回与 SSE completed 相同的已保存记录。
- `thinking=false` 不产生新的公开 Thinking；后续关闭开关不删除或隐藏已保存的思考原文。
  每次历史读取仍按当前权限、分支和保留策略进行。
- 没有可读文本时不凭空生成思考内容。仅用于模型续传的不透明 signature、加密载荷或
  `reasoning_details` 中无文本的结构保留在 Provider 上下文，不解码、猜测或当作 UI 文本。
  “原始”指模型实际返回的可读内容，不声称取得模型未返回的内部状态。
- 前端以纯文本展示原文，保留换行，不激活 Markdown/HTML；折叠标题可使用“正在分析”
  或“分析过程”，内容区域标明“原始推理”。标题是前端状态文案，不由原文另行生成摘要。
  未收到文本时只显示等待状态，不伪造正文；完成态覆盖 preview，未完成 preview 不冒充历史。

**源码证据与实现差距。** 本次设计仓分析基线为
`1eb85523fe1d210856851c5185d64858562db0c6`。Java Thinking 链路补充核对至
`4cc8dd86f601417c22cf9306e52152acbb59bb60`，旧 `dfb90ca` 等基线继续只支持其原有专题；
本次不整体升级其他模块或外部公共契约证据。pi 仍使用固定
`5cd93f688aaab89dbb6dfa4aca535f21796ae185`。下列路径相对各自仓库根目录。

| 仓库 / 源码证据 | 已观察行为 | 与本次目标的关系 |
|---|---|---|
| Java · `modules/ai/src/main/java/com/campusclaw/ai/provider/mate/MateChatSseParser.java:182` · `parseReasoning/appendReasoningText/finishThinking` | 读取 reasoning_content、reasoning、reasoning_text、reasoning_details，将可读文本累加为 Thinking delta/end，签名单独保存；使用默认事件构造器 | 保留已有原文解析能力；Mate/GLM 无需提供新标记 |
| Java · `modules/ai/src/main/java/com/campusclaw/ai/stream/AssistantMessageEvent.java:103` · `ThinkingStartEvent/ThinkingDeltaEvent/ThinkingEndEvent` | 事件增加 publicSummary；便利构造器默认 false | 此标记不再属于目标展示策略；实现同步核对生产者、消费者和测试后移除退休字段 |
| Java · `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeV2EventProjector.java:244` · `projectThinking/emitThinkingDelta/persistThinking` | 仅 publicSummary=true 才发送 delta 或保存 completed，因此 Mate 默认事件被过滤；已有按块分配 eventId、先保存再发送完整事件的骨架 | 撤销摘要门槛，复用事件身份和完整记录链路，不能只改前端文案 |
| Java · `frontend/src/components/ThinkingDisclosure.vue` · template | 当前标注公开摘要，等待及空态也使用摘要文案 | 更新为原文展示及对应等待/空态；内容继续纯文本 |
| pi · `packages/ai/src/types.ts:356` · ThinkingContent；`:535` · AssistantMessageEvent | thinking 文本与 thinkingSignature 分离；thinking_start/delta/end 不要求 publicSummary | 支持保留可读文本与不透明恢复数据的区分，不证明企业 HTTP 边界应照搬 pi |
| pi · `packages/agent/src/agent-loop.ts:281` · streamAssistantResponse；`packages/coding-agent/src/core/agent-session.ts:621` · _handleAgentEvent | thinking 作为 message_update 继续传递；完整 Assistant 消息在 message_end 后进入 Session 持久化 | 保持领域生命周期与完整消息恢复；公共原文展示是本次用户产品决定 |

**变更原因与溯源。** 实现仓 ADR-0030（`e4ef301c`，2026-08-27）曾记录直接展示原始推理。
随后 Mate 的摘要限制在设计仓 `9bedccc` 进入 v2 候选，`9096f1e` 将其列为 B05 推荐，
`2ee2a32` 记录四组批量确认；当时没有明确写出与 ADR-0030 的冲突及 Mate/GLM 原有展示能力
会消失的影响。实现按后来的摘要门槛开发，造成既有能力回退。本次按用户明确决定撤销该限制，
无需为恢复原文展示补造一个摘要能力。历史批量记录保留作溯源，不能继续作为仅摘要展示的依据。
差异分类为**产品约束变更**：撤销 Thinking 上的摘要限制；工具/错误投影、凭据和内部身份边界
各按原契约执行，不把推理文本塞入错误、日志或新增诊断字段。

**实施切片与验收。** 先同步 Provider 事件及 Runtime 投影，再验证 completed 持久化和 GET，
然后同步 Mate bridge 与前端；沿用现有分层和依赖，不新增 Maven 依赖或摘要组件。
验收使用 Mate/GLM reasoning_content 流，断言开启时原文 delta/completed/历史一致，后续关闭
仍可读取旧原文；覆盖多思考块、空格换行、completed 覆盖预览、无文本/仅 signature、关闭时
不产生新事件，以及 HTML 样文本只能按纯文本显示。可读原文不能因缺少摘要标记被静默记作
无公开事件；未完成 preview 仍遵循既有断线和权威历史规则。

本次设计交付校验：Runtime `validate-chat-api.py`、Mate `validate-chat-events-v1.py`、
前端 13 组 DOM 状态回归均通过；PlantUML 生成、SVG XML/同步、ASCII、Markdown 图链及
图源行锚、全仓 Mermaid 禁用与 `git diff --check` 通过。相关图已按原尺寸和缩放视图检查，
保留原有分层与职责链，原尺寸入口见本文 §6 和[前端全局目标图](../04-CampusClaw前端体验/target_frontend_components.svg)。
本地 HTML 浏览器预览被浏览器 URL 安全策略拒绝，本次不宣称浏览器截图验收或后端集成测试完成。

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

分支切换、访问权限改变、记录清理或可见权限变化可能使已有位置移动。调用方
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
非法参数或读取失败转成空成功。非法页码或 limit 返回 `400 / INVALID_EVENT_LIST_QUERY`；其他读取错误见精确模型，不存在游标解密/过期错误。

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
  B09 已通过原消息 eventId 明确已知回执后的归属；B10 接受首回执丢失的不确定性，不新增请求 ID、执行 ID 或幂等键。

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

[PlantUML 源码：target_event_history_paging](设计图/事件历史查询/diagram.puml#L58)

## 7. 实施切片与验收

新增批次验收：原消息归属在普通输出/续跑/失败/中断中不漂移；迟到中断拒绝新执行；
失败缺码/成功带码/非布尔 isError/非文本块被拒绝；GET/POST 与 Skill 完整帧同形；
后续关闭 thinking 不隐藏已有思考原文；配置、压缩与 Usage 投影不泄露内部 ID；
Skill 展开前回执、绑定变更重检、内部上下文恢复与保留策略保持一致。


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

当前交付是契约示例与静态验证，不包含上述运行时测试的通过声明。B01～B15 语义已确认，精确报文与码值已补齐，可进入实现。部署与数据库数值仍需实现校准。

## 8. 批量确认结果

批次 `2026-09-08.1`，用户一次提交 tools/events/lifecycle/integration 四组 A-recommended，
B01～B15 语义全部确认，L1～L10 保持确认。本次确认已实际提交；用户要求完成后通知实现任务，不增加整稿确认门槛。
本批确认前设计为 `9096f1e9ae445e67292c5e7d5a9e0d2ac10d8f5d`。表中展示当前有效决定；B05 已由 2026-09-09 明确指令替代，
具体字段与码值按上文共同源展开；实现校准项不要求用户逐个拍数值。

范围为 Claw 内部 Events、配置和 Skill；Mate 公共 API 不随本批修改。B09 的目标/关联字段和
B13 Skill SSE 是架构变更；B01 脱敏、B14 信任边界是安全加固，其余公开行为为产品约束。
类名与装配仍是 target-only 实施骨架，不声称现有 Java 已实现。

| 编号 | 需要决定的内容 | 已确认方案 |
|---|---|---|
| B01 | 失败错误码 | 失败时必有稳定 errorCode，成功时省略；区分用户拒绝、参数错误、工具不存在、超时和执行失败。文案放在 text，使用脱敏可展示信息；不透传 Mate 原始错误码、异常栈或凭据。 |
| B02 | 空文本与大小 | 工具结果至少一个 text 块，允许 text=""，不强制只有一块；没有正文时不伪造 Agent 回答。沿用工具自身的有说明截断；HTTP 不静默截断完整事件。大小上限由实现校准，超限必须明确失败或断流并可查历史。 |
| B03 | Mate 文本归一 | CallMateTool 缺省 args 在公开事件中补 {}；Mate result 为字符串时直接作为文本，对象/数组变为 JSON 文本，null 为 ""。这是已确认的适配调整，当前客户端对字符串使用 JSON 序列化的实现将有变化。 |
| B04 | 时间与增量 | 完整事件 createdAt 使用 Claw 形成该权威记录时的 UTC 毫秒时间，保存一次，GET/POST 复用；delta 使用 content 字符串，只含新增文本，沿用同一 eventId，不带 createdAt。completed 覆盖预览，之后忽略迟到 delta。 |
| B05 | Thinking 展示 | 2026-09-09 用户明确改为展示模型返回的原始推理，撤销摘要设计和 publicSummary 门槛；thinking 控制后续执行，关闭不隐藏已保存原文，读取受当前权限约束。当前完整规则见 §2.2；此项替代 2026-09-08 的仅摘要推荐。 |
| B06 | 工具确认标记 | 每个完整 agent.tool_call 都带 requiresConfirmation 布尔值；本期顺序发出需确认调用，同一执行一次只挂起一个待确认 toolCallId。允许/拒绝后分别续跑，拒绝产生 isError=true 的工具结果。 |
| B07 | 结束原因 | session.status_idle.reason 固定 done、failed、terminated、confirming；confirming 只结束当前 SSE，Session 继续 running。failed 携带稳定 errorCode 和可展示 message；工具失败可由 Agent 继续处理，不自动等同于整轮 failed。 |
| B08 | 控制请求竞争 | 确认与中断在同一执行的事务内重检；停止请求先提交，则拒绝确认；确认先提交，中断仍可停止续跑。重复/过期确认返回 409，不重复执行工具；等待超时不伪造已停止。 |
| B09 | 防止误停下一轮 | 给 user.interrupt 增加必填 targetEventId，引用原 user.message 的 eventId；不匹配当前执行时返回 409。agent.* 和 idle 用 sourceEventId 引用同一原消息，便于历史对账。复用已有事件身份，不新增 runId/executionId；这是已确认的字段扩展。 |
| B10 | 断线与回执丢失 | 保留无自动写重试的方案：没有收到首帧时显示“提交结果不确定”，不靠相同文本猜测成功，不新增幂等键。收到回执后按 eventId 和 B09 的关联补读历史；断流本身不取消执行，也不代表失败。 |
| B11 | HTTP 故障与心跳 | 接受前：非法参数 400、不存在 404、状态冲突 409、容量/依赖暂不可用 503、内部失败 500，统一 ResultBean；接受后不得伪装成未接受。SSE 已开始则不改成 JSON，能保存权威失败则发送 failed，否则断流并对账。采用 : ping 注释心跳；慢客户端可丢 preview，完整帧不能入队则断开。 |
| B12 | 配置、压缩与用量 | 模型/思考配置变更和压缩保留独立完整事件，映射到统一 v2；Usage 放在对应完整 Agent 消息，Session 保留累计用量。不新增通用 command 生命周期、进度或子 Agent 公共事件；已有内部记录逐类标明公开映射或不公开理由。 |
| B13 | Skill 请求与响应 | 共享 POST /sessions/{sessionId}/command：Skill 用 name="skill:<name>"、arguments 字符串和可选 fileIds；Skill 执行返回与消息一致的 SSE，Builtin 保持普通 JSON。Skill 遵循同一 Session 单消息准入，首帧回执为展开前的 user.message，随后普通 Agent/Tool/idle 事件，不新增 commandId。 |
| B14 | Skill 快照与恢复 | 受理前解析完整 Agent/Skill 快照并重检绑定、权限和容量，受理后本次执行固定快照；Skill 正文按资源内容处理，不提升为系统权限。内部恢复所需内容沿用 Session 持久化与保留策略，公共历史只展示用户调用和执行结果，不另建 Skill 全文审计副本。 |
| B15 | 数据保留 | 沿用部署统一的数据保留策略，不为 Events 或 Skill 另定天数；没有已配置策略时不新增自动清理。保留范围变化后重新从第 1 页加载，不能承诺永久可恢复。若已有公司保留期限，请在同一份答复中补充。 |

B09 的原因是只凭 Session “当前执行”无法区分迟到的旧中断与新一轮；复用原消息 eventId
可以拒绝错误目标，也让 GET 历史中的终态可归属。B10 仍承认首回执丢失的不确定性，
B09 不能代替尚不存在的请求幂等机制。B13 将 Skill 视为触发一次 Agent 执行，复用
普通事件及恢复规则；Builtin 已确认 JSON 行为不因此改变。具体联合 VO、错误码表和完整示例已同步到当前 HTML，作为统一实施契约。

以下是实现校准项，不再要求用户逐个拍数值：数据库表字段/约束与索引、轮询周期/批次、
心跳周期、工具/停止等待超时、事件与缓冲上限。需要依据实际 GaussDB、网关和容量测试确定；
不得把候选 500 毫秒或 15 秒当作本批默认批准。错误/超时的可观察语义仍需遵循 B02/B07～B11。当前不新增 Maven 依赖，使用现有 JDK/Jackson 完成类型化投影；实际实现若新增依赖仍须按通用规则披露。
B15 不编造公司保留天数；已有策略可在同一答复补充，缺少配置不新增自动删除。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.4.0 | 2026-09-09 | 按用户明确决定展示模型返回的原始推理，撤销摘要设计；同步 Runtime、Mate、前端及历史语义。Thinking 局部源码基线 4cc8dd86，固定 pi 5cd93f6，代码仍待同步。 |
| 0.3.0 | 2026-09-08 | 记录用户四组全部按推荐确认 B01～B15；补齐共享事件字段、错误码、源消息关联、配置/压缩/Usage 与 Skill 示例，作为统一实施契约。同步相关类图、正文与校验，运行时仍 target-only。 |
| 0.2.7 | 2026-09-08 | 确认 L10：每条工具结果必有布尔 isError，成功 false、失败 true；同步 POST；按用户要求撤下 L11 单字段问题，集中 B01～B15 为一次批量评审。沿用 dfb90ca/pi 证据，建议未确认，图不变。 |
| 0.2.6 | 2026-09-08 | 确认 L9 Mate 调用保留 CallMateTool/{tool,args}，同步 GET/POST 示例；复核同一源码基线的工具名及 Schema。继续 L10 成败标记评审，结果仅文本及既有决定不变，图不变。 |
| 0.2.5 | 2026-09-08 | 确认 L7 内容块数组与 L8 本期仅文本并同步 POST；撤回 JSON/图片块候选及图片动机。补充 dfb90ca 的 Mate 返回链路与固定 pi 证据；L9 工具身份映射、其他细节及整体仍待评审，图不变。 |
| 0.2.4 | 2026-09-07 | 确认 L6 工具调用参数 JSON 对象并同步 POST；继续 L7 工具结果内容结构评审，结合 Read 图片目标说明取舍。其他字段、图片传输与整体未确认；实现证据和图不变。 |
| 0.2.3 | 2026-09-07 | 确认 L5 Agent 完整正文字符串并同步 POST；移除该选择，继续 L6 工具参数结构评审。其他字段及整体未确认；实现证据与 PlantUML 结构不变。 |
| 0.2.2 | 2026-09-07 | 确认 L4 合法超范围页返回 200 空列表和 nextPage=null；移除已确认选择，补齐不掩盖参数/读取错误的边界。仅改设计，源码基线 dfb90ca 不变。 |
| 0.2.1 | 2026-09-06 | 确认 L2 默认 50/上限 200、L3 仅 events/nextPage，不返回 total；同步默认值、示例、图和验收。L4 空页响应待评审，未整体确认，源码基线 dfb90ca 不变。 |
| 0.2.0 | 2026-09-06 | 确认从旧到新、普通整数 page/nextPage，取消跨页固定快照、快照标识及加密游标；保留同形与顺序，移除 L1 选择，改评审每页数量与 total；补齐普通分页变化边界与目标图。 |
| 0.1.0 | 2026-09-06 | 按用户要求开启 ListEvents 修改：完整事件与 POST 对齐、固定分支/提交上界候选、两页与中断/确认示例、源码差距、目标图及验收；POST 未决项保留。 |
