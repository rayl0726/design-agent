package com.meichen.orchestrator.service;

import com.meichen.orchestrator.dto.StageLogStatsDto;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class StageLogRecommendationService {

    public List<Map<String, String>> generateRecommendations(Map<String, StageLogStatsDto> metrics) {
        List<Map<String, String>> recommendations = new ArrayList<>();

        StageLogStatsDto visualDesign = metrics.get("visual_design");
        StageLogStatsDto knowledgeRetrieve = metrics.get("knowledge_retrieve");
        StageLogStatsDto imageGeneration = metrics.get("image_generation");
        StageLogStatsDto semanticSearch = metrics.get("semantic_search");

        if (visualDesign != null && visualDesign.avgMs() != null && visualDesign.avgMs() > 60_000) {
            if (knowledgeRetrieve != null && knowledgeRetrieve.p95Ms() != null && knowledgeRetrieve.p95Ms() > 30_000) {
                recommendations.add(Map.of(
                    "stage", "visual_design",
                    "reason", "知识检索和图片生成均较慢",
                    "recommendation", "优先优化知识库缓存，减少 LLM prompt 长度。"
                ));
            } else if (imageGeneration != null && imageGeneration.avgMs() != null && imageGeneration.avgMs() > 30_000) {
                recommendations.add(Map.of(
                    "stage", "visual_design",
                    "reason", "图片生成子阶段耗时高",
                    "recommendation", "考虑增加图片生成并行度或更换图片供应商。"
                ));
            } else {
                recommendations.add(Map.of(
                    "stage", "visual_design",
                    "reason", "视觉设计平均耗时超过 60 秒",
                    "recommendation", "检查图片生成并发和 LLM 调用延迟。"
                ));
            }
        }

        if (knowledgeRetrieve != null && knowledgeRetrieve.p95Ms() != null && knowledgeRetrieve.p95Ms() > 30_000) {
            recommendations.add(Map.of(
                "stage", "knowledge_retrieve",
                "reason", "知识检索 P95 超过 30 秒",
                "recommendation", "为语义搜索添加超时保护和缓存。"
            ));
        }

        if (semanticSearch != null && semanticSearch.avgMs() != null && semanticSearch.avgMs() > 15_000
                && (knowledgeRetrieve == null || knowledgeRetrieve.p95Ms() == null || knowledgeRetrieve.p95Ms() <= 30_000)) {
            recommendations.add(Map.of(
                "stage", "knowledge_retrieve",
                "reason", "仅语义搜索子阶段慢",
                "recommendation", "优化向量索引或向量库查询性能。"
            ));
        }

        for (StageLogStatsDto dto : metrics.values()) {
            if (dto.failureRate() != null && dto.failureRate() > 0.10) {
                recommendations.add(Map.of(
                    "stage", dto.stageName(),
                    "reason", String.format("失败率 %.1f%%", dto.failureRate() * 100),
                    "recommendation", "为该阶段增加降级策略和重试机制。"
                ));
            }
        }

        return recommendations;
    }
}
