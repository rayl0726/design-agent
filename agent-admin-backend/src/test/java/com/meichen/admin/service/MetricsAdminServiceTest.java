package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.entity.StageLogStatsRead;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.meichen.admin.repository.ProjectReadRepository;
import com.meichen.admin.repository.StageLogReadRepository;
import com.meichen.admin.repository.StageLogStatsReadRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class MetricsAdminServiceTest {

    private ProjectReadRepository projectRepo;
    private FeedbackReadRepository feedbackRepo;
    private StageLogReadRepository stageLogRepo;
    private StageLogStatsReadRepository stageLogStatsRepo;
    private MetricsAdminService service;

    @BeforeEach
    void setUp() {
        projectRepo = mock(ProjectReadRepository.class);
        feedbackRepo = mock(FeedbackReadRepository.class);
        stageLogRepo = mock(StageLogReadRepository.class);
        stageLogStatsRepo = mock(StageLogStatsReadRepository.class);
        service = new MetricsAdminService(projectRepo, feedbackRepo, stageLogRepo, stageLogStatsRepo);
    }

    @Test
    void getOverview_aggregatesCounts() {
        when(projectRepo.count()).thenReturn(10L);
        when(feedbackRepo.count()).thenReturn(50L);
        when(feedbackRepo.countByFeedbackType("image")).thenReturn(30L);
        when(feedbackRepo.countByFeedbackType("intent")).thenReturn(20L);
        when(stageLogRepo.count()).thenReturn(200L);
        when(projectRepo.countProjectsWithFeedback()).thenReturn(8L);

        MetricsOverviewDTO result = service.getOverview();

        assertThat(result.projectCount()).isEqualTo(10);
        assertThat(result.feedbackCount()).isEqualTo(50);
        assertThat(result.imageFeedbackCount()).isEqualTo(30);
        assertThat(result.intentCorrectionCount()).isEqualTo(20);
        assertThat(result.stageLogCount()).isEqualTo(200);
        assertThat(result.projectsWithFeedbackCount()).isEqualTo(8);
    }

    @Test
    void getStageDurations_mapsRows() {
        StageLogStatsRead stat = mock(StageLogStatsRead.class);
        when(stat.getStageName()).thenReturn("concept_design");
        when(stat.getAvgMs()).thenReturn(5000L);
        when(stat.getP95Ms()).thenReturn(8000L);
        when(stat.getMaxMs()).thenReturn(12000L);
        when(stat.getSuccessCount()).thenReturn(5L);
        when(stat.getFailedCount()).thenReturn(1L);
        when(stageLogStatsRepo.findByWindowStartAfterOrderByWindowStartDesc(any())).thenReturn(Collections.singletonList(stat));

        List<StageDurationDTO> result = service.getStageDurations(24);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).stageName()).isEqualTo("concept_design");
        assertThat(result.get(0).avgMs()).isEqualTo(5000L);
        assertThat(result.get(0).p95Ms()).isEqualTo(8000L);
        assertThat(result.get(0).maxMs()).isEqualTo(12000L);
        assertThat(result.get(0).successCount()).isEqualTo(5L);
        assertThat(result.get(0).failedCount()).isEqualTo(1L);
    }

    @Test
    void getFeedbackDistribution_mapsRows() {
        Object[] row = {"composition", "image", 15L};
        List<Object[]> rows = Collections.singletonList(row);
        when(feedbackRepo.countByTagAndType()).thenReturn(rows);

        List<FeedbackDistributionDTO> result = service.getFeedbackDistribution();

        assertThat(result).hasSize(1);
        assertThat(result.get(0).tag()).isEqualTo("composition");
        assertThat(result.get(0).feedbackType()).isEqualTo("image");
        assertThat(result.get(0).count()).isEqualTo(15L);
    }
}
