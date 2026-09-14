# CampusAgent Channel 与飞书接入设计

| 属性 | 值 |
|---|---|
| 文档版本 | 3.0.0 |
| 状态 | target-only；渠道接入、公共 Chat 端口和依赖尚待实施设计 |
| Runtime 契约 | [当前 Session Events](chat-events-design.md)；不依赖已撤销的 entrySeq/旧事件形状 |
| 源码证据 | [固定基线与方案参考](飞书渠道/source-evidence.md)；外部资料范围仍为 2026-08-20 |
| 更新日期 | 2026-09-14 |

## 1. 目标与边界

飞书适配位于 mate-service，经 ChannelChatPort 进入 Chat 应用核心，由 Runtime Client 驱动 CampusClaw。渠道负责账号、入站去重、会话映射和卡片投递；Agent 内核不感知飞书身份或 SDK。

生产目标保留 Java Server SDK Adapter：自建应用默认长连接，Webhook 为部署选项。CLI 用于开发和 PoC，Python Channel SDK 提供行为参考，OpenAPI MCP 属于工具调用平面。SDK 的准确版本和依赖树尚未核定，见 §12。

入站先持久化 Inbox/Outbox，再由 Worker 执行，避免回调同步等待模型。Runtime 请求结果不确定时查询完整事件；没有可靠接受身份不能自动重发消息。渠道仍不向飞书展示原始 Thinking、工具参数或内部错误，这是与浏览器展示范围不同的产品约束。

## 2. 方案选择与理由

![飞书接入方式选择](飞书渠道/channel_feishu_option_decision.svg)

[原尺寸 SVG](飞书渠道/channel_feishu_option_decision.svg) · [PlantUML 源码：`channel_feishu_option_decision`](飞书渠道/diagram.puml#L1)

| 方式 | 本设计用途 | 代价与边界 |
|---|---|---|
| Java Server SDK | 默认生产适配器 | 与 Java 生命周期、事务、Secret 和监控集成；新增依赖待核定 |
| lark-cli | 本地开发、PoC、Schema 探查 | NDJSON 子进程与本机事件总线，仍需监管和数据库去重，不作为集群消费组 |
| Python Channel SDK | 行为参考或独立 Connector 候选 | 覆盖规范化、策略和流式卡片；采用服务时新增跨语言部署和私有 API |
| OpenAPI MCP | Agent 主动操作飞书 | 不承担可靠消息入站、Inbox 或 Outbox |
| Raw Webhook/OpenAPI | SDK 无法满足时的备选 | 自行承担验真、解密、兼容和限频成本 |

具体协议、固定源码路径与符号见 [方案证据](飞书渠道/source-evidence.md)。这些观察只适用于登记版本，不表示已验证当前外部服务或本项目部署。

## 3. 范围与非目标

### 3.1 本版范围

- 飞书企业自建应用的长连接入站；
- 可选 Webhook 入站，复用相同应用端口；
- 单聊、群聊 @ 机器人和群话题的 Conversation 绑定；
- 文本与 `post` 可见文本规范化；
- 数据库 Inbox、Conversation mapping、执行状态、Delivery 与 Outbox；
- 通过当前 Runtime POST SSE 执行，并通过 GET Events 做持久化恢复；
- CardKit 流式卡片的创建、合并更新、终态和错误投影；
- CLI Adapter 的开发/PoC 运行边界。

### 3.2 非目标

- 不把飞书消息事件暴露为浏览器公共 HTTP API；
- 不恢复公共 `Run`、`run_id`、独立 Run Events 或 `run_seq`；
- 不把 `lark-mcp` 当成消息接收队列；
- 不在 v1 下载图片、文件、音视频并导入 Attachment Service；
- 不开放用户从飞书消息指定 `agent_id`、`model_id`、`thinking` 或 Runtime
  `session_id`；
- 不允许多个入口同时写同一个 Channel 专属 Runtime Session；
- 不在首版实现卡片按钮到 Steer/FollowUp/Abort 的映射。

## 4. 目标架构与责任边界

![飞书 Channel 目标架构](飞书渠道/channel_feishu_target_architecture.svg)

[原尺寸 SVG](飞书渠道/channel_feishu_target_architecture.svg) · [PlantUML 源码：`channel_feishu_target_architecture`](飞书渠道/diagram.puml#L54)

### 4.1 服务责任

| 组件 | 责任 | 不承担的责任 |
|---|---|---|
| `FeishuTransport` | SDK 长连接或 Webhook 生命周期、协议验真与原始事件接收 | 数据库业务幂等和 Agent 执行 |
| `FeishuProviderAdapter` | SDK 类型解析、内容规范化、mention/发送者策略、Provider ID 封装 | 直接调用 CampusClaw |
| `ChannelInboundService` | 事务去重、Conversation 解析、Inbox 与 Outbox 原子提交 | 同步等待模型结果 |
| `ChannelExecutionWorker` | 同 Conversation 串行、Chat/Session 绑定、Runtime SSE 消费与恢复 | 解析飞书原始 JSON |
| `ChannelChatPort` | 进入 `mate-service` Chat 应用核心的内部端口 | 暴露新的公共 HTTP 契约 |
| `Chat Application Core` | 创建 Channel 专属 Chat，维护 `chat_id -> session_id`，调用 Runtime Client | 感知飞书 SDK 类型和凭据 |
| `ChannelEventProjector` | 把允许展示的 Runtime 事件转换为 Channel desired view | 公开 thinking、工具参数或内部错误 |
| `ChannelDeliveryWorker`（target-only） | 执行 Outbox 投递任务，检查 lease/fencing 与视图版本，使用稳定 uuid/sequence 调用 Gateway | Provider 内容映射和 Chat/Session 身份决策 |
| `FeishuMessageGateway` | token、CardKit、消息回复、限频与 Provider 错误分类 | 决定 Chat/Session 身份 |
| CampusClaw | Session、Entry、active execution 和请求级 SSE 权威 | 读取飞书 tenant/user/chat/message ID |

### 4.2 应用端口

以下是目标 Java 类型边界，不表示当前仓库已有实现：

| 端口 | 主要方法语义 | 数据对象 |
|---|---|---|
| `ChannelEventSource` | `start`、`stop`；只管理 Provider transport | SDK 类型只存在于 Adapter 内 |
| `ChannelInboundPort` | `accept` 返回 durable receipt，不返回 Agent 结果 | `ChannelInboundMessageDTO` / `ChannelAcceptResultDTO` |
| `ChannelChatPort` | 确保 Channel Chat/Session，提交消息，查询持久化事件和 Session 状态 | `ChannelChatSubmissionDTO` / `ChannelChatEventDTO` |
| `ChannelMessageGateway` | 创建卡片、按 sequence 更新、finish、发送终态错误 | `ChannelDeliveryCommandDTO` / `ChannelDeliveryResultDTO` |

Controller/API 边界若未来出现，必须使用独立 `*RequestVO` 与 `*ResponseVO`；Mapper 和
数据库交互使用 DTO。Service 负责 VO/DTO 转换、默认值、跨记录校验和状态迁移。
Java 数据层默认使用 MyBatis Spring Boot Starter `3.0.4`，除非工程兼容性评审确认
需要其他版本。

若将 Python SDK 或 CLI Adapter 独立部署，Connector 到 `mate-service` 的私有 intake
HTTP 必须另行逐接口评审；本设计没有授权直接复用浏览器公共 Chat API，也没有定义
一个接收任意 Provider 原始 JSON 的通用端点。

## 5. 飞书入站设计

### 5.1 长连接与 Webhook

飞书官方 Echo Bot 指引展示了自建应用通过长连接订阅
`im.message.receive_v1`；官方事件订阅安全文档同时区分了长连接与开发者服务器
Webhook。参考：

- [Echo Bot 应用配置与长连接](https://open.feishu.cn/document/develop-an-echo-bot/faq)；
- [事件订阅加密配置与两种接收方式](https://open.feishu.cn/document/server-docs/event-subscription-guide/event-subscription-configure-/encrypt-key-encryption-configuration-case?lang=en-US)；
- [Server SDK 能力说明](https://open.feishu.cn/document/ukTMukTMukTM/uETO1YjLxkTN24SM5UjN?lang=zh-CN)。

选择规则：

- 企业自建应用、无公网回调依赖时默认 `WS` 长连接；
- 已有统一公网 Gateway、需要平台级 WAF/流量治理或应用类型要求回调时使用 Webhook；
- 两种 transport 只在 `FeishuTransport` 内不同，向下必须生成相同
  `ChannelInboundMessageDTO`；
- Webhook 的 TLS、Body 上限、时间戳/签名、challenge、解密、限流和错误脱敏由
  Gateway 与 Adapter 共同承担；
- 长连接的 SDK 鉴权不能替代业务层 tenant、sender、mention 和 dedupe 校验。

### 5.2 事件与权限

首版只要求：

- `im.message.receive_v1`；
- 单聊消息；
- 群聊仅接受明确 @ 当前机器人；
- 发送机器人消息与 CardKit 创建/更新权限。

权限名和可申请范围必须在应用发布时以飞书开放平台当前界面为准，不把调研日期的
权限字符串永久固化为代码常量。默认不申请群全量消息、通讯录全量读取或用户身份
写操作权限。

### 5.3 规范化与策略顺序

固定处理顺序：

1. transport 完成连接鉴权，或 Webhook 完成签名/解密；
2. 校验 event type、当前 App/账号和允许 tenant；
3. 读取 `message_id`、`event_id`、`chat_id`、`root_id/thread_id`、sender 与
   `message_type`；
4. 过滤当前机器人自发消息和其他 bot，避免循环；
5. 群聊确认 mention 当前机器人并删除机器人自身占位；
6. 按消息类型解析内层 content，执行字节、JSON 深度、字符数和资源数量上限；
7. 生成不含凭据和原始 Header 的 `ChannelInboundMessageDTO`；
8. 数据库事务成功提交 Inbox 与 Outbox 后，回调才返回成功。

`message_id` 是首要 Provider 幂等键，`event_id` 用于投递审计。考虑到成熟实现观察到
重连可能为同一逻辑文本产生新 ID，文本再计算以下逻辑摘要作为第二层告警/去重候选：

```text
sha256(account_id || sender_id || chat_id || create_time || normalized_content)
```

数据库硬唯一约束仍以 `channel_account_id + provider_message_id` 为主。逻辑摘要自动
抑制必须有短时间窗，并记录原因，避免用户主动重复发送相同文本被永久误判。

### 5.4 消息类型

| 飞书类型 | v1 行为 | 原因 |
|---|---|---|
| `text` | 支持；解析文本并移除机器人自身 mention | 最小对话能力 |
| `post` | 支持有界可见文本、链接文字和 mention 显示内容 | 不把富文本 JSON 直接交给模型 |
| `interactive` | 普通消息入站不转 Prompt；卡片 action 另行设计 | 结构化操作不能无损降级成自由文本 |
| `image/file/audio/media/video` | 返回明确“不支持附件”提示 | 下载、扫描、文件 ID 与保留期尚未评审 |
| `sticker/share_chat/share_user/system` | 忽略或返回有界提示 | 不产生不可解释 Prompt |

规范化后按当前 Runtime content 文本约束验证；渠道可以采用更小产品上限，但不得沿用旧 message 字段的历史上限。空白内容不创建 Chat 消息或 Runtime Entry。

## 6. Conversation、Chat 与 Session

当前责任链固定为：

```text
Feishu provider conversation
  -> channel_conversation_id
  -> mate-service chat_id
  -> CampusClaw session_id
```

Channel 不直接把 Provider conversation 当 Runtime Session。每个 Channel Conversation
创建一个 `mate-service` 管理的专属 Chat，并持久化私有 `chat_id -> session_id` 映射。
CampusClaw 只接收 `session_id` 与规范化消息。

| 飞书场景 | Conversation 唯一元组 | 上下文隔离 |
|---|---|---|
| 单聊 | `account + tenant + chat_id + empty_thread` | 同一用户与机器人的持久 Chat |
| 群聊新的顶层 @ | `account + tenant + chat_id + root_message_id` | 每个根消息独立 Chat |
| 群聊话题/回复 | `account + tenant + chat_id + root_id` | 继续根消息对应 Chat |

空 thread 使用固定非空哨兵值参与唯一约束，不能依赖 SQL `NULL` 的唯一性行为。
Channel Chat 固定账号配置中的 `agent_id`；`model_id` 由 Agent 默认值和 Chat 配置
决定。已有 Conversation 不随账号默认 Agent 变更而静默迁移。

为保证无幂等键 Runtime POST 的可恢复性，每个 Channel Chat/Session 必须满足：

- 只有 Channel Worker 能提交初始 `user.message`；
- 不与浏览器 UI、其他 Channel 或后台任务共享写入口；
- 同一 Conversation 的 Inbox 严格 FIFO，一次只允许一个执行进入 `SUBMITTING`；
- v1 不向该 Session 发送 Steer/FollowUp；
- 若检测到非 Channel 写入或分支变化，停止自动重试并进入人工对账。

这是产品约束和恢复正确性的前提，不只是性能优化。

## 7. Runtime HTTP+SSE 映射与恢复

### 7.1 当前映射

| Channel 动作 | Runtime 操作 | 边界 |
|---|---|---|
| 创建专属 Session | POST /agents/{agentId}/sessions | 保存 Chat→Session 映射后再提交消息；创建结果不确定不推导消息已接受 |
| 读取状态 | GET /sessions/{sessionId} | idle/running 是资源状态，不能用任意旧 idle 判定本次完成 |
| 提交消息 | POST /sessions/{sessionId}/events | event 包装的 user.message 和有序 content，首业务帧为完整回执 |
| 恢复历史 | GET /sessions/{sessionId}/events | 普通整数分页、完整事件、eventId 去重；不公开 entrySeq |
| 运维停止 | POST Events 的 user.interrupt | 以原 user.message.eventId 为 targetEventId，回执不等于实际停止 |

精确请求与错误引用 [Runtime 契约](chat-api-review.html)。Provider tenant、用户、会话、消息、卡片 ID 和业务 metadata 只保存在 Channel Store，不进入 Runtime 请求。

### 7.2 正常主流程

![飞书消息与响应投递](飞书渠道/channel_feishu_message_sequence.svg)

[原尺寸 SVG](飞书渠道/channel_feishu_message_sequence.svg) · [PlantUML 源码：`channel_feishu_message_sequence`](飞书渠道/diagram.puml#L171)

Worker 保存首帧完整 user.message 的 eventId 作为本次接受身份。agent.message delta 只更新卡片预览，completed 覆盖为完整内容；sourceEventId 关联原消息，不能靠相同文本或“最新事件”猜归属。

对应 session.status_idle 才结束本段响应。done/failed/terminated 表示该执行的实际结果；confirming 只表示等待用户动作，资源仍为 running。本版不提供飞书工具确认入口，因此支持渠道执行的工具策略须在上线前约束，或先完成确认能力，不能把确认等待渲染成成功。

Projector 只展示允许公开的 Assistant 文本，工具阶段最多显示通用进度。原始 Thinking、工具参数/结果和内部错误不投递飞书；模型文本只进入固定卡片模板。

### 7.3 不确定结果恢复

当前 Runtime 无业务幂等键，也没有公开 Entry 水位。本版不能继续使用“提交前 entrySeq + 文本匹配”来证明请求未被接受。

1. Conversation 保持单 Writer/FIFO，提交前持久化 SUBMITTING 与本地请求关联，再调用 Runtime。
2. 收到完整回执后保存 accepted_event_id；流断开进入 RECONCILING，按普通分页读取历史并用 eventId/sourceEventId 对账，完整记录覆盖预览。
3. 没收到回执或本地保存前崩溃时，结果可能不确定。相同文本、历史暂未出现或 Session idle 都不能证明未接受；进入 MANUAL_RECONCILIATION，不自动 POST。
4. 只有得到明确“未接受”的操作错误时，才能按错误类别决定重试。确认已接受后只恢复观察和卡片投递，不重新执行。
5. 发现其他 Writer、分支变化、历史缺失或实例失联时停止自动判断。租约只协调 Channel Worker，不证明旧 Runtime 已停止，不授权重跑工具副作用。

![Channel 恢复状态](飞书渠道/channel_feishu_recovery_state.svg)

[原尺寸 SVG](飞书渠道/channel_feishu_recovery_state.svg) · [PlantUML 源码：`channel_feishu_recovery_state`](飞书渠道/diagram.puml#L260)

这是对当前 Runtime 契约的目标适配与安全加固：保留单 Writer 来减少歧义，但不再声称它使丢失回执自动可判定。代价是部分故障需要人工对账、长历史扫描成本较高；若要自动恢复这些情况，须先设计可靠的提交关联协议，不能以旧公开序号或文本摘要替代。

## 8. 飞书出站与流式卡片

### 8.1 CardKit 选择

首版优先使用 CardKit streaming card，而不是反复 PATCH 普通消息：

1. 先创建 CardKit card entity，获得 `card_id`；
2. 在本地持久化 `card_id` 后，以稳定 `uuid` 回复原消息并引用该 card；
3. 对同一 `card_id` 使用严格递增 `sequence` 更新 markdown element；
4. Projector 合并高频 delta，按账号、会话和 card 三级限频；
5. 终态写入完整文本并关闭 streaming mode；
6. 失败终态也必须关闭卡片或发送可见错误，不能让用户永久看到“生成中”。

Card entity 创建成功但发送前崩溃，只产生不可见孤儿 card，可由保留期清理。发送请求
使用稳定 `uuid`；更新任务在外部调用前持久化 `sequence + uuid + projection_version`，
超时后重试原值，不能分配新 sequence 猜测结果。

正式上线前必须在飞书 Sandbox 验证：

- 回复相同 `uuid` 的重复请求是否返回可用于对账的稳定结果；
- CardKit 相同 `sequence + uuid` 的重试语义；
- 话题回复、CardKit 引用和 `reply_in_thread` 的真实路由；
- 当前租户的限频、卡片大小、可更新期限和权限错误码。

这些外部行为未完成 live test 前，文档只承诺本地不更换幂等标识，不宣称飞书 API
与 Channel Store 存在分布式原子提交。

### 8.2 投影和限频

- desired view 以完整当前文本保存，不以 delta 作为数据库真相；
- 每次任务带单调 `projection_version`，迟到低版本任务直接完成不发送；
- 非终态更新合并为最新版本，避免每个 token 调一次飞书；
- 终态允许越过普通 debounce，但仍进入同一 per-card 串行队列；
- 模型输出只能进入固定 markdown 文本 element，不得被解释为 card JSON、按钮、URL
  或人员 ID；
- 卡片序列化使用低于飞书硬限制的内部安全上限，超限时显示有界预览并用确定性
  分段消息补齐；
- Provider 永久错误、撤回、机器人离群和权限不足进入 `DEAD_LETTER` 并产生告警。

## 9. 持久化设计

本节定义逻辑表，不提供 DDL。后续 SQL 的表和列 `COMMENT ON ... IS` 必须使用中文。
所有新表使用小写 snake_case 和 `t_` 前缀。

### 9.1 `t_channel_account`

| 字段 | 语义 |
|---|---|
| `channel_account_id` | 内部 Channel 账号 ID |
| `channel_type` | 固定枚举，飞书为 `FEISHU` |
| `provider_app_id` / `provider_tenant_key` | App 与允许租户 |
| `credential_ref` | Secret Manager 引用，不保存 App Secret |
| `transport_type` | `WS` 或 `WEBHOOK` |
| `default_agent_id` | 新 Conversation 的 Agent 绑定 |
| `status` / `config_version` | 启停和乐观并发版本 |

### 9.2 `t_channel_conversation`

| 字段 | 语义 |
|---|---|
| `channel_conversation_id` | Channel Conversation ID |
| `channel_account_id` | 所属账号 |
| `provider_tenant_key` / `provider_chat_id` / `provider_thread_key` | Provider 定位元组 |
| `chat_id` | `mate-service` Channel 专属 Chat ID |
| `session_id` | CampusClaw Session ID，只在内部存在 |
| `agent_id` | 创建时冻结的 Agent |
| `state` / `row_version` | `CREATING/ACTIVE/FAILED/DELETED` 与并发版本 |

唯一约束为账号、tenant、chat 和 thread 元组；`chat_id`、`session_id` 各自唯一。

### 9.3 `t_channel_inbound_message`

| 字段 | 语义 |
|---|---|
| `inbound_message_id` | 内部 Inbox ID |
| `channel_account_id` / `provider_message_id` | Provider 主去重唯一键 |
| `provider_event_id` | 投递审计 ID，不作为主业务幂等键 |
| `channel_conversation_id` | 解析后的 Conversation |
| `provider_actor_ref` | 最小化加密/脱敏的发送者引用 |
| `normalized_content_ciphertext` / `content_key_version` | Runtime 接受前短期加密保存的规范化内容 |
| `content_digest` / `logical_retry_digest` | 对账和短窗重复检测 |
| `state` / `error_code` | Inbox 状态和稳定错误码 |

Runtime 接受 User Entry 后，在保存 `accepted_event_id` 的同一事务中清空内容密文
和 key version；最终失败记录按保留策略清空，不无限期保存 Prompt。

### 9.4 `t_channel_execution`

| 字段 | 语义 |
|---|---|
| `channel_execution_id` | 一条 Inbox 的执行投影 ID，不是公共 Run |
| `inbound_message_id` / `session_id` | 因果关联 |
| `request_digest` | 本地审计/重复检测摘要，不能证明 Runtime 已接受 |
| `accepted_event_id` | 完整 user.message 回执的 eventId；未知时不自动重发 |
| `observed_event_ids` | 已应用完整事件的逻辑去重集合；具体存储与保留窗口待实施设计 |
| `state` | 图中执行恢复状态 |
| `lease_owner` / `lease_until` / `attempt_count` / `next_attempt_at` | 多实例接管与退避 |

`channel_execution_id` 只是 Channel 内部工作记录，不暴露为 API 资源，也不恢复旧
`run_id` 语义。

### 9.5 `t_channel_delivery`

| 字段 | 语义 |
|---|---|
| `delivery_id` / `inbound_message_id` | 出站投影身份与因果关联 |
| `provider_card_id` / `provider_reply_message_id` | CardKit 和消息定位；回复 ID 可在成功返回后补齐 |
| `card_sequence` | 下一个/已确认 CardKit sequence |
| `projection_version` / `visible_digest` | 本地 desired view 版本和去重 |
| `state` | `PENDING/STREAMING/FINALIZED/RETRY_WAIT/DEAD_LETTER` |
| `lease_owner` / `lease_until` / `attempt_count` / `next_attempt_at` | 多实例投递控制 |

### 9.6 `t_channel_outbox`

Outbox 任务至少包括：

- `PROCESS_INBOUND`；
- `RECONCILE_EXECUTION`；
- `CREATE_STREAMING_CARD`；
- `UPDATE_STREAMING_CARD`；
- `FINALIZE_STREAMING_CARD`；
- `SEND_TERMINAL_NOTICE`。

任务只保存内部 aggregate ID、目标版本和安全引用，不保存 token、App Secret、原始
Webhook Header、未脱敏事件或完整模型 thinking。

## 10. 并发、故障与可观测性

### 10.1 并发不变量

- 同一 `channel_conversation_id` 的 `PROCESS_INBOUND` FIFO 串行；不同 Conversation
  可并行；
- 一个 Conversation 同时最多一个 `SUBMITTING/STREAMING/RECONCILING`；
- worker lease 过期允许新 Pod 接管，但旧 Pod 每次写入都校验 lease/fencing token；
- Delivery 按 `delivery_id` 串行，低投影版本不覆盖高版本；
- 飞书 SDK/CLI 内存去重只做第一道减载，数据库唯一约束是最终事实。

### 10.2 故障分类

| 故障 | 处理 |
|---|---|
| Runtime POST 流建立前明确 `4xx` | 按错误码终态或退避；没有接受 User Entry时可安全处理 |
| Runtime POST 超时/断连 | 已保存 `accepted_event_id` 时进入 `RECONCILING`；没有可靠回执时进入 `MANUAL_RECONCILIATION`，禁止盲重放 |
| SSE 中途断开 | Runtime 继续执行；GET Events 恢复完整 Entry，丢弃临时 delta |
| `409 SESSION_BUSY` | 先对账同 Conversation 旧执行；不把新消息隐式转 Steer |
| `503` 容量/归属错误 | 保持同一 Inbox 与接受身份退避；是否重试取决于是否已接受 |
| Worker/Pod 重启 | 由 Inbox、execution state、Outbox 和 lease 恢复 |
| 飞书限频/网络错误 | 原 uuid/sequence 退避，不创建新逻辑 delivery |
| 飞书永久权限或目标错误 | Dead letter、可见终态和告警 |

### 10.3 指标与日志

至少提供：

- transport connected、reconnect count、last event time；
- inbox accepted/duplicate/rejected、按原因统计；
- per-conversation queue depth 与 oldest age；
- `SUBMITTING/RECONCILING/MANUAL_RECONCILIATION` 数量和持续时间；
- Runtime POST 首事件、首文本、终态延迟；
- CardKit 请求、限频、重试、dead letter；
- outbox backlog、lease steal、投影覆盖次数。

日志只记录内部 ID、稳定错误码和脱敏 Provider reference；禁止记录 App Secret、token、
完整 Header、原始事件、Prompt 明文、thinking 或工具私有结果。

## 11. 安全与隐私

1. App Secret、verification token、encrypt key 和 access token 由 Secret Manager 托管；
   数据库只保存 `credential_ref`。
2. Webhook 必须在 JSON 解析和业务处理前完成签名校验；长连接只使用官方 SDK，禁止
   自行简化握手、鉴权和解密。
3. Channel 先校验账号、tenant、sender、chat、mention 和消息类型；上游负责认证和动作授权，Runtime 校验资源与业务状态并按契约透传调用上下文，不重复认证凭据。
4. Provider ID 不进入 CampusClaw、Prompt、Tool Manager 或 Model Manager；需要用户
   可见身份时只注入受控显示文本，不注入可调用的 Provider 标识。
5. 飞书消息不能指定 Agent/Model/thinking、工具权限、系统提示、Session 或文件 URL。
6. 模型文本进入固定卡片模板并转义；不能产生卡片动作、回调 URL、人员 ID 或 OpenAPI
   参数。
7. 原始事件默认不持久化；规范化内容只在 Runtime 接受前加密短期保存。
8. 使用 MCP/CLI Tool 平面时采用与机器人最小入站权限分离的身份和 allowlist，避免
   Channel 用户通过 Prompt 间接获得高权限 Feishu Tools。

## 12. 实施依赖与切片

先实现 §4 的端口与 Inbox/Outbox 原子接受，再接入 Conversation Worker、Runtime 完整事件对账，最后连接 CardKit 投递与限频。SDK 类型留在 Adapter，持久化对象使用 DTO；不让入站服务同时负责模型执行与出站网络调用。

飞书 Java Server SDK 是拟新增的直接 Maven 依赖，用于长连接、验真和 OpenAPI；准确坐标、版本、主要传递依赖及公司仓库可用性尚未核验。定稿或实现前必须补齐依赖树、维护成本与已有 HTTP 客户端复用方案。JDK/现有 HTTP 客户端能调用 Raw API，但需要自建事件协议与安全处理；不添加 SDK 时须承担这部分成本。当前未引入新制品。

CLI/Python 只有确定需要独立 Connector 后才进入部署范围，私有 intake API 另行设计。CardKit 外部幂等与限制按 §8 的 Sandbox 验收，未验证前不承诺自动可靠投递。

## 13. 测试与验收

### 13.1 Adapter 与契约测试

- 官方 SDK 事件到 `ChannelInboundMessageDTO` 的 text/post/mention/thread 映射；
- Webhook 签名失败、挑战、加密、Body 超限和非法 JSON；
- CLI NDJSON、ready marker、结构化 stderr、stdin EOF、SIGTERM、子进程重启；
- Runtime POST/GET Events 的当前请求、SSE、分页和错误消费者合约；
- 未知飞书错误码走安全默认分支，不匹配 `msg` 文案。

### 13.2 幂等、排序与崩溃测试

- 同一 Provider `message_id` 并发投递 100 次，只有一个 Inbox 和一个
  `PROCESS_INBOUND`；
- 同 Conversation 100 条消息保持 FIFO，不同 Conversation 可并发；
- Session 创建成功、mapping 保存前崩溃只产生可清理孤儿 Session，不提交消息；
- SUBMITTING 提交后、回执前或回执保存前崩溃，结果未知时进入人工对账，不产生第二次 POST；
- 已保存 accepted_event_id 后任意中断，以完整事件与原消息关联恢复，不重跑执行；
- SSE 在任意 delta、tool 或 completed 处断开，最终卡片由 GET Events 收敛；
- 人为注入第二 Writer 时进入 `MANUAL_RECONCILIATION`，不自动重放；
- CardKit create/send/update/finish 每个外部调用点前后崩溃，保持原 uuid/sequence；
- lease 过期接管不允许旧 Worker 覆盖新 projection。

### 13.3 安全与容量测试

- 非允许 tenant、bot sender、非 @ 群消息、超长/深层 JSON、恶意 mention；
- Prompt/card injection、链接转义、日志和指标敏感数据扫描；
- SDK/CLI 断线重连、事件重复、乱序、数据库不可用和 outbox backlog；
- 飞书 Sandbox 实测回复 uuid、CardKit sequence、话题路由、限频和权限；
- 多 Pod 连接数量、租约竞争、滚动升级和 Secret 轮换。

## 14. 源码证据与差异分类

### 14.1 固定源码范围

实现与外部方案的完整提交、仓库相对路径和符号统一见 [源码证据](飞书渠道/source-evidence.md)。该组 Java 代码已观察到“先持久化再执行、断线仅 detach”；其旧 Entry 字段不作为当前 HTTP 契约。未进行新的飞书 live test 或 mate-service 实现审计。

### 14.2 目标设计与原因

| 分类 | 决策 | 原因 |
|---|---|---|
| 产品约束 | Channel Conversation 使用专属 Chat/Session 和单 Writer | 隔离上下文并减少并发写入歧义，不承诺无回执时自动恢复 |
| 产品约束 | v1 只处理 text/post，群聊必须 @，不把普通消息映射为 Steer | 控制首版能力和上下文泄露风险 |
| 架构改造 | 在 `mate-service` 新增 Provider Adapter、Inbox/Outbox、Worker、Projector 与 Gateway | 当前源码没有 Channel 实现，且 Provider 回调不能同步等待 Agent |
| 架构改造 | Channel 通过 `ChannelChatPort` 进入 Chat core | 保持 `chat_id -> session_id` 所有权，不绕过公共业务层 |
| 安全加固 | 以完整接受 eventId 和 sourceEventId 对账，无回执保持不确定 | 当前契约不公开 Entry 水位，不能根据空历史或相同文本自动重发 |
| 飞书适配 | Java SDK 长连接默认，Webhook 可选；CLI 仅 PoC | 在 Java 生产服务中保留统一生命周期、事务、Secret 和可观测性 |
| 安全加固 | Provider ID/凭据不进入 Runtime；模型输出固定卡片渲染 | 防止跨边界身份泄露、Prompt 注入和权限扩大 |
| 安全加固 | MCP Tool 身份与 Channel Bot 身份分离 | 入站聊天权限不应自动获得高权限飞书 OpenAPI 操作能力 |

## 15. 待确认与后续专题

1. 飞书 Java SDK 的准确 Maven 坐标、锁定版本和公司制品仓可用性；
2. `mate-service` Chat 应用核心的实际端口、事务库和 Channel 专属 Chat 类型；
3. 完整事件长历史扫描的容量上限，以及无回执不确定结果的可靠提交关联方案；
4. 飞书 Sandbox 对回复 uuid 与 CardKit sequence 重试的实测结果；
5. 附件导入 Attachment Service 的下载、扫描、file_id 和失败提示专题；
6. 卡片停止 action 到 user.interrupt 的授权与对账专题；FollowUp 暂不启用，不恢复三个独立控制接口；
7. 独立 CLI/Python Connector 若确有部署需求，其私有 intake HTTP API 逐接口评审。

## 16. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 3.0.0 | 2026-09-14 | 对齐当前 Session Events，移除公开 Entry 水位依赖，无可靠回执时保持人工对账。 |
| 2.1.0 | 2026-09-07 | 运维通过 user.interrupt 停止执行。 |
| 2.0.0 | 2026-08-20 | 飞书生产接入选择 Java SDK 长连接/Webhook Adapter。 |
| 1.3.0 | 2026-08-18 | 冻结旧 Run 方案并删除过渡 OpenAPI 引用。 |
| 1.2.0 | 2026-08-18 | 飞书渠道采用两跳 HTTP+SSE。 |
| 1.1.0 | 2026-08-17 | 标记 Session Events 对 Channel 映射的迁移影响。 |
| 1.0.0 | 2026-08-11 | 建立飞书 Channel 的初始设计。 |
