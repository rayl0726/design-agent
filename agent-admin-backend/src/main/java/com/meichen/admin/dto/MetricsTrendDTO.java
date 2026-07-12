package com.meichen.admin.dto;

public record MetricsTrendDTO(
    String date,
    long count,
    long cumulativeCount
) {}
