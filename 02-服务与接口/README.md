# 服务与接口导航

[返回仓库首页](../README.md)

| 专题 | 解决的问题 | 入口 |
|---|---|---|
| CampusMate 附件服务 | 上传、扫描、OBS/openGauss、删除和 Runtime 文件 ID 边界 | [设计](./01-CampusMate附件服务/README.md) |
| CampusMate 共享客户端配置 | 单一 `campusmate` 配置树、共享 base URL 和 endpoint 去重 | [设计](./02-CampusMate共享客户端配置/README.md) |
| 模型管理 Provider 契约 | Model Manager、Chat SSE、断连取消和 Usage 持久化 | [设计](./03-模型管理Provider契约/README.md) |
| Runtime HTTP 测试 Agent | 如何根据已确认契约维护分层回归测试 | [设计](./04-Runtime-HTTP测试Agent/README.md) |
| CampusClaw TDD 测试 Agent | 如何以版本化能力注册表驱动全产品测试与质量门禁 | [设计](./05-CampusClaw-TDD测试Agent/README.md) |
| mate-service 聊天命令 API | 公共 Chat 命令清单、结构化执行、鉴权和 SSE 重新投影 | [设计与契约](./06-mate-service聊天命令API/README.md) |
| mate-service 通用对话 Events API | 公共 Chat 事件提交、Chat 级 live SSE、固定快照历史和断线对账 | [三接口设计、HTML 与 OpenAPI](./07-mate-service通用对话API/README.md) |

精确 Runtime HTTP 契约位于
[`01-总体架构/01-CampusClaw多Agent运行时/接口契约/`](../01-总体架构/01-CampusClaw多Agent运行时/接口契约/)。
公共聊天命令契约位于
[`06-mate-service聊天命令API/接口契约/`](./06-mate-service聊天命令API/接口契约/)。
通用对话 Events 的已确认 operation models 位于
[`07-mate-service通用对话API/接口契约/`](./07-mate-service通用对话API/接口契约/)，
同步的机器契约是
[`chat-events-v1.openapi.yaml`](./07-mate-service通用对话API/chat-events-v1.openapi.yaml)。
