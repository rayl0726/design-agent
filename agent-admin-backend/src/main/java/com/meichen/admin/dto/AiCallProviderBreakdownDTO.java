package com.meichen.admin.dto;

public record AiCallProviderBreakdownDTO(
    String provider,
    String model,
    long callCount,
    double successRate,
    double avgLatencyMs,
    long totalTokens
) {}
