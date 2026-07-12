## 1. Database Schema

- [x] 1.1 Create `users` table with `id`, `phone`, `created_at`, `updated_at` fields
- [x] 1.2 Add `user_id` column to `projects` table
- [x] 1.3 Add `user_id` column to `session_messages` table
- [x] 1.4 Add `user_id` column to `feedbacks` table
- [~] 1.5 Add `user_id` column to `project_documents` table <!-- 不再适用：project_documents 表由 agent-core (Python) 管理，文档访问已通过 project 归属关系间接隔离，无需冗余 user_id 列 -->
- [x] 1.6 Seed a default system user for existing anonymous data

## 2. User Domain Model (agent-api)

- [x] 2.1 Create `User` JPA entity
- [x] 2.2 Create `UserRepository` with phone lookup
- [x] 2.3 Create `SmsService` interface and `MockSmsService` implementation (fixed code 8888)
- [x] 2.4 Create `JwtService` for token generation and validation
- [x] 2.5 Create `UserService` with register/login/verify-code logic

## 3. Authentication API (agent-api)

- [x] 3.1 Create `AuthController` with `/api/v1/auth/send-code` endpoint
- [x] 3.2 Create `/api/v1/auth/register` endpoint
- [x] 3.3 Create `/api/v1/auth/login` endpoint
- [x] 3.4 Add JWT secret and expiration configuration in `application.yml`

## 4. Security Integration

- [x] 4.1 Add Spring Security dependency to `pom.xml`
- [x] 4.2 Create `JwtAuthenticationFilter` to extract user from token
- [x] 4.3 Create `SecurityConfig` to allow public auth endpoints and protect others
- [x] 4.4 Create `CurrentUser` annotation and resolver for controller methods

## 5. Data Isolation

- [x] 5.1 Update `ProjectService` to scope queries by current `user_id`
- [x] 5.2 Update `SessionMessageService` to scope queries by current `user_id`
- [x] 5.3 Update `FeedbackService` to scope queries by current `user_id`
- [x] 5.4 Set `user_id` when creating new projects/messages/feedbacks
- [x] 5.5 Block cross-user access with 403 responses

## 6. Frontend Login Flow

- [x] 6.1 Create login page with phone input and verification code input
- [x] 6.2 Store JWT token after login
- [x] 6.3 Attach token to all API requests
- [x] 6.4 Redirect unauthenticated users to login page

## 7. Testing & Validation

- [x] 7.1 Test registration and login with fixed code `8888`
- [x] 7.2 Test data isolation between two users
- [x] 7.3 Verify existing anonymous data still accessible after migration
- [x] 7.4 Restart agent-api and frontend, validate full flow
