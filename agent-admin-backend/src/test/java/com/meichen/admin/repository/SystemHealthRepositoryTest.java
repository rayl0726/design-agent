package com.meichen.admin.repository;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;

import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@DataJpaTest
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:h2:mem:testdb;MODE=MySQL",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.datasource.username=sa",
    "spring.datasource.password=",
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "spring.flyway.enabled=false"
})
class SystemHealthRepositoryTest {

    @Autowired
    private StageLogReadRepository stageLogRepo;

    @Autowired
    private WorkflowLogReadRepository workflowLogRepo;

    @Autowired
    private HttpRequestLogReadRepository httpLogRepo;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("DELETE FROM stage_logs");
        jdbcTemplate.execute("DELETE FROM workflow_logs");
        jdbcTemplate.execute("DELETE FROM http_request_logs");

        // Stage logs: 2 success, 1 failed (top-level), 1 with time_anomaly
        jdbcTemplate.update("INSERT INTO stage_logs (public_id, project_id, stage_name, status, started_at, duration_ms, time_anomaly, sub_stage_overflow) " +
            "VALUES ('pid1', 'proj-1', 'concept_design', 'SUCCESS', CURRENT_TIMESTAMP, 5000, FALSE, FALSE)");
        jdbcTemplate.update("INSERT INTO stage_logs (public_id, project_id, stage_name, status, started_at, duration_ms, time_anomaly, sub_stage_overflow) " +
            "VALUES ('pid2', 'proj-2', 'concept_design', 'SUCCESS', CURRENT_TIMESTAMP, 6000, FALSE, FALSE)");
        jdbcTemplate.update("INSERT INTO stage_logs (public_id, project_id, stage_name, status, started_at, duration_ms, error_message, time_anomaly, sub_stage_overflow) " +
            "VALUES ('pid3', 'proj-3', 'image_generation', 'FAILED', CURRENT_TIMESTAMP, 30000, 'timeout', FALSE, FALSE)");
        jdbcTemplate.update("INSERT INTO stage_logs (public_id, project_id, stage_name, status, started_at, duration_ms, time_anomaly, sub_stage_overflow) " +
            "VALUES ('pid4', 'proj-4', 'concept_design', 'SUCCESS', CURRENT_TIMESTAMP, 120000, TRUE, TRUE)");

        // Workflow logs: 1 retry on concept_design, 1 failed on image_generation
        jdbcTemplate.update("INSERT INTO workflow_logs (project_id, node_name, status, error_message, retry_count) " +
            "VALUES ('proj-1', 'concept_design', 'success', NULL, 0)");
        jdbcTemplate.update("INSERT INTO workflow_logs (project_id, node_name, status, error_message, retry_count) " +
            "VALUES ('proj-2', 'concept_design', 'success', NULL, 2)");
        jdbcTemplate.update("INSERT INTO workflow_logs (project_id, node_name, status, error_message, retry_count) " +
            "VALUES ('proj-3', 'image_generation', 'failed', 'API timeout: 30s', 1)");

        // HTTP request logs
        jdbcTemplate.update("INSERT INTO http_request_logs (method, path_pattern, status_code, duration_ms, created_at) " +
            "VALUES ('GET', '/api/v1/projects', 200, 50, CURRENT_TIMESTAMP)");
        jdbcTemplate.update("INSERT INTO http_request_logs (method, path_pattern, status_code, duration_ms, created_at) " +
            "VALUES ('GET', '/api/v1/projects/{id}', 200, 30, CURRENT_TIMESTAMP)");
        jdbcTemplate.update("INSERT INTO http_request_logs (method, path_pattern, status_code, duration_ms, created_at) " +
            "VALUES ('POST', '/api/v1/projects', 500, 2000, CURRENT_TIMESTAMP)");
    }

    @Test
    void stageLogRepo_aggregateWorkflowSuccess_returnsStats() {
        LocalDateTime since = LocalDateTime.now().minusDays(7);
        List<Object[]> results = stageLogRepo.aggregateWorkflowSuccess(since);
        assertFalse(results.isEmpty());
        // Should have 2 stage_names: concept_design (2 success, 0 failed) and image_generation (0 success, 1 failed)
        assertEquals(2, results.size());
    }

    @Test
    void stageLogRepo_countAnomalies_returnsCounts() {
        LocalDateTime since = LocalDateTime.now().minusDays(7);
        Object[] result = stageLogRepo.countAnomalies(since);
        assertNotNull(result);
        // time_anomaly count = 1, sub_stage_overflow count = 1
        long timeAnomaly = ((Number) result[0]).longValue();
        long overflow = ((Number) result[1]).longValue();
        assertEquals(1, timeAnomaly);
        assertEquals(1, overflow);
    }

    @Test
    void workflowLogRepo_aggregateRetries_returnsRetryStats() {
        LocalDateTime since = LocalDateTime.now().minusDays(7);
        List<Object[]> results = workflowLogRepo.aggregateRetries(since);
        assertFalse(results.isEmpty());
    }

    @Test
    void workflowLogRepo_aggregateErrors_returnsErrorStats() {
        LocalDateTime since = LocalDateTime.now().minusDays(7);
        List<Object[]> results = workflowLogRepo.aggregateErrors(since);
        assertFalse(results.isEmpty());
    }

    @Test
    void httpLogRepo_aggregateHttp_returnsOverallStats() {
        LocalDateTime since = LocalDateTime.now().minusHours(1);
        Object[] result = httpLogRepo.aggregateHttp(since);
        assertNotNull(result);
        long totalRequests = ((Number) result[0]).longValue();
        assertEquals(3, totalRequests);
    }

    @Test
    void httpLogRepo_groupByPathPattern_returnsTopEndpoints() {
        LocalDateTime since = LocalDateTime.now().minusHours(1);
        List<Object[]> results = httpLogRepo.groupByPathPattern(since);
        assertFalse(results.isEmpty());
    }
}
