# 查询 Chat Events 决策

| 属性 | 值 |
|---|---|
| 负责任务 | `Mate Chat · 历史事件` |
| 状态 | `proposed`（分页设计重新打开） |
| operation | `GET /mate-service/v1/chats/{chatId}/events` |
| 最近更新 | 2026-09-03 |

## 仍然有效的已确认摘要

- 返回八种完整、可恢复、可审计事件，不包含 delta、SSE ping 或内部事件。
- `createdAtGte` 是包含三位毫秒的 RFC 3339 UTC inclusive 下界。
- `types` 是重复 query 参数，使用 OR 语义，重复值归一化。
- 历史用于断线后替换 preview，并按 `eventId` 对账。

## 已确认的新要求

- `page` 和 `nextPage` 不使用加密或 opaque cursor；对外展示 `1、2、3` 等一基数字页码。

## 待解决冲突 C-001

Events 1.4.4 通过 opaque cursor 保存过滤条件、快照上界和续读位置，从而保证固定快照。
数字页码只表达页序号，不能独立表达这些信息。当前候选设计是：

- `page` / `nextPage` 使用一基 `int32`；
- 第一页返回公开的 `snapshotEventId`，后续页原样提交；
- 后续页重复 `limit` 和 `types` 等过滤条件；
- 服务端用 `snapshotEventId` 解析固定上界，并在该上界内执行稳定分页；
- `createdAtGte` 是否在后续页重复，需与完整 query 形状一起确认。

这只是候选方案，未得到用户确认前不得修改 operation 和聚合契约。

## 交接

```text
operation: GET /mate-service/v1/chats/{chatId}/events
status: proposed
confirmed decisions: page/nextPage 改为一基数字页码；既有八类完整历史和过滤语义继续有效
cross-operation impact: 断线恢复算法、OpenAPI 查询参数、成功响应和分页错误码
changed owned files: 协作/决策/05-list-chat-events.md
unresolved: 数字页码与固定快照的完整请求/响应字段
```
