# Skill 使用统计源码证据与实现差距

版本 3.0.0 · 2026-09-16。[主设计](README.md)维护已确认目标；[Codex 专项](codex-skill-counting.md)维护其详细生产调用链。本页只把实际读取范围作为事实，不以 PR 结构决定产品需求。

## 1. 固定基线

| 仓库 | 实际分析提交 | 范围 |
|---|---|---|
| pi-mono-java-design | e1795131f627f50a09d7bb5142a479576b4a1762 | M05 快照与命令、M06 完整事件/B09/B14/B15、M03 通用 Read、元数据身份、既有 HTTP catalog |
| Codex | d58d0e5841e0de08e251673db2d5af8cf3a1ad51 | 三类入口、计数器、分析事实、Reducer、Skill 身份、队列、发送、Turn 指标；详见专项逐项固定源码链接 |
| pi-mono-java | f61906b9136246ca60f333704b6fc92b5420d0ec | Runtime 受理/结果持久化、最终工具结果、Read、Skill 快照、Child/Cron 入口 |
| pi-mono | 5cd93f688aaab89dbb6dfa4aca535f21796ae185 | Skill 展开与工具执行生命周期，沿用既有固定源码核验 |
| pi-mono-java PR #295 | ee2f4dd44b30a272f13fce057c61e8490418332c | 所查 PR 的全文事件及查询，不等于当前主线 |
| pi-mono-java PR #298 | 3dfd990a982f610a97c7ecb45e07bde73f45ecb3 | 所查 PR 的 Host 全文覆盖和显式命令采集，不等于当前主线 |

Java 增加 f61906b9 的集成骨架核验，没有将旧 PR 的计数器结论延伸为该主线行为。其他 Command/Session/计划模块仍保留自己的核验点。PR 提交仅作为固定历史证据，不将其状态推断为最新主线。

## 2. Java 集成骨架与 target-only 改造

以下路径相对 pi-mono-java；完整 modules/ 开头的路径直接相对仓库，其余以 modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/ 为前缀。

| 编号 | 路径与符号 | 已观察源码行为 | 已确认目标及差距 |
|---|---|---|---|
| J01 | runtimeapi/service/command/skill/SkillCommandExecutionService.java · execute/expand；SkillCommandAdmission.java · requireBoundSkill | 用 PreparedAgentRuntime 解析实际绑定并展开 content，submitPreparedMessage 接受字符串输入 | 使用内部候选传递已解析 Skill，acceptMessage 提交、target 绑定后交给 Tracker；不在主事务中计数，不在返回 SSE 后另造执行 ID |
| J02 | runtimeapi/persistence/RuntimeExecutionPersistenceService.java · acceptMessage/appendEntry | @Transactional 中接受根消息、登记固定执行及段；工具记录和公共事件经同一追加服务保存 | 原事务保持；统计在调用方的事务外通过独立 SkillUsageService 写入，失败不改变原受理/追加结果 |
| J03 | runtimeapi/event/RuntimeEventProjector.java · persistToolCall/persistToolResults（约 330/358 行） | 保存规范调用事件；TurnEnd 的结果逐项编码并保存，成功后 emit；toolCallEntryIds 保存调用映射 | 将规范工具调用 ID 以执行范围只读映射提供给 Tracker；Read 最终 hook 形成信号，不等待 TurnEnd，不声称结果已持久化 |
| J04 | runtimeapi/dto/RuntimeEntryDTO.java；runtimeapi/persistence/RuntimeSessionRepository.java · appendEntry | 已有 Entry ID、Session、序号、payload 与普通/带公共投影追加 | 复用真实身份；统计 DTO 不穿透 Controller；去重为 session/root/Skill，来源只用于追溯 |
| J05 | tool/read/ReadTool.java · execute/readText/selectLines；ReadToolDetails.java | 规范路径读取文件字节，UTF-8/offset/limit/预算截断；details 目前仅 truncation | 增加通用路径/摘要/实际正文证据；Resolver 归因，局部正文即可，无行覆盖聚合 |
| J06 | session/AgentSessionFactory.java · create/configureAgent | Runtime/Cron/Child 共用工厂，配置 before/after hooks，实例不共享消息与工具 | Factory 仅装配，Runtime 执行持有 Tracker 和快照；末尾观察 hook 保持最终结果，不给 Child/Cron 自动生成统计身份 |
| J07 | tool/agent/SubagentExecutionContext.java；SubagentExecutionService.java · runChild/projectProgress | 保存深度/祖先/模型/凭据，创建 Child，订阅开始/结束进度，没有此范围内的权威子事件存储 | Child 先明确执行身份、父调用关联和结果保存；首版统计明确不覆盖 |
| J08 | tool/cron/ManagedCronSessionRunner.java · execute；modules/cron/src/main/java/com/campusclaw/cron/engine/CronJobExecutor.java · execute | Executor 创建短 runId 和运行日志，但只向 runner 传 agentId/prompt；runner 执行内存 Session | Cron 先传递真实 job/run 身份并确定持久化边界，不能把 jobId 或随机统计 ID 当单次运行 |
| J09 | modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java · execute/applyAfterResult/toToolResultMessage | 工具执行后取消检查、after hook、最终结果事件；hook 可以改写正文/details | 复用最终 after hook 观察；统计异常在事务外捕获，避免被 applyAfterHook 转为工具失败；无需新增 agent-core 回调 |
| J10 | modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql · t_session_executions/t_session_execution_segments | 固定 root_event_id、执行/段和规范事件持久化结构 | 新增三表的主键使用 root_event_id；独立统计事务借 Session 生命周期锁防止删除后迟到写，不加入来源事务 |
| J11 | runtimeapi/dto/ExecutionTargetDTO.java；runtimeapi/runtime/RuntimeActiveExecution.java · bindTarget/target | 真实 sessionId/executionId/rootEventId/segmentId；target 在受理后绑定，确认续跑继续关联原根 | Tracker 每根一份；绑定真实 target，禁止按 HTTP 段或随机 UUID 建去重域 |
| J12 | runtimeapi/runtime/RuntimeSessionEngineRegistry.java · createSession；session/ManagedAgentSessionRequest.java | Runtime 请求带 beforeHooks/afterHooks，after 当前为空；请求没有统计根或 Tracker 参数 | Host 装配末尾观察入口，显式信号与 Read 共享执行持有者；快照及目标绑定扩展为 target-only |
| J13 | runtimeapi/event/RuntimeMessageEventService.java · submitLocked/accept/startAccepted | accept 调用事务服务后返回真实 target；startAccepted 绑定并启动模型；当前 submitPreparedMessage 只返回事件流 | 在受理提交与模型启动之间转交显式候选；不能从返回的流反推根身份 |
| J14 | runtimeapi/event/RuntimeEntryCodec.java · toolResultEntry；RuntimeCommittedEventFactory.java · agentToolResult | 工具结果按字段构造，成功分支不复制 details；错误仅从 details 取稳定错误码 | Read 证据保持内部观测用途，沿用字段白名单，不新增公共/持久化路径与摘要 |

当前方案的三表、Resolver/Tracker、根执行去重、独立事务及失败隔离和两个 GET 尚未完成实现验收。上述静态证据不证明所有领域恢复和跨实例竞争都已解决；实施 S1～S4 必须验证。

## 3. pi 与 PR 对照

pi 固定基线 packages/coding-agent/src/core/agent-session.ts 的 _expandSkillCommand（约 1320 行）读取主文档并展开；packages/coding-agent/src/core/tools/read.ts 提供 offset/limit 截断。packages/agent/src/types.ts 的 AgentEvent 提供工具生命周期及 toolCallId/result/isError。所查函数没有企业 Skill 统计写入；本设计的事实表、HTTP 与事务是 CampusClaw 架构扩展，不声称整个 pi 没有遥测。

PR #298（依赖 #295）中的以下行为仅作为对照：

| 路径 | 固定 PR 观察 | 对本设计的意义 |
|---|---|---|
| modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql · t_skill_load_events | 每次全文加载事件、独立 invocation/execution UUID | 本方案使用真实根/Skill 键；事实存在的理由是幂等/追溯，不是照搬原事件字段 |
| modules/coding-agent-cli/src/main/resources/mapper/session/SkillLoadMapper.xml；runtimeapi/service/SkillLoadService.java | 根据调用方 IDs 做 COUNT/MAX；写失败只 WARN | 本方案从统计集合排名，三张统计表独立事务且失败隔离；不存在的统计资源不伪造目录存在 |
| session/AgentSessionFactory.java · recordSkillLoad；skill/usage/SkillReadCoverage.java | Host 按版本/摘要合并完整行覆盖 | 本方案统计根执行的使用信号，首次部分正文即可，同根反复 Read 不增加次数 |
| runtimeapi/web/SkillLoadStatisticsController.java；modules/common/src/main/java/com/campusclaw/common/constant/ClawConstants.java | POST /internal/skills/load-statistics/query，必传 skillIds | 该地址只作为 PR 观察，目标 GET 以 catalog 为准，无旧入口兼容声明 |

本节缩写的 runtimeapi/session/skill 前缀同 §2，完整路径来自上述固定 PR 树。没有修改实现仓或向 PR 提交评审评论。

## 4. SQL 依据与验证边界

2026-09-15 核对 [openGauss 5.0 INSERT 官方文档](https://docs.opengauss.org/en/docs/5.0.0/docs/SQLReference/insert.html)：ON DUPLICATE KEY UPDATE 处理唯一键冲突，EXCLUDED 表示待插入值；该语法不与 WITH/RETURNING 组合。本专题只在各有一个主键的汇总表使用它，事实先查同根/Skill，普通 INSERT 成功后才增量，主键冲突回滚统计事务，禁止依赖受影响行数猜测插入还是更新。

这是语法参考，不证明公司 GaussDB 版本完全一致。未连接目标数据库执行新 DDL/事务、并发冲突、索引计划或保留策略。验证记录将设计制品检查与运行验收分开；未测结果不得标为通过。
