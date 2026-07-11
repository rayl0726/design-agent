package com.meichen.admin.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "stage_log_stats")
public class StageLogStatsRead {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "stage_name")
    private String stageName;

    @Column(name = "window_start")
    private LocalDateTime windowStart;

    @Column(name = "window_end")
    private LocalDateTime windowEnd;

    @Column(name = "avg_ms")
    private Double avgMs;

    @Column(name = "p95_ms")
    private Double p95Ms;

    @Column(name = "max_ms")
    private Long maxMs;

    @Column(name = "success_count")
    private Integer successCount;

    @Column(name = "failed_count")
    private Integer failedCount;

    public String getStageName() { return stageName; }
    public LocalDateTime getWindowStart() { return windowStart; }
    public LocalDateTime getWindowEnd() { return windowEnd; }
    public Double getAvgMs() { return avgMs; }
    public Double getP95Ms() { return p95Ms; }
    public Long getMaxMs() { return maxMs; }
    public Integer getSuccessCount() { return successCount; }
    public Integer getFailedCount() { return failedCount; }
}
