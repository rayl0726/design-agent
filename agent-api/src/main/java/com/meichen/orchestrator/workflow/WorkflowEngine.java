package com.meichen.orchestrator.workflow;

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

    public WorkflowEngine(WorkflowLogRepository logRepository,
                          com.meichen.orchestrator.service.ThinkingLogService thinkingLogService,
                          com.meichen.orchestrator.service.SseEmitterService sseEmitterService,
                          @Value("${agent-core.base-url:http://localhost:8000}") String agentCoreBaseUrl) {
        this.restTemplate = new RestTemplate();
        this.agentCoreBaseUrl = agentCoreBaseUrl.endsWith("/") ? agentCoreBaseUrl.substring(0, agentCoreBaseUrl.length() - 1) : agentCoreBaseUrl;
        this.logRepository = logRepository;
        this.thinkingLogService = thinkingLogService;
        this.sseEmitterService = sseEmitterService;
    }

    public Map<String, Object> execute(String projectId, Map<String, Object> initialPayload) {
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
        log.info("startFromNode: {}, stopAtNode: {}", startFromNode, stopAtNode);
        
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
                log.info("Skipping node {} as it's beyond stop_at node {}", nodeName, stopAtNode);
                continue;
            }

            WorkflowNode node = nodeMap.get(nodeName);
            try {
                Object result = runNode(projectId, node, outputs);
                outputs.put(nodeName, result);
            } catch (Exception e) {
                outputs.put(nodeName, Map.of("error", e.getMessage()));
                log.error("Node {} failed: {}", nodeName, e.getMessage());
            }

            if (stopAtNode != null && stopAtNode.equals(nodeName)) {
                log.info("Stopping workflow at node: {}", stopAtNode);
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

    private Object runNode(String projectId, WorkflowNode node, Map<String, Object> outputs) {
        log.info("runNode called for node: {}, project: {}", node.name(), projectId);
        boolean logThinking = thinkingLogService.shouldLog(node.name());
        if (logThinking) {
            thinkingLogService.logStarted(projectId, node.name());
            sseEmitterService.sendToProject(projectId, "thinking", Map.of(
                "node_name", node.name(),
                "status", "started",
                "message", getNodeMessage(node.name())
            ));
        }

        // Build payload based on node contract
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
            // visual_design 需要 concept_design 输出和 requirement_analyze
            payload = new HashMap<>();
            payload.put("concept_design", outputs.get(deps.get(0)));
            payload.put("requirement_analyze", outputs.get("requirement_analyze"));
        } else if ("technical_design".equals(node.name())) {
            // Multi-dependency nodes expect {"dep_name": output, ...}
            payload = new HashMap<>();
            for (String dep : deps) {
                payload.put(dep, outputs.get(dep));
            }
        } else if (deps.size() == 1) {
            // Single-dependency nodes expect the dependency output directly
            payload = new HashMap<>();
            Object depOutput = outputs.get(deps.get(0));
            if (depOutput instanceof Map) {
                payload.putAll((Map<String, Object>) depOutput);
            }
        } else {
            // Multi-dependency nodes expect {"dep_name": output, ...}
            payload = new HashMap<>();
            for (String dep : deps) {
                payload.put(dep, outputs.get(dep));
            }
        }

        log.info("Sending request to endpoint: {} with payload size: {}", node.endpoint(), payload.size());

        int retries = 0;
        Exception lastError = null;

        while (retries < MAX_RETRIES) {
            try {
                String url = agentCoreBaseUrl + node.endpoint();
                log.info("Calling endpoint {} for node {}", url, node.name());

                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_JSON);
                HttpEntity<Map<String, Object>> request = new HttpEntity<>(payload, headers);

                ResponseEntity<String> response = restTemplate.postForEntity(url, request, String.class);
                String body = response.getBody();
                log.info("Received response for node {} (status={}, length={})", node.name(), response.getStatusCode(), body != null ? body.length() : 0);

                // Log success
                WorkflowLog successLog = new WorkflowLog();
                successLog.setProjectId(projectId);
                successLog.setNodeName(node.name());
                successLog.setStatus("success");
                successLog.setOutputJson(body);
                successLog.setRetryCount(retries);
                logRepository.save(successLog);
                if (logThinking) {
                    thinkingLogService.logCompleted(projectId, node.name());
                    sseEmitterService.sendToProject(projectId, "thinking", Map.of(
                        "node_name", node.name(),
                        "status", "completed",
                        "message", getNodeMessage(node.name())
                    ));
                }

                return parseJson(body);
            } catch (Exception e) {
                lastError = e;
                retries++;
                log.warn("Node {} attempt {} failed: {}", node.name(), retries, e.getMessage());
                try {
                    Thread.sleep(1000L * retries);
                } catch (InterruptedException ignored) {}
            }
        }

        // Log failure
        WorkflowLog failLog = new WorkflowLog();
        failLog.setProjectId(projectId);
        failLog.setNodeName(node.name());
        failLog.setStatus("failed");
        String errorMsg = lastError != null ? lastError.getMessage() : "Unknown error";
        failLog.setErrorMessage(errorMsg);
        failLog.setRetryCount(retries);
        logRepository.save(failLog);
        if (logThinking) {
            thinkingLogService.logFailed(projectId, node.name(), errorMsg);
            sseEmitterService.sendToProject(projectId, "thinking", Map.of(
                "node_name", node.name(),
                "status", "failed",
                "message", getNodeMessage(node.name()) + " 失败: " + errorMsg
            ));
        }

        throw new RuntimeException("Node " + node.name() + " failed after " + MAX_RETRIES + " retries", lastError);
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
}
