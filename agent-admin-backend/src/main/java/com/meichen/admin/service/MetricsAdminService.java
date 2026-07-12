package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.entity.StageLogStatsRead;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.meichen.admin.repository.ProjectReadRepository;
import com.meichen.admin.repository.StageLogReadRepository;
import com.meichen.admin.repository.StageLogStatsReadRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class MetricsAdminService {

    private final ProjectReadRepository projectRepo;
    private final FeedbackReadRepository feedbackRepo;
    private final StageLogReadRepository stageLogRepo;
    private final StageLogStatsReadRepository stageLogStatsRepo;

    public MetricsAdminService(ProjectReadRepository projectRepo,
                               FeedbackReadRepository feedbackRepo,
                               StageLogReadRepository stageLogRepo,
                               StageLogStatsReadRepository stageLogStatsRepo) {
        this.projectRepo = projectRepo;
        this.feedbackRepo = feedbackRepo;
        this.stageLogRepo = stageLogRepo;
        this.stageLogStatsRepo = stageLogStatsRepo;
    }

    public MetricsOverviewDTO getOverview() {
        return getOverview(0);
    }

    public MetricsOverviewDTO getOverview(int hours) {
        if (hours <= 0) {
            return new MetricsOverviewDTO(
                projectRepo.count(),
                feedbackRepo.count(),
                feedbackRepo.countByFeedbackType("image"),
                feedbackRepo.countByFeedbackType("intent"),
                stageLogRepo.count(),
                projectRepo.countProjectsWithFeedback(),
                0, 0
            );
        }
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        return new MetricsOverviewDTO(
            projectRepo.count(),
            feedbackRepo.count(),
            feedbackRepo.countByFeedbackType("image"),
            feedbackRepo.countByFeedbackType("intent"),
            stageLogRepo.count(),
            projectRepo.countProjectsWithFeedback(),
            projectRepo.countByCreatedAtAfter(since),
            projectRepo.countByStatusAndCreatedAtAfter("completed", since)
        );
    }

    public List<StageDurationDTO> getStageDurations(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<StageLogStatsRead> stats = stageLogStatsRepo.findByWindowStartAfterOrderByWindowStartDesc(since);
        return stats.stream().map(s -> new StageDurationDTO(
            s.getStageName(),
            s.getAvgMs(),
            s.getP95Ms(),
            s.getMaxMs(),
            s.getSuccessCount() != null ? s.getSuccessCount() : 0L,
            s.getFailedCount() != null ? s.getFailedCount() : 0L
        )).toList();
    }

    public List<FeedbackDistributionDTO> getFeedbackDistribution() {
        List<Object[]> rows = feedbackRepo.countByTagAndType();
        return rows.stream().map(row -> new FeedbackDistributionDTO(
            (String) row[0],
            (String) row[1],
            ((Number) row[2]).longValue()
        )).toList();
    }
}
