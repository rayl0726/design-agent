package com.meichen.orchestrator.handler;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;
import com.meichen.orchestrator.repository.SessionMessageRepository;
import com.meichen.orchestrator.service.SseEmitterService;
import com.meichen.orchestrator.util.PublicIdGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

@Component
public class GenericAgentHandler implements AgentHandler {

    private static final Logger log = LoggerFactory.getLogger(GenericAgentHandler.class);

    private final WebClient webClient;
    private final SessionMessageRepository messageRepository;
    private final SseEmitterService sseEmitterService;
    private final PublicIdGenerator publicIdGenerator;
    private final ObjectMapper objectMapper;

    public GenericAgentHandler(WebClient.Builder webClientBuilder,
                               @Value("${agent-core.base-url:http://localhost:8000}") String agentCoreBaseUrl,
                               SessionMessageRepository messageRepository,
                               SseEmitterService sseEmitterService,
                               PublicIdGenerator publicIdGenerator,
                               ObjectMapper objectMapper) {
        this.webClient = webClientBuilder != null ? webClientBuilder.baseUrl(agentCoreBaseUrl).build() : null;
        this.messageRepository = messageRepository;
        this.sseEmitterService = sseEmitterService;
        this.publicIdGenerator = publicIdGenerator;
        this.objectMapper = objectMapper;
    }

    @Override
    public void handle(Project project, SessionMessage userMessage) {
        if (webClient == null) {
            log.warn("GenericAgentHandler has no WebClient configured");
            replyUnavailable(project, userMessage);
            return;
        }
        try {
            log.info("Generic agent stream start: project={}, agentType={}", project.getId(), project.getAgentType());
            StringBuilder fullContent = new StringBuilder();
            webClient.post()
                .uri("/agents/{agentId}/run", project.getAgentType())
                .bodyValue(new AgentRunRequest(
                    project.getId(),
                    userMessage.getContent(),
                    project.getAgentContextJson()))
                .retrieve()
                .bodyToFlux(new ParameterizedTypeReference<ServerSentEvent<String>>() {})
                .doOnNext(event -> {
                    if (event == null || event.event() == null || event.data() == null) {
                        return;
                    }
                    String eventName = event.event();
                    if ("text_delta".equals(eventName)) {
                        String delta = extractDelta(objectMapper, event.data());
                        if (delta != null && !delta.isEmpty()) {
                            fullContent.append(delta);
                            pushTextDelta(project.getId(), delta);
                        }
                    } else if ("tool_start".equals(eventName)) {
                        try {
                            Object payload = objectMapper.readValue(
                                event.data(), new TypeReference<java.util.Map<String, Object>>() {}
                            );
                            sseEmitterService.sendToProject(project.getId(), eventName, payload);
                        } catch (Exception ex) {
                            log.warn("Failed to parse tool_start data: {}", event.data(), ex);
                        }
                    } else if ("tool_result".equals(eventName)) {
                        try {
                            Object payload = objectMapper.readValue(
                                event.data(), new TypeReference<java.util.Map<String, Object>>() {}
                            );
                            sseEmitterService.sendToProject(project.getId(), eventName, payload);
                            saveToolResult(project, userMessage, event.data());
                        } catch (Exception ex) {
                            log.warn("Failed to parse tool_result data: {}", event.data(), ex);
                        }
                    } else if ("tool_progress".equals(eventName)) {
                        try {
                            Object payload = objectMapper.readValue(
                                event.data(), new TypeReference<java.util.Map<String, Object>>() {}
                            );
                            sseEmitterService.sendToProject(project.getId(), eventName, payload);
                        } catch (Exception ex) {
                            log.warn("Failed to parse tool_progress data: {}", event.data(), ex);
                        }
                    }
                })
                .blockLast();

            String content = fullContent.toString().trim();
            if (!content.isEmpty()) {
                saveReply(project, userMessage, content);
            }
        } catch (Exception e) {
            log.error("Generic agent stream failed: {}", e.getMessage(), e);
            replyUnavailable(project, userMessage);
        }
    }

    static String extractDelta(ObjectMapper objectMapper, String data) {
        try {
            return objectMapper.readTree(data).path("delta").asText(null);
        } catch (Exception e) {
            log.warn("Failed to parse text_delta data: {}", data, e);
            return null;
        }
    }

    static String extractStatus(ObjectMapper objectMapper, String data) {
        try {
            return objectMapper.readTree(data).path("status").asText(null);
        } catch (Exception e) {
            log.warn("Failed to parse tool_progress data: {}", data, e);
            return null;
        }
    }

    private void pushTextDelta(String projectId, String delta) {
        if (delta == null || delta.isEmpty() || sseEmitterService == null) {
            return;
        }
        sseEmitterService.sendToProject(projectId, "text_delta", delta);
    }

    private void saveReply(Project project, SessionMessage userMessage, String content) {
        if (content == null || content.isEmpty() || messageRepository == null) {
            return;
        }
        content = content.replaceAll("(?s)<tool_call>.*?</tool_call>", "").trim();
        if (content.isEmpty()) {
            return;
        }
        SessionMessage reply = SessionMessage.create(project.getId(), "assistant", "text", content);
        reply.setUserId(userMessage.getUserId());
        reply = publicIdGenerator.assignAndSave(reply, SessionMessage::setPublicId, messageRepository::save);
        pushMessage(project.getId(), reply);
    }

    private void saveToolResult(Project project, SessionMessage userMessage, String eventData) {
        if (eventData == null || eventData.isEmpty() || messageRepository == null) {
            return;
        }
        SessionMessage toolMsg = SessionMessage.create(project.getId(), "tool", "tool", eventData);
        toolMsg.setUserId(userMessage.getUserId());
        publicIdGenerator.assignAndSave(toolMsg, SessionMessage::setPublicId, messageRepository::save);
    }

    private void pushMessage(String projectId, SessionMessage msg) {
        if (msg == null || sseEmitterService == null) {
            return;
        }
        java.util.Map<String, Object> event = new java.util.HashMap<>();
        event.put("id", msg.getId() != null ? msg.getId() : "");
        event.put("role", msg.getRole() != null ? msg.getRole() : "");
        event.put("message_type", msg.getMessageType() != null ? msg.getMessageType() : "");
        event.put("content", msg.getContent() != null ? msg.getContent() : "");
        event.put("created_at", msg.getCreatedAt() != null ? msg.getCreatedAt() : "");
        sseEmitterService.sendToProject(projectId, "message", event);
    }

    private void replyUnavailable(Project project, SessionMessage userMessage) {
        if (messageRepository == null) {
            return;
        }
        String hint = "通用 Agent 执行服务暂不可用，请稍后重试或联系管理员。";
        SessionMessage reply = SessionMessage.create(project.getId(), "assistant", "text", hint);
        reply.setUserId(userMessage.getUserId());
        reply = publicIdGenerator.assignAndSave(reply, SessionMessage::setPublicId, messageRepository::save);
        pushMessage(project.getId(), reply);
    }

    public record AgentRunRequest(String conversationId, String userInput, String contextJson) {}
}
