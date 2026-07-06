package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.Feedback;
import com.meichen.orchestrator.repository.FeedbackRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

@Service
public class FeedbackService {

    private final FeedbackRepository feedbackRepository;

    public FeedbackService(FeedbackRepository feedbackRepository) {
        this.feedbackRepository = feedbackRepository;
    }

    @Transactional
    public Feedback saveFeedback(String projectId, Map<String, Object> payload) {
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
        return feedbackRepository.save(feedback);
    }

    @Transactional(readOnly = true)
    public List<Feedback> listByProject(String projectId) {
        return feedbackRepository.findByProjectIdOrderByCreatedAtDesc(projectId);
    }
}
