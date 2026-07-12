package com.meichen.admin.dto;

public record DialogueTurnDTO(
    String turnRange, long count, double percentage,
    double avgTurns, double medianTurns
) {}
