## ADDED Requirements

### Requirement: System uses structured prompt templates for image generation
The system SHALL render image generation prompts using a structured template composed of subject, environment, camera angle, lighting, style, and negative prompt sections.

#### Scenario: Shopping mall atrium Christmas installation
- **WHEN** user inputs theme "圣诞节", space_type "购物中心中庭", budget 300000
- **THEN** the rendered prompt SHALL emphasize the central atrium area and de-emphasize the background

#### Scenario: Template selects based on space type
- **WHEN** the space_type is "购物中心中庭"
- **THEN** the system SHALL use the atrium prompt template
- **WHEN** no matching template exists
- **THEN** the system SHALL fall back to the generic commercial display template

### Requirement: System supports user-configurable negative prompts
The system SHALL allow users to select or override negative prompts for image generation.

#### Scenario: Default negative prompts applied
- **WHEN** user does not specify negative prompts
- **THEN** the system SHALL apply default negative prompts including "blurry, cluttered background, people, low quality"

#### Scenario: User overrides negative prompts
- **WHEN** user provides custom negative prompts
- **THEN** the system SHALL use the provided negative prompts instead of defaults

### Requirement: System keeps prompt rendering backward compatible
The system SHALL provide a legacy prompt mode so existing projects without template configuration continue to generate images.

#### Scenario: Project without template config
- **WHEN** a project has no prompt_template_version set
- **THEN** the system SHALL render prompts using the legacy concatenation mode
