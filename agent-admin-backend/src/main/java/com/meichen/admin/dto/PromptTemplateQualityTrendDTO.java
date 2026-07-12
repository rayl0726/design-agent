package com.meichen.admin.dto;

import java.util.List;

public record PromptTemplateQualityTrendDTO(
    String date,
    String templateVersion,
    long imagesGenerated,
    long feedbackCount,
    double feedbackRate,
    List<TagCount> tagDistribution
) {
    public record TagCount(String tag, long count) {}
}
