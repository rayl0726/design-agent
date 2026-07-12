package com.meichen.admin.repository;

import com.meichen.admin.entity.ProjectRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface ProjectReadRepository extends JpaRepository<ProjectRead, String> {

    long count();

    long countByStatus(String status);

    long countByStatusAndCreatedAtAfter(String status, LocalDateTime createdAt);

    @Query("SELECT COUNT(DISTINCT f.projectId) FROM FeedbackRead f")
    long countProjectsWithFeedback();

    @Query("SELECT p FROM ProjectRead p WHERE p.status IN :statuses AND p.createdAt < :cutoff")
    List<ProjectRead> findAbandonedDrafts(@Param("statuses") List<String> statuses, @Param("cutoff") LocalDateTime cutoff);

    long countByCurrentLevel(String currentLevel);

    List<ProjectRead> findByStatusAndCreatedAtAfter(String status, LocalDateTime createdAt);

    @Query("SELECT p FROM ProjectRead p WHERE p.status IN :statuses AND p.createdAt >= :since")
    List<ProjectRead> findByStatusInAndCreatedAtAfter(@Param("statuses") List<String> statuses, @Param("since") LocalDateTime since);

    List<ProjectRead> findByCreatedAtAfter(LocalDateTime createdAt);

    long countByCreatedAtAfter(LocalDateTime createdAt);

    long countByCreatedAtBefore(LocalDateTime createdAt);

    @Query("SELECT CAST(p.createdAt AS date), COUNT(p) FROM ProjectRead p WHERE p.createdAt >= :since GROUP BY CAST(p.createdAt AS date) ORDER BY CAST(p.createdAt AS date)")
    List<Object[]> countByDate(@Param("since") LocalDateTime since);

    @Query("SELECT COUNT(p) FROM ProjectRead p WHERE p.status IN :statuses AND p.createdAt >= :since")
    long countByStatusInAndCreatedAtAfter(@Param("statuses") List<String> statuses, @Param("since") LocalDateTime since);

    @Query("SELECT COUNT(p) FROM ProjectRead p WHERE p.status IN :statuses")
    long countByStatusIn(@Param("statuses") List<String> statuses);
}
