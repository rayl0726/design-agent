## ADDED Requirements

### Requirement: System records all knowledge retrieval operations
The system SHALL log every knowledge base semantic search and structured query to the `rag_search_logs` database table with search type, result count, duration, cache hit status, and timeout status.

#### Scenario: Successful semantic search
- **WHEN** the knowledge base completes a semantic search returning 5 results in 120ms
- **THEN** the system SHALL insert a record into `rag_search_logs` with `search_type='semantic'`, `result_count=5`, `duration_ms=120`, `cache_hit=false`, `timed_out=false`

#### Scenario: Search timeout with fallback
- **WHEN** a semantic search times out after 30s and falls back to mock data
- **THEN** the system SHALL insert a record with `timed_out=true` and `search_type='fallback'`

### Requirement: Admin API exposes RAG performance metrics
The system SHALL provide admin API endpoints to query knowledge retrieval performance.

#### Scenario: Query RAG overview
- **WHEN** admin requests `GET /api/admin/metrics/rag/overview?hours=24`
- **THEN** the system SHALL return total searches, average result count, average latency, cache hit rate, timeout count, and fallback rate

#### Scenario: Query RAG search trend
- **WHEN** admin requests `GET /api/admin/metrics/rag/timeline?hours=168&interval=day`
- **THEN** the system SHALL return a time series of search count, average latency, and cache hit rate bucketed by the specified interval

### Requirement: Admin API exposes knowledge base inventory
The system SHALL provide knowledge base inventory metrics.

#### Scenario: Query knowledge base stats
- **WHEN** admin requests `GET /api/admin/metrics/rag/inventory`
- **THEN** the system SHALL return total case documents, total material entries, total image references, and last update timestamp for each collection

### Requirement: Admin API exposes zero-result search analysis
The system SHALL provide analysis of searches that returned zero results to identify knowledge gaps.

#### Scenario: Query zero-result searches
- **WHEN** admin requests `GET /api/admin/metrics/rag/zero-results?days=30`
- **THEN** the system SHALL return the count and percentage of searches returning zero results, along with the top 10 search queries that returned no results
