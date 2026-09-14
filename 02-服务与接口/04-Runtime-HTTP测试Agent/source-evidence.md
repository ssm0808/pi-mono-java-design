# Runtime HTTP 回归：历史源码证据

版本：1.0.0 · 2026-09-14。返回[适配器主设计](README.md)。

以下均是 `pi-mono-java` 提交 `1f801dbb82bdda30478e3354e685e3153b179a0c` 的已观察行为。

| 观察项 | 源码证据 | 结论 |
|---|---|---|
| 11 个 HTTP operation | `RuntimeSessionController` 51-78、`RuntimeEventController` 58-86、`RuntimeSessionConfigurationController` 55-82、`RuntimeSessionControlController` 50-75 | 已使用 Spring MVC Controller 实现 |
| 调用上下文边界 | `RuntimeRequestAuthenticator.authenticate`、`RuntimeWebMvcConfiguration.addInterceptors` 27-30 | 该提交的 JWT/APPKEY 形状校验覆盖全部 V1 路径；1.37.0 目标全部移除 Runtime 本地认证 |
| 错误与语言 | `RuntimeExceptionHandler` 42-93、`RuntimeRequestContext` 30-37 | 异常无 `result`，支持 `zh-CN/en-US`，部分错误带 `Retry-After` |
| 请求严格性 | `UserEventRequestVO` 23-48、`ChangeModelRequestVO` 25-57、`ChangeThinkingRequestVO` 22-52、`ControlMessageRequestVO` 23-54 | 写请求拒绝未知字段；类型和长度由 Jackson/Bean Validation/Service 共同约束 |
| Event 业务约束 | `RuntimeEventService.validate` 381-392、`parseLimit` 411-427 | message/file_ids 至少一个、文件 ID 唯一、分页范围 1..200 |
| HTTP 契约测试 | `RuntimeSessionRoutesTest`、`RuntimeEventRoutesTest`、`RuntimeSessionConfigurationRoutesTest`、`RuntimeSessionControlRoutesTest` | 已覆盖主要成功形状和少量错误 |
| 真实进程验证 | `RuntimeHttpProcessOpenGaussIT.packagedJarStreamsAndPagesPersistedEvents` 62-91 | 一个长场景覆盖打包 JAR、HTTP/SSE、模型桩和 openGauss |
| 数据库验证 | `RuntimeSessionRepositoryOpenGaussIT` | 覆盖事务、序号、当前分支、tombstone 和并发 CAS |
| 默认 CI | `.github/workflows/ci.yml` 1-26 | 只执行 Spotless 和 `./mvnw -B verify` |
| Maven IT 装配 | 根 POM 只配置 Surefire；没有 Failsafe execution | `*IT` 默认不随 `verify` 执行 |
| IT 前置条件 | `RuntimeHttpProcessOpenGaussIT` 64-66、537-556 | 未提供 JAR/数据库属性时使用 assumption 跳过 |

在 Runtime API 测试目录中共有 78 个 `@Test`，数量说明已有良好基础，但“有测试代码”
不等于“每次改动都执行”。该基线的主要缺口不是重新造一套测试框架，而是把现有测试转换成
不可静默跳过的持续质量门禁，并补齐契约到用例的追踪关系。

## 固定提交中的差距

1. HTML 主契约没有自动投影为测试清单，新增/删除路由不会直接触发契约漂移失败。
2. `*IT` 没有绑定 Failsafe；默认 `verify` 不运行真实数据库和跨进程用例。
3. 真实进程 IT 依赖外部系统属性并允许 skip，CI 没有自动拉起 openGauss。
4. 11 个 operation 的调用上下文透传、两种语言、错误码和严格字段矩阵没有统一参数化。
5. 跨进程场景集中在一个长测试中；失败时定位成本高，也难按变更影响选择子场景。
6. 没有“测试断言被削弱”“测试数量下降但无契约变更”“已废弃路由复活”的独立门禁。
7. `modules/*` 与 `mate-campusclaw` 是同步镜像，该基线缺少一次生成、分层复用和差异检查策略，
   容易重复耗时或漏测镜像装配。
8. 没有对客户端断线后执行继续、流内错误、容量失败、数据库故障和进程重启形成统一的
   可复现证据包。
9. 1.37.0 的类型化 Agent/Session ID、初始 `thinking=true`、无 Runtime 本地认证、受控 thinking
   事件投影和 Submit 请求删除 `type` 尚未实现；首轮 L0 必须报告实现漂移，而不能因旧测试
   全绿而通过。


## 仓库相对路径索引

下表按明示前缀展开为完整仓库相对路径，文件名即同名类型；符号和行号见上表。

- M = `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/runtimeapi/`
- T = `modules/coding-agent-cli/src/test/java/com/campusclaw/codingagent/runtimeapi/`

| 前缀 | 相对文件 |
|---|---|
| M | `web/RuntimeSessionController.java` |
| M | `web/RuntimeEventController.java` |
| M | `web/RuntimeSessionConfigurationController.java` |
| M | `web/RuntimeSessionControlController.java` |
| M | `auth/RuntimeRequestAuthenticator.java` |
| M | `web/RuntimeWebMvcConfiguration.java` |
| M | `web/RuntimeExceptionHandler.java` |
| M | `web/RuntimeRequestContext.java` |
| M | `vo/UserEventRequestVO.java` |
| M | `vo/ChangeModelRequestVO.java` |
| M | `vo/ChangeThinkingRequestVO.java` |
| M | `vo/ControlMessageRequestVO.java` |
| M | `event/RuntimeEventService.java` |
| T | `web/RuntimeSessionRoutesTest.java` |
| T | `web/RuntimeEventRoutesTest.java` |
| T | `web/RuntimeSessionConfigurationRoutesTest.java` |
| T | `web/RuntimeSessionControlRoutesTest.java` |
| T | `web/RuntimeHttpProcessOpenGaussIT.java` |
| T | `persistence/RuntimeSessionRepositoryOpenGaussIT.java` |

旧文档另记首版执行器与仓库 Skill 位于 `codex/campusclaw-tdd-agent`，但该实现记录未给出不可变提交；执行器、固定 digest openGauss 和 Failsafe 的最新落地状态须单独核验，不能由上述产品源码基线证明。
