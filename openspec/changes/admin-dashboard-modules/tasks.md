## 1. Backend Scaffolding

- [x] 1.1 Create `agent-admin-backend` Spring Boot module with `pom.xml`, main application class, and package structure
- [x] 1.2 Add shared MySQL datasource configuration pointing to existing `meichen` database (read-only by default)
- [x] 1.3 Add Flyway baseline or confirm existing migrations are shared; ensure admin module uses `validate` or `none` migration strategy
- [x] 1.4 Add CORS configuration to allow local `agent-admin-front` origin
- [x] 1.5 Add simple local-auth filter (e.g., configurable static token or basic auth) for admin endpoints

## 2. Frontend Scaffolding

- [x] 2.1 Create `agent-admin-front` Vite + React project with React Router and a UI component library
- [x] 2.2 Configure proxy/dev server to route `/api/admin` to `agent-admin-backend`
- [x] 2.3 Create base layout with navigation sidebar for Feedback, Metrics, Prompts, and Lexicon sections
- [x] 2.4 Add a simple login/token input page for local development

## 3. Data Access Layer

- [x] 3.1 Create read-only JPA entities for `projects`, `generated_images`, `feedbacks`, and `stage_logs` mapped to existing tables
- [x] 3.2 Create Spring Data repositories for paginated and filtered queries
- [x] 3.3 Add a `@Transactional(readOnly = true)` service layer for data aggregation
- [ ] 3.4 Add audit logging for any write operation performed by admin endpoints

## 4. Feedback Management API

- [x] 4.1 Implement `GET /api/admin/feedbacks` with pagination and filters (category, type, processed status)
- [x] 4.2 Implement `POST /api/admin/feedbacks/{id}/process` to mark feedback as processed with notes
- [x] 4.3 Add DTOs and mapper for feedback records including intent correction payload
- [x] 4.4 Add integration tests for feedback list and mark-processed endpoints

## 5. System Metrics API

- [x] 5.1 Implement `GET /api/admin/metrics/overview` returning project/image/feedback/session counts
- [x] 5.2 Implement `GET /api/admin/metrics/stages` returning average and p95 stage durations for the last 24 hours
- [x] 5.3 Implement `GET /api/admin/metrics/feedback-distribution` returning counts grouped by tag and category
- [x] 5.4 Add integration tests for metrics endpoints

## 6. Prompt Template Management API

- [x] 6.1 Implement `GET /api/admin/prompt-templates` listing template metadata (name, version, space_type, created_at)
- [x] 6.2 Implement `GET /api/admin/prompt-templates/{name}/performance` returning image count and feedback polarity by version
- [x] 6.3 Implement `POST /api/admin/prompt-templates/preview` returning rendered positive and negative prompts without image generation
- [x] 6.4 Add integration tests for prompt template list, performance, and preview endpoints

## 7. Intent Lexicon Management API

- [x] 7.1 Implement `GET /api/admin/intent-taxonomy` returning the full taxonomy loaded from `agent-core/data/intent_taxonomy.yaml`
- [x] 7.2 Implement `GET /api/admin/intent-taxonomy/alias-proposals` returning proposals aggregated from feedback corrections
- [x] 7.3 Implement `POST /api/admin/intent-taxonomy/alias-proposals/apply` to append approved aliases to the YAML file
- [x] 7.4 Implement `POST /api/admin/intent-taxonomy/aliases` to manually add an alias to a taxonomy entry
- [ ] 7.5 Use `ruamel.yaml` or equivalent to preserve YAML formatting and comments when writing
- [x] 7.6 Add integration tests for taxonomy read, proposals, and apply endpoints

## 8. Admin Frontend Pages

- [x] 8.1 Build Feedback page with table, filters, and "Mark Processed" action
- [x] 8.2 Build Metrics dashboard with overview cards, stage duration chart, and feedback distribution chart
- [x] 8.3 Build Prompt Templates page listing versions and showing per-version performance
- [x] 8.4 Build Prompt Preview form with theme/space_type/budget inputs and rendered prompt output
- [x] 8.5 Build Intent Lexicon page showing taxonomy tree, alias proposals, and manual alias form
- [x] 8.6 Wire all pages to backend APIs and handle loading/error states

## 9. Integration and Verification

- [x] 9.1 Add `agent-admin-backend` to the root Maven aggregator `pom.xml`
- [x] 9.2 Verify `mvn clean compile -Xlint:all` passes for the new backend module
- [x] 9.3 Verify `agent-admin-front` builds successfully (`npm run build`)
- [x] 9.4 Run end-to-end local validation by starting backend, frontend, and exercising each page
- [x] 9.5 Update root `README.md` or relevant docs with module startup instructions
