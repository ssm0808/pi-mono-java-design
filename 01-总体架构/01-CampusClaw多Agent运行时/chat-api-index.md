# CampusClaw 接口统一管理

| 属性 | 值 |
|---|---|
| 文档版本 | 1.9.0 |
| 更新日期 | 2026-09-15 |
| 变更性质 | Session POST 按可选字段部分更新；前端单项调用，接口允许组合提交；组合写入及 mode 为 target-only |
| 唯一当前入口 | [当前九项接口](chat-api-review.html) |
| 页面渲染核对基线 | 设计仓 `1d9bf16381841e183d5bd12070e9df17feb7d478`；`接口契约/页面资源/catalog.js` 的 mount、`render_chat_http_v1.py` 的 render_static；仅调整页面阅读交互 |

结构化提问新增 agent.question / user.question_answer，复用 confirming 与原执行续跑；两事件、Schema、错误和恢复由 [AskUserQuestion](../06-CampusClaw计划模式/ask-user-question.md) 及共享事件源维护。该增量为 target-only，Session/元数据不增字段，Mate 公共投影独立集成。

## 1. 维护目标

一份清单决定当前接口，一套模型维护精确契约，HTML 由模型生成。Markdown 解释设计理由和实现差距；废止报文及整合过程通过 Git 历史追溯。

任务更新的 target-only 增量已登记到共享事件源：`agent.todo_updated` 直接返回完整 `todos`，无需前端识别工具名或解析工具结果。它与成功 ToolResult 的公共事件同源同事务保存，提交后发出；失败不更新清单。具体结构、源码基线与验收由 [TodoUpdate 主设计](../06-CampusClaw计划模式/todo-update.md) 唯一维护；Java 09b32d8e 的多事件 appendEntry 骨架可复用，新增工具与事件分支尚待实现。Mate 公共桥接需单独同步后开放。

## 2. 权威与状态

- [catalog.json](接口契约/catalog.json) 唯一决定当前九项 operation、顺序、精确源和关联设计。每个 method + path 只能出现一次，活动目录中的模型必须全部登记。
- [chat-api-review.html](chat-api-review.html) 是唯一当前人类接口页，从清单及精确模型生成，不手工编辑 HTML。
- 七项普通契约复用 `接口契约/common.json`；两个 Events 使用 `事件契约/common.json`。目录名称只是源组织方式，不代表两套并行的当前接口清单。各 operation 不复制到另一目录。
- `review` 与 `reviewState` 继续记录原有确认决定；清单中的说明只解释其适用边界，不替代或自动提升确认状态。B01～B15 已实际提交确认；两个 Events 目标契约已定稿，question 列表清空，数值校准另列。
- Markdown 记录理由、源码证据与未决项；FollowUp 只见[未来设计](chat-follow-up-future-design.md)，本期不启用。Mate 公共契约独立管理；公共命令与普通对话各自维护状态。

已确认的 eventId、无公共 entrySeq、data-only SSE、五输入、普通分页等不回退。
thinking、配置与 Skill 映射已联动更新，Builtin JSON 保持；公共 Mate 边界独立管理。
GetSession、创建及 Command 的 Session 投影同步 mode；更新入口和配置事件由当前精确源维护。
普通整数分页不继承旧不透明 page 的失效规则；不能用旧配置说明覆盖新历史接口。

共享命令清单的字段、排序和状态过滤由 Slash 模块维护，两跳等值与负向门禁防止派生契约漂移。

三个属性专用 PUT 和 mode-only PATCH 不再作为目标入口或兼容别名。当前只保留一个 updateSession；名称/模型/思考的 Slash Command 仍是命令入口。

### 2.1 单一维护职责

| 内容 | 唯一维护位置 | 其他文档的处理 |
|---|---|---|
| 当前接口报文、Header、错误与确认状态 | catalog 指定的 operation JSON 与 common | HTML 自动生成，Markdown 不保存平行报文 |
| Slash 轻量清单规则与共享结构 | [通用模块](../../04-命令与技能/00-Slash-Command通用模块/README.md) | HTTP 与 Mate 引用，不重复状态矩阵 |
| Builtin 业务、事务与实施验收 | [Builtin 专题](../../04-命令与技能/01-内置命令/README.md) | HTTP 仅保留传输边界及入口 |
| Help 元数据、缓存与安全展示 | [Help 专题](../../04-命令与技能/01-内置命令/Help-Agent使用指南/README.md) | 专项 HTML 从 Runtime Command 提取，不维护专项 JSON |
| Events 执行准入、有序追加、数据库中断与机制验收 | [Events 总体设计](chat-events-design.md) | 流设计只保留调用方可见的响应边界 |
| SSE 首帧、响应绑定、关闭、背压和恢复 | [流设计](chat-events-stream-design.md) | 总体文档引用；参数仍以精确模型为准 |
| 历史投影、分页与对账 | [历史设计](chat-events-history-design.md) | 流和总体文档不重复分页参数 |

必要的安全边界摘要可以保留，但不能在摘要中新增字段、规则或未决项的确认。
废止内容从 Git 追溯；不能继续生成旧报文，也不以“历史”标签保留第二套可调用说明。
Mate 公共 Events 和 FollowUp 未来专题各有独立职责，本次不退役。

## 3. 生成与校验

当前 Runtime 页面仅由 render_chat_api.py 生成，共享渲染函数仍供 Mate 使用。历史回归用 git show 读取固定提交，不恢复旧页面、模型或跳转占位文件。

修改精确模型或增删已获批准的接口后，统一执行：

```bash
python3 render_chat_api.py
python3 ../../04-命令与技能/01-内置命令/Help-Agent使用指南/render_help_review.py
python3 validate-chat-api.py --full
node test_chat_api.cjs
```

统一校验复用七项普通契约与两项 Events 的专项门禁，并增加：清单唯一性、活动源覆盖、
报文字节同步、旧文件及生成器不存在、全仓 Markdown/HTML 不链接已删除入口、
旧模型不得回流、当前链接有效性；回归测试验证重新生成只写当前页，并拒绝旧文件和链接回流。
Help 专项页由独立渲染入口从同一份 Runtime Command 源派生，统一门禁会拒绝过期产物；
不再同步或编辑第二份 Help JSON。Mate GET 调整后，在其专题目录运行生成器及专项校验。
交互测试需可用的 `jsdom`，
可通过 `JSDOM_MODULE` 指定模块路径；缺失依赖应明确报错，不跳过后宣称通过。
页面沿用既有视觉语言：只在主动展开时挂载一个接口，滚动不触发渲染，关闭再打开保留选项；
接口内部的请求头、参数、请求示例、契约说明和响应直接显示，无需逐栏展开；响应状态、语言和调用上下文继续使用标签切换。
禁用 JavaScript 或渲染失败时，原生接口内部的 details 默认展开。锚点直接定位对应操作。

## 4. 源码边界

统一 Session 更新的源码核对、相对旧基线的变化及 target-only 差距由[HTTP 主设计 §8.1](chat-http-v1-design.md#81-统一-session-更新源码核对)唯一维护。基线 Java 09b32d8e 已有独立模型/思考 PUT、名称 Command 及各自事务，没有四字段组合 POST。设计退役不代表实现仓路由已删除。

其他接口的固定源码证据继续由 [Events 设计](chat-events-design.md) 与 [FollowUp 设计](chat-follow-up-future-design.md)维护，不能将配置专项核对视为这些模块整体升级。旧入口清理核对基线为 Java `7b3769a5eabe2d131af3023631d7ad24e6d9a9e1`，相对 `dfb90cac4e233e09a0b8f047f7e9f4682f5ad238` 的下列文件无变化；该历史观察不延伸为最新主线缺陷。源码前缀为 `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/`。

| 历史源码 / 符号 | 已观察事实 |
|---|---|
| `web/RuntimeEventController.java` · submit/list | POST SSE / GET 历史路径存在，路径相同不证明已具备目标请求和事件联合类型 |
| `vo/UserEventRequestVO.java` · message/fileIds/rejectUnknownField | 旧 message/fileIds 请求形状；页面整理不等于完成实现迁移 |
| `web/RuntimeSessionControlController.java` · steer/followUp/abort | 该提交仍声明三个独立控制接口，设计退役与代码删除属于不同交付 |

统一 Session 更新与计划审核均已纳入当前精确源，包括 mode、五类用户输入、agent.plan、agent.todo_updated，以及 requested / planApproved 模式事件。[计划接口集成边界](../06-CampusClaw计划模式/interface-delta.md)仅维护理由与接入要求，不复制报文。

## 5. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.9.0 | 2026-09-15 | 增加结构化提问与回答的契约、原根续跑及历史恢复入口。 |
| 1.8.0 | 2026-09-15 | 登记五类用户输入及计划审核完整事件，统一展示制作与执行示例。 |
| 1.7.0 | 2026-09-15 | 纳入后端显式任务更新事件，SSE 与历史共用完整快照。 |
| 1.6.0 | 2026-09-14 | 按单一来源和当前生成流程整理维护说明，历史整合记录归 Git 追溯。 |
| 1.5.3 | 2026-09-14 | 接口展开后直接显示内部栏目和请求示例，静态回退内容同步默认展开。 |
| 1.5.2 | 2026-09-14 | 计划审核目标保留在执行内部，接口清单不增加 Session 待审字段。 |
| 1.5.1 | 2026-09-14 | 同步前端单项调用、接口允许组合提交的 Session 更新说明。 |
| 1.5.0 | 2026-09-14 | 当前清单收敛为九项，四类 Session 修改共用 POST。 |
| 1.4.0 | 2026-09-10 | 将独立 Session 重命名纳入当前十一项契约，明确它与 `/name` 共用服务且尚待实现。 |
| 1.3.0 | 2026-09-08 | 关闭 B01～B15 产品待决项；共享 contractSections 维护事件字段与码表，HTML 同步；实现校准独立记录。 |
| 1.2.0 | 2026-09-07 | 明确各专题唯一维护职责；清除 Mate 废止 POST 副本，Help 直接投影 Runtime，业务决定和未决状态不变。 |
| 1.1.0 | 2026-09-07 | 同步 GET 精简确认范围和防回退门禁，记录六个未合入分支的语义核查。 |
| 1.0.1 | 2026-09-07 | 按用户决定直接删除四个旧评审页及迁移占位生成逻辑；修复导航和历史测试引用，增加文件及链接防回流回归。 |
| 1.0.0 | 2026-09-07 | 统一当前清单、页面、生成和校验；旧页面仅导航、旧 Events 模型和报文移除；原确认状态不变。 |
