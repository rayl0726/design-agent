package com.meichen.orchestrator.service;

public record LoginResponse(String token, Long userId, String phone) {}
