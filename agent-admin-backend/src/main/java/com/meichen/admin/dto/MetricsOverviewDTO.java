package com.meichen.admin.dto;

public record MetricsOverviewDTO(
    long projectCount,
    long feedbackCount,
    long imageFeedbackCount,
    long intentCorrectionCount,
    long stageLogCount,
    long projectsWithFeedbackCount
) {}
