## Why

The phone-account-isolation feature now binds every project, session message, feedback record, and workflow to a specific user. However, resources are still exposed through sequential numeric IDs in URLs (e.g., `/projects/123`, `/projects/123/messages`). Because these IDs are predictable, an authenticated user who knows or guesses another user's resource ID can attempt to access it. Although the backend currently rejects cross-user requests with 404, relying solely on authorization checks is fragile: a future endpoint could forget to add the check, and the IDs themselves leak internal ordering and table size. We need non-guessable, user-scoped public identifiers so that URLs are inherently unforgeable even before authorization is evaluated.

## What Changes

- Introduce a public, opaque identifier (public ID) for every user-owned resource: `Project`, `SessionMessage`, `Feedback`, and any workflow-related exports/thinking logs.
- Keep the internal numeric primary key for database relationships; expose only the public ID in REST URLs, SSE subscriptions, and frontend routes.
- Generate public IDs using a cryptographically secure, URL-safe encoding that is unique per resource type and bounded to the owning user.
- Update all controllers, services, repositories, and the frontend to accept and return public IDs instead of numeric IDs.
- **BREAKING**: All existing client bookmarks or hard-coded URLs that use numeric IDs will stop working. A one-time migration will assign public IDs to existing rows.
- Add a global URL/path sanitizer so internal IDs never appear in logs, error messages, or API responses.

## Capabilities

### New Capabilities
- `obfuscated-resource-ids`: Introduce non-guessable, user-bound public identifiers for all user-owned resources and use them in every public URL and API contract.

### Modified Capabilities
- `phone-account-isolation`: Update its exposed URLs and DTOs to use public resource IDs instead of numeric IDs, while keeping the user-isolation behavior unchanged.

## Impact

- `agent-api`: controllers, services, repositories, DTOs, JWT/session handling, database schema, and migration scripts.
- `agent-web`: router paths, API calls, Pinia stores, and any views that embed resource IDs.
- `agent-core`: minimal impact; it continues to receive opaque project IDs as strings where needed.
- Existing bookmarks, integrations, and stored URLs using numeric IDs will require migration.
