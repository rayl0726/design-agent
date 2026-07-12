package com.meichen.orchestrator.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "http_request_logs")
public class HttpRequestLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "method", length = 10, nullable = false)
    private String method;

    @Column(name = "path_pattern", length = 200, nullable = false)
    private String pathPattern;

    @Column(name = "status_code", nullable = false)
    private Integer statusCode;

    @Column(name = "duration_ms", nullable = false)
    private Integer durationMs;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public HttpRequestLog() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getMethod() { return method; }
    public void setMethod(String method) { this.method = method; }
    public String getPathPattern() { return pathPattern; }
    public void setPathPattern(String pathPattern) { this.pathPattern = pathPattern; }
    public Integer getStatusCode() { return statusCode; }
    public void setStatusCode(Integer statusCode) { this.statusCode = statusCode; }
    public Integer getDurationMs() { return durationMs; }
    public void setDurationMs(Integer durationMs) { this.durationMs = durationMs; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
