package com.meichen.admin.repository;

import com.meichen.admin.entity.StageLogRead;
import org.springframework.data.jpa.repository.JpaRepository;

public interface StageLogReadRepository extends JpaRepository<StageLogRead, Long> {

    long count();
}
