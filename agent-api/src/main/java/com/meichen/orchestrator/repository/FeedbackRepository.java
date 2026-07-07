package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.Feedback;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface FeedbackRepository extends JpaRepository<Feedback, String> {
    List<Feedback> findByProjectIdAndUserIdOrderByCreatedAtDesc(String projectId, Long userId);
}
