package com.meichen.admin.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record PromptPreviewResponseDTO(
    @JsonProperty("positive") String positivePrompt,
    @JsonProperty("negative") String negativePrompt,
    @JsonProperty("template_version") String templateVersion,
    @JsonProperty("aspect_ratio") String aspectRatio
) {}
