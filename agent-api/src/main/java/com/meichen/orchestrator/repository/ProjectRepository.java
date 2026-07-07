package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.Project;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ProjectRepository extends JpaRepository<Project, String> {

    List<Project> findByStatusOrderByCreatedAtDesc(String status);

    List<Project> findByUserIdOrderByCreatedAtDesc(Long userId);

    Optional<Project> findByIdAndUserId(String id, Long userId);

    Optional<Project> findByPublicId(String publicId);

    Optional<Project> findByPublicIdAndUserId(String publicId, Long userId);
}
