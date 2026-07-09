package com.meichen.orchestrator.service;

import com.meichen.orchestrator.dto.StageLogStatsDto;
import com.meichen.orchestrator.entity.StageLog;
import com.meichen.orchestrator.repository.StageLogRepository;
import com.meichen.orchestrator.repository.StageLogStatsRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class StageLogAnalyticsService {

    private final StageLogRepository stageLogRepository;
    private final StageLogStatsRepository stageLogStatsRepository;

    public StageLogAnalyticsService(StageLogRepository stageLogRepository,
                                    StageLogStatsRepository stageLogStatsRepository) {
        this.stageLogRepository = stageLogRepository;
        this.stageLogStatsRepository = stageLogStatsRepository;
    }

    @Transactional(readOnly = true)
    public List<StageLogStatsDto> getStageMetrics(LocalDateTime since) {
        List<com.meichen.orchestrator.entity.StageLogStats> stats =
            stageLogStatsRepository.findByWindowEndAfterOrderByStageNameAscWindowStartAsc(since);
        return stats.stream().map(StageLogStatsDto::fromEntity).toList();
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> getProjectTimeline(String projectId) {
        List<StageLog> logs = stageLogRepository.findByProjectIdOrderByStartedAtAscIdAsc(projectId);
        return logs.stream()
            .filter(log -> log.getParentId() == null)
            .map(log -> {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("stageName", log.getStageName());
                m.put("stageLabel", log.getStageLabel());
                m.put("status", log.getStatus());
                m.put("durationMs", log.getDurationMs());
                m.put("timeAnomaly", log.isTimeAnomaly());
                m.put("subStageOverflow", log.isSubStageOverflow());
                return m;
            }).toList();
    }

    @Transactional(readOnly = true)
    public Map<String, StageLogStatsDto> getLatestMetricsByStage() {
        LocalDateTime since = LocalDateTime.now().minusHours(24);
        List<StageLogStatsDto> all = getStageMetrics(since);
        Map<String, StageLogStatsDto> latest = new LinkedHashMap<>();
        for (StageLogStatsDto dto : all) {
            latest.merge(dto.stageName(), dto, (a, b) ->
                a.windowEnd().isAfter(b.windowEnd()) ? a : b);
        }
        return latest;
    }
}
