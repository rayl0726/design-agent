## ADDED Requirements

### Requirement: Stage duration SHALL never be negative
The system SHALL compute stage duration using a monotonic clock and idempotent state transitions, ensuring `duration_ms` is always greater than or equal to zero.

#### Scenario: Completing a running stage records non-negative duration
- **WHEN** the workflow engine starts a stage and later completes it
- **THEN** the resulting `StageLog` SHALL have `duration_ms >= 0`

#### Scenario: Repeated completion does not overwrite duration
- **WHEN** the same stage is completed more than once
- **THEN** only the first completion SHALL update `completed_at` and `duration_ms`; subsequent completions SHALL be ignored

#### Scenario: System time adjustment does not cause negative duration
- **WHEN** the operating system clock is adjusted backwards between stage start and completion
- **THEN** the recorded `duration_ms` SHALL remain non-negative because it is derived from `System.nanoTime()` or equivalent monotonic source

### Requirement: Long-running workflow stages SHALL emit sub-stage logs
The system SHALL break high-level workflow stages into sub-stages for image generation, LLM calls, knowledge retrieval, layout rendering, and cost estimation, linked via `parent_id`.

#### Scenario: Visual design stage creates image generation sub-stage
- **WHEN** the `visual_design` workflow node executes image generation
- **THEN** the system SHALL create a sub-stage log named `image_generation` with `parent_id` pointing to the `visual_design` stage log

#### Scenario: Visual design stage creates idea rendering sub-stage
- **WHEN** the `visual_design` workflow node executes LLM-based creative rendering
- **THEN** the system SHALL create a sub-stage log named `idea_rendering` with `parent_id` pointing to the `visual_design` stage log

#### Scenario: Knowledge retrieve stage creates semantic search sub-stage
- **WHEN** the `knowledge_retrieve` workflow node executes semantic search
- **THEN** the system SHALL create a sub-stage log named `semantic_search` with `parent_id` pointing to the `knowledge_retrieve` stage log

#### Scenario: Technical design stage creates cost estimation sub-stage
- **WHEN** the `technical_design` workflow node executes cost estimation
- **THEN** the system SHALL create a sub-stage log named `cost_estimation` with `parent_id` pointing to the `technical_design` stage log

### Requirement: System SHALL provide stage performance analytics
The system SHALL aggregate `stage_logs` data to provide average duration, P95 latency, maximum duration, and failure rate per stage name and per project session.

#### Scenario: Aggregate average and P95 duration by stage name
- **WHEN** the analytics service queries completed stage logs grouped by `stage_name`
- **THEN** it SHALL return average duration, P95 duration, and maximum duration for each stage name

#### Scenario: Aggregate failure rate by stage name
- **WHEN** the analytics service queries stage logs grouped by `stage_name` and `status`
- **THEN** it SHALL return the failure rate as the ratio of failed stages to total stages for each stage name

#### Scenario: Compute total project session duration
- **WHEN** the analytics service receives a `project_id`
- **THEN** it SHALL return the sum of top-level stage durations for that project session

### Requirement: System SHALL generate optimization recommendations from analytics
The system SHALL compare aggregated stage metrics against predefined thresholds and emit actionable optimization recommendations for slow or unreliable stages.

#### Scenario: Slow visual design recommends parallel image generation
- **WHEN** the average duration of `visual_design` exceeds 60 seconds
- **THEN** the system SHALL recommend increasing image generation parallelism or reviewing the image provider throughput

#### Scenario: Slow knowledge retrieval recommends timeout and cache
- **WHEN** the P95 duration of `knowledge_retrieve` exceeds 30 seconds
- **THEN** the system SHALL recommend adding timeout protection and caching frequently retrieved knowledge

#### Scenario: High failure rate recommends fallback strategy
- **WHEN** the failure rate of any stage exceeds 10%
- **THEN** the system SHALL recommend adding a fallback or degradation strategy for that stage

### Requirement: Stage log writing SHALL not block workflow execution
The system SHALL persist stage logs asynchronously or with minimal overhead so that logging instrumentation does not materially delay workflow node execution.

#### Scenario: Workflow node completes without waiting for analytics aggregation
- **WHEN** a workflow node finishes
- **THEN** the node completion SHALL not wait for analytics aggregation or recommendation generation

#### Scenario: Sub-stage logs are written through the same non-blocking path
- **WHEN** a sub-stage is started or completed
- **THEN** the write operation SHALL use the same lightweight persistence path as parent stage logs

### Requirement: Negative duration anomalies SHALL be detectable
The system SHALL flag any existing or future stage log record where `duration_ms` is negative so that operators can identify historical data corruption.

#### Scenario: Existing negative durations are flagged on analytics query
- **WHEN** the analytics service encounters historical records with `duration_ms < 0`
- **THEN** it SHALL report them as `time_anomaly` records with `duration_ms` set to null and include them in a dedicated anomaly list
