CREATE TABLE IF NOT EXISTS users (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    phone       VARCHAR(11) NOT NULL UNIQUE,
    created_at  DATETIME(6) DEFAULT NULL,
    updated_at  DATETIME(6) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET @add_java_projects_user_id := IF(
    NOT EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'java_projects'
                  AND column_name = 'user_id'),
    'ALTER TABLE java_projects ADD COLUMN user_id BIGINT',
    'SELECT 1'
);
PREPARE stmt FROM @add_java_projects_user_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @add_session_messages_user_id := IF(
    NOT EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'session_messages'
                  AND column_name = 'user_id'),
    'ALTER TABLE session_messages ADD COLUMN user_id BIGINT',
    'SELECT 1'
);
PREPARE stmt FROM @add_session_messages_user_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @add_feedbacks_user_id := IF(
    NOT EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'feedbacks'
                  AND column_name = 'user_id'),
    'ALTER TABLE feedbacks ADD COLUMN user_id BIGINT',
    'SELECT 1'
);
PREPARE stmt FROM @add_feedbacks_user_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

INSERT INTO users (id, phone, created_at, updated_at)
VALUES (1, '00000000000', NOW(6), NOW(6))
ON DUPLICATE KEY UPDATE id = id;
