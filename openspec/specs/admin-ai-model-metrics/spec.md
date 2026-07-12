## ADDED Requirements

### Requirement: System records all AI model calls
The system SHALL log every LLM, VLM, Embedding, and Image Generation API call to the `ai_call_logs` database table with call type, provider, model name, status, duration, token usage, and error information.

#### Scenario: Successful LLM call
- **WHEN** the LLM client completes a chat completion request to Zhipu GLM-4.7-Flash
- **THEN** the system SHALL insert a record into `ai_call_logs` with `call_type='llm'`, `provider='zhipu'`, `model='GLM-4.7-Flash'`, `status='success'`, `duration_ms` = actual elapsed time, `input_tokens` and `output_tokens` from API response

#### Scenario: Rate-limited API call
- **WHEN** the LLM client receives a 429 Too Many Requests response from the provider
- **THEN** the system SHALL insert a record with `status='rate_limited'` and `error_message` containing the response body
- **AND** the retry count SHALL reflect the number of retry attempts made

#### Scenario: Timed-out API call
- **WHEN** an API call exceeds the configured timeout (e.g., 180s for LLM, 120s for VLM)
- **THEN** the system SHALL insert a record with `status='timeout'` and `duration_ms` = the timeout value

### Requirement: Admin API exposes AI model call statistics
The system SHALL provide admin API endpoints to query aggregated AI model call statistics.

#### Scenario: Query call summary by type
- **WHEN** admin requests `GET /api/admin/metrics/ai-calls/summary?hours=24`
- **THEN** the system SHALL return call count, success count, failure count, rate-limit count, average latency, p95 latency, and total tokens for each `call_type` (llm, vlm, embedding, image_generation) within the specified time window

#### Scenario: Query call breakdown by provider
- **WHEN** admin requests `GET /api/admin/metrics/ai-calls/by-provider?hours=24`
- **THEN** the system SHALL return per-provider statistics including call count, success rate, average latency, and token usage

#### Scenario: Query call time series
- **WHEN** admin requests `GET /api/admin/metrics/ai-calls/timeline?hours=24&interval=hour`
- **THEN** the system SHALL return a time series of call counts and error rates bucketed by the specified interval

### Requirement: Admin API exposes token usage and cost estimation
The system SHALL track token usage and provide cost estimation based on configured provider pricing.

#### Scenario: Query token usage trend
- **WHEN** admin requests `GET /api/admin/metrics/ai-calls/tokens?hours=168`
- **THEN** the system SHALL return daily input tokens, output tokens, and total tokens for each provider, along with estimated cost

#### Scenario: Cost estimation for image generation
- **WHEN** an image generation call completes
- **THEN** the system SHALL record the provider and estimate cost based on per-image pricing configuration
