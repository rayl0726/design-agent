## ADDED Requirements

### Requirement: System captures user feedback for learning
The system SHALL store user corrections and image feedback in the `feedbacks` table with sufficient context for learning.

#### Scenario: Intent correction feedback
- **WHEN** user corrects an intent field such as space_type from "商场" to "购物中心中庭"
- **THEN** the system SHALL store category "intent_correction", intent_field "space_type", original_value "商场", corrected_value "购物中心中庭"

#### Scenario: Image feedback
- **WHEN** user marks a generated image as "主体不突出"
- **THEN** the system SHALL store category "image_feedback", point_name, image_index, and tag "composition"

### Requirement: System expands alias lexicon from corrections
The system SHALL automatically suggest alias expansions when the same intent correction occurs multiple times.

#### Scenario: Repeated correction triggers alias suggestion
- **GIVEN** at least 3 distinct feedback records correct space_type to the same value for similar original inputs
- **WHEN** the learning flywheel runs
- **THEN** the system SHALL propose adding the original input as an alias for the corrected value

### Requirement: System maintains a few-shot example library
The system SHALL accumulate high-quality intent recognition examples from user corrections and expert annotations.

#### Scenario: Store golden example
- **WHEN** an expert annotates a user input and its correct structured intent
- **THEN** the system SHALL append the input-output pair to the few-shot example library for the corresponding space_type and theme

#### Scenario: Retrieve relevant examples
- **WHEN** the intent recognizer processes an input for space_type "购物中心中庭" and theme "圣诞节"
- **THEN** the system SHALL retrieve up to 3 matching few-shot examples to include in the LLM prompt

### Requirement: System versions prompt templates and tracks performance
The system SHALL version prompt templates and associate image feedback with the template version used.

#### Scenario: Template version recorded
- **WHEN** an image is generated using prompt template version "atrium-v2"
- **THEN** the generated record SHALL include "prompt_template_version": "atrium-v2"

#### Scenario: Compare template versions
- **WHEN** admin queries feedback for images generated with version "atrium-v1" versus "atrium-v2"
- **THEN** the system SHALL return aggregated positive/negative counts per version
