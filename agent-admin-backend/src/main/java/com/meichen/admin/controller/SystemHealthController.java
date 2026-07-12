package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.SystemHealthService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/metrics/system")
public class SystemHealthController {

    private final SystemHealthService service;

    public SystemHealthController(SystemHealthService service) {
        this.service = service;
    }

    @GetMapping("/workflow-success")
    public ResponseEntity<List<WorkflowSuccessDTO>> getWorkflowSuccess(
            @RequestParam(defaultValue = "7") int days) {
        return ResponseEntity.ok(service.getWorkflowSuccess(days));
    }

    @GetMapping("/retries")
    public ResponseEntity<List<RetryDistributionDTO>> getRetries(
            @RequestParam(defaultValue = "7") int days) {
        return ResponseEntity.ok(service.getRetries(days));
    }

    @GetMapping("/errors")
    public ResponseEntity<List<ErrorDistributionDTO>> getErrors(
            @RequestParam(defaultValue = "7") int days) {
        return ResponseEntity.ok(service.getErrors(days));
    }

    @GetMapping("/anomalies")
    public ResponseEntity<AnomalyStatsDTO> getAnomalies(
            @RequestParam(defaultValue = "7") int days) {
        return ResponseEntity.ok(service.getAnomalies(days));
    }

    @GetMapping("/http")
    public ResponseEntity<HttpMetricsDTO> getHttp(
            @RequestParam(defaultValue = "1") int hours) {
        return ResponseEntity.ok(service.getHttpMetrics(hours));
    }

    @GetMapping("/thread-pools")
    public ResponseEntity<List<ThreadPoolMetricsDTO>> getThreadPools() {
        return ResponseEntity.ok(service.getThreadPools());
    }

    @GetMapping("/db-pool")
    public ResponseEntity<DbPoolMetricsDTO> getDbPool() {
        return ResponseEntity.ok(service.getDbPool());
    }
}
