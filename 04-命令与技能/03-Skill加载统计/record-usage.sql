-- Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
-- 目标 Mapper 语句片段，参数全部绑定；不是可直接运行的批处理。
-- Runtime 主事务必须已结束。由另一 Spring Bean 的 REQUIRES_NEW 方法执行本统计事务。
-- 外层 Tracker 捕获事务代理返回的异常；事务内不得吞异常后继续更新。
-- 每次只处理一个 Skill；锁顺序：Session 生命周期锁、事实、累计、日表。

-- 应用先验证 Session 存在且未进入删除/tombstone；行锁与现有删除路径共用。
SELECT id, agent_id FROM t_sessions WHERE id = :session_id FOR UPDATE;
-- 无行、已关闭准入或归属不匹配：结束统计事务，不执行 INSERT。
-- 使用实际根身份。此查询不再锁执行行，避免与 Runtime 产生反向锁依赖。
SELECT root_event_id FROM t_session_executions
WHERE session_id = :session_id AND root_event_id = :root_event_id AND state = 'RUNNING';
-- 无行：跳过统计。不得因为失败而改变主执行状态。

SELECT source_event_id, signal_type, occurred_at
FROM t_skill_usage
WHERE session_id = :session_id AND root_event_id = :root_event_id AND skill_id = :skill_id;
-- 已存在：正常重复，原事实及两张汇总保持不变，直接返回 ALREADY_RECORDED。
-- 同根/Skill 的来源、类型、时间不同是正常的后续信号，不覆盖首次事实。

-- 仅上述准入成功且事实不存在的分支执行以下三条语句。
INSERT INTO t_skill_usage (
    session_id, root_event_id, skill_id, source_event_id, agent_id, signal_type, occurred_at)
VALUES (
    :session_id, :root_event_id, :skill_id, :source_event_id, :agent_id, :signal_type,
    CAST(:occurred_at AS TIMESTAMPTZ(3)));
-- INSERT 主键冲突必须回滚整个统计事务，后两条不得执行。
-- 事务结束后只将明确 pk_skill_usage 冲突归为重复，其他错误记录失败。
-- 不使用 UPSERT/受影响行数来判断事实是否首次插入。

INSERT INTO t_skill_usage_stats (skill_id, usage_count, last_used_at)
VALUES (:skill_id, 1, CAST(:occurred_at AS TIMESTAMPTZ(3)))
ON DUPLICATE KEY UPDATE
    usage_count = t_skill_usage_stats.usage_count + 1,
    last_used_at = GREATEST(t_skill_usage_stats.last_used_at, EXCLUDED.last_used_at);

INSERT INTO t_skill_usage_daily_stats (stat_date, skill_id, usage_count, last_used_at)
VALUES (
    CAST(CAST(:occurred_at AS TIMESTAMPTZ(3)) AT TIME ZONE 'Asia/Shanghai' AS DATE),
    :skill_id, 1, CAST(:occurred_at AS TIMESTAMPTZ(3)))
ON DUPLICATE KEY UPDATE
    usage_count = t_skill_usage_daily_stats.usage_count + 1,
    last_used_at = GREATEST(t_skill_usage_daily_stats.last_used_at, EXCLUDED.last_used_at);

-- 三表全部成功才提交；任何语句或提交失败只影响本统计事务，不回滚 Runtime。
-- 使用候选固定时间，不用 CURRENT_TIMESTAMP；同根跨天重复不加日计数或刷新最近时间。
-- openGauss 5.0 为语法参考；公司 GaussDB 的主键异常映射、并发和等待预算须集成验收。
