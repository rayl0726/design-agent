# admin-feedback-management Specification

## Purpose
TBD - created by archiving change admin-dashboard-modules. Update Purpose after archive.
## Requirements
### Requirement: Admin can list user feedback
The system SHALL provide an admin API to list user feedback with pagination, filtering by type, category, and processed status.

#### Scenario: List all feedback
- **WHEN** admin requests feedback list with page 0 and size 20
- **THEN** the system SHALL return a paginated list of feedback records ordered by created_at desc

#### Scenario: Filter by category
- **WHEN** admin requests feedback with category "intent_correction"
- **THEN** the system SHALL return only intent correction records

### Requirement: Admin can mark feedback as processed
The system SHALL allow admin users to mark a feedback record as processed and add notes.

#### Scenario: Mark processed
- **WHEN** admin sends a request to mark feedback id "fb-123" as processed with notes "已审核"
- **THEN** the system SHALL update processed to true and store the notes

