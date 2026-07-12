package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.HttpRequestLog;
import com.meichen.orchestrator.repository.HttpRequestLogRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
public class HttpRequestLogService {

    private static final Logger log = LoggerFactory.getLogger(HttpRequestLogService.class);

    private final HttpRequestLogRepository repository;

    public HttpRequestLogService(HttpRequestLogRepository repository) {
        this.repository = repository;
    }

    @Async("dialogueExecutor")
    public void saveAsync(String method, String pathPattern, int statusCode, int durationMs) {
        try {
            HttpRequestLog entity = new HttpRequestLog();
            entity.setMethod(method);
            entity.setPathPattern(pathPattern);
            entity.setStatusCode(statusCode);
            entity.setDurationMs(durationMs);
            entity.setCreatedAt(LocalDateTime.now());
            repository.save(entity);
        } catch (Exception e) {
            log.warn("Failed to persist HTTP request log: {}", e.getMessage());
        }
    }
}
