package com.meichen.admin.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "rag_search_logs")
public class RagSearchLogRead {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "project_id", length = 36)
    private String projectId;

    @Column(name = "query_text", columnDefinition = "TEXT")
    private String queryText;

    @Column(name = "search_type", length = 20)
    private String searchType;

    @Column(name = "result_count")
    private Integer resultCount;

    @Column(name = "duration_ms")
    private Integer durationMs;

    @Column(name = "cache_hit")
    private Boolean cacheHit;

    @Column(name = "timed_out")
    private Boolean timedOut;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public String getProjectId() { return projectId; }
    public String getQueryText() { return queryText; }
    public String getSearchType() { return searchType; }
    public Integer getResultCount() { return resultCount; }
    public Integer getDurationMs() { return durationMs; }
    public Boolean getCacheHit() { return cacheHit; }
    public Boolean getTimedOut() { return timedOut; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
