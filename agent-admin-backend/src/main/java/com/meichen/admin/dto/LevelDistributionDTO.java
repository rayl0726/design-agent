package com.meichen.admin.dto;

public record LevelDistributionDTO(
    String level,
    long count,
    double percentage
) {}
