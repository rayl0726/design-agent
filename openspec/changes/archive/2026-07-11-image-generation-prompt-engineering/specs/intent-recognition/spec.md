## MODIFIED Requirements

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
