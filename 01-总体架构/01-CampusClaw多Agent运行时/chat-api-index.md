# CampusClaw 接口统一管理

| 属性 | 值 |
|---|---|
| 文档版本 | 1.0.0 |
| 更新日期 | 2026-09-07 |
| 设计仓变更前基线 | `54a6068d59c60ff5745f036cabbc172c0acb49c9` |
| 变更性质 | 文档治理：统一入口与契约清单，不修改 Runtime 实现或重新确认接口 |
| 唯一当前入口 | [当前十项接口](chat-api-review.html) |

## 1. 为什么统一

原入口把 v1 的旧 Events 报文与 v2 新方案分别完整展示，根导航仍指向 v1。
仅加“迁移基线”提示，仍容易把旧字段当作当前契约；聊天中的总览又没有纳入设计仓。
本次将清单和总览纳入同一生成、校验和版本控制流程，旧页面不再承载接口详情。

## 2. 权威与状态

- [catalog.json](接口契约/catalog.json) 唯一决定当前十项 operation、顺序、精确源和关联设计。每个 method + path 只能出现一次，活动目录中的模型必须全部登记。
- [chat-api-review.html](chat-api-review.html) 是唯一当前人类接口页，从清单及精确模型生成，不手工编辑 HTML。
- 八项保留契约继续复用 `接口契约/common.json`；两个 Events 使用 `接口契约-v2/common.json`。目录名称只是源组织方式，不代表两套并行的当前接口清单。各 operation 不复制到另一目录。
- `review` 与 `reviewState` 继续记录原有确认决定；清单中的说明只解释其适用边界，不替代或自动提升确认状态。两个 Events 均未整体确认，当前评审仍是 ListEvents。
- Markdown 记录理由、源码证据与未决项；FollowUp 只见[未来设计](chat-follow-up-future-design.md)，本期不启用。Mate 公共契约独立管理，不受本轮影响。

已确认的 eventId、无公共 entrySeq、data-only SSE、三输入、普通分页等不回退。
保留接口中的 thinking、配置与命令事件映射仍需联动评审，统一页在对应接口前标明。
GetSession 与 PUT Thinking 的说明移除已作废 Events 名称及游标指引，参数和响应不变。
普通整数分页不继承旧不透明 page 的失效规则；不能用旧配置说明覆盖新历史接口。

## 3. 旧入口与维护流程

以下文件仅保留轻量迁移说明和指向统一页的链接，不嵌入任何 operation model 或请求/响应示例：

| 旧入口 | 当前目标 |
|---|---|
| `chat-http-v1-review.html` | [全部十项](chat-api-review.html) |
| `chat-events-v2-submit-review.html` | [提交事件与推送](chat-api-review.html#submitSessionEvent) |
| `chat-events-v2-review.html` | [历史查询](chat-api-review.html#listSessionEvents) |
| `chat-events-v2-confirmed.html` | [当前评审与确认边界](chat-api-review.html#listSessionEvents)，不保留已失效整体确认 |

旧 `04-submit-user-message.json`、`05-list-session-events.json` 已删除；三个独立控制接口此前已删除。
旧报文和对应事件图从 Git 历史追溯，不恢复为兼容契约。原生成命令只会生成迁移说明，
不会把作废报文重新写回。HTTP 测试 Agent 的历史实现清单不等于当前目标清单。

修改精确模型或增删已获批准的接口后，统一执行：

```bash
python3 render_chat_api.py
python3 validate-chat-api.py --full
node test_chat_api.cjs
```

统一校验复用八项保留契约与两项 Events 的专项门禁，并增加：清单唯一性、活动源覆盖、
报文字节同步、旧入口无报文、旧模型不得回流、当前链接有效性。交互测试需可用的 `jsdom`，
可通过 `JSDOM_MODULE` 指定模块路径；缺失依赖应明确报错，不跳过后宣称通过。
页面沿用既有视觉语言：只在主动展开时挂载一个接口，滚动不触发渲染，关闭再打开保留选项；
禁用 JavaScript 或渲染失败仍可用原生 details 读取完整接口。锚点直接定位对应操作。

## 4. 源码边界

本次仅核对 HTTP 入口是否仍为旧实现，不重新分析 Agent Loop 或调整 pi 基线。
保留既有 Runtime 语义证据 `pi-mono@5cd93f688aaab89dbb6dfa4aca535f21796ae185`，
对应路径和符号继续由 [Events 设计](chat-events-v2-design.md) 与 [FollowUp 设计](chat-follow-up-future-design.md) 维护。

实现主线本次核对 commit 为 `7b3769a5eabe2d131af3023631d7ad24e6d9a9e1`；
此前边界基线为 `dfb90cac4e233e09a0b8f047f7e9f4682f5ad238`；以下三个文件在两基线间无变化。
以下为仓库相对路径：

| 源码 | 已观察事实与影响 |
|---|---|
| `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/web/RuntimeEventController.java` · `submit/list` | 实现仍为 POST SSE / GET 历史入口；路径相同不证明已具备 v2 请求和事件模型。 |
| `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/vo/UserEventRequestVO.java` · `message/fileIds/rejectUnknownField` | 仍使用旧 message/fileIds，请求不是目标三输入联合类型；整理文档不等于完成实现迁移。 |
| `campusclaw/src/main/java/com/huawei/hicampus/claw/codingagent/runtimeapi/web/RuntimeSessionControlController.java` · `steer/followUp/abort` | 主线仍声明三个独立接口；设计退役与代码删除属于不同交付。 |

当前目标十项、旧控制接口退役、Events v2 部分确认都是既有产品/架构决定，非本次新增能力。
本次不修改 Java、数据库、权限、运行时行为或 Mate 公共契约，也不声称 v2 已部署。
没有新增结构关系，本次不新增类图；退役旧 Events 图源与 SVG 一并移除，其余现行图不变。

## 5. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-09-07 | 统一当前清单、页面、生成和校验；旧页面仅导航、旧 Events 模型和报文移除；原确认状态不变。 |
