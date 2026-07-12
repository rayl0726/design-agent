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
class MetricsTrendIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("DELETE FROM java_projects");
        jdbcTemplate.update(
            "INSERT INTO java_projects (id, name, status, current_level, created_at) " +
            "VALUES ('p1', 'Project A', 'completed', 'L3', CURRENT_TIMESTAMP)");
    }

    @Test
    void getProjectTrend_returnsDailyCounts() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/trend/projects")
                .param("days", "30")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].date").exists())
            .andExpect(jsonPath("$[0].count").exists());
    }

    @Test
    void getOverviewWithHours_returnsTimeFilteredCounts() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/overview")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.projectCount").exists())
            .andExpect(jsonPath("$.activeProjectsInWindow").exists());
    }
}
