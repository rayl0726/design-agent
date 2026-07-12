package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.AiModelMetricsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/metrics/ai-calls")
public class AiModelMetricsController {

    private final AiModelMetricsService service;

    public AiModelMetricsController(AiModelMetricsService service) {
        this.service = service;
    }

    @GetMapping("/summary")
    public ResponseEntity<List<AiCallSummaryDTO>> getSummary(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getCallSummary(hours));
    }

    @GetMapping("/by-provider")
    public ResponseEntity<List<AiCallProviderBreakdownDTO>> getByProvider(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getByProvider(hours));
    }

    @GetMapping("/timeline")
    public ResponseEntity<List<AiCallTimelineDTO>> getTimeline(
            @RequestParam(defaultValue = "168") int hours) {
        return ResponseEntity.ok(service.getTimeline(hours));
    }

    @GetMapping("/tokens")
    public ResponseEntity<List<TokenUsageDTO>> getTokens(
            @RequestParam(defaultValue = "168") int hours) {
        return ResponseEntity.ok(service.getTokenUsage(hours));
    }
}
