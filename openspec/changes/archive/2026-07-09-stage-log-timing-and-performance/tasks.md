## 1. Fix StageLog Timing Logic

- [ ] 1.1 Audit `StageLogService` and `StageLog` entity to identify all places where `duration_ms`, `started_at`, and `completed_at` are set or updated.
- [ ] 1.2 Introduce monotonic clock tracking: in `startStage`, record `System.nanoTime()` in an internal `Map<Long, Long> startNanos` (or add `started_nanos` column).
- [ ] 1.3 In `completeStage` / `failStage`, compute `duration_ms` from `startNanos` instead of wall-clock timestamps.
- [ ] 1.4 Add idempotency guard: only a `RUNNING` stage can transition to `SUCCESS` or `FAILED`; repeated calls return the existing record unchanged.
- [ ] 1.5 Add defensive check: if computed `duration_ms < 0`, set it to `null` and flag `time_anomaly = true`.
- [ ] 1.6 Keep `started_at` / `completed_at` as `LocalDateTime` for display only; document that they MUST NOT be used for duration calculation.
- [ ] 1.7 Add unit tests covering repeated completion, concurrent completion, and monotonic clock behavior.

## 2. Introduce Sub-Stage Logging

- [ ] 2.1 Confirm `stage_logs.parent_id` foreign key and index are in place; add migration if missing.
- [ ] 2.2 Extend `StageLogService` with `startSubStage(parentId, stageName, metadata)` and `completeSubStage(subStageId)` methods.
- [ ] 2.3 In `WorkflowEngine.runNode`, instrument `visual_design` to emit `image_generation` and `idea_rendering` sub-stages.
- [ ] 2.4 In `WorkflowEngine.runNode`, instrument `technical_design` to emit `layout_rendering` and `cost_estimation` sub-stages.
- [ ] 2.5 In `WorkflowEngine.runNode`, instrument `knowledge_retrieve` to emit `semantic_search` and `summary_generation` sub-stages.
- [ ] 2.6 Add configuration flag `stage.sub-stage.enabled` (default `true`) to allow disabling sub-stage logging.
- [ ] 2.7 Add sub-stage time integrity check: on parent completion, verify `parent.duration_ms >= sum(sub.duration_ms)`; otherwise mark `sub_stage_overflow = true`.

## 3. Build Performance Analytics Service

- [ ] 3.1 Create `stage_log_stats` table with columns: `stage_name`, `window_start`, `window_end`, `avg_ms`, `p95_ms`, `max_ms`, `success_count`, `failed_count`.
- [ ] 3.2 Create `StageLogAnalyticsService` in `agent-api` with methods to aggregate by `stage_name` and by `project_id`.
- [ ] 3.3 Implement avg, P95, max duration and failure-rate calculations using database aggregation queries.
- [ ] 3.4 Add composite index on `stage_logs(project_id, stage_name, status, started_at)` to support analytics queries.
- [ ] 3.5 Add scheduled task to pre-aggregate recent 1h / 24h metrics into `stage_log_stats` every minute.
- [ ] 3.6 Add `GET /api/v1/analytics/stages` endpoint returning pre-aggregated metrics.
- [ ] 3.7 Add `GET /api/v1/analytics/stages/{stageName}` endpoint returning detailed metrics for a single stage.
- [ ] 3.8 Add `GET /api/v1/projects/{publicId}/analytics` endpoint returning total session duration and per-stage breakdown.

## 4. Implement Optimization Recommendation Engine

- [ ] 4.1 Define single-stage threshold rules: `visual_design` avg > 60s, `knowledge_retrieve` p95 > 30s, any stage failure rate > 10%.
- [ ] 4.2 Define cross-stage correlation rules: `knowledge_retrieve` slow + `visual_design` slow → cache knowledge; only `image_generation` slow → tune image provider; `semantic_search` slow only → tune vector index.
- [ ] 4.3 Create `StageOptimizationRecommendationService` that maps threshold breaches and correlations to actionable recommendations.
- [ ] 4.4 Include recommendations in analytics endpoints and persist key recommendations to `stage_logs.metadata_json`.
- [ ] 4.5 Add unit tests for recommendation rules with mocked analytics data.

## 5. Decouple Logging and Analytics from Workflow

- [ ] 5.1 Ensure `StageLogService` writes remain synchronous but lightweight (single-row insert/update); verify no blocking aggregate queries are triggered during workflow execution.
- [ ] 5.2 Run `StageLogAnalyticsService` aggregations, scheduled pre-aggregation, and recommendation generation on `dialogueExecutor` or a dedicated analytics thread pool, never on the workflow thread.
- [ ] 5.3 Add async annotation or explicit `CompletableFuture` wrapper for analytics endpoint internals where appropriate.

## 6. Historical Data Repair

- [ ] 6.1 Add Flyway migration or one-time ops script to set `duration_ms = null` and `time_anomaly = true` for all existing records where `duration_ms < 0`.
- [ ] 6.2 Add daily alert during the first week after deployment reporting the count of `time_anomaly` records.
- [ ] 6.3 Document the data repair procedure and rollback steps.

## 7. Frontend Observability Improvements

- [ ] 7.1 Update `ChatView.vue` log drawer to render sub-stages as expandable children under parent stages.
- [ ] 7.2 Display slow-stage warnings and generated recommendations next to affected stages.
- [ ] 7.3 Highlight records flagged with `time_anomaly` or `sub_stage_overflow` in the UI.

## 8. Verification and Rollout

- [ ] 8.1 Run integration test for a full project session and verify all top-level and sub-stage logs have non-negative durations.
- [ ] 8.2 Verify sub-stage time integrity: parent duration >= sum of sub-stage durations.
- [ ] 8.3 Confirm analytics endpoints return expected aggregates for at least 10 historical sessions.
- [ ] 8.4 Deploy to staging, monitor `stage-issue.log` for 24 hours, and confirm no new negative durations appear.
- [ ] 8.5 Document rollout and rollback steps; include the `stage.sub-stage.enabled` toggle in runbooks.
