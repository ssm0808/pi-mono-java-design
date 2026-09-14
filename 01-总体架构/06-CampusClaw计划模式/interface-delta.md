# 计划模式接口增量

版本：1.6.0；日期：2026-09-14；状态：**target-only 推荐设计，统一 Session 更新与 requested 模式事件已登记；计划审核部分尚未纳入当前报文源，全部新增能力仍待实现**。

本文件只定义计划功能的新增内容。现有 Header、普通消息、工具确认、ResultBean、SSE 和历史分页继续引用[当前契约](../01-CampusClaw多Agent运行时/chat-api-review.html)。这里的报文属于目标增量示例，正式纳入时移入统一 operation JSON 和 `eventContract`，本文件随后仅保留理由及链接，不产生第二份当前接口契约。

## 1. Session 配置与审核交互边界

名称、模型、思考和模式已统一登记到 `POST /campusclaw-service/v1/sessions/{sessionId}`（updateSession）。精确请求、单字段与组合示例、原子性、错误和 Header 只由[操作 07](../01-CampusClaw多Agent运行时/接口契约/操作/07-update-session.json)维护；设计理由见[HTTP 主设计 §2.4](../01-CampusClaw多Agent运行时/chat-http-v1-design.md#24-模型目录与统一-session-更新)。本文件不再维护模式更新报文副本。

mode 已是共享 Session 响应必填字段，创建复制 Agent.mode，旧元数据缺省 build，已有 Session 不跟随 Agent 更新；state 仍为 idle/running。仅名称请求可在 running 更新；只要携带 mode/modelId/thinking，均需 idle、If-Match 与一次原子提交。主动设置 build 不批准计划、不启动模型。

GET、创建、更新及复用 Session 的 Command 响应保持同一种 Session 结构，不增加待审核目标字段。计划及审核决定通过 Events 传递，卡片按[主设计 §6.2](README.md#62-恢复与结果不确定)从完整事件恢复。当前待审核目标仅保存在服务端执行控制记录中，确认接受时锁内校验；不新增状态查询接口或可写审核字段。

## 2. 提交审核决定

复用 `POST /campusclaw-service/v1/sessions/{sessionId}/events`，联合输入增加 `user.plan_confirmation`。沿用现有 POST 的调用上下文及必填 `access-token`；请求凭据不覆盖原消息执行的内存凭据。

批准完整方案：

```json
{
  "event": {
    "type": "user.plan_confirmation",
    "targetEventId": "evt-plan-H7qJ4mS9vT2c",
    "result": "approve"
  }
}
```

退回修改：

```json
{
  "event": {
    "type": "user.plan_confirmation",
    "targetEventId": "evt-plan-H7qJ4mS9vT2c",
    "result": "revise",
    "feedback": "先给出故障定位步骤，维护窗口另行安排。"
  }
}
```

| 字段 | 规则 |
|---|---|
| `type` | 固定 `user.plan_confirmation` |
| `targetEventId` | 必填非空不透明字符串，最多 128 UTF-16 单元，精确引用当前待审核计划的公共 eventId；不是 toolCallId 或根消息 ID |
| `result` | 必填 `approve` 或 `revise`，不接受同义词、大小写变体或普通聊天文本自动推断 |
| `feedback` | 仅 revise 可选；存在时必须为非空文本，最多 4096 UTF-16 单元；approve 禁止出现，包括 null |

不接受调用方传入修改后的计划正文。需要修改时先 revise，Agent 产生新的完整 `agent.plan` 后再批准新 eventId。请求只表述一个决定，不批量批准。

请求反序列化必须保留 feedback 是否出现的区别，再做 result/feedback 联合校验；不能仅凭一个可空字符串把“省略”和“显式 null”视为同一种输入。格式校验使用请求 VO 与现有 Jackson 边界，审核目标及竞争规则仍在 Service 事务内检查。

成功仍为 `200 text/event-stream`：第一个业务帧是本次已提交的完整 `user.plan_confirmation`，然后是固定续跑段输出；收到该段 `session.status_idle` 后关闭。SSE data-only，不包装 ResultBean，不使用 `id:` 或 `Last-Event-ID`。

| HTTP / resCode | 触发条件 |
|---|---|
| 400 / `INVALID_EVENT_REQUEST` | 字段、枚举、反馈、包装或 POST 凭据不满足现有及新增格式约束 |
| 404 / `SESSION_NOT_FOUND` | Session 不存在或已删除 |
| 409 / `PLAN_CONFIRMATION_NOT_PENDING`（新增） | 没有有效计划等待、targetEventId 不匹配、重复决定或目标不属于当前 Session/分支 |
| 409 / `EXECUTION_STOPPING` | 原执行已接受中断，不再接受确认 |
| 503 / `EVENT_SERVICE_UNAVAILABLE` | 接受前无法预留既有输出/等待容量 |
| 500 / `EVENT_ACCEPTANCE_FAILED` | 确认接受事务失败并回滚 |

同一个 Session 存在时，不通过“目标在其他 Session”与“目标不存在”的差异错误泄露其他 Session 数据。锁内先检查停止状态，再检查审核目标；该顺序与工具确认的停止优先规则一致。

确认接受后发生续跑故障，继续使用现有可靠终态/结果不确定规则；不能改回一个声称“未接受”的普通 JSON。客户端不得自动重放确认 POST。

## 3. 完整事件

公共 eventId 由服务端生成、精确比较且不复用，示例值仅为不透明占位；不规定其中前缀结构。所有完整事件的 createdAt 为一次保存的 UTC 毫秒时间。SSE 与 GET 历史复用相同投影，不把 Provider 原始事件直接转发。

### 3.1 `agent.plan`

```json
{
  "eventId": "evt-plan-H7qJ4mS9vT2c",
  "type": "agent.plan",
  "createdAt": "2026-09-14T03:20:00.000Z",
  "sourceEventId": "evt-msg-R8kD2pW5nL6x",
  "toolCallId": "call_plan_01",
  "content": "# 园区网络故障处置计划\n\n1. 查询告警及影响范围。\n2. 核对设备配置与最近变更。\n3. 根据定位结果提出维护操作和回退步骤。\n4. 经工具权限确认后实施并验证。"
}
```

上述字段全部必填。`content` 是经校验后原样保存的完整 plan 字符串；不从 Assistant 普通回答用正则提取，不根据网页编辑后的内容重新计算方案。`sourceEventId` 沿用原始 `user.message.eventId`；`toolCallId` 关联对应 ExitPlanMode 调用。无 phase，不提供计划正文的 token 增量事件。

同一计划同时存在模型 ToolCall 与公共展示事件是两种投影：模型恢复使用原 ToolCall，审核使用 agent.plan 的 eventId。两个投影在提交时校验正文完全一致，不分别生成、修剪或二次解析。前端把关联的 ExitPlanMode 调用折叠到计划卡片，避免展示两份正文。

### 3.2 `user.plan_confirmation`

```json
{
  "eventId": "evt-confirm-M3pX8aV2kQ7n",
  "type": "user.plan_confirmation",
  "createdAt": "2026-09-14T03:21:00.000Z",
  "targetEventId": "evt-plan-H7qJ4mS9vT2c",
  "result": "approve"
}
```

在规范化请求字段上增加公共 eventId 和 createdAt；revise 携带被接受的 feedback。无 phase，不额外增加 sourceEventId；通过 targetEventId 查找对应计划及原根消息。

### 3.3 `session.mode_changed`

主动更新的 reason=requested 模式事件已登记在[共享事件契约](../01-CampusClaw多Agent运行时/事件契约/common.json)，示例由[历史操作](../01-CampusClaw多Agent运行时/事件契约/操作/02-list-session-events.json)维护。以下仅为计划批准的目标扩展。

批准导致退出时保存：

```json
{
  "eventId": "evt-mode-K9bF2wP6sL3q",
  "type": "session.mode_changed",
  "createdAt": "2026-09-14T03:21:00.000Z",
  "previousMode": "plan",
  "mode": "build",
  "reason": "planApproved",
  "sourceEventId": "evt-msg-R8kD2pW5nL6x",
  "confirmationEventId": "evt-confirm-M3pX8aV2kQ7n"
}
```

reason=requested 时不带 sourceEventId/confirmationEventId，只进入历史，统一 Session POST 本身返回 JSON。reason=planApproved 时二者必填，模式只能 plan→build；该完整事件进入确认续跑段 SSE 和历史。sourceEventId 仍指根消息，confirmationEventId 明确批准因果关系，不混用两种身份。

### 3.4 既有事件的使用

- ExitPlanMode 的 `agent.tool_call` 保持原结构，`toolName=ExitPlanMode`、`arguments={plan}`、`requiresConfirmation=false`。计划审核由 agent.plan 表达，不能同时生成一次工具权限审核。
- 进入审核等待仍使用 `session.status_idle(reason=confirming)`；它不释放 Session running。
- 批准/修订后的 `agent.tool_result` 保持 `toolCallId/content/isError`；正常批准与正常修订均 `isError=false`，无 errorCode。
- 原始 user.message、修订后生成的计划、后续业务工具及最终回答均按同一个根消息的 sourceEventId 关联，直到原执行真实结束；普通澄清后新发 user.message 则形成新的根执行。

计划工具新增稳定失败码：`PLAN_MODE_INACTIVE`（当前模式不允许提交计划）、`PLAN_REVIEW_UNAVAILABLE`（不支持审核或当前调用不满足独占审核条件）。按现有工具错误映射保存安全文本；不把用户反馈字符串直接当作 errorCode。

### 3.5 TodoUpdate 复用通用事件

TODO 仅在 build 实施阶段记录进度，使用现有 agent.tool_call / agent.tool_result，精确工具输入输出及示例见 [TodoUpdate](todo-update.md#3-事件与执行顺序)。不新增 TODO 专用 event.type、公共字段、用户输入分支、Session 属性或 HTTP 路径；成功结果的 content 文本承载完整 JSON 清单。服务端执行内置工具，浏览器只观察，不引入 Claude 的客户端工具结果提交协议。agent.plan 继续只表示完整待审核方案。

## 4. 发布联动清单

| 维护位置 | 同批需要完成的增量 |
|---|---|
| Runtime catalog / operation JSON | 统一 Session 更新与 mode 已登记；Session 响应不增加待审核字段，POST 联合输入和 GET 历史增加计划/确认及批准模式事件 |
| Runtime eventContract / DTO / VO / 编码器 | 增加三种类型、条件字段和错误码；保留原三种输入、原失败码及分页/凭据边界 |
| 主接口 HTML 与校验器 | 从统一 JSON 生成；接口数量、完整类型集合、首帧样例和流/历史同形检查同步，不能通过删除既有检查适配新功能 |
| 内置工具契约 | 登记 ExitPlanMode、TodoUpdate 和 Runtime 默认 profile；原八项工具 Schema 与 Tool/Skill 元数据保持原值；Agent 新增 mode 的定义及发布链路见元数据主设计 |
| Runtime 调试前端 | Session mode 类型与更新；基于事件的审核卡片、确认发送及历史恢复，恢复未完成时禁用审核；TODO 按通用成功结果投影，失败不更新 |
| Mate 产品集成 | 公共 Chat 模式配置、确认输入、三类事件投影和双跳 ID 映射单独落到 Mate 契约，接通后才能向企业浏览器开放 |

所有新增失败码同时维护 Java 枚举、resCode 和 MessageSource 同名 key，保持 zh-CN/en-US 键集合一致。新增请求 VO 使用标准 Jakarta 校验，模式/目标/竞争检查放在 Service 与数据库事务，不新增自定义元数据校验注解。
