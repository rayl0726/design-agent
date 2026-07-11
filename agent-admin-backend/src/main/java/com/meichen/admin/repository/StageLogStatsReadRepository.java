package com.meichen.admin.repository;

import com.meichen.admin.entity.StageLogStatsRead;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface StageLogStatsReadRepository extends JpaRepository<StageLogStatsRead, Long> {

    List<StageLogStatsRead> findAllByOrderByWindowStartDesc();
}
