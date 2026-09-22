-- SR-MEM-001: centralized GaussDB target schema.
-- Base Session model only; not the complete Runtime installation schema.
CREATE TABLE t_sessions (
    id                 VARCHAR(128)   PRIMARY KEY,
    created_at         TIMESTAMPTZ(3) NOT NULL,
    cwd                VARCHAR(512)   NOT NULL,
    parent_session_id  VARCHAR(128),
    metadata           JSONB,
    active_leaf_id     VARCHAR(128)
);

COMMENT ON COLUMN t_sessions.id IS '会话的唯一 ID，用于关联该会话的历史记录、序号和汇总数据';
COMMENT ON COLUMN t_sessions.created_at IS '创建这个会话的时间';
COMMENT ON COLUMN t_sessions.cwd IS '创建会话时使用的工作目录；可用于按工作目录筛选会话';
COMMENT ON COLUMN t_sessions.parent_session_id IS '当前会话复制自哪个来源会话；没有来源时为空，复制内容为来源会话在固定读取上界内的线性历史';
COMMENT ON COLUMN t_sessions.metadata IS '创建会话时由调用方提供的附加信息 JSON；未提供时为 SQL NULL';
COMMENT ON COLUMN t_sessions.active_leaf_id IS '最新一条 Entry 的 ID；空会话时为空，用于追加与完整性检查，不作为递归读取起点';

CREATE INDEX idx_t_sessions_created_at
    ON t_sessions (created_at DESC);

CREATE INDEX idx_t_sessions_cwd
    ON t_sessions (cwd);

CREATE INDEX idx_t_sessions_parent
    ON t_sessions (parent_session_id);

CREATE TABLE t_session_entries (
    session_id  VARCHAR(128)   NOT NULL,
    id          VARCHAR(128)   NOT NULL,
    entry_seq   BIGINT         NOT NULL,
    parent_id   VARCHAR(128),
    type        VARCHAR(64)    NOT NULL,
    timestamp   TIMESTAMPTZ(3) NOT NULL,
    payload     JSONB          NOT NULL,
    PRIMARY KEY (session_id, id)
);

COMMENT ON COLUMN t_session_entries.session_id IS '这条历史记录属于哪个会话；对应 t_sessions.id';
COMMENT ON COLUMN t_session_entries.id IS '这条历史记录的 ID；在同一个会话内唯一';
COMMENT ON COLUMN t_session_entries.entry_seq IS '这条历史记录在会话中的持久化顺序号；严格递增且允许空洞，按该序号读取完整时间线';
COMMENT ON COLUMN t_session_entries.parent_id IS '前一条 Entry 的 ID；第一条为空，由追加事务维护，普通读取不沿此字段递归';
COMMENT ON COLUMN t_session_entries.type IS '这条历史记录的种类；新写入不接受 leaf、branch_summary 和 label';
COMMENT ON COLUMN t_session_entries.timestamp IS '这条历史记录产生时携带的事件时间；不是数据库保存该行的时间';
COMMENT ON COLUMN t_session_entries.payload IS '这条历史记录的类型相关 JSON 内容；ID、父记录、事件时间和类型分别保存在其他字段中';

CREATE UNIQUE INDEX idx_t_session_entries_session_seq
    ON t_session_entries (session_id, entry_seq);

CREATE INDEX idx_t_session_entries_session_parent
    ON t_session_entries (session_id, parent_id);

CREATE INDEX idx_t_session_entries_session_type
    ON t_session_entries (session_id, type);

CREATE TABLE t_session_sequences (
    session_id  VARCHAR(128) PRIMARY KEY,
    next_seq    BIGINT       NOT NULL
);

COMMENT ON COLUMN t_session_sequences.session_id IS '这行序号记录属于哪个会话；对应 t_sessions.id，每个会话一行';
COMMENT ON COLUMN t_session_sequences.next_seq IS '下一可分配提交序号；新建会话时为 1，Runtime 的 Entry、公共事件和内部 Record 共享分配器';

CREATE TABLE t_session_materialized (
    session_id  VARCHAR(128) PRIMARY KEY,
    payload     JSONB        NOT NULL
);

COMMENT ON COLUMN t_session_materialized.session_id IS '这份汇总属于哪个会话；对应 t_sessions.id，每个会话一行';
COMMENT ON COLUMN t_session_materialized.payload IS '会话汇总 JSON；activePath 沿用汇总键名，保存单条时间线的名称、消息数、模型和思考级别，lifetimeUsage 保存会话自创建以来的 Token 和费用总和';
