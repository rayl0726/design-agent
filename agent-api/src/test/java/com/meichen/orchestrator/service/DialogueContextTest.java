package com.meichen.orchestrator.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.*;

import static org.assertj.core.api.Assertions.assertThat;

class DialogueContextTest {

    private DialogueService dialogueService;

    @BeforeEach
    void setUp() {
        dialogueService = new DialogueService(
            WebClient.builder(),
            null, null, null, new ObjectMapper(), null, Runnable::run, "http://localhost:8000"
        );
    }

    @Test
    void extractPreviousIntent_excludesInternalFields() {
        Map<String, Object> requirementJson = new HashMap<>();
        requirementJson.put("theme", "新春国潮");
        requirementJson.put("style", "国潮");
        requirementJson.put("space_type", "购物中心中庭");
        requirementJson.put("budget", 1000000);
        requirementJson.put("budget_level", "medium");
        requirementJson.put("timeline", "2-3周");
        requirementJson.put("raw_inputs", List.of(Map.of("theme", "新春国潮")));
        requirementJson.put("_recognition_meta", Map.of("trace_id", "abc"));
        requirementJson.put("trace_id", "abc-123");
        requirementJson.put("source_type", "text");
        requirementJson.put("space_description", "购物中心中庭商业空间");
        requirementJson.put("color_palette", List.of("#FFFFFF"));
        requirementJson.put("material_suggestions", List.of("亚克力"));

        Map<String, Object> result = dialogueService.extractPreviousIntent(requirementJson);

        assertThat(result).containsKeys("theme", "style", "space_type", "budget", "budget_level", "timeline");
        assertThat(result).doesNotContainKeys(
            "raw_inputs", "_recognition_meta", "trace_id", "source_type",
            "space_description", "color_palette", "material_suggestions",
            "constraints", "conflicts", "needs_confirmation", "missing_fields",
            "is_complete", "mood_keywords", "design_direction", "spatial_notes",
            "risk_hints", "needs_clarification", "clarification_question",
            "low_confidence_fields"
        );
        assertThat(result.get("theme")).isEqualTo("新春国潮");
        assertThat(result.get("style")).isEqualTo("国潮");
    }

    @Test
    void extractPreviousIntent_emptyJsonReturnsEmptyMap() {
        Map<String, Object> result = dialogueService.extractPreviousIntent(new HashMap<>());
        assertThat(result).isEmpty();
    }

    @Test
    void extractPreviousIntent_nullReturnsEmptyMap() {
        Map<String, Object> result = dialogueService.extractPreviousIntent(null);
        assertThat(result).isEmpty();
    }

    @Test
    void extractPreviousIntent_includesListFields() {
        Map<String, Object> requirementJson = new HashMap<>();
        requirementJson.put("material_restrictions", List.of("真植物"));
        requirementJson.put("allowed_materials", List.of("亚克力"));
        requirementJson.put("special_requirements", List.of("需要灯光"));
        requirementJson.put("points", List.of(Map.of("name", "中庭", "count", 1)));

        Map<String, Object> result = dialogueService.extractPreviousIntent(requirementJson);

        assertThat(result).containsKey("material_restrictions");
        assertThat(result).containsKey("allowed_materials");
        assertThat(result).containsKey("special_requirements");
        assertThat(result).containsKey("points");
    }

    @Test
    void generateConversationSummary_moreThanThreeRounds() {
        List<Object> rawInputs = new ArrayList<>();
        rawInputs.add(Map.of("theme", "新春国潮", "style", "国潮"));
        rawInputs.add(Map.of("space_type", "购物中心中庭", "budget", 1000000));
        rawInputs.add(Map.of("points", List.of(Map.of("name", "中庭"))));
        rawInputs.add(Map.of("budget", 2000000));

        String summary = dialogueService.generateConversationSummary(rawInputs);

        assertThat(summary).contains("新春国潮");
        assertThat(summary).contains("国潮");
        assertThat(summary).contains("购物中心中庭");
    }

    @Test
    void generateConversationSummary_threeOrFewerReturnsEmpty() {
        List<Object> rawInputs = new ArrayList<>();
        rawInputs.add(Map.of("theme", "新春国潮"));

        String summary = dialogueService.generateConversationSummary(rawInputs);
        assertThat(summary).isEmpty();
    }

    @Test
    void generateConversationSummary_emptyReturnsEmpty() {
        String summary = dialogueService.generateConversationSummary(Collections.emptyList());
        assertThat(summary).isEmpty();
    }

    @Test
    void generateConversationSummary_nullReturnsEmpty() {
        String summary = dialogueService.generateConversationSummary(null);
        assertThat(summary).isEmpty();
    }

    @Test
    void generateConversationSummary_cappedAtFiftyLines() {
        List<Object> rawInputs = new ArrayList<>();
        for (int i = 0; i < 60; i++) {
            rawInputs.add(Map.of("theme", "主题" + i));
        }

        String summary = dialogueService.generateConversationSummary(rawInputs);
        String[] lines = summary.split("\n");
        assertThat(lines.length).isLessThanOrEqualTo(50);
    }
}
