## 1. Database Schema

- [ ] 1.1 Create `users` table with `id`, `phone`, `created_at`, `updated_at` fields
- [ ] 1.2 Add `user_id` column to `projects` table
- [ ] 1.3 Add `user_id` column to `session_messages` table
- [ ] 1.4 Add `user_id` column to `feedbacks` table
- [ ] 1.5 Add `user_id` column to `project_documents` table
- [ ] 1.6 Seed a default system user for existing anonymous data

## 2. User Domain Model (agent-api)

- [ ] 2.1 Create `User` JPA entity
- [ ] 2.2 Create `UserRepository` with phone lookup
- [ ] 2.3 Create `SmsService` interface and `MockSmsService` implementation (fixed code 8888)
- [ ] 2.4 Create `JwtService` for token generation and validation
- [ ] 2.5 Create `UserService` with register/login/verify-code logic

## 3. Authentication API (agent-api)

- [ ] 3.1 Create `AuthController` with `/api/v1/auth/send-code` endpoint
- [ ] 3.2 Create `/api/v1/auth/register` endpoint
- [ ] 3.3 Create `/api/v1/auth/login` endpoint
- [ ] 3.4 Add JWT secret and expiration configuration in `application.yml`

## 4. Security Integration

- [ ] 4.1 Add Spring Security dependency to `pom.xml`
- [ ] 4.2 Create `JwtAuthenticationFilter` to extract user from token
- [ ] 4.3 Create `SecurityConfig` to allow public auth endpoints and protect others
- [ ] 4.4 Create `CurrentUser` annotation and resolver for controller methods

## 5. Data Isolation

- [ ] 5.1 Update `ProjectService` to scope queries by current `user_id`
- [ ] 5.2 Update `SessionMessageService` to scope queries by current `user_id`
- [ ] 5.3 Update `FeedbackService` to scope queries by current `user_id`
- [ ] 5.4 Set `user_id` when creating new projects/messages/feedbacks
- [ ] 5.5 Block cross-user access with 403 responses

## 6. Frontend Login Flow

- [ ] 6.1 Create login page with phone input and verification code input
- [ ] 6.2 Store JWT token after login
- [ ] 6.3 Attach token to all API requests
- [ ] 6.4 Redirect unauthenticated users to login page

## 7. Testing & Validation

- [ ] 7.1 Test registration and login with fixed code `8888`
- [ ] 7.2 Test data isolation between two users
- [ ] 7.3 Verify existing anonymous data still accessible after migration
- [ ] 7.4 Restart agent-api and frontend, validate full flow
