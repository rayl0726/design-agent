-- http_request_logs: HTTP request instrumentation log
CREATE TABLE http_request_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    method VARCHAR(10) NOT NULL COMMENT 'HTTP method: GET/POST/PUT/DELETE',
    path_pattern VARCHAR(200) NOT NULL COMMENT 'Path pattern e.g. /api/v1/projects/{id}',
    status_code INT NOT NULL COMMENT 'HTTP status code',
    duration_ms INT NOT NULL COMMENT 'Response duration in milliseconds',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_path_created (path_pattern, created_at),
    INDEX idx_status_created (status_code, created_at),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
