package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.meichen.admin.repository.ProjectReadRepository;
import com.meichen.admin.repository.StageLogReadRepository;
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
    private MetricsAdminService service;

    @BeforeEach
    void setUp() {
        projectRepo = mock(ProjectReadRepository.class);
        feedbackRepo = mock(FeedbackReadRepository.class);
        stageLogRepo = mock(StageLogReadRepository.class);
        service = new MetricsAdminService(projectRepo, feedbackRepo, stageLogRepo);
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
        Object[] row = {"concept_design", 5000.0, 8000.0, 12000L, 5, 1};
        List<Object[]> rows = Collections.singletonList(row);
        when(stageLogRepo.aggregateByStageNameSince(any())).thenReturn(rows);

        List<StageDurationDTO> result = service.getStageDurations(24);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).stageName()).isEqualTo("concept_design");
        assertThat(result.get(0).avgMs()).isEqualTo(5000.0);
        assertThat(result.get(0).p95Ms()).isEqualTo(8000.0);
        assertThat(result.get(0).maxMs()).isEqualTo(12000L);
        assertThat(result.get(0).successCount()).isEqualTo(5);
        assertThat(result.get(0).failedCount()).isEqualTo(1);
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
