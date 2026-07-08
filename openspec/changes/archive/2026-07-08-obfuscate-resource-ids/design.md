## Context

The phone-account-isolation change introduced per-user ownership for projects, session messages, feedback, thinking logs, and workflows. Authorization checks now reject cross-user access, but resource URLs still expose sequential numeric IDs (e.g., `/projects/42`, `/projects/42/messages`). Predictable IDs make it easy to probe for accessible resources and leak rough table size/order. This design adds opaque public identifiers to all user-owned resources so that URLs are unguessable and internal database structure is not exposed.

## Goals / Non-Goals

**Goals:**
- Every user-owned resource exposed through the API gets a unique, opaque, URL-safe public ID.
- REST, SSE, and frontend routes use public IDs; internal numeric IDs never appear in URLs or API responses.
- Existing rows receive a public ID through a one-time migration.
- Authorization checks continue to enforce user ownership using the existing `user_id` columns.
- The frontend stores and routes by public ID only.

**Non-Goals:**
- Encrypting IDs or making them revocable (this is about unguessability, not secrecy against the owner).
- Changing the authentication mechanism (JWT/phone remains unchanged).
- Re-architecting agent-core; it continues to treat project identifiers as opaque strings.

## Decisions

### Public ID format: use nanoid
- **Choice**: Generate public IDs with nanoid (or a Java equivalent) using an alphabet of `A-Za-z0-9_-` and a length of 16 characters.
- **Rationale**: 16 characters from a 64-character alphabet gives ~2^96 combinations, making brute-force guessing infeasible for an authenticated API with rate limiting. It is URL-safe, short, and easy to read/copy.
- **Alternative considered**: HashIds encode the numeric ID reversibly; they are shorter but not cryptographically secure and still leak ordering. UUID v4 is standard but 36 characters long and visually noisy.

### Storage: add a `public_id` column per table
- **Choice**: Add `public_id VARCHAR(32) NOT NULL UNIQUE` to `project`, `session_message`, `feedback`, and `thinking_log`. Keep the existing numeric primary key for foreign keys and internal joins.
- **Rationale**: Separating public and internal IDs preserves all existing relationships and indexes while hiding internal IDs from clients. Unique constraints prevent collisions.
- **Alternative considered**: Replacing the primary key with a UUID would require updating every foreign key and join; too risky and invasive.

### Lookup strategy: public ID → internal ID → authorization
- **Choice**: Controllers accept public IDs, resolve them to internal IDs via repository lookup, then apply the existing `findByIdAndUserId` authorization.
- **Rationale**: Keeps authorization logic unchanged; only the entry point changes. If public ID resolution fails, return 404 before authorization.
- **Alternative considered**: Embedding user scope in the public ID and decoding it directly would skip a query but couples ID format to ownership and makes ID revocation harder.

### Public ID generation timing
- **Choice**: Generate the public ID at entity creation time, before persistence.
- **Rationale**: Guarantees every row has a public ID and avoids a separate backfill step for new data.

### Migration
- **Choice**: Provide a Flyway migration that adds `public_id` columns, creates unique indexes, and backfills existing rows with new nanoids.
- **Rationale**: Production deployments need reproducible, reversible schema changes. Using `ddl-auto: update` for this is risky because unique-index backfills can fail silently or lock tables.

## Risks / Trade-offs

- **Breaking existing URLs** → Mitigation: document migration; existing bookmarks will break and require users to re-navigate from project lists.
- **Public ID collision** → Mitigation: nanoid 16-char space is large; unique constraint ensures generation retries on collision.
- **Performance overhead** → Mitigation: unique index on `public_id` keeps lookups O(log n); one extra query per request is negligible compared to existing project authorization query.
- **Inconsistent ID exposure in logs** → Mitigation: add a code review checklist item and a simple test that verifies numeric IDs do not appear in JSON responses.

## Migration Plan

1. Add Flyway migration `V2__add_public_ids.sql` with column additions, unique indexes, and backfill update statements.
2. Deploy migration before code deploy.
3. Deploy new code that reads/writes public IDs.
4. Rollback: revert code first, then optionally drop columns if no public IDs were consumed externally.

## Open Questions

- Should exported files and directory names on disk also switch to public IDs, or remain internal IDs? This affects `export` and thinking-log file paths.
- Should old numeric-ID endpoints be kept temporarily with a redirect/deprecation header?
