package com.meichen.admin.repository;

import com.meichen.admin.entity.ProjectRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface ProjectReadRepository extends JpaRepository<ProjectRead, String> {

    long count();

    long countByStatus(String status);

    @Query("SELECT COUNT(DISTINCT f.projectId) FROM FeedbackRead f")
    long countProjectsWithFeedback();
}
