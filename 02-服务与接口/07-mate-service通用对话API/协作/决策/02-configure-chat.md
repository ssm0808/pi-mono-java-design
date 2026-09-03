# 配置 Chat 决策

| 属性 | 值 |
|---|---|
| 负责任务 | `Mate Chat · 配置 Chat` |
| 状态 | `proposed` |
| 契约性质 | target-only |
| 最近更新 | 2026-09-03 |

## 当前输入

- 当前方向是将 `modelId` 和深度思考设置放在 Chat 配置，而不是放进 `user.message`。
- 每条 `user.message` 被接受时固定该次执行的配置快照；运行中修改不追溯影响当前执行。
- 深度思考的公共表达、默认值、可变时机和与模型能力的校验尚未确认。

## 待逐项评审

1. 单一更新接口还是模型、深度思考分别设置；
2. 方法、路径和部分更新语义；
3. `modelId` 与深度思考字段的类型、允许值和默认值；
4. active execution / confirming 期间能否修改；
5. 成功响应是否返回完整 Chat 配置；
6. 模型不支持深度思考时的稳定错误码。

## 交接

```text
operation: 待确认
status: proposed
confirmed decisions: 配置不进入 user.message；执行开始时使用配置快照
cross-operation impact: 创建 Chat、提交消息、Chat 查询和 Claw Session 配置
changed owned files: 协作/决策/02-configure-chat.md
unresolved: operation 边界、字段形状、默认值、状态冲突和错误码
```
