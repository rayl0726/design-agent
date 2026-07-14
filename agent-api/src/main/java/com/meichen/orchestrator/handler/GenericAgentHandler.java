package com.meichen.orchestrator.handler;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

@Component
public class GenericAgentHandler implements AgentHandler {

    private static final Logger log = LoggerFactory.getLogger(GenericAgentHandler.class);

    private final WebClient webClient;

    public GenericAgentHandler(WebClient.Builder webClientBuilder,
                               @Value("${agent-core.base-url:http://localhost:8000}") String agentCoreBaseUrl) {
        this.webClient = webClientBuilder != null ? webClientBuilder.baseUrl(agentCoreBaseUrl).build() : null;
    }

    @Override
    public void handle(Project project, SessionMessage userMessage) {
        if (webClient == null) {
            log.warn("GenericAgentHandler has no WebClient configured");
            return;
        }
        webClient.post()
            .uri("/agents/{agentId}/run", project.getAgentType())
            .bodyValue(new AgentRunRequest(
                project.getId(),
                userMessage.getContent(),
                project.getAgentContextJson()))
            .retrieve()
            .bodyToFlux(AgentEvent.class)
            .subscribe(
                event -> log.debug("Agent event: {}", event),
                error -> log.error("Generic agent run failed: {}", error.getMessage())
            );
    }

    public record AgentRunRequest(String conversationId, String userInput, String contextJson) {}
    public record AgentEvent(String type, Object payload) {}
}
