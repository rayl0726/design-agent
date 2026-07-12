package com.meichen.admin.service;

import com.meichen.admin.dto.MetricsTrendDTO;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.meichen.admin.repository.ProjectReadRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class MetricsTrendService {

    private final ProjectReadRepository projectRepo;
    private final FeedbackReadRepository feedbackRepo;

    public MetricsTrendService(ProjectReadRepository projectRepo,
                               FeedbackReadRepository feedbackRepo) {
        this.projectRepo = projectRepo;
        this.feedbackRepo = feedbackRepo;
    }

    public List<MetricsTrendDTO> getProjectTrend(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<Object[]> rows = projectRepo.countByDate(since);
        long cumulative = projectRepo.countByCreatedAtBefore(since);
        List<MetricsTrendDTO> result = new ArrayList<>();
        for (Object[] row : rows) {
            String date = ((java.sql.Date) row[0]).toLocalDate().toString();
            long count = ((Number) row[1]).longValue();
            cumulative += count;
            result.add(new MetricsTrendDTO(date, count, cumulative));
        }
        return result;
    }

    public List<MetricsTrendDTO> getFeedbackTrend(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<Object[]> rows = feedbackRepo.countByDate(since);
        long cumulative = feedbackRepo.countByCreatedAtBefore(since);
        List<MetricsTrendDTO> result = new ArrayList<>();
        for (Object[] row : rows) {
            String date = ((java.sql.Date) row[0]).toLocalDate().toString();
            long count = ((Number) row[1]).longValue();
            cumulative += count;
            result.add(new MetricsTrendDTO(date, count, cumulative));
        }
        return result;
    }
}
