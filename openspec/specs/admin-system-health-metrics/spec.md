## ADDED Requirements

### Requirement: Admin API exposes workflow success rate
The system SHALL provide end-to-end workflow success rate metrics from stage logs.

#### Scenario: Query workflow success rate
- **WHEN** admin requests `GET /api/admin/metrics/system/workflow-success?days=7`
- **THEN** the system SHALL return the percentage of projects where all workflow stages completed successfully, the count of projects with at least one failed stage, and the distribution of failure points by stage name

### Requirement: Admin API exposes retry and error statistics
The system SHALL provide workflow retry and error type distribution metrics.

#### Scenario: Query retry distribution
- **WHEN** admin requests `GET /api/admin/metrics/system/retries?days=7`
- **THEN** the system SHALL return from workflow_logs: total retries, max retry count, retry rate percentage, and retry distribution by node name

#### Scenario: Query error type distribution
- **WHEN** admin requests `GET /api/admin/metrics/system/errors?days=7`
- **THEN** the system SHALL return error count grouped by node name and error category (timeout, api_error, parse_error, validation_error, other)

### Requirement: Admin API exposes time anomaly statistics
The system SHALL provide stage log time anomaly and sub-stage overflow metrics.

#### Scenario: Query time anomaly count
- **WHEN** admin requests `GET /api/admin/metrics/system/anomalies?days=7`
- **THEN** the system SHALL return count of `time_anomaly=true` events, count of `sub_stage_overflow=true` events, and the affected stage names ranked by anomaly frequency

### Requirement: Admin API exposes HTTP request metrics
The system SHALL provide HTTP request QPS and error rate metrics from agent-api.

#### Scenario: Query HTTP request statistics
- **WHEN** admin requests `GET /api/admin/metrics/system/http?hours=1`
- **THEN** the system SHALL return total request count, requests per second, error rate (4xx + 5xx), average response time, and p95 response time, grouped by endpoint pattern

### Requirement: Admin API exposes thread pool and connection pool metrics
The system SHALL provide thread pool and database connection pool utilization metrics.

#### Scenario: Query thread pool status
- **WHEN** admin requests `GET /api/admin/metrics/system/thread-pools`
- **THEN** the system SHALL return for each thread pool (workflowExecutor, dialogueExecutor): active threads, queued tasks, completed tasks, and pool utilization percentage

#### Scenario: Query database connection pool status
- **WHEN** admin requests `GET /api/admin/metrics/system/db-pool`
- **THEN** the system SHALL return HikariCP metrics: active connections, idle connections, total connections, max connections, and threads awaiting connection

### Requirement: Admin API exposes project timeline metrics
The system SHALL provide project-level timeline and performance breakdown.

#### Scenario: Query project stage breakdown
- **WHEN** admin requests `GET /api/admin/metrics/system/project-timeline?projectId=<id>`
- **THEN** the system SHALL return the timeline of all stages for the specified project, including stage name, start time, end time, duration, status, and sub-stage details
