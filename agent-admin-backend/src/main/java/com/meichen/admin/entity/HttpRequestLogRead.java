package com.meichen.admin.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "http_request_logs")
public class HttpRequestLogRead {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "method", length = 10)
    private String method;

    @Column(name = "path_pattern", length = 200)
    private String pathPattern;

    @Column(name = "status_code")
    private Integer statusCode;

    @Column(name = "duration_ms")
    private Integer durationMs;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public String getMethod() { return method; }
    public String getPathPattern() { return pathPattern; }
    public Integer getStatusCode() { return statusCode; }
    public Integer getDurationMs() { return durationMs; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
