# admin-prompt-template-management Specification

## Purpose
TBD - created by archiving change admin-dashboard-modules. Update Purpose after archive.
## Requirements
### Requirement: Admin can list prompt template versions
The system SHALL provide an admin API to list all configured prompt template versions and their metadata.

#### Scenario: List templates
- **WHEN** admin requests /api/admin/prompt-templates
- **THEN** the system SHALL return a list of templates with name, version, space_type, and created_at

### Requirement: Admin can view prompt template performance
The system SHALL correlate prompt template versions with image feedback and return performance summaries.

#### Scenario: Feedback by template version
- **WHEN** admin requests performance for template version "atrium-v2"
- **THEN** the system SHALL return total images generated, positive feedback count, and negative feedback count

### Requirement: Admin can view rendered prompt example
The system SHALL allow admin to preview a rendered prompt for given inputs without generating an image.

#### Scenario: Preview prompt
- **WHEN** admin posts theme "圣诞节", space_type "购物中心中庭", budget 300000
- **THEN** the system SHALL return the rendered positive prompt and negative prompt

