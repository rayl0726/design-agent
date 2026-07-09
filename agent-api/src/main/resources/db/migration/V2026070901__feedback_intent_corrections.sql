ALTER TABLE feedbacks
    ADD COLUMN category VARCHAR(30) NULL AFTER feedback_type,
    ADD COLUMN intent_field VARCHAR(50) NULL AFTER category,
    ADD COLUMN original_value TEXT NULL AFTER intent_field,
    ADD COLUMN corrected_value TEXT NULL AFTER original_value,
    ADD COLUMN processed BOOLEAN DEFAULT FALSE AFTER corrected_value,
    ADD COLUMN notes TEXT NULL AFTER processed;

CREATE INDEX idx_feedbacks_intent_unprocessed ON feedbacks (project_id, feedback_type, processed);
