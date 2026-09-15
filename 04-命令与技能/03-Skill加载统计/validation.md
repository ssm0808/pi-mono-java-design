# Skill 调用统计设计验证

版本 2.0.0 · 2026-09-15。基线和差距见[源码证据](source-evidence.md)，Codex 生产调用链见[专项](codex-skill-counting.md)。本页区分设计制品校验与尚未执行的产品运行验收。

## 1. 已完成检查

| 检查 | 结果及证明范围 |
|---|---|
| 固定 Codex 源码 | 三类入口、选择集合、路径身份、Turn/Resource 去重、计数器、analytics 结构、队列及 HTTP 发送、Turn 耗时已逐项读取；20 个固定 GitHub 路径/行号引用通过本地 git show 验证。未运行 Rust 测试或访问后台。 |
| Java 集成源码 | f61906b9 的 Skill 展开/受理、Runtime 事务/结果投影、最终工具结果、通用 Read、Child/Cron 入口已核对；证据不升级旧 PR 的实现状态。 |
| Runtime 全量契约 | python3 validate-chat-api.py --full 通过：11 个唯一 operation；7 项普通原契约、两项 Events、两项统计；原确认状态保持，旧操作文件未回流；原有 14 图主题校验通过。 |
| 统计专项 | python3 validate-skill-statistics.py 通过：无 ID 列表、两项 GET、Runtime scope、日期连续性及合计/排名示例一致、404/空窗口区别、ResultBean、推荐状态、三表和来源主键/中文注释。只检查设计模型，不执行 SQL。 |
| 页面交互 | JSDOM_MODULE=/private/tmp/campusclaw-session-contract-check/node_modules/jsdom node test_chat_api.cjs 通过：11 项 Header/语言/响应切换、折叠恢复、无 JS 和渲染失败回退；初始 174 个节点、单项展开峰值 616。 |
| Chrome 视觉 | 独立临时配置打开生成 HTML；1440×1000 查看列表与日趋势，390×844 查看窄屏；无页面横向溢出和 pageerror。截图实际查看，不修改用户浏览器资料。 |
| PlantUML 与 SVG | plantuml -tsvg diagram.puml 成功；两张 SVG 均为有效 XML，图源 ASCII；全局类图及提交时序在原尺寸和 860px 宽度实际查看。图名/目录保留稳定入口，内容为当前调用方案。 |
| API 设计技能校验 | python3 /Users/z/.codex/skills/company-http-api-design/scripts/validate_api_design.py 本专题通过；5 份 Markdown 的图路径/图源锚点、2 个 SVG 和 Git whitespace；无 OpenAPI 为不适用。 |
| 全仓与导航 | 无 Mermaid 围栏；当前操作已改为 invocation-statistics，旧全文 API 只保留在明确 PR 源码观察/版本记录；模块和 A09 对比同步，设计图索引已生成；git diff --check 通过。 |

运行依赖是已有本地工具，不是新增 Maven 依赖。缺省位置未找到 jsdom 后使用上述已有路径重跑成功；Chrome 沙箱启动失败后在允许的临时独立进程中完成视觉验证。

## 2. 尚未执行的实施验收

- 未连接公司 GaussDB 执行 schema.sql/record-invocation.sql；本机没有 gsql，psql 的存在不证明目标数据库可用。openGauss 官方语法只作为依据。
- 未实现或运行新 Java 统计代码；没有执行来源重复通知、事务中途失败、提交结果不明、并发首写、热行锁、执行段关闭或恢复的集成测试。
- 未实测同步三表对主流程延迟、连接/锁等待、30 日查询和事实保留容量的影响。
- 未核验部署管理权限的真实服务集成、保留策略的覆盖日期或生产清理/备份恢复。它们是启用范围内功能的验收条件，不因 Header 示例存在就视为完成。
- Child/Cron 没有纳入 scope=runtime；其身份和持久化前提见主设计 §9，不将未知数据报告为零。

以上由主设计 S1～S4 的实现验收关闭。文档和模型检查不能证明数据可靠性或运行性能；本交付仍为推荐目标、target-only。
