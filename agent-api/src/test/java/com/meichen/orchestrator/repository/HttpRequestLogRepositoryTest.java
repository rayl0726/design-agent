package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.HttpRequestLog;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
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
class HttpRequestLogRepositoryTest {

    @Autowired
    private HttpRequestLogRepository repository;

    @BeforeEach
    void setUp() {
        HttpRequestLog log1 = new HttpRequestLog();
        log1.setMethod("GET");
        log1.setPathPattern("/api/v1/projects/{id}");
        log1.setStatusCode(200);
        log1.setDurationMs(50);
        log1.setCreatedAt(LocalDateTime.now());
        repository.save(log1);

        HttpRequestLog log2 = new HttpRequestLog();
        log2.setMethod("POST");
        log2.setPathPattern("/api/v1/projects");
        log2.setStatusCode(500);
        log2.setDurationMs(2000);
        log2.setCreatedAt(LocalDateTime.now());
        repository.save(log2);
    }

    @Test
    void save_persistsAllFields() {
        HttpRequestLog log = new HttpRequestLog();
        log.setMethod("DELETE");
        log.setPathPattern("/api/v1/projects/{id}");
        log.setStatusCode(204);
        log.setDurationMs(30);
        log.setCreatedAt(LocalDateTime.now());
        HttpRequestLog saved = repository.save(log);
        assertNotNull(saved.getId());
        assertEquals("DELETE", saved.getMethod());
        assertEquals(204, saved.getStatusCode());
    }

    @Test
    void findByCreatedAtAfter_returnsRecentLogs() {
        LocalDateTime since = LocalDateTime.now().minusHours(1);
        List<HttpRequestLog> logs = repository.findByCreatedAtAfter(since);
        assertEquals(2, logs.size());
    }

    @Test
    void countByCreatedAtAfter_returnsCorrectCount() {
        LocalDateTime since = LocalDateTime.now().minusHours(1);
        long count = repository.countByCreatedAtAfter(since);
        assertEquals(2, count);
    }
}
