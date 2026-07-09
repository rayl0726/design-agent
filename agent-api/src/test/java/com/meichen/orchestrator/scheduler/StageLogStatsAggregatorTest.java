package com.meichen.orchestrator.scheduler;

import com.meichen.orchestrator.entity.StageLogStats;
import com.meichen.orchestrator.repository.StageLogRepository;
import com.meichen.orchestrator.repository.StageLogStatsRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class StageLogStatsAggregatorTest {

    @Mock
    private StageLogRepository stageLogRepository;

    @Mock
    private StageLogStatsRepository stageLogStatsRepository;

    @Test
    void aggregate_shouldComputeStatsAndSave() {
        LocalDateTime windowStart = LocalDateTime.now().minusHours(1).withSecond(0).withNano(0);
        LocalDateTime windowEnd = LocalDateTime.now().withSecond(0).withNano(0);

        Object[] row = new Object[]{
            "visual_design",
            90_000.0,
            200_000L,
            9L,
            1L,
            10L
        };

        when(stageLogRepository.aggregateByStageNameSince(any(LocalDateTime.class)))
            .thenReturn(List.<Object[]>of(row));
        when(stageLogStatsRepository.findByStageNameAndWindowStartAndWindowEnd(any(), any(), any()))
            .thenReturn(Optional.empty());

        StageLogStatsAggregator aggregator = new StageLogStatsAggregator(stageLogRepository, stageLogStatsRepository);
        aggregator.aggregate();

        ArgumentCaptor<StageLogStats> captor = ArgumentCaptor.forClass(StageLogStats.class);
        verify(stageLogStatsRepository).save(captor.capture());

        StageLogStats saved = captor.getValue();
        assertThat(saved.getStageName()).isEqualTo("visual_design");
        assertThat(saved.getAvgMs()).isEqualTo(90_000L);
        assertThat(saved.getMaxMs()).isEqualTo(200_000L);
        assertThat(saved.getSuccessCount()).isEqualTo(9L);
        assertThat(saved.getFailedCount()).isEqualTo(1L);
    }
}
