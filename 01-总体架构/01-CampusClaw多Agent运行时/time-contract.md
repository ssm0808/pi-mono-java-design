# Claw 秒级时间一致性

| 属性 | 值 |
|---|---|
| 版本 | 1.2.0 · 2026-10-04 |
| 状态 | 秒级目标已确认；实现调整待实现 |
| 范围 | Claw Session、完整公共事件、定时任务的绝对时间及对应存储；不改变 Provider 原始时间、耗时、超时或内部计时单位 |
| 精确 HTTP 契约 | Session/Command 的接口契约、Events 共享契约及定时任务配置专题分别维护；本文维护共同的一致性理由和实施边界 |

## 1. 业务结果

园区告警任务的创建、计划执行时刻和会话历史统一显示到秒。创建后立刻查询、收到完整 SSE 后再查历史，返回同一个已保存时刻，不因直接返回内存对象还是回读数据库而改变值或格式。

绝对时刻响应统一使用 UTC、以 `Z` 结尾、不含小数秒，例如 `2026-10-01T00:00:00Z`。Session 的 createdAt/updatedAt、完整事件 createdAt，以及定时任务已定义的绝对时间均适用。相同一秒可以有多个事件、多次更新；事件按提交序号排序，以 eventId 去重。配置更新在最新行锁内合并提交字段，内部版本用于执行一致性，不提供公共 ETag 或版本条件，也不使用时间戳代替，详见 [Session 更新](chat-http-v1-design.md#session-update)。

## 2. 正常处理与失败边界

服务端生成的记录时间在首次形成持久化 DTO 时转 UTC 并截断到秒，再参与事务写入。所有写入口使用相同规范化规则；不是等到 JSON 输出时才隐藏小数。持久化成功后，可直接返回同一已规范化的提交快照；回读则返回数据库保存值。两条路径必须等值，不能为格式一致额外回读一个可能已被其他请求修改的最新状态。事务失败不返回成功；完整事件时间只生成并保存一次，GET 与 POST SSE 使用同一投影，不在读取时重新取时。

定时任务配置仅接受 Cron 表达式与 IANA timezone，不接收绝对单次时间或间隔起点。Cron 的时区用于日历计算，响应 UTC 不改变该时区；未来计划按秒输出。具体输入范围由[定时任务配置](../08-CampusClaw定时任务/README.md#432-仅-cron-的范围与代价)维护，不从公共时间精度推导额外的输入字段。

格式精度不承诺调度准时，也不限制内部计时器精度。模型原始 timestamp、耗时与超时等数值字段不做毫秒到秒的机械替换。使用 JDK 时间类型及现有 Jackson，不新增 Maven 依赖。

## 3. 存储与交付

目标时间列采用 `TIMESTAMPTZ(0)`，应用先规范化，不能依赖数据库隐式舍入来决定业务时间。Session 基础 DDL 见[存储专题](../../03-数据与存储/01-会话记忆GaussDB/README.md#second-precision-storage)。覆盖 `t_sessions.created_at/updated_at`、`t_session_entries.timestamp`、`t_session_records.timestamp`、`t_session_events.created_at`，以及定时任务配置与运行记录中承载上述时间的列。

沿用存储专题的新建环境交付范围：同步完整安装 DDL、公司安装镜像、DTO 写入规范化和响应投影；本设计不新增存量迁移脚本，也未操作实际数据库。若将来要用于已有毫秒数据的环境，需要另行确定数据转换和发布方案，不能只改序列化器后声称历史存储已统一。租约、执行期限等控制字段不因本次公共时间调整而自动降低精度，其安全判断由所属生命周期设计维护。

Mate 是独立公共协议：目前其事件时间及 createdAtGte 过滤约定三位毫秒。本次确定的是 Claw 范围，不能把 Claw 新格式原样透传到旧 Mate 契约。接入时应在 Mate 适配边界按其契约表示同一时刻（补 `.000` 不增加精度），或独立完成公共协议调整后再开放；不修改用户过滤条件的比较语义。

## 4. 已观察实现与基线

2026-10-02 读取本地固定快照 `pi-mono-java@553dcd5e2ff682f9684810a043b442b37a02e54a`；不是本日最新上游或部署状态。源码前缀 R 为 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/`。

| 相对路径、符号 | 已观察行为 | 待实现调整 |
|---|---|---|
| R/session/RuntimeSessionService.java · create/newSession/now | UTC 取时但不截断，保存后从同一 DTO 组装创建响应 | 首次写入前统一秒级值，覆盖其他 Session 时间写入口 |
| R/persistence/MyBatisRuntimeSessionRepository.java · appendEventsLocked/normalizeTimestamp | 完整事件转 UTC 并截断到 MILLIS | 规范化为 SECONDS，保持同次提交快照 |
| R/event/CommittedEventProjection.java · EVENT_TIME_FORMATTER/project | appendInstant(3) 固定三位毫秒 | 秒级 UTC 输出，GET 与 SSE 共用 |
| modules/coding-agent-cli/src/main/resources/db/gaussdb/install/session_schema.sql · 上述四表 | 相关时间列均为 TIMESTAMPTZ(3) | 新建环境改为 TIMESTAMPTZ(0)，应用先规范化；同步公司安装镜像 |

2026-10-02 重新核对 Claude Managed Agents 公开 Beta [Create Session](https://platform.claude.com/docs/en/api/http/beta/sessions/create) 与 [Create Deployment](https://platform.claude.com/docs/en/api/http/beta/deployments/create)：created_at/updated_at 示例使用 `2026-03-15T10:00:00Z`。这些公开示例支持借鉴整秒表示，未承诺只支持秒级，也不能证明服务端数据库精度。CampusClaw 秒级限制属于产品约束：满足当前业务展示、计划和对账需求，代价是不能用这些字段分析同一秒内的时间差；顺序与并发由序号、标识、行锁事务和内部版本保证。

## 5. 验收要求

- 使用带亚秒的固定 Clock，验证写入前截断、直接响应与 GET 回读相同；同秒多次更新仍推进适用的资源版本。
- 同秒多条完整事件保持不同 eventId 和提交顺序，SSE 与历史 createdAt 逐字一致，delta 仍不带 createdAt。
- 所有相关响应只输出 `YYYY-MM-DDTHH:mm:ssZ`；Cron 在保存时区下计算的时刻正确换算为 UTC，覆盖跨日与 DST；创建配置不接受 at/startAt 等额外时间字段。
- 新建 GaussDB 环境验证列精度、JDBC 往返和事务回滚；实际产品与数据库验收仍待实施，设计静态校验不能替代。

## 6. 设计校验记录

2026-10-02：31 项接口设计回归通过；POST SSE 与历史专项通过，拒绝 114 项 POST、57 项历史及既有批次/任务/计划/问题负向样例；秒级正向样例与小数秒反例已同步。普通契约、HTML/Help 同步、共享字段及控制接口退役专项通过，23 项接口用途检查通过。API 技能机械检查覆盖 Runtime、调度、存储与架构对比；全仓图检查覆盖 36 个专题、131 个块、52 张时序图，0 错误。两项时序复杂度提示属于未修改的 compaction 与其他工作区计划流图，不随本次改写。

存储图仅调整两列精度，PlantUML/SVG 同步并检查原尺寸和 840px 文档宽度；隔离当前任务重新生成图索引，与主线相同，无须覆盖工作区其他任务的索引。完整接口校验仍被学习目录已有的 `../../02-服务与接口/03-模型管理Provider契约/diagram.puml` 失效引用阻断；DOM 交互检查缺少 jsdom，未通过。未运行产品、GaussDB 或实际调度测试。
