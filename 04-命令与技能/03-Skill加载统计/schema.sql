-- Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
-- Skill 使用统计目标全量安装片段；不自动执行，不是存量迁移脚本。
-- 首版范围为 Runtime；Skill、Session 和事件身份由已有权威服务提供。

CREATE TABLE t_skill_usage (
    session_id       VARCHAR(128)   NOT NULL,
    source_event_id  VARCHAR(128)   NOT NULL,
    skill_id         VARCHAR(64)    NOT NULL,
    root_event_id    VARCHAR(128)   NOT NULL,
    agent_id         VARCHAR(64)    NOT NULL,
    signal_type      VARCHAR(16)    NOT NULL,
    occurred_at      TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT pk_skill_usage PRIMARY KEY (session_id, root_event_id, skill_id),
    CONSTRAINT ck_skill_usage_id CHECK (skill_id ~ '^skill-[0-9a-fA-F]{32}$'),
    CONSTRAINT ck_skill_usage_source CHECK (
        (signal_type = 'EXPLICIT' AND source_event_id = root_event_id)
        OR (signal_type = 'READ' AND source_event_id <> root_event_id)),
    CONSTRAINT ck_skill_usage_required CHECK (
        length(session_id) > 0 AND length(source_event_id) > 0
        AND length(root_event_id) > 0 AND length(agent_id) > 0)
);

COMMENT ON TABLE t_skill_usage IS 'Runtime 根执行内首次入账的 Skill 使用信号，根执行与 Skill 唯一，不代表任务成功';
COMMENT ON COLUMN t_skill_usage.session_id IS '本次 Runtime Session 的权威标识';
COMMENT ON COLUMN t_skill_usage.source_event_id IS '显式调用的根消息事件或 Read 的规范工具调用事件，不使用 Provider toolCallId';
COMMENT ON COLUMN t_skill_usage.skill_id IS '实际执行快照中已验证的 Skill ID，精确匹配';
COMMENT ON COLUMN t_skill_usage.root_event_id IS '原 user.message 的事件 ID，确认及计划续跑不换根';
COMMENT ON COLUMN t_skill_usage.agent_id IS '实际执行 Agent ID，来自可信 Session 和执行快照';
COMMENT ON COLUMN t_skill_usage.signal_type IS '首次使用信号来源：EXPLICIT 为显式注入，READ 为主文档读取';
COMMENT ON COLUMN t_skill_usage.occurred_at IS '首次入账信号的服务端 UTC 毫秒时间，候选形成后固定';

CREATE INDEX idx_skill_usage_time ON t_skill_usage (skill_id, occurred_at);

CREATE TABLE t_skill_usage_stats (
    skill_id         VARCHAR(64)    PRIMARY KEY,
    usage_count      BIGINT         NOT NULL,
    last_used_at     TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT ck_skill_usage_stats_id CHECK (skill_id ~ '^skill-[0-9a-fA-F]{32}$'),
    CONSTRAINT ck_skill_usage_stats_count CHECK (usage_count > 0)
);

COMMENT ON TABLE t_skill_usage_stats IS 'Runtime Skill 使用的生命周期累计，每个已使用 Skill 一行';
COMMENT ON COLUMN t_skill_usage_stats.skill_id IS '与使用事实一致的 Skill ID';
COMMENT ON COLUMN t_skill_usage_stats.usage_count IS '功能启用以来已提交使用事实的累计数';
COMMENT ON COLUMN t_skill_usage_stats.last_used_at IS '所有已计事实的最近 occurred_at';

CREATE INDEX idx_skill_usage_stats_count ON t_skill_usage_stats (usage_count DESC, skill_id ASC);
CREATE INDEX idx_skill_usage_stats_last ON t_skill_usage_stats (last_used_at DESC, skill_id ASC);

CREATE TABLE t_skill_usage_daily_stats (
    stat_date        DATE           NOT NULL,
    skill_id         VARCHAR(64)    NOT NULL,
    usage_count      BIGINT         NOT NULL,
    last_used_at     TIMESTAMPTZ(3) NOT NULL,
    PRIMARY KEY (stat_date, skill_id),
    CONSTRAINT ck_skill_usage_daily_id CHECK (skill_id ~ '^skill-[0-9a-fA-F]{32}$'),
    CONSTRAINT ck_skill_usage_daily_count CHECK (usage_count > 0),
    CONSTRAINT ck_skill_usage_daily_date CHECK (
        stat_date = CAST(last_used_at AT TIME ZONE 'Asia/Shanghai' AS DATE))
);

COMMENT ON TABLE t_skill_usage_daily_stats IS '按 Asia/Shanghai 自然日汇总的 Runtime Skill 使用次数';
COMMENT ON COLUMN t_skill_usage_daily_stats.stat_date IS '首次使用 occurred_at 转换为 Asia/Shanghai 后的日期';
COMMENT ON COLUMN t_skill_usage_daily_stats.skill_id IS '与使用事实和累计表一致的 Skill ID';
COMMENT ON COLUMN t_skill_usage_daily_stats.usage_count IS '该日已提交使用事实数，无使用事实日不落零值行';
COMMENT ON COLUMN t_skill_usage_daily_stats.last_used_at IS '该统计日已计使用事实的最近 occurred_at';

CREATE INDEX idx_skill_usage_daily_skill ON t_skill_usage_daily_stats (skill_id, stat_date);

-- 应用角色：事实表 SELECT/INSERT，汇总两表 SELECT/INSERT/UPDATE。
-- 删除 Session 和平台保留策略的专用清理路径按需取得事实表 DELETE；日表清理另按部署策略授权。
-- 不与远端 Skill 主数据建外键，不因 Session 删除级联扣减汇总。
-- 精确角色名复用发布平台配置；没有配置保留策略时不自动清理。
