package com.meichen.admin.dto;

import java.util.List;

public record ImageGenProviderDTO(
    String provider,
    long callCount,
    double successRate,
    double avgLatencyMs,
    List<FailureReason> failureReasons
) {
    public record FailureReason(String error, long count) {}
}
