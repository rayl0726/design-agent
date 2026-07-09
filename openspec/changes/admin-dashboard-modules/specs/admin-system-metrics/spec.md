## ADDED Requirements

### Requirement: Admin can view system overview metrics
The system SHALL expose an admin API that returns aggregated system metrics.

#### Scenario: Overview metrics
- **WHEN** admin requests /api/admin/metrics/overview
- **THEN** the system SHALL return counts for projects, generated images, feedback records, and active sessions

### Requirement: Admin can view stage performance metrics
The system SHALL expose an admin API that returns aggregated stage log performance data.

#### Scenario: Stage duration percentiles
- **WHEN** admin requests /api/admin/metrics/stages
- **THEN** the system SHALL return average and p95 duration per stage for the last 24 hours

### Requirement: Admin can view feedback distribution
The system SHALL expose an admin API that returns feedback distribution by tag and category.

#### Scenario: Feedback by tag
- **WHEN** admin requests /api/admin/metrics/feedback-distribution
- **THEN** the system SHALL return counts grouped by tag and category
