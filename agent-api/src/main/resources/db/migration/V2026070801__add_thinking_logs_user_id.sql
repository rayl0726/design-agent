SET @add_thinking_logs_user_id := IF(
    NOT EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'thinking_logs'
                  AND column_name = 'user_id'),
    'ALTER TABLE thinking_logs ADD COLUMN user_id BIGINT',
    'SELECT 1'
);
PREPARE stmt FROM @add_thinking_logs_user_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
