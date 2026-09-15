# Codex 基线的 Skill 计数机制

[统计主设计](README.md) · [Agent 基线概览](trace-baselines.md) · [CampusClaw 源码差距](source-evidence.md)

| 属性 | 值 |
|---|---|
| 版本 | 1.1.0；2026-09-16 |
| 固定仓库与提交 | openai/codex，d58d0e5841e0de08e251673db2d5af8cf3a1ad51 |
| 证据性质 | 固定源码静态分析、测试用例阅读、官方文档核对；未运行基线或访问分析后台 |
| 范围 | Skill 选择、主提示加载、Shell 识别、资源读取、身份、去重、metric、analytics、Turn 耗时归因 |

## 1. 先区分四种数据

Codex 已实现专用 Skill 遥测。它在运行时产生使用信号，分别递增指标和提交分析事实，不依赖事后扫描日志文本识别 Skill。

| 数据 | 实际含义 | 不能据此推出 |
|---|---|---|
| codex.skill.injected | 带 status、skill、invoke_type 等标签的计数器 | SKILL.md 全文覆盖次数、所有入口统一去重的成功次数 |
| SkillInvoked 内部事实 | tracking 加 SkillInvocation 列表，交给分析队列 | 已成功送达服务器或已存入数据库 |
| skill_invocation 上报事件 | 带 skill_id、Thread/Turn 关联的分析事件 | 标准 Skill span、逐次无损账本或业务成功证明 |
| codex.skill.turn.duration_seconds | 使用过相应 plugin 的整个 Turn 耗时 | 单个 Skill 的独立运行耗时或各 Skill 耗时之和 |

[官方高级配置](https://learn.chatgpt.com/docs/config-file/config-advanced#metrics-catalog)于 2026-09-15 核对：指标目录列出 skill.injected，页面说明目录省略 codex 前缀；指标与 OTel 日志/Trace 导出有独立配置边界。文档仅佐证公开指标，精确触发和去重以下列固定代码为准。

## 2. 三类触发入口

### 2.1 显式选择与指令注入

Host 主线为 build_skills_and_plugins → collect_explicit_skill_mentions → load_skill_prompts → emit_explicit_skill_invocations。

1. 选择器先解析结构化 UserInput::Skill，再解析文本中的 Skill 引用。路径要匹配可用目录，纯名称只能在无歧义时解析；禁用项被排除。一次选择过程用 seen_paths/seen_names 去重。未知名称未进入 mentioned_skills，因此不能把指标 error 理解为所有无效 Skill 请求的数量。
2. 加载函数返回 fragments、实际注入集合和 warnings。显式埋点用 mentioned_skills 对比 injected_skills：Host 路径每个已选 Skill 都递增计数，注入成功 status=ok，未成功 status=error。
3. 分析事件只为 injected_skills 构造，invoke_type=explicit。触发发生在模型执行之前，证明指令加载处理的结果，不证明模型已理解、已应用或任务成功。
4. 扩展资源的显式路径由 TurnInputContributor for SkillsExtension 的 contribute 单独处理：read_main_prompt 成功、允许截断并生成 fragment 后，非 Host 资源经 SkillAnalytics 上报；Host 成功路径汇入 InjectedHostSkillPrompts。不能把 Host 的 error 计数规则推广到所有资源分支。
5. contributor 回调与 analytics 是不同消费者。Host 显式分支对 is_superseded_path 的跳过位于 contributor 循环，不能据此认定后面的 analytics 列表同样被过滤。

源码：[turn.rs · build_skills_and_plugins](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/core/src/session/turn.rs#L774)、[selection.rs](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/skills/src/selection.rs#L42)、[core/skills.rs](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/core/src/skills.rs#L38)、[extension.rs](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/ext/skills/src/extension.rs#L440)。

### 2.2 Shell 隐式识别

exec_command 在真正执行命令前调用 maybe_emit_implicit_skill_invocation。识别器结合命令参数、工作目录、环境 ID 与本次可用 Skill 快照：

- 文档访问：解析出 Read 命令，规范化路径，精确匹配已知主文档。
- 脚本执行：识别 python/python3、bash/zsh/sh、node/deno、ruby/perl、pwsh 等入口及支持的文件扩展名，检查脚本是否位于已知 Skill 的 scripts 目录。
- Host 使用本地路径/快照；Executor 资源另检查目录、环境和启用状态。并非看到任意 SKILL.md 文件名就能归因。
- 静态解析返回一个匹配结果；动态构造路径、未支持的命令形式及一次复杂命令里的多 Skill 访问不保证完整覆盖。

TurnContext.extension_data 内保存 ImplicitSkillInvocations(Mutex<HashSet<String>>)。Host 去重键由 scope、path、skill_name 组成；Resource 用 resource:id。已见过即返回；新匹配才执行 contributor、计数和分析上报。

这条链的 status=ok 表示识别并接受了使用信号。命令随后失败、被后续校验拒绝或没有交付文档内容，都不能从这个 status 排除。计数入口未做全文行覆盖、内容区间合并或命令成功结果检查。

源码：[执行前触发](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/core/src/tools/handlers/unified_exec/exec_command.rs#L231)、[识别器](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/skills/src/invocation.rs#L26)、[资源适配](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/ext/skills/src/invocation.rs#L17)、[Turn 去重](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/core/src/skills.rs#L121)。

### 2.3 skills.read 首次分页读取

ReadTool.handle 校验资源与权限，取得快照并构造分页结果；只有 requested_resource 等于 main_prompt，且请求 cursor 为空时，才调用 SkillAnalytics.track_skill_invocation，类型为 implicit。

| 请求情况 | 此入口的计数行为 |
|---|---|
| 成功读取主提示第一页，仍有 next_cursor | 计数；不等待余页 |
| 使用 cursor 续读主提示 | 不在该分支计数 |
| 读取 supporting resource | 不在该分支计数 |
| 主提示读取失败 | 不到达成功埋点 |
| 同一 Turn 再次不带 cursor 读取主提示 | 调用点再次递增 metric；analytics 后续可去重 |

SkillAnalytics 先调 metrics.counter，再提交分析事实。因而 Reducer 的去重不可能撤销已经递增的计数器。

源码：[read.rs](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/ext/skills/src/tools/read.rs#L277)、[SkillAnalytics](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/ext/skills/src/tools/mod.rs#L127)。

## 3. 两条输出链

### 3.1 Metric：进程内递增并交给指标管线

SessionTelemetry.counter 合并元数据标签，调用 MetricsClient。底层按指标名称/单位/描述缓存 Counter<u64>，首次使用由 meter.u64_counter(name).build() 创建，然后 counter.add(inc, attributes)。具体管线可能未启用或按配置过滤；没有 metrics client 时不产生有效输出，失败只警告。

Skill 标签常见为 status、skill、invoke_type、plugin_id、model_slug、reasoning_effort；标签值经过 sanitize。它们是指标维度，不承担调用唯一身份。两个同名但不同路径的 Skill，不能仅凭 skill 名称标签保证区分；analytics 的 skill_id 又是另一套身份。

源码：[SessionTelemetry.counter](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/otel/src/events/session_telemetry.rs#L178)、[MetricsClientInner.counter](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/otel/src/metrics/client.rs#L115)。

### 3.2 Analytics：事实转换与关联上报

track_skill_invocations 将非空列表封装成 CustomAnalyticsFact::SkillInvoked。后台 Reducer.ingest_skill_invoked 转换每个调用，输出 SkillInvocationEventRequest。固定版本 wire 字段如下；Optional 字段不等于必然有业务值。

| 位置 | 字段 |
|---|---|
| 顶层 | event_type="skill_invocation"、skill_id、skill_name、event_params |
| event_params | product_client_id、skill_scope、plugin_id、remote_plugin_id、repo_url、thread_id、turn_id、invoke_type、model_slug |

该结构没有独立 invocation_id、occurred_at、trace_id、span_id 或成功 status。不能套用其他 analytics event 的字段，也不能用 Thread/Turn 关联证明它是 OTel span。

Resource 且 implicit 的分析事实在 Reducer 再做一次按 turn_id/resource id 的去重；Host 分支和显式 Resource 分支没有这项过滤。Turn 去重状态是内存状态，不是持久化幂等账本。

源码：[事件数据结构](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/analytics/src/events.rs#L196)、[事实入口](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/analytics/src/client.rs#L298)、[Reducer](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/analytics/src/reducer.rs#L1211)。

## 4. Skill 身份怎么产生

Host 的 skill_id_for_local_skill 先规范化路径：有仓库 URL 和根路径时取仓库相对路径，否则取规范化绝对路径，统一路径分隔符。再对 prefix、path、skill_name 的组合做 SHA-1；prefix 为 repo 加仓库 URL，或者 personal。

这不是文件正文摘要，也不是每次调用随机产生的 UUID。移动文件、改名或仓库 URL 改变可能改变统计身份，scope 本身不直接进入此 hash 公式。Resource 优先采用其已有 skill_id，缺失时才对 resource id 做 SHA-1。

它适应 Codex 的本地与资源 Skill 模型。CampusClaw 已有元数据 Skill ID，应直接复用经过执行快照验证的 ID，无须把 Codex 的路径 hash 搬进企业主数据。

源码：[skill_id_for_local_skill / normalize_path_for_skill_id](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/analytics/src/reducer.rs#L3574)。

## 5. 去重和失败案例矩阵

以下只计算调用点产生的量，假定对应指标启用、分析队列接收成功且内存状态仍存在；送达后台的数量另受第 6 节影响。

| 场景 | metric 增量 | analytics 事件 | 原因 |
|---|---:|---:|---|
| 一次 Host 显式成功注入 | 1，ok | 1，explicit | 加载成功 |
| 一个已选 Host Skill 注入失败 | 1，error | 0 | mentioned 与 injected 不同 |
| 一个输入重复选择同一 Host Skill | 通常 1 | 通常 1 | 本次选择集合按路径去重 |
| 同一 Turn 三次可识别 Shell 访问同一 Skill | 1 | 1 | Shell 入口先去重 |
| 已识别 Shell 命令随后执行失败 | 已加 1，ok | 已生成 1 | 识别发生在执行前 |
| 同一 Turn 两次从第一页读取同一 Resource 主提示 | 2 | 1 | metric 在 Resource Reducer 去重之前 |
| 主提示第一页加两次 cursor 续页 | 1 | 1 | 续页不触发此埋点 |
| 显式注入后又经 Shell 隐式访问 | 可以为 2 | 可以为 2 | 没有跨显式/隐式的统一去重 |
| 下一 Turn 再次访问同一 Skill | 可再计数 | 可再生成 | 不是 Thread 或根任务全局去重 |

由此，SUM(skill.injected)、COUNT(skill_invocation)、COUNT(DISTINCT turn_id, skill_id) 是三个不同问题，不能互换。任何聚合还必须明确来源类型、status 及投递覆盖范围。

## 6. 队列、配置与送达保证

AnalyticsEventsClient 在 analytics_enabled 不为 false 时创建队列。队列容量 256，使用 Tokio mpsc.try_send；队列满或关闭导致发送失败时丢弃事实并记录警告。消费者逐项归约，调用 send_track_events；flush 是有期限的屏障，不能恢复已经丢弃的事实。

正常 HTTP 目的地为配置的 base_url 加 /codex/analytics-events/events，请求体为 events 数组。每次发送有 10 秒超时；未成功的 HTTP 响应及网络错误在该层只写警告，未见持久化 outbox 或补偿重放。调试构建有 capture file 分支，可替代网络发送。

发送还受认证约束：无可用 auth 或不属于支持的 Codex 后端时不发送；API key 模式只允许其中部分事件，SkillInvocation 要具有 plugin_id。不能把“源码调用了 track”描述为“每个用户的每次 Skill 都会送达”。

源码：[队列与开关](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/analytics/src/client.rs#L79)、[发送与失败处理](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/analytics/src/client.rs#L819)、[API key 事件过滤](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/analytics/src/events.rs#L163)。

## 7. Turn 耗时归因

SkillTelemetry 在 Turn 开始保存计时器。调用时 record_plugin_turn_usage 记录用到的 plugin 集合；停止、取消或错误结束时，SkillTurnMetrics.finish 对每个 plugin 输出同一段 Turn 总耗时，按秒向上取整。usage.take() 避免 finish 重复输出，失败状态覆盖普通 completed。

一个 Turn 使用 A、B 两个 plugin，两者都可能被归因该 Turn 的完整耗时。因此不能将这两个值相加作为 Turn 耗时，也不能将其包装为 Skill A、B 各自的执行时长。

源码：[telemetry.rs · SkillTurnMetrics / SkillTelemetry](https://github.com/openai/codex/blob/d58d0e5841e0de08e251673db2d5af8cf3a1ad51/codex-rs/ext/skills/src/telemetry.rs)。

## 8. 对 CampusClaw 的取舍

| Codex 参考点 | CampusClaw 已确认目标 | 分类与理由 |
|---|---|---|
| 运行时结构化观测 | 显式输入受理后与最终 Read 成功正文形成信号，用真实根/Skill 归因 | 架构变更：保留触发证据，不扫描日志猜测采用 |
| 主提示首屏可计数 | 主文档部分正文即可；允许首先读取中段 | 产品约束：不要求全文覆盖，也不复制 cursor 条件 |
| 不同入口去重不同 | 同一 (sessionId, rootEventId, skillId) 至多计一次，显式与 Read 共用 Tracker 和数据库唯一键 | 架构变更：统一观察根执行使用频度，不能称为 Codex 的原样口径 |
| Shell 执行前识别 | 首版仅显式受理与通用 Read，不增加 Shell/activate_skill 工具 | 产品约束：使用现有可验证入口，不以命令字符串证明成功 |
| 路径/名称 hash 身份 | 复用受管元数据 Skill ID、Runtime 根与规范工具调用来源 | 产品约束：保持企业资源身份和可核对关联 |
| best-effort 遥测 | 统计失败不改变主执行结果；三张统计表在独立事务中一起提交 | 架构变更：内部汇总一致但允许漏计，不保证与 Runtime 历史恒等 |
| 有界异步分析队列 | 首版一次有等待预算的同步写入，无新增 MQ/OTel 依赖 | 架构变更：实现较少，但连接/锁/语句等待仍影响延迟，须实测；不能称作 Codex 同一投递架构 |
| Thread/Turn 关联 | 复用 sessionId/rootEventId；确认、问答、审核续跑保持根 | 产品约束：根执行不等同 Codex Turn 或整个 Session |
| 无公开后台表证据 | 自行设计 t_skill_usage、累计/日表和两项 GET | 证据边界：这是 CampusClaw 目标，不是 Codex 后台实现 |

显式 A 后 Read A 三次，在本目标中共计 1；Codex 的不同入口可能输出不同数量。CampusClaw usageCount 表示已记录使用信号的根执行数，不证明模型实际采用。日期归首个入账信号，同根跨天重复不刷新计数或 lastUsedAt。范围、失败和清理以[主设计](README.md)为准；目标已确认但仍为 target-only。

## 9. 核验记录

已读取各链接所列函数、相关数据结构和生产调用点。另读取 codex-rs/skills/src/invocation_tests.rs 的识别用例、codex-rs/analytics/src/analytics_client_tests.rs 的 reducer_ingests_skill_invoked_fact（约 4159 行），核对事件字段样例；未运行 Rust 测试、未启动 Codex、未校验实际遥测出口。

未核验范围：服务端数据库、指标聚合与采样配置、报表和排行 API、实际端到端送达率。固定提交不升级为当前最新版本，也不重置设计仓其他 Codex 模块的源码核验点。
