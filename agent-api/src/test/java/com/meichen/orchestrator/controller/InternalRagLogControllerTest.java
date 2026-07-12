package com.meichen.orchestrator.controller;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:h2:mem:testdb;MODE=MySQL",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.datasource.username=sa",
    "spring.datasource.password=",
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "spring.flyway.enabled=false",
    "jwt.secret=test-secret-test-secret-test-secret-32"
})
class InternalRagLogControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

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

        Long count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM rag_search_logs WHERE search_type = 'semantic'",
            Long.class);
        assertEquals(1L, count);
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
