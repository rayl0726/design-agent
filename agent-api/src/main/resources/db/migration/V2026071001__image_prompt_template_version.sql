ALTER TABLE feedbacks
    ADD COLUMN prompt_template_version VARCHAR(100) NULL AFTER image_url,
    ADD COLUMN rendered_prompt TEXT NULL AFTER prompt_template_version,
    ADD COLUMN generation_params JSON NULL AFTER rendered_prompt;

CREATE INDEX idx_feedbacks_prompt_version ON feedbacks (prompt_template_version);
