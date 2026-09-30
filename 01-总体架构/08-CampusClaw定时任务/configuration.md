# Claw 定时任务配置接口

[模块主设计](README.md) · [源码证据](source-evidence.md#configuration-evidence) · [与 Claude 的取舍](#claude-tradeoffs)

| 属性 | 值 |
|---|---|
| 版本 | 0.8.0 · 2026-09-30 |
| 状态 | 已确认能力与 proposed 接口形状分开记录；新接口待实现、尚未发布，整项操作尚未完成确认 |
| 本文权威范围 | Claw 的创建、列表、详情、部分更新、时间预览；不定义 Mate 接口或页面实现 |
| 产品范围 | 支持新建独立 Session 与继续已有 Session，独立 Session 优先；具体交付批次待确定 |
| 源码基线 | Claw main `553dcd5e2ff682f9684810a043b442b37a02e54a`；2026-09-29 确认并 fetch，2026-09-30 重读该提交的调度范围 |
| 对照 | Claude Managed Agents 公开 Beta HTTP API；2026-09-29 核对调度文档，2026-09-30 再核对创建输入与 Cron 方言 |

## 1. 业务结果与接口边界

调用方配置“工作日 08:00 汇总园区设备告警”，向 Claw 提交 Agent、任务内容、执行目标和时间规则。Claw 验证当前调用范围、绑定和规则，持久化后返回任务 ID、完整配置及版本。之后可读取、修改该配置，不依赖调用方在线。

已确认的创建行为：schedule 可省略，省略时只保存、不立即执行；填写有效 schedule 后保存即登记自动计划，无需额外启用。试运行是独立的显式操作，可用于无 schedule 的配置；其 HTTP 路径、返回与运行细节待设计。每次执行输入为一条 `user.message`，新建 Session 时作为首条任务消息，已有 Session 时作为新增消息；Cron 沿用 Spring 六字段。

时间规则已确认支持 `cron`、`at`、`every`：分别覆盖日历周期、指定时刻单次执行和间隔重复任务。every 使用整数秒字段 intervalSeconds，按固定时间表触发；startAt 可选，创建时省略则等待一个完整间隔，最终起点保存并在创建响应和详情回显。更新省略起点时重算，新起点必须是未来时间，原样回传已保存旧起点允许保留；精确规则见 §3.2。服务端取时点、时区默认值、at 的过期处理及执行后状态仍需细化。

除明确标记已确认的字段外，下文状态模型、其余字段名、路径和错误码仍为 proposed。候选新建状态为 `ACTIVE`，创建处理器不直接调用模型或创建 Session；自动执行由后续调度触发。暂停、恢复、显式试运行、归档和运行记录的精确契约另行设计，不能把下列五个配置接口当作完整产品接口清单。

上述已确认创建语义不能被解释为“后端暂未接线也返回 active”。配置服务可以先开发和测试，但调度接线、执行身份及准入尚未交付时，不发布可自动运行的创建承诺；未满足依赖的请求返回服务不可用。保存成功也不保证后续业务一定成功，执行时仍须检查当前 Agent、授权和容量。

失败时，格式或规则无效不写入；版本冲突不覆盖；数据库失败不返回成功；响应丢失可按原请求键重试查询原提交结果，不创建第二份任务。Claw 不定义浏览器草稿、Mate 转发、公共 Chat 映射或 Agent 选择器。

## 2. Claw 接口清单

基础路径为 `/campusclaw-service/v1`。资源名沿用定时任务领域的 `schedules`；它保存完整任务配置，不是只有一个 Cron 字符串，也不宣称兼容 Claude Deployment 报文。

| 操作 | 方法与完整路径 | 成功结果 |
|---|---|---|
| 创建配置 | POST `/campusclaw-service/v1/schedules` | 201；完整资源、Location、ETag；要求 Idempotency-Key |
| 列表 | GET `/campusclaw-service/v1/schedules` | 200；当前可信范围内的分页摘要 |
| 详情 | GET `/campusclaw-service/v1/schedules/{scheduleId}` | 200；完整资源及 ETag |
| 部分更新 | POST `/campusclaw-service/v1/schedules/{scheduleId}` | 200；完整资源及 ETag；要求 If-Match、Idempotency-Key |
| 时间预览 | POST `/campusclaw-service/v1/schedules/preview` | 200；规范规则、计算基准与最多五次未来计划时间；不保存 |

本切片不增加 options、Agent 目录或请求回执查询接口。能力和字段由本契约定义；同键写请求重放承担丢失响应的恢复。调用方须保存请求键、原请求正文和原 If-Match 才能重试，具体客户端存储方式不属于 Claw 契约。

Claw 必须在服务认证边界取得可信调用者和管理作用域，再按资源、Agent 和目标 Session 授权。scope、owner、授权结果与凭据不进入请求 JSON；不能信任任意 Header 中的声明。相关公司适配器和可信范围解析尚未接线，是明确的实施缺口；本设计不因“内部 API”而省略鉴权，也不新增或推断 Mate 认证协议。到期业务执行身份与配置管理身份分别处理，不能保存请求 Token 供将来运行。

所有普通成功使用 `resCode/resMsg/result`；失败仅返回 `resCode/resMsg`，保留真实 HTTP 状态。JSON 为 lowerCamelCase。配置响应为 `Cache-Control: no-store`；语言支持 zh-CN/en-US，缺省或不支持时回退 zh-CN，返回 Content-Language。scheduleId 由服务端生成、大小写敏感且不复用；示例中的 UUID 后缀不构成客户端可构造 ID 的许可。

## 3. 配置字段与时间规则

| 字段 | 创建与更新约束 |
|---|---|
| name | 创建必填；去首尾空白后 1～128 个 Java 字符；允许重名，不作为身份 |
| description | 可选，最多 2048 个 Java 字符；创建省略默认 null，更新省略保持，空白或显式 null 清除；不附加到模型输入 |
| agentId | 创建必填；复用 `ClawConstants.Agent.ID_REGEX`，验证存在、可用和当前调用者的配置资格；只绑定 Agent 身份，不保证固定历史版本 |
| target | 创建必填；`{ "type": "newSession" }` 或绑定已有 Session；两种目标均属于需求范围 |
| message | 创建必填；一条 `type:"user.message"`，content 复用现有文本与文件引用格式；外层字段名 message 为候选，附件长期保留与到期访问规则待确定；不开放 system.message 或 user.define_outcome |
| schedule | 可选；创建省略默认 null，更新省略保持；非空为下表的联合类型，更新时整体替换 |
| status/revision/id/createdAt/updatedAt | 全部只读；新建 ACTIVE、revision=1，时间为 UTC ISO 8601；status 为 ACTIVE/PAUSED/ARCHIVED，ARCHIVED 不可修改 |

以下为候选请求形状；类型范围、Spring 六字段、every 固定时间表、整数秒 intervalSeconds 及 §3.2 的 startAt 行为已确认；时区、绝对时间格式及其他约束仍为 proposed。

| schedule.type | 候选完整输入 | 语义与确认边界 |
|---|---|---|
| cron | type、expression、timezone | Spring 六字段 `second minute hour day-of-month month day-of-week`；timezone 使用 IANA 名称，必填性及默认值见 §3.4 待定方案；拒绝五字段，不自动补秒 |
| at | type、at、timezone | 已确认指定时刻单次执行；建议以带明确 offset 的 ISO 8601 输入并输出 UTC，创建/替换时拒绝过去时刻；timezone 仅供展示，是否保留另定 |
| every | type、intervalSeconds、startAt（可选）、timezone（是否保留待定） | 已确认 intervalSeconds 为整数秒，按固定时间表重复，startAt 可选；保存、回显与更新规则见 §3.2。间隔必须为正；最小/最大间隔、绝对时间格式、精确取时点与 timezone 待确定 |

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

各字段支持 Spring 的列表、范围、步长及其日期扩展，具体匹配以项目使用的 Spring `CronExpression` 为准；宏快捷写法是否开放另行确定，不能仅因解析器接受就纳入本 API。月内日期与星期同时受限时要求同时匹配：`0 0 8 1 * MON` 表示“每月 1 日且为周一的 08:00”，不能按 POSIX 常见的日期或星期匹配方式解读。时区单独传入 timezone，避免运行节点配置改变计划含义。[官方语法](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/scheduling/support/CronExpression.html)

### 3.2. 三种类型的边界与待定细节

Cron 不能完整替代 at/every。`0 0 8 1 10 *` 表示每年 10 月 1 日 08:00，不表达某一年的单次执行；`0 */7 * * * *` 在每个小时内匹配 0、7、14、21、28、35、42、49、56 分，跨小时最后一段只有 4 分钟，不等于从任意起点连续每隔 7 分钟。三种类型对应不同业务语义，不将单次计划或任意间隔强行转换成 Cron。

every 按固定时间表触发。首次计划时刻为 T、固定间隔为 Δ 时，第 n 次计划为 `T + n × Δ`（n 从 0 开始），不根据实际开始或完成时间重设后续计划。例如首次为 10:00、间隔 10 分钟，即使本次耗时 3 分钟，后续计划仍为 10:10、10:20。该规则便于稳定预览，不保证实际准点开始，也不决定上一轮尚未结束、停机或迟到时采用跳过、排队还是补跑；这些执行策略另行确定。

`every.startAt` 可选，显式值表示第一次计划时间 T。创建时省略则等待一个完整间隔后首次触发：设创建基准时间为 B、间隔为 Δ，则首次计划时间 T = B + Δ，后续为 T + n × Δ。例如 B 为 10:00、间隔 10 分钟，计划时间为 10:10、10:20、10:30。此默认行为不适用于完全省略 schedule 的配置；后者只保存，不登记自动计划。可选仅表示允许省略，显式 null 是否接受仍待确定。

服务端保存最终确定的 startAt，创建响应与详情均返回该固定起点；重试、读取和重启复用已保存值，不能按当前时间重新计算，startAt 也不随每次触发向后推进。创建基准 B 的精确取时点及预览默认值与保存值的关系仍待确定。

更新省略整个 schedule 时保留原计划；提交 every 规则但省略 startAt 时重新起算，首次计划为更新基准加本次 intervalSeconds。显式传回已保存起点则保留它，可同时修改间隔。新设 startAt 必须严格晚于校验基准；更新为与当前已保存 every 起点相同的时刻时，即使它已过去也允许保留，这一例外不要求间隔也不变。原值比较应按同一绝对时刻，不能只比较时间字符串。已有任务的停机、重叠、补跑策略不由此推定。

同一幂等键的原请求重试返回原结果，不重算起点。以新键提交省略 startAt 的 every 规则会应用新的更新基准；即使间隔相同，也不能仅据输入间隔相同就当作无变化。规范化后的完整规则相同才按未修改处理。这里只冻结起点行为，不代表更新操作的完整 HTTP 契约已确认。

其余候选规则：at/every 接受带 Z 或数值偏移的 ISO 8601 输入，规范化 UTC 输出可原样回传；小数秒精度仍待明确。timezone 不改变绝对时刻或固定秒间隔，是否保留见 §3.4。已有规则只修改名称等字段时，不因其起点已过去而拒绝或重设起点。旧 CronTool 的 every 字符串值及内部 intervalMs 使用毫秒，新 HTTP 的 intervalSeconds 使用秒；不自动将两套报文互认或迁移，旧毫秒间隔可能无法无损表示为整数秒。旧 CronEngine 使用完成时间基准；目标固定时间表属于需独立验收的语义变更，不能称为原样复用。

### 3.3. 预览与运行时间响应候选

候选预览输入为 `{ "schedule": { ... } }`，schedule 必须非空；返回 result `{schedule, computedAt, upcomingRunsAt}`。computedAt 由服务端采样；upcomingRunsAt 是严格晚于它、按升序排列的最多五个 UTC 计划时刻，at 最多一个。every 根据固定时间表计算，可用过去的起点预览未来；已过期 at 或无未来匹配的 Cron 返回 `SCHEDULE_RULE_INVALID`，不改动已保存资源。

创建、详情、更新是否直接返回只读 upcomingRunsAt/lastRunAt、字段放置与 lastRunAt 的事件含义仍待确认；增加动态字段时需同步修正配置版本与完整响应 ETag 的关系。下文报文暂保留配置表示，不将这一候选结构当成已完成的 Claude 响应对齐。

预览与写入复用同一时间策略，保存重新校验，不把预览当作准入凭证。预览是规则计算值，不是实际开始时间保证，也不是当前调度游标。频率、间隔与配额由部署策略约束；超过范围返回稳定的策略错误，策略本身未配置则服务不可用，不能默许无限频率。DST 与解析库版本边界必须验收，本接口不复制 Claude 的 jitter 承诺。

已有会话使用候选 `target={type:"existingSession",sessionId:"..."}`，沿用 Claw 已有 Session ID，不引入 chatId。要求目标存在、可访问、未删除且归属于同一 agentId；更新 agentId/target 后对最终组合整体校验。保存不要求此刻 idle，实际投递准入另定；目标失效不能回退新建。独立会话优先不等于已决定首版拒绝已有会话。

### 3.4. 时区选择与确认边界

CampusClaw 的主要业务时区为 Asia/Shanghai。推荐 Cron 的 timezone 可省略，服务端补全为 Asia/Shanghai，并将确定的时区保存、回显后用于计算；也可选择严格对齐 Claude，将 timezone 设为必填。该选择尚未确认，不能将“主要使用上海时区”自动等同于“接口只能使用上海时区”或已接受缺省值。两种方案均不依赖运行节点的默认时区。

推荐 at/startAt 的输入字符串携带明确偏移量、响应统一 UTC，at/every 不再另设 timezone；调用方按所需时区展示。这仍为候选，不因 intervalSeconds 已确认就一并冻结。带 offset 的单次时刻与固定秒间隔不需要日历解释时区；若额外保存 timezone 供展示，则必须再定义其与输入偏移量的关系。

[基线时区证据](source-evidence.md#timezone-evidence)区分 DSH Cron 必填时区、GitHub Actions 可选时区且默认 UTC、pi 无日历时区字段及 Codex 尚未核实的默认来源；不能据此宣称存在统一行业默认值。默认上海是 CampusClaw 的产品约束候选。

## 4. 创建、读取与更新报文

创建 `POST /campusclaw-service/v1/schedules`，携带 `Idempotency-Key: 0ca92847-fb58-4a9a-900f-8a7b26a71496`：

```json
{
  "name": "工作日园区告警汇总",
  "agentId": "agent-550e8400e29b41d4a716446655440000",
  "target": { "type": "newSession" },
  "message": {
    "type": "user.message",
    "content": [
      { "type": "text", "text": "汇总园区过去24小时的设备告警，并标出需要跟进的工单。" }
    ]
  },
  "schedule": {
    "type": "cron",
    "expression": "0 0 8 * * MON-FRI",
    "timezone": "Asia/Shanghai"
  }
}
```

响应 HTTP 201，`Location: /campusclaw-service/v1/schedules/schedule-927e03d2a4784f90a6238e790539c6e4`，`ETag: "scfg-1"`：

```json
{
  "resCode": "0",
  "resMsg": "success",
  "result": {
    "id": "schedule-927e03d2a4784f90a6238e790539c6e4",
    "name": "工作日园区告警汇总",
    "description": null,
    "agentId": "agent-550e8400e29b41d4a716446655440000",
    "target": { "type": "newSession" },
    "message": {
      "type": "user.message",
      "content": [
        { "type": "text", "text": "汇总园区过去24小时的设备告警，并标出需要跟进的工单。" }
      ]
    },
    "schedule": {
      "type": "cron",
      "expression": "0 0 8 * * MON-FRI",
      "timezone": "Asia/Shanghai"
    },
    "status": "ACTIVE",
    "revision": 1,
    "createdAt": "2026-09-29T12:00:00Z",
    "updatedAt": "2026-09-29T12:00:00Z"
  }
}
```

GET 详情返回同形资源及当前 ETag。列表允许 pageIndex/pageSize/name/agentId/status 查询：一基页码，默认1/20，上限100；name 为名称包含匹配，agentId/status 为精确匹配；按 updatedAt DESC、id ASC 排序。result 为 `{data,total,pageIndex,pageSize}`；每条摘要省略 message/description，其余字段同详情。权限过滤先于分页和计数；分页不保证固定快照，跨页可能受并发修改影响。

更新到工作日 09:00，`POST /campusclaw-service/v1/schedules/{scheduleId}`，携带 `If-Match: "scfg-1"` 和新的 Idempotency-Key：

```json
{
  "schedule": {
    "type": "cron",
    "expression": "0 0 9 * * MON-FRI",
    "timezone": "Asia/Shanghai"
  }
}
```

成功返回完整资源及新 ETag。更新至少提供 name/description/agentId/target/message/schedule 中一个字段；省略保持，description/schedule 显式 null 清除，其他 null 拒绝。target/message/schedule 整体替换，`{"schedule":{"timezone":"UTC"}}` 不合法。先与已保存配置合并，再校验最终整体，任一错误则全部不改。拒绝未知字段、错误 JSON 类型和只读字段；同值更新不增 revision，但记录请求结果。

更新保持 ACTIVE/PAUSED 状态；清除 schedule 只移除未来自动计划，不取消在途 Session。变更后的 revision 供后续受理使用，不修改已接受输入；仅改 message 等字段不重置时间规则。更新与到期受理须有明确的事务先后关系，具体 worker 机制不在此定义。

详情不包含会随运行变化的统计、nextFireAt 或目录展示信息，ETag 对应完整配置表示。未来启停/归档改变配置状态时递增 revision；运行进展不递增配置版本。计划预览走独立接口，避免时间自然推进导致用户编辑冲突。

## 5. 可靠写入与保存流程

场景为创建园区告警汇总配置，从调用 Claw 到返回持久化结果结束。前提为可信调用身份已可验证；图为待实现目标。Caller 为任意合规调用方，Schedule 是 Claw 应用编排，Directory 是只读 Agent/目标解析能力，Store 为配置与请求结果的唯一持久化权威；不规定上游产品或部署拓扑。

![Claw 配置保存](schedule_configuration_save.svg)

[原尺寸 SVG](schedule_configuration_save.svg) · [PlantUML 源码](diagram.puml#L134)

1. Claw 验证身份、当前管理范围和请求形状；读取同 scope/actor/key 的已提交结果。允许范围内的同键同请求重放先于 Agent 当前启用状态、时间有效性和 If-Match 重验，避免成功请求因时间流逝变成第二次操作。授权撤销仍拒绝访问，不代表原事务未提交。
2. 首次写入只读解析 Agent/Session 绑定、校验参数和权限；不能用会发布运行目录的 `AgentRuntimeManager.prepare` 充当纯校验。目录能力暂不可用则明确503，不靠旧缓存猜测授权；不持数据库锁跨远程目录查询。
3. 在一个事务中写入配置和成功请求结果；唯一键决定相同请求只提交一次。事务内先重查幂等记录：已有相同键时比较指纹并返回原结果，只有首次写入才在锁内重查 revision/状态；不能先用新版本或 ARCHIVED 拒绝已成功请求的重放。配置失败整体回滚。数据库成功是响应成功的依据，不沿用 jobs.json 写失败仅记日志的行为。
4. 事务提交后返回配置，不在创建处理器内调用模型、工具或 Session 工厂；自动触发只由后续调度链读取已提交配置。目录/权限在配置校验后仍可能变化，执行时重新检查，不宣称跨目录与 Claw 数据库的原子性。

Idempotency-Key 为调用方生成的规范小写 UUID，在同一可信 scope/actor 内不得跨操作复用；指纹包含方法、目标、原请求正文和原 If-Match，区分省略与 null。相同键及相同请求返回原成功响应和原 ETag，即使资源之后已更新；需当前状态时再 GET 详情。同键不同请求409；同键尚在处理中可等待或409 `SCHEDULE_REQUEST_IN_PROGRESS`，不能并行创建两份。网络断开不取消已提交写入；重试必须使用原键和原快照，不能自动换键。

请求记录至少与配置及归档记录同寿命；如清理原响应，保留键、指纹和结果身份，返回明确的结果过期冲突，不把旧键视为新创建。该选择需要额外存储和清理策略，不能承诺任意旧响应永远可回放。实现可用 `t_schedule` 与 `t_schedule_request` 承载事务，具体 DDL 属于实施；不存 Token/APPKEY。

If-Match 用于防止覆盖别人修改，Idempotency-Key 用于重放同一次操作，两者不能互相替代。缺版本返回428，过期返回412；不能自动取新版本覆盖。现有 Session API 已有版本检查模式，新增 Schedule 接线仍为待实现。

## 6. 错误契约

| HTTP / resCode | 含义 |
|---|---|
| 400 `SCHEDULE_NAME_INVALID` / `SCHEDULE_MESSAGE_INVALID` / `SCHEDULE_RULE_INVALID` / `SCHEDULE_TIMEZONE_INVALID` | 对应字段不合法 |
| 400 `SCHEDULE_REQUEST_INVALID` | 缺少请求键、错误类型/字段/目标形状或空更新 |
| 401 `SCHEDULE_AUTH_REQUIRED` | 未通过 Claw 认证边界 |
| 403 `SCHEDULE_MANAGE_FORBIDDEN` | 无任务管理功能权限 |
| 404 `SCHEDULE_NOT_FOUND` / `SCHEDULE_AGENT_NOT_FOUND` / `SCHEDULE_SESSION_NOT_FOUND` | 资源不存在或不在当前可见范围 |
| 409 `SCHEDULE_AGENT_DISABLED` / `SCHEDULE_ARCHIVED` / `SCHEDULE_TARGET_CONFLICT` | Agent 禁用、配置已归档或目标与 Agent 绑定不符 |
| 409 `SCHEDULE_REQUEST_CONFLICT` / `SCHEDULE_REQUEST_IN_PROGRESS` / `SCHEDULE_REQUEST_RESULT_EXPIRED` | 请求键冲突、原请求进行中或原响应过期；不得换键自动重发 |
| 428 `SCHEDULE_VERSION_REQUIRED`；412 `SCHEDULE_VERSION_CONFLICT` | 缺少 If-Match；或版本已变化 |
| 422 `SCHEDULE_POLICY_REJECTED` | 规则超出部署频率/间隔/配额策略 |
| 503 `SCHEDULE_SERVICE_UNAVAILABLE` | 目录、持久化、准入策略或所需运行依赖不可用 |

错误体固定只有 resCode/resMsg；按稳定错误码分支，不解析文案。字段错误按 name、description、agentId、target、message、schedule 的固定顺序返回首个错误；每个 Java enum、resCode、MessageSource key 同名。错误不泄露凭据、内部堆栈或用户消息；响应丢失不能据503或断网推断原请求未提交。

<a id="claude-tradeoffs"></a>

## 7. 与 Claude Managed Agents 的取舍

本节只比较当前公开 Beta [创建](https://platform.claude.com/docs/en/api/http/beta/deployments/create)、[更新](https://platform.claude.com/docs/en/api/http/beta/deployments/update)和[定时 Deployment](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments)契约，不推断服务端实现。

| 决策 | Claude 公开契约 | Claw 推荐目标、理由与代价 | 分类 |
|---|---|---|---|
| 配置资源 | Deployment 绑定 Agent、环境、初始事件和可选规则 | Schedule 绑定 Agent、目标、单条用户消息和可选规则；保留配置与 Session 执行分离，范围聚焦现有调度领域，不建设完整部署平台 | 架构范围 |
| 创建即登记计划 | 提供 schedule 后自动触发，新建示例为 active | 同样登记自动计划；创建处理器不直接运行。不能因为先开发配置就永久默认 PAUSED；运行未接线应限制发布 | 参考基线，无额外启用流程 |
| 执行目标 | 每次触发创建新 Session | 两种目标均需支持，newSession 优先；existingSession 增加目标授权、上下文和并发准入责任，交付批次另定 | 产品扩展 |
| Agent 版本 | 字符串固定当时最新版本，亦可指定历史版本 | 只绑定 agentId，使用执行时实际取得的已发布目录；现有 prepare 可命中缓存，非每次远端最新。目录刷新后未来行为可能变，暂缺固定版本可复现保证 | 现有能力缺口 |
| 运行环境 | 显式 environment_id | 不提供空壳 environmentId，沿现有 Host/Agent 目录装配；减少资源模型，但失去独立环境选择与复用 | 架构范围 |
| 初始输入 | initial_events 支持多事件及受约束事件类型 | 一条 user.message，复用既有文本与文件引用格式；不开放多初始事件、system.message 或 user.define_outcome。旧 CronPayload 只有纯文本，调度消息接线与附件长期访问仍待实现/细化 | 产品范围、实现差距 |
| 时间表达 | 五字段 POSIX Cron，IANA 时区 | 采用 Spring 六字段，复用现有解析器且不新增 Maven 依赖；代价是 Claude 表达式不能直接复制，日/周组合语义也不同。[固定与动态调度场景](README.md#spring-scheduling)说明框架能力和执行边界 | 产品约束（方言选择）、实现成本取舍 |
| 单次与间隔 | 上述 schedule 模型只声明 cron | 已确认支持 at/every；every 使用整数秒 intervalSeconds 与可选固定 startAt，创建缺省先等一个间隔，保存并回显起点，更新缺省重算；具体见 §3.2。精确取时与运行恢复待定，需验收旧完成时间基准的迁移差异 | 产品扩展、间隔基准语义变更 |
| 更新 | 省略保持、schedule:null 清除、初始事件/规则整体替换 | 推荐沿用；Claw 的 message/target/schedule 整体替换，不引入通用深层合并；更新操作仍待整体确认 | 参考基线 |
| 并发与重试 | 本次公开操作页未给出与本方案相同的版本/幂等契约 | 明确 ETag/If-Match 和 Idempotency-Key，借鉴现有 Session 更新模式；增加请求记录与冲突处理成本，不能据此声称 Claude 内部没有保护 | Claw 可靠性设计 |
| 返回与预览 | Deployment 表示内返回 upcoming_runs_at | ResultBean + 配置 ETag；时间预览独立读取，避免时间变化使配置版本失效；代价是多一次预览调用 | 公司契约、架构取舍 |

固定 Agent 版本是最显著的能力差距，不应包装成单纯“字段简化”。未来若要求长期告警策略可重复审计，需要先建设可解析的历史定义与资源绑定，再开放 agentVersion；只保存一个 version 数字不能兑现版本固定。Spring 六字段是本产品已选定的方言，其理由是复用 Java 现有能力与降低维护成本，不是企业园区业务天然要求秒级执行。

## 8. 实施与验收

本配置切片描述上述五个 Claw 接口；已确认的显式试运行作为相邻运行接口继续设计。Controller 使用 RequestVO/ResponseVO 和 ResultBean；Service 处理默认值、完整更新合并与 VO/DTO 转换；Repository/Mapper 只收发 DTO。请求格式校验使用 Jakarta，业务状态和绑定校验在 Service，最终唯一性与版本检查由数据库保障。更新反序列化必须区分省略/null。

全局结构引用[目标类图](README.md#10-全局目标类图与依赖)。配置服务、解析策略和持久化 Adapter 是 Spring 单例，请求上下文/写入快照按请求隔离；配置服务不依赖执行协调器或 Session 工厂。只读绑定端口与可信范围解析待实现，不能直接拿 prepare 替代。

验收至少覆盖：五个配置接口的成功/错误报文；当前范围过滤；预览与保存一致；六字段秒位、拒绝五字段/年字段、日与星期同时受限、IANA/DST、UTC 往返、every 旧锚点；两种 target 的绑定校验；单条 user.message 的文本与文件格式及非法事件类型；未知字段/null/整体替换；同键并发只落一份；写失败回滚；丢失回包以原键恢复；同一 ETag 的两个并发且实际改变配置的更新仅一份成功；重放不重做过期时间及 Agent enabled 校验；省略 schedule 只保存、有效 schedule 保存即自动调度；显式试运行独立触发，清除规则不取消在途执行。运行与附件访问仍需独立接线验收，不能由配置单测替代。

every 另须验收：intervalSeconds 按整数秒解释；创建缺省先等一个间隔，显式 startAt 不额外加间隔；保存的固定起点在创建/详情回显，重试及重启不重算。更新省略整个 schedule 保持，提交 every 但省略 startAt 重算；新设过去或等于当前的起点拒绝，回传当前已保存旧起点允许且可同时改间隔。同键重试不重算；新键省略起点的更新按完整规范规则判断变化。两种输入的后续计划均不随任务耗时漂移；精确取时、时间格式及范围确定后补充对应边界验收。

不新增直接 Maven 依赖：复用 JDK、Spring CronExpression/Jackson、宿主 MyBatis 3.0.4 与数据库驱动。完整传递依赖图未重跑。公司身份适配、无人值守身份及实际调度是上线依赖，不在本次扩写其接口。当前没有产品代码、数据库或集群测试证据。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.8.0 | 2026-09-30 | 明确整数秒间隔、固定起点回显及更新校验，补充上海时区候选与各基线时区边界。 |
| 0.7.0 | 2026-09-30 | 创建 every 时省略 startAt 默认等待一个完整间隔后首次触发，继续沿固定时间表推进。 |
| 0.6.0 | 2026-09-30 | every.startAt 为可选字段，省略后的默认首次时间、显式 null 与更新语义继续待定。 |
| 0.5.0 | 2026-09-30 | every 按固定时间表计算后续计划，不随执行耗时漂移，首次触发默认值与重叠恢复策略待定。 |
| 0.4.0 | 2026-09-30 | 明确 cron、at、every 的支持范围与语义边界，保留间隔基准、首次触发及动态响应的待定项。 |
| 0.3.0 | 2026-09-30 | 明确 Spring 六字段、单条 user.message 和可选计划的创建行为，区分已定能力与待确认接口形状。 |
| 0.2.0 | 2026-09-29 | 将配置契约限定为五个 Claw 接口，明确创建登记计划及与 Claude 的能力、成本取舍。 |
| 0.1.0 | 2026-09-29 | 建立 Mate 公共入口到 Claw 单一配置存储的加载、预览、保存、回显与并发编辑闭环。 |
