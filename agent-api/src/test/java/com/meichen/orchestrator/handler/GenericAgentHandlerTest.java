package com.meichen.orchestrator.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class GenericAgentHandlerTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void extractDelta_shouldReturnNullForNullOrEmptyData() {
        assertThat(GenericAgentHandler.extractDelta(objectMapper, null)).isNull();
        assertThat(GenericAgentHandler.extractDelta(objectMapper, "")).isNull();
    }

    @Test
    void extractDelta_shouldExtractDeltaField() {
        String data = "{\"delta\":\"你好\"}";

        String delta = GenericAgentHandler.extractDelta(objectMapper, data);

        assertThat(delta).isEqualTo("你好");
    }

    @Test
    void extractDelta_shouldReturnNullWhenDeltaFieldMissing() {
        String data = "{\"other\":\"value\"}";

        String delta = GenericAgentHandler.extractDelta(objectMapper, data);

        assertThat(delta).isNull();
    }

    @Test
    void extractDelta_shouldReturnNullForInvalidJson() {
        String data = "not-json";

        String delta = GenericAgentHandler.extractDelta(objectMapper, data);

        assertThat(delta).isNull();
    }

    @Test
    void extractStatus_shouldReturnSummarizing() {
        String data = "{\"id\":\"call-1\",\"status\":\"summarizing\",\"detail\":\"x\"}";
        String status = GenericAgentHandler.extractStatus(objectMapper, data);
        assertThat(status).isEqualTo("summarizing");
    }
}
