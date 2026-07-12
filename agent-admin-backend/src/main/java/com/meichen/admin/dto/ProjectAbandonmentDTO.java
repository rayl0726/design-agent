package com.meichen.admin.dto;

import java.time.LocalDateTime;

public record ProjectAbandonmentDTO(
    String projectId,
    String projectName,
    LocalDateTime createdAt,
    long daysIdle
) {}
