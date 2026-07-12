package com.meichen.admin.dto;

public record RagTimelineDTO(
    String date,
    long searchCount,
    double avgLatencyMs,
    double cacheHitRate
) {}
