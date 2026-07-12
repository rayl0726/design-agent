package com.meichen.admin.dto;

public record AliasProposalStatsDTO(
    long totalProposals, long pendingCount, long appliedCount, double rejectionRate
) {}
