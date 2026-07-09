CREATE TABLE IF NOT EXISTS stage_log_stats (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stage_name VARCHAR(100) NOT NULL,
    window_start DATETIME NOT NULL,
    window_end DATETIME NOT NULL,
    avg_ms BIGINT NULL,
    p95_ms BIGINT NULL,
    max_ms BIGINT NULL,
    success_count BIGINT NOT NULL DEFAULT 0,
    failed_count BIGINT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_stage_log_stats_name_window (stage_name, window_start, window_end),
    INDEX idx_stage_log_stats_window (window_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_stage_logs_analytics
    ON stage_logs (project_id, stage_name, status, started_at);
