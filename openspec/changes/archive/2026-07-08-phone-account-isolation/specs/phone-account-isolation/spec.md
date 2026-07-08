## ADDED Requirements

### Requirement: User registers with phone and verification code
The system SHALL allow a new user to register using a phone number and a verification code.

#### Scenario: Successful registration
- **WHEN** user provides a valid Chinese mainland phone number and the verification code `8888`
- **THEN** system creates a new user and returns a JWT token

#### Scenario: Phone number already registered
- **WHEN** user provides a phone number that already exists
- **THEN** system returns an error indicating the phone number is already registered

### Requirement: User logs in with phone and verification code
The system SHALL allow an existing user to log in using a phone number and the verification code `8888`.

#### Scenario: Successful login
- **WHEN** user provides a registered phone number and the verification code `8888`
- **THEN** system returns a JWT token

#### Scenario: Phone number not registered
- **WHEN** user provides a phone number that does not exist
- **THEN** system returns an error indicating the phone number is not registered

### Requirement: System sends verification code
The system SHALL provide an endpoint to request a verification code for a given phone number.

#### Scenario: Request verification code
- **WHEN** user requests a verification code for any phone number
- **THEN** system returns success and the fixed verification code is `8888`

### Requirement: User data is isolated by account
The system SHALL ensure that a user can only access data belonging to their own account.

#### Scenario: User queries own projects
- **WHEN** an authenticated user requests their project list
- **THEN** system returns only projects with matching `user_id`

#### Scenario: User cannot access another user's project
- **WHEN** an authenticated user requests a project owned by another user
- **THEN** system returns a 403 or 404 error

### Requirement: Authentication is required for protected endpoints
The system SHALL require a valid JWT token for all endpoints except auth-related endpoints (`/auth/**`).

#### Scenario: Access without token
- **WHEN** user calls a non-auth endpoint without a valid JWT token
- **THEN** system returns a 401 Unauthorized error

#### Scenario: Access with valid token
- **WHEN** user calls a protected endpoint with a valid JWT token
- **THEN** system processes the request using the token's user identity

### Requirement: JWT token expires after 30 days
The system SHALL issue JWT tokens that expire 30 days after creation.

#### Scenario: Token is within 30 days
- **WHEN** user calls a protected endpoint with a token created less than 30 days ago
- **THEN** system accepts the token and processes the request

#### Scenario: Token has expired
- **WHEN** user calls a protected endpoint with a token created more than 30 days ago
- **THEN** system returns a 401 Unauthorized error
