package com.meichen.admin.controller;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
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
class IntentQualityControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    // Note: admin.agent-core.base-url is set to an invalid port (99999) so
    // WebClient calls will fail gracefully, returning empty/zero values.
    // This tests the graceful degradation path.

    @Test
    void getSources_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/intent-quality/sources")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getConfidence_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/intent-quality/confidence")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.lowConfidenceRate").exists())
            .andExpect(jsonPath("$.buckets").isArray());
    }

    @Test
    void getCorrectionRate_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/intent-quality/correction-rate")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getDialogueTurns_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/intent-quality/dialogue-turns")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk());
    }

    @Test
    void getAliasProposals_returns200() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/intent-quality/alias-proposals")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk());
    }

    @Test
    void getSources_noToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/metrics/intent-quality/sources"))
            .andExpect(status().isUnauthorized());
    }
}
