## ADDED Requirements

### Requirement: Image generation is exposed as a generic tool
The system SHALL expose image generation as a tool named `image_generation` in the generic agent tool system, allowing the generic agent runtime to invoke it dynamically during the ReAct loop.

#### Scenario: Generic agent calls image generation
- **WHEN** the generic agent runtime determines that visual concepts are needed
- **THEN** the system SHALL invoke the `image_generation` tool with parameters derived from the current task context

#### Scenario: Image generation tool receives structured inputs
- **WHEN** the `image_generation` tool is called
- **THEN** it SHALL receive inputs including theme, space_type, design_point, camera_angle, style, and optional negative_prompts

### Requirement: Prompt templates remain reusable across invocation paths
The system SHALL retain existing structured prompt templates and legacy fallback mode so that image generation invoked via the generic agent tool produces the same output quality as direct workflow invocation.

#### Scenario: Tool invocation uses atrium template
- **WHEN** the `image_generation` tool is invoked for space_type "购物中心中庭"
- **THEN** the system SHALL use the atrium prompt template

#### Scenario: Tool invocation supports legacy mode
- **WHEN** the task context has no prompt_template_version
- **THEN** the system SHALL render prompts using the legacy concatenation mode

## MODIFIED Requirements

### Requirement: System supports user-configurable negative prompts
The system SHALL allow users to select or override negative prompts for image generation. When invoked through the generic agent tool, negative prompts MAY be specified in the tool input or inherited from agent configuration defaults.

#### Scenario: Default negative prompts applied via tool
- **WHEN** the `image_generation` tool is invoked without custom negative prompts
- **THEN** the system SHALL apply default negative prompts including "blurry, cluttered background, people, low quality"

#### Scenario: Tool caller overrides negative prompts
- **WHEN** the generic agent runtime provides custom negative prompts in the tool input
- **THEN** the system SHALL use the provided negative prompts instead of defaults
