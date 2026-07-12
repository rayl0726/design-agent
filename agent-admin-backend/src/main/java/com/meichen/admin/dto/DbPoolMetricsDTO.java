package com.meichen.admin.dto;

public record DbPoolMetricsDTO(
    int active,
    int idle,
    int max,
    int pending
) {}
