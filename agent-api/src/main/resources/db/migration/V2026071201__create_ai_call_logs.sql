-- ai_call_logs: AI model call instrumentation log
CREATE TABLE ai_call_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id VARCHAR(36) DEFAULT NULL,
    call_type VARCHAR(20) NOT NULL COMMENT 'llm/vlm/embedding/image_gen',
    provider VARCHAR(50) NOT NULL COMMENT 'zhipu/siliconflow/pollinations/ollama',
    model VARCHAR(100) NOT NULL,
    node_name VARCHAR(50) DEFAULT NULL COMMENT 'text_parse/concept_design/image_generation etc',
    status VARCHAR(20) NOT NULL COMMENT 'success/failed/timeout/rate_limited',
    duration_ms INT NOT NULL,
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    error_message TEXT DEFAULT NULL,
    retry_count INT DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_call_type_created (call_type, created_at),
    INDEX idx_provider_created (provider, created_at),
    INDEX idx_project_id (project_id),
    INDEX idx_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
