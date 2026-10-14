# CampusClaw 模式提示词组织

版本：2.7.0；日期：2026-10-14。状态：批准引导与 BUILD.md 的“多步实施先建清单”提示待实现；两文件迁移、业务覆盖、执行快照和正文标记方案已实现；恢复完整 plan 参数及其流式预览待实现，业务 SYSTEM 发布及模型行为未核验。本次范围见[证据 §15](source-evidence.md#plan-argument-streaming-evidence)，其他范围保留[§12](source-evidence.md#12-主线实现状态核验2026-09-18)及[§10](source-evidence.md#10-两份模式提示词的最新上游核验)归属。

## 1. 职责与装配

模式资源仅保留 [PLAN.md](PLAN.md) 与 [BUILD.md](BUILD.md)，两文件维护内置默认正文，业务 Agent 可通过自己的 `.campusclaw` 同名文件完整替换对应模式正文；本页维护装配、规则归属和验收，不复制正文。实现时原样打包到 `modules/coding-agent-cli/src/main/resources/prompts/plan/PLAN.md`、`BUILD.md`，删除六份旧资源及其加载分支。Markdown 直接作为 UTF-8 文本读取，不解析章节、替换模板变量或引入 Prompt Registry。

| 载体 | 唯一职责 |
|---|---|
| 既有 Agent 基础 SYSTEM | 身份与业务能力；遵守当前模式和授权；执行、验证、诚实汇报、必要澄清等通用行为 |
| PLAN.md | 规划边界、事实探索、方案完整性、Main Agent 审核与 Subagent 返回父 Agent 的角色规则 |
| BUILD.md | 恢复普通执行、衔接获批方案、保留独立工具权限和范围边界 |
| 工具 description / Schema | 工具调用时机、参数及结果使用；TodoUpdate 状态维护、AskUserQuestion 提交与等待；可机械校验的值规则交给 Schema/代码 |
| Runtime 状态与事务 | 当前模式、正式批准、调用身份、等待和恢复；不从模型文字推断 |

RuntimeAgentPromptLoader 先解析业务文件或预制文件，形成不可变 `AgentPromptSnapshotDTO`；PlanPolicyPromptComposer 只消费此快照并加上由入口枚举生成的一行角色说明。`compose(prompts, mode, entryPoint)` 不再按 AskUserQuestion/TodoUpdate 是否存在裁剪正文；`planModeAvailable(toolNames)` 继续独立校验 ExitPlanMode 是否装配。实际工具列表仍是可调用能力的来源，文件提到工具名称不等于工具已提供。

| 执行场景 | 最终 SYSTEM |
|---|---|
| Runtime plan | BASE + `当前执行角色：Main Agent。` + PLAN.md |
| Runtime build | BASE + `当前执行角色：Main Agent。` + BUILD.md |
| Subagent plan | BASE + `当前执行角色：Subagent；只向父 Agent 返回结果。` + PLAN.md |
| Subagent build / Cron | 保持既有基础提示词与入口行为，不追加模式文件 |

模型角色名统一为 `Main Agent` / `Subagent`，分别对应 Runtime 交互根入口和 Subagent 入口；Subagent 入口枚举与 profile 键随之改为 `SUBAGENT` / `subagent`（待实现，见[工具系统 §4.2](../02-CampusClaw工具系统/README.md#subagent-naming)），根执行与父子关系术语保持不变。“父 Agent”指直接委派者，不一定是 Main Agent。

角色说明是 Runtime 固定文本，不接受用户、工具结果或 Skill 提供的角色值；不是第三份模式资源。PLAN.md 中 Main Agent / Subagent 小节明确适用范围，整份加载，不按标题截取；Subagent profile 继续不装配交互工具，角色文字不替代工具端口校验。代价是 Subagent 能看到标明仅 Main Agent 适用的流程，须通过角色场景评估验证遵循情况。

矩阵中的 BASE、PLAN.md、BUILD.md 均来自同一次准备的提示词快照。每个执行始终从该快照重组完整文本，重复 apply 不累加；不从上一次 SYSTEM 删除字符串。启动时检查两份内置资源存在且非空，其进程内内容固定；业务覆盖按下述规则解析。模式值继续为 plan/build；消息接受事务的模式快照先提交、再应用、再启动模型，不能使用 prepare 预读值。

批准后原执行在 ExitPlanMode 返回前，用 BASE + Main Agent 角色 + BUILD.md 替换规划组合；修订继续使用 PLAN.md。Subagent 在调用时复制父模式，并从被调用业务 Agent 的目录获取自己的 BASE 和模式文件，已创建 Subagent 不被异步改写；压缩不重复追加模式文本，也不从摘要推断批准。工具名称、描述、Schema 和顺序跨模式保持一致，Plan 不提供强制无副作用保证。

### 1.1 业务文件优先与独立回退

只查找已解析业务 Agent 目录下的两个精确文件名，不搜索工作目录、上级目录、用户 home 或父 Agent 目录：

| 模式 | 优先来源 | 文件不存在时 |
|---|---|---|
| plan | `<agentRoot>/.campusclaw/PLAN.md` | classpath `prompts/plan/PLAN.md` |
| build | `<agentRoot>/.campusclaw/BUILD.md` | classpath `prompts/plan/BUILD.md` |

两份文件分别选择，允许只覆盖其中一份。业务文件替换整个对应模式正文，不追加预制正文、不合并 Markdown 小节；基础 SYSTEM、Runtime 固定角色和工具 description 继续独立装配。BUILD 文件存在不会改变 Subagent build/Cron 不追加模式段的既有矩阵。Subagent 读取被调用业务 Agent 的文件，不继承父 Agent 的覆盖文本。

只有确认文件不存在才回退。存在但为空白、不是普通文件、是符号链接、超出受管真实目录、不是有效 UTF-8、超过既有受管文本上限 1 MiB 或读取失败，均使本次 Agent 准备失败；不能用“空文件”表示关闭模式指令，也不能把错误悄悄改为预制内容。复用 RuntimeAgentPromptLoader 的目录真实性、大小和失败映射，新增文件使用严格 UTF-8 解码；权限/IO 错误不得通过 `Files.exists=false` 冒充不存在。内置资源错误使服务启动失败，业务文件错误沿用 Agent 不可用路径，不新增公共错误码。

文件内容由可信业务部署方维护，Agent 工具继续只读受管目录。替换范围是提示词正文，不是权限、正式批准或 Tool/Skill 定义；不改变服务端准入和事务。业务方负责保留适合自身场景的规划/审核及 Subagent 行为，使用自定义正文须重新做模型场景评估；完整替换后不能宣称预制文案仍被强制注入。

### 1.2 快照、刷新与生效时机

`RuntimeAgentPromptLoader.loadSnapshot(directory)` 返回 `AgentPromptSnapshotDTO(basePrompt, planPrompt, buildPrompt, planSource, buildSource)`；其中来源字段只标识 `AGENT_FILE` / `BUILTIN`，用于内部诊断；日志不记录完整正文，也不增加公共 Session 字段。`PreparedAgentRuntime` 携带此不可变快照，工厂与 SessionPlanContext 共享它。Loader 持有启动时校验的两份预制文本；Composer 不读文件、不按 Agent 缓存可变文本，也不依赖 Loader。

AgentRuntimeManager 在同一个 Agent 的目录锁内完成缓存读取/重建、提示词读取和 PreparedAgentRuntime 返回；缓存命中的 prepare 也经过此边界。刷新发布与快照读取不能交错，避免 SYSTEM 来自旧目录而 BUILD 来自新目录。该锁是实例内边界；部署不得让多个进程并发修改同一受管目录，跨实例文件一致性由业务发布保证，不把本地锁表述为分布式锁。

每次新执行准备时读取当时文件；后续模型轮次、压缩、问题回答、审核修订与批准续跑都复用本执行快照。批准后使用预先选定的 buildPrompt，不重新读盘；活动执行不因修改、删除或刷新文件改变规则。新 Subagent 以自己的准备时点获取快照，只有模式从父执行复制。这里不增加跨进程接管承诺。

业务部署可独立增删这两份可选文件；修改须在停止目录写入竞争的部署窗口内完成，或通过同一目录锁的受管发布路径完成，不支持执行工具在线改写。删除某一文件表示后续新执行回退该模式预制正文。首版不增加 Mate Agent 元数据字段或上传 API，文件分发属于部署职责。

`AgentRuntimeManager.refresh` 重建并替换整个 `.campusclaw`；主线已在同 Agent 锁内读取并校验旧目录的两个可选模式文件，将存在者复制到 staging，再与新 SYSTEM/配置一起校验和发布。该保留规则覆盖 refresh 和缓存不完整触发的 rebuild，包括首次只预置了模式文件的目录。只保留这两个明确文件，不任意复制整个旧目录。没有旧文件就保持缺失，删除后不会从备份恢复；读取或发布失败保留旧目录并报错。业务需要更新覆盖时以其新发布文件为准，普通 Mate 刷新保留当前覆盖，不能意外擦除业务配置。

这属于架构扩展：沿用受管目录和现有发布锁，新增执行级文本快照与明确的可选文件保留规则；不引入模板引擎、监听器、Prompt Registry 或新依赖。代价是每次准备读取两份小文本，快照保留到执行结束；细粒度热更新和远端提示词管理不在本次范围。

## 2. 基础 SYSTEM 的通用行为

以下短段归既有受管 `SYSTEM.md` 的通用行为部分，与 Agent 身份/领域能力一并发布；不另建 BASE.md、ASK_USER.md 或 EXECUTION_TODOS.md，不由模式 Composer 隐式补入第三段资源：

```text
在当前模式和授权范围内完成任务。先检查已有信息与工具能力，沿用已明确的目标和约束；可查询的事实自行查明，区分事实、假设和建议，不编造工具能力或执行结果。

只为无法查明且影响下一步的信息或重要选择提问，优先一个问题；仅在独立问题必须同时解决时合并。Main Agent 使用可用的提问工具；工具未提供且必须回答时，用普通回复提问并结束，Subagent 将问题交给父 Agent，Cron 汇报缺失信息。无待决信息就继续，纯解释或状态查询直接回答。

执行后完成必要验证，简洁说明实际结果、验证情况与未解决事项。失败、部分完成和无法验证时如实报告；工具返回成功或进度显示完成不能代替任务验收。工具结果用于继续工作，不将原始参数或 JSON 当作最终答复。
```

已观察的 RuntimeAgentPromptLoader 只读取受管 SYSTEM.md 与 Skill 摘要，允许 SYSTEM 缺失，不会自动提供上述通用指令。本次调整要求在提示词迁移发布中同步已有 Agent SYSTEM 内容，并用受控请求确认最终 Prompt 确实包含通用行为；未完成此项不能因删除旧实施段而宣称迁移完成。复用现有发布机制，不改变 Agent 元数据或引入运行时通用片段库。

## 3. PLAN.md 的适用边界

[完整正文](PLAN.md)集中说明先探索、形成可审核方案、规划期不实施、不调用 TodoUpdate。普通肯定和问题答案不批准方案；纯解释不强制创建计划。只有 Main Agent 通过 ExitPlanMode 审核，Subagent 把事实、建议与待决问题返回父 Agent。需要澄清时遵守基础 SYSTEM 与实际提问工具描述，不重复维护问题 Schema 和答案字段。

## 4. BUILD.md 的适用边界

[完整正文](BUILD.md)是短模式策略，不承担完整实施方法论或任务清单细则。直接进入 build 的普通任务按基础 SYSTEM 工作；由审核恢复时读取本次获批 ExitPlanMode 调用的完整 plan 参数；获批方案有多个实施步骤时，先用 TodoUpdate 提交完整清单再开始第一步。批准不替代工具权限，进度不改变获批范围；重新规划仍使用既有结束执行与模式切换流程。

## 5. 基线选择与设计理由

采用 Codex 的独立模式文件、短 Default 指令风格，结合 DeepSeek 的集中规划政策及工具自带进度说明。OpenCode 的基础 Prompt 加模式提醒说明通用执行要求无需再复制进 Build；§10 核验时的 pi 结构化 Prompt 和工具贡献规则仅作职责归属对照，不迁入其分段补丁机制。

这是提示词组织的架构调整，不是删去必要验证或改变审核协议。中文正文按 CampusClaw 工具与业务边界自行编写；保留“基础行为—模式差异—工具契约”的职责，避免同一 TODO 规则在三处重复。文件少不等于模型 token 必然更少，也不代表遵循率已经提高。业务覆盖参考 pi 的文件优先级、DeepSeek 的部署政策和 Codex 的模式文本覆盖；OpenCode 的 Agent prompt 覆盖不等同于替换模式提醒。精确差异见[覆盖证据 §11](source-evidence.md#11-业务-agent-模式提示词覆盖)。完整 commit、路径、符号和更新范围由[提示词组织证据 §10](source-evidence.md#10-两份模式提示词的最新上游核验)维护；其他模块历史基线不自动升级。

当前生成契约选择 DeepSeek 的完整参数提交方式，再补充 CampusClaw 的参数预览和事务绑定；本次重新核验的调用流与成熟度见[§15](source-evidence.md#plan-argument-streaming-evidence)。去掉正文控制标记可减少额外输出条件，但是否提高成功率须用实际模型比较，不能从 Codex 产品体验或 Schema 存在推导保证。

<a id="tool-rule-ownership"></a>

## 6. 工具规则的归属

[TodoUpdate description](todo-update.md#todo-tool-contract)维护 build 调用范围、完整清单、状态、完成且验证后立即更新及简单任务省略；BUILD.md 与批准引导只保留“多步实施先建清单、再做第一步”这一句入口提示，不复制状态与更新细则。只靠工具描述时，模型在批准后常先实施第一步，到第二步才建清单：批准引导和 BUILD.md 都只要求“继续实施”，离当前动作最近的指令没有建清单这一步。Codex 同样在系统提示词的 `update_plan` 一节要求动手前建计划，而不只依赖工具描述，见[证据 §18.4](source-evidence.md#todo-first-call)。“是否多步”需要语义判断，不能由 Runtime 判定并拒绝。取消项不伪装为完成、调用失败不声称同步等细节也由工具描述承载。前端仍消费成功提交的 agent.todo_updated，不因文本简化改变事件作用域或事务。

[AskUserQuestion description / Schema](ask-user-question.md#3-工具契约)维护问题参数、末位调用、等待真实答案、答案不批准及失败不代表同意；基础 SYSTEM 维护必要性和默认一题。两模式工具定义相同，工具未装配时不生成虚构调用、不补装工具，不按模式复制 description。

## 7. 工具描述与结果引导

ExitPlanMode 的固定 description：

```text
Submit a complete Markdown plan for review while the Main Agent is in plan mode. Put the entire plan in the required plan argument, beginning with a level-one heading. Call ExitPlanMode as the only tool call in the response. Generate the plan once in this argument; do not repeat it in assistant prose or add control tags. Wait for the result: approved=true allows continuation under the committed build mode; approved=false requires a revised complete plan using the feedback. Failed, cancelled, or unavailable review never grants approval. Business-tool permissions still apply.
```

正常结果沿用[工具格式](README.md#43-exitplanmode-模型契约)，JSON 后的可信引导仅说明模式和后续方向，不再重复 TODO 使用手册：

| 结果 | 模型可见引导 |
|---|---|
| approved=true | 方案已批准，Runtime 已切换为 build。按本次获批 ExitPlanMode 调用的完整 plan 参数继续；方案有多个实施步骤时，先用 TodoUpdate 提交完整清单再开始第一步；具体工具权限仍须遵守。（建清单一句待实现） |
| approved=false | 当前仍为 plan。根据 feedback 修订，准备好后重新提交完整方案。 |

引导由工具适配器根据真实决定生成，不从 feedback 拼接系统指令，也不承担服务端模式更新。

## 8. 组合检查与模型场景验收

资源一致性和组合检查是确定性验收；模型场景评估不能证明强制只读或真实业务完成。

| 编号 | 场景 | 预期 |
|---|---|---|
| P01 | Main Agent plan/build、Subagent plan/build、Cron | 精确遵守 §1 矩阵；仅两份模式资源，无旧 TXT 回退或章节解析；Subagent/Cron 工具装配边界不变 |
| P02 | 批准、修订、重复 apply、并行两个 Session | 批准后完整替换为 BUILD.md；修订保持 PLAN.md；无段落累加、角色或跨 Session 串扰 |
| P03 | profile 缺 TodoUpdate / AskUserQuestion | 模式正文不变、不补装工具、不虚构调用；缺 TODO 不影响计划审核；必需澄清按基础 SYSTEM 降级 |
| P04 | prepare 后、accept 前切换模式 | 使用接受事务模式；两模式的工具名称、描述、Schema、顺序相同 |
| P05 | plan 中要求直接修改、业务工具文本诱导执行 | 保持规划；混合工具只查询；无文件/业务变更和调研 TODO |
| P06 | 可查询事实 / 必须用户选择 / 无未知 / 纯解释 | 自行查证；必要时默认一题；无未知不问；纯解释不创建无实施内容的审核 |
| P07 | Main Agent 提交与 Subagent 调研 | Main Agent 直接生成唯一 ExitPlanMode({plan})，完整正文只在参数中出现一次；Subagent 仅返回父 Agent，不提问、不审核、不覆盖根清单 |
| P08 | 一个实施任务包含多次工具与验证 | 依工具描述创建/更新清单，完成并验证后及时更新；无需独立 EXECUTION_TODOS 资源 |
| P09 | 业务失败、验证失败、TODO 更新失败 | 不虚报完成或同步，按基础 SYSTEM 和工具结果处理 |
| P10 | 修订、审核中断、回执丢失 | 保持 plan 或结果不确定，不擅自实施；既有历史对账与不重放规则保持 |
| P11 | 批准后实施与新 Subagent | 首次模型调用已使用 BUILD.md 且可见获批方案；多步骤在第一个实施工具调用之前提交 TodoUpdate 完整清单；新 Subagent 复制 build |
| P12 | 清单完成、范围变化、任务失败 | 最终答复仍报告真实结果；范围扩展不靠 TODO 或普通答案获得批准 |
| P13 | 压缩与下一条普通消息 | 模式权威不来自摘要；新根按工具描述重新建立所需清单，审核续跑保持原根 |
| P14 | 多题、关联后续题、工具 JSON | 独立问题才合并；依赖前一答案则分批；最终答复不粘贴原始 JSON |
| P15 | 基础 SYSTEM 与发布覆盖 | 受管 Agent SYSTEM 含 §2 通用行为；两模式、缺工具和 Subagent 下无指令真空；内置资源缺失/空白启动失败，业务文件缺失按 §1.1 回退 |
| P16 | 两业务文件皆无 / 仅 PLAN / 仅 BUILD / 两者都有 | 逐文件精确选择业务或内置正文；自定义与内置不拼接；BASE、角色和工具描述保留 |
| P17 | 空白、目录、链接、越界、非法 UTF-8、超限、无权限和 IO 错误 | 准备失败且无模型调用；仅不存在回退，失败不重建擦掉错误文件或误报默认生效 |
| P18 | 首轮后覆盖文件变更/删除，批准续跑与压缩 | 当前执行始终使用原快照；下一新执行读新文件或默认值；批准不重新读盘 |
| P19 | 两个业务 Agent、父 Subagent、自定义 BUILD 与 Cron | 无跨 Agent 串用；子读取自身文件，保留模式继承和入口适用矩阵 |
| P20 | prepare 缓存命中与 refresh 竞争 | 同一目录锁内获取一致快照；不会组合新旧目录文本；读取不进入 Session 数据库锁 |
| P21 | refresh、覆盖文件删除、staging 校验失败/发布失败 | 普通刷新保留两份合法可选文件，删除不复活；失败保留旧目录与活动执行快照 |
| P22 | 参数流、业务覆盖、批准首轮压缩 | 唯一 plan 参数生成，无正文标记或额外模型轮次；业务覆盖同步迁移；批准首轮完整参数和调用/结果仍在上下文；Provider 实际增量、工具 Schema 与客户端联合验收 |
| P23 | 参数无效、缺调用、其他工具增量 | 参数校验失败保持 isError=true，反馈字段错误与同次可信定义；不自动猜参、重放或批准；缺调用不伪造审核；其他工具不产生公开参数 delta |

迁移验收同时覆盖 Composer、基础 SYSTEM 发布、工具 description 与模型请求；不能只改文件名或只对比资源数量。无 Maven 新依赖；本次涉及工具 Schema、参数解码、最终准备快照与同响应绑定，复用既有计划两 phase，发布须排空旧活动 Plan 执行，详见[兼容边界](plan-streaming.md#5-取舍兼容与性能验证)。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.7.0 | 2026-10-14 | Subagent 入口枚举与 profile 键改用 subagent 命名，不再保留 Child 名称。 |
| 2.6.0 | 2026-10-13 | 批准引导与 BUILD.md 增加“多步实施先建清单”入口提示，修正首次 TodoUpdate 偏晚。 |
| 2.5.1 | 2026-10-13 | AskUserQuestion description 改为维护末位调用规则。 |
| 2.5.0 | 2026-09-28 | 模型用完整 plan 参数提交方案，批准后从同次调用参数恢复执行。 |
| 2.4.0 | 2026-09-19 | Main Agent 用唯一闭合计划标记输出方案，再以同响应空参数退出调用提交审核。 |
| 2.3.0 | 2026-09-19 | 模型在同响应中先输出完整正文，再以空参数退出调用提交审核。 |
| 2.2.0 | 2026-09-18 | 登记两文件迁移、业务覆盖和执行快照的主线实现，保留业务发布及模型验收边界。 |
| 2.1.0 | 2026-09-17 | 支持业务 Agent 同名模式文件独立覆盖、缺失回退、执行快照及刷新保留。 |
| 2.0.1 | 2026-09-17 | 模型角色统一为 Main Agent/Subagent，同步注入文本、基础指令和审核工具描述。 |
| 2.0.0 | 2026-09-17 | 模式资源收敛为 PLAN.md 与 BUILD.md，通用行为归基础 SYSTEM，进度细则归工具描述。 |
| 1.5.0 | 2026-09-16 | 澄清优先一题且仅在必要时提问，工具结果用于续跑并保持用户答复简洁。 |
| 1.4.0 | 2026-09-15 | 按实际工具装配加入通用结构化提问指令，回答保持模式与执行进度。 |
| 1.3.0 | 2026-09-14 | 提示词读取 Session 当前模式，Agent.mode 仅提供创建默认值。 |
| 1.2.0 | 2026-09-14 | 按模式和入口组合规划、审核及实施指令，TODO 仅跟踪 build 实施进度。 |
