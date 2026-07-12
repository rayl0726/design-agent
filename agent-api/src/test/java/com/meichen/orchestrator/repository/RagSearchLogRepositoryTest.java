package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.RagSearchLog;
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
class RagSearchLogRepositoryTest {

    @Autowired
    private RagSearchLogRepository repository;

    @Test
    void saveAndFindBySearchType() {
        RagSearchLog log = new RagSearchLog();
        log.setProjectId("proj-1");
        log.setQueryText("modern office design");
        log.setSearchType("semantic");
        log.setResultCount(5);
        log.setDurationMs(120);
        log.setCacheHit(false);
        log.setTimedOut(false);
        log.setCreatedAt(LocalDateTime.now());
        repository.save(log);

        List<RagSearchLog> results = repository.findBySearchTypeAndCreatedAtAfter(
            "semantic", LocalDateTime.now().minusMinutes(1));
        assertEquals(1, results.size());
        assertEquals("modern office design", results.get(0).getQueryText());
        assertEquals(5, results.get(0).getResultCount());
    }

    @Test
    void countByCreatedAtAfter_returnsZeroForNoData() {
        long count = repository.countByCreatedAtAfter(LocalDateTime.now().minusDays(1));
        assertEquals(0, count);
    }
}
