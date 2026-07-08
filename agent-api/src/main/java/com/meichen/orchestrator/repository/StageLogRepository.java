package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.StageLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface StageLogRepository extends JpaRepository<StageLog, Long> {

    List<StageLog> findByProjectIdOrderByStartedAtAscIdAsc(String projectId);

    List<StageLog> findByParentIdOrderByStartedAtAscIdAsc(Long parentId);

    Optional<StageLog> findTopByProjectIdAndStageNameAndParentIdIsNullOrderByStartedAtDesc(String projectId, String stageName);
}
