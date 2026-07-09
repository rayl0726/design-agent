package com.meichen.orchestrator.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "stage_log_stats", indexes = {
    @Index(name = "idx_stage_log_stats_name_window", columnList = "stage_name, window_start, window_end", unique = true),
    @Index(name = "idx_stage_log_stats_window", columnList = "window_end")
})
public class StageLogStats {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "stage_name", nullable = false, length = 100)
    private String stageName;

    @Column(name = "window_start", nullable = false)
    private LocalDateTime windowStart;

    @Column(name = "window_end", nullable = false)
    private LocalDateTime windowEnd;

    @Column(name = "avg_ms")
    private Long avgMs;

    @Column(name = "p95_ms")
    private Long p95Ms;

    @Column(name = "max_ms")
    private Long maxMs;

    @Column(name = "success_count", nullable = false)
    private Long successCount = 0L;

    @Column(name = "failed_count", nullable = false)
    private Long failedCount = 0L;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getStageName() { return stageName; }
    public void setStageName(String stageName) { this.stageName = stageName; }

    public LocalDateTime getWindowStart() { return windowStart; }
    public void setWindowStart(LocalDateTime windowStart) { this.windowStart = windowStart; }

    public LocalDateTime getWindowEnd() { return windowEnd; }
    public void setWindowEnd(LocalDateTime windowEnd) { this.windowEnd = windowEnd; }

    public Long getAvgMs() { return avgMs; }
    public void setAvgMs(Long avgMs) { this.avgMs = avgMs; }

    public Long getP95Ms() { return p95Ms; }
    public void setP95Ms(Long p95Ms) { this.p95Ms = p95Ms; }

    public Long getMaxMs() { return maxMs; }
    public void setMaxMs(Long maxMs) { this.maxMs = maxMs; }

    public Long getSuccessCount() { return successCount; }
    public void setSuccessCount(Long successCount) { this.successCount = successCount; }

    public Long getFailedCount() { return failedCount; }
    public void setFailedCount(Long failedCount) { this.failedCount = failedCount; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
