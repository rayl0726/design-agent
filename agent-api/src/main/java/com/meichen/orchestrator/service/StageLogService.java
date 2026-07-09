package com.meichen.orchestrator.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.meichen.orchestrator.entity.StageLog;
import com.meichen.orchestrator.repository.StageLogRepository;
import com.meichen.orchestrator.util.PublicIdGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class StageLogService {

    private static final Logger STAGE_LOG = LoggerFactory.getLogger(StageLogService.class);

    private final StageLogRepository stageLogRepository;
    private final PublicIdGenerator publicIdGenerator;
    private final ObjectMapper objectMapper;
    private final ConcurrentHashMap<Long, Long> startNanos = new ConcurrentHashMap<>();

    public StageLogService(StageLogRepository stageLogRepository,
                           PublicIdGenerator publicIdGenerator,
                           ObjectMapper objectMapper) {
        this.stageLogRepository = stageLogRepository;
        this.publicIdGenerator = publicIdGenerator;
        this.objectMapper = objectMapper;
    }

    @Transactional(readOnly = true)
    public List<StageLog> listByProjectId(String projectId) {
        return stageLogRepository.findByProjectIdOrderByStartedAtAscIdAsc(projectId);
    }

    @Transactional(readOnly = true)
    public List<StageLog> listChildren(Long parentId) {
        return stageLogRepository.findByParentIdOrderByStartedAtAscIdAsc(parentId);
    }

    @Transactional
    public StageLog startStage(String projectId, String stageName, String stageLabel, Long userId) {
        return startStage(projectId, stageName, stageLabel, userId, null, null);
    }

    @Transactional
    public StageLog startStage(String projectId, String stageName, String stageLabel, Long userId,
                               Long parentId, Map<String, Object> metadata) {
        StageLog log = new StageLog();
        log.setPublicId(publicIdGenerator.generate());
        log.setProjectId(projectId);
        log.setStageName(stageName);
        log.setStageLabel(stageLabel);
        log.setStatus("RUNNING");
        log.setStartedAt(LocalDateTime.now());
        log.setUserId(userId);
        log.setParentId(parentId);
        if (metadata != null) {
            log.setMetadataJson(toJson(metadata));
        }
        StageLog saved = stageLogRepository.save(log);
        startNanos.put(saved.getId(), System.nanoTime());
        STAGE_LOG.info("[STAGE_START] project={} stage={} label={} logId={}",
                projectId, stageName, stageLabel, saved.getId());
        return saved;
    }

    @Transactional
    public StageLog completeStage(Long stageLogId) {
        return completeStage(stageLogId, null);
    }

    @Transactional
    public StageLog completeStage(Long stageLogId, Map<String, Object> metadata) {
        Optional<StageLog> opt = stageLogRepository.findById(stageLogId);
        if (opt.isEmpty()) {
            STAGE_LOG.warn("[STAGE_COMPLETE] stageLogId={} not found", stageLogId);
            return null;
        }
        StageLog log = opt.get();
        if (!log.isRunning()) {
            STAGE_LOG.warn("[STAGE_COMPLETE] stageLogId={} already finalized, status={}", stageLogId, log.getStatus());
            return log;
        }

        log.setStatus("SUCCESS");
        log.setCompletedAt(LocalDateTime.now());
        long durationMs = computeDurationMs(stageLogId);
        if (durationMs < 0) {
            log.setDurationMs(null);
            log.setTimeAnomaly(true);
            STAGE_LOG.warn("[STAGE_TIME_ANOMALY] stageLogId={} durationMs={}", stageLogId, durationMs);
        } else {
            log.setDurationMs(durationMs);
        }

        if (metadata != null) {
            log.setMetadataJson(toJson(metadata));
        }
        StageLog saved = stageLogRepository.save(log);
        String imageStats = formatImageStats(metadata);
        STAGE_LOG.info("[STAGE_SUCCESS] project={} stage={} label={} durationMs={} logId={} {}",
                log.getProjectId(), log.getStageName(), log.getStageLabel(),
                log.getDurationMs(), saved.getId(), imageStats);
        return saved;
    }

    @Transactional
    public StageLog failStage(Long stageLogId, String errorMessage) {
        Optional<StageLog> opt = stageLogRepository.findById(stageLogId);
        if (opt.isEmpty()) {
            STAGE_LOG.warn("[STAGE_FAIL] stageLogId={} not found", stageLogId);
            return null;
        }
        StageLog log = opt.get();
        if (!log.isRunning()) {
            STAGE_LOG.warn("[STAGE_FAIL] stageLogId={} already finalized, status={}", stageLogId, log.getStatus());
            return log;
        }

        log.setStatus("FAILED");
        log.setCompletedAt(LocalDateTime.now());
        log.setErrorMessage(errorMessage);
        long durationMs = computeDurationMs(stageLogId);
        if (durationMs < 0) {
            log.setDurationMs(null);
            log.setTimeAnomaly(true);
            STAGE_LOG.warn("[STAGE_TIME_ANOMALY] stageLogId={} durationMs={}", stageLogId, durationMs);
        } else {
            log.setDurationMs(durationMs);
        }
        StageLog saved = stageLogRepository.save(log);
        STAGE_LOG.error("[STAGE_FAILED] project={} stage={} label={} durationMs={} logId={} error={}",
                log.getProjectId(), log.getStageName(), log.getStageLabel(),
                log.getDurationMs(), saved.getId(), errorMessage);
        return saved;
    }

    private long computeDurationMs(Long stageLogId) {
        Long startNano = startNanos.remove(stageLogId);
        if (startNano == null) {
            return -1;
        }
        return (System.nanoTime() - startNano) / 1_000_000L;
    }

    @Transactional
    public StageLog startSubStage(Long parentId, String stageName, String stageLabel, Long userId) {
        String projectId = null;
        if (parentId != null) {
            projectId = stageLogRepository.findById(parentId)
                    .map(StageLog::getProjectId)
                    .orElse(null);
        }
        return startStage(projectId, stageName, stageLabel, userId, parentId, null);
    }

    @Transactional
    public StageLog completeSubStage(Long stageLogId) {
        return completeStage(stageLogId, null);
    }

    @Transactional
    public StageLog updateMetadata(Long stageLogId, Map<String, Object> metadata) {
        Optional<StageLog> opt = stageLogRepository.findById(stageLogId);
        if (opt.isEmpty()) {
            return null;
        }
        StageLog log = opt.get();
        log.setMetadataJson(toJson(metadata));
        return stageLogRepository.save(log);
    }

    private String formatImageStats(Map<String, Object> metadata) {
        if (metadata == null) {
            return "";
        }
        Object total = metadata.get("total_images");
        Object success = metadata.get("success_images");
        Object failed = metadata.get("failed_images");
        if (total == null) {
            return "";
        }
        return String.format("images=%s/%s failed=%s", success, total, failed);
    }

    private String toJson(Map<String, Object> metadata) {
        try {
            return objectMapper.writeValueAsString(metadata);
        } catch (JsonProcessingException e) {
            return "{}";
        }
    }
}
