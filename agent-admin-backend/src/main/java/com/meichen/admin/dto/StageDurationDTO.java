package com.meichen.admin.dto;

public record StageDurationDTO(
    String stageName,
    Double avgMs,
    Double p95Ms,
    Long maxMs,
    Integer successCount,
    Integer failedCount
) {}
