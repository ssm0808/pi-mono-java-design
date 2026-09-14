# CampusClaw Java 四表 GaussDB Session 事件存储 SR 设计

> 文档编号：SR-MEM-001<br>
> 版本：v0.15.0<br>
> 日期：2026-09-14<br>
> 状态：设计评审稿<br>
> pi 源码基线：[`f0deb8dd8e9611e89b5bc4145ca92c03ae6ed4ee`](https://github.com/badlogic/pi-mono/tree/f0deb8dd8e9611e89b5bc4145ca92c03ae6ed4ee)<br>
> 设计仓库分析基线：`b5b0d1ecc3419c5960cac394b683a635ac9f853e`<br>
> CampusClaw Java 源码基线：四表方案未核验 Java 实现；本文 Java 接口、GaussDB 存储和发布机制为目标方案，压缩专题单独登记已核验实现<br>
> 目标数据库：集中式 GaussDB<br>
> JDBC 约束：openGauss JDBC `6.0.0-htrunks.csi.gaussdb_kernel.opengaussjdbc.r1`

## 1. 职责与设计结论

本模块维护 Session 历史、当前路径、模型上下文恢复和累计用量。四表方案的源码范围见 §2；运行时压缩算法另见[压缩与恢复](./compaction.md)，其实现证据独立登记，不把四表目标等同于最新 Runtime 数据库全貌。公共事件投影由[Session Events](../../01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md)维护。

CampusClaw 的 Session 存储由四张表组成：

1. `t_sessions`：保存 Session 基本信息，以及当前路径的最后一条记录。
2. `t_session_entries`：保存全部不可变的 Entry（历史记录）及其父子关系。
3. `t_session_sequences`：为每个 Session 分配严格递增的写入序号。
4. `t_session_materialized`：保存当前路径摘要和 Session 自创建以来的累计用量。

本设计不创建 `t_branch_entries`、`t_branch_tips` 和 `t_entry_materialized`。在 pi SQLite 中，前两张表只是可以根据 `parent_id` 重建的分支路径缓存。CampusClaw 不提供通用的分支创建、切换、恢复和查询能力，因此读取时直接从 `t_sessions.active_leaf_id` 开始，逐条按 `t_session_entries.parent_id` 向前回溯。标签能力也不在本期范围内，所以不再保存独立的标签汇总数据。

产品只允许编辑当前路径上最近一条用户消息。编辑时不覆盖、不删除旧 Entry，而是在同一位置写入一条新的用户消息，再把 `active_leaf_id` 指向这条新记录。旧消息及其后续记录仍然完整保留，但只能通过内部审计接口查看。普通分页、模型上下文、会话复制（fork）和 UI 都只读取当前路径。

`t_session_materialized.payload` 分离两种口径：

- `activePath`：当前路径的名称、消息数、当前模型和思考级别；编辑后根据新路径重新计算。
- `lifetimeUsage`：Session 自创建以来，所有已成功保存的模型调用产生的 Token 和费用总和；编辑消息不会减去已经发生的消耗。

集中式 GaussDB 允许多个 AgentService 实例同时连接同一个 Schema，因此不能只依赖 pi SQLite 在单进程内使用的 `SerialOperationQueue`。所有追加和编辑事务都先锁定 `t_sessions`，再锁定 `t_session_sequences`。请求还必须提交预期的父记录或预期的当前路径末端；如果数据库中的 `active_leaf_id` 已经变化，则拒绝该请求，避免旧 Run 或过期页面继续写入。

![CampusClaw 四表 Session 架构](./设计图/memory-architecture.svg)

[原尺寸 SVG](./设计图/memory-architecture.svg) · [查看 PlantUML 源码](./设计图/diagram.puml#L6)

### 1.1 术语约定

代码标识、数据库字段和固定枚举值保持原名；解释性文字使用下列中文表达：

| 源码或代码中的术语 | 本文用语 | 说明 |
|---|---|---|
| Entry | Entry（历史记录） | 保留类型名；表达数据含义时使用“历史记录” |
| parent chain | 按 `parent_id` 回溯得到的路径 | 用来说明如何从末端向前读取当前路径 |
| active leaf | 当前路径末端 | 字段名仍为 `active_leaf_id` |
| active path | 当前路径 | JSON 字段名仍为 `activePath` |
| append log | 全部历史记录 | 强调按 `entry_seq` 保留的完整写入历史 |
| expected leaf/parent | 预期的路径末端/父记录 | 对应 `expectedLeafId` 和 `expectedParentEntryId` |
| fence | 并发校验或写入前置条件 | 按实际并发语义解释，不使用字面翻译 |
| materialized state / projection | 会话汇总/可重建的派生数据 | 表名仍为 `t_session_materialized` |

## 2. 来源证据与设计边界

### 2.1 观察到的 pi 行为

pi 基线使用七张 Session 数据表：`sessions`、`session_entries`、`session_sequences`、`branch_entries`、`branch_tips`、`session_materialized` 和 `entry_materialized`。此外，应用侧的数据库升级机制还会维护 `migrations` 表。

关键源码事实如下：

- `session_entries.parent_id` 记录 Entry 之间的父子关系；从 `sessions.active_leaf_id` 开始按 `parent_id` 回溯，即可得到当前路径。
- 追加 Entry 时，pi 会在同一个 SQLite 事务中写入 Entry、更新写入序号、会话汇总、当前路径末端和分支路径缓存。
- `branch_entries` 和 `branch_tips` 缓存了从会话起点到各分支末端的完整路径；这些数据可以根据 `parent_id` 重新生成。
- `entry_materialized` 当前只保存从 `label` 设置和清除记录中提取的派生数据。
- `SerialOperationQueue` 只能保证同一个 SQLite 存储后端实例内的串行执行。

源码证据：

- [`001_initial.sql`](https://github.com/badlogic/pi-mono/blob/f0deb8dd8e9611e89b5bc4145ca92c03ae6ed4ee/packages/storage/sqlite-node/src/sqlite/migrations/001_initial.sql#L1-L59)
- [`002_branch_tips.sql`](https://github.com/badlogic/pi-mono/blob/f0deb8dd8e9611e89b5bc4145ca92c03ae6ed4ee/packages/storage/sqlite-node/src/sqlite/migrations/002_branch_tips.sql#L1-L12)
- [`SqliteSessionConnection.appendEntry()`](https://github.com/badlogic/pi-mono/blob/f0deb8dd8e9611e89b5bc4145ca92c03ae6ed4ee/packages/storage/sqlite-node/src/sqlite/storage/index.ts#L367-L418)
- [`branch-cache.ts`](https://github.com/badlogic/pi-mono/blob/f0deb8dd8e9611e89b5bc4145ca92c03ae6ed4ee/packages/storage/sqlite-node/src/sqlite/storage/branch-cache.ts#L1-L326)
- [`session-materialized.ts`](https://github.com/badlogic/pi-mono/blob/f0deb8dd8e9611e89b5bc4145ca92c03ae6ed4ee/packages/storage/sqlite-node/src/sqlite/storage/session-materialized.ts#L1-L355)
- [`SerialOperationQueue`](https://github.com/badlogic/pi-mono/blob/f0deb8dd8e9611e89b5bc4145ca92c03ae6ed4ee/packages/storage/sqlite-node/src/sqlite/repo.ts#L50-L67)

### 2.2 CampusClaw 目标决策

| 决策 | 分类 | 设计原因 |
|---|---|---|
| 只保留四张 Session 表 | 产品约束 | 产品只展示一条当前路径，不提供通用分支管理 |
| 保留 `parent_id` 与 `active_leaf_id` | 产品约束 | 最近用户消息编辑仍需保留旧路径并切换当前路径 |
| 删除分支路径缓存 | 架构变化 | 构建模型上下文时直接按 `parent_id` 回溯，避免额外的缓存写入和修复逻辑 |
| 删除 `t_entry_materialized` 和标签能力 | 产品约束 | 当前产品没有标签查询和展示需求 |
| 编辑最近用户消息时写入新 Entry | 安全与审计强化 | 不覆盖旧输入，也不改写已经发生的模型调用和工具调用历史 |
| 增加预期父记录/路径末端校验 | 并发强化 | 拒绝旧 Run 的迟到写入，以及基于过期页面发起的编辑 |
| 分开保存当前路径摘要与会话累计用量 | 架构变化 | 切换当前路径不能减去已经发生的 Token 和费用 |
| 不沿用 pi 的 `migrations` 表 | 架构变化 | 数据库结构统一由 CampusClaw 数据库发布平台升级 |

上述决策都是 CampusClaw 的目标方案，不是 pi SQLite 的原有行为。CampusClaw 保留 pi 的 Entry 编码、父子关系、写入序号、压缩裁剪和模型上下文转换规则，但不保留通用分支管理、路径切换和标签能力。

### 2.3 范围与非目标

本期包括：

- `create`、`open`、`list`、`delete`、`append` 和模型上下文重建。
- 当前路径分页和内部全历史审计分页。
- 编辑当前路径上最近一条用户消息。
- 复制 Session（fork）时只复制当前路径。
- SQLite/JSONL 到四表结构的导入和受控导出。
- 集中式 GaussDB 多实例写入的并发校验。

本期不包括：

- 通用 `moveTo`、分支列表、分支切换、分支恢复或任意历史消息编辑。
- 新写入 `leaf`、`branch_summary` 或 `label` Entry。
- 标签 API 和标签派生数据。
- Runtime Checkpoint、跨会话长期记忆、全文检索、向量索引、多租户和 RLS。
- 持久化 Run、工具副作用补偿、operation id、request hash 或数据库幂等结果表。
- AgentService 启动时执行 DDL 或维护数据库升级记录。

已经执行的外部工具操作不会因用户编辑消息而自动撤销。编辑后启动的新 Run 如果再次调用高风险工具，必须重新执行产品既有的确认流程。

## 3. 四表数据模型

![CampusClaw 四表 Session 数据模型](./设计图/memory-data-model.svg)

[原尺寸 SVG](./设计图/memory-data-model.svg) · [查看 PlantUML 源码](./设计图/diagram.puml#L165)

### 3.1 `t_sessions`

| 字段 | 类型 | 语义 |
|---|---|---|
| `id` | `VARCHAR(128)` | Session 唯一 ID |
| `created_at` | `TIMESTAMPTZ(3)` | 创建时间 |
| `cwd` | `VARCHAR(512)` | 受控规范工作目录 |
| `parent_session_id` | `VARCHAR(128)` | 复制会话（fork）的来源 Session；没有来源时为空 |
| `metadata` | `JSONB` | 调用方附加元数据；没有时为 SQL `NULL` |
| `active_leaf_id` | `VARCHAR(128)` | 当前路径的最后一条记录；空 Session 时为空 |

`active_leaf_id` 逻辑引用同 Session 的 `t_session_entries.id`。应用在事务内维护该关系；本版本不增加物理外键。

### 3.2 `t_session_entries`

| 字段 | 类型 | 语义 |
|---|---|---|
| `session_id` | `VARCHAR(128)` | 所属 Session |
| `id` | `VARCHAR(128)` | Session 内唯一 Entry ID |
| `entry_seq` | `BIGINT` | Session 内严格递增的写入序号 |
| `parent_id` | `VARCHAR(128)` | 同 Session 直接父 Entry；根 Entry 为空 |
| `type` | `VARCHAR(64)` | Entry 类型标识 |
| `timestamp` | `TIMESTAMPTZ(3)` | Entry 自带事件时间 |
| `payload` | `JSONB` | 类型相关内容 |

主键为 `(session_id, id)`，唯一索引 `(session_id, entry_seq)` 保证同一 Session 内的写入顺序稳定且不重复。当前路径必须根据 `parent_id` 回溯；`entry_seq` 只表示各条记录的保存先后，不能直接用来渲染聊天记录。

编辑后的用户消息不新增 `replaces_entry_id`。Service 在事务中确认编辑目标确实是当前路径上最近一条用户消息，再将新 Entry 的 `parent_id` 设为旧消息的 `parent_id`。这样会形成两条从同一父记录开始的后续路径，但产品只展示 `active_leaf_id` 指向的那一条。

### 3.3 `t_session_sequences`

每个 Session 一行：

| 字段 | 类型 | 语义 |
|---|---|---|
| `session_id` | `VARCHAR(128)` | 所属 Session |
| `next_seq` | `BIGINT` | 下一条 Entry 使用的 `entry_seq`；从 1 开始 |

所有写事务都按 `t_sessions` → `t_session_sequences` 的顺序加锁。分配 `entry_seq` 后，必须在同一事务中写入 Entry 并更新 `active_leaf_id`；任一步失败都必须整体回滚。

### 3.4 `t_session_materialized`

每个 Session 一行：

| 字段 | 类型 | 语义 |
|---|---|---|
| `session_id` | `VARCHAR(128)` | 所属 Session |
| `payload` | `JSONB` | 当前路径摘要和会话累计用量 |

`payload` 的结构固定为：

```json
{
  "activePath": {
    "name": null,
    "messageCount": 0,
    "currentModel": null,
    "currentThinkingLevel": null
  },
  "lifetimeUsage": {
    "cachedTokens": 0,
    "uncachedTokens": 0,
    "totalTokens": 0,
    "costTotal": 0
  }
}
```

规则：

- `activePath` 按当前路径从起点到末端的顺序计算；编辑或复制会话后整体重算。
- 沿当前路径正常追加 Entry 时，可以增量更新 `activePath`。
- `lifetimeUsage` 只累计已成功保存的 `assistant`、`compaction` 等带有 usage 的 Entry；切换当前路径时不减少。
- 新的模型调用成功保存后，同时更新 `activePath` 和 `lifetimeUsage`。
- JSON 字段必须完整，数值必须为有限非负数；Service 和导入器负责校验，JSONB 负责 JSON 语法校验。
- 这两组汇总都可以根据 `t_session_entries` 重新计算；完整历史仍以 `t_session_entries` 为准。

## 4. 最终态 GaussDB DDL

完整初始化语句见 [`schema.sql`](./schema.sql)，字段含义见 §3；SQL 只在该文件维护。


最终的 Session 应用 Schema 只包含上述四张表和 17 个字段。数据库发布平台负责初始化新环境，并在已有环境中删除三张不再使用的派生表。AgentService 运行账号只允许执行 DML，不具备 DDL 权限。

## 5. Java 接口与错误语义

### 5.1 应用服务

```java
interface MemorySessionApplicationService {
    SessionDTO createSession(CreateSessionDTO dto);
    SessionDTO openSession(String sessionId);
    List<SessionSummaryDTO> listSessions(SessionListQueryDTO queryDTO);
    void deleteSession(String sessionId);
    SessionDTO forkSession(ForkSessionDTO dto);
    AppendResultDTO appendEntry(AppendEntryDTO dto);
    SessionEntryDTO editLastUserMessage(EditLastUserMessageDTO dto);
    ContextSnapshotDTO loadContext(LoadContextDTO dto);
    EntryPageDTO pageEntries(EntryPageQueryDTO queryDTO);
    EntryPageDTO pageAllEntriesForAudit(AuditEntryPageQueryDTO queryDTO);
}
```

不提供 `moveTo`、`findEntriesOnBranch`、分支选择和标签相关能力。`pageEntries` 只返回当前路径；`pageAllEntriesForAudit` 仅供已授权的内部调用方使用，按 `entry_seq` 返回全部历史记录。

上述对象都是内部 Application Service DTO，不引入 PO、DO 或 Entity。如果通过 Controller 或对外 API 提供编辑和分页能力，请求与响应必须分别使用 `*RequestVO` 和 `*ResponseVO`。请求 VO 使用 Jakarta Bean Validation；Controller 只收发 VO，Service 负责 VO/DTO 转换、最近用户消息校验和事务编排，MyBatis Mapper 只接收或返回 DTO 与标量结果。

### 5.2 写入 DTO

`AppendEntryDTO` 必须包含：

```text
sessionId
expectedParentEntryId
entry
```

`expectedParentEntryId` 可以为空，但仅限于空 Session 首次追加 Entry 的场景。

`EditLastUserMessageDTO` 固定包含：

```text
sessionId
targetEntryId
expectedLeafId
newUserMessage
```

`newUserMessage` 必须是合法的用户消息。调用方不提交新 Entry 的 ID、`entry_seq`、`timestamp` 和 `parent_id`；这些值统一由 Service 产生。

### 5.3 稳定错误

| 错误码 | 条件 |
|---|---|
| `SESSION_NOT_FOUND` | Session 不存在 |
| `SESSION_INVALID_ENTRY` | Entry 类型、`payload`、ID 或请求字段非法 |
| `SESSION_EDIT_TARGET_NOT_LATEST_USER_MESSAGE` | 编辑目标不是当前路径最近用户消息 |
| `SESSION_STALE_LEAF` | 编辑请求中的 `expectedLeafId` 与当前路径末端不一致 |
| `SESSION_STALE_PARENT` | 追加请求中的 `expectedParentEntryId` 与当前路径末端不一致 |
| `SESSION_CORRUPTED_PATH` | 父节点缺失、跨 Session、重复节点或形成环 |
| `SESSION_PATH_TOO_DEEP` | 当前路径超过部署配置的最大递归深度 |
| `SESSION_STORAGE_ERROR` | 事务、JDBC 或会话汇总写入失败 |

校验错误不能通过截断、自动选择最新路径或静默丢弃旧 Entry 恢复。

## 6. 事务与并发协议

![CampusClaw 四表 Session 写事务](./设计图/memory-write-transaction.svg)

[原尺寸 SVG](./设计图/memory-write-transaction.svg) · [查看 PlantUML 源码](./设计图/diagram.puml#L95)

### 6.1 创建 Session

一个事务按顺序插入：

1. `t_sessions(active_leaf_id = NULL)`。
2. `t_session_sequences(next_seq = 1)`。
3. `t_session_materialized` 的初始汇总数据。

### 6.2 追加 Entry

```text
BEGIN
  SELECT t_sessions WHERE id = ? FOR UPDATE
  校验 active_leaf_id IS NOT DISTINCT FROM expectedParentEntryId
  拒绝新写入的 leaf、branch_summary 和 label Entry
  SELECT t_session_sequences WHERE session_id = ? FOR UPDATE
  分配 next_seq
  INSERT t_session_entries(parent_id = expectedParentEntryId)
  UPDATE t_session_sequences
  按 Entry 类型更新 activePath 和 lifetimeUsage
  UPDATE t_session_materialized
  UPDATE t_sessions SET active_leaf_id = newEntryId
COMMIT
```

加锁顺序固定为 Session 主表记录，然后是序号表记录。如果某个实例仍按旧的父记录追加 Entry，则返回 `SESSION_STALE_PARENT`。该请求不写入任何 Entry，也不更改当前路径。

### 6.3 编辑最近用户消息

编辑请求进入数据库事务前，Service 会尝试取消与该 Session 关联的运行中 Run。取消只是尽力而为；最终仍由事务内的 `expectedLeafId` 校验防止旧 Run 继续写入。

```text
BEGIN
  SELECT t_sessions WHERE id = ? FOR UPDATE
  校验 active_leaf_id IS NOT DISTINCT FROM expectedLeafId
  读取并校验当前路径
  从路径末端向前查找最近一条用户消息
  校验 nearestUser.id = targetEntryId
  SELECT t_session_sequences WHERE session_id = ? FOR UPDATE
  分配 next_seq
  INSERT new user message(parent_id = target.parent_id)
  UPDATE t_session_sequences
  按新的当前路径重新计算 activePath
  lifetimeUsage 保持不变
  UPDATE t_session_materialized
  UPDATE t_sessions SET active_leaf_id = newUserEntryId
COMMIT
```

编辑完成后，旧消息及其后续记录仍然存在。普通 API 不提供恢复旧路径的能力。新 Run 以新用户 Entry 作为 `expectedParentEntryId`；旧 Run 携带的父记录已经过期，因此追加请求会被并发校验拒绝。已经完成的外部工具调用不会自动回滚。

### 6.4 复制 Session（fork）

复制 Session 时，只读取来源 Session 的当前路径，并按原顺序写入新 Session。新 Session 设置 `parent_session_id=sourceSessionId`，不允许调用方选择其他起点或分支。复制过程保留 Entry ID 和 `parent_id` 关系，为新 Session 从 1 开始连续分配 `entry_seq`，并重新计算会话汇总。

### 6.5 删除 Session

一个事务按顺序删除：

1. `t_session_entries`。
2. `t_session_materialized`。
3. `t_session_sequences`。
4. `t_sessions`。

不使用 `ON DELETE CASCADE` 代替事务顺序。

## 7. 当前路径、分页和模型上下文

![CampusClaw 不依赖路径缓存的模型上下文重建](./设计图/memory-context-rebuild.svg)

[原尺寸 SVG](./设计图/memory-context-rebuild.svg) · [查看 PlantUML 源码](./设计图/diagram.puml#L258)

### 7.1 读取当前路径

Repository 使用递归 CTE，从 `active_leaf_id` 指向的记录开始，按 `parent_id` 逐条回溯。读取结果必须满足以下条件：

- 每条记录的 `session_id` 都与请求的 Session 一致。
- `active_leaf_id` 非空时，必须能找到对应 Entry。
- 每个非空 `parent_id` 都必须指向实际存在的同 Session Entry。
- 同一条路径中不能重复出现同一个 Entry ID；一旦发现环，立即返回错误。
- 递归深度不得超过部署配置；默认上限由实现配置，不写入数据库。

校验通过后，再按 `entry_seq ASC` 返回当前路径。不能把同一 Session 的全部 Entry 直接按 `entry_seq` 排序后当作聊天记录，因为其中同时包含编辑前的旧路径。

### 7.2 普通分页与审计分页

- `pageEntries`：内部读取当前路径，再按路径内 `entry_seq` 分批加载，供 Session 打开和模型恢复使用。公共 UI 经 [ListEvents](../../01-总体架构/01-CampusClaw多Agent运行时/chat-events-history-design.md#3-普通数字页码) 读取已过滤的完整事件，并使用普通 `page/nextPage`；内部读取位置不作为公共游标暴露。
- `pageAllEntriesForAudit`：经过内部授权后，按整个 Session 的 `entry_seq` 分页，同时显示旧路径和当前路径；返回结果不得作为模型上下文。

### 7.3 重建模型上下文

```text
leaf = t_sessions.active_leaf_id
path = validatedParentChain(leaf)
trimmedPath = trimPathToRootOrCompaction(path)
state = deriveModelThinkingAndTools(trimmedPath)
messages = project(defaultContextEntryTransform(trimmedPath))
```

删除分支路径缓存不会改变 compaction、`retainedTail`、旧字段 `firstKeptEntryId` 或自定义上下文转换器的处理规则。历史导入的 `leaf`、`branch_summary` 和 `label` Entry 可以保留在审计历史中；新写入接口拒绝这些类型，标签数据也不进入会话汇总。

## 8. 数据迁移与发布

### 8.1 SQLite 导入

1. `sessions` → `t_sessions`，保留最终 `active_leaf_id`。
2. `session_entries` → `t_session_entries`，保留全部 Entry、`entry_seq` 和 `parent_id` 关系。
3. `session_sequences` → `t_session_sequences`，并校验 `next_seq > MAX(entry_seq)`。
4. 不导入 `branch_entries`、`branch_tips`、`entry_materialized` 或 `migrations`。
5. 根据最终的当前路径重新计算 `activePath`；根据全部已成功保存、带有 usage 的 Entry 重新计算 `lifetimeUsage`。
6. 历史 `label`、`leaf` 和 `branch_summary` Entry 只作为审计记录保留，不开放对应的写入 API。

导入时必须校验字符串长度、时间戳、JSON 结构、主键、`entry_seq` 唯一性、`parent_id` 引用完整性、`active_leaf_id` 和模型上下文结果。如果某个 Session 的当前路径无法完整回溯，则不得只导入其中一部分数据。

### 8.2 JSONL 导入

JSONL 导入器只写入四张表。它先保存全部 Entry，再确定目标 `active_leaf_id`。如果源数据没有明确记录当前路径末端，只有在能够证明全部历史是单一路径时，才能选择最后一条 Entry；否则必须返回迁移错误，不得猜测当前路径。

### 8.3 已有七表环境

数据库发布平台按以下顺序升级：

1. 部署能够读取旧 payload 并写入新 payload 的兼容应用版本或执行离线转换。
2. 重建并校验每个 Session 的 `activePath` 与 `lifetimeUsage`。
3. 停止旧版本写入，并确认已无 Mapper 访问三张待删表。
4. 删除 `t_entry_materialized`、`t_branch_tips`、`t_branch_entries`。
5. 抽样校验四张表的行数、键集合、当前路径、模型上下文和会话汇总。
6. 部署只依赖四表的应用版本。

具体迁移工具、变更历史、校验和以及并发锁由 CampusClaw 数据库发布平台统一管理；相关元数据不放在 Session 应用 Schema 内。

## 9. 测试与验收

### 9.1 数据库结构

- Session 应用 Schema 中的表集合严格等于四张目标表。
- 四表共 17 个字段，均有中文 `COMMENT ON COLUMN`。
- 不存在三张删除表及其索引、Mapper 或运行查询。
- ID 及引用字段、`type`、`cwd`、序号、时间和 JSONB 字段均与本文的类型定义一致。

### 9.2 行为

- `create`、`open`、`list`、`delete` 和连续追加 Entry。
- 空 Session 首次追加时，`expectedParentEntryId` 为空；此后每次追加都必须与当前路径末端一致。
- 编辑最近一条用户消息后，新路径出现在普通分页和模型上下文中，旧路径只能通过审计分页查看。
- 编辑非最近用户消息、提交过期的 `expectedLeafId`、旧 Run 迟到写入和并发编辑都必须返回明确错误。
- 复制 Session 时只复制当前路径。
- 新写入的 `leaf`、`branch_summary` 和 `label` Entry 必须被拒绝。

### 9.3 会话汇总与事务

- 编辑后根据新的当前路径重新计算 `activePath`；旧回答不再计入当前消息数和当前模型状态。
- `lifetimeUsage` 编辑前后不回退，新回答成功持久化后继续增加。
- 追加、编辑、复制或删除事务中的任一步失败时，整个事务都必须回滚。
- 多实例针对同一当前路径末端并发追加时，只允许一个请求成功。

### 9.4 路径与迁移

- 父记录缺失、`parent_id` 指向其他 Session、路径成环或超过深度限制时，都必须返回明确错误。
- 压缩裁剪、`retainedTail` 和旧字段 `firstKeptEntryId` 的处理结果与 pi 基线一致。
- 导入包含历史分支的 SQLite Session 后，当前路径、审计历史和模型上下文均正确，且目标库中不存在分支路径缓存表。
- 历史 `label` Entry 可以审计，但不对外提供标签能力。

### 9.5 JDBC 与发布边界

- 使用指定 JDBC JAR 验证 TLS、认证、类型绑定、递归 CTE、`FOR UPDATE`、事务回滚和 SQLState 映射。
- 使用真实的集中式 GaussDB 验证锁等待、死锁超时、复合索引和最大路径查询计划。
- AgentService 运行账号执行 DDL 必须失败；数据库发布身份执行目标 DDL 和 17 条注释必须成功。
- 真实服务端和定制 JDBC 验证完成前，不得宣称生产兼容性已通过。

## 10. 安全与运维

- JDBC 强制使用 TLS，凭据来自部署 Secret；AgentService 运行身份只具有四张表的 DML 权限。
- `payload`、`metadata` 和用户消息正文默认不写入普通日志。
- 全历史审计接口只允许已授权的内部主体调用，返回结果不得暴露给模型或普通用户。
- 监控预期父记录不一致、预期路径末端不一致、路径数据损坏、路径过深、锁等待、事务失败和会话汇总重算耗时。
- 限制单条 Entry 的 `payload` 大小、单个 Session 的 Entry 数量和最大递归深度。
- 编辑消息不会撤销已经执行的外部工具操作；新 Run 如果再次调用高风险工具，必须重新确认。
- 先完成数据库变更，再切换到依赖四表结构的应用版本，并保留可验证的兼容窗口。

## 11. 设计决策

决策及理由集中在[§2.2](#22-campusclaw-目标决策)。实施引用保留以下编号：TD-MEM-01 四表、02 当前路径、03 无分支缓存、04 最近用户消息编辑、05 不可变新 Entry、06 无标签、07 审计隔离、08 双口径汇总、09 并发校验、10 当前路径复制、11 平台发布、12 MyBatis 3.0.4 与 DTO/VO 分层。它们不另定义一套规则。

## 12. 图表生成与验证

图源维护在 [`设计图/diagram.puml`](./设计图/diagram.puml)：

```bash
cd '03-数据与存储/01-会话记忆GaussDB/设计图'
plantuml -tsvg diagram.puml
```

提交前验证：

- Markdown 中不存在 Mermaid fenced block。
- `.puml` 只包含 ASCII 字符。
- PlantUML 生成成功，四个 SVG 均为有效 XML，并与图源同步。
- Markdown 中的 SVG 路径和 PlantUML 源码行锚有效。
- DDL 只有四张表和 17 个字段注释，不包含三张删除表。
- `git diff --check` 通过。

## 13. 版本记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.15.0 | 2026-09-14 | 集中维护 Session 存储与压缩职责，独立 DDL 并收敛重复说明。 |
| v0.14.2 | 2026-08-11 | 统一中文术语和行文风格。 |
| v0.14.1 | 2026-08-11 | 优化四张图的可视化表达。 |
| v0.14 | 2026-08-11 | Session Schema 从七表收敛为四表。 |
| v0.13 | 2026-08-06 | 采用 `t_` 表名与数据库发布平台统一升级。 |
| v0.12 | 2026-08-03 | 调整数据库中文列注释表述，不改变 DDL 结构 |
| v0.11 | 2026-08-03 | 为目标字段增加中文 `COMMENT ON COLUMN` |
| v0.10 | 2026-08-03 | 标识字段、`type` 和 `cwd` 采用显式长度，增加长度预检和边界测试 |
| v0.9 | 2026-08-03 | 补充各表职责，明确原始历史、缓存和派生汇总的边界 |
| v0.8 | 2026-08-03 | 使用 `BIGINT`、`TIMESTAMPTZ(3)` 和 `JSONB` 原生类型 |
| v0.7 | 2026-08-03 | 采用与 SQLite 物理表结构对应的初始方案 |
| v0.6 | 2026-08-03 | 更新 pi 基线，并对齐写入序号、会话汇总、分支路径缓存和模型上下文处理 |
| v0.5 | 2026-07-30 | 更新 pi 基线，并采用新 harness 的当前路径末端与 `retainedTail` 语义 |
| v0.4 | 2026-07-20 | 将范围收敛为 Session 事件存储 |
| v0.3 | 2026-07-17 | 更新 pi 源码基线并核对记忆实现 |
| v0.2 | 2026-07-16 | 为 DDL 表和字段补充数据库说明 |
| v0.1 | 2026-07-15 | 建立 Java ToB GaussDB 持久化、事务和迁移设计 |
