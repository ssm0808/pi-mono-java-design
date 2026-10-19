# mate-service 定时任务设计

[服务与接口导航](../README.md) · [Claw 定时任务主设计](../../01-总体架构/08-CampusClaw定时任务/README.md) · [Claw 接口协议](../../01-总体架构/08-CampusClaw定时任务/README.md#interface) · [页面设计 M07 场景09](../../07-前端设计/场景/09-配置与管理定时任务/README.md) · [共享连接目录](../02-CampusMate共享客户端配置/README.md)

本文是 Mate 侧定时任务的唯一设计文档，集中维护 Mate 在定时任务里的全部职责：对浏览器提供的管理接口（§3）、调用 Claw 时的处理（§4）、为 Claw 提供的两个接口（§5）以及归属对账（§6）。Claw 侧的调度、受理、表结构和 HTTP 契约只在 [Claw 主设计](../../01-总体架构/08-CampusClaw定时任务/README.md)维护，本文引用不复制。

| 属性 | 值 |
|---|---|
| 文档版本 | 1.0.0 |
| 更新日期 | 2026-10-19 |
| 模块 | M10 · 调度与并发治理（Mate 侧） |
| 设计状态 | 目标设计，Mate 侧全部待实现；§5.1 的 Claw 调用方已在 pi-mono-java 实现，§5.2 的 Claw 端口已接入受理流程 |
| 依据 | Claw 主设计 0.66.0；Mate 公共约定沿用 [mate-service 通用对话 API](../07-mate-service通用对话API/README.md#3-公共约定)；mate-service 当前源码未核验，不指定物理表名 |

## 评审记录

### 待确认事项

以下各项本文先按“建议”一列设计，评审确认或改动后同步正文。

| # | 问题 | 建议 | 影响 |
|---|---|---|---|
| <a id="m1"></a>M1 | 接口配置的任务谁能看到和管理 | 首版只有创建者可见、可管理；不做同组织共享 | 决定 §3.4 的可见范围和 Claw [T10](../../01-总体架构/08-CampusClaw定时任务/README.md#todo-t10)（Claw 是否加 userId） |
| <a id="m2"></a>M2 | 每个用户最多能有多少个接口配置的任务 | 每用户 20 个，部署可配置；对话中创建的任务不计入，已由 Claw 限制为每个会话一个启用中的任务 | §3.5 配额检查 |
| <a id="m3"></a>M3 | Session 归属登记接口的路径与报文 | 采用 §5.2 的两个 runtime 路径 | 关闭 Claw [T7](../../01-总体架构/08-CampusClaw定时任务/README.md#todo-t7) 中登记接口部分 |
| <a id="m4"></a>M4 | Mate 写归属失败时留下的无主任务如何处理 | 无主任务登记一律拒绝，因此不会运行；对账任务 10 分钟后经 Claw 删除 | §6 |
| <a id="m5"></a>M5 | Claw 与 Mate 互相调用的服务认证 | 仍待定，沿用 Claw [T2](../../01-总体架构/08-CampusClaw定时任务/README.md#todo-t2) | §4、§5 全部接口 |

## 1. 职责与边界

运营人员在浏览器里通过 Mate 管理定时任务；任务的保存、调度和运行都在 Claw。Mate 在其中承担三件事：

1. **管理入口**：对浏览器提供定时任务的管理接口，负责用户认证、功能权限、可见范围、Agent 使用权限、配额以及任务与用户的关联。
2. **Claw 的调用方**：完成上述检查后，以可信服务身份调用 Claw 的 10 个定时任务接口，不把用户身份传给 Claw。
3. **Claw 的被调用方**：为定时运行提供统一账号 access-token 和 Session 归属登记两个接口。

| 能力 | Mate | Claw |
|---|---|---|
| 用户认证、功能权限、可见范围 | 负责（§3.4） | 不保存用户，只校验服务来源与 Mate 给出的操作范围 |
| 任务与用户的关联 | 负责，保存归属记录（§2） | 不保存 |
| 配额 | 每用户任务数（§3.5） | 频率策略（`SCHEDULE_POLICY_REJECTED`）；对话中创建的任务每个会话一个启用中 |
| 字段校验、Cron、计划时间 | 不重复校验，原样转发 | 唯一权威 |
| 调度、受理、运行、Run 记录 | 不参与 | 负责 |
| 定时运行的业务凭据 | 提供统一账号 access-token（§5.1） | 每批工具调用取一次 |
| 新 Session 的归属与访问入口 | 登记并建立 Chat 映射（§5.2） | 受理前请求登记 |
| 对话中创建的任务 | 只读归属：按关联会话的 Chat 判断 | Cron 工具直接创建，不经 Mate |

### 1.1 接口总览

定时任务涉及的全部接口集中列在这里；Mate 后续新增或修改接口须同步本表。

| 方向 | 接口 | 定义位置 | 状态 |
|---|---|---|---|
| 浏览器 → Mate | 10 个管理接口 `/mate-service/v1/schedules…`、`/mate-service/v1/schedule-runs…` | §3 | 待实现 |
| Mate → Claw | 10 个定时任务接口 `/campusclaw-service/v1/schedules…`、`/schedule-runs…` | [Claw §4.2](../../01-总体架构/08-CampusClaw定时任务/README.md#interface-list) | 待实现 |
| Claw → Mate | 获取统一账号 access-token | §5.1 | Claw 已实现调用方，Mate 待实现 |
| Claw → Mate | Session 归属登记与核对 | §5.2 | Claw 端口已接入受理，HTTP 适配与 Mate 待实现 |
| Claw → Mate | Agent runtime、Skill、工具查询、工具执行、模型调用 | [共享连接目录](../02-CampusMate共享客户端配置/README.md) | 普通对话已在用，定时任务不新增 |

## 2. 归属数据

Mate 用两类记录判断“任务属于谁”。物理表名和存储位置由 mate-service 实现决定，本文只定义逻辑字段与约束。

| 记录 | 字段 | 约束 |
|---|---|---|
| 任务归属 | scheduleId（创建成功前为空）、userId、state（`pending` / `active`）、createdAt | 只为接口配置的任务建立；scheduleId 非空时唯一；`pending` 记录计入配额，超过 10 分钟未补全 scheduleId 视为失败并删除 |
| 定时会话登记 | sessionId、scheduleId、runId、agentId、userId、chatId、createdAt | sessionId 唯一；userId 取自任务归属；同时建立 Chat → Session 映射，使用户可以从 Chat 入口打开这个会话 |

对话中创建的任务不建任务归属记录：它的 `sessionId` 就是用户已有 Chat 映射的 Session，Mate 按该 Chat 的所属用户判断归属。

删除任务只删除任务归属；定时会话登记和 Chat 映射随 Session 生命周期保留，规则见 §5.2。

<a id="management-api"></a>

## 3. 管理接口（浏览器 → Mate）

### 3.1 公共约定

| 项 | 规定 |
|---|---|
| 基础路径 | `/mate-service/v1` |
| 认证与 Header | 与 [通用对话 API §3.1](../07-mate-service通用对话API/README.md#31-认证header-与-path) 相同：Authorization 与 X-HW-APPKEY 至少一个，JWT 优先；X-HW-ID 为显式请求头；不接收 access-token，定时运行不使用调用者的凭据 |
| 报文 | ResultBean，lowerCamelCase；成功 `resCode/resMsg/result`，失败只有 `resCode/resMsg`，保留真实 HTTP 状态；`Cache-Control: no-store` |
| 时间 | 沿用 Claw：UTC 秒级、以 Z 结尾；页面按任务时区或浏览器时区显示 |
| 语言 | 错误文案按公司公共上下文的语言返回，`Content-Language` 标明实际语言 |
| 请求字段 | 与 Claw 契约相同，Mate 不增删业务字段，未知字段由 Claw 拒绝 |

### 3.2 接口清单

每个管理接口对应一个 Claw 接口，请求字段和 query 原样转发；Mate 只在转发前做权限检查、转发后做归属记录和标识投影。

| 操作 | Mate 方法与路径 | 需要的功能权限 | 对应 Claw 接口 | Mate 额外处理 |
|---|---|---|---|---|
| 创建 | POST `/schedules` | 管理 | POST `/schedules` | Agent 使用权限、配额、写任务归属（§3.5） |
| 列表 | GET `/schedules` | 读取 | GET `/schedules`（拉取全部页） | 按可见范围过滤后自行分页（§3.6） |
| 详情 | GET `/schedules/{scheduleId}` | 读取 | GET `/schedules/{scheduleId}` | 可见性检查（§3.7） |
| 部分更新 | POST `/schedules/{scheduleId}` | 管理 | POST `/schedules/{scheduleId}` | 可见性检查；改 agentId 时检查 Agent 使用权限 |
| 删除 | DELETE `/schedules/{scheduleId}` | 管理 | DELETE `/schedules/{scheduleId}` | 可见性检查；成功后删除任务归属 |
| 立即运行 | POST `/schedules/{scheduleId}/run` | 运行 | POST `/schedules/{scheduleId}/run` | 可见性检查；Run 投影（§3.3） |
| 暂停 | POST `/schedules/{scheduleId}/pause` | 管理 | POST `/schedules/{scheduleId}/pause` | 可见性检查 |
| 取消暂停 | POST `/schedules/{scheduleId}/unpause` | 管理 | POST `/schedules/{scheduleId}/unpause` | 可见性检查 |
| Run 列表 | GET `/schedule-runs` | 读取 | GET `/schedule-runs`（指定任务时单次，否则拉取全部页） | 可见性过滤（§3.8） |
| Run 详情 | GET `/schedule-runs/{runId}` | 读取 | GET `/schedule-runs/{runId}` | 按所属任务检查可见性（§3.8） |

路径和资源名与 Claw 一致，页面设计 [M07 场景09](../../07-前端设计/场景/09-配置与管理定时任务/README.md) 描述的报文语义（如 `schedule:null` 表示仅手动运行）直接适用于本接口。

### 3.3 资源投影

Mate 对外使用 Chat/chatId，不暴露 Runtime 的 sessionId（[通用对话 API §1](../07-mate-service通用对话API/README.md#1-接口与权威来源)）。Mate 原样返回 Claw 的 Schedule 与 Run，只替换会话标识：

| Claw 字段 | Mate 字段 | 规则 |
|---|---|---|
| Schedule.sessionId | Schedule.chatId | 接口配置的任务为 null；对话中创建的任务为关联会话的 chatId |
| Run.sessionId | Run.chatId | 受理成功时为 §5.2 登记时建立的 chatId（对话中创建的任务为原 Chat）；受理失败为 null；映射暂时查不到时为 null，页面显示“结果入口准备中”，不能因此再次运行 |

其余字段（id、scheduleId、agentId、triggerContext、error、status、pausedReason、schedule、metadata、时间）原样返回。scheduleId 与 runId 是 Claw 生成的不透明 ID，Mate 不另造公共 ID。

### 3.4 权限与可见范围

| 检查 | 规则 |
|---|---|
| 功能权限 | 读取、管理、运行三项，来自公司权限体系；缺少时返回 403，不调用 Claw |
| 可见范围 | 接口配置的任务：任务归属 `active` 且 userId 为当前用户；对话中创建的任务：关联 Chat 属于当前用户（[M1](#m1)） |
| 不可见 | 一律按不存在处理：详情与写操作返回 404 `SCHEDULE_NOT_FOUND`，Run 详情返回 404 `SCHEDULE_RUN_NOT_FOUND`，列表中不出现 |
| Agent 使用权限 | 创建和修改 agentId 时，按 Mate 现有 Agent 权限检查当前用户能否使用该 Agent；不能用返回 403 `SCHEDULE_AGENT_FORBIDDEN` |
| 用户权限变化 | 只在管理操作时检查；用户失去权限或离职后，已保存的任务仍按统一账号运行（Claw [D10](../../01-总体架构/08-CampusClaw定时任务/README.md#key-decisions)），需由管理员删除或暂停 |

对话中创建的任务也能在管理页看到，可以修改、暂停、恢复、删除，但不能改 agentId（Claw 拒绝）；对它立即运行时 Claw 在关联会话追加一轮，会话正忙则 Run 记为 `session_busy_error`。

### 3.5 创建

1. 校验功能权限与 Agent 使用权限。
2. 短事务内统计当前用户 `pending` 与 `active` 的任务归属数，达到上限（[M2](#m2)）返回 422 `SCHEDULE_QUOTA_EXCEEDED`；否则插入一条 `pending` 归属。统计与插入按用户串行，不持锁调用 Claw。
3. 调用 Claw 创建。
4. Claw 返回 201：把 scheduleId 写入该归属并置为 `active`，返回投影后的资源，HTTP 201。
5. Claw 明确失败（4xx/5xx 带错误码）：删除 `pending` 归属，把错误按 §3.9 返回。
6. 结果未知（超时、断连）：保留 `pending` 归属到过期，返回 503 `SCHEDULE_SERVICE_UNAVAILABLE`，提示用户刷新列表核对；Mate 不自动重试创建，Claw 也没有幂等键。
7. 步骤 4 写归属失败：调用 Claw 删除刚创建的任务作补偿；补偿失败则留给 §6 对账。

步骤 6、7 可能在 Claw 留下没有归属的任务。这类任务对用户不可见，到点运行时 §5.2 登记会拒绝，因此不会执行业务，最终由 §6 清理。

### 3.6 列表

Claw 首版不按用户过滤（Claw [D9](../../01-总体架构/08-CampusClaw定时任务/README.md#key-decisions)），Mate 自行过滤和分页：

1. 把 name、agentId、status 筛选原样转给 Claw，以 `limit=200` 从 page 1 拉到 `nextPage` 为 null。
2. 按 id 去重，按 §3.4 保留当前用户可见的任务。Claw 的顺序（updatedAt DESC、id ASC）在过滤后保持不变，不重新排序。
3. 按请求的 page/limit（与 Claw 相同：page 默认 1，limit 默认 50、范围 1～200）切页，返回 `{schedules, nextPage}`。

代价：每次列表读取全部任务，读取量随任务总数增长；跨页拉取期间有并发修改时可能重复或遗漏，与 Claw 普通翻页的限制相同。任务量增长后改为 Claw 按用户查询，见 Claw [T10](../../01-总体架构/08-CampusClaw定时任务/README.md#todo-t10)。

### 3.7 详情与写操作

详情、更新、删除、立即运行、暂停、取消暂停都先做 §3.4 的可见性检查，不可见直接返回 404，不调用 Claw。

- **可见性判断**：先查任务归属；没有归属时读取 Claw 详情，`chatId` 非空且该 Chat 属于当前用户才可见。
- **删除**：Claw 返回成功后删除任务归属；Claw 返回 404 时同样删除归属并返回 404。已生成的 Session、定时会话登记与 Chat 映射保留。
- **立即运行**：接口配置的任务会在这次请求中触发 Claw 回调 §5.2 登记，Mate 的管理请求不得持有会阻塞登记的锁。
- **结果未知**：写操作超时后返回 503，不自动重试；页面先读取详情核对，规则同 Claw [§4.5](../../01-总体架构/08-CampusClaw定时任务/README.md#reliable-write-flow)。

### 3.8 Run 列表与详情

| 请求 | 处理 |
|---|---|
| 带 scheduleId 的列表 | 先检查该任务可见，不可见返回空页；可见则把全部 query 原样转给 Claw 单次查询并投影 |
| 不带 scheduleId 的列表 | 拉取 Claw 全部页（其余筛选原样转发），只保留可见任务的 Run，再按 page/limit 切页；顺序保持 Claw 的 createdAt DESC、id DESC |
| 详情 | 读取 Claw Run，再检查其 scheduleId 对应任务可见；不可见返回 404 `SCHEDULE_RUN_NOT_FOUND` |

### 3.9 错误

| HTTP / resCode | 来源与含义 |
|---|---|
| 401 公司认证组件错误码 | 用户认证失败，复用公司组件 |
| 403 `SCHEDULE_READ_FORBIDDEN` / `SCHEDULE_MANAGE_FORBIDDEN` / `SCHEDULE_RUN_FORBIDDEN` | 用户缺少对应功能权限，Mate 判断 |
| 403 `SCHEDULE_AGENT_FORBIDDEN` | 用户不能使用请求的 Agent，Mate 判断 |
| 422 `SCHEDULE_QUOTA_EXCEEDED` | 当前用户任务数已达上限，Mate 判断 |
| 404 `SCHEDULE_NOT_FOUND` / `SCHEDULE_RUN_NOT_FOUND` | 不存在、已删除或不可见 |
| 400、404、409、422 的 Claw 业务错误码 | 字段校验、激活冲突、频率策略等，resCode 原样返回，文案由 Mate 按语言重新给出 |
| 503 `SCHEDULE_SERVICE_UNAVAILABLE` | Claw 不可达或结果未知；Claw 返回 401/403（服务认证或 Mate 传入的操作范围有误，属部署问题）也映射为 503，并记录告警 |
| 500 `SCHEDULE_*_FAILED` | Claw 内部失败，原样返回 |

错误不回显 Claw 内部地址、原始异常或 sessionId。

## 4. Mate 调用 Claw

| 项 | 规定 |
|---|---|
| 服务认证 | 每个请求附 Mate 的服务凭据，机制待定（[M5](#m5)、Claw T2） |
| 操作范围 | 随请求告诉 Claw 本次允许的操作（读取 / 管理 / 运行）和可选的 Agent 限制，Claw 映射为 `ScheduleAccessDTO`；携带方式随 T2 确定 |
| 不传内容 | 用户 ID、组织、访问令牌、可见集合；Claw 不需要也不保存 |
| 超时 | 读取可有界重试；写入不自动重试，按 §3.5、§3.7 处理结果未知 |

## 5. Mate 为 Claw 提供的接口

两个接口都只允许已认证的 Claw 服务调用（[M5](#m5)），不接收用户凭据；成功与错误都用 ResultBean，`Cache-Control: no-store`，支持 `Accept-Language` zh-CN / en-US，缺省 en-US，只影响错误文案。Claw 何时调用、失败后怎么处理见 Claw [§4.8](../../01-总体架构/08-CampusClaw定时任务/README.md#mate-calls)。

<a id="scheduled-access-token"></a>

### 5.1 获取统一账号 access-token

普通对话中，用户请求带着 `access-token` Header，Claw 调用 Mate 业务工具时原样透传（[M06 §7.1](../../01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md#credential-forwarding)）。定时任务到点运行时没有用户请求，也就没有用户的 access-token。2026-10-13 评审确定：所有定时任务统一使用 Mate 配置的同一个账号，Claw 运行时向 Mate 取这个账号的 access-token。

代价：用户创建任务后失去权限或离职，任务仍以统一账号的权限照常运行；统一账号能做什么，就是所有定时任务能做什么。用户权限只在配置任务时由 Mate 检查。

**请求**

```http
POST /mate-service/v1/runtime/scheduled-access-token
Accept-Language: zh-CN
```

| 项 | 规定 |
|---|---|
| 路径 | 草案路径；Claw 用 `campusclaw.schedule.access-token-path` 配置，服务地址沿用[共享连接目录](../02-CampusMate共享客户端配置/README.md)的 `campusmate.base-url` |
| 请求体与参数 | 无请求体，无 query 参数；不传用户、任务、Session 或 Agent 标识 |

**成功响应**：HTTP 200。

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

**错误**：只返回 resCode 与 resMsg，不回显 Token、内部地址或原始异常。

| HTTP / resCode | 含义 | zh-CN / en-US |
|---|---|---|
| 401 / SCHEDULED_TOKEN_AUTH_REQUIRED | 调用方不是获准的 Claw 服务 | 定时执行凭据认证失败。 / Scheduled execution token authentication is required. |
| 403 / SCHEDULED_TOKEN_FORBIDDEN | 统一账号未配置或已停用 | 定时执行账号不可用。 / Scheduled execution account is not available. |
| 500 / SCHEDULED_TOKEN_FAILED | 内部处理失败 | 获取定时执行凭据失败。 / Failed to obtain scheduled execution token. |
| 503 / SCHEDULED_TOKEN_UNAVAILABLE | 认证中心等依赖不可用 | 定时执行凭据服务暂不可用。 / Scheduled execution token service is temporarily unavailable. |

**Claw 如何使用**

| 项 | 规定 |
|---|---|
| 调用时机 | 定时触发的根执行及其 Subagent 中，模型一次返回的工具调用里至少一个需要凭据的工具通过参数校验和权限判断后、执行前取一次；只含无凭据工具、参数错误或需要人工确认时不取 |
| 使用范围 | 同一批工具调用共用；下一批重新取；不跨批次、不跨运行、不跨实例缓存 |
| 透传方式 | 只作为 `access-token` Header 传给 `POST /mate-service/v1/runtime/tools/{toolId}/execute`，不补 X-HW-ID、Authorization、X-HW-APPKEY |
| 失败 | 本批需要凭据的工具都不执行，按工具失败返回模型，模型可在下一批重试；不换其他账号或旧值；execute 已发出后不因刷新 Token 重放 |
| 保密 | 只在本批次内存中使用；不进日志、异常、模型提示、工具结果、Session 事件和数据库；对象 toString 脱敏 |
| 不调用的情况 | 用户在定时任务的 Session 里继续对话时，用该请求 Header 里的用户凭据（Claw [§3.11](../../01-总体架构/08-CampusClaw定时任务/README.md#session-credentials)）；未配置 CampusMate 地址时 Claw 关闭此接口 |

Claw 侧实现为 `MateAccessTokenClient`（实现 `ScheduleAccessTokenProvider`），已随 pi-mono-java PR #332 合并：只认 resCode 0 与非空 accessToken，构造只含 `access-token` 的 `MateCredentials` 快照。

**验收**

- 一批多个需要凭据的工具只取一次；两批之间重新取；Subagent 各自获取。
- 只含无凭据工具、参数错误或需要人工确认时不取。
- 取 Token 失败时本批工具不执行，不换账号重试。
- execute 的 Header 只含 `access-token`。
- Token 不进日志、事件和数据库；execute 结果未知不重放。
- 需要真实 Mate/Claw 联调和公司认证中心验证。

<a id="session-ownership"></a>

### 5.2 Session 归属登记与核对

接口配置的任务每次运行都新建 Session。Mate 需要知道这个 Session 属于哪个用户，之后用户读取、继续、停止或删除它时，Mate 才能据此授权再调用 Claw。2026-10-13 评审确定归属登记保留在 Mate，Claw 不保存用户或归属。对话中由 Cron 工具创建的任务在用户自己的会话里运行，归属随会话，不登记。

路径与报文为本文提出的草案（[M3](#m3)）。Claw 侧端口为 `ScheduleSessionRegistry` 的 `registerSession` 与 `findSessionRegistration`，HTTP 适配在 Mate 接口确定后实现。

**登记**

```http
POST /mate-service/v1/runtime/scheduled-sessions
Content-Type: application/json

{
  "sessionId": "session-3f0c9a1e5b7d4c2a8e6f1b0d9c8a7e65",
  "scheduleId": "schedule-927e03d2a4784f90a6238e790539c6e4",
  "runId": "run-4b1d2c3e5f60718293a4b5c6d7e8f901",
  "agentId": "agent-550e8400e29b41d4a716446655440000"
}
```

| 步骤 | 规则 |
|---|---|
| 1 | 按 scheduleId 查任务归属；没有 `active` 归属（任务已删除、无主或是对话中创建的任务）时拒绝 |
| 2 | sessionId 已登记：四个字段完全相同则直接返回原登记（幂等）；任一字段不同则拒绝 |
| 3 | 在同一事务中写定时会话登记，并为任务归属的 userId 建立 Chat → Session 映射，生成 chatId |
| 4 | 返回登记结果 |

成功 HTTP 200，result 返回与请求相同的四个字段，另附 chatId；Claw 只比较四个字段，忽略 chatId：

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "sessionId": "session-3f0c9a1e5b7d4c2a8e6f1b0d9c8a7e65",
    "scheduleId": "schedule-927e03d2a4784f90a6238e790539c6e4",
    "runId": "run-4b1d2c3e5f60718293a4b5c6d7e8f901",
    "agentId": "agent-550e8400e29b41d4a716446655440000",
    "chatId": "<chatId generated by Mate>"
  }
}
```

**只读核对**

```http
GET /mate-service/v1/runtime/scheduled-sessions/{sessionId}
```

已登记时 HTTP 200，result 与登记响应同形；未登记返回 404 `SCHEDULED_SESSION_NOT_FOUND`，Claw 视为空。只读，不创建记录。

**错误**

| HTTP / resCode | 含义 | Claw 处理 |
|---|---|---|
| 400 / SCHEDULED_SESSION_REQUEST_INVALID | 字段缺失或格式非法 | 明确拒绝，本次不受理 |
| 401 / SCHEDULED_SESSION_AUTH_REQUIRED | 调用方不是获准的 Claw 服务 | 明确拒绝，本次不受理 |
| 404 / SCHEDULED_SESSION_NOT_FOUND | 仅核对：未登记 | 继续核对直到准备期限 |
| 409 / SCHEDULED_SESSION_REJECTED | 任务没有有效归属，或 sessionId 已用不同字段登记 | 明确拒绝，Run 记为 `session_creation_rejected_error` |
| 500 / SCHEDULED_SESSION_FAILED | 内部处理失败 | 结果未知，转只读核对 |
| 503 / SCHEDULED_SESSION_UNAVAILABLE | 存储等依赖不可用 | 结果未知，转只读核对 |

**交接规则**

1. Claw 为同一次 Run 先固定 Session ID，之后准备和受理都复用这个 ID。
2. 在数据库事务外请求登记。重复登记相同的四个标识不得改变归属。
3. 登记成功后，Claw 在同库事务中创建 Session、首消息、根执行和 Run 关联；Mate 记录不加入这个事务。
4. 登记结果未知时只读核对，不重发登记，也不换新 ID。Mate 已登记而 Claw 回滚时，由 §6 对账确认 Session 从未提交后再清理登记；提交结果未知时保留待核对，不能凭超时删除。
5. 删除 Schedule/Run 不删除已建立的 Session 归属；Session 删除后由 Mate 关闭对应访问映射。

现状：pi-mono-java main `ead67eba` 中，`schedule/session/ScheduledSessionStarter.prepare/confirmRegistration` 已按第 1～4 步接线；默认实现 `schedule/mate/MateScheduleSessionRegistry` 一律返回服务不可用。因此在本接口上线或部署方替换实现之前，接口配置的任务到点后不会运行（Claw [§4.8.2](../../01-总体架构/08-CampusClaw定时任务/README.md#mate-calls)）。

**验收**

- 相同四字段重复登记返回同一 chatId，不新建 Chat。
- 无归属、已删除或对话中创建的任务登记被拒绝。
- 登记后用户能从 Chat 入口打开该会话；其他用户不能。
- 核对接口不创建记录。

## 6. 对账与清理

Mate 定期（建议每 10 分钟）运行一次对账，只处理 Mate 自己的记录和 Claw 中的无主任务：

| 对象 | 判断 | 处理 |
|---|---|---|
| 过期的 `pending` 任务归属 | 创建超过 10 分钟仍无 scheduleId | 删除，释放配额 |
| 无主任务 | Claw 列表中 `sessionId` 为 null、创建超过 10 分钟、没有任务归属 | 经 Claw DELETE 删除；它运行时登记会被拒绝，不会执行业务（[M4](#m4)） |
| 未提交的定时会话登记 | 登记超过准备期限，Claw 读取该 Session 明确返回不存在 | 删除登记与 Chat 映射；读取结果未知时保留，下轮再查 |

对账只读取 Claw 公开接口，不直接访问 Claw 数据库。无主任务的删除与普通删除一样保留已生成的 Session。

## 7. 实现与验收

| 范围 | 验收 |
|---|---|
| 管理接口 | 10 个操作与 Claw 一一对应；不可见任务一律 404；列表与 Run 列表只含可见记录；sessionId 不出现在任何响应中 |
| 创建 | 配额并发下不超限；Claw 失败删除 `pending` 归属；结果未知不自动重试 |
| 删除 | 删除后归属清除，已生成会话仍可从 Chat 打开 |
| 对话中创建的任务 | 关联 Chat 的所属用户可见、可管理，不能改 agentId |
| §5 接口 | 见 §5.1、§5.2 的验收 |
| 对账 | 无主任务不会运行，并在对账后被删除 |
| 联调 | 依赖服务认证（M5）确定；需真实 Mate/Claw 联调 |

## 8. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-10-19 | 新建 Mate 侧定时任务唯一设计：管理接口、调用 Claw 的处理、Session 归属登记接口草案与对账；并入原共享连接目录下的定时执行凭据草案。 |
