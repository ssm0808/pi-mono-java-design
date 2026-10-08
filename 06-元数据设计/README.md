# CampusClaw 元数据设计

版本：2.0.0；日期：2026-10-08。设计状态：当前元数据设计；实现与验收状态按所属模块分别维护。

[返回仓库首页](../README.md)

## 1. 职责与样例入口

元数据描述园区 Agent 的职责、能力绑定，以及 Tool、Skill 的定义，供 Mate 管理和 Claw 装配运行配置。会话当前状态、调用结果和用户确认属于 Session 与执行记录；业务执行凭据不保存在这些元数据中。

本目录维护元数据字段说明和具体 JSON 样例。元数据文件使用 snake_case，HTTP 字段及响应裁剪以所属模块契约为准，不直接把完整元数据对象作为创建、更新或 Runtime 响应报文。正式设计状态不表示所有字段已实现，也不新增全字段写入接口。

| 资源 | 可读取的完整 JSON 样例 | 业务职责 |
|---|---|---|
| Agent | [AGENT元数据设计.json](./AGENT元数据设计.json) | 设备告警助手：绑定模型、告警查询工具与排查技能 |
| Tool | [TOOL元数据设计.json](./TOOL元数据设计.json) | query-device-alarm：按设备标识查询当前告警 |
| Skill | [SKILL元数据设计.json](./SKILL元数据设计.json) | device-alarm-triage：组织设备告警排查步骤 |

三个文件均使用真实 JSON 类型：version 为整数，enabled 与 is_concurrency_safe 为布尔值，绑定为数组，Schema 为对象。资源名称、ID、时间和业务数据为虚构样例，不对应已部署资源；Model ID 是外部模型目录的示例引用，实际使用前必须配置可用模型。工具的业务参数、告警级别和结果结构用于演示元数据，不作为已有园区接口事实。

样例使用固定版本 1；Agent 与 Skill 引用同一个 Tool ID，Agent 引用本目录的 Skill ID。Agent.binding_agents 与 Skill.binding_skills 均为空，表示本场景不需要委派或组合技能，不暗示递归加载能力。Tool 同时被 Agent 和 Skill 绑定用于展示两种关联；宿主保留来源，不因重复关联获得额外权限。

## 2. 公共字段

| 字段 | JSON 类型 | 含义 |
|---|---|---|
| id | string | 资源标识；agent-、tool- 或 skill- 加 32 位十六进制 UUID，绑定引用既有 ID |
| type | string | 固定资源类型：agent、tool、skill |
| version | integer | 定义版本，从 1 开始；版本字段不代表具备历史存储或回滚能力 |
| created_at / updated_at | string | 创建与更新时间；样例使用带时区的 ISO 8601 时间字符串 |
| enabled | boolean | 资源启停状态，不能替代执行权限检查 |
| name | string | 技术名称，用于资源定位；工具按原名精确匹配 |
| display_name | string | 面向用户的展示名称，不参与执行身份判断 |
| description | string | 能力用途和适用条件 |

资源 ID、Agent 版本与启停的具体校验由 [Agent 主设计](../03-数据与存储/02-Agent元数据GaussDB/README.md#4-主表-t_agent_definition)维护；工具名称与展示规则由 [工具系统](../01-总体架构/02-CampusClaw工具系统/README.md#9-工具注册与发现)维护。

## 3. Agent 元数据

| 字段 | JSON 类型 | 含义与样例 |
|---|---|---|
| mode | string | 新建交互 Session 的默认模式，仅 build / plan；样例为 build |
| binding_models | string[] | 有序模型 ID 列表；至少一个，不重复 |
| system_prompt | object | 结构化提示词；样例填写下面八段，字段均为可选软约束 |
| use_cases | string[] | 适用场景，如查询设备当前告警；元素非空、不重复 |
| binding_tools | object[] | 直接工具绑定，每项包含 tool_id 和可选 version |
| binding_skills | object[] | 技能绑定，每项包含 skill_id 和可选 version |
| binding_agents | object[] | 其他 Agent 的绑定，每项包含 agent_id 和可选 version；禁止自绑定 |
| permission | object | 按 deny、ask、allow 分组的工具 ID 数组 |

| system_prompt 字段 | 职责 |
|---|---|
| role | 身份、专业能力与责任范围 |
| objective | 长期目标与成功结果 |
| instructions | 通用原则、优先顺序与行为要求 |
| tool_policy | 工具使用条件与结果核验方式 |
| safety | 不可信内容处理、权限边界与高风险操作要求 |
| completion | 完成条件、自检和无法完成时的报告方式 |
| response_style | 默认语言、篇幅、格式与汇报方式 |
| example | 行为或输出示例，不作为实时业务事实 |

管理详情保留结构化提示词，Runtime 视图按固定顺序拼接有效段落。Agent 默认 mode 只初始化新交互 Session，已有 Session 独立维护模式。绑定版本、提示词拼接、权限存储、五表结构和接口可写范围统一见 [Agent 元数据主设计](../03-数据与存储/02-Agent元数据GaussDB/README.md)，本目录不增加规则副本。

## 4. Tool 元数据

| 字段 | JSON 类型 | 含义与样例 |
|---|---|---|
| is_concurrency_safe | boolean | 声明工具是否支持安全并行；告警查询样例为 true |
| permission | string | 工具权限：ask / allow / deny；只读查询样例为 allow |
| source | string | 工具来源：builtin-toolset / mcp-toolset；样例为 builtin-toolset |
| input_schema | object | 输入 JSON Schema；样例要求非空字符串 deviceId |
| output_schema | object | 预期业务结果 JSON Schema；样例返回 deviceId 和 alarms 数组 |

input_schema 与 output_schema 内部的属性名属于具体业务工具。本样例使用 deviceId、alarmId、occurredAt 等 lower camel case，不因外层元数据采用 snake_case 而改写业务参数。

告警查询输入示例：

```json
{
  "deviceId": "AHU-001"
}
```

对应业务结果示例，未包装 Mate HTTP 响应或模型 Tool Result：

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

## 5. Skill 元数据

| 字段 | JSON 类型 | 含义与样例 |
|---|---|---|
| use_cases | string[] | 适用场景，如排查设备当前告警 |
| binding_tools | object[] | 工具引用，每项包含 tool_id 和可选 version；样例绑定告警查询工具 |
| binding_skills | object[] | 其他 Skill 的引用，每项包含 skill_id 和可选 version；样例为空 |
| permission | object | 按 deny、ask、allow 分组的工具 ID 数组；样例允许查询 |

Skill 元数据不承载操作步骤正文；运行目录中的 SKILL.md 与 references/templates 保存正文和资源。正文按唯一工具技术名引用能力，可信绑定来自元数据，正文提及工具不能新增绑定。目录文件的实际字段及加载范围见 [受管目录](../01-总体架构/02-CampusClaw工具系统/README.md#8-统一受管目录与刷新)。

binding_skills 保留既有元数据字段，不由本样例定义递归展开、循环依赖处理或传递授权；相关运行时能力未核验。当前工具目标范围仍以当前 Agent 直接绑定的 Skill 为准。

## 6. 样例的使用流程与失败处理

正常场景：用户查询 AHU-001 的当前告警，Agent 使用直接业务工具；需要排查步骤时加载绑定 Skill，其正文可引用同一 query-device-alarm。直接工具代理与 Skill 工具入口分别遵守各自的发现契约，最后都进入相同的可信执行链。

执行顺序为：可信绑定解析 → 按 input_schema 校验参数 → Host 权限判断或必要确认 → 业务执行 → 结果回传。放行后执行同次准备快照；allow 不跳过解析与校验，ask 也必须先校验再确认。

缺少 deviceId 时保持 isError=true，向模型返回字段错误和同次校验使用的可信定义，不确认、不执行业务、不自动猜参或重放。未知名称、禁用工具、绑定冲突和无效定义明确失败；请求发出后的超时不能宣称未执行或自动重试。公共用户事件隐藏内部 Schema 和敏感参数。精确行为及实现证据统一见 [工具参数恢复](../01-总体架构/02-CampusClaw工具系统/README.md#tool-argument-recovery)。

## 7. 权威来源与实现边界

本样例按设计仓提交 `5293e79cd4f2244faa1290602832f8833d963df4` 的既有字段与模块约束整理；日期为 2026-10-08。仅将字段说明实例化并将专题明确为元数据设计，不改变架构结论、数据库结构、HTTP 契约或模型工具集合；[Agent 架构对比](../01-总体架构/07-Agent架构对比/README.md)的结论与源码核验范围不变。

| 范围 | 权威文档与状态 |
|---|---|
| Agent 聚合、版本、权限、存储与管理接口 | [Agent 主设计 v0.19.2](../03-数据与存储/02-Agent元数据GaussDB/README.md)；既有实现证据保留 Mate 9dd5d85e，mode 专项保留 Mate 956b547f / Runtime 09b32d8e，不视为本次最新源码核验 |
| Agent 默认 mode 传播 | [主设计 §4.4](../03-数据与存储/02-Agent元数据GaussDB/README.md#44-agent-mode)仍标记待实现；样例值不改变实现状态 |
| Skill、业务代理、CallTool 和确认前准备 | [工具主设计 v2.19.0](../01-总体架构/02-CampusClaw工具系统/README.md)及其证据记录开发提交 ae6645ca 已实现，未据此宣称全部主线交付 |
| SearchTools 与发现、校验的一致性接线 | 工具主设计标记待实现；缓存、刷新、跨节点同步和版本切换机制待设计 |
| Tool/Skill 的完整存储、历史版本及统一输出 Schema 校验 | 本目录不补造数据库表或运行时实现；实现状态未核验 |

## 8. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.0.0 | 2026-10-08 | 元数据设计提供相互关联的 Agent、Tool、Skill 园区告警样例及字段、流程与实现边界说明。 |
