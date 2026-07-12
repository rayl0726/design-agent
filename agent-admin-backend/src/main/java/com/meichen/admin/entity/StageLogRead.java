package com.meichen.admin.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "stage_logs")
public class StageLogRead {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "public_id", length = 32)
    private String publicId;

    @Column(name = "project_id", length = 36)
    private String projectId;

    @Column(name = "stage_name")
    private String stageName;

    @Column(name = "stage_label")
    private String stageLabel;

    @Column(name = "status")
    private String status;

    @Column(name = "duration_ms")
    private Long durationMs;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @Column(name = "parent_id")
    private Long parentId;

    @Column(name = "error_message", length = 4000)
    private String errorMessage;

    @Column(name = "time_anomaly")
    private boolean timeAnomaly;

    @Column(name = "sub_stage_overflow")
    private boolean subStageOverflow;

    public Long getId() { return id; }
    public String getPublicId() { return publicId; }
    public String getProjectId() { return projectId; }
    public String getStageName() { return stageName; }
    public String getStageLabel() { return stageLabel; }
    public String getStatus() { return status; }
    public Long getDurationMs() { return durationMs; }
    public LocalDateTime getStartedAt() { return startedAt; }
    public LocalDateTime getCompletedAt() { return completedAt; }
    public Long getParentId() { return parentId; }
    public String getErrorMessage() { return errorMessage; }
    public boolean isTimeAnomaly() { return timeAnomaly; }
    public boolean isSubStageOverflow() { return subStageOverflow; }
}
