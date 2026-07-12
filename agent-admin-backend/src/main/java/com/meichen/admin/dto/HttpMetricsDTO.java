package com.meichen.admin.dto;

import java.util.List;

public record HttpMetricsDTO(
    long totalRequests,
    long errorCount,
    double errorRate,
    double avgDurationMs,
    long maxDurationMs,
    List<HttpPathBreakdownDTO> topEndpoints
) {
    public record HttpPathBreakdownDTO(
        String pathPattern,
        long requestCount,
        long errorCount,
        double avgDurationMs
    ) {}
}
