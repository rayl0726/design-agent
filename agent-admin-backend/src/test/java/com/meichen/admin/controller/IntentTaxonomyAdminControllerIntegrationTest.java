package com.meichen.admin.controller;

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
    "admin.agent-core.base-url=http://localhost:8000"
})
class IntentTaxonomyAdminControllerIntegrationTest {

    private static Path tempDataDir;

    @DynamicPropertySource
    static void dynamicProperties(DynamicPropertyRegistry registry) throws Exception {
        tempDataDir = Files.createTempDirectory("admin-taxonomy-test");
        String yaml =
            "version: \"1.0\"\n" +
            "space_types:\n" +
            "  - name: \"购物中心中庭\"\n" +
            "    aliases: [\"商场中庭\", \"中庭\"]\n" +
            "  - name: \"快闪店\"\n" +
            "    aliases: [\"popup store\"]\n" +
            "points:\n" +
            "  - name: \"中庭\"\n" +
            "    aliases: [\"中庭吊饰\"]\n" +
            "  - name: \"DP点\"\n" +
            "    aliases: [\"dp点\", \"打卡点\"]\n" +
            "budget_levels:\n" +
            "  - name: \"low\"\n" +
            "    aliases: [\"低预算\"]\n" +
            "  - name: \"medium\"\n" +
            "    aliases: [\"中等预算\"]\n" +
            "styles:\n" +
            "  - name: \"国潮\"\n" +
            "    aliases: [\"中国风\", \"新中式\"]\n" +
            "materials:\n" +
            "  - name: \"亚克力\"\n" +
            "    aliases: [\"acrylic\"]\n" +
            "field_defaults:\n" +
            "  space_type:\n" +
            "    required: true\n";
        Files.writeString(tempDataDir.resolve("intent_taxonomy.yaml"), yaml);
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
    void getTaxonomy_returnsFullTaxonomy() throws Exception {
        mockMvc.perform(get("/api/admin/intent-taxonomy")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.version").value("1.0"))
            .andExpect(jsonPath("$.spaceTypes").isArray())
            .andExpect(jsonPath("$.spaceTypes[0].name").value("购物中心中庭"))
            .andExpect(jsonPath("$.spaceTypes[0].aliases[0]").value("商场中庭"))
            .andExpect(jsonPath("$.points").isArray())
            .andExpect(jsonPath("$.budgetLevels").isArray())
            .andExpect(jsonPath("$.styles").isArray());
    }

    @Test
    void getAliasProposals_returnsEmptyWhenNoData() throws Exception {
        mockMvc.perform(get("/api/admin/intent-taxonomy/alias-proposals")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void getAliasProposals_returnsProposalsFromCorrections() throws Exception {
        for (int i = 0; i < 3; i++) {
            jdbcTemplate.update(
                "INSERT INTO feedbacks (id, project_id, feedback_type, category, processed, " +
                "intent_field, original_value, corrected_value, public_id) " +
                "VALUES (?, 'proj-1', 'intent', 'correction', false, 'space_type', '商场中庭', '购物中心中庭', ?)",
                "fb-" + i, "pub-" + i);
        }

        mockMvc.perform(get("/api/admin/intent-taxonomy/alias-proposals")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$.length()").value(1))
            .andExpect(jsonPath("$[0].intentField").value("space_type"))
            .andExpect(jsonPath("$[0].originalValue").value("商场中庭"))
            .andExpect(jsonPath("$[0].correctedValue").value("购物中心中庭"))
            .andExpect(jsonPath("$[0].occurrenceCount").value(3));
    }

    @Test
    void applyAlias_addsAliasToTaxonomy() throws Exception {
        mockMvc.perform(post("/api/admin/intent-taxonomy/alias-proposals/apply")
                .header("X-Admin-Token", "test-token")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"intentField\":\"space_type\",\"originalValue\":\"shopping mall\",\"correctedValue\":\"购物中心中庭\"}"))
            .andExpect(status().isOk());

        mockMvc.perform(get("/api/admin/intent-taxonomy")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.spaceTypes[0].aliases").value(org.hamcrest.Matchers.hasItem("shopping mall")));
    }

    @Test
    void addAlias_manuallyAddsAlias() throws Exception {
        mockMvc.perform(post("/api/admin/intent-taxonomy/aliases")
                .header("X-Admin-Token", "test-token")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"section\":\"styles\",\"canonicalName\":\"国潮\",\"alias\":\"chinoiserie\"}"))
            .andExpect(status().isOk());

        mockMvc.perform(get("/api/admin/intent-taxonomy")
                .header("X-Admin-Token", "test-token"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.styles[0].aliases").value(org.hamcrest.Matchers.hasItem("chinoiserie")));
    }

    @Test
    void applyAlias_canonicalNotFound_returns400() throws Exception {
        mockMvc.perform(post("/api/admin/intent-taxonomy/alias-proposals/apply")
                .header("X-Admin-Token", "test-token")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"intentField\":\"space_type\",\"originalValue\":\"x\",\"correctedValue\":\"不存在的空间类型\"}"))
            .andExpect(status().isBadRequest());
    }

    @Test
    void getTaxonomy_withoutToken_returns401() throws Exception {
        mockMvc.perform(get("/api/admin/intent-taxonomy"))
            .andExpect(status().isUnauthorized());
    }
}
