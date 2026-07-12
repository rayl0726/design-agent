package com.meichen.admin.dto;

public record ApplyAliasRequestDTO(
    String intentField,
    String originalValue,
    String correctedValue
) {}
