package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.StageLog;
import com.meichen.orchestrator.repository.StageLogRepository;
import com.meichen.orchestrator.service.analyzer.StageLogPerformanceAnalyzer;
import com.meichen.orchestrator.service.analyzer.StageLogPerformanceAnalyzerImpl;
import com.meichen.orchestrator.service.analyzer.StagePerformanceReport;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class StageLogPerformanceAnalyzerTest {

    @Mock
    private StageLogRepository stageLogRepository;

    private StageLogPerformanceAnalyzer analyzer;

    @BeforeEach
    void setUp() {
        analyzer = new StageLogPerformanceAnalyzerImpl(stageLogRepository);
    }

    @Test
    void analyzeProjectPerformance_shouldComputeStageDurationsAndRatios() {
        String projectId = "proj-1";

        StageLog visualDesign = parentStage(1L, "visual_design", "生成视觉方案", "SUCCESS", 120_000L);
        StageLog ideaRendering = childStage(2L, 1L, "idea_rendering", "创意生成", "SUCCESS", 20_000L);
        StageLog imageGeneration = childStage(3L, 1L, "image_generation", "图片生成", "SUCCESS", 90_000L);

        when(stageLogRepository.findByProjectIdOrderByStartedAtAscIdAsc(projectId))
            .thenReturn(List.of(visualDesign, ideaRendering, imageGeneration));

        StagePerformanceReport report = analyzer.analyzeProjectPerformance(projectId);

        assertThat(report.projectId()).isEqualTo(projectId);
        assertThat(report.totalDurationMs()).isEqualTo(120_000L);
        assertThat(report.stages()).hasSize(1);

        StagePerformanceReport.StageMetric stage = report.stages().get(0);
        assertThat(stage.stageName()).isEqualTo("visual_design");
        assertThat(stage.durationMs()).isEqualTo(120_000L);
        assertThat(stage.subStages()).hasSize(2);

        StagePerformanceReport.SubStageMetric imageSub = stage.subStages().stream()
            .filter(s -> s.stageName().equals("image_generation"))
            .findFirst()
            .orElseThrow();
        assertThat(imageSub.durationMs()).isEqualTo(90_000L);
        assertThat(imageSub.ratio()).isEqualTo(0.75);
    }

    @Test
    void analyzeProjectPerformance_shouldDetectAnomalies() {
        String projectId = "proj-2";

        StageLog knowledgeRetrieve = parentStage(1L, "knowledge_retrieve", "检索知识库", "SUCCESS", 5_000L);
        knowledgeRetrieve.setTimeAnomaly(true);

        StageLog visualDesign = parentStage(2L, "visual_design", "生成视觉方案", "FAILED", null);
        visualDesign.setErrorMessage("image provider timeout");

        StageLog technicalDesign = parentStage(3L, "technical_design", "生成落地方案", "SUCCESS", 30_000L);
        technicalDesign.setSubStageOverflow(true);

        when(stageLogRepository.findByProjectIdOrderByStartedAtAscIdAsc(projectId))
            .thenReturn(List.of(knowledgeRetrieve, visualDesign, technicalDesign));

        StagePerformanceReport report = analyzer.analyzeProjectPerformance(projectId);

        assertThat(report.anomalies()).hasSize(3);
        assertThat(report.anomalies())
            .anyMatch(a -> a.type().equals("TIME_ANOMALY") && a.stageName().equals("knowledge_retrieve"))
            .anyMatch(a -> a.type().equals("FAILED") && a.stageName().equals("visual_design"))
            .anyMatch(a -> a.type().equals("SUB_STAGE_OVERFLOW") && a.stageName().equals("technical_design"));
    }

    @Test
    void analyzeProjectPerformance_shouldIdentifyBottlenecks() {
        String projectId = "proj-3";

        StageLog textParse = parentStage(1L, "text_parse", "解析文本输入", "SUCCESS", 500L);
        StageLog visualDesign = parentStage(2L, "visual_design", "生成视觉方案", "SUCCESS", 120_000L);
        StageLog technicalDesign = parentStage(3L, "technical_design", "生成落地方案", "SUCCESS", 30_000L);

        when(stageLogRepository.findByProjectIdOrderByStartedAtAscIdAsc(projectId))
            .thenReturn(List.of(textParse, visualDesign, technicalDesign));

        StagePerformanceReport report = analyzer.analyzeProjectPerformance(projectId);

        assertThat(report.bottlenecks()).isNotEmpty();
        StagePerformanceReport.Bottleneck topBottleneck = report.bottlenecks().get(0);
        assertThat(topBottleneck.stageName()).isEqualTo("visual_design");
        assertThat(topBottleneck.ratio()).isGreaterThan(0.7);
        assertThat(topBottleneck.recommendation()).isNotBlank();
    }

    @Test
    void analyzeProjectPerformance_shouldHandleEmptyProject() {
        String projectId = "proj-empty";
        when(stageLogRepository.findByProjectIdOrderByStartedAtAscIdAsc(projectId))
            .thenReturn(List.of());

        StagePerformanceReport report = analyzer.analyzeProjectPerformance(projectId);

        assertThat(report.projectId()).isEqualTo(projectId);
        assertThat(report.totalDurationMs()).isEqualTo(0L);
        assertThat(report.stages()).isEmpty();
        assertThat(report.anomalies()).isEmpty();
        assertThat(report.bottlenecks()).isEmpty();
    }

    private StageLog parentStage(Long id, String name, String label, String status, Long durationMs) {
        StageLog log = new StageLog();
        log.setId(id);
        log.setStageName(name);
        log.setStageLabel(label);
        log.setStatus(status);
        log.setDurationMs(durationMs);
        return log;
    }

    private StageLog childStage(Long id, Long parentId, String name, String label, String status, Long durationMs) {
        StageLog log = parentStage(id, name, label, status, durationMs);
        log.setParentId(parentId);
        return log;
    }
}
