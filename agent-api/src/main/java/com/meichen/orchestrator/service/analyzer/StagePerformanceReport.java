package com.meichen.orchestrator.service.analyzer;

import java.util.List;

public record StagePerformanceReport(
    String projectId,
    Long totalDurationMs,
    List<StageMetric> stages,
    List<Anomaly> anomalies,
    List<Bottleneck> bottlenecks
) {

    public record StageMetric(
        String stageName,
        String stageLabel,
        String status,
        Long durationMs,
        List<SubStageMetric> subStages
    ) {}

    public record SubStageMetric(
        String stageName,
        String stageLabel,
        String status,
        Long durationMs,
        Double ratio
    ) {}

    public record Anomaly(
        Long logId,
        String stageName,
        String type,
        String message
    ) {}

    public record Bottleneck(
        String stageName,
        String stageLabel,
        Long durationMs,
        Double ratio,
        String recommendation
    ) {}
}
