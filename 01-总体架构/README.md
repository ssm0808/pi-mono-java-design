# 总体架构导航

[返回仓库首页](../README.md)

| 专题 | 解决的问题 | 入口 |
|---|---|---|
| CampusClaw 多 Agent 运行时 | Runtime、HTTP+SSE、Session、Manager 和服务责任如何协作 | [总体设计](./01-CampusClaw多Agent运行时/README.md) |
| CampusClaw 工具系统 | 内置工具、Mate 工具、Child Agent 和受管目录如何装配 | [工具系统设计](./02-CampusClaw工具系统/README.md) |
| 虚拟线程并发管理 | 执行准入、容量、背压和下游边界 | [PlantUML 图源](./03-虚拟线程并发管理/diagram.puml) |
| CampusClaw 前端体验 | Runtime 事件如何投影为对话、工具、Slash Command 和异常状态 | [前端体验设计](./04-CampusClaw前端体验/README.md) · [Slash Command 前端专项](../04-命令与技能/00-Slash-Command通用模块/前端设计/README.md) |
| CampusClaw 调用日志 | 调用失败如何简化记录和定位 | [异常日志设计](./05-CampusClaw调用日志/README.md) |
| CampusClaw 计划模式 | 通过 Session 更新切换 plan/build，审核方案、在原执行续跑并通过通用工具结果更新 TODO | [计划模式设计](./06-CampusClaw计划模式/README.md) · [接口增量](./06-CampusClaw计划模式/interface-delta.md) · [TodoUpdate](./06-CampusClaw计划模式/todo-update.md) |
| Agent 架构对比 | 按模块说明 CampusClaw 与基线的设计、实现差异、理由、代价和证据 | [架构对比](./07-Agent架构对比/README.md) · [全仓模块索引](../README.md#module-index) |

多 Agent Runtime 专题中还包含 [Runtime HTTP API 设计](./01-CampusClaw多Agent运行时/chat-http-v1-design.md)、
[接口评审页](./01-CampusClaw多Agent运行时/chat-api-review.html) 和
[飞书渠道设计](./01-CampusClaw多Agent运行时/channel-feishu-v1-design.md)。
