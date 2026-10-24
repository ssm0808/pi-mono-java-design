-- Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
-- 待实现：Subagent 独立留档只新增以下六字段关系表。
-- 既有 t_sessions、t_session_entries 及历史/执行表共用，不新增物理列。
-- 通用工具结果去重和 Skill 统计属于独立专题，本文件不实施其结构增量。
-- 合入新环境完整安装材料；不是生产升级、迁移或回填脚本。
CREATE TABLE t_session_execution_links (
    child_session_id VARCHAR(128) PRIMARY KEY,
    child_execution_id VARCHAR(128) NOT NULL,
    parent_session_id VARCHAR(128) NOT NULL,
    parent_execution_id VARCHAR(128) NOT NULL,
    parent_tool_call_entry_id VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ(0) NOT NULL,
    CONSTRAINT uq_session_child_call UNIQUE (parent_session_id, parent_tool_call_entry_id),
    CONSTRAINT ck_session_child_distinct CHECK (parent_session_id <> child_session_id)
);
COMMENT ON TABLE t_session_execution_links IS '一次父工具调用与独立子会话首执行的不可变关联，不保存聊天副本';
COMMENT ON COLUMN t_session_execution_links.child_session_id IS '本次 Subagent 调用创建的子会话 ID';
COMMENT ON COLUMN t_session_execution_links.child_execution_id IS '子会话的本次首执行 ID，后续对话不能替换';
COMMENT ON COLUMN t_session_execution_links.parent_session_id IS '发出 Agent 工具调用的父会话 ID，不代表复制来源';
COMMENT ON COLUMN t_session_execution_links.parent_execution_id IS '本次父执行 ID，用于受理和定向取消校验';
COMMENT ON COLUMN t_session_execution_links.parent_tool_call_entry_id IS '父会话已保存工具调用 Entry 的 id，同次 Subagent 委派复用';
COMMENT ON COLUMN t_session_execution_links.created_at IS '关联创建的 UTC 秒级时间';
CREATE INDEX idx_session_child_parent_execution
    ON t_session_execution_links (parent_session_id, parent_execution_id);
-- 不设级联删除；授权及可信服务来源仅在本次内存执行快照中使用，Claw 不落用户归属或秘密。
-- 子 t_sessions 行存在时 incoming link 绝不能先删除；父行删除不改变子分类。
-- 仅当子 Session 已不存在、两端历史已实际删除或清理完成且原执行已明确收尾后，才清理关系。
-- 公开主会话查询按 NOT EXISTS 子端关系过滤；不 JOIN 父行判断分类。
