package com.meichen.admin.dto;

public record PromptPreviewRequestDTO(
    String theme,
    String spaceType,
    String budgetLevel,
    String style
) {}
