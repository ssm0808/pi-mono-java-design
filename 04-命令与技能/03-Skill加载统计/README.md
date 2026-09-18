# Skill 使用统计设计

[命令与技能](../README.md) · [M05 主设计](../00-Slash-Command通用模块/README.md) · [Codex 机制详解](codex-skill-counting.md) · [统一接口页](../../01-总体架构/01-CampusClaw多Agent运行时/chat-api-review.html#querySkillLoadStatistics)

| 属性 | 值 |
|---|---|
| 文档版本 | 3.1.0 |
| 更新日期 | 2026-09-18 |
| 所属模块 | M05 负责 Skill 使用归因与统计；M06 提供真实根执行和工具来源；M04 维护 Session 生命周期 |
| 状态 | F19 查询契约已对齐 PR #295；其余采集、存储及 F20 范围仍按所列历史基线待对齐，不表示整项验收 |
| 设计依据 | F19 按 2026-09-18 需求确认采用现有批量 POST；其他章节保留 v3.0.0 的目标与核验范围 |
| 源码基线 | Codex d58d0e5841e0de08e251673db2d5af8cf3a1ad51；Java f61906b9136246ca60f333704b6fc92b5420d0ec；pi 5cd93f688aaab89dbb6dfa4aca535f21796ae185 |
| 精确模型 | Runtime catalog 的批量统计查询 operation JSON；本文维护计量、职责、存储与实施约束 |

本次仅修订 F19 查询契约。§6 的 `activationCount` / `lastLoadedAt` 是现行响应字段；其他章节的 `usageCount` / `lastUsedAt`、Runtime 范围及目标表结构仍是 v3.0.0 待对齐内容，不应据此要求现行接口返回旧字段或 `scope`。F20 不在本次修订中关闭。

## 1. 目标、口径与范围

管理端按指定 skillIds 查询累计激活次数或精确时间范围内的次数。排名、日趋势当前没有需求，待管理面明确需要后再增加。**usageCount 表示已记录到合格使用信号的根执行数：同一 (sessionId, rootEventId, skillId) 至多计 1。** 显式注入与 Read 共用这一规则，不因分页、反复读取或确认续跑增加次数。

合格信号是实际 Skill 指令已随输入成功受理，或成功 Read 最终结果中确有受管主文档正文。部分正文即可触发；它证明执行接触过该 Skill，不证明模型理解、实际遵循了指令或业务成功。因此展示为“使用次数”，不能标为“全文加载次数”“每次工具调用次数”或已经验证的“任务采用率”。

首版 **scope=runtime**，跨 Agent、Skill 版本及 plan/build 汇总；同一根执行跨模式仍只有一个去重域。Child/Cron 尚未接入，不能把它们的缺席解释为零使用。真实执行身份和关联持久化前提见 §9。

本专题负责使用归因、统计事实及投影、管理查询。Skill 主数据和名称由元数据服务负责；本专题不建设全量 Trace 平台，不新增 Shell/activate_skill 工具，不保存主文档正文副本，也不提供客户端计数上报 API。统计允许观测缺失，不能作为严格审计或计费账本。

## 2. 借鉴 Codex 与有意差异

Codex 在运行时产生使用信号，分别输出 metric 和 analytics；不同入口的成功条件与去重位置不同。Shell 识别发生在执行前；资源主提示首屏即可计数；分析队列可能丢事件。[机制详解](codex-skill-counting.md)维护逐入口证据，不能从公开客户端源码推断其后台数据库。

| 决策 | 差异分类 | 理由和代价 |
|---|---|---|
| 显式受理和主文档 Read 形成合格信号，部分正文即可 | 产品约束 | 观察有依据的 Skill 接触；不要求全文覆盖，保守排除失败和不可归因结果 |
| 所有入口统一按根执行/Skill 去重 | 架构变更 | 减少分页与重复读取对排名的影响；失去逐次读取频度，不能再从本表恢复它 |
| 统计三表独立短事务，失败不改变主执行结果 | 架构变更 | 保持工具与输入受理语义；接受漏计和主记录与统计不严格相等 |
| 首版同步尝试一次，不增加队列或 MQ | 架构变更 | 复用现有事务设施；仍会增加连接和锁等待，须实测并限制等待成本，与 Codex 的异步队列不同 |
| 复用 Skill ID、根消息和规范工具调用身份 | 产品约束 | 身份可核对，避免为统计再生成随机执行 UUID；不照搬 Codex 的路径 hash |
| Runtime 首版及部署管理权限 | 产品约束与安全加固 | 覆盖范围明确，授权先于聚合；Child/Cron 扩展须补真实归属 |

## 3. 到底怎么记

### 3.1 触发与去重示例

下表的加数假定统计写入成功；失败边界见 §5。

| 场景 | usageCount 增量 | 说明 |
|---|---:|---|
| 根 R1 显式注入 A，随后 Read A 三次 | A +1 | 四个信号共享 R1/A；保留首次事实 |
| R1 分三段 Read A | A +1 | 第一次交付部分正文即可，不累加全文覆盖 |
| R1 先读文档中段，再读首页 | A +1 | CampusClaw 不使用 Codex cursor 首屏规则 |
| R1 使用 A、B | A +1，B +1 | 按 Skill 分别记录 |
| 普通新消息创建 R2，再使用 A | A +1 | 同一 Session 的新根是新的去重域 |
| R1 问答、工具确认、计划批准或修订续跑，再 Read A | A +0 | 续跑段改变，根消息不变 |
| R1 昨天已计 A，今天续跑再读 A | A +0 | 归属首次入账信号的日期，不按每天重置去重 |
| 仅继承上下文、fork 复制历史、恢复、SSE 重连、查询历史 | +0 | 没有新的显式受理或 Read 信号 |
| Read 失败/拒绝/取消、空正文、只返回提示、辅助文件或目录 | +0 | 没有合格主文档信号 |
| After hook 改写正文，现有证据无法验证结果 | +0 | 保守跳过并诊断，不把旧 details 当作新证据 |
| 使用已计数，随后模型/任务失败或取消 | +0，不撤销原计数 | 使用信号与任务成败分离 |

### 3.2 根身份与时间

去重键固定为 **(session_id, root_event_id, skill_id)**。Runtime 的 ExecutionTargetDTO 已有 sessionId、executionId、rootEventId、segmentId；统计使用其中真实根标识，不能在工厂或每次入库时生成一个新的 executionId。rootEventId 是原 user.message 的公共事件 ID；普通新消息换根，问答/确认/审核续跑保持原根。

skillId 来自本次执行的不可变受管快照，精确匹配，不归一大小写；版本更新、Agent 或执行段不进入去重键。路径匹配只用于归因，任意同名 SKILL.md 不能生成受管 Skill 身份。

source_event_id 只记录首次事实的来源：EXPLICIT 为根消息，READ 为 Runtime 已保存的规范工具调用事件 ID。Provider toolCallId 只在当前执行映射内查找规范 ID，不能直接作为数据库业务身份。规范映射未就绪时跳过统计并诊断，不临时补造来源。Host 通过线程安全的按调用查询或不可变快照提供映射，不向并行工具线程暴露可变 Map。

occurred_at 为被记录信号的服务端 UTC 毫秒时间：显式取受理时间；Read 取最终成功结果被观测的时间。候选形成后固定，SQL 等待/重试不改时间。Read 采集发生在权威结果追加之前，所以表不声称已保存成功结果，不要求 result_event_id。

“首次”指该键首条成功入账事实。正常在线流程由 Tracker 固定首个合格候选；数据库保留先提交者。并发、丢失或进程重启时不承诺恢复绝对最早的信号。已有事实的来源、类型和时间不覆盖；相同根/Skill 的另一次 Read 或显式信号是正常重复，不是冲突。

### 3.3 逻辑分别放在哪里

| 位置 | 职责与接入时点 | 不承担的职责 |
|---|---|---|
| ReadTool / ReadToolDetails | 在实际已读字节上生成通用证据：规范路径、文件 SHA-256、实际返回正文字符数、返回内容 SHA-256 指纹 | 不引用 Skill ID、统计 Service、Mapper；不额外重读磁盘 |
| skill/usage/SkillUsageResolver，Spring 单例 | 在所有改写 hook 之后，用最终 isError/content/details 与执行快照验证受管主文档，生成不可变 SkillUsageCandidateDTO | 不持有跨执行集合，不维护 BitSet、行覆盖或全文轮次 |
| skill/usage/SkillUsageTracker，每个 Runtime 根执行一份 | 绑定真实根和不可变快照，接收 explicit/read 信号；线程安全地选择每个 Skill 的首个候选，调用统计服务并隔离异常 | 内存集合不是持久化去重依据；不生成根身份、不决定工具成败 |
| RuntimeSessionEngineRegistry / RuntimeActiveExecution | 为当前执行组装 Tracker；根受理后绑定 ExecutionTargetDTO；工具调用落库后提供只读规范 ID 映射 | 不把用户请求、Provider ID 或旧执行实例当新根 |
| AgentSessionFactory / AgentSessionHookChain | 保留现有 hook 扩展，组装最终只读观察入口；工厂仅组装依赖 | 不集中实现路径匹配、统计规则和数据库写入，不给 agent-core 新增通用回调 |
| SkillCommandExecutionService / RuntimeMessageEventService | 将已解析的 Skill 候选随内部受理上下文传递；acceptMessage 已提交且 target 绑定后、模型启动前交给同一个 Tracker | 不在返回 SSE 后凭随机 ID 加数；不在受理事务内写统计 |
| SkillUsageService / SkillUsageMapper | 独立统计事务、生命周期准入、唯一事实和原子汇总；查询复用 Mapper | 不控制模型、工具与 Runtime 主事务 |

读取证据仅用于内部观察，不新增公共事件或持久化工具结果字段；沿用 RuntimeEntryCodec / RuntimeCommittedEventFactory 的字段白名单，不将路径、摘要或指纹拼入正文。

现有 afterHooks 可组合：业务 hook 依次完成结果改写，末尾观察器只观察最终值并原样传回。Hook 链提前失败、最终 isError=true 或观察时取消均不记；统计/归因异常在观察适配器内隔离，不能被 ToolExecutionPipeline 当作工具失败。主流程自身的取消仍遵循原语义，不由统计清除中断标志。观察之后发生的任务失败不撤销事实。

Factory 只把执行入口提供的 Tracker/快照绑定到链尾；ManagedAgentSessionRequest 当前尚无统计装配参数，该扩展及 Host 的规范调用映射属于 target-only。使用请求范围的不可变 DTO 或显式依赖传递，不能在单例上保存“当前执行”、在工具线程中从 ThreadLocal 猜根，或让 Child/Cron 意外复用 Runtime Tracker。

Tracker 在 root 完成并释放执行对象时关闭，等待确认期间保持同一去重域；恢复时可重建内存优化，数据库键仍负责最终去重。每个 Skill 在一个 Tracker 内至多一次数据库尝试；失败状态也不循环重试。不得在持有 Tracker 的全局互斥锁时进行数据库 I/O，避免不同 Skill 的信号互相阻塞。

## 4. 三张数据库表

[目标 DDL](schema.sql)维护类型、主键、索引和中文注释。三表专门服务统计；没有跨服务 Skill 外键，不增加无业务依据的统计 execution_id、随机 usage_id、全文内容、路径或耗时维度。

### 4.1 t_skill_usage：根执行内首次入账的使用事实

| 字段 | 类型 | 含义 |
|---|---|---|
| session_id | VARCHAR(128) | Runtime Session，主键组成 |
| root_event_id | VARCHAR(128) | 原根消息，主键组成 |
| skill_id | VARCHAR(64) | 受管 Skill，主键组成 |
| source_event_id | VARCHAR(128) | 首次入账信号的根消息或规范工具调用事件，仅追溯 |
| agent_id | VARCHAR(64) | 实际执行 Agent，来自可信执行快照 |
| signal_type | VARCHAR(16) | EXPLICIT 或 READ，首次信号来源 |
| occurred_at | TIMESTAMPTZ(3) | 本事实固定的服务端信号时间 |

命名主键 pk_skill_usage；索引 (skill_id, occurred_at) 支持有限范围核对。每行权重为 1，没有逐次 Read 明细，不能从此表恢复工具调用总次数。根关联直接体现在主键中，不再另建重复根索引。

### 4.2 t_skill_usage_stats：累计汇总

| 字段 | 类型 | 含义 |
|---|---|---|
| skill_id | VARCHAR(64)，主键 | 已有入账事实的统计资源 |
| usage_count | BIGINT，大于 0 | 功能启用以来不同根/Skill 事实的累计数 |
| last_used_at | TIMESTAMPTZ(3) | 已计事实 occurred_at 的最大值 |

首次事实自动创建统计行，不预建零行，不远程查询 Skill 存在性。索引 (usage_count DESC, skill_id ASC) 与 (last_used_at DESC, skill_id ASC) 服务排名。lastUsedAt 是最近一次**计入统计的使用**时间；同根重复 Read 不刷新它。

### 4.3 t_skill_usage_daily_stats：按日汇总

| 字段 | 类型 | 含义 |
|---|---|---|
| stat_date | DATE，主键组成 | occurred_at 转为 Asia/Shanghai 的自然日 |
| skill_id | VARCHAR(64)，主键组成 | 同一 Skill 身份 |
| usage_count | BIGINT，大于 0 | 归属当日的首次使用事实数 |
| last_used_at | TIMESTAMPTZ(3) | 当日已计事实的最近 occurred_at |

主键 (stat_date, skill_id)，补充 (skill_id, stat_date) 支持单项趋势。无事实的日期不落零行，由查询补齐。跨天长任务只归首次入账信号所在日，因此近 7 天不是“这 7 天内仍活跃的 Skill 根执行数”。

事实解决幂等与有限追溯，累计解决长期排名，日表解决 7/30 天聚合。仅事实表会让累计扫描随历史增长；仅两张计数表不能识别重复。根去重减少反复 Read 的写入，但热门 Skill 累计行仍可能竞争，性能需实测。

## 5. 事务、失败隔离与生命周期

### 5.1 独立短事务

[record-usage.sql](record-usage.sql)给出 Mapper 语句与分支前提。复用既有 Spring、MyBatis 和数据源；**Runtime 主事务先结束，统计事务仅包含准入读取、事实及两张汇总。**

1. 显式信号在 acceptMessage 提交、target 绑定之后进入 Tracker；Read 信号在最终观察 hook 进入，均不位于 Runtime 持久化事务内部。不得在主事务尚持有数据库锁时另开统计事务。
2. Tracker 调用另一个 Spring Bean 的 SkillUsageService.record；该方法采用 REQUIRES_NEW 保证统计独立提交。禁止 self-invocation，禁止把它改成 REQUIRED 后加入来源事务；入口需验证没有活动的 Runtime 数据库事务，误装配时跳过统计并诊断。
3. 统计事务先沿用 Session 生命周期数据库锁（锁定 t_sessions.id），检查 Session 未删除、真实根仍存在且允许当前执行记录。仅作快照读取根记录，不新增与 Runtime 相反的执行行锁顺序。删除路径使用同一 Session 锁；不存在、tombstone 或已关闭准入则不插入。此锁防止清理后的迟到写入，去重仍由事实主键保证。
4. 查询同一根/Skill：存在则返回 ALREADY_RECORDED，保持首次来源和时间，**不更新任何汇总**；不存在才执行普通 INSERT t_skill_usage。主键冲突必须使本统计事务回滚，不能吞异常后继续加数。并发兜底只将明确 pk_skill_usage 冲突识别为重复，其他唯一键/完整性错误按失败处理。
5. 仅 INSERT 成功后，按“事实 → 累计 → 日表”固定顺序执行数据库原子加一；所有三表同事务提交。不能 SELECT 数字到 Java 再覆盖写回，不依赖 UPSERT 的受影响行数猜测是否首次插入。每次 record 只处理一个 Skill。
6. 事务代理完成提交/回滚后才返回 Tracker。**catch 在事务调用外层**，覆盖执行及提交阶段错误；记录受控诊断并继续主执行。不得在事务内 catch 后返回成功而留下 rollback-only 状态。

Session 生命周期锁不会让统计与 Runtime 主事务成为同一个事务，但会引入等待。统计服务不修改 Session 状态、版本或最后更新时间；它也不重新核验并控制已成功受理的主请求。

### 5.2 可靠性边界

| 情况 | 统计与主执行行为 |
|---|---|
| 三表任意一步失败 | 仅统计三表回滚；记录失败诊断；已受理输入与成功 Read 保持原结果 |
| 数据库不可用、连接/锁/语句等待超限 | 终止本次统计尝试，释放资源；不循环重试、不改为单表加一 |
| 统计提交成功但应用未收到确认 | 记录提交结果不确定，不宣称一定漏计；以后同键被数据库拒绝重复，不重做工具或输入 |
| 进程在信号出现后、统计提交前崩溃 | 可以漏计；不从历史自动重放，也不承诺无损补偿 |
| 同 Tracker 中首次尝试失败后又 Read 同 Skill | 不再次自动尝试；避免错误风暴，承认这个根可能漏计 |
| 恢复后出现新的合格信号且内存集合已重建 | 已有事实则不重计；原事实缺失时可能记录新的信号，以本次候选时间归日，不声称恢复了最早使用时间 |
| 已计数后工具结果追加失败、模型失败或取消 | 保留已记录信号；统计不承诺与权威成功结果条数恒等 |
| 统计查询失败 | 返回真实查询错误，不把失败伪装成零；写侧的历史漏计无法靠成功查询消除 |

首版为一次有等待预算的同步尝试，仍可能延迟模型启动或 Read 返回。必须配置并实测连接获取、锁、语句、事务和调用总等待预算；仅 Mapper timeout 或事务 timeout 不能证明端到端有界。禁止用超时 Future 包裹后丢弃仍运行的 JDBC 任务。预算数值由实际数据源/驱动验收确定，未通过前不能宣称“统计无阻塞”。

日志只含受控的 Session/根/Skill 标识、阶段和错误分类，不含正文、路径、凭据或完整数据库异常参数；应限流避免故障风暴。后续若同步成本不可接受，再单独设计有界异步投递及关闭、丢弃、重试策略，不在本版提前加入 MQ、OTel 或持久化队列。

### 5.3 清理、删除与恢复

沿用 M06 B15 的部署保留策略，不另定 90 天。没有配置时不新增自动清理。日表至少覆盖最近 30 个自然日；请求窗口超出实际保留覆盖返回 503 SKILL_USAGE_STATISTICS_UNAVAILABLE，不能将过期数据补零。功能启用前不回填；零只表示没有已记录事实，也可能受观测缺失影响。

- 活跃或等待确认的根，其事实去重键必须保留；不能因 occurred_at 较老就删除，否则长任务续跑会重计。
- 根终态且执行对象/在途观察已结束后才可关闭统计准入并按策略清理；清理后拒绝旧根回放。若未来允许终态根重启，必须先设计持久化去重保留，不能复用已清理的键。
- Session 删除沿用生命周期锁与 tombstone，阻止新信号后删除该 Session 事实，保留无 Session 关联的累计/日表。清理属于删除事务，不要求统计采集与 Runtime 受理同事务。统计先写则删除清掉事实，删除先提交则迟到采集被拒绝。
- 删除事实或日表不扣减累计；部分事实无法重建生命周期累计。三张统计表必须一致备份/恢复，不能单独回滚一张。与 Runtime 恢复点不一致时须停止采集核对根身份与删除记录，不能将来源恢复变成自动补数。
- Skill 更新、解除绑定或远端删除不重置统计；Skill ID 不得复用于另一资源。治理清除整项统计应统一处理三表和去重保留，不提供公共 DELETE。

## 6. 查询接口

当前提供一个只读批量查询：`POST /campusclaw-service/v1/internal/skills/load-statistics/query`。
操作标识为 `querySkillLoadStatistics`，成功使用 ResultBean；精确模型和示例见[统一接口页](../../01-总体架构/01-CampusClaw多Agent运行时/chat-api-review.html#querySkillLoadStatistics)。
实现证据为 PR #295 `c8cbda4946403d5e51b95ceaf0d7485166c54395` 的 Controller、Request/Response VO、Service 和 Mapper，详见[查询证据](source-evidence.md#f19-query)。

### 6.1 请求与时间边界

| 字段 | 规则 |
|---|---|
| skillIds | 必填字符串数组，原始数组 1～100 项；每项符合 `skill-[0-9A-Fa-f]{32}`，精确去重且保留首次出现顺序 |
| from | 可省略；带明确时区的 RFC 3339 时间戳，最多毫秒精度；左闭边界 |
| to | 可省略；同上；右开边界，缺省取本次数据库查询时间 queriedAt |

请求体只允许这三个字段；显式 null、非字符串 ID/时间、未知字段和多个根 JSON 对象拒绝。提供 from 时必须早于生效的 to。

- from、to 均省略：读取累计表，返回功能启用以来所有已入账激活；历史事实清理不扣减累计。
- 任一时间字段出现：从事实表按 `[from, to)` 精确聚合；省略 from 表示无下界，省略 to 使用 queriedAt。
- 时间按绝对时刻比较，不按日表或近 7/30 个自然日近似替代。请求可带偏移，响应统一 UTC 毫秒。
- 返回有效 to；from 未提供时为 null。累计分支的 to 是查询快照时间标记，不代表重新按事实时间过滤累计表。

### 6.2 响应与错误

result 固定为 `queriedAt`、`from`、`to`、`items`；每项固定为 `skillId`、`activationCount`、`lastLoadedAt`。
同一查询使用数据库语句快照，items 按请求 ID 首次出现的顺序返回，不排序、不分页。
activationCount 为非负 64 位整数；lastLoadedAt 是所查询集合内最近的已计激活时间，不是最近一次重复读取时间。
没有统计记录的合法 ID 也返回一项，activationCount=0、lastLoadedAt=null；不查询远端主数据，也不据此判断 Skill 是否存在，不返回统计资源 404。
响应不含 metric、definitionVersion、scope、period、排名、分页或趋势字段。统计允许漏计，不证明模型遵循指令或任务成功。

| HTTP | 错误码 | 条件 |
|---|---|---|
| 400 | INVALID_SKILL_LOAD_STATISTICS_QUERY | 请求字段、类型、ID、时间格式或范围不合法 |
| 500 | SKILL_LOAD_STATISTICS_QUERY_FAILED | 数据库查询等内部失败；不得伪装为零 |
| 503 | SKILL_LOAD_STATISTICS_HISTORY_UNAVAILABLE | 请求时间范围与已清理事实的范围相交，无法提供精确统计 |

错误沿用现有 ResultBean 错误包装及请求语言，不带 result。成功响应 Cache-Control 为 no-store。

### 6.3 权限与分层

只供有部署级统计权限的管理调用方经 CampusMate/部署入口访问内部 Runtime；传入 skillIds 不构成授权。
Claw 沿用上游授权；X-HW-ID 是凭据 ID，不能推导 tenantId。没有可信租户维度前不能宣称提供租户隔离统计。
Skill 名称和目录状态由元数据所有者补充，接口只返回请求 ID 的统计。
Controller 使用 SkillLoadStatisticsRequestVO / SkillLoadStatisticsResponseVO；Service 精确去重、校验有效时间边界并转换响应；Mapper 负责快照查询。

### 6.4 暂缓排名与趋势

F19 可以暂不实施，等管理面明确需要排名、趋势时再增加。当前不发布 `/skills/usage-statistics` 和 `/skills/{skillId}/usage-statistics/daily` 两项 GET，也不保留其分页或 7/30 日参数作为现行契约。
若未来沿用现有统计维度及 Asia/Shanghai 自然日口径，可复用累计表和日汇总表，增加查询接口、查询逻辑和测试，无需为此预先变更表结构。
按入口等新维度拆分、保留窗口、排名分页一致性及缺日处理，待需求明确后另行设计，不预先承诺接口形状。

## 7. 推荐全局目标类图

![Skill 使用统计全局目标类图](skill_load_statistics_classes.svg)

[PlantUML 源码](diagram.puml#L1) · [原尺寸 SVG](skill_load_statistics_classes.svg)

专题路径和类图文件名保留稳定链接；图中是当前使用统计目标。执行持有 Tracker，通用 Read 提供证据，Resolver 负责 Skill 归因，统计 Service 负责独立事务。Factory 只装配，Controller 不访问 Mapper，任何统计依赖都不进入 agent-core。

![Skill 使用记录与失败隔离](skill_usage_record.svg)

[PlantUML 源码](diagram.puml#L90) · [原尺寸 SVG](skill_usage_record.svg)

时序将主流程和统计事务分开；只在新事实插入后加数，异常必须在统计事务结束后隔离。它是 CampusClaw target-only 方案，不是 Codex 实际队列实现。

## 8. 实施切片与验收

| 切片 | 实施内容 | 关键验收 |
|---|---|---|
| S1 · 数据与失败隔离 | 三表、Mapper、独立 Service 事务、外层异常隔离、生命周期准入 | 重复键不加数；并发首写和不同根共享 Skill 不丢更新；任一统计写/提交失败只回滚三表；主受理/工具保持成功；超时与连接释放 |
| S2 · 信号与根绑定 | Read 通用证据、Resolver、执行级 Tracker、最终 hook 和显式受理后接入 | 显式加三次 Read 共 1；部分/中段正文计数；A/B 分别计；新根再计；确认续跑不变；失败/空/改写/取消无信号；规范 ID 缺失安全跳过 |
| S3 · 查询契约 | 批量 POST、skillIds、可选 from/to、activationCount 与管理授权 | 原始 1～100 项、精确去重及顺序；累计/精确范围；零值与 null；400/500/503；事实清理后累计保留 |
| S4 · 生命周期与部署 | Tracker 关闭/恢复、清理准入、三表一致备份、发布脚本 | 活跃根事实不清理；删除与迟到写竞争；历史读取/fork 不重计；失败漏计边界；热点/连接/锁/端到端等待与 30 日查询实测 |

首版无历史回填或旧报表兼容要求；目标 SQL 是安装设计片段，不自动执行数据库变更。F19 查询以 §6 的现有 POST 为准；采集和数据库目标的历史差距不因本次接口对齐而自动关闭。

## 9. Child、Cron 与后续扩展

| 入口 | 已观察实现 | 接入前提 |
|---|---|---|
| Runtime | ExecutionTargetDTO、原根消息、规范工具调用映射与持久化 | 实施 S1～S4，传递真实根及可信执行快照 |
| Child | SubagentExecutionContext 保存深度/祖先/模型/凭据，使用内存执行和进度回调 | 先明确真实子执行身份、父调用关联、持久化与保留；再决定父子共享哪一个去重域，不能把 fork 来源当委派关系 |
| Cron | CronJobExecutor 有运行记录，runner 仅接 agentId/prompt，未传 job/run | 调度模块提供可唯一定位的 job/run 及生命周期，再定义统计根；不能临时生成统计 UUID 冒充运行 |

扩展时更新 scope 和去重定义，不能在 scope=runtime 中悄悄混入新入口。Trace 可关联真实 root/source/span 供诊断，本统计不依赖 Trace 是否采样或导出，也不新增公共 traceparent Header。

## 10. 依赖与验证边界

不新增 Maven 直接依赖；复用 JDK 摘要/时间、已有 Spring 事务、MyBatis Starter 3.0.4、Jackson、Jakarta Validation 和日志，无新增传递依赖。部署镜像和现有依赖版本仍需在实现时验证。

openGauss 5.0 INSERT 文档作为 UPSERT 语法依据；公司 GaussDB 版本、主键异常识别、并发、索引计划和等待预算尚未执行验证。设计制品校验不证明运行可靠性，具体已验证项目与待实现项见[验证记录](validation.md)。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 3.1.0 | 2026-09-18 | F19 对齐现有批量 POST 与 activationCount 响应，排名和趋势延后按需设计。 |
| 3.0.0 | 2026-09-16 | 按根执行统一去重 Skill 使用信号，统计独立短事务且失败不阻断主执行。 |
| 2.0.0 | 2026-09-15 | 基于 Codex 观测机制定义成功调用事实、来源幂等、三表同事务和 Runtime 统计查询。 |
| 1.1.0 | 2026-09-15 | 按设计仓职责补充 Skill 调用观测基线，明确全文加载方案的候选边界。 |
| 1.0.0 | 2026-09-15 | 定义累计与日汇总、直接排名查询、单 Skill 趋势及事务和保留边界。 |
