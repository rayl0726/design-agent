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

    @Query("SELECT p FROM ProjectRead p WHERE p.status = 'draft' AND p.createdAt < :cutoff")
    List<ProjectRead> findAbandonedDrafts(@Param("cutoff") LocalDateTime cutoff);
}
