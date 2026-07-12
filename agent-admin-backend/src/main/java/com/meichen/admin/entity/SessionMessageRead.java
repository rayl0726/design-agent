package com.meichen.admin.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import java.time.LocalDateTime;

@Entity
@Table(name = "session_messages")
public class SessionMessageRead {

    @Id
    @Column(length = 36)
    private String id;

    @Column(name = "project_id")
    private String projectId;

    @Column(name = "role")
    private String role;

    @Column(name = "message_type")
    private String messageType;

    @Column(name = "content")
    private String content;

    @CreationTimestamp
    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "user_id")
    private Long userId;

    @Column(name = "public_id")
    private String publicId;

    public String getId() { return id; }
    public String getProjectId() { return projectId; }
    public String getRole() { return role; }
    public String getMessageType() { return messageType; }
    public String getContent() { return content; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public Long getUserId() { return userId; }
    public String getPublicId() { return publicId; }
}
