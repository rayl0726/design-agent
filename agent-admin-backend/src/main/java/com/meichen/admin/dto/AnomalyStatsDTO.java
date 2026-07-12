package com.meichen.admin.dto;

import java.util.List;

public record AnomalyStatsDTO(
    long timeAnomalyCount,
    long subStageOverflowCount,
    List<AnomalyStageDTO> affectedStages
) {
    public record AnomalyStageDTO(
        String stageName,
        long timeAnomalyCount,
        long subStageOverflowCount
    ) {}
}
