package com.meichen.orchestrator.controller;

import com.meichen.orchestrator.dto.AiCallLogRequest;
import com.meichen.orchestrator.dto.RagSearchLogRequest;
import com.meichen.orchestrator.entity.AiCallLog;
import com.meichen.orchestrator.entity.RagSearchLog;
import com.meichen.orchestrator.repository.AiCallLogRepository;
import com.meichen.orchestrator.repository.RagSearchLogRepository;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;

@RestController
@RequestMapping("/api/v1/internal")
public class InternalLogController {

    private static final Logger log = LoggerFactory.getLogger(InternalLogController.class);

    private final AiCallLogRepository aiCallLogRepository;
    private final RagSearchLogRepository ragSearchLogRepository;

    public InternalLogController(AiCallLogRepository aiCallLogRepository,
                                 RagSearchLogRepository ragSearchLogRepository) {
        this.aiCallLogRepository = aiCallLogRepository;
        this.ragSearchLogRepository = ragSearchLogRepository;
    }

    @PostMapping("/ai-call-logs")
    public ResponseEntity<Void> receiveAiCallLog(@Valid @RequestBody AiCallLogRequest request) {
        try {
            AiCallLog entity = new AiCallLog();
            entity.setCallType(request.getCallType());
            entity.setProvider(request.getProvider());
            entity.setModel(request.getModel());
            entity.setNodeName(request.getNodeName());
            entity.setStatus(request.getStatus());
            entity.setDurationMs(request.getDurationMs());
            entity.setProjectId(request.getProjectId());
            entity.setInputTokens(request.getInputTokens() != null ? request.getInputTokens() : 0);
            entity.setOutputTokens(request.getOutputTokens() != null ? request.getOutputTokens() : 0);
            entity.setTotalTokens(request.getTotalTokens() != null ? request.getTotalTokens() : 0);
            entity.setErrorMessage(request.getErrorMessage());
            entity.setRetryCount(request.getRetryCount() != null ? request.getRetryCount() : 0);
            entity.setCreatedAt(LocalDateTime.now());
            aiCallLogRepository.save(entity);
            return ResponseEntity.ok().build();
        } catch (Exception e) {
            log.error("Failed to persist AI call log: {}", e.getMessage(), e);
            return ResponseEntity.internalServerError().build();
        }
    }

    @PostMapping("/rag-search-logs")
    public ResponseEntity<Void> receiveRagSearchLog(@Valid @RequestBody RagSearchLogRequest request) {
        try {
            RagSearchLog entity = new RagSearchLog();
            entity.setProjectId(request.getProjectId());
            entity.setQueryText(request.getQueryText());
            entity.setSearchType(request.getSearchType());
            entity.setResultCount(request.getResultCount());
            entity.setDurationMs(request.getDurationMs());
            entity.setCacheHit(request.getCacheHit());
            entity.setTimedOut(request.getTimedOut());
            entity.setCreatedAt(LocalDateTime.now());
            ragSearchLogRepository.save(entity);
            return ResponseEntity.ok().build();
        } catch (Exception e) {
            log.error("Failed to persist RAG search log: {}", e.getMessage(), e);
            return ResponseEntity.internalServerError().build();
        }
    }
}
