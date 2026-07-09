package com.meichen.orchestrator.service;

import com.meichen.orchestrator.dto.StageLogStatsDto;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class StageLogRecommendationServiceTest {

    private final StageLogRecommendationService service = new StageLogRecommendationService();

    @Test
    void recommendsParallelismWhenVisualDesignSlow() {
        Map<String, StageLogStatsDto> metrics = Map.of(
            "visual_design", new StageLogStatsDto("visual_design", LocalDateTime.now(), LocalDateTime.now(), 90_000L, 120_000L, 200_000L, 10L, 0L, 0.0)
        );

        List<Map<String, String>> recs = service.generateRecommendations(metrics);

        assertThat(recs).isNotEmpty();
        assertThat(recs.get(0)).containsEntry("stage", "visual_design");
        assertThat(recs.get(0).get("recommendation")).contains("图片生成并发");
    }

    @Test
    void recommendsKnowledgeCacheWhenBothVisualAndKnowledgeSlow() {
        Map<String, StageLogStatsDto> metrics = Map.of(
            "visual_design", new StageLogStatsDto("visual_design", LocalDateTime.now(), LocalDateTime.now(), 90_000L, 120_000L, 200_000L, 10L, 0L, 0.0),
            "knowledge_retrieve", new StageLogStatsDto("knowledge_retrieve", LocalDateTime.now(), LocalDateTime.now(), 40_000L, 60_000L, 80_000L, 10L, 0L, 0.0)
        );

        List<Map<String, String>> recs = service.generateRecommendations(metrics);

        assertThat(recs)
            .anyMatch(r -> r.get("stage").equals("visual_design") && r.get("recommendation").contains("知识库缓存"));
    }

    @Test
    void recommendsRetryWhenFailureRateHigh() {
        Map<String, StageLogStatsDto> metrics = Map.of(
            "visual_design", new StageLogStatsDto("visual_design", LocalDateTime.now(), LocalDateTime.now(), 10_000L, 15_000L, 20_000L, 8L, 2L, 0.2)
        );

        List<Map<String, String>> recs = service.generateRecommendations(metrics);

        assertThat(recs)
            .anyMatch(r -> r.get("stage").equals("visual_design") && r.get("recommendation").contains("降级策略"));
    }

    @Test
    void recommendsVectorIndexWhenOnlySemanticSearchSlow() {
        Map<String, StageLogStatsDto> metrics = Map.of(
            "knowledge_retrieve", new StageLogStatsDto("knowledge_retrieve", LocalDateTime.now(), LocalDateTime.now(), 10_000L, 20_000L, 25_000L, 10L, 0L, 0.0),
            "semantic_search", new StageLogStatsDto("semantic_search", LocalDateTime.now(), LocalDateTime.now(), 20_000L, 25_000L, 30_000L, 10L, 0L, 0.0)
        );

        List<Map<String, String>> recs = service.generateRecommendations(metrics);

        assertThat(recs)
            .anyMatch(r -> r.get("stage").equals("knowledge_retrieve") && r.get("recommendation").contains("向量索引"));
    }
}
