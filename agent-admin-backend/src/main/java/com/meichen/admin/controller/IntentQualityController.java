package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.IntentQualityService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/metrics/intent-quality")
public class IntentQualityController {

    private final IntentQualityService service;

    public IntentQualityController(IntentQualityService service) {
        this.service = service;
    }

    @GetMapping("/sources")
    public ResponseEntity<List<IntentSourceDistributionDTO>> getSources(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(service.getSources(days));
    }

    @GetMapping("/confidence")
    public ResponseEntity<ConfidenceDistributionDTO> getConfidence(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(service.getConfidence(days));
    }

    @GetMapping("/correction-rate")
    public ResponseEntity<List<CorrectionRateDTO>> getCorrectionRate(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(service.getCorrectionRate(days));
    }

    @GetMapping("/dialogue-turns")
    public ResponseEntity<DialogueTurnDTO> getDialogueTurns(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(service.getDialogueTurns(days));
    }

    @GetMapping("/alias-proposals")
    public ResponseEntity<AliasProposalStatsDTO> getAliasProposalStats() {
        return ResponseEntity.ok(service.getAliasProposalStats());
    }
}
