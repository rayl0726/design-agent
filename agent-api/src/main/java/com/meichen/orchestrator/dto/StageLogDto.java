package com.meichen.orchestrator.dto;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.meichen.orchestrator.entity.StageLog;

import java.time.LocalDateTime;
import java.util.Collections;
import java.util.Map;

public record StageLogDto(
    Long id,
    String publicId,
    String projectId,
    Long parentId,
    String stageName,
    String stageLabel,
    String status,
    LocalDateTime startedAt,
    LocalDateTime completedAt,
    Long durationMs,
    String errorMessage,
    Map<String, Object> metadata,
    Long userId,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    public static StageLogDto fromEntity(StageLog entity) {
        return new StageLogDto(
            entity.getId(),
            entity.getPublicId(),
            entity.getProjectId(),
            entity.getParentId(),
            entity.getStageName(),
            entity.getStageLabel(),
            entity.getStatus(),
            entity.getStartedAt(),
            entity.getCompletedAt(),
            entity.getDurationMs(),
            entity.getErrorMessage(),
            parseMetadata(entity.getMetadataJson()),
            entity.getUserId(),
            entity.getCreatedAt(),
            entity.getUpdatedAt()
        );
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> parseMetadata(String json) {
        if (json == null || json.isBlank()) {
            return Collections.emptyMap();
        }
        try {
            return OBJECT_MAPPER.readValue(json, Map.class);
        } catch (JsonProcessingException e) {
            return Collections.emptyMap();
        }
    }
}
