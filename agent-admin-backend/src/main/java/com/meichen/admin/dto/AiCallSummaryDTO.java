package com.meichen.admin.dto;

public record AiCallSummaryDTO(
    String callType,
    long totalCount,
    long successCount,
    long failedCount,
    long rateLimitedCount,
    double avgLatencyMs,
    long totalInputTokens,
    long totalOutputTokens
) {}
