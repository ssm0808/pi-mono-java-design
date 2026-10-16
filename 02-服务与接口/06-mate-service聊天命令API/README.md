# mate-service 聊天命令 API 设计

| 属性 | 值 |
|---|---|
| 文档版本 | 1.9.0 |
| 状态 | GET Descriptor 已确认；公共路径、认证、bridge 与错误映射待独立评审，待实现 |
| 精确展示源 | [GET 模型](接口契约/操作/01-list-chat-commands.json)与[公共候选上下文](接口契约/common.json) |
| 人类评审入口 | [GET 命令清单](chat-command-v1-review.html) |
| 更新日期 | 2026-10-16 |

## 1. 保留范围

只保留 `GET /mate-service/v1/chats/{chatId}/commands` 的轻量字段投影。
字段确认不等于公共接口整体获批；页面上的认证、Chat 标识与错误响应仍是待重审候选。
Runtime 清单已改为按 Agent 查询（`GET /campusclaw-service/v1/agents/{agentId}/commands`），本投影由 Mate 先解析 Chat 所属 Agent 再读取；公共路径是否同步改为按 Agent 查询待定。

公共命令执行协议仍需独立设计，不从 Runtime JSON 或 Skill SSE 自动推导。

## 2. GET 共享规则

字段、排序、命令状态规则、完整快照要求与 Slash 交互路由统一引用
[Slash 通用模块](../../01-总体架构/04-CampusClaw命令系统/README.md#31-get-轻量清单已确认)。
页面只保留标准请求和响应示例，不增加字段说明、交互速查或实现状态区块。本文不重述字段表。两跳成功示例继续做等值校验，不因公共认证独立而复制不同的 Descriptor 语义。

未命中、清单失败或输入形态不支持时保留草稿，不自动转为普通消息。
GET 不是执行预约；后续 POST 必须独立解析并在所属事务或锁内重新准入。
Help 元数据与缓存行为见 [Help 专题](../../01-总体架构/04-CampusClaw命令系统/01-内置命令/Help-Agent使用指南/README.md)。

## 3. 公共边界待决

| 待决事项 | 不得据此推定 |
|---|---|
| Chat 资源路径、标识、访问检查与 Session 映射 | 字段同形不意味着浏览器可直连 Runtime 或公开内部 sessionId |
| 公共凭据、授权及下游凭据构造 | 不把当前候选 Header 当作已确认认证策略，不将 Runtime 规则机械复制到公共层 |
| 错误映射、语言与不可用重试 | Runtime 的错误码与状态不能自动成为公共错误契约 |
| Builtin / Skill 公共执行协议及 Events 衔接 | 不恢复已废止的 POST SSE、命令生命周期和名称历史，不擅自发布新 POST |

当前不新增公共执行接口、实现切片或目标类图。边界确认后再补充目标结构和实施验收。

## 4. 证据边界

- 共享 GET 的已核对源码为 pi-mono-java `6f52fddc87a03c20916fc7b6ef1de87f6a7a8cf5`，
  完整路径、符号与目标差距由 [Slash 源码证据 §5](../../01-总体架构/04-CampusClaw命令系统/source-evidence.md#33-发现层证据与验收)维护。
- Mate 历史证据点为 `956b547f5ca12ca89e68f73012f92a4406b0c9fa`：
  `src/main/java/com/huawei/hicampus/mate/agentdefinition/controller/AgentDefinitionController.java:39-67`
  与同模块 `modelmanager/controller/LlmChatController.java:34-56`、`modelmanager/service/UpstreamChatCall.java:19-31`。
  当时只观察到 Agent 配置查询和 Model Manager 透明代理；这些证据不能证明当前已有 Chat Command bridge。
- 实现结论限定于上述固定提交，尚未核验公共 Chat Command bridge。

## 5. 生成与校验

```bash
python3 render_chat_command_v1.py
python3 validate-chat-command-v1.py --full
```

校验只保留一个 GET 投影、两跳成功数据等值、公共边界待评审标识、生成字节与无脚本展示，
并拒绝废止 POST 模型与两张旧图回流。实现、公共认证和端到端执行未在本轮验证。

## 6. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.9.0 | 2026-10-16 | 清单投影跟随 Runtime：Builtin 中文描述优化，hints 改为固定参数值列表。 |
| 1.8.0 | 2026-10-16 | 清单投影跟随 Runtime：Builtin description 按 Accept-Language 国际化，补 en-US 示例。 |
| 1.7.0 | 2026-10-16 | 清单投影跟随 Runtime 改为按所属 Agent 返回全部命令，不再按会话状态过滤；公共路径是否改为按 Agent 查询待定。 |
| 1.6.0 | 2026-09-22 | 清单投影增加 mode 查询与模式切换入口，公共执行仍独立验收。 |
| 1.5.1 | 2026-09-22 | 接口作用只描述调用功能，具体规则与实现状态由各自栏目维护。 |
| 1.5.0 | 2026-09-22 | 同步 type/hints 描述符投影，公共认证与执行边界保持独立。 |
| 1.4.0 | 2026-09-14 | 以当前 GET 投影和公共待决边界整理正文，精确契约保持原状态。 |
| 1.3.0 | 2026-09-07 | 清除废止 POST SSE 及旧图、验收；保留 GET 投影和公共边界待决，规则改为引用。 |
| 1.2.0 | 2026-09-07 | 合入已确认 GET 字段减法，保留后续 Help 无参，公共边界待重审。 |
| 1.1.0 | 2026-09-04 | 废止旧公共 POST SSE；旧内容现只从 Git 历史追溯。 |
