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

    public SseEmitter subscribe(String projectId) {
        SseEmitter emitter = new SseEmitter(SSE_TIMEOUT);
        emitters.computeIfAbsent(projectId, k -> new CopyOnWriteArrayList<>()).add(emitter);

        emitter.onCompletion(() -> removeEmitter(projectId, emitter));
        emitter.onTimeout(() -> removeEmitter(projectId, emitter));
        emitter.onError(e -> removeEmitter(projectId, emitter));

        // 补推历史状态、消息和思考记录
        sendHistory(projectId, emitter);

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

    public void sendHistory(String projectId, SseEmitter emitter) {
        try {
            Project project = projectRepository.findById(projectId).orElse(null);
            if (project != null) {
                sendEvent(emitter, "status", Map.of(
                    "project_id", projectId,
                    "status", project.getStatus(),
                    "current_level", project.getCurrentLevel()
                ));
            }

            List<SessionMessage> messages = sessionMessageService.listMessages(projectId);
            for (SessionMessage msg : messages) {
                sendEvent(emitter, "message", Map.of(
                    "id", msg.getId(),
                    "role", msg.getRole(),
                    "message_type", msg.getMessageType(),
                    "content", msg.getContent(),
                    "created_at", msg.getCreatedAt()
                ));
            }

            List<ThinkingLog> logs = thinkingLogService.listByProject(projectId);
            for (ThinkingLog log : logs) {
                sendEvent(emitter, "thinking", Map.of(
                    "id", log.getId(),
                    "node_name", log.getNodeName(),
                    "status", log.getStatus(),
                    "message", log.getMessage(),
                    "created_at", log.getCreatedAt()
                ));
            }
        } catch (Exception e) {
            log.error("Failed to send SSE history for project {}: {}", projectId, e.getMessage());
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
