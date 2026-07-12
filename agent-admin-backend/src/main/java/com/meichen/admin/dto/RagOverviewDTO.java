package com.meichen.admin.dto;

public record RagOverviewDTO(
    long totalSearches,
    double avgResultCount,
    double avgLatencyMs,
    double cacheHitRate,
    long timeoutCount,
    double fallbackRate
) {}
