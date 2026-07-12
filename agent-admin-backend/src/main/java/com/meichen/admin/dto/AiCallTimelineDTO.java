package com.meichen.admin.dto;

public record AiCallTimelineDTO(
    String date,
    String callType,
    long count,
    long errorCount
) {}
