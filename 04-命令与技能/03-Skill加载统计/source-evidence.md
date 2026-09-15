# Skill 加载统计源码证据

版本 1.0.0 · 2026-09-15。本文只记录已经读取的源码及验证边界；目标表和接口由[主设计](README.md)维护。

## 1. 固定基线

| 仓库 | 实际分析提交 | 范围 |
|---|---|---|
| pi-mono-java-design | `497d34a4f05def36d4e3c62085d9eb4848b70f69` | M05 模块、统一 HTTP catalog、整数 page/limit、公司 ResultBean 与 Runtime/Mate 边界 |
| pi-mono-java，PR #295 | `ee2f4dd44b30a272f13fce057c61e8490418332c` | 全文加载事件表、批量 ID 查询、写入失败处理 |
| pi-mono-java，PR #298 | `3dfd990a982f610a97c7ecb45e07bde73f45ecb3` | 显式命令及同执行分段覆盖；该提交不是已合入 main 的声明 |
| pi-mono | `5cd93f688aaab89dbb6dfa4aca535f21796ae185` | `_expandSkillCommand` 和 Read 执行；沿用固定基线，不升级其他模块的证据范围 |

PR head 于 2026-09-15 重新核对，仍为以上提交。下面 Java 路径均相对 pi-mono-java，P01/P02 相对 pi-mono。

## 2. 已观察行为与目标差距

| 编号 | 仓库相对路径、符号或行号 | 已观察行为 | 本专题目标差距 |
|---|---|---|---|
| J01 | `modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql:453-483`，`t_skill_load_events` | 每次加载一行；随机 invocation/execution UUID；按 Skill/时间索引；没有累计或日汇总表 | 改为累计与日汇总；不保存逐次事件和统计专用执行 UUID |
| J02 | `modules/coding-agent-cli/src/main/resources/mapper/session/SkillLoadMapper.xml:18-44`，`insert/query` | 同步 INSERT；请求 ID 构成查询集合；LEFT JOIN 后 COUNT/MAX，按输入顺序返回 | 数据库原子增量；按统计结果筛选、排序、分页，不要求预先知道 Skill ID |
| J03 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/service/SkillLoadService.java`，`record/query` | RuntimeException 只记 WARN，无补偿；查询校验结果与去重 ID 数量相同 | 两表同事务，异常在事务代理外处理；列表允许空结果 |
| J04 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSessionFactory.java:128-173`，`configureAgent/recordSkillLoad` | 工厂生成统计执行 UUID；后置 hook 核对最终结果、文件摘要、执行快照，再累计完整覆盖 | 保留 Host 归因和边界，统计写入仅携带汇总必需信息 |
| J05 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/skill/usage/SkillReadCoverage.java`，`include` | 同一执行按 Skill/版本/摘要取完整行范围并集；完成一轮即删除位图 | 保留执行内状态；不把位图、正文或片段持久化 |
| J06 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/service/command/skill/SkillCommandExecutionService.java:75-103`，`execute` | 完整快照正文受理成功后计数；每次生成两个随机 UUID；命令入口为 RUNTIME | 命令和 Read 共用统计记录端口，去掉无业务追溯意义的持久化 UUID |
| J07 | `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/read/ReadTool.java`，`execute/readText/readRange` | 返回实际文件字节摘要及完整行范围；业务 Skill 身份由 Host 匹配 | 保持通用文件语义，不把统计数据库或 Skill 类型放入 Read |
| J08 | `modules/common/src/main/java/com/campusclaw/common/constant/ClawConstants.java:97-98`；`runtimeapi/web/SkillLoadStatisticsController.java` | POST `/internal/skills/load-statistics/query`，必传 skillIds，ResultBean | 新 GET 统计集合进入统一 catalog；旧 PR 入口只作为源码差距 |
| J09 | `modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_privileges.sql:25-26` | 应用仅 SELECT/INSERT 事件表 | 汇总需要 SELECT/INSERT/UPDATE；清理角色与应用角色分离 |
| P01 | `packages/coding-agent/src/core/agent-session.ts:1320-1344`，`_expandSkillCommand` | 本地查找 Skill、读取正文、去 frontmatter 后拼接参数；未知 Skill 可回退原文本 | 只参考展开与 Read 分离；企业加载计数、GaussDB 和管理查询为 CampusClaw 扩展 |
| P02 | `packages/coding-agent/src/core/tools/read.ts`，`createReadToolDefinition.execute` | 文件读取后按 offset/limit、行数和字节预算截断；这条函数没有企业 Skill 计数写入 | 保留通用工具职责；不能声称加载统计是 pi 自带行为，也不据此推断整个 pi 仓库没有遥测 |

J01～J09 以 #298 为主；#295 提供其基础。Java 的全文计数不是任务采用数、模型已接收数或任务成功数。本次设计不升级其他 Command、Session、计划模式的旧实现结论。

## 3. SQL 方言与验证边界

2026-09-15 核对 [openGauss 5.0 INSERT 官方文档](https://docs.opengauss.org/en/docs/5.0.0/docs/SQLReference/insert.html)：`ON DUPLICATE KEY UPDATE` 可处理主键冲突并更新既有行，需要 SELECT/INSERT/UPDATE 权限；`EXCLUDED` 可引用本次待插入值。该语法不与 WITH 或 RETURNING 组合。本专题 SQL 遵守这些限制；每张统计表只有一份唯一键。

官方文档证明语法依据，不能替代部署所用 GaussDB 版本的验收。当前只核对 DDL、Mapper、生产调用点和设计契约，没有在真实 GaussDB 执行新表、并发写入、查询计划或容量测试。验收要求见主设计；不把此前 PR 的测试结果记作本方案已实现。
