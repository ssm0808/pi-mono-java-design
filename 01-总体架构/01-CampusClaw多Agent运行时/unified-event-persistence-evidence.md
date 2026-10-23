# 统一历史：源码证据与差距

版本 1.1.0 · 2026-10-23。[目标设计](unified-event-persistence.md)不代表以下源码已经实现统一持久化。§1～§6 保留 2026-10-10 的历史核验归属；[§7](#session-kind-evidence)仅更新本次实际复核的 Session 分类、主会话/Cron 持久化与 Subagent 范围，不将旧 Cron JSONL 或旧上游路径当作当前结论。

## 1. 2026-10-10 快照与升级范围

对四个仓库先用 `git ls-remote --symref <upstream> HEAD` 确认默认分支，再在 `/tmp/subagent-history-baselines-20261010/*.git` 隔离 fetch，读取明确提交；没有覆盖用户工作树。默认分支源码不等于稳定发布。

| 仓库 | 默认分支 / 完整 SHA | 升级范围与原证据 |
|---|---|---|
| [pi](https://github.com/badlogic/pi-mono) | main / `42a3497d03ad17e308a2299fa824727894f2c0ec` | Skill 4.0.0 已使用同 SHA 的工具事件；新增 Subagent 示例、Session 消息落盘与 experimental durable 范围。历史 5cd93f68 的其他专题不升级 |
| [Codex](https://github.com/openai/codex) | main / `322bbf4d8486efd7dbbcf49598711a9e3fefc282` | 从登记 d58d0e58 扩展到本次 child spawn、Session rollout、thread-store 与保留策略；不升级旧 Provider/API 结论 |
| [OpenCode](https://github.com/anomalyco/opencode) | dev / `055d95bb7e278c94baf06235a52cac79dd13ba67` | 从登记 849c2598 扩展到 Task、Session 消息与 Part 数据库投影；dev 快照不代表全部 v2/后台功能稳定发布 |
| [CampusClaw Java](https://github.com/superheromeZzh/pi-mono-java) | main / `769e86592285f4a25b0febaf551eddea6bc7212c` | 重新核验 Runtime/Subagent/Cron/工具 Pipeline；Cron 原 553dcd5e 的数据库受理目标仍待实现；Skill PR #335 的 dad4433d 只保留独立开发证据 |

最新 Cron 设计来源为设计仓起点 `ec05afd28c766a55df26ad324c8ad0240c568b15`：`01-总体架构/08-CampusClaw定时任务/README.md` 0.31.2、`execution.md` 0.1.0，以及配置专题 Run/Session 删除边界。本任务沿用其已选产品规则；没有新增 Claude 托管服务内部实现推断，也不把该专题旧官方核对日期改成今天。

## 2. pi：内存子运行与独立 durable conversation 是两种路径

以下路径均相对 pi，固定新 SHA：

| 路径 / 符号 | 观察与边界 |
|---|---|
| `packages/coding-agent/examples/extensions/subagent/index.ts` · runSingleAgent / SingleResult，约 300、362、384、706 行 | 子进程参数含 --no-session；收集 message_end 与 tool_result_end，返回最后文本，同时 details 保留 messages。不能说完全没保存内容，也不能说每个普通示例子任务有独立持久 Session |
| `packages/coding-agent/src/main.ts` · createSessionManager，约 365 行 | noSession 使用 SessionManager.inMemory |
| `packages/coding-agent/src/core/agent-session.ts` · _handleAgentEvent，约 1144–1162 行 | 完整 message_end 写 appendMessage，含 toolResult；父会话中的工具返回 details 可随完整消息保存，不等于子会话独立可读 |
| `packages/coding-agent/src/core/session-manager.ts` · _persist / appendMessage，约 1172、1204 行 | 持久模式向 JSONL 追加 Session Entry；内存模式不写文件；不是企业数据库公共事件表 |
| `packages/coding-agent/src/experimental/durable/subagent.ts` · api.commit / createConversation / submit / wait | 为任务创建/查找独立 conversation，保留跨工具调用的子会话；路径明确 experimental，不当成稳定内核默认能力 |
| `packages/agent/src/agent-loop.ts` · prepareToolCall / finalizeExecutedToolCall / emitToolExecutionEnd；`types.ts` AgentEvent | 后置处理后发最终 End；pi Start 先于 prepare，Java Start 在校验/prepare/before 之后。不能用 Start 推断成功，也不存在据此可宣称的统一校验顺序 |

## 3. Codex：独立 child thread 与有选择的持久化

| 仓库相对路径 / 符号 | 观察与适用范围 |
|---|---|
| `codex-rs/core/src/agent/control/spawn.rs` · spawn_child_thread / persist_thread_spawn_edge_for_source / ensure_rollout_materialized，约 785–911 行 | 启动 child thread 并记录父子来源；fork/history 模式还有对应物化处理，不将所有 child 初始化方式合成一种 |
| `codex-rs/core/src/session/session.rs` · CreateThreadParams / LiveThread::create，约 1020–1100 行 | 非 ephemeral 创建持久 thread，含 parent_thread_id/source/history_mode；ephemeral 是明确例外 |
| `codex-rs/thread-store/src/local/mod.rs` · LocalThreadStore，约 133 行 | canonical JSONL 是持久历史，SQLite 用于元数据索引；不能说完整聊天统一存 SQLite 一张事件表 |
| `codex-rs/rollout/src/policy.rs` · 持久项分类，约 77–99 行 | Message、Reasoning、FunctionCall/Output、CustomToolCall/Output 等按策略保留；不是保存全部临时增量 |

CampusClaw 采用独立历史和父侧摘要的职责分离；本库事务、权限、保留及 Skill 统计不是 Codex 上游的已观察设计。

## 4. OpenCode：Task Session 与消息/Part 投影

| 仓库相对路径 / 符号 | 观察与边界 |
|---|---|
| `packages/opencode/src/tool/task.ts` · execute，约 136–169、197–225、328–348 行 | task_id 可定位既有 Session，否则用 parentID 创建；prompt 写到子 Session，父工具返回文本和 metadata。CampusClaw 首版不采用 task_id 复用 |
| `packages/opencode/src/session/session.ts` · updateMessage/updatePart，约 630–643 行；`packages/opencode/src/event-v2-bridge.ts` | 消息/Part 变更转入 core 事件路径，不是只向父文本流发送 |
| `packages/core/src/session/projector.ts` · MessageUpdated / PartUpdated，约 260–269、310–320 行 | 写 MessageTable 与 PartTable，完整工具 Part 有持久数据 |
| `packages/core/src/session/sql.ts` · SessionTable/MessageTable/PartTable，约 31、68、82 行；`packages/schema/src/session-message.ts` · ToolStateCompleted | Session 有 parent_id，消息/Part 归属 Session；工具 part 保存调用输入和终态输出等。本文没有核验所有实时 delta 的保留能力 |

## 5. Java：已有骨架与必须改造的边界

下表除 modules/ 开头外统一以前缀 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/` 展开，全部为新 main SHA。

| 路径 / 关键符号 | 已观察实现 | 待实现差距 |
|---|---|---|
| `session/AgentSessionFactory.java:create` | 构造 Agent、工具/hooks 与 ManagedAgentSession | 保持对象工厂；持久受理放应用服务，不在 Factory 偷写数据库 |
| `runtimeapi/event/RuntimeExecutionCoordinator.java:start` | 创建 Projector、安装确认处理并订阅 Agent/压缩，再 prompt | 三入口都经同一持久执行协调，后台仅替换输出 |
| `runtimeapi/event/RuntimeEventProjector.java:project`，227–235；persistToolCall/persistFinalizedToolCalls，414–449；persistToolResults，467–477 | 调用可在 Assistant 定稿时保存；TurnEnd 才保存工具结果；map 主要按 Provider callId | 每个完整消息内定位真实调用，形成服务端调用身份；每个最终结果立即走可靠提交；TurnEnd 不重复写 |
| `runtimeapi/event/RuntimeEntryCodec.java:toolResultEntry/toolCallEntry`，208–246 | 内部结果含 tool_call_id/tool_name/content/is_error/error_code；调用含 arguments/requires_confirmation | 保存受控的内部恢复结果与可信 skillId，不把公共裁剪结果作为唯一恢复源；增加固定结果关联 |
| `runtimeapi/event/RuntimeCommittedEventFactory.java:agentToolCall/agentToolResult` | sourceEventId、toolCallId 等公共结构；没有公共 skillId | 保持既有安全字段，统计读内部可信记录，不加一个公共统计事件 |
| `runtimeapi/persistence/MyBatisRuntimeSessionRepository.java:appendEntryLocked/appendEventsLocked` | 锁 Session，Entry/公共事件/投影标记/序号/末端一起写 | 在唯一新结果同事务加入累计更新；固定执行身份、重复与删除竞争继续强校验 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/tool/ToolExecutionPipeline.java:execute` | 校验/prepare/before 可直接返回错误；执行后检查取消、after hook、End，随后返回结果 | 通用最终结果提交覆盖所有返回分支；取消不能吞掉已经形成的最终结果；持久异常不归一成工具业务失败 |
| `modules/agent-core/src/main/java/com/campusclaw/agent/Agent.java:emit`；Projector.projectSafely | 监听器异常被隔离/记录 | 增加必须完成的提交端口，不能用普通观察订阅冒充故障可阻断的提交屏障 |
| `tool/agent/SubagentExecutionService.java:runChild/projectProgress` | 直接 Factory → prompt.join，取消桥、进度、最后文本 | 独立持久子 Session、关系、启动防重、授权与可靠收尾 |
| `tool/cron/ManagedCronSessionRunner.java:execute`；`modules/cron/src/main/java/com/campusclaw/cron/CronJobExecutor.java` | Factory → prompt，Run JSONL 另存 | 按最新 Cron 设计原子受理并复用 Runtime；JSONL 不代替完整历史 |

PR #335 `dad4433d38fcb4104bd8d093f844ea2afc9612ee` 的 Skill 追溯、同步统计和测试是独立开发分支证据，详情见[M05](../04-CampusClaw命令系统/03-Skill加载统计/source-evidence.md)。不能将其视为 main 的新统一历史能力。

## 6. 尚未验证

通用提交端口、Subagent 持久准入、关联表、SQL 方言、同事务统计、删除竞争和性能均未实现/运行验收。本设计没有证明外部副作用 exactly-once，没有核验上游所有历史读取/裁剪选项，也没有推断托管产品服务端数据表。

<a id="session-kind-evidence"></a>

## 7. 2026-10-23 Session 分类与独立 Subagent 历史核验

本次先确认默认分支并重新 fetch 实现仓 `superheromeZzh/pi-mono-java main@e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2`，使用明确提交读取，保留用户工作树。设计仓个人 `main@e30934e912f3d993dd3363355e18e5547010fc0a` 与公共 `main@0de537c4db46ed3e74aab943fbc961f6bce43530` 分别隔离 fetch；本设计以个人主线的已定独立保留规则为依据。pi 的普通扩展与结果提交顺序同轮重新 fetch `badlogic/pi-mono main@14c8118412bffc8f8df7a088fde51d2ffa74fd8f` 后核验。默认分支快照不等于稳定发布，以下均为静态源码证据，未运行产品、上游或真实 GaussDB 测试。

### 7.1 Java 的已有机制与分类缺口

下列链接固定到本次 Java 提交；路径均相对实现仓。只升级此表范围，§1～§6 的 Skill、Codex、OpenCode 及其他历史证据保持原归属。

| 文件与符号 | 已观察事实与设计影响 |
|---|---|
| [session_schema.sql](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql#L32) · t_sessions，32～63 行 | 无 session_kind；parent_session_id 的现有注释为复制来源，不能复用成委派父身份；分类列与一致性校验待实现 |
| [RuntimeSessionService.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/session/RuntimeSessionService.java#L65) · create/get/delete/newSession | 主会话已创建数据库资源；读取和删除按 sessionId 定位，没有 Subagent 分类检查 |
| [RuntimeExecutionCoordinator.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeExecutionCoordinator.java#L98) · start/subscribe；[RuntimeEventProjector.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventProjector.java#L232) · project/persistAssistant/persistToolResults | 先安装投影与确认处理再 prompt；完整消息写历史，TurnEnd 保存工具结果；主会话已有持久化，最终结果逐调用可靠提交屏障仍是目标增量 |
| [MyBatisRuntimeSessionRepository.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java#L126) · acceptUserEventLocked/appendEntryLocked/appendEventsLocked；[RuntimeSessionMapper.xml](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeSessionMapper.xml#L41) · findSession/lockSessionForUpdate | 既有 Session 锁、序号、Entry 与公共事件同事务机制可复用；当前只按 ID 和状态检查，不能直接插入 Subagent 行后向公开入口放行 |
| [SubagentExecutionService.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/agent/SubagentExecutionService.java#L76) · runChild；[ManagedAgentSession.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/ManagedAgentSession.java#L132) · close/abort | 仍直接创建内存执行、等待 prompt、返回最后文本并 close；没有持久子 Session、父调用关系或恢复句柄；close 是取消和队列清理，不是删除 Agent 目录 |
| [ScheduledSessionStarter.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/schedule/session/ScheduledSessionStarter.java#L118) · prepare/prepareLinkedSession/acceptSession/startExecution | 当前 Cron 已使用 Session Repository 受理、提交后调用 Coordinator；新建和关联主会话路径均存在，不再适用旧 JSONL 结论；关联路径仍需增加分类检查 |
| [RuntimeEventReadMapper.xml](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/resources/mapper/session/RuntimeEventReadMapper.xml#L23) · listAgentEvents/countAgentEvents/findTurn | 用户请求聚合只按 agent_id 与 user.message 筛选；持久化 Subagent 后须对总数和分页同时加主会话条件，轮次读取同样不能当作子公开入口 |
| [RuntimeControlEventService.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeControlEventService.java#L104) · acceptInterrupt/acceptToolConfirmation/acceptPlanConfirmation/acceptQuestionAnswer；[RuntimeSessionControlDispatcher.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/runtime/RuntimeSessionControlDispatcher.java#L94) · dispatchStopLocked | 既有控制围绕固定执行目标，不因新增子留档而开放子确认/问答；父停止需经内部关系定位原 child_execution_id |
| [MyBatisRuntimeSessionRepository.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/persistence/MyBatisRuntimeSessionRepository.java#L470) · beginDeletion/completeCleanup；[ScheduleSessionDeleteHook.java](https://github.com/superheromeZzh/pi-mono-java/blob/e8da1b77d2780cb4d19d837c6f6ef95f8887e4c2/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/schedule/dispatch/ScheduleSessionDeleteHook.java#L26) · beforeDelete | idle 删除先跑 Schedule 钩子再锁会话；tombstone 与 cleanup 同事务；清理只处理该 Session 自己的数据，不删除共用 Agent 目录；保持独立保留与既有锁顺序 |

实现范围未发现公开 Session 列表或复制操作；M04 的这两类接口仍是存储目标，不能写成当前已经开放。新增分类、独立 Subagent 历史、父子关联与公开入口隔离均待实现；本次不修改实际安装 DDL，也不设计存量迁移或生产回填。

### 7.2 pi 普通示例与提交先后顺序的限定核验

此次从 §1 的历史 pi `42a3497d03ad17e308a2299fa824727894f2c0ec` 仅升级下表，不改写当时 experimental durable、Codex 或 OpenCode 的事实。

| 文件与符号 | 已观察事实与边界 |
|---|---|
| [examples/extensions/subagent/index.ts](https://github.com/badlogic/pi-mono/blob/14c8118412bffc8f8df7a088fde51d2ffa74fd8f/packages/coding-agent/examples/extensions/subagent/index.ts#L298) · runSingleAgent，298、360～383、709～710 行 | 普通仓库示例仍以 --no-session 运行独立子进程，details 保留消息与结果，父 content 返回最终文本；[官方默认功能说明](https://github.com/badlogic/pi-mono/blob/14c8118412bffc8f8df7a088fde51d2ffa74fd8f/packages/coding-agent/README.md#L19)明确不内建 Subagent，不能将该示例当作默认独立持久子会话 |
| [src/main.ts](https://github.com/badlogic/pi-mono/blob/14c8118412bffc8f8df7a088fde51d2ffa74fd8f/packages/coding-agent/src/main.ts#L364) · createSessionManager；[session-manager.ts](https://github.com/badlogic/pi-mono/blob/14c8118412bffc8f8df7a088fde51d2ffa74fd8f/packages/coding-agent/src/core/session-manager.ts#L1160) · _persist/appendCompaction | noSession 使用内存 SessionManager；持久模式可从首条 user/assistant 开始写完整 Message JSONL，压缩保存摘要与保留边界；不具有 CampusClaw 的集中式数据库事务 |
| [packages/agent/src/agent-loop.ts](https://github.com/badlogic/pi-mono/blob/14c8118412bffc8f8df7a088fde51d2ffa74fd8f/packages/agent/src/agent-loop.ts#L580) · 最终 ToolResult 的 message_end | 先 await 最终结果事件，再将结果推进模型上下文；该顺序不等于公共输出必定等待持久化 |
| [agent-session.ts](https://github.com/badlogic/pi-mono/blob/14c8118412bffc8f8df7a088fde51d2ffa74fd8f/packages/coding-agent/src/core/agent-session.ts#L1142) · _handleAgentEvent，1142～1165 行 | 先通知扩展/公共 listeners，再 appendMessage；CampusClaw 的提交后发布完整公共事件仍是自己的产品约束与架构差异 |

durable 示例在本次树中位于 `packages/durable/test/examples/21-subagent-foreground.ts`、`22-subagent-background.ts`；仅确认路径，不升级其实现与成熟度结论。未运行 pi 测试或实测子进程恢复。
