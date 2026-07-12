package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.PromptTemplateAdminService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/prompt-templates")
public class PromptTemplateAdminController {

    private final PromptTemplateAdminService service;

    public PromptTemplateAdminController(PromptTemplateAdminService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<List<PromptTemplateInfoDTO>> listTemplates() {
        return ResponseEntity.ok(service.listTemplates());
    }

    @GetMapping("/{name}/performance")
    public ResponseEntity<List<PromptTemplatePerformanceDTO>> getPerformance(
            @PathVariable String name) {
        return ResponseEntity.ok(service.getPerformance(name));
    }

    @PostMapping("/preview")
    public ResponseEntity<PromptPreviewResponseDTO> previewPrompt(
            @RequestBody PromptPreviewRequestDTO request) {
        return ResponseEntity.ok(service.previewPrompt(request));
    }
}
