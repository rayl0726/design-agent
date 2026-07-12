package com.meichen.admin.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "stage_logs")
public class StageLogRead {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

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

    public Long getId() { return id; }
    public String getProjectId() { return projectId; }
    public String getStageName() { return stageName; }
    public String getStageLabel() { return stageLabel; }
    public String getStatus() { return status; }
    public Long getDurationMs() { return durationMs; }
    public LocalDateTime getStartedAt() { return startedAt; }
    public LocalDateTime getCompletedAt() { return completedAt; }
}
