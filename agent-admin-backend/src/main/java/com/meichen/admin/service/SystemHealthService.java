package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.HttpRequestLogReadRepository;
import com.meichen.admin.repository.StageLogReadRepository;
import com.meichen.admin.repository.WorkflowLogReadRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class SystemHealthService {

    private final StageLogReadRepository stageLogRepo;
    private final WorkflowLogReadRepository workflowLogRepo;
    private final HttpRequestLogReadRepository httpLogRepo;
    private final ActuatorClient actuatorClient;

    public SystemHealthService(StageLogReadRepository stageLogRepo,
                               WorkflowLogReadRepository workflowLogRepo,
                               HttpRequestLogReadRepository httpLogRepo,
                               ActuatorClient actuatorClient) {
        this.stageLogRepo = stageLogRepo;
        this.workflowLogRepo = workflowLogRepo;
        this.httpLogRepo = httpLogRepo;
        this.actuatorClient = actuatorClient;
    }

    public List<WorkflowSuccessDTO> getWorkflowSuccess(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<Object[]> rows = stageLogRepo.aggregateWorkflowSuccess(since);
        return rows.stream().map(row -> {
            long total = ((Number) row[1]).longValue();
            long success = ((Number) row[2]).longValue();
            long failed = ((Number) row[3]).longValue();
            return new WorkflowSuccessDTO(
                (String) row[0],
                total,
                success,
                failed,
                total > 0 ? (double) success / total * 100 : 0.0
            );
        }).toList();
    }

    public List<RetryDistributionDTO> getRetries(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<Object[]> rows = workflowLogRepo.aggregateRetries(since);
        return rows.stream().map(row -> new RetryDistributionDTO(
            (String) row[0],
            ((Number) row[1]).longValue(),
            row[2] != null ? ((Number) row[2]).longValue() : 0L,
            row[3] != null ? ((Number) row[3]).longValue() : 0L
        )).toList();
    }

    public List<ErrorDistributionDTO> getErrors(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<Object[]> rows = workflowLogRepo.aggregateErrors(since);
        return rows.stream().map(row -> new ErrorDistributionDTO(
            (String) row[0],
            ((Number) row[1]).longValue(),
            (String) row[2]
        )).toList();
    }

    public AnomalyStatsDTO getAnomalies(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        Object[] counts = stageLogRepo.countAnomalies(since);
        long timeAnomaly = counts[0] != null ? ((Number) counts[0]).longValue() : 0L;
        long overflow = counts[1] != null ? ((Number) counts[1]).longValue() : 0L;

        List<Object[]> stageRows = stageLogRepo.findAnomalyStages(since);
        List<AnomalyStatsDTO.AnomalyStageDTO> affectedStages = stageRows.stream().map(row ->
            new AnomalyStatsDTO.AnomalyStageDTO(
                (String) row[0],
                row[1] != null ? ((Number) row[1]).longValue() : 0L,
                row[2] != null ? ((Number) row[2]).longValue() : 0L
            )
        ).toList();

        return new AnomalyStatsDTO(timeAnomaly, overflow, affectedStages);
    }

    public HttpMetricsDTO getHttpMetrics(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        Object[] overall = httpLogRepo.aggregateHttp(since);
        long totalRequests = overall[0] != null ? ((Number) overall[0]).longValue() : 0L;
        long errorCount = overall[1] != null ? ((Number) overall[1]).longValue() : 0L;
        double avgDuration = overall[2] != null ? ((Number) overall[2]).doubleValue() : 0.0;
        long maxDuration = overall[3] != null ? ((Number) overall[3]).longValue() : 0L;

        List<Object[]> pathRows = httpLogRepo.groupByPathPattern(since);
        List<HttpMetricsDTO.HttpPathBreakdownDTO> topEndpoints = pathRows.stream().map(row ->
            new HttpMetricsDTO.HttpPathBreakdownDTO(
                (String) row[0],
                ((Number) row[1]).longValue(),
                row[2] != null ? ((Number) row[2]).longValue() : 0L,
                row[3] != null ? ((Number) row[3]).doubleValue() : 0.0
            )
        ).toList();

        return new HttpMetricsDTO(
            totalRequests,
            errorCount,
            totalRequests > 0 ? (double) errorCount / totalRequests * 100 : 0.0,
            avgDuration,
            maxDuration,
            topEndpoints
        );
    }

    public List<ThreadPoolMetricsDTO> getThreadPools() {
        return actuatorClient.getThreadPoolMetrics();
    }

    public DbPoolMetricsDTO getDbPool() {
        return actuatorClient.getDbPoolMetrics();
    }
}
