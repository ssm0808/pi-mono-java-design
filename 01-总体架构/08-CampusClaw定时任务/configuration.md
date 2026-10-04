# Claw 定时任务配置接口

[模块主设计](README.md) · [源码证据](source-evidence.md#configuration-evidence) · [与 Claude 的取舍](#claude-tradeoffs)

| 属性 | 值 |
|---|---|
| 版本 | 0.18.0 · 2026-10-04 |
| 状态 | 已确认能力与 proposed 接口形状分开记录；新接口待实现、尚未发布，整项操作尚未完成确认 |
| 本文权威范围 | Claw 的创建、列表、详情、部分更新、时间预览；不定义 Mate 接口或页面实现 |
| 产品范围 | 每次运行创建独立 Session，使用已绑定 Agent；不提供已有 Session 目标 |
| 源码基线 | Claw main `553dcd5e2ff682f9684810a043b442b37a02e54a`；2026-09-29 确认并 fetch，2026-09-30 重读该提交的调度范围；2026-10-04 重新 fetch 同提交并核验文件、Session 创建与凭据/模型链路、Cron、Session、ListEvents 读取及暂停状态；详见源码证据 §8.6～§8.10 |
| 对照 | Claude Managed Agents 公开 Beta HTTP API；2026-09-29 核对调度文档，2026-09-30 核对创建输入与 Cron 方言，2026-10-02 核对时间示例与精度边界；2026-10-04 重核名称、Cron 范围、执行目标、Files API、创建响应、metadata、Vault/凭据模型，以及 Deployment 详情/列表、资源类型、暂停原因和 Run 读取边界 |

## 1. 业务结果与接口边界

调用方配置“工作日 08:00 汇总园区设备告警”，向 Claw 提交 Agent、任务内容和时间规则。Claw 验证当前调用范围、绑定和规则，持久化后返回任务 ID、完整配置及计划时间摘要。之后可读取、修改该配置，不依赖调用方在线。

已确认的创建行为：schedule 可省略，省略时只保存、不立即执行；填写有效 schedule 后保存即登记自动计划，无需额外启用。试运行是独立的显式操作，可用于无 schedule 的配置；其 HTTP 路径、返回与运行细节待设计。每次运行均新建独立 Session，将配置中的一条 `user.message` 作为首条任务消息；绑定的 Agent 定义继续复用；Cron 沿用 Spring 六字段。

时间规则仅支持 `cron`，采用 Spring 六字段。Cron 的 timezone 可省略，默认 Asia/Shanghai 并保存、回显；不接收 at、every、intervalSeconds 或 startAt。schedule 仍可整体省略或为 null，表示仅手动运行。绝对时刻响应统一为 UTC、以 Z 结尾且不含小数秒，与 Session 和完整事件共同采用秒级目标。响应的非空 schedule 包含只读 lastRunAt/upcomingRunsAt，status 使用小写，JSON 不提供 revision，并支持可选 metadata；顶层只读 type 固定为 schedule，pausedReason 返回当前暂停原因或 null，见 [§4.1.1](#schedule-type-paused-reason)。Claw 通过 credentialIds 直接绑定一份或多份独立凭据，能力、引用层级与字段名已确认，详见 §4.2。名称上限为 256；时间类型范围与名称上限对齐 Claude，Cron 方言和时区默认值沿用 CampusClaw 已确认约束。

除明确标记已确认的字段外，下文状态模型、其余字段名、路径和错误码仍为 proposed。已确认新建状态为 `active`，创建处理器不直接调用模型或创建 Session；自动执行由后续调度触发。暂停、恢复、显式试运行、归档和运行记录的精确契约另行设计，不能把下列五个配置接口当作完整产品接口清单。

上述已确认创建语义不能被解释为“后端暂未接线也返回 active”。配置服务可以先开发和测试，但调度接线、执行身份及准入尚未交付时，不发布可自动运行的创建承诺；未满足依赖的请求返回服务不可用。保存成功也不保证后续业务一定成功，执行时仍须检查当前 Agent、授权和容量。

失败时，格式或规则无效不写入；版本冲突不覆盖；数据库失败不返回成功；响应丢失可按原请求键重试查询原提交结果，不创建第二份任务。Claw 不定义浏览器草稿、Mate 转发、公共 Chat 映射或 Agent 选择器。

## 2. Claw 接口清单

基础路径为 `/campusclaw-service/v1`。资源名沿用定时任务领域的 `schedules`；它保存完整任务配置，不是只有一个 Cron 字符串，也不宣称兼容 Claude Deployment 报文。

| 操作 | 方法与完整路径 | 成功结果 |
|---|---|---|
| 创建配置 | POST `/campusclaw-service/v1/schedules` | 201；完整资源、Location、ETag；要求 Idempotency-Key |
| 列表 | GET `/campusclaw-service/v1/schedules` | 200；当前可信范围内的分页结果，每项为与详情同形的完整资源 |
| 详情 | GET `/campusclaw-service/v1/schedules/{scheduleId}` | 200；完整资源及 ETag |
| 部分更新 | POST `/campusclaw-service/v1/schedules/{scheduleId}` | 200；完整资源及 ETag；要求 If-Match、Idempotency-Key |
| 时间预览 | POST `/campusclaw-service/v1/schedules/preview` | 200；规范规则、计算基准与最多五次未来计划时间；不保存 |

本切片不增加 options、Agent 目录或请求回执查询接口。能力和字段由本契约定义；同键写请求重放承担丢失响应的恢复。调用方须保存请求键、原请求正文和原 If-Match 才能重试，具体客户端存储方式不属于 Claw 契约。

Claw 必须在服务认证边界取得可信调用者和管理作用域，再按资源及 Agent 授权。scope、owner、授权结果与原始凭据不进入请求 JSON；可选凭据引用单独校验，不能把引用当作已授权结论；不能信任任意 Header 中的声明。相关公司适配器和可信范围解析尚未接线，是明确的实施缺口；本设计不因“内部 API”而省略鉴权，也不新增或推断 Mate 认证协议。到期业务执行身份与配置管理身份分别处理，不能保存请求 Token 供将来运行。

所有普通成功使用 `resCode/resMsg/result`；失败仅返回 `resCode/resMsg`，保留真实 HTTP 状态。JSON 为 lowerCamelCase。配置响应为 `Cache-Control: no-store`；语言支持 zh-CN/en-US，缺省或不支持时回退 zh-CN，返回 Content-Language。scheduleId 由服务端生成、大小写敏感且不复用；示例中的 UUID 后缀不构成客户端可构造 ID 的许可。

## 3. 配置字段与时间规则

| 字段 | 创建与更新约束 |
|---|---|
| name | 创建必填；去首尾空白后 1～256 个 Java 字符；允许重名，不作为身份 |
| description | 可选，最多 2048 个 Java 字符；创建省略默认 null，更新省略保持，空白或显式 null 清除；不附加到模型输入 |
| agentId | 创建必填；复用 `ClawConstants.Agent.ID_REGEX`，验证存在、可用和当前调用者的配置资格；只绑定 Agent 身份，不保证固定历史版本 |
| message | 创建必填；一条 `type:"user.message"`，content 复用现有文本与 fileId 引用格式；引用不等于上传或文件内容可读，见 §3.6；外层字段名 message 为候选，附件长期保留与到期访问规则待确定；不开放 system.message 或 user.define_outcome |
| schedule | 可选；创建省略默认 null，更新省略保持；非空时只允许下表的 cron 对象，更新时整体替换 |
| metadata | 可选字符串键值对象；创建省略为 {}；建议沿用 Claude 最多 16 对、键最多 64、值最多 512 个字符；不传给模型、不作为授权依据，详见 §3.7 |
| credentialIds | 已确认 string[]，直接绑定独立受管凭据；建议可选、创建省略为 []，响应同名回显；更新省略保持、数组整体替换、[] 清空；原始秘密不进入配置请求；数量、ID 格式及冲突策略待定，见 §4.2 |
| type | 资源顶层只读字段，固定为 schedule；创建、详情、列表元素和更新响应均返回；区别于 schedule.type 和 message.type，见 §4.1.1 |
| pausedReason | 只读的当前暂停原因，始终返回 object 或 null；创建为 null，人工暂停为 manual，错误自动暂停为 error，恢复后清空；精确边界见 §4.1.1 |
| status/id/createdAt/updatedAt | 全部只读；新建 active；时间为 UTC ISO 8601，秒级且无小数；status 候选集合为 active/paused/archived，archived 不可修改；小写及新建 active 已确认，归档模型尚待生命周期审阅 |
| schedule.lastRunAt / schedule.upcomingRunsAt | 仅响应使用；最近自动运行实际开始时间及最多五个未来计划时刻，见 §3.3；创建、更新和预览请求传入时拒绝 |
| revision | 不属于公共请求或响应字段；内部配置代次只用于持久化和调度竞态检查，不透出 JSON |

以下为候选请求形状；名称上限 256、仅 Cron、Spring 六字段、默认上海时区和秒级 UTC 响应规则已确认；其他未明确确认的约束仍为 proposed。

| schedule.type | 完整输入 | 语义与确认边界 |
|---|---|---|
| cron | type、expression、timezone（可选） | type 固定为 cron；Spring 六字段 `second minute hour day-of-month month day-of-week`；timezone 使用 IANA 名称，省略默认 Asia/Shanghai，保存并回显有效值；拒绝五字段，不自动补秒 |

名称允许重名，不承载资源身份。256 的上限与 Claude 的 maxLength 对齐；不另设缺少业务依据的 128 限制。当前长度校验沿用 Java 字符计数；本次未验证两端对补充 Unicode 字符的计数是否完全一致。

<a id="spring-cron-contract"></a>

### 3.1. Spring 六字段的含义

对外 Cron 契约采用六个以空格分隔的字段，不自动识别或转换五字段 POSIX，也不接收年字段。秒字段可指定计划触发秒，但不承诺任务在该秒准时开始；允许的最小执行频率仍须由产品策略确定。

| 顺序 | 字段 | 范围与含义 |
|---|---|---|
| 1 | second | 秒，0～59 |
| 2 | minute | 分，0～59 |
| 3 | hour | 时，0～23 |
| 4 | day-of-month | 月内日期，1～31 |
| 5 | month | 月，1～12 或 JAN～DEC |
| 6 | day-of-week | 星期，0～7 或 SUN～SAT；0 与 7 都是周日 |

| 示例 expression | 在 Asia/Shanghai 下的含义 |
|---|---|
| `0 0 8 * * MON-FRI` | 每周一至周五 08:00:00；不自动排除法定节假日 |
| `30 0 8 * * *` | 每天 08:00:30 |
| `*/10 * * * * *` | 每分钟第 0、10、20、30、40、50 秒；仅说明表达式含义，不代表产品已允许该频率 |

各字段支持 Spring 的列表、范围、步长及其日期扩展，具体匹配以项目使用的 Spring `CronExpression` 为准；宏快捷写法是否开放另行确定，不能仅因解析器接受就纳入本 API。月内日期与星期同时受限时要求同时匹配：`0 0 8 1 * MON` 表示“每月 1 日且为周一的 08:00”，不能按 POSIX 常见的日期或星期匹配方式解读。时区由显式 timezone 或 §3.4 的服务端默认值确定并保存，避免运行节点配置改变计划含义。[官方语法](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/scheduling/support/CronExpression.html)

### 3.2. 仅 Cron 的范围与代价

非空 schedule 只接受 `type:"cron"`。创建、更新和预览使用同一限制；其他类型及 at、intervalSeconds、startAt 等额外字段均拒绝，不尝试转换成 Cron。仅手动运行继续用 schedule 省略或 null 表达，即时测试通过独立运行操作完成。

这一范围与 Claude Deployment 的仅 Cron 取舍一致，减少一次性任务耗尽、间隔起点和更新重置等契约。代价是本接口不支持未来指定时刻只执行一次，也不支持从任意起点连续按固定秒数重复。`0 0 8 1 10 *` 会每年匹配 10 月 1 日，不是指定某年的一次性任务；`0 */7 * * * *` 每小时重新匹配，不能冒充严格每隔 7 分钟。

旧 CronTool/CronSchedule 中 At/Every 的实现保留为既有源码事实；新配置 HTTP 不暴露这些类型。旧任务不自动迁移成 Cron，也不直接删除旧类型及其调用方；旧入口的兼容与迁移由独立切片处理。收敛时间类型不改变 Spring 六字段、默认上海时区、每次新建 Session 或显式试运行的既有决定。

### 3.3. 计划时间与最近运行摘要

创建、详情、更新及列表元素中的非空 schedule 包含 type、expression、有效 timezone，以及只读 lastRunAt/upcomingRunsAt。两个只读字段已纳入响应范围；以下具体运行语义为建议契约，与运行接口一起验收。

| 响应字段 | 建议语义 |
|---|---|
| lastRunAt | 最近一次自动运行的实际开始时间，首次创建为 null；未启动的失败/跳过不更新，手动试跑不更新。不是计划时刻、结束时间或成功标志；自动运行开始后再失败仍保留该开始时间 |
| upcomingRunsAt | 响应计算时刻之后、按升序排列的最多五个 Cron 计划时刻；active/paused 均按规则计算，paused 的值仅表示恢复运行时对应规则的计划，不代表已经登记触发；archived 返回 [] |

创建先取一次服务端计算时刻完成规则校验，并把该次 upcomingRunsAt、lastRunAt:null 连同成功响应保存为幂等快照。详情/更新在各自一致读写快照中重新计算，数组按时间推进；同键重放始终返回原数组，不按重试时间重算。所有时刻为 UTC 秒级 Z 格式。实际受理/启动可能晚于计划时刻，跳过和失败通过 Run 记录说明，不以数组保证执行。

lastRunAt 归属于整个任务，修改 Cron 或消息不清除历史；规则为 null 时整个 schedule 返回 null，不另造空规则对象。若之后重新配置 Cron，回显任务已有的最近自动开始时间。运行专题还需确定可信 startedAt 事件的持久化边界及摘要对账；字段存在不等于该链路已经实现。Claude 同字段说明同时提到实际开始与“Null until one completes”，本产品明确采用实际开始语义，不据文档推断其内部写入点。

独立预览用于保存前检查：输入 `{ "schedule": { ... } }`，schedule 必须非空且只含可写规则；返回 result `{schedule, computedAt, upcomingRunsAt}`。其中 schedule 只回显规范规则，不带任务运行摘要；computedAt 是本次服务端取时，upcomingRunsAt 严格晚于它且最多五项。预览不关联已保存任务，因此没有 lastRunAt。无未来匹配的 Cron 返回 `SCHEDULE_RULE_INVALID`，不改动已保存资源。

预览与写入复用同一时间策略，保存重新校验，不把预览当作准入凭证。频率与配额由部署策略约束；超过范围返回稳定的策略错误，策略本身未配置则服务不可用。DST 与解析库版本边界必须验收，本接口不复制 Claude 的 jitter 承诺。动态时间摘要与 HTTP 条件更新的关系见 §5。

### 3.4. 时区选择与确认边界

Cron 的 timezone 可省略，服务端默认使用 Asia/Shanghai；显式提供时允许其他合法 IANA 时区。保存前确定具体时区并随规则持久化，创建、详情和更新响应均回显有效值；计划计算使用已保存值，不取运行节点默认时区。创建和整体替换 Cron 规则使用同一默认处理；更新省略整个 schedule 则保留原规则及其时区。默认处理位于 Service，显式 null、空字符串和时区别名的处理仍待确定。

例如，调用方省略时区的 schedule 片段为：

```json
{ "type": "cron", "expression": "0 0 8 * * MON-FRI" }
```

保存并回显的 schedule 片段为：

```json
{ "type": "cron", "expression": "0 0 8 * * MON-FRI", "timezone": "Asia/Shanghai" }
```

定时任务绝对时刻响应统一为 UTC、以 Z 结尾且不含小数秒，适用于 createdAt/updatedAt 及预览、最近运行和未来计划时间字段。Session 与完整事件同步采用这一目标；[秒级时间一致性](../01-CampusClaw多Agent运行时/time-contract.md)维护写入规范化、存储与回显要求。Cron 的 timezone 仍回显已保存的 IANA 名称。当前创建/更新请求不接收绝对计划时间字段；只读时间摘要不作为请求输入。

服务端生成记录时间先转 UTC 并截断到秒再保存和响应，Cron 计算得到的计划时间按秒表示。秒级表示不承诺准时启动。[既有实现证据](source-evidence.md#runtime-time-format-evidence)保留当前毫秒实现与目标差距，不能把目标规则表述为现状。

[2026-09-30 时区专项的历史证据](source-evidence.md#timezone-evidence)区分 DSH Cron 必填时区、GitHub Actions 可选时区且默认 UTC、pi 无日历时区字段及 Codex 尚未核实的默认来源；不存在据此可推导的统一行业默认值。默认上海是 CampusClaw 已确认的产品约束，方便主要园区场景配置；代价是调用方省略字段时采用了产品预设，必须通过保存和回显使该选择可见。

### 3.5. 每次运行创建独立 Session

每次自动触发或显式手动运行均使用配置绑定的 agentId，新建一个独立 Session 并提交配置消息。Agent 是可复用定义，Session 是一次会话容器；运行时可据该定义创建执行对象，但不创建新的 Agent 定义资源或返回新的 agentId。一次运行使用一个新 Session，不自动继承上次运行的聊天历史；Agent 配置、受管资源及外部业务数据不因此自动隔离或清空。

创建、更新请求均不提供 target 或 sessionId，响应也不回显恒定目标；这些字段按未知字段拒绝。Schedule 配置没有待绑定的 Session，创建保存不启动 Session；真正运行后的 sessionId/rootExecutionId 归 Run 关联。创建请求的幂等重放和同一 Run 的重复受理必须返回原记录，不因“每次新建”生成重复会话。

例如“工作日 08:00 汇总园区设备告警”，周一、周二分别产生不同 Session；需要昨日结论时通过已授权的业务数据或资源获取。本能力不提供在指定旧聊天中持续追加输入。每个 Run 仍须固定本次消息和根执行，后续人工继续该结果会话不会改写原 Run 的结论。

该选择对齐 Claude Deployment 的新 Session 行为，减少原会话授权、模式、忙闲状态及多任务竞争的契约；代价是不能自动延续原会话上下文。其他基线保留各自的历史证据，不作为本产品必须提供目标选择的理由。Agent 版本固定是另一项能力，不能从“新 Session”推导 Claw 已具备 Claude 的版本 pin。

### 3.6. 文件引用与上传边界

当前 Claw 已实现的普通 Session 消息块是 `{"type":"file","fileId":"0123456789abcdef0123456789abcdef"}`：ID 为 32 位十六进制，最多四个、不重复；文本块如有必须位于第一项。它能保存引用并在完整事件中回显，不接收 multipart 文件字节。

2026-10-04 在 Java main `553dcd5e2ff682f9684810a043b442b37a02e54a` 的 modules、campusclaw、frontend 及 Runtime/ControlPlane Controller 范围未发现 Claw 上传路由；前端附件按钮明确禁用。RuntimeEntryCodec 仅把 fileId 转成 `[File IDs]` 文本交给模型，未下载、解析或验证文件可读性；Read 工具按工作区 path 读取文件，不能自动充当 fileId 解析器。精确路径见[文件证据](source-evidence.md#target-file-evidence)。

既有 [M09 附件设计](../../02-服务与接口/01-CampusMate附件服务/README.md)把上传、扫描与文件存储归于 mate-service，把 Claw 定位为引用及内容消费者；该设计标记待实现，不能当作当前上传实现。其附件不可变绑定单个 Session、内部 resolve 拒绝跨 Session，且文件 ID 格式仍为 file_<26 alnum>，与当前 Runtime 的 32 位十六进制引用未对齐。

定时消息复用 fileId 形状是待实现目标；旧 CronPayload 只有纯文本。“每次新建 Session 且重复使用同一巡检标准附件”无法直接套用上述 Session 绑定，需在 M09/M10 衔接时明确授权引用或复制机制、ID 契约、保存期限、执行时读取及删除后的失败行为；此处不擅自选择其中一种。外部 Mate/附件服务实现本次未核验。Claude 的独立 Files API 和 Deployment resources 文件挂载是对照能力，不能视作 Claw 已有接口。

### 3.7. metadata 的用途与范围

metadata 是可选的业务关联信息，例如 `{ "parkCode": "park-east", "purpose": "alarm-summary" }`。支持该字段已确认；建议沿用 Claude 的字符串 map 与 16/64/512 限制，长度沿用本项目 Java 字符计数，不声称补充 Unicode 字符与 Claude 的计数完全一致。键建议非空，值允许空字符串；创建及保存值拒绝 null、数值、布尔值、数组和嵌套对象，不自动转换成字符串。

创建省略返回 {}。更新建议沿用 Claude 的逐 key patch：字符串新增或覆盖，key 的值为 null 时删除该 key，省略 key 保留；{} 不做修改，需清空时逐 key 删除。合并后的存储对象仍满足 16/64/512 限制且不含 null；顶层 metadata:null 建议拒绝。这些更新细节仍为 proposed。metadata 不进入 user.message、系统提示或工具参数，也不自动继承为 Session 元数据；不得用其中的 tenantId、owner 或凭据引用代替可信授权。不得保存 Token、密码或其他 secret，敏感凭据应采用独立保管与授权引用。首版不承诺按 metadata 过滤或索引。

## 4. 创建、读取与更新报文

以下创建主体包含已确认的 credentialIds 字段；默认值和校验细节继续按 §4.2 审阅，整项操作尚未冻结。创建 `POST /campusclaw-service/v1/schedules`，携带 `Idempotency-Key: 0ca92847-fb58-4a9a-900f-8a7b26a71496`：

```json
{
  "name": "工作日园区告警汇总",
  "agentId": "agent-550e8400e29b41d4a716446655440000",
  "message": {
    "type": "user.message",
    "content": [
      {
        "type": "text",
        "text": "汇总园区过去24小时的设备告警，并标出需要跟进的工单。"
      }
    ]
  },
  "schedule": {
    "type": "cron",
    "expression": "0 0 8 * * MON-FRI",
    "timezone": "Asia/Shanghai"
  },
  "metadata": {
    "parkCode": "park-east",
    "purpose": "alarm-summary"
  },
  "credentialIds": [
    "credential-alarm-example",
    "credential-workorder-example"
  ]
}
```

响应 HTTP 201，`Location: /campusclaw-service/v1/schedules/schedule-927e03d2a4784f90a6238e790539c6e4`，`ETag: "d7ac4f82b9034b5ca46bb81705a63f29"`：

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "type": "schedule",
    "id": "schedule-927e03d2a4784f90a6238e790539c6e4",
    "name": "工作日园区告警汇总",
    "description": null,
    "agentId": "agent-550e8400e29b41d4a716446655440000",
    "message": {
      "type": "user.message",
      "content": [
        {
          "type": "text",
          "text": "汇总园区过去24小时的设备告警，并标出需要跟进的工单。"
        }
      ]
    },
    "schedule": {
      "type": "cron",
      "expression": "0 0 8 * * MON-FRI",
      "timezone": "Asia/Shanghai",
      "lastRunAt": null,
      "upcomingRunsAt": [
        "2026-10-05T00:00:00Z",
        "2026-10-06T00:00:00Z",
        "2026-10-07T00:00:00Z",
        "2026-10-08T00:00:00Z",
        "2026-10-09T00:00:00Z"
      ]
    },
    "status": "active",
    "pausedReason": null,
    "createdAt": "2026-10-04T02:00:00Z",
    "updatedAt": "2026-10-04T02:00:00Z",
    "metadata": {
      "parkCode": "park-east",
      "purpose": "alarm-summary"
    },
    "credentialIds": [
      "credential-alarm-example",
      "credential-workorder-example"
    ]
  }
}
```

GET 详情返回同形完整资源及当前 ETag；列表每项同样返回完整资源，此点已确认。分页、筛选及其他候选见[读取详情](#get-schedule-review)与[读取列表](#list-schedules-review)。读取操作尚未整体确认，不改变上述创建字段的确认范围。

更新到工作日 09:00，`POST /campusclaw-service/v1/schedules/{scheduleId}`，携带 `If-Match: "d7ac4f82b9034b5ca46bb81705a63f29"` 和新的 Idempotency-Key：

```json
{
  "schedule": {
    "type": "cron",
    "expression": "0 0 9 * * MON-FRI",
    "timezone": "Asia/Shanghai"
  }
}
```

成功返回完整资源及新 ETag。更新至少提供 name/description/agentId/message/schedule/metadata/credentialIds 中一个字段；省略保持，description/schedule 显式 null 清除，其他所列顶层字段的 null 拒绝。嵌套 timezone 的 null 语义仍待确定。message/schedule/credentialIds 整体替换，metadata 依 §3.7 逐 key 更新，`{"schedule":{"timezone":"UTC"}}` 不合法。先与已保存配置合并，再校验最终整体，任一错误则全部不改。拒绝未知字段、错误 JSON 类型和只读字段；同值更新不增内部配置代次、不改 updatedAt，但记录请求结果；只读时间摘要仍按本次快照生成。

更新保持 active/paused 状态及当前 pausedReason；修复消息或凭据引用不隐含恢复，恢复由独立生命周期操作完成。清除 schedule 只移除未来自动计划，不取消在途 Session。变更后的内部配置代次供后续受理使用，不修改已接受输入；仅改 message 等字段不重置时间规则。更新与到期受理须有明确的事务先后关系，具体 worker 机制不在此定义。

详情包含 §3.3 的只读时间摘要，不返回内部 nextFireAt 调度游标、配置 revision 或目录展示信息。ETag 对应完整资源表示，包括动态时间摘要与暂停原因；不能只按内部配置代次生成。updatedAt 表示配置或生命周期最近修改时间，普通运行摘要变化及重新计算预览不改该时间。内部配置代次仍随配置或生命周期修改递增，供调度竞态检查使用；普通运行进展不递增它。

<a id="creation-response-review"></a>

### 4.1. 创建成功响应逐项对齐（候选）

创建 `POST /campusclaw-service/v1/schedules` 解决的是保存可运行配置。上述 JSON 包含已确认的资源 type、pausedReason、只读时间字段、小写 active、不提供 revision、可选 metadata 和直接凭据引用 credentialIds；201、精确响应其余字段、metadata 限制与整项操作仍待确认。新接口待实现。

| 项目 | 创建时的值及含义 | 与 Claude 的对应或差异 |
|---|---|---|
| HTTP / Location | 201 Created；Location 指向新配置详情 | Claude 创建参考页为 200；Claw 沿用现有 Session 创建风格 |
| ETag | 服务端生成的不透明强标签，调用方原样用于 If-Match；示例不是可推导的版本号 | Claw 候选并发规则，既有 Session create 未提供此 Header；动态摘要变化也可使其失效 |
| resCode/resMsg/result | 成功有三字段；resCode 为字符串 0，result 为完整资源 | 公司 ResultBean；Claude 直接返回资源 |
| id | 定时任务配置 ID | 对应 Deployment id，不是 agentId/sessionId/runId |
| type | 固定为 schedule，标识返回的是任务配置资源 | 对应 Claude 的 type:deployment；采用 Claw 自身资源名称 |
| name/description | 规范化名称；未提供 description 返回 null | 对应同名字段；description 不参与模型输入 |
| agentId | 绑定的 Agent ID | Claude 返回 id/version/type 对象；Claw 无历史版本绑定，不伪造 agentVersion |
| message | 保存的一条 user.message | Claude initial_events 为数组；Claw 仅一条用户消息 |
| schedule | 规则及 lastRunAt/upcomingRunsAt；未配置则 null | 对应 Claude schedule；Claw 六字段且默认上海时区 |
| schedule.lastRunAt | 创建为 null；建议表示最近自动运行的实际开始 | 对应 last_run_at；手动试跑不更新，不当作业务成功 |
| schedule.upcomingRunsAt | 最多五个未来计划时刻 | 对应 upcoming_runs_at；计划值不保证实际启动 |
| status | 创建 active；active 且 schedule 非空才有自动计划 | 与 Claude active 拼写一致；归档模型仍是待审阅的独立差异 |
| pausedReason | 创建为 null；表示当前暂停原因，不是最近运行错误 | 对应 paused_reason，采用 lowerCamelCase；manual/error 与恢复清空语义对齐 |
| metadata | 原样保存的字符串对象；省略默认 {} | 对应同名字段；建议沿用 16/64/512 限制，不传模型 |
| credentialIds | 引用独立凭据的 ID 数组，响应不含秘密；建议省略时回显 [] | Claude vault_ids 引用集合；Claw 直接选择独立凭据，不新增 Vault 分组层 |
| createdAt/updatedAt | 新建相等；UTC 秒级无小数 | 对应 created_at/updated_at；Claw 精度是产品规则 |

revision 不进入创建、详情、列表或更新响应。它是内部实现可用的配置代次，与用户任务内容、Agent 版本、执行次数均无关，不需要调用方感知。创建也不返回 sessionId、runId、executionId、模型答案或业务完成状态。

省略 schedule 的创建响应仍含 `type:"schedule"`、`schedule:null`、`status:"active"`、`pausedReason:null`：可以手动运行，但没有自动计划，不隐含立即试跑。提供有效 schedule 后无需再显式启用；状态与时间摘要是服务端保存的响应快照，不是客户端收包时的实况。幂等重放返回原成功快照，需要当前计划、状态和运行时间时再 GET。

小写已确认；完整生命周期尚未确认。当前保留候选 active/paused/archived，Claude 则为 active/paused 加 archived_at，归档后的 status 仍可为 active。不能把改为小写说成归档模型已完全对齐。environment_id/resources/budget 仍不引入；凭据引用单独按 §4.2 讨论，不能把 metadata 当成凭据或权限入口。

<a id="schedule-type-paused-reason"></a>

### 4.1.1. 资源类型与当前暂停原因

园区运营人员发现告警汇总没有继续执行，需要区分人工暂停与错误导致的自动暂停。pausedReason 随完整资源返回当前原因，历史运行错误继续由 Run 记录。顶层 type 则使调用方脱离请求路径仍能辨认这是 Schedule 配置。两字段已确认，待实现。

type 始终为字符串 schedule，创建、详情、列表元素和更新使用同一规则；无 Cron 计划时也不改变。它与 schedule.type 的 cron、message.type 的 user.message 分属不同层，不增加时间规则或消息类型。

| 当前状态或动作 | pausedReason 的响应语义 |
|---|---|
| 新建或处于 active | null；字段不能省略 |
| 人工暂停 | 非空对象，type 为 manual |
| 错误导致自动暂停 | 非空对象，type 为 error，包含安全 error 对象；其精确 Schema、错误类型及与 Run 的映射另行对齐 |
| 恢复为 active | 清空为 null；不删除历史 Run 或暂停审计 |
| 修改已暂停配置 | 保持当前原因；修复配置后仍需显式恢复 |

人工暂停后的**资源片段**如下，其余字段继续按完整资源返回：

```json
{
  "type": "schedule",
  "status": "paused",
  "pausedReason": { "type": "manual" }
}
```

在 active/paused 范围内，pausedReason 非空当且仅当 status 为 paused；不能返回 active 与 manual/error 原因的组合。归档模型及归档后的原因处理仍待生命周期审阅，增加这两个字段不代表整个生命周期已确认。自动暂停的触发条件也由运行契约确定，不把每次失败、限流或业务失败都等价为暂停；Claw 尚无对应 Environment/Vault 资源，不照搬 Claude 的相关错误枚举。

两个字段由服务端生成；创建和配置更新若传入顶层 type 或 pausedReason，即使值看似正确，也按只读字段返回 400 `SCHEDULE_REQUEST_INVALID`。合法的 message.type 和 schedule.type 仍是原有输入。暂停/恢复操作负责生成原因，调用方不能通过配置更新伪造或清空它。

status 与 pausedReason 在同一持久化边界原子修改，并按生命周期变更更新 updatedAt 和内部配置代次；读取只能观察一致组合。原因属于 Schedule 当前状态，不能由 GET 临时推断最近一个 Run 的错误。错误投影不暴露原始异常、堆栈、凭据或敏感业务参数。强 ETag 覆盖原因；写请求幂等重放仍返回原状态与原因快照，需要当前值时 GET。

Claude 的资源 type 固定为 deployment，Claw 改为 schedule 以匹配自身领域；paused_reason 对应 pausedReason，保留 manual/error 和恢复清空的语义。依据为 2026-10-04 重读的[Deployment 模型](https://platform.claude.com/docs/en/api/http/beta/deployments)与[调度指南](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)。创建参考页的 active 配 manual 示例与模型约束冲突，不作为本设计依据。公开证据及现有 Session VO/Cron 状态差距见[专项核验](source-evidence.md#schedule-type-pause-reason-evidence)。

<a id="credential-reference-proposal"></a>

### 4.2. credentialIds 直接绑定凭据

业务问题是“每天 08:00 自动读取园区告警时，凭什么身份调用业务服务”。创建任务的登录凭据可能早已过期；管理任务的权限也不自动等于调用告警、门禁或工单接口的权限。模型服务认证是第三个独立边界。

Claude 的 Deployment 可选 vault_ids 引用已有 Vault（最多 50）；Vault 的 Credential 由独立接口创建和更新。敏感 token/secret 只写不回读。MCP 凭据按 mcp_server_url 匹配注入；环境变量凭据在 sandbox 中表现为不透明占位符，在受控出站边界替换。Vault 是 workspace 范围，不自动提供企业用户/园区级业务授权。公开事实、轮转和自托管限制见[凭据证据](source-evidence.md#creation-metadata-credentials-evidence)。

Claw 使用 credentialIds 直接引用一份或多份独立受管凭据；能力、资源层级及字段名已确认，功能待实现。每个 ID 指向完整的逻辑凭据或连接身份，例如园区告警服务访问身份，内部可以包含多个认证值，不是一项对应一个 Header。真实秘密由独立权威系统保管，任务保存引用，执行时重新授权并由可信 Adapter 使用。

| 产品 | 资源关系 | 收益与代价 |
|---|---|---|
| Claude | Deployment → vault_ids → Vault → Credential | 凭据集合便于成组授权及复用，同时需要集合和成员变更规则 |
| CampusClaw | Schedule → credentialIds → Credential | 任务明确选择可用凭据，首版不增加 Vault 集合层；多个任务共用一组凭据时需分别维护引用列表 |

创建请求和 result 响应采用同名字段。以下为字段片段；本文 credential-* 示例仅说明引用，不定义最终 ID 格式：

```json
{ "credentialIds": ["credential-alarm-example", "credential-workorder-example"] }
```

建议字段可选、创建省略归一化为 []；响应只回显引用 ID，不回显 secret。[] 表示没有显式绑定业务凭据，不表示借用创建请求的 Token。更新省略保持、[] 清空、非空数组整体替换，显式 null 建议拒绝；这些默认和更新细节仍为 proposed。创建和每次执行均需校验当前引用资格；保存成功不等于下游业务已经认证成功。原 ID 下的凭据轮转不要求任务重新保存 secret，具体解析/撤销时效由凭据权威契约确定。

不开放 vaultIds、credentialRefs 或原始 credentials 对象作为别名；这些值按未知字段拒绝。凭据保管方、服务身份或用户委托、ID 格式、数量限制、重复 ID 与同目标冲突规则仍待确定。普通 Session 是否同时增加同名字段，另按其接口范围确定。

现有一次执行只有一份 MateCredentials 快照，不能把多 ID 列表直接转换为 Header 合并或最后一个覆盖。多凭据引用需要按受信业务目标匹配凭据，并定义冲突规则；这是待实现增量，不由数组字段自动提供。配置修改影响后续运行准备；已受理运行继续固定原配置引用快照，凭据本身的轮转/撤销与配置引用列表更新分别处理。

正常流程建议为：管理方在独立凭据系统完成授权 → 保存任务时校验其可引用资格，仅存引用 → 到期时宿主复核主体、租户、Agent 和业务目标，取得当次可用凭据 → 每次新 Session 使用当次凭据快照 → 工具完成可信目标解析、参数校验及权限判断后，由可信执行 Adapter 注入并调用业务服务 → 只返回安全业务结果。secret 不进入模型提示、metadata、Schedule/Run 记录或公共响应，准备和换取凭据不提前执行业务。

凭据失效或撤销时本次运行失败并记录安全原因；长期不可用可按后续生命周期规则自动暂停，不能静默借用创建者浏览器 Token、管理员身份或另一组凭据。后续轮转通过同一引用生效的范围、刷新失败和运行中撤销时效，需要凭据权威系统明示，不承诺实时传播。

Claw 已观察行为是：普通消息只捕获本次执行 Header 的不可变 MateCredentials 并在工具执行时转发，Cron 明确使用 empty()，不会恢复旧请求凭据。模型当前使用内部 CampusMateProvider，不能把模型 API Key 与业务凭据合并成一个请求字段。新增无人值守凭据来源、服务身份或用户长期委托均待确定；M03/M06 现有凭据规则保持有效，相关变化须在身份方案确定后同步。建议园区统一日常任务优先采用受限服务身份，按个人权限执行的任务另行设计可撤销委托。

该建议属于企业产品约束与安全加固。首版受控业务工具不必复制 Claude 的整个 sandbox 环境变量出站替换机制；收益是复用现有可信 Adapter，代价是还不能向任意命令提供等价的安全凭据能力。凭据存储、签发/刷新、授权接口及 Java 依赖尚未选定，不新增 Maven 依赖或宣称已具备 Vault。

<a id="get-schedule-review"></a>

### 4.3. 读取任务详情（候选，待实现）

运营人员打开“工作日园区告警汇总”，需要看到保存的任务内容、Agent、凭据引用、时间规则和当前计划摘要。详情读取返回这一份配置；某次运行的结果另从 Run 和关联 Session 读取，不在配置中嵌入完整执行历史。

```http
GET /campusclaw-service/v1/schedules/schedule-927e03d2a4784f90a6238e790539c6e4
Accept-Language: zh-CN
```

| 请求项 | 候选契约 |
|---|---|
| path.scheduleId | 必填，使用创建返回的原 ID；不通过名称查找，不自行构造 |
| query / body | 无业务查询参数，无请求体 |
| 认证与授权 | 复用 §2 的可信调用上下文，先认证和检查读取功能资格，再按当前可见范围查找任务；具体公司认证 Header/适配器待接线，不用 credentialIds 充当调用本接口的认证 |
| Accept-Language | 可选；支持及回退规则见 §2 |
| 写入控制 Header | 不要求 Idempotency-Key 或 If-Match；读取可安全重试，不触发任务 |

成功为 HTTP 200，返回 `Content-Type: application/json`、`Cache-Control: no-store`、`Content-Language` 与当前 `ETag`。result 与 §4 创建成功的完整资源同形，固定包含 type、id、name、description、agentId、message、schedule、status、pausedReason、metadata、credentialIds、createdAt、updatedAt；无计划时 schedule 为 null，空元数据/凭据分别为 {} 和 []。不返回凭据秘密、文件内容、Agent 完整定义、内部调度游标、revision 或尚未关联的 Session/Run ID。

读取返回当前持久化配置及按 §3.3 生成的时间摘要，不返回创建时的幂等响应快照。一次读取使用一致的配置/lastRunAt 快照，并取一次权威计算时刻生成 upcomingRunsAt；配置或生命周期最近修改时间 updatedAt 不因 GET 或时间数组滚动而变化。ETag 覆盖本次完整表示，其动态变化与条件更新代价由 §5 维护；客户端不得把它解析成版本数，也不依赖尚未定义的 304 缓存协商流程。

正常调用只进行身份与范围校验、持久化读取、时间计算和安全投影。Agent 停用、已绑定凭据失效或无人值守执行依赖不可用，不妨碍有读取权限的用户查看已保存任务并修复；不在 GET 中重新 prepare、换取业务凭据、刷新 token、读取 secret、验证下游登录或创建 Session。读取资格本身被撤销仍应拒绝。凭据引用按保存值返回，不因引用暂时不可用而静默删掉或替换它，也不附加未经验证的 credentialStatus。

建议归档后仍允许有权限者读取详情以便审计；具体归档模型与状态字段仍待生命周期审阅，不以读取接口提前确认 active/paused/archived 枚举。Claude 详情模型有 archived_at，但本次官方 GET 文档未明确归档资源读取的 200/404 行为，不能把此建议说成已核实的基线行为。

失败采用 §6 的两字段错误体：非法 ID 为 400 `SCHEDULE_REQUEST_INVALID`；未认证为 401；无读取功能资格为 403 `SCHEDULE_READ_FORBIDDEN`；任务不存在或不在当前可见范围均为 404 `SCHEDULE_NOT_FOUND`。权限权威或持久化暂不可用为 503；已存记录损坏或响应投影失败为 500 `SCHEDULE_READ_FAILED`，不能把读取故障转成 404。普通 GET 不产生 Agent 禁用的 409、缺版本的 428 或版本冲突的 412。成功和错误均按本专题目标禁用缓存。

```json
{
  "resCode": "SCHEDULE_NOT_FOUND",
  "resMsg": "定时任务不存在或不可访问。"
}
```

en-US 的同一错误为 `{"resCode":"SCHEDULE_NOT_FOUND","resMsg":"Schedule not found or not accessible."}`，HTTP 状态仍为 404。读取权限错误是功能级拒绝；资源级不可见使用上述统一 404，避免泄露另一范围内的任务是否存在。

Claude 对应 `GET /v1/deployments/{deployment_id}`，同样返回完整配置，但直接返回 Deployment，包含其 Agent 版本、环境、初始事件、Vault 引用等资源。Claw 保持既定 Schedule 字段和公司包装；ETag 是本产品候选，不是该官方 GET 页面已声明的能力。[官方详情](https://platform.claude.com/docs/en/api/http/beta/deployments/retrieve)与[读取源码证据](source-evidence.md#schedule-read-evidence)分别说明公开契约和当前实现缺口。

<a id="list-schedules-review"></a>

### 4.4. 读取任务列表（候选，待实现）

列表用于按名称、Agent 和状态找到任务，并直接取得任务配置。已确认每个列表元素与详情 result 采用相同的完整资源，包含 message、description、metadata 和 credentialIds，不维护单独的摘要字段集合；这与 Claude 的完整 Deployment 元素取舍一致。只返回调用方有权读取的任务，凭据只返回引用。分页按现有 [ListEvents 权威契约](../01-CampusClaw多Agent运行时/事件契约/操作/02-list-session-events.json)及[数字分页规则](../01-CampusClaw多Agent运行时/chat-events-history-design.md#3-普通数字页码)收敛为普通整数 page/limit 和 nextPage；下文具体映射、筛选和整项读取操作仍为候选。

```http
GET /campusclaw-service/v1/schedules?page=1&limit=1&status=active
Accept-Language: zh-CN
```

| query | 候选规则 |
|---|---|
| page | 可选正整数，默认 1；1、2、3……是普通页码，不是游标或 Schedule ID；禁止 0、负数、非整数及超出支持范围的数值 |
| limit | 建议沿用 ListEvents：可选正整数，默认 50，范围 1～200；表示本页最多任务数，越界拒绝，不静默截断；Service 应用默认值 |
| name | 可选；去首尾空白后 1～256 个 Java 字符，按名称包含匹配；空值拒绝，省略不筛选。按字面量匹配，用户输入的 %/_ 不作为 SQL 通配符；大小写敏感性待与数据库排序规则一起确定 |
| agentId | 可选；格式复用 Agent ID 规则，按绑定 ID 精确匹配；合法但无可见任务时返回空页，不借查询探测 Agent 存在性 |
| status | 可选单值精确匹配，小写；active/paused/archived 为当前生命周期候选，最终枚举及归档筛选仍待确认 |

无请求体；认证、读取功能资格和语言与详情一致，不要求写入控制 Header。筛选条件以 AND 组合，不提供客户端 owner/scope、任意排序、metadata 查询或凭据反查。重复标量、未知查询项及非法格式建议以 400 `SCHEDULE_REQUEST_INVALID` 拒绝。沿当前归档状态候选，建议省略 status 时只列 active/paused，显式 archived 才列归档；若生命周期采用 Claude 的独立归档时间模型，应同步重审归档筛选，不提前固定 includeArchived。

成功 HTTP 200，普通响应 Header 与详情一致，但不提供用于更新单条任务的列表 ETag；编辑前 GET 详情取得该任务当前 ETag。以下例子请求 page=1、limit=1，当前查询还有后续记录，因此 nextPage=2：

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "schedules": [
      {
        "type": "schedule",
        "id": "schedule-927e03d2a4784f90a6238e790539c6e4",
        "name": "工作日园区告警汇总",
        "description": null,
        "agentId": "agent-550e8400e29b41d4a716446655440000",
        "message": {
          "type": "user.message",
          "content": [
            {"type": "text", "text": "汇总园区过去24小时的设备告警，并标出需要跟进的工单。"}
          ]
        },
        "schedule": {
          "type": "cron",
          "expression": "0 0 8 * * MON-FRI",
          "timezone": "Asia/Shanghai",
          "lastRunAt": null,
          "upcomingRunsAt": [
            "2026-10-05T00:00:00Z",
            "2026-10-06T00:00:00Z",
            "2026-10-07T00:00:00Z",
            "2026-10-08T00:00:00Z",
            "2026-10-09T00:00:00Z"
          ]
        },
        "status": "active",
        "pausedReason": null,
        "metadata": {"parkCode": "park-east", "purpose": "alarm-summary"},
        "credentialIds": ["credential-alarm-example", "credential-workorder-example"],
        "createdAt": "2026-10-04T02:00:00Z",
        "updatedAt": "2026-10-04T02:00:00Z"
      }
    ],
    "nextPage": 2
  }
}
```

列表每项直接采用详情资源，不增加 agentName、nextRunAt、lastRunStatus 或执行结果。完整元素便于直接消费同一响应模型，也避免调用方为读取每条消息另发详情请求；代价是列表传输全部任务内容，需要限制页大小。result 仅包含 schedules/nextPage，不返回 total、page、limit 或额外 hasMore。读取完整元素不提供凭据秘密或文件字节；列表中的配置是当次读取快照，后续编辑仍需取得详情的当前 ETag。

权限范围与业务过滤必须先于分页；禁止先取全局页再过滤。计算 offset=(page-1)*limit，查询前检查整数和乘法边界，溢出或不支持的数值返回 400。读取最多 limit+1 个匹配任务，额外一条仅用于判断下一页；响应最多 limit 条，有后续记录时 nextPage=page+1，否则为 null，不为此接口执行 total 的 COUNT 查询。整页配置及下一页判断来自单次一致读取边界，时间摘要共用本次计算时刻，不跨 HTTP 请求持有事务或快照。

候选排序仍为 updatedAt DESC、id ASC，而 ListEvents 按已提交事件顺序从旧到新读取；只复用分页协议，不照搬事件顺序。运行摘要变化不更新 updatedAt，因此不会仅因一次自动启动改变任务排序。但任务配置可被编辑、归档，新任务会进入列表前部，不能借用事件只在尾部追加的稳定位置前提；并发翻页仍可能重复或遗漏，按 id 去重不能补回漏项。同一轮保持 limit 与筛选不变；修改它们或已知列表发生变更时从 page=1 重读，不将此接口作为可靠增量同步协议。

无匹配或合法超末页均返回 HTTP 200、schedules:[]、nextPage:null，不返回 404、204 或 null 数组；nextPage:null 仅说明本次查询无下一页，不表示不会再有任务或任务已执行完成。无读取功能资格返回 403，认证失败为 401；权限/存储暂不可用为 503，记录损坏或投影失败为 500，不伪装成空列表。具体错误格式、语言与详情一致。

| 对比项 | Claude Deployment 列表 | Claw 当前候选及取舍 |
|---|---|---|
| 元素 | 完整 Deployment，包含 initial_events、metadata、vault_ids | 已确认完整 Schedule，与详情同形；复用响应模型，代价是传输每条任务内容 |
| 分页 | limit 默认 20、最多 100；page 为不透明游标，响应 data/next_page，末页 next_page:null | 参考 ListEvents 的整数 page/nextPage，limit 建议默认50、最多200；result 为 schedules/nextPage，无 total。保持 Claw 客户端风格，代价是深页 OFFSET 和并发翻页移动 |
| 过滤 | agent_id、创建时间 gte/lte、status、include_archived；status 与 include_archived 不能组合 | 增加名称搜索，保留 agentId/status；暂不提供创建时间区间，归档模型另审 |
| 顺序 | 本次公开页未声明默认排序、稳定快照或游标失效规则 | 显式 updatedAt DESC、id ASC，便于最近修改的任务靠前；仍有并发翻页限制 |
| 身份 | Anthropic API 身份/workspace 边界 | 公司可信调用范围；Agent ID 与 metadata 不代替租户/园区授权 |

官方证据为 2026-10-04 重读的[列表参考页](https://platform.claude.com/docs/en/api/http/beta/deployments/list)。Claude page 必须原样传回，不能把它当成数字页码；Claw 的 page 则明确是可按规则构造的正整数，nextPage 为整数或 null，两者同名但类型和语义不同。不依据 Claude 未声明内容推断其内部 SQL、索引或分页快照。

配置读取与运行读取分开：Claude 另有 `GET /v1/deployment_runs` 和 `GET /v1/deployment_runs/{deployment_run_id}`，记录 Session 创建结果；Agent 后续业务结果需要 Session 观察。Claw 同样保留独立 Run 读取边界，路径、过滤、状态与响应另审；任务详情页面可以组合配置详情与 Run 列表，但配置 GET 不因此内嵌运行历史。

## 5. 可靠写入与保存流程

场景为创建园区告警汇总配置，从调用 Claw 到返回持久化结果结束。前提为可信调用身份已可验证；图为待实现目标。Caller 为任意合规调用方，Schedule 是 Claw 应用编排，Directory 是只读 Agent 绑定解析能力，Store 为配置与请求结果的唯一持久化权威；不规定上游产品或部署拓扑。

![Claw 配置保存](schedule_configuration_save.svg)

[原尺寸 SVG](schedule_configuration_save.svg) · [PlantUML 源码](diagram.puml#L130)

1. Claw 验证身份、当前管理范围和请求形状；读取同 scope/actor/key 的已提交结果。允许范围内的同键同请求重放先于 Agent 当前启用状态、时间有效性和 If-Match 重验，避免成功请求因时间流逝变成第二次操作。授权撤销仍拒绝访问，不代表原事务未提交。
2. 首次写入只读解析 Agent 绑定、校验参数和权限；不能用会发布运行目录的 `AgentRuntimeManager.prepare` 充当纯校验。目录能力暂不可用则明确503，不靠旧缓存猜测授权；不持数据库锁跨远程目录查询。
3. 在一个事务中写入配置和成功请求结果；唯一键决定相同请求只提交一次。事务内先重查幂等记录：已有相同键时比较指纹并返回原结果；创建新资源不要求 If-Match，首次执行的更新请求才在锁内重查完整表示的 If-Match/状态。不能先用新版本或 archived 拒绝已成功请求的重放。配置失败整体回滚。数据库成功是响应成功的依据，不沿用 jobs.json 写失败仅记日志的行为。
4. 事务提交后返回配置，不在创建处理器内调用模型、工具或 Session 工厂；自动触发只由后续调度链读取已提交配置。目录/权限在配置校验后仍可能变化，执行时重新检查，不宣称跨目录与 Claw 数据库的原子性。

Idempotency-Key 为调用方生成的规范小写 UUID，在同一可信 scope/actor 内不得跨操作复用；指纹包含方法、目标、原请求正文和原 If-Match，区分省略与 null。相同键及相同请求返回原成功响应和原 ETag，即使资源之后已更新；需当前状态时再 GET 详情。同键不同请求409；同键尚在处理中可等待或409 `SCHEDULE_REQUEST_IN_PROGRESS`，不能并行创建两份。网络断开不取消已提交写入；重试必须使用原键和原快照，不能自动换键。

请求记录至少与配置及归档记录同寿命；如清理原响应，保留键、指纹和结果身份，返回明确的结果过期冲突，不把旧键视为新创建。该选择需要额外存储和清理策略，不能承诺任意旧响应永远可回放。实现可用 `t_schedule` 与 `t_schedule_request` 承载事务，具体 DDL 属于实施；不存 Token/APPKEY。

If-Match 用于条件更新，Idempotency-Key 用于重放同一次操作，内部配置代次用于调度竞态，三者不能互相替代。缺条件标签返回428，不匹配返回412；客户端须重新读取并审阅，不能自动取得新标签覆盖。

候选强 ETag 覆盖完整返回表示（含语言变体和只读时间摘要），由稳定序列化后的内容生成不透明标签；不使用弱 ETag 做 If-Match，也不把内部 revision 包装为完整动态资源的强标签。更新先处理已提交请求重放；首次执行在事务锁内取一次权威时间、读取当前配置及 lastRunAt 并计算当前数组，再判断条件，成功后写入配置和响应快照。启动摘要写入与配置更新需使用同一权威一致性边界，不在锁内调用远程服务。

代价是计划数组滚动或 lastRunAt 变化也可能引起412，即使无人编辑配置；因此这里不承诺只在配置修改时冲突。后续若要求编辑不受运行进展影响，需独立配置表示或另审自定义并发令牌，不能继续把配置版本称为完整资源强 ETag。这一并发形状仍为候选，并非删除 JSON revision 的已确认内容。[HTTP 语义依据](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.1)

## 6. 错误契约

| HTTP / resCode | 含义 |
|---|---|
| 400 `SCHEDULE_NAME_INVALID` / `SCHEDULE_MESSAGE_INVALID` / `SCHEDULE_RULE_INVALID` / `SCHEDULE_TIMEZONE_INVALID` | 对应字段不合法 |
| 400 `SCHEDULE_REQUEST_INVALID` | 非法读取 ID/查询参数；写入缺少请求键、错误类型/字段或空更新 |
| 401 `SCHEDULE_AUTH_REQUIRED` | 未通过 Claw 认证边界 |
| 403 `SCHEDULE_MANAGE_FORBIDDEN` | 无任务管理功能权限 |
| 403 `SCHEDULE_READ_FORBIDDEN` | 无任务读取功能权限；资源级不可见统一用 404 |
| 404 `SCHEDULE_NOT_FOUND` / `SCHEDULE_AGENT_NOT_FOUND` | 资源不存在或不在当前可见范围 |
| 409 `SCHEDULE_AGENT_DISABLED` / `SCHEDULE_ARCHIVED` | Agent 禁用或配置已归档 |
| 409 `SCHEDULE_REQUEST_CONFLICT` / `SCHEDULE_REQUEST_IN_PROGRESS` / `SCHEDULE_REQUEST_RESULT_EXPIRED` | 请求键冲突、原请求进行中或原响应过期；不得换键自动重发 |
| 428 `SCHEDULE_VERSION_REQUIRED`；412 `SCHEDULE_VERSION_CONFLICT` | 缺少 If-Match；或版本已变化 |
| 422 `SCHEDULE_POLICY_REJECTED` | 规则超出部署频率/配额策略 |
| 500 `SCHEDULE_READ_FAILED` | 配置记录损坏、反序列化或安全投影失败；不得降为空成功 |
| 503 `SCHEDULE_SERVICE_UNAVAILABLE` | 当前操作所需权威依赖不可用；读取仅依赖可信身份/可见范围、配置存储和本地时间计算，不因 Agent 或业务执行依赖不可用而失败 |

错误体固定只有 resCode/resMsg；按稳定错误码分支，不解析文案。字段错误按 name、description、agentId、message、schedule、metadata、credentialIds 的固定顺序返回首个错误；每个 Java enum、resCode、MessageSource key 同名。错误不泄露凭据、内部堆栈或用户消息；响应丢失不能据503或断网推断原请求未提交。

<a id="claude-tradeoffs"></a>

## 7. 与 Claude Managed Agents 的取舍

本节只比较当前公开 Beta [创建](https://platform.claude.com/docs/en/api/http/beta/deployments/create)、[更新](https://platform.claude.com/docs/en/api/http/beta/deployments/update)和[定时 Deployment](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)契约，不推断服务端实现；读取详情及列表差异由 §4.3～§4.4 维护。

| 决策 | Claude 公开契约 | Claw 推荐目标、理由与代价 | 分类 |
|---|---|---|---|
| 名称长度 | name 的 maxLength 为 256 | 名称上限同为 256，不增加缺少业务依据的限制；Java 字符计数不声明为已验证的跨语言 Unicode 等价 | 参考基线 |
| 配置资源 | Deployment 绑定 Agent、环境、初始事件和可选规则 | Schedule 绑定 Agent、单条用户消息和可选规则；保留配置与 Session 执行分离，范围聚焦现有调度领域，不建设完整部署平台 | 架构范围 |
| 创建即登记计划 | 提供 schedule 后自动触发，新建示例为 active | 同样登记自动计划；创建处理器不直接运行。不能因为先开发配置就永久默认 paused；运行未接线应限制发布 | 参考基线，无额外启用流程 |
| 执行目标 | 每次触发创建新 Session | 每次运行固定新建 Session，不提供 target；减少已有会话准入规则，代价是不自动延续原会话上下文 | 参考基线、产品范围 |
| Agent 版本 | 字符串固定当时最新版本，亦可指定历史版本 | 只绑定 agentId，使用执行时实际取得的已发布目录；现有 prepare 可命中缓存，非每次远端最新。目录刷新后未来行为可能变，暂缺固定版本可复现保证 | 现有能力缺口 |
| 运行环境 | 显式 environment_id | 不提供空壳 environmentId，沿现有 Host/Agent 目录装配；减少资源模型，但失去独立环境选择与复用 | 架构范围 |
| 初始输入 | initial_events 支持多事件及受约束事件类型 | 一条 user.message，复用既有文本与文件引用格式；不开放多初始事件、system.message 或 user.define_outcome。旧 CronPayload 只有纯文本，调度消息接线与附件长期访问仍待实现/细化 | 产品范围、实现差距 |
| 时间表达 | 五字段 POSIX Cron，IANA 时区 | 采用 Spring 六字段，复用现有解析器且不新增 Maven 依赖；代价是 Claude 表达式不能直接复制，日/周组合语义也不同。[固定与动态调度场景](README.md#spring-scheduling)说明框架能力和执行边界 | 产品约束（方言选择）、实现成本取舍 |
| 时间精度 | 创建 Session/Deployment 示例为整秒 UTC；公开文档未保证只支持秒级或披露数据库精度 | Claw 明确仅支持秒级，Session、完整事件与定时任务一致；降低展示和存储差异，代价是放弃这些字段的亚秒时间差。见[时间证据](source-evidence.md#claude-time-precision-evidence) | 产品约束 |
| Cron 时区 | timezone 必填，使用 IANA 名称 | timezone 可省略，默认 Asia/Shanghai，保存并回显有效值；适配主要园区场景，代价是调用方需了解省略时采用的产品预设，不能继承运行节点默认值 | 产品约束 |
| 时间类型范围 | schedule 模型只声明 cron | 同样只接受 cron；不提供单次计划和任意起点间隔，减少起点、耗尽与更新规则；Spring 六字段与默认上海时区继续保留 | 产品约束（范围收敛） |
| 更新 | 省略保持、schedule:null 清除、初始事件/规则整体替换 | 推荐沿用；Claw 的 message/schedule/credentialIds 整体替换，metadata 依 §3.7 逐 key 更新，不引入通用深层合并；更新操作仍待整体确认 | 参考基线 |
| 并发与重试 | 本次公开操作页未给出与本方案相同的版本/幂等契约 | 明确 ETag/If-Match 和 Idempotency-Key，借鉴现有 Session 更新模式；增加请求记录与冲突处理成本，不能据此声称 Claude 内部没有保护 | Claw 可靠性设计 |
| 返回与预览 | schedule 内有 last_run_at/upcoming_runs_at | 同样返回最近自动开始与最多五次计划；ResultBean、lowerCamelCase、UTC 秒级是公司/产品规则；动态摘要使完整表示 ETag 也随之变化 | 参考基线、公司契约 |
| 状态与版本 | active/paused，另有 archived_at；未声明 revision | 新建 active、响应无 revision；内部配置代次不外露，归档模型另审 | 参考基线、边界明确 |
| 资源类型 | 顶层 type 固定为 deployment | 顶层 type 固定为 schedule，完整响应统一返回；便于识别资源，代价是增加一个恒定字段，不扩展现有 Session 契约 | 产品约束 |
| 暂停原因 | paused_reason 为 null 或 manual/error 原因对象，恢复后清空 | pausedReason 保留相同职责，随状态持久化并安全投影；增加当前原因维护成本，不能用最后一个 Run 错误替代，精确自动错误类型另审 | 参考基线、架构增量 |
| metadata | 最多 16 对字符串，键最多 64、值最多 512 | 支持可选 map，建议同样限制；不进模型，不作身份、权限或凭据依据 | 参考基线、产品约束 |
| 凭据 | vault_ids 引用 workspace 范围 Vault，运行时使用其中凭据 | 已确认 credentialIds 直接引用独立凭据，不增加 Vault 集合层；企业授权独立校验，凭据来源和管理接口待确定 | 企业产品约束、安全加固 |

固定 Agent 版本是最显著的能力差距，不应包装成单纯“字段简化”。未来若要求长期告警策略可重复审计，需要先建设可解析的历史定义与资源绑定，再开放 agentVersion；只保存一个 version 数字不能兑现版本固定。Spring 六字段是本产品已选定的方言，其理由是复用 Java 现有能力与降低维护成本，不是企业园区业务天然要求秒级执行。

## 8. 实施与验收

本配置切片描述上述五个 Claw 接口；已确认的显式试运行作为相邻运行接口继续设计。Controller 使用 RequestVO/ResponseVO 和 ResultBean；Service 处理默认值、完整更新合并与 VO/DTO 转换；Repository/Mapper 只收发 DTO。请求格式校验使用 Jakarta，业务状态和绑定校验在 Service，最终唯一性与版本检查由数据库保障。更新反序列化必须区分省略/null。

全局结构引用[目标类图](README.md#10-全局目标类图与依赖)。配置服务、解析策略和持久化 Adapter 是 Spring 单例，请求上下文/写入快照按请求隔离；配置服务不依赖执行协调器或 Session 工厂。只读绑定端口与可信范围解析待实现，不能直接拿 prepare 替代。

验收至少覆盖：五个配置接口的成功/错误报文；当前范围过滤；预览与保存一致；六字段秒位、拒绝五字段/年字段、日与星期同时受限、IANA/DST、UTC 输出；名称 256/257 边界；创建/更新/预览均拒绝 at/every 与额外起点字段；Agent 绑定校验、拒绝 target/sessionId、不同 Run 创建不同 Session 且同一 Run 不重复创建；单条 user.message 的文本与文件格式及非法事件类型；未知字段/null/整体替换；同键并发只落一份；写失败回滚；丢失回包以原键恢复；credentialIds 直接引用、原样回显且不含 secret，拒绝 vaultIds/credentialRefs 别名，多目标匹配与冲突规则确定后补充执行验收；响应无 revision、status 为小写、metadata 长度/类型/省略/空对象/key 删除和 patch 后大小限制；只读时间字段拒绝写入；创建 lastRunAt 为 null、手动不更新、开始后失败不清空；paused/archived 的计划数组；幂等重放保留原时间数组；同一 ETag 的两个并发且实际改变配置的更新仅一份成功，运行摘要变化也使标签失效；已成功请求重放不重做 Agent enabled 等可变业务校验；省略 schedule 只保存、有效 schedule 保存即自动调度；显式试运行独立触发，清除规则不取消在途执行。运行与附件访问仍需独立接线验收，不能由配置单测替代。

时区另须验收：创建或整体替换 Cron 时省略 timezone 均保存为 Asia/Shanghai，显式其他合法 IANA 时区按输入生效；响应回显保存值，节点时区变化不改变规则，更新省略整个 schedule 不重置时区。绝对时刻响应统一为 Z 结尾的 UTC，秒级且无小数；Cron 的 timezone 仍保留有效值。显式 null 与空字符串策略确定后再补充相应边界。旧 At/Every 不得经新 HTTP 绕过仅 Cron 校验，旧 Job 迁移不得静默改变时间语义。

读取验收须覆盖：列表元素与详情字段和类型一致，包括 message/description；401/403/资源不可见404、读取损坏500与暂不可用503区分；权限过滤先于分页；page/limit 默认与边界、偏移溢出、limit+1 判断；空页与超末页为 schedules:[]/nextPage:null；result 仅 schedules/nextPage、无 total/COUNT；同次读取与排序；列表共用计划计算时刻；GET 不改 updatedAt、不推进调度、不换取凭据、不创建 Session；Agent 停用或引用凭据失效时仍可按读取资格查看；动态摘要参与详情 ETag；错误禁用缓存。归档枚举和筛选/排序确认后补齐对应最终用例，当前不把候选当作已通过实现测试。

资源类型与暂停原因验收须覆盖：创建、详情、列表元素和更新响应均含 type:schedule 与 pausedReason；有无 Cron 的新建资源均为 active/null；人工暂停为 manual，自动暂停为 error 且只含安全错误；恢复清空原因但保留历史，配置修改不隐含恢复；status/pausedReason 原子一致；拒绝顶层只读字段写入而保留嵌套消息/规则 type；幂等重放返回原状态与原因、GET 返回当前快照，原因变化参与 ETag。自动错误 Schema、类型及归档规则确定后补齐最终用例。

不新增直接 Maven 依赖：复用 JDK、Spring CronExpression/Jackson、宿主 MyBatis 3.0.4 与数据库驱动。完整传递依赖图未重跑。公司身份适配、无人值守身份及实际调度是上线依赖，不在本次扩写其接口。当前没有产品代码、数据库或集群测试证据。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.18.0 | 2026-10-04 | 完整资源增加只读 type 与 pausedReason，明确新建、暂停、恢复及当前原因的一致性边界。 |
| 0.17.0 | 2026-10-04 | 列表元素与详情统一完整资源，分页参考 ListEvents 的整数 page/nextPage，并明确读取授权与故障边界。 |
| 0.16.0 | 2026-10-04 | 创建、详情与更新采用 credentialIds 直接绑定独立凭据，请求和响应同名回显。 |
| 0.15.0 | 2026-10-04 | 明确支持凭据绑定，比较独立凭据与 Vault 集合并推荐 credentialIds 条件候选。 |
| 0.14.0 | 2026-10-04 | 响应补齐计划时间摘要、状态改小写并移除 revision，加入 metadata 与凭据引用取舍。 |
| 0.13.0 | 2026-10-04 | 每次运行固定新建 Session，移除 target，并展开创建响应及时间摘要的确认边界。 |
| 0.12.0 | 2026-10-04 | 名称上限对齐 256，时间规则仅支持 Cron，并区分文件引用、上传能力与两种会话目标的证据。 |
| 0.11.0 | 2026-10-02 | 定时任务统一秒级输入、存储与 UTC 响应，默认间隔起点向上取整以保留完整等待。 |
| 0.10.0 | 2026-09-30 | 绝对时刻响应沿用 UTC 并固定三位毫秒，输入精度及超出精度的处理继续待定。 |
| 0.9.0 | 2026-09-30 | Cron 时区可省略并默认保存、回显上海时区，at/startAt 必须携带偏移量且 at/every 不另设时区。 |
| 0.8.0 | 2026-09-30 | 明确整数秒间隔、固定起点回显及更新校验，补充上海时区候选与各基线时区边界。 |
| 0.7.0 | 2026-09-30 | 创建 every 时省略 startAt 默认等待一个完整间隔后首次触发，继续沿固定时间表推进。 |
| 0.6.0 | 2026-09-30 | every.startAt 为可选字段，省略后的默认首次时间、显式 null 与更新语义继续待定。 |
| 0.5.0 | 2026-09-30 | every 按固定时间表计算后续计划，不随执行耗时漂移，首次触发默认值与重叠恢复策略待定。 |
| 0.4.0 | 2026-09-30 | 明确 cron、at、every 的支持范围与语义边界，保留间隔基准、首次触发及动态响应的待定项。 |
| 0.3.0 | 2026-09-30 | 明确 Spring 六字段、单条 user.message 和可选计划的创建行为，区分已定能力与待确认接口形状。 |
| 0.2.0 | 2026-09-29 | 将配置契约限定为五个 Claw 接口，明确创建登记计划及与 Claude 的能力、成本取舍。 |
| 0.1.0 | 2026-09-29 | 建立 Mate 公共入口到 Claw 单一配置存储的加载、预览、保存、回显与并发编辑闭环。 |
