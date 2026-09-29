# 定时任务配置：从页面到持久化

[模块主设计](README.md) · [源码证据](source-evidence.md#configuration-evidence) · [前端入口](../../07-前端设计/README.md)

| 属性 | 值 |
|---|---|
| 版本 | 0.1.0 · 2026-09-29 |
| 状态 | 推荐目标、待实现；接口为 proposed，尚未发布 |
| 本文权威范围 | 配置页面、候选 Agent、时间预览、创建、列表、详情、部分更新及两跳持久化回执；本文是这些新增接口的唯一精确设计源 |
| 本次交付边界 | 保存配置，不启动 Agent；新会话配置优先，已有 Chat 目标保留第二阶段规则 |
| 源码基线 | Claw `553dcd5e2ff682f9684810a043b442b37a02e54a`；Mate 本地示例 `4b957a3a846659f5b7569c9d6133abc070cd2e3c`；具体范围见证据 |

## 1. 用户完成什么操作

园区运营人员要配置“工作日 08:00 汇总过去 24 小时的设备告警”。进入“定时任务”，选择自己有权使用的 Agent，填写任务名称和每次要做的事，选择时间与时区，看见未来五次计划时间，点击“保存”。页面回到详情，显示服务端实际保存的内容和“已暂停，尚未启用”。重新打开页面或换设备，仍从服务端读回同一份配置。

配置保存和执行启用是两个结果。此切片新建任务为 `PAUSED`，保存不创建 Chat/Session，不调用模型、工具、`CronService.createJob` 或 `AgentRuntimeManager.prepare`。后续启用、手动运行、停止及运行结果属于执行切片；本页不得先展示可以使用的按钮。无人值守身份尚未确定，不妨碍保存合法的暂停配置，也不能据保存成功推断已经具备执行资格。

失败时，页面保留草稿并定位错误：时间格式错误修改时间，Agent 不再可用重新选择，别人已修改则读取新版本后比较。保存响应丢失时保留同一次请求标识，不能换一个标识再创建。用户看到的是“保存结果待确认”，不是未经确认的成功或失败。

## 2. 根据现有系统划分职责

正常链路为 **浏览器 → Mate → Claw 配置服务 → Claw 数据库**。Mate 是公开入口，Claw 是任务配置的唯一持久化权威。两跳独立鉴权、校验、错误映射；不在 Mate 和 Claw 双写两份可变任务正文。

| 层 | 负责什么 | 当前可复用与新增范围 |
|---|---|---|
| 页面 | 表单草稿、选择 Agent、请求预览、保存反馈和版本冲突处理 | 复用 Vue 组件和请求代次隔离模式；正式 Mate API 客户端及本页待实现。现有 `useRuntimeApi` 是内部调试客户端 |
| Mate | 认证当前操作者，校验任务管理范围和 Agent 使用权，输出安全候选；已有 Chat 模式解析私有 Session 映射；包装公共响应 | Agent 查询 Service 已有示例；完整认证、范围过滤、调度客户端及 Chat 映射不能当成已接线 |
| Claw 配置服务 | 校验任务字段与时间，处理请求幂等和配置版本，在事务内读写配置，返回完整保存结果 | 复用时间解析能力及已有 MyBatis 宿主；Controller、Service、Repository/Mapper 接线待实现 |
| Claw 数据库 | 保存配置、可信作用域、修订号及配置写请求结果 | 新增 `t_schedule` 配置部分与 `t_schedule_request`；不使用现有 `jobs.json` 作为 HTTP 成功依据 |

Mate 到 Claw 必须是受认证的内部服务调用，另带由 Mate 构造、绑定操作者和管理范围的可信上下文。Claw 不接受浏览器直接提交 `tenantId`、`ownerId`、授权结果或内部 `sessionId`；每次查询也按可信范围过滤。此上下文适配属于待实现接口，现有 `RuntimeRequestContext` 读取 Header 并不证明其真实性。公司服务认证制品及范围字段的实际映射尚未核验，不能以普通可伪造 Header 替代。

保存只证明该次检查和配置事务成功。Mate 的 Agent 定义可能在校验后变化；两库之间不宣称原子事务，也不持 Claw 数据库锁查询 Mate。到期执行必须重新核验 Agent 和执行权限，这个事实不要求配置页面触发目录发布或模型调用。

## 3. 页面字段与 Claude 的映射

| 页面项 / JSON | 行为 | 与现有系统的关系 |
|---|---|---|
| 名称 `name` | 必填，去首尾空白后 1～128 字符；同作用域可重名，身份使用服务端 ID | 当前 CronJob 已有 name；不以名称去重创建 |
| 说明 `description` | 可选，最多 2048 字符；空白归一为 null | 只给人阅读，不附加到模型任务 |
| Agent `agentId` | 必选；从授权候选中选择，保存时重新检查 | 绑定业务 Agent 身份；不复制 Agent 的模型、工具或 SYSTEM 配置 |
| 执行目标 `target` | 首期固定 `{ "type": "newSession" }`，页面显示“每次创建独立会话” | 不要求已有 Chat；第二阶段才提供 existingChat |
| 每次任务 `prompt` | 非空白纯文本，保留正文空白；上限复用普通文本消息的 262144 个 Java 字符；不执行插值或拼接隐式指令 | 对应一次初始 user.message 的文本。首期不接受任意 initial_events、system.message、附件或凭据 |
| 时间 `schedule` | 可为 null；非空是 at/every/cron 联合类型，整体校验/替换 | null 表示未配置自动时间；不等于已提供手动运行能力 |
| 状态 `status` | 只读。新建 PAUSED；配置更新保持原状态；ARCHIVED 不可更新 | 启用与暂停不通过修改配置字段隐式完成 |

表单按“任务内容、执行目标、时间计划”组织；时间优先提供每天、工作日、每周、固定间隔、指定日期，高级 Cron 明确标注方言。页面不要求用户填写 Runtime 路径、模型内部参数或认证 Header。Agent 与目标从已有 Chat 入口带入时也必须向服务端重新读取，不能相信 URL 中的名称或归属。

Claude Deployment 把 Agent、环境、初始事件和可选时间放在一个资源中；这里复用其“保存可执行任务配置”的边界。当前系统没有可供用户选择的 Environment 资源，也没有可解析任意历史版本的 Agent 仓库，因此不新增空壳 `environmentId` 或 `agentVersion` 请求字段。Mate 返回的当前元数据版本只能作为展示信息，不能显示为“已固定执行版本”或“所有节点已发布”。这是产品范围与架构差异，非 Claude 同名字段的兼容实现。

## 4. 从打开表单到编辑成功

| 步骤 | 前端动作 | 服务端动作与回显 |
|---|---|---|
| 打开列表 | 请求任务第一页；支持名称、Agent、状态筛选 | Mate 校验范围，Claw 查询服务端列表；不使用浏览器本地会话索引 |
| 新建 | 打开空表单，读取配置选项和授权 Agent 候选 | 选项返回首期支持目标与规则；候选仅含 ID、名称、展示名，不返回 SYSTEM、permission 或工具定义 |
| 编辑时间 | 草稿中修改规则，防抖调用 preview；为每次请求附本地代次 | Claw 用统一时间策略返回规范规则、计算基准和未来最多五次时刻；不落库、不预约执行 |
| 保存 | 在发出前保存完整待确认提交快照与 Idempotency-Key，禁用重复提交按钮 | Mate 重新核验 Agent/作用域；Claw 重新校验字段，在同一事务保存配置和请求结果；提交成功才回包 |
| 成功回显 | 以返回资源替换已保存快照和 ETag，再展示详情 | 新建显示 PAUSED，更新显示返回的实际状态；计划预览单独展示，不混入实际调度游标 |
| 重新编辑 | GET 详情取得当前配置和 ETag，草稿另存 | POST 只传变更字段，同时传 If-Match 和新的 Idempotency-Key；事务锁内检查配置版本 |
| 并发冲突 | 保留草稿，读取最新版，展示变化；用户重新保存才产生新请求 | 返回 412；不自动拿新 ETag 重发原草稿 |

时间预览响应只能应用到产生它的草稿代次；切换 Agent、任务或目标时，旧请求即使晚到也不覆盖新草稿。保存期间允许取消页面等待，但不能把取消 fetch 当服务端撤销；返回页面后按原请求身份恢复保存结果。

列表使用一基 `pageIndex`、`pageSize`，默认 1/20、上限 100；按 `updatedAt DESC, id ASC` 排序。响应含 `data,total,pageIndex,pageSize`。这与现有 Agent 管理分页习惯一致；不同页之间不承诺固定快照，后续变化可导致跨页漂移。权限过滤必须在数据库分页与计数之前完成，不能先取一页再在前端删除未授权条目。

## 5. 公共与内部接口

以下均为新增 proposed 接口；不会改变现有 Chat Events 或 Agent 管理接口。JSON 使用 lowerCamelCase；普通成功必须有 `resCode/resMsg/result`，失败仅有 `resCode/resMsg`，保留真实 HTTP 状态。精确认证库待公司集成核验，产品契约采用 `X-HW-ID + Authorization: Bearer <JWT>` 或 `X-HW-ID + X-HW-APPKEY` 两种完整凭据对，恰好选择一组，冲突拒绝且验证失败不回退；页面由宿主身份客户端提供凭据，不建开发者 Token 输入框。

| 公共操作（Mate） | 功能与关键约束 | Claw 内部对应 |
|---|---|---|
| GET `/mate-service/v1/schedules/options` | 读取 supportedTargetTypes、supportedScheduleTypes、cronDialect、previewLimit；来自同一部署能力配置 | GET `/campusclaw-service/v1/schedules/options` |
| GET `/mate-service/v1/schedules/agents` | 查询可配置 Agent 摘要；pageIndex/pageSize/name；结果分页 | 无；复用 Mate 目录查询能力并增加范围过滤与安全投影 |
| GET `/mate-service/v1/schedules/agents/{agentId}` | 定点读取安全 Agent 摘要供详情回显；不在授权范围或不存在均404 | 无；复用 Mate 单项查询和相同权限过滤 |
| POST `/mate-service/v1/schedules/preview` | 输入 `{schedule}`，只校验/计算时间；schedule 必须非空 | POST `/campusclaw-service/v1/schedules/preview` |
| POST `/mate-service/v1/schedules` | 创建配置；必需 Idempotency-Key；201 + Location + ETag，result 为完整配置 | POST `/campusclaw-service/v1/schedules` |
| GET `/mate-service/v1/schedules` | 查询本范围任务摘要；支持 pageIndex/pageSize/name/agentId/status | GET `/campusclaw-service/v1/schedules` |
| GET `/mate-service/v1/schedules/{scheduleId}` | 读取完整已保存配置；200 + ETag | GET `/campusclaw-service/v1/schedules/{scheduleId}` |
| POST `/mate-service/v1/schedules/{scheduleId}` | 部分更新；必需 If-Match、Idempotency-Key；200 + ETag，result 为完整配置 | POST `/campusclaw-service/v1/schedules/{scheduleId}` |
| GET `/mate-service/v1/schedules/requests/{requestKey}` | 按原创建/更新请求键读取提交回执；仅原操作者与原管理范围可查；不执行配置变更 | GET `/campusclaw-service/v1/schedules/requests/{requestKey}` |

两跳传递相同的逻辑写请求身份，Mate 不给同一次重试生成新键。Claw 将键与可信作用域、操作者、操作和目标绑定，不存在单独面向浏览器的 Claw 入口。Mate 重建 Location 为公共路径，映射业务错误，不转发内部 URL、Session ID、堆栈或原始诊断。scheduleId 是 Claw 生成的公开业务 ID，大小写敏感、不可复用；无需为了隐藏它再复制一份配置或另建可变映射。

options 的 result 包含 `supportedTargetTypes:["newSession"]`、`supportedScheduleTypes:["at","every","cron"]`、`cronDialect:"spring6"`、`previewLimit:5`，以及 `constraints` 中的正整数或 null 字段 `minIntervalSeconds/maxIntervalSeconds/minCronIntervalSeconds`。null 表示该部署尚未配置执行准入范围，只允许保存暂停配置。声明支持不等于已交付，直到对应后端和页面通过验收才开放能力。候选与单项 Agent 摘要字段固定为 id/name/displayName/enabled；列表只返回可访问且 enabled=true 的项，单项可返回已禁用但仍有读取权的绑定，便于解释既有配置。普通详情回显不依赖在候选第一页找到 Agent。

新建必填 name、agentId、target、prompt；description、schedule 省略时由 Service 归一为 null。更新允许 name、description、agentId、target、prompt、schedule；至少一个字段，省略保持，description/schedule 显式 null 清除，其余 null 拒绝。target/schedule 为整体替换，不能只提交 timezone 或 chatId。先合并服务端原配置，再校验最终整体；失败全部不改。未知字段、错误 JSON 类型、只读字段输入均拒绝，不进行字符串/数字自动猜测。

对于 ACTIVE 的既有配置，更新不改状态；新 revision 只供之后受理的触发使用，在途执行仍用已接受的输入。修改时间为 null 清除未来自动时间；未改变 schedule 的正文修改不重置计划游标。具体到期领取与修改竞争由执行切片完善，不从配置更新成功推断在途取消。首期配置服务不自行安排 timer。

### 5.1 创建与回显示例

创建：`POST /mate-service/v1/schedules`，Header `Idempotency-Key: 0ca92847-fb58-4a9a-900f-8a7b26a71496`。

```json
{
  "name": "工作日园区告警汇总",
  "agentId": "agent-550e8400e29b41d4a716446655440000",
  "target": { "type": "newSession" },
  "prompt": "汇总园区过去24小时的设备告警，并标出需要跟进的工单。",
  "schedule": {
    "type": "cron",
    "expression": "0 0 8 * * MON-FRI",
    "timezone": "Asia/Shanghai"
  }
}
```

响应：HTTP 201，`Location: /mate-service/v1/schedules/schedule-927e03d2a4784f90a6238e790539c6e4`，`ETag: "scfg-1"`。

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
    "prompt": "汇总园区过去24小时的设备告警，并标出需要跟进的工单。",
    "schedule": {
      "type": "cron",
      "expression": "0 0 8 * * MON-FRI",
      "timezone": "Asia/Shanghai"
    },
    "status": "PAUSED",
    "revision": 1,
    "createdAt": "2026-09-29T12:00:00Z",
    "updatedAt": "2026-09-29T12:00:00Z"
  }
}
```

配置列表使用上述资源的摘要：id/name/agentId/target/status/schedule/revision/createdAt/updatedAt，省略 prompt/description。详情不混入运行统计、实际调度游标或会随目录变化的 Agent 聚合字段；UI 的 Agent 展示信息从授权目录单独取得，已失效的绑定显示“Agent 当前不可用”。ETag 标识整个配置表示；后续启停/归档改变配置状态也必须递增配置 revision，运行进展由独立查询维护。

编辑为工作日 09:00：`POST /mate-service/v1/schedules/{scheduleId}`，`If-Match: "scfg-1"`，使用本次新的 Idempotency-Key。

```json
{
  "schedule": {
    "type": "cron",
    "expression": "0 0 9 * * MON-FRI",
    "timezone": "Asia/Shanghai"
  }
}
```

成功返回同形完整资源及 `ETag: "scfg-2"`；name/Agent/任务内容/status 保持。`{"schedule":null}` 清除自动时间；`{}` 和 `{"schedule":{"timezone":"UTC"}}` 均拒绝。更新同值不增加 revision；请求幂等结果仍要记录。

### 5.2 时间联合类型与预览

| type | 完整输入 | 配置规则 |
|---|---|---|
| at | type、at、timezone | at 为带 UTC offset 的 ISO 8601 时间，按其绝对时刻解析，响应规范化 UTC；timezone 为有效 IANA，仅决定本地展示。允许 UTC 响应原样再提交；保存新规则时须仍在未来 |
| every | type、intervalSeconds、startAt、timezone | intervalSeconds 为正整数；startAt 是带 offset 的明确起点，规范化 UTC且必须在未来；同一已保存规则编辑其他字段时不重新要求旧起点在未来。周期定义为固定起点的间隔序列，非上次结束后延迟 |
| cron | type、expression、timezone | 明确使用现有 Spring 六字段语法，必须指定 IANA；高级输入拒绝五字段，不默默补秒；首期表单常用选项生成六字段表达式 |

预览 every 可以用已过去的 startAt 计算之后的 occurrence；未来起点约束只在创建/替换为新规则时检查，不能阻止已有周期配置的预览。at/every 上的 timezone 用于回显本地时刻，不把固定秒间隔解释为本地日历的“每天”。只有创建/实际替换规则时检查新起点在未来；原配置读取、名称修改及原键重试不因时间流逝失败。相同规范规则按未修改处理。

Cron 的六字段是对现有解析能力的兼容选择；Claude 是五字段 POSIX。接口不声称兼容 Claude 原报文。若产品决定公开五字段，应另选并核验 POSIX 解析语义、星期/日期组合和 DST，再调整契约；不能仅在字符串前加 `0` 宣称完全等价。本切片未增加 Maven 依赖。

预览响应 result 为 `{schedule, computedAt, upcomingRunsAt}`：computedAt 由服务端采样，upcomingRunsAt 是严格晚于它的最多五个 UTC instant，按配置 timezone 展示。at 只返回一个；新规则无未来匹配拒绝并定位时间。前端可显示本地日期、星期、offset 和时区，不自行计算第二套计划。配置详情不返回会独立变化的实际 nextFireAt；“假设启用后的计划预览”单独读取，PAUSED 也可显示。旧配置的单次时间已过时，详情仍可读取和修改名称；预览明确提示时间已过，不抹去原配置。

预览与保存复用 `ScheduleTimePolicy` 的同一解析与计算逻辑，保存重新计算，不提交预览 token；时区与时间库边界测试是实现验收项。最小频率、最大间隔及配额由服务端部署策略约束并通过 options 返回有效范围；未配置可执行范围前只开放暂停配置，不能把解析成功视为容量承诺。

## 6. 保存时序与一致性

场景是保存一份新的告警汇总配置，从点击保存到数据库提交并回显结束。前提是操作者已登录；图为待实现目标。Browser、Mate、Schedule、Store 分别是页面、公共权限边界、Claw 配置应用服务和唯一数据库权威，不代表四个必然独立进程；不包含到期运行。

![定时任务配置保存](schedule_configuration_save.svg)

[原尺寸 SVG](schedule_configuration_save.svg) · [PlantUML 源码](diagram.puml#L134)

关键不变量：

1. Mate 在数据库事务外完成认证、Agent 绑定和管理权限检查。Claw 验证可信调用上下文和字段，不能因为页面预览成功就跳过保存检查；此管理操作无模型工具确认环节。
2. 配置与成功的幂等结果在同一 Claw 事务提交；数据库写失败必须回滚并返回失败。不能沿用 `CronStore.saveUnsafe` 吞写失败后返回成功的行为。
3. 创建在范围、操作者和请求键上唯一；更新锁定范围内配置并检查 If-Match，在同一事务写入全部变更及 revision。配置版本独立于 Run 进展和统计；执行增量不能不断制造编辑冲突。
4. Claw 的幂等检查在格式/可信身份校验后、时效及 If-Match 重验前：到达 Claw 的同键同请求返回已提交原响应；同键不同请求返回409。若尚未提交可串行等待或返回请求进行中，不能两次创建。请求指纹包括规范请求、操作、目标和原 If-Match，不能跨用户或目标重放。公共 POST 仍经过 Mate 的当前 Agent 检查，不承诺跨 Agent 禁用或权限变化返回旧成功；恢复已提交事实以独立的只读回执为准，不能把后来的 POST 拒绝当作原请求未提交。
5. 两跳任一回包丢失，先 GET 原请求键的只读提交回执：200 的 result 为 `{scheduleId, revision}`，再 GET 当前详情。仅校验当前身份、原操作者与资源管理范围，不因 Agent 后来禁用而隐藏已提交事实。未查到返回404 `SCHEDULE_REQUEST_NOT_FOUND`，只代表尚无可见提交结果，不能证明原请求未在途；允许按原键、原快照和原 If-Match 重试，仍由唯一约束串行决定一次提交。不能因404更换新键自动创建。
6. 请求键记录至少与配置及其归档记录同寿命；清理响应正文后保留键、指纹和结果身份，返回明确的结果过期冲突，不把旧键当成新请求执行。归档后 ID 不复用。

配置持久化包含：`t_schedule` 的 id、可信 scope、agent_id、target_type、可空内部目标绑定、name、description、prompt、schedule、status、revision、created/updated_at 与操作者审计；`t_schedule_request` 的 scope/actor/key 唯一约束、操作/目标、指纹、结果身份/版本和原响应。无 Token、APPKEY 或登录 Header。精确 GaussDB 类型、SQL 与索引在实现切片生成，表名遵守 `t_`，SQL COMMENT 使用中文。

请求键是客户端生成的 UUID 请求关联值，不是 scheduleId；在同一可信 scope/actor 内不得跨操作复用，operation/目标参与指纹，保证回执查询唯一。未发送表单草稿留内存；点击保存时，前端先在按后端/作用域/操作者隔离的本地待确认存储中写入请求键、操作、目标、原 If-Match 和完整提交正文，写入失败则不发 POST。这样即使原请求根本未到服务器，刷新后仍能读取原快照并按原键重试，不会只剩一个无法解决的查询键。正文包含用户任务内容，但不含 Token 或认证 Header；确认后清理，退出登录清除本地副本，身份切换不展示另一身份的记录。用户主动清理浏览器数据会丢失本地恢复信息，不以此推断服务端未保存。所有配置及回执响应 `Cache-Control: no-store`；跨域部署须显式暴露 ETag/Location/Content-Language 并允许 If-Match/Idempotency-Key。

Java 对象边界采用 `ScheduleCreateRequestVO`、`ScheduleUpdateRequestVO`、`SchedulePreviewRequestVO`、`ScheduleResponseVO`；Controller 包装 ResultBean，Service 做规范化与 VO/DTO 转换，Mapper 只接收 DTO。更新绑定必须保留“未出现”和“显式 null”的区别，不能用普通可空字段丢失清除语义。请求 VO 无默认值，格式校验用 Jakarta，跨记录规则在 Service，数据库保留唯一与版本最终约束。

全局结构复用[模块目标类图](README.md#10-全局目标类图与依赖)。配置服务、时间策略、Repository/Mapper 为 Spring 单例；页面草稿和写请求快照按请求隔离。配置服务不依赖执行协调器或 Session 工厂，UI/API/CronTool 未来可共用应用服务；旧工具迁移前不允许把两套存储的任务合并为一个看似统一的清单。

## 7. 错误、权限与第二种目标

| HTTP / 稳定 resCode | 页面处理 |
|---|---|
| 400 `SCHEDULE_NAME_INVALID` / `SCHEDULE_PROMPT_INVALID` / `SCHEDULE_RULE_INVALID` / `SCHEDULE_TIMEZONE_INVALID` | 按码定位对应表单项，保留草稿；resMsg 用于说明，不解析文案 |
| 400 `SCHEDULE_REQUEST_INVALID` | 请求字段、类型、只读字段或目标形状错误；显示表单提示，不尝试猜值 |
| 401 `SCHEDULE_AUTH_REQUIRED` / `SCHEDULE_AUTH_CONFLICT` | 宿主重新登录或修复凭据；不静默降级到另一认证方式 |
| 403 `SCHEDULE_MANAGE_FORBIDDEN` | 无创建/管理功能权限；不发下游写入 |
| 404 `SCHEDULE_NOT_FOUND` / `SCHEDULE_AGENT_NOT_FOUND` | 不存在或不在访问范围，避免泄露；绑定不可用时保留其他草稿 |
| 409 `SCHEDULE_AGENT_DISABLED` / `SCHEDULE_ARCHIVED` | 当前状态阻止保存；提示修复，不通过历史缓存绕过 |
| 409 `SCHEDULE_REQUEST_CONFLICT` / `SCHEDULE_REQUEST_IN_PROGRESS` / `SCHEDULE_REQUEST_RESULT_EXPIRED` | 键内容不符、尚在处理或历史回执已清理；不得换键自动重发 |
| 428 `SCHEDULE_VERSION_REQUIRED`；412 `SCHEDULE_VERSION_CONFLICT` | 补充初次读取；或保留草稿并比较最新版本，不自动覆盖 |
| 422 `SCHEDULE_TARGET_UNSUPPORTED` | 首期拒绝 existingChat；不悄悄改成 newSession |
| 503 `SCHEDULE_SERVICE_UNAVAILABLE` | 明确服务不可用；网络或网关结果不确定保留原键，按 §6 恢复 |

错误体只有 resCode/resMsg，不增加未经约定的 fieldErrors；先返回按请求字段顺序确定的一个错误。每个错误 enum、resCode、MessageSource key 同名；支持 zh-CN/en-US，缺省或不支持回退 zh-CN，并返回实际 Content-Language。普通成功为三个固定字段；不复制 Mate 示例“更新省略 result”的行为。精确公司认证 Adapter 待集成，但认证成功、授权范围、错误投影必须分别验收。

第二阶段 `target={type:"existingChat",chatId:"..."}`。只用公共 chatId；Mate 验证 Chat 访问权与 Agent 归属，解析内部 Session 绑定后交 Claw。页面从当前 Chat 入口进入时展示只读归属 Agent；手选 Chat 的目录接口另随公共 Chat 管理契约提供。首期 options 仅返回 newSession，服务端也拒绝 unsupported 输入，不能只隐藏控件。保存无需要求目标 Session 此刻 idle；忙时如何投递属于运行准入，不能把当前瞬时 busy 变成无法保存长期配置。

## 8. 实施与验收

| 切片 | 验收结果 |
|---|---|
| 配置后端骨架 | DTO/VO、MyBatis、两张表及可信 scope 隔离；创建/更新事务回滚，写失败无成功回包；保存不调用模型、prepare、Session 工厂或 CronEngine |
| Mate 公共边界 | 授权后候选分页与安全摘要；每次写入重新检查 Agent；鉴权、租户/操作者范围、两跳错误与幂等键保持；不存在浏览器直连回退 |
| 时间预览 | 常见表单与高级输入共用服务端规则；IANA、DST、无未来匹配、单次时间过期、every 起点、preview 乱序可验证；文档示例的工作日时刻正确 |
| 页面闭环 | 列表→新建→预览→保存→详情→刷新→编辑；规范化资源和 ETag 一起替换；失败不清草稿，断网按原键恢复，412 不覆盖他人修改 |
| 并发与恢复 | 两个相同键只创建一条配置；不同正文同键409；两跳回包丢失返回同一资源；两个相同版本更新只有一个成功；旧键过期不产生新配置 |
| 执行衔接 | 配置提交不启动；启用/手动运行另行交付；未来 worker 只读取同一权威配置，既有工具迁移也不旁路写 jobs.json |

复用 JDK、现有 Spring CronExpression/Jackson、宿主 MyBatis 3.0.4 与数据库驱动，不新增直接 Maven 或前端表单依赖；未运行完整依赖树，不宣称传递依赖已审计。Vue 页面沿既有组件/Composition API，是否引入路由库须在实现需求出现时独立评估。

尚未核验的公司认证库、内部可信上下文映射和完整 Mate Chat 授权必须在产品接入前补齐；这不授权保存登录凭据或把 Agent enabled 当使用权限。本切片不冻结多节点触发、重叠、补跑和故障接管策略，也不把配置提交测试替代调度执行验收。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.0 | 2026-09-29 | 建立 Mate 公共入口到 Claw 单一配置存储的加载、预览、保存、回显与并发编辑闭环。 |
