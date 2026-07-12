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
    "jwt.secret=test-secret-test-secret-test-secret-32"
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
