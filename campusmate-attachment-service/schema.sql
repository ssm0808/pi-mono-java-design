-- SR-FILE-001 v3.0.0
-- 目标设计：CampusMate 文件服务 openGauss 元数据账本。
-- 文件正文仅保存于私有 OBS，完整 Object Key 精确等于 file_id。
-- 表中不保存文件正文、OBS URL、凭据、ETag、第二套 Object Key 或 chat_id。

CREATE TABLE t_file (
    file_id     VARCHAR(31)    NOT NULL,
    session_id  VARCHAR(128)   NOT NULL,
    status      VARCHAR(16)    NOT NULL DEFAULT 'UPLOADING',
    created_at  TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at  TIMESTAMPTZ(3),

    CONSTRAINT pk_file PRIMARY KEY (file_id),
    CONSTRAINT ck_file_id CHECK (
        file_id ~ '^file_[0-9A-Za-z]{26}$'
    ),
    CONSTRAINT ck_file_session_id CHECK (
        session_id ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'
    ),
    CONSTRAINT ck_file_status CHECK (
        status IN (
            'UPLOADING',
            'PROCESSING',
            'READY',
            'BLOCKED',
            'FAILED',
            'DELETING',
            'DELETED'
        )
    ),
    CONSTRAINT ck_file_deleted_at CHECK (
        (status = 'DELETED' AND deleted_at IS NOT NULL)
        OR (status <> 'DELETED' AND deleted_at IS NULL)
    ),
    CONSTRAINT ck_file_time_order CHECK (
        deleted_at IS NULL OR deleted_at >= created_at
    )
);

CREATE TABLE t_file_active_detail (
    file_id             VARCHAR(31)    NOT NULL,
    filename            VARCHAR(512)   NOT NULL,
    detected_media_type VARCHAR(127),
    expected_size_bytes BIGINT         NOT NULL,
    size_bytes          BIGINT,
    sha256              CHAR(64),
    referenced_at       TIMESTAMPTZ(3),
    expires_at          TIMESTAMPTZ(3),
    error_code          VARCHAR(64),
    attempt_count       INTEGER        NOT NULL DEFAULT 0,
    next_attempt_at     TIMESTAMPTZ(3),
    lease_owner         VARCHAR(128),
    lease_until         TIMESTAMPTZ(3),
    row_version         BIGINT         NOT NULL DEFAULT 0,

    CONSTRAINT pk_file_active_detail PRIMARY KEY (file_id),
    CONSTRAINT fk_file_active_detail_file FOREIGN KEY (file_id)
        REFERENCES t_file (file_id) ON DELETE RESTRICT,
    CONSTRAINT ck_file_active_filename CHECK (filename <> ''),
    CONSTRAINT ck_file_active_detected_media_type CHECK (
        detected_media_type IS NULL
        OR detected_media_type ~ '^[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+$'
    ),
    CONSTRAINT ck_file_active_expected_size CHECK (
        expected_size_bytes BETWEEN 1 AND 20971520
    ),
    CONSTRAINT ck_file_active_actual_size CHECK (
        size_bytes IS NULL OR size_bytes BETWEEN 1 AND 20971520
    ),
    CONSTRAINT ck_file_active_size_match CHECK (
        size_bytes IS NULL OR size_bytes = expected_size_bytes
    ),
    CONSTRAINT ck_file_active_sha256 CHECK (
        sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT ck_file_active_reference_lifecycle CHECK (
        (referenced_at IS NULL AND expires_at IS NOT NULL)
        OR (referenced_at IS NOT NULL AND expires_at IS NULL)
    ),
    CONSTRAINT ck_file_active_attempt_count CHECK (attempt_count >= 0),
    CONSTRAINT ck_file_active_lease_pair CHECK (
        (lease_owner IS NULL AND lease_until IS NULL)
        OR (lease_owner IS NOT NULL AND lease_until IS NOT NULL)
    ),
    CONSTRAINT ck_file_active_row_version CHECK (row_version >= 0),
    CONSTRAINT ck_file_active_error_code CHECK (
        error_code IS NULL OR error_code ~ '^[A-Z][A-Z0-9_]{0,63}$'
    )
);

COMMENT ON TABLE t_file IS
    '文件永久身份和生命周期状态；DELETED 行作为不可复用的 ID 墓碑永久保留';
COMMENT ON COLUMN t_file.file_id IS
    '大小写敏感的文件资源 ID 和私有 OBS 完整 Object Key，永久不复用';
COMMENT ON COLUMN t_file.session_id IS
    '不可变的 CampusClaw Runtime Session 绑定';
COMMENT ON COLUMN t_file.status IS
    '文件状态：UPLOADING、PROCESSING、READY、BLOCKED、FAILED、DELETING 或 DELETED';
COMMENT ON COLUMN t_file.created_at IS
    '永久身份记录创建时间';
COMMENT ON COLUMN t_file.deleted_at IS
    'OBS 删除完成时间，仅 DELETED 墓碑非空';

COMMENT ON TABLE t_file_active_detail IS
    '每个非 DELETED 文件的一对一活动元数据，删除正文后移除';
COMMENT ON COLUMN t_file_active_detail.file_id IS
    '连接永久身份记录的主键和外键';
COMMENT ON COLUMN t_file_active_detail.filename IS
    '清洗后的不可信显示名，不用于构造 OBS Object Key';
COMMENT ON COLUMN t_file_active_detail.detected_media_type IS
    '内容嗅探和安全处理确认的无参数小写 MIME 类型';
COMMENT ON COLUMN t_file_active_detail.expected_size_bytes IS
    '通过 X-File-Size 声明并用于上传准入和长度复核的字节数';
COMMENT ON COLUMN t_file_active_detail.size_bytes IS
    '流式上传期间实际观察并复核的字节数';
COMMENT ON COLUMN t_file_active_detail.sha256 IS
    '扫描、解析和 Runtime 读取时复核的原始内容小写 SHA-256';
COMMENT ON COLUMN t_file_active_detail.referenced_at IS
    '首次 Runtime 成功解析时间，非空表示文件已被 Session Entry 引用';
COMMENT ON COLUMN t_file_active_detail.expires_at IS
    '未引用文件的自动清理截止时间，首次引用后清空';
COMMENT ON COLUMN t_file_active_detail.error_code IS
    '有界且脱敏的稳定失败码，不包含供应商原文或凭据';
COMMENT ON COLUMN t_file_active_detail.attempt_count IS
    '当前扫描、删除或对账阶段的尝试次数';
COMMENT ON COLUMN t_file_active_detail.next_attempt_at IS
    'Worker 可再次尝试当前后台阶段的最早时间';
COMMENT ON COLUMN t_file_active_detail.lease_owner IS
    '临时 Worker 标识，仅在 lease_until 之前有效';
COMMENT ON COLUMN t_file_active_detail.lease_until IS
    '租约到期时间，过期后其他 Pod 可以接管';
COMMENT ON COLUMN t_file_active_detail.row_version IS
    '每次条件更新时递增的乐观锁版本';

CREATE INDEX idx_file_session_status
    ON t_file (session_id, status);

CREATE INDEX idx_file_status
    ON t_file (status);

CREATE INDEX idx_file_deleted_at
    ON t_file (deleted_at);

CREATE INDEX idx_file_active_next_attempt
    ON t_file_active_detail (next_attempt_at);

CREATE INDEX idx_file_active_expires
    ON t_file_active_detail (expires_at);

-- 无法由单行 CHECK 完整表达的应用事务规则：
-- 1. t_file 与 t_file_active_detail 在一个事务中插入；每个非 DELETED 身份
--    恰好有一条活动明细，DELETED 身份没有活动明细。
-- 2. session_id、file_id、expected_size_bytes 和文件身份不可变。
--    file_id 就是完整 OBS Object Key，因此不另存 object_key。
-- 3. READY 要求 detected_media_type、size_bytes 和 sha256 全部非空。
-- 4. Resolve 按稳定顺序锁定请求 ID，原子执行
--    referenced_at = COALESCE(referenced_at, now()) 和 expires_at = NULL。
-- 5. 状态转换先锁 t_file，再锁 t_file_active_detail；业务更新同时匹配
--    file_id 和 row_version。
-- 6. Worker 在短事务中 claim lease 并提交，之后才执行 OBS I/O 或安全扫描。
-- 7. 进入新阶段时按需重置 attempt_count、next_attempt_at、lease_owner、
--    lease_until 和 error_code。
-- 8. OBS DELETE 成功或 NotFound 后，一个事务删除活动明细并将主表更新为
--    DELETED，同时设置 deleted_at。
-- 9. DELETED 身份是永久墓碑，不再删除。
-- 10. 创建时 expires_at = created_at + 24 小时。普通扫描允许 PROCESSING
--     进入 READY、BLOCKED 或 FAILED；只有受审计特权路径可执行 READY -> BLOCKED。
-- 11. 部署必须使用 UTF-8 和大小写敏感的标识符比较，并用生产 JDBC 驱动验证。
-- 12. 普通删除、24 小时清理、Session 删除和普通 Worker claim 必须排除
--     FAILED + OBJECT_KEY_CONFLICT；只有受审计对账可以收束该记录。
