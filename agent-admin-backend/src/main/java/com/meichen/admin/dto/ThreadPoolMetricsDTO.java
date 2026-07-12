package com.meichen.admin.dto;

public record ThreadPoolMetricsDTO(
    String name,
    int active,
    int core,
    int max,
    long completedTaskCount,
    int queueSize
) {}
