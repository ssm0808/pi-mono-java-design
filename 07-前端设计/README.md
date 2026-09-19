# CampusClaw 前端设计

版本：2.2.0 · 2026-09-19 · 模块 M07

[仓库导航](../README.md) · [打开场景原型](原型/index.html) · [公共规范](公共规范.md) · [技术设计与全局类图](技术设计/README.md)

前端围绕用户完成任务组织：进入会话、提交材料、观察执行，在需要时回答问题、审核方案或授权操作。先选场景查看原型和行为，再按问题下钻技术设计。

## 场景

| 编号 | 场景设计 | 用户目标 | 原型 |
|---|---|---|---|
| 01 | [创建与管理会话](场景/01-创建与管理会话/README.md) | 进入合适的 Agent 会话，并能快速找到、整理已有任务。 | [高](原型/index.html#scene=sessions&fidelity=high) · [低](原型/index.html#scene=sessions&fidelity=low) |
| 02 | [发送消息与附件](场景/02-发送消息与附件/README.md) | 提交目标与材料，确认请求是否被接收，并继续编辑后续草稿。 | [高](原型/index.html#scene=message&fidelity=high) · [低](原型/index.html#scene=message&fidelity=low) |
| 03 | [查看执行与停止](场景/03-查看执行与停止/README.md) | 理解当前进展、查看真实工具结果，并在需要时停止任务。 | [高](原型/index.html#scene=execution&fidelity=high) · [低](原型/index.html#scene=execution&fidelity=low) |
| 04 | [工具授权](场景/04-工具授权/README.md) | 在操作执行前理解影响范围，明确允许或拒绝本次工具调用。 | [高](原型/index.html#scene=permission&fidelity=high) · [低](原型/index.html#scene=permission&fidelity=low) |
| 05 | [回答问题](场景/05-回答问题/README.md) | 逐题澄清目标与约束，完整提交答案后继续原任务。 | [高](原型/index.html#scene=question&fidelity=high) · [低](原型/index.html#scene=question&fidelity=low) |
| 06 | [审核与修改计划](场景/06-审核与修改计划/README.md) | 检查实施范围、步骤、验证和回退方式，再批准实施或提出修改。 | [高](原型/index.html#scene=plan&fidelity=high) · [低](原型/index.html#scene=plan&fidelity=low) |
| 07 | [命令与技能](场景/07-命令与技能/README.md) | 在当前会话快速发现命令、填写参数，并理解命令结果如何影响任务。 | [高](原型/index.html#scene=commands&fidelity=high) · [低](原型/index.html#scene=commands&fidelity=low) |
| 08 | [开发者设置](场景/08-开发者设置/README.md) | 在开发环境配置连接、认证和请求头，理解配置何时生效。 | [高](原型/index.html#scene=settings&fidelity=high) · [低](原型/index.html#scene=settings&fidelity=low) |

[自动刷新交互原型](原型/index.html#scene=message&fidelity=high&state=token-ready)只展示发送进度、失败保留草稿及重试；技术演示选项默认收起，可切换高低保真。

开发工作台发送前自动获取 `access-token` 的目标流程见[认证与发送门禁](技术设计/runtime-workbench-alignment.md#61-页面流程)；该增量待实现，手动获取与配置保存已实现，长任务续期边界单列。

## 阅读与维护

- **场景页**：目标、前置条件、高/低保真入口、交互行为、必要取舍与验收。
- **公共规范**：布局、品牌、组件共性、响应式、键盘和文案；场景页引用共享规则。
- **技术设计**：全局结构、状态与事件投影、服务适配、恢复、渲染及工程验收。
- **源码证据**：实现提交、文件与符号、实际验证范围及差距。

高、低保真由同一份 HTML 和同一套交互状态生成：低保真使用结构框、区域标签和简化视觉，高保真使用产品样式。切换保真度保持当前操作；切换场景或初始状态会重置演示。主线场景使用计划工作台，基础对话与命令专题复用现有夹具。

原型全部使用本地示例数据。每个场景单独列明覆盖范围；Headers 原型覆盖已有编辑器，完整环境设置与保存能力见目标设计。真实实现状态统一见[源码证据](source-evidence.md)，原型通过与产品完成分别验收。

## 设计权威与基线

场景页维护用户行为，公共规范维护跨场景规则，技术设计维护实现约束；HTTP 精确字段和业务生命周期引用所属服务模块。重大取舍保留具体原因，历史迭代通过 Git 与[归档](归档/README.md)追溯。

本次整理基于设计仓 `3e5f1189987c425c9987cce2fc261a5d3c59f1c8`，将两处前端资料统一到本目录。既有源码核验以 `pi-mono-java@1d08f98eb04f8ea6e01bcfbfd4008c1b638391c4` 等分项证据为准；本次迁移未重新核验上游或升级实现结论，Agent 架构对比仅更新引用位置。

## 本地预览与校验

在仓库根目录运行 `python3 -m http.server 8765 --bind 127.0.0.1`，打开 `/07-前端设计/原型/index.html`。原型入口也可直接打开；跨文件框架访问受浏览器本地文件策略限制时使用本地服务。

原型的四个交互回归脚本及场景入口回归脚本位于 `原型/`，使用 Node.js 与 jsdom；运行方法和当前迁移结果见[迁移校验](迁移校验.md)。图纸在 `技术设计/` 与 `技术设计/命令/` 分别执行 `plantuml -tsvg diagram.puml`，然后更新仓库图索引。

## 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.2.0 | 2026-09-19 | 自动刷新使用统一发送反馈，技术演示选项默认折叠。 |
| 2.1.1 | 2026-09-19 | 增加自动刷新 Token 的交互原型与高低保真状态入口。 |
| 2.1.0 | 2026-09-19 | 开发写动作提交前自动获取 Token，补充失败、取消与运行中续期边界。 |
| 2.0.0 | 2026-09-18 | 前端设计独立维护，提供八个场景及共享行为的高低保真入口。 |

[1.x 版本与历史验证](归档/版本与验证记录.md)
