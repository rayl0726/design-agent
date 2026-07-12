package com.meichen.admin.dto;

public record DimensionDistributionDTO(
    String dimensionValue,
    long count,
    double percentage
) {}
