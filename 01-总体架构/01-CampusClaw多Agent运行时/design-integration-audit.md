# 已确认设计整合与分支核查

| 属性 | 值 |
|---|---|
| 文档版本 | 1.1.0 |
| 核查日期 | 2026-09-07 |
| 设计仓起点 | main / origin/main：2734a36b6f3cee2ebe16f1133d50ccb3eaaeb4e9；开始前已 fast-forward 同步 |
| 核查范围 | §1–§3 保留已完成的 GET 整合记录；§4 记录后续冗余清理，不修改产品代码 |
| 实现核对 | pi-mono-java 6f52fddc87a03c20916fc7b6ef1de87f6a7a8cf5；只核对 Command 发现层与 HTTP 发布边界 |
| 原始决定 | 任务「对齐 slash command 内置命令设计」，2026-09-03 用户要求实施 GET 字段减法；设计提交 ec5492aedb254d39f5b284eb36d80ad528236d80 |

§1–§3 是已在 `2c10a70ceb105d6ff10ba9bd5a3fbf760c6a10a9` 交付的历史核查结果，
不是当前接口清单；后续文件退役与派生流程以 §4 及[统一维护规则](chat-api-index.md#21-单一维护职责)为准。

## 1. GET 字段整合记录

根因不是缓存：ec5492a 已提交到独立分支，但未进入 main；随后主线继续变更 Help、Builtin POST 和
Events，沿用了旧 GET Descriptor。Help 专题当时明确暂不合并字段减法，用户本次现已要求合入。

本次在最新主线做语义整合，不整文件恢复旧分支，也不使用 ours merge 假装吸收全部旧内容。
因此 ec5492a 不会因本次提交成为 main 的祖先；已确认决定是否落地以本表、精确模型和门禁为准。

| 决定 | 当前落点 / 处理 |
|---|---|
| name/kind/description + 可选 input.hint/acceptsFiles | [Runtime GET 精确源](接口契约/操作/12-list-session-commands.json)；[Mate GET 投影](../../02-服务与接口/06-mate-service聊天命令API/接口契约/操作/01-list-chat-commands.json) 同形 |
| running 隐藏 Compact/Skill，Model/Thinking 仅查询，固定 Builtin 顺序 | 两组 idle/running 完整示例，删除双层 available 与建议值 |
| 完整 Agent 缓存前置、GET 缺失整体 503 | 不返回残缺 Builtin；不改变 POST Help 的既有 422 |
| Slash 未命中保留草稿 | 不回退普通消息；直接普通消息 API 仍不解析 Slash |
| 后续 Help 决定 | 保留无参 Agent 指南与四字段结果，Help Descriptor 无 input，不恢复 [command] |
| 后续 POST 决定 | 保留普通 JSON、Name 仅当前状态、无 commandId/通用生命周期；未修改 POST 精确模型 |
| 后续 Events / 文档治理 | 保留当前十项、eventId、无公共序号、data-only、普通分页及现有部分确认状态；不恢复退役控制接口或旧 Claw 页面 |
| Mate 公共边界 | 仅同步已确认 GET Descriptor；公共认证、bridge、错误映射仍待重审，旧公共 POST SSE 不恢复 |

精确产品规则、实现路径/符号和差异分类集中在[通用模块 §3.1–3.2](../../04-命令与技能/00-Slash-Command通用模块/README.md#31-get-轻量清单已确认)。
TUI 轻量提示的参考仍为 pi 5cd93f688aaab89dbb6dfa4aca535f21796ae185 的
packages/coding-agent/src/core/slash-commands.ts；未更新 Runtime 内核基线。

还发现一处同类同步遗漏：Help 专项页的请求头示例仍为占位符，未跟随 Runtime 的具体非生产测试值。
本次从 Runtime POST Command 同步全部 Header 示例与说明，并增加逐项等值及负向门禁；
不改变认证规则、POST 字段或 Help 结果。Help 专项改用仓库共享渲染器，避免技能默认模板重新强制占位符；不修改技能的全局规则。

## 2. 其他未合入分支

起点有六个去重后的非 main 祖先分支头。逐个检查 tip 相对父提交的主题变化，再与当前主线文本、
契约及版本记录比较；Git 未形成祖先关系不等于设计缺失。本次没有清理分支或工作树。

| 分支（均以 codex/ 开头） | 提交 | 核查结果 | 当前证据与处理 |
|---|---|---|---|
| reduce-command-get-contract | ec5492a | 确认的 GET 精简遗漏，本次整合 | 见第 1 节及新增两跳等值/负向门禁 |
| http-v1-campusclaw-directory | 769b819 | 核心决定已吸收，不需重复合并 | [HTTP §2.1](chat-http-v1-design.md#21-session-生命周期) 已有 agent/{agentId}/.campusclaw、HTTP 文件名边界，历史保留 1.31.0 |
| model-manager-internal-gateway-noauth | 78c01c9 | 已吸收并被后续 Chat 协议演进，不是遗漏 | [Provider 设计](../../02-服务与接口/03-模型管理Provider契约/README.md) 显式记录完整提交、ProviderAuth.none 与免应用认证；原 Responses create/cancel 已被后续 Chat 替代，不能恢复旧接口 |
| restore-command-global-class-view | 06bea56 | 已按新版 Help 重做并合入，不是遗漏 | main 的 c3ad422 / 04e13e3；[全局主图说明](../../04-命令与技能/00-Slash-Command通用模块/README.md#11-全局目标类图) 明确以 06bea56 为完整版骨架，本次不重排主图 |
| event-preview-terminology | da6e369 | 旧术语补丁未原样吸收；核心语义已被 v2 覆盖 | [流设计 §事件投影](chat-events-v2-stream-design.md) 已明确 preview 不持久化、不补发及 completed 权威；当前采用 agent.* + phase，不恢复旧事件名及旧预览类型全集 |
| code-layering-rules | b34ef95 | 另一个未合入专题，但不能证明已确认 | 分支中的 01-总体架构/06-CampusClaw代码分层与规则/README.md 明确“推荐目标，待评审”；还含已被替代的并行人员分工。本次只记录，不自动颁布新工程规则 |

补充核对了任务「制定 CampusClaw 内部整改方案」与「分析 event 接口设计稳定性」；其可读取内容是
分析建议，不能把助手提出的方案当作用户确认。上述分层专题若要合入，需先核对最新代码并处理后续
分工、Help 与 Events 的变化。已确认的 Java/分层通用规则仍以现行 AGENTS.md 为准。

## 3. 门禁与覆盖边界

- 两跳 GET 共享字段校验，逐状态精确比对响应；反例覆盖旧字段、候选值替代、空/错误 input、false 附件标记、排序、重复命令与状态过滤。
- 当前十项清单、旧 Claw 文件不存在、HTML 嵌入 JSON 与生成源同步，继续由统一校验入口检查。
- Help 十组测试保护无参、四字段结果与共享 Header 同步；POST 精确 JSON 源和 Events v2 源与本轮起点保持不变。
- Command HTTP 流图只调整 GET/POST 来源选择；Skill 图只解释共享 GET 与内部 Builtin 快路径。完整版全局类图不变。
- 本次是设计整合与有限范围核查，不是对所有历史会话、所有实现 PR 或全部产品行为的完整审计。
  除 GET 精简与 Help Header 投影遗漏外，未找到其他可以证实“已确认、仍有效、却缺失于当前主线”的接口决定；分层专题待评审事项不能归零。

### GET 整合时的验证结果

- `validate-chat-api.py --full`：通过；当前十项、14 个 PlantUML 主题、111 个 Events 负向反例、
  2 组退役测试、8 组清单测试、10 组 Help 测试、7 组 GET 精简测试。
- Mate `validate-chat-command-v1.py --full`：通过；两项历史/待评审边界未被自动提升为已发布。
- `validate-global-class-view.py`：6 组测试通过；全局主图与变更前字节相同。
- company-http-api-design 技能校验覆盖 Runtime、Mate Command、Slash 通用、Builtin/Help、Skill：
  Markdown、ASCII PlantUML、生成 SVG 的 XML、HTML 内联脚本与 diff 检查通过。
- 实际查看两个调整图的原尺寸及 840px 文档缩放图，文字与关系无相互遮挡；原尺寸入口位于各图下方。
  同一图源中未改语义的另外两个 SVG 仅随源注释元数据重新生成。
- Help 专项 DOM 核对两组 Header、全部响应及无 JS 展示值通过；HTML 字节与共享渲染结果一致。
- Runtime DOM 测试遍历十项、认证/响应/语言与无 JS 回退，通过；同时只展开一项，滚动 DOM 变更数为 0。
  这不是宿主浏览器的滚动帧率或 HTML 像素级验收，未据此宣称真实滚动性能已验证。
- Runtime/Mate POST 精确模型与 Events v2 模型未变；未运行 Java、数据库或端到端执行测试。
  原工作树中无关的虚拟线程 README 删除保持原样，不纳入提交。

## 4. 冗余清理（2026-09-07）

整理起点为设计仓 `2c10a70ceb105d6ff10ba9bd5a3fbf760c6a10a9`。
仅清理已废止内容和重复维护；沿用上述实现证据，不宣称重新核对产品源码或更新参考基线。

- 删除 Mate 旧 Command POST SSE JSON、专用 diagram.puml 和两张生成 SVG；
  专题仅保留 GET 投影及公共边界待决。没有新增公共执行契约，已删内容可从 Git 恢复。
- 删除 Help 手工 JSON 与正文报文副本，专项 HTML 直接提取 Runtime 操作 13；
  Header、参数、请求约束、结果及错误随源更新，新增防回退测试，不改变 Help 业务。
- HTTP 只维护传输边界，Command 业务及源码理由引用 Slash/Builtin/Help 专题；
  Events 总体、流与历史各自维护执行机制、响应生命周期、分页与对账，不复制整段规则。
- 从 HTTP 历史证据表移除已被替代的目标报文与分页规则；保留仍有价值的固定提交观察、
  版本记录和差距引用，不恢复旧接口。

验证通过：统一接口全量门禁（14 个图主题、111 个 Events 负向反例、2 组控制退役、
8 组清单、10 组 Help、7 组 GET、6 组新增文档维护测试）、Mate GET 专项门禁及 6 组全局类图检查；
company-http-api-design 的 Markdown、PlantUML/SVG、HTML 脚本和 diff 检查通过。
DOM 交互遍历当前十项、Help 的两组 Header/六个响应及 Mate GET 的七个响应，
无脚本回退与生成字节同步通过；当前总览滚动事件的 DOM 变更数为 0。
当前十项 operation 精确 JSON、Events v2 全部 JSON、catalog、Mate GET 模型和保留图源/图产物
与整理起点相同；变化仅为文档职责、派生流程、废止文件及展示版本。
未运行 Java、数据库或端到端执行测试；不将 DOM 检查当作宿主浏览器的像素或滚动帧率验收。
原工作树中无关的虚拟线程 README 删除仍保持原样，不纳入本任务提交。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.1.0 | 2026-09-07 | 区分整合历史与当前清理；记录废止文件删除、单源 Help、专题职责及验证边界。 |
| 1.0.0 | 2026-09-07 | 整合 GET 精简，记录六个未合入分支的语义状态及校验边界。 |
