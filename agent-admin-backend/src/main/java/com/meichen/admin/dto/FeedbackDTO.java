package com.meichen.admin.dto;

import java.time.LocalDateTime;

public record FeedbackDTO(
    String id,
    String projectId,
    String feedbackType,
    String category,
    String intentField,
    String originalValue,
    String correctedValue,
    Boolean processed,
    String notes,
    Integer ideaIndex,
    String pointName,
    Integer imageIndex,
    String imageUrl,
    String promptTemplateVersion,
    String tag,
    String comment,
    LocalDateTime createdAt,
    String publicId
) {}
