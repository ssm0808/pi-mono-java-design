# 实时 Chat Events 决策

| 属性 | 值 |
|---|---|
| 负责任务 | `Mate Chat · 实时事件` |
| 状态 | `validated`（Events 1.4.4）；允许重新评审 |
| operation | `GET /mate-service/v1/chats/{chatId}/events/stream` |
| 最近更新 | 2026-09-03 |

## 已确认摘要

- 长连接跨越多次 execution；`chat.status_idle` 不关闭连接。
- 业务帧只使用 `data:` JSON，保活使用 `: ping`；不使用 SSE `event:` 或 `id:`。
- 实时类型只有四种 `agent.*` 和 `chat.status_idle`；不重复发送 `user.*`。
- message/thinking 的 delta 是 preview，completed 是完整权威事件并复用同一 `eventId`。
- 流不重放，不接收 `Last-Event-ID` 或 sequence；断线后重开流并查询历史。

## 待重新评审项

- 公司 Swagger 不支持 `text/event-stream` 时，如何准确展示而不改变真实 HTTP 契约。

## 交接

```text
operation: GET /mate-service/v1/chats/{chatId}/events/stream
status: validated
confirmed decisions: 见 Events 1.4.4 operation 和上述摘要
cross-operation impact: ListEvents 是断线恢复的权威来源；SubmitEvents 提交确认但流不重复发送
changed owned files: 当前无
unresolved: Swagger 展示兼容方案
```
