package com.meichen.orchestrator.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public class RagSearchLogRequest {

    private String projectId;

    @NotBlank
    private String queryText;

    @NotBlank
    private String searchType;

    @NotNull
    private Integer resultCount;

    @NotNull
    private Integer durationMs;

    @NotNull
    private Boolean cacheHit;

    @NotNull
    private Boolean timedOut;

    public String getProjectId() { return projectId; }
    public void setProjectId(String projectId) { this.projectId = projectId; }
    public String getQueryText() { return queryText; }
    public void setQueryText(String queryText) { this.queryText = queryText; }
    public String getSearchType() { return searchType; }
    public void setSearchType(String searchType) { this.searchType = searchType; }
    public Integer getResultCount() { return resultCount; }
    public void setResultCount(Integer resultCount) { this.resultCount = resultCount; }
    public Integer getDurationMs() { return durationMs; }
    public void setDurationMs(Integer durationMs) { this.durationMs = durationMs; }
    public Boolean getCacheHit() { return cacheHit; }
    public void setCacheHit(Boolean cacheHit) { this.cacheHit = cacheHit; }
    public Boolean getTimedOut() { return timedOut; }
    public void setTimedOut(Boolean timedOut) { this.timedOut = timedOut; }
}
