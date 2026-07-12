# Sprint 3: System Health Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add HTTP request logging (agent-api filter), Spring Boot Actuator integration, admin query APIs for workflow success/retries/errors/anomalies/HTTP/threads/DB pool, and a frontend SystemHealth.vue page.

**Architecture:** agent-api's `HttpRequestLogFilter` intercepts `/api/v1/*` requests and async-writes to `http_request_logs` table. Spring Boot Actuator exposes thread pool and HikariCP metrics at `/actuator/metrics/*`. admin-backend queries `stage_logs`, `workflow_logs`, and `http_request_logs` via read-only JPA entities for 5 DB-based endpoints, and calls agent-api's Actuator via WebClient for 2 infrastructure endpoints. Frontend `SystemHealth.vue` renders gauges, charts, and tables.

**Tech Stack:** Java 17 / Spring Boot 3.2.5 / JPA / Flyway / Actuator / H2 (tests), Vue 3 / Element Plus / ECharts

## Global Constraints

- agent-api Flyway migrations follow existing naming: V2026071202__*.sql (Sprint 2 used V2026071201)
- admin-backend entities are read-only (getters only, no setters beyond id), mapping to tables created by agent-api
- admin-backend DTOs use Java `record` type
- admin-backend tests use @SpringBootTest + H2 in MySQL mode
- Frontend uses existing `client` from `src/api/client.js` (baseURL: `/api/admin`, X-Admin-Token header)
- HTTP filter must not block the HTTP response — use @Async for DB writes
- Actuator endpoints (/actuator/**) are permitAll in agent-api (relies on network isolation, same as /api/v1/internal/**)
- admin-backend WebClient calls to Actuator must gracefully degrade (return empty object on failure)
- Use TypeReference<Map<String, Object>> {} instead of Map.class for objectMapper.readValue

---

## File Structure

### agent-api (Java, :8080)

| File | Responsibility |
|------|---------------|
| `agent-api/src/main/resources/db/migration/V2026071202__create_http_request_logs.sql` | Flyway migration creating `http_request_logs` table |
| `agent-api/pom.xml` (modify) | Add `spring-boot-starter-actuator` dependency |
| `agent-api/src/main/resources/application.yml` (modify) | Add management endpoints config |
| `agent-api/src/main/java/com/meichen/orchestrator/security/SecurityConfig.java` (modify) | Allow `/actuator/**` |
| `agent-api/src/main/java/com/meichen/orchestrator/entity/HttpRequestLog.java` | JPA entity mapping to `http_request_logs` |
| `agent-api/src/main/java/com/meichen/orchestrator/repository/HttpRequestLogRepository.java` | Spring Data JPA repository |
| `agent-api/src/main/java/com/meichen/orchestrator/service/HttpRequestLogService.java` | @Async service for non-blocking DB writes |
| `agent-api/src/main/java/com/meichen/orchestrator/filter/HttpRequestLogFilter.java` | OncePerRequestFilter intercepting /api/v1/* |
| `agent-api/src/test/java/com/meichen/orchestrator/repository/HttpRequestLogRepositoryTest.java` | @DataJpaTest for repository |
| `agent-api/src/test/java/com/meichen/orchestrator/filter/HttpRequestLogFilterIntegrationTest.java` | @SpringBootTest for filter |

### agent-admin-backend (Java, :8081)

| File | Responsibility |
|------|---------------|
| `agent-admin-backend/src/main/java/com/meichen/admin/entity/StageLogRead.java` (modify) | Add parentId, errorMessage, timeAnomaly, subStageOverflow fields |
| `agent-admin-backend/src/main/java/com/meichen/admin/entity/WorkflowLogRead.java` | Read-only entity for `workflow_logs` |
| `agent-admin-backend/src/main/java/com/meichen/admin/entity/HttpRequestLogRead.java` | Read-only entity for `http_request_logs` |
| `agent-admin-backend/src/main/java/com/meichen/admin/repository/StageLogReadRepository.java` (modify) | Add aggregation queries for workflow-success + anomalies |
| `agent-admin-backend/src/main/java/com/meichen/admin/repository/WorkflowLogReadRepository.java` | Aggregation queries for retries + errors |
| `agent-admin-backend/src/main/java/com/meichen/admin/repository/HttpRequestLogReadRepository.java` | Aggregation queries for HTTP metrics |
| `agent-admin-backend/src/main/java/com/meichen/admin/dto/WorkflowSuccessDTO.java` | Workflow success rate record |
| `agent-admin-backend/src/main/java/com/meichen/admin/dto/RetryDistributionDTO.java` | Retry distribution record |
| `agent-admin-backend/src/main/java/com/meichen/admin/dto/ErrorDistributionDTO.java` | Error distribution record |
| `agent-admin-backend/src/main/java/com/meichen/admin/dto/AnomalyStatsDTO.java` | Anomaly stats record |
| `agent-admin-backend/src/main/java/com/meichen/admin/dto/HttpMetricsDTO.java` | HTTP metrics record |
| `agent-admin-backend/src/main/java/com/meichen/admin/dto/ThreadPoolMetricsDTO.java` | Thread pool metrics record |
| `agent-admin-backend/src/main/java/com/meichen/admin/dto/DbPoolMetricsDTO.java` | DB pool metrics record |
| `agent-admin-backend/src/main/java/com/meichen/admin/service/SystemHealthService.java` | Service with 5 DB-based query methods |
| `agent-admin-backend/src/main/java/com/meichen/admin/service/ActuatorClient.java` | WebClient wrapper for agent-api Actuator |
| `agent-admin-backend/src/main/java/com/meichen/admin/controller/SystemHealthController.java` | Controller at `/api/admin/metrics/system` with 7 endpoints |
| `agent-admin-backend/src/test/java/com/meichen/admin/controller/SystemHealthControllerIntegrationTest.java` | Integration tests |

### agent-admin-front (Vue, :8082)

| File | Responsibility |
|------|---------------|
| `agent-admin-front/src/views/SystemHealth.vue` | System health page with gauges + charts + tables |
| `agent-admin-front/src/router/index.js` (modify) | Add route |
| `agent-admin-front/src/layouts/AdminLayout.vue` (modify) | Add menu item |

---

## Task 1: agent-api Setup — Migration + Actuator + Config

**Files:**
- Create: `agent-api/src/main/resources/db/migration/V2026071202__create_http_request_logs.sql`
- Modify: `agent-api/pom.xml` (add actuator dependency)
- Modify: `agent-api/src/main/resources/application.yml` (add management config)
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/security/SecurityConfig.java` (allow /actuator/**)

**Interfaces:**
- Produces: `http_request_logs` table, Actuator endpoints at `/actuator/health` and `/actuator/metrics/*`

- [ ] **Step 1: Create the Flyway migration script**

```sql
-- http_request_logs: HTTP request instrumentation log
CREATE TABLE http_request_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    method VARCHAR(10) NOT NULL COMMENT 'HTTP method: GET/POST/PUT/DELETE',
    path_pattern VARCHAR(200) NOT NULL COMMENT 'Path pattern e.g. /api/v1/projects/{id}',
    status_code INT NOT NULL COMMENT 'HTTP status code',
    duration_ms INT NOT NULL COMMENT 'Response duration in milliseconds',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_path_created (path_pattern, created_at),
    INDEX idx_status_created (status_code, created_at),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

- [ ] **Step 2: Add Actuator dependency to pom.xml**

In `agent-api/pom.xml`, add this dependency after the `spring-boot-starter-webflux` dependency (around line 68):

```xml
        <!-- Actuator (health + metrics endpoints) -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-actuator</artifactId>
        </dependency>
```

- [ ] **Step 3: Add management config to application.yml**

In `agent-api/src/main/resources/application.yml`, add this block at the top level (after the `jwt:` block at the end):

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics
  endpoint:
    health:
      show-details: always
```

- [ ] **Step 4: Allow /actuator/** in SecurityConfig**

In `agent-api/src/main/java/com/meichen/orchestrator/security/SecurityConfig.java`, add `.requestMatchers("/actuator/**").permitAll()` to the `authorizeHttpRequests` chain. The modified section should look like:

```java
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/v1/auth/**").permitAll()
                .requestMatchers("/api/v1/internal/**").permitAll()
                .requestMatchers("/actuator/**").permitAll()
                .requestMatchers("/images/**", "/data/**").permitAll()
                .anyRequest().authenticated()
            )
```

- [ ] **Step 5: Verify migration applies and Actuator works**

Run: `cd agent-api && mvn spring-boot:run -q 2>&1 | tail -20`
Expected: Application starts, Flyway log shows "Migrating schema... to version 2026071202"

Then in another terminal, verify Actuator:
```bash
curl -s http://localhost:8080/actuator/health | head -5
curl -s http://localhost:8080/actuator/metrics | head -20
```
Expected: health returns `{"status":"UP"}`, metrics returns list of available metric names

Verify table exists:
```bash
mysql -u meichen -pmeichen123 -e "DESCRIBE http_request_logs;" meichen 2>/dev/null
```

Stop the app with Ctrl+C.

- [ ] **Step 6: Commit**

```bash
git add agent-api/src/main/resources/db/migration/V2026071202__create_http_request_logs.sql \
        agent-api/pom.xml \
        agent-api/src/main/resources/application.yml \
        agent-api/src/main/java/com/meichen/orchestrator/security/SecurityConfig.java
git commit -m "feat(agent-api): add http_request_logs table and Actuator for system health metrics"
```

---

## Task 2: agent-api HttpRequestLog Entity + Repository + Service

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/entity/HttpRequestLog.java`
- Create: `agent-api/src/main/java/com/meichen/orchestrator/repository/HttpRequestLogRepository.java`
- Create: `agent-api/src/main/java/com/meichen/orchestrator/service/HttpRequestLogService.java`
- Test: `agent-api/src/test/java/com/meichen/orchestrator/repository/HttpRequestLogRepositoryTest.java`

**Interfaces:**
- Produces: `HttpRequestLog` entity, `HttpRequestLogRepository` with `save()`, `HttpRequestLogService` with `@Async saveAsync()` method

- [ ] **Step 1: Write the failing repository test**

```java
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-api && mvn test -Dtest=HttpRequestLogRepositoryTest -q 2>&1 | tail -10`
Expected: COMPILATION ERROR (HttpRequestLog and HttpRequestLogRepository don't exist)

- [ ] **Step 3: Write HttpRequestLog entity**

```java
package com.meichen.orchestrator.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "http_request_logs")
public class HttpRequestLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "method", length = 10, nullable = false)
    private String method;

    @Column(name = "path_pattern", length = 200, nullable = false)
    private String pathPattern;

    @Column(name = "status_code", nullable = false)
    private Integer statusCode;

    @Column(name = "duration_ms", nullable = false)
    private Integer durationMs;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public HttpRequestLog() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getMethod() { return method; }
    public void setMethod(String method) { this.method = method; }
    public String getPathPattern() { return pathPattern; }
    public void setPathPattern(String pathPattern) { this.pathPattern = pathPattern; }
    public Integer getStatusCode() { return statusCode; }
    public void setStatusCode(Integer statusCode) { this.statusCode = statusCode; }
    public Integer getDurationMs() { return durationMs; }
    public void setDurationMs(Integer durationMs) { this.durationMs = durationMs; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
```

- [ ] **Step 4: Write HttpRequestLogRepository**

```java
package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.HttpRequestLog;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;

public interface HttpRequestLogRepository extends JpaRepository<HttpRequestLog, Long> {

    List<HttpRequestLog> findByCreatedAtAfter(LocalDateTime createdAt);

    long countByCreatedAtAfter(LocalDateTime createdAt);
}
```

- [ ] **Step 5: Write HttpRequestLogService**

```java
package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.HttpRequestLog;
import com.meichen.orchestrator.repository.HttpRequestLogRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
public class HttpRequestLogService {

    private static final Logger log = LoggerFactory.getLogger(HttpRequestLogService.class);

    private final HttpRequestLogRepository repository;

    public HttpRequestLogService(HttpRequestLogRepository repository) {
        this.repository = repository;
    }

    @Async("dialogueExecutor")
    public void saveAsync(String method, String pathPattern, int statusCode, int durationMs) {
        try {
            HttpRequestLog entity = new HttpRequestLog();
            entity.setMethod(method);
            entity.setPathPattern(pathPattern);
            entity.setStatusCode(statusCode);
            entity.setDurationMs(durationMs);
            entity.setCreatedAt(LocalDateTime.now());
            repository.save(entity);
        } catch (Exception e) {
            log.warn("Failed to persist HTTP request log: {}", e.getMessage());
        }
    }
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd agent-api && mvn test -Dtest=HttpRequestLogRepositoryTest -q 2>&1 | tail -10`
Expected: Tests run: 3, Failures: 0, Errors: 0

- [ ] **Step 7: Commit**

```bash
git add agent-api/src/main/java/com/meichen/orchestrator/entity/HttpRequestLog.java \
        agent-api/src/main/java/com/meichen/orchestrator/repository/HttpRequestLogRepository.java \
        agent-api/src/main/java/com/meichen/orchestrator/service/HttpRequestLogService.java \
        agent-api/src/test/java/com/meichen/orchestrator/repository/HttpRequestLogRepositoryTest.java
git commit -m "feat(agent-api): add HttpRequestLog entity, repository, and async service"
```

---

## Task 3: agent-api HttpRequestLogFilter

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/filter/HttpRequestLogFilter.java`
- Test: `agent-api/src/test/java/com/meichen/orchestrator/filter/HttpRequestLogFilterIntegrationTest.java`

**Interfaces:**
- Consumes: `HttpRequestLogService.saveAsync()` from Task 2
- Produces: `HttpRequestLogFilter` bean that intercepts `/api/v1/*` requests, excludes `/actuator/*`, `/images/*`, `/data/*`

- [ ] **Step 1: Write the failing filter integration test**

```java
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-api && mvn test -Dtest=HttpRequestLogFilterIntegrationTest -q 2>&1 | tail -10`
Expected: COMPILATION ERROR or test failure (HttpRequestLogFilter doesn't exist)

- [ ] **Step 3: Write HttpRequestLogFilter**

```java
package com.meichen.orchestrator.filter;

import com.meichen.orchestrator.service.HttpRequestLogService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

@Component
public class HttpRequestLogFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(HttpRequestLogFilter.class);

    private final HttpRequestLogService logService;

    public HttpRequestLogFilter(HttpRequestLogService logService) {
        this.logService = logService;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        return path.startsWith("/actuator") ||
               path.startsWith("/images/") ||
               path.startsWith("/data/");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        long start = System.currentTimeMillis();
        try {
            filterChain.doFilter(request, response);
        } finally {
            try {
                int durationMs = (int) (System.currentTimeMillis() - start);
                String method = request.getMethod();
                String pathPattern = (String) request.getAttribute(
                    org.springframework.web.servlet.HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE);
                if (pathPattern == null || pathPattern.isEmpty()) {
                    pathPattern = request.getRequestURI();
                }
                int statusCode = response.getStatus();
                logService.saveAsync(method, pathPattern, statusCode, durationMs);
            } catch (Exception e) {
                log.warn("Failed to log HTTP request: {}", e.getMessage());
            }
        }
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent-api && mvn test -Dtest=HttpRequestLogFilterIntegrationTest -q 2>&1 | tail -15`
Expected: Tests run: 2, Failures: 0, Errors: 0

- [ ] **Step 5: Run full agent-api test suite to check for regressions**

Run: `cd agent-api && mvn test -q 2>&1 | grep -E "Tests run|BUILD"`
Expected: BUILD SUCCESS, all tests pass

- [ ] **Step 6: Commit**

```bash
git add agent-api/src/main/java/com/meichen/orchestrator/filter/HttpRequestLogFilter.java \
        agent-api/src/test/java/com/meichen/orchestrator/filter/HttpRequestLogFilterIntegrationTest.java
git commit -m "feat(agent-api): add HttpRequestLogFilter to intercept and log API requests"
```

---

## Task 4: admin-backend Read-Only Entities + Repositories

**Files:**
- Modify: `agent-admin-backend/src/main/java/com/meichen/admin/entity/StageLogRead.java` (add parentId, errorMessage, timeAnomaly, subStageOverflow)
- Modify: `agent-admin-backend/src/main/java/com/meichen/admin/repository/StageLogReadRepository.java` (add aggregation queries)
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/entity/WorkflowLogRead.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/entity/HttpRequestLogRead.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/repository/WorkflowLogReadRepository.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/repository/HttpRequestLogReadRepository.java`
- Test: `agent-admin-backend/src/test/java/com/meichen/admin/repository/SystemHealthRepositoryTest.java`

**Interfaces:**
- Produces: `StageLogRead` (enhanced), `WorkflowLogRead`, `HttpRequestLogRead` entities + repositories with aggregation queries used by Task 5

- [ ] **Step 1: Write the failing repository test**

```java
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
    void stageLogRepo_findFailurePoints_returnsFailedStages() {
        LocalDateTime since = LocalDateTime.now().minusDays(7);
        List<Object[]> results = stageLogRepo.findFailurePoints(since);
        assertFalse(results.isEmpty());
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-admin-backend && mvn test -Dtest=SystemHealthRepositoryTest -q 2>&1 | tail -10`
Expected: COMPILATION ERROR (WorkflowLogRead, HttpRequestLogRead, WorkflowLogReadRepository, HttpRequestLogReadRepository don't exist; StageLogReadRepository missing methods)

- [ ] **Step 3: Modify StageLogRead entity to add missing fields**

In `agent-admin-backend/src/main/java/com/meichen/admin/entity/StageLogRead.java`, add these fields and getters after the existing `completedAt` field:

```java
    @Column(name = "parent_id")
    private Long parentId;

    @Column(name = "error_message", length = 4000)
    private String errorMessage;

    @Column(name = "time_anomaly")
    private boolean timeAnomaly;

    @Column(name = "sub_stage_overflow")
    private boolean subStageOverflow;
```

And add these getters at the end of the class (before the closing brace):

```java
    public Long getParentId() { return parentId; }
    public String getErrorMessage() { return errorMessage; }
    public boolean isTimeAnomaly() { return timeAnomaly; }
    public boolean isSubStageOverflow() { return subStageOverflow; }
```

- [ ] **Step 4: Modify StageLogReadRepository to add aggregation queries**

Replace the entire content of `agent-admin-backend/src/main/java/com/meichen/admin/repository/StageLogReadRepository.java` with:

```java
package com.meichen.admin.repository;

import com.meichen.admin.entity.StageLogRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface StageLogReadRepository extends JpaRepository<StageLogRead, Long> {

    @Query("SELECT s.stageName, COUNT(s), " +
           "SUM(CASE WHEN s.status = 'SUCCESS' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN s.status = 'FAILED' THEN 1 ELSE 0 END) " +
           "FROM StageLogRead s WHERE s.parentId IS NULL AND s.startedAt >= :since " +
           "GROUP BY s.stageName ORDER BY COUNT(s) DESC")
    List<Object[]> aggregateWorkflowSuccess(@Param("since") LocalDateTime since);

    @Query("SELECT s.stageName, COUNT(s) FROM StageLogRead s " +
           "WHERE s.status = 'FAILED' AND s.parentId IS NULL AND s.startedAt >= :since " +
           "GROUP BY s.stageName ORDER BY COUNT(s) DESC")
    List<Object[]> findFailurePoints(@Param("since") LocalDateTime since);

    @Query("SELECT " +
           "SUM(CASE WHEN s.timeAnomaly = true THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN s.subStageOverflow = true THEN 1 ELSE 0 END) " +
           "FROM StageLogRead s WHERE s.startedAt >= :since")
    Object[] countAnomalies(@Param("since") LocalDateTime since);

    @Query("SELECT s.stageName, " +
           "SUM(CASE WHEN s.timeAnomaly = true THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN s.subStageOverflow = true THEN 1 ELSE 0 END) " +
           "FROM StageLogRead s WHERE s.startedAt >= :since " +
           "AND (s.timeAnomaly = true OR s.subStageOverflow = true) " +
           "GROUP BY s.stageName ORDER BY COUNT(s) DESC")
    List<Object[]> findAnomalyStages(@Param("since") LocalDateTime since);

    long count();
}
```

- [ ] **Step 5: Write WorkflowLogRead entity**

```java
package com.meichen.admin.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "workflow_logs")
public class WorkflowLogRead {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "project_id", length = 36)
    private String projectId;

    @Column(name = "node_name", length = 100)
    private String nodeName;

    @Column(name = "status", length = 50)
    private String status;

    @Column(name = "error_message", length = 2000)
    private String errorMessage;

    @Column(name = "retry_count")
    private Integer retryCount;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public String getProjectId() { return projectId; }
    public String getNodeName() { return nodeName; }
    public String getStatus() { return status; }
    public String getErrorMessage() { return errorMessage; }
    public Integer getRetryCount() { return retryCount; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
```

- [ ] **Step 6: Write WorkflowLogReadRepository**

```java
package com.meichen.admin.repository;

import com.meichen.admin.entity.WorkflowLogRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface WorkflowLogReadRepository extends JpaRepository<WorkflowLogRead, Long> {

    @Query("SELECT w.nodeName, COUNT(w), SUM(w.retryCount), " +
           "SUM(CASE WHEN w.retryCount > 0 THEN 1 ELSE 0 END) " +
           "FROM WorkflowLogRead w WHERE w.createdAt >= :since " +
           "GROUP BY w.nodeName ORDER BY SUM(w.retryCount) DESC")
    List<Object[]> aggregateRetries(@Param("since") LocalDateTime since);

    @Query("SELECT w.nodeName, COUNT(w), w.errorMessage " +
           "FROM WorkflowLogRead w WHERE w.status = 'failed' AND w.createdAt >= :since " +
           "GROUP BY w.nodeName, w.errorMessage ORDER BY COUNT(w) DESC")
    List<Object[]> aggregateErrors(@Param("since") LocalDateTime since);
}
```

- [ ] **Step 7: Write HttpRequestLogRead entity**

```java
package com.meichen.admin.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "http_request_logs")
public class HttpRequestLogRead {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "method", length = 10)
    private String method;

    @Column(name = "path_pattern", length = 200)
    private String pathPattern;

    @Column(name = "status_code")
    private Integer statusCode;

    @Column(name = "duration_ms")
    private Integer durationMs;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public String getMethod() { return method; }
    public String getPathPattern() { return pathPattern; }
    public Integer getStatusCode() { return statusCode; }
    public Integer getDurationMs() { return durationMs; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
```

- [ ] **Step 8: Write HttpRequestLogReadRepository**

```java
package com.meichen.admin.repository;

import com.meichen.admin.entity.HttpRequestLogRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface HttpRequestLogReadRepository extends JpaRepository<HttpRequestLogRead, Long> {

    @Query("SELECT COUNT(h), " +
           "SUM(CASE WHEN h.statusCode >= 400 THEN 1 ELSE 0 END), " +
           "AVG(h.durationMs), " +
           "MAX(h.durationMs) " +
           "FROM HttpRequestLogRead h WHERE h.createdAt >= :since")
    Object[] aggregateHttp(@Param("since") LocalDateTime since);

    @Query("SELECT h.pathPattern, COUNT(h), " +
           "SUM(CASE WHEN h.statusCode >= 400 THEN 1 ELSE 0 END), " +
           "AVG(h.durationMs) " +
           "FROM HttpRequestLogRead h WHERE h.createdAt >= :since " +
           "GROUP BY h.pathPattern ORDER BY COUNT(h) DESC")
    List<Object[]> groupByPathPattern(@Param("since") LocalDateTime since);
}
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd agent-admin-backend && mvn test -Dtest=SystemHealthRepositoryTest -q 2>&1 | tail -15`
Expected: Tests run: 7, Failures: 0, Errors: 0

- [ ] **Step 10: Commit**

```bash
git add agent-admin-backend/src/main/java/com/meichen/admin/entity/StageLogRead.java \
        agent-admin-backend/src/main/java/com/meichen/admin/entity/WorkflowLogRead.java \
        agent-admin-backend/src/main/java/com/meichen/admin/entity/HttpRequestLogRead.java \
        agent-admin-backend/src/main/java/com/meichen/admin/repository/StageLogReadRepository.java \
        agent-admin-backend/src/main/java/com/meichen/admin/repository/WorkflowLogReadRepository.java \
        agent-admin-backend/src/main/java/com/meichen/admin/repository/HttpRequestLogReadRepository.java \
        agent-admin-backend/src/test/java/com/meichen/admin/repository/SystemHealthRepositoryTest.java
git commit -m "feat(admin): add read-only entities and repositories for system health metrics"
```

---

## Task 5: admin-backend DTOs + SystemHealthService (DB) + Controller (5 endpoints)

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/WorkflowSuccessDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/RetryDistributionDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/ErrorDistributionDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/AnomalyStatsDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/HttpMetricsDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/service/SystemHealthService.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/controller/SystemHealthController.java`
- Test: `agent-admin-backend/src/test/java/com/meichen/admin/controller/SystemHealthControllerIntegrationTest.java`

**Interfaces:**
- Consumes: `StageLogReadRepository`, `WorkflowLogReadRepository`, `HttpRequestLogReadRepository` from Task 4
- Produces: 5 API endpoints at `/api/admin/metrics/system`: GET /workflow-success, /retries, /errors, /anomalies, /http

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
    "admin.agent-core.data-dir=/tmp",
    "admin.agent-api.base-url=http://localhost:8080"
})
class SystemHealthControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("DELETE FROM stage_logs");
        jdbcTemplate.execute("DELETE FROM workflow_logs");
        jdbcTemplate.execute("DELETE FROM http_request_logs");

        jdbcTemplate.update("INSERT INTO stage_logs (public_id, project_id, stage_name, status, started_at, duration_ms, time_anomaly, sub_stage_overflow) " +
            "VALUES ('pid1', 'proj-1', 'concept_design', 'SUCCESS', CURRENT_TIMESTAMP, 5000, FALSE, FALSE)");
        jdbcTemplate.update("INSERT INTO stage_logs (public_id, project_id, stage_name, status, started_at, duration_ms, error_message, time_anomaly, sub_stage_overflow) " +
            "VALUES ('pid2', 'proj-2', 'image_generation', 'FAILED', CURRENT_TIMESTAMP, 30000, 'timeout', FALSE, FALSE)");

        jdbcTemplate.update("INSERT INTO workflow_logs (project_id, node_name, status, error_message, retry_count) " +
            "VALUES ('proj-1', 'concept_design', 'success', NULL, 2)");
        jdbcTemplate.update("INSERT INTO workflow_logs (project_id, node_name, status, error_message, retry_count) " +
            "VALUES ('proj-2', 'image_generation', 'failed', 'API timeout', 1)");

        jdbcTemplate.update("INSERT INTO http_request_logs (method, path_pattern, status_code, duration_ms, created_at) " +
            "VALUES ('GET', '/api/v1/projects', 200, 50, CURRENT_TIMESTAMP)");
        jdbcTemplate.update("INSERT INTO http_request_logs (method, path_pattern, status_code, duration_ms, created_at) " +
            "VALUES ('POST', '/api/v1/projects', 500, 2000, CURRENT_TIMESTAMP)");
    }

    @Test
    void getWorkflowSuccess_returnsStats() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/workflow-success")
                .param("days", "7")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].stageName").exists())
            .andExpect(jsonPath("$[0].totalCount").exists())
            .andExpect(jsonPath("$[0].successCount").exists())
            .andExpect(jsonPath("$[0].failedCount").exists());
    }

    @Test
    void getRetries_returnsDistribution() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/retries")
                .param("days", "7")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].nodeName").exists())
            .andExpect(jsonPath("$[0].totalRetries").exists());
    }

    @Test
    void getErrors_returnsDistribution() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/errors")
                .param("days", "7")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].nodeName").exists());
    }

    @Test
    void getAnomalies_returnsStats() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/anomalies")
                .param("days", "7")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.timeAnomalyCount").exists())
            .andExpect(jsonPath("$.subStageOverflowCount").exists());
    }

    @Test
    void getHttp_returnsMetrics() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/http")
                .param("hours", "1")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalRequests").exists())
            .andExpect(jsonPath("$.errorCount").exists())
            .andExpect(jsonPath("$.avgDurationMs").exists());
    }

    @Test
    void getWorkflowSuccess_withoutToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/workflow-success"))
            .andExpect(status().isUnauthorized());
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-admin-backend && mvn test -Dtest=SystemHealthControllerIntegrationTest -q 2>&1 | tail -10`
Expected: COMPILATION ERROR (DTOs, service, controller don't exist)

- [ ] **Step 3: Write DTOs**

`WorkflowSuccessDTO.java`:
```java
package com.meichen.admin.dto;

public record WorkflowSuccessDTO(
    String stageName,
    long totalCount,
    long successCount,
    long failedCount,
    double successRate
) {}
```

`RetryDistributionDTO.java`:
```java
package com.meichen.admin.dto;

public record RetryDistributionDTO(
    String nodeName,
    long totalExecutions,
    long totalRetries,
    long executionsWithRetry
) {}
```

`ErrorDistributionDTO.java`:
```java
package com.meichen.admin.dto;

public record ErrorDistributionDTO(
    String nodeName,
    long errorCount,
    String errorMessage
) {}
```

`AnomalyStatsDTO.java`:
```java
package com.meichen.admin.dto;

import java.util.List;

public record AnomalyStatsDTO(
    long timeAnomalyCount,
    long subStageOverflowCount,
    List<AnomalyStageDTO> affectedStages
) {
    public record AnomalyStageDTO(
        String stageName,
        long timeAnomalyCount,
        long subStageOverflowCount
    ) {}
}
```

`HttpMetricsDTO.java`:
```java
package com.meichen.admin.dto;

import java.util.List;

public record HttpMetricsDTO(
    long totalRequests,
    long errorCount,
    double errorRate,
    double avgDurationMs,
    long maxDurationMs,
    List<HttpPathBreakdownDTO> topEndpoints
) {
    public record HttpPathBreakdownDTO(
        String pathPattern,
        long requestCount,
        long errorCount,
        double avgDurationMs
    ) {}
}
```

- [ ] **Step 4: Write SystemHealthService**

```java
package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.HttpRequestLogReadRepository;
import com.meichen.admin.repository.StageLogReadRepository;
import com.meichen.admin.repository.WorkflowLogReadRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class SystemHealthService {

    private final StageLogReadRepository stageLogRepo;
    private final WorkflowLogReadRepository workflowLogRepo;
    private final HttpRequestLogReadRepository httpLogRepo;

    public SystemHealthService(StageLogReadRepository stageLogRepo,
                               WorkflowLogReadRepository workflowLogRepo,
                               HttpRequestLogReadRepository httpLogRepo) {
        this.stageLogRepo = stageLogRepo;
        this.workflowLogRepo = workflowLogRepo;
        this.httpLogRepo = httpLogRepo;
    }

    public List<WorkflowSuccessDTO> getWorkflowSuccess(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<Object[]> rows = stageLogRepo.aggregateWorkflowSuccess(since);
        return rows.stream().map(row -> {
            long total = ((Number) row[1]).longValue();
            long success = ((Number) row[2]).longValue();
            long failed = ((Number) row[3]).longValue();
            return new WorkflowSuccessDTO(
                (String) row[0],
                total,
                success,
                failed,
                total > 0 ? (double) success / total * 100 : 0.0
            );
        }).toList();
    }

    public List<RetryDistributionDTO> getRetries(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<Object[]> rows = workflowLogRepo.aggregateRetries(since);
        return rows.stream().map(row -> new RetryDistributionDTO(
            (String) row[0],
            ((Number) row[1]).longValue(),
            row[2] != null ? ((Number) row[2]).longValue() : 0L,
            row[3] != null ? ((Number) row[3]).longValue() : 0L
        )).toList();
    }

    public List<ErrorDistributionDTO> getErrors(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<Object[]> rows = workflowLogRepo.aggregateErrors(since);
        return rows.stream().map(row -> new ErrorDistributionDTO(
            (String) row[0],
            ((Number) row[1]).longValue(),
            (String) row[2]
        )).toList();
    }

    public AnomalyStatsDTO getAnomalies(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        Object[] counts = stageLogRepo.countAnomalies(since);
        long timeAnomaly = counts[0] != null ? ((Number) counts[0]).longValue() : 0L;
        long overflow = counts[1] != null ? ((Number) counts[1]).longValue() : 0L;

        List<Object[]> stageRows = stageLogRepo.findAnomalyStages(since);
        List<AnomalyStatsDTO.AnomalyStageDTO> affectedStages = stageRows.stream().map(row ->
            new AnomalyStatsDTO.AnomalyStageDTO(
                (String) row[0],
                row[1] != null ? ((Number) row[1]).longValue() : 0L,
                row[2] != null ? ((Number) row[2]).longValue() : 0L
            )
        ).toList();

        return new AnomalyStatsDTO(timeAnomaly, overflow, affectedStages);
    }

    public HttpMetricsDTO getHttpMetrics(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        Object[] overall = httpLogRepo.aggregateHttp(since);
        long totalRequests = overall[0] != null ? ((Number) overall[0]).longValue() : 0L;
        long errorCount = overall[1] != null ? ((Number) overall[1]).longValue() : 0L;
        double avgDuration = overall[2] != null ? ((Number) overall[2]).doubleValue() : 0.0;
        long maxDuration = overall[3] != null ? ((Number) overall[3]).longValue() : 0L;

        List<Object[]> pathRows = httpLogRepo.groupByPathPattern(since);
        List<HttpMetricsDTO.HttpPathBreakdownDTO> topEndpoints = pathRows.stream().map(row ->
            new HttpMetricsDTO.HttpPathBreakdownDTO(
                (String) row[0],
                ((Number) row[1]).longValue(),
                row[2] != null ? ((Number) row[2]).longValue() : 0L,
                row[3] != null ? ((Number) row[3]).doubleValue() : 0.0
            )
        ).toList();

        return new HttpMetricsDTO(
            totalRequests,
            errorCount,
            totalRequests > 0 ? (double) errorCount / totalRequests * 100 : 0.0,
            avgDuration,
            maxDuration,
            topEndpoints
        );
    }
}
```

- [ ] **Step 5: Write SystemHealthController**

```java
package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.SystemHealthService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/metrics/system")
public class SystemHealthController {

    private final SystemHealthService service;

    public SystemHealthController(SystemHealthService service) {
        this.service = service;
    }

    @GetMapping("/workflow-success")
    public ResponseEntity<List<WorkflowSuccessDTO>> getWorkflowSuccess(
            @RequestParam(defaultValue = "7") int days) {
        return ResponseEntity.ok(service.getWorkflowSuccess(days));
    }

    @GetMapping("/retries")
    public ResponseEntity<List<RetryDistributionDTO>> getRetries(
            @RequestParam(defaultValue = "7") int days) {
        return ResponseEntity.ok(service.getRetries(days));
    }

    @GetMapping("/errors")
    public ResponseEntity<List<ErrorDistributionDTO>> getErrors(
            @RequestParam(defaultValue = "7") int days) {
        return ResponseEntity.ok(service.getErrors(days));
    }

    @GetMapping("/anomalies")
    public ResponseEntity<AnomalyStatsDTO> getAnomalies(
            @RequestParam(defaultValue = "7") int days) {
        return ResponseEntity.ok(service.getAnomalies(days));
    }

    @GetMapping("/http")
    public ResponseEntity<HttpMetricsDTO> getHttp(
            @RequestParam(defaultValue = "1") int hours) {
        return ResponseEntity.ok(service.getHttpMetrics(hours));
    }
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd agent-admin-backend && mvn test -Dtest=SystemHealthControllerIntegrationTest -q 2>&1 | tail -15`
Expected: Tests run: 6, Failures: 0, Errors: 0

- [ ] **Step 7: Run full admin-backend test suite**

Run: `cd agent-admin-backend && mvn test -q 2>&1 | grep -E "Tests run|BUILD"`
Expected: BUILD SUCCESS, all tests pass

- [ ] **Step 8: Commit**

```bash
git add agent-admin-backend/src/main/java/com/meichen/admin/dto/WorkflowSuccessDTO.java \
        agent-admin-backend/src/main/java/com/meichen/admin/dto/RetryDistributionDTO.java \
        agent-admin-backend/src/main/java/com/meichen/admin/dto/ErrorDistributionDTO.java \
        agent-admin-backend/src/main/java/com/meichen/admin/dto/AnomalyStatsDTO.java \
        agent-admin-backend/src/main/java/com/meichen/admin/dto/HttpMetricsDTO.java \
        agent-admin-backend/src/main/java/com/meichen/admin/service/SystemHealthService.java \
        agent-admin-backend/src/main/java/com/meichen/admin/controller/SystemHealthController.java \
        agent-admin-backend/src/test/java/com/meichen/admin/controller/SystemHealthControllerIntegrationTest.java
git commit -m "feat(admin): add system health API with workflow, retry, error, anomaly, and HTTP endpoints"
```

---

## Task 6: admin-backend ActuatorClient + Thread-Pool/DB-Pool Endpoints

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/ThreadPoolMetricsDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/DbPoolMetricsDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/service/ActuatorClient.java`
- Modify: `agent-admin-backend/src/main/java/com/meichen/admin/service/SystemHealthService.java` (add 2 Actuator methods)
- Modify: `agent-admin-backend/src/main/java/com/meichen/admin/controller/SystemHealthController.java` (add 2 endpoints)
- Modify: `agent-admin-backend/src/main/resources/application.yml` (add agent-api base-url config)
- Modify: `agent-admin-backend/src/test/java/com/meichen/admin/controller/SystemHealthControllerIntegrationTest.java` (add 2 tests)

**Interfaces:**
- Consumes: agent-api Actuator endpoints at `/actuator/metrics/executor.*` and `/actuator/metrics/hikaricp.*`
- Produces: GET `/api/admin/metrics/system/thread-pools` and GET `/api/admin/metrics/system/db-pool`

- [ ] **Step 1: Add tests to the existing integration test**

Add these two test methods to `SystemHealthControllerIntegrationTest.java` (inside the class, before the closing brace):

```java
    @Test
    void getThreadPools_returnsMetrics() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/thread-pools")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].name").exists())
            .andExpect(jsonPath("$[0].active").exists())
            .andExpect(jsonPath("$[0].core").exists())
            .andExpect(jsonPath("$[0].max").exists());
    }

    @Test
    void getDbPool_returnsMetrics() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/system/db-pool")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.active").exists())
            .andExpect(jsonPath("$.idle").exists())
            .andExpect(jsonPath("$.max").exists());
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-admin-backend && mvn test -Dtest=SystemHealthControllerIntegrationTest -q 2>&1 | tail -10`
Expected: Test failures (endpoints don't exist yet)

- [ ] **Step 3: Add agent-api base-url to application.yml**

In `agent-admin-backend/src/main/resources/application.yml`, add under the `admin:` block (after `agent-core:`):

```yaml
  agent-api:
    base-url: ${AGENT_API_BASE_URL:http://localhost:8080}
```

The full `admin:` block should look like:

```yaml
admin:
  token: ${ADMIN_TOKEN:admin-secret-2026}
  agent-core:
    base-url: http://localhost:8000
    data-dir: ${AGENT_CORE_DATA_DIR:/Users/liulei/private-work/design-agent/agent-core/data}
  agent-api:
    base-url: ${AGENT_API_BASE_URL:http://localhost:8080}
```

- [ ] **Step 4: Write ThreadPoolMetricsDTO**

```java
package com.meichen.admin.dto;

public record ThreadPoolMetricsDTO(
    String name,
    int active,
    int core,
    int max,
    long completedTaskCount,
    int queueSize
) {}
```

- [ ] **Step 5: Write DbPoolMetricsDTO**

```java
package com.meichen.admin.dto;

public record DbPoolMetricsDTO(
    int active,
    int idle,
    int max,
    int pending
) {}
```

- [ ] **Step 6: Write ActuatorClient**

```java
package com.meichen.admin.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.meichen.admin.dto.DbPoolMetricsDTO;
import com.meichen.admin.dto.ThreadPoolMetricsDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Component
public class ActuatorClient {

    private static final Logger log = LoggerFactory.getLogger(ActuatorClient.class);
    private static final ObjectMapper objectMapper = new ObjectMapper();

    private final WebClient actuatorClient;

    public ActuatorClient(@Value("${admin.agent-api.base-url}") String agentApiBaseUrl) {
        this.actuatorClient = WebClient.builder().baseUrl(agentApiBaseUrl).build();
    }

    public List<ThreadPoolMetricsDTO> getThreadPoolMetrics() {
        List<ThreadPoolMetricsDTO> pools = new ArrayList<>();
        String[] executorNames = {"workflowExecutor", "dialogueExecutor"};
        for (String name : executorNames) {
            try {
                int active = getMetricValue("executor.active", "name", name);
                int core = getMetricValue("executor.pool.core", "name", name);
                int max = getMetricValue("executor.pool.max", "name", name);
                long completed = getMetricValueAsLong("executor.completed", "name", name);
                int queueSize = getMetricValue("executor.queue.remaining", "name", name);
                pools.add(new ThreadPoolMetricsDTO(name, active, core, max, completed, queueSize));
            } catch (Exception e) {
                log.warn("Failed to fetch thread pool metrics for {}: {}", name, e.getMessage());
                pools.add(new ThreadPoolMetricsDTO(name, 0, 0, 0, 0, 0));
            }
        }
        return pools;
    }

    public DbPoolMetricsDTO getDbPoolMetrics() {
        try {
            int active = getMetricValue("hikaricp.connections.active", "pool", "HikariPool-1");
            int idle = getMetricValue("hikaricp.connections.idle", "pool", "HikariPool-1");
            int max = getMetricValue("hikaricp.connections.max", "pool", "HikariPool-1");
            int pending = getMetricValue("hikaricp.connections.pending", "pool", "HikariPool-1");
            return new DbPoolMetricsDTO(active, idle, max, pending);
        } catch (Exception e) {
            log.warn("Failed to fetch DB pool metrics: {}", e.getMessage());
            return new DbPoolMetricsDTO(0, 0, 0, 0);
        }
    }

    private int getMetricValue(String metric, String tagKey, String tagValue) {
        Map<String, Object> response = fetchMetric(metric, tagKey, tagValue);
        List<?> measurements = (List<?>) response.get("measurements");
        if (measurements == null || measurements.isEmpty()) {
            return 0;
        }
        Map<?, ?> first = (Map<?, ?>) measurements.get(0);
        Number value = (Number) first.get("value");
        return value != null ? value.intValue() : 0;
    }

    private long getMetricValueAsLong(String metric, String tagKey, String tagValue) {
        Map<String, Object> response = fetchMetric(metric, tagKey, tagValue);
        List<?> measurements = (List<?>) response.get("measurements");
        if (measurements == null || measurements.isEmpty()) {
            return 0L;
        }
        Map<?, ?> first = (Map<?, ?>) measurements.get(0);
        Number value = (Number) first.get("value");
        return value != null ? value.longValue() : 0L;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> fetchMetric(String metric, String tagKey, String tagValue) {
        String json = actuatorClient.get()
            .uri(uriBuilder -> uriBuilder
                .path("/actuator/metrics/" + metric)
                .queryParam("tag", tagKey + ":" + tagValue)
                .build())
            .retrieve()
            .bodyToMono(String.class)
            .block(Duration.ofSeconds(5));
        try {
            return objectMapper.readValue(json, new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {});
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse Actuator response for " + metric, e);
        }
    }
}
```

- [ ] **Step 7: Add Actuator methods to SystemHealthService**

In `agent-admin-backend/src/main/java/com/meichen/admin/service/SystemHealthService.java`:

1. Add `ActuatorClient` as a constructor parameter and field. Add this import:
```java
import com.meichen.admin.dto.ThreadPoolMetricsDTO;
import com.meichen.admin.dto.DbPoolMetricsDTO;
```

2. Modify the constructor to inject `ActuatorClient`:

```java
    private final ActuatorClient actuatorClient;

    public SystemHealthService(StageLogReadRepository stageLogRepo,
                               WorkflowLogReadRepository workflowLogRepo,
                               HttpRequestLogReadRepository httpLogRepo,
                               ActuatorClient actuatorClient) {
        this.stageLogRepo = stageLogRepo;
        this.workflowLogRepo = workflowLogRepo;
        this.httpLogRepo = httpLogRepo;
        this.actuatorClient = actuatorClient;
    }
```

3. Add these two methods at the end of the class (before the closing brace):

```java
    public List<ThreadPoolMetricsDTO> getThreadPools() {
        return actuatorClient.getThreadPoolMetrics();
    }

    public DbPoolMetricsDTO getDbPool() {
        return actuatorClient.getDbPoolMetrics();
    }
```

- [ ] **Step 8: Add 2 endpoints to SystemHealthController**

In `agent-admin-backend/src/main/java/com/meichen/admin/controller/SystemHealthController.java`:

1. Add these imports (if not already present from the DTOs):
```java
import org.springframework.web.bind.annotation.GetMapping;
```

2. Add these endpoints before the closing brace of the class:

```java
    @GetMapping("/thread-pools")
    public ResponseEntity<List<ThreadPoolMetricsDTO>> getThreadPools() {
        return ResponseEntity.ok(service.getThreadPools());
    }

    @GetMapping("/db-pool")
    public ResponseEntity<DbPoolMetricsDTO> getDbPool() {
        return ResponseEntity.ok(service.getDbPool());
    }
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd agent-admin-backend && mvn test -Dtest=SystemHealthControllerIntegrationTest -q 2>&1 | tail -15`
Expected: Tests run: 8, Failures: 0, Errors: 0

Note: The Actuator endpoints won't be available during tests (agent-api not running), so the ActuatorClient will return default/empty values. The tests verify the endpoint returns 200 with the expected JSON structure.

- [ ] **Step 10: Commit**

```bash
git add agent-admin-backend/src/main/java/com/meichen/admin/dto/ThreadPoolMetricsDTO.java \
        agent-admin-backend/src/main/java/com/meichen/admin/dto/DbPoolMetricsDTO.java \
        agent-admin-backend/src/main/java/com/meichen/admin/service/ActuatorClient.java \
        agent-admin-backend/src/main/java/com/meichen/admin/service/SystemHealthService.java \
        agent-admin-backend/src/main/java/com/meichen/admin/controller/SystemHealthController.java \
        agent-admin-backend/src/main/resources/application.yml \
        agent-admin-backend/src/test/java/com/meichen/admin/controller/SystemHealthControllerIntegrationTest.java
git commit -m "feat(admin): add thread-pool and db-pool metrics via Actuator WebClient"
```

---

## Task 7: Frontend SystemHealth.vue + Router + Menu

**Files:**
- Create: `agent-admin-front/src/views/SystemHealth.vue`
- Modify: `agent-admin-front/src/router/index.js`
- Modify: `agent-admin-front/src/layouts/AdminLayout.vue`

**Interfaces:**
- Consumes: 7 API endpoints from Tasks 5-6 (`/metrics/system/workflow-success`, `/retries`, `/errors`, `/anomalies`, `/http`, `/thread-pools`, `/db-pool`)

- [ ] **Step 1: Create SystemHealth.vue**

```vue
<template>
  <div class="system-health" v-loading="loading">
    <!-- 时间范围选择器 -->
    <div class="header">
      <el-radio-group v-model="days" size="small" @change="loadDbMetrics">
        <el-radio-button :label="1">24h</el-radio-button>
        <el-radio-button :label="7">7d</el-radio-button>
        <el-radio-button :label="30">30d</el-radio-button>
      </el-radio-group>
      <el-radio-group v-model="httpHours" size="small" @change="loadHttpMetrics" style="margin-left: 12px">
        <el-radio-button :label="1">HTTP 1h</el-radio-button>
        <el-radio-button :label="6">HTTP 6h</el-radio-button>
        <el-radio-button :label="24">HTTP 24h</el-radio-button>
      </el-radio-group>
      <el-button size="small" @click="loadInfraMetrics" style="margin-left: 12px">
        <el-icon><Refresh /></el-icon> 刷新基础设施
      </el-button>
    </div>

    <!-- 工作流成功率 + 异常 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">工作流成功率</span></div>
          <v-chart class="chart" :option="workflowGaugeOption" autoresize style="height: 280px" />
          <el-table :data="workflowSuccess" stripe size="small" style="margin-top: 12px">
            <el-table-column prop="stageName" label="阶段" />
            <el-table-column prop="totalCount" label="总数" width="80" />
            <el-table-column prop="successCount" label="成功" width="80" />
            <el-table-column prop="failedCount" label="失败" width="80" />
            <el-table-column label="成功率" width="100">
              <template #default="{ row }">{{ row.successRate.toFixed(1) }}%</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">异常事件</span></div>
          <el-row :gutter="16" style="margin-bottom: 16px">
            <el-col :span="12">
              <div class="anomaly-card">
                <div class="anomaly-value">{{ anomalies.timeAnomalyCount }}</div>
                <div class="anomaly-label">时间异常</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="anomaly-card">
                <div class="anomaly-value">{{ anomalies.subStageOverflowCount }}</div>
                <div class="anomaly-label">子阶段溢出</div>
              </div>
            </el-col>
          </el-row>
          <el-table :data="anomalies.affectedStages" stripe size="small">
            <el-table-column prop="stageName" label="受影响阶段" />
            <el-table-column prop="timeAnomalyCount" label="时间异常" width="100" />
            <el-table-column prop="subStageOverflowCount" label="子阶段溢出" width="120" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 重试 + 错误分布 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">重试分布</span></div>
          <v-chart class="chart" :option="retryChartOption" autoresize style="height: 280px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">错误分布</span></div>
          <el-table :data="errors" stripe size="small">
            <el-table-column prop="nodeName" label="节点" />
            <el-table-column prop="errorCount" label="错误次数" width="100" />
            <el-table-column prop="errorMessage" label="错误信息" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- HTTP 指标 -->
    <el-card shadow="never" class="chart-card">
      <div class="chart-header"><span class="chart-title">HTTP 请求指标</span></div>
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="4">
          <div class="http-stat"><div class="http-value">{{ httpMetrics.totalRequests }}</div><div class="http-label">总请求</div></div>
        </el-col>
        <el-col :span="4">
          <div class="http-stat"><div class="http-value" :class="{ 'error-text': httpMetrics.errorCount > 0 }">{{ httpMetrics.errorCount }}</div><div class="http-label">错误数</div></div>
        </el-col>
        <el-col :span="4">
          <div class="http-stat"><div class="http-value">{{ httpMetrics.errorRate.toFixed(2) }}%</div><div class="http-label">错误率</div></div>
        </el-col>
        <el-col :span="4">
          <div class="http-stat"><div class="http-value">{{ httpMetrics.avgDurationMs.toFixed(0) }}ms</div><div class="http-label">平均响应</div></div>
        </el-col>
        <el-col :span="4">
          <div class="http-stat"><div class="http-value">{{ httpMetrics.maxDurationMs }}ms</div><div class="http-label">最大响应</div></div>
        </el-col>
      </el-row>
      <el-table :data="httpMetrics.topEndpoints" stripe size="small">
        <el-table-column prop="pathPattern" label="路径" />
        <el-table-column prop="requestCount" label="请求数" width="100" />
        <el-table-column prop="errorCount" label="错误数" width="100" />
        <el-table-column label="平均响应(ms)" width="130">
          <template #default="{ row }">{{ row.avgDurationMs.toFixed(0) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 线程池 + DB 连接池 -->
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">线程池状态</span></div>
          <el-row :gutter="16">
            <el-col v-for="pool in threadPools" :key="pool.name" :span="12">
              <div class="pool-card">
                <div class="pool-name">{{ pool.name }}</div>
                <v-chart class="chart" :option="getPoolGaugeOption(pool)" autoresize style="height: 200px" />
                <div class="pool-stats">
                  <span>Active: {{ pool.active }}</span>
                  <span>Core: {{ pool.core }}</span>
                  <span>Max: {{ pool.max }}</span>
                  <span>Queue: {{ pool.queueSize }}</span>
                  <span>Completed: {{ pool.completedTaskCount }}</span>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">DB 连接池</span></div>
          <v-chart class="chart" :option="dbPoolGaugeOption" autoresize style="height: 200px" />
          <div class="pool-stats" style="text-align: center">
            <span>Active: {{ dbPool.active }}</span>
            <span>Idle: {{ dbPool.idle }}</span>
            <span>Max: {{ dbPool.max }}</span>
            <span>Pending: {{ dbPool.pending }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import client from '../api/client'
import { use } from 'echarts/core'
import VChart from 'vue-echarts'
import { GaugeChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { Refresh } from '@element-plus/icons-vue'

use([CanvasRenderer, GaugeChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(false)
const days = ref(7)
const httpHours = ref(1)

const workflowSuccess = ref([])
const retries = ref([])
const errors = ref([])
const anomalies = ref({ timeAnomalyCount: 0, subStageOverflowCount: 0, affectedStages: [] })
const httpMetrics = ref({ totalRequests: 0, errorCount: 0, errorRate: 0, avgDurationMs: 0, maxDurationMs: 0, topEndpoints: [] })
const threadPools = ref([])
const dbPool = ref({ active: 0, idle: 0, max: 0, pending: 0 })

const overallSuccessRate = computed(() => {
  const total = workflowSuccess.value.reduce((sum, w) => sum + w.totalCount, 0)
  const success = workflowSuccess.value.reduce((sum, w) => sum + w.successCount, 0)
  return total > 0 ? (success / total * 100) : 0
})

const workflowGaugeOption = computed(() => ({
  series: [{
    type: 'gauge',
    progress: { show: true, width: 18 },
    axisLine: { lineStyle: { width: 18 } },
    detail: { valueAnimation: true, formatter: '{value}%', fontSize: 28 },
    data: [{ value: overallSuccessRate.value.toFixed(1) }],
    max: 100,
  }],
}))

const retryChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['总执行', '重试次数'] },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: retries.value.map(r => r.nodeName), axisLabel: { rotate: 20 } },
  yAxis: { type: 'value' },
  series: [
    { name: '总执行', type: 'bar', data: retries.value.map(r => r.totalExecutions) },
    { name: '重试次数', type: 'bar', data: retries.value.map(r => r.totalRetries) },
  ],
}))

function getPoolGaugeOption(pool) {
  const usage = pool.max > 0 ? (pool.active / pool.max * 100) : 0
  return {
    series: [{
      type: 'gauge',
      progress: { show: true, width: 14 },
      axisLine: { lineStyle: { width: 14 } },
      detail: { valueAnimation: true, formatter: '{value}%', fontSize: 20 },
      data: [{ value: usage.toFixed(1) }],
      max: 100,
    }],
  }
}

const dbPoolGaugeOption = computed(() => {
  const usage = dbPool.value.max > 0 ? (dbPool.value.active / dbPool.value.max * 100) : 0
  return {
    series: [{
      type: 'gauge',
      progress: { show: true, width: 14 },
      axisLine: { lineStyle: { width: 14 } },
      detail: { valueAnimation: true, formatter: '{value}%', fontSize: 20 },
      data: [{ value: usage.toFixed(1) }],
      max: 100,
    }],
  }
})

async function loadDbMetrics() {
  loading.value = true
  try {
    const [wf, rt, err, anom] = await Promise.all([
      client.get('/metrics/system/workflow-success', { params: { days: days.value } }),
      client.get('/metrics/system/retries', { params: { days: days.value } }),
      client.get('/metrics/system/errors', { params: { days: days.value } }),
      client.get('/metrics/system/anomalies', { params: { days: days.value } }),
    ])
    workflowSuccess.value = wf
    retries.value = rt
    errors.value = err
    anomalies.value = anom
  } finally {
    loading.value = false
  }
}

async function loadHttpMetrics() {
  const http = await client.get('/metrics/system/http', { params: { hours: httpHours.value } })
  httpMetrics.value = http
}

async function loadInfraMetrics() {
  const [tp, dbp] = await Promise.all([
    client.get('/metrics/system/thread-pools'),
    client.get('/metrics/system/db-pool'),
  ])
  threadPools.value = tp
  dbPool.value = dbp
}

onMounted(() => {
  loadDbMetrics()
  loadHttpMetrics()
  loadInfraMetrics()
})
</script>

<style scoped>
.system-health { display: flex; flex-direction: column; gap: 20px; }
.header { display: flex; align-items: center; justify-content: flex-end; }
.chart-card { margin-bottom: 0; }
.chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.chart-title { font-size: 16px; font-weight: 600; color: #303133; }
.chart { width: 100%; }
.anomaly-card { text-align: center; padding: 20px; background: #f5f7fa; border-radius: 8px; }
.anomaly-value { font-size: 32px; font-weight: 700; color: #e6a23c; }
.anomaly-label { font-size: 14px; color: #909399; margin-top: 4px; }
.http-stat { text-align: center; padding: 16px; background: #f5f7fa; border-radius: 8px; }
.http-value { font-size: 22px; font-weight: 700; color: #303133; }
.http-value.error-text { color: #f56c6c; }
.http-label { font-size: 12px; color: #909399; margin-top: 4px; }
.pool-card { text-align: center; padding: 12px; background: #f5f7fa; border-radius: 8px; }
.pool-name { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.pool-stats { display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; font-size: 12px; color: #606266; margin-top: 8px; }
</style>
```

- [ ] **Step 2: Add route in router/index.js**

Add this entry to the `children` array in `src/router/index.js`, after the `ai-monitoring` route:

```javascript
      {
        path: 'system-health',
        name: 'SystemHealth',
        component: () => import('../views/SystemHealth.vue'),
        meta: { title: '系统健康', icon: 'Cpu' }
      }
```

- [ ] **Step 3: Add menu item in AdminLayout.vue**

Add this object to the `menuItems` array in `src/layouts/AdminLayout.vue`, after the `ai-monitoring` entry:

```javascript
  { path: '/system-health', title: '系统健康', icon: 'Cpu' },
```

- [ ] **Step 4: Verify frontend compiles**

Run: `cd agent-admin-front && npx vite build --mode development 2>&1 | tail -10`
Expected: Build succeeds without errors

- [ ] **Step 5: Commit**

```bash
git add agent-admin-front/src/views/SystemHealth.vue \
        agent-admin-front/src/router/index.js \
        agent-admin-front/src/layouts/AdminLayout.vue
git commit -m "feat(admin-front): add system health page with gauges, charts, and tables"
```

---

## Post-Implementation: E2E Validation

After all 7 tasks are complete, perform end-to-end validation:

1. **Restart agent-api** (to pick up Flyway migration + Actuator): `cd agent-api && mvn spring-boot:run`
2. **Verify table created**: `mysql -u meichen -pmeichen123 -e "DESCRIBE http_request_logs;" meichen`
3. **Verify Actuator endpoints**:
   ```bash
   curl -s http://localhost:8080/actuator/health
   curl -s http://localhost:8080/actuator/metrics/executor.pool.max?tag=name:workflowExecutor
   curl -s http://localhost:8080/actuator/metrics/hikaricp.connections.max
   ```
4. **Trigger an API request and verify HTTP log**:
   ```bash
   curl -s http://localhost:8080/api/v1/projects -H "Authorization: Bearer invalid"
   mysql -u meichen -pmeichen123 -e "SELECT * FROM http_request_logs ORDER BY id DESC LIMIT 5;" meichen
   ```
5. **Restart admin-backend**: `cd agent-admin-backend && mvn spring-boot:run`
6. **Verify admin API endpoints** with curl:
   ```bash
   curl -s -H "X-Admin-Token: admin-secret-2026" "http://localhost:8081/api/admin/metrics/system/workflow-success?days=7"
   curl -s -H "X-Admin-Token: admin-secret-2026" "http://localhost:8081/api/admin/metrics/system/retries?days=7"
   curl -s -H "X-Admin-Token: admin-secret-2026" "http://localhost:8081/api/admin/metrics/system/errors?days=7"
   curl -s -H "X-Admin-Token: admin-secret-2026" "http://localhost:8081/api/admin/metrics/system/anomalies?days=7"
   curl -s -H "X-Admin-Token: admin-secret-2026" "http://localhost:8081/api/admin/metrics/system/http?hours=1"
   curl -s -H "X-Admin-Token: admin-secret-2026" "http://localhost:8081/api/admin/metrics/system/thread-pools"
   curl -s -H "X-Admin-Token: admin-secret-2026" "http://localhost:8081/api/admin/metrics/system/db-pool"
   ```
7. **Verify frontend**: Navigate to `http://localhost:8082/system-health` in browser, verify all gauges, charts, and tables render
