# 飞书渠道源码与方案参考

版本 1.0.0 · 整理日期 2026-09-14

[返回渠道主设计](../channel-feishu-v1-design.md)

以下保留原分析时的固定提交与2026-08-20公开资料范围，本次未升级外部基线。旧Runtime源码证明接受和断线行为，不证明当前Session Events的精确报文。

| 基线 | 值 |
|---|---|
| pi-mono-java 实现基线 | `1f801dbb82bdda30478e3354e685e3153b179a0c` |
| mate-service 源码核对基线 | `6d5e6f3714e1cf8744d187a4796ca06300ad7e33`；未发现 Channel/飞书实现 |
| 飞书官方 CLI 基线 | `larksuite/cli@755daa4de3ea12785c43a15244ffb8f012122c13` |
| 飞书官方 Channel SDK 基线 | `larksuite/channel-sdk-python@731d459cca55ac76e85911bba2b1666508145e03` |
| OpenClaw 参考基线 | `openclaw/openclaw@b015925bc30f6a8363f290b07d5f8588e21422b8` |
| 外部资料核对日期 | 2026-08-20 |


## 1. 方案与源码

### 2.1 方案对比

| 方案 | 入站 | 出站 | 进程模型 | 生产适配性 | 本设计定位 |
|---|---|---|---|---|---|
| 官方 Java Server SDK | 长连接或 Webhook | SDK/OpenAPI | `mate-service` 进程内 | 与 Java 生命周期、监控、Secret、数据库事务边界最贴合 | **生产首选** |
| 官方 `lark-cli` | `event consume` 实时事件 | `im` 命令或 Raw API | 每个 EventKey 一个子进程，共享本机事件总线 | 需要自行补进程监管、数据库 Inbox/Outbox、集群租约和稳定凭据托管 | PoC、开发和单机 Agent |
| 官方 Python Channel SDK | 长连接或 Webhook | 消息、媒体、卡片和 CardKit streaming | Python 进程或独立服务 | Channel 能力完整；Java 系统采用时会新增跨语言部署和私有接入 API | 行为基线或独立 Connector |
| 官方 OpenAPI MCP | 不负责可靠事件入站 | MCP Tool 调用 OpenAPI | MCP Server/CLI | 适合模型主动调用，不提供 Channel durable admission | Tool 平面 |
| Raw Webhook + Raw OpenAPI | Webhook | HTTP OpenAPI | 自行实现 | 鉴权、解密、重试、Schema、限频和兼容成本最高 | SDK 无法满足时的最后选择 |

### 2.2 官方 `lark-cli` 的实际能力

官方 [`larksuite/cli`](https://github.com/larksuite/cli) 在固定提交中不是单纯的“发消息命令”。
其事件命令具备以下宿主协议：

| 契约点 | 已观察行为 | Channel 影响 |
|---|---|---|
| 消费命令 | `event consume <EventKey>`；一次只能监听一个 EventKey | 首版消息和卡片回调至少需要两个受监管子进程 |
| 正常输出 | stdout 每行一个 JSON，即 NDJSON | Adapter 可以逐行反序列化为入站 DTO |
| 就绪信号 | stderr 固定输出 `[event] ready event_key=<key>` | 父进程必须等待信号，不能用固定 sleep 猜测启动完成 |
| 生命周期 | 无界非 TTY 消费者把 stdin EOF 视为优雅停止；支持 SIGTERM | systemd/Kubernetes/Java ProcessBuilder 必须保持 stdin 或使用有界重启策略 |
| 退出语义 | 0 表示 limit/timeout/signal；非 0 使用结构化错误 envelope | 监管器按退出码和 `error.type/subtype` 分类，不匹配错误文案 |
| 多事件 | N 个 EventKey 对应 N 个子进程；共享一个本机 UDS bus daemon | 本机故障域清晰，但不是跨 Pod 消费组 |
| 消息输出 | `im.message.receive_v1` 被扁平化；`content` 对多数类型已是可读文本 | 不能再按 Raw OpenAPI 的嵌套 JSON 盲目 `fromjson` |
| 推荐去重键 | 输出 Schema 明确推荐 `message_id`，`event_id` 只是投递 ID | 数据库唯一键以账号和 `message_id` 为主 |
| CLI 内部去重 | `event_id` 内存 TTL 默认 5 分钟、环容量 10000 | 不能替代多实例数据库唯一约束和永久业务幂等 |

源码证据：

- [`skills/lark-event/SKILL.md`](https://github.com/larksuite/cli/blob/755daa4de3ea12785c43a15244ffb8f012122c13/skills/lark-event/SKILL.md#L15-L110)
  定义命令、ready marker、stdin/SIGTERM、退出码与“一 EventKey 一进程”；
- [`cmd/event/consume.go`](https://github.com/larksuite/cli/blob/755daa4de3ea12785c43a15244ffb8f012122c13/cmd/event/consume.go#L46-L84)
  声明 NDJSON 消费命令和参数；
- [`events/im/message_receive.go`](https://github.com/larksuite/cli/blob/755daa4de3ea12785c43a15244ffb8f012122c13/events/im/message_receive.go#L15-L108)
  定义消息扁平字段、`message_id` 去重建议和内容预渲染；
- [`internal/event/dedup.go`](https://github.com/larksuite/cli/blob/755daa4de3ea12785c43a15244ffb8f012122c13/internal/event/dedup.go#L11-L70)
  显示 CLI 自带去重是单进程内存结构。

若采用 CLI Adapter，最小启动形态是：

```bash
lark-cli event consume im.message.receive_v1 --as bot
```

需要卡片按钮时再启动：

```bash
lark-cli event consume card.action.trigger --as bot
```

这些命令只替换 `FeishuTransport` 和部分 `FeishuMessageGateway`，不会替换
`ChannelInboundService`、数据库、Outbox、会话串行化、Runtime 恢复或卡片投影。

### 2.3 官方 OpenAPI MCP 的边界

官方 [OpenAPI MCP 概览](https://open.feishu.cn/document/mcp_open_tools/mcp-overview)
和 [`larksuite/lark-openapi-mcp`](https://github.com/larksuite/lark-openapi-mcp)
表明 MCP Server 的目标是把飞书 OpenAPI 变为可被 Agent 调用的 Tools。官方
[MCP 智能助手机器人示例](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/mcp_integration/develop-mcp-intelligent-assistant-bot)
同时使用长连接接收消息和 MCP 调用能力，恰好说明两者是两条责任链：

```text
Channel data plane: Feishu event -> durable inbox -> Chat -> Runtime -> reply
Tool plane:         Agent tool call -> lark-mcp -> Feishu OpenAPI
```

因此不能用“已经接入 lark-mcp”推导“机器人消息 Channel 已经具备可靠入站”。

### 2.4 官方 Python Channel SDK 的可复用结论

官方 [`channel-sdk-python`](https://github.com/larksuite/channel-sdk-python) 的
`FeishuChannel` 已观察到：

- transport 支持 `ws` 与 `webhook`，默认 WS；
- 入站先做事件/消息双键去重、消息规范化与 mention 解析，再进入安全策略；
- 安全层包含 stale、重复、自发消息、mention/allowlist、处理锁、按 Chat 排队；
- 出站支持消息、媒体、卡片和 CardKit streaming；
- Markdown streaming 预创建卡片，以严格递增 `sequence` 更新，并在终态关闭
  streaming mode；
- 默认去重存储是内存；自定义共享缓存协议没有原子 SETNX 语义，多 Worker 场景仍需
  数据库唯一约束和幂等业务处理。

源码证据包括
[`channel.py`](https://github.com/larksuite/channel-sdk-python/blob/731d459cca55ac76e85911bba2b1666508145e03/lark_channel/channel/channel.py#L289-L400)、
[`normalize/dedup.py`](https://github.com/larksuite/channel-sdk-python/blob/731d459cca55ac76e85911bba2b1666508145e03/lark_channel/channel/normalize/dedup.py#L1-L125)、
[`safety/pipeline.py`](https://github.com/larksuite/channel-sdk-python/blob/731d459cca55ac76e85911bba2b1666508145e03/lark_channel/channel/safety/pipeline.py#L43-L317)
和
[`markdown_stream.py`](https://github.com/larksuite/channel-sdk-python/blob/731d459cca55ac76e85911bba2b1666508145e03/lark_channel/channel/outbound/streaming/markdown_stream.py#L34-L213)。

### 2.5 OpenClaw 源码参考

OpenClaw 的飞书插件不是本项目依赖，但提供了可核查的源码参考：

- `extensions/feishu/src/monitor.transport.ts` 同时支持 WS 与 Webhook，Webhook 在解析
  JSON 前校验签名并限制请求体、Content-Type 和速率；
- `extensions/feishu/src/feishu-ingress.ts` 将识别出的消息事件先交给持久化 ingress
  queue，再由 drain 处理，并以 Chat 作为顺序 lane；
- `extensions/feishu/src/dedupe-key.ts` 不只依赖 `message_id`，还处理重连时同一逻辑
  文本获得新 ID 的实际问题；
- `extensions/feishu/src/sequential-queue.ts` 同 Chat FIFO、跨 Chat 并行；
- `extensions/feishu/src/streaming-card.ts` 使用 CardKit card ID、递增 sequence、稳定
  uuid、限频合并与明确 finish。

这些行为说明生产 Channel 不是“接上 SDK 回调后直接调用模型”，而是 transport、
durable admission、逻辑去重、策略、顺序、执行和 delivery 七个边界的组合。


## 2. 实现核验

### 14.1 观察到的源码行为

| 来源 | 路径/符号 | 观察结果 |
|---|---|---|
| pi-mono-java `1f801dbb` | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java`，`submit()` 58-73 | POST 直接返回 `SseEmitter`；completion/timeout/error 只 detach |
| pi-mono-java `1f801dbb` | `.../runtimeapi/event/RuntimeEventService.java`，`prepareAndSubmit()` / `acceptUserEntry()` 66-102 | 锁定 Session、确认 idle、持久化 User Entry、启动执行并返回请求级 EventStream |
| pi-mono-java `1f801dbb` | `.../runtimeapi/event/RuntimeEventStream.java`，`emit()` / `attach()` / `detachInternal()` 48-79、107-138 | 单订阅者、有界缓冲；断线清空本地流但不调用 Agent abort |
| pi-mono-java `1f801dbb` | `.../runtimeapi/event/RuntimeExecutionCoordinator.java`，`start()` / `completeExecution()` 68-82、150-164 | Agent 异步执行，终态持久化 Session、释放 active execution 并发终态事件 |
| mate-service `6d5e6f37` | 全仓检索 Channel、Feishu/Lark、`im.message.receive_v1` | 未发现现有飞书 Channel 实现；本文 Java 组件均是目标设计 |
| lark-cli `755daa4d` | `skills/lark-event/SKILL.md`、`cmd/event/consume.go`、`events/im/message_receive.go` | CLI 可消费实时事件，使用 NDJSON/子进程协议，并对 IM 消息做扁平化 |
| Channel SDK `731d459c` | `lark_channel/channel/**` | 完整 WS/Webhook、规范化、安全、出站和 streaming 参考；默认内存去重不足以承担集群业务幂等 |
| OpenClaw `b015925b` | `extensions/feishu/src/monitor.transport.ts`、`feishu-ingress.ts`、`dedupe-key.ts`、`streaming-card.ts` | 成熟实现把 transport、durable ingress、逻辑去重、串行队列和 CardKit 明确分层 |
