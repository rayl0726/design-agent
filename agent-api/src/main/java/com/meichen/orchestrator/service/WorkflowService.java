package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.WorkflowLog;
import com.meichen.orchestrator.repository.ProjectRepository;
import com.meichen.orchestrator.repository.WorkflowLogRepository;
import com.meichen.orchestrator.workflow.WorkflowEngine;
import com.meichen.orchestrator.workflow.WorkflowDefinition;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.*;

@Service
public class WorkflowService {

    private static final Logger log = LoggerFactory.getLogger(WorkflowService.class);

    private final ProjectRepository projectRepository;
    private final WorkflowLogRepository logRepository;
    private final WorkflowEngine workflowEngine;
    private final WebClient webClient;
    private final SessionMessageService sessionMessageService;

    public WorkflowService(ProjectRepository projectRepository,
                           WorkflowLogRepository logRepository,
                           WorkflowEngine workflowEngine,
                           WebClient.Builder webClientBuilder,
                           SessionMessageService sessionMessageService,
                           @Value("${agent-core.base-url:http://localhost:8000}") String agentCoreBaseUrl) {
        this.projectRepository = projectRepository;
        this.logRepository = logRepository;
        this.workflowEngine = workflowEngine;
        this.sessionMessageService = sessionMessageService;
        this.webClient = webClientBuilder.baseUrl(agentCoreBaseUrl).build();
    }

    @Transactional
    public Project createProject(String name, String description, Map<String, Object> inputs) {
        Project project = new Project();
        project.setId(UUID.randomUUID().toString());
        project.setName(name);
        project.setDescription(description);
        project.setStatus("INIT");
        project.setRawInputsJson(toJson(inputs));
        return projectRepository.save(project);
    }

    @Transactional
    public void startWorkflow(String projectId, String targetLevel) {
        Project project = projectRepository.findById(projectId)
            .orElseThrow(() -> new IllegalArgumentException("Project not found: " + projectId));

        project.setStatus("PARSING");
        projectRepository.save(project);

        Map<String, Object> payload = parseJson(project.getRawInputsJson());
        payload.put("target_level", targetLevel);
        
        String startNode = WorkflowDefinition.getStartNodeForLevel(targetLevel);
        String stopNode = WorkflowDefinition.getNodeForLevel(targetLevel);
        
        payload.put("start_from", startNode);
        payload.put("stop_at", stopNode);
        
        log.info("Starting workflow for project {}: startFrom={}, stopAt={}, targetLevel={}", 
            projectId, startNode, stopNode, targetLevel);

        // 异步执行工作流
        new Thread(() -> {
            try {
                Map<String, Object> result = workflowEngine.execute(projectId, payload);
                updateProjectStatus(projectId, result, targetLevel);
            } catch (Exception e) {
                log.error("Workflow failed for project {}: {}", projectId, e.getMessage());
                updateProjectFailed(projectId, e.getMessage());
            }
        }).start();
    }

    @Transactional
    public void confirmCheckpoint(String projectId, String level, boolean approved, String feedback) {
        Project project = projectRepository.findById(projectId)
            .orElseThrow(() -> new IllegalArgumentException("Project not found: " + projectId));

        String nextStatus = approved ? level + "_CONFIRMED" : level + "_REJECTED";
        project.setStatus(nextStatus);
        projectRepository.save(project);

        if (approved) {
                Map<String, Object> payload = new HashMap<>();
                payload.put("project_id", projectId);
                payload.put("confirmed_level", level);
                payload.put("feedback", feedback);
                
                Map<String, Object> l1Output = parseJson(project.getL1OutputJson());
                Map<String, Object> l2Output = parseJson(project.getL2OutputJson());
                
                if (l1Output != null && !l1Output.isEmpty()) {
                    payload.put("concept_design", l1Output);
                }
                if (l2Output != null && !l2Output.isEmpty()) {
                    payload.put("visual_design", l2Output);
                }
                
                Map<String, Object> rawInputs = parseJson(project.getRawInputsJson());
                if (rawInputs != null && !rawInputs.isEmpty()) {
                    payload.put("text_parse", rawInputs);
                    payload.put("input_merge", rawInputs);
                }

                String startNode;
                String stopNode;
                String targetLevel;
                
                if ("L2".equals(level)) {
                    startNode = WorkflowDefinition.getStartNodeForLevel("L3");
                    stopNode = WorkflowDefinition.getNodeForLevel("L3");
                    targetLevel = "L3";
                } else {
                    startNode = WorkflowDefinition.getStartNodeForLevel("L2");
                    stopNode = WorkflowDefinition.getNodeForLevel("L2");
                    targetLevel = "L2";
                }
                
                payload.put("start_from", startNode);
                payload.put("stop_at", stopNode);
                
                log.info("Continuing workflow for project {}: startFrom={}, stopAt={}, targetLevel={}", 
                    projectId, startNode, stopNode, targetLevel);

                final String finalTargetLevel = targetLevel;
                new Thread(() -> {
                    try {
                        Map<String, Object> result = workflowEngine.execute(projectId, payload);
                        updateProjectStatus(projectId, result, finalTargetLevel);
                    } catch (Exception e) {
                        log.error("Workflow continuation failed: {}", e.getMessage());
                        updateProjectFailed(projectId, e.getMessage());
                    }
                }).start();
            }
    }

    @Transactional(readOnly = true)
    public Map<String, Object> getStatus(String projectId) {
        Project project = projectRepository.findById(projectId)
            .orElseThrow(() -> new IllegalArgumentException("Project not found: " + projectId));

        List<WorkflowLog> logs = logRepository.findByProjectIdOrderByCreatedAtAsc(projectId);

        Map<String, Object> status = new HashMap<>();
        status.put("project_id", project.getId());
        status.put("name", project.getName());
        status.put("status", project.getStatus());
        status.put("current_level", project.getCurrentLevel());
        status.put("created_at", project.getCreatedAt());
        status.put("updated_at", project.getUpdatedAt());
        status.put("logs", logs.stream().map(this::logToMap).toList());
        status.put("l1_output", parseJson(project.getL1OutputJson()));
        status.put("l2_output", parseJson(project.getL2OutputJson()));
        status.put("l3_output", parseJson(project.getL3OutputJson()));
        return status;
    }

    private void updateProjectStatus(String projectId, Map<String, Object> result, String targetLevel) {
        Project project = projectRepository.findById(projectId).orElse(null);
        if (project == null) return;

        log.info("updateProjectStatus called for project {}, result keys: {}", projectId, result.keySet());

        if (result.containsKey("concept_design")) {
            project.setL1OutputJson(toJson(result.get("concept_design")));
            project.setCurrentLevel("L1");
            project.setStatus("L1_PENDING");
            sessionMessageService.addAssistantMessage(projectId, "idea_gallery", project.getL1OutputJson());
        }
        if (result.containsKey("visual_design")) {
            project.setL2OutputJson(toJson(result.get("visual_design")));
            project.setCurrentLevel("L2");
            project.setStatus("L2_PENDING");
            sessionMessageService.addAssistantMessage(projectId, "visual_scheme", project.getL2OutputJson());
        }
        if (result.containsKey("technical_design")) {
            project.setL3OutputJson(toJson(result.get("technical_design")));
            project.setCurrentLevel("L3");
            project.setStatus("L3_PENDING");
            sessionMessageService.addAssistantMessage(projectId, "proposal", project.getL3OutputJson());
        }
        if (result.containsKey("doc_generate")) {
            project.setStatus("COMPLETED");
            log.info("doc_generate found, generating HTML reports...");
            
            try {
                Map<String, Object> htmlPaths = generateHtmlReport(projectId, project.getName(), project.getDescription(), result);
                log.info("HTML paths generated: {}", htmlPaths);
                project.setL1HtmlPath((String) htmlPaths.get("l1"));
                project.setL2HtmlPath((String) htmlPaths.get("l2"));
                project.setL3HtmlPath((String) htmlPaths.get("l3"));
            } catch (Exception e) {
                log.error("Failed to generate HTML report for project {}: {}", projectId, e.getMessage());
            }
        } else {
            log.warn("doc_generate not found in result, skipping HTML generation");
        }
        projectRepository.save(project);
    }

    private Map<String, Object> generateHtmlReport(String projectId, String projectName, String description, Map<String, Object> workflowResult) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            for (String level : java.util.Arrays.asList("L1", "L2", "L3")) {
                Map<String, Object> payload = new HashMap<>();
                payload.put("project_id", projectId);
                payload.put("project_name", projectName);
                payload.put("description", description);
                payload.put("level", level);
                
                if ("L1".equals(level)) {
                    payload.put("concept_design", workflowResult.get("concept_design"));
                } else if ("L2".equals(level)) {
                    payload.put("concept_design", workflowResult.get("concept_design"));
                    payload.put("visual_design", workflowResult.get("visual_design"));
                } else {
                    payload.put("concept_design", workflowResult.get("concept_design"));
                    payload.put("visual_design", workflowResult.get("visual_design"));
                    payload.put("technical_design", workflowResult.get("technical_design"));
                }
                
                log.info("Sending HTML generation request for level {} with payload size: {}", level, payload.size());
                
                String response = webClient.post()
                    .uri("/agents/doc-generator/generate")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(payload)
                    .retrieve()
                    .bodyToMono(String.class)
                    .timeout(Duration.ofMinutes(5))
                    .block();
                
                log.info("Received response for level {}: {}", level, response);
                
                Map<String, Object> responseBody = new com.fasterxml.jackson.databind.ObjectMapper()
                    .readValue(response, HashMap.class);
                
                String htmlPath = (String) responseBody.get("html");
                log.info("HTML path for level {}: {}", level, htmlPath);
                if (htmlPath != null) {
                    if ("L1".equals(level)) {
                        result.put("l1", htmlPath);
                    } else if ("L2".equals(level)) {
                        result.put("l2", htmlPath);
                    } else {
                        result.put("l3", htmlPath);
                    }
                }
            }
        } catch (Exception e) {
            log.error("HTML generation API call failed: {}", e.getMessage());
            e.printStackTrace();
        }
        
        return result;
    }

    private void updateProjectFailed(String projectId, String error) {
        Project project = projectRepository.findById(projectId).orElse(null);
        if (project == null) return;
        project.setStatus("FAILED");
        projectRepository.save(project);
    }

    private Map<String, Object> logToMap(WorkflowLog log) {
        Map<String, Object> map = new HashMap<>();
        map.put("node_name", log.getNodeName());
        map.put("status", log.getStatus());
        map.put("retry_count", log.getRetryCount());
        map.put("created_at", log.getCreatedAt());
        map.put("error_message", log.getErrorMessage());
        return map;
    }

    private String toJson(Object obj) {
        try {
            return new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(obj);
        } catch (Exception e) {
            return "{}";
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseJson(String json) {
        if (json == null || json.isEmpty()) {
            return new HashMap<>();
        }
        try {
            return new com.fasterxml.jackson.databind.ObjectMapper().readValue(json, HashMap.class);
        } catch (Exception e) {
            return new HashMap<>();
        }
    }
}
