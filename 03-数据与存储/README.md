# 数据与存储

[返回仓库首页](../README.md)

**[Claw 数据库设计](Claw数据库设计.md)** 是 Claw 全库唯一主文件，集中维护表、字段、关系、约束、索引、生命周期及源码状态。各模块维护业务流程并引用其中对应章节；SQL 文件按版本作为关联实施材料。

| 阅读目的 | 数据库章节 | 对应业务设计 |
|---|---|---|
| 当前主线全表、字段与索引 | [全库清单](Claw数据库设计.md#table-index) · [主线结构](Claw数据库设计.md#current-schema) | [Session](01-会话记忆GaussDB/README.md) |
| 公共事件、执行控制与交互决定 | [表与模块映射](Claw数据库设计.md#table-index) | [Runtime / Events](../01-总体架构/01-CampusClaw多Agent运行时/chat-events-design.md) |
| Mate 归属/权限与 Claw 运行数据 | [职责边界](Claw数据库设计.md#mate-ownership) | [Mate 会话交接](../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md#session-ownership) |
| 定时任务与 Session 扩展 | [定时任务设计 §3.2](../01-总体架构/08-CampusClaw定时任务/README.md#persistence-lifecycle) | [定时任务](../01-总体架构/08-CampusClaw定时任务/README.md) |
| 工具结果、父子关系和累计投影 | [待实现增量](Claw数据库设计.md#pending-changes) | [统一历史](../01-总体架构/01-CampusClaw多Agent运行时/unified-event-persistence.md) · [Skill 统计](../01-总体架构/04-CampusClaw命令系统/03-Skill加载统计/README.md) |
| 删除、恢复与部署 SQL | [生命周期](Claw数据库设计.md#lifecycle) · [SQL 文件](Claw数据库设计.md#sql-files) | [Session 生命周期](01-会话记忆GaussDB/README.md#65-删除-session) |
| 自动与手工压缩、用量及恢复 | [会话历史表](Claw数据库设计.md#t_session_entries) | [压缩与恢复](01-会话记忆GaussDB/compaction.md) |
| Mate Agent 元数据 | 外部服务独立数据库，不属于 Claw 安装表 | [Agent 元数据设计](02-Agent元数据GaussDB/README.md) |
| 比较事件历史、Checkpoint 与长期记忆 | 研究参考，不另定义当前 Schema | [数据库模式研究](03-Agent数据库模式/README.md) |
