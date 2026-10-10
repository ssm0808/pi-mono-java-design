-- Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
-- 待实现：新建环境的累计投影片段，不是迁移/删除脚本。
-- 唯一事实复用 t_session_entries，不创建独立 t_skill_usage。
CREATE TABLE t_skill_usage_stats (
    skill_id VARCHAR(64) PRIMARY KEY,
    activation_count BIGINT NOT NULL,
    last_loaded_at TIMESTAMPTZ(0) NOT NULL,
    pruned_from TIMESTAMPTZ(0),
    pruned_to TIMESTAMPTZ(0),
    CONSTRAINT ck_skill_usage_stats_id CHECK (skill_id ~ '^skill-[0-9a-fA-F]{32}$'),
    CONSTRAINT ck_skill_usage_stats_count CHECK (activation_count > 0),
    CONSTRAINT ck_skill_usage_stats_pruned CHECK (
        (pruned_from IS NULL AND pruned_to IS NULL) OR
        (pruned_from IS NOT NULL AND pruned_to IS NOT NULL AND pruned_from <= pruned_to))
);
COMMENT ON TABLE t_skill_usage_stats IS '由统一工具成功结果同事务维护的累计投影，独立于会话保留周期';
COMMENT ON COLUMN t_skill_usage_stats.skill_id IS '结果形成时可信绑定中的 Skill ID';
COMMENT ON COLUMN t_skill_usage_stats.activation_count IS '统一采集覆盖期内已提交真实成功调用的累计次数，删除会话不扣减';
COMMENT ON COLUMN t_skill_usage_stats.last_loaded_at IS '已累计调用的最大最终结果时间，使用 UTC 秒级';
COMMENT ON COLUMN t_skill_usage_stats.pruned_from IS '已删除真实成功结果的最早时间，空值表示尚无此类清理';
COMMENT ON COLUMN t_skill_usage_stats.pruned_to IS '已删除真实成功结果的最晚时间，与起点共同表示保守历史缺口';
-- 精确 from/to 和日表仍待核实；本文件不授权删除已有表或变更公共接口。
