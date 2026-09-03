# Mate Chat API 协同评审

| 属性 | 值 |
|---|---|
| 协作机制版本 | 0.1.1 |
| 状态 | 启用 |
| 建立日期 | 2026-09-03 |
| 最近更新 | 2026-09-03 |
| 设计仓核对基线 | `678ccdb30a0e95506874ca099b0a9eeed62375bd` |
| Events 契约内容基线 | `cc3b5576882b04dd6efb175fd87eb8525dc85c8c`（1.4.4） |
| CampusClaw 源码核对基线 | `pi-mono-java@c9d858bc8261bf07f5585f545b53495bf2226a56` |

本文是多个 Codex 任务协同设计 Mate Chat API 的事实源和导航，不是 HTTP API 契约。
现有 Events API 仍以 [主题 README](../README.md)、operation JSON 和 OpenAPI 为准。

## 1. 协作边界

- 当前总控任务负责跨接口决策、冲突仲裁、聚合文档、OpenAPI、评审页、图、校验、提交和推送。
- 每个接口任务只与用户评审一个明确主题，只修改自己的决策文件和分配给它的 operation 文件。
- 不同接口可并行；存在前置依赖或共享字段冲突时停止局部定稿，交回总控任务处理。
- 各任务的对话记录不会自动合并。相互感知依靠本目录的版本化决策文件，以及总控任务读取各任务状态后进行整合。
- 所有任务共用当前 Local 项目目录。禁止两个任务同时修改聚合文件，也禁止接口任务自行提交或推送。

## 2. 事实源与同步顺序

每个接口任务在开始新一轮评审、提出跨接口决定或修改文件之前，依次读取：

1. 仓库和项目级 `AGENTS.md`；
2. 本文件；
3. [主题 README](../README.md)；
4. `决策/` 下全部决策文件；
5. 自己负责的 operation 文件和受影响的现有契约。

信息冲突时，优先级为：用户在较新评审中的明确决定 > 本目录已确认决策 > 已确认 operation
契约 > 尚未确认的建议。发现冲突的任务不得静默选择，必须记录冲突并通知总控任务。

决策状态固定为：

```text
proposed -> confirmed -> integrated -> validated
```

- `proposed`：正在讨论，其他接口不得依赖；
- `confirmed`：用户已明确同意，可以作为其他接口的设计输入；
- `integrated`：总控任务已同步到聚合契约；
- `validated`：生成物和自动校验均已通过。

## 3. 当前任务划分

| Codex 任务 | 负责范围 | 独占决策文件 | 独占 operation 文件 |
|---|---|---|---|
| `Mate Chat API · 总控` | 跨接口规则、冲突、聚合与验收 | 本文件 | README、OpenAPI、HTML、生成器、校验器、PlantUML/SVG |
| `Mate Chat · 创建 Chat` | 创建 Chat、初始资源形状和初始配置 | [01-create-chat.md](决策/01-create-chat.md) | 待接口确认后分配 |
| `Mate Chat · 配置 Chat` | 模型和深度思考等 Chat 级配置 | [02-configure-chat.md](决策/02-configure-chat.md) | 待接口确认后分配 |
| `Mate Chat · 提交事件` | `POST /chats/{chatId}/events` | [03-submit-chat-event.md](决策/03-submit-chat-event.md) | [01-submit-chat-event.json](../接口契约/操作/01-submit-chat-event.json) |
| `Mate Chat · 实时事件` | `GET /chats/{chatId}/events/stream` | [04-stream-chat-events.md](决策/04-stream-chat-events.md) | [02-stream-chat-events.json](../接口契约/操作/02-stream-chat-events.json) |
| `Mate Chat · 历史事件` | `GET /chats/{chatId}/events` | [05-list-chat-events.md](决策/05-list-chat-events.md) | [03-list-chat-events.json](../接口契约/操作/03-list-chat-events.json) |

总控文件只能由总控任务修改。接口任务不能直接修改 `README.md`、
`chat-events-v1.openapi.yaml`、`chat-events-v1-review.html`、生成器、校验器或设计图。

## 4. 已确认的跨接口决定

| 主题 | 当前决定 | 适用范围 |
|---|---|---|
| 公共资源命名 | Mate 对外使用 `Chat/chatId/chat.*`；Claw 内部使用 `Session/sessionId/session.*` | 全部 Mate Chat API |
| ID 隔离 | Mate 私有、稳定地解析 `chatId -> sessionId`，不向调用方暴露 `sessionId` | 全部 Mate Chat API |
| 执行并发 | 同一个 Chat 最多一个 active execution | 提交、状态、配置生效边界 |
| 提交与观察 | 提交事件、实时观察、权威历史是三个独立 operation | Events API |
| 提交事件类型 | `user.message`、`user.interrupt`、`user.tool_confirmation` | SubmitEvents |
| 实时事件类型 | `agent.message`、`agent.thinking`、`agent.tool_call`、`agent.tool_result`、`chat.status_idle` | StreamEvents |
| 历史事件类型 | 三种 `user.*`、四种 `agent.*`、`chat.status_idle` | ListEvents |
| idle 原因 | `done`、`terminated`、`failed`、`confirming` | StreamEvents、ListEvents |
| 中断流程 | `interrupt` 被接受后等待 `chat.status_idle(reason=terminated)`，再提交新 `message` | SubmitEvents、StreamEvents |
| Tool 关联 | `toolCallId` 直接使用 OpenAI Responses `call_id` 或 Chat Completions `tool_calls[].id`，区分大小写且不透明 | Tool Call、确认、结果 |
| POST 成功体 | 返回服务端实际持久化的完整 `user.*` 事件 | SubmitEvents、ListEvents |
| 实时与恢复 | delta 仅作实时 preview；completed 和其他完整事件进入权威历史；断线后重开流并查询历史对账 | StreamEvents、ListEvents |
| 公共顺序字段 | 不公开 `eventSeq` | Events API |
| 国际化请求头 | Mate operation 不声明 `Accept-Language`；Claw operation 需要时单独声明 | Mate/Claw HTTP 边界 |

下面两项是已形成的设计方向，但尚未写入 Events 1.4.4 聚合契约：

- `modelId` 和深度思考设置属于 Chat/Session 配置，不属于 `user.message` 事件字段；
- 每条 `user.message` 被接受时应固定本次执行使用的配置快照，运行中修改配置不追溯影响该次执行。

## 5. 当前待决策与冲突

| 编号 | 状态 | 问题 | 约束与下一步 |
|---|---|---|---|
| C-001 | `proposed` | ListEvents 的 `page/nextPage` 改为 `1、2、3` 等一基数字页码 | 用户已明确不使用加密或 opaque cursor；仍需决定如何保留当前固定快照。候选是数字 `page/nextPage` 加公开 `snapshotEventId`，并在后续页重复过滤条件；不得直接删除固定快照承诺。 |
| C-002 | `proposed` | 公司 Swagger 不支持展示 `text/event-stream` | 文档工具限制不能静默改变线上媒体类型。需决定使用普通文本示例、附件说明或单独实时协议文档；HTTP 契约仍需明确真实媒体类型。 |
| C-003 | `proposed` | 创建 Chat 与配置 Chat 的 operation 边界 | 需逐项确认创建时可设置的字段、后续可变字段、默认值、状态冲突和响应资源形状。 |
| C-004 | `proposed` | Mate 单一组合配置更新与 Claw 当前两个独立更新接口的原子性冲突 | 若 Mate 用一个请求同时修改 `modelId` 和 `thinking`，顺序调用 Claw 的两个 `PUT` 会产生部分成功和 ETag 竞争。需在“Mate 也拆成两个 operation”与“Claw 新增原子组合更新”之间做架构决策。 |
| C-005 | `proposed` | `modelId` 的公共格式约束在 Model Manager 设计与 Claw Runtime 实现之间不一致 | Model Manager 目标设计定义大小写敏感、1–64 字符的不透明值；当前 Runtime 请求使用 1–128 且限制字符集的正则。Mate Chat 配置不得在校准前复制任一约束。 |

C-004 的源码证据来自 `pi-mono-java@c9d858bc8261bf07f5585f545b53495bf2226a56`：

- `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeSessionConfigurationController.java`：`changeModel` 和 `changeThinking` 分别暴露 `PUT /sessions/{sessionId}/model` 与 `PUT /sessions/{sessionId}/thinking`，均使用 `If-Match`；
- `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionConfigurationService.java`：`changeModel`、`changeThinking` 是两个独立服务调用；`modelChangeEntries` 在目标模型不支持 reasoning 时把 `thinking` 归一为 `false`；
- `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java`：`updateModel` 与 `updateThinking` 分别是独立 `@Transactional` 事务边界。

以上是当前源码观察。是否改变 Claw 接口或 Mate 公共 operation 属于待确认的架构变化。

C-005 的两侧证据为：

- 本设计仓 `02-服务与接口/03-模型管理Provider契约/README.md` 2.4.0 第 2 节将 `modelId` 定义为 1–64 字符、大小写敏感的不透明字符串；这是目标契约；
- `pi-mono-java@c9d858bc8261bf07f5585f545b53495bf2226a56` 的 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/RuntimeApiConstants.java`：`MODEL_ID_PATTERN` 为 `^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$`；
- 同基线的 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/vo/ChangeModelRequestVO.java`：`modelId` 通过 `@Pattern` 实际使用该正则。

这是一项目标契约与当前实现的校准问题，不能把任一侧静默描述为全系统统一规则。

## 6. 接口任务交接格式

接口任务在完成一轮评审后，用以下格式更新自己的决策文件并向用户汇报：

```text
operation: 方法与路径，或待确认的候选
status: proposed | confirmed
confirmed decisions: 本轮用户明确同意的字段与行为
cross-operation impact: 影响的公共字段、错误、状态或其他 operation
changed owned files: 只列本任务拥有的文件
unresolved: 仍需用户或总控决定的问题
```

总控任务只整合 `confirmed` 决策；完成聚合、生成与验证后，将对应状态提升为
`integrated` 或 `validated`。

## 7. 持续优化规则

每次出现返工、冲突或信息遗漏时，总控任务判断它是否可复用：

- 只影响一个接口的内容，写入该接口决策文件；
- 影响多个接口的规则，精炼后写入本文件；
- 能机械检查的约束，优先加入校验器，而不是增加长篇提示；
- 已失效的规则直接修改或删除，不累计相互矛盾的历史说明；
- 每次只解决一个可观察问题，并记录改变是否减少了后续返工。

## 8. 工程实践依据

本协作机制基于以下官方公开实践在本项目中的适配，核对日期为 2026-09-03：

| 官方实践 | 可观察结论 | 本项目采用方式 |
|---|---|---|
| [OpenAI：Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/) | 同一 Project 内用独立任务并行工作，并由人监督和切换上下文 | 总控任务和接口任务放在同一 Local Project，并按接口拆分 |
| [OpenAI：Harness engineering](https://openai.com/index/harness-engineering/) | 大目标拆成小构件；仓库知识是事实源；给 Agent 一张地图，而不是巨型说明书；用反馈和验证闭环提高可靠性 | 本文件只做导航和公共决定，细节留在 operation 与独立决策文件，最后统一校验 |
| [OpenAI：Building self-improving tax agents](https://openai.com/index/building-self-improving-tax-agents-with-codex/) | 使用真实产物和执行反馈持续改进能力，同时由人负责架构和发布判断 | 用真实 OpenAPI/评审页/校验结果作为反馈，用户确认产品语义，总控负责集成 |
| [Anthropic：Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | 上下文是有限资源，应持续筛选最相关的信息 | 每个任务按固定顺序读取最小必要事实源，不复制整段聊天 |
| [Anthropic：Multi-agent research system](https://www.anthropic.com/engineering/how-we-built-our-multi-agent-research-system) | 由 lead 规划和委派专门任务，子任务返回压缩后的结果，再由 lead 综合 | 总控—接口任务结构和固定交接包 |
| [Anthropic：Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) | 并行适用于相互独立的子任务；有累计上下文或共享状态依赖时应串行 | 接口可并行，跨接口冲突回到总控串行处理 |

这些资料提供的是工程方法依据，不证明 Mate 或 Claw 的任何现有实现行为。
