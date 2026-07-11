package com.meichen.admin.dto;

public record PromptPreviewRequestDTO(
    String theme,
    String spaceType,
    Integer budget,
    String style
) {}
