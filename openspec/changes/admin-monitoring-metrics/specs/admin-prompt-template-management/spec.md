## ADDED Requirements

### Requirement: Admin can view prompt template usage frequency
The system SHALL track and report how often each prompt template version is used in image generation.

#### Scenario: Query template usage frequency
- **WHEN** admin requests `GET /api/admin/prompt-templates/usage?days=30`
- **THEN** the system SHALL return for each template version: total invocations, unique projects using it, and invocation count trend over time

### Requirement: Admin can view prompt template quality trend
The system SHALL provide quality trend analysis for prompt templates based on feedback correlation.

#### Scenario: Query template quality trend
- **WHEN** admin requests `GET /api/admin/prompt-templates/quality-trend?days=30`
- **THEN** the system SHALL return for each template version a daily time series of: images generated, feedback received, feedback rate, and feedback tag distribution

### Requirement: Admin can compare prompt template versions
The system SHALL provide A/B comparison metrics between different prompt template versions.

#### Scenario: Compare two template versions
- **WHEN** admin requests `GET /api/admin/prompt-templates/compare?v1=atrium-v1&v2=atrium-v2&days=30`
- **THEN** the system SHALL return a side-by-side comparison of: total images, feedback count, feedback rate, positive feedback rate, negative feedback rate, and top feedback tags for each version
