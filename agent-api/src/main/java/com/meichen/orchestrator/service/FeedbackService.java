package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.Feedback;
import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.repository.FeedbackRepository;
import com.meichen.orchestrator.repository.ProjectRepository;
import com.meichen.orchestrator.util.PublicIdGenerator;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

@Service
public class FeedbackService {

    private final FeedbackRepository feedbackRepository;
    private final ProjectRepository projectRepository;
    private final PublicIdGenerator publicIdGenerator;
    private final ObjectMapper objectMapper;

    public FeedbackService(FeedbackRepository feedbackRepository, ProjectRepository projectRepository, PublicIdGenerator publicIdGenerator) {
        this(feedbackRepository, projectRepository, publicIdGenerator, new ObjectMapper());
    }

    @Autowired
    public FeedbackService(FeedbackRepository feedbackRepository, ProjectRepository projectRepository, PublicIdGenerator publicIdGenerator, ObjectMapper objectMapper) {
        this.feedbackRepository = feedbackRepository;
        this.projectRepository = projectRepository;
        this.publicIdGenerator = publicIdGenerator;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public Feedback saveFeedback(String projectId, Map<String, Object> payload, Long userId) {
        ensureProjectBelongsToUser(projectId, userId);

        String feedbackType = (String) payload.get("feedback_type");

        Feedback feedback;
        if ("intent".equalsIgnoreCase(feedbackType)) {
            feedback = Feedback.createIntentCorrection(
                projectId,
                (String) payload.get("intent_field"),
                (String) payload.get("original_value"),
                (String) payload.get("corrected_value"),
                (String) payload.get("category"),
                (String) payload.get("notes")
            );
        } else {
            Integer ideaIndex = payload.get("idea_index") instanceof Number n ? n.intValue() : null;
            String pointName = (String) payload.get("point_name");
            Integer imageIndex = payload.get("image_index") instanceof Number n ? n.intValue() : null;
            String imageUrl = (String) payload.get("image_url");
            String tag = (String) payload.get("tag");
            String comment = (String) payload.get("comment");

            feedback = Feedback.create(
                projectId, feedbackType, ideaIndex, pointName, imageIndex, imageUrl, tag, comment
            );
            feedback.setPromptTemplateVersion((String) payload.get("prompt_template_version"));
            feedback.setRenderedPrompt((String) payload.get("rendered_prompt"));
            Object generationParams = payload.get("generation_params");
            if (generationParams != null) {
                feedback.setGenerationParams(serializeGenerationParams(generationParams));
            }
        }
        feedback.setUserId(userId);
        return publicIdGenerator.assignAndSave(feedback, Feedback::setPublicId, feedbackRepository::save);
    }

    private String serializeGenerationParams(Object generationParams) {
        if (generationParams instanceof String s) {
            return s;
        }
        try {
            return objectMapper.writeValueAsString(generationParams);
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("Invalid generation_params", e);
        }
    }

    @Transactional(readOnly = true)
    public List<Feedback> listUnprocessedIntentCorrections(String projectId, Long userId) {
        ensureProjectBelongsToUser(projectId, userId);
        return feedbackRepository.findByProjectIdAndFeedbackTypeAndProcessedFalseOrderByCreatedAtDesc(projectId, "intent");
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
