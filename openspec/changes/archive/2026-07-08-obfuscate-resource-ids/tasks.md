## 1. Database & Migration

- [x] 1.1 Add `public_id VARCHAR(32) NOT NULL` columns to `project`, `session_message`, `feedback`, and `thinking_log` tables.
- [x] 1.2 Add unique indexes on `public_id` for each table.
- [x] 1.3 Create Flyway migration `V2__add_public_ids.sql` that adds columns, creates indexes, and backfills existing rows with new nanoids.
- [x] 1.4 Run migration against local MySQL and verify all existing rows have a public ID.

## 2. Backend Public ID Utilities

- [x] 2.1 Add a `PublicIdGenerator` utility/service in `agent-api` that generates 16-character URL-safe nanoids.
- [x] 2.2 Add a collision-retry wrapper so entity creation regenerates the ID on unique-constraint violation.
- [x] 2.3 Add unit tests for `PublicIdGenerator` (format, length, uniqueness over a sample).

## 3. Entity & Repository Changes

- [x] 3.1 Add `publicId` field to `Project`, `SessionMessage`, `Feedback`, and `ThinkingLog` entities.
- [x] 3.2 Add `findByPublicId(String publicId)` and `findByPublicIdAndUserId(String publicId, Long userId)` methods to each repository.
- [x] 3.3 Update entity creation paths to generate and set `publicId` before persistence.

## 4. Service Layer Updates

- [ ] 4.1 Update `ProjectService` to accept public IDs in public methods and resolve them internally.
- [ ] 4.2 Update `SessionMessageService` to accept project public ID and message public ID where applicable.
- [ ] 4.3 Update `FeedbackService` to accept project public ID.
- [ ] 4.4 Update `ThinkingLogService` and `WorkflowService` to accept project public ID.
- [ ] 4.5 Ensure all services still enforce user ownership via `findByPublicIdAndUserId`.

## 5. Controller & API Contract Updates

- [ ] 5.1 Update `ProjectController` paths and DTOs to use `publicId` instead of numeric `id`.
- [ ] 5.2 Update `SessionMessageController` (or `ProjectController` message endpoints) to use public IDs.
- [ ] 5.3 Update `FeedbackController` to use public IDs.
- [ ] 5.4 Update `SseController` SSE subscription path to use project public ID.
- [ ] 5.5 Update `WorkflowController` export/status/thinking-log endpoints to use project public ID.
- [ ] 5.6 Add a global response filter/test that asserts no numeric `id` field leaks in JSON responses.

## 6. Frontend Updates

- [ ] 6.1 Update `agent-web` router paths to use `:publicId` instead of `:id`.
- [ ] 6.2 Update all API calls to pass public IDs.
- [ ] 6.3 Update project/message/feedback stores and views to reference `publicId`.
- [ ] 6.4 Ensure numeric IDs are never stored in `localStorage` or URL state.
- [ ] 6.5 Run `npm run build` and a manual smoke test.

## 7. Integration & Verification

- [ ] 7.1 Verify existing rows are accessible only through their new public IDs.
- [ ] 7.2 Verify numeric-ID URLs return 404.
- [ ] 7.3 Verify cross-user access by public ID returns 404.
- [ ] 7.4 Run `mvn test` and `npm run build` successfully.
- [ ] 7.5 Request final code review before merge.
