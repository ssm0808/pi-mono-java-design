# 定时任务待对齐事项

[模块主设计](README.md) · [接口协议](configuration.md) · [Claw 数据库设计（定时任务表）](../../03-数据与存储/Claw数据库设计.md#schedule)

| 属性 | 值 |
|---|---|
| 文档版本 | 0.2.0 |
| 更新日期 | 2026-10-14 |
| 用途 | 集中记录定时任务尚未确定、需另开设计或在实现阶段验证的事项；已定的决策写入主设计，本文只保留问题、影响和首版做法 |

<a id="claw-dev-readiness"></a>

## 1. Claw 首版开发前提

Claw 端的配置接口、两张表、到期扫描与领取、原子受理、立即运行、暂停与取消暂停、删除、失败自动暂停（D12）和 Run 结束（D11）均已确定，可以开发。以下依赖不阻塞编码，但决定能否联调和上线：

| 依赖 | 开发期做法 | 联调或上线前必须完成 |
|---|---|---|
| Mate 统一账号 access-token 接口、Session 归属登记接口（[Mate 草案](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md)） | 按 `ScheduledAccessTokenPort`、`ScheduleAuthorizationPort` 编码，测试用桩实现 | Mate 实现接口，路径与 VO 定稿 |
| Claw 与 Mate 的服务鉴权（[T2](#todo-t2)） | 入站校验与出站凭据各留一个端口，先用测试配置 | 确定鉴权机制 |
| Runtime 的事务内终态扩展点（[D11](README.md#key-decisions)）、后台准备与非交互 Host 策略 | 属于 M06 改造；2026-10-14 确定终态扩展点随定时任务 PR #332 一起实现 | 随 PR #332 合入 Runtime |
| 实例宕机后自动恢复（[T9](#todo-t9)） | 首版不实现 | 上线前须有人工释放被占用任务的处置方式，见 §4 应急预案缺口 |

<a id="separate-design"></a>

## 2. 需另开设计确定

| # | 问题 | 影响 | 首版做法 | 归属 |
|---|---|---|---|---|
| <a id="todo-t2"></a>T2 | Claw 与 Mate 互相调用时如何认证对方；统一账号如何配置；access-token 有效期多长 | 不定则无法联调；有效期影响是否需要缓存 Token | Mate 新增接口仍为[内部草案](../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md)；每批工具调用取一次 Token，不缓存 | Claw 与 Mate 共同 |
| <a id="todo-t7"></a>T7 | Mate 任务配额准入与 Session 归属登记的内部契约 | 归属登记未定则受理流程无法联调 | 列表由 Mate 拉取全部后自行过滤，不传获准集合；归属登记保留在 Mate | Mate |
| <a id="todo-t8"></a>T8 | Mate 管理入口在调用 Claw 前后的处理（权限、配额、任务与用户关联） | 只影响 Mate 侧；Claw 侧逻辑已确认 | Claw 只接收可信服务调用 | Mate |
| <a id="todo-t9"></a>T9 | 实例宕机后执行卡在运行中：会话无法继续对话，任务一直被占用，后续计划全部遇忙跳过 | 需人工处置才能恢复 | 不自动恢复。候选方案（Runtime 通用能力，定时任务复用）：① 实例心跳表与执行所属实例，心跳超时约 30 秒后把执行标为中断、写入中断事件，中断终态走 D11 的同一终态提交，Run 随之结束；② 执行期写入与工具调用前检查执行未终止，防止恢复的旧实例继续执行；③ 工具调用携带幂等键（executionId + toolCallId），并在会话中显示中断时所在的工具调用 | Runtime |
| <a id="todo-t10"></a>T10 | 是否在 Claw 的 t_schedule（及 Run、Session）增加 userId，使列表直接按用户查询；需先确定任务仅创建者可见还是同范围共享，以及与 Mate 归属的同步规则 | 任务量增长后 Mate 全量拉取的读取量随之增长 | 方法 A：Mate 拉取全部后过滤（[D9](README.md#key-decisions)） | Claw 与 Mate 共同 |

<a id="implementation-verification"></a>

## 3. 实现阶段验证

| # | 事项 | 来源 |
|---|---|---|
| <a id="todo-t3"></a>T3 | PR #332 已实现但未合并，与目标结构仍有差异（含本地身份链路），按差异表修改 | [数据库 PR #332 差异](../../03-数据与存储/Claw数据库设计.md#schedule-pr-diff) |
| <a id="todo-t4"></a>T4 | 原子受理、受理后失联、取消终态与多副本故障测试 | [自动化测试](README.md#auto-tests) |
| <a id="todo-t5"></a>T5 | 完整 Maven 依赖树与 corporate NativeParent 未核验 | [模块与依赖](README.md#module-merge) |
| <a id="todo-t6"></a>T6 | 每实例 8 个活动执行上限在多副本下会放大总并发，部署阶段按实例数与下游配额核对 | [部署初始值](README.md#deployment-defaults) |

<a id="template-gaps"></a>

## 4. 文档缺口

以下内容需要项目或运维信息补充，主设计中对应位置标注【缺口】：

| 缺口 | 主设计位置 |
|---|---|
| 原始需求文档、需求编号、优先级和目标版本；各待办事项的负责人 | [需求信息](README.md#需求信息)、[需求整理](README.md#12-需求整理) |
| 容量目标与压测计划 | [容量与限流](README.md#deployment-defaults) |
| 监控指标与告警 | [监控告警](README.md#523-监控告警) |
| 应急预案：人工处置结果未知的入口、权限与审计，数据库长时间不可用时的步骤，紧急停用全部自动运行 | [应急预案](README.md#524-应急预案) |
| 灰度与回滚方案 | [灰度能力](README.md#61-灰度能力)、[回滚能力](README.md#62-回滚能力) |
| QA 流程 | [QA 流程](README.md#64-qa-流程) |
| 删除与受理竞争的详细时序图（规则已定） | [§3.7](README.md#37-删除任务配置的详细时序bu7uc5) |

<a id="closed"></a>

## 5. 已关闭

| # | 问题 | 结论 |
|---|---|---|
| <a id="todo-t1"></a>T1 | 运行失败是否自动暂停整个 Schedule | 2026-10-14 评审确定，见[主设计 D12](README.md#key-decisions) |

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.2.0 | 2026-10-14 | Runtime 终态扩展点确定随 PR #332 一起实现。 |
| 0.1.0 | 2026-10-14 | 从主设计评审 Todo 拆出，按另开设计、实现验证、文档缺口和已关闭分类，并说明 Claw 首版开发前提。 |
