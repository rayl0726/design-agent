package com.meichen.admin.dto;

public record ProjectFunnelDTO(
    long draftCount,
    long generatingCount,
    long completedCount,
    double draftToGeneratingRate,
    double generatingToCompletedRate,
    double overallCompletionRate
) {}
