package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.StageLogStats;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface StageLogStatsRepository extends JpaRepository<StageLogStats, Long> {

    List<StageLogStats> findByWindowEndAfterOrderByStageNameAscWindowStartAsc(LocalDateTime since);

    Optional<StageLogStats> findByStageNameAndWindowStartAndWindowEnd(String stageName, LocalDateTime windowStart, LocalDateTime windowEnd);
}
