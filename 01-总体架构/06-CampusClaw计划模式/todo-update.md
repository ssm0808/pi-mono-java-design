# TodoUpdate：后端显式发布任务进度

版本：1.4.0；日期：2026-09-18。状态：主线 `8c5fda1dde51675859bc9c07e145dbe253656dea` 已实现工具、装配、显式任务事件、前端快照恢复和 description/两文件迁移，见[源码证据 §12](source-evidence.md#12-主线实现状态核验2026-09-18)。Mate 公共桥接待实现；本次未重跑产品或真实模型测试，历史测试保留原提交范围。

本专题属于 M03/M06/M07，复用[计划模式全局目标类图](README.md#3-推荐全局目标类图)。本文件维护工具契约、提交边界、进度生命周期与验收；公共事件精确字段由[共享事件源](../01-CampusClaw多Agent运行时/事件契约/common.json)维护，POST SSE 与 GET 历史共用。

## 1. 目标与基线选择

模型在 build 实施阶段通过 `TodoUpdate` 提交完整执行清单；plan 阶段只调研、澄清、设计和修订方案，不记录调研 TODO。Runtime 在成功工具结果提交时显式生成 `agent.todo_updated`，前端直接用事件的 `todos` 替换面板，不识别工具名、不关联工具调用和结果、不解析结果中的 JSON 文本。

清单更新参考 DeepSeek 的 `todo/write`、OpenCode 的 `todo.updated` 与 Codex 的 `turn/plan/updated`；公共权威历史和断线对账继续参考 Claude Managed Agents。后者未公开内置 TodoUpdate 或同名任务事件，不能将 CampusClaw 新事件描述为 Claude 原生契约。固定版本、层次及证据见[源码证据 §6](source-evidence.md#6-todo-update-基线与接入证据)。

| 边界 | 当前目标与理由 |
|---|---|
| 方案与进度 | `agent.plan` 固定待审核完整方案；`agent.todo_updated` 表示执行清单快照。进度不修改已批准正文、不批准方案、不更新 mode。 |
| 工具执行方 | Runtime 内置工具执行，浏览器只消费后端事件；不引入客户端提交工具结果的职责。 |
| 公共事件 | 后端显式投影进度是架构变更，降低客户端与工具实现的耦合；代价是增加一个公共类型及每次成功更新的一份快照事件。 |
| 进度作用域 | `(sessionId, sourceEventId)` 对应原始 user.message 的根执行；审核续跑保持归属，新普通消息开始新清单。属于产品约束。 |
| 首版入口 | Runtime 根执行默认追加 TodoUpdate；Child/Cron profile 保持原值，父 Agent 汇报 Child 工作，子调用不覆盖父清单。 |
| 模式约束 | plan/build 工具定义相同，固定 description 与模式提示词约束只在 build 使用；不增加模式过滤器，不把提示词说成绝对防误用保障。 |
| 权威与状态 | 公共进度从持久化 `agent.todo_updated` 恢复；模型从同次提交的 ToolResult 恢复。二者同源、同事务，不另存一份可变 TODO 状态。无新 Session/元数据字段、HTTP 路径或 TODO 表。 |

## 2. 模型工具契约

| 项目 | 定义 |
|---|---|
| 名称 | `TodoUpdate`，遵循现有区分大小写的 PascalCase；不提供别名 |
| 执行模式 | `SEQUENTIAL`，沿用现有串行 barrier；按批次原始调用顺序产生结果，不并行更新同一清单 |
| 暴露 | Runtime 缺省 profile 在 ExitPlanMode 后追加；显式 profile 仍完全替换默认值。缺少 TodoUpdate 只关闭进度能力，不影响计划审核准入 |
| 输入 | 必填 `todos` 数组；每项只有 `content` 和 `status`；每次提交整个列表 |
| 状态 | `pending`、`in_progress`、`completed`；首版最多一项 in_progress，与串行工作流一致 |
| 成功 | `isError=false`；恰好一个 text 块，其 text 是完整 JSON 对象 `{"todos":[...]}`；不混入自然语言或 Markdown 围栏 |
| 失败 | 沿用既有工具参数错误与执行失败映射；`isError=true` 不更新清单，不增加 TODO 专用公共错误码 |

固定 description：

```text
Track implementation progress in build mode; do not call this tool during plan-mode research or proposal design. Before multi-step implementation, submit the complete task list and mark the first active task in_progress. Mark each task completed immediately after its work and required verification finish; do not batch independent completions. The same call may complete the previous task and start the next one. Send the entire list every time, retaining completed tasks that should remain visible; use pending, in_progress, or completed with at most one task in_progress. Skip trivial work. Do not mark failed, partial, or unverified work completed. Adjust the list when the work changes within the authorized scope; remove cancelled items with an explanation instead of marking them completed. Read the result and do not claim a failed update was saved. Submit the required full list again when a new user-message execution continues earlier work. This tool reports progress only and does not execute tasks, approve proposals, change session mode, or replace the final answer.
```

进度调用与状态维护只在上述 description 定义，不再注入独立 EXECUTION_TODOS 资源或在 BUILD.md 复制操作步骤。[PLAN.md](PLAN.md)仅强调规划期不调用 TODO，基础 SYSTEM 负责通用验证和真实汇报。description 在两模式保持同一文本；它是模型行为约束，值校验不判断业务任务是否真正完成，也不新增模式拦截。

参数 Schema：

```json
{
  "type": "object",
  "properties": {
    "todos": {
      "type": "array",
      "maxItems": 100,
      "items": {
        "type": "object",
        "properties": {
          "content": {"type": "string", "minLength": 1, "maxLength": 1024},
          "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}
        },
        "required": ["content", "status"],
        "additionalProperties": false
      }
    }
  },
  "required": ["todos"],
  "additionalProperties": false
}
```

工具层逐项校验并创建独立快照：content 使用 Java `String.strip()` 去除首尾空白后非空，最多 1024 个 UTF-16 单元，规范化后内容不得重复；最多一个 in_progress。Schema 的 maxLength 按 JSON Schema 字符定义校验，工具层另外执行 UTF-16 上限，返回正文取规范化后的值。100 项上限用于限制每轮上下文和完整事件体积，仍须通过既有 SSE 编码字节检查，不能截断清单后当作成功。所有规则一次校验，任一项失败则整次失败。

空数组是明确清空当前清单；省略 todos、null、未知字段或状态均失败。整份替换使新建、调整、完成、清空共用一个工具，不增加 action、条目 ID、优先级、版本或百分比。列表顺序就是展示顺序，完成比例由客户端从列表计算；没有清单或空列表不显示为“100% 完成”。

## 3. 事件与执行顺序

![TodoUpdate 后端任务事件流程](todo_update_sequence.svg)

[原尺寸 SVG](todo_update_sequence.svg) · [PlantUML 源码：`todo_update_sequence`](diagram.puml#L455)

1. 模型生成 TodoUpdate ToolCall；Projector 按原路径保存和发送 `agent.tool_call`，`requiresConfirmation=false`。调用参数不提交进度。
2. Pipeline 校验参数并执行工具，工具返回规范化完整列表，不直接写数据库或发 SSE。
3. 在既有 `TurnEndEvent → RuntimeEventProjector.persistToolResults` 提交点，后端用当前执行内已确定的内置工具调用识别成功 TodoUpdate。`RuntimeTodoEventMapper` 校验最终成功结果的规范 JSON，生成不可变 `TodoSnapshotDTO`，不采用模型调用参数作为成功快照。
4. `RuntimeCommittedEventFactory` 从同一最终结果构造 `agent.tool_result` 与 `agent.todo_updated`。先校验两份完整载荷与编码大小，再以一个 ToolResult Entry 为共同 anchor，调用既有 `appendEntry(target, entry, List.of(toolResultEvent, todoUpdatedEvent))`。两个事件有独立 eventId，按列表顺序在一个事务提交，并归属同一原执行与续跑段。
5. 事务提交后依次发送工具结果和任务事件；前端只在 `agent.todo_updated` 上替换任务面板。网络失败不回滚已提交快照，断线后由历史恢复。失败工具结果不生成任务事件，保留上一清单。
6. 模型继续思考、调用业务工具、输出答案；每项实际完成且验证后立即调用 TodoUpdate。进度发布仍在工具批次结果提交点，不能承诺 Java 工具方法返回即推送。

任务更新不需要审核，不关闭 SSE、不创建续跑段。全列表 completed 只表示 Agent 报告的完成状态，真实执行结果仍由最终回答和 `session.status_idle` 表达。

目标事件示例（精确字段及配套 SSE/历史示例见共享源）：

```json
{
  "eventId": "evt-todo-01",
  "type": "agent.todo_updated",
  "createdAt": "2026-09-15T06:00:00.100Z",
  "sourceEventId": "evt-msg-01",
  "toolCallId": "call_todo_01",
  "todos": [
    {"content": "调整配置", "status": "completed"},
    {"content": "执行验证", "status": "in_progress"},
    {"content": "整理交付说明", "status": "pending"}
  ]
}
```

`todos` 是完整快照，空数组明确清空。`toolCallId` 只保留来源追踪，前端展示不依赖查找对应工具记录；`sourceEventId` 用于隔离不同根执行。无 phase、增量 patch、百分比、任务 ID 或新元数据字段。原有 agent.tool_result 继续使用文本块与 isError，不为任务面板修改其通用字段。

## 4. 客户端投影与恢复

客户端用 `applyTodoUpdated` 消费已解码、去重并对账的完整事件，实时与历史使用同一更新规则：

1. 复用 eventId 去重、历史数组顺序及保留 live 尾部的机制，不按 createdAt 排序或解析 eventId。
2. 按 Session 与原始 sourceEventId 选择清单，收到 `agent.todo_updated` 直接整份替换 `todos`。无需拿到关联的 tool_call/tool_result，也不以普通文本或工具参数推断进度。
3. 某根尚无任务事件时不显示清单；新 user.message 切换新根，审核续跑保持原根。真实结束后保留最后列表并独立展示 done/failed/terminated，不能自动把未完成项改为 completed。
4. SSE 断线后 GET Events 补读同形任务事件。分页未完成或新旧顺序尚未对账时保留已知列表并标记恢复中；旧历史页不能覆盖较新的 live 快照。空列表与尚未获知列表区分。
5. 不因网络重连重新 POST 消息、执行 TodoUpdate 或由前端补造任务事件。未知事件类型的旧客户端提示待升级，不当作成功或终态。

条目按纯文本展示，列表顺序就是显示顺序。客户端可以从明确状态计算完成项数量，但不承担判断任务真实完成的业务规则。模型上下文和压缩仍使用 ToolCall/ToolResult，不将公共任务事件再注入模型造成重复；压缩摘要不是前端进度来源。

## 5. 接入结构与权威提交

`TodoUpdateTool` 实现既有 AgentTool，由 Session 工厂按 profile 装配；不依赖 Controller、Mapper 或公共 VO，不持有当前列表。新增无状态 `RuntimeTodoEventMapper` 由 Projector 调用，识别可信内置调用并校验经过 Pipeline/after hook 后的最终结果，返回内部只读快照 DTO。不得因普通工具输出含 todos 或同名文本就生成事件；失败/未知调用不能生成成功更新。

既有 `RuntimeExecutionPersistenceService.appendEntry` 已接收事件列表；`MyBatisRuntimeSessionRepository.appendEventsLocked` 顺序分配并保存事件，`recordProjectionIfComplete` 保存实际事件数。目标复用该路径，一条 ToolResult Entry 对应两条公共事件，投影计数为 2；其他工具和失败结果沿用原计数。无需新增 Entry 类型、TODO Repository、数据库列或第二次事务。`t_session_events` 的 anchor 不是唯一键，既有投影表支持多事件数量。源码与提交见[证据 §6](source-evidence.md#6-todo-update-基线与接入证据)。

已知 TodoUpdate 的成功结果损坏、载荷超限或事务失败时，整组不提交、不发成功快照，进入现有投影失败与可靠收尾路径；不能先发布工具成功再尝试另写进度。提交成功但只送出工具结果就断线时，两条事件仍在历史中。公共事件共享原执行/段/分支/保留及访问规则，不推进 Session 配置 ETag。历史查询读取已保存事件，不在每次 GET 时重算列表或重新分配 ID。

任务事件响应及既有事件枚举、Factory、共享完整投影/编解码分支已有实现；实际响应类为 `SessionEventResponseVO.AgentTodoUpdatedResponseVO`。Controller 仍通过既有 VO 边界返回，Mapper 只使用 DTO。复用 JDK、既有 Jackson 与校验库，不新增 Maven 依赖。部署仍须确保读取端类型联合和解码器已升级；不为未部署过的 TodoUpdate 假造旧进度历史。

Mate 集成须显式映射 `agent.todo_updated` 到公共 Chat 事件，复用私有 Chat→Session 映射，并补齐公共 eventId 与原消息 sourceEventId 的对应关系；toolCallId 遵守 Mate 当前工具身份规则，不直接泄露内部 Session 身份。公共端保存后发布、去重并直接提供 todos。该 待实现 桥接增量由 [Mate C-007](../../02-服务与接口/07-mate-service通用对话API/协作/README.md#c-007) 登记，需同步公共精确模型后开放；现有 Mate 公共模型尚无 sourceEventId，不能声称两跳已实现。

## 6. 实施切片与验收

| 切片 | 实施内容 | 验收 |
|---|---|---|
| T1 | TodoUpdateTool、枚举/工厂、Runtime profile | plan/build 定义相同；提示词仅允许 build 实施；显式 profile 不被补齐；非法/重复/空白/多进行中整次失败；空列表清空，返回独立快照 |
| T2 | Mapper/DTO、Factory/ResponseVO、Projector 与持久化接入 | 成功产生两条事件且同源同事务；后一条 eventId 独立、根与段不漂移、投影计数为 2；失败无任务事件；畸形成功/超限/DB 失败不部分提交；提交后断线可补读 |
| T3 | applyTodoUpdated 与任务面板 | 不读取工具名或工具结果文本；仅任务事件也能展示；实时与历史一致；分页分割两个事件、旧页与 live 交错、重复帧、空列表、新根、断线及终态分别验证 |
| T4 | 提示词与 Mate 场景 | plan 调研/修订无 TODO；批准后创建实施清单；完成且验证后逐项更新；正常消息工具与任务事件交错；公共两跳关联不串根、不泄露内部身份 |

T1/T2 的工具与权威提交、T3 的内部前端投影已有实现；T4 的提示词资源迁移已实现，Mate 桥接待实现，实际模型行为待验收。build 清单可独立于计划审核验证。文档契约检查不代替产品集成测试，既有测试证据仅适用于记录的提交。

## 7. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.4.0 | 2026-09-18 | 登记主线工具、任务事件和提示词迁移实现，保留 Mate 桥接待实现边界。 |
| 1.3.0 | 2026-09-17 | 进度细则集中到工具 description，取消独立实施进度提示词段。 |
