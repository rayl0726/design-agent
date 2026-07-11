package com.meichen.admin.repository;

import com.meichen.admin.entity.StageLogRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface StageLogReadRepository extends JpaRepository<StageLogRead, Long> {

    @Query("SELECT s.stageName, AVG(s.durationMs), " +
           "PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY s.durationMs), " +
           "MAX(s.durationMs), " +
           "SUM(CASE WHEN s.status = 'SUCCESS' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN s.status != 'SUCCESS' THEN 1 ELSE 0 END) " +
           "FROM StageLogRead s WHERE s.startedAt >= :since " +
           "GROUP BY s.stageName ORDER BY AVG(s.durationMs) DESC")
    List<Object[]> aggregateByStageNameSince(@Param("since") LocalDateTime since);

    long count();
}
