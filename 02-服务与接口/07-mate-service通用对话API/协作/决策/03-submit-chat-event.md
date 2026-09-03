# 提交 Chat Event 决策

| 属性 | 值 |
|---|---|
| 负责任务 | `Mate Chat · 提交事件` |
| 状态 | `validated`（Events 1.4.4）；允许重新评审 |
| operation | `POST /mate-service/v1/chats/{chatId}/events` |
| 最近更新 | 2026-09-03 |

## 已确认摘要

- 一次提交一个 `user.message`、`user.interrupt` 或 `user.tool_confirmation`。
- 不能在同一请求中组合 interrupt 与 message；等待 `terminated` 后再发 message。
- `toolCallId` 原样使用 OpenAI Tool Call ID，不施加前缀或长度正则。
- 成功响应在 `result.event` 返回实际持久化的完整用户事件。
- `user.*` 不在实时流中重复发送；POST 响应丢失时查询历史，不能盲目重放。
- Mate 不声明 `Accept-Language`。

## 交接

```text
operation: POST /mate-service/v1/chats/{chatId}/events
status: validated
confirmed decisions: 见 Events 1.4.4 operation 和上述摘要
cross-operation impact: StreamEvents 的确认/终止状态；ListEvents 的三种 user.* 完整形状
changed owned files: 当前无
unresolved: 重新评审时逐项记录
```
