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
class RagMetricsControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("DELETE FROM rag_search_logs");
        jdbcTemplate.update(
            "INSERT INTO rag_search_logs (project_id, query_text, search_type, result_count, duration_ms, cache_hit, timed_out, created_at) " +
            "VALUES ('proj-1', 'modern office', 'semantic', 5, 120, false, false, CURRENT_TIMESTAMP)");
        jdbcTemplate.update(
            "INSERT INTO rag_search_logs (project_id, query_text, search_type, result_count, duration_ms, cache_hit, timed_out, created_at) " +
            "VALUES ('proj-1', 'unknown topic', 'semantic', 0, 200, false, false, CURRENT_TIMESTAMP)");
        jdbcTemplate.update(
            "INSERT INTO rag_search_logs (project_id, query_text, search_type, result_count, duration_ms, cache_hit, timed_out, created_at) " +
            "VALUES ('proj-2', 'retail design', 'fallback', 3, 50, false, true, CURRENT_TIMESTAMP)");
    }

    @Test
    void getOverview_returns200AndAggregatedStats() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/rag/overview")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalSearches").value(3))
            .andExpect(jsonPath("$.timeoutCount").value(1))
            .andExpect(jsonPath("$.fallbackRate").exists());
    }

    @Test
    void getTimeline_returns200AndDailyAggregates() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/rag/timeline")
                .param("hours", "168")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getZeroResults_returns200AndZeroResultQueries() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/rag/zero-results")
                .param("days", "30")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalZeroResultSearches").value(1))
            .andExpect(jsonPath("$.topQueries[0].queryText").value("unknown topic"));
    }

    @Test
    void getInventory_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/rag/inventory")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk());
    }

    @Test
    void getOverview_noToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/rag/overview"))
            .andExpect(status().isUnauthorized());
    }
}
