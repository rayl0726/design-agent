package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.AiCallLogReadRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
public class AiModelMetricsService {

    private static final Map<String, Map<String, Double>> PRICING = Map.of(
        "zhipu", Map.of("input", 0.5 / 1_000_000, "output", 0.5 / 1_000_000),
        "siliconflow", Map.of("input", 0.0, "output", 0.0),
        "ollama", Map.of("input", 0.0, "output", 0.0),
        "pollinations", Map.of("input", 0.0, "output", 0.0)
    );

    private final AiCallLogReadRepository repository;

    public AiModelMetricsService(AiCallLogReadRepository repository) {
        this.repository = repository;
    }

    public List<AiCallSummaryDTO> getCallSummary(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = repository.groupByCallType(since);
        return rows.stream().map(row -> new AiCallSummaryDTO(
            (String) row[0],
            ((Number) row[1]).longValue(),
            ((Number) row[2]).longValue(),
            ((Number) row[3]).longValue(),
            ((Number) row[4]).longValue(),
            row[5] != null ? ((Number) row[5]).doubleValue() : 0.0,
            row[6] != null ? ((Number) row[6]).longValue() : 0L,
            row[7] != null ? ((Number) row[7]).longValue() : 0L
        )).toList();
    }

    public List<AiCallProviderBreakdownDTO> getByProvider(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = repository.groupByProvider(since);
        return rows.stream().map(row -> {
            long total = ((Number) row[2]).longValue();
            long success = ((Number) row[3]).longValue();
            return new AiCallProviderBreakdownDTO(
                (String) row[0],
                (String) row[1],
                total,
                total > 0 ? (double) success / total * 100 : 0.0,
                row[4] != null ? ((Number) row[4]).doubleValue() : 0.0,
                row[5] != null ? ((Number) row[5]).longValue() : 0L
            );
        }).toList();
    }

    public List<AiCallTimelineDTO> getTimeline(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = repository.groupByDateAndCallType(since);
        return rows.stream().map(row -> new AiCallTimelineDTO(
            row[0] != null ? row[0].toString() : "",
            (String) row[1],
            ((Number) row[2]).longValue(),
            ((Number) row[3]).longValue()
        )).toList();
    }

    public List<TokenUsageDTO> getTokenUsage(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = repository.groupTokensByDateAndProvider(since);
        return rows.stream().map(row -> {
            String provider = (String) row[1];
            long inputTokens = row[2] != null ? ((Number) row[2]).longValue() : 0L;
            long outputTokens = row[3] != null ? ((Number) row[3]).longValue() : 0L;
            long totalTokens = row[4] != null ? ((Number) row[4]).longValue() : 0L;
            double cost = estimateCost(provider, inputTokens, outputTokens);
            return new TokenUsageDTO(
                row[0] != null ? row[0].toString() : "",
                provider,
                inputTokens,
                outputTokens,
                totalTokens,
                cost
            );
        }).toList();
    }

    private double estimateCost(String provider, long inputTokens, long outputTokens) {
        Map<String, Double> pricing = PRICING.getOrDefault(provider, Map.of("input", 0.0, "output", 0.0));
        return inputTokens * pricing.get("input") + outputTokens * pricing.get("output");
    }
}
