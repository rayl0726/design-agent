package com.meichen.admin.dto;

public record ImageGenOverviewDTO(
    long totalGenerated,
    long successCount,
    long failedCount,
    double successRate,
    double avgGenerationMs,
    double avgImagesPerProject
) {}
