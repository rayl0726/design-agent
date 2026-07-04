package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.WorkflowLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface WorkflowLogRepository extends JpaRepository<WorkflowLog, Long> {

    List<WorkflowLog> findByProjectIdOrderByCreatedAtAsc(String projectId);

    List<WorkflowLog> findByProjectIdAndNodeNameOrderByCreatedAtDesc(String projectId, String nodeName);
}
