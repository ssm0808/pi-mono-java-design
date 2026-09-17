# 服务与接口导航

[返回仓库首页](../README.md)

| 专题 | 解决的问题 | 入口 |
|---|---|---|
| CampusMate 附件服务 | 上传、扫描、OBS/openGauss、删除和 Runtime 文件 ID 边界 | [设计](./01-CampusMate附件服务/README.md) |
| CampusMate 共享客户端配置 | 单一 `campusmate` 配置树、共享 base URL 和 endpoint 去重 | [设计](./02-CampusMate共享客户端配置/README.md) |
| 模型与 Provider | 业务 Agent 模型设置、CampusMate 调用与用量记录 | [主设计](./03-模型与Provider/README.md) · [全局图](./03-模型与Provider/provider-classes.svg) · [用量](./03-模型与Provider/usage.md) |
| Runtime HTTP 测试 Agent | 如何根据已确认契约维护分层回归测试 | [设计](./04-Runtime-HTTP测试Agent/README.md) |
| CampusClaw TDD 测试 Agent | 如何以版本化能力注册表驱动全产品测试与质量门禁 | [设计](./05-CampusClaw-TDD测试Agent/README.md) |
| mate-service 聊天命令 API | GET 轻量清单；公共边界与执行协议待独立重审 | [设计与契约](./06-mate-service聊天命令API/README.md) |
| mate-service 通用对话 Events API | 公共 Chat 提交、live SSE、历史对账及未整合分页要求 | [三接口设计、HTML 与 OpenAPI](./07-mate-service通用对话API/README.md) |

精确 Runtime HTTP 契约位于
[`01-总体架构/01-CampusClaw多Agent运行时/接口契约/`](../01-总体架构/01-CampusClaw多Agent运行时/接口契约/)。
公共聊天命令 GET 展示源位于
[`06-mate-service聊天命令API/接口契约/`](./06-mate-service聊天命令API/接口契约/)。
通用对话 Events 的已确认 operation models 位于
[`07-mate-service通用对话API/接口契约/`](./07-mate-service通用对话API/接口契约/)，
同步的机器契约是
[`chat-events-v1.openapi.yaml`](./07-mate-service通用对话API/chat-events-v1.openapi.yaml)。
