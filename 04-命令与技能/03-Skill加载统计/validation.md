# Skill 使用统计设计验证

版本 3.0.0 · 2026-09-16。目标方案已确认，新增实现仍为 target-only。[源码证据](source-evidence.md)维护固定 Java/pi/PR 基线，[Codex 专项](codex-skill-counting.md)维护计数器与分析事件的区别。

## 1. 设计制品检查

| 检查 | 结果及证明范围 |
|---|---|
| 源码与边界 | 沿用 Codex d58d0e58、pi 5cd93f68；Java f61906b9 核对 ExecutionTargetDTO、根绑定、消息受理/启动、Factory/hook 组合、工具调用映射、最终结果与 details 投影。新方案独立标为 target-only，不把固定 PR 对照升级为最新主线事实。 |
| Runtime 全量契约 | python3 validate-chat-api.py --full：11 个唯一 operation、原 7 项普通接口、两项 Events、两项统计；原确认状态保持，14 个既有图主题及关联负向回归通过。 |
| 统计专项 | python3 validate-skill-statistics.py：两项 GET、无需 ID 列表、Runtime scope、7/30 日连续序列及合计、同窗口排名/趋势一致、零值/404、ResultBean、目标状态、三表/中文注释、根/Skill 主键与 SQL 写入顺序通过。仅检查文档模型，未执行数据库事务。 |
| 页面交互 | JSDOM_MODULE=/private/tmp/campusclaw-session-contract-check/node_modules/jsdom node test_chat_api.cjs：11 项接口的 Header/语言/响应切换、重开状态、无 JS 与渲染失败回退通过。 |
| 浏览器视觉 | 独立临时 Chrome 检查 1440×1000 的排名和 30 日趋势、390×844 窄屏；无页面横向溢出、无 pageerror。实际查看截图，未使用用户浏览器资料。 |
| PlantUML 与 SVG | plantuml -tsvg diagram.puml 成功；两图为有效 XML，图源 ASCII。全局类图与失败隔离时序已查看原尺寸和 860px 缩放图，检查职责链、箭头、标签及遮挡；Markdown 提供原尺寸入口。 |
| API 设计技能校验 | validate_api_design.py 本专题通过：5 份 Markdown 的 SVG 路径及 PlantUML 锚点、2 张生成 SVG、Git whitespace。无 OpenAPI 为不适用；精确报文由 catalog 的 JSON 维护。 |
| 导航与退役检查 | 模块主设计、M04/M06、A09 对比及图索引同步；当前目标使用 usage-statistics、usageCount、t_skill_usage 三表；旧名称仅留在明确的基线证据和版本历史。无 Mermaid 围栏，图源/图文件/链接同步，git diff --check 通过。 |

校验工具为已有本地依赖，没有新增 Maven 依赖。本次改写不改变其他模块主图的架构结论；M05 的统计全局主图和时序图统一维护于本专题。

## 2. 必须由实现验收关闭的项目

- 未连接公司 GaussDB 执行 schema.sql / record-usage.sql；没有可用的目标数据库验证环境。openGauss 5.0 文档仅支持语法选择，不证明公司版本、唯一键异常映射或并发行为。
- 未实现或运行新 Java 统计代码。S1/S2 需验证实际事务代理、无主事务嵌套、提交阶段异常、重复主键及任意统计写失败只回滚三表，主受理与工具保持原结果。
- 尚未执行显式加多次 Read 共 1、新根再计、跨天确认/问答/审核续跑、部分正文、后置改写、取消、并行信号、恢复后数据库去重等集成场景。
- 未实测连接/锁/语句/事务和端到端等待预算、热点 Skill 行锁、30 日查询执行计划和事实保留容量；不能宣称同步统计无阻塞或无损。
- 未核验部署管理权限、活跃根去重键保留、Session 删除与迟到写竞争、三表一致备份及与 Runtime 恢复点的核对流程。
- Child/Cron 未纳入 scope=runtime。其身份、关联和去重域需按主设计 §9 完成后再扩展，不能报告为零使用。

本方案接受观测缺失。统计事务内一致不等于使用信号完整，也不等于 Runtime 历史与统计严格相等。以上运行验收由主设计 S1～S4 关闭，文档校验不能替代。
