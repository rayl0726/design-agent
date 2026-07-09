package com.meichen.orchestrator.controller;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;
import com.meichen.orchestrator.entity.ThinkingLog;
import com.meichen.orchestrator.repository.ProjectRepository;
import com.meichen.orchestrator.service.SessionMessageService;
import com.meichen.orchestrator.service.DialogueService;
import com.meichen.orchestrator.service.ThinkingLogService;
import com.meichen.orchestrator.service.WorkflowService;
import com.meichen.orchestrator.security.CurrentUser;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.*;

@RestController
@RequestMapping("/api/v1/projects")
public class ProjectController {

    private final WorkflowService workflowService;
    private final ProjectRepository projectRepository;
    private final SessionMessageService sessionMessageService;
    private final ThinkingLogService thinkingLogService;
    private final DialogueService dialogueService;
    private final ObjectMapper objectMapper;

    public ProjectController(WorkflowService workflowService,
                             ProjectRepository projectRepository,
                             SessionMessageService sessionMessageService,
                             ThinkingLogService thinkingLogService,
                             DialogueService dialogueService,
                             ObjectMapper objectMapper) {
        this.workflowService = workflowService;
        this.projectRepository = projectRepository;
        this.sessionMessageService = sessionMessageService;
        this.thinkingLogService = thinkingLogService;
        this.dialogueService = dialogueService;
        this.objectMapper = objectMapper;
    }

    @GetMapping
    public ResponseEntity<List<Project>> listProjects(@CurrentUser Long userId) {
        return ResponseEntity.ok(projectRepository.findByUserIdOrderByCreatedAtDesc(userId));
    }

    @PostMapping(consumes = "multipart/form-data")
    public ResponseEntity<Project> createProject(
        @RequestParam("name") String name,
        @RequestParam(value = "description", required = false) String description,
        @RequestParam(value = "text", required = false) String text,
        @RequestParam(value = "photos", required = false) List<MultipartFile> photos,
        @RequestParam(value = "cad", required = false) MultipartFile cad,
        @RequestParam(value = "pdf", required = false) MultipartFile pdf,
        @RequestParam(value = "ppt", required = false) MultipartFile ppt,
        @RequestParam(value = "references", required = false) List<MultipartFile> references,
        @CurrentUser Long userId
    ) {
        Map<String, Object> inputs = new HashMap<>();
        inputs.put("text", text);
        inputs.put("photo_count", photos != null ? photos.size() : 0);
        inputs.put("cad_present", cad != null);
        inputs.put("pdf_present", pdf != null);
        inputs.put("ppt_present", ppt != null);
        inputs.put("reference_count", references != null ? references.size() : 0);

        Project project = workflowService.createProject(name, description, inputs, userId);
        return ResponseEntity.ok(project);
    }

    @PostMapping(consumes = "application/json")
    public ResponseEntity<Project> createProjectJson(@RequestBody Map<String, Object> body,
                                                     @CurrentUser Long userId) {
        String name = (String) body.get("name");
        if (name == null || name.isEmpty()) {
            name = "未命名项目";
        }

        String description = (String) body.get("description");
        Map<String, Object> inputs = new HashMap<>();

        Object inputsObj = body.get("inputs");
        if (inputsObj instanceof List) {
            List<?> inputList = (List<?>) inputsObj;
            StringBuilder textBuilder = new StringBuilder();
            int photoCount = 0;
            boolean cadPresent = false;
            boolean pdfPresent = false;
            boolean pptPresent = false;
            int referenceCount = 0;

            for (Object item : inputList) {
                if (item instanceof Map) {
                    Map<?, ?> inputMap = (Map<?, ?>) item;
                    String type = (String) inputMap.get("type");
                    String content = (String) inputMap.get("content");

                    if ("text".equals(type) && content != null) {
                        textBuilder.append(content).append("\n");
                    } else if ("image".equals(type)) {
                        photoCount++;
                    } else if ("cad".equals(type)) {
                        cadPresent = true;
                    } else if ("pdf".equals(type)) {
                        pdfPresent = true;
                    } else if ("ppt".equals(type)) {
                        pptPresent = true;
                    } else if ("reference".equals(type)) {
                        referenceCount++;
                    }
                }
            }

            inputs.put("text", textBuilder.toString().trim());
            inputs.put("photo_count", photoCount);
            inputs.put("cad_present", cadPresent);
            inputs.put("pdf_present", pdfPresent);
            inputs.put("ppt_present", pptPresent);
            inputs.put("reference_count", referenceCount);
        } else {
            inputs.put("text", description);
            inputs.put("photo_count", 0);
            inputs.put("cad_present", false);
            inputs.put("pdf_present", false);
            inputs.put("ppt_present", false);
            inputs.put("reference_count", 0);
        }

        Project project = workflowService.createProject(name, description, inputs, userId);
        return ResponseEntity.ok(project);
    }

    @PostMapping("/{id}/workflow/start")
    public ResponseEntity<Map<String, String>> startWorkflow(
        @PathVariable("id") String projectId,
        @RequestParam(value = "level", defaultValue = "L3") String level,
        @CurrentUser Long userId
    ) {
        workflowService.startWorkflow(projectId, level, userId);
        return ResponseEntity.ok(Map.of("status", "started", "project_id", projectId));
    }

    @PostMapping("/{id}/workflow/confirm")
    public ResponseEntity<Map<String, String>> confirmCheckpoint(
        @PathVariable("id") String projectId,
        @RequestBody Map<String, Object> body,
        @CurrentUser Long userId
    ) {
        String level = (String) body.get("level");
        Boolean approved = (Boolean) body.get("approved");
        String feedback = (String) body.get("feedback");
        
        workflowService.confirmCheckpoint(projectId, level, approved != null && approved, feedback, userId);
        String msg = approved != null && approved ? "confirmed" : "rejected";
        return ResponseEntity.ok(Map.of("status", msg, "project_id", projectId));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Project> getProject(@PathVariable("id") String projectId, @CurrentUser Long userId) {
        return projectRepository.findByIdAndUserId(projectId, userId)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Map<String, String>> deleteProject(@PathVariable("id") String projectId,
                                                             @CurrentUser Long userId) {
        workflowService.deleteProject(projectId, userId);
        return ResponseEntity.ok(Map.of("status", "deleted", "project_id", projectId));
    }

    @GetMapping("/{id}/messages")
    public ResponseEntity<List<SessionMessage>> listMessages(@PathVariable("id") String projectId,
                                                             @CurrentUser Long userId) {
        return projectRepository.findByIdAndUserId(projectId, userId)
            .map(p -> ResponseEntity.ok(sessionMessageService.listMessages(projectId, userId)))
            .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/thinking-logs")
    public ResponseEntity<List<ThinkingLog>> listThinkingLogs(@PathVariable("id") String projectId,
                                                              @CurrentUser Long userId) {
        return projectRepository.findByIdAndUserId(projectId, userId)
            .map(p -> ResponseEntity.ok(thinkingLogService.listByProject(projectId)))
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/messages")
    public ResponseEntity<SessionMessage> addMessage(
        @PathVariable("id") String projectId,
        @RequestBody Map<String, Object> body,
        @CurrentUser Long userId
    ) {
        String content = (String) body.get("content");
        if (content == null || content.isBlank()) {
            throw new IllegalArgumentException("content is required");
        }
        Project project = projectRepository.findByIdAndUserId(projectId, userId)
            .orElse(null);
        if (project == null) {
            return ResponseEntity.notFound().build();
        }
        SessionMessage msg = sessionMessageService.addUserMessage(projectId, content, userId);

        Map<String, Object> inputs;
        try {
            inputs = objectMapper.readValue(project.getRawInputsJson(), new TypeReference<Map<String, Object>>() {});
        } catch (Exception e) {
            inputs = new HashMap<>();
        }
        inputs.put("text", content);
        try {
            project.setRawInputsJson(objectMapper.writeValueAsString(inputs));
        } catch (Exception ignored) {}
        projectRepository.save(project);

        String status = project.getStatus();
        if ("INIT".equals(status) || "RECOMMENDATION_PENDING".equals(status)) {
            dialogueService.handleUserMessage(projectId, content, userId);
        } else if ("L1_PENDING".equals(status)) {
            // 旧流程兼容：直接生成视觉方案
            workflowService.startWorkflow(projectId, "L2", userId);
        } else if ("L2_PENDING".equals(status)) {
            // 已展示带图创意，用户选择后进入 L3 技术方案
            workflowService.startWorkflow(projectId, "L3", userId);
        } else if ("L3_PENDING".equals(status)) {
            workflowService.startWorkflow(projectId, "L3", userId);
        }

        return ResponseEntity.ok(msg);
    }

    @GetMapping("/{id}/status")
    public ResponseEntity<Map<String, Object>> getStatus(@PathVariable("id") String projectId,
                                                         @CurrentUser Long userId) {
        return ResponseEntity.ok(workflowService.getStatus(projectId, userId));
    }

    @GetMapping("/{id}/export")
    public ResponseEntity<Map<String, String>> exportDocument(
        @PathVariable("id") String projectId,
        @RequestParam("format") String format,
        @CurrentUser Long userId
    ) {
        return projectRepository.findByIdAndUserId(projectId, userId)
            .map(p -> ResponseEntity.ok(Map.of(
                "project_id", projectId,
                "format", format,
                "url", "/data/uploads/" + projectId + "/L3_方案." + format
            )))
            .orElse(ResponseEntity.notFound().build());
    }
}
