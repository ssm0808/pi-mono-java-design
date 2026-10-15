-- Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
-- 待实现：对 Session 基础模型的目标补充，不是生产升级/迁移脚本。
-- 实施时合并进完整安装 DDL；不重复定义既有公共事件、控制和根执行表。
ALTER TABLE t_session_entries ADD COLUMN tool_call_entry_id VARCHAR(128);
COMMENT ON COLUMN t_session_entries.tool_call_entry_id IS '仅工具最终结果填写的同会话调用 Entry ID，用于唯一结果约束';
ALTER TABLE t_session_entries ADD CONSTRAINT ck_session_tool_result_ref CHECK (
    (type = 'tool.result' AND tool_call_entry_id IS NOT NULL) OR
    (type <> 'tool.result' AND tool_call_entry_id IS NULL));
CREATE UNIQUE INDEX idx_session_tool_result_once
    ON t_session_entries (session_id, tool_call_entry_id);
-- NULL 的唯一索引行为必须在公司 GaussDB 验证。
-- 追加事务检查被引用调用存在、属于相同固定 execution，且工具与可信准备绑定一致。
-- tool.result payload 受控扩展：schema_version=1、execution_id、origin=LIVE/COPY、
-- Skill 专属 skill_id，以及既有 tool_call_id/tool_name/content/is_error/error_code。
-- schema_version/origin 由写入端生成，不接受模型/客户端自报；其他 Entry 不强加这些字段。
-- 固定 resultEntryId 与时间后重试，校验同调用已有结果全部载荷一致；冲突不可覆盖。
-- 若需要区间 COUNT，基于实际计划再评估 JSONB 表达式索引，不预设容量结论。

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
COMMENT ON COLUMN t_session_execution_links.parent_tool_call_entry_id IS '父会话内的服务端工具调用 Entry ID，同次 Subagent 调用复用';
COMMENT ON COLUMN t_session_execution_links.created_at IS '关联创建的 UTC 秒级时间';
CREATE INDEX idx_session_child_parent_execution
    ON t_session_execution_links (parent_session_id, parent_execution_id);
-- 不设级联删除；可信 scope/授权快照归子 Session/首执行，绝不复制秘密凭据。
-- 父子分别保留；双方均可清理且原执行已明确收尾后，才清除此最小关系。
