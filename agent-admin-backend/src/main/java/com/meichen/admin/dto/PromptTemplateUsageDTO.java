package com.meichen.admin.dto;

import java.util.List;

public record PromptTemplateUsageDTO(
    String templateVersion,
    long totalInvocations,
    long uniqueProjects,
    List<InvocationDay> invocationTrend
) {
    public record InvocationDay(String date, long count) {}
}
