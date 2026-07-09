package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.StageLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface StageLogRepository extends JpaRepository<StageLog, Long> {

    List<StageLog> findByProjectIdOrderByStartedAtAscIdAsc(String projectId);

    List<StageLog> findByParentIdOrderByStartedAtAscIdAsc(Long parentId);

    Optional<StageLog> findTopByProjectIdAndStageNameAndParentIdIsNullOrderByStartedAtDesc(String projectId, String stageName);

    @Query("""
        SELECT s.stageName,
               AVG(s.durationMs),
               MAX(s.durationMs),
               SUM(CASE WHEN s.status = 'SUCCESS' THEN 1 ELSE 0 END),
               SUM(CASE WHEN s.status = 'FAILED' THEN 1 ELSE 0 END),
               COUNT(s.id)
        FROM StageLog s
        WHERE s.parentId IS NULL
          AND s.startedAt >= :since
        GROUP BY s.stageName
        """)
    List<Object[]> aggregateByStageNameSince(@Param("since") LocalDateTime since);

    @Query("""
        SELECT s.durationMs
        FROM StageLog s
        WHERE s.stageName = :stageName
          AND s.parentId IS NULL
          AND s.startedAt >= :windowStart
          AND s.startedAt < :windowEnd
          AND s.durationMs IS NOT NULL
        ORDER BY s.durationMs
        """)
    List<Long> findDurations(@Param("stageName") String stageName,
                             @Param("windowStart") LocalDateTime windowStart,
                             @Param("windowEnd") LocalDateTime windowEnd);
}
