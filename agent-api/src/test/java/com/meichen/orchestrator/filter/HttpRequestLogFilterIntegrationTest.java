package com.meichen.orchestrator.filter;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:h2:mem:testdb;MODE=MySQL",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.datasource.username=sa",
    "spring.datasource.password=",
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "spring.flyway.enabled=false",
    "jwt.secret=test-secret-at-least-32-characters-long-for-testing"
})
class HttpRequestLogFilterIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Test
    void filter_logsApiRequestToHttpRequestLogs() throws Exception {
        // Actuator endpoint should be accessible and NOT logged
        mockMvc.perform(get("/actuator/health"))
            .andExpect(status().isOk());

        // API endpoint requiring auth — should return 401 but still be logged
        mockMvc.perform(get("/api/v1/projects"))
            .andExpect(status().isUnauthorized());

        // Wait a moment for @Async to complete
        Thread.sleep(500);

        // Verify that /api/v1/projects was logged but /actuator/health was NOT
        Long apiCount = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM http_request_logs WHERE path_pattern LIKE '%/api/v1/projects%'",
            Long.class);
        assertNotNull(apiCount);
        assertTrue(apiCount >= 1, "API request should be logged");

        Long actuatorCount = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM http_request_logs WHERE path_pattern LIKE '%/actuator%'",
            Long.class);
        assertEquals(0L, actuatorCount, "Actuator requests should NOT be logged");
    }

    @Test
    void filter_recordsStatusCodeAndDuration() throws Exception {
        mockMvc.perform(get("/api/v1/projects"))
            .andExpect(status().isUnauthorized());

        Thread.sleep(500);

        Integer statusCode = jdbcTemplate.queryForObject(
            "SELECT status_code FROM http_request_logs WHERE path_pattern LIKE '%/api/v1/projects%' ORDER BY id DESC LIMIT 1",
            Integer.class);
        assertNotNull(statusCode);
        assertEquals(401, statusCode);

        Integer durationMs = jdbcTemplate.queryForObject(
            "SELECT duration_ms FROM http_request_logs WHERE path_pattern LIKE '%/api/v1/projects%' ORDER BY id DESC LIMIT 1",
            Integer.class);
        assertNotNull(durationMs);
        assertTrue(durationMs >= 0);
    }
}
