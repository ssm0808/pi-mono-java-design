# Mate 模型信息与执行快照

版本：1.1.0 · 2026-09-19 · 状态：已确认目标，待实现。

[返回 Model 主设计](README.md) · [全局目标类图](model-classes.svg) · [源码证据](source-evidence.md#model-capability-evidence)

## 1. 权威与边界

Mate 维护逐模型信息、路由和输出额度策略。CampusClaw 每个新执行开始前查询一次当前选中模型的信息，使用 `contextWindow` 管理上下文与压缩；普通对话、工具循环、Child/Cron 和压缩摘要均不设置、裁剪或转发输出 token 上限。Mate 根据模型、当前输入和上游协议自行确定输出额度；需要显式输出参数的上游由 Mate 补齐并适配。

Agent 已发布设置中的 `bindingModels/defaultModel` 继续决定允许使用和默认选择的模型。模型信息查询不能增加可选模型；信息也不写入 Agent 目录，不通过 refresh 才生效。`contextWindow` 是 Mate 当前路由实际可用的总上下文窗口，单位 token，不是请求输出预算。Mate 必须返回真实有效窗口；同一 modelId 对应多个候选路由时，返回所有可能被选择路由均支持的保守窗口，或在 Mate 内保证查询与调用使用一致的能力约束。

这是产品约束与架构变更：Mate 统一控制生成参数，Claw 在每次新执行取得较新的窗口并在执行内固定使用。代价是每个新执行多一次短 HTTP 查询，并增加对模型元数据可用性的依赖；Claw 放弃独立摘要输出预算和基于目标输出上限的截断推断。首版只要求 `modelId/contextWindow`，不查询或消费 `maxTokens`；reasoning、模态、计费按既有设计处理，后续增加字段时另行定义语义。

## 2. 独立模型信息查询契约

本节维护新增 operation 的精确契约；Chat 由 `chat-api.json/html` 维护。

| 项目 | 规则 |
|---|---|
| Method / path | `GET /mate-service/v1/models/{modelId}` |
| 用途 | 返回一个模型的当前信息；不枚举模型，不调用上游生成接口 |
| modelId | 沿用 Mate Chat 的不透明、大小写敏感、1–64 字符身份；客户端用 URI path-segment 编码一次，服务端不 trim、转小写或重写 ID；网关需验证编码 ID 的透传 |
| 调用边界 | 经内部网关与现有服务准入、网络 ACL；不携带用户 execution 四项凭据，不返回上游 endpoint、apiKey 或私有路由 |
| 成功 | HTTP 200、`application/json`、`Cache-Control: no-store`；ResultBean 为 `resCode/resMsg/result` |
| 失败 | 真实 HTTP 状态，仅 `resCode/resMsg`；按 Accept-Language 支持 zh-CN/en-US、缺失或不支持时回退 en-US，并设置 Content-Language |
| result.modelId | 必填，精确等于请求 ID |
| result.contextWindow | 必填 JSON 整数，范围 1–2147483647，单位 token；缺失或非法不能用部署常量补齐 |

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "modelId": "model-550e8400e29b41d4a716446655440000",
    "contextWindow": 128000
  }
}
```

示例数字不是默认值。Mate 应从当前有效模型描述读取信息；Claw、客户端与网关不得用跨请求缓存或条件请求替代本次读取。Mate 自身的配置发布有生效边界，本接口不承诺读取尚未发布的管理修改。

| HTTP 状态 | resCode | 条件 |
|---|---|---|
| 400 | `INVALID_MODEL_ID` | 请求 ID 不满足标量边界约束 |
| 404 | `MODEL_NOT_FOUND` | Mate 不存在该 ID |
| 503 | `MODEL_UNAVAILABLE` | 模型被禁用或不能提供服务；与 Chat 的同名错误保持一致 |
| 503 | `MANAGER_UNAVAILABLE` | 元数据来源不可用、缺少 contextWindow 或配置值非法 |

查询不授予模型使用权，也不预占路由。Chat 仍检查当时的模型可用性；读取后模型或路由仍可能变化，Claw 保留明确 overflow 处置，不声称仅凭一次查询就保证整个长执行始终使用最新能力。

## 3. 查询与执行生命周期

| 入口 | 查询边界 |
|---|---|
| 新 user.message、实际启动执行的 Skill/命令 | 新根执行准备阶段，仅查询选中的 modelId 一次 |
| 自动压缩、同一执行的 Tool Loop、溢出恢复重试 | 复用该执行的不可变模型信息，不再次查询 |
| 权限确认、计划审核、结构化回答 | 续跑原根执行，复用原快照，不因新增 HTTP 请求刷新窗口 |
| 独立手工压缩 | 开始该次压缩前查询一次；摘要复用结果 |
| Child / Cron | 每个独立执行查询其实际选中模型一次，不能沿用父执行或上一次调度的信息 |
| 模型列表/选择、历史读取、停止与只读命令 | 不触发模型信息查询；切换后的下一次执行查询新模型 |

执行准备分为三个阶段（待实现）：

1. **观察与选择。** 读取 Session 版本、状态、选中模型和 Agent 绑定快照，依照既有模型校准规则确定候选 modelId；此阶段不接受 user.message、不启动模型或工具，也不提交观察阶段的模型变更。
2. **远程读取。** 在 Session 操作锁和数据库事务之外，由新增单例 `ExecutionModelResolver` 调用 `MateServiceClient` 查询一次候选模型。校验 ID、contextWindow 类型和范围，构造深度不可变的 `ModelCapabilityDTO`。沿用 runtime 短请求超时与响应大小限制；首版失败即返回，不自动重试或回退上次请求、Agent 文件及 128000 等常量。
3. **复核与固定。** 回到原有 Session 锁/事务准入边界，重新检查状态、resourceVersion、候选 modelId、Agent 绑定及准备快照身份。观察已过期时沿既有冲突语义失败，不将旧查询结果嫁接到新模型，也不在锁内二次查询。校准、受理和执行装配使用同一候选；将 DTO 组合进本次执行的 Model/上下文，交给 Agent Loop 与 SessionCompactor。信息查询失败不产生已接受 user.message 或活动执行。

`RuntimeModelManager` 的本地列表/绑定选择与远程能力装配分开：列表和设置修改不构造带虚假窗口的可执行 Model；执行描述只能在查询成功后构造。`AgentRuntimeManager/PreparedAgentRuntime/AgentDirectorySnapshotDTO` 继续管理已发布 Agent 绑定，不增加 `modelCapabilities`，也不因动态能力引入目录 schema 升级。

快照生命周期是一个根执行及其原根续跑，不是整个 Session，也不是每个 SSE/Chat 请求。不同执行即使 modelId 相同也重新查询；并行执行不能共享可变 DTO。快照仅保存在活动执行中，本专题不增加数据库表或崩溃接管；实例丢失继续遵守[既有执行与凭据恢复边界](../../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md#45-确认续跑的跨实例交接待实现-实施骨架)，不查询新能力后自动重放旧执行。

## 4. 输出控制与上下文消费

**Claw 不发送输出额度。** 删除 `campusmate.model.context-window/max-output-tokens` 及对应环境变量、Java 默认值；删除 CampusMate 链路从 `Model.maxTokens`、显式 options、fast/thorough 工厂和摘要 reserve 比例生成输出额度的逻辑。`MateChatRequestMapper` 不序列化 `max_output_tokens/max_tokens/max_completion_tokens`，包括调用方残留 options 的值。共享类型的清理需核对其他消费者，但任何残留字段均不能成为 CampusMate 的控制来源；不得用 0 或极大值冒充“无限制”。Chat 目标请求不再定义输出额度字段，发送时按未知字段拒绝。Mate 的路由额度来源、合法性校验、输入与输出空间协调和上游必填参数补齐需同时实现，不能只删 Claw 参数后假定每个上游均可省略。

**Claw 仍管理输入上下文。** `reserveTokens` 是压缩触发所需的输入安全余量，`keepRecentTokens` 是保留上下文策略，均不作为 HTTP 输出限制。启用压缩时要求 `contextWindow > reserveTokens`，否则本次执行准备失败。阈值保持严格大于 `contextWindow-reserveTokens`；它是估算策略，不保证 Mate 一定能生成 reserveTokens 数量的输出。

新执行取得窗口后，在首次生成前检查完整待发送上下文（系统提示词、工具定义、历史、摘要及本次新输入）；后续工具结果追加后也检查。旧 Usage 必须结合新增内容估算，不能把同一 modelId 的旧 Usage 当作新窗口下的可用额度。窗口缩小时先按新阈值压缩，再重新估算；无安全切点、摘要请求本身已超窗口、摘要无压缩收益或压缩后仍超阈值时明确失败并保留历史，不无界循环压缩、不静默删消息。关闭自动压缩时不自动生成摘要，已估算超出窗口的输入仍不能盲目发送。摘要输入装不下时首版失败；分块摘要属于后续独立设计。

`LENGTH` 只说明生成截断，不能单独判定上下文不足；停止使用“output 小于 model.maxTokens”恢复启发式。保留明确上下文溢出信号以及已验证、仅依赖 contextWindow/Usage 的判断；有证据的失败恢复最多一次，成功 STOP 不重放。摘要同样由 Mate 控制输出，只接受完整成功摘要；LENGTH、空摘要、ToolCall、取消或失败不发布新上下文。摘要完成后校验压缩收益与新上下文预算，不能硬截断生成文本凑额度。算法与历史一致性见[Session 压缩设计](../../03-数据与存储/01-会话记忆GaussDB/compaction.md)。

## 5. Java 分层与实施切片

[全局目标图](model-classes.svg)与[图源](diagram.puml#L1)区分单例查询服务和执行级 DTO。Mate 新增 `ModelCapabilityController/ModelCapabilityService/ModelCapabilityResponseVO`：Controller 校验标量 ID 并包装 ResultBean，Service 从模型元数据/路由来源组装只读 VO，不序列化带凭据的 ModelRoute。Claw 的 `ExecutionModelResolver` 负责锁外查询，应用服务负责锁内复核，避免把网络 I/O 藏入本地模型选择或 AgentSessionFactory。首版扩展 Mate 现有逐模型配置来源，输出策略在 Mate 内维护；不新增模型数据库表或 Maven 依赖。

| 切片 | 实施内容 | 验收 |
|---|---|---|
| C1 · Mate 信息与输出策略 | 逐模型 contextWindow、独立 GET、Mate 输出额度与协议适配 | 两模型返回不同窗口；缺值、非法、禁用、不存在准确失败；输出参数必填的上游也可调用；无路由凭据泄漏 |
| C2 · 执行准备 | 共享 endpoint、查询 DTO、ExecutionModelResolver、锁外查询及锁内准入 | 两次新消息分别 GET；同一根工具/确认续跑仅一次；查询失败无接受记录；版本/模型/绑定竞争拒绝；prepareCached、列表不联网 |
| C3 · 输出与压缩 | 清理 Agent/options/Mapper/摘要的额度；按新窗口前置估算与压缩；删除部署默认值 | 所有 Chat 请求无三个输出限制字段；LENGTH 无输出上限推断；窗口缩小、超大输入、无收益摘要与关闭压缩有界失败且不丢历史 |
| C4 · 跨入口与发布 | Runtime/Child/Cron/手工压缩、modules/公司镜像与服务端协同 | 各新执行查询一次；确认复用；不同执行不串窗口；镜像行为等价；不增加旧目录能力 schema |

发布顺序：Mate 先具备查询与自主输出策略，在兼容阶段仍识别旧客户端字段；Claw 全量切换到无输出字段后，Mate 移除该请求字段并按目标契约拒绝。该顺序避免旧 Claw 请求被提前拒绝；不为新 Claw 保留旧默认值或缓存回退。

当前实现仍依赖全局 128000/8192，Agent 自动补输出额度且摘要独立限额；信息查询、执行级能力装配、Mate 自主额度和前置预算检查均待实现。现有绑定快照、执行准入与压缩骨架已存在，不将其整项标为待实现；文档校验不代表产品测试通过。

## 6. 版本记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.1.0 | 2026-09-19 | Mate 独立控制输出额度，Claw 每个新执行查询模型窗口并固定执行快照。 |
| 1.0.0 | 2026-09-19 | 定义独立模型能力查询、快照与字段消费边界。 |
