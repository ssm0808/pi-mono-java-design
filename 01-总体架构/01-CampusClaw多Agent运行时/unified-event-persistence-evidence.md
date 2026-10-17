# 统一历史：源码证据与差距

版本 1.0.0 · 2026-10-10。[目标设计](unified-event-persistence.md)不代表以下源码已经实现统一持久化。

## 1. 本次最新快照与升级范围

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
