## MODIFIED Requirements

### Requirement: Admin can view system overview metrics
The system SHALL expose an admin API that returns aggregated system metrics with time range filtering.

#### Scenario: Overview metrics with time filter
- **WHEN** admin requests `GET /api/admin/metrics/overview?hours=24`
- **THEN** the system SHALL return counts for projects created within the time window, feedback records, image feedback, intent corrections, stage logs, projects with feedback, active projects (modified within window), and completed projects within window

#### Scenario: Overview metrics without time filter
- **WHEN** admin requests `GET /api/admin/metrics/overview` without hours parameter
- **THEN** the system SHALL return all-time cumulative counts (backward compatible with existing behavior)

### Requirement: Admin can view stage performance metrics
The system SHALL expose an admin API that returns aggregated stage log performance data with configurable time window.

#### Scenario: Stage duration with custom time window
- **WHEN** admin requests `GET /api/admin/metrics/stages?hours=72`
- **THEN** the system SHALL return average, p95, and max duration per stage for the last 72 hours, with success count and failure count

### Requirement: Admin can view feedback distribution
The system SHALL expose an admin API that returns feedback distribution by tag and category with time range filtering.

#### Scenario: Feedback distribution with time filter
- **WHEN** admin requests `GET /api/admin/metrics/feedback-distribution?days=30`
- **THEN** the system SHALL return counts grouped by tag and category within the specified time window

## ADDED Requirements

### Requirement: Admin can view metrics trend over time
The system SHALL provide a metrics trend API to track key indicators over time.

#### Scenario: Query project creation trend
- **WHEN** admin requests `GET /api/admin/metrics/trend/projects?days=30&interval=day`
- **THEN** the system SHALL return a time series of daily project creation count and cumulative project count

#### Scenario: Query feedback trend
- **WHEN** admin requests `GET /api/admin/metrics/trend/feedback?days=30&interval=day`
- **THEN** the system SHALL return a time series of daily feedback count by type (image, intent)
