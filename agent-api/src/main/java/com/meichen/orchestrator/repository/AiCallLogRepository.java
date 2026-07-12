package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.AiCallLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface AiCallLogRepository extends JpaRepository<AiCallLog, Long> {

    long countByCallTypeAndCreatedAtAfter(String callType, LocalDateTime createdAt);

    List<AiCallLog> findByCallTypeAndCreatedAtAfter(String callType, LocalDateTime createdAt);

    @Query("SELECT l FROM AiCallLog l WHERE l.createdAt >= :since ORDER BY l.createdAt DESC")
    List<AiCallLog> findAllSince(@Param("since") LocalDateTime since);
}
