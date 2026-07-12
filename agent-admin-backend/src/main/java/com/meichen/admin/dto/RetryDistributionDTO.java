package com.meichen.admin.dto;

public record RetryDistributionDTO(
    String nodeName,
    long totalExecutions,
    long totalRetries,
    long executionsWithRetry
) {}
