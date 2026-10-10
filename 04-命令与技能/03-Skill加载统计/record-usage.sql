-- Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
-- 待实现 Mapper 片段：绑定参数由受信任结果 DTO 提供，不是独立脚本。
-- 只能在统一 Session 追加事务中、新 LIVE 成功 Skill 结果首次插入后执行。
-- 既有结果重试先核对载荷后返回，不能再次执行下面的加一。
-- 顺序：固定执行/Session 锁 -> 序号 -> Entry/公共事件 -> 本累计 -> 整体提交。
INSERT INTO t_skill_usage_stats (skill_id, activation_count, last_loaded_at)
VALUES (:skill_id, 1, CAST(:completed_at AS TIMESTAMPTZ(0)))
ON DUPLICATE KEY UPDATE
    activation_count = t_skill_usage_stats.activation_count + 1,
    last_loaded_at = GREATEST(t_skill_usage_stats.last_loaded_at, EXCLUDED.last_loaded_at);

-- 历史清理持相同 Session 锁，按 skill_id 排序，在删除来源前同事务登记缺口。
-- min/max 只来自即将删除的 LIVE 成功 Skill 结果；累计行缺失视为一致性错误。
UPDATE t_skill_usage_stats
SET pruned_from = CASE WHEN pruned_from IS NULL THEN CAST(:removed_min AS TIMESTAMPTZ(0))
        ELSE LEAST(pruned_from, CAST(:removed_min AS TIMESTAMPTZ(0))) END,
    pruned_to = CASE WHEN pruned_to IS NULL THEN CAST(:removed_max AS TIMESTAMPTZ(0))
        ELSE GREATEST(pruned_to, CAST(:removed_max AS TIMESTAMPTZ(0))) END
WHERE skill_id = :skill_id;
-- 此 UPDATE 必须影响一行，否则回滚清理；任何 SQL 失败均回滚整个历史事务。
-- 不改工具的真实 isError、不自动重跑工具；回执不确定先按固定结果身份对账。
-- 真实 GaussDB 方言、唯一冲突及事务并发仍待实施验证。
