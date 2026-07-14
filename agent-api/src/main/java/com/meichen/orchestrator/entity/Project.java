package com.meichen.orchestrator.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "java_projects")
public class Project {

    @Id
    @Column(length = 36)
    private String id;

    @Column(nullable = false, length = 255)
    private String name;

    @Column(length = 1000)
    private String description;

    @Column(length = 50)
    private String status = "draft";

    @Column(length = 10)
    private String currentLevel;

    @Column(length = 30)
    private String currentStage;

    @Column(name = "selected_idea_index")
    private Integer selectedIdeaIndex;

    @Column(name = "requirement_json", columnDefinition = "TEXT")
    private String requirementJson;

    @Column(columnDefinition = "TEXT")
    private String rawInputsJson;

    @Column(columnDefinition = "TEXT")
    private String l1OutputJson;

    @Column(columnDefinition = "TEXT")
    private String l2OutputJson;

    @Column(columnDefinition = "TEXT")
    private String l3OutputJson;

    @Column(length = 500)
    private String l1HtmlPath;

    @Column(length = 500)
    private String l2HtmlPath;

    @Column(length = 500)
    private String l3HtmlPath;

    @Column(name = "user_id")
    private Long userId;

    @Column(name = "public_id", unique = true, nullable = false, length = 32)
    private String publicId;

    @Column(name = "agent_type", nullable = false, length = 30)
    private String agentType = "generic";

    @Column(name = "agent_context_json", columnDefinition = "TEXT")
    private String agentContextJson;

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    public Project() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public String getCurrentLevel() { return currentLevel; }
    public void setCurrentLevel(String currentLevel) { this.currentLevel = currentLevel; }

    public String getCurrentStage() { return currentStage; }
    public void setCurrentStage(String currentStage) { this.currentStage = currentStage; }

    public Integer getSelectedIdeaIndex() { return selectedIdeaIndex; }
    public void setSelectedIdeaIndex(Integer selectedIdeaIndex) { this.selectedIdeaIndex = selectedIdeaIndex; }

    public String getRequirementJson() { return requirementJson; }
    public void setRequirementJson(String requirementJson) { this.requirementJson = requirementJson; }

    public String getRawInputsJson() { return rawInputsJson; }
    public void setRawInputsJson(String rawInputsJson) { this.rawInputsJson = rawInputsJson; }

    public String getL1OutputJson() { return l1OutputJson; }
    public void setL1OutputJson(String l1OutputJson) { this.l1OutputJson = l1OutputJson; }

    public String getL2OutputJson() { return l2OutputJson; }
    public void setL2OutputJson(String l2OutputJson) { this.l2OutputJson = l2OutputJson; }

    public String getL3OutputJson() { return l3OutputJson; }
    public void setL3OutputJson(String l3OutputJson) { this.l3OutputJson = l3OutputJson; }

    public String getL1HtmlPath() { return l1HtmlPath; }
    public void setL1HtmlPath(String l1HtmlPath) { this.l1HtmlPath = l1HtmlPath; }

    public String getL2HtmlPath() { return l2HtmlPath; }
    public void setL2HtmlPath(String l2HtmlPath) { this.l2HtmlPath = l2HtmlPath; }

    public String getL3HtmlPath() { return l3HtmlPath; }
    public void setL3HtmlPath(String l3HtmlPath) { this.l3HtmlPath = l3HtmlPath; }

    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }

    public String getPublicId() { return publicId; }
    public void setPublicId(String publicId) { this.publicId = publicId; }

    public String getAgentType() { return agentType; }
    public void setAgentType(String agentType) { this.agentType = agentType; }

    public String getAgentContextJson() { return agentContextJson; }
    public void setAgentContextJson(String agentContextJson) { this.agentContextJson = agentContextJson; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
