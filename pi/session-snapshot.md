# SessionSnapshot 设计说明

## 文档信息

| 项目 | 内容 |
|---|---|
| 文档版本 | 1.0.0 |
| 状态 | 提案，待接口评审确认 |
| 主题 | SessionSnapshot 的边界、内容与恢复语义 |
| pi-mono 基线 | `086c32e74530564922d011ade23ff582c9d63116` |
| pi-mono-java 基线 | `dff835743fc7f3c93e1154c3eb51028749867ca8` |

## 1. 定义

`SessionSnapshot` 是在某一个确定版本上，对 Session 当前可观察状态的一次原子快照。

它的目标是让客户端能够：

1. 重建 Session 当前界面；
2. 判断 Session 是否存在执行中的 Run；
3. 恢复正在生成的 assistant 消息和运行中的工具；
4. 确认已接受但尚未消费的 steer；
5. 从明确的历史水位和事件水位继续读取后续数据；
6. 基于一致性版本安全地修改模型或 thinking。

`SessionSnapshot` 不是以下对象：

- Session 的完整持久化日志；
- 下一次发送给模型的完整上下文；
- Java `AgentStateSnapshot` 的网络序列化结果；
- 服务端崩溃恢复所需的完整 Runtime Checkpoint；
- 数据库表或运行时对象的直接镜像。

## 2. 概念边界

| 概念 | 面向对象 | 主要内容 | 对外暴露 |
|---|---|---|---|
| SessionSnapshot | 客户端 | 当前配置、状态、历史水位、Active Run 安全投影 | 是 |
| Session History | 客户端与审计 | 已持久化消息、Run 终态、usage 等 | 通过独立 history 接口 |
| Model Context | 模型调用 | compaction、分支、系统提示词和扩展处理后的 messages | 否 |
| Runtime Checkpoint | 服务端恢复 | operation、step、队列、pending write、deferred、tool replay 等 | 否 |
| AgentStateSnapshot | Java 进程内代码 | Agent 当前内存对象的线程安全副本 | 否 |

## 3. pi-mono 已观察行为

### 3.1 对外协议快照

pi-mono 的协议层 `SessionSnapshotSchema` 定义了以下字段：

- `id`；
- `name`；
- `cwd`；
- `createdAt`；
- `updatedAt`；
- `phase`；
- `model`；
- `thinkingLevel`；
- `attached`；
- `locked`；
- `revision`；
- `transcript`；
- `queuedSteer`；
- `queuedSteerCount`。

源码证据：

- `packages/protocol/src/schemas.ts`，`SessionSnapshotSchema`，基线行 241；
- `packages/protocol/src/schemas.ts`，`TranscriptItemSchema`，基线行 120；
- `packages/protocol/src/schemas.ts`，`TranscriptProgressSchema`，基线行 203；
- `packages/server/src/sessions.ts`，`normalizedSnapshot`，基线行 276。

pi-mono 将快照定义为权威状态，增量事件用于从一个快照版本推进到下一个状态。assistant 消息可以处于 `streaming`，工具条目可以处于 `running`，因此客户端重连后不只知道“正在运行”，还能够恢复已生成内容和运行中工具。

### 3.2 phase

pi-mono 对外协议中的 Session phase 包括：

| phase | 含义 |
|---|---|
| `idle` | 没有执行中的操作 |
| `turn` | 正在处理模型轮次 |
| `compaction` | 正在压缩上下文 |
| `branch_summary` | 正在生成分支摘要 |
| `retry` | 正在重试模型请求 |

工具执行没有单独作为 Session phase，而是通过状态为 `running` 的 tool transcript item 表达。

### 3.3 transcript

pi-mono 的 transcript 是面向客户端的显示投影，包括：

- user item；
- assistant item：`streaming`、`complete`、`error`、`aborted`；
- tool item：`running`、`complete`、`error`。

它不是模型请求上下文。模型上下文还会受到 compaction、分支选择、扩展转换和系统提示词的影响。

### 3.4 queuedSteer

pi-mono 在 SessionSnapshot 中返回完整的 `queuedSteer` 和 `queuedSteerCount`。这使重连客户端能够确认 steer 已经被服务端接受，但尚未被当前 Run 消费，从而避免重复提交。

### 3.5 连接相关字段

`attached` 是相对于当前连接的状态，同一个 Session 对不同连接可能有不同的值。`locked` 表示服务端是否已经独占获取 Session Runtime。

这两个字段属于 pi Server 的连接和运行时管理语义，不属于 CampusClaw HTTP Session 的固有业务状态。

## 4. pi-mono 内部恢复模型

pi-mono Agent Harness 定义了比对外 SessionSnapshot 更详细的内部状态，包括：

- lane 和 leafId；
- operation ID、operation kind；
- `running`、`suspended`、`aborting`；
- steer、follow-up、next-run 队列；
- pending writes；
- 未完成工具调用；
- deferred handle；
- 缺失的工具或模型；
- compaction 和 retry 状态；
- operation intent 和 step attempt；
- usage 和工具 replay policy。

源码证据：

- `packages/agent/src/harness/agent-harness.ts`，`SuspendedOperation`、`LaneSnapshot`、`SessionSnapshot`，基线行 140；
- `packages/agent/src/harness/session/types.ts`，`OperationStartedRecord`，基线行 87；
- `packages/agent/src/harness/session/types.ts`，`ToolStartedRecord`，基线行 150；
- `packages/agent/src/harness/session/types.ts`，`QueueEnqueuedRecord`，基线行 162；
- `packages/agent/src/harness/reducer.ts`，`LaneState`，基线行 79。

这些字段属于 Runtime Checkpoint，不应直接通过 HTTP 暴露。其原因包括：

- `effectiveArgs` 可能包含敏感工具参数；
- extension `resumeData` 属于内部扩展状态；
- pending write 和 replay policy 会把客户端绑定到服务端实现；
- 客户端不需要理解服务端恢复算法。

当前基线中，Agent Harness 的恢复和 watch 能力尚未完全实现：

- `AgentHarness.create` 遇到已有 record 时抛出 `HarnessNotImplemented("create.restore")`；
- `watchSession()` 返回未实现错误。

因此这部分是明确的内部目标模型和恢复协议依据，不能描述成已经完整可用的生产行为。

## 5. pi-mono 旧 SessionManager 的持久化语义

pi-mono coding-agent 的 JSONL SessionManager 持久化：

- Session header：ID、timestamp、cwd、parentSession；
- message；
- model change；
- thinking level change；
- compaction；
- branch summary；
- custom entry；
- custom message；
- label；
- session info。

记录通过 `id` 和 `parentId` 形成会话树。`buildSessionContext` 沿当前分支恢复有效 model、thinking level 和经过 compaction 的 messages。

源码证据：

- `packages/coding-agent/src/core/session-manager.ts`，`SessionHeader` 和 `SessionEntry`，基线行 32；
- `packages/coding-agent/src/core/session-manager.ts`，`getSessionContextSettings`，基线行 362；
- `packages/coding-agent/src/core/session-manager.ts`，`buildContextEntries`，基线行 418；
- `packages/coding-agent/src/core/session-manager.ts`，`buildSessionContext`，基线行 461。

该持久化日志是构建 Session 状态的事实来源，不等同于对外 SessionSnapshot。

## 6. pi-mono-java 已观察行为

### 6.1 AgentStateSnapshot

Java `AgentStateSnapshot` 包含：

- `systemPrompt`；
- `model`；
- `thinkingLevel`；
- `tools`；
- `messages`；
- `streaming`；
- `streamMessage`；
- `pendingToolCalls`；
- `error`。

源码证据：

- `modules/agent-core/src/main/java/com/campusclaw/agent/state/AgentStateSnapshot.java`，`AgentStateSnapshot`，基线行 21；
- `modules/agent-core/src/main/java/com/campusclaw/agent/state/AgentState.java`，`snapshot()`，基线行 266。

`AgentState.snapshot()` 在读锁内生成副本，能够保证这些 AgentState 字段的一致读取。但该锁不覆盖 SessionManager、Run 事件序号和持久化历史水位。CampusClaw 要生成完整 HTTP SessionSnapshot，需要建立 Session 级一致性边界，避免不同字段来自不同时间点。

`AgentStateSnapshot` 是进程内对象，不能直接作为 API DTO。以下内容不得直接暴露：

- system prompt；
- `AgentTool` 实例；
- 原始 `Model` 对象；
- 内部异常和堆栈；
- 未脱敏工具参数；
- 凭据和 Provider 内部状态。

### 6.2 WebSocket get_state

当前 Java WebSocket `get_state` 只返回：

- `conversation_id`；
- `isStreaming`；
- `model`；
- `thinkingLevel`；
- `messageCount`。

源码证据：

- `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/ChatWebSocketHandler.java`，`handleGetState`，基线行 365。

该结构是状态摘要，不足以作为断线恢复快照，因为它无法恢复：

- 正在生成的 assistant 内容；
- 运行中工具；
- open content；
- steer 队列；
- aborting 或 suspended 状态；
- 历史和事件消费水位。

### 6.3 Java 持久化缺口

Java SessionManager 会写入 `model_change` 和 `thinking_level_change`，但 `loadSession()` 恢复时只提取 message。SessionPool 随后使用 `baseConfig` 初始化 Agent，再恢复 messages。

源码证据：

- `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/SessionManager.java`，`loadSession`，基线行 160；
- 同文件，`extractMessages`，基线行 204；
- 同文件，`appendModelChange`，基线行 304；
- 同文件，`appendThinkingLevelChange`，基线行 326；
- `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/mode/server/SessionPool.java`，`createSessionWithPersistence`，基线行 204。

因此当前 Java 在进程重启或 SessionPool 淘汰后，可能丢失 Session 已切换的模型和 thinking。这与“一个 Session 可以切换模型”的产品语义不一致。

当前 Java 也没有持久化 Run ID、step、工具执行状态、steer 队列和 pending write，因此尚不能承诺 active Run 的跨进程恢复。

## 7. CampusClaw 目标 SessionSnapshot

以下结构是目标设计提案，不是当前 pi-mono-java 已实现行为。

```json
{
  "session_id": "01JY8W6M8D9K4H2Q7P3V5N1R0T",
  "agent_id": "agent_01JY8VZY4CRQN4PJW8M94D1B2C",
  "model_id": "model_current",
  "thinking": "hidden",
  "state": "running",
  "history_seq": 42,
  "created_at": "2026-08-15T10:00:00Z",
  "updated_at": "2026-08-15T10:05:00Z",
  "active_run": {
    "run_id": "run_01JY8X2E3R4T5Y6U7I8O9P0A1S",
    "state": "running",
    "phase": "turn",
    "started_at": "2026-08-15T10:04:00Z",
    "run_seq": 18,
    "model_id": "model_frozen_for_run",
    "thinking": "hidden",
    "message_snapshot": {
      "message_id": "msg_01JY8X3A4S5D6F7G8H9J0K1L2Z",
      "role": "assistant",
      "status": "streaming",
      "content": []
    },
    "open_contents": {},
    "active_tools": [],
    "queued_steers": []
  }
}
```

HTTP 响应使用 ETag 表示整个快照的一致性版本：

```http
ETag: "session-rev-7"
Cache-Control: no-store
```

如已使用 ETag，响应体不强制重复返回 `revision`。

## 8. 字段语义

### 8.1 Session 层

| 字段 | 必填 | 语义 |
|---|---|---|
| `session_id` | 是 | Session 稳定身份，不受模型切换影响 |
| `agent_id` | 是 | Session 不可变的 Agent 绑定 |
| `model_id` | 是 | Session 当前默认模型，供后续 Run 使用 |
| `thinking` | 是 | Session 当前默认 thinking 配置 |
| `state` | 是 | `idle` 或 `running` |
| `history_seq` | 是 | 快照所覆盖的持久历史水位，idle 时仍然存在 |
| `created_at` | 是 | Session 创建时间 |
| `updated_at` | 是 | Session 最近一次可观察状态变化时间 |
| `active_run` | 是 | idle 时为 null，running 时为 Active Run 快照 |

### 8.2 Active Run 层

| 字段 | 必填 | 语义 |
|---|---|---|
| `run_id` | 是 | 当前 Active Run 身份 |
| `state` | 是 | Run 当前控制状态，例如 queued、running、aborting、suspended |
| `phase` | 是 | Run 当前执行阶段，最终枚举待接口评审确认 |
| `started_at` | 是 | Run 接受或开始时间，最终语义待确认 |
| `run_seq` | 是 | 快照已覆盖的 Run 事件水位 |
| `model_id` | 是 | Run 接受时原子固化的模型 |
| `thinking` | 是 | Run 接受时原子固化的 thinking |
| `message_snapshot` | 是 | 当前正在生成的 assistant 消息安全投影；没有时为 null |
| `open_contents` | 是 | 尚未闭合的文本、thinking 或工具参数增量 |
| `active_tools` | 是 | 运行中工具的脱敏投影 |
| `queued_steers` | 是 | 已接受但尚未消费的 steer 消息投影 |

## 9. 一致性约束

### 9.1 Session 状态与 Active Run

```text
state = idle    => active_run = null
state = running => active_run != null
```

服务端必须在同一个一致性边界内读取 `state` 和 `active_run`，禁止返回 `state=idle` 但仍携带 Active Run 的撕裂快照。

### 9.2 模型语义

```text
Session.model_id
  = Session 当前默认模型

ActiveRun.model_id
  = Run 接受时固化的实际模型
```

当 Session 在 Run 执行期间允许切换默认模型时，两个 model ID 可以不同。这不产生新的 Session，也不改变 Session 身份。

### 9.3 thinking 语义

thinking 与模型采用相同规则：顶层是 Session 当前默认值，Active Run 中是该 Run 接受时固化的值。

### 9.4 水位语义

```text
history_seq
  = 当前快照已经覆盖的持久历史最大序号

run_seq
  = 当前快照已经覆盖的 Run 事件最大序号
```

客户端加载快照后，只消费大于对应水位的后续记录或事件。

### 9.5 ETag

ETag 标识整个 SessionSnapshot 的版本，而不只是某一个字段。模型、thinking、state、history_seq 或 Active Run 发生可观察变化时，都必须产生新的 ETag。

## 10. 不进入 SessionSnapshot 的内容

以下字段明确排除：

- 完整历史 transcript；
- system prompt；
- 完整工具定义和工具实现对象；
- Provider 凭据、认证状态和密钥；
- 原始工具执行上下文；
- 未脱敏工具参数；
- Java exception、stack trace；
- pending write；
- extension resumeData；
- tool replay policy；
- pi-mono 的 `attached`、`locked` 和 CLI `cwd`；
- 仅供模型调用的最终 context messages。

## 11. 对当前第二个 HTTP 接口的影响

目标接口：

```http
GET /campusclaw-service/v1/sessions/{session_id}
```

当前评审方向应定义为：

> 返回足以恢复客户端界面和事件消费的权威 Session 快照，但不返回完整持久历史，也不暴露服务端 Runtime Checkpoint。

相对于当前 SessionResource / ActiveRunSnapshot 提案，建议后续评审以下增量：

1. Session 层增加 `updated_at`；
2. Session 层始终返回 `history_seq`；
3. Active Run 增加明确的 `state`；
4. Active Run 增加执行 `phase`；
5. Active Run 增加 `started_at`；
6. Active Run 增加 `queued_steers`；
7. 使用 ETag 作为快照一致性版本；
8. Java 实现建立 Session 级原子快照边界；
9. Java 恢复流程必须恢复 model 和 thinking；
10. 若承诺跨进程恢复 Active Run，必须增加持久化 Runtime Checkpoint 或等价操作日志。

以上内容仍是第二个接口的设计提案，只有在接口评审明确确认后，才能固化为正式契约。

## 12. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-08-15 | 基于 pi-mono 和 pi-mono-java 源码建立 SessionSnapshot 独立设计说明 |
