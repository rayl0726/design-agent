package com.meichen.admin.controller;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:h2:mem:testdb;MODE=MySQL",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.datasource.username=sa",
    "spring.datasource.password=",
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "spring.flyway.enabled=false",
    "admin.token=test-token",
    "admin.agent-core.base-url=http://localhost:99999"
})
class PromptTemplateAdminControllerIntegrationTest {

    private static Path tempDataDir;

    @DynamicPropertySource
    static void dynamicProperties(DynamicPropertyRegistry registry) throws Exception {
        tempDataDir = Files.createTempDirectory("admin-prompt-test");
        Path templateDir = tempDataDir.resolve("prompt_templates");
        Files.createDirectories(templateDir);
        Files.writeString(templateDir.resolve("generic_commercial_display.yaml"),
            "version: \"1.0\"\n" +
            "space_types: []\n" +
            "positive_prompt: \"commercial display\"\n" +
            "negative_prompt: \"blurry\"\n");
        Files.writeString(templateDir.resolve("shopping_mall_atrium.yaml"),
            "version: \"1.0\"\n" +
            "space_types:\n" +
            "  - \"购物中心中庭\"\n" +
            "  - \"商场中庭\"\n" +
            "positive_prompt: \"shopping mall atrium\"\n" +
            "negative_prompt: \"low quality\"\n");
        registry.add("admin.agent-core.data-dir", () -> tempDataDir.toString());
    }

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("DELETE FROM feedbacks");
    }

    @Test
    void listTemplates_returnsAllTemplates() throws Exception {
        mockMvc.perform(get("/api/admin/prompt-templates")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$.length()").value(2))
            .andExpect(jsonPath("$[?(@.name=='shopping_mall_atrium')].spaceType").value("购物中心中庭, 商场中庭"))
            .andExpect(jsonPath("$[?(@.name=='generic_commercial_display')].version").value("1.0"));
    }

    @Test
    void getPerformance_returnsEmptyWhenNoData() throws Exception {
        mockMvc.perform(get("/api/admin/prompt-templates/generic_commercial_display/performance")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void previewPrompt_returnsErrorWhenAgentCoreUnavailable() throws Exception {
        mockMvc.perform(post("/api/admin/prompt-templates/preview")
                .header("X-Admin-Token", "test-token")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"theme\":\"新春国潮\",\"spaceType\":\"购物中心中庭\",\"budgetLevel\":\"medium\"}"))
            .andExpect(status().is5xxServerError());
    }

    @Test
    void listTemplates_withoutToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/prompt-templates"))
            .andExpect(status().isUnauthorized());
    }
}
