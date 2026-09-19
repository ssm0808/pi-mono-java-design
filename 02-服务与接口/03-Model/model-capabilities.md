# Mate 模型能力查询与快照

版本：1.0.0 · 2026-09-19 · 状态：已确认目标，待实现。

[返回 Model 主设计](README.md) · [全局目标类图](model-classes.svg) · [源码证据](source-evidence.md#model-capability-evidence)

## 1. 权威与边界

Mate 按 modelId 维护模型实际可用的上下文窗口和可选输出上限。CampusClaw 根据 Agent 的绑定模型 ID 单独查询 Mate，再把结果与 Agent 设置一起发布到本地快照；不把能力字段加入 Agent runtime 查询响应，也不在每次 Chat 或 Session 锁内访问 Mate。

`bindingModels/defaultModel` 决定允许使用和默认选择的模型；能力查询只补充已绑定模型的描述，不能增加可选模型。`contextWindow` 是 Mate 当前路由实际支持的总上下文窗口，`maxTokens` 是已知时的模型有效最大输出上限；二者不能由 CampusClaw 的统一部署默认值推断。Mate 应依据所管理模型及路由的真实限制维护数据，不能把旧的两个默认值搬到 Mate 后对所有模型统一返回。

这是产品约束与架构变更：模型能力由拥有路由信息的 Mate 维护，Runtime 使用固定快照。代价是准备/刷新多一次每模型读取，并需要 Mate 维护准确元数据。首版只迁移这两个 token 字段；reasoning、模态及计费仍按各自既有设计处理，不因本专题宣称已从 Mate 获取。

## 2. 独立能力查询契约

本节维护新增 operation 的精确契约；既有 `chat-api.json/html` 只维护 Chat，不受替换。

| 项目 | 规则 |
|---|---|
| Method / path | `GET /mate-service/v1/models/{modelId}` |
| 用途 | 返回一个模型的能力；不提供全局模型枚举，不调用上游生成接口 |
| modelId | 沿用 Mate Chat 的不透明、大小写敏感、1–64 字符身份；客户端用 URI path-segment 编码一次，服务端不 trim、转小写或重写 ID；网关需验证编码 ID 的透传 |
| 调用边界 | CampusClaw 经内部网关读取；使用现有服务准入与网络 ACL，不携带用户 execution 四项凭据或上游 endpoint、apiKey |
| 成功 | HTTP 200、`application/json`、`Cache-Control: no-store`，ResultBean 为 `resCode/resMsg/result` |
| 失败 | 使用真实 HTTP 状态，只含 `resCode/resMsg`；消息按既有 `Accept-Language` 规则本地化并设置 `Content-Language` |
| result.modelId | 必填，精确等于请求 ID |
| result.contextWindow | 必填 JSON 整数，范围 1–2147483647，单位 token |
| result.maxTokens | 可选 JSON 整数；提供时为 1–contextWindow；未知时省略，不返回 null、0、负数或虚构默认值 |

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "modelId": "model-550e8400e29b41d4a716446655440000",
    "contextWindow": 128000,
    "maxTokens": 8192
  }
}
```

示例数字仅表示某个模型的已知能力，不是默认值；maxTokens 未知时整个属性省略。

| HTTP 状态 | resCode | 条件 |
|---|---|---|
| 400 | `INVALID_MODEL_ID` | 请求 ID 不满足标量边界约束 |
| 404 | `MODEL_NOT_FOUND` | Mate 不存在该 ID |
| 422 | `MODEL_UNAVAILABLE` | 模型被禁用或不能提供服务 |
| 503 | `MANAGER_UNAVAILABLE` | 元数据来源不可用、缺少 contextWindow 或配置值非法 |

缺少可选 maxTokens 本身不构成失败。查询不是一次模型调用或使用授权；真实 Chat 仍检查当时的模型可用状态，快照不能保证路由永久可用。返回窗口正确也不等于已经验证真实模型容量。

## 3. 查询、校验与发布

1. `AgentRuntimeManager` 在准备/刷新时先取得 Agent runtime 定义，固定绑定列表和默认模型，再通过 `MateServiceClient` 按每个绑定 ID 查询能力；同次准备每个 ID 只查询一次。
2. 检查响应 ID、必填字段、整数类型、数值范围及模型与能力的一一对应关系。任何模型失败或缺少 contextWindow，整个新快照发布失败；不得省略失败模型后悄悄修改允许列表。
3. `.campusclaw/settings.json` 保留 `defaultModel/bindingModels`，新增 `modelCapabilities` 对象，以 modelId 为键，值为 `contextWindow` 与可选 `maxTokens`。键集合必须精确等于 bindingModels，所有值均来自本次成功查询。
4. 复用 staging、完整性验证与原子发布。`PreparedAgentRuntime`、`AgentDirectorySnapshotDTO` 持有深度不可变的能力映射；`MateRuntimeModelManager` 只从该快照构造 Model，不联网、不回退本地常量。Java 内部新增/扩展的数据对象使用 DTO。
5. 执行创建时固定完整 Model；模型列表、选择、普通调用、压缩、Child/Cron 使用各自 Agent 的同一准备快照。正在执行的 Model 不受目录刷新影响；显式模型切换和后续新准备读取完整新快照，并在原有锁/事务内复核可变准入状态。

多个 GET 不构成 Mate 跨模型的数据库快照；本设计承诺的是 CampusClaw 对完整查询结果的一次本地原子发布。单个响应的两个数值必须由 Mate 从同一模型描述读取，不能分别从可变配置取值。模型更新通过已有 refresh/重新发布生效，不新增后台轮询；更新尚未刷新时继续使用已发布能力，Chat 仍可能因路由变化而失败，不自动重放写请求。

快照 schema 必须升级并显式校验。旧快照缺少整个 modelCapabilities 视为不完整，按既有允许联网的 prepare 重建；仅允许读缓存的 prepareCached 失败，不自行联网。刷新失败保留磁盘旧完整快照并报告失败，不把失败刷新包装成成功；已固定的活动执行继续遵守原生命周期。没有可用完整快照时拒绝准备。

## 4. 可选 maxTokens 的消费规则

模型能力上限与调用输出预算是两个概念。未知上限使用可空类型表示，不能用 0、负数、Integer.MAX_VALUE 或 8192 冒充。目标 `Model.maxTokens` 及对应 DTO 改为可空 Integer，并逐项处理现有算术与自动拆箱消费者。

| 场景 | maxTokens 已知 | maxTokens 未知 |
|---|---|---|
| 普通 Chat 无显式输出额度 | 延续 Agent 默认使用模型上限的行为 | 不自动填充 `max_output_tokens`，由 Mate/上游处理 |
| 调用方显式输出预算 | 使用正整数预算，上限取预算与模型上限较小者 | 保留显式正整数预算；它是调用策略，不被记录为模型能力 |
| fast 等明确限制输出的辅助方法 | 按自身预算与已知上限取较小值 | 保留自身策略预算；fromModel/thorough 等不得虚构上限 |
| 上下文阈值与显式溢出 | 使用 contextWindow 和既有压缩规则 | 相同；不依赖 maxTokens 是否存在 |
| 仅凭 LENGTH 与输出数比较推断可恢复截断 | 使用该次调用已知的有效期望额度，避免显式小预算导致误判 | 跳过依赖模型上限的启发式；不能由 LENGTH 单独推断上下文不足 |
| 压缩摘要 | 历史/轮次前缀预算仍分别为 reserve 的 80%/50%，再与已知模型上限取较小值 | 保留摘要自身预算，不把该预算反写成模型 maxTokens |

摘要预算是运行策略，仍可能被未知的上游限制拒绝；沿既有失败规则处理，不发布失败摘要、不猜测能力后无界重试。启用压缩且 `contextWindow <= reserveTokens` 时当前压缩配置不可用，准备阶段明确失败，要求调整运行策略；不能扩大模型窗口来适配默认 reserve。

Provider Mapper 仅转发最终 options，缺少 maxTokens 时省略字段；Mate Chat 仍保持输出参数可选。需要输出参数的上游由 Mate 的协议适配负责，CampusClaw 不恢复全局输出能力默认值。本专题不直接照搬 pi 最新实现的 4096 上下文安全余量算法，也不改变现有自动压缩时点。

## 5. Java 分层与实施切片

全局目标关系见 [Model 主图](model-classes.svg)，图源见 [diagram.puml](diagram.puml#L1)。Mate 新增 `ModelCapabilityController` 和 `ModelCapabilityService`；Controller 校验标量 ID、返回 `ModelCapabilityResponseVO` 并包装 ResultBean，Service 从模型元数据/路由解析边界取得描述并组装 VO，不直接把含凭据的 ModelRoute 序列化出去。首版可在现有 Mate 模型配置来源增加逐模型能力字段，后续元数据存储替换不改变查询契约；不新增模型数据库表或 Maven 依赖。

| 切片 | 实施内容 | 验收 |
|---|---|---|
| C1 · Mate 能力 | 逐模型元数据、独立查询 Controller/Service/VO、错误与国际化 | 两个不同模型返回不同能力；未知输出上限可成功；缺窗口、非法值、禁用及不存在均准确失败；响应无私有路由及凭据 |
| C2 · 快照发布 | 共享 endpoint、MateServiceClient 查询与 DTO、settings schema、不可变快照 | 全量成功才发布；ID 错配/重复/缺失拒绝；一项失败保留旧完整目录；旧 schema 触发明确重建；缓存读取不联网 |
| C3 · 消费与配置清理 | Model 可空 maxTokens、Agent/options 工厂、压缩/截断判断；删除两个部署默认值及 Java fallback | 未知时普通 Chat 无输出字段，显式额度与摘要预算仍生效；无拆箱异常、错误启发式和全局常量回退 |
| C4 · 一致性 | 默认/切换/Child/Cron/压缩及 modules/公司镜像 | 活动调用固定 Model，新准备读取完整新快照；两个入口配置与 Java 行为等价；Mate 不可用不生成伪造能力 |

目前源码只具备 ID 绑定、默认值补齐和目录原子发布骨架；独立查询、能力快照和可选 maxTokens 链路均待实现。文档检查不代表上述测试通过。
