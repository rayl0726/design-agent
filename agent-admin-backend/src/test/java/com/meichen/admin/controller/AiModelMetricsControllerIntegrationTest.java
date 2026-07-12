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
    "admin.agent-core.data-dir=/tmp"
})
class AiModelMetricsControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("DELETE FROM ai_call_logs");
        jdbcTemplate.update(
            "INSERT INTO ai_call_logs (call_type, provider, model, status, duration_ms, input_tokens, output_tokens, total_tokens, created_at) " +
            "VALUES ('llm', 'zhipu', 'GLM-4.7-Flash', 'success', 1500, 100, 50, 150, CURRENT_TIMESTAMP)");
        jdbcTemplate.update(
            "INSERT INTO ai_call_logs (call_type, provider, model, status, duration_ms, input_tokens, output_tokens, total_tokens, created_at) " +
            "VALUES ('llm', 'zhipu', 'GLM-4.7-Flash', 'failed', 500, 0, 0, 0, CURRENT_TIMESTAMP)");
        jdbcTemplate.update(
            "INSERT INTO ai_call_logs (call_type, provider, model, status, duration_ms, input_tokens, output_tokens, total_tokens, created_at) " +
            "VALUES ('image_gen', 'siliconflow', 'FLUX.1-schnell', 'success', 3000, 0, 0, 0, CURRENT_TIMESTAMP)");
    }

    @Test
    void getSummary_returnsAggregatedByCallType() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/ai-calls/summary")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].callType").value("llm"))
            .andExpect(jsonPath("$[0].totalCount").value(2))
            .andExpect(jsonPath("$[0].successCount").value(1))
            .andExpect(jsonPath("$[0].failedCount").value(1));
    }

    @Test
    void getByProvider_returnsProviderBreakdown() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/ai-calls/by-provider")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].provider").exists());
    }

    @Test
    void getTimeline_returnsTimeSeries() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/ai-calls/timeline")
                .param("hours", "168")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getTokens_returnsTokenUsage() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/ai-calls/tokens")
                .param("hours", "168")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getSummary_withoutToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/ai-calls/summary"))
            .andExpect(status().isUnauthorized());
    }
}
