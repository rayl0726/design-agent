## ADDED Requirements

### Requirement: Knowledge retrieval tool exposes agent type parameter
The `knowledge_retrieval` tool in the generic agent runtime SHALL accept an `agent_type` parameter to scope the search to the appropriate knowledge base and log the invoking agent.

#### Scenario: Scoped retrieval by agent type
- **WHEN** the generic agent runtime invokes `knowledge_retrieval` with `agent_type='meichen'`
- **THEN** the system SHALL scope the search to meichen-relevant knowledge and record `agent_type='meichen'` in search logs

### Requirement: RAG logs include agent context
Every knowledge retrieval operation SHALL record the `agent_type` and `conversation_id` in `rag_search_logs` when available.

#### Scenario: Log agent context
- **WHEN** a semantic search is performed through the generic agent tool system
- **THEN** the system SHALL insert a record with `agent_type` and `conversation_id` populated

### Requirement: Knowledge retrieval supports timeout and fallback per agent
The knowledge retrieval tool SHALL respect the configured timeout and fallback behavior per agent type.

#### Scenario: Meichen agent timeout fallback
- **WHEN** a meichen-scoped semantic search times out after 30s
- **THEN** the system SHALL fall back to predefined meichen mock cases and log `timed_out=true`
