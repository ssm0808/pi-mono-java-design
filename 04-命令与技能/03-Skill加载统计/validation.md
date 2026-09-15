# Skill 加载统计设计验证

版本 1.1.0 · 2026-09-15。源码范围见[证据](source-evidence.md)，本页不表示产品实现已完成。

| 检查 | 实际结果与证明范围 |
|---|---|
| Runtime 契约 | `1dbc9d7` 的 `python3 validate-chat-api.py --full` 通过；当前修订执行 `python3 validate-chat-api.py` 通过：11 项唯一操作，原 Session/Events/Command 回归保持；统计列表和日趋势已登记，现有确认状态未改变。包括原有 14 个图主题的生成核对。 |
| `python3 validate-skill-statistics.py` | 通过：GET 路径、无必传 ID 的列表、7/30 自然日、连续日期、补零、列表/趋势示例数值同源、404 统计资源缺失、ResultBean、全文加载候选和口径待评审状态。只验证契约与示例，不执行 SQL。 |
| `JSDOM_MODULE=... node test_chat_api.cjs` | 通过：11 项操作的 Header/响应/语言切换、折叠与状态保留、禁用 JS 和渲染失败回退；无动态错误，初始 174 个元素，单项展开峰值 616 个元素。 |
| 本地 Chrome 浏览器 | 1440×1000 与 390×844 渲染；列表参数和日趋势响应已实际查看，窄屏无页面横向溢出、无 pageerror。使用独立临时配置；预览脚本与截图是临时验证产物。 |
| `python3 .../company-http-api-design/scripts/validate_api_design.py <本专题>` | 通过：Markdown 图链接/图源锚点、PlantUML ASCII、实际 SVG 生成、XML、Git whitespace；未使用 OpenAPI，标记不适用。 |
| `plantuml -tsvg diagram.puml` 与视觉验收 | 成功；新全局目标类图已在原尺寸和 860px 文档宽度查看，改正连线标签遮挡，保留入口、Service、事务 Bean、Mapper、执行对象和两表。 |
| Slash `validate-global-class-view.py` | 6 项通过；原完整全局类图与锚点保留，统计专题独立下钻。 |
| 调用观测源码 | 读取固定 Codex d58d0e58 的计数/分析/队列及调用点、OpenCode 849c2598 的 Skill/工具结果、pi 5cd93f68 的展开/事件；逐项核对引用行号。见 trace-baselines.md；没有运行这些基线或查询分析后台。 |
| 全仓 Markdown 与最终差异 | 未发现 Mermaid 围栏；`git diff --check` 通过。图索引只增加本专题，生成时保留用户工作区既有 README 删除造成的索引状态。 |

## 尚未执行的实施验收

- 新 DDL/UPSERT 没有连接真实 GaussDB 执行；本机无 gsql，存在 psql 不代表可访问目标 GaussDB。
- 未运行新统计 Java 的编译、单元或集成测试，因为本次没有实现该 Java 代码。
- 未执行并发首次插入、两表回滚、跨午夜、清理任务、驱动重试配置、连接等待、热行锁竞争、真实 SQL 执行计划及容量测试。
- 未核验 CampusMate/网关的实际统计权限接口或部署级管理授权。权限范围仍按主设计的推荐边界评审，不把示例 Header 当作授权实现。

这些项目必须由主设计 S1～S4 的实现验收关闭；文档、生成器和浏览器检查不能代替运行验证。
