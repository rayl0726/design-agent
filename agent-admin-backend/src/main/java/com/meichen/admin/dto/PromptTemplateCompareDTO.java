package com.meichen.admin.dto;

import java.util.List;

public record PromptTemplateCompareDTO(
    String version,
    long totalImages,
    long feedbackCount,
    double feedbackRate,
    double positiveRate,
    double negativeRate,
    List<TagCount> topTags
) {
    public record TagCount(String tag, long count) {}
}
