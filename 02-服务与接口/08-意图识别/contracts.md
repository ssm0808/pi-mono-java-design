# 意图路由与任务接续业务契约草案

| 属性 | 值 |
|---|---|
| 版本 / 日期 | 0.2.0 / 2026-10-13 |
| 状态 | 待实现；语义示意，HTTP 路径、字段、Schema 及外层协议未冻结 |
| 来源 | [主设计](意图识别重构设计.md#interfaces)前版的字段和示例，按当前边界整理 |

这是业务关联负载，不是 OpenAI 模型 API 原生字段，也不能直接提交给当前 CampusClaw Session Events。正式契约评审应统一鉴权、标识格式、错误映射、幂等及版本兼容；本文不另建一份声称已批准的 HTTP 规范。

<a id="input"></a>
## 1. 用户消息

| 字段 | 语义与约束 |
|---|---|
| `chatId` | 当前独立聊天，必须验证访问权限 |
| `messageId` | 本次逻辑提交的稳定标识；重传保持不变，新的内容用新值 |
| `interactionId` | 回复业务待补充项时携带；新问题不沿用旧关联 |
| `expectedVersion` | 该问题或动作的预期版本；不得与展示项版本混为一谈 |
| `text` | 原始输入；用户选择回复对象时保留内容，不要求重新输入 |

用户和租户取自鉴权，后端从可信记录得到处理方，不允许前端任意指定另一个 `agentId` 接续。示例标识只演示关联，不表示已确定标识格式。

```json
{
  "chatId": "chat-example-01",
  "messageId": "message-example-02",
  "interactionId": "interaction-example-01",
  "expectedVersion": 1,
  "text": "三号楼502设备间"
}
```

同一去重作用域内相同 ID 不同内容是冲突，不覆盖先前答案。新问题和无明确标识的追问进入归属判断；携带失效标识的回复不能被当成无标识输入。

<a id="internal"></a>
## 2. 两侧任务关联

| 方向 | 必须表达的业务语义 |
|---|---|
| 中心到 Claw | 根任务、父 Session、具体处理方及可信身份；接续时包含子任务、原业务待补充项、答案与稳定投递标识 |
| Claw 到中心 | 可信任务及子任务关联、一次执行标识、处理状态、公开结果或缺少信息的结构化描述 |
| MainAgent 到 SubAgent | 明确目标、相关原话、事实与来源、先前结果、补充答案、限制和预算；权限来自执行上下文，不由模型自报 |
| SubAgent 到 MainAgent | 本次完成结果或 `UserInputRequired`；异常仍按错误语义回传，缺字段不是编造成功结果 |

系统分配并绑定标识，模型可以提出目标和标题，不能自行决定关联到任意任务。`subTaskId` 在补充后不变，`invocationId` 每次执行不同。新增字段放在哪里、与现有 `user.message` 的关系、受理与应用回执的错误码、超时和容量限制均为 **【缺口】**。

现有 `user.question_answer` 按 `targetEventId` 提交整批答案，用于原执行仍在等待的调用。它不是本稿 `interactionId` 的同义字段。业务接续的 invocation 已结束时，不能伪造一个原问题事件去调用该控制接口；须先冻结独立适配方式。

<a id="display"></a>
## 3. 前端展示

```json
{
  "schemaVersion": "1.0",
  "eventType": "user_input_required",
  "eventId": "evt-example-01",
  "itemVersion": 4,
  "chatId": "chat-example-01",
  "taskId": "task-example-01",
  "subTaskId": "subtask-example-02",
  "title": "设施漏水报修",
  "status": "waiting_input",
  "interaction": {
    "interactionId": "interaction-example-01",
    "kind": "missing_fields",
    "question": "请提供漏水设施的楼栋和具体位置。",
    "requiredFields": ["building", "location"],
    "expectedVersion": 1,
    "expiresAt": "2026-10-13T18:00:00+08:00"
  }
}
```

`expiresAt` 仅为示例，不代表约定有效期。标题由业务配置或 MainAgent 的任务摘要生成，只用于阅读；归属由可信 ID 决定。

前端处理步骤：

1. 在完整业务事件或完整消息边界解码；验证 `schemaVersion`、事件类型和字段形态，不解析半段 JSON。
2. 用 `eventId` 去重，查找 `taskId + subTaskId` 对应项；根任务使用明确的根项键。
3. 只比较该项的 `itemVersion`，不让旧版本覆盖新状态；其他子任务的版本不参与比较。
4. 更新标题、状态、结果及专属回复入口；补充回复带 `interactionId/expectedVersion`，新问题不带旧问题标识。
5. 重连查询持久化快照并校对逐项版本，不把 token 流当历史数据源。

执行确认应使用不同的业务类型，绑定具体动作及版本；选择某项回复或补充位置不代表确认提交工单。外层保留现有 OpenAI-compatible 协议还是采用独立业务事件接口，仍待前后端契约评审；不得把这些自定义类型宣称为 OpenAI 标准事件。

## 4. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.2.0 | 2026-10-13 | 将示意契约从主设计分离，明确业务接续与原问题事件控制不可混用。 |
