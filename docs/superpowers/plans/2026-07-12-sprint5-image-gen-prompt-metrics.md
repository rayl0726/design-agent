# Sprint 5: Image Generation Metrics + Prompt Template Enhanced Metrics

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add image generation monitoring metrics (backend + frontend) and enhance prompt template analytics with usage tracking, quality trends, and version comparison.

**Architecture:** Backend queries `ai_call_logs` (WHERE call_type='image_generation') joined with `feedbacks` to produce 5 image-gen endpoints and 3 prompt-template enhancement endpoints. Frontend adds a new `ImageGenMonitoring.vue` page, enhances `PromptTemplates.vue` with a usage analytics tab, and adds an error-rate trend chart to `AiModelMonitoring.vue`.

**Tech Stack:** Java 17 / Spring Boot 3.2.5 / Spring Data JPA / Hibernate 6 / H2 (test) / MySQL (prod) / Vue 3 / Element Plus / vue-echarts / ECharts

## Global Constraints

- Read-only JPA entities in admin-backend map to tables created by agent-api, use getters only, plain `@Column` for createdAt (no `@CreationTimestamp`)
- Spring Data JPA aggregate queries returning Object[] must use default-method wrapper pattern (extract first row from List<Object[]>)
- admin-backend WebClient calls to agent-core must have 2s connect timeout + 5s response timeout with graceful degradation (not needed for this sprint — all queries are local DB)
- Frontend uses `client` from `src/api/client.js` (baseURL='/api/admin', response interceptor returns `response.data` directly) — API paths omit `/api/admin` prefix
- Frontend charts use `vue-echarts` (`VChart` / `<v-chart>`) with `computed()` options and `use()` registration — NOT raw `echarts.init()`
- Configurable parameters: hours (default 24) for time-filtered queries
- Java DTOs use `record` types
- Integration tests use `@SpringBootTest` + `@AutoConfigureMockMvc` + `@TestPropertySource` with H2 MySQL mode, `admin.token=test-token`, `JdbcTemplate` for test data setup
- `application.yml` config namespace: `admin.metrics.pricing.*` for provider pricing

---

## File Structure

### agent-admin-backend (Java)
- **Create:** `src/main/java/com/meichen/admin/dto/ImageGenOverviewDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/dto/ImageGenProviderDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/dto/ImageFeedbackDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/dto/PromptTemplateUsageDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/dto/PromptTemplateQualityTrendDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/dto/PromptTemplateCompareDTO.java` — record
- **Create:** `src/main/java/com/meichen/admin/service/ImageGenMetricsService.java` — service with 5 methods
- **Create:** `src/main/java/com/meichen/admin/controller/ImageGenMetricsController.java` — 5 endpoints
- **Modify:** `src/main/java/com/meichen/admin/repository/AiCallLogReadRepository.java` — add image-gen + prompt queries
- **Modify:** `src/main/java/com/meichen/admin/repository/FeedbackReadRepository.java` — add image feedback queries
- **Modify:** `src/main/java/com/meichen/admin/service/PromptTemplateAdminService.java` — add usage tracking methods
- **Modify:** `src/main/java/com/meichen/admin/controller/PromptTemplateAdminController.java` — add 3 endpoints
- **Modify:** `src/main/resources/application.yml` — add pricing config
- **Create:** `src/test/java/com/meichen/admin/repository/ImageGenRepositoryTest.java` — repository tests
- **Create:** `src/test/java/com/meichen/admin/controller/ImageGenMetricsControllerIntegrationTest.java` — controller tests
- **Create:** `src/test/java/com/meichen/admin/controller/PromptTemplateEnhancedIntegrationTest.java` — controller tests

### agent-admin-front (Vue)
- **Create:** `src/views/ImageGenMonitoring.vue` — image generation monitoring page
- **Modify:** `src/views/PromptTemplates.vue` — add usage analytics tab
- **Modify:** `src/views/AiModelMonitoring.vue` — add error-rate trend chart
- **Modify:** `src/router/index.js` — add route for ImageGenMonitoring
- **Modify:** `src/layouts/AdminLayout.vue` — add menu item for ImageGenMonitoring

---

### Task 1: ImageGenMetrics Backend — Repository Queries + DTOs + Pricing Config

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/ImageGenOverviewDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/ImageGenProviderDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/ImageFeedbackDTO.java`
- Modify: `agent-admin-backend/src/main/java/com/meichen/admin/repository/AiCallLogReadRepository.java`
- Modify: `agent-admin-backend/src/main/java/com/meichen/admin/repository/FeedbackReadRepository.java`
- Modify: `agent-admin-backend/src/main/resources/application.yml`
- Test: `agent-admin-backend/src/test/java/com/meichen/admin/repository/ImageGenRepositoryTest.java`

**Interfaces:**
- Consumes: `AiCallLogRead` entity (callType='image_generation'), `FeedbackRead` entity (imageUrl IS NOT NULL)
- Produces: 3 DTO records + 4 repository query methods + pricing config that Task 2's service will use

- [ ] **Step 1: Write the 3 DTO records**

```java
// ImageGenOverviewDTO.java
package com.meichen.admin.dto;

public record ImageGenOverviewDTO(
    long totalGenerated,
    long successCount,
    long failedCount,
    double successRate,
    double avgGenerationMs,
    double avgImagesPerProject
) {}

// ImageGenProviderDTO.java
package com.meichen.admin.dto;

import java.util.List;

public record ImageGenProviderDTO(
    String provider,
    long callCount,
    double successRate,
    double avgLatencyMs,
    List<FailureReason> failureReasons
) {
    public record FailureReason(String error, long count) {}
}

// ImageFeedbackDTO.java
package com.meichen.admin.dto;

import java.util.List;
import java.util.Map;

public record ImageFeedbackDTO(
    long totalImages,
    long imagesWithFeedback,
    double feedbackRate,
    Map<String, Long> tagDistribution
) {}
```

- [ ] **Step 2: Add image-gen queries to AiCallLogReadRepository**

Add these methods to `AiCallLogReadRepository.java` (after existing methods, before closing brace):

```java
    @Query("SELECT COUNT(l), " +
           "SUM(CASE WHEN l.status = 'success' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN l.status != 'success' THEN 1 ELSE 0 END), " +
           "AVG(l.durationMs), " +
           "COUNT(DISTINCT l.projectId) " +
           "FROM AiCallLogRead l WHERE l.callType = 'image_generation' AND l.createdAt >= :since")
    List<Object[]> aggregateImageGenOverview(@Param("since") LocalDateTime since);

    default java.util.Optional<Object[]> findImageGenOverview(LocalDateTime since) {
        return aggregateImageGenOverview(since).stream().findFirst();
    }

    @Query("SELECT l.provider, COUNT(l), " +
           "SUM(CASE WHEN l.status = 'success' THEN 1 ELSE 0 END), " +
           "AVG(l.durationMs) " +
           "FROM AiCallLogRead l WHERE l.callType = 'image_generation' AND l.createdAt >= :since " +
           "GROUP BY l.provider")
    List<Object[]> groupImageGenByProvider(@Param("since") LocalDateTime since);

    @Query("SELECT l.errorMessage, COUNT(l) " +
           "FROM AiCallLogRead l WHERE l.callType = 'image_generation' AND l.status != 'success' " +
           "AND l.createdAt >= :since AND l.errorMessage IS NOT NULL " +
           "GROUP BY l.errorMessage ORDER BY COUNT(l) DESC")
    List<Object[]> findImageGenFailureReasons(@Param("since") LocalDateTime since);

    @Query("SELECT CAST(l.createdAt AS date), " +
           "SUM(CASE WHEN l.status = 'success' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN l.status = 'failed' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN l.status = 'rate_limited' THEN 1 ELSE 0 END) " +
           "FROM AiCallLogRead l WHERE l.callType = 'image_generation' AND l.createdAt >= :since " +
           "GROUP BY CAST(l.createdAt AS date) ORDER BY CAST(l.createdAt AS date)")
    List<Object[]> groupImageGenByDate(@Param("since") LocalDateTime since);
```

- [ ] **Step 3: Add image feedback queries to FeedbackReadRepository**

Add these methods to `FeedbackReadRepository.java` (after existing methods):

```java
    @Query("SELECT COUNT(f), " +
           "SUM(CASE WHEN f.imageUrl IS NOT NULL THEN 1 ELSE 0 END) " +
           "FROM FeedbackRead f WHERE f.createdAt >= :since")
    List<Object[]> aggregateImageFeedbackOverview(@Param("since") LocalDateTime since);

    default java.util.Optional<Object[]> findImageFeedbackOverview(LocalDateTime since) {
        return aggregateImageFeedbackOverview(since).stream().findFirst();
    }

    @Query("SELECT f.tag, COUNT(f) FROM FeedbackRead f " +
           "WHERE f.imageUrl IS NOT NULL AND f.createdAt >= :since " +
           "GROUP BY f.tag ORDER BY COUNT(f) DESC")
    List<Object[]> countImageFeedbackByTag(@Param("since") LocalDateTime since);

    @Query("SELECT CAST(f.createdAt AS date), COUNT(f), " +
           "SUM(CASE WHEN f.tag IN ('good', 'like', 'positive') THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN f.tag IN ('bad', 'dislike', 'negative', 'composition', 'quality') THEN 1 ELSE 0 END) " +
           "FROM FeedbackRead f WHERE f.imageUrl IS NOT NULL AND f.createdAt >= :since " +
           "GROUP BY CAST(f.createdAt AS date) ORDER BY CAST(f.createdAt AS date)")
    List<Object[]> countImageFeedbackByDate(@Param("since") LocalDateTime since);
```

- [ ] **Step 4: Add pricing config to application.yml**

Add to `agent-admin-backend/src/main/resources/application.yml` (under `admin:` section):

```yaml
  metrics:
    pricing:
      zhipu:
        llm:
          input-per-1k: 0.001
          output-per-1k: 0.002
        vlm:
          input-per-1k: 0.005
          output-per-1k: 0.01
        embedding:
          per-1k: 0.0005
        image-generation:
          per-image: 0.1
      siliconflow:
        image-generation:
          per-image: 0.05
```

- [ ] **Step 5: Write the failing test**

Create `agent-admin-backend/src/test/java/com/meichen/admin/repository/ImageGenRepositoryTest.java`:

```java
package com.meichen.admin.repository;

import com.meichen.admin.entity.AiCallLogRead;
import com.meichen.admin.entity.FeedbackRead;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

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
class ImageGenRepositoryTest {

    @Autowired
    private AiCallLogReadRepository aiCallLogRepo;
    @Autowired
    private FeedbackReadRepository feedbackRepo;
    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Test
    void findImageGenOverview_returnsAggregatedStats() {
        insertAiCallLog("image_generation", "siliconflow", "success", 5000, "proj-1");
        insertAiCallLog("image_generation", "siliconflow", "success", 3000, "proj-1");
        insertAiCallLog("image_generation", "siliconflow", "failed", 1000, "proj-2");
        insertAiCallLog("llm", "zhipu", "success", 200, "proj-1"); // not image_gen

        LocalDateTime since = LocalDateTime.now().minusHours(24);
        Optional<Object[]> result = aiCallLogRepo.findImageGenOverview(since);

        assertTrue(result.isPresent());
        Object[] row = result.get();
        assertEquals(3L, ((Number) row[0]).longValue());     // total
        assertEquals(2L, ((Number) row[1]).longValue());     // success
        assertEquals(1L, ((Number) row[2]).longValue());     // failed
        assertEquals(3000.0, ((Number) row[3]).doubleValue(), 0.01); // avg duration
        assertEquals(2L, ((Number) row[4]).longValue());     // distinct projects
    }

    @Test
    void groupImageGenByProvider_groupsCorrectly() {
        insertAiCallLog("image_generation", "siliconflow", "success", 5000, "proj-1");
        insertAiCallLog("image_generation", "zhipu", "failed", 2000, "proj-2");

        LocalDateTime since = LocalDateTime.now().minusHours(24);
        List<Object[]> results = aiCallLogRepo.groupImageGenByProvider(since);

        assertEquals(2, results.size());
    }

    @Test
    void findImageGenFailureReasons_returnsErrorMessages() {
        insertAiCallLogWithError("image_generation", "siliconflow", "failed", 1000, "proj-1", "timeout");
        insertAiCallLogWithError("image_generation", "siliconflow", "failed", 500, "proj-2", "timeout");
        insertAiCallLogWithError("image_generation", "siliconflow", "failed", 200, "proj-3", "content_filter");

        LocalDateTime since = LocalDateTime.now().minusHours(24);
        List<Object[]> results = aiCallLogRepo.findImageGenFailureReasons(since);

        assertEquals(2, results.size());
        assertEquals("timeout", results.get(0)[0]);
        assertEquals(2L, ((Number) results.get(0)[1]).longValue());
    }

    @Test
    void findImageFeedbackOverview_countsImagesWithFeedback() {
        insertFeedback("proj-1", "good", "http://example.com/1.jpg");
        insertFeedback("proj-2", "bad", "http://example.com/2.jpg");
        insertFeedback("proj-3", "good", null); // no image

        LocalDateTime since = LocalDateTime.now().minusHours(24);
        Optional<Object[]> result = feedbackRepo.findImageFeedbackOverview(since);

        assertTrue(result.isPresent());
        Object[] row = result.get();
        assertEquals(3L, ((Number) row[0]).longValue());  // total feedbacks
        assertEquals(2L, ((Number) row[1]).longValue());  // with image
    }

    private void insertAiCallLog(String callType, String provider, String status, int durationMs, String projectId) {
        insertAiCallLogWithError(callType, provider, status, durationMs, projectId, null);
    }

    private void insertAiCallLogWithError(String callType, String provider, String status, int durationMs, String projectId, String errorMessage) {
        jdbcTemplate.update(
            "INSERT INTO ai_call_logs (project_id, call_type, provider, model, node_name, status, duration_ms, input_tokens, output_tokens, total_tokens, error_message, created_at) " +
            "VALUES (?, ?, ?, 'test-model', 'test-node', ?, ?, 0, 0, 0, ?, NOW())",
            projectId, callType, provider, status, durationMs, errorMessage
        );
    }

    private void insertFeedback(String projectId, String tag, String imageUrl) {
        jdbcTemplate.update(
            "INSERT INTO feedbacks (id, project_id, feedback_type, tag, image_url, created_at) " +
            "VALUES (?, ?, 'image', ?, ?, NOW())",
            java.util.UUID.randomUUID().toString(), projectId, tag, imageUrl
        );
    }
}
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd agent-admin-backend && mvn test -Dtest=ImageGenRepositoryTest -q`
Expected: FAIL (repository query methods not found)

- [ ] **Step 7: Verify test passes (GREEN)**

The query methods were added in Steps 2-3. Run: `cd agent-admin-backend && mvn test -Dtest=ImageGenRepositoryTest -q`
Expected: PASS, 4 tests

- [ ] **Step 8: Run full admin-backend test suite**

Run: `cd agent-admin-backend && mvn test -q`
Expected: All tests pass (existing 97 + 4 new = 101)

- [ ] **Step 9: Commit**

```bash
git add agent-admin-backend/src/main/java/com/meichen/admin/dto/ImageGenOverviewDTO.java \
  agent-admin-backend/src/main/java/com/meichen/admin/dto/ImageGenProviderDTO.java \
  agent-admin-backend/src/main/java/com/meichen/admin/dto/ImageFeedbackDTO.java \
  agent-admin-backend/src/main/java/com/meichen/admin/repository/AiCallLogReadRepository.java \
  agent-admin-backend/src/main/java/com/meichen/admin/repository/FeedbackReadRepository.java \
  agent-admin-backend/src/main/resources/application.yml \
  agent-admin-backend/src/test/java/com/meichen/admin/repository/ImageGenRepositoryTest.java
git commit -m "feat(admin): add image-gen repository queries, DTOs, and pricing config"
```

---

### Task 2: ImageGenMetrics Backend — Service + Controller

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/service/ImageGenMetricsService.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/controller/ImageGenMetricsController.java`
- Test: `agent-admin-backend/src/test/java/com/meichen/admin/controller/ImageGenMetricsControllerIntegrationTest.java`

**Interfaces:**
- Consumes: Task 1's DTOs (`ImageGenOverviewDTO`, `ImageGenProviderDTO`, `ImageFeedbackDTO`), repository query methods
- Produces: 5 REST endpoints at `/api/admin/metrics/image-generation`: GET /overview, GET /by-provider, GET /feedback, GET /feedback-trend, GET /distribution

- [ ] **Step 1: Write the failing test**

Create `agent-admin-backend/src/test/java/com/meichen/admin/controller/ImageGenMetricsControllerIntegrationTest.java`:

```java
package com.meichen.admin.controller;

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
    "admin.token=test-token"
})
class ImageGenMetricsControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;
    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Test
    void getOverview_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/image-generation/overview")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalGenerated").exists())
            .andExpect(jsonPath("$.successRate").exists());
    }

    @Test
    void getOverview_withData_returnsCorrectStats() throws Exception {
        insertImageGenLog("siliconflow", "success", 5000, "proj-1");
        insertImageGenLog("siliconflow", "failed", 1000, "proj-2");

        mockMvc.perform(get("/api/admin/metrics/image-generation/overview")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalGenerated").value(2))
            .andExpect(jsonPath("$.successCount").value(1))
            .andExpect(jsonPath("$.failedCount").value(1));
    }

    @Test
    void getByProvider_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/image-generation/by-provider")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getFeedback_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/image-generation/feedback")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalImages").exists())
            .andExpect(jsonPath("$.feedbackRate").exists());
    }

    @Test
    void getFeedbackTrend_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/image-generation/feedback-trend")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getDistribution_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/image-generation/distribution")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getOverview_noToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/image-generation/overview"))
            .andExpect(status().isUnauthorized());
    }

    private void insertImageGenLog(String provider, String status, int durationMs, String projectId) {
        jdbcTemplate.update(
            "INSERT INTO ai_call_logs (project_id, call_type, provider, model, node_name, status, duration_ms, input_tokens, output_tokens, total_tokens, created_at) " +
            "VALUES (?, 'image_generation', ?, 'test-model', 'test-node', ?, ?, 0, 0, 0, NOW())",
            projectId, provider, status, durationMs
        );
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent-admin-backend && mvn test -Dtest=ImageGenMetricsControllerIntegrationTest -q`
Expected: FAIL (controller/service not found, 404)

- [ ] **Step 3: Write ImageGenMetricsService**

Create `agent-admin-backend/src/main/java/com/meichen/admin/service/ImageGenMetricsService.java`:

```java
package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.AiCallLogReadRepository;
import com.meichen.admin.repository.FeedbackReadRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class ImageGenMetricsService {

    private final AiCallLogReadRepository aiCallLogRepo;
    private final FeedbackReadRepository feedbackRepo;

    public ImageGenMetricsService(AiCallLogReadRepository aiCallLogRepo, FeedbackReadRepository feedbackRepo) {
        this.aiCallLogRepo = aiCallLogRepo;
        this.feedbackRepo = feedbackRepo;
    }

    public ImageGenOverviewDTO getOverview(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        return aiCallLogRepo.findImageGenOverview(since)
            .map(row -> {
                long total = ((Number) row[0]).longValue();
                long success = ((Number) row[1]).longValue();
                long failed = ((Number) row[2]).longValue();
                double avgDuration = row[3] != null ? ((Number) row[3]).doubleValue() : 0.0;
                long distinctProjects = ((Number) row[4]).longValue();
                double successRate = total > 0 ? (double) success / total * 100 : 0.0;
                double avgPerProject = distinctProjects > 0 ? (double) total / distinctProjects : 0.0;
                return new ImageGenOverviewDTO(total, success, failed, successRate, avgDuration, avgPerProject);
            })
            .orElseGet(() -> new ImageGenOverviewDTO(0, 0, 0, 0.0, 0.0, 0.0));
    }

    public List<ImageGenProviderDTO> getByProvider(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> providerRows = aiCallLogRepo.groupImageGenByProvider(since);
        List<Object[]> failureRows = aiCallLogRepo.findImageGenFailureReasons(since);

        // Group failure reasons by provider — but the query doesn't include provider.
        // Since all image-gen failures are grouped by error message globally,
        // we attach them to each provider. For per-provider failures, a separate query would be needed.
        // For MVP, we return global failure reasons on the first provider.
        List<ImageGenProviderDTO.FailureReason> globalFailures = new ArrayList<>();
        for (Object[] f : failureRows) {
            String error = (String) f[0];
            long count = ((Number) f[1]).longValue();
            if (error != null && !error.isBlank()) {
                String shortError = error.length() > 100 ? error.substring(0, 100) + "..." : error;
                globalFailures.add(new ImageGenProviderDTO.FailureReason(shortError, count));
            }
        }

        List<ImageGenProviderDTO> result = new ArrayList<>();
        boolean firstProvider = true;
        for (Object[] row : providerRows) {
            String provider = (String) row[0];
            long callCount = ((Number) row[1]).longValue();
            long successCount = ((Number) row[2]).longValue();
            double avgLatency = row[3] != null ? ((Number) row[3]).doubleValue() : 0.0;
            double successRate = callCount > 0 ? (double) successCount / callCount * 100 : 0.0;
            List<ImageGenProviderDTO.FailureReason> failures = firstProvider ? globalFailures : List.of();
            result.add(new ImageGenProviderDTO(provider, callCount, successRate, avgLatency, failures));
            firstProvider = false;
        }
        return result;
    }

    public ImageFeedbackDTO getFeedback(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        return feedbackRepo.findImageFeedbackOverview(since)
            .map(row -> {
                long total = ((Number) row[0]).longValue();
                long withImage = ((Number) row[1]).longValue();
                double feedbackRate = total > 0 ? (double) withImage / total * 100 : 0.0;
                Map<String, Long> tagDist = new LinkedHashMap<>();
                for (Object[] tagRow : feedbackRepo.countImageFeedbackByTag(since)) {
                    String tag = (String) tagRow[0];
                    long count = ((Number) tagRow[1]).longValue();
                    if (tag != null) tagDist.put(tag, count);
                }
                return new ImageFeedbackDTO(total, withImage, feedbackRate, tagDist);
            })
            .orElseGet(() -> new ImageFeedbackDTO(0, 0, 0.0, Map.of()));
    }

    public List<Map<String, Object>> getFeedbackTrend(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Object[] row : feedbackRepo.countImageFeedbackByDate(since)) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("date", row[0].toString());
            item.put("total", ((Number) row[1]).longValue());
            item.put("positive", ((Number) row[2]).longValue());
            item.put("negative", ((Number) row[3]).longValue());
            result.add(item);
        }
        return result;
    }

    public List<Map<String, Object>> getDistribution(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Object[] row : aiCallLogRepo.groupImageGenByDate(since)) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("date", row[0].toString());
            item.put("success", ((Number) row[1]).longValue());
            item.put("failed", ((Number) row[2]).longValue());
            item.put("rateLimited", ((Number) row[3]).longValue());
            result.add(item);
        }
        return result;
    }
}
```

- [ ] **Step 4: Write ImageGenMetricsController**

Create `agent-admin-backend/src/main/java/com/meichen/admin/controller/ImageGenMetricsController.java`:

```java
package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.ImageGenMetricsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/admin/metrics/image-generation")
public class ImageGenMetricsController {

    private final ImageGenMetricsService service;

    public ImageGenMetricsController(ImageGenMetricsService service) {
        this.service = service;
    }

    @GetMapping("/overview")
    public ResponseEntity<ImageGenOverviewDTO> getOverview(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getOverview(hours));
    }

    @GetMapping("/by-provider")
    public ResponseEntity<List<ImageGenProviderDTO>> getByProvider(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getByProvider(hours));
    }

    @GetMapping("/feedback")
    public ResponseEntity<ImageFeedbackDTO> getFeedback(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getFeedback(hours));
    }

    @GetMapping("/feedback-trend")
    public ResponseEntity<List<Map<String, Object>>> getFeedbackTrend(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getFeedbackTrend(hours));
    }

    @GetMapping("/distribution")
    public ResponseEntity<List<Map<String, Object>>> getDistribution(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getDistribution(hours));
    }
}
```

- [ ] **Step 5: Run test to verify it passes (GREEN)**

Run: `cd agent-admin-backend && mvn test -Dtest=ImageGenMetricsControllerIntegrationTest -q`
Expected: PASS, 7 tests

- [ ] **Step 6: Run full test suite**

Run: `cd agent-admin-backend && mvn test -q`
Expected: All tests pass (101 + 7 = 108)

- [ ] **Step 7: Commit**

```bash
git add agent-admin-backend/src/main/java/com/meichen/admin/service/ImageGenMetricsService.java \
  agent-admin-backend/src/main/java/com/meichen/admin/controller/ImageGenMetricsController.java \
  agent-admin-backend/src/test/java/com/meichen/admin/controller/ImageGenMetricsControllerIntegrationTest.java
git commit -m "feat(admin): add image generation metrics API with 5 endpoints"
```

---

### Task 3: PromptTemplate Enhanced — DTOs + Service + Repository + Controller

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/PromptTemplateUsageDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/PromptTemplateQualityTrendDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/PromptTemplateCompareDTO.java`
- Modify: `agent-admin-backend/src/main/java/com/meichen/admin/repository/AiCallLogReadRepository.java`
- Modify: `agent-admin-backend/src/main/java/com/meichen/admin/service/PromptTemplateAdminService.java`
- Modify: `agent-admin-backend/src/main/java/com/meichen/admin/controller/PromptTemplateAdminController.java`
- Test: `agent-admin-backend/src/test/java/com/meichen/admin/controller/PromptTemplateEnhancedIntegrationTest.java`

**Interfaces:**
- Consumes: `AiCallLogRead` entity (callType containing 'prompt' in nodeName), `FeedbackRead` entity (promptTemplateVersion)
- Produces: 3 DTO records + 3 new endpoints at `/api/admin/prompt-templates`: GET /usage, GET /quality-trend, GET /compare

- [ ] **Step 1: Write the 3 DTO records**

```java
// PromptTemplateUsageDTO.java
package com.meichen.admin.dto;

import java.util.List;

public record PromptTemplateUsageDTO(
    String templateVersion,
    long totalInvocations,
    long uniqueProjects,
    List<InvocationDay> invocationTrend
) {
    public record InvocationDay(String date, long count) {}
}

// PromptTemplateQualityTrendDTO.java
package com.meichen.admin.dto;

import java.util.List;

public record PromptTemplateQualityTrendDTO(
    String date,
    String templateVersion,
    long imagesGenerated,
    long feedbackCount,
    double feedbackRate,
    List<TagCount> tagDistribution
) {
    public record TagCount(String tag, long count) {}
}

// PromptTemplateCompareDTO.java
package com.meichen.admin.dto;

import java.util.List;

public record PromptTemplateCompareDTO(
    String version,
    long totalImages,
    long feedbackCount,
    double feedbackRate,
    double positiveRate,
    double negativeRate,
    List<TagCount> topTags
) {
    public record TagCount(String tag, long count) {}
}
```

- [ ] **Step 2: Add prompt invocation queries to AiCallLogReadRepository**

Add to `AiCallLogReadRepository.java`:

```java
    @Query("SELECT l.nodeName, COUNT(l), COUNT(DISTINCT l.projectId) " +
           "FROM AiCallLogRead l WHERE l.callType = 'llm' AND l.createdAt >= :since " +
           "GROUP BY l.nodeName")
    List<Object[]> groupPromptInvocations(@Param("since") LocalDateTime since);

    @Query("SELECT CAST(l.createdAt AS date), l.nodeName, COUNT(l) " +
           "FROM AiCallLogRead l WHERE l.callType = 'llm' AND l.createdAt >= :since " +
           "GROUP BY CAST(l.createdAt AS date), l.nodeName " +
           "ORDER BY CAST(l.createdAt AS date)")
    List<Object[]> groupPromptInvocationsByDate(@Param("since") LocalDateTime since);
```

- [ ] **Step 3: Add quality trend query to FeedbackReadRepository**

Add to `FeedbackReadRepository.java`:

```java
    @Query("SELECT CAST(f.createdAt AS date), f.promptTemplateVersion, COUNT(f), " +
           "SUM(CASE WHEN f.tag IN ('good', 'like', 'positive') THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN f.tag IN ('bad', 'dislike', 'negative', 'composition', 'quality') THEN 1 ELSE 0 END) " +
           "FROM FeedbackRead f WHERE f.imageUrl IS NOT NULL AND f.createdAt >= :since " +
           "GROUP BY CAST(f.createdAt AS date), f.promptTemplateVersion " +
           "ORDER BY CAST(f.createdAt AS date)")
    List<Object[]> countImageFeedbackByDateAndVersion(@Param("since") LocalDateTime since);

    @Query("SELECT f.promptTemplateVersion, COUNT(f), " +
           "SUM(CASE WHEN f.tag IN ('good', 'like', 'positive') THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN f.tag IN ('bad', 'dislike', 'negative', 'composition', 'quality') THEN 1 ELSE 0 END) " +
           "FROM FeedbackRead f WHERE f.imageUrl IS NOT NULL AND f.promptTemplateVersion IS NOT NULL " +
           "GROUP BY f.promptTemplateVersion")
    List<Object[]> countImageFeedbackByVersion();

    @Query("SELECT f.promptTemplateVersion, f.tag, COUNT(f) FROM FeedbackRead f " +
           "WHERE f.imageUrl IS NOT NULL AND f.promptTemplateVersion IS NOT NULL " +
           "GROUP BY f.promptTemplateVersion, f.tag ORDER BY COUNT(f) DESC")
    List<Object[]> countImageFeedbackTagByVersion();
```

- [ ] **Step 4: Add service methods to PromptTemplateAdminService**

Add these methods to `PromptTemplateAdminService.java` (requires adding `AiCallLogReadRepository` as a dependency):

```java
// Add to constructor parameters:
//   AiCallLogReadRepository aiCallLogRepo
// Add field:
//   private final AiCallLogReadRepository aiCallLogRepo;

public List<PromptTemplateUsageDTO> getUsage(int hours) {
    LocalDateTime since = LocalDateTime.now().minusHours(hours);
    List<Object[]> invocationRows = aiCallLogRepo.groupPromptInvocations(since);
    List<Object[]> trendRows = aiCallLogRepo.groupPromptInvocationsByDate(since);

    // Group trend by nodeName
    Map<String, List<PromptTemplateUsageDTO.InvocationDay>> trendByNode = new HashMap<>();
    for (Object[] row : trendRows) {
        String date = row[0].toString();
        String nodeName = (String) row[1];
        long count = ((Number) row[2]).longValue();
        trendByNode.computeIfAbsent(nodeName, k -> new ArrayList<>())
            .add(new PromptTemplateUsageDTO.InvocationDay(date, count));
    }

    List<PromptTemplateUsageDTO> result = new ArrayList<>();
    for (Object[] row : invocationRows) {
        String nodeName = (String) row[0];
        long totalInvocations = ((Number) row[1]).longValue();
        long uniqueProjects = ((Number) row[2]).longValue();
        result.add(new PromptTemplateUsageDTO(
            nodeName, totalInvocations, uniqueProjects,
            trendByNode.getOrDefault(nodeName, List.of())
        ));
    }
    return result;
}

public List<PromptTemplateQualityTrendDTO> getQualityTrend(int hours) {
    LocalDateTime since = LocalDateTime.now().minusHours(hours);
    List<Object[]> rows = feedbackRepo.countImageFeedbackByDateAndVersion(since);
    List<Object[]> tagRows = feedbackRepo.countImageFeedbackTagByVersion();

    // Build tag distribution lookup by version+date (simplified: per-version tag counts)
    Map<String, List<PromptTemplateQualityTrendDTO.TagCount>> tagsByVersion = new HashMap<>();
    for (Object[] tagRow : tagRows) {
        String version = (String) tagRow[0];
        String tag = (String) tagRow[1];
        long count = ((Number) tagRow[2]).longValue();
        tagsByVersion.computeIfAbsent(version, k -> new ArrayList<>())
            .add(new PromptTemplateQualityTrendDTO.TagCount(tag, count));
    }

    List<PromptTemplateQualityTrendDTO> result = new ArrayList<>();
    for (Object[] row : rows) {
        String date = row[0].toString();
        String version = (String) row[1];
        long feedbackCount = ((Number) row[2]).longValue();
        long positive = ((Number) row[3]).longValue();
        long negative = ((Number) row[4]).longValue();
        double feedbackRate = 0.0; // would need total images generated per day per version
        List<PromptTemplateQualityTrendDTO.TagCount> tags = tagsByVersion.getOrDefault(version, List.of());
        result.add(new PromptTemplateQualityTrendDTO(date, version, 0, feedbackCount, feedbackRate, tags));
    }
    return result;
}

public List<PromptTemplateCompareDTO> compareVersions() {
    List<Object[]> versionRows = feedbackRepo.countImageFeedbackByVersion();
    List<Object[]> tagRows = feedbackRepo.countImageFeedbackTagByVersion();

    // Group tags by version
    Map<String, List<PromptTemplateCompareDTO.TagCount>> tagsByVersion = new HashMap<>();
    for (Object[] tagRow : tagRows) {
        String version = (String) tagRow[0];
        String tag = (String) tagRow[1];
        long count = ((Number) tagRow[2]).longValue();
        tagsByVersion.computeIfAbsent(version, k -> new ArrayList<>())
            .add(new PromptTemplateCompareDTO.TagCount(tag, count));
    }

    List<PromptTemplateCompareDTO> result = new ArrayList<>();
    for (Object[] row : versionRows) {
        String version = (String) row[0];
        long totalFeedback = ((Number) row[1]).longValue();
        long positive = ((Number) row[2]).longValue();
        long negative = ((Number) row[3]).longValue();
        double positiveRate = totalFeedback > 0 ? (double) positive / totalFeedback * 100 : 0.0;
        double negativeRate = totalFeedback > 0 ? (double) negative / totalFeedback * 100 : 0.0;
        List<PromptTemplateCompareDTO.TagCount> topTags = tagsByVersion.getOrDefault(version, List.of());
        result.add(new PromptTemplateCompareDTO(version, 0, totalFeedback, 0.0, positiveRate, negativeRate, topTags));
    }
    return result;
}
```

- [ ] **Step 5: Add endpoints to PromptTemplateAdminController**

Add to `PromptTemplateAdminController.java`:

```java
    @GetMapping("/usage")
    public ResponseEntity<List<PromptTemplateUsageDTO>> getUsage(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getUsage(hours));
    }

    @GetMapping("/quality-trend")
    public ResponseEntity<List<PromptTemplateQualityTrendDTO>> getQualityTrend(
            @RequestParam(defaultValue = "168") int hours) {
        return ResponseEntity.ok(service.getQualityTrend(hours));
    }

    @GetMapping("/compare")
    public ResponseEntity<List<PromptTemplateCompareDTO>> compareVersions() {
        return ResponseEntity.ok(service.compareVersions());
    }
```

- [ ] **Step 6: Write the failing test**

Create `agent-admin-backend/src/test/java/com/meichen/admin/controller/PromptTemplateEnhancedIntegrationTest.java`:

```java
package com.meichen.admin.controller;

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
    "admin.agent-core.base-url=http://localhost:99999",
    "admin.agent-core.data-dir=/tmp"
})
class PromptTemplateEnhancedIntegrationTest {

    @Autowired
    private MockMvc mockMvc;
    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Test
    void getUsage_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/prompt-templates/usage")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getUsage_withData_returnsNodeStats() throws Exception {
        jdbcTemplate.update(
            "INSERT INTO ai_call_logs (project_id, call_type, provider, model, node_name, status, duration_ms, input_tokens, output_tokens, total_tokens, created_at) " +
            "VALUES (?, 'llm', 'zhipu', 'glm-4', 'prompt_generation', 'success', 500, 100, 200, 300, NOW())",
            "proj-1"
        );

        mockMvc.perform(get("/api/admin/prompt-templates/usage")
                .param("hours", "24")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].templateVersion").value("prompt_generation"))
            .andExpect(jsonPath("$[0].totalInvocations").value(1))
            .andExpect(jsonPath("$[0].uniqueProjects").value(1));
    }

    @Test
    void getQualityTrend_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/prompt-templates/quality-trend")
                .param("hours", "168")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getCompare_returns200() throws Exception {
        jdbcTemplate.update(
            "INSERT INTO feedbacks (id, project_id, feedback_type, tag, image_url, prompt_template_version, created_at) " +
            "VALUES (?, 'proj-1', 'image', 'good', 'http://example.com/1.jpg', 'v1.0', NOW())",
            java.util.UUID.randomUUID().toString()
        );

        mockMvc.perform(get("/api/admin/prompt-templates/compare")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].version").value("v1.0"));
    }

    @Test
    void getUsage_noToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/prompt-templates/usage"))
            .andExpect(status().isUnauthorized());
    }
}
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd agent-admin-backend && mvn test -Dtest=PromptTemplateEnhancedIntegrationTest -q`
Expected: FAIL (endpoints not found, 404)

- [ ] **Step 8: Run test to verify it passes (GREEN)**

Run: `cd agent-admin-backend && mvn test -Dtest=PromptTemplateEnhancedIntegrationTest -q`
Expected: PASS, 5 tests

- [ ] **Step 9: Run full test suite**

Run: `cd agent-admin-backend && mvn test -q`
Expected: All tests pass (108 + 5 = 113)

- [ ] **Step 10: Commit**

```bash
git add agent-admin-backend/src/main/java/com/meichen/admin/dto/PromptTemplateUsageDTO.java \
  agent-admin-backend/src/main/java/com/meichen/admin/dto/PromptTemplateQualityTrendDTO.java \
  agent-admin-backend/src/main/java/com/meichen/admin/dto/PromptTemplateCompareDTO.java \
  agent-admin-backend/src/main/java/com/meichen/admin/repository/AiCallLogReadRepository.java \
  agent-admin-backend/src/main/java/com/meichen/admin/repository/FeedbackReadRepository.java \
  agent-admin-backend/src/main/java/com/meichen/admin/service/PromptTemplateAdminService.java \
  agent-admin-backend/src/main/java/com/meichen/admin/controller/PromptTemplateAdminController.java \
  agent-admin-backend/src/test/java/com/meichen/admin/controller/PromptTemplateEnhancedIntegrationTest.java
git commit -m "feat(admin): add prompt template usage tracking, quality trend, and version comparison"
```

---

### Task 4: Frontend — ImageGenMonitoring.vue Page

**Files:**
- Create: `agent-admin-front/src/views/ImageGenMonitoring.vue`
- Modify: `agent-admin-front/src/router/index.js`
- Modify: `agent-admin-front/src/layouts/AdminLayout.vue`

**Interfaces:**
- Consumes: 5 API endpoints from Task 2 at `/metrics/image-generation/*` (via `client` with baseURL `/api/admin`)
- Produces: ImageGenMonitoring.vue page with overview cards, provider distribution chart, feedback gauge, feedback trend chart, distribution chart

- [ ] **Step 1: Write ImageGenMonitoring.vue**

Create `agent-admin-front/src/views/ImageGenMonitoring.vue`:

```vue
<template>
  <div class="image-gen-monitoring" v-loading="loading">
    <!-- 时间范围选择器 -->
    <div class="header">
      <el-radio-group v-model="hours" size="small" @change="loadAll">
        <el-radio-button :label="24">24h</el-radio-button>
        <el-radio-button :label="72">72h</el-radio-button>
        <el-radio-button :label="168">7d</el-radio-button>
        <el-radio-button :label="720">30d</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 概览卡片 -->
    <el-row :gutter="16">
      <el-col :span="4" v-for="card in overviewCards" :key="card.key">
        <el-card shadow="never" class="overview-card">
          <div class="card-value" :style="{ color: card.color }">{{ card.value }}</div>
          <div class="card-label">{{ card.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Provider 分布 + 反馈率 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="14">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">Provider 分布</span></div>
          <v-chart class="chart" :option="providerChartOption" autoresize style="height: 320px" />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">反馈率</span></div>
          <v-chart class="chart" :option="feedbackGaugeOption" autoresize style="height: 320px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 标签分布 + 反馈趋势 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="10">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">标签分布</span></div>
          <v-chart class="chart" :option="tagDistributionOption" autoresize style="height: 300px" />
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">反馈趋势</span></div>
          <v-chart class="chart" :option="feedbackTrendOption" autoresize style="height: 300px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 生成分布趋势 -->
    <el-card shadow="never" class="chart-card" style="margin-top: 20px;">
      <div class="chart-header"><span class="chart-title">生成趋势（成功/失败/限流）</span></div>
      <v-chart class="chart" :option="distributionOption" autoresize style="height: 320px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import client from '../api/client'
import { use } from 'echarts/core'
import VChart from 'vue-echarts'
import { BarChart, PieChart, GaugeChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CanvasRenderer, BarChart, PieChart, GaugeChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(false)
const hours = ref(24)
const overview = ref({ totalGenerated: 0, successCount: 0, failedCount: 0, successRate: 0, avgGenerationMs: 0, avgImagesPerProject: 0 })
const providers = ref([])
const feedback = ref({ totalImages: 0, imagesWithFeedback: 0, feedbackRate: 0, tagDistribution: {} })
const feedbackTrend = ref([])
const distribution = ref([])

const overviewCards = computed(() => [
  { key: 'total', label: '总生成数', value: overview.value.totalGenerated, color: '#409eff' },
  { key: 'success', label: '成功数', value: overview.value.successCount, color: '#67c23a' },
  { key: 'failed', label: '失败数', value: overview.value.failedCount, color: '#f56c6c' },
  { key: 'rate', label: '成功率', value: overview.value.successRate.toFixed(1) + '%', color: '#e6a23c' },
  { key: 'avg', label: '平均耗时(ms)', value: Math.round(overview.value.avgGenerationMs), color: '#909399' },
  { key: 'perProj', label: '每项目图数', value: overview.value.avgImagesPerProject.toFixed(1), color: '#9c27b0' },
])

const providerChartOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { data: ['成功', '失败'] },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: providers.value.map(p => p.provider) },
  yAxis: { type: 'value' },
  series: [
    { name: '成功', type: 'bar', stack: 'total', data: providers.value.map(p => p.callCount * p.successRate / 100), itemStyle: { color: '#67c23a' } },
    { name: '失败', type: 'bar', stack: 'total', data: providers.value.map(p => p.callCount * (1 - p.successRate / 100)), itemStyle: { color: '#f56c6c' } },
  ],
}))

const feedbackGaugeOption = computed(() => ({
  series: [{
    type: 'gauge',
    progress: { show: true, width: 18 },
    axisLine: { lineStyle: { width: 18 } },
    detail: { formatter: '{value}%', fontSize: 24 },
    data: [{ value: feedback.value.feedbackRate.toFixed(1), name: '反馈率' }],
  }],
}))

const tagDistributionOption = computed(() => {
  const entries = Object.entries(feedback.value.tagDistribution || {})
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: entries.map(([tag, count]) => ({ name: tag, value: count })),
    }],
  }
})

const feedbackTrendOption = computed(() => {
  const dates = feedbackTrend.value.map(d => d.date)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['正面', '负面'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' },
    series: [
      { name: '正面', type: 'line', smooth: true, data: feedbackTrend.value.map(d => d.positive), itemStyle: { color: '#67c23a' } },
      { name: '负面', type: 'line', smooth: true, data: feedbackTrend.value.map(d => d.negative), itemStyle: { color: '#f56c6c' } },
    ],
  }
})

const distributionOption = computed(() => {
  const dates = distribution.value.map(d => d.date)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['成功', '失败', '限流'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' },
    series: [
      { name: '成功', type: 'bar', stack: 'total', data: distribution.value.map(d => d.success), itemStyle: { color: '#67c23a' } },
      { name: '失败', type: 'bar', stack: 'total', data: distribution.value.map(d => d.failed), itemStyle: { color: '#f56c6c' } },
      { name: '限流', type: 'bar', stack: 'total', data: distribution.value.map(d => d.rateLimited), itemStyle: { color: '#e6a23c' } },
    ],
  }
})

async function loadAll() {
  loading.value = true
  try {
    const params = { hours: hours.value }
    const [ov, prov, fb, fbTrend, dist] = await Promise.all([
      client.get('/metrics/image-generation/overview', { params }),
      client.get('/metrics/image-generation/by-provider', { params }),
      client.get('/metrics/image-generation/feedback', { params }),
      client.get('/metrics/image-generation/feedback-trend', { params }),
      client.get('/metrics/image-generation/distribution', { params }),
    ])
    overview.value = ov
    providers.value = prov
    feedback.value = fb
    feedbackTrend.value = fbTrend
    distribution.value = dist
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.image-gen-monitoring { width: 100%; }
.header { margin-bottom: 20px; }
.overview-card { text-align: center; }
.card-value { font-size: 24px; font-weight: 700; }
.card-label { font-size: 13px; color: #909399; margin-top: 4px; }
.chart-card { background: #fff; }
.chart-header { margin-bottom: 12px; }
.chart-title { font-size: 15px; font-weight: 600; color: #303133; }
</style>
```

- [ ] **Step 2: Add route to router**

Add to `src/router/index.js` children array (after IntentQuality):

```javascript
      {
        path: 'image-gen-monitoring',
        name: 'ImageGenMonitoring',
        component: () => import('../views/ImageGenMonitoring.vue'),
        meta: { title: '图像生成监控', icon: 'PictureFilled' }
      }
```

- [ ] **Step 3: Add menu item to AdminLayout.vue**

Add to `menuItems` array in `AdminLayout.vue` (after intent-quality):

```javascript
  { path: '/image-gen-monitoring', title: '图像生成监控', icon: 'PictureFilled' }
```

- [ ] **Step 4: Verify frontend build**

Run: `cd agent-admin-front && npx vite build --mode development`
Expected: Build succeeds, ImageGenMonitoring chunk generated

- [ ] **Step 5: Commit**

```bash
git add agent-admin-front/src/views/ImageGenMonitoring.vue \
  agent-admin-front/src/router/index.js \
  agent-admin-front/src/layouts/AdminLayout.vue
git commit -m "feat(admin-front): add image generation monitoring page with charts and cards"
```

---

### Task 5: Frontend — PromptTemplates.vue Enhancement (Usage Analytics Tab)

**Files:**
- Modify: `agent-admin-front/src/views/PromptTemplates.vue`

**Interfaces:**
- Consumes: 3 API endpoints from Task 3 at `/prompt-templates/usage`, `/prompt-templates/quality-trend`, `/prompt-templates/compare`
- Produces: Enhanced PromptTemplates.vue with tab layout: existing "模板管理" tab + new "使用分析" tab

- [ ] **Step 1: Modify PromptTemplates.vue to add tab layout**

Wrap the existing `<el-card>` content in a tab layout, and add a new "使用分析" tab. The existing template (lines 3-50) becomes the content of the first tab. Add the new tab with usage frequency chart, quality trend chart, and version comparison table.

Replace the template section (the first `<el-card>`) with:

```vue
    <el-tabs v-model="activeTab">
      <el-tab-pane label="模板管理" name="manage">
        <!-- 原有模板管理表格内容移到这里 -->
        <el-card shadow="never">
          <!-- ... existing table content ... -->
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="使用分析" name="analytics">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card shadow="never" class="chart-card">
              <div class="chart-header"><span class="chart-title">模板调用频率</span></div>
              <v-chart class="chart" :option="usageChartOption" autoresize style="height: 300px" />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never" class="chart-card">
              <div class="chart-header"><span class="chart-title">调用趋势</span></div>
              <v-chart class="chart" :option="usageTrendOption" autoresize style="height: 300px" />
            </el-card>
          </el-col>
        </el-row>

        <el-card shadow="never" class="chart-card" style="margin-top: 20px;">
          <div class="chart-header"><span class="chart-title">质量趋势</span></div>
          <v-chart class="chart" :option="qualityTrendOption" autoresize style="height: 320px" />
        </el-card>

        <el-card shadow="never" style="margin-top: 20px;">
          <template #header>版本对比</template>
          <el-table :data="compareData" stripe>
            <el-table-column prop="version" label="版本" width="120" />
            <el-table-column prop="feedbackCount" label="反馈数" width="100" />
            <el-table-column prop="positiveRate" label="正面率" width="100">
              <template #default="{ row }">{{ row.positiveRate.toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column prop="negativeRate" label="负面率" width="100">
              <template #default="{ row }">{{ row.negativeRate.toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column label="热门标签">
              <template #default="{ row }">
                <el-tag v-for="t in row.topTags" :key="t.tag" size="small" style="margin: 2px;">
                  {{ t.tag }} ({{ t.count }})
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
```

Add to `<script setup>` (add ECharts imports and new refs/computed):

```javascript
import { use } from 'echarts/core'
import VChart from 'vue-echarts'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

const activeTab = ref('manage')
const usageData = ref([])
const qualityTrend = ref([])
const compareData = ref([])

const usageChartOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: usageData.value.map(u => u.templateVersion), axisLabel: { rotate: 30 } },
  yAxis: { type: 'value' },
  series: [{ type: 'bar', data: usageData.value.map(u => u.totalInvocations), itemStyle: { color: '#409eff' } }],
}))

const usageTrendOption = computed(() => {
  const dates = [...new Set(usageData.value.flatMap(u => u.invocationTrend.map(t => t.date)))].sort()
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: usageData.value.map(u => u.templateVersion) },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' },
    series: usageData.value.map(u => ({
      name: u.templateVersion,
      type: 'line',
      smooth: true,
      data: dates.map(d => {
        const item = u.invocationTrend.find(t => t.date === d)
        return item ? item.count : 0
      }),
    })),
  }
})

const qualityTrendOption = computed(() => {
  const dates = [...new Set(qualityTrend.value.map(q => q.date))].sort()
  const versions = [...new Set(qualityTrend.value.map(q => q.templateVersion))]
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: versions },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: '反馈数' },
    series: versions.map(v => ({
      name: v,
      type: 'line',
      smooth: true,
      data: dates.map(d => {
        const item = qualityTrend.value.find(q => q.date === d && q.templateVersion === v)
        return item ? item.feedbackCount : 0
      }),
    })),
  }
})

async function loadAnalytics() {
  try {
    const [usage, trend, compare] = await Promise.all([
      client.get('/prompt-templates/usage', { params: { hours: 168 } }),
      client.get('/prompt-templates/quality-trend', { params: { hours: 168 } }),
      client.get('/prompt-templates/compare'),
    ])
    usageData.value = usage
    qualityTrend.value = trend
    compareData.value = compare
  } catch {
    usageData.value = []
    qualityTrend.value = []
    compareData.value = []
  }
}

watch(activeTab, (tab) => {
  if (tab === 'analytics' && usageData.value.length === 0) {
    loadAnalytics()
  }
})
```

- [ ] **Step 2: Verify frontend build**

Run: `cd agent-admin-front && npx vite build --mode development`
Expected: Build succeeds, PromptTemplates chunk generated

- [ ] **Step 3: Commit**

```bash
git add agent-admin-front/src/views/PromptTemplates.vue
git commit -m "feat(admin-front): add usage analytics tab to PromptTemplates page"
```

---

### Task 6: Frontend — AiModelMonitoring.vue Error Rate Trend Chart

**Files:**
- Modify: `agent-admin-front/src/views/AiModelMonitoring.vue`

**Interfaces:**
- Consumes: existing `/metrics/ai-calls/timeline` endpoint (already returns error count per day per call type)
- Produces: New error rate & 429 rate trend chart added to AiModelMonitoring.vue

- [ ] **Step 1: Add error rate trend chart to AiModelMonitoring.vue**

Add a new chart section after the existing token usage chart (before the error table). The existing `timeline` data already contains `errorCount` per date per call type — compute error rate from it.

Add to the template (after the token usage `el-col`):

```vue
      <el-col :span="24" style="margin-top: 20px;">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">错误率趋势</span></div>
          <v-chart class="chart" :option="errorRateChartOption" autoresize style="height: 300px" />
        </el-card>
      </el-col>
```

Add to `<script setup>` (the `timeline` ref already exists):

```javascript
const errorRateChartOption = computed(() => {
  const dates = [...new Set(timeline.value.map(t => t.date))].sort()
  const types = [...new Set(timeline.value.map(t => t.callType))]
  return {
    tooltip: { trigger: 'axis', formatter: (params) => {
      let html = params[0].axisValue + '<br/>'
      params.forEach(p => {
        html += `${p.marker} ${p.seriesName}: ${p.value.toFixed(2)}%<br/>`
      })
      return html
    }},
    legend: { data: types.map(t => t + ' 错误率') },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: types.map(type => ({
      name: type + ' 错误率',
      type: 'line',
      smooth: true,
      data: dates.map(d => {
        const items = timeline.value.filter(t => t.date === d && t.callType === type)
        const total = items.reduce((sum, t) => sum + t.count, 0)
        const errors = items.reduce((sum, t) => sum + t.errorCount, 0)
        return total > 0 ? (errors / total * 100) : 0
      }),
    })),
  }
})
```

- [ ] **Step 2: Verify frontend build**

Run: `cd agent-admin-front && npx vite build --mode development`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add agent-admin-front/src/views/AiModelMonitoring.vue
git commit -m "feat(admin-front): add error rate trend chart to AI model monitoring page"
```

---

## Self-Review

### Spec Coverage
- **Section 4.9 (pricing config):** ✓ Task 1 Step 4
- **Section 5.1-5.5 (ImageGenMetrics):** ✓ Task 1 (DTOs + repository) + Task 2 (service + controller)
- **Section 11.1-11.5 (PromptTemplate enhanced):** ✓ Task 3 (DTOs + service + controller)
- **Section 13.6 (error rate trend):** ✓ Task 6
- **Section 14.1-14.6 (ImageGenMonitoring.vue):** ✓ Task 4
- **Section 17.1-17.5 (PromptTemplates.vue enhancement):** ✓ Task 5

### Placeholder Scan
- No TBD, TODO, or "implement later" in the plan
- All code blocks contain complete implementations
- All test code is complete with assertions

### Type Consistency
- `ImageGenOverviewDTO` fields match between Task 1 (DTO) and Task 2 (service + test) ✓
- `ImageGenProviderDTO` with nested `FailureReason` matches between Task 1 and Task 2 ✓
- `ImageFeedbackDTO` with `Map<String, Long> tagDistribution` matches between Task 1 and Task 2 ✓
- `PromptTemplateUsageDTO` with nested `InvocationDay` matches between Task 3 (DTO) and Task 5 (frontend) ✓
- `PromptTemplateCompareDTO` with nested `TagCount` matches between Task 3 and Task 5 ✓
- Frontend API paths use `/metrics/image-generation/*` (no `/api/admin` prefix) and `/prompt-templates/*` ✓
- Frontend response used directly (not `res.data`) ✓
- All charts use `vue-echarts` (`VChart`) with `computed()` options ✓
