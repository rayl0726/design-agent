package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.HttpRequestLog;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;

public interface HttpRequestLogRepository extends JpaRepository<HttpRequestLog, Long> {

    List<HttpRequestLog> findByCreatedAtAfter(LocalDateTime createdAt);

    long countByCreatedAtAfter(LocalDateTime createdAt);
}
