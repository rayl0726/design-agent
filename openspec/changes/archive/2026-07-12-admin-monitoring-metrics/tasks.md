## 1. Database Schema

- [x] 1.1 Create `ai_call_logs` table with columns: id, project_id, call_type (llm/vlm/embedding/image_generation), provider, model, node_name, status (success/failed/timeout/rate_limited), duration_ms, input_tokens, output_tokens, total_tokens, error_message, retry_count, created_at. Add indexes on (call_type, created_at), (provider, created_at), (project_id), (status, created_at)
- [x] 1.2 Create `rag_search_logs` table with columns: id, project_id, query_text, search_type (semantic/structured/fallback), result_count, duration_ms, cache_hit, timed_out, created_at. Add indexes on (search_type, created_at), (project_id)
- [x] 1.3 Add `http_request_logs` table for HTTP request metrics: id, method, path_pattern, status_code, duration_ms, created_at. Add index on (path_pattern, created_at)
- [x] 1.4 Create Flyway migration script `V2026071201__create_ai_call_logs.sql`
- [x] 1.5 Create Flyway migration script `V2026071203__create_rag_search_logs.sql`
- [x] 1.6 Create Flyway migration script `V2026071202__create_http_request_logs.sql`

## 2. Python-side Instrumentation (agent-core)

- [x] 2.1 Create `app/services/call_logger.py` with async `log_ai_call()` function that POSTs to agent-api `/api/v1/internal/ai-call-logs` endpoint. Use fire-and-forget pattern (non-blocking, swallow errors)
- [x] 2.2 Create `@log_ai_call(call_type)` decorator for automatic AI call logging. Capture provider, model, duration, status, error, retry count
- [x] 2.3 Apply `@log_ai_call('llm')` decorator to `LLMClient.complete()` and `LLMClient.stream()` in `llm_client.py`
- [x] 2.4 Apply `@log_ai_call('vlm')` decorator to `ZhipuVLMClient.describe()` and `ZhipuVLMClient.describe_batch()` in `vlm_client.py`
- [x] 2.5 Apply `@log_ai_call('embedding')` decorator to `EmbeddingClient.embed()` and `EmbeddingClient.embed_batch()` in `embedding_client.py`
- [x] 2.6 Apply `@log_ai_call('image_generation')` decorator to `ImageGenerationService.generate()` in `image_generation.py`. Log provider, model, duration, success/failure
- [x] 2.7 Create `log_rag_search()` function in `rag_logger.py` for knowledge base search logging
- [x] 2.8 Add `log_rag_search()` calls in `knowledge_base.py` semantic_search(), structured_query() methods (with `log_rag_search_sync()` for thread context)
- [x] 2.9 Create agent-core API endpoint `GET /api/v1/admin/intent-traces/stats` that reads JSONL trace files and returns aggregated source distribution and confidence distribution
- [x] 2.10 Create agent-core API endpoint `GET /api/v1/admin/intent-traces/correction-stats` that reads JSONL traces and returns per-field correction stats

## 3. Java Internal API (agent-api)

- [x] 3.1 Create `AiCallLog` JPA entity in agent-api mapping to `ai_call_logs` table
- [x] 3.2 Create `AiCallLogRepository` with save method and query methods (countByTypeAndCreatedAtAfter, groupByProvider, timeSeriesQueries)
- [x] 3.3 Create `RagSearchLog` JPA entity mapping to `rag_search_logs` table
- [x] 3.4 Create `RagSearchLogRepository` with save and aggregation query methods
- [x] 3.5 Create `InternalLogController` with `POST /api/v1/internal/ai-call-logs` endpoint accepting AI call log records from Python
- [x] 3.6 Create `POST /api/v1/internal/rag-search-logs` endpoint for Python RAG search logging
- [x] 3.7 Add HTTP request interceptor/filter to log request method, path, status code, and duration to `http_request_logs` table. Use async write to avoid blocking
- [x] 3.8 Configure HikariCP metrics exposure via Spring Boot Actuator `/actuator/metrics/hikaricp.*`
- [x] 3.9 Add Spring Boot Actuator dependency to agent-api pom.xml and configure management endpoints

## 4. Admin Backend - AI Model Metrics (agent-admin-backend)

- [x] 4.1 Create `AiCallLogRead` entity (read-only, maps to `ai_call_logs` table) in admin-backend
- [x] 4.2 Create `AiCallLogReadRepository` with query methods: countByTypeGroupByStatus, groupByProvider, timeSeriesByType, sumTokensByProvider
- [x] 4.3 Create `AiCallMetricsDTO` record: callType, totalCount, successCount, failedCount, rateLimitedCount, avgLatencyMs, p95LatencyMs, totalInputTokens, totalOutputTokens
- [x] 4.4 Create `AiCallProviderBreakdownDTO` record: provider, model, callCount, successRate, avgLatencyMs, totalTokens
- [x] 4.5 Create `AiCallTimelineDTO` record: timestamp, callType, count, errorCount
- [x] 4.6 Create `TokenUsageDTO` record: date, provider, inputTokens, outputTokens, totalTokens, estimatedCost
- [x] 4.7 Create `AiModelMetricsService` with methods: getCallSummary(hours), getByProvider(hours), getTimeline(hours, interval), getTokenUsage(hours)
- [x] 4.8 Create `AiModelMetricsController` at `/api/admin/metrics/ai-calls` with endpoints: GET /summary, GET /by-provider, GET /timeline, GET /tokens
- [x] 4.9 Add provider pricing configuration in `application.yml` for cost estimation (per 1K tokens, per image) — added in Sprint 5 Task 1, later removed in final review because no Java consumer existed

## 5. Admin Backend - Image Generation Metrics

- [x] 5.1 Create `ImageGenMetricsService` querying `ai_call_logs` WHERE call_type='image_gen' joined with `feedbacks` — corrected from 'image_generation' to match production data
- [x] 5.2 Create `ImageGenOverviewDTO` record: totalGenerated, successCount, failedCount, successRate, avgGenerationMs, avgImagesPerProject
- [x] 5.3 Create `ImageGenProviderDTO` record: provider, callCount, successRate, avgLatencyMs, failureReasons
- [x] 5.4 Create `ImageFeedbackDTO` record: totalImages, imagesWithFeedback, feedbackRate, tagDistribution
- [x] 5.5 Create `ImageGenMetricsController` at `/api/admin/metrics/image-generation` with endpoints: GET /overview, GET /by-provider, GET /feedback, GET /feedback-trend, GET /distribution

## 6. Admin Backend - Business Funnel Metrics

- [x] 6.1 Create `BusinessFunnelService` querying `projects` and `session_messages` tables
- [x] 6.2 Create `ProjectFunnelDTO` record: draftCount, generatingCount, completedCount, draftToGeneratingRate, generatingToCompletedRate, dropOffRate
- [x] 6.3 Create `ProjectAbandonmentDTO` record: projectId, projectName, createdAt, lastActivityAt, daysIdle
- [x] 6.4 Create `LevelDistributionDTO` record: level, count, percentage, conversionRateFromPrevious
- [x] 6.5 Create `ConversationStatsDTO` record: avgTurns, medianTurns, maxTurns, turnDistribution
- [x] 6.6 Create `DimensionDistributionDTO` record: dimensionValue, count, percentage
- [x] 6.7 Create `ProjectDurationDTO` record: avgDurationHours, medianDurationHours, p90DurationHours, maxDurationHours
- [x] 6.8 Create `BusinessFunnelController` at `/api/admin/metrics/funnel` with endpoints: GET /, GET /abandonment, GET /levels, GET /duration
- [x] 6.9 Create `ConversationController` at `/api/admin/metrics/conversations`
- [x] 6.10 Create `DimensionController` at `/api/admin/metrics/dimensions` with endpoints: GET /space-type, GET /budget-level, GET /style

## 7. Admin Backend - Intent Quality Metrics

- [x] 7.1 Create `IntentQualityService` that calls agent-core `/api/v1/admin/intent-traces/stats` via WebClient
- [x] 7.2 Create `IntentSourceDistributionDTO` record: source, count, percentage
- [x] 7.3 Create `ConfidenceDistributionDTO` record: buckets (List<ConfidenceBucket>), lowConfidenceRate
- [x] 7.4 Create `CorrectionRateDTO` record: field, totalRecognitions, correctionCount, correctionRate, topCorrectedValues
- [x] 7.5 Create `DialogueTurnDTO` record: turnRange, count, percentage, avgTurns, medianTurns
- [x] 7.6 Create `AliasProposalStatsDTO` record: totalProposals, pendingCount, appliedCount, rejectionRate
- [x] 7.7 Create `IntentQualityController` at `/api/admin/metrics/intent-quality` with endpoints: GET /sources, GET /confidence, GET /correction-rate, GET /dialogue-turns, GET /alias-proposals
- [ ] 7.8 Add correction rate query from `feedbacks` table WHERE feedback_type='intent', grouped by intent_field (deferred — correction rate currently sourced from intent traces)

## 8. Admin Backend - Knowledge RAG Metrics

- [x] 8.1 Create `RagSearchLogRead` entity (read-only, maps to `rag_search_logs`) in admin-backend
- [x] 8.2 Create `RagSearchLogReadRepository` with aggregation queries
- [x] 8.3 Create `RagOverviewDTO` record: totalSearches, avgResultCount, avgLatencyMs, cacheHitRate, timeoutCount, fallbackRate
- [x] 8.4 Create `RagTimelineDTO` record: timestamp, searchCount, avgLatencyMs, cacheHitRate
- [ ] 8.5 Create `RagInventoryDTO` record: caseCount, materialCount, imageCount, lastUpdatedAt (deferred — inventory endpoint returns placeholder, needs Milvus stats)
- [x] 8.6 Create `RagZeroResultDTO` record: queryText, searchCount, lastSearchedAt
- [x] 8.7 Create `RagMetricsController` at `/api/admin/metrics/rag` with endpoints: GET /overview, GET /timeline, GET /inventory, GET /zero-results

## 9. Admin Backend - System Health Metrics

- [x] 9.1 Create `SystemHealthService` querying `stage_logs`, `workflow_logs`, and `http_request_logs`
- [x] 9.2 Create `WorkflowSuccessDTO` record: totalProjects, successCount, failedCount, successRate, failurePoints
- [x] 9.3 Create `RetryDistributionDTO` record: totalRetries, maxRetryCount, retryRate, retryByNode
- [x] 9.4 Create `ErrorTypeDistributionDTO` record: nodeName, errorCategory, count
- [x] 9.5 Create `AnomalyStatsDTO` record: timeAnomalyCount, subStageOverflowCount, affectedStages
- [x] 9.6 Create `HttpRequestStatsDTO` record: totalRequests, qps, errorRate, avgResponseMs, p95ResponseMs, byEndpoint
- [x] 9.7 Create `ThreadPoolStatsDTO` record: poolName, activeThreads, queuedTasks, completedTasks, poolUtilization
- [x] 9.8 Create `DbPoolStatsDTO` record: activeConnections, idleConnections, totalConnections, maxConnections, awaitingThreads
- [x] 9.9 Create `SystemHealthController` at `/api/admin/metrics/system` with endpoints: GET /workflow-success, GET /retries, GET /errors, GET /anomalies, GET /http, GET /thread-pools, GET /db-pool

## 10. Admin Backend - Enhanced Overview & Trend

- [x] 10.1 Modify `MetricsOverviewDTO` to add: activeProjectsCount, completedProjectsInWindow, timeWindowHours parameter support
- [x] 10.2 Modify `MetricsAdminService.getOverview()` to accept optional `hours` parameter for time-filtered counts
- [x] 10.3 Create `MetricsTrendService` with project creation trend and feedback trend queries
- [x] 10.4 Create `TrendDTO` record: date, count, cumulativeCount
- [x] 10.5 Modify `MetricsAdminController` to accept `hours` parameter on /overview and /feedback-distribution endpoints
- [x] 10.6 Add `GET /api/admin/metrics/trend/projects` and `GET /api/admin/metrics/trend/feedback` endpoints

## 11. Admin Backend - Prompt Template Enhanced Metrics

- [x] 11.1 Create `PromptTemplateUsageDTO` record: templateVersion, totalInvocations, uniqueProjects, invocationTrend
- [x] 11.2 Create `PromptTemplateQualityTrendDTO` record: date, templateVersion, imagesGenerated, feedbackCount, feedbackRate, tagDistribution
- [x] 11.3 Create `PromptTemplateCompareDTO` record: version, totalImages, feedbackCount, feedbackRate, positiveRate, negativeRate, topTags
- [x] 11.4 Add usage tracking methods to `PromptTemplateAdminService` querying `ai_call_logs` WHERE node_name LIKE '%prompt%' joined with `feedbacks`
- [x] 11.5 Add `GET /api/admin/prompt-templates/usage`, `GET /quality-trend`, `GET /compare` endpoints to `PromptTemplateAdminController`

## 12. Admin Frontend - Dashboard Refactor

- [x] 12.1 Add time range selector component (24h / 72h / 7d / 30d) to Dashboard, pass as query parameter to all API calls
- [x] 12.2 Expand overview cards from 6 to 12: add activeProjects, completedInWindow, aiCallCount, imageGenSuccessRate, avgDialogueTurns, workflowSuccessRate
- [x] 12.3 Add project funnel chart (funnel diagram using ECharts) showing draft → generating → completed conversion
- [x] 12.4 Add project creation trend line chart on Dashboard
- [x] 12.5 Add feedback trend line chart on Dashboard

## 13. Admin Frontend - AI Model Monitoring Page

- [x] 13.1 Create `AiModelMonitoring.vue` page with tab layout: LLM / VLM / Embedding / Image Gen
- [x] 13.2 Add call summary cards: total calls, success rate, error rate, avg latency, total tokens
- [x] 13.3 Add provider distribution pie chart
- [x] 13.4 Add call timeline stacked bar chart (success vs failed over time)
- [x] 13.5 Add token usage trend line chart with cost estimation overlay
- [x] 13.6 Add error rate & 429 rate trend chart — error rate implemented; 429 rate deferred because timeline data has no dedicated 429 field
- [x] 13.7 Add router entry and navigation menu item for AI Model Monitoring

## 14. Admin Frontend - Image Generation Monitoring Page

- [x] 14.1 Create `ImageGenMonitoring.vue` page
- [x] 14.2 Add image gen overview cards: total, success, failed, success rate, avg time, images per project
- [x] 14.3 Add provider distribution bar chart with success/failure stacked
- [x] 14.4 Add feedback rate gauge chart and tag distribution pie chart
- [x] 14.5 Add feedback trend line chart (30-day)
- [x] 14.6 Add router entry and navigation menu item

## 15. Admin Frontend - Intent Quality Monitoring Page

- [x] 15.1 Create `IntentQuality.vue` page
- [x] 15.2 Add recognition source distribution pie chart
- [x] 15.3 Add confidence distribution histogram
- [x] 15.4 Add correction rate by field bar chart with top corrected values table
- [ ] 15.5 Add dialogue turns distribution bar chart (deferred — backend endpoint is placeholder)
- [x] 15.6 Add alias proposal statistics cards
- [x] 15.7 Add router entry and navigation menu item

## 16. Admin Frontend - System Health Monitoring Page

- [x] 16.1 Create `SystemHealth.vue` page
- [x] 16.2 Add workflow success rate gauge chart and failure point bar chart
- [x] 16.3 Add retry distribution heatmap by node
- [x] 16.4 Add time anomaly & sub-stage overflow count cards with affected stages table
- [x] 16.5 Add HTTP QPS & error rate trend line chart
- [x] 16.6 Add thread pool utilization gauge charts (workflowExecutor, dialogueExecutor)
- [x] 16.7 Add database connection pool status card
- [x] 16.8 Add router entry and navigation menu item

## 17. Admin Frontend - Prompt Template Enhanced Page

- [x] 17.1 Modify `PromptTemplates.vue` to add usage frequency tab
- [x] 17.2 Add template usage frequency bar chart and invocation trend line chart
- [x] 17.3 Add quality trend line chart (feedback rate over time per version)
- [x] 17.4 Add version comparison table with side-by-side metrics
- [ ] 17.5 Add A/B comparison radar chart for two selected versions

## 18. Integration & Testing

- [x] 18.1 Write integration tests for `AiModelMetricsController` all endpoints
- [x] 18.2 Write integration tests for `ImageGenMetricsController` all endpoints
- [x] 18.3 Write integration tests for `BusinessFunnelController` all endpoints
- [x] 18.4 Write integration tests for `IntentQualityController` all endpoints
- [x] 18.5 Write integration tests for `RagMetricsController` all endpoints
- [x] 18.6 Write integration tests for `SystemHealthController` all endpoints
- [x] 18.7 Write unit tests for Python `@log_ai_call` decorator: verify log record is created with correct fields
- [x] 18.8 Write unit tests for Python `log_rag_search()`: verify log record is created
- [x] 18.9 Write unit tests for agent-core intent-traces stats endpoint
- [ ] 18.10 End-to-end test: trigger a full workflow and verify all metrics endpoints return expected data
- [x] 18.11 Verify frontend pages render correctly with real data
- [ ] 18.12 Performance test: verify metrics queries complete under 500ms with 100K rows in ai_call_logs

## 19. Documentation

- [ ] 19.1 Update admin backend README with new metrics endpoints documentation
- [ ] 19.2 Create metrics catalog document listing all available metrics, their APIs, and data sources
- [ ] 19.3 Document Python instrumentation guide: how to add `@log_ai_call` to new AI providers
