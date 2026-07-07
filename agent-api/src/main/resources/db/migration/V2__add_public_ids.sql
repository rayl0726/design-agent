-- Add public_id columns to user-owned resource tables.
-- Backfill existing rows with unique 16-character URL-safe identifiers.
-- Create unique indexes for public ID lookups.

-- java_projects
SET @add_java_projects_public_id := IF(
    NOT EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'java_projects'
                  AND column_name = 'public_id'),
    'ALTER TABLE java_projects ADD COLUMN public_id VARCHAR(32) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_java_projects_public_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- session_messages
SET @add_session_messages_public_id := IF(
    NOT EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'session_messages'
                  AND column_name = 'public_id'),
    'ALTER TABLE session_messages ADD COLUMN public_id VARCHAR(32) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_session_messages_public_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- feedbacks
SET @add_feedbacks_public_id := IF(
    NOT EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'feedbacks'
                  AND column_name = 'public_id'),
    'ALTER TABLE feedbacks ADD COLUMN public_id VARCHAR(32) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_feedbacks_public_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- thinking_logs
SET @add_thinking_logs_public_id := IF(
    NOT EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'thinking_logs'
                  AND column_name = 'public_id'),
    'ALTER TABLE thinking_logs ADD COLUMN public_id VARCHAR(32) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_thinking_logs_public_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Backfill existing rows with 16-char URL-safe base64url identifiers.
-- RANDOM_BYTES(12) -> 96 bits -> 16 base64url characters (no padding).
-- The alphabet is A-Z a-z 0-9 _ -, matching the nanoid-compatible set.
UPDATE java_projects SET public_id = REPLACE(REPLACE(TO_BASE64(RANDOM_BYTES(12)), '+', '-'), '/', '_') WHERE public_id IS NULL;
UPDATE session_messages SET public_id = REPLACE(REPLACE(TO_BASE64(RANDOM_BYTES(12)), '+', '-'), '/', '_') WHERE public_id IS NULL;
UPDATE feedbacks SET public_id = REPLACE(REPLACE(TO_BASE64(RANDOM_BYTES(12)), '+', '-'), '/', '_') WHERE public_id IS NULL;
UPDATE thinking_logs SET public_id = REPLACE(REPLACE(TO_BASE64(RANDOM_BYTES(12)), '+', '-'), '/', '_') WHERE public_id IS NULL;

-- Make public_id NOT NULL once all rows are backfilled.
SET @modify_java_projects_public_id := IF(
    EXISTS (SELECT 1 FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'java_projects'
              AND column_name = 'public_id'
              AND is_nullable = 'YES'),
    'ALTER TABLE java_projects MODIFY COLUMN public_id VARCHAR(32) NOT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @modify_java_projects_public_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @modify_session_messages_public_id := IF(
    EXISTS (SELECT 1 FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'session_messages'
              AND column_name = 'public_id'
              AND is_nullable = 'YES'),
    'ALTER TABLE session_messages MODIFY COLUMN public_id VARCHAR(32) NOT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @modify_session_messages_public_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @modify_feedbacks_public_id := IF(
    EXISTS (SELECT 1 FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'feedbacks'
              AND column_name = 'public_id'
              AND is_nullable = 'YES'),
    'ALTER TABLE feedbacks MODIFY COLUMN public_id VARCHAR(32) NOT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @modify_feedbacks_public_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @modify_thinking_logs_public_id := IF(
    EXISTS (SELECT 1 FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'thinking_logs'
              AND column_name = 'public_id'
              AND is_nullable = 'YES'),
    'ALTER TABLE thinking_logs MODIFY COLUMN public_id VARCHAR(32) NOT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @modify_thinking_logs_public_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Unique indexes for public ID lookups.
SET @add_idx_java_projects_public_id := IF(
    NOT EXISTS (SELECT 1 FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = 'java_projects'
                  AND index_name = 'idx_java_projects_public_id'),
    'CREATE UNIQUE INDEX idx_java_projects_public_id ON java_projects(public_id)',
    'SELECT 1'
);
PREPARE stmt FROM @add_idx_java_projects_public_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @add_idx_session_messages_public_id := IF(
    NOT EXISTS (SELECT 1 FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = 'session_messages'
                  AND index_name = 'idx_session_messages_public_id'),
    'CREATE UNIQUE INDEX idx_session_messages_public_id ON session_messages(public_id)',
    'SELECT 1'
);
PREPARE stmt FROM @add_idx_session_messages_public_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @add_idx_feedbacks_public_id := IF(
    NOT EXISTS (SELECT 1 FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = 'feedbacks'
                  AND index_name = 'idx_feedbacks_public_id'),
    'CREATE UNIQUE INDEX idx_feedbacks_public_id ON feedbacks(public_id)',
    'SELECT 1'
);
PREPARE stmt FROM @add_idx_feedbacks_public_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @add_idx_thinking_logs_public_id := IF(
    NOT EXISTS (SELECT 1 FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = 'thinking_logs'
                  AND index_name = 'idx_thinking_logs_public_id'),
    'CREATE UNIQUE INDEX idx_thinking_logs_public_id ON thinking_logs(public_id)',
    'SELECT 1'
);
PREPARE stmt FROM @add_idx_thinking_logs_public_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
