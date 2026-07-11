package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.meichen.admin.repository.ProjectReadRepository;
import com.meichen.admin.repository.StageLogReadRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class MetricsAdminService {

    private final ProjectReadRepository projectRepo;
    private final FeedbackReadRepository feedbackRepo;
    private final StageLogReadRepository stageLogRepo;

    public MetricsAdminService(ProjectReadRepository projectRepo,
                               FeedbackReadRepository feedbackRepo,
                               StageLogReadRepository stageLogRepo) {
        this.projectRepo = projectRepo;
        this.feedbackRepo = feedbackRepo;
        this.stageLogRepo = stageLogRepo;
    }

    public MetricsOverviewDTO getOverview() {
        return new MetricsOverviewDTO(
            projectRepo.count(),
            feedbackRepo.count(),
            feedbackRepo.countByFeedbackType("image"),
            feedbackRepo.countByFeedbackType("intent"),
            stageLogRepo.count(),
            projectRepo.countProjectsWithFeedback()
        );
    }

    public List<StageDurationDTO> getStageDurations(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = stageLogRepo.aggregateByStageNameSince(since);
        return rows.stream().map(row -> new StageDurationDTO(
            (String) row[0],
            row[1] != null ? ((Number) row[1]).doubleValue() : null,
            row[2] != null ? ((Number) row[2]).doubleValue() : null,
            row[3] != null ? ((Number) row[3]).longValue() : null,
            row[4] != null ? ((Number) row[4]).intValue() : 0,
            row[5] != null ? ((Number) row[5]).intValue() : 0
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
