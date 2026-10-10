-- Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
-- Skill 成功调用计数：核心两表的新建环境目标片段，待实现。
-- 不自动执行，不是存量迁移或删除脚本；from/to、日表和保留策略仍待核实。
-- 当前统计时间保持 UTC 毫秒，统一格式的最终接口决定另行核实。

CREATE TABLE t_skill_usage (
    observation_id VARCHAR(36) NOT NULL,
    skill_id VARCHAR(64) NOT NULL,
    loaded_at TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT pk_skill_usage PRIMARY KEY (observation_id),
    CONSTRAINT ck_skill_usage_id CHECK (skill_id ~ '^skill-[0-9a-fA-F]{32}$'),
    CONSTRAINT ck_skill_usage_observation CHECK (length(observation_id) = 36)
);
COMMENT ON TABLE t_skill_usage IS 'Skill 成功调用的最小统计幂等记录，不表示权威业务执行事件';
COMMENT ON COLUMN t_skill_usage.observation_id IS '本次调用的统计技术键；同一记录重复提交保持不变，不是执行或业务事件标识';
COMMENT ON COLUMN t_skill_usage.skill_id IS '本次调用可信绑定的 Skill ID';
COMMENT ON COLUMN t_skill_usage.loaded_at IS '最终成功结束被观察时固定的 UTC 毫秒时间';

CREATE TABLE t_skill_usage_stats (
    skill_id VARCHAR(64) NOT NULL,
    activation_count BIGINT NOT NULL,
    last_loaded_at TIMESTAMPTZ(3) NOT NULL,
    CONSTRAINT pk_skill_usage_stats PRIMARY KEY (skill_id),
    CONSTRAINT ck_skill_usage_stats_id CHECK (skill_id ~ '^skill-[0-9a-fA-F]{32}$'),
    CONSTRAINT ck_skill_usage_stats_count CHECK (activation_count > 0)
);
COMMENT ON TABLE t_skill_usage_stats IS 'Skill 成功调用的累计统计，与 Session 生命周期独立';
COMMENT ON COLUMN t_skill_usage_stats.skill_id IS '被统计的 Skill ID，不随 Agent 或执行入口划分';
COMMENT ON COLUMN t_skill_usage_stats.activation_count IS '已提交成功调用统计记录的累计数量，重复记录不增加';
COMMENT ON COLUMN t_skill_usage_stats.last_loaded_at IS '所有已计调用中最大的成功结束时间';

-- 若确认精确时间范围查询，按数据量和查询计划补 (skill_id, loaded_at) 索引。
-- 若确认保留独立日汇总，将其作为同一事务第三投影逐调用加一。
-- 本片段没有 DROP，不授权取消日表或 from/to，也不替代最终全量发布 DDL。
-- 不关联 Session 外键；不随 Session 删除清理；保留与备份须按统计自身规则验收。
