-- V2026071203__create_rag_search_logs.sql
CREATE TABLE rag_search_logs (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    project_id VARCHAR(36),
    query_text TEXT NOT NULL,
    search_type VARCHAR(20) NOT NULL,
    result_count INT NOT NULL DEFAULT 0,
    duration_ms INT NOT NULL DEFAULT 0,
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
    timed_out BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_rag_search_type_created ON rag_search_logs (search_type, created_at);
CREATE INDEX idx_rag_search_project ON rag_search_logs (project_id);
CREATE INDEX idx_rag_search_result_count ON rag_search_logs (result_count);
