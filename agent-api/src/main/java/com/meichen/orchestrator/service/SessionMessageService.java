package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;
import com.meichen.orchestrator.repository.ProjectRepository;
import com.meichen.orchestrator.repository.SessionMessageRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class SessionMessageService {

    private final SessionMessageRepository messageRepository;
    private final ProjectRepository projectRepository;

    public SessionMessageService(SessionMessageRepository messageRepository,
                                  ProjectRepository projectRepository) {
        this.messageRepository = messageRepository;
        this.projectRepository = projectRepository;
    }

    @Transactional(readOnly = true)
    public List<SessionMessage> listMessages(String projectId, Long userId) {
        ensureProjectBelongsToUser(projectId, userId);
        return messageRepository.findByProjectIdAndUserIdOrderByCreatedAtAsc(projectId, userId);
    }

    @Transactional
    public SessionMessage addUserMessage(String projectId, String content, Long userId) {
        ensureProjectBelongsToUser(projectId, userId);
        SessionMessage msg = SessionMessage.create(projectId, "user", "text", content);
        msg.setUserId(userId);
        SessionMessage saved = messageRepository.save(msg);
        return saved;
    }

    @Transactional
    public SessionMessage addAssistantMessage(String projectId, String messageType, String content, Long userId) {
        ensureProjectBelongsToUser(projectId, userId);
        SessionMessage msg = SessionMessage.create(projectId, "assistant", messageType, content);
        msg.setUserId(userId);
        return messageRepository.save(msg);
    }

    @Transactional
    public void addSystemMessage(String projectId, String content, Long userId) {
        SessionMessage msg = SessionMessage.create(projectId, "system", "text", content);
        msg.setUserId(userId);
        messageRepository.save(msg);
    }

    private Project ensureProjectBelongsToUser(String projectId, Long userId) {
        return projectRepository.findByIdAndUserId(projectId, userId)
                .orElseThrow(() -> new IllegalArgumentException("Project not found: " + projectId));
    }
}
