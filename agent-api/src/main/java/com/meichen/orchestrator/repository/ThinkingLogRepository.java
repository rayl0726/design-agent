package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.ThinkingLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ThinkingLogRepository extends JpaRepository<ThinkingLog, String> {
    List<ThinkingLog> findByProjectIdOrderByCreatedAtAsc(String projectId);

    Optional<ThinkingLog> findTopByProjectIdAndNodeNameOrderByCreatedAtDesc(String projectId, String nodeName);

    Optional<ThinkingLog> findByPublicId(String publicId);

    Optional<ThinkingLog> findByPublicIdAndUserId(String publicId, Long userId);
}
