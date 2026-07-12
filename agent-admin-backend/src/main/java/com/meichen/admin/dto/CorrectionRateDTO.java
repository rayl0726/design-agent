package com.meichen.admin.dto;

import java.util.List;

public record CorrectionRateDTO(
    String field, long totalRecognitions, long correctionCount,
    double correctionRate, List<TopCorrectedValue> topCorrectedValues
) {
    public record TopCorrectedValue(String original, long count) {}
}
