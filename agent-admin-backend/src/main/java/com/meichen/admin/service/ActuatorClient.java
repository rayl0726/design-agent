package com.meichen.admin.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.meichen.admin.dto.DbPoolMetricsDTO;
import com.meichen.admin.dto.ThreadPoolMetricsDTO;
import io.netty.channel.ChannelOption;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

@Component
public class ActuatorClient {

    private static final Logger log = LoggerFactory.getLogger(ActuatorClient.class);
    private static final ObjectMapper objectMapper = new ObjectMapper();

    private final WebClient actuatorClient;

    public ActuatorClient(@Value("${admin.agent-api.base-url}") String agentApiBaseUrl) {
        HttpClient httpClient = HttpClient.create()
            .responseTimeout(Duration.ofSeconds(5))
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 2000);
        this.actuatorClient = WebClient.builder()
            .baseUrl(agentApiBaseUrl)
            .clientConnector(new ReactorClientHttpConnector(httpClient))
            .build();
    }

    public List<ThreadPoolMetricsDTO> getThreadPoolMetrics() {
        List<ThreadPoolMetricsDTO> pools = new ArrayList<>();
        String[] executorNames = {"workflowExecutor", "dialogueExecutor"};
        for (String name : executorNames) {
            try {
                CompletableFuture<Integer> activeF = CompletableFuture.supplyAsync(() -> getMetricValue("executor.active", "name", name));
                CompletableFuture<Integer> coreF = CompletableFuture.supplyAsync(() -> getMetricValue("executor.pool.core", "name", name));
                CompletableFuture<Integer> maxF = CompletableFuture.supplyAsync(() -> getMetricValue("executor.pool.max", "name", name));
                CompletableFuture<Long> completedF = CompletableFuture.supplyAsync(() -> getMetricValueAsLong("executor.completed", "name", name));
                CompletableFuture<Integer> queueF = CompletableFuture.supplyAsync(() -> getMetricValue("executor.queue.remaining", "name", name));
                CompletableFuture.allOf(activeF, coreF, maxF, completedF, queueF).join();
                pools.add(new ThreadPoolMetricsDTO(name, activeF.join(), coreF.join(), maxF.join(), completedF.join(), queueF.join()));
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
