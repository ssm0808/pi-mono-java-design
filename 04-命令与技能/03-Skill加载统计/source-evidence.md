# Skill 统计：源码与目标差距

版本 5.0.0 · 2026-10-10。[主设计](README.md)维护当前目标；完整历史的新基线与路径见[统一证据](../../01-总体架构/01-CampusClaw多Agent运行时/unified-event-persistence-evidence.md)。

## 当前核验归属

本次重新确认 Java main 并隔离 fetch `769e86592285f4a25b0febaf551eddea6bc7212c`。PR #335 的固定开发 head `dad4433d38fcb4104bd8d093f844ea2afc9612ee` 是此前同日读取的实现证据，不是 main，也未将 PR 的实时合入状态作为新结论。pi main `42a3497d03ad17e308a2299fa824727894f2c0ec` 本次再次 fetch，工具事件结论不变，新增 Session/SubAgent 范围见统一证据；Codex/OpenCode 的新核验只证明独立历史，不推断其 Skill 统计后端。

## 固定 #335 代码及新差距

下列相对路径以 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/` 为前缀，除明确 modules/ 路径外均对应 #335 head。

| 路径 / 符号 | 已观察实现 | 5.0.0 目标 |
|---|---|---|
| `runtime/PreparedAgentRuntime.java:skillIdsByName` | 可信 name→id 映射 | 固定到同次通用结果提交 DTO，无二次目录解析 |
| `tool/skill/SkillTool.java:execute` | 输出正文和 SkillToolDetails(name/hash/signal) | 工具功能保持；统计不依赖正文/hash/details |
| `skill/usage/SkillUsageTracker.java:skill/record` | 最终成功 End 之外还要求正文/hash/source/identity，13 字段 DTO | 删除专用观察，使用已提交最终 LIVE 成功结果 |
| `session/AgentSessionFactory.java:create` | 公共装配，PR 已无具体 Tracker 参数 | 保持装配职责，不再给 Factory 新装统计 Observer |
| `runtimeapi/runtime/RuntimeSessionEngineRegistry.java` · attach/close；`tool/agent/SubagentExecutionContext.java` / `SubagentExecutionService.java`；`tool/cron/ManagedCronSessionRunner.java` | 三 Host 接统计身份/来源与追踪 | 三入口走统一持久 Runtime；移除统计专用接线 |
| `session/ExecutionIdentity.java` / `ManagedExecutionLog.java:observe` | Cron/Child 先 JSONL 记来源再统计 | 完整历史进公共 Session 存储；只删除无独立用途的统计日志，不删除真实 Cron Run |
| `runtimeapi/event/RuntimeEventProjector.java` / `runtimeapi/runtime/RuntimeActiveExecution.java` · rememberToolCallEventId | 来源映射传播给统计 | 通用服务端调用身份归历史，累计消费结果，无统计专用来源解析 |
| `runtimeapi/service/SkillLoadTransaction.java:record` / `SkillLoadService.java:record` | REQUIRES_NEW，Session/root 准入，事实与总数一起写 | 累计直接加入统一历史事务；不创建独立事实/事务 |
| `runtimeapi/persistence/MyBatisRuntimeSessionRepository.java:beginDeletion` | deleteSkillUsage | 统一删除协调及缺口标记，不扣累计，无专用事实可删 |
| `modules/coding-agent-cli/src/main/resources/mapper/session/SkillLoadMapper.xml` | 事实、累计 UPSERT、累计查询 | 仅累计表投影；新增结果唯一约束由 M06/M04 管理 |

旧目标 4.0.0 的观察器、三列事实、有界队列不是已实现的新源码；不能把本次设计表述成删除了已经上线的队列。

## 事件语义与历史证据

Java `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java:execute` 的 validate/prepare/before 可直接返回错误，不保证每个错误都有 End；业务执行后 after hook 决定最终 isError。`Agent.java:emit` 会隔离监听器异常，故普通 subscribe 不能作为可靠写入屏障。主线 Projector 在 TurnEnd 保存 toolResults，新方案须改变结果提交时点而非只更换监听器。

pi `packages/agent/src/agent-loop.ts:prepareToolCall/finalizeExecutedToolCall/emitToolExecutionEnd` 与 `types.ts:AgentEvent` 支持最终结果语义，但 Start 顺序与 Java 不同；pi 并未提供本文的企业累计表或事务。Codex 计数研究与其他 trace 文件保留原历史 SHA，不因新的子 Session 证据升级其统计结论。

固定 #335 的 SkillUsageTrackerTest 中，三次成功计三次；正文移除/hash变化或 Cron 来源日志失败时会零计数。此前同 head 的 16 类 156 项聚焦测试是原实现证据，不证明本次提交端口/DDL/同事务方案。新方案把这些“真实成功但被来源条件漏掉”的情况按最终结果计数。

## 查询与依赖边界

from/to、独立日汇总及保留策略仍待核实；#335 删除它们的行为不自动成为获批目标，本次不改精确 HTTP 模型。旧 PR #295 的查询证据保留在历史提交 `c8cbda4946403d5e51b95ceaf0d7485166c54395`，不描述为最新实现。

现有 Mapper 使用 openGauss `ON DUPLICATE KEY UPDATE` / EXCLUDED；本设计沿用方言但须在公司 GaussDB 验证。项目已用 MyBatis Starter 3.0.4、Spring Boot、JDBC、Validation，无新增 Maven 依赖。
