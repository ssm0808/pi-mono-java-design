# Agent 基线研究

[返回仓库首页](../README.md) · [Agent 架构对比](../01-总体架构/07-Agent架构对比/README.md)

本组保存固定源码或官方契约的研究证据。每个结论只适用于文档登记的提交与核验日期；研究候选不自动成为 CampusClaw 产品设计。需要了解 CampusClaw 的当前选择、理由和实现差距时，先读架构对比，再进入所属模块主设计。

| 问题 | 研究入口 |
|---|---|
| 描述、执行代码和通用驱动如何装配成 Tool/Agent | [配置生成机制](./01-配置生成Tool与Agent/README.md) |
| 托管 Agent 如何组织资源、工具执行、事件与恢复 | [Anthropic 公开模型](./02-Anthropic托管Agent公开模型/README.md) |
| pi 从哪些文件构建模型上下文 | [pi 上下文研究](./03-pi会话上下文/README.md) |
| pi 对外快照表达哪些客户端状态 | [pi 协议快照](./04-pi会话快照/README.md) |
| 查找平台的 Agent、Tool、Skill 创建入口 | [官方资料索引](./05-主流Agent平台资料/README.md) |
| 区分 Session、Checkpoint 与长期记忆存储 | [数据库模式研究](../03-数据与存储/03-Agent数据库模式/README.md) |
