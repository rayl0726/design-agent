package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.RagSearchLog;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;

public interface RagSearchLogRepository extends JpaRepository<RagSearchLog, Long> {

    List<RagSearchLog> findBySearchTypeAndCreatedAtAfter(String searchType, LocalDateTime since);

    long countByCreatedAtAfter(LocalDateTime since);
}
