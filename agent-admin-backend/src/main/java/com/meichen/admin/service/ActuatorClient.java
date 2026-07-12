package com.meichen.admin.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.meichen.admin.dto.DbPoolMetricsDTO;
import com.meichen.admin.dto.ThreadPoolMetricsDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Component
public class ActuatorClient {

    private static final Logger log = LoggerFactory.getLogger(ActuatorClient.class);
    private static final ObjectMapper objectMapper = new ObjectMapper();

    private final WebClient actuatorClient;

    public ActuatorClient(@Value("${admin.agent-api.base-url}") String agentApiBaseUrl) {
        this.actuatorClient = WebClient.builder().baseUrl(agentApiBaseUrl).build();
    }

    public List<ThreadPoolMetricsDTO> getThreadPoolMetrics() {
        List<ThreadPoolMetricsDTO> pools = new ArrayList<>();
        String[] executorNames = {"workflowExecutor", "dialogueExecutor"};
        for (String name : executorNames) {
            try {
                int active = getMetricValue("executor.active", "name", name);
                int core = getMetricValue("executor.pool.core", "name", name);
                int max = getMetricValue("executor.pool.max", "name", name);
                long completed = getMetricValueAsLong("executor.completed", "name", name);
                int queueSize = getMetricValue("executor.queue.remaining", "name", name);
                pools.add(new ThreadPoolMetricsDTO(name, active, core, max, completed, queueSize));
            } catch (Exception e) {
                log.warn("Failed to fetch thread pool metrics for {}: {}", name, e.getMessage());
                pools.add(new ThreadPoolMetricsDTO(name, 0, 0, 0, 0, 0));
            }
        }
        return pools;
    }

    public DbPoolMetricsDTO getDbPoolMetrics() {
        try {
            int active = getMetricValue("hikaricp.connections.active", "pool", "HikariPool-1");
            int idle = getMetricValue("hikaricp.connections.idle", "pool", "HikariPool-1");
            int max = getMetricValue("hikaricp.connections.max", "pool", "HikariPool-1");
            int pending = getMetricValue("hikaricp.connections.pending", "pool", "HikariPool-1");
            return new DbPoolMetricsDTO(active, idle, max, pending);
        } catch (Exception e) {
            log.warn("Failed to fetch DB pool metrics: {}", e.getMessage());
            return new DbPoolMetricsDTO(0, 0, 0, 0);
        }
    }

    private int getMetricValue(String metric, String tagKey, String tagValue) {
        Map<String, Object> response = fetchMetric(metric, tagKey, tagValue);
        List<?> measurements = (List<?>) response.get("measurements");
        if (measurements == null || measurements.isEmpty()) {
            return 0;
        }
        Map<?, ?> first = (Map<?, ?>) measurements.get(0);
        Number value = (Number) first.get("value");
        return value != null ? value.intValue() : 0;
    }

    private long getMetricValueAsLong(String metric, String tagKey, String tagValue) {
        Map<String, Object> response = fetchMetric(metric, tagKey, tagValue);
        List<?> measurements = (List<?>) response.get("measurements");
        if (measurements == null || measurements.isEmpty()) {
            return 0L;
        }
        Map<?, ?> first = (Map<?, ?>) measurements.get(0);
        Number value = (Number) first.get("value");
        return value != null ? value.longValue() : 0L;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> fetchMetric(String metric, String tagKey, String tagValue) {
        String json = actuatorClient.get()
            .uri(uriBuilder -> uriBuilder
                .path("/actuator/metrics/" + metric)
                .queryParam("tag", tagKey + ":" + tagValue)
                .build())
            .retrieve()
            .bodyToMono(String.class)
            .block(Duration.ofSeconds(5));
        try {
            return objectMapper.readValue(json, new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {});
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse Actuator response for " + metric, e);
        }
    }
}
