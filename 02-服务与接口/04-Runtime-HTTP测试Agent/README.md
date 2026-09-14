# Runtime HTTP 回归适配器（历史基线）

| 属性 | 值 |
|---|---|
| 文档版本 | 1.2.0 |
| 状态 | HTTP 1.37 历史回归资料；适配器机制保留，当前契约迁移待实施 |
| 模块职责 | 为产品级 TDD Agent 提供 HTTP、数据库与打包进程回归能力 |
| 历史 HTTP 契约版本 | `1.37.0`，十一项 operation 均已确认 |
| 设计仓分析基线 | `8ab8eef47b2dc0d9e21ae0ca0bd7617f8a158a32`；运行时仍另记工作树状态与 SHA-256 |
| 历史 HTML 契约 SHA-256 | `5c1f235bd04017390bf2a8fd603d176b5f9a3babc019e33cee192ce132672604` |
| 历史实现分析基线 | `1f801dbb82bdda30478e3354e685e3153b179a0c`，`origin/main` |
| 初始机器用例目录 | [`test-case-catalog.json`](test-case-catalog.json) |
| 更新日期 | 2026-09-14 |

> 历史实现回归基线，不是当前目标接口清单。本文与用例目录固定于 HTTP 1.37 / 旧实现，
> 其中三个控制接口仅供旧版本回归；当前目标已移除，不得据此新增或恢复路由。
> [当前九项清单](../../01-总体架构/01-CampusClaw多Agent运行时/README.md#4-当前目标-http-接口清单)
> 与 Events v2 为迁移目标；测试执行须固定匹配的历史契约 commit，不能用当前 HTML 冒充 1.37。

## 1. 职责与使用边界

本专题是[CampusClaw TDD Agent](../05-CampusClaw-TDD测试Agent/README.md)的 `runtime-http` 领域适配器。它解析固定契约、选择用例、拉起隔离环境、运行确定性断言并收集证据；产品能力盘点、跨模块覆盖和测试维护策略由 TDD 主设计维护。

此处的机器目录及具体 operation 场景固定于 HTTP 1.37。当前 Runtime 已采用九项接口和 Events v2，因此历史用例不能直接作为当前版本的通过证明。迁移需先绑定新契约与精确 requirement，再更新用例；不得据此恢复已移除路由。

通过或失败由签入仓库的断言、Schema、状态机和数据库不变量决定。Agent 可提出用例补丁，但不能放宽断言或覆盖失败。影响不明时运行全量；必需环境和测试缺失时直接失败，不能按 skip 计为通过。

## 2. 权威输入与基线选择

### 2.1 契约权威

本节仅描述 HTTP 1.37 历史回归，测试 Agent 必须在对应历史 commit 读取以下文件。
当前工作树的旧 HTML 已删除，不保留迁移页，也不得为测试恢复副本。
当前目标契约统一见 [九项接口页](../../01-总体架构/01-CampusClaw多Agent运行时/chat-api-review.html)。
历史源固定为设计提交 `8ab8eef47b2dc0d9e21ae0ca0bd7617f8a158a32`，当时的目录为
`pi-mono-java-manager-driven-multi-agent-runtime/`；以下两个文件名是该提交内的路径，
不是当前工作树链接。历史读取顺序为：

1. `chat-http-v1-review.html`：
   HTTP V1 的人类主维护契约，在 `api-review-models` 中内嵌 11 个 operation model；
2. `chat-http-v1-design.md`：
   状态、并发、SSE、错误和恢复原因；
3. 本目录的 [`test-case-catalog.json`](test-case-catalog.json)：
   契约要求到可执行测试的稳定映射；
4. 候选提交的 Controller、VO、Service、Mapper、SQL 和配置：实现证据，不能反向覆盖已确认
   契约。

本目录校验器按用例目录中的 `sourceKind=git-history`、完整 `sourceCommit`、仓库相对路径
和 SHA-256，通过 `git show` 在内存中读取历史契约。默认运行
`python3 validate-http-test-agent-design.py` 不依赖已删除页面；缺少提交或摘要不符直接失败。
`--contract-ref` 只允许完整提交 ID，仍必须匹配冻结的摘要，不能借此覆盖当前九项接口。

Runtime HTTP 接口当前不维护 OpenAPI。Agent 必须从 HTML 中的结构化 review model 提取
operation，而不是从历史 Git 恢复已经废弃的 OpenAPI。提取结果必须记录契约版本、文件
SHA-256、设计提交、工作树状态和 11 个 operation key，任何无法解析、重复或缺失都直接
阻止测试开始。设计工作树可处于未提交状态，以支持设计阶段 TDD；报告必须显式标记
`sourceDirty=true`，不得把它表述成稳定发布基线。

### 2.2 代码基线差异

历史 HTTP V1 的 11 个 Spring MVC operation 存在于 `pi-mono-java` 基线
`1f801dbb...`。Agent 每次运行仍必须显式接收不可变 `candidate_commit` 和
`merge_base_commit`：

- 不根据当前目录名猜分支；
- 不在用户脏工作区中切换分支或覆盖文件；
- CI 使用当前 PR 的不可变 SHA；本地使用独立临时 worktree；
- 如果目标提交没有 11 个接口，报告契约漂移或错误基线，而不是悄悄回退到旧 `/api/*`；
- 报告同时记录源码提交、契约版本、目录状态和实际执行命令。

## 3. HTTP 1.37 冻结清单

基础路径为 `/campusclaw-service/v1`。下表是 Agent 启动时必须从 HTML 主契约重新提取并
与用例目录核对的冻结清单。

| # | 接口简称 | Operation key | Method | Path | 主要响应 |
|---:|---|---|---|---|---|
| 1 | 创建会话 | `createSession` | `POST` | `/agents/{agent_id}/sessions` | `201` ResultBean |
| 2 | 查询会话 | `getSession` | `GET` | `/sessions/{session_id}` | `200` ResultBean + ETag |
| 3 | 删除会话 | `deleteSession` | `DELETE` | `/sessions/{session_id}` | `204` |
| 4 | 提交用户消息 | `submitUserMessage` | `POST` | `/sessions/{session_id}/events` | `200 text/event-stream` |
| 5 | 查询会话事件 | `listSessionEvents` | `GET` | `/sessions/{session_id}/events` | `200` ResultBean |
| 6 | 查询可用模型 | `listSessionModels` | `GET` | `/sessions/{session_id}/models` | `200` ResultBean |
| 7 | 切换会话模型 | `changeSessionModel` | `PUT` | `/sessions/{session_id}/model` | `200` ResultBean + ETag |
| 8 | 设置深度思考 | `changeSessionThinking` | `PUT` | `/sessions/{session_id}/thinking` | `200` ResultBean + ETag |
| 9 | 追加引导消息 | `appendSteer` | `POST` | `/sessions/{session_id}/steers` | `202` ResultBean |
| 10 | 追加后续消息 | `appendFollowUp` | `POST` | `/sessions/{session_id}/follow-ups` | `202` ResultBean |
| 11 | 中止会话执行 | `abortSession` | `POST` | `/sessions/{session_id}/abort` | `204` |

WebSocket、公开 Run、旧 `/api/chat` 和旧 `/api/skills` 不属于该历史 Runtime HTTP V1。
Agent 应保留路由 tombstone 测试，防止大改动时把这些已废弃接口重新暴露出来。

## 4. 实现范围与差距

历史产品源码 `1f801dbb82bdda30478e3354e685e3153b179a0c` 已有十一项 Controller、路由测试、数据库测试和可手动运行的进程 IT；默认 CI 未强制运行这些 IT，缺少前置参数时允许跳过。具体路径、符号与差距见[历史源码证据](source-evidence.md)。

适配器的契约抽取、环境编排、必跑门禁和精确 case 绑定按下文目标维护。旧文档记载的首版执行器位于开发分支，但未绑定不可变提交；本次整理不据此宣称最新实现已经通过验收。

## 5. 目标架构

![HTTP 测试 Agent 架构](http_test_agent_architecture.svg)

[PlantUML 源码：`http_test_agent_architecture`](diagram.puml#L1) · [原尺寸 SVG](http_test_agent_architecture.svg)

### 5.1 Agent 组件

| 组件 | 职责 | 失败策略 |
|---|---|---|
| Baseline Resolver | 解析候选 SHA、merge base、契约版本和工作区状态 | 任一基线不明确立即 fail closed |
| Contract Extractor | 解析 11 个 HTML review model，生成规范化 operation 快照和摘要 | 缺失、重复、非法 JSON、版本不一致均失败 |
| Change Impact Analyzer | 将 Git diff 映射到 operation、状态机、数据库、启动和镜像边界 | 无法映射的变更视为全局影响 |
| Deterministic Test Planner | 展开公共矩阵和 operation 用例，生成不可变执行计划 | 不得省略 P0 不变量 |
| Environment Provisioner | 创建临时 worktree/home、随机端口、固定 Agent 目录、openGauss 和模型 SSE 桩 | 必需依赖未就绪时失败，不 skip |
| Test Executor | 执行静态、MockMvc、Service、DB、并发、进程和兼容性层 | 每层独立超时，失败后仍收集诊断 |
| Oracle and Evidence Collector | 解析 JUnit XML、HTTP/SSE、数据库断言、退出码和日志 | 只接受确定性断言；不以自然语言判断通过 |
| Case Maintenance Proposer | 比较契约、路由和用例覆盖，生成新增或迁移补丁 | 不自动删除/放宽用例，不自动合并 |

### 5.2 确定性判定

operation 集合、HTTP/JSON/SSE 字段、数据库状态、退出码、skip 数量及 case ID 均由程序验证。Agent 的影响分析和补丁建议进入报告，不能覆盖这些判定；产品级权限与防弱化规则见[TDD 主设计](../05-CampusClaw-TDD测试Agent/README.md#4-agent-的专业角色与权限)。

## 6. 用例目录模型

[`test-case-catalog.json`](test-case-catalog.json) 是本设计提供的机器用例目录。
它不是新的 HTTP 契约，而是主契约的测试投影，并持续留在本设计仓维护。代码仓执行器
通过显式 `--design-repo` 只读消费本目录；不得在代码仓复制第二份目录形成双重权威。

### 6.1 单个用例字段

| 字段 | 规则 |
|---|---|
| `id` | 永久稳定，如 `HTA-EVT-SUBMIT-012`；修改语义不能复用旧 ID |
| `operationKey` | 必须引用 11 个已提取 operation，跨接口用例使用 `crossOperation` |
| `priority` | `P0/P1/P2`；P0 是所有 PR 必跑不变量 |
| `layer` | `static/mvc/service/database/process/concurrency/recovery/compatibility` |
| `requirementRefs` | 指向 HTML 契约版本、设计章节或稳定规则 ID |
| `preconditions` | Session 状态、模型能力、数据库、Agent 目录和桩行为 |
| `request` | Method、Path、Header、Query、Body 或断连动作 |
| `oracle` | status、Header、JSON/SSE、状态变化、持久化和负向泄漏断言 |
| `cleanup` | 删除临时 Session、停止进程/容器、清理临时目录；必须幂等 |
| `determinism` | 固定时钟、随机种子、游标密钥和可重放桩脚本 |
| `status` | `active/proposed/retired`；只有 active 参与 required gate |
| `sourceEvidence` | 对应实现提交、仓库相对路径、符号或基线行号 |

### 6.2 公共矩阵

公共模板按 operation 展开，避免在 11 个接口中复制维护。

| 模板 | 展开范围 | 必要断言 |
|---|---|---|
| `AUTH_*`（retired） | 不再展开 | 保留历史用例 ID，防止旧 Runtime 本地 `401` 契约被误认为仍 active |
| `NO_BUSINESS_AUTH` | 全部 11 项 operation | JWT、APPKEY、两者共存、缺失或坏形状均不触发 Runtime 本地认证；Header 不进入响应/日志 |
| `LOCALE_ZH_EN_FALLBACK` | 全部错误码 | `zh-CN`、`en-US` 和未知语言回退；`Content-Language` 与实际文本一致 |
| `ERROR_ENVELOPE` | 全部非 SSE 错误 | 响应只有 `resCode/resMsg`，不得出现 `result` 或敏感信息 |
| `SUCCESS_ENVELOPE` | 普通 JSON 成功 | 精确包含 `resCode="0"/resMsg="success"/result` |
| `NO_BODY_204` | Delete、Abort | 空 Body，不使用 ResultBean |
| `NO_RESULTBEAN_SSE` | POST Events | `text/event-stream`，frame 中不得出现顶层 ResultBean |
| `IDENTIFIER_BOUNDARY` | agent/session/model ID | 类型前缀 + 32 位十六进制、错前缀、内部连字符、长度、旧下划线格式和大小写 |

调用上下文模板只断言 Runtime 不根据 Header 组合、共存、形状或真实性产生本地认证结果；
业务层可由固定桩返回该 operation 的最窄成功或业务错误。真实性与动作授权由上游负责。

## 7. 分层测试策略

| 层级 | 目标 | 主要技术 | PR 门禁 |
|---|---|---|---|
| L0 契约与路由漂移 | HTML、目录、Controller 路由、错误枚举、消息资源一致 | HTML JSON 抽取、Spring `RequestMappingHandlerMapping`、静态校验 | 始终必跑 |
| L1 HTTP 边界 | Method/Path/Header/Body/status/ResultBean/语言 | JUnit 5 + MockMvc 参数化/动态测试 | 始终必跑 |
| L2 Service 不变量 | Session 状态、模型切换、队列、Event 投影、恢复 | 现有 Service 测试 + 固定 Clock/Stub | 影响相关必跑；P0 始终 |
| L3 数据库与并发 | 原子事务、Entry 序号、当前分支、CAS、tombstone、清理 | Failsafe + 隔离 openGauss | 数据/状态变更和全量模式必跑 |
| L4 打包进程 HTTP/SSE | 真实 JAR、Servlet/Netty 装配、序列化、SSE、断线 | Failsafe + 随机端口 + 模型桩 + openGauss | 高风险 PR、全量、发布必跑 |
| L5 镜像与公司适配 | `mate-campusclaw` 同步、包名、ResultBean Bean 替换 | 同步 dry-run、镜像编译、契约复用 | 相关变更和发布必跑 |
| L6 变异与韧性 | 发现“测试通过但断言无效”与故障恢复缺口 | 关键包 mutation、网络/DB 故障注入 | 夜间和发布 |

代码覆盖率只作为缺口线索，不作为唯一质量门禁。关键要求以用例 ID 和不变量是否真实执行
为准；对 auth、ETag、状态机、分页游标和 SSE 终态建议增加夜间变异测试。

## 8. 历史用例范围

每项 operation 的正向、边界和负向断言由[test-case-catalog.json](test-case-catalog.json)维护；公共 Header、语言、错误包装与 ID 边界由 §6.2 模板展开。这里保留跨接口不变量和仍未冻结的拒绝语义，避免再维护一张与机器目录重复的场景表。

### 8.1 跨接口场景

至少维护以下端到端 P0 场景：

1. Create → Get → Submit → SSE 完成 → List Events → Change Thinking → Change Model → Delete。
2. Create → Submit 保持 running → Steer → FollowUp → 原 SSE 顺序输出 → 分页读回。
3. Create → Submit 保持 running → 第二个 Submit 409 → Delete 409 → Abort → Delete 204。
4. SSE 客户端断连 → 执行继续 → GET Events 从第一页恢复并按 `entry_id/entry_seq` 去重。
5. 旧 ETag 并发写：两个配置请求只允许一个成功，另一个 412，数据库无部分状态。
6. 删除事务失败 → Session 仍可读；重试成功 → API 隐藏、tombstone 保留、清理任务最终完成。
7. 主模块测试通过后同步生成 `mate-campusclaw`，镜像路由清单、JSON 和 SSE 契约完全一致。

### 8.2 待契约校准项

以下请求在文档中描述为“不接受”，但已确认错误表没有冻结具体 HTTP status/resCode，且
Spring MVC 默认可能忽略它们。测试目录将其标记为 `proposed`，不应凭空设为 P0：

- 向 Create、Get、Delete、List Models、Abort 发送额外 Body；
- 向不支持过滤的 GET 接口发送未知 Query 参数；
- 向 Abort 发送 `If-Match`、`Idempotency-Key` 或原因字段。

在接口评审冻结拒绝语义前，Agent只报告“契约可测试性缺口”，不能自行选择 400、415 或
忽略行为。该分类属于待确认产品约束，不是已观察实现行为。

## 9. 变更感知与大改动策略

### 9.1 影响映射

| 变更路径或符号 | 强制测试集合 |
|---|---|
| 主 HTML、设计版本、review model | L0 + 11 operation 全矩阵 + 用例维护审计 |
| Controller、VO、auth、exception、messages | L0 + L1 全矩阵 + 受影响业务层 |
| RuntimeEvent/Agent/Tool/queue/SSE | Submit、Steer、FollowUp、Abort + 并发/恢复 + L4 |
| Session Service、model manager adapter | Create/Get/Delete/Models/两个 PUT + L3/L4 |
| Mapper XML、SQL、DTO、repository | 全部状态 operation + L3 + L4 |
| 启动类、application 配置、POM、打包 | L0-L5 全量 |
| sync 脚本或 `mate-campusclaw` | 主模块回归 + 镜像差异/编译/进程 smoke |
| 无法映射、跨两个以上核心边界或大规模重命名 | 全量，不允许 affected-only |

### 9.2 全量触发与最低保留集

基础路由、契约版本、认证边界、ResultBean、错误与语言、Session 状态、SSE、数据库或构建系统变化必须全量。跨核心层变更、rename/copy 识别不完整、merge base 缺失、镜像不同步或未知符号也进入 `pr-full`；人工可显式要求全量。文件数或改动行数只能辅助判断。

`affected-only` 仍须执行契约抽取、路由清单、调用上下文矩阵、错误/语言资源、ResultBean、全部 P0 的编译与目录校验、变更模块单测和打包启动 smoke。

## 10. 自动拉起与执行流程

![HTTP 测试 Agent 执行时序](http_test_execution_sequence.svg)

[PlantUML 源码：`http_test_execution_sequence`](diagram.puml#L80) · [原尺寸 SVG](http_test_execution_sequence.svg)

### 10.1 隔离环境

每次执行创建独立任务目录，并至少提供：

- 候选提交的 detached worktree；
- JDK 21 与 Maven Wrapper；
- 由候选提交构建的可执行 JAR，不复用未知来源的本地 `target/`；
- 固定版本且最终按 digest 锁定的 openGauss 测试实例；
- 本地 fake Model SSE server，按脚本产生成功、工具调用、慢响应、错误和断连；
- 临时 `CAMPUSCLAW_HOME`、受控 Agent 目录、固定 Clock/seed/cursor secret；
- 由操作系统分配的随机本地端口；
- 所有外部网络默认禁止，避免测试误调真实模型、Manager 或生产数据库。

openGauss 的具体镜像仓库与 digest 需要按实际 CI 网络和公司制品库校准；在校准前只记录为
目标依赖，不能假设某个公网 `latest` 标签永久可用。

### 10.2 Maven 生命周期

目标实现应：

1. Surefire 执行 `*Test`；
2. Failsafe 在 `integration-test/verify` 执行 `*IT`；
3. 将 openGauss/JAR 参数由环境控制器显式注入；
4. required CI 中断言 Failsafe 实际发现并运行预期 IT ID，`Tests skipped > 0` 直接失败；
5. 将数据库 IT 和进程 IT 拆成可单独定位的场景，同时保留一个完整生命周期 smoke；
6. 默认 CI 不重跑失败用例来制造绿色结果；只允许显式诊断重跑，并保留首次失败证据。

### 10.3 执行模式

| 模式 | 触发 | 内容 |
|---|---|---|
| `pr-fast` | 普通低风险 PR | L0/L1、受影响 L2、P0、打包启动 smoke |
| `pr-full` | 大改动或高风险路径 | L0-L5 全量，openGauss 与真实进程必跑 |
| `nightly` | 定时 | 全量 + 并发重复种子 + 故障注入 + 关键包 mutation |
| `release` | 发布候选 | nightly 内容 + 主/镜像 JAR + 公司 Adapter/Profile 兼容矩阵 |
| `local` | 开发者手动 | 与 CI 相同的 plan JSON，可选择单个 case ID，但报告为非合并门禁 |

## 11. 结果判定与证据

一次通过必须同时满足：

1. 候选和 merge base 是不可变提交，契约版本与哈希已记录；
2. 11 个 operation 与用例目录完全对应，无未知路由或复活的废弃路由；
3. 执行计划中的 required case ID 全部实际运行，零意外 skip；
4. HTTP/SSE/JSON/数据库断言全部通过；
5. 进程、端口、容器和临时目录已清理，无残留测试 Session；
6. `modules/*` 与需要验证的 `mate-campusclaw` 镜像同步；
7. 证据包完整并可用相同 seed、fixture 和命令重放。

证据包建议包含：

```text
http-test-agent-results/
├── plan.json
├── baseline.json
├── contract-snapshot.json
├── case-results.json
├── junit/
├── http/
├── sse/
├── database/
├── process-logs/
└── summary.md
```

报告按 `contract failure / implementation failure / environment failure / flaky evidence /
review required` 分类。环境失败不计为产品通过；允许单独重跑以诊断，但 required check
保持失败直到一次全新隔离执行完整通过。

## 12. 用例维护与防弱化

![HTTP 用例维护生命周期](http_test_case_maintenance.svg)

[PlantUML 源码：`http_test_case_maintenance`](diagram.puml#L147) · [原尺寸 SVG](http_test_case_maintenance.svg)

### 12.1 自动维护规则

- 新 operation：先出现契约变更，再生成新的 operation key、P0 happy path、调用上下文矩阵、错误
  包装和 route inventory 用例；缺任一项不得合并。
- 新字段/状态/错误：生成边界、未知值、兼容性和负向泄漏用例，并保留旧 case ID。
- 实现重构但契约未变：只更新 source evidence 和 fixture，不修改预期。
- 确认删除 operation：旧用例转为 `retired`，同时新增“路由不存在”的 tombstone 用例。
- 测试发现真实遗漏：Agent 可以提交 additive proposal；由维护者审核后变为 active。
- 不稳定用例：先记录 seed/日志并修复隔离或时钟；禁止无到期日 quarantine。

### 12.2 断言与目录保护

弱化、替换或退役必须有显式人审、契约引用和版本记录。禁止用当前返回值覆盖断言、删除字段/顺序/副作用校验、扩大超时或重试来掩盖失败、无依据更新 golden、因源码删路由便删测试，或让 required IT 可以跳过。Agent 只提出补丁，不自动合并；真实凭据与生产数据不进入测试。

## 13. 安全、可靠性与成本

| 关注点 | 规则与理由 |
|---|---|
| 隔离 | 假凭据、loopback、默认断网；数据库名称或 Schema 每次唯一，清理目标先做前缀校验 |
| 证据安全 | JUnit、HTTP、SSE 归档前扫描敏感字段，Header 不进入日志 |
| 可复现 | 固定 Clock、seed、游标密钥和模型输出；条件等待有界，并发用 barrier/latch，端口由系统分配 |
| 首次失败 | 保存原始失败上下文；诊断重跑不能覆盖首次证据或制造通过 |
| 构建成本 | 同一候选只构建一次主 JAR；跨场景复用制品，不复用数据库状态 |
| 镜像成本 | 主模块跑业务回归，镜像先查同步、编译和进程 smoke；发布跑完整镜像矩阵 |
| 深测成本 | mutation 与高次数并发进入 nightly；Agent 仅修改测试、fixture、目录和报告 |

## 14. 分阶段落地

### 阶段 A：先把现有测试变成门禁

1. 新增 HTML review model 抽取器和 11 operation route inventory 校验。
2. 代码仓只读消费设计仓用例目录，增加唯一 ID、字段和契约哈希校验。
3. 配置 Failsafe，自动拉起隔离 openGauss；required 模式禁止 `*IT` skip。
4. 将现有 `RuntimeHttpProcessOpenGaussIT` 拆成可定位场景并保留完整 smoke。
5. CI 增加 `pr-fast/pr-full`，先覆盖当前实现，不改业务契约。

### 阶段 B：补全用例矩阵

1. 用动态测试展开 11 operation 的调用上下文、语言、错误 envelope 和 ID 边界。
2. 补齐 SSE 断连、流内错误、工具路径、容量失败和恢复。
3. 补齐 openGauss 故障、删除重试、并发 POST/PUT 和游标隔离。
4. 增加旧 `/api/*`、WebSocket 和公开 Run 的 tombstone 路由测试。

### 阶段 C：Agent 维护闭环

1. 生成 `plan.json` 和变更影响报告；未识别变更自动全量。
2. 生成新增用例 proposal 和 source evidence 更新，禁止自动弱化。
3. 夜间运行 mutation/故障注入，按存活 mutation 生成候选用例。
4. 接入公司 ResultBean/调用上下文 Adapter profile 后执行同一契约矩阵。

## 15. 验收标准

- 主契约增删 operation，而用例目录和 route inventory 未同步时，L0 必须失败。
- 任一 Controller 改变 Method、Path、status、Header、JSON 或 SSE 顺序时，相应用例必须失败。
- required CI 中 openGauss 或打包 JAR IT 未执行时，任务必须失败而非通过。
- 大规模重构、无法映射的 rename 或跨层变更自动选择 `pr-full`。
- 同一失败可用证据包中的提交、seed、fixture 和命令重放。
- Agent 提出的用例维护补丁包含 requirement refs、source evidence 和新增断言；弱化补丁不能
  自动合并。
- 主模块和 `mate-campusclaw` 的公开 HTTP 行为保持一致。
- 所有 11 operation 至少有 P0 happy path、适用的 auth/no-auth、error envelope 和资源不存在/
  状态冲突等负向用例。

## 16. 设计理由与实现边界

契约抽取、不可变计划、环境控制与确定性证据是架构变更，目的是让“存在测试”落实为“必需测试实际运行”。假服务、默认断网、敏感扫描和防弱化属于安全加固。其代价是维护环境、fixture 和用例映射，并承担数据库及进程回归的执行成本。

历史实现、开发分支记录和待落地能力分别见 §4 与[源码证据](source-evidence.md)；§8.2 的拒绝语义仍待校准，不因增加自动化而成为已确认契约。

## 17. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.2.0 | 2026-09-14 | 明确历史回归适配器的职责、源码边界和目录归属，重排架构及执行流程。 |
| 1.1.4 | 2026-09-14 | 当前目标导航对齐统一 Session POST 的九项清单，冻结回归基线与用例不变。 |
| 1.1.3 | 2026-09-10 | 同步当前目标为十一项接口，历史 HTTP 1.37 回归基线不变。 |
| 1.1.2 | 2026-09-07 | 历史契约校验固定 Git 提交、路径和 SHA-256。 |
| 1.1.1 | 2026-09-07 | 保留旧实现回归证据及断言，明确旧控制接口不属于当前目标。 |
| 1.1.0 | 2026-08-20 | 对齐 HTTP 1.37 的调用上下文、ID、Thinking 与用例目录，并记录执行器范围。 |
| 1.0.0 | 2026-08-19 | 建立 HTTP 1.30 的分层回归、环境编排和证据维护设计。 |
