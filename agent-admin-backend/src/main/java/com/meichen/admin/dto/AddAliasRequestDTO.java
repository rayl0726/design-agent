package com.meichen.admin.dto;

public record AddAliasRequestDTO(
    String section,
    String canonicalName,
    String alias
) {}
