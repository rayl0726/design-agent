package com.meichen.admin.dto;

public record WorkflowSuccessDTO(
    String stageName,
    long totalCount,
    long successCount,
    long failedCount,
    double successRate
) {}
