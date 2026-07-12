package com.meichen.admin.dto;

public record ConversationStatsDTO(
    double avgTurns,
    double medianTurns,
    long maxTurns,
    long totalProjects,
    long turns1to3,
    long turns4to6,
    long turns7to10,
    long turns10plus
) {}
