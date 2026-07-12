package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.ImageGenMetricsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/admin/metrics/image-generation")
public class ImageGenMetricsController {

    private final ImageGenMetricsService service;

    public ImageGenMetricsController(ImageGenMetricsService service) {
        this.service = service;
    }

    @GetMapping("/overview")
    public ResponseEntity<ImageGenOverviewDTO> getOverview(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getOverview(hours));
    }

    @GetMapping("/by-provider")
    public ResponseEntity<List<ImageGenProviderDTO>> getByProvider(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getByProvider(hours));
    }

    @GetMapping("/feedback")
    public ResponseEntity<ImageFeedbackDTO> getFeedback(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getFeedback(hours));
    }

    @GetMapping("/feedback-trend")
    public ResponseEntity<List<Map<String, Object>>> getFeedbackTrend(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getFeedbackTrend(hours));
    }

    @GetMapping("/distribution")
    public ResponseEntity<List<Map<String, Object>>> getDistribution(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getDistribution(hours));
    }
}
