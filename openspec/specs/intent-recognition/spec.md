## Purpose

TBD: Define the purpose of the intent recognition capability.

## Requirements

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

### Requirement: System expands point-of-interest recognition with synonyms
The system SHALL map user descriptions of display points to canonical point names using synonyms.

#### Scenario: Synonym for entrance gate
- **WHEN** user inputs "门头装置"
- **THEN** the system SHALL recognize point "门头" with source "alias"

#### Scenario: Synonym for DP point
- **WHEN** user inputs "打卡点"
- **THEN** the system SHALL recognize point "DP点" with source "alias"

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

### Requirement: System captures intent corrections for learning
The system SHALL accept and store intent correction feedback to support continuous improvement of the intent recognizer.

#### Scenario: Submit space type correction
- **WHEN** user submits feedback with feedback_type "intent", intent_field "space_type", original_value "商场", corrected_value "购物中心中庭"
- **THEN** the system SHALL persist the correction with category "intent_correction" and processed false

#### Scenario: List unprocessed corrections
- **WHEN** admin requests unprocessed intent corrections for a project
- **THEN** the system SHALL return all feedback records with feedback_type "intent" and processed false

### Requirement: System exposes alias expansion from corrections
The system SHALL provide an interface to review and apply alias expansions derived from accumulated intent corrections.

#### Scenario: Propose alias from corrections
- **GIVEN** multiple corrections map original input "商厦中庭" to corrected value "购物中心中庭"
- **WHEN** admin requests alias proposals
- **THEN** the system SHALL suggest adding "商厦中庭" as an alias for "购物中心中庭"
