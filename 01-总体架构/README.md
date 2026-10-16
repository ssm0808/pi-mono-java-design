# 总体架构导航

[返回仓库首页](../README.md)

| 专题 | 解决的问题 | 入口 |
|---|---|---|
| CampusClaw 多 Agent 运行时 | Runtime、HTTP+SSE、Session、Manager 和服务责任如何协作 | [总体设计](./01-CampusClaw多Agent运行时/README.md) |
| CampusClaw 工具系统 | 内置工具、Mate 工具、Subagent 和受管目录如何装配 | [工具系统设计](./02-CampusClaw工具系统/README.md) |
| CampusClaw 命令系统 | Slash Command 的 Agent 命令清单、Builtin、Help、Skill 命令执行与 Skill 使用统计 | [命令系统设计](./04-CampusClaw命令系统/README.md) · [Builtin](./04-CampusClaw命令系统/01-内置命令/README.md) · [Help](./04-CampusClaw命令系统/01-内置命令/Help-Agent使用指南/README.md) · [Skill Command](./04-CampusClaw命令系统/02-技能命令/README.md) · [Skill 使用统计](./04-CampusClaw命令系统/03-Skill加载统计/README.md) |
| 虚拟线程并发管理 | 执行准入、容量、背压和下游边界 | [PlantUML 图源](./03-虚拟线程并发管理/diagram.puml) |
| CampusClaw 前端体验 | 以场景组织用户目标、界面与交互，按需下钻共享结构与事件投影 | [独立前端设计目录](../07-前端设计/README.md) · [场景原型](../07-前端设计/原型/index.html) · [全局组件](../07-前端设计/技术设计/README.md) |
| CampusClaw 调用日志 | 调用失败如何简化记录和定位 | [异常日志设计](./05-CampusClaw调用日志/README.md) |
| CampusClaw 计划模式 | 通过 Session 更新切换 plan/build，审核方案、在原执行续跑并在 build 通过后端任务事件跟踪实施进度 | [计划模式设计](./06-CampusClaw计划模式/README.md) · [接口增量](./06-CampusClaw计划模式/interface-delta.md) · [TodoUpdate](./06-CampusClaw计划模式/todo-update.md) · [提示词](./06-CampusClaw计划模式/plan-policy.md) · [完整交互](./06-CampusClaw计划模式/plan_mode_end_to_end.svg) |
| CampusClaw 定时任务 | 服务端按时新建会话或继续已有会话，管理触发、暂停、恢复与运行证据 | [定时任务主设计](./08-CampusClaw定时任务/README.md) · [接口协议](./08-CampusClaw定时任务/README.md#interface) · [源码证据](./08-CampusClaw定时任务/source-evidence.md) |
| Agent 架构对比 | 按模块说明 CampusClaw 与基线的设计、实现差异、理由、代价和证据 | [架构对比](./07-Agent架构对比/README.md) · [全仓模块索引](../README.md#module-index) · [全部设计图](../设计图索引.html) |

多 Agent Runtime 专题中还包含 [Runtime HTTP API 设计](./01-CampusClaw多Agent运行时/chat-http-v1-design.md)和
[接口评审页](./01-CampusClaw多Agent运行时/chat-api-review.html)。
