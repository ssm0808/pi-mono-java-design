# Skill 调用统计源码证据与实现差距

版本 2.0.0 · 2026-09-15。[主设计](README.md)维护推荐目标；[Codex 专项](codex-skill-counting.md)维护其详细生产调用链。本页只把实际读取范围作为事实，不以 PR 结构决定产品需求。

## 1. 固定基线

| 仓库 | 实际分析提交 | 范围 |
|---|---|---|
| pi-mono-java-design | 761b7640f76b74162423c0372496cdef0b88d708 | M05 快照与命令、M06 完整事件/B09/B14/B15、M03 通用 Read、元数据身份、既有 HTTP catalog |
| Codex | d58d0e5841e0de08e251673db2d5af8cf3a1ad51 | 三类入口、计数器、分析事实、Reducer、Skill 身份、队列、发送、Turn 指标；详见专项逐项固定源码链接 |
| pi-mono-java | f61906b9136246ca60f333704b6fc92b5420d0ec | Runtime 受理/结果持久化、最终工具结果、Read、Skill 快照、Child/Cron 入口 |
| pi-mono | 5cd93f688aaab89dbb6dfa4aca535f21796ae185 | Skill 展开与工具执行生命周期，沿用既有固定源码核验 |
| pi-mono-java PR #295 | ee2f4dd44b30a272f13fce057c61e8490418332c | 所查 PR 的全文事件及查询，不等于当前主线 |
| pi-mono-java PR #298 | 3dfd990a982f610a97c7ecb45e07bde73f45ecb3 | 所查 PR 的 Host 全文覆盖和显式命令采集，不等于当前主线 |

Java 增加 f61906b9 的集成骨架核验，没有将旧 PR 的计数器结论延伸为该主线行为。其他 Command/Session/计划模块仍保留自己的核验点。本页未重新查询 PR 最新 head；所列 PR 是固定历史证据。

## 2. Java 集成骨架与 target-only 改造

以下路径相对 pi-mono-java；除 J09 外以 modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/ 为前缀。

| 编号 | 路径与符号 | 已观察源码行为 | 推荐目标及差距 |
|---|---|---|---|
| J01 | runtimeapi/service/command/skill/SkillCommandExecutionService.java · execute/expand；SkillCommandAdmission.java · requireBoundSkill | 用 PreparedAgentRuntime 解析实际绑定并展开 content，submitPreparedMessage 接受字符串输入 | 携带可信 Skill 候选至受理事务；不能在返回 SSE 之后另起事务盲目加一 |
| J02 | runtimeapi/persistence/RuntimeExecutionPersistenceService.java · acceptMessage/appendEntry | @Transactional 中接受根消息、登记固定执行及段；工具记录和公共事件经同一追加服务保存 | 追加统计参与端口；来源、事实、累计/日原子提交；既有源码尚不能证明新统计事务已实现 |
| J03 | runtimeapi/event/RuntimeEventProjector.java · persistToolCall/persistToolResults（约 330/358 行） | 保存规范调用事件；TurnEnd 的结果逐项编码并保存，成功后 emit；toolCallEntryIds 保存调用映射 | 使用规范调用事件作为事实来源；重复结果须复用原记录，不能每次 ids.nextId 后重复计数 |
| J04 | runtimeapi/dto/RuntimeEntryDTO.java；runtimeapi/persistence/RuntimeSessionRepository.java · appendEntry | 已有 Entry ID、Session、序号、payload 与普通/带公共投影追加 | 复用已有身份与锁；统计 DTO 不穿透 Controller，不新造统计 execution UUID |
| J05 | tool/read/ReadTool.java · execute/readText/selectLines；ReadToolDetails.java | 规范路径读取文件字节，UTF-8/offset/limit/预算截断；details 目前仅 truncation | 增加通用路径/摘要/实际正文证据；Host 最终结果归因，首版没有行覆盖聚合 |
| J06 | session/AgentSessionFactory.java · create/configureAgent | Runtime/Cron/Child 共用工厂，配置 before/after hooks，实例不共享消息与工具 | 共享工厂不等于三入口有共同持久化；归因接入不能仅靠工厂生成无关联 UUID |
| J07 | tool/agent/SubagentExecutionContext.java；SubagentExecutionService.java · runChild/projectProgress | 保存深度/祖先/模型/凭据，创建 Child，订阅开始/结束进度，没有此范围内的权威子事件存储 | Child 先明确执行身份、父调用关联和结果保存；首版统计明确不覆盖 |
| J08 | tool/cron/ManagedCronSessionRunner.java · execute；modules/cron/src/main/java/com/campusclaw/cron/engine/CronJobExecutor.java · execute | Executor 创建短 runId 和运行日志，但只向 runner 传 agentId/prompt；runner 执行内存 Session | Cron 先传递真实 job/run 身份并确定持久化边界，不能把 jobId 或随机统计 ID 当单次运行 |
| J09 | modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java · execute/applyAfterResult/toToolResultMessage | 工具执行后取消检查、after hook、最终结果事件；hook 可以改写正文/details | 在全部 hook 之后检查实际交付，不把较早的成功状态当成最终事实 |
| J10 | modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql · t_session_executions/t_session_execution_segments | 固定 root_event_id、执行/段和规范事件持久化结构 | 统计三表是新增结构；外部接口不暴露内部执行 ID，也不假设现有计数表已支持来源幂等 |

当前方案的三表、归因 DTO、来源去重、参与原事务端口和两个 GET 尚无对应完成验收。上述静态证据不证明所有领域恢复和跨实例竞争都已解决；实施 S1～S4 必须验证。

## 3. pi 与 PR 对照

pi 固定基线 packages/coding-agent/src/core/agent-session.ts 的 _expandSkillCommand（约 1320 行）读取主文档并展开；packages/coding-agent/src/core/tools/read.ts 提供 offset/limit 截断。packages/agent/src/types.ts 的 AgentEvent 提供工具生命周期及 toolCallId/result/isError。所查函数没有企业 Skill 统计写入；本设计的事实表、HTTP 与事务是 CampusClaw 架构扩展，不声称整个 pi 没有遥测。

PR #298（依赖 #295）中的以下行为仅作为对照：

| 路径 | 固定 PR 观察 | 对本设计的意义 |
|---|---|---|
| modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql · t_skill_load_events | 每次全文加载事件、独立 invocation/execution UUID | 本方案使用业务来源键；事实存在的理由是幂等/追溯，不是照搬原事件字段 |
| modules/coding-agent-cli/src/main/resources/mapper/session/SkillLoadMapper.xml；runtimeapi/service/SkillLoadService.java | 根据调用方 IDs 做 COUNT/MAX；写失败只 WARN | 本方案从统计集合排名，事实与汇总同事务；不存在的统计资源不伪造目录存在 |
| session/AgentSessionFactory.java · recordSkillLoad；skill/usage/SkillReadCoverage.java | Host 按版本/摘要合并完整行覆盖 | 本方案统计每次成功交付，未采用全文覆盖口径 |
| runtimeapi/web/SkillLoadStatisticsController.java；modules/common/src/main/java/com/campusclaw/common/constant/ClawConstants.java | POST /internal/skills/load-statistics/query，必传 skillIds | 该地址只作为 PR 观察，目标 GET 以 catalog 为准，无旧入口兼容声明 |

本节缩写的 runtimeapi/session/skill 前缀同 §2，完整路径来自上述固定 PR 树。没有修改实现仓或向 PR 提交评审评论。

## 4. SQL 依据与验证边界

2026-09-15 核对 [openGauss 5.0 INSERT 官方文档](https://docs.opengauss.org/en/docs/5.0.0/docs/SQLReference/insert.html)：ON DUPLICATE KEY UPDATE 处理唯一键冲突，EXCLUDED 表示待插入值；该语法不与 WITH/RETURNING 组合。本专题只在各有一个主键的汇总表使用它，事实首次插入由来源锁内分支决定，禁止依赖受影响行数猜测插入还是更新。

这是语法参考，不证明公司 GaussDB 版本完全一致。未连接目标数据库执行新 DDL/事务、并发冲突、索引计划或保留策略。验证记录将设计制品检查与运行验收分开；未测结果不得标为通过。
