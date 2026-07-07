package com.meichen.orchestrator.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "session_messages")
public class SessionMessage {

    @Id
    @Column(length = 36)
    private String id;

    @Column(name = "project_id", nullable = false, length = 36)
    private String projectId;

    // user / assistant / system
    @Column(nullable = false, length = 20)
    private String role;

    // text / summary / idea_gallery / visual_scheme / proposal
    @Column(nullable = false, length = 30)
    private String messageType;

    // 文本内容或 JSON 字符串
    @Column(nullable = false, columnDefinition = "LONGTEXT")
    private String content;

    @CreationTimestamp
    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "user_id")
    private Long userId;

    @Column(name = "public_id", unique = true, nullable = false, length = 32)
    private String publicId;

    public SessionMessage() {}

    public static SessionMessage create(String projectId, String role, String messageType, String content) {
        SessionMessage msg = new SessionMessage();
        msg.setId(UUID.randomUUID().toString());
        msg.setProjectId(projectId);
        msg.setRole(role);
        msg.setMessageType(messageType);
        msg.setContent(content);
        msg.setCreatedAt(LocalDateTime.now());
        return msg;
    }

    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }

    public String getPublicId() { return publicId; }
    public void setPublicId(String publicId) { this.publicId = publicId; }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getProjectId() { return projectId; }
    public void setProjectId(String projectId) { this.projectId = projectId; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public String getMessageType() { return messageType; }
    public void setMessageType(String messageType) { this.messageType = messageType; }

    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
