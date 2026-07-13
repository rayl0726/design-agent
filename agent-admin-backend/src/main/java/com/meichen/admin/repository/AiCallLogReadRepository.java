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
           "GROUP BY l.callType " +
           "ORDER BY COUNT(l) DESC, l.callType")
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

    @Query("SELECT COUNT(l), " +
           "SUM(CASE WHEN l.status = 'success' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN l.status != 'success' THEN 1 ELSE 0 END), " +
           "AVG(l.durationMs), " +
           "COUNT(DISTINCT l.projectId) " +
           "FROM AiCallLogRead l WHERE l.callType = 'image_gen' AND l.createdAt >= :since")
    List<Object[]> aggregateImageGenOverview(@Param("since") LocalDateTime since);

    default java.util.Optional<Object[]> findImageGenOverview(LocalDateTime since) {
        return aggregateImageGenOverview(since).stream().findFirst();
    }

    @Query("SELECT l.provider, COUNT(l), " +
           "SUM(CASE WHEN l.status = 'success' THEN 1 ELSE 0 END), " +
           "AVG(l.durationMs) " +
           "FROM AiCallLogRead l WHERE l.callType = 'image_gen' AND l.createdAt >= :since " +
           "GROUP BY l.provider ORDER BY l.provider")
    List<Object[]> groupImageGenByProvider(@Param("since") LocalDateTime since);

    @Query("SELECT l.errorMessage, COUNT(l) " +
           "FROM AiCallLogRead l WHERE l.callType = 'image_gen' AND l.status != 'success' " +
           "AND l.createdAt >= :since AND l.errorMessage IS NOT NULL " +
           "GROUP BY l.errorMessage ORDER BY COUNT(l) DESC")
    List<Object[]> findImageGenFailureReasons(@Param("since") LocalDateTime since);

    @Query("SELECT CAST(l.createdAt AS date), " +
           "SUM(CASE WHEN l.status = 'success' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN l.status = 'failed' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN l.status = 'rate_limited' THEN 1 ELSE 0 END) " +
           "FROM AiCallLogRead l WHERE l.callType = 'image_gen' AND l.createdAt >= :since " +
           "GROUP BY CAST(l.createdAt AS date) ORDER BY CAST(l.createdAt AS date)")
    List<Object[]> groupImageGenByDate(@Param("since") LocalDateTime since);

    @Query("SELECT l.nodeName, COUNT(l), COUNT(DISTINCT l.projectId) " +
           "FROM AiCallLogRead l WHERE l.callType = 'llm' AND l.createdAt >= :since " +
           "GROUP BY l.nodeName")
    List<Object[]> groupPromptInvocations(@Param("since") LocalDateTime since);

    @Query("SELECT CAST(l.createdAt AS date), l.nodeName, COUNT(l) " +
           "FROM AiCallLogRead l WHERE l.callType = 'llm' AND l.createdAt >= :since " +
           "GROUP BY CAST(l.createdAt AS date), l.nodeName " +
           "ORDER BY CAST(l.createdAt AS date)")
    List<Object[]> groupPromptInvocationsByDate(@Param("since") LocalDateTime since);
}
