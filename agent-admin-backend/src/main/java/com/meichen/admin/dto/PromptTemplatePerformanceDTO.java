package com.meichen.admin.dto;

public record PromptTemplatePerformanceDTO(
    String promptTemplateVersion,
    long totalCount,
    long positiveCount,
    long negativeCount
) {}
