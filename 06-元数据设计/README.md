# CampusClaw 元数据设计

版本：2.1.5；日期：2026-10-08。设计状态：当前元数据设计；实现与验收状态按所属模块分别维护。

[返回仓库首页](../README.md)

## 1. 职责与样例入口

元数据描述园区 Agent 的职责、能力关联，以及工具、技能的定义，供 Mate 管理和 Claw 装配运行配置。会话当前状态、调用结果和用户确认属于 Session 与执行记录；业务执行凭据不保存在这些元数据中。

本目录维护元数据字段说明和具体 JSON 样例。`binding_*` 字段记录资源间的关联关系；关联项引用目标资源的 ID，不为目标生成新 ID。元数据文件使用 snake_case，HTTP 字段及响应裁剪以所属模块契约为准，不直接把完整元数据对象作为创建、更新或 Runtime 响应报文。正式设计状态不表示所有字段已实现，也不新增全字段写入接口。

| 资源 | 可读取的完整 JSON 样例 | 业务职责 |
|---|---|---|
| Agent | [AGENT元数据设计.json](./AGENT元数据设计.json) | 设备告警助手：关联模型、告警查询工具与排查技能 |
| 技能 | [SKILL元数据设计.json](./SKILL元数据设计.json) | device-alarm-triage：组织设备告警排查步骤 |
| 工具 | [TOOL元数据设计.json](./TOOL元数据设计.json) | query-device-alarm：按设备标识查询当前告警 |

三个文件均使用真实 JSON 类型：version 为整数，enabled 与 is_concurrency_safe 为布尔值，关联列表为数组，Schema 为对象。资源名称、ID、时间和业务数据为虚构样例，不对应已部署资源；模型 ID 是外部模型目录的示例引用，实际使用前必须配置可用模型。工具的业务参数、告警级别和结果结构用于演示元数据，不作为已有园区接口事实。

样例使用固定版本 1；Agent 与技能引用同一个工具 ID，Agent 引用本目录的技能 ID。`Agent.binding_agents` 与 `Skill.binding_skills` 均为空，表示本场景不需要委派或组合技能，不暗示递归加载能力。Agent 与技能均关联该工具，用于展示两种关联来源；宿主保留来源，不因重复关联获得额外权限。

## 2. Agent 元数据

| 字段 | 含义 | 规则 |
|---|---|---|
| id | Agent 唯一标识 | string；符合 `^agent-[0-9a-fA-F]{32}$`；其他 Agent 关联该 Agent 时引用此 ID |
| type | 资源类型 | string；固定为 agent |
| version | Agent 定义版本 | integer；从 1 开始，定义修改后递增；不代表具备历史存储或回滚能力 |
| created_at | Agent 定义的创建时间 | string；UTC 时间，精确到秒，格式为 `YYYY-MM-DDTHH:mm:ssZ`，以大写 Z 结尾，不含小数秒 |
| updated_at | Agent 定义的最后更新时间 | string；时间格式与 created_at 相同，定义修改时更新 |
| enabled | Agent 是否启用 | boolean；true 表示启用，false 表示禁用；启用不能替代执行权限检查 |
| name | Agent 名称，用于识别和查找 | string；名称唯一；管理前端只读 |
| display_name | Agent 展示名称，供用户阅读 | string；管理前端只读，不参与执行身份判断 |
| description | Agent 的职责与适用场景 | string |
| mode | 新建交互 Session 的默认模式 | string；仅 build / plan；创建后由 Session 独立维护当前模式 |
| binding_models | 可用模型的关联列表 | string[]；至少一个模型 ID，不重复，保留配置顺序 |
| system_prompt | 结构化提示词 | object；包含下表八个可选字段，各字段均为软约束 |
| use_cases | Agent 的适用场景 | string[]；元素非空、不重复 |
| binding_tools | Agent 直接关联的工具 | object[]；每项包含 tool_id 和可选 version |
| binding_skills | Agent 关联的技能 | object[]；每项包含 skill_id 和可选 version |
| binding_agents | Agent 关联的其他 Agent | object[]；每项包含 agent_id 和可选 version；禁止自关联 |
| permission | Agent 对关联工具的权限配置 | object；deny、ask、allow 分别保存工具 ID 数组；同一工具只属于一组，权限引用必须对应已关联工具 |

| system_prompt 字段 | 含义 | 规则 |
|---|---|---|
| role | 身份、专业能力与责任范围 | string；可选软约束 |
| objective | 长期目标与成功结果 | string；可选软约束 |
| instructions | 通用原则、优先顺序与行为要求 | string；可选软约束 |
| tool_policy | 工具使用条件与结果核验方式 | string；可选软约束，不替代实际执行检查 |
| safety | 不可信内容处理、权限边界与高风险操作要求 | string；可选软约束，不替代宿主权限判断 |
| completion | 完成条件、自检和无法完成时的报告方式 | string；可选软约束 |
| response_style | 默认语言、篇幅、格式与汇报方式 | string；可选软约束 |
| example | 行为或输出示例 | string；可选软约束，不作为实时业务事实 |

时间样例：`2026-08-03T00:00:00Z`。资源 ID、版本与启停的具体校验见 [Agent 主设计](../03-数据与存储/02-Agent元数据GaussDB/README.md#4-主表-t_agent_definition)。

管理详情保留结构化提示词，Runtime 视图按固定顺序拼接有效段落。Agent 默认 mode 只初始化新交互 Session，已有 Session 独立维护模式。关联版本、提示词拼接、权限存储、五表结构和接口可写范围统一见 [Agent 元数据主设计](../03-数据与存储/02-Agent元数据GaussDB/README.md)，本目录不增加规则副本。

<a id="3-skill-元数据"></a>

## 3. 技能元数据

| 字段 | 含义 | 规则 |
|---|---|---|
| id | 技能唯一标识 | string；符合 `^skill-[0-9a-fA-F]{32}$`；Agent 或其他技能关联该技能时引用此 ID |
| type | 资源类型 | string；固定为 skill |
| version | 技能定义版本 | integer；从 1 开始，定义修改后递增；不代表具备历史存储或回滚能力 |
| created_at | 技能定义的创建时间 | string；UTC 时间，精确到秒，格式为 `YYYY-MM-DDTHH:mm:ssZ`，以大写 Z 结尾，不含小数秒 |
| updated_at | 技能定义的最后更新时间 | string；时间格式与 created_at 相同，定义修改时更新 |
| enabled | 技能是否启用 | boolean；true 表示启用，false 表示禁用；启用不能替代执行权限检查 |
| name | 技能名称，供模型识别和调用 | string；运行目录名称与元数据名称逐字符一致，在所属索引内唯一 |
| display_name | 技能展示名称，供用户阅读 | string；用于展示，不参与执行身份判断 |
| description | 技能的用途与适用场景 | string |
| use_cases | 技能的适用场景 | string[]；使用场景文本列表 |
| binding_tools | 技能关联的工具 | object[]；每项包含 tool_id 和可选 version |
| binding_skills | 技能关联的其他技能 | object[]；每项包含 skill_id 和可选 version；不据此定义递归加载或传递授权 |
| permission | 技能对关联工具的权限配置 | object；deny、ask、allow 分别保存工具 ID 数组；实际调用仍需经过宿主权限判断 |

时间样例：`2026-08-03T00:00:00Z`。

技能元数据不承载操作步骤正文；运行目录中的 SKILL.md 与 references/templates 保存正文和资源。正文使用唯一工具名称引用能力，可信关联来自元数据，正文提及工具不能新增关联。目录文件的实际字段及加载范围见 [受管目录](../01-总体架构/02-CampusClaw工具系统/README.md#8-统一受管目录与刷新)。

binding_skills 保留既有元数据字段，不由本样例定义递归展开、循环依赖处理或传递授权；相关运行时能力未核验。当前工具目标范围仍以当前 Agent 直接关联的技能为准。

<a id="4-tool-元数据"></a>

## 4. 工具元数据

| 字段 | 含义 | 规则 |
|---|---|---|
| id | 工具唯一标识 | string；符合 `^tool-[0-9a-fA-F]{32}$`；Agent 或技能关联该工具时引用此 ID |
| type | 资源类型 | string；固定为 tool |
| version | 工具定义版本 | integer；从 1 开始，定义修改后递增；不代表具备历史存储或回滚能力 |
| created_at | 工具定义的创建时间 | string；UTC 时间，精确到秒，格式为 `YYYY-MM-DDTHH:mm:ssZ`，以大写 Z 结尾，不含小数秒 |
| updated_at | 工具定义的最后更新时间 | string；时间格式与 created_at 相同，定义修改时更新 |
| enabled | 工具是否启用 | boolean；true 表示启用，false 表示禁用；启用不能替代执行权限检查 |
| name | 工具名称，供模型识别和调用 | string；区分大小写 |
| display_name | 工具展示名称，供用户阅读 | string |
| description | 工具的用途与适用场景 | string |
| is_concurrency_safe | 工具是否支持安全并行调用 | boolean；true 表示支持，false 表示不支持；数据源缺失时按 false 处理，实际调度仍遵守工具系统规则 |
| permission | 工具自身的权限配置 | string；仅 ask / allow / deny，分别表示需要确认、允许、禁止；Agent 关联未配置权限时继承工具权限 |
| source | 工具来源 | string；仅 builtin-toolset / mcp-toolset |
| input_schema | 工具输入参数的结构与约束 | object；使用 JSON Schema 描述参数，运行时在权限确认前校验业务参数 |
| output_schema | 预期成功业务结果的结构与约束 | object；使用 JSON Schema 描述结果，不据此宣称已实现统一的运行时输出校验 |

时间样例：`2026-08-03T00:00:00Z`，适用于工具元数据的 created_at、updated_at；业务输入、输出时间字段仍由其业务 Schema 定义。工具名称与展示规则见 [工具系统](../01-总体架构/02-CampusClaw工具系统/README.md#9-工具注册与发现)。

input_schema 与 output_schema 内部的属性名属于具体业务工具。本样例使用 deviceId、alarmId、occurredAt 等小驼峰命名，不因外层元数据采用 snake_case 而改写业务参数。

告警查询输入示例：

```json
{
  "deviceId": "AHU-001"
}
```

对应业务结果示例，未包装 Mate HTTP 响应或模型工具结果：

```json
{
  "deviceId": "AHU-001",
  "alarms": [
    {
      "alarmId": "ALARM-20261008-001",
      "severity": "critical",
      "message": "送风温度过高",
      "occurredAt": "2026-10-08T01:30:00Z"
    }
  ]
}
```

无告警时 alarms 为 []；业务失败不伪装为成功的空列表。output_schema 描述成功业务结果，当前未据此定义统一的运行时输出校验机制，其实现状态未核验。

并行标志只描述工具能力；[当前调度设计](../01-总体架构/02-CampusClaw工具系统/README.md#7-pipelinehook-与批量调度)仍让业务代理与 CallTool 串行执行。Runtime Agent 的 bindingTools 不返回输入、输出 Schema；面向模型的完整定义包含 name、description、inputSchema，具体披露和调用范围由 [工具发现设计](../01-总体架构/02-CampusClaw工具系统/README.md#9-工具注册与发现)维护。

## 5. 样例的使用流程与失败处理

正常场景：用户查询 AHU-001 的当前告警，Agent 使用直接业务工具；需要排查步骤时加载已关联的技能，其正文可引用同一 query-device-alarm。直接工具代理与技能关联工具的调用入口分别遵守各自的发现契约，最后都进入相同的可信执行链。

执行顺序为：可信关联解析 → 按 input_schema 校验参数 → 宿主权限判断或必要确认 → 业务执行 → 结果回传。放行后执行同次准备快照；allow 不跳过解析与校验，ask 也必须先校验再确认。

缺少 deviceId 时保持 isError=true，向模型返回字段错误和同次校验使用的可信定义，不确认、不执行业务、不自动猜参或重放。未知名称、禁用工具、关联冲突和无效定义明确失败；请求发出后的超时不能宣称未执行或自动重试。公共用户事件隐藏内部 Schema 和敏感参数。精确行为及实现证据统一见 [工具参数恢复](../01-总体架构/02-CampusClaw工具系统/README.md#tool-argument-recovery)。

## 6. 权威来源与实现边界

本样例按设计仓提交 `5293e79cd4f2244faa1290602832f8833d963df4` 的既有字段与模块约束整理；日期为 2026-10-08。仅将字段说明实例化并将专题明确为元数据设计，不改变架构结论、数据库结构、HTTP 契约或模型工具集合；[Agent 架构对比](../01-总体架构/07-Agent架构对比/README.md)的结论与源码核验范围不变。

| 范围 | 权威文档与状态 |
|---|---|
| Agent 聚合、版本、权限、存储与管理接口 | [Agent 主设计 v0.19.4](../03-数据与存储/02-Agent元数据GaussDB/README.md)；既有实现证据保留 Mate 9dd5d85e，mode 专项保留 Mate 956b547f / Runtime 09b32d8e，不视为本次最新源码核验 |
| Agent 默认 mode 传播 | [主设计 §4.4](../03-数据与存储/02-Agent元数据GaussDB/README.md#44-agent-mode)仍标记待实现；样例值不改变实现状态 |
| 技能、业务代理、CallTool 和确认前准备 | [工具主设计 v2.19.0](../01-总体架构/02-CampusClaw工具系统/README.md)及其证据记录开发提交 ae6645ca 已实现，未据此宣称全部主线交付 |
| SearchTools 与发现、校验的一致性接线 | 工具主设计标记待实现；缓存、刷新、跨节点同步和版本切换机制待设计 |
| 工具和技能的完整存储、历史版本及统一输出 Schema 校验 | 本目录不补造数据库表或运行时实现；实现状态未核验 |

## 7. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.1.5 | 2026-10-08 | 中文说明统一使用“技能”和“工具”，名称及用途描述采用直接易懂的表述。 |
| 2.1.4 | 2026-10-08 | Tool name 与 display_name 分别说明模型调用名称和用户展示名称。 |
| 2.1.3 | 2026-10-08 | Tool name 字段规则简化为区分大小写。 |
| 2.1.2 | 2026-10-08 | 将元数据资源关系统一称为“关联”，并明确关联项引用目标资源 ID。 |
| 2.1.1 | 2026-10-08 | Agent、Skill、Tool 分别列出完整字段的含义和规则，取消公共字段章节。 |
| 2.1.0 | 2026-10-08 | 字段说明统一为含义与规则，明确三类元数据时间采用 UTC 秒级且以 Z 结尾的格式。 |
| 2.0.0 | 2026-10-08 | 元数据设计提供相互关联的 Agent、Tool、Skill 园区告警样例及字段、流程与实现边界说明。 |
