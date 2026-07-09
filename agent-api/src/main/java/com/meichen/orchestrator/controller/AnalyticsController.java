package com.meichen.orchestrator.controller;

import com.meichen.orchestrator.dto.StageLogStatsDto;
import com.meichen.orchestrator.security.CurrentUser;
import com.meichen.orchestrator.service.StageLogAnalyticsService;
import com.meichen.orchestrator.service.StageLogRecommendationService;
import com.meichen.orchestrator.service.analyzer.StageLogPerformanceAnalyzer;
import com.meichen.orchestrator.service.analyzer.StagePerformanceReport;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/analytics")
public class AnalyticsController {

    private final StageLogAnalyticsService analyticsService;
    private final StageLogRecommendationService recommendationService;
    private final StageLogPerformanceAnalyzer performanceAnalyzer;

    public AnalyticsController(StageLogAnalyticsService analyticsService,
                               StageLogRecommendationService recommendationService,
                               StageLogPerformanceAnalyzer performanceAnalyzer) {
        this.analyticsService = analyticsService;
        this.recommendationService = recommendationService;
        this.performanceAnalyzer = performanceAnalyzer;
    }

    @GetMapping("/stages")
    public ResponseEntity<List<StageLogStatsDto>> listStageMetrics(@CurrentUser Long userId) {
        LocalDateTime since = LocalDateTime.now().minusHours(24);
        return ResponseEntity.ok(analyticsService.getStageMetrics(since));
    }

    @GetMapping("/stages/{stageName}")
    public ResponseEntity<List<StageLogStatsDto>> getStageMetrics(@PathVariable String stageName,
                                                                  @CurrentUser Long userId) {
        LocalDateTime since = LocalDateTime.now().minusHours(24);
        List<StageLogStatsDto> metrics = analyticsService.getStageMetrics(since).stream()
            .filter(dto -> dto.stageName().equals(stageName))
            .toList();
        return ResponseEntity.ok(metrics);
    }

    @GetMapping("/stages/recommendations")
    public ResponseEntity<List<Map<String, String>>> getRecommendations(@CurrentUser Long userId) {
        Map<String, StageLogStatsDto> latest = analyticsService.getLatestMetricsByStage();
        return ResponseEntity.ok(recommendationService.generateRecommendations(latest));
    }

    @GetMapping("/projects/{projectId}/timeline")
    public ResponseEntity<List<Map<String, Object>>> getProjectTimeline(@PathVariable String projectId,
                                                                        @CurrentUser Long userId) {
        return ResponseEntity.ok(analyticsService.getProjectTimeline(projectId));
    }

    @GetMapping("/projects/{projectId}/performance")
    public ResponseEntity<StagePerformanceReport> getProjectPerformance(@PathVariable String projectId,
                                                                        @CurrentUser Long userId) {
        return ResponseEntity.ok(performanceAnalyzer.analyzeProjectPerformance(projectId));
    }
}
