# 数据与存储

[返回仓库首页](../README.md)

本组按数据所有者组织：Session 保存交互历史和恢复依据；Agent 元数据保存可复用定义与绑定。研究资料解释参考来源，不另定义当前 Schema。

| 阅读目的 | 入口 |
|---|---|
| Session 当前路径、不可变历史、事务与数据迁移 | [Session 主设计](./01-会话记忆GaussDB/README.md) |
| 自动与手工压缩、用量及重载一致性 | [压缩与恢复](./01-会话记忆GaussDB/compaction.md) |
| Agent 定义、默认模式和运行依赖解析 | [Agent 元数据主设计](./02-Agent元数据GaussDB/README.md) |
| 比较事件历史、Checkpoint 与长期记忆 | [数据库模式研究](./03-Agent数据库模式/README.md) |
