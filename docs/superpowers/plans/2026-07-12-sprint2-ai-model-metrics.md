# Sprint 2: AI Model Call Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AI model call instrumentation (Python decorator), internal log ingestion endpoint (agent-api), admin query APIs, and a frontend monitoring page for LLM/VLM/Embedding/Image generation calls.

**Architecture:** Python `@log_ai_call` decorator wraps AI client methods and fire-and-forget POSTs log records to agent-api's internal endpoint. agent-api persists to `ai_call_logs` table via JPA. admin-backend queries the same table (read-only) and exposes 4 metrics endpoints. Frontend `AiModelMonitoring.vue` renders summary cards, provider pie chart, timeline chart, and token usage chart.

**Tech Stack:** Python 3.11+ / httpx / pytest, Java 17 / Spring Boot 3.2.5 / JPA / Flyway / H2 (tests), Vue 3 / Element Plus / ECharts

## Global Constraints

- LLM/VLM must use 智谱 API only (GLM-4.7-Flash); Embedding must use Ollama bge-m3
- Python logging must be fire-and-forget (asyncio.create_task, swallow errors, 3s timeout)
- agent-api Flyway migrations follow existing naming: V2026071201__*.sql
- admin-backend entities are read-only (no setters beyond id), mapping to tables created by agent-api
- admin-backend DTOs use Java `record` type
- admin-backend tests use @SpringBootTest + H2 in MySQL mode
- Frontend uses existing `client` from `src/api/client.js` (baseURL: `/api/admin`, X-Admin-Token header)
- Use TypeReference<Map<String, Object>> {} instead of Map.class for objectMapper.readValue

---

## File Structure

### agent-api (Java, :8080)

| File | Responsibility |
|------|---------------|
| `agent-api/src/main/resources/db/migration/V2026071201__create_ai_call_logs.sql` | Flyway migration creating `ai_call_logs` table |
| `agent-api/src/main/java/com/meichen/orchestrator/entity/AiCallLog.java` | JPA entity mapping to `ai_call_logs` |
| `agent-api/src/main/java/com/meichen/orchestrator/repository/AiCallLogRepository.java` | Spring Data JPA repository with save + queries |
| `agent-api/src/main/java/com/meichen/orchestrator/controller/InternalLogController.java` | POST `/api/v1/internal/ai-call-logs` endpoint |
| `agent-api/src/main/java/com/meichen/orchestrator/dto/AiCallLogRequest.java` | DTO for incoming log record from Python |
| `agent-api/src/test/java/com/meichen/orchestrator/repository/AiCallLogRepositoryTest.java` | @DataJpaTest for repository |
| `agent-api/src/test/java/com/meichen/orchestrator/controller/InternalLogControllerIntegrationTest.java` | @SpringBootTest for endpoint |

### agent-core (Python, :8000)

| File | Responsibility |
|------|---------------|
| `agent-core/app/services/call_logger.py` | `@log_ai_call` decorator + `_send_log()` async function |
| `agent-core/app/core/config.py` (modify) | Add `agent_api_base_url` setting |
| `agent-core/app/services/llm_client.py` (modify) | Apply decorator to `ZhipuProvider.complete()`, store `_last_usage` |
| `agent-core/app/services/vlm_client.py` (modify) | Apply decorator to `ZhipuVLMClient.describe()`, store `_last_usage` |
| `agent-core/app/services/embedding_client.py` (modify) | Apply decorator to `OllamaEmbeddingProvider.embed()` |
| `agent-core/app/services/image_generation.py` (modify) | Apply decorator to each provider's `generate()` |
| `agent-core/tests/services/test_call_logger.py` | Unit tests for decorator |

### agent-admin-backend (Java, :8081)

| File | Responsibility |
|------|---------------|
| `agent-admin-backend/src/main/java/com/meichen/admin/entity/AiCallLogRead.java` | Read-only JPA entity |
| `agent-admin-backend/src/main/java/com/meichen/admin/repository/AiCallLogReadRepository.java` | Aggregation query methods |
| `agent-admin-backend/src/main/java/com/meichen/admin/dto/AiCallSummaryDTO.java` | Summary record (per call_type) |
| `agent-admin-backend/src/main/java/com/meichen/admin/dto/AiCallProviderBreakdownDTO.java` | Provider breakdown record |
| `agent-admin-backend/src/main/java/com/meichen/admin/dto/AiCallTimelineDTO.java` | Timeline record |
| `agent-admin-backend/src/main/java/com/meichen/admin/dto/TokenUsageDTO.java` | Token usage + cost record |
| `agent-admin-backend/src/main/java/com/meichen/admin/service/AiModelMetricsService.java` | Service with 4 query methods |
| `agent-admin-backend/src/main/java/com/meichen/admin/controller/AiModelMetricsController.java` | Controller at `/api/admin/metrics/ai-calls` |
| `agent-admin-backend/src/test/java/com/meichen/admin/controller/AiModelMetricsControllerIntegrationTest.java` | Integration tests |

### agent-admin-front (Vue, :8082)

| File | Responsibility |
|------|---------------|
| `agent-admin-front/src/views/AiModelMonitoring.vue` | AI monitoring page with cards + charts |
| `agent-admin-front/src/router/index.js` (modify) | Add route |
| `agent-admin-front/src/layouts/AdminLayout.vue` (modify) | Add menu item |

---

## Task 1: Flyway Migration for ai_call_logs Table

**Files:**
- Create: `agent-api/src/main/resources/db/migration/V2026071201__create_ai_call_logs.sql`

**Interfaces:**
- Produces: `ai_call_logs` table with columns: id (BIGINT AUTO_INCREMENT PK), project_id, call_type, provider, model, node_name, status, duration_ms, input_tokens, output_tokens, total_tokens, error_message, retry_count, created_at

- [ ] **Step 1: Create the Flyway migration script**

```sql
-- ai_call_logs: AI model call instrumentation log
CREATE TABLE ai_call_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id VARCHAR(36) DEFAULT NULL,
    call_type VARCHAR(20) NOT NULL COMMENT 'llm/vlm/embedding/image_gen',
    provider VARCHAR(50) NOT NULL COMMENT 'zhipu/siliconflow/pollinations/ollama',
    model VARCHAR(100) NOT NULL,
    node_name VARCHAR(50) DEFAULT NULL COMMENT 'text_parse/concept_design/image_generation etc',
    status VARCHAR(20) NOT NULL COMMENT 'success/failed/timeout/rate_limited',
    duration_ms INT NOT NULL,
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    error_message TEXT DEFAULT NULL,
    retry_count INT DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_call_type_created (call_type, created_at),
    INDEX idx_provider_created (provider, created_at),
    INDEX idx_project_id (project_id),
    INDEX idx_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

- [ ] **Step 2: Verify migration applies**

Run: `cd agent-api && mvn spring-boot:run -q 2>&1 | tail -20`
Expected: Application starts, Flyway log shows "Migrating schema... to version 2026071201" (then stop the app with Ctrl+C)

- [ ] **Step 3: Verify table exists in MySQL**

Run: `mysql -u meichen -pmeichen123 -e "DESCRIBE ai_call_logs;" meichen 2>/dev/null`
Expected: Table structure with all columns listed

- [ ] **Step 4: Commit**

```bash
git add agent-api/src/main/resources/db/migration/V2026071201__create_ai_call_logs.sql
git commit -m "feat(agent-api): add ai_call_logs table for AI call instrumentation"
```

---

## Task 2: agent-api AiCallLog Entity + Repository

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/entity/AiCallLog.java`
- Create: `agent-api/src/main/java/com/meichen/orchestrator/repository/AiCallLogRepository.java`
- Test: `agent-api/src/test/java/com/meichen/orchestrator/repository/AiCallLogRepositoryTest.java`

**Interfaces:**
- Produces: `AiCallLog` entity with getters/setters, `AiCallLogRepository` with `save()` and query methods

- [ ] **Step 1: Write the failing repository test**

```java
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-api && mvn test -pl . -Dtest=AiCallLogRepositoryTest -q 2>&1 | tail -10`
Expected: COMPILATION ERROR (AiCallLog and AiCallLogRepository don't exist)

- [ ] **Step 3: Write AiCallLog entity**

```java
package com.meichen.orchestrator.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "ai_call_logs")
public class AiCallLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "project_id", length = 36)
    private String projectId;

    @Column(name = "call_type", length = 20, nullable = false)
    private String callType;

    @Column(name = "provider", length = 50, nullable = false)
    private String provider;

    @Column(name = "model", length = 100, nullable = false)
    private String model;

    @Column(name = "node_name", length = 50)
    private String nodeName;

    @Column(name = "status", length = 20, nullable = false)
    private String status;

    @Column(name = "duration_ms", nullable = false)
    private Integer durationMs;

    @Column(name = "input_tokens")
    private Integer inputTokens;

    @Column(name = "output_tokens")
    private Integer outputTokens;

    @Column(name = "total_tokens")
    private Integer totalTokens;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "retry_count")
    private Integer retryCount;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getProjectId() { return projectId; }
    public void setProjectId(String projectId) { this.projectId = projectId; }
    public String getCallType() { return callType; }
    public void setCallType(String callType) { this.callType = callType; }
    public String getProvider() { return provider; }
    public void setProvider(String provider) { this.provider = provider; }
    public String getModel() { return model; }
    public void setModel(String model) { this.model = model; }
    public String getNodeName() { return nodeName; }
    public void setNodeName(String nodeName) { this.nodeName = nodeName; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public Integer getDurationMs() { return durationMs; }
    public void setDurationMs(Integer durationMs) { this.durationMs = durationMs; }
    public Integer getInputTokens() { return inputTokens; }
    public void setInputTokens(Integer inputTokens) { this.inputTokens = inputTokens; }
    public Integer getOutputTokens() { return outputTokens; }
    public void setOutputTokens(Integer outputTokens) { this.outputTokens = outputTokens; }
    public Integer getTotalTokens() { return totalTokens; }
    public void setTotalTokens(Integer totalTokens) { this.totalTokens = totalTokens; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public Integer getRetryCount() { return retryCount; }
    public void setRetryCount(Integer retryCount) { this.retryCount = retryCount; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
```

- [ ] **Step 4: Write AiCallLogRepository**

```java
package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.AiCallLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface AiCallLogRepository extends JpaRepository<AiCallLog, Long> {

    long countByCallTypeAndCreatedAtAfter(String callType, LocalDateTime createdAt);

    List<AiCallLog> findByCallTypeAndCreatedAtAfter(String callType, LocalDateTime createdAt);

    @Query("SELECT l FROM AiCallLog l WHERE l.createdAt >= :since ORDER BY l.createdAt DESC")
    List<AiCallLog> findAllSince(@Param("since") LocalDateTime since);
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd agent-api && mvn test -pl . -Dtest=AiCallLogRepositoryTest -q 2>&1 | tail -10`
Expected: Tests run: 3, Failures: 0, Errors: 0

- [ ] **Step 6: Commit**

```bash
git add agent-api/src/main/java/com/meichen/orchestrator/entity/AiCallLog.java \
        agent-api/src/main/java/com/meichen/orchestrator/repository/AiCallLogRepository.java \
        agent-api/src/test/java/com/meichen/orchestrator/repository/AiCallLogRepositoryTest.java
git commit -m "feat(agent-api): add AiCallLog entity and repository"
```

---

## Task 3: agent-api Internal Endpoint for AI Call Logs

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/dto/AiCallLogRequest.java`
- Create: `agent-api/src/main/java/com/meichen/orchestrator/controller/InternalLogController.java`
- Test: `agent-api/src/test/java/com/meichen/orchestrator/controller/InternalLogControllerIntegrationTest.java`

**Interfaces:**
- Consumes: `AiCallLogRepository.save()` from Task 2
- Produces: `POST /api/v1/internal/ai-call-logs` endpoint accepting JSON body with call_type, provider, model, status, duration_ms, input_tokens, output_tokens, total_tokens, error_message, project_id, node_name

- [ ] **Step 1: Write the failing controller integration test**

```java
package com.meichen.orchestrator.controller;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
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
    "jwt.secret=test-secret"
})
class InternalLogControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Test
    void postAiCallLog_persistsRecord() throws Exception {
        String body = """
            {
                "call_type": "llm",
                "provider": "zhipu",
                "model": "GLM-4.7-Flash",
                "status": "success",
                "duration_ms": 1500,
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "project_id": "proj-1",
                "node_name": "intent_recognition"
            }
            """;

        mockMvc.perform(post("/api/v1/internal/ai-call-logs")
                .contentType(MediaType.APPLICATION_JSON)
                .content(body))
            .andExpect(status().isOk());

        Long count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM ai_call_logs WHERE call_type = 'llm'",
            Long.class);
        assertEquals(1L, count);
    }

    @Test
    void postAiCallLog_failedStatus_persistsErrorMessage() throws Exception {
        String body = """
            {
                "call_type": "image_gen",
                "provider": "siliconflow",
                "model": "FLUX.1-schnell",
                "status": "failed",
                "duration_ms": 500,
                "error_message": "API returned 500"
            }
            """;

        mockMvc.perform(post("/api/v1/internal/ai-call-logs")
                .contentType(MediaType.APPLICATION_JSON)
                .content(body))
            .andExpect(status().isOk());
    }

    @Test
    void postAiCallLog_missingRequiredField_returns400() throws Exception {
        String body = """
            {
                "provider": "zhipu",
                "model": "GLM-4.7-Flash"
            }
            """;

        mockMvc.perform(post("/api/v1/internal/ai-call-logs")
                .contentType(MediaType.APPLICATION_JSON)
                .content(body))
            .andExpect(status().isBadRequest());
    }

    private static void assertEquals(Object expected, Object actual) {
        org.junit.jupiter.api.Assertions.assertEquals(expected, actual);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-api && mvn test -pl . -Dtest=InternalLogControllerIntegrationTest -q 2>&1 | tail -10`
Expected: COMPILATION ERROR (InternalLogController doesn't exist)

- [ ] **Step 3: Write AiCallLogRequest DTO**

```java
package com.meichen.orchestrator.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public class AiCallLogRequest {

    @NotBlank
    private String callType;

    @NotBlank
    private String provider;

    @NotBlank
    private String model;

    private String nodeName;

    @NotBlank
    private String status;

    @NotNull
    private Integer durationMs;

    private String projectId;

    private Integer inputTokens;

    private Integer outputTokens;

    private Integer totalTokens;

    private String errorMessage;

    private Integer retryCount;

    public String getCallType() { return callType; }
    public void setCallType(String callType) { this.callType = callType; }
    public String getProvider() { return provider; }
    public void setProvider(String provider) { this.provider = provider; }
    public String getModel() { return model; }
    public void setModel(String model) { this.model = model; }
    public String getNodeName() { return nodeName; }
    public void setNodeName(String nodeName) { this.nodeName = nodeName; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public Integer getDurationMs() { return durationMs; }
    public void setDurationMs(Integer durationMs) { this.durationMs = durationMs; }
    public String getProjectId() { return projectId; }
    public void setProjectId(String projectId) { this.projectId = projectId; }
    public Integer getInputTokens() { return inputTokens; }
    public void setInputTokens(Integer inputTokens) { this.inputTokens = inputTokens; }
    public Integer getOutputTokens() { return outputTokens; }
    public void setOutputTokens(Integer outputTokens) { this.outputTokens = outputTokens; }
    public Integer getTotalTokens() { return totalTokens; }
    public void setTotalTokens(Integer totalTokens) { this.totalTokens = totalTokens; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public Integer getRetryCount() { return retryCount; }
    public void setRetryCount(Integer retryCount) { this.retryCount = retryCount; }
}
```

- [ ] **Step 4: Write InternalLogController**

```java
package com.meichen.orchestrator.controller;

import com.meichen.orchestrator.dto.AiCallLogRequest;
import com.meichen.orchestrator.entity.AiCallLog;
import com.meichen.orchestrator.repository.AiCallLogRepository;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;

@RestController
@RequestMapping("/api/v1/internal")
public class InternalLogController {

    private static final Logger log = LoggerFactory.getLogger(InternalLogController.class);

    private final AiCallLogRepository aiCallLogRepository;

    public InternalLogController(AiCallLogRepository aiCallLogRepository) {
        this.aiCallLogRepository = aiCallLogRepository;
    }

    @PostMapping("/ai-call-logs")
    public ResponseEntity<Void> receiveAiCallLog(@Valid @RequestBody AiCallLogRequest request) {
        try {
            AiCallLog entity = new AiCallLog();
            entity.setCallType(request.getCallType());
            entity.setProvider(request.getProvider());
            entity.setModel(request.getModel());
            entity.setNodeName(request.getNodeName());
            entity.setStatus(request.getStatus());
            entity.setDurationMs(request.getDurationMs());
            entity.setProjectId(request.getProjectId());
            entity.setInputTokens(request.getInputTokens() != null ? request.getInputTokens() : 0);
            entity.setOutputTokens(request.getOutputTokens() != null ? request.getOutputTokens() : 0);
            entity.setTotalTokens(request.getTotalTokens() != null ? request.getTotalTokens() : 0);
            entity.setErrorMessage(request.getErrorMessage());
            entity.setRetryCount(request.getRetryCount() != null ? request.getRetryCount() : 0);
            entity.setCreatedAt(LocalDateTime.now());
            aiCallLogRepository.save(entity);
            return ResponseEntity.ok().build();
        } catch (Exception e) {
            log.error("Failed to persist AI call log: {}", e.getMessage(), e);
            return ResponseEntity.internalServerError().build();
        }
    }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd agent-api && mvn test -pl . -Dtest=InternalLogControllerIntegrationTest -q 2>&1 | tail -10`
Expected: Tests run: 3, Failures: 0, Errors: 0

- [ ] **Step 6: Commit**

```bash
git add agent-api/src/main/java/com/meichen/orchestrator/dto/AiCallLogRequest.java \
        agent-api/src/main/java/com/meichen/orchestrator/controller/InternalLogController.java \
        agent-api/src/test/java/com/meichen/orchestrator/controller/InternalLogControllerIntegrationTest.java
git commit -m "feat(agent-api): add internal endpoint for AI call log ingestion"
```

---

## Task 4: Python @log_ai_call Decorator

**Files:**
- Create: `agent-core/app/services/call_logger.py`
- Modify: `agent-core/app/core/config.py` (add `agent_api_base_url` setting)
- Test: `agent-core/tests/services/test_call_logger.py`

**Interfaces:**
- Produces: `@log_ai_call(call_type, provider)` decorator that wraps async methods, captures timing/status/tokens, and fire-and-forget POSTs to `{agent_api_base_url}/api/v1/internal/ai-call-logs`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for @log_ai_call decorator."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.call_logger import log_ai_call, _send_log


@pytest.mark.asyncio
async def test_decorator_success_logs_correctly():
    """Decorator should send a success log with correct fields."""
    captured = {}

    async def fake_send(**kwargs):
        captured.update(kwargs)

    class FakeClient:
        model = "GLM-4.7-Flash"
        _last_usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

        @log_ai_call("llm", "zhipu")
        async def complete(self, system_prompt, user_prompt):
            return "result"

    with patch("app.services.call_logger._send_log", side_effect=fake_send):
        client = FakeClient()
        result = await client.complete("sys", "user")

    assert result == "result"
    assert captured["call_type"] == "llm"
    assert captured["provider"] == "zhipu"
    assert captured["model"] == "GLM-4.7-Flash"
    assert captured["status"] == "success"
    assert captured["duration_ms"] >= 0
    assert captured["input_tokens"] == 100
    assert captured["output_tokens"] == 50
    assert captured["total_tokens"] == 150


@pytest.mark.asyncio
async def test_decorator_failed_logs_error():
    """Decorator should log failed status when exception is raised."""
    captured = {}

    async def fake_send(**kwargs):
        captured.update(kwargs)

    class FakeClient:
        model = "GLM-4.7-Flash"

        @log_ai_call("llm", "zhipu")
        async def complete(self, system_prompt, user_prompt):
            raise RuntimeError("API error")

    with patch("app.services.call_logger._send_log", side_effect=fake_send):
        client = FakeClient()
        with pytest.raises(RuntimeError):
            await client.complete("sys", "user")

    assert captured["status"] == "failed"
    assert "API error" in captured["error_message"]


@pytest.mark.asyncio
async def test_decorator_swallows_send_errors():
    """Decorator should not raise if _send_log fails."""
    class FakeClient:
        model = "GLM-4.7-Flash"

        @log_ai_call("llm", "zhipu")
        async def complete(self, system_prompt, user_prompt):
            return "ok"

    async def failing_send(**kwargs):
        raise ConnectionError("network down")

    with patch("app.services.call_logger._send_log", side_effect=failing_send):
        client = FakeClient()
        result = await client.complete("sys", "user")

    assert result == "ok"


@pytest.mark.asyncio
async def test_send_log_posts_to_correct_url():
    """_send_log should POST to agent-api internal endpoint."""
    import httpx
    from app.services.call_logger import _send_log

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        await _send_log(
            call_type="llm",
            provider="zhipu",
            model="GLM-4.7-Flash",
            status="success",
            duration_ms=100,
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
        )

    assert mock_post.called
    call_args = mock_post.call_args
    assert "/api/v1/internal/ai-call-logs" in call_args[0][0]
    body = call_args[1]["json"]
    assert body["call_type"] == "llm"
    assert body["provider"] == "zhipu"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-core && python -m pytest tests/services/test_call_logger.py -v 2>&1 | tail -20`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.call_logger'"

- [ ] **Step 3: Add agent_api_base_url to config**

In `agent-core/app/core/config.py`, add this line after `comfyui_base_url` (around line 52):

```python
    agent_api_base_url: str = "http://localhost:8080"
```

- [ ] **Step 4: Write call_logger.py**

```python
"""AI call logging decorator for fire-and-forget instrumentation."""
from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _send_log(**kwargs: Any) -> None:
    """Send a log record to agent-api internal endpoint. Swallows all errors."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(
                f"{settings.agent_api_base_url}/api/v1/internal/ai-call-logs",
                json=kwargs,
            )
    except Exception as e:
        logger.debug("Failed to send AI call log: %s", e)


def log_ai_call(call_type: str, provider: str):
    """Decorator that logs AI model calls to agent-api.

    Wraps an async method on a client class. Captures duration, status,
    and token usage (from self._last_usage if available).

    Args:
        call_type: One of 'llm', 'vlm', 'embedding', 'image_gen'
        provider: Provider name like 'zhipu', 'siliconflow', 'ollama'
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            start = asyncio.get_event_loop().time()
            status = "success"
            error_message = None
            try:
                result = await func(self, *args, **kwargs)
                return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    status = "rate_limited"
                else:
                    status = "failed"
                error_message = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                raise
            except httpx.TimeoutException:
                status = "timeout"
                error_message = "Request timed out"
                raise
            except Exception as e:
                status = "failed"
                error_message = f"{type(e).__name__}: {e}"
                raise
            finally:
                duration_ms = int((asyncio.get_event_loop().time() - start) * 1000)
                model = getattr(self, "model", "unknown")
                usage = getattr(self, "_last_usage", None) or {}
                input_tokens = usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0
                output_tokens = usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0
                total_tokens = usage.get("total_tokens", 0) if isinstance(usage, dict) else 0

                log_payload = {
                    "call_type": call_type,
                    "provider": provider,
                    "model": model,
                    "status": status,
                    "duration_ms": duration_ms,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                }
                if error_message:
                    log_payload["error_message"] = error_message
                project_id = getattr(self, "_log_project_id", None)
                if project_id:
                    log_payload["project_id"] = project_id
                node_name = getattr(self, "_log_node_name", None)
                if node_name:
                    log_payload["node_name"] = node_name

                try:
                    asyncio.create_task(_send_log(**log_payload))
                except RuntimeError:
                    pass

        return wrapper

    return decorator
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd agent-core && python -m pytest tests/services/test_call_logger.py -v 2>&1 | tail -20`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add agent-core/app/services/call_logger.py \
        agent-core/app/core/config.py \
        agent-core/tests/services/test_call_logger.py
git commit -m "feat(agent-core): add @log_ai_call decorator for AI call instrumentation"
```

---

## Task 5: Apply Decorator to AI Clients

**Files:**
- Modify: `agent-core/app/services/llm_client.py` — apply `@log_ai_call("llm", "zhipu")` to `ZhipuProvider.complete()`, store `_last_usage`
- Modify: `agent-core/app/services/vlm_client.py` — apply `@log_ai_call("vlm", "zhipu")` to `ZhipuVLMClient.describe()`, store `_last_usage`
- Modify: `agent-core/app/services/embedding_client.py` — apply `@log_ai_call("embedding", "ollama")` to `OllamaEmbeddingProvider.embed()`
- Modify: `agent-core/app/services/image_generation.py` — apply `@log_ai_call("image_gen", "siliconflow")` to `SiliconFlowProvider.generate()`, `@log_ai_call("image_gen", "zhipu")` to `ZhipuProvider.generate()`, `@log_ai_call("image_gen", "pollinations")` to `PollinationsProvider.generate()`

**Interfaces:**
- Consumes: `log_ai_call` decorator from Task 4
- Produces: Instrumented AI client methods that log every call to agent-api

- [ ] **Step 1: Apply decorator to ZhipuProvider in llm_client.py**

In `agent-core/app/services/llm_client.py`:

1. Add import at top (after `from app.core.config import settings`):
```python
from app.services.call_logger import log_ai_call
```

2. In `ZhipuProvider.complete()`, add `self._last_usage = None` at the start of the method, and before `return data.get(...)` add:
```python
                usage = data.get("usage", {})
                self._last_usage = usage
```

3. Add `@log_ai_call("llm", "zhipu")` decorator on the `complete` method:
```python
    @log_ai_call("llm", "zhipu")
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
```

- [ ] **Step 2: Apply decorator to ZhipuVLMClient in vlm_client.py**

In `agent-core/app/services/vlm_client.py`:

1. Add import:
```python
from app.services.call_logger import log_ai_call
```

2. In `ZhipuVLMClient.describe()`, before `return data.get(...)` add:
```python
            usage = data.get("usage", {})
            self._last_usage = usage
```

3. Add decorator:
```python
    @log_ai_call("vlm", "zhipu")
    async def describe(
        self,
        image_path: str | Path,
        prompt: str = "请详细描述这张图片中的场景、物体、颜色、材质和空间布局。",
        json_mode: bool = False,
    ) -> str:
```

- [ ] **Step 3: Apply decorator to OllamaEmbeddingProvider in embedding_client.py**

In `agent-core/app/services/embedding_client.py`:

1. Add import:
```python
from app.services.call_logger import log_ai_call
```

2. Add decorator to `OllamaEmbeddingProvider.embed()`:
```python
    @log_ai_call("embedding", "ollama")
    async def embed(self, text: str) -> list[float]:
```

- [ ] **Step 4: Apply decorator to image generation providers in image_generation.py**

In `agent-core/app/services/image_generation.py`:

1. Add import:
```python
from app.services.call_logger import log_ai_call
```

2. Add decorator to `SiliconFlowProvider.generate()`:
```python
    @log_ai_call("image_gen", "siliconflow")
    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
```

3. Add decorator to `ZhipuProvider.generate()`:
```python
    @log_ai_call("image_gen", "zhipu")
    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
```

4. Add decorator to `PollinationsProvider.generate()`:
```python
    @log_ai_call("image_gen", "pollinations")
    async def generate(self, prompt: str, aspect_ratio: str = "16:9", style: str = "realistic") -> str:
```

- [ ] **Step 5: Verify Python imports work**

Run: `cd agent-core && python -c "from app.services.llm_client import ZhipuProvider; from app.services.vlm_client import ZhipuVLMClient; from app.services.embedding_client import OllamaEmbeddingProvider; from app.services.image_generation import SiliconFlowProvider; print('All imports OK')"`
Expected: "All imports OK"

- [ ] **Step 6: Run existing Python tests to ensure no regression**

Run: `cd agent-core && python -m pytest tests/services/ -v 2>&1 | tail -20`
Expected: All existing tests still pass

- [ ] **Step 7: Commit**

```bash
git add agent-core/app/services/llm_client.py \
        agent-core/app/services/vlm_client.py \
        agent-core/app/services/embedding_client.py \
        agent-core/app/services/image_generation.py
git commit -m "feat(agent-core): apply @log_ai_call decorator to all AI client methods"
```

---

## Task 6: admin-backend AiCallLogRead Entity + Repository

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/entity/AiCallLogRead.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/repository/AiCallLogReadRepository.java`
- Test: `agent-admin-backend/src/test/java/com/meichen/admin/repository/AiCallLogReadRepositoryTest.java`

**Interfaces:**
- Produces: `AiCallLogRead` read-only entity, `AiCallLogReadRepository` with aggregation queries

- [ ] **Step 1: Write the failing repository test**

```java
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-admin-backend && mvn test -Dtest=AiCallLogReadRepositoryTest -q 2>&1 | tail -10`
Expected: COMPILATION ERROR

- [ ] **Step 3: Write AiCallLogRead entity**

```java
package com.meichen.admin.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "ai_call_logs")
public class AiCallLogRead {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "project_id", length = 36)
    private String projectId;

    @Column(name = "call_type", length = 20)
    private String callType;

    @Column(name = "provider", length = 50)
    private String provider;

    @Column(name = "model", length = 100)
    private String model;

    @Column(name = "node_name", length = 50)
    private String nodeName;

    @Column(name = "status", length = 20)
    private String status;

    @Column(name = "duration_ms")
    private Integer durationMs;

    @Column(name = "input_tokens")
    private Integer inputTokens;

    @Column(name = "output_tokens")
    private Integer outputTokens;

    @Column(name = "total_tokens")
    private Integer totalTokens;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public String getProjectId() { return projectId; }
    public String getCallType() { return callType; }
    public String getProvider() { return provider; }
    public String getModel() { return model; }
    public String getNodeName() { return nodeName; }
    public String getStatus() { return status; }
    public Integer getDurationMs() { return durationMs; }
    public Integer getInputTokens() { return inputTokens; }
    public Integer getOutputTokens() { return outputTokens; }
    public Integer getTotalTokens() { return totalTokens; }
    public String getErrorMessage() { return errorMessage; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
```

- [ ] **Step 4: Write AiCallLogReadRepository**

```java
package com.meichen.admin.repository;

import com.meichen.admin.entity.AiCallLogRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface AiCallLogReadRepository extends JpaRepository<AiCallLogRead, Long> {

    long countByCallTypeAndCreatedAtAfter(String callType, LocalDateTime createdAt);

    @Query("SELECT l.callType, COUNT(l), " +
           "SUM(CASE WHEN l.status = 'success' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN l.status = 'failed' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN l.status = 'rate_limited' THEN 1 ELSE 0 END), " +
           "AVG(l.durationMs), " +
           "SUM(l.inputTokens), " +
           "SUM(l.outputTokens) " +
           "FROM AiCallLogRead l WHERE l.createdAt >= :since " +
           "GROUP BY l.callType")
    List<Object[]> groupByCallType(@Param("since") LocalDateTime since);

    @Query("SELECT l.provider, l.model, COUNT(l), " +
           "SUM(CASE WHEN l.status = 'success' THEN 1 ELSE 0 END), " +
           "AVG(l.durationMs), " +
           "SUM(l.totalTokens) " +
           "FROM AiCallLogRead l WHERE l.createdAt >= :since " +
           "GROUP BY l.provider, l.model")
    List<Object[]> groupByProvider(@Param("since") LocalDateTime since);

    @Query("SELECT CAST(l.createdAt AS date), l.callType, COUNT(l), " +
           "SUM(CASE WHEN l.status != 'success' THEN 1 ELSE 0 END) " +
           "FROM AiCallLogRead l WHERE l.createdAt >= :since " +
           "GROUP BY CAST(l.createdAt AS date), l.callType " +
           "ORDER BY CAST(l.createdAt AS date)")
    List<Object[]> groupByDateAndCallType(@Param("since") LocalDateTime since);

    @Query("SELECT CAST(l.createdAt AS date), l.provider, " +
           "SUM(l.inputTokens), SUM(l.outputTokens), SUM(l.totalTokens) " +
           "FROM AiCallLogRead l WHERE l.createdAt >= :since " +
           "GROUP BY CAST(l.createdAt AS date), l.provider " +
           "ORDER BY CAST(l.createdAt AS date)")
    List<Object[]> groupTokensByDateAndProvider(@Param("since") LocalDateTime since);

    @Query("SELECT l FROM AiCallLogRead l WHERE l.status != 'success' AND l.createdAt >= :since " +
           "ORDER BY l.createdAt DESC LIMIT :limit")
    List<AiCallLogRead> findRecentErrors(@Param("since") LocalDateTime since, @Param("limit") int limit);
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd agent-admin-backend && mvn test -Dtest=AiCallLogReadRepositoryTest -q 2>&1 | tail -10`
Expected: Tests run: 3, Failures: 0, Errors: 0

- [ ] **Step 6: Commit**

```bash
git add agent-admin-backend/src/main/java/com/meichen/admin/entity/AiCallLogRead.java \
        agent-admin-backend/src/main/java/com/meichen/admin/repository/AiCallLogReadRepository.java \
        agent-admin-backend/src/test/java/com/meichen/admin/repository/AiCallLogReadRepositoryTest.java
git commit -m "feat(admin): add AiCallLogRead entity and repository for AI metrics"
```

---

## Task 7: admin-backend DTOs + Service + Controller

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/AiCallSummaryDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/AiCallProviderBreakdownDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/AiCallTimelineDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/TokenUsageDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/service/AiModelMetricsService.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/controller/AiModelMetricsController.java`
- Test: `agent-admin-backend/src/test/java/com/meichen/admin/controller/AiModelMetricsControllerIntegrationTest.java`

**Interfaces:**
- Consumes: `AiCallLogReadRepository` from Task 6
- Produces: 4 API endpoints at `/api/admin/metrics/ai-calls`: GET /summary, GET /by-provider, GET /timeline, GET /tokens

- [ ] **Step 1: Write the failing controller integration test**

```java
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
class AiModelMetricsControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

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
    void getSummary_returnsAggregatedByCallType() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/ai-calls/summary")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].callType").value("llm"))
            .andExpect(jsonPath("$[0].totalCount").value(2))
            .andExpect(jsonPath("$[0].successCount").value(1))
            .andExpect(jsonPath("$[0].failedCount").value(1));
    }

    @Test
    void getByProvider_returnsProviderBreakdown() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/ai-calls/by-provider")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].provider").exists());
    }

    @Test
    void getTimeline_returnsTimeSeries() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/ai-calls/timeline")
                .param("hours", "168")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getTokens_returnsTokenUsage() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/ai-calls/tokens")
                .param("hours", "168")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getSummary_withoutToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/ai-calls/summary"))
            .andExpect(status().isUnauthorized());
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-admin-backend && mvn test -Dtest=AiModelMetricsControllerIntegrationTest -q 2>&1 | tail -10`
Expected: COMPILATION ERROR

- [ ] **Step 3: Write DTOs**

`AiCallSummaryDTO.java`:
```java
package com.meichen.admin.dto;

public record AiCallSummaryDTO(
    String callType,
    long totalCount,
    long successCount,
    long failedCount,
    long rateLimitedCount,
    double avgLatencyMs,
    long totalInputTokens,
    long totalOutputTokens
) {}
```

`AiCallProviderBreakdownDTO.java`:
```java
package com.meichen.admin.dto;

public record AiCallProviderBreakdownDTO(
    String provider,
    String model,
    long callCount,
    double successRate,
    double avgLatencyMs,
    long totalTokens
) {}
```

`AiCallTimelineDTO.java`:
```java
package com.meichen.admin.dto;

public record AiCallTimelineDTO(
    String date,
    String callType,
    long count,
    long errorCount
) {}
```

`TokenUsageDTO.java`:
```java
package com.meichen.admin.dto;

public record TokenUsageDTO(
    String date,
    String provider,
    long inputTokens,
    long outputTokens,
    long totalTokens,
    double estimatedCost
) {}
```

- [ ] **Step 4: Write AiModelMetricsService**

```java
package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.AiCallLogReadRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
public class AiModelMetricsService {

    private static final Map<String, Map<String, Double>> PRICING = Map.of(
        "zhipu", Map.of("input", 0.5 / 1_000_000, "output", 0.5 / 1_000_000),
        "siliconflow", Map.of("input", 0.0, "output", 0.0),
        "ollama", Map.of("input", 0.0, "output", 0.0),
        "pollinations", Map.of("input", 0.0, "output", 0.0)
    );

    private final AiCallLogReadRepository repository;

    public AiModelMetricsService(AiCallLogReadRepository repository) {
        this.repository = repository;
    }

    public List<AiCallSummaryDTO> getCallSummary(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = repository.groupByCallType(since);
        return rows.stream().map(row -> new AiCallSummaryDTO(
            (String) row[0],
            ((Number) row[1]).longValue(),
            ((Number) row[2]).longValue(),
            ((Number) row[3]).longValue(),
            ((Number) row[4]).longValue(),
            row[5] != null ? ((Number) row[5]).doubleValue() : 0.0,
            row[6] != null ? ((Number) row[6]).longValue() : 0L,
            row[7] != null ? ((Number) row[7]).longValue() : 0L
        )).toList();
    }

    public List<AiCallProviderBreakdownDTO> getByProvider(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = repository.groupByProvider(since);
        return rows.stream().map(row -> {
            long total = ((Number) row[2]).longValue();
            long success = ((Number) row[3]).longValue();
            return new AiCallProviderBreakdownDTO(
                (String) row[0],
                (String) row[1],
                total,
                total > 0 ? (double) success / total * 100 : 0.0,
                row[4] != null ? ((Number) row[4]).doubleValue() : 0.0,
                row[5] != null ? ((Number) row[5]).longValue() : 0L
            );
        }).toList();
    }

    public List<AiCallTimelineDTO> getTimeline(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = repository.groupByDateAndCallType(since);
        return rows.stream().map(row -> new AiCallTimelineDTO(
            row[0] != null ? row[0].toString() : "",
            (String) row[1],
            ((Number) row[2]).longValue(),
            ((Number) row[3]).longValue()
        )).toList();
    }

    public List<TokenUsageDTO> getTokenUsage(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = repository.groupTokensByDateAndProvider(since);
        return rows.stream().map(row -> {
            String provider = (String) row[1];
            long inputTokens = row[2] != null ? ((Number) row[2]).longValue() : 0L;
            long outputTokens = row[3] != null ? ((Number) row[3]).longValue() : 0L;
            long totalTokens = row[4] != null ? ((Number) row[4]).longValue() : 0L;
            double cost = estimateCost(provider, inputTokens, outputTokens);
            return new TokenUsageDTO(
                row[0] != null ? row[0].toString() : "",
                provider,
                inputTokens,
                outputTokens,
                totalTokens,
                cost
            );
        }).toList();
    }

    private double estimateCost(String provider, long inputTokens, long outputTokens) {
        Map<String, Double> pricing = PRICING.getOrDefault(provider, Map.of("input", 0.0, "output", 0.0));
        return inputTokens * pricing.get("input") + outputTokens * pricing.get("output");
    }
}
```

- [ ] **Step 5: Write AiModelMetricsController**

```java
package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.AiModelMetricsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/metrics/ai-calls")
public class AiModelMetricsController {

    private final AiModelMetricsService service;

    public AiModelMetricsController(AiModelMetricsService service) {
        this.service = service;
    }

    @GetMapping("/summary")
    public ResponseEntity<List<AiCallSummaryDTO>> getSummary(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getCallSummary(hours));
    }

    @GetMapping("/by-provider")
    public ResponseEntity<List<AiCallProviderBreakdownDTO>> getByProvider(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getByProvider(hours));
    }

    @GetMapping("/timeline")
    public ResponseEntity<List<AiCallTimelineDTO>> getTimeline(
            @RequestParam(defaultValue = "168") int hours) {
        return ResponseEntity.ok(service.getTimeline(hours));
    }

    @GetMapping("/tokens")
    public ResponseEntity<List<TokenUsageDTO>> getTokens(
            @RequestParam(defaultValue = "168") int hours) {
        return ResponseEntity.ok(service.getTokenUsage(hours));
    }
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd agent-admin-backend && mvn test -Dtest=AiModelMetricsControllerIntegrationTest -q 2>&1 | tail -10`
Expected: Tests run: 5, Failures: 0, Errors: 0

- [ ] **Step 7: Run full admin-backend test suite**

Run: `cd agent-admin-backend && mvn test -q 2>&1 | grep -E "Tests run|BUILD"`
Expected: BUILD SUCCESS, all tests pass

- [ ] **Step 8: Commit**

```bash
git add agent-admin-backend/src/main/java/com/meichen/admin/dto/AiCall*.java \
        agent-admin-backend/src/main/java/com/meichen/admin/dto/TokenUsageDTO.java \
        agent-admin-backend/src/main/java/com/meichen/admin/service/AiModelMetricsService.java \
        agent-admin-backend/src/main/java/com/meichen/admin/controller/AiModelMetricsController.java \
        agent-admin-backend/src/test/java/com/meichen/admin/controller/AiModelMetricsControllerIntegrationTest.java
git commit -m "feat(admin): add AI model metrics API with summary, provider, timeline, and token endpoints"
```

---

## Task 8: Frontend AiModelMonitoring.vue + Router + Menu

**Files:**
- Create: `agent-admin-front/src/views/AiModelMonitoring.vue`
- Modify: `agent-admin-front/src/router/index.js`
- Modify: `agent-admin-front/src/layouts/AdminLayout.vue`

**Interfaces:**
- Consumes: 4 API endpoints from Task 7 (`/metrics/ai-calls/summary`, `/by-provider`, `/timeline`, `/tokens`)

- [ ] **Step 1: Create AiModelMonitoring.vue**

```vue
<template>
  <div class="ai-monitoring" v-loading="loading">
    <!-- 时间范围选择器 -->
    <div class="header">
      <el-radio-group v-model="hours" size="small" @change="loadAll">
        <el-radio-button :label="24">24h</el-radio-button>
        <el-radio-button :label="168">7d</el-radio-button>
        <el-radio-button :label="720">30d</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 调用概览卡片 -->
    <el-row :gutter="20" class="overview-row">
      <el-col v-for="card in summaryCards" :key="card.key" :xs="12" :sm="8" :md="6" :lg="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-body">
            <div class="stat-icon" :style="{ backgroundColor: card.color }">
              <el-icon :size="24"><component :is="card.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Provider 分布 + 调用趋势 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">Provider 分布</span></div>
          <v-chart class="chart" :option="providerChartOption" autoresize style="height: 320px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">调用趋势</span></div>
          <v-chart class="chart" :option="timelineChartOption" autoresize style="height: 320px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Token 用量 -->
    <el-card shadow="never" class="chart-card">
      <div class="chart-header"><span class="chart-title">Token 用量趋势</span></div>
      <v-chart class="chart" :option="tokenChartOption" autoresize style="height: 350px" />
    </el-card>

    <!-- 错误分析表格 -->
    <el-card shadow="never" class="chart-card">
      <div class="chart-header"><span class="chart-title">Provider 调用明细</span></div>
      <el-table :data="providerBreakdown" stripe style="width: 100%">
        <el-table-column prop="provider" label="Provider" width="120" />
        <el-table-column prop="model" label="Model" />
        <el-table-column prop="callCount" label="调用次数" width="100" />
        <el-table-column prop="successRate" label="成功率" width="100">
          <template #default="{ row }">{{ row.successRate.toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column prop="avgLatencyMs" label="平均延迟(ms)" width="120">
          <template #default="{ row }">{{ row.avgLatencyMs.toFixed(0) }}</template>
        </el-table-column>
        <el-table-column prop="totalTokens" label="总Token" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import client from '../api/client'
import { use } from 'echarts/core'
import VChart from 'vue-echarts'
import { BarChart, PieChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CanvasRenderer, BarChart, PieChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(false)
const hours = ref(24)
const summary = ref([])
const providerBreakdown = ref([])
const timeline = ref([])
const tokenUsage = ref([])

const summaryCards = computed(() => {
  const cards = []
  const types = [
    { type: 'llm', label: 'LLM 调用', icon: 'ChatLineSquare', color: '#409eff' },
    { type: 'vlm', label: 'VLM 调用', icon: 'Picture', color: '#67c23a' },
    { type: 'embedding', label: 'Embedding', icon: 'Histogram', color: '#e6a23c' },
    { type: 'image_gen', label: '图像生成', icon: 'Image', color: '#f56c6c' },
  ]
  for (const t of types) {
    const s = summary.value.find(s => s.callType === t.type)
    cards.push({
      key: t.type,
      label: t.label,
      icon: t.icon,
      color: t.color,
      value: s ? s.totalCount : 0,
    })
  }
  const totalCalls = summary.value.reduce((sum, s) => sum + s.totalCount, 0)
  const totalSuccess = summary.value.reduce((sum, s) => sum + s.successCount, 0)
  const totalTokens = summary.value.reduce((sum, s) => sum + s.totalInputTokens + s.totalOutputTokens, 0)
  cards.push(
    { key: 'total', label: '总调用', icon: 'DataLine', color: '#9c27b0', value: totalCalls },
    { key: 'successRate', label: '成功率', icon: 'CircleCheck', color: '#4caf50', value: totalCalls > 0 ? ((totalSuccess / totalCalls) * 100).toFixed(1) + '%' : '0%' },
    { key: 'tokens', label: '总Token', icon: 'Coin', color: '#ff9800', value: totalTokens },
  )
  return cards
})

const providerChartOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { orient: 'vertical', left: 'left', top: 'center' },
  series: [{
    type: 'pie',
    radius: ['40%', '65%'],
    center: ['60%', '50%'],
    data: providerBreakdown.value.map(p => ({ name: `${p.provider}/${p.model}`, value: p.callCount })),
    label: { show: true, formatter: '{b}: {c}' },
  }],
}))

const timelineChartOption = computed(() => {
  const dates = [...new Set(timeline.value.map(t => t.date))].sort()
  const types = [...new Set(timeline.value.map(t => t.callType))]
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: types },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' },
    series: types.map(type => ({
      name: type,
      type: 'bar',
      stack: 'total',
      data: dates.map(d => {
        const item = timeline.value.find(t => t.date === d && t.callType === type)
        return item ? item.count : 0
      }),
    })),
  }
})

const tokenChartOption = computed(() => {
  const dates = [...new Set(tokenUsage.value.map(t => t.date))].sort()
  const providers = [...new Set(tokenUsage.value.map(t => t.provider))]
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: providers },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: 'Tokens' },
    series: providers.map(prov => ({
      name: prov,
      type: 'line',
      smooth: true,
      data: dates.map(d => {
        const item = tokenUsage.value.find(t => t.date === d && t.provider === prov)
        return item ? item.totalTokens : 0
      }),
    })),
  }
})

async function loadAll() {
  loading.value = true
  try {
    const [s, p, t, tokens] = await Promise.all([
      client.get('/metrics/ai-calls/summary', { params: { hours: hours.value } }),
      client.get('/metrics/ai-calls/by-provider', { params: { hours: hours.value } }),
      client.get('/metrics/ai-calls/timeline', { params: { hours: hours.value } }),
      client.get('/metrics/ai-calls/tokens', { params: { hours: hours.value } }),
    ])
    summary.value = s
    providerBreakdown.value = p
    timeline.value = t
    tokenUsage.value = tokens
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.ai-monitoring { display: flex; flex-direction: column; gap: 20px; }
.header { display: flex; align-items: center; justify-content: flex-end; }
.overview-row { margin-bottom: 0; }
.stat-card { margin-bottom: 20px; }
.stat-body { display: flex; align-items: center; gap: 16px; }
.stat-icon { width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #fff; flex-shrink: 0; }
.stat-info { display: flex; flex-direction: column; justify-content: center; min-width: 0; }
.stat-value { font-size: 24px; font-weight: 700; color: #303133; line-height: 1.2; }
.stat-label { font-size: 12px; color: #909399; margin-top: 4px; }
.chart-card { margin-bottom: 0; }
.chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.chart-title { font-size: 16px; font-weight: 600; color: #303133; }
.chart { width: 100%; }
</style>
```

- [ ] **Step 2: Add route in router/index.js**

Add this entry to the `children` array in `src/router/index.js`, after the `IntentTaxonomy` route:

```javascript
      {
        path: 'ai-monitoring',
        name: 'AiModelMonitoring',
        component: () => import('../views/AiModelMonitoring.vue'),
        meta: { title: 'AI 模型监控', icon: 'Monitor' }
      },
```

- [ ] **Step 3: Add menu item in AdminLayout.vue**

Add this object to the `menuItems` array in `src/layouts/AdminLayout.vue`, after the `IntentTaxonomy` entry:

```javascript
  { path: '/ai-monitoring', title: 'AI 模型监控', icon: 'Monitor' },
```

- [ ] **Step 4: Verify frontend compiles**

Run: `cd agent-admin-front && npx vite build --mode development 2>&1 | tail -10`
Expected: Build succeeds without errors

- [ ] **Step 5: Commit**

```bash
git add agent-admin-front/src/views/AiModelMonitoring.vue \
        agent-admin-front/src/router/index.js \
        agent-admin-front/src/layouts/AdminLayout.vue
git commit -m "feat(admin-front): add AI model monitoring page with charts and provider table"
```

---

## Post-Implementation: E2E Validation

After all 8 tasks are complete, perform end-to-end validation:

1. **Restart agent-api** (to pick up Flyway migration): `cd agent-api && mvn spring-boot:run`
2. **Verify table created**: `mysql -u meichen -pmeichen123 -e "DESCRIBE ai_call_logs;" meichen`
3. **Restart admin-backend**: `cd agent-admin-backend && mvn spring-boot:run`
4. **Verify admin API endpoints** with curl:
   ```bash
   curl -s -H "X-Admin-Token: admin-secret-2026" "http://localhost:8081/api/admin/metrics/ai-calls/summary?hours=24"
   curl -s -H "X-Admin-Token: admin-secret-2026" "http://localhost:8081/api/admin/metrics/ai-calls/by-provider?hours=24"
   curl -s -H "X-Admin-Token: admin-secret-2026" "http://localhost:8081/api/admin/metrics/ai-calls/timeline?hours=168"
   curl -s -H "X-Admin-Token: admin-secret-2026" "http://localhost:8081/api/admin/metrics/ai-calls/tokens?hours=168"
   ```
5. **Test Python instrumentation**: Trigger a workflow that calls LLM/VLM/embedding/image generation, then verify records appear in `ai_call_logs` table
6. **Verify frontend**: Navigate to `http://localhost:8082/ai-monitoring` in browser, verify all charts and table render
