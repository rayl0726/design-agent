package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.RagMetricsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/metrics/rag")
public class RagMetricsController {

    private final RagMetricsService service;

    public RagMetricsController(RagMetricsService service) {
        this.service = service;
    }

    @GetMapping("/overview")
    public ResponseEntity<RagOverviewDTO> getOverview(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getOverview(hours));
    }

    @GetMapping("/timeline")
    public ResponseEntity<List<RagTimelineDTO>> getTimeline(
            @RequestParam(defaultValue = "168") int hours) {
        return ResponseEntity.ok(service.getTimeline(hours));
    }

    @GetMapping("/inventory")
    public ResponseEntity<Object> getInventory() {
        return ResponseEntity.ok(service.getInventory());
    }

    @GetMapping("/zero-results")
    public ResponseEntity<RagZeroResultDTO> getZeroResults(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(service.getZeroResults(days));
    }
}
