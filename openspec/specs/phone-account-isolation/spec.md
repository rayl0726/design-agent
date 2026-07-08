# Purpose

TBD

# Requirements

## Requirement: User data is isolated by account
The system SHALL ensure that a user can only access data belonging to their own account using opaque public resource identifiers.

### Scenario: User queries own projects
- **WHEN** an authenticated user requests their project list
- **THEN** the system returns only projects with matching `user_id`
- **AND** each project exposes only its `publicId`

### Scenario: User cannot access another user's project
- **WHEN** an authenticated user requests a project owned by another user using either a numeric ID or another user's public ID
- **THEN** the system returns a 403 or 404 error
- **AND** the response leaks no internal numeric ID

## Requirement: Resource URLs use public identifiers
The system SHALL expose all user-owned resources through opaque public identifiers instead of sequential numeric IDs.

### Scenario: Project URL uses public ID
- **WHEN** the frontend navigates to `/projects/{publicId}`
- **THEN** the system loads the project if it belongs to the authenticated user

### Scenario: Message URL uses public IDs
- **WHEN** the frontend navigates to `/projects/{publicId}/messages`
- **THEN** the system loads messages for that project if it belongs to the authenticated user
