# Skill 成功调用统计：源码与实现差距

版本 4.0.0 · 2026-10-10。[主设计](README.md)给出目标；本页只记录实际读取的固定源码。运行测试与设计制品验收见[validation.md](validation.md)。

## 1. 查询基线

| 对象 | 查询结果与范围 |
|---|---|
| #335 | 当日 GitHub 查询确认 OPEN，head `dad4433d38fcb4104bd8d093f844ea2afc9612ee`，base `769e86592285f4a25b0febaf551eddea6bc7212c`；已读取 diff、采集/三 Host/工具/Pipeline/事务与测试 |
| 设计主线 | 创建隔离工作树前 fetch `origin/main@da81fed06ed9e8964b0dfd0bc0ed612c5be1e543`；不改原目录未提交内容 |
| pi | 2026-10-10 先 `ls-remote --symref` 确认 main，再隔离 depth=1 fetch；`42a3497d03ad17e308a2299fa824727894f2c0ec` |

pi 的本专题旧证据为 `5cd93f688aaab89dbb6dfa4aca535f21796ae185`，只将工具事件与订阅结论升级至新 SHA。新源码 `packages/agent/package.json` 标记版本 1.1.0；这是默认分支快照，不等同发布验证。Codex/OpenCode 专项保留历史证据，本次不升级或宣称其为最新。

## 2. Java 已观察行为与目标差距

除完整 modules/ 路径外，以下路径前缀为 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`；所有行号以 #335 head 为准。

| 路径、符号、行号 | 已观察行为 | 本方案调整（待实现） |
|---|---|---|
| `session/AgentSessionFactory.java:create/configureAgent`，69–117 | 三入口共用创建；before/after hooks；当前无统计接线 | 一个窄观察器装配点，保持 create(request) 与受理顺序，不传追溯上下文 |
| `runtime/PreparedAgentRuntime.java:skillIdsByName`，88–95 | 按绑定名称给出可信 ID 映射 | Observer 使用此只读数据，不存全文快照 |
| `tool/builtin/DefaultBuiltInToolFactory.java:create` | 三入口的 SKILL 均构造相同 SkillTool | 保持工具选择和执行能力 |
| `tool/skill/SkillTool.java:execute`，97–124 | 返回正文与 SkillToolDetails(name, hash, signal) | 统计不再需要 details 或摘要；复查消费者后删除专用凭据，保留路径、安全和取消逻辑 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/event/ToolExecutionStartEvent.java` / `ToolExecutionEndEvent.java` | Start 有参数；End 有 result/isError，无参数 | Observer 私有暂存正在执行的 Skill 关联；不改通用事件 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java:execute`，66–88 | 校验/prepare/before → Start → 执行 → 后置 hook → End → ToolResult | 消费最终 End；不提前在 SkillTool 返回前计数 |
| `session/AgentSessionHookChain.java:executeAfter`，47–63 | 每个 hook 收到原 context，再合并覆盖值 | 不把新 observer 塞到 afterHooks 末尾并误称可见前面所有最终改写 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/Agent.java:subscribe/emit`，227–231、294–305 | 同步遍历监听器，异常隔离 | 事件回调不做 JDBC，使用有界入队 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/loop/AgentLoop.java:runInternal`，85–110 | finally 发 AgentEnd | 清理仅在 Observer 内的未完成关联，不再按 Host 管理 Tracker 关闭 |
| `skill/usage/SkillUsageTracker.java:skill/record`，101–148 | 正文/hash/source/identity 条件，13 字段 DTO | 改为按最终成功生成 3 字段计数 DTO |
| `runtimeapi/runtime/RuntimeActiveExecution.java`，50、88–93；`runtimeapi/event/RuntimeEventProjector.java`，437–449、522–538 | Projector 已有映射，另写 ActiveExecution 来源映射 | 删除额外映射及 remember 调用，保留 Projector 自己的持久化映射和业务事件 |
| `runtimeapi/runtime/RuntimeSessionEngineRegistry.java`，205–209、259–271 | attach/保存/关闭统计观察器并提供延迟身份 | 移除这组统计专用托管；普通 Session 生命周期保持 |
| `tool/agent/SubagentExecutionContext.java`，39–40；`SubagentExecutionService.java`，119–139 | 父身份、来源函数、Child 身份推导及日志/统计装配 | 删除统计所需参数与装配，保留授权、深度、模型、凭据和进度 |
| `tool/cron/ManagedCronSessionRunner.java`，74–111；`session/ExecutionIdentity.java` | 基于实际 Cron run 推导统计身份，日志先于统计 | 计数不接收 run，不删除 Cron 自己的真实运行记录；重载按独立消费者复查 |
| `session/ManagedExecutionLog.java:observe`，77–105 | 每个 Tool Start 同步写 JSONL，再登记规范来源；失败则无来源 | 不为计数创建日志；执行审计若有独立要求由其所属模块维护 |
| `runtimeapi/service/SkillLoadTransaction.java:record`，28–40；`SkillLoadService.java:record`，69–96 | REQUIRES_NEW，同步等待，Session 行锁/root 校验，事实与总数同事务 | 保留事务原子性，在后台执行；移除 Session 准入，仅访问统计表 |
| `runtimeapi/persistence/MyBatisRuntimeSessionRepository.java:beginDeletion`，452–463 | Session 删除调用 deleteSkillUsage | 移除此统计联动；已成功调用可以晚于 Session 关闭入账 |
| `modules/coding-agent-cli/src/main/resources/mapper/session/SkillLoadMapper.xml` | 13 列事实、累计原子 UPSERT、按 skillIds 累计查询 | 3 列事实；沿用累计原子更新，范围查询继续待核实 |

生产代码检索 `SkillToolDetails`、`ExecutionIdentity`、`ManagedExecutionLog`、`rememberToolCallEventId` 和来源函数的消费者，当前所查额外追溯链服务于此统计及其配套日志。不能把“日志不 import Tracker”作为独立产品需求的证明，也不能据此删除真正的 Runtime/Cron 历史记录。实施时必须按最新消费者再次确认。

## 3. 可以直接复核的测试证据

同提交已有 `SkillUsageTrackerTest`：86–98 三次成功三次、重复事件一次；112–141 正文移除或摘要变化时最终仍成功但零计数；180–199 Cron 日志失败、工具成功、统计服务零调用。这证明新方案与旧方案存在有意语义差异，不能只做方法挪动后声称等价。

本会话同 head 的 16 类 156 项聚焦测试已通过；这是旧实现验证，不能当作新 Observer、异步写入或新 DDL 已通过。#335 文档所列真实数据库等待数据来自作者报告，本任务未独立复跑。

## 4. pi 的事件依据与差异

固定新 SHA 的仓库相对路径及符号：

- `packages/agent/src/types.ts:AgentEvent`，529–539：Start 有 args，End 有 result/isError；`AfterToolCall` 注释 328–337 说明后置处理在 End 之前。
- `packages/agent/src/agent-loop.ts:executeToolCallsSequential/Parallel`，530–648；`prepareToolCall`，707–781；`finalizeExecutedToolCall`，859–909；`emitToolExecutionEnd`，919–927：最终结果由后置处理归一，再发布 End。
- `packages/agent/src/agent.ts:subscribe`，266–269；事件发射尾部遍历并 await listener：订阅回调本身可以拖延推进，订阅不自动意味着异步隔离。

重要差异：最新 pi 在 prepare/校验之前发 Start，并且截断输出的失败调用也有 Start；Java 当前在校验、prepare、before hook 后发 Start。两者都不能用 Start 当成功依据。本方案沿用 Java 的已有顺序，以最终 End 决定计数；不宣称存在统一行业校验顺序。CampusClaw 的可信解析/校验先于交互确认是本产品目标。

所查 pi 路径提供事件能力，不提供本文的 Skill 幂等表、应用级队列或管理 API；这些是 CampusClaw 的架构选择。无需为比较统计重新解读其他 pi 模块、企业数据表或私有遥测。

<a id="f19-query"></a>

## 5. 查询未决范围

设计仓起点的 README §6 与现有 operation JSON 仍保留 from/to；#335 仅累计且拒绝这两个字段。用户答复为“暂时不确定，先标为待核实”。本任务只调整成功调用采集和持久化职责，不改精确 HTTP 模型、不静默批准删除。历史 PR #295 查询证据仍可按提交 `c8cbda4946403d5e51b95ceaf0d7485166c54395` 追溯，不作为 #335 现状。

## 6. SQL 与依赖依据

目标 SQL 沿用 #335 `SkillLoadMapper.xml:incrementTotal` 的 `ON DUPLICATE KEY UPDATE` 和 EXCLUDED 方言，事实普通 INSERT 后才累加。新 DDL、主键冲突识别、公司 GaussDB 方言、共享数据源故障和异步关闭仍需真实集成验收，不以设计 SQL 代替执行证明。

`pom.xml` 已声明 MyBatis Starter 3.0.4；`modules/coding-agent-cli/pom.xml` 已有 Spring Boot、JDBC、Validation、MyBatis。本方案的 JDK 执行器/UUID/并发容器不引入 Maven 依赖，不新增传递依赖树。
