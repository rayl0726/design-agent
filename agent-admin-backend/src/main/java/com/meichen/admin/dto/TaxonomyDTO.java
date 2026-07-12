package com.meichen.admin.dto;

import java.util.List;
import java.util.Map;

public record TaxonomyDTO(
    String version,
    List<TaxonomyEntry> spaceTypes,
    List<TaxonomyEntry> points,
    List<TaxonomyEntry> budgetLevels,
    List<TaxonomyEntry> styles,
    List<TaxonomyEntry> materials,
    Map<String, Object> fieldDefaults
) {
    public record TaxonomyEntry(String name, List<String> aliases) {}
}
