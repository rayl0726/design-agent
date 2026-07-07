package com.meichen.orchestrator.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;
import com.meichen.orchestrator.entity.ThinkingLog;
import com.meichen.orchestrator.repository.ProjectRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class SseEmitterService {

    private static final Logger log = LoggerFactory.getLogger(SseEmitterService.class);
    private static final long SSE_TIMEOUT = 0L; // 不超时，由前端控制重连

    private final Map<String, List<SseEmitter>> emitters = new ConcurrentHashMap<>();
    private final ProjectRepository projectRepository;
    private final SessionMessageService sessionMessageService;
    private final ThinkingLogService thinkingLogService;
    private final ObjectMapper objectMapper;

    public SseEmitterService(ProjectRepository projectRepository,
                             SessionMessageService sessionMessageService,
                             ThinkingLogService thinkingLogService,
                             ObjectMapper objectMapper) {
        this.projectRepository = projectRepository;
        this.sessionMessageService = sessionMessageService;
        this.thinkingLogService = thinkingLogService;
        this.objectMapper = objectMapper;
    }

    public SseEmitter subscribe(String projectId, Long userId) {
        // 先校验项目归属，避免未授权用户订阅他人项目的事件流
        projectRepository.findByIdAndUserId(projectId, userId)
            .orElseThrow(() -> new IllegalArgumentException("Project not found: " + projectId));

        SseEmitter emitter = new SseEmitter(SSE_TIMEOUT);
        emitters.computeIfAbsent(projectId, k -> new CopyOnWriteArrayList<>()).add(emitter);

        emitter.onCompletion(() -> removeEmitter(projectId, emitter));
        emitter.onTimeout(() -> removeEmitter(projectId, emitter));
        emitter.onError(e -> removeEmitter(projectId, emitter));

        // 补推历史状态、消息和思考记录
        sendHistory(projectId, emitter, userId);

        return emitter;
    }

    private void removeEmitter(String projectId, SseEmitter emitter) {
        List<SseEmitter> list = emitters.get(projectId);
        if (list != null) {
            list.remove(emitter);
            if (list.isEmpty()) {
                emitters.remove(projectId);
            }
        }
    }

    public void sendHistory(String projectId, SseEmitter emitter, Long userId) {
        try {
            Project project = projectRepository.findByIdAndUserId(projectId, userId).orElse(null);
            if (project != null) {
                Map<String, Object> statusEvent = new HashMap<>();
                statusEvent.put("project_id", projectId);
                statusEvent.put("status", project.getStatus() != null ? project.getStatus() : "");
                statusEvent.put("current_level", project.getCurrentLevel() != null ? project.getCurrentLevel() : "");
                sendEvent(emitter, "status", statusEvent);
            }

            List<SessionMessage> messages = userId != null
                ? sessionMessageService.listMessages(projectId, userId)
                : List.of();
            for (SessionMessage msg : messages) {
                Map<String, Object> event = new HashMap<>();
                event.put("id", msg.getId() != null ? msg.getId() : "");
                event.put("role", msg.getRole() != null ? msg.getRole() : "");
                event.put("message_type", msg.getMessageType() != null ? msg.getMessageType() : "");
                event.put("content", msg.getContent() != null ? msg.getContent() : "");
                event.put("created_at", msg.getCreatedAt() != null ? msg.getCreatedAt() : "");
                sendEvent(emitter, "message", event);
            }

            List<ThinkingLog> logs = thinkingLogService.listByProject(projectId);
            for (ThinkingLog log : logs) {
                Map<String, Object> event = new HashMap<>();
                event.put("id", log.getId() != null ? log.getId() : "");
                event.put("node_name", log.getNodeName() != null ? log.getNodeName() : "");
                event.put("status", log.getStatus() != null ? log.getStatus() : "");
                event.put("message", log.getMessage() != null ? log.getMessage() : "");
                event.put("created_at", log.getCreatedAt() != null ? log.getCreatedAt() : "");
                sendEvent(emitter, "thinking", event);
            }
        } catch (Exception e) {
            log.error("Failed to send SSE history for project {}: {}", projectId, e.getMessage(), e);
        }
    }

    public void sendToProject(String projectId, String eventName, Object data) {
        List<SseEmitter> list = emitters.get(projectId);
        if (list == null || list.isEmpty()) {
            return;
        }

        List<SseEmitter> dead = new java.util.ArrayList<>();
        for (SseEmitter emitter : list) {
            try {
                sendEvent(emitter, eventName, data);
            } catch (Exception e) {
                dead.add(emitter);
            }
        }

        for (SseEmitter emitter : dead) {
            removeEmitter(projectId, emitter);
        }
    }

    private void sendEvent(SseEmitter emitter, String eventName, Object data) throws IOException {
        String json = objectMapper.writeValueAsString(data);
        emitter.send(SseEmitter.event()
            .name(eventName)
            .data(json));
    }
}
