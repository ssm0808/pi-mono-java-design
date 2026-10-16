# mate-service 聊天命令 API 设计

| 属性 | 值 |
|---|---|
| 文档版本 | 1.10.0 |
| 状态 | GET Descriptor 已确认；argumentType 与命令选项接口待评审；公共路径、认证、bridge 与错误映射待独立评审，待实现 |
| 精确展示源 | [命令清单](接口契约/操作/01-list-chat-commands.json)、[命令选项](接口契约/操作/02-list-chat-command-options.json)与[公共候选上下文](接口契约/common.json) |
| 人类评审入口 | [命令清单与命令选项](chat-command-v1-review.html) |
| 更新日期 | 2026-10-16 |

## 1. 保留范围

保留两个 GET：`GET /mate-service/v1/chats/{chatId}/commands` 的轻量字段投影（Mate 补充 argumentType），以及 `GET /mate-service/v1/chats/{chatId}/commands/{commandName}/options` 的命令选项查询。
字段确认不等于公共接口整体获批；页面上的认证、Chat 标识与错误响应仍是待重审候选。
Runtime 清单已改为按 Agent 查询（`GET /campusclaw-service/v1/agents/{agentId}/commands`），sessionId 为可选查询参数。本投影由 Mate 先解析 Chat 所属 Agent 与映射的 Session，再带该 sessionId 读取，因此始终是完整命令；公共路径是否同步改为按 Agent 查询待定。

公共命令执行协议仍需独立设计，不从 Runtime JSON 或 Skill SSE 自动推导。

| 层 | 负责 | 不负责 |
|---|---|---|
| Runtime | 命令清单（name/type/description/argumentHint）、会话的模型、深度思考与工作模式可选值、执行与最终准入 | 模型名称、选项显示名、按命令拼装前端数据 |
| mate-service | 为清单补 argumentType；按命令提供当前值与 value/label 候选，补模型名称和本地化显示名 | 执行准入；增加 Runtime 未给出的候选 |
| 前端 | 按 argumentType 选输入方式，以 argumentHint 作占位提示，展示 label、提交 value | 按命令名查询模型信息或维护显示名 |

理由：模型名称只在 Mate 模型管理中，Claw 数据库没有对应字段；把按命令取数的逻辑集中在 Mate，新增选项型命令时前端无需新增适配。代价是 Mate 多维护一组选项提供者，每次打开选项多一次 Mate 请求和最多两次 Runtime 请求。

## 2. GET 共享规则

字段、排序、命令状态规则、完整快照要求与 Slash 交互路由统一引用
[Slash 通用模块](../../01-总体架构/04-CampusClaw命令系统/README.md#31-get-轻量清单已确认)。
页面只保留标准请求和响应示例，不增加字段说明、交互速查或实现状态区块。本文不重述字段表。两跳成功示例继续做等值校验，不因公共认证独立而复制不同的 Descriptor 语义。

未命中、清单失败或输入形态不支持时保留草稿，不自动转为普通消息。
GET 不是执行预约；后续 POST 必须独立解析并在所属事务或锁内重新准入。
Help 元数据与缓存行为见 [Help 专题](../../01-总体架构/04-CampusClaw命令系统/01-内置命令/Help-Agent使用指南/README.md)。

<a id="command-options"></a>

## 3. 命令选项

前端的输入规则只有三条，不按命令名分支：

| argumentType | 前端行为 |
|---|---|
| 省略 | 不带参数，选中后直接执行 |
| `text` | 文本框；有 argumentHint 时作为占位提示；技能命令另可附文件 |
| `options` | 调用命令选项接口，展示 `label`、勾选 `currentValue`，把选中的 `value` 作为 arguments 提交；清空选择即无参查询 |

argumentType 由 Mate 的命令映射决定：name 与技能命令为 text，model、thinking、mode 为 options，其余省略。映射与会话状态无关，运行中的限制仍按[命令状态规则](../../01-总体架构/04-CampusClaw命令系统/README.md#command-state-rules)处理。

这套分工与 pi 一致：pi 的命令描述只有 `argumentHint` 占位文字，可选值由各命令的 `getArgumentCompletions` 按会话实时生成（`interactive-mode.ts:733-773`），返回 `{value, label}`。我们隔着 HTTP，无法像 pi 那样在进程内判断命令有没有补全函数，所以由 argumentType 告诉前端是否调用选项接口。

### 3.1 选项接口

| 项目 | 规则 |
|---|---|
| Method / path | `GET /mate-service/v1/chats/{chatId}/commands/{commandName}/options` |
| commandName | 清单中 argumentType=options 的命令名；其他命令返回 404 COMMAND_OPTIONS_NOT_FOUND |
| 成功 | 200，`Cache-Control: no-store`，`result` 为 `currentValue` 与 `options[{value, label}]`；候选为空也是成功 |
| 语言 | thinking、mode 的 label 按 Accept-Language 返回；模型名称是业务数据，各语言相同 |
| 失败 | 400 INVALID_CHAT_ID、401 UNAUTHENTICATED、403 CHAT_ACCESS_DENIED、404 CHAT_NOT_FOUND、404 COMMAND_OPTIONS_NOT_FOUND、503 COMMAND_OPTIONS_UNAVAILABLE |

精确示例见[命令选项契约](接口契约/操作/02-list-chat-command-options.json)与[评审页](chat-command-v1-review.html)。选项是读取时的观察结果，不是执行授权；提交仍由执行入口在 Runtime 锁内最终准入。

### 3.2 Mate 依赖的接口

Mate 先按 chatId 校验用户访问并解析映射的 sessionId 与 agentId，再按命令调用：

| 命令 | currentValue 来源 | 候选来源 | label 来源 |
|---|---|---|---|
| model | Runtime `GET /sessions/{sessionId}/models` 的 currentModelId | 同一响应的 models，顺序保持 | Mate 模型管理中的模型名称；没有名称时回退为 modelId |
| thinking | Runtime `GET /sessions/{sessionId}/thinking-values` 的 currentValue | 同一响应的 values；当前模型不支持深度思考时只有 off | Mate 文案资源（开启/关闭，On/Off） |
| mode | Runtime `GET /sessions/{sessionId}/modes` 的 currentValue | 同一响应的 values | Mate 文案资源（计划/实施，Plan/Build） |
| 清单 argumentType | — | Runtime `GET /agents/{agentId}/commands?sessionId={sessionId}` | Mate 命令映射 |

- Mate 不写死任何候选值：model、thinking、mode 的取值都以 Runtime 按会话返回的为准，Runtime 新增取值时 Mate 只需补显示名。
- 模型管理只补名称，不增加或删除候选；候选范围以 Runtime 的会话可选模型为准。Mate 模型管理需要为每个模型维护显示名称，现有 [模型信息查询](../03-Model/model-capabilities.md#2-独立模型信息查询契约)只返回 modelId 与 contextWindow，名称字段是本设计新增的待实现要求。
- 同一次选项请求内每个上游接口只读一次；任一 Runtime 调用或模型管理整体不可用时返回 503，不返回部分候选。
- 不缓存选项：当前值随会话变化，候选随 Agent 绑定变化。

### 3.3 扩展结构

命名按“做什么”而不是“怎么实现”，一个类只回答一个问题：

| 类型 | 名称 | 职责 |
|---|---|---|
| Controller | `ChatCommandController` | `listCommands(chatId)`、`listCommandOptions(chatId, commandName)`，只做参数校验与响应包装 |
| 应用服务 | `ChatCommandCatalogService` | 读取 Runtime 清单，用 `CommandArgumentTypeResolver` 为每条命令补 argumentType |
| 应用服务 | `ChatCommandOptionService` | 解析 Chat，按 commandName 找到提供者并返回 `CommandOptions`；找不到时抛 COMMAND_OPTIONS_NOT_FOUND |
| 映射 | `CommandArgumentTypeResolver` | `resolve(descriptor)`：name 与技能命令为 TEXT，model、thinking、mode 为 OPTIONS，其余为空 |
| 扩展点 | `CommandOptionProvider` | `commandName()`、`listOptions(ResolvedChat chat, Locale locale)`；每个选项型命令一个实现 |
| 实现 | `ModelOptionProvider`、`ThinkingOptionProvider`、`ModeOptionProvider` | 分别按 §3.2 取当前值、候选和显示名 |
| 值对象 | `ResolvedChat` | 用户可访问的 chatId 及其映射的 sessionId、agentId |
| 值对象 | `CommandOptions`、`CommandOption` | `currentValue` + `options`；`value` + `label`，与接口字段同名 |
| Runtime 客户端 | `RuntimeSessionClient`、`RuntimeCommandClient` | `listSessionModels`、`listThinkingValues`、`listModes`；`listCommands(agentId, sessionId)` |
| 模型名称 | `ModelDisplayNameQuery` | `findDisplayNames(modelIds)`：从 Mate 模型管理批量读名称，没有名称的 ID 不出现在结果中 |

新增选项型命令只需新增一个 `CommandOptionProvider` 实现，并在 `CommandArgumentTypeResolver` 中标为 OPTIONS；前端与 Runtime 清单结构不变。

## 4. 公共边界待决

| 待决事项 | 不得据此推定 |
|---|---|
| Chat 资源路径、标识、访问检查与 Session 映射 | 字段同形不意味着浏览器可直连 Runtime 或公开内部 sessionId |
| 公共凭据、授权及下游凭据构造 | 不把当前候选 Header 当作已确认认证策略，不将 Runtime 规则机械复制到公共层 |
| 错误映射、语言与不可用重试 | Runtime 的错误码与状态不能自动成为公共错误契约 |
| Builtin / Skill 公共执行协议及 Events 衔接 | 不恢复已废止的 POST SSE、命令生命周期和名称历史，不擅自发布新 POST |

当前不新增公共执行接口、实现切片或目标类图。边界确认后再补充目标结构和实施验收。

## 5. 证据边界

- 共享 GET 的已核对源码为 pi-mono-java `6f52fddc87a03c20916fc7b6ef1de87f6a7a8cf5`，
  完整路径、符号与目标差距由 [Slash 源码证据 §5](../../01-总体架构/04-CampusClaw命令系统/source-evidence.md#33-发现层证据与验收)维护。
- Mate 历史证据点为 `956b547f5ca12ca89e68f73012f92a4406b0c9fa`：
  `src/main/java/com/huawei/hicampus/mate/agentdefinition/controller/AgentDefinitionController.java:39-67`
  与同模块 `modelmanager/controller/LlmChatController.java:34-56`、`modelmanager/service/UpstreamChatCall.java:19-31`。
  当时只观察到 Agent 配置查询和 Model Manager 透明代理；这些证据不能证明当前已有 Chat Command bridge。
- 实现结论限定于上述固定提交，尚未核验公共 Chat Command bridge。

## 6. 生成与校验

```bash
python3 render_chat_command_v1.py
python3 validate-chat-command-v1.py --full
```

校验覆盖命令清单与命令选项两个 GET：清单去掉 argumentType 后与 Runtime 两跳等值、argumentType 符合 Mate 映射；选项的 value 与 currentValue 与 Runtime 的会话模型、深度思考或工作模式可选值一致、label 按语言规则区分；另查公共边界待评审标识、生成字节与无脚本展示，
并拒绝废止 POST 模型与两张旧图回流。实现、公共认证和端到端执行未在本轮验证。

## 7. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.10.0 | 2026-10-16 | 清单补充 argumentType，并跟随 Runtime 以 argumentHint 占位字符串替换 hints；新增命令选项接口 `GET /chats/{chatId}/commands/{commandName}/options`：Mate 提供 model、thinking、mode 的 currentValue 与 value/label 候选，取值都来自 Runtime 会话查询（模型、深度思考可选值、工作模式可选值），模型名称取自 Mate 模型管理；登记 Mate 依赖的 Runtime 接口、类名与职责。公共契约 1.8.0。 |
| 1.9.0 | 2026-10-16 | 清单投影跟随 Runtime：Builtin 中文描述优化，hints 改为固定参数值列表；Mate 以 Chat 映射的 sessionId 调用 Runtime，投影完整命令。 |
| 1.8.0 | 2026-10-16 | 清单投影跟随 Runtime：Builtin description 按 Accept-Language 国际化，补 en-US 示例。 |
| 1.7.0 | 2026-10-16 | 清单投影跟随 Runtime 改为按所属 Agent 返回全部命令，不再按会话状态过滤；公共路径是否改为按 Agent 查询待定。 |
| 1.6.0 | 2026-09-22 | 清单投影增加 mode 查询与模式切换入口，公共执行仍独立验收。 |
| 1.5.1 | 2026-09-22 | 接口作用只描述调用功能，具体规则与实现状态由各自栏目维护。 |
| 1.5.0 | 2026-09-22 | 同步 type/hints 描述符投影，公共认证与执行边界保持独立。 |
| 1.4.0 | 2026-09-14 | 以当前 GET 投影和公共待决边界整理正文，精确契约保持原状态。 |
| 1.3.0 | 2026-09-07 | 清除废止 POST SSE 及旧图、验收；保留 GET 投影和公共边界待决，规则改为引用。 |
| 1.2.0 | 2026-09-07 | 合入已确认 GET 字段减法，保留后续 Help 无参，公共边界待重审。 |
| 1.1.0 | 2026-09-04 | 废止旧公共 POST SSE；旧内容现只从 Git 历史追溯。 |
