package com.meichen.admin.controller;

import com.meichen.admin.dto.FeedbackDTO;
import com.meichen.admin.dto.ProcessFeedbackRequestDTO;
import com.meichen.admin.service.FeedbackAdminService;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin/feedbacks")
public class FeedbackAdminController {

    private final FeedbackAdminService service;

    public FeedbackAdminController(FeedbackAdminService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<Page<FeedbackDTO>> listFeedbacks(
            @RequestParam(required = false) String feedbackType,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) Boolean processed,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<FeedbackDTO> result = service.listFeedbacks(feedbackType, category, processed, PageRequest.of(page, size));
        return ResponseEntity.ok(result);
    }

    @PostMapping("/{id}/process")
    public ResponseEntity<FeedbackDTO> processFeedback(
            @PathVariable String id,
            @RequestBody(required = false) ProcessFeedbackRequestDTO request) {
        return ResponseEntity.ok(service.processFeedback(id, request));
    }
}
