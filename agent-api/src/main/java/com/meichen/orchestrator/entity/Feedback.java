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

    // idea / image / intent
    @Column(name = "feedback_type", nullable = false, length = 20)
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
    private Boolean processed = false;

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

    @Column(name = "public_id", unique = true, nullable = false, length = 32)
    private String publicId;

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

    public static Feedback createIntentCorrection(String projectId, String intentField,
                                                  String originalValue, String correctedValue,
                                                  String category, String notes) {
        Feedback f = new Feedback();
        f.setId(UUID.randomUUID().toString());
        f.setProjectId(projectId);
        f.setFeedbackType("intent");
        f.setIntentField(intentField);
        f.setOriginalValue(originalValue);
        f.setCorrectedValue(correctedValue);
        f.setCategory(category);
        f.setNotes(notes);
        f.setProcessed(false);
        return f;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getProjectId() { return projectId; }
    public void setProjectId(String projectId) { this.projectId = projectId; }

    public String getFeedbackType() { return feedbackType; }
    public void setFeedbackType(String feedbackType) { this.feedbackType = feedbackType; }

    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }

    public String getIntentField() { return intentField; }
    public void setIntentField(String intentField) { this.intentField = intentField; }

    public String getOriginalValue() { return originalValue; }
    public void setOriginalValue(String originalValue) { this.originalValue = originalValue; }

    public String getCorrectedValue() { return correctedValue; }
    public void setCorrectedValue(String correctedValue) { this.correctedValue = correctedValue; }

    public Boolean getProcessed() { return processed; }
    public void setProcessed(Boolean processed) { this.processed = processed; }

    public String getNotes() { return notes; }
    public void setNotes(String notes) { this.notes = notes; }

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

    public String getPublicId() { return publicId; }
    public void setPublicId(String publicId) { this.publicId = publicId; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }
}
