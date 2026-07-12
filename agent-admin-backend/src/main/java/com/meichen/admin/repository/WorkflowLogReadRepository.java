package com.meichen.admin.repository;

import com.meichen.admin.entity.WorkflowLogRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface WorkflowLogReadRepository extends JpaRepository<WorkflowLogRead, Long> {

    @Query("SELECT w.nodeName, COUNT(w), SUM(w.retryCount), " +
           "SUM(CASE WHEN w.retryCount > 0 THEN 1 ELSE 0 END) " +
           "FROM WorkflowLogRead w WHERE w.createdAt >= :since " +
           "GROUP BY w.nodeName ORDER BY SUM(w.retryCount) DESC")
    List<Object[]> aggregateRetries(@Param("since") LocalDateTime since);

    @Query("SELECT w.nodeName, COUNT(w), w.errorMessage " +
           "FROM WorkflowLogRead w WHERE w.status = 'failed' AND w.createdAt >= :since " +
           "GROUP BY w.nodeName, w.errorMessage ORDER BY COUNT(w) DESC")
    List<Object[]> aggregateErrors(@Param("since") LocalDateTime since);
}
