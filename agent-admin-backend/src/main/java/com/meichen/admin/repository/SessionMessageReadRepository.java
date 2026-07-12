package com.meichen.admin.repository;

import com.meichen.admin.entity.SessionMessageRead;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SessionMessageReadRepository extends JpaRepository<SessionMessageRead, String> {

    long countByProjectIdAndRole(String projectId, String role);
}
