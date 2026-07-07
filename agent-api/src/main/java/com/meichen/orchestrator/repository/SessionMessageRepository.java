package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.SessionMessage;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SessionMessageRepository extends JpaRepository<SessionMessage, String> {
    List<SessionMessage> findByProjectIdOrderByCreatedAtAsc(String projectId);

    List<SessionMessage> findByProjectIdAndUserIdOrderByCreatedAtAsc(String projectId, Long userId);

    Optional<SessionMessage> findByPublicId(String publicId);

    Optional<SessionMessage> findByPublicIdAndUserId(String publicId, Long userId);
}
