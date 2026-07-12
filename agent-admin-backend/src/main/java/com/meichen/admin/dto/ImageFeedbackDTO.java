package com.meichen.admin.dto;

import java.util.List;
import java.util.Map;

public record ImageFeedbackDTO(
    long totalImages,
    long imagesWithFeedback,
    double feedbackRate,
    Map<String, Long> tagDistribution
) {}
