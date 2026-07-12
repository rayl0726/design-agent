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
    "admin.token=test-token",
    "admin.agent-core.base-url=http://localhost:99999",
    "admin.agent-core.data-dir=/tmp"
})
class PromptTemplateEnhancedIntegrationTest {

    @Autowired
    private MockMvc mockMvc;
    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Test
    void getUsage_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/prompt-templates/usage")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getUsage_withData_returnsNodeStats() throws Exception {
        jdbcTemplate.update(
            "INSERT INTO ai_call_logs (project_id, call_type, provider, model, node_name, status, duration_ms, input_tokens, output_tokens, total_tokens, created_at) " +
            "VALUES (?, 'llm', 'zhipu', 'glm-4', 'prompt_generation', 'success', 500, 100, 200, 300, NOW())",
            "proj-1"
        );

        mockMvc.perform(get("/api/admin/prompt-templates/usage")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].templateVersion").value("prompt_generation"))
            .andExpect(jsonPath("$[0].totalInvocations").value(1))
            .andExpect(jsonPath("$[0].uniqueProjects").value(1));
    }

    @Test
    void getQualityTrend_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/prompt-templates/quality-trend")
                .param("hours", "168")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getCompare_returns200() throws Exception {
        jdbcTemplate.update(
            "INSERT INTO feedbacks (id, project_id, feedback_type, tag, image_url, prompt_template_version, created_at) " +
            "VALUES (?, 'proj-1', 'image', 'good', 'http://example.com/1.jpg', 'v1.0', NOW())",
            java.util.UUID.randomUUID().toString()
        );

        mockMvc.perform(get("/api/admin/prompt-templates/compare")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].version").value("v1.0"));
    }

    @Test
    void getUsage_noToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/prompt-templates/usage"))
            .andExpect(status().isUnauthorized());
    }
}
