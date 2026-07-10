package com.meichen.orchestrator.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@ExtendWith(MockitoExtension.class)
class DialogueServiceTest {

    private DialogueService dialogueService;

    @BeforeEach
    void setUp() {
        dialogueService = new DialogueService(
            WebClient.builder(),
            null, null, null, new ObjectMapper(), null, Runnable::run, "http://localhost:8000"
        );
    }

    @Test
    void isValidValue_rejectsPunctuationOnly() {
        assertThat(dialogueService.isValidValue("theme", "，")).isFalse();
        assertThat(dialogueService.isValidValue("theme", ",")).isFalse();
        assertThat(dialogueService.isValidValue("theme", "。")).isFalse();
    }

    @Test
    void isValidValue_rejectsNullAndBlank() {
        assertThat(dialogueService.isValidValue("theme", null)).isFalse();
        assertThat(dialogueService.isValidValue("theme", "")).isFalse();
        assertThat(dialogueService.isValidValue("theme", "   ")).isFalse();
    }

    @Test
    void isValidValue_acceptsMeaningfulString() {
        assertThat(dialogueService.isValidValue("theme", "圣诞节")).isTrue();
        assertThat(dialogueService.isValidValue("space_type", "快闪店")).isTrue();
        assertThat(dialogueService.isValidValue("budget", "30万")).isTrue();
    }

    @Test
    void isValidValue_acceptsNumericBudget() {
        assertThat(dialogueService.isValidValue("budget", 300000)).isTrue();
        assertThat(dialogueService.isValidValue("budget", 0)).isFalse();
    }

    @Test
    void isValidValue_rejectsPureDigitTheme() {
        assertThat(dialogueService.isValidValue("theme", "123")).isFalse();
        assertThat(dialogueService.isValidValue("space_type", "45")).isFalse();
    }

    @Test
    void mergeRequirements_doesNotOverwriteValidWithGarbage() {
        Map<String, Object> existing = Map.of("theme", "圣诞节");
        Map<String, Object> current = Map.of("theme", "，", "budget", 300000);
        Map<String, Object> merged = dialogueService.mergeRequirements(existing, current);
        assertThat(merged.get("theme")).isEqualTo("圣诞节");
        assertThat(merged.get("budget")).isEqualTo(300000);
    }
}
