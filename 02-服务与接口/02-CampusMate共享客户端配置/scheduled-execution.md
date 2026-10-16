# Mate 定时执行凭据接口

版本：1.0.0；日期：2026-10-16；状态：接口草案，Mate 侧待实现。以下新增路径与字段是配套设计，不冒充已发布接口。

[共享连接目录](README.md) · [定时任务主设计](../../01-总体架构/08-CampusClaw定时任务/README.md) · [Claw 调用 Mate 的接口总览（主设计 §4.8）](../../01-总体架构/08-CampusClaw定时任务/README.md#mate-calls)

本文定义 Mate 为定时任务新增的两个接口：获取统一账号 access-token（§1），以及 Session 归属登记（§2，路径与报文待定）。Claw 何时调用、失败后怎么处理，以主设计 §4.8 为准。

<a id="scheduled-access-token"></a>

## 1. 获取统一账号 access-token

### 1.1 为什么需要

普通对话中，用户请求带着 `access-token` Header，Claw 调用 Mate 业务工具时原样透传（[M06 §7.1](../../01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md#credential-forwarding)）。定时任务到点运行时没有用户请求，也就没有用户的 access-token。2026-10-13 评审确定：所有定时任务统一使用 Mate 配置的同一个账号，Claw 运行时向 Mate 取这个账号的 access-token。

代价：用户创建任务后失去权限或离职，任务仍以统一账号的权限照常运行；统一账号能做什么，就是所有定时任务能做什么。用户权限只在配置任务时由 Mate 检查。

### 1.2 请求

```http
POST /mate-service/v1/runtime/scheduled-access-token
Accept-Language: zh-CN
```

| 项 | 规定 |
|---|---|
| 路径 | 草案路径；Claw 用 `campusclaw.schedule.access-token-path` 配置，服务地址沿用[共享连接目录](README.md)的 `campusmate.base-url` |
| 请求体与参数 | 无请求体，无 query 参数；不传用户、任务、Session 或 Agent 标识 |
| 调用方认证 | 只允许已认证的 Claw 服务调用，认证方式待定（主设计 T2） |
| Accept-Language | 支持 zh-CN / en-US，缺省 en-US，只影响错误文案 |

### 1.3 成功响应

HTTP 200，ResultBean：

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "accessToken": "<value supplied by Mate>"
  }
}
```

| 字段 | 规定 |
|---|---|
| result.accessToken | 统一账号当前有效的 access-token，非空字符串；Claw 收到空值按失败处理 |
| 响应头 | `Cache-Control: no-store`；网关与客户端不记录响应正文 |

首版不返回有效期，Claw 也不缓存。以后若需要减少调用，可增加过期时间字段，由 Claw 在进程内缓存、临近过期再取。

### 1.4 错误响应

失败时只返回 resCode 与 resMsg，不回显 Token、内部地址或原始异常。

| HTTP / resCode | 含义 | zh-CN / en-US |
|---|---|---|
| 401 / SCHEDULED_TOKEN_AUTH_REQUIRED | 调用方不是获准的 Claw 服务 | 定时执行凭据认证失败。 / Scheduled execution token authentication is required. |
| 403 / SCHEDULED_TOKEN_FORBIDDEN | 统一账号未配置或已停用 | 定时执行账号不可用。 / Scheduled execution account is not available. |
| 500 / SCHEDULED_TOKEN_FAILED | 内部处理失败 | 获取定时执行凭据失败。 / Failed to obtain scheduled execution token. |
| 503 / SCHEDULED_TOKEN_UNAVAILABLE | 认证中心等依赖不可用 | 定时执行凭据服务暂不可用。 / Scheduled execution token service is temporarily unavailable. |

### 1.5 Claw 如何使用

| 项 | 规定 |
|---|---|
| 调用时机 | 定时触发的根执行及其 Child 中，模型一次返回的工具调用里至少一个需要凭据的工具通过参数校验和权限判断后、执行前取一次；只含无凭据工具、参数错误或需要人工确认时不取 |
| 使用范围 | 同一批工具调用共用；下一批重新取；不跨批次、不跨运行、不跨实例缓存 |
| 透传方式 | 只作为 `access-token` Header 传给 `POST /mate-service/v1/runtime/tools/{toolId}/execute`，不补 X-HW-ID、Authorization、X-HW-APPKEY |
| 失败 | 本批需要凭据的工具都不执行，按工具失败返回模型，模型可在下一批重试；不换其他账号或旧值；execute 已发出后不因刷新 Token 重放 |
| 保密 | 只在本批次内存中使用；不进日志、异常、模型提示、工具结果、Session 事件和数据库；对象 toString 脱敏 |
| 不调用的情况 | 用户在定时任务的 Session 里继续对话时，用该请求 Header 里的用户凭据（主设计 [§3.11](../../01-总体架构/08-CampusClaw定时任务/README.md#session-credentials)）；未配置 CampusMate 地址时 Claw 关闭此接口 |

Claw 侧实现为 `MateAccessTokenClient`（实现 `ScheduleAccessTokenProvider`），已随 pi-mono-java PR #332 合并：只认 resCode 0 与非空 accessToken，构造只含 `access-token` 的 `MateCredentials` 快照。

### 1.6 验收

- 一批多个需要凭据的工具只取一次；两批之间重新取；Child 各自获取。
- 只含无凭据工具、参数错误或需要人工确认时不取。
- 取 Token 失败时本批工具不执行，不换账号重试。
- execute 的 Header 只含 `access-token`。
- Token 不进日志、事件和数据库；execute 结果未知不重放。
- 需要真实 Mate/Claw 联调和公司认证中心验证。

<a id="session-ownership"></a>

## 2. Session 归属登记（待设计，T7）

接口配置的任务每次运行都新建 Session。Mate 需要知道这个 Session 属于哪个用户，之后用户读取、继续、停止或删除它时，Mate 才能据此授权再调用 Claw。2026-10-13 评审确定归属登记保留在 Mate，Claw 不保存用户或归属。对话中由 Cron 工具创建的任务在用户自己的会话里运行，归属随会话，不登记；Mate 按任务的 sessionId 判断它属于哪个用户。

Mate 侧的路径与 VO 尚未确定。Claw 侧已按下列语义定义 `ScheduleSessionRegistry`，Mate 接口确定后由部署适配实现：

| 操作 | 入参 | 期望结果 |
|---|---|---|
| 登记 | sessionId、scheduleId、runId、agentId 四个技术标识，不含用户、消息正文或凭据 | 返回与入参相同的四个字段表示登记成功；明确拒绝时返回错误；Mate 按自己维护的任务与用户关联确定归属（用 user_id 标识），不接收 Claw 自报的用户 |
| 只读核对 | 同上 | 已登记时返回该登记；未登记返回空；不创建记录 |

交接规则：

1. Claw 为同一次 Run 先固定 Session ID，之后准备和受理都复用这个 ID。
2. 在数据库事务外请求登记。重复登记相同的四个标识不得改变归属。
3. 登记成功后，Claw 在同库事务中创建 Session、首消息、根执行和 Run 关联；Mate 记录不加入这个事务。
4. 登记结果未知时只读核对，不重发登记，也不换新 ID。Mate 已登记而 Claw 回滚时，由对账确认 Session 从未提交后再清理登记；提交结果未知时保留待核对，不能凭超时删除。
5. 删除 Schedule/Run 不删除已建立的 Session 归属；Session 删除后由 Mate 关闭对应访问映射。

现状：pi-mono-java main `ead67eba` 中，`schedule/session/ScheduledSessionStarter.prepare/confirmRegistration` 已按第 1～4 步接线；默认实现 `schedule/mate/MateScheduleSessionRegistry` 一律返回服务不可用。因此在 Mate 接口上线或部署方替换实现之前，接口配置的任务到点后不会运行（主设计 [§4.8.2](../../01-总体架构/08-CampusClaw定时任务/README.md#mate-calls)）。未读取 Mate 当前生产实现，不指定其物理表名。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-10-16 | 改为先完整定义获取 access-token 接口，再写归属登记；删除既有接口列表等非本接口内容。 |
| 0.9.0 | 2026-10-16 | 接口总览改以主设计 §4.8 为准，对话中创建的任务不登记归属，Claw 侧类名对齐实现。 |
| 0.8.0 | 2026-10-15 | 列表改为按 D9 由 Mate 拉取全部后过滤，Cron 工具首版只读且不向 Mate 请求授权，会话归属用 user_id 标识。 |
| 0.7.0 | 2026-10-15 | 撤销按 agentId 的 Agent 存在且启用校验，定时任务不再校验 Agent 启停用。 |
| 0.6.0 | 2026-10-15 | 定时准备按 agentId 校验 Agent 存在且启用，作为 D12 自动暂停的唯一判定依据；接口待 Mate 确认。 |
| 0.5.0 | 2026-10-13 | 确认 Session 归属登记保留在 Mate，去掉“待对齐”；登记接口路径与 VO 仍待定。 |
| 0.4.0 | 2026-10-13 | 定时执行改为统一账号：Claw 无入参向 Mate 获取 access-token，模型每批工具调用取一次；撤销执行上下文查询、按目标解析凭据和 authorizationRef。 |
| 0.3.0 | 2026-10-13 | M10 定时任务移除 credentialIds，凭据改由 Mate 按 Agent 绑定在运行时决定。 |
| 0.2.0 | 2026-10-10 | 身份、资源归属和权限统一由 Mate 维护，明确会话登记与受理失败的交接边界。 |
| 0.1.0 | 2026-10-05 | 定义Mate上下文查询与按目标解析凭据草案，复用现有工具定义入口并区分服务认证与业务凭据。 |
