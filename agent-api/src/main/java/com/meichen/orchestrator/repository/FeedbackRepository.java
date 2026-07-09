package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.Feedback;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface FeedbackRepository extends JpaRepository<Feedback, String> {
    List<Feedback> findByProjectIdAndUserIdOrderByCreatedAtDesc(String projectId, Long userId);

    List<Feedback> findByProjectIdAndFeedbackTypeAndProcessedFalseOrderByCreatedAtDesc(String projectId, String feedbackType);

    Optional<Feedback> findByPublicId(String publicId);

    Optional<Feedback> findByPublicIdAndUserId(String publicId, Long userId);
}
