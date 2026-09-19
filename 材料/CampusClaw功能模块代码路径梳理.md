# CampusClaw 功能模块代码路径梳理

基于 `pi-mono-java` 仓库 `main` 分支、commit `fb842b1ac6cb4818f6b146f79dd184a5cd88bf12` 梳理（核对日期：2026-09-19）。`campusclaw` 是独立 Maven 模块，当前有 460 个主源码 Java 文件、193 个测试 Java 文件；本材料只覆盖该模块的当前源码树。

## 1. 总体入口与配置

- 应用启动：[CampusClawApplication.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/CampusClawApplication.java)
- Maven 配置：[campusclaw/pom.xml](/Users/z/pi-mono-java/campusclaw/pom.xml)
- 运行配置：[application.properties](/Users/z/pi-mono-java/campusclaw/src/main/resources/application.properties)
- 共享路径、ID、API 常量：[ClawConstants.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/common/constant/ClawConstants.java)
- 数据库初始化：[initdb_gaussdbv5.sql](/Users/z/pi-mono-java/campusclaw/scripts/install/initdb_gaussdbv5.sql)

## 2. Agent 核心运行时

负责 Agent 状态、消息、循环、工具调用和运行事件。

- Agent 门面：[agent/Agent.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/agent/Agent.java)
- Agent 主循环：[agent/loop/AgentLoop.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/agent/loop/AgentLoop.java)
- 状态管理：[agent/state](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/agent/state)
- 消息队列、Steer、Follow-up：[agent/queue](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/agent/queue)
- Agent 事件：[agent/event](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/agent/event)
- 工具调用流水线：[ToolExecutionPipeline.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/agent/tool/ToolExecutionPipeline.java)
- 上下文转换：[agent/context](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/agent/context)

当前 `campusclaw` 源码树不包含 `CampusClawAgentCore.java`；实际运行逻辑集中在 `Agent` 和 `AgentLoop`。

## 3. AI 模型与 Provider

负责模型类型、Provider 路由和 CampusMate SSE 调用。模型实例由受管 Agent 的目录快照解析，不再由独立全局模型目录加载。

- AI 统一入口：[CampusClawAiService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/ai/CampusClawAiService.java)
- 模型类型与成本计算：[ai/types](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/ai/types)、[ModelCostCalculator.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/ai/model/ModelCostCalculator.java)
- Provider 注册：[ApiProviderRegistry.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/ai/provider/ApiProviderRegistry.java)、[AiProviderRegistry.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/ai/provider/AiProviderRegistry.java)
- CampusMate Provider：[CampusMateProvider.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/ai/provider/mate/CampusMateProvider.java)
- 请求转换：[MateChatRequestMapper.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/ai/provider/mate/MateChatRequestMapper.java)
- SSE 解析：[MateChatSseParser.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/ai/provider/mate/MateChatSseParser.java)
- AI 类型模型：[ai/types](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/ai/types)
- 流式事件：[ai/stream](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/ai/stream)

## 4. 受管 Agent Runtime 与 Session

负责从 Mate 获取 Agent 配置、Skill、子 Agent，并构建可执行的 Session。

- Mate 服务客户端：[MateServiceClient.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtime/MateServiceClient.java)
- Agent Runtime 缓存与原子发布：[AgentRuntimeManager.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtime/AgentRuntimeManager.java)
- Runtime 元数据：[PreparedAgentRuntime.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtime/PreparedAgentRuntime.java)
- Runtime 模型解析：[MateRuntimeModelManager.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/model/MateRuntimeModelManager.java)
- Session 创建工厂：[AgentSessionFactory.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/session/AgentSessionFactory.java)
- Session 执行封装：[ManagedAgentSession.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/session/ManagedAgentSession.java)
- Plan 模式提示词：[PlanPolicyPromptComposer.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/session/PlanPolicyPromptComposer.java)
- Agent 目录和提示词：[runtimeapi/agent](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/agent)

运行目录文件约定：`.campusclaw/agent.json`、`settings.json`、`SYSTEM.md`。`settings.json` 提供默认模型和可用模型白名单；AgentRuntimeManager 同时发布模式提示词快照，Session 创建时按入口和当前模式组合系统提示词。

## 5. Runtime HTTP 公共 API

API 前缀为：

```text
/campusclaw-service/v1
```

### Session 管理

- Controller：[RuntimeSessionController.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/web/RuntimeSessionController.java)
- Service：[RuntimeSessionService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/session/RuntimeSessionService.java)
- 更新：[RuntimeSessionUpdateService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/session/RuntimeSessionUpdateService.java)
- 配置：[RuntimeSessionConfigurationService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/session/RuntimeSessionConfigurationService.java)

主要接口：

```text
POST   /agents/{agentId}/sessions
GET    /sessions/{sessionId}
POST   /sessions/{sessionId}
DELETE /sessions/{sessionId}
GET    /sessions/{sessionId}/models
```

### Event 提交、SSE 与历史查询

- Controller：[RuntimeEventController.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/web/RuntimeEventController.java)
- 事件分派：[RuntimeEventService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/RuntimeEventService.java)
- 用户消息：[RuntimeMessageEventService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/RuntimeMessageEventService.java)
- 控制事件：[RuntimeControlEventService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/RuntimeControlEventService.java)
- 执行协调：[RuntimeExecutionCoordinator.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java)
- SSE 分发：[RuntimeSseDispatcher.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/RuntimeSseDispatcher.java)
- 历史查询：[CommittedEventQueryService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/event/CommittedEventQueryService.java)

主要接口：

```text
POST /sessions/{sessionId}/events   # 用户消息、停止、工具确认、计划确认、问题回答
GET  /sessions/{sessionId}/events   # 当前分支事件分页查询
```

### Command 命令

- 命令执行：[RuntimeCommandController.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/web/RuntimeCommandController.java)
- 命令清单：[RuntimeCommandCatalogController.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/web/RuntimeCommandCatalogController.java)
- 命令注册与发现：[runtimeapi/service/command](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/service/command)
- Builtin 命令贡献者：[runtimeapi/service/command/contributor](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/service/command/contributor)
- Skill 命令：[runtimeapi/service/command/skill](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/service/command/skill)

主要接口：

```text
GET  /sessions/{sessionId}/commands
POST /sessions/{sessionId}/command
```

## 6. Runtime 执行状态与跨实例控制

- 活动 Session 注册表：[RuntimeSessionEngineRegistry.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/runtime/RuntimeSessionEngineRegistry.java)
- Session Holder：[RuntimeSessionHolder.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/runtime/RuntimeSessionHolder.java)
- 活动执行：[RuntimeActiveExecution.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/runtime/RuntimeActiveExecution.java)
- 控制分发：[RuntimeSessionControlDispatcher.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/runtime/RuntimeSessionControlDispatcher.java)
- 数据库轮询控制：[ExecutionControlPollingService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/runtime/ExecutionControlPollingService.java)
- 超时处理：[RuntimeExecutionTimeoutScheduler.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/runtime/RuntimeExecutionTimeoutScheduler.java)
- 终态重试：[RuntimeTerminalRetryScheduler.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/runtime/RuntimeTerminalRetryScheduler.java)

## 7. Event 持久化与 Session 数据库

### Java 持久化层

- Session Repository：[MyBatisRuntimeSessionRepository.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java)
- 执行控制 Repository：[MyBatisRuntimeExecutionControlRepository.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/persistence/MyBatisRuntimeExecutionControlRepository.java)
- 执行结果 Repository：[MyBatisRuntimeExecutionResultRepository.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/persistence/MyBatisRuntimeExecutionResultRepository.java)
- 事务编排：[RuntimeExecutionPersistenceService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/persistence/RuntimeExecutionPersistenceService.java)

### MyBatis Mapper

- [RuntimeSessionMapper.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/mapper/RuntimeSessionMapper.java)
- [RuntimeExecutionControlMapper.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/mapper/RuntimeExecutionControlMapper.java)
- [RuntimeExecutionResultMapper.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/mapper/RuntimeExecutionResultMapper.java)

### XML Mapper

- [RuntimeSessionMapper.xml](/Users/z/pi-mono-java/campusclaw/src/main/resources/mapper/session/RuntimeSessionMapper.xml)
- [RuntimeExecutionControlMapper.xml](/Users/z/pi-mono-java/campusclaw/src/main/resources/mapper/session/RuntimeExecutionControlMapper.xml)
- [RuntimeExecutionResultMapper.xml](/Users/z/pi-mono-java/campusclaw/src/main/resources/mapper/session/RuntimeExecutionResultMapper.xml)

主要数据表：

```text
t_sessions
t_session_entries
t_session_records
t_session_events
t_session_event_projection
t_session_sequences
t_session_executions
t_session_execution_segments
t_session_execution_segment_events
t_session_tool_confirmations
t_session_plan_confirmations
t_session_question_answers
t_session_stats
t_session_materialized
t_session_tombstone
t_session_cleanup_task
```

## 8. 工具系统

### 工具装配

- 工具装配入口：[DefaultConfiguredToolAssembler.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/builtin/DefaultConfiguredToolAssembler.java)
- 工具工厂：[DefaultBuiltInToolFactory.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/builtin/DefaultBuiltInToolFactory.java)
- 工具上下文：[ToolAssemblyContext.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/builtin/ToolAssemblyContext.java)

### 本地工作区工具

- Read、Find、Grep、Ls：[tool](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool)
- 文件系统操作：[tool/ops](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/ops)
- 工作区边界：[tool/workspace](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/workspace)

当前 `BuiltInToolName` 和默认配置没有 Bash、Edit、Write；这些名称及对应源码路径不属于当前 `campusclaw` 工具树。

### Agent 专用工具

- 子 Agent：[SubagentExecutionService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/agent/SubagentExecutionService.java)
- Mate 工具发现与调用：[tool/mate](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/mate)
- 工具调用展示名快照：[RuntimeToolCallSnapshotResolver.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/runtime/RuntimeToolCallSnapshotResolver.java)
- Cron 工具：[tool/cron](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/cron)
- Todo：[tool/todo](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/todo)
- Plan 审核：[tool/plan](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/plan)
- 用户提问：[tool/question](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/question)

## 9. Skill、Plan、Question、Compaction

- Skill 加载：[codingagent/skill](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/skill)
- Skill 运行目录准备：`AgentRuntimeManager`
- Skill 命令执行：[SkillCommandExecutionService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/service/command/skill/SkillCommandExecutionService.java)
- Plan 模式提示词资源：[prompts/plan](/Users/z/pi-mono-java/campusclaw/src/main/resources/prompts/plan)
- Plan 审核事件：[runtimeapi/dto](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/dto)
- 用户问题事件：[runtimeapi/dto](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/dto)
- 会话压缩：[codingagent/session/compaction](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/session/compaction)
- Runtime 压缩协调：[runtimeapi/compaction](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/compaction)

## 10. 多 Agent

- 子 Agent 工具：[BoundAgentTool.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/agent/BoundAgentTool.java)
- 子 Agent 执行：[SubagentExecutionService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/tool/agent/SubagentExecutionService.java)
- 子 Agent Session 复用：[AgentSessionFactory.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/session/AgentSessionFactory.java)
- Agent 绑定、版本和模型校验：[AgentRuntimeManager.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtime/AgentRuntimeManager.java)

## 11. Control Plane

### 控制面服务

- 节点注册与心跳：[NodeRegistry.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/agent/controlplane/service/NodeRegistry.java)
- Runtime 调度：[RuntimeScheduler.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/agent/controlplane/service/RuntimeScheduler.java)
- 健康检查：[HealthCheckScheduler.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/agent/controlplane/service/HealthCheckScheduler.java)

### 控制面 API

- 节点接口：[NodeController.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/controlplane/api/NodeController.java)
- Runtime 调度接口：[RuntimeController.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/controlplane/api/RuntimeController.java)
- 状态接口：[StatusController.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/controlplane/api/StatusController.java)

主要接口：

```text
GET    /api/v1/status
POST   /api/v1/nodes
POST   /api/v1/nodes/{nodeId}/heartbeat
GET    /api/v1/nodes
GET    /api/v1/nodes/{nodeId}
DELETE /api/v1/nodes/{nodeId}
GET    /api/v1/runtimes
GET    /api/v1/runtimes/capabilities
POST   /api/v1/runtimes/schedule
```

当前 `NodeRegistry` 是进程内内存实现，节点持久化尚未接入数据库。

## 12. Cron 定时任务

- 门面服务：[CronService.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/cron/CronService.java)
- 调度引擎：[CronEngine.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/cron/engine/CronEngine.java)
- Agent 执行器：[CronAgentSessionRunner.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/cron/engine/CronAgentSessionRunner.java)
- JSON 任务存储：[CronStore.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/cron/store/CronStore.java)
- 运行日志：[CronRunLog.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/cron/store/CronRunLog.java)
- Agent 工具：[CronTool.java](/Users/z/pi-mono-java/campusclaw/src/main/java/com/huawei/hicampus/claw/cron/tool/CronTool.java)

默认任务文件：

```text
~/.campusclaw/agent/cron/jobs.json
```

## 13. 最核心的主调用链

```text
RuntimeEventController
  -> RuntimeEventService
  -> RuntimeMessageEventService
  -> RuntimeSessionEngineRegistry
  -> AgentSessionFactory
  -> ManagedAgentSession
  -> Agent
  -> AgentLoop
  -> ToolExecutionPipeline / CampusClawAiService
  -> MateToolDiscovery / CampusMateProvider
  -> RuntimeToolCallSnapshotResolver
  -> RuntimeEventProjector
  -> RuntimeExecutionCoordinator
  -> MyBatis Repository
  -> Session/Event 数据库
```

建议后续阅读顺序：

1. `RuntimeEventController`
2. `RuntimeEventService`
3. `RuntimeSessionEngineRegistry`
4. `AgentSessionFactory`
5. `Agent`
6. `AgentLoop`
7. `CampusClawAiService`
8. `RuntimeEventProjector`
9. `RuntimeExecutionPersistenceService`
10. MyBatis Mapper XML
