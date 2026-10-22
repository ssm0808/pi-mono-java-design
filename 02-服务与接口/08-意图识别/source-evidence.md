# 意图识别重构源码证据与验证

| 属性 | 值 |
|---|---|
| 文档版本 / 更新日期 | 0.5.0 / 2026-10-22 |
| 源码核验日期 | 2026-10-22：仅核验 §9 的 Session、Child、提问与业务工具入口；§1～2 保留 2026-10-13 历史范围 |
| 当前上游 | `superheromeZzh/pi-mono-java`，默认分支 `main` |
| 当次 fetch 快照 | `3ade086fcbbe1f88b6729ef5f85d0e595d5b9421`；历史 `7edbcf42d52f6ef412fad74897cc0c7b39d61659` 不批量升级 |
| 本地维护位置 | `pi-mono-java-design/02-服务与接口/08-意图识别/`；本次仅本地保存，不提交、推送或创建 PR |
| 迁移来源 | `ssm0808/pi-mono-java@d870d0b617627dbb10991a5d2dead3119bc0f687` 中的已整理稿；仅迁移位置和修正引用，不重新分析或升级源码结论 |
| 历史文档基点 | `origin/main@1813c601101660a401e5e2004c5c00b8e3d7b75b`；上游实现未合并到历史文档分支 |
| 旧稿证据 | 旧稿 commit `8d184fb71cb6a92766d4c5ed5d9b627d5fae5bd3` 引用上述 fork 基点，仅作历史证据 |

2026-10-13 先通过 `gh repo view` 确认上游默认分支，再在隔离工作树 `git fetch target main` 和 `git fetch origin main codex/intent-recognition-refactor`，按固定提交读取源码。不将本地工作树、旧聊天摘录或设计文档里的历史状态冒充最新实现。该次仅更新与意图路由、子调用及补充协议有关的证据，不做整个运行时评审；下文源码结论保留该核验日期，不视为 2026-10-19 最新实现结论。

<a id="current-behavior"></a>
## 1. 2026-10-13 源码观察与待实现差距

以下路径均相对仓库根目录；链接固定到本次上游提交。`C` 表示 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`，表内路径与符号组合定位代码。

| 分类 | 路径与符号 | 实际观察及设计影响 |
|---|---|---|
| 已实现 | [C/tool/agent/BoundAgentTool.java](https://github.com/superheromeZzh/pi-mono-java/blob/7edbcf42d52f6ef412fad74897cc0c7b39d61659/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/agent/BoundAgentTool.java)，`parameters/executionMode/execute` | `Agent` 参数为 `agentName/task`，拒绝额外字段；候选来自直接绑定；`SEQUENTIAL`。不能说已经具备并行子任务或公开 subTaskId 协议 |
| 已实现 | [C/tool/agent/SubagentExecutionService.java](https://github.com/superheromeZzh/pi-mono-java/blob/7edbcf42d52f6ef412fad74897cc0c7b39d61659/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/agent/SubagentExecutionService.java)，`execute/runChild/extractFinalAnswer/projectProgress` | 校验深度、直接绑定、启用、自引用及环；按 CHILD_AGENT 创建 Session，结束关闭，传播取消；返回最终非空 Assistant 文本，投影工具起止进度。结构化业务待补充结果待实现 |
| 已实现 | [C/tool/question/AskUserQuestionTool.java](https://github.com/superheromeZzh/pi-mono-java/blob/7edbcf42d52f6ef412fad74897cc0c7b39d61659/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/question/AskUserQuestionTool.java)，`prepare/execute` | 准备并校验结构化问题，通过 `UserQuestionPort.await` 等答案；该机制不是“子调用结束后另开调用” |
| 已实现 | [C/runtimeapi/runtime/RuntimePendingInteraction.java](https://github.com/superheromeZzh/pi-mono-java/blob/7edbcf42d52f6ef412fad74897cc0c7b39d61659/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/runtime/RuntimePendingInteraction.java)，`beginQuestion/awaitQuestion/claimQuestion/requireAvailable` | 保存当前执行唯一交互的 kind、toolCallId、targetEventId、Future；校验固定执行身份，等待并清理。不能用一份当前等待槽代表一个聊天下的多个独立业务等待项 |
| 已实现 | [C/runtimeapi/event/RuntimeUserQuestionService.java](https://github.com/superheromeZzh/pi-mono-java/blob/7edbcf42d52f6ef412fad74897cc0c7b39d61659/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeUserQuestionService.java)，`normalizeCurrent` | 读取已提交问题事件并校验整批答案；包含结构化问题与业务确认负载判断。不能把无结构的“请补充”文本当成可信等待记录 |
| 已实现 | [C/runtimeapi/vo/UserQuestionAnswerEventRequestVO.java](https://github.com/superheromeZzh/pi-mono-java/blob/7edbcf42d52f6ef412fad74897cc0c7b39d61659/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/vo/UserQuestionAnswerEventRequestVO.java)，`targetEventId/answers/rejectUnknownField` | 使用目标问题事件和批量答案，拒绝未知字段；不是新增业务 interactionId 接口 |
| 待实现 | `C/tool/agent/` 与 `C/runtimeapi/` | 定向检索 `UserInputRequired/subTaskId/interactionId` 无命中；结合上述完整类读取，当前检查范围未见本设计的业务子任务接续协议。仅限此范围，不断言整个系统无任何同类能力 |
| 未核验 | CampusMateService 源码 | 旧状态机、中心权限和路由现状来自用户说明，未把另一个产品模块当成该服务源码 |
| 未核验 | 通用工具 Pipeline 的完整链路、持久化恢复和部署性能 | 本次没有逐项重验；正文中的工具顺序是项目目标约束，不能当成本次已证明的所有实现行为 |

<a id="current-api"></a>
## 2. 当前接口与历史材料

完整读取的当前代码：

- [RuntimeEventController#submit/list](https://github.com/superheromeZzh/pi-mono-java/blob/7edbcf42d52f6ef412fad74897cc0c7b39d61659/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/web/RuntimeEventController.java)：`BASE_PATH + /sessions/{sessionId}/events` 上的 POST/GET，输入为 `SubmitSessionEventRequestVO`，POST 返回 SSE。
- [RuntimeEventService#submit/submitQuestionAnswer](https://github.com/superheromeZzh/pi-mono-java/blob/7edbcf42d52f6ef412fad74897cc0c7b39d61659/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventService.java)：当前分派 message、interrupt、tool confirmation、plan confirmation、question answer 五种请求；问题答案先受理再通过 dispatcher 交给原等待目标。

已读取 [Session Events 联合请求边界](https://github.com/superheromeZzh/pi-mono-java/blob/7edbcf42d52f6ef412fad74897cc0c7b39d61659/docs/designs/runtime-event-request/README.md) 与 [统一 HTTP 接入](https://github.com/superheromeZzh/pi-mono-java/blob/7edbcf42d52f6ef412fad74897cc0c7b39d61659/docs/designs/runtime-events-http/README.md)。两者保留各自切片时期的三类事件等描述，当前类型数以本次读取的 Service 为准。既有文档记载的测试是历史测试，不算本次执行；不把旧稿的 `UserEventRequestVO(message/fileIds)`、`/steers` 和 `/follow-ups` 当作当前接续方案依据。

本次还读取文档分支的 `docs/designs/agent-delegation.md`、`tool-system-v2.md` 和 `docs/decisions/0030-intent-routing-and-task-continuation.html`，用于理解旧稿来源；没有据此升级未读模块的实现结论。不同仓库的 ADR 编号不具有跨仓唯一性，本文 ADR-0030 仅指交付 fork 内的现有文件。

本设计不以 pi/Codex/OpenCode 为实现基线，不复制这些项目的能力结论；因此没有将其历史 SHA 冒充本次核验。Jev 是待评测候选，本次仅整理业务校准方法，未核验其最新官方产品能力。

## 3. 业务来源与推导边界

原始图路径：`/Users/simon/Library/Mobile Documents/iCloud~md~obsidian/Documents/Simon/Simon/SimonFile/Excalidraw/原意图识别框架.excalidraw.md`。前版已据原图与用户回答记录旧状态机行为，本次从前版及可见对话续接，不声称重新读取了原图。

已确认约束：两侧 Pod 分层；agentId 为业务 Agent；MainAgent 不任意 A2A 调用；无 SubAgent 池、临时执行；业务补充不恢复旧工具栈；knowledge 与 UNK 分离。当前采用第一阶段统一 MainAgent、第二阶段增加快速直达；原任务接续和确认不得被快路径截走。上下文推送/拉取、精确标识与表结构、跨父任务协调和发布规则仍待专项设计，不把历史快分类研究当作第一阶段。

## 4. 模板整理映射

下表保留 0.2～0.4 版整理记录，不是当前章节导航；当前结构以主设计 0.5.0 为准。

| 前版内容 | 当前位置 |
|---|---|
| 设计结论、原系统、重构动因 | 主文 §1～2 |
| 架构、Session 关联与标识 | 主文 §3.1～3.2 |
| 快路径、Jev 校准、消息归属 | 主文 §3.3～3.4 |
| 多意图、SubAgent 补充与生命周期 | 主文 §3.7～3.8 |
| 展示、JSON 示例 | 主文 §3.6、§4 与 contracts.md |
| 源码差距、边界、DFX | 本文件及主文 §5 |
| 阶段建议、验收、待确认项 | 主文评审 Todo 与 §6 |

未新增部署图，因为本次没有确定新的进程或服务部署方案。§3.4 保留决策流程图而非额外编造跨模型服务时序，待 Jev 部署和调用方式冻结后再补；这是针对该主题的模板调整。

<a id="validation"></a>
## 5. 原稿验证

| 检查 | 结果与边界 |
|---|---|
| 生成 | PlantUML 1.2025.2、JDK 21 执行 `plantuml -tsvg diagram.puml` 成功，10 个稳定命名块生成 10 张 SVG；类图与状态图使用内置 Smetana，不依赖 Graphviz |
| 格式与结构 | 3 个 Markdown 均无 Mermaid；PlantUML 为有效 UTF-8，10 张 SVG 为有效 XML；2 个 JSON 示例可解析 |
| 链接 | 56 个本地链接及锚点通过检查，10 个 PlantUML 行锚点均落在对应 `@startuml`；远端源码链接由实际读取的固定提交与路径构建，未逐个发起 HTTP 验证 |
| 图源同步 | 在交付目录再次生成，10 张 SVG 的 SHA-256 均与生成前一致 |
| 图面 | 10 张图分别在原尺寸及 900px 文档宽度转换预览并逐图检查，中文无缺字，调用、返回及阶段编号一致；SVG 自身声明白色背景，PNG 预览使用白底 |
| 仓库检查 | JDK 21 下 `./mvnw -q -N spotless:apply spotless:check` 与 `git diff --check` 通过；根项目检查不代表所有 Java 模块编译或测试 |
| 未执行 | Java 业务测试、两侧联调、跨 Pod 故障与性能测试；本次没有修改产品实现，无需同步企业镜像 |

以上验证发生于原稿整理阶段，不冒充设计仓本次运行结果。迁移时另行检查相对链接、图源与 SVG，业务设计、源码核验范围和对比结论不变。设计中的验收用例仍待执行。

## 6. 本地迁移验证

2026-10-13 将正文、契约、证据、PlantUML 和 10 张 SVG 保存到本专题，更新仓库及服务导航，并通过现有脚本生成设计图索引。未执行 commit、push 或 PR 操作，未改动此前已创建的 Draft PR。

- 56 个本地链接和锚点、2 个 JSON 示例及 10 张 SVG XML 校验通过。
- `plantuml -tsvg diagram.puml` 成功；除新增证据注释对应的源行元数据外，SVG 图面与前次已检查的版本一致。
- `git diff --check` 通过；`scripts/render-diagram-index.py` 成功，索引共 149 张图。
- 全仓 `scripts/check-diagrams.py --render` 未通过，报告 142 项问题，涉及无关的模板占位链接及其他专题 SVG 与本机重新生成的差异；本专题没有错误。不以本专题通过声称全仓通过，也未改写其他专题。

<a id="context-flow-validation"></a>
## 7. 上下文流程图验证

2026-10-19 在主设计 §2.4 增加 `intent_context_routing_flow`，用 01～10 及 A/B 分支说明消息接入、归属、最小上下文、快速分类、可信路由和结果展示。补充逐步输入输出、园区示例及待执行验收用例；细化方案待评审，不新增公共接口或产品实现。

本次只读取并细化现有设计，不分析源码或升级基线；上下游职责、MainAgent 约束和已有基线对比结论不变。源码证据仍固定为 2026-10-13 的 `7edbcf42d52f6ef412fad74897cc0c7b39d61659`。未把新增流程标成已实现，未重新核验 Jev 产品能力。

| 检查 | 结果与边界 |
|---|---|
| 图源生成 | PlantUML 1.2025.2 / JDK 21 执行 `plantuml -tsvg diagram.puml` 成功；11 个命名块对应 11 张 SVG |
| 专题结构与链接 | 专题检查 0 错误；63 个本地链接及锚点、2 个 JSON 示例通过；11 张 SVG 为有效 XML，无 Mermaid，PlantUML 为 UTF-8 |
| 图源同步与范围 | 全仓重生成比较未报告本专题差异；原有 10 张 SVG、原有命名块及业务契约保持不变 |
| 图面 | 实际查看新增图的 797×2057 原尺寸与 900px 文档宽度预览，中文、判断条件、分支和合流箭头无缺字或重叠 |
| 导航与空白 | 更新两级导航；图索引生成成功，共 150 张图；`git diff --check` 通过，未跟踪专题的对照空白检查无错误输出 |
| 全仓边界 | `scripts/check-diagrams.py --render` 检查 39 个专题，报告 139 项其他专题 SVG 与本机重新生成的差异；本专题无错误，不声称全仓通过，未重写其他专题 |
| 未执行 | Java 业务测试、模型准确率评测、两侧联调及容量测试；这次仅本地保存，未 commit、push 或操作 PR |

<a id="scenario-flows-validation"></a>
## 8. 八类场景流程验证

2026-10-22 根据用户确认的中心职责收敛，按八类场景新增 `intent_type_new_task`、`intent_type_continue`、`intent_type_task_control`、`intent_type_attribution`、`intent_type_task_structure`、`intent_type_mixed_input`、`intent_type_boundary`、`intent_type_general`，覆盖19个场景。主设计及关联旧图同步采用一次带上下文的快速判断、原处理方解释回复、MainAgent 独立路由和 UNK 拒答。

这些是 CampusMateService 与 CampusClaw 之间的产品约束和架构分工设计，不是对最新实现的观察。本次没有分析源码、重新 fetch、核验 Jev 产品或更新外部 Agent 基线；保留2026-10-13的历史提交、路径与符号。旧能力工具桥接、独立状态机实例和跨服务交互仍待实现；跨父任务并发接续及精确协议仍待评审。

| 检查 | 结果与边界 |
|---|---|
| 场景覆盖 | 19行编号连续、6列完整、8类齐全；复杂与混合场景不再输出 UNK；接续不要求回复子类型 |
| 图源生成 | PlantUML 1.2025.2 / JDK 21 执行 `plantuml -tsvg diagram.puml` 成功；19个稳定命名块对应19张SVG，新增8张 |
| 结构与引用 | 100个本地链接及锚点、2个JSON示例通过；PlantUML为UTF-8，19张SVG均为有效XML，专题Markdown无Mermaid |
| 生成同步 | 现有脚本专题检查0错误、0复杂度提示；再次生成与保存的SVG一致；5张图的可见元素与前版一致，契约文件未变 |
| 图面 | 逐图检查8张新图和6张内容变化旧图的原尺寸及900px文档宽度，中文和分支可读；中心在上游、Claw在下游，旧能力回调注明中心位置，返回路径可辨认 |
| 导航与空白 | 两级导航已更新；图索引生成成功，共158张图；`git diff --check`通过，专题逐行无尾随空白 |
| 全仓边界 | 全仓检查39个专题、158个命名块，报告其他专题139项SVG重生成差异；本专题无错误，未改写其他专题，不能声称全仓通过 |
| 未执行 | 模型准确率、业务执行、跨Pod联调、故障及性能测试；本次仅本地保存，未commit、push或操作PR |

<a id="phase-source-20261022"></a>
## 9. 两阶段重构的源码核验与图源范围

2026-10-22 使用 `git ls-remote --symref` 确认上游默认分支为 `main`，在隔离 bare 仓库 fetch 该分支，按完整提交 `3ade086fcbbe1f88b6729ef5f85d0e595d5b9421` 读取下列完整文件。没有切换、合并、暂存或覆盖用户实现工作树；这是当次源码快照，不是稳定发布认证。只升级下表范围，§1～2 和其他模块的旧提交仍是历史证据。

路径前缀 `C` 为 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/`。

| 路径与关键符号 | 已观察实现 | 对当前设计的影响 |
|---|---|---|
| [C/session/AgentSessionFactory.java](https://github.com/superheromeZzh/pi-mono-java/blob/3ade086fcbbe1f88b6729ef5f85d0e595d5b9421/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/session/AgentSessionFactory.java)，`create/createMateState/configureAgent` | 按 entryPoint 装配工具，创建隔离 Agent Session，带入凭据和安全上下文 | Main/Child 可复用内核；不证明业务任务管理已完成 |
| [C/tool/agent/BoundAgentTool.java](https://github.com/superheromeZzh/pi-mono-java/blob/3ade086fcbbe1f88b6729ef5f85d0e595d5b9421/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/agent/BoundAgentTool.java)，`parameters/executionMode/execute` | 输入 `agentName/task`，直接绑定枚举、拒绝额外字段、`SEQUENTIAL` | 不改写成已有 `invoke_agent(agentId, subTaskId)` API，不承诺并行或任意 A2A |
| [C/tool/agent/SubagentExecutionService.java](https://github.com/superheromeZzh/pi-mono-java/blob/3ade086fcbbe1f88b6729ef5f85d0e595d5b9421/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/agent/SubagentExecutionService.java)，`execute/runChild/extractFinalAnswer/projectProgress` | 深度上限1，校验绑定/启用/自引用/环；每次创建 Child Session、结束关闭，传播取消；返回最后非空 Assistant 文本，投影工具起止 | 子调用基础可复用；结构化业务等待、父任务接续和分项业务结果在该实现中尚不具备，相关增强待实现 |
| [C/tool/question/AskUserQuestionTool.java](https://github.com/superheromeZzh/pi-mono-java/blob/3ade086fcbbe1f88b6729ef5f85d0e595d5b9421/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/question/AskUserQuestionTool.java)，`prepare/interactionMode/execute` | 准备和校验结构化问题，作为最后交互调用，经 `UserQuestionPort.await` 等待原执行答案 | 可复用交互能力，但不能等价成子调用结束后业务新调用式接续 |
| [C/runtimeapi/event/RuntimeEventService.java](https://github.com/superheromeZzh/pi-mono-java/blob/3ade086fcbbe1f88b6729ef5f85d0e595d5b9421/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/event/RuntimeEventService.java)，`submit/submitQuestionAnswer` | 分派 message、interrupt、tool confirmation、plan confirmation、question answer；结构化答案受理后定向 dispatcher | 明确已有控制不必再次做语义分类；未据此审计事务、跨 Pod 恢复和多等待并发 |
| [C/tool/mate/CallTool.java](https://github.com/superheromeZzh/pi-mono-java/blob/3ade086fcbbe1f88b6729ef5f85d0e595d5b9421/modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/tool/mate/CallTool.java)，`prepare/execute/executionMode` | 受管 Skill 工具入口，参数为 `tool/args`，准备委托 `MateToolExecutor.prepareSkill`，串行执行 | 旧能力可考虑纳入受控工具边界；不把该入口当成旧 Agent 桥接已经实现，也未证明完整安全链顺序 |

**未核验范围。** CampusMateService 的完整源码、`MateToolExecutor` 与完整 Pipeline/Host 实现、Session 数据库事务、当前并发准入、企业镜像、真实部署与模型性能均未重新审计。两阶段路由、跨服务归属、业务等待和桥接是产品约束/架构变更，待实现；中心具体差距仍待其源码核验。没有新比较 pi、Codex、OpenCode 或其他 Agent 基线，也未新核验 Jev 产品资料。

**图源适用范围。** 当前主设计使用 `intent_phase_one_flow`、`intent_phase_two_flow`、`intent_phase_architecture`、`intent_phase_one_sequence`。更早 `intent_type_*` 与其余前置快速分类图保留为对应版本的研究资料，不作为第一阶段规则；`intent_option_*` 和 `intent_energy_*` 继续用于选型与示例比较。既有24个块及SVG保留原样，不把旧图升级为当前已观察实现。

<a id="phase-redesign-validation"></a>
## 10. 两阶段设计验证

主设计0.5.0按先方案一、再方案二重写，场景表0.4.0按两阶段对照，比较稿0.5.0保留选型依据。新增四个 `intent_phase_*` 块及SVG，更新根/服务导航、A17架构条目与图索引；未改产品实现和业务契约。

模板按本次范围调整：用两阶段流程帮助读者理解整体方案，保留业务用例、服务级正常时序、关键决策、系统用例和九段评审结构；数据部分只描述逻辑责任及生命周期，精确协议、DDL和上下文传输方式后续专项设计，不补造实现细节或审批结论。

| 检查 | 结果与边界 |
|---|---|
| 生成与同步 | PlantUML 1.2025.2 / JDK21执行 `plantuml -tsvg diagram.puml`成功；专题28个稳定命名块、28张SVG，隔离重新生成与保存版本逐字节一致 |
| 链接与格式 | 专题检查0错误、0范围提示；73个本地链接及锚点、2个JSON示例通过；PlantUML为UTF-8，28张SVG均为有效XML，无Mermaid和尾随空白 |
| 场景与模板 | 19行编号连续、6列完整，对照两阶段的正常处理与约束；主设计包含评审及概述到其他补充的九段结构，实施只分第一、第二阶段 |
| 保留范围 | 原24张SVG、原24个PlantUML源块及 `contracts.md`逐字节不变；未变更已有外部框架证据归属 |
| 图面 | 实际检查四张新图原尺寸及900px文档宽度；流程图866×1377、965×1385，职责图1201×1625，时序图1046×1131；中文、分支、服务边界、调用和返回可读，无文字越界 |
| 导航与空白 | 图索引更新为167张图；`git diff --check`与专题独立空白检查通过；本地链接保持可访问 |
| 全仓边界 | `scripts/check-diagrams.py --render`检查39个专题、167个命名块、66张时序图，仍有其他专题139项SVG重生成差异和2个既有范围提示；本专题0错误，未改写其他专题SVG，不声称全仓通过 |
| 未执行 | Java业务测试、中文模型准确率与阈值校准、两侧联调、故障及性能测试；不据此声称两阶段业务能力已实现 |

本次只本地保存，未提交、推送、创建或修改PR，未切换实现/设计仓库分支。源码更新使用隔离bare仓库，不合并到用户工作树。
