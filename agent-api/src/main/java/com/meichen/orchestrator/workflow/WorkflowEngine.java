package com.meichen.orchestrator.workflow;

import com.meichen.orchestrator.entity.StageLog;
import com.meichen.orchestrator.entity.WorkflowLog;
import com.meichen.orchestrator.repository.WorkflowLogRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Collectors;

@Component
public class WorkflowEngine {

    private static final Logger log = LoggerFactory.getLogger(WorkflowEngine.class);
    private static final int MAX_RETRIES = 3;

    private final RestTemplate restTemplate;
    private final String agentCoreBaseUrl;
    private final WorkflowLogRepository logRepository;
    private final com.meichen.orchestrator.service.ThinkingLogService thinkingLogService;
    private final com.meichen.orchestrator.service.SseEmitterService sseEmitterService;
    private final com.meichen.orchestrator.service.StageLogService stageLogService;
    private static final String SUBSTAGE_AGENT_CORE_CALL = "agent_core_call";
    private static final String SUBSTAGE_RESULT_PARSE = "result_parse";

    private static final Map<String, String> NODE_LABELS = Map.ofEntries(
        Map.entry("text_parse", "解析文本输入"),
        Map.entry("photo_parse", "解析照片输入"),
        Map.entry("pdf_parse", "解析 PDF 输入"),
        Map.entry("ppt_parse", "解析 PPT 输入"),
        Map.entry("reference_parse", "解析参考图"),
        Map.entry("cad_parse", "解析 CAD 输入"),
        Map.entry("input_merge", "合并多模态输入"),
        Map.entry("knowledge_retrieve", "检索设计知识库"),
        Map.entry("requirement_analyze", "分析设计需求"),
        Map.entry("concept_design", "生成创意方向"),
        Map.entry("visual_design", "生成视觉方案"),
        Map.entry("technical_design", "生成落地方案"),
        Map.entry("doc_generate", "生成最终文档")
    );

    public WorkflowEngine(WorkflowLogRepository logRepository,
                          com.meichen.orchestrator.service.ThinkingLogService thinkingLogService,
                          com.meichen.orchestrator.service.SseEmitterService sseEmitterService,
                          com.meichen.orchestrator.service.StageLogService stageLogService,
                          RestTemplate restTemplate,
                          @Value("${agent-core.base-url:http://localhost:8000}") String agentCoreBaseUrl) {
        this.restTemplate = restTemplate;
        this.agentCoreBaseUrl = agentCoreBaseUrl.endsWith("/") ? agentCoreBaseUrl.substring(0, agentCoreBaseUrl.length() - 1) : agentCoreBaseUrl;
        this.logRepository = logRepository;
        this.thinkingLogService = thinkingLogService;
        this.sseEmitterService = sseEmitterService;
        this.stageLogService = stageLogService;
    }

    public Map<String, Object> execute(String projectId, Map<String, Object> initialPayload, Long userId) {
        String startFromNode = (String) initialPayload.get("start_from");
        
        List<WorkflowNode> nodes = WorkflowDefinition.getNodes();
        Map<String, Set<String>> adj = new HashMap<>();
        Map<String, Integer> inDegree = new HashMap<>();
        Map<String, WorkflowNode> nodeMap = new HashMap<>();

        for (WorkflowNode node : nodes) {
            nodeMap.put(node.name(), node);
            inDegree.put(node.name(), node.dependencies().size());
            adj.computeIfAbsent(node.name(), k -> new HashSet<>());
            for (String dep : node.dependencies()) {
                adj.computeIfAbsent(dep, k -> new HashSet<>()).add(node.name());
            }
        }

        Map<String, Object> outputs = new ConcurrentHashMap<>();
        outputs.put("project_id", projectId);
        outputs.put("initial_payload", initialPayload);

        String stopAtNode = (String) initialPayload.get("stop_at");
        log.debug("startFromNode: {}, stopAtNode: {}", startFromNode, stopAtNode);
        
        Set<String> completedNodes = new HashSet<>();
        
        if (startFromNode != null && !startFromNode.isEmpty()) {
            for (WorkflowNode node : nodes) {
                if (isDependencyOf(node.name(), startFromNode, nodes)) {
                    completedNodes.add(node.name());
                    Object savedOutput = initialPayload.get(node.name());
                    if (savedOutput != null) {
                        outputs.put(node.name(), savedOutput);
                    }
                }
            }
            
            for (String completed : completedNodes) {
                for (String next : adj.getOrDefault(completed, Set.of())) {
                    inDegree.put(next, inDegree.get(next) - 1);
                }
            }
            
            if (inDegree.get(startFromNode) == 0) {
                Object savedOutput = initialPayload.get(startFromNode);
                if (savedOutput != null) {
                    outputs.put(startFromNode, savedOutput);
                }
            }
        }

        Queue<String> queue = new ConcurrentLinkedQueue<>();
        for (String name : inDegree.keySet()) {
            if (inDegree.get(name) == 0 && !completedNodes.contains(name)) {
                queue.add(name);
            }
        }

        while (!queue.isEmpty()) {
            String nodeName = queue.poll();

            if (stopAtNode != null && !stopAtNode.isEmpty() && isDependencyOf(stopAtNode, nodeName, nodes)) {
                log.debug("Skipping node {} as it's beyond stop_at node {}", nodeName, stopAtNode);
                continue;
            }

            WorkflowNode node = nodeMap.get(nodeName);
            try {
                Object result = runNode(projectId, node, outputs, userId);
                outputs.put(nodeName, result);
            } catch (Exception e) {
                outputs.put(nodeName, Map.of("error", e.getMessage()));
                log.error("Node {} failed: {}", nodeName, e.getMessage());
            }

            if (stopAtNode != null && stopAtNode.equals(nodeName)) {
                log.debug("Stopping workflow at node: {}", stopAtNode);
                break;
            }

            for (String next : adj.getOrDefault(nodeName, Set.of())) {
                inDegree.put(next, inDegree.get(next) - 1);
                if (inDegree.get(next) == 0) {
                    queue.add(next);
                }
            }
        }

        return outputs;
    }

    Object runNode(String projectId, WorkflowNode node, Map<String, Object> outputs, Long userId) {
        log.debug("runNode called for node: {}, project: {}", node.name(), projectId);
        String stageLabel = NODE_LABELS.getOrDefault(node.name(), node.name());
        StageLog stageLog = stageLogService.startStage(projectId, node.name(), stageLabel, userId);

        boolean logThinking = thinkingLogService.shouldLog(node.name());
        if (logThinking) {
            thinkingLogService.logStarted(projectId, node.name(), userId);
            sseEmitterService.sendToProject(projectId, "thinking", Map.of(
                "node_name", node.name(),
                "status", "started",
                "message", getNodeMessage(node.name())
            ));
        }

        Map<String, Object> payload = buildPayload(node, outputs);
        log.debug("Sending request to endpoint: {} with payload size: {}", node.endpoint(), payload.size());

        StageLog networkSub = stageLogService.startSubStage(stageLog.getId(), SUBSTAGE_AGENT_CORE_CALL, "调用Agent-Core", userId);
        int retries = 0;
        Exception lastError = null;
        String body = null;

        while (retries < MAX_RETRIES) {
            try {
                String url = agentCoreBaseUrl + node.endpoint();
                log.debug("Calling endpoint {} for node {}", url, node.name());

                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_JSON);
                HttpEntity<Map<String, Object>> request = new HttpEntity<>(payload, headers);

                ResponseEntity<String> response = restTemplate.postForEntity(url, request, String.class);
                body = response.getBody();
                log.debug("Received response for node {} (status={}, length={})", node.name(), response.getStatusCode(), body != null ? body.length() : 0);
                break;
            } catch (Exception e) {
                lastError = e;
                retries++;
                log.warn("Node {} attempt {} failed: {}", node.name(), retries, e.getMessage());
                try {
                    Thread.sleep(1000L * retries);
                } catch (InterruptedException ignored) {}
            }
        }

        if (body == null) {
            String errorMsg = lastError != null ? lastError.getMessage() : "Unknown error";
            stageLogService.failStage(networkSub.getId(), errorMsg);
            return failNode(projectId, node, stageLog, errorMsg, retries, logThinking, userId, lastError);
        }
        stageLogService.completeSubStage(networkSub.getId());

        StageLog parseSub = stageLogService.startSubStage(stageLog.getId(), SUBSTAGE_RESULT_PARSE, "解析结果", userId);
        Object result;
        Map<String, Object> metadata;
        try {
            result = parseJson(body);
            metadata = buildStageMetadata(node.name(), result);
        } catch (Exception e) {
            stageLogService.failStage(parseSub.getId(), e.getMessage());
            return failNode(projectId, node, stageLog, e.getMessage(), retries, logThinking, userId, e);
        }
        stageLogService.completeSubStage(parseSub.getId());

        WorkflowLog successLog = new WorkflowLog();
        successLog.setProjectId(projectId);
        successLog.setNodeName(node.name());
        successLog.setStatus("success");
        successLog.setOutputJson(body);
        successLog.setRetryCount(retries);
        logRepository.save(successLog);
        if (logThinking) {
            thinkingLogService.logCompleted(projectId, node.name(), userId);
            sseEmitterService.sendToProject(projectId, "thinking", Map.of(
                "node_name", node.name(),
                "status", "completed",
                "message", getNodeMessage(node.name())
            ));
        }

        stageLogService.completeStage(stageLog.getId(), metadata);
        return result;
    }

    private Map<String, Object> buildPayload(WorkflowNode node, Map<String, Object> outputs) {
        Map<String, Object> payload;
        List<String> deps = node.dependencies();

        if ("text_parse".equals(node.name())) {
            payload = new HashMap<>();
            Map<String, Object> initialPayload = (Map<String, Object>) outputs.get("initial_payload");
            if (initialPayload != null) {
                Object textObj = initialPayload.get("text");
                if (textObj != null) {
                    payload.put("text", textObj);
                }
            }
        } else if ("input_merge".equals(node.name())) {
            List<Object> parsedResults = deps.stream()
                .map(outputs::get)
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
            payload = Map.of("parsed_results", parsedResults);
        } else if ("visual_design".equals(node.name()) && deps.size() == 1) {
            payload = new HashMap<>();
            payload.put("concept_design", outputs.get(deps.get(0)));
            payload.put("requirement_analyze", outputs.get("requirement_analyze"));
        } else if ("technical_design".equals(node.name())) {
            payload = new HashMap<>();
            for (String dep : deps) {
                payload.put(dep, outputs.get(dep));
            }
        } else if (deps.size() == 1) {
            payload = new HashMap<>();
            Object depOutput = outputs.get(deps.get(0));
            if (depOutput instanceof Map) {
                payload.putAll((Map<String, Object>) depOutput);
            }
        } else {
            payload = new HashMap<>();
            for (String dep : deps) {
                payload.put(dep, outputs.get(dep));
            }
        }
        return payload;
    }

    private Object failNode(String projectId, WorkflowNode node, StageLog stageLog, String errorMsg,
                            int retries, boolean logThinking, Long userId, Exception lastError) {
        WorkflowLog failLog = new WorkflowLog();
        failLog.setProjectId(projectId);
        failLog.setNodeName(node.name());
        failLog.setStatus("failed");
        failLog.setErrorMessage(errorMsg);
        failLog.setRetryCount(retries);
        logRepository.save(failLog);
        if (logThinking) {
            thinkingLogService.logFailed(projectId, node.name(), errorMsg, userId);
            sseEmitterService.sendToProject(projectId, "thinking", Map.of(
                "node_name", node.name(),
                "status", "failed",
                "message", getNodeMessage(node.name()) + " 失败: " + errorMsg
            ));
        }

        stageLogService.failStage(stageLog.getId(), errorMsg);
        throw new RuntimeException("Node " + node.name() + " failed after " + (retries > 0 ? retries : MAX_RETRIES) + " retries", lastError);
    }

    private boolean isDependencyOf(String candidate, String target, List<WorkflowNode> nodes) {
        if (candidate.equals(target)) return false;
        
        Map<String, WorkflowNode> nodeMap = nodes.stream()
            .collect(Collectors.toMap(WorkflowNode::name, n -> n));
        
        Set<String> visited = new HashSet<>();
        Queue<String> queue = new LinkedList<>();
        queue.add(target);
        
        while (!queue.isEmpty()) {
            String current = queue.poll();
            WorkflowNode node = nodeMap.get(current);
            if (node == null) continue;
            
            for (String dep : node.dependencies()) {
                if (dep.equals(candidate)) return true;
                if (!visited.contains(dep)) {
                    visited.add(dep);
                    queue.add(dep);
                }
            }
        }
        
        return false;
    }

    private String getNodeMessage(String nodeName) {
        return Map.of(
            "text_parse", "解析用户输入",
            "input_merge", "合并多模态输入",
            "requirement_analyze", "分析设计需求",
            "knowledge_retrieve", "检索设计知识库",
            "concept_design", "生成创意方向",
            "visual_design", "生成视觉方案",
            "technical_design", "生成落地方案",
            "doc_generate", "生成方案文档"
        ).getOrDefault(nodeName, "执行 " + nodeName);
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
        try {
            if (json == null || json.isBlank()) return new HashMap<>();
            return new com.fasterxml.jackson.databind.ObjectMapper().readValue(json, Map.class);
        } catch (Exception e) {
            log.warn("Failed to parse JSON: {}", e.getMessage());
            return new HashMap<>();
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> buildStageMetadata(String nodeName, Object result) {
        Map<String, Object> metadata = new HashMap<>();
        if (!(result instanceof Map)) {
            return metadata;
        }
        Map<String, Object> resultMap = (Map<String, Object>) result;

        if ("visual_design".equals(nodeName)) {
            List<Map<String, Object>> ideas = (List<Map<String, Object>>) resultMap.get("ideas");
            if (ideas != null) {
                int totalImages = 0;
                int successImages = 0;
                int failedImages = 0;
                for (Map<String, Object> idea : ideas) {
                    List<Map<String, Object>> points = (List<Map<String, Object>>) idea.get("points");
                    if (points != null) {
                        for (Map<String, Object> point : points) {
                            List<String> urls = (List<String>) point.get("image_urls");
                            if (urls != null) {
                                totalImages += urls.size();
                                for (String url : urls) {
                                    if (url != null && !url.isBlank()) {
                                        successImages++;
                                    } else {
                                        failedImages++;
                                    }
                                }
                            }
                        }
                    }
                    List<String> ideaUrls = (List<String>) idea.get("image_urls");
                    if (ideaUrls != null) {
                        totalImages += ideaUrls.size();
                        for (String url : ideaUrls) {
                            if (url != null && !url.isBlank()) {
                                successImages++;
                            } else {
                                failedImages++;
                            }
                        }
                    }
                }
                metadata.put("total_images", totalImages);
                metadata.put("success_images", successImages);
                metadata.put("failed_images", failedImages);
            }
        } else if ("concept_design".equals(nodeName)) {
            List<Map<String, Object>> ideas = (List<Map<String, Object>>) resultMap.get("ideas");
            if (ideas != null) {
                metadata.put("idea_count", ideas.size());
            }
        }
        return metadata;
    }
}
