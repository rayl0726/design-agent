package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;
import com.meichen.orchestrator.repository.ProjectRepository;
import com.meichen.orchestrator.repository.SessionMessageRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

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
    public List<SessionMessage> listMessages(String projectId) {
        ensureProjectExists(projectId);
        return messageRepository.findByProjectIdOrderByCreatedAtAsc(projectId);
    }

    @Transactional
    public SessionMessage addUserMessage(String projectId, String content) {
        ensureProjectExists(projectId);
        SessionMessage msg = SessionMessage.create(projectId, "user", "text", content);
        return messageRepository.save(msg);
    }

    @Transactional
    public SessionMessage addAssistantMessage(String projectId, String messageType, String content) {
        ensureProjectExists(projectId);
        SessionMessage msg = SessionMessage.create(projectId, "assistant", messageType, content);
        return messageRepository.save(msg);
    }

    @Transactional
    public void addSystemMessage(String projectId, String content) {
        SessionMessage msg = SessionMessage.create(projectId, "system", "text", content);
        messageRepository.save(msg);
    }

    private void ensureProjectExists(String projectId) {
        if (!projectRepository.existsById(projectId)) {
            throw new IllegalArgumentException("Project not found: " + projectId);
        }
    }
}
