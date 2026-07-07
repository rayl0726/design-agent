package com.meichen.orchestrator.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "feedbacks")
public class Feedback {

    @Id
    @Column(length = 36)
    private String id;

    @Column(name = "project_id", nullable = false, length = 36)
    private String projectId;

    // idea / image
    @Column(name = "feedback_type", nullable = false, length = 20)
    private String feedbackType;

    @Column(name = "idea_index")
    private Integer ideaIndex;

    @Column(name = "point_name", length = 100)
    private String pointName;

    @Column(name = "image_index")
    private Integer imageIndex;

    @Column(name = "image_url", length = 500)
    private String imageUrl;

    // 风格/调性、构图/视角、内容、材质/灯光
    @Column(name = "tag", length = 50)
    private String tag;

    @Column(name = "comment", columnDefinition = "TEXT")
    private String comment;

    @CreationTimestamp
    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "user_id")
    private Long userId;

    public Feedback() {}

    public static Feedback create(String projectId, String feedbackType, Integer ideaIndex,
                                  String pointName, Integer imageIndex, String imageUrl,
                                  String tag, String comment) {
        Feedback f = new Feedback();
        f.setId(UUID.randomUUID().toString());
        f.setProjectId(projectId);
        f.setFeedbackType(feedbackType);
        f.setIdeaIndex(ideaIndex);
        f.setPointName(pointName);
        f.setImageIndex(imageIndex);
        f.setImageUrl(imageUrl);
        f.setTag(tag);
        f.setComment(comment);
        return f;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getProjectId() { return projectId; }
    public void setProjectId(String projectId) { this.projectId = projectId; }

    public String getFeedbackType() { return feedbackType; }
    public void setFeedbackType(String feedbackType) { this.feedbackType = feedbackType; }

    public Integer getIdeaIndex() { return ideaIndex; }
    public void setIdeaIndex(Integer ideaIndex) { this.ideaIndex = ideaIndex; }

    public String getPointName() { return pointName; }
    public void setPointName(String pointName) { this.pointName = pointName; }

    public Integer getImageIndex() { return imageIndex; }
    public void setImageIndex(Integer imageIndex) { this.imageIndex = imageIndex; }

    public String getImageUrl() { return imageUrl; }
    public void setImageUrl(String imageUrl) { this.imageUrl = imageUrl; }

    public String getTag() { return tag; }
    public void setTag(String tag) { this.tag = tag; }

    public String getComment() { return comment; }
    public void setComment(String comment) { this.comment = comment; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }
}
