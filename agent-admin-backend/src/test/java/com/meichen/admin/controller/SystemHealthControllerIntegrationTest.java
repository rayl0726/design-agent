package com.meichen.admin.controller;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:h2:mem:testdb;MODE=MySQL",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.datasource.username=sa",
    "spring.datasource.password=",
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "spring.flyway.enabled=false",
    "admin.token=test-token",
    "admin.agent-core.base-url=http://localhost:8000",
    "admin.agent-core.data-dir=/tmp",
    "admin.agent-api.base-url=http://localhost:8080"
})
class SystemHealthControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("DELETE FROM stage_logs");
        jdbcTemplate.execute("DELETE FROM workflow_logs");
        jdbcTemplate.execute("DELETE FROM http_request_logs");

        jdbcTemplate.update("INSERT INTO stage_logs (public_id, project_id, stage_name, status, started_at, duration_ms, time_anomaly, sub_stage_overflow) " +
            "VALUES ('pid1', 'proj-1', 'concept_design', 'SUCCESS', CURRENT_TIMESTAMP, 5000, FALSE, FALSE)");
        jdbcTemplate.update("INSERT INTO stage_logs (public_id, project_id, stage_name, status, started_at, duration_ms, error_message, time_anomaly, sub_stage_overflow) " +
            "VALUES ('pid2', 'proj-2', 'image_generation', 'FAILED', CURRENT_TIMESTAMP, 30000, 'timeout', FALSE, FALSE)");

        jdbcTemplate.update("INSERT INTO workflow_logs (project_id, node_name, status, error_message, retry_count) " +
            "VALUES ('proj-1', 'concept_design', 'success', NULL, 2)");
        jdbcTemplate.update("INSERT INTO workflow_logs (project_id, node_name, status, error_message, retry_count) " +
            "VALUES ('proj-2', 'image_generation', 'failed', 'API timeout', 1)");

        jdbcTemplate.update("INSERT INTO http_request_logs (method, path_pattern, status_code, duration_ms, created_at) " +
            "VALUES ('GET', '/api/v1/projects', 200, 50, CURRENT_TIMESTAMP)");
        jdbcTemplate.update("INSERT INTO http_request_logs (method, path_pattern, status_code, duration_ms, created_at) " +
            "VALUES ('POST', '/api/v1/projects', 500, 2000, CURRENT_TIMESTAMP)");
    }

    @Test
    void getWorkflowSuccess_returnsStats() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/workflow-success")
                .param("days", "7")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].stageName").exists())
            .andExpect(jsonPath("$[0].totalCount").exists())
            .andExpect(jsonPath("$[0].successCount").exists())
            .andExpect(jsonPath("$[0].failedCount").exists());
    }

    @Test
    void getRetries_returnsDistribution() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/retries")
                .param("days", "7")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].nodeName").exists())
            .andExpect(jsonPath("$[0].totalRetries").exists());
    }

    @Test
    void getErrors_returnsDistribution() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/errors")
                .param("days", "7")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].nodeName").exists());
    }

    @Test
    void getAnomalies_returnsStats() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/anomalies")
                .param("days", "7")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.timeAnomalyCount").exists())
            .andExpect(jsonPath("$.subStageOverflowCount").exists());
    }

    @Test
    void getHttp_returnsMetrics() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/http")
                .param("hours", "1")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalRequests").exists())
            .andExpect(jsonPath("$.errorCount").exists())
            .andExpect(jsonPath("$.avgDurationMs").exists());
    }

    @Test
    void getWorkflowSuccess_withoutToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/workflow-success"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void getThreadPools_returnsMetrics() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/thread-pools")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].name").exists())
            .andExpect(jsonPath("$[0].active").exists())
            .andExpect(jsonPath("$[0].core").exists())
            .andExpect(jsonPath("$[0].max").exists());
    }

    @Test
    void getDbPool_returnsMetrics() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/db-pool")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.active").exists())
            .andExpect(jsonPath("$.idle").exists())
            .andExpect(jsonPath("$.max").exists());
    }
}
