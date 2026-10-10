# Mate 定时执行上下文与凭据接口

版本：0.2.0；日期：2026-10-10；状态：接口草案，待实现。Mate作为可信接口定义、执行身份和凭据来源已确认；以下新增Mate路径及字段是配套设计，不冒充已发布接口。

[共享连接目录](README.md) · [定时任务主设计](../../01-总体架构/08-CampusClaw定时任务/README.md) · [执行与工程落地](../../01-总体架构/08-CampusClaw定时任务/execution.md) · [核验依据](../../01-总体架构/08-CampusClaw定时任务/source-evidence.md#schedule-engineering-evidence)

## 1. 业务问题与边界

每天08:00汇总园区告警时，Claw需要知道当前Agent可以调用哪些接口，以及该次业务调用可使用哪份凭据。Mate拥有接口定义、授权和凭据保管；Claw消费可信结果，不保存浏览器登录Token，也不根据prompt猜测调用地址或执行身份。Schedule继续只接受credentialIds，服务身份或用户委托的具体来源由Mate权威配置解析，不把二者的选择藏在Claw的默认账号中。

正常流程为：保存配置时核验可用Agent与凭据引用 → 到期后重新取得当前授权上下文并准备Agent → 接受新Session及根执行 → 模型选定工具后完成可信目标解析、参数校验和权限判断 → 从Mate解析该目标凭据 → 通过既有Mate execute执行 → 保存安全结果。凭据解析失败时不发业务请求，记录本次失败；实际execute结果未知时不自动再次发送。

接口发现、服务间认证、业务执行凭据是三个边界。发现请求可使用部署层服务身份，但不得复制用户或业务执行的凭据快照。Mate校验请求来自获准Claw服务，并验证其代表的管理/执行范围；authorizationRef只是指向权威授权记录的不可猜测标识，不是持有即授权的Token。公司服务认证SDK及可信操作者传递方式尚未核验，不能以任意JSON中的tenant/owner或自定义Header代替该接线。

## 2. 复用现有接口定义入口

| 操作 | 用途 | 本次源码证据与限制 |
|---|---|---|
| GET /mate-service/v1/agents/{agentId}/runtime | Agent配置、工具/Skill绑定和运行定义 | Mate示例已有Controller；当前缓存prepare不保证每次从远端刷新，沿现有发布快照语义 |
| GET /mate-service/v1/agents/{agentId} | 取得Agent直接绑定的工具标识 | 已有Controller与Claw消费者；仍须补可信范围授权，不因Agent存在就认为可执行 |
| GET /mate-service/v1/skill/query/{skillId} | 取得可信Skill工具绑定 | Claw已有客户端路径；本次Mate示例范围未发现对应Controller |
| POST /mate-service/v1/runtime/tools/query | 按已绑定toolIds取得完整定义及inputSchema | Claw客户端已有；本次Mate示例未发现Controller。保留现有消费者契约，不在定时设计中另建工具定义目录 |
| POST /mate-service/v1/runtime/tools/{toolId}/execute | 执行业务工具 | 只在目标、参数、权限均通过后调用；真实endpoint来自共享目录，不能用模型提供的URL替代 |

本次不把接口定义和秘密混成一个返回模型的工具清单。工具发现结果只供解析/模型理解，凭据只由可信执行Adapter使用。工具元数据的历史snake_case输入兼容属于既有客户端事实；下列新增接口使用lowerCamelCase，不全局改写旧协议。

## 3. 查询可用执行上下文

推荐新增 `POST /mate-service/v1/runtime/schedule-contexts/query`，用于保存时校验和每次触发时重新授权。该操作只读取当前配置/授权，不执行模型或业务；查询不新建委托、不扩大权限，也不返回秘密。

请求使用Schedule既有agentId及credentialIds，用户主体仅在 Mate 内解析和使用。管理校验由 Mate 在向 Claw 发起请求前完成；后台准备额外提交此前由Mate返回的authorizationRef，由Mate结合服务身份重新校验委托，不能仅凭Claw服务账号扩大权限。下面展示管理查询；后台查询可增加同名authorizationRef字符串，不能靠省略它回退到服务管理员身份：

```json
{
  "agentId": "agent-550e8400e29b41d4a716446655440000",
  "credentialIds": ["credential-alarm-example"]
}
```

HTTP200，ResultBean.result形状：

```json
{
  "agentId": "agent-550e8400e29b41d4a716446655440000",
  "authorizationRef": "grant-alarm-summary-example",
  "credentialBindings": [
    {
      "credentialId": "credential-alarm-example",
      "toolIds": ["tool-query-device-alarm"]
    }
  ],
  "validUntil": "2026-10-05T00:01:00Z"
}
```

authorizationRef 由 Mate 生成，Claw 仅用作查询当前授权的不透明关联引用，不解析、不自选，也不作为访问令牌。响应不返回用户范围、操作者或会话 owner，Claw 不持久化这些信息。validUntil 只限定同次准备结果有效期，不是永久授权；用户、资源归属与当前权限全部在 Mate 维护，见[全库职责边界](../../03-数据与存储/Claw数据库设计.md#mate-ownership)。

Mate必须验证当前调用者、Agent绑定、凭据引用及目标范围；对credentialIds检查原ID的唯一性，重复输入拒绝，最多16个，[]合法且不借用登录凭据。多个引用映射到同一工具且没有Mate明确的唯一选择时，返回409/CREDENTIAL_BINDING_CONFLICT，Claw不得按数组顺序覆盖Header。查询结果中的toolIds只限制凭据适用范围，不为Agent增加新的工具绑定。

<a id="session-ownership"></a>

### 3.1 会话归属登记与当前权限（待实现）

Mate 独立维护 Session ID 到用户、组织/管理范围及授权政策的关联；Schedule/Run 的管理归属也由 Mate 维护。Claw 不建对应身份表或列。下述是必须实现的交接顺序，具体登记/核对操作的路径与 VO 待实现时细化；现有 `schedule-contexts/query` 保持只读，不偷偷承担登记写入。

1. Claw 为同次 Run 固定拟建 Session ID；该 ID 由 Runtime 生成，后续准备和事务受理复用，不能在 `newSession` 再生成另一个 ID。
2. 数据库事务外，Claw 用服务身份、固定 Session/Run/Schedule/Agent ID 及原 authorizationRef 请求 Mate 登记。Mate 查询自己的授权记录、检查当前资格并持久保存会话归属；不接收 Claw 自报用户、租户或 owner。记录在 Claw 确认存在前仅为待核对关联，不对外承诺会话可访问。重复登记相同技术身份不得改绑归属。
3. 确认 Mate 登记成功且准备未过期后，Claw 在原同库事务创建 Session、首消息、根执行和 Run 关联，提交后才能启动；Mate 记录不加入该数据库事务，不引入跨库事务。关联或准备失败不启动模型、不执行业务。
4. Mate 登记响应未知时，按固定技术 ID 只读核对；仍未知则本次不受理，不重新分配 ID 或自动重放业务。Mate 已登记、Claw 回滚时，由对账确认会话从未提交后清理关联；提交结果未知时保留待核对，不能凭超时删除。Claw 已受理但回执丢失时，读取现有 Session/Run/根执行，不再次创建。
5. 用户读取、继续对话、停止和删除会话时，Mate 依据当前主体及会话关联逐次授权，再以可信服务请求调用 Claw。Claw 校验服务来源和获准操作/目标，执行自身状态检查；浏览器、模型提供的资源 ID 不是授权依据。列表先取 Mate 判定的可见集合再分页，空集合禁止退化为全库。
6. 删除 Schedule/Run 不删除已经建立的 Session 归属或撤销已受理执行的独立关联；后续凭据资格仍由 Mate 按当前政策检查。Session 删除确认后 Mate 关闭相应访问映射，未知结果先核对；公共 Chat 映射可以异步补齐，但不能替代上述归属登记。

Claw 的 Cron 工具只携带当前执行/Session、Agent 和目标资源 ID 向 Mate 请求操作授权，不捕获浏览器用户主体，不让 `sessionOwnerRef` 冒充 `operatorRef`，也不在通用 Runtime 中引入 ScheduleSubjectDTO。服务认证、授权结果的传递绑定与防越权检查仍须真实联调；缺失时拒绝，不能为了移除身份列而开放内部接口。Mate 用户审计独立记录，Claw 技术日志只关联资源与执行身份。

核验：PR #332 `e9d31e8888a81b7fe95071e705482bb16fa10476` 的 `schedule/mate/MateScheduleContextClient.query/resolveCredentials`、`runtimeapi/schedule/ScheduledRuntimeAdmissionService.newSession/encodeContext` 尚传递并保存归属；源码根为 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。本节职责修正、归属登记及服务授权接线均**待实现**；未读取 Mate 当前生产实现，不指定其物理表名，不宣称已有上述接口。

## 4. 解析本次工具执行凭据

推荐新增 `POST /mate-service/v1/runtime/credentials/resolve`，只允许已认证的Claw执行适配器调用。初次运行通过上下文查询验证引用；工具调用实际需要凭据时，按已准备的可信toolId解析。权限ASK或参数错误时不解析业务秘密、不执行工具。

```json
{
  "authorizationRef": "grant-alarm-summary-example",
  "agentId": "agent-550e8400e29b41d4a716446655440000",
  "scheduleId": "schedule-927e03d2a4784f90a6238e790539c6e4",
  "runId": "run-example",
  "toolId": "tool-query-device-alarm",
  "credentialIds": ["credential-alarm-example"]
}
```

scheduleId/runId只用于关联及审计，不能充当授权证明；Mate根据服务身份、authorizationRef、Agent和目标重新校验当前资格。执行开始后的Schedule/Run可以被删除，因此授权不能以它们仍可读取为前提；原根执行仅保留必要的资源关联与不透明授权引用；Mate 按独立执行/会话关联校验，Claw 不重建用户主体。操作不可被模型直接调用，不提供给浏览器或写入Schedule公开响应。

HTTP200，ResultBean.result形状：

```json
{
  "credentialId": "credential-alarm-example",
  "toolId": "tool-query-device-alarm",
  "expiresAt": "2026-10-05T00:05:00Z",
  "headers": {
    "X-HW-ID": "<value supplied by Mate>",
    "Authorization": "<value supplied by Mate>",
    "access-token": "<value supplied by Mate>"
  }
}
```

expiresAt表示本次授权凭据快照的使用截止时间，不要求底层静态APPKEY采用同一失效时间；Mate应给出有限有效期，Claw过期后不得继续使用该快照。

headers仅允许既有执行Adapter支持的X-HW-ID、Authorization、X-HW-APPKEY、access-token；实际选择和值由Mate权威提供，不由Claw拼接或回退认证模式。未提供的项省略。秘密只存在于本次受限内存快照，禁止日志、异常、追踪正文、模型提示、工具结果、Session事件、缓存文件和数据库留存；不能使用Lombok默认toString输出含secret的对象。所有成功/错误响应均no-store，客户端和网关禁用该操作的正文记录，链路使用受信TLS。

过期或轮转时可在尚未发起业务请求前重新解析同一授权和目标；这是凭据读取，不是重跑作业。解析失败结束本次相关执行，不静默换用其他credentialId、管理员或创建人的Token；已经发送execute后不得通过刷新凭据再自动重放同次业务。撤销最终由Mate执行端校验，缓存不得跨执行共享，已下发快照不承诺实时撤回。

凭据类型超出当前Header适配能力时明确拒绝，不因接口返回任意键就支持环境变量、Shell秘密或任意外部地址注入。credentialIds为空时不调用resolve；具体无凭据工具是否可执行由Mate判断，Claw不假造secret。

## 5. 共用HTTP、错误及Java边界

两个新增POST均接受application/json，无业务query，成功HTTP200和ResultBean；失败仅resCode/resMsg。Accept-Language支持zh-CN/en-US，缺省en-US，返回实际Content-Language；时间统一UTC秒级。不得添加If-Match、Idempotency-Key、ETag或同义body/query键。普通查询可只读重试，但本次运行准备超过期限后不重新调度。

| HTTP / resCode | 边界 | zh-CN / en-US |
|---|---|---|
| 400 / SCHEDULE_CONTEXT_REQUEST_INVALID | 请求缺失、类型/ID格式或重复引用不合法 | 定时执行上下文请求无效。 / Invalid scheduled execution context request. |
| 401 / EXECUTION_CONTEXT_AUTH_REQUIRED | 服务认证未通过 | 执行上下文认证失败。 / Execution context authentication is required. |
| 403 / EXECUTION_CONTEXT_FORBIDDEN | 无该操作功能或当前授权已撤销 | 无定时执行授权。 / Scheduled execution is not permitted. |
| 404 / EXECUTION_BINDING_NOT_FOUND | Agent、授权引用、工具或凭据不存在/不可见 | 执行绑定不可用。 / Execution binding is unavailable. |
| 409 / CREDENTIAL_BINDING_CONFLICT | 同目标多个凭据无法唯一匹配 | 执行凭据绑定冲突。 / Execution credential bindings conflict. |
| 409 / EXECUTION_CONTEXT_CHANGED | 当前Agent/工具或授权不再适用于准备结果 | 执行上下文已变化。 / Execution context has changed. |
| 500 / EXECUTION_CONTEXT_FAILED | 内部处理失败 | 获取执行上下文失败。 / Failed to obtain execution context. |
| 503 / EXECUTION_CONTEXT_UNAVAILABLE | 权威依赖不可用 | 执行上下文服务暂不可用。 / Execution context service is temporarily unavailable. |

不存在/不可见不披露记录、目标或凭据。所有错误不得回显Header、接口内部地址或原始异常。Claw将受理前明确错误映射到既有Run.error；受理后错误归原Session的真实结果，不能重写已成功的Run.sessionId。具体映射沿Claw接口，不把Mate信封原样返回模型。

Controller使用ScheduleContextQueryRequestVO/ResponseVO、ExecutionCredentialResolveRequestVO/ResponseVO，Service负责授权与VO/DTO转换，Mapper只使用DTO。请求边界采用Jakarta及嵌套@Valid，状态/唯一目标在Service复核。复用现有JDK HTTP客户端、Jackson、Spring、MyBatis3.0.4；不新增外部依赖。实际企业认证SDK、凭据保管服务和完整传递依赖尚未核验，实施必须接权威能力，不能以示例内存map替代生产凭据系统。

## 6. 配置、结构与验收

共享端点目录增加schedule-context-query-path和credential-resolve-path，仍只有一个campusmate.base-url。Claw新增MateScheduleContextClient及对应Adapter，实现ScheduleBindingResolver、ScheduleAuthorizationPort和ScheduleCredentialPort；定义与凭据从同一Mate权威取得但生命周期不同。全局结构复用[M10目标类图](../../01-总体架构/08-CampusClaw定时任务/README.md#10-全局目标类图与依赖)，不另建平行调度器。

验收覆盖：发现不复制业务凭据、保存不换取secret、越权和跨范围失败、重复/冲突引用、当前撤销、TTL过期、按可信toolId匹配、secret不落地、参数无效/ASK不发resolve或execute、execute不重放、删除Schedule后已受理Session仍可独立授权执行。Mate示例现有Controller不代表新增能力已完成；需要真实Mate/Claw联调和公司身份验证。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.2.0 | 2026-10-10 | 身份、资源归属和权限统一由 Mate 维护，明确会话登记与受理失败的交接边界。 |
| 0.1.0 | 2026-10-05 | 定义Mate上下文查询与按目标解析凭据草案，复用现有工具定义入口并区分服务认证与业务凭据。 |
