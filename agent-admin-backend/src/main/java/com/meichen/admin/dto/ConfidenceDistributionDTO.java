package com.meichen.admin.dto;

import java.util.List;

public record ConfidenceDistributionDTO(
    List<ConfidenceBucket> buckets,
    double lowConfidenceRate
) {
    public record ConfidenceBucket(String bucket, long count, double percentage) {}
}
