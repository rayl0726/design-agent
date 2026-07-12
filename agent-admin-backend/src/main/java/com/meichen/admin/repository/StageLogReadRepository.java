package com.meichen.admin.repository;

import com.meichen.admin.entity.StageLogRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface StageLogReadRepository extends JpaRepository<StageLogRead, Long> {

    @Query("SELECT s.stageName, COUNT(s), " +
           "SUM(CASE WHEN s.status = 'SUCCESS' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN s.status = 'FAILED' THEN 1 ELSE 0 END) " +
           "FROM StageLogRead s WHERE s.parentId IS NULL AND s.startedAt >= :since " +
           "GROUP BY s.stageName ORDER BY COUNT(s) DESC")
    List<Object[]> aggregateWorkflowSuccess(@Param("since") LocalDateTime since);

    @Query("SELECT " +
           "SUM(CASE WHEN s.timeAnomaly = true THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN s.subStageOverflow = true THEN 1 ELSE 0 END) " +
           "FROM StageLogRead s WHERE s.startedAt >= :since")
    List<Object[]> findAnomalyCountsRaw(@Param("since") LocalDateTime since);

    default Object[] countAnomalies(LocalDateTime since) {
        List<Object[]> rows = findAnomalyCountsRaw(since);
        if (rows.isEmpty() || rows.get(0)[0] == null) {
            return new Object[]{0L, 0L};
        }
        return rows.get(0);
    }

    @Query("SELECT s.stageName, " +
           "SUM(CASE WHEN s.timeAnomaly = true THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN s.subStageOverflow = true THEN 1 ELSE 0 END) " +
           "FROM StageLogRead s WHERE s.startedAt >= :since " +
           "AND (s.timeAnomaly = true OR s.subStageOverflow = true) " +
           "GROUP BY s.stageName ORDER BY COUNT(s) DESC")
    List<Object[]> findAnomalyStages(@Param("since") LocalDateTime since);

    long count();
}
