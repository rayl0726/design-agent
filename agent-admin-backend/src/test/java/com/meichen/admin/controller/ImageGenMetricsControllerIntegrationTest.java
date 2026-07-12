package com.meichen.admin.controller;

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
    "admin.token=test-token"
})
class ImageGenMetricsControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;
    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Test
    void getOverview_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/image-generation/overview")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalGenerated").exists())
            .andExpect(jsonPath("$.successRate").exists());
    }

    @Test
    void getOverview_withData_returnsCorrectStats() throws Exception {
        insertImageGenLog("siliconflow", "success", 5000, "proj-1");
        insertImageGenLog("siliconflow", "failed", 1000, "proj-2");

        mockMvc.perform(get("/api/admin/metrics/image-generation/overview")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalGenerated").value(2))
            .andExpect(jsonPath("$.successCount").value(1))
            .andExpect(jsonPath("$.failedCount").value(1));
    }

    @Test
    void getByProvider_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/image-generation/by-provider")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getFeedback_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/image-generation/feedback")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalImages").exists())
            .andExpect(jsonPath("$.feedbackRate").exists());
    }

    @Test
    void getFeedbackTrend_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/image-generation/feedback-trend")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getDistribution_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/image-generation/distribution")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getOverview_noToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/image-generation/overview"))
            .andExpect(status().isUnauthorized());
    }

    private void insertImageGenLog(String provider, String status, int durationMs, String projectId) {
        jdbcTemplate.update(
            "INSERT INTO ai_call_logs (project_id, call_type, provider, model, node_name, status, duration_ms, input_tokens, output_tokens, total_tokens, created_at) " +
            "VALUES (?, 'image_generation', ?, 'test-model', 'test-node', ?, ?, 0, 0, 0, NOW())",
            projectId, provider, status, durationMs
        );
    }
}
