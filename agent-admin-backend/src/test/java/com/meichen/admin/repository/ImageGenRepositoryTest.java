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
        insertAiCallLog("image_gen", "siliconflow", "success", 5000, "proj-1");
        insertAiCallLog("image_gen", "siliconflow", "success", 3000, "proj-1");
        insertAiCallLog("image_gen", "siliconflow", "failed", 1000, "proj-2");
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
        insertAiCallLog("image_gen", "siliconflow", "success", 5000, "proj-1");
        insertAiCallLog("image_gen", "zhipu", "failed", 2000, "proj-2");

        LocalDateTime since = LocalDateTime.now().minusHours(24);
        List<Object[]> results = aiCallLogRepo.groupImageGenByProvider(since);

        assertEquals(2, results.size());
    }

    @Test
    void findImageGenFailureReasons_returnsErrorMessages() {
        insertAiCallLogWithError("image_gen", "siliconflow", "failed", 1000, "proj-1", "timeout");
        insertAiCallLogWithError("image_gen", "siliconflow", "failed", 500, "proj-2", "timeout");
        insertAiCallLogWithError("image_gen", "siliconflow", "failed", 200, "proj-3", "content_filter");

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
