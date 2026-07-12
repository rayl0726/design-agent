package com.meichen.admin.repository;

import com.meichen.admin.entity.RagSearchLogRead;
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
class RagSearchLogReadRepositoryTest {

    @Autowired
    private RagSearchLogReadRepository repository;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("DELETE FROM rag_search_logs");
        // Insert test data: 2 semantic searches (1 with results, 1 zero-result), 1 fallback, 1 structured
        jdbcTemplate.update(
            "INSERT INTO rag_search_logs (project_id, query_text, search_type, result_count, duration_ms, cache_hit, timed_out, created_at) " +
            "VALUES ('proj-1', 'modern office', 'semantic', 5, 120, false, false, CURRENT_TIMESTAMP)");
        jdbcTemplate.update(
            "INSERT INTO rag_search_logs (project_id, query_text, search_type, result_count, duration_ms, cache_hit, timed_out, created_at) " +
            "VALUES ('proj-1', 'unknown topic', 'semantic', 0, 200, false, false, CURRENT_TIMESTAMP)");
        jdbcTemplate.update(
            "INSERT INTO rag_search_logs (project_id, query_text, search_type, result_count, duration_ms, cache_hit, timed_out, created_at) " +
            "VALUES ('proj-2', 'retail design', 'fallback', 3, 50, false, true, CURRENT_TIMESTAMP)");
        jdbcTemplate.update(
            "INSERT INTO rag_search_logs (project_id, query_text, search_type, result_count, duration_ms, cache_hit, timed_out, created_at) " +
            "VALUES ('proj-2', 'wood material', 'structured', 2, 30, true, false, CURRENT_TIMESTAMP)");
    }

    @Test
    void aggregateOverview_returnsCorrectStats() {
        LocalDateTime since = LocalDateTime.now().minusHours(1);
        Object[] result = repository.aggregateOverview(since);
        assertNotNull(result);
        // 6 values: total_count, avg_result_count, avg_duration, cache_hits, timeouts, fallbacks
        long total = ((Number) result[0]).longValue();
        assertEquals(4, total);
        long fallbacks = ((Number) result[5]).longValue();
        assertEquals(1, fallbacks);
    }

    @Test
    void aggregateOverview_returnsZerosForNoData() {
        LocalDateTime since = LocalDateTime.now().plusHours(1); // future = no data
        Object[] result = repository.aggregateOverview(since);
        assertNotNull(result);
        long total = ((Number) result[0]).longValue();
        assertEquals(0, total);
    }

    @Test
    void groupByDay_returnsDailyAggregates() {
        LocalDateTime since = LocalDateTime.now().minusDays(1);
        List<Object[]> results = repository.groupByDay(since);
        assertFalse(results.isEmpty());
        // Each row: date, count, avg_duration, cache_hit_rate
        Object[] firstRow = results.get(0);
        assertEquals(4, firstRow.length);
    }

    @Test
    void findZeroResults_returnsZeroResultQueries() {
        LocalDateTime since = LocalDateTime.now().minusDays(1);
        List<Object[]> results = repository.findZeroResults(since);
        assertFalse(results.isEmpty());
        // Should find "unknown topic" with 1 occurrence
        Object[] firstRow = results.get(0);
        String queryText = (String) firstRow[0];
        assertEquals("unknown topic", queryText);
        long count = ((Number) firstRow[1]).longValue();
        assertEquals(1, count);
    }
}
