package com.meichen.admin.dto;

public record StageDurationDTO(
    String stageName,
    Long avgMs,
    Long p95Ms,
    Long maxMs,
    Long successCount,
    Long failedCount
) {}
