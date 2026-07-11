package com.meichen.admin.dto;

public record PromptPreviewResponseDTO(
    String positivePrompt,
    String negativePrompt,
    String templateName,
    String templateVersion
) {}
