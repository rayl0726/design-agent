package com.meichen.admin.dto;

public record AliasProposalDTO(
    String intentField,
    String originalValue,
    String correctedValue,
    long occurrenceCount,
    String status
) {}
