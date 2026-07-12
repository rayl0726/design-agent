## ADDED Requirements

### Requirement: Admin API exposes image generation statistics
The system SHALL provide admin API endpoints to query image generation performance and quality metrics.

#### Scenario: Query image generation overview
- **WHEN** admin requests `GET /api/admin/metrics/image-generation/overview?hours=24`
- **THEN** the system SHALL return total generation count, success count, failure count, success rate, average generation time, and total images generated per project on average

#### Scenario: Query provider distribution
- **WHEN** admin requests `GET /api/admin/metrics/image-generation/by-provider?hours=24`
- **THEN** the system SHALL return per-provider (zhipu, siliconflow, pollinations, comfyui) call count, success rate, average latency, and failure reason distribution

### Requirement: Admin API exposes image feedback analysis
The system SHALL provide image feedback analysis metrics to track generation quality.

#### Scenario: Query image feedback rate
- **WHEN** admin requests `GET /api/admin/metrics/image-generation/feedback?hours=168`
- **THEN** the system SHALL return total images generated, images with feedback, feedback rate percentage, and feedback tag distribution (e.g., composition, style_mismatch, subject_unclear, background_clutter)

#### Scenario: Query feedback trend over time
- **WHEN** admin requests `GET /api/admin/metrics/image-generation/feedback-trend?days=30`
- **THEN** the system SHALL return a daily time series of feedback rate to identify quality trends

### Requirement: Admin API exposes per-project image statistics
The system SHALL provide per-project image generation statistics.

#### Scenario: Query image generation distribution
- **WHEN** admin requests `GET /api/admin/metrics/image-generation/distribution`
- **THEN** the system SHALL return the distribution of images generated per project, including min, max, median, and p90 values
