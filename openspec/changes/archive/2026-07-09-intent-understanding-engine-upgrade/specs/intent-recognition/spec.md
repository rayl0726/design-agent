## MODIFIED Requirements

### Requirement: System recognizes commercial space types from user input
The system SHALL identify the commercial space type from user text input using an LLM structured-output extractor followed by taxonomy-based validation.

#### Scenario: Exact match for atrium
- **WHEN** user inputs "购物中心中庭"
- **THEN** the system SHALL recognize space_type as "购物中心中庭" with source "validated" and confidence 1.0

#### Scenario: Alias match for pop-up store
- **WHEN** user inputs "快闪店"
- **THEN** the system SHALL recognize space_type as "快闪店" with source "validated" and confidence >= 0.9

#### Scenario: Fuzzy match for department store entrance
- **WHEN** user inputs "百货入口"
- **THEN** the system SHALL recognize space_type as "百货入口" with source "validated" and confidence >= 0.75

#### Scenario: LLM fallback for uncommon description
- **WHEN** user inputs "步行街展示区域"
- **THEN** the system SHALL recognize space_type as "步行街" with source "llm" and confidence >= 0.6

### Requirement: System extracts budget, style, material, and timeline fields
The system SHALL extract budget, style, material restrictions, timeline, theme, color, and brand fields from user input using LLM structured output and normalize the extracted values.

#### Scenario: Budget extraction
- **WHEN** user inputs "预算30万"
- **THEN** the system SHALL extract budget as integer 300000 and budget_level "high"

#### Scenario: Theme extraction
- **WHEN** user inputs "圣诞节"
- **THEN** the system SHALL extract theme as "圣诞节" with source "llm"

#### Scenario: Material restriction extraction
- **WHEN** user inputs "不要用真植物，亚克力可以"
- **THEN** the system SHALL extract material_restrictions containing "真植物" and allowed_materials containing "亚克力"

### Requirement: System reports recognition confidence and source
The system SHALL attach a confidence score and recognition source to every extracted field.

#### Scenario: High confidence exact match
- **WHEN** a field is matched exactly from the taxonomy after LLM extraction
- **THEN** the system SHALL set source to "validated" and confidence to 1.0

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
- **THEN** the system SHALL respond with "请问这次设计的预算范围大概是多少？"

## ADDED Requirements

### Requirement: System recognizes open-ended theme and budget fields
The system SHALL use LLM structured output to identify theme, budget, timeline, color, and brand from natural language without relying on fixed vocabularies.

#### Scenario: Recognize theme from a single word
- **WHEN** user inputs "圣诞节 30万 中庭"
- **THEN** the system SHALL extract theme "圣诞节", budget 300000, and space_type "购物中心中庭"

#### Scenario: Recognize budget variants
- **WHEN** user inputs "预算在二十万到三十万之间"
- **THEN** the system SHALL extract budget as a range or midpoint value and budget_level "medium"

### Requirement: System normalizes extracted values through post-validation
The system SHALL run a validation pass after LLM extraction to normalize budget to RMB integer, map aliases to canonical taxonomy values, and flag missing required fields.

#### Scenario: Budget normalization
- **WHEN** the LLM returns budget "30万"
- **THEN** the validator SHALL convert it to integer 300000

#### Scenario: Alias normalization
- **WHEN** the LLM returns space_type "商场中庭"
- **THEN** the validator SHALL map it to canonical value "购物中心中庭"

#### Scenario: Unknown value preserved
- **WHEN** the LLM returns space_type "酒店大堂" which is not in the taxonomy
- **THEN** the system SHALL preserve "酒店大堂" as the space_type and mark source "llm"

### Requirement: System supports open taxonomy values
The system SHALL allow extracted field values to exist outside the canonical taxonomy while still using the taxonomy for normalization when a match exists.

#### Scenario: New style accepted
- **WHEN** user inputs "科技感风格"
- **THEN** the system SHALL extract style "科技感" even if it is not listed in intent_taxonomy.yaml
