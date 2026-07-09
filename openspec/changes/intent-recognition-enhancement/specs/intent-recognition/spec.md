## ADDED Requirements

### Requirement: System recognizes commercial space types from user input
The system SHALL identify the commercial space type from user text input using a domain taxonomy.

#### Scenario: Exact match for atrium
- **WHEN** user inputs "购物中心中庭"
- **THEN** the system SHALL recognize space_type as "购物中心中庭" with source "exact" and confidence 1.0

#### Scenario: Alias match for pop-up store
- **WHEN** user inputs "快闪店"
- **THEN** the system SHALL recognize space_type as "快闪店" with source "alias" and confidence >= 0.9

#### Scenario: Fuzzy match for department store entrance
- **WHEN** user inputs "百货入口"
- **THEN** the system SHALL recognize space_type as "百货入口" with source "fuzzy" and confidence >= 0.75

#### Scenario: LLM fallback for uncommon description
- **WHEN** user inputs "步行街展示区域"
- **THEN** the system SHALL recognize space_type as "步行街" with source "llm" and confidence >= 0.6

### Requirement: System expands point-of-interest recognition with synonyms
The system SHALL map user descriptions of display points to canonical point names using synonyms.

#### Scenario: Synonym for entrance gate
- **WHEN** user inputs "门头装置"
- **THEN** the system SHALL recognize point "门头" with source "alias"

#### Scenario: Synonym for DP point
- **WHEN** user inputs "打卡点"
- **THEN** the system SHALL recognize point "DP点" with source "alias"

### Requirement: System extracts budget, style, material, and timeline fields
The system SHALL extract budget, style, material restrictions, and timeline fields from user input.

#### Scenario: Budget extraction
- **WHEN** user inputs "预算30万"
- **THEN** the system SHALL extract budget "30万" and budget_level "high"

#### Scenario: Material restriction extraction
- **WHEN** user inputs "不要用真植物，亚克力可以"
- **THEN** the system SHALL extract material_restrictions containing "真植物" and allowed_materials containing "亚克力"

### Requirement: System completes missing fields from conversation context
The system SHALL use prior conversation turns to fill missing intent fields before falling back to defaults.

#### Scenario: Inherit space type from previous turn
- **GIVEN** the previous user turn already specified space_type "购物中心中庭"
- **WHEN** the current user input only says "预算加到50万"
- **THEN** the system SHALL retain space_type "购物中心中庭" and update budget to "50万"

#### Scenario: Fill default point count
- **GIVEN** user specified space_type "快闪店" but no points
- **WHEN** the system requires point configuration
- **THEN** the system SHALL suggest default points for "快闪店" (e.g., 门头、DP点、合影墙) with source "default"

### Requirement: System reports recognition confidence and source
The system SHALL attach a confidence score and recognition source to every extracted field.

#### Scenario: High confidence exact match
- **WHEN** a field is matched exactly from the taxonomy
- **THEN** the system SHALL set source to "exact" and confidence to 1.0

#### Scenario: Low confidence triggers clarification
- **WHEN** a required field has confidence below the configured threshold
- **THEN** the system SHALL mark the field as "needs_clarification" and generate a follow-up question

### Requirement: System clarifies low-confidence fields instead of guessing
The system SHALL ask the user for clarification when critical fields cannot be recognized with sufficient confidence.

#### Scenario: Unknown space type
- **WHEN** user inputs "做个美陈" without recognizable space type
- **THEN** the system SHALL respond with "请问设计用在什么类型的商业空间？（如购物中心中庭、快闪店、百货入口等）"

#### Scenario: Unknown budget
- **WHEN** user confirms design intent but no budget was provided or extracted
- **THEN** the system SHALL ask "项目预算大概是多少？"
