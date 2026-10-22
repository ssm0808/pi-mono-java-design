# 智能体本地目录：源码与基线证据

[返回设计](README.md)

| 属性 | 值 |
|---|---|
| 文档版本 | 1.0.0 |
| 更新日期 | 2026-10-22 |

<a id="source-evidence"></a>

## 1. CampusClaw 源码

基线：`pi-mono-java` main `3ade086fcbbe1f88b6729ef5f85d0e595d5b9421`（2026-10-22 fetch）。删除 `refresh` 的变更在 [#381](https://github.com/superheromeZzh/pi-mono-java/pull/381)，head `e5126ac355b208fb00a4eabbda4fcc739669b31e`。路径前缀 `modules/coding-agent-cli/src/main/java/com/campusclaw/codingagent/` 省略为 `…/`。

| # | 位置与符号 | 观察结果 |
|---|---|---|
| J-LD-01 | `…/runtime/AgentRuntimeManager.java` · `prepare`、`prepareCached`、`withAgentLock` | `prepare` 在锁内先 `loadIfComplete`，为空才 `rebuild`；`prepareCached` 只 `loadIfComplete`；锁是 `ConcurrentHashMap<String, ReentrantLock>`，单进程内有效 |
| J-LD-02 | 同文件 · `refresh` | main 上存在但没有生产调用方（`git grep` 仅测试使用）；#381 删除 |
| J-LD-03 | 同文件 · `rebuild`、`loadExistingModeOverrides`、`writeRuntimeTree` | 先读已有 `PLAN.md`、`BUILD.md`，再查 Mate，写同级 `.campusclaw-stage-*`，把模式文件一并写入 |
| J-LD-04 | 同文件 · `loadSnapshot`、`validSnapshot`、`containsForbiddenEntry` | 候选目录和已发布目录用同一读取规则；符号链接或 `tools.json` 使目录无效 |
| J-LD-05 | 同文件 · `loadSettings`、`hasPublishedRuntimeFiles` | `settings.json` 读取或校验失败时，如果 `agent.json`、`settings.json`、`SYSTEM.md` 任一存在就抛 `AgentRuntimeException`，不返回空，因而不重建 |
| J-LD-06 | 同文件 · `publish`、`rollbackPublish`、`moveAtomically` | 旧目录 `ATOMIC_MOVE` 到 `.campusclaw-backup-*`，候选目录 `ATOMIC_MOVE` 到 `.campusclaw`；失败删除新目录并移回备份；文件系统不支持原子移动时报错 |
| J-LD-07 | 同文件 · `requireAgentRoot`、`validatePath` | 校验 ID 格式与路径段，两端取 canonical path，要求结果等于 `根目录/{agentId}` |
| J-LD-08 | 同文件 · `AgentSettings`、`validSettings`、`toSettings` | 当前 `settings.json` 含 `defaultModel`、`bindingModels`、`bindingTools`、`mode`，校验要求模型非空且默认模型在列表中 |
| J-LD-09 | `…/runtime/PreparedAgentRuntime.java` | 不可变 record：`agentId`、`agentRoot`、`metadata`、`skills`、`prompts`、`defaultModelId` |
| J-LD-10 | `…/runtimeapi/agent/FileAgentDirectoryResolver.java` · `prepare`、`resolve`；`AgentDirectoryResolver.toPrepareErrorCode` | HTTP 侧准备入口；Mate 不可用映射 `AGENT_SERVICE_UNAVAILABLE`，其他 `AGENT_NOT_AVAILABLE` |
| J-LD-11 | `…/session/AgentSessionFactory.java` · `create` | Runtime、定时执行、Subagent 共用，调用 `prepare` |
| J-LD-12 | `…/runtimeapi/service/command/SkillCommandSource.java`、`readonly/AgentHelpQueryService.java`、`readonly/BoundSkillQueryService.java` | 调用 `prepareCached`，只读本地副本 |
| J-LD-13 | `modules/coding-agent-cli/src/main/resources/application.yml` · `campusmate.runtime` | `agents-root` 默认 `agent`，连接 10 秒、请求 30 秒、响应上限 4194304 字节 |
| J-LD-14 | `modules/common/src/main/java/com/campusclaw/common/constant/ClawConstants.java` · `AGENT_RUNTIME_PATH_TEMPLATE`、`SKILL_INFO_PATH_TEMPLATE` | `/mate-service/v1/agents/%s/runtime`、`/mate-service/v1/skill/query/%s` |

测试证据（#381 head）：`AgentRuntimeManagerTest.deletingIdentityRebuildsFromMateAndPreservesBothModeOverrides` 证明删除 `agent.json` 后重建并保留两份模式文件；`shouldRejectOldCacheWhenAgentToolBindingsAreMissing` 证明 `settings.json` 缺字段时准备失败；`shouldRejectOldCacheWhenSkillToolBindingsAreMissing` 证明 `skill.json` 缺字段时重建。

<a id="baseline-evidence"></a>

## 2. 基线

| 基线 | 版本与日期 | 位置与符号 | 观察结果 |
|---|---|---|---|
| Claude Managed Agents | 中文公开文档，2026-10-22 读取 | [定义您的智能体](https://platform.claude.com/docs/zh-CN/managed-agents/agent-setup)、[启动会话](https://platform.claude.com/docs/zh-CN/managed-agents/sessions) | 智能体是“可复用、带版本控制的配置”，打包模型、系统提示、工具、MCP 服务器和技能；配置变化时生成新版本；以字符串 ID 创建会话使用最新版本，可传对象固定版本；会话响应中的 `agent` 是“应用了覆盖后的已解析快照”。只证明公开契约，不推断服务端存储 |
| pi | `badlogic/pi-mono` main `476a303c1250ce002215bfd08bdab5f6886f0573`，2026-10-22 | `packages/coding-agent/src/config.ts` · `getAgentDir`；`packages/coding-agent/src/core/resource-loader.ts` · `discoverSystemPromptFile`、`reload`；`packages/coding-agent/src/core/slash-commands.ts` · `reload` | 配置目录是本机 `~/.pi/agent/`（含 `SYSTEM.md`、`settings.json`、技能），项目级 `.pi/SYSTEM.md` 优先；用户执行 `/reload` 才重新读取 |
| Codex | `openai/codex` main `94350a910143c406013683ae634708320f93f1f6`，2026-10-22 | `codex-rs/skills/src/lib.rs` · `install_system_skills`、`embedded_system_skills_fingerprint` | 内置技能写入 `CODEX_HOME/skills/.system`，用内容指纹 marker 判断；不一致时先删除旧目录再写入，不是原子替换 |
| OpenCode | `sst/opencode` dev `b42c31613fdcbd220e859bea357fea48260a6c7a`，2026-10-22 | `packages/core/src/skill/discovery.ts` · `pull`；`packages/core/src/config/plugin/skill.ts` · `load` | 远端技能按 URL 拉到全局缓存 `skills/<hash>/`；每次加载取远端索引，`.opencode-version` 不同才下载到 `.tmp-*`，旧目录改名 `.old-*` 后替换，失败改回 |

## 3. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-10-22 | 记录智能体本地目录的源码与四个基线的核验结果。 |
