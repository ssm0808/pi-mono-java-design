# 计划模式接口增量

版本：1.8.0；日期：2026-09-15；状态：**已确认目标契约；Session 更新、计划审核与显式任务事件均已登记到共享 JSON，运行时实现待独立验收**。

本文件维护计划接口的集成边界与理由。精确请求、完整事件、条件字段、错误码及示例由 [共享事件契约](../01-CampusClaw多Agent运行时/事件契约/common.json)、[POST 操作](../01-CampusClaw多Agent运行时/事件契约/操作/01-submit-session-event.json) 与 [GET 操作](../01-CampusClaw多Agent运行时/事件契约/操作/02-list-session-events.json) 唯一维护，并生成[统一接口页](../01-CampusClaw多Agent运行时/chat-api-review.html)。登记不代表 Java 或 Mate 已实现。

## 1. Session 配置与审核交互边界

名称、模型、思考和模式已统一登记到 `POST /campusclaw-service/v1/sessions/{sessionId}`（updateSession）。精确请求、单字段与组合示例、原子性、错误和 Header 只由[操作 07](../01-CampusClaw多Agent运行时/接口契约/操作/07-update-session.json)维护；设计理由见[HTTP 主设计 §2.4](../01-CampusClaw多Agent运行时/chat-http-v1-design.md#24-模型目录与统一-session-更新)。本文件不再维护模式更新报文副本。

mode 已是共享 Session 响应必填字段，创建复制 Agent.mode，旧元数据缺省 build，已有 Session 不跟随 Agent 更新；state 仍为 idle/running。仅名称请求可在 running 更新；只要携带 mode/modelId/thinking，均需 idle、If-Match 与一次原子提交。主动设置 build 不批准计划、不启动模型。

GET、创建、更新及复用 Session 的 Command 响应保持同一种 Session 结构，不增加待审核目标字段。计划及审核决定通过 Events 传递，卡片按[主设计 §6.2](README.md#62-恢复与结果不确定)从完整事件恢复。当前待审核目标仅保存在服务端执行控制记录中，确认接受时锁内校验；不新增状态查询接口或可写审核字段。

## 2. 提交审核决定

复用 `POST /campusclaw-service/v1/sessions/{sessionId}/events`，联合输入增加 `user.plan_confirmation`。沿用现有 POST 的调用上下文及必填 `access-token`；请求凭据不覆盖原消息执行的内存凭据。

POST 精确模型提供批准与修订两个请求示例，以及制作计划、批准执行和修订再提交的三个完整 SSE 场景。`targetEventId` 精确绑定当前待审核计划，审核输入不携带新的方案正文；条件反馈规则由同一模型与校验器执行。

不接受调用方传入修改后的计划正文。需要修改时先 revise，Agent 产生新的完整 `agent.plan` 后再批准新 eventId。请求只表述一个决定，不批量批准。

请求反序列化必须保留 feedback 是否出现的区别，再做 result/feedback 联合校验；不能仅凭一个可空字符串把“省略”和“显式 null”视为同一种输入。格式校验使用请求 VO 与现有 Jackson 边界，审核目标及竞争规则仍在 Service 事务内检查。

成功仍为 `200 text/event-stream`：第一个业务帧是本次已提交的完整 `user.plan_confirmation`，然后是固定续跑段输出；收到该段 `session.status_idle` 后关闭。SSE data-only，不包装 ResultBean，不使用 `id:` 或 `Last-Event-ID`。

接受前失败沿用 ResultBean；新增审核冲突码与稳定工具失败码由共享错误表维护，不另设控制接口。

同一个 Session 存在时，不通过“目标在其他 Session”与“目标不存在”的差异错误泄露其他 Session 数据。锁内先检查停止状态，再检查审核目标；该顺序与工具确认的停止优先规则一致。

确认接受后发生续跑故障，继续使用现有可靠终态/结果不确定规则；不能改回一个声称“未接受”的普通 JSON。客户端不得自动重放确认 POST。

## 3. 完整事件

公共 eventId 由服务端生成、精确比较且不复用，示例值仅为不透明占位；不规定其中前缀结构。所有完整事件的 createdAt 为一次保存的 UTC 毫秒时间。SSE 与 GET 历史复用相同投影，不把 Provider 原始事件直接转发。

### 3.1 `agent.plan`

`agent.plan` 是无 phase 的完整方案记录。内容原样来自已校验的 ExitPlanMode 参数，不从普通回答或网页内容重新提取；sourceEventId 保持原始消息归属，toolCallId 关联原调用。精确字段与长度约束见共享事件源。

同一计划同时存在模型 ToolCall 与公共展示事件是两种投影：模型恢复使用原 ToolCall，审核使用 agent.plan 的 eventId。两个投影在提交时校验正文完全一致，不分别生成、修剪或二次解析。前端把关联的 ExitPlanMode 调用折叠到计划卡片，避免展示两份正文。

### 3.2 `user.plan_confirmation`

在规范化请求字段上增加公共 eventId 和 createdAt；revise 携带被接受的 feedback。无 phase，不额外增加 sourceEventId；通过 targetEventId 查找对应计划及原根消息。

### 3.3 `session.mode_changed`

主动配置更新与计划批准的两种原因均由共享事件源维护；GET 的配置场景与计划批准场景分别给出完整示例。

reason=requested 时不带 sourceEventId/confirmationEventId，只进入历史，统一 Session POST 本身返回 JSON。reason=planApproved 时二者必填，模式只能 plan→build；该完整事件进入确认续跑段 SSE 和历史。sourceEventId 仍指根消息，confirmationEventId 明确批准因果关系，不混用两种身份。

### 3.4 既有事件的使用

- ExitPlanMode 的 `agent.tool_call` 保持原结构，`toolName=ExitPlanMode`、`arguments={plan}`、`requiresConfirmation=false`。计划审核由 agent.plan 表达，不能同时生成一次工具权限审核。
- 进入审核等待仍使用 `session.status_idle(reason=confirming)`；它不释放 Session running。
- 批准/修订后的 `agent.tool_result` 保持 `toolCallId/content/isError`；正常批准与正常修订均 `isError=false`，无 errorCode。
- 原始 user.message、修订后生成的计划、后续业务工具及最终回答均按同一个根消息的 sourceEventId 关联，直到原执行真实结束；普通澄清后新发 user.message 则形成新的根执行。

计划工具新增稳定失败码：`PLAN_MODE_INACTIVE`（当前模式不允许提交计划）、`PLAN_REVIEW_UNAVAILABLE`（不支持审核或当前调用不满足独占审核条件）。按现有工具错误映射保存安全文本；不把用户反馈字符串直接当作 errorCode。

### 3.5 TodoUpdate 显式任务事件

TODO 仅在 build 实施阶段记录进度。`agent.todo_updated` 已登记到共享 eventContract，POST SSE 与 GET 历史共用精确字段和示例；前端直接消费 todos，不再从通用工具记录推导。成功工具结果与任务事件同源同事务，失败不发任务更新；具体提交与恢复边界见 [TodoUpdate](todo-update.md#3-事件与执行顺序)。不新增用户输入、Session 属性、元数据字段或 HTTP 路径；agent.plan 继续表示完整待审核方案。

## 4. 发布联动清单

| 维护位置 | 同批需要完成的增量 |
|---|---|
| Runtime catalog / operation JSON | 已登记四输入、计划审核和批准模式事件；完整 Session 响应不增加待审核字段 |
| Runtime eventContract / DTO / VO / 编码器 | 实现已登记的 agent.todo_updated、审核类型、条件字段和错误码；保留原三种输入、原失败码及分页/凭据边界 |
| 主接口 HTML 与校验器 | 从统一 JSON 生成；接口数量、完整类型集合、首帧样例和流/历史同形检查同步，不能通过删除既有检查适配新功能 |
| 内置工具契约 | 登记 ExitPlanMode、TodoUpdate 和 Runtime 默认 profile；原八项工具 Schema 与 Tool/Skill 元数据保持原值；Agent 新增 mode 的定义及发布链路见元数据主设计 |
| Runtime 调试前端 | Session mode 类型与更新；基于事件的审核卡片、确认发送及历史恢复，恢复未完成时禁用审核；TODO 直接消费 agent.todo_updated，失败不更新 |
| Mate 产品集成 | 公共 Chat 模式配置、确认输入、计划审核与任务更新事件投影和双跳 ID 映射单独落到 Mate 契约，接通后才能向企业浏览器开放 |

所有新增失败码同时维护 Java 枚举、resCode 和 MessageSource 同名 key，保持 zh-CN/en-US 键集合一致。新增请求 VO 使用标准 Jakarta 校验，模式/目标/竞争检查放在 Service 与数据库事务，不新增自定义元数据校验注解。
