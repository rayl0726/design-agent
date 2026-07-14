## ADDED Requirements

### Requirement: RAG logs capture agent type
The system SHALL record the invoking agent type in every `rag_search_logs` entry when knowledge retrieval is invoked through the generic agent runtime.

#### Scenario: Semantic search from generic agent
- **WHEN** the generic agent runtime invokes knowledge_retrieval for agent_mode "meichen"
- **THEN** the system SHALL insert a `rag_search_logs` record with `agent_type='meichen'`

#### Scenario: Semantic search from meichen workflow
- **WHEN** the meichen workflow invokes knowledge retrieval directly
- **THEN** the system SHALL insert a `rag_search_logs` record with `agent_type='meichen'`

### Requirement: Admin RAG metrics support agent type filtering
The admin RAG metrics API SHALL support filtering and grouping by agent_type.

#### Scenario: Query RAG overview by agent
- **WHEN** admin requests `GET /api/admin/metrics/rag/overview?hours=24&agent_type=meichen`
- **THEN** the system SHALL return metrics scoped to the meichen agent

#### Scenario: Query RAG overview across all agents
- **WHEN** admin requests `GET /api/admin/metrics/rag/overview?hours=24`
- **THEN** the system SHALL return aggregate metrics across all agent types with a breakdown per agent_type

### Requirement: Zero-result search analysis includes agent type
The zero-result search analysis API SHALL include agent_type for each query so admins can identify knowledge gaps per agent domain.

#### Scenario: Query zero-result searches by agent
- **WHEN** admin requests `GET /api/admin/metrics/rag/zero-results?days=30&agent_type=meichen`
- **THEN** the system SHALL return zero-result searches only for the meichen agent
