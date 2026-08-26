# pi-mono-java Design

本仓库用于维护 CampusClaw、mate-service 与 pi-mono-java 的目标设计和源码研究。

## 当前规范性设计

- [CampusClaw Runtime 总体设计](./pi-mono-java-manager-driven-multi-agent-runtime/README.md)：两跳 HTTP+SSE、十一项内部 Runtime operation、Manager 与数据边界。
- [CampusClaw Runtime HTTP API](./pi-mono-java-manager-driven-multi-agent-runtime/chat-http-v1-design.md)：接口语义、状态、错误和源码证据。
- [Runtime HTTP API HTML 评审页](./pi-mono-java-manager-driven-multi-agent-runtime/chat-http-v1-review.html)：面向人的主维护契约，可直接在浏览器打开。
- [Runtime HTTP 测试 Agent](./pi-mono-java-http-test-agent/README.md)：基于已确认契约规划、拉起、执行和维护分层回归测试。
- [CampusMate 统一客户端地址配置](./campusmate-shared-client-configuration/README.md)：Model Manager 与受管 Runtime 共享唯一 `campusmate.base-url`，各自保留路径和传输参数。
- [MateService Model Manager Provider](./model-manager-provider-contract/README.md)：通用 Provider、Mate Chat SSE、断连取消与 Usage Record 契约。
- [虚拟线程并发管理](./virtual-thread-concurrency-management/README.md)：内部 active execution、容量准入、背压与 DFX。
- [AgentRuntimeTemplate](./agent-runtime-template/README.md)：不可变 Agent 模板、revision pinning、加载缓存与回收。
- [CampusMate 文件服务](./campusmate-attachment-service/README.md)：文件上传、扫描、OBS/openGauss 边界和内部 Runtime 解析。

Runtime HTTP 接口不维护 OpenAPI。已经确认的 HTML 是人类评审主契约，Markdown
负责设计理由和源码证据。文件服务仍维护独立 OpenAPI；它不能被当作 Runtime
OpenAPI，也不能恢复已经废弃的 Run 或 WebSocket 资源。

## 支撑设计

- [Agent 数据库模式](./agent-database-patterns/README.md)
- [Agent 元数据 GaussDB 表设计](./agent-metadata-gaussdb-design/README.md)
- [集中式 GaussDB 会话记忆](./memory-jsonl-to-gaussdb.md)
- [Command SR 设计](./pi-mono-java-command-SR设计.md)
- [Skill Command SR 设计](./pi-mono-java-skill-command-SR设计.md)

## 源码与产品研究

- [pi Session Context 与当前分支](./pi-mono-agent-session-context/README.md)
- [pi SessionSnapshot 类图与语义](./pi/session-snapshot.md)
- [主流 Agent Tool/Agent 元数据机制](./config-to-tool-agent-research/README.md)
- [Anthropic Managed Agents 公开模型](./anthropic-managed-agents-public-model/README.md)
- [主流 Agent 平台 Agent、Tool 与 Skill 官方文档](./主流Agent平台Agent-Tool-Skill创建官方文档.md)

## 已废弃内容

当前目标传输统一为 HTTP+SSE。WebSocket、AsyncAPI、连接级 resume、公开 Run、
Run Events、RunRecord 和旧 Channel 方案已经从工作树清除；如需追溯只能查看 Git
历史。新实现不得从历史文件恢复这些模型。

## 文档约定

- 设计文档使用 Markdown；接口 HTML 是 Runtime HTTP 的人类评审主契约。
- 设计图使用 PlantUML，统一维护 `diagram.puml` 并提交生成后的 SVG；禁止手改 SVG。
- PlantUML 图源只使用英文 ASCII；Markdown 正文和图注可以使用中文。
- 源码对齐设计记录固定 commit、仓库相对路径和相关符号或基线行号。
- 区分源码观察、目标设计和设计原因；差异标记为产品约束、安全加固或架构改造。
- 数据库表使用 `t_` 前缀和小写 snake_case，SQL `COMMENT ON` 使用中文。
- 设计行为变更同步更新文档版本和版本历史。
