# Sprint 4: RAG Metrics + Intent Quality Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add RAG search logging infrastructure and intent quality monitoring metrics to the admin dashboard.

**Architecture:** Python agent-core logs RAG searches via fire-and-forget HTTP to agent-api (same pattern as `@log_ai_call`). Agent-core also aggregates intent trace JSONL files into stats endpoints. Admin-backend reads from `rag_search_logs` table and proxies to agent-core for intent quality data. Frontend gets a new IntentQuality.vue page.

**Tech Stack:** Python 3.11 + FastAPI + httpx (agent-core), Java 17 + Spring Boot 3.2.5 + JPA + Flyway (agent-api, admin-backend), Vue 3 + Element Plus + ECharts (admin-front)

## Global Constraints

- LLM/VLM must use 智谱 API only; embedding must use local Ollama bge-m3
- Async tasks must use thread pools instead of direct new Thread() operations
- Python fire-and-forget logging must use asyncio.create_task with _pending_tasks set (same pattern as call_logger.py)
- Internal endpoints at `/api/v1/internal/**` and `/api/v1/admin/**` must have permitAll() security (already configured)
- Database must use MySQL; Flyway migrations follow V{date}__{description}.sql naming
- Read-only JPA entities in admin-backend map to tables created by agent-api, use getters only
- Spring Data JPA aggregate queries returning Object[] must use default-method wrapper pattern (extract first row from List<Object[]>)
- admin-backend WebClient calls to agent-core must have 2s connect timeout + 5s response timeout with graceful degradation
- Frontend uses `client` from `src/api/client.js` for API calls, ECharts for charts
- Configurable parameters: hours (default 24) for time-filtered queries, days (default 30) for trace analysis

---

## File Structure

### agent-core (Python)
- **Create:** `app/services/rag_logger.py` — async `log_rag_search()` function + `@log_rag_search_decorator`
- **Modify:** `app/services/knowledge_base.py` — add RAG logging calls to semantic_search, _fallback_search, structured_query
- **Create:** `app/api/endpoints/admin_metrics.py` — intent trace aggregation endpoints
- **Modify:** `app/api/app.py` (or equivalent router registration) — register admin_metrics router
- **Create:** `tests/services/test_rag_logger.py` — unit tests for log_rag_search
- **Create:** `tests/api/test_admin_metrics.py` — unit tests for intent trace stats endpoints

### agent-api (Java)
- **Create:** `src/main/resources/db/migration/V2026071203__create_rag_search_logs.sql` — Flyway migration
- **Create:** `src/main/java/com/meichen/orchestrator/entity/RagSearchLog.java` — JPA entity
- **Create:** `src/main/java/com/meichen/orchestrator/repository/RagSearchLogRepository.java` — repository with save method
- **Modify:** `src/main/java/com/meichen/orchestrator/controller/InternalLogController.java` — add POST /api/v1/internal/rag-search-logs endpoint
- **Create:** `src/test/java/com/meichen/orchestrator/repository/RagSearchLogRepositoryTest.java` — repository tests
- **Create:** `src/test/java/com/meichen/orchestrator/controller/InternalRagLogControllerTest.java` — controller tests

### agent-admin-backend (Java)
- **Create:** `src/main/java/com/meichen/admin/entity/RagSearchLogRead.java` — read-only entity
- **Create:** `src/main/java/com/meichen/admin/repository/RagSearchLogReadRepository.java` — aggregation queries
- **Create:** `src/main/java/com/meichen/admin/dto/RagOverviewDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/dto/RagTimelineDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/dto/RagZeroResultDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/service/RagMetricsService.java` — service with 4 methods
- **Create:** `src/main/java/com/meichen/admin/controller/RagMetricsController.java` — 4 endpoints
- **Create:** `src/main/java/com/meichen/admin/dto/IntentSourceDistributionDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/dto/ConfidenceDistributionDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/dto/CorrectionRateDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/dto/DialogueTurnDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/dto/AliasProposalStatsDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/service/IntentQualityService.java` — service with WebClient to agent-core
- **Create:** `src/main/java/com/meichen/admin/controller/IntentQualityController.java` — 5 endpoints
- **Create:** `src/test/java/com/meichen/admin/repository/RagSearchLogReadRepositoryTest.java` — repository tests
- **Create:** `src/test/java/com/meichen/admin/controller/RagMetricsControllerIntegrationTest.java` — controller tests
- **Create:** `src/test/java/com/meichen/admin/controller/IntentQualityControllerIntegrationTest.java` — controller tests

### agent-admin-front (Vue)
- **Create:** `src/views/IntentQuality.vue` — intent quality monitoring page
- **Modify:** `src/router/index.js` — add route
- **Modify:** `src/layouts/AdminLayout.vue` — add menu item

---

### Task 1: RAG Search Logs Table + Flyway Migration

**Files:**
- Create: `agent-api/src/main/resources/db/migration/V2026071203__create_rag_search_logs.sql`

**Interfaces:**
- Produces: `rag_search_logs` table with columns: id (BIGINT PK AUTO_INCREMENT), project_id (VARCHAR(36)), query_text (TEXT), search_type (VARCHAR(20) — semantic/structured/fallback), result_count (INT), duration_ms (INT), cache_hit (BOOLEAN DEFAULT FALSE), timed_out (BOOLEAN DEFAULT FALSE), created_at (DATETIME DEFAULT CURRENT_TIMESTAMP). Indexes on (search_type, created_at), (project_id), (result_count) for zero-result queries.

- [ ] **Step 1: Write the Flyway migration SQL**

```sql
-- V2026071203__create_rag_search_logs.sql
CREATE TABLE rag_search_logs (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    project_id VARCHAR(36),
    query_text TEXT NOT NULL,
    search_type VARCHAR(20) NOT NULL,
    result_count INT NOT NULL DEFAULT 0,
    duration_ms INT NOT NULL DEFAULT 0,
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
    timed_out BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_rag_search_type_created ON rag_search_logs (search_type, created_at);
CREATE INDEX idx_rag_search_project ON rag_search_logs (project_id);
CREATE INDEX idx_rag_search_result_count ON rag_search_logs (result_count);
```

- [ ] **Step 2: Verify migration applies**

Run: `cd agent-api && mvn flyway:info -Dflyway.url=jdbc:mysql://localhost:3306/meichen -Dflyway.user=meichen -Dflyway.password=meichen123 -Dflyway.locations=classpath:db/migration`
Expected: V2026071203 shows as pending

Run: `cd agent-api && mvn flyway:migrate -Dflyway.url=jdbc:mysql://localhost:3306/meichen -Dflyway.user=meichen -Dflyway.password=meichen123 -Dflyway.locations=classpath:db/migration`
Expected: V2026071203 applied successfully

Run: `mysql -u meichen -pmeichen123 -e "DESCRIBE rag_search_logs;" meichen`
Expected: Table with 9 columns and 3 indexes

- [ ] **Step 3: Commit**

```bash
git add agent-api/src/main/resources/db/migration/V2026071203__create_rag_search_logs.sql
git commit -m "feat(agent-api): add rag_search_logs table for RAG search instrumentation"
```

---

### Task 2: Java RagSearchLog Entity + Repository + Internal Endpoint

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/entity/RagSearchLog.java`
- Create: `agent-api/src/main/java/com/meichen/orchestrator/repository/RagSearchLogRepository.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/controller/InternalLogController.java`
- Create: `agent-api/src/test/java/com/meichen/orchestrator/repository/RagSearchLogRepositoryTest.java`
- Create: `agent-api/src/test/java/com/meichen/orchestrator/controller/InternalRagLogControllerTest.java`

**Interfaces:**
- Consumes: `rag_search_logs` table from Task 1
- Produces: `RagSearchLog` entity, `RagSearchLogRepository.save()`, `POST /api/v1/internal/rag-search-logs` endpoint accepting JSON body: `{projectId, queryText, searchType, resultCount, durationMs, cacheHit, timedOut}`

- [ ] **Step 1: Write RagSearchLog entity test**

```java
// RagSearchLogRepositoryTest.java
package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.RagSearchLog;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.test.context.ActiveProfiles;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@ActiveProfiles("test")
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
        repository.save(log);

        List<RagSearchLog> results = repository.findBySearchTypeAndCreatedAtAfter(
            "semantic", LocalDateTime.now().minusMinutes(1));
        assertThat(results).hasSize(1);
        assertThat(results.get(0).getQueryText()).isEqualTo("modern office design");
        assertThat(results.get(0).getResultCount()).isEqualTo(5);
    }

    @Test
    void countByCreatedAtAfter_returnsZeroForNoData() {
        long count = repository.countByCreatedAtAfter(LocalDateTime.now().minusDays(1));
        assertThat(count).isEqualTo(0);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-api && mvn test -Dtest=RagSearchLogRepositoryTest -q`
Expected: FAIL with "cannot find symbol class RagSearchLog"

- [ ] **Step 3: Write RagSearchLog entity**

```java
// RagSearchLog.java
package com.meichen.orchestrator.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import java.time.LocalDateTime;

@Entity
@Table(name = "rag_search_logs")
public class RagSearchLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "project_id", length = 36)
    private String projectId;

    @Column(name = "query_text", columnDefinition = "TEXT", nullable = false)
    private String queryText;

    @Column(name = "search_type", length = 20, nullable = false)
    private String searchType;

    @Column(name = "result_count", nullable = false)
    private Integer resultCount;

    @Column(name = "duration_ms", nullable = false)
    private Integer durationMs;

    @Column(name = "cache_hit", nullable = false)
    private Boolean cacheHit;

    @Column(name = "timed_out", nullable = false)
    private Boolean timedOut;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public String getProjectId() { return projectId; }
    public String getQueryText() { return queryText; }
    public String getSearchType() { return searchType; }
    public Integer getResultCount() { return resultCount; }
    public Integer getDurationMs() { return durationMs; }
    public Boolean getCacheHit() { return cacheHit; }
    public Boolean getTimedOut() { return timedOut; }
    public LocalDateTime getCreatedAt() { return createdAt; }

    public void setProjectId(String projectId) { this.projectId = projectId; }
    public void setQueryText(String queryText) { this.queryText = queryText; }
    public void setSearchType(String searchType) { this.searchType = searchType; }
    public void setResultCount(Integer resultCount) { this.resultCount = resultCount; }
    public void setDurationMs(Integer durationMs) { this.durationMs = durationMs; }
    public void setCacheHit(Boolean cacheHit) { this.cacheHit = cacheHit; }
    public void setTimedOut(Boolean timedOut) { this.timedOut = timedOut; }
}
```

- [ ] **Step 4: Write RagSearchLogRepository**

```java
// RagSearchLogRepository.java
package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.RagSearchLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface RagSearchLogRepository extends JpaRepository<RagSearchLog, Long> {

    List<RagSearchLog> findBySearchTypeAndCreatedAtAfter(String searchType, LocalDateTime since);

    long countByCreatedAtAfter(LocalDateTime since);
}
```

- [ ] **Step 5: Run repository test to verify it passes**

Run: `cd agent-api && mvn test -Dtest=RagSearchLogRepositoryTest -q`
Expected: PASS, 2 tests

- [ ] **Step 6: Write internal controller test**

```java
// InternalRagLogControllerTest.java
package com.meichen.orchestrator.controller;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class InternalRagLogControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void postRagSearchLog_returns200() throws Exception {
        String json = """
            {
                "projectId": "proj-1",
                "queryText": "modern office design",
                "searchType": "semantic",
                "resultCount": 5,
                "durationMs": 120,
                "cacheHit": false,
                "timedOut": false
            }
            """;
        mockMvc.perform(post("/api/v1/internal/rag-search-logs")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json))
            .andExpect(status().isOk());
    }

    @Test
    void postRagSearchLog_missingQueryText_returns400() throws Exception {
        String json = """
            {
                "searchType": "semantic",
                "resultCount": 5,
                "durationMs": 120,
                "cacheHit": false,
                "timedOut": false
            }
            """;
        mockMvc.perform(post("/api/v1/internal/rag-search-logs")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json))
            .andExpect(status().isBadRequest());
    }
}
```

- [ ] **Step 7: Add endpoint to InternalLogController**

Add to the existing `InternalLogController.java`:

```java
@PostMapping("/rag-search-logs")
public ResponseEntity<Void> receiveRagSearchLog(@RequestBody RagSearchLogRequest req) {
    RagSearchLog log = new RagSearchLog();
    log.setProjectId(req.projectId());
    log.setQueryText(req.queryText());
    log.setSearchType(req.searchType());
    log.setResultCount(req.resultCount());
    log.setDurationMs(req.durationMs());
    log.setCacheHit(req.cacheHit());
    log.setTimedOut(req.timedOut());
    ragSearchLogRepository.save(log);
    return ResponseEntity.ok().build();
}

public record RagSearchLogRequest(
    String projectId,
    String queryText,
    String searchType,
    int resultCount,
    int durationMs,
    boolean cacheHit,
    boolean timedOut
) {}
```

Inject `RagSearchLogRepository` into the controller's constructor.

- [ ] **Step 8: Run all tests**

Run: `cd agent-api && mvn test -q`
Expected: All tests pass (existing 59 + 4 new = 63)

- [ ] **Step 9: Commit**

```bash
git add agent-api/src/main/java/com/meichen/orchestrator/entity/RagSearchLog.java \
  agent-api/src/main/java/com/meichen/orchestrator/repository/RagSearchLogRepository.java \
  agent-api/src/main/java/com/meichen/orchestrator/controller/InternalLogController.java \
  agent-api/src/test/java/com/meichen/orchestrator/repository/RagSearchLogRepositoryTest.java \
  agent-api/src/test/java/com/meichen/orchestrator/controller/InternalRagLogControllerTest.java
git commit -m "feat(agent-api): add RagSearchLog entity, repository, and internal endpoint"
```

---

### Task 3: Python RAG Logger + Knowledge Base Instrumentation

**Files:**
- Create: `agent-core/app/services/rag_logger.py`
- Modify: `agent-core/app/services/knowledge_base.py` (add logging calls)
- Create: `agent-core/tests/services/test_rag_logger.py`

**Interfaces:**
- Consumes: agent-api `POST /api/v1/internal/rag-search-logs` endpoint from Task 2
- Produces: `async log_rag_search(project_id, query_text, search_type, result_count, duration_ms, cache_hit, timed_out)` fire-and-forget function

- [ ] **Step 1: Write rag_logger test**

```python
# test_rag_logger.py
"""Tests for RAG search logging."""
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.rag_logger import log_rag_search


@patch("app.services.rag_logger._send_rag_log", new_callable=AsyncMock)
async def test_log_rag_search_sends_correct_payload(mock_send):
    await log_rag_search(
        project_id="proj-1",
        query_text="modern office design",
        search_type="semantic",
        result_count=5,
        duration_ms=120,
        cache_hit=False,
        timed_out=False,
    )
    mock_send.assert_called_once_with(
        projectId="proj-1",
        queryText="modern office design",
        searchType="semantic",
        resultCount=5,
        durationMs=120,
        cacheHit=False,
        timedOut=False,
    )


@patch("app.services.rag_logger._send_rag_log", new_callable=AsyncMock)
async def test_log_rag_search_swallows_errors(mock_send):
    mock_send.side_effect = Exception("network error")
    # Should not raise
    await log_rag_search(
        project_id="proj-1",
        query_text="test",
        search_type="fallback",
        result_count=0,
        duration_ms=0,
        cache_hit=False,
        timed_out=True,
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-core && python3 -m pytest tests/services/test_rag_logger.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.rag_logger'"

- [ ] **Step 3: Write rag_logger.py**

```python
# rag_logger.py
"""RAG search logging for fire-and-forget instrumentation."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_pending_tasks: set = set()


async def _send_rag_log(**kwargs: Any) -> None:
    """Send a RAG search log record to agent-api. Swallows all errors."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(
                f"{settings.agent_api_base_url}/api/v1/internal/rag-search-logs",
                json=kwargs,
            )
    except Exception as e:
        logger.debug("Failed to send RAG search log: %s", e)


async def log_rag_search(
    *,
    project_id: str | None,
    query_text: str,
    search_type: str,
    result_count: int,
    duration_ms: int,
    cache_hit: bool = False,
    timed_out: bool = False,
) -> None:
    """Log a RAG search operation. Fire-and-forget, swallows all errors."""
    payload = {
        "projectId": project_id,
        "queryText": query_text,
        "searchType": search_type,
        "resultCount": result_count,
        "durationMs": duration_ms,
        "cacheHit": cache_hit,
        "timedOut": timed_out,
    }
    try:
        task = asyncio.create_task(_send_rag_log(**payload))
        _pending_tasks.add(task)
        task.add_done_callback(_pending_tasks.discard)
    except RuntimeError:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent-core && python3 -m pytest tests/services/test_rag_logger.py -v`
Expected: PASS, 2 tests

- [ ] **Step 5: Add RAG logging calls to knowledge_base.py**

Modify `semantic_search()` method — add timing and logging at the end:

```python
# At the top of knowledge_base.py, add import:
from app.services.rag_logger import log_rag_search

# In semantic_search(), wrap the existing try block with timing:
async def semantic_search(
    self,
    query: str,
    space_type: str | None = None,
    budget_level: str | None = None,
    top_k: int = 5,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    import time
    start = time.monotonic()
    search_type = "semantic"
    try:
        self._ensure_client()
        if self._milvus_available:
            try:
                # ... existing search logic ...
                results = self._client.search(...)
                # ... existing hit processing ...
                duration_ms = int((time.monotonic() - start) * 1000)
                await log_rag_search(
                    project_id=project_id,
                    query_text=query,
                    search_type=search_type,
                    result_count=len(hits),
                    duration_ms=duration_ms,
                    cache_hit=False,
                    timed_out=False,
                )
                return hits
            except Exception:
                # Fallback
                fallback_results = self._fallback_search(query, space_type, budget_level, top_k)
                duration_ms = int((time.monotonic() - start) * 1000)
                await log_rag_search(
                    project_id=project_id,
                    query_text=query,
                    search_type="fallback",
                    result_count=len(fallback_results),
                    duration_ms=duration_ms,
                    cache_hit=False,
                    timed_out=True,
                )
                return fallback_results
        else:
            results = self._fallback_search(query, space_type, budget_level, top_k)
            duration_ms = int((time.monotonic() - start) * 1000)
            await log_rag_search(
                project_id=project_id,
                query_text=query,
                search_type="fallback",
                result_count=len(results),
                duration_ms=duration_ms,
                cache_hit=False,
                timed_out=False,
            )
            return results
    except Exception:
        duration_ms = int((time.monotonic() - start) * 1000)
        await log_rag_search(
            project_id=project_id,
            query_text=query,
            search_type=search_type,
            result_count=0,
            duration_ms=duration_ms,
            cache_hit=False,
            timed_out=True,
        )
        return []
```

Also add `project_id` parameter to `_fallback_search` and `structured_query` with logging.

- [ ] **Step 6: Run all agent-core tests**

Run: `cd agent-core && python3 -m pytest tests/ -q`
Expected: All tests pass (existing 106 + 2 new = 108, minus any that break from signature change)

- [ ] **Step 7: Commit**

```bash
git add agent-core/app/services/rag_logger.py \
  agent-core/app/services/knowledge_base.py \
  agent-core/tests/services/test_rag_logger.py
git commit -m "feat(agent-core): add RAG search logging with fire-and-forget instrumentation"
```

---

### Task 4: Admin Backend — RagSearchLogRead Entity + Repository

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/entity/RagSearchLogRead.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/repository/RagSearchLogReadRepository.java`
- Create: `agent-admin-backend/src/test/java/com/meichen/admin/repository/RagSearchLogReadRepositoryTest.java`

**Interfaces:**
- Consumes: `rag_search_logs` table from Task 1
- Produces: `RagSearchLogRead` entity (read-only), `RagSearchLogReadRepository` with aggregation queries: `aggregateOverview(hours)`, `groupByDay(hours)`, `findZeroResults(days, limit)`

- [ ] **Step 1: Write repository test**

```java
// RagSearchLogReadRepositoryTest.java
package com.meichen.admin.repository;

import com.meichen.admin.entity.RagSearchLogRead;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.test.context.ActiveProfiles;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@ActiveProfiles("test")
class RagSearchLogReadRepositoryTest {

    @Autowired
    private RagSearchLogReadRepository repository;

    @Test
    void aggregateOverview_returnsStats() {
        // Test data is inserted via data.sql or manually
        Object[] result = repository.aggregateOverview(LocalDateTime.now().minusDays(1));
        assertThat(result).isNotNull();
    }

    @Test
    void findZeroResults_returnsEmptyQueries() {
        List<Object[]> results = repository.findZeroResults(LocalDateTime.now().minusDays(1), 10);
        assertThat(results).isNotNull();
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-admin-backend && mvn test -Dtest=RagSearchLogReadRepositoryTest -q`
Expected: FAIL

- [ ] **Step 3: Write RagSearchLogRead entity**

```java
// RagSearchLogRead.java
package com.meichen.admin.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import java.time.LocalDateTime;

@Entity
@Table(name = "rag_search_logs")
public class RagSearchLogRead {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "project_id", length = 36)
    private String projectId;

    @Column(name = "query_text", columnDefinition = "TEXT")
    private String queryText;

    @Column(name = "search_type", length = 20)
    private String searchType;

    @Column(name = "result_count")
    private Integer resultCount;

    @Column(name = "duration_ms")
    private Integer durationMs;

    @Column(name = "cache_hit")
    private Boolean cacheHit;

    @Column(name = "timed_out")
    private Boolean timedOut;

    @CreationTimestamp
    @Column(name = "created_at", insertable = false, updatable = false)
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public String getProjectId() { return projectId; }
    public String getQueryText() { return queryText; }
    public String getSearchType() { return searchType; }
    public Integer getResultCount() { return resultCount; }
    public Integer getDurationMs() { return durationMs; }
    public Boolean getCacheHit() { return cacheHit; }
    public Boolean getTimedOut() { return timedOut; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
```

- [ ] **Step 4: Write RagSearchLogReadRepository**

```java
// RagSearchLogReadRepository.java
package com.meichen.admin.repository;

import com.meichen.admin.entity.RagSearchLogRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface RagSearchLogReadRepository extends JpaRepository<RagSearchLogRead, Long> {

    @Query("SELECT COUNT(r), COALESCE(AVG(r.resultCount), 0.0), COALESCE(AVG(r.durationMs), 0.0), " +
           "SUM(CASE WHEN r.cacheHit = true THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN r.timedOut = true THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN r.searchType = 'fallback' THEN 1 ELSE 0 END) " +
           "FROM RagSearchLogRead r WHERE r.createdAt >= :since")
    List<Object[]> findOverviewRaw(@Param("since") LocalDateTime since);

    default Object[] aggregateOverview(LocalDateTime since) {
        List<Object[]> rows = findOverviewRaw(since);
        if (rows.isEmpty() || rows.get(0)[0] == null) {
            return new Object[]{0L, 0.0, 0.0, 0L, 0L, 0L};
        }
        return rows.get(0);
    }

    @Query("SELECT FUNCTION('DATE', r.createdAt), COUNT(r), COALESCE(AVG(r.durationMs), 0.0), " +
           "SUM(CASE WHEN r.cacheHit = true THEN 1 ELSE 0 END) * 1.0 / COUNT(r) " +
           "FROM RagSearchLogRead r WHERE r.createdAt >= :since " +
           "GROUP BY FUNCTION('DATE', r.createdAt) ORDER BY FUNCTION('DATE', r.createdAt)")
    List<Object[]> groupByDay(@Param("since") LocalDateTime since);

    @Query("SELECT r.queryText, COUNT(r), MAX(r.createdAt) " +
           "FROM RagSearchLogRead r WHERE r.createdAt >= :since AND r.resultCount = 0 " +
           "GROUP BY r.queryText ORDER BY COUNT(r) DESC")
    List<Object[]> findZeroResults(@Param("since") LocalDateTime since);
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd agent-admin-backend && mvn test -Dtest=RagSearchLogReadRepositoryTest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent-admin-backend/src/main/java/com/meichen/admin/entity/RagSearchLogRead.java \
  agent-admin-backend/src/main/java/com/meichen/admin/repository/RagSearchLogReadRepository.java \
  agent-admin-backend/src/test/java/com/meichen/admin/repository/RagSearchLogReadRepositoryTest.java
git commit -m "feat(admin): add RagSearchLogRead entity and repository for RAG metrics"
```

---

### Task 5: Admin Backend — RagMetrics Service + DTOs + Controller

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/RagOverviewDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/RagTimelineDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/RagZeroResultDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/service/RagMetricsService.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/controller/RagMetricsController.java`
- Create: `agent-admin-backend/src/test/java/com/meichen/admin/controller/RagMetricsControllerIntegrationTest.java`

**Interfaces:**
- Consumes: `RagSearchLogReadRepository` from Task 4
- Produces: 4 API endpoints at `/api/admin/metrics/rag`: GET /overview, GET /timeline, GET /inventory, GET /zero-results

- [ ] **Step 1: Write DTOs**

```java
// RagOverviewDTO.java
package com.meichen.admin.dto;
public record RagOverviewDTO(
    long totalSearches,
    double avgResultCount,
    double avgLatencyMs,
    double cacheHitRate,
    long timeoutCount,
    double fallbackRate
) {}

// RagTimelineDTO.java
package com.meichen.admin.dto;
public record RagTimelineDTO(
    String date,
    long searchCount,
    double avgLatencyMs,
    double cacheHitRate
) {}

// RagZeroResultDTO.java
package com.meichen.admin.dto;
public record RagZeroResultDTO(
    long totalZeroResultSearches,
    double zeroResultRate,
    java.util.List<ZeroResultQuery> topQueries
) {
    public record ZeroResultQuery(String queryText, long searchCount, String lastSearchedAt) {}
}
```

- [ ] **Step 2: Write RagMetricsService**

```java
// RagMetricsService.java
package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.RagSearchLogReadRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class RagMetricsService {

    private final RagSearchLogReadRepository repository;

    public RagMetricsService(RagSearchLogReadRepository repository) {
        this.repository = repository;
    }

    public RagOverviewDTO getOverview(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        Object[] row = repository.aggregateOverview(since);
        long total = ((Number) row[0]).longValue();
        double avgResultCount = ((Number) row[1]).doubleValue();
        double avgLatency = ((Number) row[2]).doubleValue();
        long cacheHits = ((Number) row[3]).longValue();
        long timeouts = ((Number) row[4]).longValue();
        long fallbacks = ((Number) row[5]).longValue();

        return new RagOverviewDTO(
            total,
            avgResultCount,
            avgLatency,
            total > 0 ? (double) cacheHits / total : 0.0,
            timeouts,
            total > 0 ? (double) fallbacks / total : 0.0
        );
    }

    public List<RagTimelineDTO> getTimeline(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = repository.groupByDay(since);
        List<RagTimelineDTO> result = new ArrayList<>();
        for (Object[] row : rows) {
            result.add(new RagTimelineDTO(
                row[0].toString(),
                ((Number) row[1]).longValue(),
                ((Number) row[2]).doubleValue(),
                ((Number) row[3]).doubleValue()
            ));
        }
        return result;
    }

    public RagZeroResultDTO getZeroResults(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<Object[]> rows = repository.findZeroResults(since);
        long totalZero = rows.stream().mapToLong(r -> ((Number) r[1]).longValue()).sum();

        Object[] overview = repository.aggregateOverview(since);
        long totalSearches = ((Number) overview[0]).longValue();

        List<RagZeroResultDTO.ZeroResultQuery> topQueries = new ArrayList<>();
        for (Object[] row : rows.stream().limit(10).toList()) {
            topQueries.add(new RagZeroResultDTO.ZeroResultQuery(
                (String) row[0],
                ((Number) row[1]).longValue(),
                row[2].toString()
            ));
        }

        return new RagZeroResultDTO(
            totalZero,
            totalSearches > 0 ? (double) totalZero / totalSearches : 0.0,
            topQueries
        );
    }

    public Object getInventory() {
        // Query Milvus collection stats via agent-core or direct DB count
        // For now, return placeholder structure
        return new java.util.LinkedHashMap<>();
    }
}
```

- [ ] **Step 3: Write RagMetricsController**

```java
// RagMetricsController.java
package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.RagMetricsService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/metrics/rag")
public class RagMetricsController {

    private final RagMetricsService service;

    public RagMetricsController(RagMetricsService service) {
        this.service = service;
    }

    @GetMapping("/overview")
    public RagOverviewDTO getOverview(@RequestParam(defaultValue = "24") int hours) {
        return service.getOverview(hours);
    }

    @GetMapping("/timeline")
    public List<RagTimelineDTO> getTimeline(@RequestParam(defaultValue = "168") int hours) {
        return service.getTimeline(hours);
    }

    @GetMapping("/inventory")
    public Object getInventory() {
        return service.getInventory();
    }

    @GetMapping("/zero-results")
    public RagZeroResultDTO getZeroResults(@RequestParam(defaultValue = "30") int days) {
        return service.getZeroResults(days);
    }
}
```

- [ ] **Step 4: Write integration test**

```java
// RagMetricsControllerIntegrationTest.java
package com.meichen.admin.controller;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class RagMetricsControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void getOverview_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/rag/overview")
                .header("X-Admin-Token", "admin-secret-2026"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalSearches").exists())
            .andExpect(jsonPath("$.avgLatencyMs").exists());
    }

    @Test
    void getTimeline_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/rag/timeline")
                .header("X-Admin-Token", "admin-secret-2026"))
            .andExpect(status().isOk());
    }

    @Test
    void getZeroResults_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/rag/zero-results")
                .header("X-Admin-Token", "admin-secret-2026"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalZeroResultSearches").exists());
    }

    @Test
    void getOverview_noToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/rag/overview"))
            .andExpect(status().isUnauthorized());
    }
}
```

- [ ] **Step 5: Run all tests**

Run: `cd agent-admin-backend && mvn test -q`
Expected: All tests pass (existing 82 + 6 new = 88)

- [ ] **Step 6: Commit**

```bash
git add agent-admin-backend/src/main/java/com/meichen/admin/dto/Rag*.java \
  agent-admin-backend/src/main/java/com/meichen/admin/service/RagMetricsService.java \
  agent-admin-backend/src/main/java/com/meichen/admin/controller/RagMetricsController.java \
  agent-admin-backend/src/test/java/com/meichen/admin/controller/RagMetricsControllerIntegrationTest.java
git commit -m "feat(admin): add RAG metrics API with overview, timeline, and zero-results endpoints"
```

---

### Task 6: Python Intent Trace Aggregation Endpoints

**Files:**
- Create: `agent-core/app/api/endpoints/admin_metrics.py`
- Modify: `agent-core/app/api/app.py` (or wherever routers are registered) — register admin_metrics router
- Create: `agent-core/tests/api/test_admin_metrics.py`

**Interfaces:**
- Consumes: IntentTraceRecorder JSONL files at `agent-core/data/intent_traces/*.jsonl`
- Produces: `GET /api/v1/admin/intent-traces/stats?days=30` returning `{sources: [{source, count, percentage}], confidence: [{bucket, count, percentage}], lowConfidenceRate: float}`, `GET /api/v1/admin/intent-traces/correction-stats?days=30` returning `{fields: [{field, totalRecognitions, correctionCount, correctionRate, topCorrectedValues: [{original, count}]}]}`

- [ ] **Step 1: Write endpoint test**

```python
# test_admin_metrics.py
"""Tests for admin metrics endpoints."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def trace_data(tmp_path):
    """Create temporary trace files for testing."""
    trace_file = tmp_path / "2026-07-12.jsonl"
    records = [
        {
            "trace_id": "t1",
            "project_id": "p1",
            "timestamp": "2026-07-12T10:00:00+00:00",
            "validated": {
                "space_type": {"name": "space_type", "value": "office", "source": "llm", "confidence": 0.9},
                "style": {"name": "style", "value": "modern", "source": "exact", "confidence": 0.95},
            },
            "llm_output": {"space_type": "office"},
            "merged_output": {"space_type": "office"},
        },
        {
            "trace_id": "t2",
            "project_id": "p2",
            "timestamp": "2026-07-12T11:00:00+00:00",
            "validated": {
                "space_type": {"name": "space_type", "value": "retail", "source": "alias", "confidence": 0.5},
                "style": {"name": "style", "value": "minimalist", "source": "fuzzy", "confidence": 0.6},
            },
            "llm_output": {"space_type": "shop"},
            "merged_output": {"space_type": "retail"},
        },
    ]
    with trace_file.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return tmp_path


def test_intent_traces_stats(trace_data):
    from app.api.endpoints.admin_metrics import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    with patch("app.api.endpoints.admin_metrics._get_trace_dir", return_value=trace_data):
        client = TestClient(app)
        response = client.get("/api/v1/admin/intent-traces/stats?days=30")

    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert "confidence" in data
    assert "lowConfidenceRate" in data
    # 4 field sources across 2 traces
    total_sources = sum(s["count"] for s in data["sources"])
    assert total_sources == 4


def test_intent_traces_correction_stats(trace_data):
    from app.api.endpoints.admin_metrics import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    with patch("app.api.endpoints.admin_metrics._get_trace_dir", return_value=trace_data):
        client = TestClient(app)
        response = client.get("/api/v1/admin/intent-traces/correction-stats?days=30")

    assert response.status_code == 200
    data = response.json()
    assert "fields" in data
    # space_type was corrected in trace t2 (llm_output: "shop" -> validated: "retail")
    space_type_field = next(f for f in data["fields"] if f["field"] == "space_type")
    assert space_type_field["correctionCount"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-core && python3 -m pytest tests/api/test_admin_metrics.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write admin_metrics.py endpoint**

```python
# admin_metrics.py
"""Admin metrics endpoints for intent trace aggregation."""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-metrics"])

_TRACE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "intent_traces"

_CONFIDENCE_BUCKETS = [
    (0.0, 0.3, "0-0.3"),
    (0.3, 0.5, "0.3-0.5"),
    (0.5, 0.7, "0.5-0.7"),
    (0.7, 0.85, "0.7-0.85"),
    (0.85, 1.01, "0.85-1.0"),
]

_INTENT_FIELDS = ["space_type", "points", "budget", "style", "material_restrictions"]


def _get_trace_dir() -> Path:
    return _TRACE_DIR


def _read_traces(days: int) -> list[dict[str, Any]]:
    """Read JSONL trace files from the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    trace_dir = _get_trace_dir()
    if not trace_dir.exists():
        return []

    records: list[dict[str, Any]] = []
    for path in sorted(trace_dir.glob("*.jsonl"), reverse=True):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    ts = datetime.fromisoformat(record.get("timestamp", ""))
                    if ts >= cutoff:
                        records.append(record)
                except (json.JSONDecodeError, ValueError):
                    continue
    return records


def _extract_fields(validated: dict[str, Any]) -> list[tuple[str, str, float]]:
    """Extract (field_name, source, confidence) from validated intent."""
    result = []
    if not validated:
        return result
    for field_name in _INTENT_FIELDS:
        field_val = validated.get(field_name)
        if field_val is None:
            continue
        if isinstance(field_val, list):
            for item in field_val:
                if isinstance(item, dict):
                    result.append((
                        field_name,
                        item.get("source", "unknown"),
                        float(item.get("confidence", 0.0)),
                    ))
        elif isinstance(field_val, dict):
            result.append((
                field_name,
                field_val.get("source", "unknown"),
                float(field_val.get("confidence", 0.0)),
            ))
    return result


@router.get("/intent-traces/stats")
async def get_intent_trace_stats(days: int = Query(30, ge=1, le=365)):
    """Aggregate source distribution and confidence distribution from intent traces."""
    records = _read_traces(days)

    source_counter: Counter = Counter()
    confidence_counter: Counter = Counter()
    total_fields = 0
    low_confidence_count = 0

    for record in records:
        validated = record.get("validated", {})
        fields = _extract_fields(validated)
        for _field_name, source, confidence in fields:
            source_counter[source] += 1
            total_fields += 1
            if confidence < 0.7:
                low_confidence_count += 1
            for lo, hi, label in _CONFIDENCE_BUCKETS:
                if lo <= confidence < hi:
                    confidence_counter[label] += 1
                    break

    sources = [
        {"source": s, "count": c, "percentage": (c / total_fields * 100) if total_fields > 0 else 0.0}
        for s, c in source_counter.most_common()
    ]

    confidence = [
        {"bucket": label, "count": confidence_counter.get(label, 0),
         "percentage": (confidence_counter.get(label, 0) / total_fields * 100) if total_fields > 0 else 0.0}
        for _, _, label in _CONFIDENCE_BUCKETS
    ]

    return {
        "sources": sources,
        "confidence": confidence,
        "lowConfidenceRate": (low_confidence_count / total_fields) if total_fields > 0 else 0.0,
    }


@router.get("/intent-traces/correction-stats")
async def get_intent_trace_correction_stats(days: int = Query(30, ge=1, le=365)):
    """Aggregate per-field correction rates from intent traces."""
    records = _read_traces(days)

    field_stats: dict[str, dict[str, Any]] = {}

    for record in records:
        validated = record.get("validated", {})
        llm_output = record.get("llm_output", {})
        merged_output = record.get("merged_output", {})

        for field_name in _INTENT_FIELDS:
            if field_name not in field_stats:
                field_stats[field_name] = {
                    "total": 0,
                    "corrected": 0,
                    "corrections": Counter(),
                }

            field_val = validated.get(field_name)
            if field_val is None:
                continue

            field_stats[field_name]["total"] += 1

            # Get the validated value
            if isinstance(field_val, dict):
                validated_value = str(field_val.get("value", ""))
            elif isinstance(field_val, list):
                validated_value = str([item.get("value", "") if isinstance(item, dict) else str(item) for item in field_val])
            else:
                validated_value = str(field_val)

            # Get the LLM output value
            llm_value = str(llm_output.get(field_name, ""))

            # Check if corrected (LLM output differs from validated)
            if llm_value and llm_value != validated_value:
                field_stats[field_name]["corrected"] += 1
                field_stats[field_name]["corrections"][llm_value] += 1

    fields = []
    for field_name, stats in field_stats.items():
        total = stats["total"]
        corrected = stats["corrected"]
        top_corrected = [
            {"original": val, "count": cnt}
            for val, cnt in stats["corrections"].most_common(5)
        ]
        fields.append({
            "field": field_name,
            "totalRecognitions": total,
            "correctionCount": corrected,
            "correctionRate": (corrected / total * 100) if total > 0 else 0.0,
            "topCorrectedValues": top_corrected,
        })

    return {"fields": fields}
```

- [ ] **Step 4: Register router in app.py**

Find the router registration in `agent-core/app/api/app.py` (or equivalent) and add:

```python
from app.api.endpoints.admin_metrics import router as admin_metrics_router
app.include_router(admin_metrics_router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd agent-core && python3 -m pytest tests/api/test_admin_metrics.py -v`
Expected: PASS, 2 tests

- [ ] **Step 6: Run all agent-core tests**

Run: `cd agent-core && python3 -m pytest tests/ -q`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add agent-core/app/api/endpoints/admin_metrics.py \
  agent-core/app/api/app.py \
  agent-core/tests/api/test_admin_metrics.py
git commit -m "feat(agent-core): add intent trace aggregation endpoints for admin metrics"
```

---

### Task 7: Admin Backend — IntentQuality Service + Controller

**Files:**
- Create: 5 DTO records (IntentSourceDistributionDTO, ConfidenceDistributionDTO, CorrectionRateDTO, DialogueTurnDTO, AliasProposalStatsDTO)
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/service/IntentQualityService.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/controller/IntentQualityController.java`
- Create: `agent-admin-backend/src/test/java/com/meichen/admin/controller/IntentQualityControllerIntegrationTest.java`

**Interfaces:**
- Consumes: agent-core `GET /api/v1/admin/intent-traces/stats` and `GET /api/v1/admin/intent-traces/correction-stats` from Task 6, `FeedbackRead` entity for correction rate and dialogue turns, `IntentTaxonomyAdminService` for alias proposal stats
- Produces: 5 endpoints at `/api/admin/metrics/intent-quality`: GET /sources, GET /confidence, GET /correction-rate, GET /dialogue-turns, GET /alias-proposals

- [ ] **Step 1: Write DTOs**

```java
// IntentSourceDistributionDTO.java
package com.meichen.admin.dto;
public record IntentSourceDistributionDTO(
    String source, long count, double percentage
) {}

// ConfidenceDistributionDTO.java
package com.meichen.admin.dto;
public record ConfidenceDistributionDTO(
    String bucket, long count, double percentage,
    double lowConfidenceRate
) {}

// CorrectionRateDTO.java
package com.meichen.admin.dto;
public record CorrectionRateDTO(
    String field, long totalRecognitions, long correctionCount,
    double correctionRate, java.util.List<TopCorrectedValue> topCorrectedValues
) {
    public record TopCorrectedValue(String original, long count) {}
}

// DialogueTurnDTO.java
package com.meichen.admin.dto;
public record DialogueTurnDTO(
    String turnRange, long count, double percentage,
    double avgTurns, double medianTurns
) {}

// AliasProposalStatsDTO.java
package com.meichen.admin.dto;
public record AliasProposalStatsDTO(
    long totalProposals, long pendingCount, long appliedCount, double rejectionRate
) {}
```

- [ ] **Step 2: Write IntentQualityService**

```java
// IntentQualityService.java
package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.meichen.admin.repository.SessionMessageReadRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;

@Service
public class IntentQualityService {

    private final WebClient webClient;
    private final ObjectMapper objectMapper;
    private final FeedbackReadRepository feedbackRepository;
    private final SessionMessageReadRepository sessionMessageRepository;

    public IntentQualityService(
            @Value("${agent-core.base-url:http://localhost:8000}") String agentCoreBaseUrl,
            FeedbackReadRepository feedbackRepository,
            SessionMessageReadRepository sessionMessageRepository) {
        this.webClient = WebClient.builder()
            .baseUrl(agentCoreBaseUrl)
            .build();
        this.objectMapper = new ObjectMapper();
        this.feedbackRepository = feedbackRepository;
        this.sessionMessageRepository = sessionMessageRepository;
    }

    @SuppressWarnings("unchecked")
    public List<IntentSourceDistributionDTO> getSources(int days) {
        try {
            String json = webClient.get()
                .uri("/api/v1/admin/intent-traces/stats?days=" + days)
                .retrieve()
                .bodyToMono(String.class)
                .block(Duration.ofSeconds(5));
            Map<String, Object> response = objectMapper.readValue(json, new TypeReference<>() {});
            List<Map<String, Object>> sources = (List<Map<String, Object>>) response.get("sources");
            List<IntentSourceDistributionDTO> result = new ArrayList<>();
            for (Map<String, Object> s : sources) {
                result.add(new IntentSourceDistributionDTO(
                    (String) s.get("source"),
                    ((Number) s.get("count")).longValue(),
                    ((Number) s.get("percentage")).doubleValue()
                ));
            }
            return result;
        } catch (Exception e) {
            return Collections.emptyList();
        }
    }

    @SuppressWarnings("unchecked")
    public ConfidenceDistributionDTO getConfidence(int days) {
        try {
            String json = webClient.get()
                .uri("/api/v1/admin/intent-traces/stats?days=" + days)
                .retrieve()
                .bodyToMono(String.class)
                .block(Duration.ofSeconds(5));
            Map<String, Object> response = objectMapper.readValue(json, new TypeReference<>() {});
            List<Map<String, Object>> confidenceBuckets = (List<Map<String, Object>>) response.get("confidence");
            double lowConfidenceRate = ((Number) response.get("lowConfidenceRate")).doubleValue();

            // Return aggregated confidence distribution
            // For the DTO, we return the first bucket as representative and include lowConfidenceRate
            // The frontend will display all buckets from the raw response
            // Actually, let's return a combined structure
            StringBuilder buckets = new StringBuilder();
            for (Map<String, Object> b : confidenceBuckets) {
                buckets.append(b.get("bucket")).append(":").append(b.get("count")).append(";");
            }
            return new ConfidenceDistributionDTO(buckets.toString(), 0, 0.0, lowConfidenceRate);
        } catch (Exception e) {
            return new ConfidenceDistributionDTO("", 0, 0.0, 0.0);
        }
    }

    @SuppressWarnings("unchecked")
    public List<CorrectionRateDTO> getCorrectionRate(int days) {
        // Try agent-core correction stats first
        try {
            String json = webClient.get()
                .uri("/api/v1/admin/intent-traces/correction-stats?days=" + days)
                .retrieve()
                .bodyToMono(String.class)
                .block(Duration.ofSeconds(5));
            Map<String, Object> response = objectMapper.readValue(json, new TypeReference<>() {});
            List<Map<String, Object>> fields = (List<Map<String, Object>>) response.get("fields");
            List<CorrectionRateDTO> result = new ArrayList<>();
            for (Map<String, Object> f : fields) {
                List<Map<String, Object>> topValues = (List<Map<String, Object>>) f.get("topCorrectedValues");
                List<CorrectionRateDTO.TopCorrectedValue> topCorrected = new ArrayList<>();
                if (topValues != null) {
                    for (Map<String, Object> v : topValues) {
                        topCorrected.add(new CorrectionRateDTO.TopCorrectedValue(
                            (String) v.get("original"),
                            ((Number) v.get("count")).longValue()
                        ));
                    }
                }
                result.add(new CorrectionRateDTO(
                    (String) f.get("field"),
                    ((Number) f.get("totalRecognitions")).longValue(),
                    ((Number) f.get("correctionCount")).longValue(),
                    ((Number) f.get("correctionRate")).doubleValue(),
                    topCorrected
                ));
            }
            return result;
        } catch (Exception e) {
            return Collections.emptyList();
        }
    }

    public DialogueTurnDTO getDialogueTurns(int days) {
        // Query session_messages to count turns per project
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        // This uses existing SessionMessageReadRepository or a new query
        // For now, return placeholder
        return new DialogueTurnDTO("N/A", 0, 0.0, 0.0, 0.0);
    }

    public AliasProposalStatsDTO getAliasProposalStats() {
        // Query intent_taxonomy for alias proposal stats
        // This uses existing IntentTaxonomyAdminService data
        return new AliasProposalStatsDTO(0, 0, 0, 0.0);
    }
}
```

- [ ] **Step 3: Write IntentQualityController**

```java
// IntentQualityController.java
package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.IntentQualityService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/metrics/intent-quality")
public class IntentQualityController {

    private final IntentQualityService service;

    public IntentQualityController(IntentQualityService service) {
        this.service = service;
    }

    @GetMapping("/sources")
    public List<IntentSourceDistributionDTO> getSources(@RequestParam(defaultValue = "30") int days) {
        return service.getSources(days);
    }

    @GetMapping("/confidence")
    public ConfidenceDistributionDTO getConfidence(@RequestParam(defaultValue = "30") int days) {
        return service.getConfidence(days);
    }

    @GetMapping("/correction-rate")
    public List<CorrectionRateDTO> getCorrectionRate(@RequestParam(defaultValue = "30") int days) {
        return service.getCorrectionRate(days);
    }

    @GetMapping("/dialogue-turns")
    public DialogueTurnDTO getDialogueTurns(@RequestParam(defaultValue = "30") int days) {
        return service.getDialogueTurns(days);
    }

    @GetMapping("/alias-proposals")
    public AliasProposalStatsDTO getAliasProposalStats() {
        return service.getAliasProposalStats();
    }
}
```

- [ ] **Step 4: Write integration test**

```java
// IntentQualityControllerIntegrationTest.java
package com.meichen.admin.controller;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class IntentQualityControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void getSources_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/intent-quality/sources")
                .header("X-Admin-Token", "admin-secret-2026"))
            .andExpect(status().isOk());
    }

    @Test
    void getConfidence_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/intent-quality/confidence")
                .header("X-Admin-Token", "admin-secret-2026"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.lowConfidenceRate").exists());
    }

    @Test
    void getCorrectionRate_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/intent-quality/correction-rate")
                .header("X-Admin-Token", "admin-secret-2026"))
            .andExpect(status().isOk());
    }

    @Test
    void getDialogueTurns_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/intent-quality/dialogue-turns")
                .header("X-Admin-Token", "admin-secret-2026"))
            .andExpect(status().isOk());
    }

    @Test
    void getAliasProposals_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/intent-quality/alias-proposals")
                .header("X-Admin-Token", "admin-secret-2026"))
            .andExpect(status().isOk());
    }

    @Test
    void getSources_noToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/intent-quality/sources"))
            .andExpect(status().isUnauthorized());
    }
}
```

- [ ] **Step 5: Run all tests**

Run: `cd agent-admin-backend && mvn test -q`
Expected: All tests pass (existing 88 + 6 new = 94)

- [ ] **Step 6: Commit**

```bash
git add agent-admin-backend/src/main/java/com/meichen/admin/dto/Intent*.java \
  agent-admin-backend/src/main/java/com/meichen/admin/dto/Confidence*.java \
  agent-admin-backend/src/main/java/com/meichen/admin/dto/CorrectionRate*.java \
  agent-admin-backend/src/main/java/com/meichen/admin/dto/DialogueTurn*.java \
  agent-admin-backend/src/main/java/com/meichen/admin/dto/AliasProposal*.java \
  agent-admin-backend/src/main/java/com/meichen/admin/service/IntentQualityService.java \
  agent-admin-backend/src/main/java/com/meichen/admin/controller/IntentQualityController.java \
  agent-admin-backend/src/test/java/com/meichen/admin/controller/IntentQualityControllerIntegrationTest.java
git commit -m "feat(admin): add intent quality metrics API with 5 endpoints"
```

---

### Task 8: Frontend — IntentQuality.vue Page

**Files:**
- Create: `agent-admin-front/src/views/IntentQuality.vue`
- Modify: `agent-admin-front/src/router/index.js` — add route
- Modify: `agent-admin-front/src/layouts/AdminLayout.vue` — add menu item

**Interfaces:**
- Consumes: 5 API endpoints from Task 7 at `/api/admin/metrics/intent-quality/*`
- Produces: IntentQuality.vue page with source distribution pie chart, confidence distribution histogram, correction rate bar chart, dialogue turns distribution, alias proposal cards

- [ ] **Step 1: Write IntentQuality.vue**

Create the Vue page with:
- Source distribution pie chart (ECharts)
- Confidence distribution histogram (ECharts bar chart)
- Correction rate by field bar chart with top corrected values table
- Dialogue turns distribution bar chart
- Alias proposal statistics cards

```vue
<template>
  <div class="intent-quality">
    <el-row :gutter="20" v-loading="loading">
      <!-- Source Distribution -->
      <el-col :span="12">
        <el-card>
          <template #header>识别来源分布</template>
          <div ref="sourceChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>

      <!-- Confidence Distribution -->
      <el-col :span="12">
        <el-card>
          <template #header>
            置信度分布
            <el-tag v-if="confidenceData.lowConfidenceRate > 0.3" type="danger" size="small">
              低置信度: {{ (confidenceData.lowConfidenceRate * 100).toFixed(1) }}%
            </el-tag>
          </template>
          <div ref="confidenceChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- Correction Rate -->
      <el-col :span="14">
        <el-card>
          <template #header>字段纠正率</template>
          <div ref="correctionChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>

      <!-- Alias Proposals -->
      <el-col :span="10">
        <el-card>
          <template #header>别名学习统计</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="总提案数">{{ aliasStats.totalProposals }}</el-descriptions-item>
            <el-descriptions-item label="待处理">{{ aliasStats.pendingCount }}</el-descriptions-item>
            <el-descriptions-item label="已应用">{{ aliasStats.appliedCount }}</el-descriptions-item>
            <el-descriptions-item label="拒绝率">{{ (aliasStats.rejectionRate * 100).toFixed(1) }}%</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- Correction Details Table -->
    <el-card style="margin-top: 20px;" v-if="correctionData.length > 0">
      <template #header>纠正详情</template>
      <el-table :data="correctionData" stripe>
        <el-table-column prop="field" label="字段" width="150" />
        <el-table-column prop="totalRecognitions" label="总识别数" width="120" />
        <el-table-column prop="correctionCount" label="纠正数" width="100" />
        <el-table-column prop="correctionRate" label="纠正率" width="100">
          <template #default="{ row }">{{ row.correctionRate.toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column label="最常被纠正的值">
          <template #default="{ row }">
            <el-tag v-for="v in row.topCorrectedValues" :key="v.original" size="small" style="margin: 2px;">
              {{ v.original }} ({{ v.count }})
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import client from '../api/client'
import * as echarts from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([PieChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const loading = ref(false)
const sourceChartRef = ref(null)
const confidenceChartRef = ref(null)
const correctionChartRef = ref(null)
const confidenceData = ref({ lowConfidenceRate: 0 })
const correctionData = ref([])
const aliasStats = ref({ totalProposals: 0, pendingCount: 0, appliedCount: 0, rejectionRate: 0 })

let sourceChart = null
let confidenceChart = null
let correctionChart = null

async function loadSources() {
  const res = await client.get('/api/admin/metrics/intent-quality/sources?days=30')
  sourceChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: res.data.map(s => ({ name: s.source, value: s.count })),
    }],
  })
}

async function loadConfidence() {
  const res = await client.get('/api/admin/metrics/intent-quality/confidence?days=30')
  confidenceData.value = res.data
  // Parse bucket string back to chart data
  const buckets = res.data.bucket ? res.data.bucket.split(';').filter(Boolean).map(b => {
    const [label, count] = b.split(':')
    return { label, value: parseInt(count) }
  }) : []
  confidenceChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: buckets.map(b => b.label) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: buckets.map(b => b.value), itemStyle: { color: '#409eff' } }],
  })
}

async function loadCorrectionRate() {
  const res = await client.get('/api/admin/metrics/intent-quality/correction-rate?days=30')
  correctionData.value = res.data
  correctionChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: res.data.map(d => d.field) },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [{
      type: 'bar',
      data: res.data.map(d => d.correctionRate),
      itemStyle: { color: '#e6a23c' },
      label: { show: true, position: 'top', formatter: '{c}%' },
    }],
  })
}

async function loadAliasStats() {
  const res = await client.get('/api/admin/metrics/intent-quality/alias-proposals')
  aliasStats.value = res.data
}

onMounted(async () => {
  loading.value = true
  await nextTick()
  sourceChart = echarts.init(sourceChartRef.value)
  confidenceChart = echarts.init(confidenceChartRef.value)
  correctionChart = echarts.init(correctionChartRef.value)

  await Promise.allSettled([loadSources(), loadConfidence(), loadCorrectionRate(), loadAliasStats()])
  loading.value = false
})
</script>
```

- [ ] **Step 2: Add route to router**

Add to `src/router/index.js` children array:

```javascript
{
  path: 'intent-quality',
  name: 'IntentQuality',
  component: () => import('../views/IntentQuality.vue'),
  meta: { title: '意图质量', icon: 'Aim' }
}
```

- [ ] **Step 3: Add menu item to AdminLayout.vue**

Add to `menuItems` array in `AdminLayout.vue`:

```javascript
{ path: '/intent-quality', title: '意图质量', icon: 'Aim' }
```

- [ ] **Step 4: Verify frontend build**

Run: `cd agent-admin-front && npx vite build --mode development`
Expected: Build succeeds, IntentQuality chunk generated

- [ ] **Step 5: Commit**

```bash
git add agent-admin-front/src/views/IntentQuality.vue \
  agent-admin-front/src/router/index.js \
  agent-admin-front/src/layouts/AdminLayout.vue
git commit -m "feat(admin-front): add intent quality monitoring page with charts and tables"
```

---

## Self-Review

### Spec Coverage
- **RAG spec**: ✓ rag_search_logs table (Task 1), logging (Task 3), internal API (Task 2), admin overview/timeline/zero-results (Task 5). Inventory endpoint returns placeholder (Milvus stats not directly queryable from admin-backend).
- **Intent Quality spec**: ✓ source distribution (Task 6+7), confidence distribution (Task 6+7), correction rate (Task 6+7), dialogue turns (Task 7, placeholder), alias proposals (Task 7, placeholder). Agent-core aggregation API (Task 6).
- **Tasks.md coverage**: Tasks 1.2, 1.5, 2.7, 2.8, 2.9, 2.10, 3.3, 3.4, 3.6, 7.1-7.8, 8.1-8.7, 15.1-15.7 covered.

### Placeholder Scan
- Dialogue turns endpoint returns placeholder (needs SessionMessageReadRepository query — not yet available)
- Alias proposals endpoint returns placeholder (needs IntentTaxonomyAdminService integration)
- RAG inventory endpoint returns placeholder (needs Milvus collection stats)
These are acceptable for MVP — the endpoints exist and return valid responses, data can be populated later.

### Type Consistency
- `RagSearchLog` entity fields match migration SQL columns ✓
- `RagSearchLogRead` entity fields match `RagSearchLog` entity ✓
- DTO field names match between Python endpoints and Java service parsing ✓
- Controller endpoint paths match spec requirements ✓
