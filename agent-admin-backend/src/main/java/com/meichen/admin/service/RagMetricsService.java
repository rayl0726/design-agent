package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.RagSearchLogReadRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Service
public class RagMetricsService {

    private final RagSearchLogReadRepository repository;

    public RagMetricsService(RagSearchLogReadRepository repository) {
        this.repository = repository;
    }

    public RagOverviewDTO getOverview(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        Object[] row = repository.aggregateOverview(since);
        long total = row[0] != null ? ((Number) row[0]).longValue() : 0L;
        double avgResultCount = row[1] != null ? ((Number) row[1]).doubleValue() : 0.0;
        double avgLatency = row[2] != null ? ((Number) row[2]).doubleValue() : 0.0;
        long cacheHits = row[3] != null ? ((Number) row[3]).longValue() : 0L;
        long timeouts = row[4] != null ? ((Number) row[4]).longValue() : 0L;
        long fallbacks = row[5] != null ? ((Number) row[5]).longValue() : 0L;

        return new RagOverviewDTO(
            total,
            avgResultCount,
            avgLatency,
            total > 0 ? (double) cacheHits / total : 0.0,
            timeouts,
            total > 0 ? (double) fallbacks / total : 0.0
        );
    }

    public List<RagTimelineDTO> getTimeline(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = repository.groupByDay(since);
        List<RagTimelineDTO> result = new ArrayList<>();
        for (Object[] row : rows) {
            result.add(new RagTimelineDTO(
                row[0] != null ? row[0].toString() : "",
                row[1] != null ? ((Number) row[1]).longValue() : 0L,
                row[2] != null ? ((Number) row[2]).doubleValue() : 0.0,
                row[3] != null ? ((Number) row[3]).doubleValue() : 0.0
            ));
        }
        return result;
    }

    public RagZeroResultDTO getZeroResults(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<Object[]> rows = repository.findZeroResults(since);
        long totalZero = rows.stream()
            .mapToLong(r -> r[1] != null ? ((Number) r[1]).longValue() : 0L)
            .sum();

        Object[] overview = repository.aggregateOverview(since);
        long totalSearches = overview[0] != null ? ((Number) overview[0]).longValue() : 0L;

        List<RagZeroResultDTO.ZeroResultQuery> topQueries = new ArrayList<>();
        for (Object[] row : rows.stream().limit(10).toList()) {
            topQueries.add(new RagZeroResultDTO.ZeroResultQuery(
                row[0] != null ? (String) row[0] : "",
                row[1] != null ? ((Number) row[1]).longValue() : 0L,
                row[2] != null ? row[2].toString() : ""
            ));
        }

        return new RagZeroResultDTO(
            totalZero,
            totalSearches > 0 ? (double) totalZero / totalSearches : 0.0,
            topQueries
        );
    }

    public Object getInventory() {
        // Placeholder — Milvus collection stats require calling agent-core
        // Returns empty structure for now; will be populated in a future sprint
        return Collections.emptyMap();
    }
}
