package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;
import com.meichen.orchestrator.entity.WorkflowLog;
import com.meichen.orchestrator.repository.ProjectRepository;
import com.meichen.orchestrator.repository.WorkflowLogRepository;
import com.meichen.orchestrator.workflow.WorkflowEngine;
import com.meichen.orchestrator.workflow.WorkflowDefinition;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Lazy;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.reactive.function.client.WebClient;

import java.nio.file.Path;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.Executor;

@Service
public class WorkflowService {

    private static final Logger log = LoggerFactory.getLogger(WorkflowService.class);

    private final ProjectRepository projectRepository;
    private final WorkflowLogRepository logRepository;
    private final WorkflowEngine workflowEngine;
    private final WebClient webClient;
    private final SessionMessageService sessionMessageService;
    private final SseEmitterService sseEmitterService;
    private final Executor workflowExecutor;

    @Autowired
    @Lazy
    private WorkflowService self;

    public WorkflowService(ProjectRepository projectRepository,
                           WorkflowLogRepository logRepository,
                           WorkflowEngine workflowEngine,
                           WebClient.Builder webClientBuilder,
                           SessionMessageService sessionMessageService,
                           SseEmitterService sseEmitterService,
                           @Qualifier("workflowExecutor") Executor workflowExecutor,
                           @Value("${agent-core.base-url:http://localhost:8000}") String agentCoreBaseUrl) {
        this.projectRepository = projectRepository;
        this.logRepository = logRepository;
        this.workflowEngine = workflowEngine;
        this.sessionMessageService = sessionMessageService;
        this.sseEmitterService = sseEmitterService;
        this.workflowExecutor = workflowExecutor;
        this.webClient = webClientBuilder.baseUrl(agentCoreBaseUrl).build();
    }

    @Transactional
    public Project createProject(String name, String description, Map<String, Object> inputs, Long userId) {
        Project project = new Project();
        project.setId(UUID.randomUUID().toString());
        project.setName(name);
        project.setDescription(description);
        project.setUserId(userId);
        project.setStatus("INIT");
        project.setRawInputsJson(toJson(inputs));
        project = projectRepository.save(project);

        String greeting = "你好！我是你的美陈设计助手。\n"
            + "请告诉我：\n"
            + "• 项目主题（如：夏日海洋、新春国潮）\n"
            + "• 空间类型（购物中心 / 百货 / 快闪店 / 展厅等）\n"
            + "• 预算区间\n"
            + "• 涉及哪些点位？每个点位需要几个？";
        sessionMessageService.addAssistantMessage(project.getId(), "text", greeting, userId);

        return project;
    }

    @Transactional
    public void deleteProject(String projectId) {
        Project project = projectRepository.findById(projectId)
            .orElseThrow(() -> new IllegalArgumentException("Project not found: " + projectId));
        sessionMessageService.addSystemMessage(projectId, "会话已删除", project.getUserId());
        projectRepository.delete(project);
    }

    @Transactional
    public void startWorkflow(String projectId, String targetLevel) {
        Project project = projectRepository.findById(projectId)
            .orElseThrow(() -> new IllegalArgumentException("Project not found: " + projectId));

        project.setStatus("PARSING");
        projectRepository.save(project);
        Map<String, Object> parsingStatus = new HashMap<>();
        parsingStatus.put("project_id", projectId);
        parsingStatus.put("status", "PARSING");
        parsingStatus.put("current_level", project.getCurrentLevel() != null ? project.getCurrentLevel() : "");
        sseEmitterService.sendToProject(projectId, "status", parsingStatus);

        Map<String, Object> payload = parseJson(project.getRawInputsJson());
        payload.put("target_level", targetLevel);

        // 如果有已合并的需求，补充到文本输入中，确保工作流能解析到完整信息
        Map<String, Object> requirement = parseJson(project.getRequirementJson());
        if (requirement != null && !requirement.isEmpty()) {
            String richText = buildRichTextFromRequirement(requirement);
            if (!richText.isEmpty()) {
                payload.put("text", richText);
            }
        }

        String startNode;
        String stopNode = WorkflowDefinition.getNodeForLevel(targetLevel);

        if ("L2".equals(targetLevel)) {
            if (project.getL1OutputJson() == null || project.getL1OutputJson().isBlank()) {
                startNode = "photo_parse";
            } else {
                startNode = "visual_design";
                payload.put("concept_design", parseJson(project.getL1OutputJson()));
            }
        } else if ("L3".equals(targetLevel)) {
            startNode = "technical_design";
            if (project.getL1OutputJson() != null && !project.getL1OutputJson().isBlank()) {
                payload.put("concept_design", parseJson(project.getL1OutputJson()));
            }
            if (project.getL2OutputJson() != null && !project.getL2OutputJson().isBlank()) {
                payload.put("visual_design", parseJson(project.getL2OutputJson()));
            }
            if (project.getRequirementJson() != null && !project.getRequirementJson().isBlank()) {
                payload.put("requirement_analyze", parseJson(project.getRequirementJson()));
            }
        } else {
            startNode = WorkflowDefinition.getStartNodeForLevel(targetLevel);
        }

        payload.put("start_from", startNode);
        payload.put("stop_at", stopNode);
        log.info("Starting workflow for project {}: startFrom={}, stopAt={}, targetLevel={}",
            projectId, startNode, stopNode, targetLevel);

            final String finalStopNode = stopNode;
        workflowExecutor.execute(() -> {
            try {
                Map<String, Object> result = workflowEngine.execute(projectId, payload);
                self.updateProjectStatus(projectId, result, targetLevel, finalStopNode);
            } catch (Exception e) {
                log.error("Workflow failed for project {}: {}", projectId, e.getMessage());
                self.updateProjectFailed(projectId, e.getMessage());
            }
        });
    }

    private String buildRichTextFromRequirement(Map<String, Object> requirement) {
        StringBuilder sb = new StringBuilder();
        appendIfPresent(sb, "主题", requirement.get("theme"));
        appendIfPresent(sb, "空间类型", requirement.get("space_type"));
        appendIfPresent(sb, "预算", requirement.get("budget"));
        appendIfPresent(sb, "风格", requirement.get("style"));
        appendIfPresent(sb, "目标人群", requirement.get("target_audience"));
        appendIfPresent(sb, "工期", requirement.get("timeline"));
        appendIfPresent(sb, "颜色偏好", requirement.get("color_preference"));
        appendIfPresent(sb, "品牌定位", requirement.get("brand_positioning"));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> points = (List<Map<String, Object>>) requirement.get("points");
        if (points != null && !points.isEmpty()) {
            sb.append("涉及点位：");
            for (Map<String, Object> p : points) {
                sb.append(p.get("name"));
                Object count = p.get("count");
                if (count != null) sb.append("×").append(count);
                sb.append("、");
            }
            if (sb.toString().endsWith("、")) {
                sb.setLength(sb.length() - 1);
            }
            sb.append("。\n");
        }

        return sb.toString();
    }

    private void appendIfPresent(StringBuilder sb, String label, Object value) {
        if (value != null && !(value instanceof String s && s.isEmpty())) {
            sb.append(label).append("：").append(value).append("。\n");
        }
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
                final String finalStopNode = stopNode;
                workflowExecutor.execute(() -> {
                    try {
                        Map<String, Object> result = workflowEngine.execute(projectId, payload);
                        self.updateProjectStatus(projectId, result, finalTargetLevel, finalStopNode);
                    } catch (Exception e) {
                        log.error("Workflow continuation failed: {}", e.getMessage());
                        self.updateProjectFailed(projectId, e.getMessage());
                    }
                });
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

    @Transactional
    public void updateProjectStatus(String projectId, Map<String, Object> result, String targetLevel, String stopNode) {
        try {
            Project project = projectRepository.findById(projectId).orElse(null);
            if (project == null) return;

            log.info("updateProjectStatus called for project {}, result keys: {}", projectId, result.keySet());

            // 仅处理本次工作流实际执行到的节点输出，避免把 initial_payload 中带入的历史输出重复推送
            String effectiveStop = stopNode != null ? stopNode : WorkflowDefinition.getNodeForLevel(targetLevel);

            if ("concept_design".equals(effectiveStop) && result.containsKey("concept_design")) {
            Map<String, Object> conceptDesign = (Map<String, Object>) result.get("concept_design");
            project.setL1OutputJson(toJson(conceptDesign));
            project.setCurrentLevel("L1");
            project.setStatus("L1_PENDING");
            Object ideas = conceptDesign.get("ideas");
            pushMessage(projectId, sessionMessageService.addAssistantMessage(projectId, "idea_gallery", toJson(ideas != null ? ideas : conceptDesign), project.getUserId()));
            pushMessage(projectId, sessionMessageService.addAssistantMessage(projectId, "text",
                "已为你生成 3 个创意方向。请直接回复选择第几个（如“选第3个”），我将基于该创意继续生成效果图。", project.getUserId()));
        }
        if ("visual_design".equals(effectiveStop) && result.containsKey("visual_design")) {
            Map<String, Object> visualDesign = (Map<String, Object>) result.get("visual_design");
            project.setL2OutputJson(toJson(visualDesign));
            project.setCurrentLevel("L2");
            project.setStatus("L2_PENDING");

            Object ideas = visualDesign.get("ideas");
            if (ideas instanceof List) {
                List<Map<String, Object>> ideasWithUrls = convertImagePathsToUrls((List<Map<String, Object>>) ideas);
                pushMessage(projectId, sessionMessageService.addAssistantMessage(projectId, "idea_gallery", toJson(ideasWithUrls), project.getUserId()));
                pushMessage(projectId, sessionMessageService.addAssistantMessage(projectId, "text",
                    "已为你生成 3 个创意方向及效果图。请直接回复选择第几个（如“选第3个”），我将基于该创意继续深化方案。", project.getUserId()));
            } else {
                pushMessage(projectId, sessionMessageService.addAssistantMessage(projectId, "visual_scheme", project.getL2OutputJson(), project.getUserId()));
            }
        }
        if ("technical_design".equals(effectiveStop) && result.containsKey("technical_design")) {
            project.setL3OutputJson(toJson(result.get("technical_design")));
            project.setCurrentLevel("L3");
            project.setStatus("L3_PENDING");
            pushMessage(projectId, sessionMessageService.addAssistantMessage(projectId, "proposal", project.getL3OutputJson(), project.getUserId()));
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
        Map<String, Object> finalStatus = new HashMap<>();
        finalStatus.put("project_id", projectId);
        finalStatus.put("status", project.getStatus());
        finalStatus.put("current_level", project.getCurrentLevel() != null ? project.getCurrentLevel() : "");
        sseEmitterService.sendToProject(projectId, "status", finalStatus);
        } catch (Exception e) {
            log.error("updateProjectStatus failed for project {}: {}", projectId, e.getMessage(), e);
            updateProjectFailed(projectId, e.getMessage() != null ? e.getMessage() : "保存结果失败");
        }
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

    @Transactional
    public void updateProjectFailed(String projectId, String error) {
        Project project = projectRepository.findById(projectId).orElse(null);
        if (project == null) return;
        project.setStatus("FAILED");
        projectRepository.save(project);
        Map<String, Object> failedStatus = new HashMap<>();
        failedStatus.put("project_id", projectId);
        failedStatus.put("status", "FAILED");
        failedStatus.put("current_level", project.getCurrentLevel() != null ? project.getCurrentLevel() : "");
        sseEmitterService.sendToProject(projectId, "status", failedStatus);
        Map<String, Object> errorEvent = new HashMap<>();
        errorEvent.put("project_id", projectId);
        errorEvent.put("message", error != null ? error : "工作流执行失败");
        sseEmitterService.sendToProject(projectId, "error", errorEvent);
    }

    private void pushMessage(String projectId, SessionMessage msg) {
        if (msg == null) {
            log.warn("pushMessage called with null message for project {}", projectId);
            return;
        }
        Map<String, Object> event = new HashMap<>();
        event.put("id", msg.getId() != null ? msg.getId() : "");
        event.put("role", msg.getRole() != null ? msg.getRole() : "");
        event.put("message_type", msg.getMessageType() != null ? msg.getMessageType() : "");
        event.put("content", msg.getContent() != null ? msg.getContent() : "");
        event.put("created_at", msg.getCreatedAt() != null ? msg.getCreatedAt() : "");
        sseEmitterService.sendToProject(projectId, "message", event);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> convertImagePathsToUrls(List<Map<String, Object>> ideas) {
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> idea : ideas) {
            Map<String, Object> copy = new HashMap<>(idea);
            // 处理单张封面图
            Object imageUrl = copy.get("image_url");
            if (imageUrl instanceof String path && !path.isEmpty()) {
                Path p = Path.of(path);
                copy.put("image_url", "/images/" + p.getFileName().toString());
            }
            // 处理多张图数组（兼容旧结构）
            Object imageUrls = copy.get("image_urls");
            if (imageUrls instanceof List) {
                List<String> urls = new ArrayList<>();
                for (Object item : (List<?>) imageUrls) {
                    if (item instanceof String path && !path.isEmpty()) {
                        Path p = Path.of(path);
                        urls.add("/images/" + p.getFileName().toString());
                    } else {
                        urls.add("");
                    }
                }
                copy.put("image_urls", urls);
            }
            // 处理点位图片（新结构）
            Object pointsObj = copy.get("points");
            if (pointsObj instanceof List) {
                List<Map<String, Object>> points = new ArrayList<>();
                for (Object pointObj : (List<?>) pointsObj) {
                    if (pointObj instanceof Map) {
                        Map<String, Object> point = new HashMap<>();
                        for (Object keyObj : ((Map<?, ?>) pointObj).keySet()) {
                            String key = String.valueOf(keyObj);
                            point.put(key, ((Map<?, ?>) pointObj).get(keyObj));
                        }
                        Object pointImageUrls = point.get("image_urls");
                        if (pointImageUrls instanceof List) {
                            List<String> urls = new ArrayList<>();
                            for (Object item : (List<?>) pointImageUrls) {
                                if (item instanceof String path && !path.isEmpty()) {
                                    Path p = Path.of(path);
                                    urls.add("/images/" + p.getFileName().toString());
                                } else {
                                    urls.add("");
                                }
                            }
                            point.put("image_urls", urls);
                        }
                        points.add(point);
                    }
                }
                copy.put("points", points);
            }
            result.add(copy);
        }
        return result;
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
