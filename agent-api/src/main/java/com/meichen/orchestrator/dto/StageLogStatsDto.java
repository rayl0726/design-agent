package com.meichen.orchestrator.dto;

import com.meichen.orchestrator.entity.StageLogStats;

import java.time.LocalDateTime;

public record StageLogStatsDto(
    String stageName,
    LocalDateTime windowStart,
    LocalDateTime windowEnd,
    Long avgMs,
    Long p95Ms,
    Long maxMs,
    Long successCount,
    Long failedCount,
    Double failureRate
) {
    public static StageLogStatsDto fromEntity(StageLogStats entity) {
        long total = (entity.getSuccessCount() != null ? entity.getSuccessCount() : 0L)
            + (entity.getFailedCount() != null ? entity.getFailedCount() : 0L);
        double failureRate = total == 0 ? 0.0 : (double) entity.getFailedCount() / total;
        return new StageLogStatsDto(
            entity.getStageName(),
            entity.getWindowStart(),
            entity.getWindowEnd(),
            entity.getAvgMs(),
            entity.getP95Ms(),
            entity.getMaxMs(),
            entity.getSuccessCount(),
            entity.getFailedCount(),
            failureRate
        );
    }
}
