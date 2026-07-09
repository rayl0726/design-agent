package com.meichen.orchestrator.scheduler;

import com.meichen.orchestrator.entity.StageLogStats;
import com.meichen.orchestrator.repository.StageLogRepository;
import com.meichen.orchestrator.repository.StageLogStatsRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Component
public class StageLogStatsAggregator {

    private static final Logger log = LoggerFactory.getLogger(StageLogStatsAggregator.class);

    private final StageLogRepository stageLogRepository;
    private final StageLogStatsRepository stageLogStatsRepository;

    public StageLogStatsAggregator(StageLogRepository stageLogRepository,
                                   StageLogStatsRepository stageLogStatsRepository) {
        this.stageLogRepository = stageLogRepository;
        this.stageLogStatsRepository = stageLogStatsRepository;
    }

    @Scheduled(fixedDelay = 60_000)
    @Transactional
    public void aggregate() {
        LocalDateTime windowEnd = LocalDateTime.now().withSecond(0).withNano(0);
        LocalDateTime windowStart = windowEnd.minusHours(1);

        List<Object[]> rows = stageLogRepository.aggregateByStageNameSince(windowStart);
        for (Object[] row : rows) {
            String stageName = (String) row[0];
            Double avgMsDouble = (Double) row[1];
            Long maxMs = (Long) row[2];
            Long successCount = (Long) row[3];
            Long failedCount = (Long) row[4];
            Long totalCount = (Long) row[5];

            Long avgMs = avgMsDouble != null ? avgMsDouble.longValue() : null;
            Long p95Ms = computeP95(stageName, windowStart, windowEnd);

            StageLogStats stats = stageLogStatsRepository
                .findByStageNameAndWindowStartAndWindowEnd(stageName, windowStart, windowEnd)
                .orElse(new StageLogStats());
            stats.setStageName(stageName);
            stats.setWindowStart(windowStart);
            stats.setWindowEnd(windowEnd);
            stats.setAvgMs(avgMs);
            stats.setP95Ms(p95Ms);
            stats.setMaxMs(maxMs);
            stats.setSuccessCount(successCount != null ? successCount : 0L);
            stats.setFailedCount(failedCount != null ? failedCount : 0L);
            stageLogStatsRepository.save(stats);

            log.debug("Aggregated stats for {}: count={}, avgMs={}", stageName, totalCount, avgMs);
        }
    }

    private Long computeP95(String stageName, LocalDateTime windowStart, LocalDateTime windowEnd) {
        List<Long> durations = stageLogRepository.findDurations(stageName, windowStart, windowEnd);
        if (durations.isEmpty()) {
            return null;
        }
        int index = (int) Math.ceil(durations.size() * 0.95) - 1;
        return durations.get(Math.max(index, 0));
    }
}
