package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.Feedback;
import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.repository.FeedbackRepository;
import com.meichen.orchestrator.repository.ProjectRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

@Service
public class FeedbackService {

    private final FeedbackRepository feedbackRepository;
    private final ProjectRepository projectRepository;

    public FeedbackService(FeedbackRepository feedbackRepository, ProjectRepository projectRepository) {
        this.feedbackRepository = feedbackRepository;
        this.projectRepository = projectRepository;
    }

    @Transactional
    public Feedback saveFeedback(String projectId, Map<String, Object> payload, Long userId) {
        ensureProjectBelongsToUser(projectId, userId);

        String feedbackType = (String) payload.get("feedback_type");
        Integer ideaIndex = payload.get("idea_index") instanceof Number n ? n.intValue() : null;
        String pointName = (String) payload.get("point_name");
        Integer imageIndex = payload.get("image_index") instanceof Number n ? n.intValue() : null;
        String imageUrl = (String) payload.get("image_url");
        String tag = (String) payload.get("tag");
        String comment = (String) payload.get("comment");

        Feedback feedback = Feedback.create(
            projectId, feedbackType, ideaIndex, pointName, imageIndex, imageUrl, tag, comment
        );
        feedback.setUserId(userId);
        return feedbackRepository.save(feedback);
    }

    @Transactional(readOnly = true)
    public List<Feedback> listByProject(String projectId, Long userId) {
        ensureProjectBelongsToUser(projectId, userId);
        return feedbackRepository.findByProjectIdAndUserIdOrderByCreatedAtDesc(projectId, userId);
    }

    private Project ensureProjectBelongsToUser(String projectId, Long userId) {
        return projectRepository.findByIdAndUserId(projectId, userId)
                .orElseThrow(() -> new IllegalArgumentException("Project not found: " + projectId));
    }
}
