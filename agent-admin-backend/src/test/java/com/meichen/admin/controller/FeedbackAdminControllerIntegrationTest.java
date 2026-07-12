package com.meichen.admin.controller;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
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
    "admin.token=test-token",
    "admin.agent-core.base-url=http://localhost:8000",
    "admin.agent-core.data-dir=/tmp"
})
class FeedbackAdminControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("DELETE FROM feedbacks");
        jdbcTemplate.update(
            "INSERT INTO feedbacks (id, project_id, feedback_type, category, processed, comment, public_id) " +
            "VALUES ('fb-1', 'proj-1', 'image', 'like', false, 'Great', 'pub1')");
        jdbcTemplate.update(
            "INSERT INTO feedbacks (id, project_id, feedback_type, category, processed, comment, public_id) " +
            "VALUES ('fb-2', 'proj-1', 'intent', 'intent_correction', false, 'Wrong theme', 'pub2')");
        jdbcTemplate.update(
            "INSERT INTO feedbacks (id, project_id, feedback_type, category, processed, comment, public_id) " +
            "VALUES ('fb-3', 'proj-2', 'image', 'dislike', true, 'Bad', 'pub3')");
    }

    @Test
    void listFeedbacks_returnsPaginatedResults() throws Exception {
        mockMvc.perform(get("/api/admin/feedbacks")
                .header("X-Admin-Token", "test-token")
                .param("page", "0")
                .param("size", "10"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.content").isArray())
            .andExpect(jsonPath("$.totalElements").value(3))
            .andExpect(jsonPath("$.size").value(10));
    }

    @Test
    void listFeedbacks_filterByType() throws Exception {
        mockMvc.perform(get("/api/admin/feedbacks")
                .header("X-Admin-Token", "test-token")
                .param("feedbackType", "image"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalElements").value(2))
            .andExpect(jsonPath("$.content[0].feedbackType").value("image"));
    }

    @Test
    void listFeedbacks_filterByProcessed() throws Exception {
        mockMvc.perform(get("/api/admin/feedbacks")
                .header("X-Admin-Token", "test-token")
                .param("processed", "false"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.totalElements").value(2));
    }

    @Test
    void processFeedback_marksAsProcessed() throws Exception {
        mockMvc.perform(post("/api/admin/feedbacks/fb-1/process")
                .header("X-Admin-Token", "test-token")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"notes\":\"handled\"}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value("fb-1"))
            .andExpect(jsonPath("$.processed").value(true))
            .andExpect(jsonPath("$.notes").value("handled"));
    }

    @Test
    void processFeedback_withoutNotes() throws Exception {
        mockMvc.perform(post("/api/admin/feedbacks/fb-2/process")
                .header("X-Admin-Token", "test-token")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.processed").value(true));
    }

    @Test
    void processFeedback_notFound_returns400() throws Exception {
        mockMvc.perform(post("/api/admin/feedbacks/nonexistent/process")
                .header("X-Admin-Token", "test-token")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isBadRequest());
    }

    @Test
    void listFeedbacks_withoutToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/feedbacks"))
            .andExpect(status().isUnauthorized());
    }
}
