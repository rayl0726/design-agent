package com.meichen.orchestrator.workflow;

import com.meichen.orchestrator.entity.WorkflowLog;
import com.meichen.orchestrator.repository.WorkflowLogRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
import reactor.netty.http.client.HttpClient;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Collectors;

@Component
public class WorkflowEngine {

    private static final Logger log = LoggerFactory.getLogger(WorkflowEngine.class);
    private static final int MAX_RETRIES = 3;

    private final WebClient webClient;
    private final WorkflowLogRepository logRepository;
    private final ExecutorService executor;
    private final com.meichen.orchestrator.service.ThinkingLogService thinkingLogService;

    public WorkflowEngine(WebClient.Builder webClientBuilder, 
                          WorkflowLogRepository logRepository,
                          com.meichen.orchestrator.service.ThinkingLogService thinkingLogService,
                          @Value("${agent-core.base-url:http://localhost:8000}") String agentCoreBaseUrl) {
        HttpClient httpClient = HttpClient.create()
            .option(io.netty.channel.ChannelOption.CONNECT_TIMEOUT_MILLIS, 10000)
            .responseTimeout(Duration.ofMinutes(10));
        
        this.webClient = webClientBuilder
            .baseUrl(agentCoreBaseUrl)
            .clientConnector(new ReactorClientHttpConnector(httpClient))
            .build();
        this.logRepository = logRepository;
        this.thinkingLogService = thinkingLogService;
        this.executor = Executors.newFixedThreadPool(8);
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
            List<String> batch = new ArrayList<>();
            while (!queue.isEmpty() && batch.size() < 8) {
                String nodeName = queue.poll();
                
                if (stopAtNode != null && !stopAtNode.isEmpty() && isDependencyOf(stopAtNode, nodeName, nodes)) {
                    log.info("Skipping node {} as it's beyond stop_at node {}", nodeName, stopAtNode);
                    continue;
                }
                
                batch.add(nodeName);
            }

            if (batch.isEmpty()) {
                break;
            }

            List<Future<?>> futures = new ArrayList<>();
            for (String nodeName : batch) {
                WorkflowNode node = nodeMap.get(nodeName);
                futures.add(executor.submit(() -> {
                    try {
                        Object result = runNode(projectId, node, outputs);
                        outputs.put(nodeName, result);
                    } catch (Exception e) {
                        outputs.put(nodeName, Map.of("error", e.getMessage()));
                        log.error("Node {} failed: {}", nodeName, e.getMessage());
                    }
                }));
            }

            for (Future<?> f : futures) {
                try {
                    f.get();
                } catch (InterruptedException | ExecutionException e) {
                    log.error("Batch execution error: {}", e.getMessage());
                }
            }

            for (String nodeName : batch) {
                if (stopAtNode != null && stopAtNode.equals(nodeName)) {
                    log.info("Stopping workflow at node: {}", stopAtNode);
                    queue.clear();
                    break;
                }
                
                for (String next : adj.getOrDefault(nodeName, Set.of())) {
                    inDegree.put(next, inDegree.get(next) - 1);
                    if (inDegree.get(next) == 0) {
                        queue.add(next);
                    }
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
        }
        
        // Build payload from dependencies
        Map<String, Object> payload = new HashMap<>();
        for (String dep : node.dependencies()) {
            payload.put(dep, outputs.get(dep));
        }

        // Pass initial text to text_parse node
        if ("text_parse".equals(node.name())) {
            log.info("text_parse node detected, preparing payload");
            Map<String, Object> initialPayload = (Map<String, Object>) outputs.get("initial_payload");
            log.info("initial_payload exists: {}", initialPayload != null);
            if (initialPayload != null) {
                Object textObj = initialPayload.get("text");
                log.info("text value exists: {}, text: {}", textObj != null, textObj);
                if (textObj != null) {
                    payload.put("text", textObj);
                    log.info("text added to payload");
                }
            }
        }

        // Log start
        WorkflowLog startLog = new WorkflowLog();
        startLog.setProjectId(projectId);
        startLog.setNodeName(node.name());
        startLog.setStatus("running");
        startLog.setInputJson(toJson(payload));
        logRepository.save(startLog);

        log.info("Sending request to endpoint: {} with payload size: {}", node.endpoint(), payload.size());

        int retries = 0;
        Exception lastError = null;

        while (retries < MAX_RETRIES) {
            try {
                String response = webClient.post()
                    .uri(node.endpoint())
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(payload)
                    .retrieve()
                    .bodyToMono(String.class)
                    .timeout(Duration.ofMinutes(5))
                    .block();
                
                log.debug("Received response from {}: {}", node.name(), response);

                // Log success
                WorkflowLog successLog = new WorkflowLog();
                successLog.setProjectId(projectId);
                successLog.setNodeName(node.name());
                successLog.setStatus("success");
                successLog.setOutputJson(response);
                successLog.setRetryCount(retries);
                logRepository.save(successLog);
                if (logThinking) {
                    thinkingLogService.logCompleted(projectId, node.name());
                }

                return parseJson(response);
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
        }

        throw new RuntimeException("Node " + node.name() + " failed after " + MAX_RETRIES + " retries", lastError);
    }

    private boolean isDependencyOf(String candidate, String target, List<WorkflowNode> nodes) {
        if (candidate.equals(target)) return false;
        
        Map<String, List<String>> reverseAdj = new HashMap<>();
        for (WorkflowNode node : nodes) {
            for (String dep : node.dependencies()) {
                reverseAdj.computeIfAbsent(node.name(), k -> new ArrayList<>()).add(dep);
            }
        }
        
        Set<String> visited = new HashSet<>();
        Queue<String> queue = new LinkedList<>();
        queue.add(target);
        visited.add(target);
        
        while (!queue.isEmpty()) {
            String current = queue.poll();
            for (String dep : reverseAdj.getOrDefault(current, List.of())) {
                if (dep.equals(candidate)) {
                    return true;
                }
                if (!visited.contains(dep)) {
                    visited.add(dep);
                    queue.add(dep);
                }
            }
        }
        
        return false;
    }

    private String toJson(Object obj) {
        try {
            return new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(obj);
        } catch (Exception e) {
            return "{}";
        }
    }

    private Object parseJson(String json) {
        try {
            return new com.fasterxml.jackson.databind.ObjectMapper().readValue(json, Object.class);
        } catch (Exception e) {
            return json;
        }
    }
}
