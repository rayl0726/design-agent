package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.AiCallLog;
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
class AiCallLogRepositoryTest {

    @Autowired
    private AiCallLogRepository repository;

    @BeforeEach
    void setUp() {
        AiCallLog log1 = new AiCallLog();
        log1.setCallType("llm");
        log1.setProvider("zhipu");
        log1.setModel("GLM-4.7-Flash");
        log1.setStatus("success");
        log1.setDurationMs(1500);
        log1.setInputTokens(100);
        log1.setOutputTokens(50);
        log1.setTotalTokens(150);
        log1.setCreatedAt(LocalDateTime.now());
        repository.save(log1);

        AiCallLog log2 = new AiCallLog();
        log2.setCallType("llm");
        log2.setProvider("zhipu");
        log2.setModel("GLM-4.7-Flash");
        log2.setStatus("failed");
        log2.setDurationMs(500);
        log2.setErrorMessage("timeout");
        log2.setCreatedAt(LocalDateTime.now());
        repository.save(log2);

        AiCallLog log3 = new AiCallLog();
        log3.setCallType("image_gen");
        log3.setProvider("siliconflow");
        log3.setModel("FLUX.1-schnell");
        log3.setStatus("success");
        log3.setDurationMs(3000);
        log3.setCreatedAt(LocalDateTime.now());
        repository.save(log3);
    }

    @Test
    void countByCallTypeAndCreatedAtAfter_returnsCorrectCount() {
        LocalDateTime since = LocalDateTime.now().minusHours(1);
        long count = repository.countByCallTypeAndCreatedAtAfter("llm", since);
        assertEquals(2, count);
    }

    @Test
    void findByCallTypeAndCreatedAtAfter_returnsLogs() {
        LocalDateTime since = LocalDateTime.now().minusHours(1);
        List<AiCallLog> logs = repository.findByCallTypeAndCreatedAtAfter("image_gen", since);
        assertEquals(1, logs.size());
        assertEquals("siliconflow", logs.get(0).getProvider());
    }

    @Test
    void save_persistsAllFields() {
        AiCallLog log = new AiCallLog();
        log.setCallType("embedding");
        log.setProvider("ollama");
        log.setModel("bge-m3");
        log.setStatus("success");
        log.setDurationMs(200);
        log.setProjectId("proj-123");
        log.setNodeName("semantic_search");
        log.setCreatedAt(LocalDateTime.now());
        AiCallLog saved = repository.save(log);
        assertNotNull(saved.getId());
        assertEquals("proj-123", saved.getProjectId());
        assertEquals("semantic_search", saved.getNodeName());
    }
}
