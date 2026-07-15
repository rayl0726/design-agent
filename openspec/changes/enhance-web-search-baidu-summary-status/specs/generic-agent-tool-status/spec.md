## ADDED Requirements

### Requirement: Tool execution progress is emitted via SSE
The system SHALL emit a `tool_progress` SSE event when a tool changes execution phase.

#### Scenario: Web search starts
- **WHEN** `web_search` begins execution
- **THEN** agent-core sends `event: tool_start` with `status: searching`
- **AND** the frontend displays the tool card with status “搜索中...”

#### Scenario: Web search enters summarization phase
- **WHEN** `web_search` finishes searching and begins summarization
- **THEN** agent-core sends `event: tool_progress` with `status: summarizing`
- **AND** the frontend updates the same tool card to status “总结中...”

#### Scenario: Tool completes
- **WHEN** `web_search` returns a ToolResult
- **THEN** agent-core sends `event: tool_result` with the final observation
- **AND** the frontend updates the tool card to status “已完成”

### Requirement: Tool progress events are forwarded by agent-api
The system SHALL forward `tool_progress` events from agent-core to the frontend.

#### Scenario: User is in a generic agent session
- **WHEN** the user sends a message that triggers `web_search`
- **THEN** agent-api receives `tool_progress` from agent-core
- **AND** forwards it to the connected SSE client

### Requirement: Frontend updates tool card status
The system SHALL update the tool card UI when a `tool_progress` event is received.

#### Scenario: Status changes from searching to summarizing
- **WHEN** the frontend receives `tool_progress` with `status: summarizing`
- **THEN** the existing tool card for the same call id updates its status label
- **AND** no duplicate tool card is created

#### Scenario: Tool card receives final result
- **WHEN** the frontend receives `tool_result`
- **THEN** the tool card displays the final observation
- **AND** the status label becomes “已完成”
