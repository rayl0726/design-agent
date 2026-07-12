package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.BusinessFunnelService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/metrics")
public class BusinessFunnelController {

    private final BusinessFunnelService service;

    public BusinessFunnelController(BusinessFunnelService service) {
        this.service = service;
    }

    @GetMapping("/funnel")
    public ResponseEntity<ProjectFunnelDTO> getFunnel(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(service.getFunnel(days));
    }

    @GetMapping("/funnel/abandonment")
    public ResponseEntity<List<ProjectAbandonmentDTO>> getAbandonment(
            @RequestParam(defaultValue = "7") int days) {
        return ResponseEntity.ok(service.getAbandonment(days));
    }

    @GetMapping("/funnel/levels")
    public ResponseEntity<List<LevelDistributionDTO>> getLevels() {
        return ResponseEntity.ok(service.getLevelDistribution());
    }

    @GetMapping("/funnel/duration")
    public ResponseEntity<ProjectDurationDTO> getDuration(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(service.getDuration(days));
    }

    @GetMapping("/conversations")
    public ResponseEntity<ConversationStatsDTO> getConversations(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(service.getConversationStats(days));
    }
}
