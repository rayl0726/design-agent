## ADDED Requirements

### Requirement: Admin API exposes intent recognition source distribution
The system SHALL provide intent recognition source distribution metrics from intent traces.

#### Scenario: Query source distribution
- **WHEN** admin requests `GET /api/admin/metrics/intent-quality/sources?days=30`
- **THEN** the system SHALL return the distribution of recognition sources (exact, alias, fuzzy, semantic, llm, default, unknown) across all intent fields, including count and percentage

### Requirement: Admin API exposes confidence distribution
The system SHALL provide intent recognition confidence metrics.

#### Scenario: Query confidence distribution
- **WHEN** admin requests `GET /api/admin/metrics/intent-quality/confidence?days=30`
- **THEN** the system SHALL return the confidence score distribution histogram (0-0.3, 0.3-0.5, 0.5-0.7, 0.7-0.85, 0.85-1.0) and the percentage of low-confidence recognitions (confidence < 0.7)

### Requirement: Admin API exposes correction rate by field
The system SHALL provide intent correction rate metrics grouped by intent field.

#### Scenario: Query correction rate by field
- **WHEN** admin requests `GET /api/admin/metrics/intent-quality/correction-rate?days=30`
- **THEN** the system SHALL return for each intent field (space_type, point, budget, style, material): total recognitions, correction count, correction rate percentage, and top 5 most-corrected original values

### Requirement: Admin API exposes dialogue turn distribution
The system SHALL provide dialogue turn metrics to measure how efficiently users complete requirement input.

#### Scenario: Query dialogue turns to completion
- **WHEN** admin requests `GET /api/admin/metrics/intent-quality/dialogue-turns?days=30`
- **THEN** the system SHALL return the distribution of dialogue turns needed before the workflow starts (1 turn, 2 turns, 3 turns, 4+ turns), including average and median

### Requirement: Admin API exposes alias proposal statistics
The system SHALL provide alias proposal and application statistics from the learning flywheel.

#### Scenario: Query alias proposal summary
- **WHEN** admin requests `GET /api/admin/metrics/intent-quality/alias-proposals`
- **THEN** the system SHALL return total proposals, pending proposals, applied proposals, and rejection rate

### Requirement: System provides intent trace aggregation API
The agent-core service SHALL provide an internal API endpoint to aggregate intent trace statistics for the admin backend.

#### Scenario: Query intent trace stats from agent-core
- **WHEN** the admin backend requests `GET /api/v1/admin/intent-traces/stats?days=30` from agent-core
- **THEN** agent-core SHALL read the JSONL trace files, aggregate source distribution and confidence distribution, and return the aggregated statistics as JSON
