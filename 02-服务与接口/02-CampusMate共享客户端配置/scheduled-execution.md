# Mate 定时执行凭据接口

版本：0.6.0；日期：2026-10-15；状态：接口草案，待实现。以下新增 Mate 路径及字段是配套设计，不冒充已发布接口。

[共享连接目录](README.md) · [定时任务主设计](../../01-总体架构/08-CampusClaw定时任务/README.md) · [核验依据](../../01-总体架构/08-CampusClaw定时任务/source-evidence.md#schedule-engineering-evidence)

## 1. 业务问题与边界

普通对话中，用户请求带着 `access-token` 等凭据 Header，Claw 把它们存成本次执行快照，调用 Mate 工具时原样透传（[M06 §7.1](../../01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md#credential-forwarding)）。定时任务到点运行时没有用户请求，Claw 需要从 Mate 取得调用业务工具所需的凭据。

2026-10-13 评审确定首版方案：

| 决策 | 内容 |
|---|---|
| 权限检查时机 | 只在配置任务时由 Mate 检查用户是否有权限；运行时不再按用户重新检查 |
| 执行账号 | 所有定时任务统一使用 Mate 配置的同一个账号，不代表任务创建者 |
| 凭据范围 | 首版只支持 `access-token`，不提供 X-HW-ID、Authorization、X-HW-APPKEY |
| 获取接口 | Claw 调用 Mate 一个无入参接口取得该账号的 `access-token`，见 §3 |
| 获取频率 | 模型一次返回中包含需要凭据的工具调用时取一次，这一批工具调用共用；不跨批次、不跨运行缓存 |

代价：用户创建任务后失去权限或离职，任务仍以统一账号的权限照常运行；统一账号能做什么，就是所有定时任务能做什么。Claw 不保存凭据、授权引用或用户身份。

正常流程为：到期后准备 Agent → 受理新 Session 及根执行 → 模型返回一批工具调用 → 逐个完成可信目标解析、参数校验和权限判断 → 本批有需要凭据的工具通过判断时，向 Mate 取一次 `access-token` → 通过既有 Mate execute 执行，Header 只带 `access-token` → 保存安全结果。取 Token 失败时本批需要凭据的工具都不发业务请求，按工具失败返回模型；实际 execute 结果未知时不自动再次发送。

## 2. 复用现有接口定义入口

| 操作 | 用途 | 本次源码证据与限制 |
|---|---|---|
| GET /mate-service/v1/agents/{agentId}/runtime | Agent配置、工具/Skill绑定和运行定义 | Mate示例已有Controller；当前缓存prepare不保证每次从远端刷新，沿现有发布快照语义 |
| GET /mate-service/v1/agents/{agentId} | 取得Agent直接绑定的工具标识 | 已有Controller与Claw消费者；仍须补可信范围授权，不因Agent存在就认为可执行 |
| GET /mate-service/v1/skill/query/{skillId} | 取得可信Skill工具绑定 | Claw已有客户端路径；本次Mate示例范围未发现对应Controller |
| POST /mate-service/v1/runtime/tools/query | 按已绑定toolIds取得完整定义及inputSchema | Claw客户端已有；本次Mate示例未发现Controller。保留现有消费者契约，不在定时设计中另建工具定义目录 |
| POST /mate-service/v1/runtime/tools/{toolId}/execute | 执行业务工具 | 只在目标、参数、权限均通过后调用；真实endpoint来自共享目录，不能用模型提供的URL替代 |

定时准备还需要按 agentId 确认 Agent 存在且启用（Claw 侧 `ScheduleAuthorizationPort`，主设计 D12）：只做技术校验，不查用户资格，不经发布缓存；结果须能区分“不存在/已删除”“已禁用”“查询失败”，只有前两者让 Claw 记 agent_unavailable_error。可复用 `GET /mate-service/v1/agents/{agentId}`（需返回启用状态，404 表示不存在），具体路径与字段待 Mate 确认。

本次不把接口定义和秘密混成一个返回模型的工具清单。工具发现结果只供解析/模型理解，凭据只由可信执行Adapter使用。工具元数据的历史snake_case输入兼容属于既有客户端事实；新增接口使用lowerCamelCase，不全局改写旧协议。

## 3. 获取定时执行 access-token（待实现）

推荐新增 `POST /mate-service/v1/runtime/scheduled-access-token`，路径为草案。只允许已认证的 Claw 服务调用；服务认证机制尚未确定（主设计 T2）。

请求：无正文，也无 query 参数。

HTTP200，ResultBean.result 形状：

```json
{
  "accessToken": "<value supplied by Mate>"
}
```

| 规则 | 内容 |
|---|---|
| 调用时机 | 模型一次返回中，至少一个需要凭据的工具通过参数校验和权限判断后、发起 execute 前调用一次；只含无凭据工具、参数错误或权限 ASK 时不调用 |
| 使用范围 | 同一批工具调用共用这次取得的值；Subagent 的工具批次各自获取；不跨批次、不跨运行、不跨实例缓存 |
| 透传方式 | 作为 `access-token` Header 传给 `tools/{toolId}/execute`，不改名、不补其他 Header |
| 保密 | 只存在本批次的内存快照；不进日志、异常、模型提示、工具结果、Session 事件、缓存文件和数据库；对象 toString 必须脱敏 |
| 失败 | 401/403/5xx 或返回空值时，本批需要凭据的工具都不执行，按工具失败返回模型，不换用其他账号或旧值；已发送 execute 后不因刷新 Token 重放 |
| 缓存控制 | 响应 `Cache-Control: no-store`，网关与客户端禁用正文记录 |

Token 有效期目前未知。以后若需要减少调用，可由 Mate 同时返回过期时间，Claw 在进程内缓存统一账号的值，临近过期再取；首版不做。

<a id="session-ownership"></a>

## 4. 会话归属登记（待实现）

Mate 独立维护 Session ID 到用户、组织/管理范围及授权政策的关联；Schedule/Run 的管理归属也由 Mate 维护。Claw 不建对应身份表或列。2026-10-13 评审确定：Session 归属登记保留在 Mate，Claw 不保存用户或归属。下述交接顺序沿用此前设计，登记接口的路径与 VO 仍待定。

1. Claw 为同次 Run 固定拟建 Session ID；该 ID 由 Runtime 生成，后续准备和事务受理复用，不能在 `newSession` 再生成另一个 ID。
2. 数据库事务外，Claw 用服务身份和固定的 Session/Run/Schedule/Agent ID 请求 Mate 登记。Mate 按自己维护的任务与用户关联持久保存会话归属；不接收 Claw 自报用户、租户或 owner。记录在 Claw 确认存在前仅为待核对关联，不对外承诺会话可访问。重复登记相同技术身份不得改绑归属。
3. 确认 Mate 登记成功且准备未过期后，Claw 在原同库事务创建 Session、首消息、根执行和 Run 关联，提交后才能启动；Mate 记录不加入该数据库事务，不引入跨库事务。关联或准备失败不启动模型、不执行业务。
4. Mate 登记响应未知时，按固定技术 ID 只读核对；仍未知则本次不受理，不重新分配 ID 或自动重放业务。Mate 已登记、Claw 回滚时，由对账确认会话从未提交后清理关联；提交结果未知时保留待核对，不能凭超时删除。Claw 已受理但回执丢失时，读取现有 Session/Run/根执行，不再次创建。
5. 用户读取、继续对话、停止和删除会话时，Mate 依据当前主体及会话关联逐次授权，再以可信服务请求调用 Claw。Claw 校验服务来源和获准操作/目标，执行自身状态检查；浏览器、模型提供的资源 ID 不是授权依据。列表先取 Mate 判定的可见集合再分页，空集合禁止退化为全库。
6. 删除 Schedule/Run 不删除已经建立的 Session 归属或撤销已受理执行的独立关联。Session 删除确认后 Mate 关闭相应访问映射，未知结果先核对；公共 Chat 映射可以异步补齐，但不能替代上述归属登记。

Claw 的 Cron 工具只携带当前执行/Session、Agent 和目标资源 ID 向 Mate 请求操作授权，不捕获浏览器用户主体，不让 `sessionOwnerRef` 冒充 `operatorRef`，也不在通用 Runtime 中引入 ScheduleSubjectDTO。服务认证、授权结果的传递绑定与防越权检查仍须真实联调；缺失时拒绝，不能为了移除身份列而开放内部接口。Mate 用户审计独立记录，Claw 技术日志只关联资源与执行身份。

核验：PR #332 `e9d31e8888a81b7fe95071e705482bb16fa10476` 的 `schedule/mate/MateScheduleContextClient.query/resolveCredentials`、`runtimeapi/schedule/ScheduledRuntimeAdmissionService.newSession/encodeContext` 尚传递并保存归属；源码根为 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。本节职责修正、归属登记及服务授权接线均**待实现**；未读取 Mate 当前生产实现，不指定其物理表名，不宣称已有上述接口。

## 5. 共用HTTP、错误及Java边界

新增接口成功返回 HTTP200 和 ResultBean，失败仅 resCode/resMsg。Accept-Language 支持 zh-CN/en-US，缺省 en-US。不得添加 If-Match、Idempotency-Key、ETag 或同义 body/query 键。

| HTTP / resCode | 边界 | zh-CN / en-US |
|---|---|---|
| 401 / SCHEDULED_TOKEN_AUTH_REQUIRED | 调用方不是获准的 Claw 服务 | 定时执行凭据认证失败。 / Scheduled execution token authentication is required. |
| 403 / SCHEDULED_TOKEN_FORBIDDEN | 统一账号未配置或已停用 | 定时执行账号不可用。 / Scheduled execution account is not available. |
| 500 / SCHEDULED_TOKEN_FAILED | 内部处理失败 | 获取定时执行凭据失败。 / Failed to obtain scheduled execution token. |
| 503 / SCHEDULED_TOKEN_UNAVAILABLE | 认证中心等依赖不可用 | 定时执行凭据服务暂不可用。 / Scheduled execution token service is temporarily unavailable. |

错误不得回显 Token、接口内部地址或原始异常。受理后发生的取 Token 失败属于原 Session 内该批工具的真实结果，不改写已成功的 Run。

Claw 新增 `ScheduledAccessTokenClient`，在工具批次执行前取得值并构造只含 `access-token` 的 `MateCredentials` 快照；定时路径不做“X-HW-ID + access-token + JWT/APPKEY”的完整性检查，与 M06 目标一致。复用现有 JDK HTTP 客户端、Jackson、Spring，不新增外部依赖。

## 6. 配置、结构与验收

共享端点目录增加 `scheduled-access-token-path`，仍只有一个 `campusmate.base-url`。全局结构复用 [M10 目标类图](../../01-总体架构/08-CampusClaw定时任务/README.md#class-diagram)。

验收覆盖：一批多个需要凭据的工具只取一次；只含无凭据工具、参数错误或 ASK 时不取；两批之间重新取；Subagent 各自获取；取 Token 失败时本批工具不执行且不重试其他账号；Header 只含 `access-token`；Token 不进日志、事件和数据库；execute 结果未知不重放。需要真实 Mate/Claw 联调和公司认证中心验证。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.6.0 | 2026-10-15 | 定时准备按 agentId 校验 Agent 存在且启用，作为 D12 自动暂停的唯一判定依据；接口待 Mate 确认。 |
| 0.5.0 | 2026-10-13 | 确认 Session 归属登记保留在 Mate，去掉“待对齐”；登记接口路径与 VO 仍待定。 |
| 0.4.0 | 2026-10-13 | 定时执行改为统一账号：Claw 无入参向 Mate 获取 access-token，模型每批工具调用取一次；撤销执行上下文查询、按目标解析凭据和 authorizationRef。 |
| 0.3.0 | 2026-10-13 | M10 定时任务移除 credentialIds，凭据改由 Mate 按 Agent 绑定在运行时决定。 |
| 0.2.0 | 2026-10-10 | 身份、资源归属和权限统一由 Mate 维护，明确会话登记与受理失败的交接边界。 |
| 0.1.0 | 2026-10-05 | 定义Mate上下文查询与按目标解析凭据草案，复用现有工具定义入口并区分服务认证与业务凭据。 |
