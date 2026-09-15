-- Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
-- 目标 Mapper 语句片段；所有冒号参数均绑定，禁止拼接。
-- 必须参加 Runtime 来源事件现有的短事务，不在此另开事务或吞异常。
-- 以下前置分支由持有原 Session/执行锁的应用服务执行：
-- 1. 先查询规范来源的既有结果/事实；相同提交直接返回原记录，不运行以下 INSERT 和增量。
-- 2. 相同来源的冲突内容报错；旧来源因保留期缺少事实时不得经正常路径重新入账。
-- 3. 新来源的权威根输入或工具结果及公共投影在本事务内追加。
-- 4. 下列三条语句全部成功后，与来源一起提交；任何异常整笔回滚。
-- 唯一键冲突不能被捕获后继续更新汇总；受影响行数不用于猜测首次 INSERT。

SELECT session_id, source_event_id, skill_id, root_event_id, result_event_id,
       agent_id, invocation_type, occurred_at
FROM t_skill_invocation
WHERE session_id = :session_id AND source_event_id = :source_event_id AND skill_id = :skill_id;

-- 仅在已验证为新来源、新事实的分支执行以下语句。
INSERT INTO t_skill_invocation (
    session_id, source_event_id, skill_id, root_event_id, result_event_id,
    agent_id, invocation_type, occurred_at)
VALUES (
    :session_id, :source_event_id, :skill_id, :root_event_id, :result_event_id,
    :agent_id, :invocation_type, CAST(:occurred_at AS TIMESTAMPTZ(3)));

INSERT INTO t_skill_invocation_stats (skill_id, invocation_count, last_invoked_at)
VALUES (:skill_id, 1, CAST(:occurred_at AS TIMESTAMPTZ(3)))
ON DUPLICATE KEY UPDATE
    invocation_count = t_skill_invocation_stats.invocation_count + 1,
    last_invoked_at = GREATEST(t_skill_invocation_stats.last_invoked_at, EXCLUDED.last_invoked_at);

INSERT INTO t_skill_invocation_daily_stats (stat_date, skill_id, invocation_count, last_invoked_at)
VALUES (
    CAST(CAST(:occurred_at AS TIMESTAMPTZ(3)) AT TIME ZONE 'Asia/Shanghai' AS DATE),
    :skill_id, 1, CAST(:occurred_at AS TIMESTAMPTZ(3)))
ON DUPLICATE KEY UPDATE
    invocation_count = t_skill_invocation_daily_stats.invocation_count + 1,
    last_invoked_at = GREATEST(t_skill_invocation_daily_stats.last_invoked_at, EXCLUDED.last_invoked_at);

-- 使用来源固定时间而不是 CURRENT_TIMESTAMP，重试及跨午夜提交均保留原统计日。
-- openGauss 5.0 是语法参考；实际公司 GaussDB 版本及并发行为须完成集成验收。
