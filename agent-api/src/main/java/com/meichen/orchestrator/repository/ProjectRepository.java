package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.Project;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ProjectRepository extends JpaRepository<Project, String> {

    List<Project> findByStatusOrderByCreatedAtDesc(String status);
}
