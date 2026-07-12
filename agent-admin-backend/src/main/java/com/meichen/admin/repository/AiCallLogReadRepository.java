package com.meichen.admin.repository;

import com.meichen.admin.entity.AiCallLogRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface AiCallLogReadRepository extends JpaRepository<AiCallLogRead, Long> {

    long countByCallTypeAndCreatedAtAfter(String callType, LocalDateTime createdAt);

    @Query("SELECT l.callType, COUNT(l), " +
           "SUM(CASE WHEN l.status = 'success' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN l.status = 'failed' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN l.status = 'rate_limited' THEN 1 ELSE 0 END), " +
           "AVG(l.durationMs), " +
           "SUM(l.inputTokens), " +
           "SUM(l.outputTokens) " +
           "FROM AiCallLogRead l WHERE l.createdAt >= :since " +
           "GROUP BY l.callType")
    List<Object[]> groupByCallType(@Param("since") LocalDateTime since);

    @Query("SELECT l.provider, l.model, COUNT(l), " +
           "SUM(CASE WHEN l.status = 'success' THEN 1 ELSE 0 END), " +
           "AVG(l.durationMs), " +
           "SUM(l.totalTokens) " +
           "FROM AiCallLogRead l WHERE l.createdAt >= :since " +
           "GROUP BY l.provider, l.model")
    List<Object[]> groupByProvider(@Param("since") LocalDateTime since);

    @Query("SELECT CAST(l.createdAt AS date), l.callType, COUNT(l), " +
           "SUM(CASE WHEN l.status != 'success' THEN 1 ELSE 0 END) " +
           "FROM AiCallLogRead l WHERE l.createdAt >= :since " +
           "GROUP BY CAST(l.createdAt AS date), l.callType " +
           "ORDER BY CAST(l.createdAt AS date)")
    List<Object[]> groupByDateAndCallType(@Param("since") LocalDateTime since);

    @Query("SELECT CAST(l.createdAt AS date), l.provider, " +
           "SUM(l.inputTokens), SUM(l.outputTokens), SUM(l.totalTokens) " +
           "FROM AiCallLogRead l WHERE l.createdAt >= :since " +
           "GROUP BY CAST(l.createdAt AS date), l.provider " +
           "ORDER BY CAST(l.createdAt AS date)")
    List<Object[]> groupTokensByDateAndProvider(@Param("since") LocalDateTime since);

    @Query("SELECT l FROM AiCallLogRead l WHERE l.status != 'success' AND l.createdAt >= :since " +
           "ORDER BY l.createdAt DESC LIMIT :limit")
    List<AiCallLogRead> findRecentErrors(@Param("since") LocalDateTime since, @Param("limit") int limit);
}
