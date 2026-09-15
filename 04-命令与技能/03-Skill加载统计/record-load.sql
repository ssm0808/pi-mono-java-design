-- Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
-- 目标事务示意；:skill_id 为绑定参数，不做字符串拼接。
-- 应用通过独立 Spring 事务 Bean 执行两条 Mapper 语句，不在 Mapper 中提交事务。
-- 同一次调用两表共用毫秒精度的 CURRENT_TIMESTAMP；先累计、后按日，整笔提交或回滚。
-- 先统一转换为 TIMESTAMPTZ(3)，再取统计日，避免午夜精度舍入造成日期约束不一致。

BEGIN;

INSERT INTO t_skill_load_stats (skill_id, full_load_count, last_loaded_at)
VALUES (:skill_id, 1, CAST(CURRENT_TIMESTAMP AS TIMESTAMPTZ(3)))
ON DUPLICATE KEY UPDATE
    full_load_count = t_skill_load_stats.full_load_count + 1,
    last_loaded_at = GREATEST(t_skill_load_stats.last_loaded_at, EXCLUDED.last_loaded_at);

INSERT INTO t_skill_load_daily_stats (stat_date, skill_id, full_load_count, last_loaded_at)
VALUES (
    CAST(CAST(CURRENT_TIMESTAMP AS TIMESTAMPTZ(3)) AT TIME ZONE 'Asia/Shanghai' AS DATE),
    :skill_id, 1, CAST(CURRENT_TIMESTAMP AS TIMESTAMPTZ(3)))
ON DUPLICATE KEY UPDATE
    full_load_count = t_skill_load_daily_stats.full_load_count + 1,
    last_loaded_at = GREATEST(t_skill_load_daily_stats.last_loaded_at, EXCLUDED.last_loaded_at);

COMMIT;
