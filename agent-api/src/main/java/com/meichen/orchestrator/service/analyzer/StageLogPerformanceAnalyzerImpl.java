package com.meichen.orchestrator.service.analyzer;

import com.meichen.orchestrator.entity.StageLog;
import com.meichen.orchestrator.repository.StageLogRepository;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Component
public class StageLogPerformanceAnalyzerImpl implements StageLogPerformanceAnalyzer {

    private static final long BOTTLENECK_THRESHOLD_MS = 30_000L;
    private static final double BOTTLENECK_RATIO_THRESHOLD = 0.25;

    private final StageLogRepository stageLogRepository;

    public StageLogPerformanceAnalyzerImpl(StageLogRepository stageLogRepository) {
        this.stageLogRepository = stageLogRepository;
    }

    @Override
    @Transactional(readOnly = true)
    public StagePerformanceReport analyzeProjectPerformance(String projectId) {
        List<StageLog> allLogs = stageLogRepository.findByProjectIdOrderByStartedAtAscIdAsc(projectId);

        Map<Long, List<StageLog>> childrenByParent = allLogs.stream()
            .filter(log -> log.getParentId() != null)
            .collect(Collectors.groupingBy(StageLog::getParentId));

        List<StageLog> parentLogs = allLogs.stream()
            .filter(log -> log.getParentId() == null)
            .toList();

        long totalDurationMs = parentLogs.stream()
            .mapToLong(log -> log.getDurationMs() != null ? log.getDurationMs() : 0L)
            .sum();

        List<StagePerformanceReport.StageMetric> stages = new ArrayList<>();
        List<StagePerformanceReport.Anomaly> anomalies = new ArrayList<>();

        for (StageLog parent : parentLogs) {
            List<StageLog> children = childrenByParent.getOrDefault(parent.getId(), List.of());
            long parentDuration = parent.getDurationMs() != null ? parent.getDurationMs() : 0L;

            List<StagePerformanceReport.SubStageMetric> subStages = children.stream()
                .map(child -> {
                    long childDuration = child.getDurationMs() != null ? child.getDurationMs() : 0L;
                    double ratio = parentDuration > 0 ? (double) childDuration / parentDuration : 0.0;
                    return new StagePerformanceReport.SubStageMetric(
                        child.getStageName(),
                        child.getStageLabel(),
                        child.getStatus(),
                        child.getDurationMs(),
                        ratio
                    );
                })
                .toList();

            stages.add(new StagePerformanceReport.StageMetric(
                parent.getStageName(),
                parent.getStageLabel(),
                parent.getStatus(),
                parent.getDurationMs(),
                subStages
            ));

            collectAnomalies(parent, anomalies);
            for (StageLog child : children) {
                collectAnomalies(child, anomalies);
            }
        }

        List<StagePerformanceReport.Bottleneck> bottlenecks = identifyBottlenecks(stages, totalDurationMs);

        return new StagePerformanceReport(
            projectId,
            totalDurationMs,
            stages,
            anomalies,
            bottlenecks
        );
    }

    private void collectAnomalies(StageLog log, List<StagePerformanceReport.Anomaly> anomalies) {
        if (log.isTimeAnomaly()) {
            anomalies.add(new StagePerformanceReport.Anomaly(
                log.getId(),
                log.getStageName(),
                "TIME_ANOMALY",
                "阶段耗时存在异常（可能为负数或缺失开始时间）"
            ));
        }
        if (log.isSubStageOverflow()) {
            anomalies.add(new StagePerformanceReport.Anomaly(
                log.getId(),
                log.getStageName(),
                "SUB_STAGE_OVERFLOW",
                "子阶段耗时之和超过父阶段总耗时"
            ));
        }
        if ("FAILED".equals(log.getStatus())) {
            anomalies.add(new StagePerformanceReport.Anomaly(
                log.getId(),
                log.getStageName(),
                "FAILED",
                log.getErrorMessage() != null ? log.getErrorMessage() : "阶段执行失败"
            ));
        }
    }

    private List<StagePerformanceReport.Bottleneck> identifyBottlenecks(
        List<StagePerformanceReport.StageMetric> stages,
        long totalDurationMs
    ) {
        List<StagePerformanceReport.Bottleneck> bottlenecks = new ArrayList<>();

        for (StagePerformanceReport.StageMetric stage : stages) {
            long duration = stage.durationMs() != null ? stage.durationMs() : 0L;
            double ratio = totalDurationMs > 0 ? (double) duration / totalDurationMs : 0.0;

            if (duration >= BOTTLENECK_THRESHOLD_MS || ratio >= BOTTLENECK_RATIO_THRESHOLD) {
                String recommendation = buildRecommendation(stage.stageName(), duration, ratio);
                bottlenecks.add(new StagePerformanceReport.Bottleneck(
                    stage.stageName(),
                    stage.stageLabel(),
                    duration,
                    ratio,
                    recommendation
                ));
            }
        }

        bottlenecks.sort((a, b) -> Long.compare(b.durationMs(), a.durationMs()));
        return bottlenecks;
    }

    private String buildRecommendation(String stageName, long durationMs, double ratio) {
        return switch (stageName) {
            case "visual_design" -> "视觉设计耗时较长，建议增加图片生成并行度或优化 LLM prompt 长度";
            case "knowledge_retrieve" -> "知识检索耗时较长，建议添加语义搜索缓存和超时保护";
            case "technical_design" -> "落地方案生成耗时较长，建议减少冗余计算或启用增量生成";
            case "concept_design" -> "创意方向生成耗时较长，建议优化 LLM 调用链路";
            default -> String.format("%s 阶段耗时 %dms（占比 %.1f%%），建议Review该阶段实现", stageName, durationMs, ratio * 100);
        };
    }
}
