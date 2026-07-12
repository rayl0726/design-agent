## ADDED Requirements

### Requirement: Admin API exposes project funnel conversion
The system SHALL provide project status funnel metrics to track conversion from creation to completion.

#### Scenario: Query project funnel
- **WHEN** admin requests `GET /api/admin/metrics/funnel?days=30`
- **THEN** the system SHALL return counts and conversion rates for each project status: draft → generating → completed, including drop-off rates between stages

#### Scenario: Query project abandonment
- **WHEN** admin requests `GET /api/admin/metrics/funnel/abandonment?days=7`
- **THEN** the system SHALL return projects that have been in `draft` status for more than 7 days without any activity, including project ID, name, created_at, and last_activity_at

### Requirement: Admin API exposes project level distribution
The system SHALL provide L1/L2/L3 level distribution metrics.

#### Scenario: Query level distribution
- **WHEN** admin requests `GET /api/admin/metrics/funnel/levels`
- **THEN** the system SHALL return the count and percentage of projects at each level (L1, L2, L3), and the conversion rate from L1 → L2 and L2 → L3

### Requirement: Admin API exposes conversation metrics
The system SHALL provide conversation-level metrics from session messages.

#### Scenario: Query conversation turn statistics
- **WHEN** admin requests `GET /api/admin/metrics/conversations?days=30`
- **THEN** the system SHALL return average turns per project, median turns, max turns, and turn count distribution (1-3, 4-6, 7-10, 10+)

### Requirement: Admin API exposes project dimension distribution
The system SHALL provide project distribution by design requirement dimensions.

#### Scenario: Query distribution by space type
- **WHEN** admin requests `GET /api/admin/metrics/dimensions/space-type`
- **THEN** the system SHALL return project count grouped by space_type (e.g., 购物中心中庭, 快闪店, 百货入口)

#### Scenario: Query distribution by budget level
- **WHEN** admin requests `GET /api/admin/metrics/dimensions/budget-level`
- **THEN** the system SHALL return project count grouped by budget level (low, medium, high)

#### Scenario: Query distribution by style
- **WHEN** admin requests `GET /api/admin/metrics/dimensions/style`
- **THEN** the system SHALL return project count grouped by design style

### Requirement: Admin API exposes project duration metrics
The system SHALL provide project lifecycle duration metrics.

#### Scenario: Query project completion time
- **WHEN** admin requests `GET /api/admin/metrics/funnel/duration?days=30`
- **THEN** the system SHALL return average, median, p90, and max duration from project creation to completion for completed projects within the specified time window
