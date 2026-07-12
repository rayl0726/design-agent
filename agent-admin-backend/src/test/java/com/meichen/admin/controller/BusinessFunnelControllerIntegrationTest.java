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
class BusinessFunnelControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("DELETE FROM java_projects");
        jdbcTemplate.execute("DELETE FROM session_messages");
        jdbcTemplate.update(
            "INSERT INTO java_projects (id, name, status, current_level, created_at, requirement_json) " +
            "VALUES ('p1', 'Project A', 'completed', 'L3', CURRENT_TIMESTAMP, " +
            "'{\"space_type\": \"购物中心中庭\", \"budget_level\": \"high\", \"style\": \"现代简约\"}')");
        jdbcTemplate.update(
            "INSERT INTO java_projects (id, name, status, current_level, created_at, requirement_json) " +
            "VALUES ('p2', 'Project B', 'draft', 'L1', CURRENT_TIMESTAMP, " +
            "'{\"space_type\": \"品牌门店\", \"budget_level\": \"medium\", \"style\": \"工业风\"}')");
        jdbcTemplate.update(
            "INSERT INTO java_projects (id, name, status, current_level, created_at) " +
            "VALUES ('p3', 'Project C', 'generating', 'L2', CURRENT_TIMESTAMP)");

        jdbcTemplate.update(
            "INSERT INTO session_messages (id, project_id, role, message_type, content, public_id) " +
            "VALUES ('m1', 'p1', 'user', 'text', 'hello', 'smpub1')");
        jdbcTemplate.update(
            "INSERT INTO session_messages (id, project_id, role, message_type, content, public_id) " +
            "VALUES ('m2', 'p1', 'assistant', 'text', 'hi', 'smpub2')");
        jdbcTemplate.update(
            "INSERT INTO session_messages (id, project_id, role, message_type, content, public_id) " +
            "VALUES ('m3', 'p1', 'user', 'text', 'design', 'smpub3')");
        jdbcTemplate.update(
            "INSERT INTO session_messages (id, project_id, role, message_type, content, public_id) " +
            "VALUES ('m4', 'p2', 'user', 'text', 'test', 'smpub4')");
    }

    @Test
    void getFunnel_returnsStatusCounts() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/funnel")
                .param("days", "30")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.draftCount").value(1))
            .andExpect(jsonPath("$.generatingCount").value(1))
            .andExpect(jsonPath("$.completedCount").value(1));
    }

    @Test
    void getFunnel_withoutToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/funnel"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void getLevels_returnsLevelDistribution() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/funnel/levels")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].level").value("L1"))
            .andExpect(jsonPath("$[0].count").value(1));
    }

    @Test
    void getDuration_returnsStats() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/funnel/duration")
                .param("days", "30")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.avgDurationHours").exists());
    }

    @Test
    void getConversations_returnsTurnStats() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/conversations")
                .param("days", "30")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.avgTurns").exists())
            .andExpect(jsonPath("$.totalProjects").value(2));
    }

    @Test
    void getDimensionSpaceType_returnsDistribution() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/dimensions/space-type")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].dimensionValue").exists())
            .andExpect(jsonPath("$[0].count").exists());
    }

    @Test
    void getDimensionBudgetLevel_returnsDistribution() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/dimensions/budget-level")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getAbandonment_returnsOldDrafts() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/funnel/abandonment")
                .param("days", "0")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getDimensions_allThree() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/dimensions/space-type")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());

        mockMvc.perform(get("/api/admin/metrics/dimensions/budget-level")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());

        mockMvc.perform(get("/api/admin/metrics/dimensions/style")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }
}
