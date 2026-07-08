## ADDED Requirements

### Requirement: Resources have unique opaque public identifiers
The system SHALL assign a non-sequential, URL-safe public identifier to every user-owned resource at creation time.

#### Scenario: Project creation returns public ID
- **WHEN** an authenticated user creates a project
- **THEN** the response contains a `publicId` field with a 16-character URL-safe string

#### Scenario: Public ID is not guessable
- **WHEN** two projects are created sequentially by the same user
- **THEN** their public IDs share no obvious prefix, suffix, or numeric relationship

### Requirement: Public identifiers replace numeric IDs in URLs
The system SHALL use public identifiers in all REST, SSE, and frontend resource paths.

#### Scenario: Fetch project by public ID
- **WHEN** an authenticated user requests `GET /api/v1/projects/{publicId}`
- **THEN** the system returns the matching project if it belongs to the user

#### Scenario: Numeric ID in URL is rejected
- **WHEN** an authenticated user requests `GET /api/v1/projects/{numericId}`
- **THEN** the system returns a 404 Not Found error

#### Scenario: Messages endpoint uses project public ID
- **WHEN** an authenticated user requests `GET /api/v1/projects/{publicId}/messages`
- **THEN** the system returns messages for the project if it belongs to the user

### Requirement: Internal numeric IDs are never exposed externally
The system SHALL ensure that internal numeric primary keys do not appear in API responses, error messages, URLs, or SSE events.

#### Scenario: Project list hides numeric ID
- **WHEN** an authenticated user lists their projects
- **THEN** each project entry contains only `publicId` and no `id` field

#### Scenario: Error message hides numeric ID
- **WHEN** a request fails for a resource that does not exist or does not belong to the user
- **THEN** the error response contains no numeric ID

### Requirement: Existing data receives public identifiers
The system SHALL backfill public identifiers for all existing user-owned resources during migration.

#### Scenario: Existing project gets public ID
- **WHEN** the migration runs against a project created before this change
- **THEN** the project row receives a unique public identifier
- **AND** the project remains accessible through its new public ID

### Requirement: Public ID lookups enforce ownership
The system SHALL resolve a public ID to an internal resource only when the requesting user owns the resource.

#### Scenario: User accesses own resource by public ID
- **WHEN** an authenticated user requests a resource using its correct public ID
- **THEN** the system returns the resource

#### Scenario: User cannot access another user's resource by public ID
- **WHEN** an authenticated user requests a resource using another user's public ID
- **THEN** the system returns a 404 Not Found error
