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
class MetricsAdminControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("DELETE FROM feedbacks");
        jdbcTemplate.execute("DELETE FROM java_projects");
        jdbcTemplate.execute("DELETE FROM stage_logs");
        jdbcTemplate.execute("DELETE FROM stage_log_stats");

        jdbcTemplate.update(
            "INSERT INTO java_projects (id, name, status, current_level, created_at) " +
            "VALUES ('proj-1', 'Test Project 1', 'completed', 'L3', CURRENT_TIMESTAMP)");
        jdbcTemplate.update(
            "INSERT INTO java_projects (id, name, status, current_level, created_at) " +
            "VALUES ('proj-2', 'Test Project 2', 'in_progress', 'L1', CURRENT_TIMESTAMP)");

        jdbcTemplate.update(
            "INSERT INTO feedbacks (id, project_id, feedback_type, category, processed, tag, public_id) " +
            "VALUES ('fb-1', 'proj-1', 'image', 'like', false, 'positive', 'fpub1')");
        jdbcTemplate.update(
            "INSERT INTO feedbacks (id, project_id, feedback_type, category, processed, tag, public_id) " +
            "VALUES ('fb-2', 'proj-1', 'intent', 'correction', false, 'negative', 'fpub2')");

        jdbcTemplate.update(
            "INSERT INTO stage_logs (project_id, stage_name, stage_label, status, duration_ms) " +
            "VALUES ('proj-1', 'intent_recognition', '意图识别', 'success', 1500)");

        jdbcTemplate.update(
            "INSERT INTO stage_log_stats (stage_name, window_start, window_end, avg_ms, p95_ms, max_ms, success_count, failed_count) " +
            "VALUES ('intent_recognition', NOW(), NOW(), 1200, 1800, 2000, 10, 1)");
    }

    @Test
    void getOverview_returnsCorrectCounts() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/overview")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.projectCount").value(2))
            .andExpect(jsonPath("$.feedbackCount").value(2))
            .andExpect(jsonPath("$.imageFeedbackCount").value(1))
            .andExpect(jsonPath("$.intentCorrectionCount").value(1))
            .andExpect(jsonPath("$.stageLogCount").value(1));
    }

    @Test
    void getStageDurations_returnsStats() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/stages")
                .header("X-Admin-Token", "test-token")
                .param("hours", "24"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getFeedbackDistribution_returnsGroupedCounts() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/feedback-distribution")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getOverview_withoutToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/overview"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void getOverviewWithHours_returnsFilteredCounts() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/overview")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.projectCount").value(2))
            .andExpect(jsonPath("$.activeProjectsInWindow").exists())
            .andExpect(jsonPath("$.completedProjectsInWindow").exists());
    }

    @Test
    void getProjectTrend_returnsTimeSeries() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/trend/projects")
                .param("days", "30")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }
}
