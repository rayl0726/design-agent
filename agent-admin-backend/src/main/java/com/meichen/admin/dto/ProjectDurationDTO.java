package com.meichen.admin.dto;

public record ProjectDurationDTO(
    double avgDurationHours,
    double medianDurationHours,
    double p90DurationHours,
    double maxDurationHours,
    long completedCount
) {}
