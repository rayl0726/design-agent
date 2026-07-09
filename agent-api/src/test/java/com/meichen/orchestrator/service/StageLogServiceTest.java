package com.meichen.orchestrator.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.meichen.orchestrator.entity.StageLog;
import com.meichen.orchestrator.repository.StageLogRepository;
import com.meichen.orchestrator.util.PublicIdGenerator;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class StageLogServiceTest {

    @Mock
    private StageLogRepository stageLogRepository;

    private StageLogService stageLogService;
    private long nextId = 1L;

    @BeforeEach
    void setUp() {
        PublicIdGenerator publicIdGenerator = new PublicIdGenerator();
        stageLogService = new StageLogService(stageLogRepository, publicIdGenerator, new ObjectMapper());
        when(stageLogRepository.save(any(StageLog.class))).thenAnswer(inv -> {
            StageLog arg = inv.getArgument(0);
            if (arg.getId() == null) {
                arg.setId(nextId++);
            }
            return arg;
        });
    }

    @Test
    void completeStage_shouldBeIdempotent() {
        StageLog log = stageLogService.startStage("p1", "VISION_DESIGN", "视觉设计", 1L);
        Long logId = log.getId();
        when(stageLogRepository.findById(logId)).thenReturn(Optional.of(log));

        StageLog first = stageLogService.completeStage(logId);
        StageLog second = stageLogService.completeStage(logId);

        assertThat(second.getStatus()).isEqualTo("SUCCESS");
        assertThat(second.getDurationMs()).isEqualTo(first.getDurationMs());
        assertThat(second.isTimeAnomaly()).isFalse();
    }

    @Test
    void completeStage_shouldMarkTimeAnomalyWhenStartNanoMissing() {
        StageLog log = new StageLog();
        log.setId(2L);
        log.setProjectId("p1");
        log.setStageName("VISION_DESIGN");
        log.setStatus("RUNNING");
        log.setStartedAt(LocalDateTime.now());
        when(stageLogRepository.findById(2L)).thenReturn(Optional.of(log));

        StageLog result = stageLogService.completeStage(2L);

        assertThat(result.getStatus()).isEqualTo("SUCCESS");
        assertThat(result.getDurationMs()).isNull();
        assertThat(result.isTimeAnomaly()).isTrue();
    }

    @Test
    void completeStage_shouldComputeNonNegativeDuration() {
        StageLog log = stageLogService.startStage("p1", "VISION_DESIGN", "视觉设计", 1L);
        Long logId = log.getId();
        when(stageLogRepository.findById(logId)).thenReturn(Optional.of(log));

        StageLog result = stageLogService.completeStage(logId);

        assertThat(result.getDurationMs()).isNotNull();
        assertThat(result.getDurationMs()).isGreaterThanOrEqualTo(0L);
        assertThat(result.isTimeAnomaly()).isFalse();
    }

    @Test
    void failStage_shouldMarkTimeAnomalyWhenStartNanoMissing() {
        StageLog log = new StageLog();
        log.setId(3L);
        log.setProjectId("p1");
        log.setStageName("VISION_DESIGN");
        log.setStatus("RUNNING");
        log.setStartedAt(LocalDateTime.now());
        when(stageLogRepository.findById(3L)).thenReturn(Optional.of(log));

        StageLog result = stageLogService.failStage(3L, "timeout");

        assertThat(result.getStatus()).isEqualTo("FAILED");
        assertThat(result.getDurationMs()).isNull();
        assertThat(result.isTimeAnomaly()).isTrue();
        assertThat(result.getErrorMessage()).isEqualTo("timeout");
    }

    @Test
    void startSubStage_shouldInheritParentProjectId() {
        StageLog parent = new StageLog();
        parent.setId(10L);
        parent.setProjectId("p1");
        when(stageLogRepository.findById(10L)).thenReturn(Optional.of(parent));

        StageLog child = stageLogService.startSubStage(10L, "IMAGE_GENERATION", "图片生成", 1L);

        assertThat(child.getParentId()).isEqualTo(10L);
        assertThat(child.getProjectId()).isEqualTo("p1");
        assertThat(child.getStatus()).isEqualTo("RUNNING");
    }

    @Test
    void completeSubStage_shouldFinalizeChildStage() {
        StageLog parent = new StageLog();
        parent.setId(20L);
        parent.setProjectId("p1");
        when(stageLogRepository.findById(20L)).thenReturn(Optional.of(parent));

        StageLog child = stageLogService.startSubStage(20L, "IMAGE_GENERATION", "图片生成", 1L);
        Long childId = child.getId();
        when(stageLogRepository.findById(childId)).thenReturn(Optional.of(child));

        StageLog result = stageLogService.completeSubStage(childId);

        assertThat(result.getStatus()).isEqualTo("SUCCESS");
        assertThat(result.getDurationMs()).isNotNull();
        assertThat(result.isTimeAnomaly()).isFalse();
    }
}
