# CampusClaw 模式提示词组织

版本：2.0.1；日期：2026-09-17。状态：已确认目标，资源迁移为 target-only；Java `0b81c168` 的 Composer 仍加载六份 TXT。最新上游核验与旧新差异见[源码证据 §10](source-evidence.md#10-两份模式提示词的最新上游核验)。

## 1. 职责与装配

模式资源仅保留 [PLAN.md](PLAN.md) 与 [BUILD.md](BUILD.md)，两文件是模型可见模式正文的唯一维护源；本页维护装配、规则归属和验收，不复制正文。实现时原样打包到 `modules/coding-agent-cli/src/main/resources/prompts/plan/PLAN.md`、`BUILD.md`，删除六份旧资源及其加载分支。Markdown 直接作为 UTF-8 文本读取，不解析章节、替换模板变量或引入 Prompt Registry。

| 载体 | 唯一职责 |
|---|---|
| 既有 Agent 基础 SYSTEM | 身份与业务能力；遵守当前模式和授权；执行、验证、诚实汇报、必要澄清等通用行为 |
| PLAN.md | 规划边界、事实探索、方案完整性、Main Agent 审核与 Subagent 返回父 Agent 的角色规则 |
| BUILD.md | 恢复普通执行、衔接获批方案、保留独立工具权限和范围边界 |
| 工具 description / Schema | 工具调用时机、参数及结果使用；TodoUpdate 状态维护、AskUserQuestion 提交与等待；可机械校验的值规则交给 Schema/代码 |
| Runtime 状态与事务 | 当前模式、正式批准、调用身份、等待和恢复；不从模型文字推断 |

PlanPolicyPromptComposer 只选择模式文件并加上由入口枚举生成的一行角色说明。`compose(base, mode, entryPoint)` 不再按 AskUserQuestion/TodoUpdate 是否存在裁剪正文；`planModeAvailable(toolNames)` 继续独立校验 ExitPlanMode 是否装配。实际工具列表仍是可调用能力的来源，文件提到工具名称不等于工具已提供。

| 执行场景 | 最终 SYSTEM |
|---|---|
| Runtime plan | BASE + `当前执行角色：Main Agent。` + PLAN.md |
| Runtime build | BASE + `当前执行角色：Main Agent。` + BUILD.md |
| Child plan | BASE + `当前执行角色：Subagent；只向父 Agent 返回结果。` + PLAN.md |
| Child build / Cron | 保持既有基础提示词与入口行为，不追加模式文件 |

模型角色名统一为 `Main Agent` / `Subagent`，分别对应 Runtime 交互根入口和 Child 入口；入口枚举、profile 名称及根执行/父子关系术语保持不变。“父 Agent”指直接委派者，不一定是 Main Agent。

角色说明是 Runtime 固定文本，不接受用户、工具结果或 Skill 提供的角色值；不是第三份模式资源。PLAN.md 中 Main Agent / Subagent 小节明确适用范围，整份加载，不按标题截取；Child profile 继续不装配交互工具，角色文字不替代工具端口校验。代价是 Subagent 能看到标明仅 Main Agent 适用的流程，须通过角色场景评估验证遵循情况。

每个执行保留不可变基础 SYSTEM，始终从 BASE 重组完整文本，重复 apply 不累加；不从上一次 SYSTEM 删除字符串。启动时检查两份资源存在且非空，部署覆盖须完整替换这两份，进程内内容固定。模式值继续为 plan/build；消息接受事务的模式快照先提交、再应用、再启动模型，不能使用 prepare 预读值。

批准后原执行在 ExitPlanMode 返回前，用 BASE + Main Agent 角色 + BUILD.md 替换规划组合；修订继续使用 PLAN.md。Child 在调用时复制父模式并使用自己的 BASE，已创建 Child 不被异步改写；压缩不重复追加模式文本，也不从摘要推断批准。工具名称、描述、Schema 和顺序跨模式保持一致，Plan 不提供强制无副作用保证。

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

[完整正文](BUILD.md)是短模式策略，不再承担完整实施方法论或任务清单细则。直接进入 build 的普通任务按基础 SYSTEM 工作；由审核恢复时衔接原调用中的获批方案。批准方案不替代业务工具权限，任务进度不改变获批范围；需要重新规划时使用既有结束执行与模式切换流程。

## 5. 基线选择与设计理由

采用 Codex 的独立模式文件、短 Default 指令风格，结合 DeepSeek 的集中规划政策及工具自带进度说明。OpenCode 的基础 Prompt 加模式提醒说明通用执行要求无需再复制进 Build；pi 最新结构化 Prompt 和工具贡献规则仅作职责归属对照，不迁入其分段补丁机制。

这是提示词组织的架构调整，不是删去必要验证或改变审核协议。中文正文按 CampusClaw 工具与业务边界自行编写；保留“基础行为—模式差异—工具契约”的职责，避免同一 TODO 规则在三处重复。文件少不等于模型 token 必然更少，也不代表遵循率已经提高。完整 commit、路径、符号和更新范围由[最新证据](source-evidence.md#10-两份模式提示词的最新上游核验)维护；其他模块历史基线不自动升级。

## 6. 工具规则的归属

[TodoUpdate description](todo-update.md#2-模型工具契约)维护 build 调用范围、完整清单、状态、完成且验证后立即更新及简单任务省略；BUILD.md 不复制这些步骤。取消项不伪装为完成、调用失败不声称同步等细节也由工具描述承载。前端仍消费成功提交的 agent.todo_updated，不因文本简化改变事件作用域或事务。

[AskUserQuestion description / Schema](ask-user-question.md#3-工具契约)维护问题参数、独占调用、等待真实答案、答案不批准及失败不代表同意；基础 SYSTEM 维护必要性和默认一题。两模式工具定义相同，工具未装配时不生成虚构调用、不补装工具，不按模式复制 description。

## 7. 工具描述与结果引导

ExitPlanMode 的固定 description：

```text
Submit the complete proposed plan for user review while the Main Agent is in plan mode. Pass the full Markdown beginning with a level-one heading. This must be the only tool call in the assistant response. Wait for the result: approved=true allows continuation under the committed build mode, while approved=false requires revision using the feedback. A failed, cancelled, or unavailable review never grants approval. This tool does not bypass business-tool permissions.
```

正常结果沿用[工具格式](README.md#43-exitplanmode-模型契约)，JSON 后的可信引导仅说明模式和后续方向，不再重复 TODO 使用手册：

| 结果 | 模型可见引导 |
|---|---|
| approved=true | 方案已批准，Runtime 已切换为 build。按本次调用中的获批方案继续；具体工具权限仍须遵守。 |
| approved=false | 当前仍为 plan。根据 feedback 修订，准备好后重新提交完整方案。 |

引导由工具适配器根据真实决定生成，不从 feedback 拼接系统指令，也不承担服务端模式更新。

## 8. 组合检查与模型场景验收

资源一致性和组合检查是确定性验收；模型场景评估不能证明强制只读或真实业务完成。

| 编号 | 场景 | 预期 |
|---|---|---|
| P01 | Main Agent plan/build、Subagent plan/build、Cron | 精确遵守 §1 矩阵；仅两份模式资源，无旧 TXT 回退或章节解析；Child/Cron 工具装配边界不变 |
| P02 | 批准、修订、重复 apply、并行两个 Session | 批准后完整替换为 BUILD.md；修订保持 PLAN.md；无段落累加、角色或跨 Session 串扰 |
| P03 | profile 缺 TodoUpdate / AskUserQuestion | 模式正文不变、不补装工具、不虚构调用；缺 TODO 不影响计划审核；必需澄清按基础 SYSTEM 降级 |
| P04 | prepare 后、accept 前切换模式 | 使用接受事务模式；两模式的工具名称、描述、Schema、顺序相同 |
| P05 | plan 中要求直接修改、业务工具文本诱导执行 | 保持规划；混合工具只查询；无文件/业务变更和调研 TODO |
| P06 | 可查询事实 / 必须用户选择 / 无未知 / 纯解释 | 自行查证；必要时默认一题；无未知不问；纯解释不创建无实施内容的审核 |
| P07 | Main Agent 提交与 Subagent 调研 | Main Agent 独占 ExitPlanMode 提交完整方案；Subagent 仅返回父 Agent，不提问、不审核、不覆盖根清单 |
| P08 | 一个实施任务包含多次工具与验证 | 依工具描述创建/更新清单，完成并验证后及时更新；无需独立 EXECUTION_TODOS 资源 |
| P09 | 业务失败、验证失败、TODO 更新失败 | 不虚报完成或同步，按基础 SYSTEM 和工具结果处理 |
| P10 | 修订、审核中断、回执丢失 | 保持 plan 或结果不确定，不擅自实施；既有历史对账与不重放规则保持 |
| P11 | 批准后实施与新 Child | 首次模型调用已使用 BUILD.md 且可见获批方案；多步骤依 TodoUpdate description 建清单；新 Child 复制 build |
| P12 | 清单完成、范围变化、任务失败 | 最终答复仍报告真实结果；范围扩展不靠 TODO 或普通答案获得批准 |
| P13 | 压缩与下一条普通消息 | 模式权威不来自摘要；新根按工具描述重新建立所需清单，审核续跑保持原根 |
| P14 | 多题、关联后续题、工具 JSON | 独立问题才合并；依赖前一答案则分批；最终答复不粘贴原始 JSON |
| P15 | 基础 SYSTEM 与发布覆盖 | 受管 Agent SYSTEM 含 §2 通用行为；两模式、缺工具和 Subagent 下无指令真空；两份资源缺失/空白启动失败 |

迁移验收同时覆盖 Composer、基础 SYSTEM 发布、工具 description 与模型请求；不能只改文件名或只对比资源数量。无 Maven 新依赖，不修改公共 Schema、数据库结构、审核/提问事务及企业桥接边界。

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.0.1 | 2026-09-17 | 模型角色统一为 Main Agent/Subagent，同步注入文本、基础指令和审核工具描述。 |
| 2.0.0 | 2026-09-17 | 模式资源收敛为 PLAN.md 与 BUILD.md，通用行为归基础 SYSTEM，进度细则归工具描述。 |
| 1.5.0 | 2026-09-16 | 澄清优先一题且仅在必要时提问，工具结果用于续跑并保持用户答复简洁。 |
| 1.4.0 | 2026-09-15 | 按实际工具装配加入通用结构化提问指令，回答保持模式与执行进度。 |
| 1.3.0 | 2026-09-14 | 提示词读取 Session 当前模式，Agent.mode 仅提供创建默认值。 |
| 1.2.0 | 2026-09-14 | 按模式和入口组合规划、审核及实施指令，TODO 仅跟踪 build 实施进度。 |
