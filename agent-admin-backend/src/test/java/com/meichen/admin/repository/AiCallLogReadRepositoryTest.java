package com.meichen.admin.repository;

import com.meichen.admin.entity.AiCallLogRead;
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
class AiCallLogReadRepositoryTest {

    @Autowired
    private AiCallLogReadRepository repository;

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
    void countByCallTypeAndCreatedAtAfter_returnsCorrectCount() {
        LocalDateTime since = LocalDateTime.now().minusHours(1);
        long count = repository.countByCallTypeAndCreatedAtAfter("llm", since);
        assertEquals(2, count);
    }

    @Test
    void groupByCallType_returnsAggregatedStats() {
        LocalDateTime since = LocalDateTime.now().minusHours(1);
        List<Object[]> results = repository.groupByCallType(since);
        assertFalse(results.isEmpty());
    }

    @Test
    void groupByProvider_returnsProviderStats() {
        LocalDateTime since = LocalDateTime.now().minusHours(1);
        List<Object[]> results = repository.groupByProvider(since);
        assertFalse(results.isEmpty());
    }
}
