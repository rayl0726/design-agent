package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.ThinkingLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ThinkingLogRepository extends JpaRepository<ThinkingLog, String> {
    List<ThinkingLog> findByProjectIdOrderByCreatedAtAsc(String projectId);
}
