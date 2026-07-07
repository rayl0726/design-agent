package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;
import com.meichen.orchestrator.repository.ProjectRepository;
import com.meichen.orchestrator.repository.SessionMessageRepository;
import com.meichen.orchestrator.util.PublicIdGenerator;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class SessionMessageService {

    private final SessionMessageRepository messageRepository;
    private final ProjectRepository projectRepository;
    private final PublicIdGenerator publicIdGenerator;

    public SessionMessageService(SessionMessageRepository messageRepository,
                                  ProjectRepository projectRepository,
                                  PublicIdGenerator publicIdGenerator) {
        this.messageRepository = messageRepository;
        this.projectRepository = projectRepository;
        this.publicIdGenerator = publicIdGenerator;
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
        return publicIdGenerator.assignAndSave(msg, SessionMessage::setPublicId, messageRepository::save);
    }

    @Transactional
    public SessionMessage addAssistantMessage(String projectId, String messageType, String content, Long userId) {
        ensureProjectBelongsToUser(projectId, userId);
        SessionMessage msg = SessionMessage.create(projectId, "assistant", messageType, content);
        msg.setUserId(userId);
        return publicIdGenerator.assignAndSave(msg, SessionMessage::setPublicId, messageRepository::save);
    }

    @Transactional
    public void addSystemMessage(String projectId, String content, Long userId) {
        SessionMessage msg = SessionMessage.create(projectId, "system", "text", content);
        msg.setUserId(userId);
        publicIdGenerator.assignAndSave(msg, SessionMessage::setPublicId, messageRepository::save);
    }

    private Project ensureProjectBelongsToUser(String projectId, Long userId) {
        return projectRepository.findByIdAndUserId(projectId, userId)
                .orElseThrow(() -> new IllegalArgumentException("Project not found: " + projectId));
    }
}
