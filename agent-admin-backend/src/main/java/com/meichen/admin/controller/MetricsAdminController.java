package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.MetricsAdminService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/metrics")
public class MetricsAdminController {

    private final MetricsAdminService service;

    public MetricsAdminController(MetricsAdminService service) {
        this.service = service;
    }

    @GetMapping("/overview")
    public ResponseEntity<MetricsOverviewDTO> getOverview() {
        return ResponseEntity.ok(service.getOverview());
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
}
