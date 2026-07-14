## ADDED Requirements

### Requirement: Request Analyzer performs semantic task decomposition
The system SHALL analyze user input and decompose it into a structured Task Plan containing goals, types, dependencies, success criteria, and per-task confidence thresholds.

#### Scenario: Meichen design request decomposition
- **WHEN** user inputs "帮我设计一个海洋主题购物中心中庭美陈，预算15万"
- **THEN** the system SHALL produce a Task Plan with tasks for information_gathering, retrieve_cases, generate_ideas, and generate_images

#### Scenario: General question decomposition
- **WHEN** user inputs "美陈设计一般多少钱"
- **THEN** the system SHALL produce a Task Plan containing only an answer_question task

#### Scenario: Multi-intent input decomposition
- **WHEN** user inputs "先告诉我美陈设计多少钱，再帮我做一个海洋主题方案"
- **THEN** the system SHALL produce separate tasks for price_inquiry and meichen_design

### Requirement: Intent output includes agent mode selection
The system SHALL identify which agent mode the user request belongs to and include it in the analysis result.

#### Scenario: Select meichen mode
- **WHEN** user input indicates a commercial display design request
- **THEN** the analysis result SHALL set agent_mode to "meichen"

#### Scenario: Select generic mode
- **WHEN** user input is a general question not tied to a specific agent domain
- **THEN** the analysis result SHALL set agent_mode to "generic"

## MODIFIED Requirements

### Requirement: System extracts budget, style, material, and timeline fields
The system SHALL extract budget, style, material restrictions, timeline, theme, color, and brand fields from user input using LLM structured output and normalize the extracted values. The extracted fields SHALL be attached to the information_gathering task in the Task Plan when running under the generic agent runtime.

#### Scenario: Budget extraction in task plan
- **WHEN** user inputs "预算30万"
- **THEN** the system SHALL extract budget as integer 300000 and budget_level "high" and attach it to the active information_gathering task

#### Scenario: Theme extraction in task plan
- **WHEN** user inputs "圣诞节"
- **THEN** the system SHALL extract theme as "圣诞节" with source "llm" and attach it to the active information_gathering task

#### Scenario: Material restriction extraction in task plan
- **WHEN** user inputs "不要用真植物，亚克力可以"
- **THEN** the system SHALL extract material_restrictions containing "真植物" and allowed_materials containing "亚克力" and store them in the task context

### Requirement: System completes missing fields from conversation context
The system SHALL use prior conversation turns to fill missing intent fields before falling back to defaults. When operating under the generic agent runtime, missing required fields SHALL be escalated as a clarification task rather than immediately applying defaults.

#### Scenario: Inherit space type from previous turn
- **GIVEN** the previous user turn already specified space_type "购物中心中庭"
- **WHEN** the current user input only says "预算加到50万"
- **THEN** the system SHALL retain space_type "购物中心中庭" and update budget to "50万" in the Task Plan

#### Scenario: Missing required fields trigger clarification task
- **GIVEN** user specified theme "海洋" but no space_type or budget
- **WHEN** the generic agent runtime processes the request
- **THEN** the system SHALL create a clarification task for the missing fields instead of applying defaults

### Requirement: System reports recognition confidence and source
The system SHALL attach a confidence score and recognition source to every extracted field. The confidence score SHALL be consumed by the generic agent runtime's verifier to decide whether to proceed, retry, or clarify.

#### Scenario: High confidence exact match
- **WHEN** a field is matched exactly from the taxonomy after LLM extraction
- **THEN** the system SHALL set source to "validated" and confidence to 1.0

#### Scenario: Low confidence triggers verifier clarification
- **WHEN** a required field has confidence below the configured threshold
- **THEN** the system SHALL mark the field as "needs_clarification" and the verifier SHALL generate a follow-up task or ask_user action
