package com.meichen.admin.dto;

public record ErrorDistributionDTO(
    String nodeName,
    long errorCount,
    String errorMessage
) {}
