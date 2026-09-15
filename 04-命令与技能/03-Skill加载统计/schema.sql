-- Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
-- Skill 加载统计目标全量安装片段；不自动执行，不是存量迁移脚本。

CREATE TABLE t_skill_load_stats (
    skill_id        VARCHAR(64)   PRIMARY KEY,
    full_load_count BIGINT        NOT NULL,
    last_loaded_at  TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT ck_skill_stats_id CHECK (skill_id ~ '^skill-[0-9a-fA-F]{32}$'),
    CONSTRAINT ck_skill_stats_count CHECK (full_load_count > 0)
);

COMMENT ON TABLE t_skill_load_stats IS 'Skill 自统计启用以来成功记账的全文加载累计值，每个 Skill 一行';
COMMENT ON COLUMN t_skill_load_stats.skill_id IS '受管执行快照中的 Skill ID，跨 Agent、版本及执行入口累计';
COMMENT ON COLUMN t_skill_load_stats.full_load_count IS '累计成功记账的全文加载次数，不是任务采用数';
COMMENT ON COLUMN t_skill_load_stats.last_loaded_at IS '最近一次成功记账采用的数据库事务开始时间，非模型送达时间';

CREATE INDEX idx_skill_stats_count ON t_skill_load_stats (full_load_count DESC, skill_id ASC);
CREATE INDEX idx_skill_stats_last ON t_skill_load_stats (last_loaded_at DESC, skill_id ASC);

CREATE TABLE t_skill_load_daily_stats (
    stat_date       DATE          NOT NULL,
    skill_id        VARCHAR(64)   NOT NULL,
    full_load_count BIGINT        NOT NULL,
    last_loaded_at  TIMESTAMPTZ(3) NOT NULL,
    PRIMARY KEY (stat_date, skill_id),
    CONSTRAINT ck_skill_daily_id CHECK (skill_id ~ '^skill-[0-9a-fA-F]{32}$'),
    CONSTRAINT ck_skill_daily_count CHECK (full_load_count > 0),
    CONSTRAINT ck_skill_daily_date CHECK (
        stat_date = CAST(last_loaded_at AT TIME ZONE 'Asia/Shanghai' AS DATE))
);

COMMENT ON TABLE t_skill_load_daily_stats IS '按 Asia/Shanghai 自然日汇总的 Skill 全文加载次数，无加载的日期不落零值行';
COMMENT ON COLUMN t_skill_load_daily_stats.stat_date IS '统计日期，按本次记账数据库事务时间转换为 Asia/Shanghai 日期';
COMMENT ON COLUMN t_skill_load_daily_stats.skill_id IS '受管执行快照中的 Skill ID，与累计表使用相同标识';
COMMENT ON COLUMN t_skill_load_daily_stats.full_load_count IS '当日成功记账的全文加载次数';
COMMENT ON COLUMN t_skill_load_daily_stats.last_loaded_at IS '该统计日最近一次成功记账采用的数据库事务开始时间';

CREATE INDEX idx_skill_daily_skill_date ON t_skill_load_daily_stats (skill_id, stat_date);

-- 应用角色：两表 SELECT、INSERT、UPDATE，不授予 DELETE。
-- 平台清理角色：日表 SELECT、DELETE；累计表不做时间清理。
-- 精确角色名复用发布平台配置，不在设计中创建运行账号。
