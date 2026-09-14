# Mate Chat API 待决事项

[返回主设计](../README.md)

版本 0.2.0 · 2026-09-14

本页维护尚未进入公共契约的要求与跨模块差距。当前字段、报文和机器评审状态归 operation JSON；已整合的决定不在此重复维护。目录保留原路径，具体任务分工和交接过程通过 Git 历史追溯。

| 编号 | 状态 | 当前问题与边界 |
|---|---|---|
| [C-001](#c-001) | 要求已确认，完整方案待定 | 一基数字页码与现有固定快照分页如何结合 |
| C-002 | 展示方案待定 | 公司 Swagger 不能展示 text/event-stream，真实 HTTP 媒体类型保持 SSE；另行选择准确的展示方式 |
| C-003 | 公共 operation 待定 | 创建与配置 Chat 的方法、字段、默认值、状态准入、响应和错误尚未整合为契约 |
| [C-004](#c-004) | Runtime 目标已明确，实施/桥接待对齐 | Claw 已选择原子 Session POST，Mate 公共配置入口仍未定稿 |
| [C-005](#c-005) | 标识约束待校准 | Provider 与 Runtime 的 modelId 长度/字符集不同，不能直接复制任一方为全系统规则 |
| [C-006](#c-006) | 公共与内部事件待桥接 | 中断目标、工具结果、错误字段、分页和流生命周期存在已知差异 |

<a id="c-001"></a>

## 数字页码与快照

已确认要求是 page/nextPage 使用 1、2、3 等一基数字，不使用 opaque cursor。现有公共模型仍用游标保存过滤条件、固定上界与续读位置，数字本身不能表达这些上下文。

原候选为数字页码加 snapshotEventId，并在后续请求重传过滤条件；快照标识、完整 Query/响应和错误尚未确认。该候选保持 proposed，不能因 Runtime 已采用普通分页就取消公共快照保证。先完成这项整体决定，再同步 JSON、OpenAPI、HTML、客户端恢复和校验。

<a id="c-004"></a>

## Chat 配置与 Runtime 原子更新

modelId 和思考设置属于 Chat/Session 配置，不进入 user.message；消息被接受时固定执行配置，运行中配置变化不追溯已有执行。公共创建/配置接口的具体形状仍待确定。

[Runtime Session 更新](../../../01-总体架构/01-CampusClaw多Agent运行时/chat-http-v1-design.md#session-update) 已确认用 POST 原子更新 displayName/modelId/thinking/mode，按字段决定 busy 准入并要求 If-Match。原先“只能拆成两次 PUT 或增加原子操作”的目标选择已经解决；实际组合事务仍为 target-only，不能让 Mate 顺序调用旧 PUT 假装原子成功。

原冲突的实际源码基线为 Java c9d858bc8261bf07f5585f545b53495bf2226a56：`modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/` 下 `web/RuntimeSessionConfigurationController.java#changeModel/changeThinking`、`session/RuntimeSessionConfigurationService.java#changeModel/changeThinking` 和 `persistence/MyBatisRuntimeSessionRepository.java#updateModel/updateThinking` 分别提供独立更新与事务。新的专项证据由 Runtime 主设计 §8.1 维护，未将旧差距延伸为最新实现审计。

<a id="c-005"></a>

## modelId 跨边界约束

Provider 契约定义大小写敏感的 1–64 字符不透明标识；Runtime 的配置契约沿用 1–128 和限定字符集。公共 Chat 配置在校准前不选取任一方作为共同约束。

证据：本仓 [Provider 主设计](../../03-模型管理Provider契约/README.md)；Java c9d858bc 的 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/RuntimeApiConstants.java#MODEL_ID_PATTERN` 及 `vo/ChangeModelRequestVO.java#modelId`。此处记录契约差异，不推断底层模型目录已经统一。

<a id="c-006"></a>

## 公共与内部事件衔接

| 边界 | 公共 Chat 目标 | Runtime Session 目标 | 所需设计工作 |
|---|---|---|---|
| 中断关联 | user.interrupt 无业务目标字段 | 必填 targetEventId 绑定原消息 | 明确公共动作如何固定原目标及跨执行竞争，不能动态中断最新任务 |
| 工具结果 | content 字符串，失败 errorCode 按条件可选 | content 文本块数组，失败码必填 | 明确安全转换和稳定错误映射 |
| 请求输出 | POST JSON 回执，GET stream 跨多轮 | POST 回执与对应执行段 SSE，idle 关闭 | bridge 维护独立观察和输出范围，不转发底层连接生命周期 |
| 历史 | createdAt 固定快照，数字分页要求待整合 | 因果追加顺序，普通整数 page | 公共历史必须有自己的投影与读取契约，不能透传内部页码 |

以上两侧均来自本仓当前精确模型，不是服务端实现事实。本文不新增字段或隐式兼容规则；公共事件 ID、权限与工具名称也需在 bridge 验收中逐项对齐。

## 维护方式

修改一侧契约时同步核对本表及受影响模型。确认结果先整合到唯一契约源，再生成页面、校验与检查图文；未完成的产品选择保留明确状态。新的源码结论必须绑定实际分析提交、仓库路径及符号。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.2.0 | 2026-09-14 | 集中维护未整合要求和桥接差距，更新 Runtime 原子配置目标状态。 |
| 0.1.1 | 2026-09-03 | 登记接口共享决定与跨模块冲突。 |
