# CampusClaw 接口统一管理

| 属性 | 值 |
|---|---|
| 文档版本 | 1.4.0 |
| 更新日期 | 2026-09-10 |
| 设计仓变更前基线 | `2c10a70ceb105d6ff10ba9bd5a3fbf760c6a10a9`（1.2.0 清理起点） |
| 变更性质 | 增加已确认的独立 Session 重命名目标契约；不声称 Runtime 已实现该入口 |
| 唯一当前入口 | [当前十一项接口](chat-api-review.html) |

## 1. 为什么统一

原入口把 v1 的旧 Events 报文与 Session Events 新方案分别完整展示，根导航仍指向 v1。
仅加“迁移基线”提示，仍容易把旧字段当作当前契约；聊天中的总览又没有纳入设计仓。
清单和总览已纳入同一生成、校验和版本控制流程。用户进一步明确：废弃文档直接删除，
不保留迁移说明页、跳转页或占位文件；历史版本只从 Git 追溯。

## 2. 权威与状态

- [catalog.json](接口契约/catalog.json) 唯一决定当前十一项 operation、顺序、精确源和关联设计。每个 method + path 只能出现一次，活动目录中的模型必须全部登记。
- [chat-api-review.html](chat-api-review.html) 是唯一当前人类接口页，从清单及精确模型生成，不手工编辑 HTML。
- 九项普通契约复用 `接口契约/common.json`；两个 Events 使用 `事件契约/common.json`。目录名称只是源组织方式，不代表两套并行的当前接口清单。各 operation 不复制到另一目录。
- `review` 与 `reviewState` 继续记录原有确认决定；清单中的说明只解释其适用边界，不替代或自动提升确认状态。B01～B15 已实际提交确认；两个 Events 目标契约已定稿，question 列表清空，数值校准另列。
- Markdown 记录理由、源码证据与未决项；FollowUp 只见[未来设计](chat-follow-up-future-design.md)，本期不启用。Mate 公共契约独立管理；本轮仅清除其已废止 Command POST 内容，保留 GET 投影及待评审公共边界。

已确认的 eventId、无公共 entrySeq、data-only SSE、三输入、普通分页等不回退。
thinking、配置与 Skill 映射已联动更新，Builtin JSON 保持；公共 Mate 边界独立管理。
GetSession 与 PUT Thinking 的说明移除已作废 Events 名称及游标指引，参数和响应不变。
普通整数分页不继承旧不透明 page 的失效规则；不能用旧配置说明覆盖新历史接口。

共享 GET 已恢复精简后的字段、排序和状态过滤；证据与其他分支处理状态见[整合核查](design-integration-audit.md)。
对应门禁增加两跳 GET 等值与负向测试；后续 Help/POST 修改不得恢复旧 GET 字段。

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
本节为用户于 2026-09-07 授权的文档维护收敛，不改变已确认业务行为。

## 3. 旧入口与维护流程

以下旧页面已从工作树删除，不保留兼容入口；已有链接统一指向当前页：

| 旧入口 | 当前目标 |
|---|---|
| `chat-http-v1-review.html` | [全部十一项](chat-api-review.html) |
| `chat-events-v2-submit-review.html` | [提交事件与推送](chat-api-review.html#submitSessionEvent) |
| `chat-events-v2-review.html` | [历史查询](chat-api-review.html#listSessionEvents) |
| `chat-events-v2-confirmed.html` | [当前评审与确认边界](chat-api-review.html#listSessionEvents)，不保留已失效整体确认 |

旧 `04-submit-user-message.json`、`05-list-session-events.json` 已删除；三个独立控制接口此前已删除。
旧报文和对应事件图从 Git 历史追溯，不恢复为兼容契约。`render_chat_events_v2.py`
已删除；`render_chat_http_v1.py` 仅保留当前 Runtime 与 Mate 页面仍复用的渲染函数，
删除旧页输出入口。只有 `render_chat_api.py` 生成当前 Runtime 接口页。
HTTP 测试 Agent 的历史回归通过 `git show` 读取固定提交和当时路径，不恢复工作树副本，
其历史实现清单不等于当前目标清单。

修改精确模型或增删已获批准的接口后，统一执行：

```bash
python3 render_chat_api.py
python3 ../../04-命令与技能/01-内置命令/Help-Agent使用指南/render_help_review.py
python3 validate-chat-api.py --full
node test_chat_api.cjs
```

统一校验复用九项普通契约与两项 Events 的专项门禁，并增加：清单唯一性、活动源覆盖、
报文字节同步、旧文件及生成器不存在、全仓 Markdown/HTML 不链接已删除入口、
旧模型不得回流、当前链接有效性；回归测试验证重新生成只写当前页，并拒绝旧文件和链接回流。
Help 专项页由独立渲染入口从同一份 Runtime Command 源派生，统一门禁会拒绝过期产物；
不再同步或编辑第二份 Help JSON。Mate GET 调整后，在其专题目录运行生成器及专项校验。
交互测试需可用的 `jsdom`，
可通过 `JSDOM_MODULE` 指定模块路径；缺失依赖应明确报错，不跳过后宣称通过。
页面沿用既有视觉语言：只在主动展开时挂载一个接口，滚动不触发渲染，关闭再打开保留选项；
禁用 JavaScript 或渲染失败仍可用原生 details 读取完整接口。锚点直接定位对应操作。

## 4. 源码边界

1.4.0 核对 `pi-mono-java@510d882ca45541e0086586dab89c429c5a18cf20` 的 `SessionNamingService`、`RuntimeSessionRepository.updateName`、`RuntimeSessionController` 和 `RuntimeSessionConfigurationController`：底层命名已实现，但目前只有 `/name` Command 入口。独立 Name API 是 target-only 设计，不写成已实现行为。

1.3.0 按已确认 B01～B15 补齐目标契约，源码证据沿用 Events 与 Skill 专题的 Java `dfb90cac4e233e09a0b8f047f7e9f4682f5ad238`、pi `5cd93f688aaab89dbb6dfa4aca535f21796ae185`。新增关系、差异与验证见相应专题；下列 1.0～1.2 记录只说明此前整理工作。

1.0.1 仅删除废弃文档及其生成入口，源码核对沿用 1.0.0 记录，不宣称本次重新核对实现主线。
不重新分析 Agent Loop 或调整 pi 基线。
保留既有 Runtime 语义证据 `pi-mono@5cd93f688aaab89dbb6dfa4aca535f21796ae185`，
对应路径和符号继续由 [Events 设计](chat-events-design.md) 与 [FollowUp 设计](chat-follow-up-future-design.md) 维护。

1.0.0 核对的实现主线 commit 为 `7b3769a5eabe2d131af3023631d7ad24e6d9a9e1`；
此前边界基线为 `dfb90cac4e233e09a0b8f047f7e9f4682f5ad238`；以下三个文件在两基线间无变化。
以下为仓库相对路径：

| 源码 | 已观察事实与影响 |
|---|---|
| `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/web/RuntimeEventController.java` · `submit/list` | 实现仍为 POST SSE / GET 历史入口；路径相同不证明已具备 Session Events 请求和事件模型。 |
| `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/vo/UserEventRequestVO.java` · `message/fileIds/rejectUnknownField` | 仍使用旧 message/fileIds，请求不是目标三输入联合类型；整理文档不等于完成实现迁移。 |
| `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/web/RuntimeSessionControlController.java` · `steer/followUp/abort` | 主线仍声明三个独立接口；设计退役与代码删除属于不同交付。 |

当前十一项中，新增的 Name API 是目标设计；本次不修改 Java、数据库、权限、运行时行为或仍有效的 Mate 公共契约。

## 5. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.4.0 | 2026-09-10 | 将独立 Session 重命名纳入当前十一项契约，明确它与 `/name` 共用服务且尚待实现。 |
| 1.3.0 | 2026-09-08 | 关闭 B01～B15 产品待决项；共享 contractSections 维护事件字段与码表，HTML 同步；实现校准独立记录。 |
| 1.2.0 | 2026-09-07 | 明确各专题唯一维护职责；清除 Mate 废止 POST 副本，Help 直接投影 Runtime，业务决定和未决状态不变。 |
| 1.1.0 | 2026-09-07 | 同步 GET 精简确认范围和防回退门禁，记录六个未合入分支的语义核查。 |
| 1.0.1 | 2026-09-07 | 按用户决定直接删除四个旧评审页及迁移占位生成逻辑；修复导航和历史测试引用，增加文件及链接防回流回归。 |
| 1.0.0 | 2026-09-07 | 统一当前清单、页面、生成和校验；旧页面仅导航、旧 Events 模型和报文移除；原确认状态不变。 |
