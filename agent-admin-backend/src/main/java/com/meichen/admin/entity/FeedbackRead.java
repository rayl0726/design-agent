package com.meichen.admin.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import java.time.LocalDateTime;

@Entity
@Table(name = "feedbacks")
public class FeedbackRead {

    @Id
    @Column(length = 36)
    private String id;

    @Column(name = "project_id", length = 36)
    private String projectId;

    @Column(name = "feedback_type", length = 20)
    private String feedbackType;

    @Column(name = "category", length = 30)
    private String category;

    @Column(name = "intent_field", length = 50)
    private String intentField;

    @Column(name = "original_value", columnDefinition = "TEXT")
    private String originalValue;

    @Column(name = "corrected_value", columnDefinition = "TEXT")
    private String correctedValue;

    @Column(name = "processed")
    private Boolean processed;

    @Column(name = "notes", columnDefinition = "TEXT")
    private String notes;

    @Column(name = "idea_index")
    private Integer ideaIndex;

    @Column(name = "point_name", length = 100)
    private String pointName;

    @Column(name = "image_index")
    private Integer imageIndex;

    @Column(name = "image_url", length = 500)
    private String imageUrl;

    @Column(name = "prompt_template_version", length = 100)
    private String promptTemplateVersion;

    @Column(name = "tag", length = 50)
    private String tag;

    @Column(name = "comment", columnDefinition = "TEXT")
    private String comment;

    @CreationTimestamp
    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "user_id")
    private Long userId;

    @Column(name = "public_id", length = 32)
    private String publicId;

    public String getId() { return id; }
    public String getProjectId() { return projectId; }
    public String getFeedbackType() { return feedbackType; }
    public String getCategory() { return category; }
    public String getIntentField() { return intentField; }
    public String getOriginalValue() { return originalValue; }
    public String getCorrectedValue() { return correctedValue; }
    public Boolean getProcessed() { return processed; }
    public String getNotes() { return notes; }
    public Integer getIdeaIndex() { return ideaIndex; }
    public String getPointName() { return pointName; }
    public Integer getImageIndex() { return imageIndex; }
    public String getImageUrl() { return imageUrl; }
    public String getPromptTemplateVersion() { return promptTemplateVersion; }
    public String getTag() { return tag; }
    public String getComment() { return comment; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public Long getUserId() { return userId; }
    public String getPublicId() { return publicId; }

    public void setId(String id) { this.id = id; }
    public void setFeedbackType(String feedbackType) { this.feedbackType = feedbackType; }
    public void setCategory(String category) { this.category = category; }
    public void setProcessed(Boolean processed) { this.processed = processed; }
    public void setNotes(String notes) { this.notes = notes; }
}
