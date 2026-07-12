package com.meichen.admin.dto;

public record TokenUsageDTO(
    String date,
    String provider,
    long inputTokens,
    long outputTokens,
    long totalTokens,
    double estimatedCost
) {}
