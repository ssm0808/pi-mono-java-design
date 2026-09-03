# 创建 Chat 决策

| 属性 | 值 |
|---|---|
| 负责任务 | `Mate Chat · 创建 Chat` |
| 状态 | `proposed` |
| 契约性质 | target-only |
| 最近更新 | 2026-09-03 |

## 当前输入

- Mate 对外使用 `Chat/chatId`，内部私有解析为 Claw `Session/sessionId`。
- 创建 Chat 时可以承载初始模型和深度思考配置，但具体字段尚未确认。
- 创建成功响应是否返回完整 Chat 资源、资源包含哪些状态字段，尚未确认。

## 待逐项评审

1. 方法、路径和幂等语义；
2. 必需请求头；
3. 创建请求字段、默认值和约束；
4. 初始模型与深度思考配置；
5. 成功响应的完整 Chat 资源；
6. 错误码、国际化和并发行为。

## 交接

```text
operation: 待确认
status: proposed
confirmed decisions: 暂无
cross-operation impact: Chat 公共资源形状将约束配置与 Events 接口
changed owned files: 协作/决策/01-create-chat.md
unresolved: 方法、路径、字段、响应、错误均待评审
```
