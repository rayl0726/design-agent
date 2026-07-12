package com.meichen.admin.dto;

import java.util.List;

public record RagZeroResultDTO(
    long totalZeroResultSearches,
    double zeroResultRate,
    List<ZeroResultQuery> topQueries
) {
    public record ZeroResultQuery(String queryText, long searchCount, String lastSearchedAt) {}
}
