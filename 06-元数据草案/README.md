# 元数据草案导航

版本：1.1.1；日期：2026-09-14。

[返回仓库首页](../README.md)

| 草案 | 入口 |
|---|---|
| Agent 元数据 | [`AGENT元数据设计.json`](./AGENT元数据设计.json) |
| Tool 元数据 | [`TOOL元数据设计.json`](./TOOL元数据设计.json) |
| Skill 元数据 | [`SKILL元数据设计.json`](./SKILL元数据设计.json) |

Agent 顶层 `mode`，JSON 类型为 string，仅支持 `build`、`plan`；草案示例为 `build`。它是新建交互 Session 的默认模式，已有 Session 独立维护当前模式；缺省兼容、存储和生效时机由[主设计 §4.4](../03-数据与存储/02-Agent元数据GaussDB/README.md#44-agent-mode)维护。Tool、Skill 的字段分别以其草案和所属主设计为准。

这三份文件是元数据草案，不应被误认为已发布的 Runtime 或 HTTP 契约。
