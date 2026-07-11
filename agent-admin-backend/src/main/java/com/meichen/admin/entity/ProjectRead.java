package com.meichen.admin.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import java.time.LocalDateTime;

@Entity
@Table(name = "java_projects")
public class ProjectRead {

    @Id
    @Column(length = 36)
    private String id;

    @Column(name = "name")
    private String name;

    @Column(name = "status")
    private String status;

    @Column(name = "current_level")
    private String currentLevel;

    @CreationTimestamp
    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "user_id")
    private Long userId;

    public String getId() { return id; }
    public String getName() { return name; }
    public String getStatus() { return status; }
    public String getCurrentLevel() { return currentLevel; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public Long getUserId() { return userId; }
}
