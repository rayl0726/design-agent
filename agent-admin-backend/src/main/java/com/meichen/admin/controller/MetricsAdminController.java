package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.MetricsAdminService;
import com.meichen.admin.service.MetricsTrendService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/metrics")
public class MetricsAdminController {

    private final MetricsAdminService service;
    private final MetricsTrendService trendService;

    public MetricsAdminController(MetricsAdminService service,
                                  MetricsTrendService trendService) {
        this.service = service;
        this.trendService = trendService;
    }

    @GetMapping("/overview")
    public ResponseEntity<MetricsOverviewDTO> getOverview(
            @RequestParam(required = false, defaultValue = "0") int hours) {
        return ResponseEntity.ok(service.getOverview(hours));
    }

    @GetMapping("/stages")
    public ResponseEntity<List<StageDurationDTO>> getStageDurations(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getStageDurations(hours));
    }

    @GetMapping("/feedback-distribution")
    public ResponseEntity<List<FeedbackDistributionDTO>> getFeedbackDistribution() {
        return ResponseEntity.ok(service.getFeedbackDistribution());
    }

    @GetMapping("/trend/projects")
    public ResponseEntity<List<MetricsTrendDTO>> getProjectTrend(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(trendService.getProjectTrend(days));
    }

    @GetMapping("/trend/feedback")
    public ResponseEntity<List<MetricsTrendDTO>> getFeedbackTrend(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(trendService.getFeedbackTrend(days));
    }
}
