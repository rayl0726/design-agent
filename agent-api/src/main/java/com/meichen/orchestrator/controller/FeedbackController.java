package com.meichen.orchestrator.controller;

import com.meichen.orchestrator.entity.Feedback;
import com.meichen.orchestrator.security.CurrentUser;
import com.meichen.orchestrator.service.FeedbackService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/projects/{projectId}/feedbacks")
public class FeedbackController {

    private final FeedbackService feedbackService;

    public FeedbackController(FeedbackService feedbackService) {
        this.feedbackService = feedbackService;
    }

    @PostMapping
    public ResponseEntity<Feedback> createFeedback(
        @PathVariable("projectId") String projectId,
        @RequestBody Map<String, Object> body,
        @CurrentUser Long userId
    ) {
        return ResponseEntity.ok(feedbackService.saveFeedback(projectId, body, userId));
    }

    @GetMapping
    public ResponseEntity<List<Feedback>> listFeedbacks(
        @PathVariable("projectId") String projectId,
        @CurrentUser Long userId
    ) {
        return ResponseEntity.ok(feedbackService.listByProject(projectId, userId));
    }
}
