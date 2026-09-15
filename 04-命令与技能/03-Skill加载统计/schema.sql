-- Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
-- Skill 调用统计目标全量安装片段；不自动执行，不是存量迁移脚本。
-- 首版范围为 Runtime；Skill、Session 和事件身份由已有权威服务提供。

CREATE TABLE t_skill_invocation (
    session_id       VARCHAR(128)   NOT NULL,
    source_event_id  VARCHAR(128)   NOT NULL,
    skill_id         VARCHAR(64)    NOT NULL,
    root_event_id    VARCHAR(128)   NOT NULL,
    result_event_id  VARCHAR(128),
    agent_id         VARCHAR(64)    NOT NULL,
    invocation_type  VARCHAR(16)    NOT NULL,
    occurred_at      TIMESTAMPTZ(3) NOT NULL,
    PRIMARY KEY (session_id, source_event_id, skill_id),
    CONSTRAINT ck_skill_invocation_id CHECK (skill_id ~ '^skill-[0-9a-fA-F]{32}$'),
    CONSTRAINT ck_skill_invocation_source CHECK (
        (invocation_type = 'EXPLICIT' AND source_event_id = root_event_id AND result_event_id IS NULL)
        OR (invocation_type = 'READ' AND source_event_id <> root_event_id
            AND result_event_id IS NOT NULL AND result_event_id <> source_event_id)),
    CONSTRAINT ck_skill_invocation_required CHECK (
        length(session_id) > 0 AND length(source_event_id) > 0
        AND length(root_event_id) > 0 AND length(agent_id) > 0
        AND (result_event_id IS NULL OR length(result_event_id) > 0))
);

COMMENT ON TABLE t_skill_invocation IS 'Runtime 成功 Skill 指令交付事实，来源事件与 Skill 唯一，不代表任务成功';
COMMENT ON COLUMN t_skill_invocation.session_id IS '本次 Runtime Session 的权威标识';
COMMENT ON COLUMN t_skill_invocation.source_event_id IS '显式调用的根消息事件或 Read 的规范工具调用事件，不使用 Provider toolCallId';
COMMENT ON COLUMN t_skill_invocation.skill_id IS '实际执行快照中已验证的 Skill ID，精确匹配';
COMMENT ON COLUMN t_skill_invocation.root_event_id IS '原 user.message 的事件 ID，确认及计划续跑不换根';
COMMENT ON COLUMN t_skill_invocation.result_event_id IS 'Read 对应的成功工具结果事件 ID，显式注入为空';
COMMENT ON COLUMN t_skill_invocation.agent_id IS '实际执行 Agent ID，来自可信 Session 和执行快照';
COMMENT ON COLUMN t_skill_invocation.invocation_type IS '成功交付来源：EXPLICIT 为显式注入，READ 为主文档读取';
COMMENT ON COLUMN t_skill_invocation.occurred_at IS '来源权威记录的服务端 UTC 毫秒时间，重试时保持原值';

CREATE INDEX idx_skill_invocation_time ON t_skill_invocation (skill_id, occurred_at);
CREATE INDEX idx_skill_invocation_root ON t_skill_invocation (session_id, root_event_id, skill_id);

CREATE TABLE t_skill_invocation_stats (
    skill_id         VARCHAR(64)    PRIMARY KEY,
    invocation_count BIGINT         NOT NULL,
    last_invoked_at  TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT ck_skill_invocation_stats_id CHECK (skill_id ~ '^skill-[0-9a-fA-F]{32}$'),
    CONSTRAINT ck_skill_invocation_stats_count CHECK (invocation_count > 0)
);

COMMENT ON TABLE t_skill_invocation_stats IS 'Runtime Skill 成功调用的生命周期累计，每个已调用 Skill 一行';
COMMENT ON COLUMN t_skill_invocation_stats.skill_id IS '与调用事实一致的 Skill ID';
COMMENT ON COLUMN t_skill_invocation_stats.invocation_count IS '功能启用以来已提交成功调用事实的累计数';
COMMENT ON COLUMN t_skill_invocation_stats.last_invoked_at IS '所有已计事实的最近 occurred_at';

CREATE INDEX idx_skill_invocation_stats_count ON t_skill_invocation_stats (invocation_count DESC, skill_id ASC);
CREATE INDEX idx_skill_invocation_stats_last ON t_skill_invocation_stats (last_invoked_at DESC, skill_id ASC);

CREATE TABLE t_skill_invocation_daily_stats (
    stat_date        DATE           NOT NULL,
    skill_id         VARCHAR(64)    NOT NULL,
    invocation_count BIGINT         NOT NULL,
    last_invoked_at  TIMESTAMPTZ(3) NOT NULL,
    PRIMARY KEY (stat_date, skill_id),
    CONSTRAINT ck_skill_invocation_daily_id CHECK (skill_id ~ '^skill-[0-9a-fA-F]{32}$'),
    CONSTRAINT ck_skill_invocation_daily_count CHECK (invocation_count > 0),
    CONSTRAINT ck_skill_invocation_daily_date CHECK (
        stat_date = CAST(last_invoked_at AT TIME ZONE 'Asia/Shanghai' AS DATE))
);

COMMENT ON TABLE t_skill_invocation_daily_stats IS '按 Asia/Shanghai 自然日汇总的 Runtime Skill 成功调用次数';
COMMENT ON COLUMN t_skill_invocation_daily_stats.stat_date IS '调用 occurred_at 转换为 Asia/Shanghai 后的日期';
COMMENT ON COLUMN t_skill_invocation_daily_stats.skill_id IS '与调用事实和累计表一致的 Skill ID';
COMMENT ON COLUMN t_skill_invocation_daily_stats.invocation_count IS '该日已提交成功调用事实数，无调用日不落零值行';
COMMENT ON COLUMN t_skill_invocation_daily_stats.last_invoked_at IS '该统计日最近一次调用 occurred_at';

CREATE INDEX idx_skill_invocation_daily_skill ON t_skill_invocation_daily_stats (skill_id, stat_date);

-- 应用角色：事实表 SELECT/INSERT，汇总两表 SELECT/INSERT/UPDATE。
-- 删除 Session 和平台保留策略的专用清理路径按需取得事实表 DELETE；日表清理另按部署策略授权。
-- 不与远端 Skill 主数据建外键，不因 Session 删除级联扣减汇总。
-- 精确角色名复用发布平台配置；没有配置保留策略时不自动清理。
