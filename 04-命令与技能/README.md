# 命令与技能导航

[返回仓库首页](../README.md)

| 专题 | 解决的问题 | 入口 |
|---|---|---|
| Slash Command 通用模块 | 共享命令清单、来源解析、不可变请求快照与 JSON/SSE 边界 | [通用模块设计](./00-Slash-Command通用模块/README.md) · [前端设计与交互评审稿](../07-前端设计/技术设计/命令/README.md) |
| 内置命令 | 七个 Builtin 的行为、业务委派和实施验收 | [Builtin 设计](./01-内置命令/README.md) |
| Help 使用指南（已确认） | 无参读取 Agent 显示名、用途和场景；空数组、缓存往返与显式刷新旧缓存 | [Help 专项设计](./01-内置命令/Help-Agent使用指南/README.md) |
| Skill 使用统计 | 每次 Skill 成功调用加一、公共事件观察与有界后台入账；对比 #335，查询范围待核实 | [使用统计设计](./03-Skill加载统计/README.md) · [Codex 详解](./03-Skill加载统计/codex-skill-counting.md) |
| 技能命令 | Skill 名称、调用快照、执行与恢复 | [Skill 设计](./02-技能命令/README.md) |

当前实现入口：[Runtime 与剩余增量状态表](00-Slash-Command通用模块/README.md#current-runtime-status)，
固定核验 pi-mono-java@53eff85c；Builtin、Skill 执行、严格名称与前端行为已实现，测试验收与公共接入分别记录。

`03-历史Word文档/` 仅保存本机历史导出，Markdown 才是 Git 中的可维护源。
