-- Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
-- 待实现的 Mapper 语句片段：仅使用绑定参数，不是直接执行的批处理。
-- 由后台线程调用独立 Spring 事务 Bean；不在 Agent 事件线程执行 JDBC。
-- 锁/写入顺序为统计幂等记录、累计表；完全不读锁 Session 或执行表。

INSERT INTO t_skill_usage (observation_id, skill_id, loaded_at)
VALUES (:observation_id, :skill_id, CAST(:completed_at AS TIMESTAMPTZ(3)));
-- 普通 INSERT 失败立即使整笔事务回滚，不执行下面的累计更新。
-- 事务代理外仅把明确 pk_skill_usage 唯一冲突视为重复，其他错误记失败。
-- 同 observation_id 的载荷必须相同；需要诊断不同载荷复用时在回滚后读取比较，不更新原事实。

INSERT INTO t_skill_usage_stats (skill_id, activation_count, last_loaded_at)
VALUES (:skill_id, 1, CAST(:completed_at AS TIMESTAMPTZ(3)))
ON DUPLICATE KEY UPDATE
    activation_count = t_skill_usage_stats.activation_count + 1,
    last_loaded_at = GREATEST(t_skill_usage_stats.last_loaded_at, EXCLUDED.last_loaded_at);

-- 两表成功才提交；任何语句或提交失败不返回 Agent 工具错误、不自动重试工具。
-- observation_id 在 Start 创建并随同一记录复用；completed_at 在成功 End 固定。
-- 与 #335 已有 Mapper 相同的 openGauss UPSERT 方言；公司 GaussDB 版本仍须集成验收。
-- 若日投影保留，在本事务中增加第三投影后整体提交；由查询范围核实决定。
