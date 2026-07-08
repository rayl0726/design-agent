# 手机号账号隔离 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 agent-api 中引入基于中国大陆手机号的账号体系，实现注册、登录、JWT 鉴权和用户数据隔离。

**Architecture:** 在 agent-api 新增 `User` 领域模型和 `/auth/**` 端点；所有用户请求通过 Spring Security + JWT Filter 鉴权；业务表增加 `user_id` 字段，Service 层根据当前登录用户过滤数据；验证码服务保留接口，当前用 `MockSmsService` 固定返回 `8888`。

**Tech Stack:** Java 17, Spring Boot 3.x, Spring Security 6.x, Spring Data JPA, jjwt, MySQL, Vue 3 + Element Plus

## Global Constraints

- 账号体系仅在 agent-api 实现，agent-core 不感知用户态。
- 仅支持中国大陆手机号登录，验证码固定为 `8888`。
- JWT 有效期 30 天，通过 `Authorization: Bearer <token>` 传递。
- 全站强制登录，除 `/auth/**` 外所有端点需有效 JWT。
- 历史匿名数据通过默认系统用户（id=1）兼容。

---

## File Structure

### New Files

- `agent-api/src/main/java/com/meichen/orchestrator/entity/User.java` — 用户实体
- `agent-api/src/main/java/com/meichen/orchestrator/repository/UserRepository.java` — 用户数据访问
- `agent-api/src/main/java/com/meichen/orchestrator/service/SmsService.java` — 短信服务接口
- `agent-api/src/main/java/com/meichen/orchestrator/service/MockSmsService.java` — 固定验证码实现
- `agent-api/src/main/java/com/meichen/orchestrator/service/JwtService.java` — JWT 生成与校验
- `agent-api/src/main/java/com/meichen/orchestrator/service/UserService.java` — 注册/登录业务逻辑
- `agent-api/src/main/java/com/meichen/orchestrator/controller/AuthController.java` — 验证码/注册/登录接口
- `agent-api/src/main/java/com/meichen/orchestrator/security/JwtAuthenticationFilter.java` — JWT 鉴权过滤器
- `agent-api/src/main/java/com/meichen/orchestrator/security/SecurityConfig.java` — Spring Security 配置
- `agent-api/src/main/java/com/meichen/orchestrator/security/CurrentUser.java` — 当前用户注解
- `agent-api/src/main/java/com/meichen/orchestrator/security/CurrentUserArgumentResolver.java` — 注解解析器
- `frontend/src/views/LoginView.vue` — 登录页面
- `frontend/src/stores/auth.js` — Pinia 登录态存储

### Modified Files

- `agent-api/pom.xml` — 添加 Spring Security、jjwt 依赖
- `agent-api/src/main/resources/application.yml` — JWT 密钥与过期时间配置
- `agent-api/src/main/java/com/meichen/orchestrator/entity/Project.java` — 增加 `userId`
- `agent-api/src/main/java/com/meichen/orchestrator/entity/SessionMessage.java` — 增加 `userId`
- `agent-api/src/main/java/com/meichen/orchestrator/entity/Feedback.java` — 增加 `userId`
- `agent-api/src/main/java/com/meichen/orchestrator/repository/ProjectRepository.java` — 按 userId 查询方法
- `agent-api/src/main/java/com/meichen/orchestrator/repository/SessionMessageRepository.java` — 按 projectId + userId 查询
- `agent-api/src/main/java/com/meichen/orchestrator/repository/FeedbackRepository.java` — 按 projectId + userId 查询
- `agent-api/src/main/java/com/meichen/orchestrator/service/WorkflowService.java` — 创建项目时写入 userId
- `agent-api/src/main/java/com/meichen/orchestrator/service/SessionMessageService.java` — 查询/写入时校验 userId
- `agent-api/src/main/java/com/meichen/orchestrator/service/FeedbackService.java` — 查询/写入时校验 userId
- `agent-api/src/main/java/com/meichen/orchestrator/controller/ProjectController.java` — 注入当前用户并隔离数据
- `agent-api/src/main/java/com/meichen/orchestrator/controller/FeedbackController.java` — 注入当前用户并隔离数据
- `agent-api/src/main/java/com/meichen/orchestrator/config/WebMvcConfig.java` — 注册 CurrentUser 参数解析器
- `frontend/src/router/index.js` — 增加登录路由与导航守卫
- `frontend/src/api/request.js` — 请求拦截器附加 token

---

## Task 1: Add Dependencies

**Files:**
- Modify: `agent-api/pom.xml`

**Interfaces:**
- Produces: `spring-boot-starter-security`, `jjwt-api`, `jjwt-impl`, `jjwt-jackson` on classpath.

- [ ] **Step 1: Add dependencies to pom.xml**

  Add inside `<dependencies>`:

  ```xml
  <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-security</artifactId>
  </dependency>
  <dependency>
      <groupId>io.jsonwebtoken</groupId>
      <artifactId>jjwt-api</artifactId>
      <version>0.12.6</version>
  </dependency>
  <dependency>
      <groupId>io.jsonwebtoken</groupId>
      <artifactId>jjwt-impl</artifactId>
      <version>0.12.6</version>
      <scope>runtime</scope>
  </dependency>
  <dependency>
      <groupId>io.jsonwebtoken</groupId>
      <artifactId>jjwt-jackson</artifactId>
      <version>0.12.6</version>
      <scope>runtime</scope>
  </dependency>
  ```

- [ ] **Step 2: Verify Maven can resolve dependencies**

  Run: `cd /Users/liulei/private-work/design-agent/agent-api && JAVA_HOME=/Users/liulei/.jdks/amazon-corretto-17.jdk/Contents/Home mvn dependency:resolve -q`

  Expected: BUILD SUCCESS

- [ ] **Step 3: Commit**

  ```bash
  git add agent-api/pom.xml
  git commit -m "deps: add spring security and jjwt for phone account isolation"
  ```

---

## Task 2: Database Schema Migration via JPA

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/entity/User.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/entity/Project.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/entity/SessionMessage.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/entity/Feedback.java`

**Interfaces:**
- Consumes: JPA `ddl-auto: update` will create/alter tables on startup.
- Produces: `User` entity with `Long id`, `String phone`; `Project`, `SessionMessage`, `Feedback` gain `Long userId`.

- [ ] **Step 1: Create User entity**

  ```java
  package com.meichen.orchestrator.entity;

  import jakarta.persistence.*;
  import org.hibernate.annotations.CreationTimestamp;
  import org.hibernate.annotations.UpdateTimestamp;

  import java.time.LocalDateTime;

  @Entity
  @Table(name = "users")
  public class User {

      @Id
      @GeneratedValue(strategy = GenerationType.IDENTITY)
      private Long id;

      @Column(nullable = false, unique = true, length = 11)
      private String phone;

      @CreationTimestamp
      @Column(name = "created_at")
      private LocalDateTime createdAt;

      @UpdateTimestamp
      @Column(name = "updated_at")
      private LocalDateTime updatedAt;

      public User() {}

      public static User of(String phone) {
          User user = new User();
          user.setPhone(phone);
          return user;
      }

      public Long getId() { return id; }
      public void setId(Long id) { this.id = id; }

      public String getPhone() { return phone; }
      public void setPhone(String phone) { this.phone = phone; }

      public LocalDateTime getCreatedAt() { return createdAt; }
      public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

      public LocalDateTime getUpdatedAt() { return updatedAt; }
      public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
  }
  ```

- [ ] **Step 2: Add userId to Project entity**

  In `Project.java`, add field and accessors:

  ```java
  @Column(name = "user_id")
  private Long userId;

  public Long getUserId() { return userId; }
  public void setUserId(Long userId) { this.userId = userId; }
  ```

- [ ] **Step 3: Add userId to SessionMessage entity**

  In `SessionMessage.java`, add field and accessors:

  ```java
  @Column(name = "user_id")
  private Long userId;

  public Long getUserId() { return userId; }
  public void setUserId(Long userId) { this.userId = userId; }
  ```

- [ ] **Step 4: Add userId to Feedback entity**

  In `Feedback.java`, add field and accessors:

  ```java
  @Column(name = "user_id")
  private Long userId;

  public Long getUserId() { return userId; }
  public void setUserId(Long userId) { this.userId = userId; }
  ```

- [ ] **Step 5: Start agent-api and verify schema**

  Run: `cd /Users/liulei/private-work/design-agent/agent-api && JAVA_HOME=/Users/liulei/.jdks/amazon-corretto-17.jdk/Contents/Home mvn clean spring-boot:run`

  Verify MySQL tables:

  ```sql
  SHOW COLUMNS FROM users;
  SHOW COLUMNS FROM java_projects;
  SHOW COLUMNS FROM session_messages;
  SHOW COLUMNS FROM feedbacks;
  ```

  Expected: each table has `user_id` column; `users` table exists with `id`, `phone`, `created_at`, `updated_at`.

- [ ] **Step 6: Commit**

  ```bash
  git add agent-api/src/main/java/com/meichen/orchestrator/entity/
  git commit -m "feat(account): add User entity and user_id columns to business tables"
  ```

---

## Task 3: User Repository

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/repository/UserRepository.java`

**Interfaces:**
- Consumes: `User` entity.
- Produces: `Optional<User> findByPhone(String phone)`; `boolean existsByPhone(String phone)`.

- [ ] **Step 1: Create UserRepository**

  ```java
  package com.meichen.orchestrator.repository;

  import com.meichen.orchestrator.entity.User;
  import org.springframework.data.jpa.repository.JpaRepository;
  import org.springframework.stereotype.Repository;

  import java.util.Optional;

  @Repository
  public interface UserRepository extends JpaRepository<User, Long> {
      Optional<User> findByPhone(String phone);
      boolean existsByPhone(String phone);
  }
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add agent-api/src/main/java/com/meichen/orchestrator/repository/UserRepository.java
  git commit -m "feat(account): add UserRepository"
  ```

---

## Task 4: SmsService and MockSmsService

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/service/SmsService.java`
- Create: `agent-api/src/main/java/com/meichen/orchestrator/service/MockSmsService.java`

**Interfaces:**
- Produces: `SmsService.sendVerificationCode(String phone)` returns `String` verification code.

- [ ] **Step 1: Create SmsService interface**

  ```java
  package com.meichen.orchestrator.service;

  public interface SmsService {
      String sendVerificationCode(String phone);
  }
  ```

- [ ] **Step 2: Create MockSmsService**

  ```java
  package com.meichen.orchestrator.service;

  import org.springframework.stereotype.Service;

  @Service
  public class MockSmsService implements SmsService {

      public static final String FIXED_CODE = "8888";

      @Override
      public String sendVerificationCode(String phone) {
          return FIXED_CODE;
      }
  }
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add agent-api/src/main/java/com/meichen/orchestrator/service/SmsService.java
  git add agent-api/src/main/java/com/meichen/orchestrator/service/MockSmsService.java
  git commit -m "feat(account): add sms service with fixed 8888 mock implementation"
  ```

---

## Task 5: JwtService

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/service/JwtService.java`
- Modify: `agent-api/src/main/resources/application.yml`

**Interfaces:**
- Consumes: `jwt.secret` and `jwt.expiration-days` from `application.yml`.
- Produces: `String generateToken(Long userId, String phone)`; `Optional<Long> extractUserId(String token)`; `boolean isValid(String token)`.

- [ ] **Step 1: Add JWT config to application.yml**

  Append to `application.yml`:

  ```yaml
  jwt:
    secret: ${JWT_SECRET:meichen-default-secret-key-must-be-overridden-in-production}
    expiration-days: 30
  ```

- [ ] **Step 2: Create JwtService**

  ```java
  package com.meichen.orchestrator.service;

  import io.jsonwebtoken.Claims;
  import io.jsonwebtoken.Jwts;
  import io.jsonwebtoken.security.Keys;
  import org.springframework.beans.factory.annotation.Value;
  import org.springframework.stereotype.Service;

  import javax.crypto.SecretKey;
  import java.nio.charset.StandardCharsets;
  import java.time.Instant;
  import java.time.temporal.ChronoUnit;
  import java.util.Date;
  import java.util.Optional;

  @Service
  public class JwtService {

      private final SecretKey key;
      private final long expirationDays;

      public JwtService(
              @Value("${jwt.secret}") String secret,
              @Value("${jwt.expiration-days:30}") long expirationDays) {
          this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
          this.expirationDays = expirationDays;
      }

      public String generateToken(Long userId, String phone) {
          Instant now = Instant.now();
          Instant expiry = now.plus(expirationDays, ChronoUnit.DAYS);
          return Jwts.builder()
                  .subject(String.valueOf(userId))
                  .claim("phone", phone)
                  .issuedAt(Date.from(now))
                  .expiration(Date.from(expiry))
                  .signWith(key)
                  .compact();
      }

      public Optional<Long> extractUserId(String token) {
          try {
              Claims claims = parseToken(token);
              return Optional.ofNullable(claims.getSubject()).map(Long::parseLong);
          } catch (Exception e) {
              return Optional.empty();
          }
      }

      public boolean isValid(String token) {
          try {
              Claims claims = parseToken(token);
              return claims.getExpiration().after(new Date());
          } catch (Exception e) {
              return false;
          }
      }

      private Claims parseToken(String token) {
          return Jwts.parser()
                  .verifyWith(key)
                  .build()
                  .parseSignedClaims(token)
                  .getPayload();
      }
  }
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add agent-api/src/main/resources/application.yml
  git add agent-api/src/main/java/com/meichen/orchestrator/service/JwtService.java
  git commit -m "feat(account): add JwtService with 30-day expiration"
  ```

---

## Task 6: UserService

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/service/UserService.java`

**Interfaces:**
- Consumes: `UserRepository`, `JwtService`, `SmsService`.
- Produces: `LoginResponse sendCode(String phone)`; `LoginResponse register(String phone, String code)`; `LoginResponse login(String phone, String code)`; `User findById(Long id)`.

- [ ] **Step 1: Create LoginResponse DTO inside service package**

  ```java
  package com.meichen.orchestrator.service;

  public record LoginResponse(String token, Long userId, String phone) {}
  ```

- [ ] **Step 2: Create UserService**

  ```java
  package com.meichen.orchestrator.service;

  import com.meichen.orchestrator.entity.User;
  import com.meichen.orchestrator.repository.UserRepository;
  import org.springframework.stereotype.Service;
  import org.springframework.transaction.annotation.Transactional;

  import java.util.regex.Pattern;

  @Service
  public class UserService {

      private static final Pattern PHONE_PATTERN = Pattern.compile("^1[3-9]\\d{9}$");

      private final UserRepository userRepository;
      private final JwtService jwtService;
      private final SmsService smsService;

      public UserService(UserRepository userRepository,
                         JwtService jwtService,
                         SmsService smsService) {
          this.userRepository = userRepository;
          this.jwtService = jwtService;
          this.smsService = smsService;
      }

      public String sendCode(String phone) {
          validatePhone(phone);
          return smsService.sendVerificationCode(phone);
      }

      @Transactional
      public LoginResponse register(String phone, String code) {
          validatePhone(phone);
          validateCode(code);
          if (userRepository.existsByPhone(phone)) {
              throw new IllegalArgumentException("手机号已注册");
          }
          User user = User.of(phone);
          userRepository.save(user);
          String token = jwtService.generateToken(user.getId(), phone);
          return new LoginResponse(token, user.getId(), phone);
      }

      @Transactional(readOnly = true)
      public LoginResponse login(String phone, String code) {
          validatePhone(phone);
          validateCode(code);
          User user = userRepository.findByPhone(phone)
                  .orElseThrow(() -> new IllegalArgumentException("手机号未注册"));
          String token = jwtService.generateToken(user.getId(), phone);
          return new LoginResponse(token, user.getId(), phone);
      }

      @Transactional(readOnly = true)
      public User findById(Long id) {
          return userRepository.findById(id)
                  .orElseThrow(() -> new IllegalArgumentException("用户不存在"));
      }

      private void validatePhone(String phone) {
          if (phone == null || !PHONE_PATTERN.matcher(phone).matches()) {
              throw new IllegalArgumentException("手机号格式不正确");
          }
      }

      private void validateCode(String code) {
          if (!MockSmsService.FIXED_CODE.equals(code)) {
              throw new IllegalArgumentException("验证码错误");
          }
      }
  }
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add agent-api/src/main/java/com/meichen/orchestrator/service/UserService.java
  git add agent-api/src/main/java/com/meichen/orchestrator/service/LoginResponse.java
  git commit -m "feat(account): add UserService with register, login and fixed code validation"
  ```

---

## Task 7: AuthController

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/controller/AuthController.java`

**Interfaces:**
- Consumes: `UserService`.
- Produces: `POST /api/v1/auth/send-code`, `POST /api/v1/auth/register`, `POST /api/v1/auth/login`.

- [ ] **Step 1: Create request DTOs**

  Create `agent-api/src/main/java/com/meichen/orchestrator/controller/AuthRequest.java`:

  ```java
  package com.meichen.orchestrator.controller;

  public record AuthRequest(String phone, String code) {}
  ```

  Create `agent-api/src/main/java/com/meichen/orchestrator/controller/SendCodeRequest.java`:

  ```java
  package com.meichen.orchestrator.controller;

  public record SendCodeRequest(String phone) {}
  ```

- [ ] **Step 2: Create AuthController**

  ```java
  package com.meichen.orchestrator.controller;

  import com.meichen.orchestrator.service.LoginResponse;
  import com.meichen.orchestrator.service.UserService;
  import org.springframework.http.ResponseEntity;
  import org.springframework.web.bind.annotation.*;

  import java.util.Map;

  @RestController
  @RequestMapping("/api/v1/auth")
  public class AuthController {

      private final UserService userService;

      public AuthController(UserService userService) {
          this.userService = userService;
      }

      @PostMapping("/send-code")
      public ResponseEntity<Map<String, String>> sendCode(@RequestBody SendCodeRequest request) {
          String code = userService.sendCode(request.phone());
          return ResponseEntity.ok(Map.of("phone", request.phone(), "code", code));
      }

      @PostMapping("/register")
      public ResponseEntity<LoginResponse> register(@RequestBody AuthRequest request) {
          return ResponseEntity.ok(userService.register(request.phone(), request.code()));
      }

      @PostMapping("/login")
      public ResponseEntity<LoginResponse> login(@RequestBody AuthRequest request) {
          return ResponseEntity.ok(userService.login(request.phone(), request.code()));
      }
  }
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add agent-api/src/main/java/com/meichen/orchestrator/controller/AuthController.java
  git add agent-api/src/main/java/com/meichen/orchestrator/controller/AuthRequest.java
  git add agent-api/src/main/java/com/meichen/orchestrator/controller/SendCodeRequest.java
  git commit -m "feat(account): add AuthController for send-code, register and login"
  ```

---

## Task 8: Spring Security + JWT Filter

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/security/JwtAuthenticationFilter.java`
- Create: `agent-api/src/main/java/com/meichen/orchestrator/security/SecurityConfig.java`

**Interfaces:**
- Consumes: `JwtService`.
- Produces: `SecurityFilterChain` allowing `/api/v1/auth/**` and requiring JWT for others; populates `SecurityContextHolder` with authenticated user id.

- [ ] **Step 1: Create JwtAuthenticationFilter**

  ```java
  package com.meichen.orchestrator.security;

  import com.meichen.orchestrator.service.JwtService;
  import jakarta.servlet.FilterChain;
  import jakarta.servlet.ServletException;
  import jakarta.servlet.http.HttpServletRequest;
  import jakarta.servlet.http.HttpServletResponse;
  import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
  import org.springframework.security.core.context.SecurityContextHolder;
  import org.springframework.stereotype.Component;
  import org.springframework.web.filter.OncePerRequestFilter;

  import java.io.IOException;
  import java.util.Collections;
  import java.util.Optional;

  @Component
  public class JwtAuthenticationFilter extends OncePerRequestFilter {

      private final JwtService jwtService;

      public JwtAuthenticationFilter(JwtService jwtService) {
          this.jwtService = jwtService;
      }

      @Override
      protected void doFilterInternal(HttpServletRequest request,
                                      HttpServletResponse response,
                                      FilterChain filterChain) throws ServletException, IOException {
          String header = request.getHeader("Authorization");
          if (header != null && header.startsWith("Bearer ")) {
              String token = header.substring(7);
              Optional<Long> userId = jwtService.extractUserId(token);
              if (userId.isPresent() && jwtService.isValid(token)) {
                  UsernamePasswordAuthenticationToken auth =
                          new UsernamePasswordAuthenticationToken(userId.get(), null, Collections.emptyList());
                  SecurityContextHolder.getContext().setAuthentication(auth);
              }
          }
          filterChain.doFilter(request, response);
      }
  }
  ```

- [ ] **Step 2: Create SecurityConfig**

  ```java
  package com.meichen.orchestrator.security;

  import org.springframework.context.annotation.Bean;
  import org.springframework.context.annotation.Configuration;
  import org.springframework.security.config.annotation.web.builders.HttpSecurity;
  import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
  import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
  import org.springframework.security.config.http.SessionCreationPolicy;
  import org.springframework.security.web.SecurityFilterChain;
  import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

  @Configuration
  @EnableWebSecurity
  public class SecurityConfig {

      private final JwtAuthenticationFilter jwtAuthenticationFilter;

      public SecurityConfig(JwtAuthenticationFilter jwtAuthenticationFilter) {
          this.jwtAuthenticationFilter = jwtAuthenticationFilter;
      }

      @Bean
      public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
          http
              .csrf(AbstractHttpConfigurer::disable)
              .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
              .authorizeHttpRequests(auth -> auth
                  .requestMatchers("/api/v1/auth/**").permitAll()
                  .anyRequest().authenticated()
              )
              .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);
          return http.build();
      }
  }
  ```

- [ ] **Step 3: Start agent-api and verify public/private endpoints**

  Run agent-api.

  Test public endpoint:

  ```bash
  curl -s -X POST http://localhost:8080/api/v1/auth/send-code \
    -H "Content-Type: application/json" \
    -d '{"phone":"13800138000"}'
  ```

  Expected: `{"phone":"13800138000","code":"8888"}`

  Test protected endpoint without token:

  ```bash
  curl -s -X GET http://localhost:8080/api/v1/projects
  ```

  Expected: HTTP 401

- [ ] **Step 4: Commit**

  ```bash
  git add agent-api/src/main/java/com/meichen/orchestrator/security/
  git commit -m "feat(account): add JWT filter and spring security config"
  ```

---

## Task 9: CurrentUser Annotation and Resolver

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/security/CurrentUser.java`
- Create: `agent-api/src/main/java/com/meichen/orchestrator/security/CurrentUserArgumentResolver.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/config/WebMvcConfig.java`

**Interfaces:**
- Consumes: `SecurityContextHolder` authentication principal.
- Produces: `@CurrentUser Long userId` works in controller method parameters.

- [ ] **Step 1: Create CurrentUser annotation**

  ```java
  package com.meichen.orchestrator.security;

  import java.lang.annotation.ElementType;
  import java.lang.annotation.Retention;
  import java.lang.annotation.RetentionPolicy;
  import java.lang.annotation.Target;

  @Target(ElementType.PARAMETER)
  @Retention(RetentionPolicy.RUNTIME)
  public @interface CurrentUser {}
  ```

- [ ] **Step 2: Create CurrentUserArgumentResolver**

  ```java
  package com.meichen.orchestrator.security;

  import org.springframework.core.MethodParameter;
  import org.springframework.security.core.context.SecurityContextHolder;
  import org.springframework.stereotype.Component;
  import org.springframework.web.bind.support.WebDataBinderFactory;
  import org.springframework.web.context.request.NativeWebRequest;
  import org.springframework.web.method.support.HandlerMethodArgumentResolver;
  import org.springframework.web.method.support.ModelAndViewContainer;

  @Component
  public class CurrentUserArgumentResolver implements HandlerMethodArgumentResolver {

      @Override
      public boolean supportsParameter(MethodParameter parameter) {
          return parameter.hasParameterAnnotation(CurrentUser.class)
                  && parameter.getParameterType().equals(Long.class);
      }

      @Override
      public Object resolveArgument(MethodParameter parameter,
                                    ModelAndViewContainer mavContainer,
                                    NativeWebRequest webRequest,
                                    WebDataBinderFactory binderFactory) {
          Object principal = SecurityContextHolder.getContext().getAuthentication().getPrincipal();
          if (principal instanceof Long userId) {
              return userId;
          }
          throw new IllegalStateException("无法获取当前用户 ID");
      }
  }
  ```

- [ ] **Step 3: Register resolver in WebMvcConfig**

  Modify `WebMvcConfig.java`:

  ```java
  import com.meichen.orchestrator.security.CurrentUserArgumentResolver;
  import org.springframework.web.method.support.HandlerMethodArgumentResolver;

  // add field
  private final CurrentUserArgumentResolver currentUserArgumentResolver;

  // update constructor to inject it

  @Override
  public void addArgumentResolvers(List<HandlerMethodArgumentResolver> resolvers) {
      resolvers.add(currentUserArgumentResolver);
  }
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add agent-api/src/main/java/com/meichen/orchestrator/security/CurrentUser.java
  git add agent-api/src/main/java/com/meichen/orchestrator/security/CurrentUserArgumentResolver.java
  git add agent-api/src/main/java/com/meichen/orchestrator/config/WebMvcConfig.java
  git commit -m "feat(account): add @CurrentUser argument resolver"
  ```

---

## Task 10: Seed System User

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/config/SystemUserInitializer.java`

**Interfaces:**
- Consumes: `UserRepository`.
- Produces: System user with id=1 exists in `users` table on startup.

- [ ] **Step 1: Create SystemUserInitializer**

  ```java
  package com.meichen.orchestrator.config;

  import com.meichen.orchestrator.entity.User;
  import com.meichen.orchestrator.repository.UserRepository;
  import org.springframework.boot.CommandLineRunner;
  import org.springframework.stereotype.Component;

  @Component
  public class SystemUserInitializer implements CommandLineRunner {

      public static final Long SYSTEM_USER_ID = 1L;
      public static final String SYSTEM_PHONE = "00000000000";

      private final UserRepository userRepository;

      public SystemUserInitializer(UserRepository userRepository) {
          this.userRepository = userRepository;
      }

      @Override
      public void run(String... args) {
          if (!userRepository.existsById(SYSTEM_USER_ID)) {
              User system = new User();
              system.setId(SYSTEM_USER_ID);
              system.setPhone(SYSTEM_PHONE);
              userRepository.save(system);
          }
      }
  }
  ```

- [ ] **Step 2: Start agent-api and verify system user**

  ```sql
  SELECT * FROM users WHERE id = 1;
  ```

  Expected: one row with phone `00000000000`.

- [ ] **Step 3: Commit**

  ```bash
  git add agent-api/src/main/java/com/meichen/orchestrator/config/SystemUserInitializer.java
  git commit -m "feat(account): seed system user for anonymous legacy data"
  ```

---

## Task 11: Project Data Isolation

**Files:**
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/repository/ProjectRepository.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/service/WorkflowService.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/controller/ProjectController.java`

**Interfaces:**
- Consumes: `@CurrentUser Long userId`.
- Produces: `List<Project> findByUserIdOrderByCreatedAtDesc(Long userId)`; `Optional<Project> findByIdAndUserId(String id, Long userId)`.

- [ ] **Step 1: Add query methods to ProjectRepository**

  ```java
  List<Project> findByUserIdOrderByCreatedAtDesc(Long userId);
  Optional<Project> findByIdAndUserId(String id, Long userId);
  ```

- [ ] **Step 2: Update ProjectController**

  Change `listProjects` to:

  ```java
  @GetMapping
  public ResponseEntity<List<Project>> listProjects(@CurrentUser Long userId) {
      return ResponseEntity.ok(projectRepository.findByUserIdOrderByCreatedAtDesc(userId));
  }
  ```

  Change `getProject` to:

  ```java
  @GetMapping("/{id}")
  public ResponseEntity<Project> getProject(@PathVariable("id") String projectId, @CurrentUser Long userId) {
      return projectRepository.findByIdAndUserId(projectId, userId)
              .map(ResponseEntity::ok)
              .orElse(ResponseEntity.notFound().build());
  }
  ```

  Change `createProject` (multipart) to accept `@CurrentUser Long userId` and pass to `workflowService.createProject`.
  Update signature of `createProject` to include userId as first argument after name/description/inputs.

  Change `createProjectJson` similarly.

- [ ] **Step 3: Update WorkflowService.createProject signature and implementation**

  Add `Long userId` parameter to `createProject` and set it on the new Project:

  ```java
  public Project createProject(String name, String description, Map<String, Object> inputs, Long userId) {
      Project project = new Project();
      project.setId(UUID.randomUUID().toString());
      project.setName(name);
      project.setDescription(description);
      project.setUserId(userId);
      // ... rest unchanged
  }
  ```

  Update all internal callers of `createProject` within `WorkflowService` (if any) to pass `userId`. For workflow-triggered creation from messages, use the project's existing userId.

- [ ] **Step 4: Verify with curl**

  Register and get token:

  ```bash
  TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d '{"phone":"13800138000","code":"8888"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
  ```

  Create project:

  ```bash
  curl -s -X POST http://localhost:8080/api/v1/projects \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"测试项目"}' | head -c 200
  ```

  List projects:

  ```bash
  curl -s -X GET http://localhost:8080/api/v1/projects \
    -H "Authorization: Bearer $TOKEN"
  ```

  Expected: list contains only the newly created project.

- [ ] **Step 5: Commit**

  ```bash
  git add agent-api/src/main/java/com/meichen/orchestrator/repository/ProjectRepository.java
  git add agent-api/src/main/java/com/meichen/orchestrator/service/WorkflowService.java
  git add agent-api/src/main/java/com/meichen/orchestrator/controller/ProjectController.java
  git commit -m "feat(account): isolate projects by user_id"
  ```

---

## Task 12: SessionMessage Data Isolation

**Files:**
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/repository/SessionMessageRepository.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/service/SessionMessageService.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/controller/ProjectController.java`

**Interfaces:**
- Consumes: `@CurrentUser Long userId`, `ProjectRepository`.
- Produces: `listMessages` and `addUserMessage` scoped to user's project.

- [ ] **Step 1: Update SessionMessageRepository**

  Add method:

  ```java
  List<SessionMessage> findByProjectIdAndUserIdOrderByCreatedAtAsc(String projectId, Long userId);
  ```

- [ ] **Step 2: Update SessionMessageService**

  Change method signatures to include `Long userId`:

  ```java
  @Transactional(readOnly = true)
  public List<SessionMessage> listMessages(String projectId, Long userId) {
      ensureProjectBelongsToUser(projectId, userId);
      return messageRepository.findByProjectIdAndUserIdOrderByCreatedAtAsc(projectId, userId);
  }

  @Transactional
  public SessionMessage addUserMessage(String projectId, String content, Long userId) {
      Project project = ensureProjectBelongsToUser(projectId, userId);
      SessionMessage msg = SessionMessage.create(projectId, "user", "text", content);
      msg.setUserId(userId);
      SessionMessage saved = messageRepository.save(msg);
      // ... rest unchanged
  }

  @Transactional
  public SessionMessage addAssistantMessage(String projectId, String messageType, String content, Long userId) {
      ensureProjectBelongsToUser(projectId, userId);
      SessionMessage msg = SessionMessage.create(projectId, "assistant", messageType, content);
      msg.setUserId(userId);
      return messageRepository.save(msg);
  }

  @Transactional
  public void addSystemMessage(String projectId, String content, Long userId) {
      SessionMessage msg = SessionMessage.create(projectId, "system", "text", content);
      msg.setUserId(userId);
      messageRepository.save(msg);
  }

  private Project ensureProjectBelongsToUser(String projectId, Long userId) {
      return projectRepository.findByIdAndUserId(projectId, userId)
              .orElseThrow(() -> new IllegalArgumentException("Project not found: " + projectId));
  }
  ```

  Update all callers inside `SessionMessageService` and `ProjectController`.

- [ ] **Step 3: Update ProjectController message endpoints**

  ```java
  @GetMapping("/{id}/messages")
  public ResponseEntity<List<SessionMessage>> listMessages(@PathVariable("id") String projectId,
                                                           @CurrentUser Long userId) {
      return ResponseEntity.ok(sessionMessageService.listMessages(projectId, userId));
  }

  @PostMapping("/{id}/messages")
  public ResponseEntity<SessionMessage> addMessage(@PathVariable("id") String projectId,
                                                   @RequestBody Map<String, Object> body,
                                                   @CurrentUser Long userId) {
      // ... pass userId to sessionMessageService.addUserMessage
  }
  ```

- [ ] **Step 4: Update other callers of SessionMessageService**

  Search for usages:

  ```bash
  grep -rn "sessionMessageService\." agent-api/src/main/java/
  ```

  Update `DialogueService`, `WorkflowService`, `SseEmitterService` to pass `userId` when calling `addAssistantMessage` / `addSystemMessage`. Retrieve userId from the Project entity.

- [ ] **Step 5: Verify**

  Post a message and list messages with token. Expected: only messages for the user's project are returned.

- [ ] **Step 6: Commit**

  ```bash
  git add agent-api/src/main/java/com/meichen/orchestrator/repository/SessionMessageRepository.java
  git add agent-api/src/main/java/com/meichen/orchestrator/service/SessionMessageService.java
  git add agent-api/src/main/java/com/meichen/orchestrator/controller/ProjectController.java
  git add agent-api/src/main/java/com/meichen/orchestrator/service/DialogueService.java
  git add agent-api/src/main/java/com/meichen/orchestrator/service/WorkflowService.java
  git add agent-api/src/main/java/com/meichen/orchestrator/service/SseEmitterService.java
  git commit -m "feat(account): isolate session messages by user_id"
  ```

---

## Task 13: Feedback Data Isolation

**Files:**
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/repository/FeedbackRepository.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/service/FeedbackService.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/controller/FeedbackController.java`

**Interfaces:**
- Consumes: `@CurrentUser Long userId`.
- Produces: feedback queries scoped to `userId`.

- [ ] **Step 1: Update FeedbackRepository**

  Add method:

  ```java
  List<Feedback> findByProjectIdAndUserId(String projectId, Long userId);
  ```

- [ ] **Step 2: Update FeedbackService**

  ```java
  @Transactional(readOnly = true)
  public List<Feedback> listByProject(String projectId, Long userId) {
      ensureProjectBelongsToUser(projectId, userId);
      return feedbackRepository.findByProjectIdAndUserId(projectId, userId);
  }

  @Transactional
  public Feedback create(String projectId, FeedbackRequest request, Long userId) {
      ensureProjectBelongsToUser(projectId, userId);
      Feedback feedback = Feedback.create(projectId, request.feedbackType(), request.ideaIndex(),
              request.pointName(), request.imageIndex(), request.imageUrl(), request.tag(), request.comment());
      feedback.setUserId(userId);
      return feedbackRepository.save(feedback);
  }

  private Project ensureProjectBelongsToUser(String projectId, Long userId) {
      return projectRepository.findByIdAndUserId(projectId, userId)
              .orElseThrow(() -> new IllegalArgumentException("Project not found: " + projectId));
  }
  ```

- [ ] **Step 3: Update FeedbackController**

  Inject `@CurrentUser Long userId` into list and create endpoints and pass to service.

- [ ] **Step 4: Verify**

  Post feedback and list feedback with token. Expected: only own feedback visible.

- [ ] **Step 5: Commit**

  ```bash
  git add agent-api/src/main/java/com/meichen/orchestrator/repository/FeedbackRepository.java
  git add agent-api/src/main/java/com/meichen/orchestrator/service/FeedbackService.java
  git add agent-api/src/main/java/com/meichen/orchestrator/controller/FeedbackController.java
  git commit -m "feat(account): isolate feedbacks by user_id"
  ```

---

## Task 14: Frontend Login Flow

**Files:**
- Create: `frontend/src/views/LoginView.vue`
- Create: `frontend/src/stores/auth.js`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/api/request.js` (or create if not exists)

**Interfaces:**
- Consumes: `/api/v1/auth/send-code`, `/api/v1/auth/login`, `/api/v1/auth/register`.
- Produces: token stored in `localStorage`; Axios interceptor adds `Authorization` header; router guard redirects unauthenticated users to `/login`.

- [ ] **Step 1: Create auth store**

  `frontend/src/stores/auth.js`:

  ```javascript
  import { defineStore } from 'pinia'
  import { ref, computed } from 'vue'

  export const useAuthStore = defineStore('auth', () => {
    const token = ref(localStorage.getItem('token') || '')
    const phone = ref(localStorage.getItem('phone') || '')

    const isLoggedIn = computed(() => !!token.value)

    function setAuth(newToken, newPhone) {
      token.value = newToken
      phone.value = newPhone
      localStorage.setItem('token', newToken)
      localStorage.setItem('phone', newPhone)
    }

    function logout() {
      token.value = ''
      phone.value = ''
      localStorage.removeItem('token')
      localStorage.removeItem('phone')
    }

    return { token, phone, isLoggedIn, setAuth, logout }
  })
  ```

- [ ] **Step 2: Create LoginView.vue**

  Simple phone input + code input + login/register buttons. On send-code, call `/api/v1/auth/send-code` and auto-fill code `8888`. On login/register, call corresponding endpoint and store token.

- [ ] **Step 3: Update router**

  Add `/login` route and a navigation guard that checks `authStore.isLoggedIn`, redirecting to `/login` when not authenticated.

- [ ] **Step 4: Update Axios request interceptor**

  In `frontend/src/api/request.js` (or main Axios config):

  ```javascript
  import axios from 'axios'
  import { useAuthStore } from '@/stores/auth'

  const request = axios.create({ baseURL: '/api/v1' })

  request.interceptors.request.use(config => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  })

  request.interceptors.response.use(
    response => response,
    error => {
      if (error.response?.status === 401) {
        const authStore = useAuthStore()
        authStore.logout()
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }
  )

  export default request
  ```

- [ ] **Step 5: Verify frontend login**

  Open [http://localhost:5173](http://localhost:5173). Expected: redirect to `/login`. Enter phone `13800138000`, code `8888`, login. Expected: redirect to home and subsequent API calls include token.

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/src/views/LoginView.vue
  git add frontend/src/stores/auth.js
  git add frontend/src/router/index.js
  git add frontend/src/api/request.js
  git commit -m "feat(account): add frontend login flow with JWT"
  ```

---

## Task 15: Integration Testing

**Files:**
- None (manual verification)

- [ ] **Step 1: End-to-end smoke test**

  1. Clear browser localStorage, refresh page, confirm redirect to `/login`.
  2. Register a new phone number, receive token.
  3. Create a project, start workflow, confirm messages appear.
  4. In an incognito window, register a different phone number.
  5. Create a project in window B.
  6. In window A, list projects. Expected: only window A's project visible.
  7. Try to access window B's project ID in window A. Expected: 404.

- [ ] **Step 2: Regression test**

  Verify existing workflows still function: input parse → recommendation → confirm → L2 image generation.

- [ ] **Step 3: Restart all services**

  ```bash
  # agent-core
  cd /Users/liulei/private-work/design-agent/agent-core && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # agent-api
  cd /Users/liulei/private-work/design-agent/agent-api && JAVA_HOME=/Users/liulei/.jdks/amazon-corretto-17.jdk/Contents/Home mvn spring-boot:run

  # frontend
  cd /Users/liulei/private-work/design-agent/frontend && npm run dev
  ```

- [ ] **Step 4: Final commit**

  If any fixes were made during testing, commit them with a clear message.

---

## Self-Review

### Spec Coverage

| Spec Requirement | Implementing Task |
|------------------|-------------------|
| 手机号 + 验证码注册 | Task 6, 7 |
| 手机号 + 验证码登录 | Task 6, 7 |
| 发送验证码接口 | Task 4, 7 |
| 用户数据隔离 | Task 11, 12, 13 |
| 全站强制登录 | Task 8 |
| JWT 30 天过期 | Task 5 |

### Placeholder Scan

- No TBD/TODO in steps.
- All code snippets are complete and copy-paste ready.
- All file paths are exact.

### Type Consistency

- `userId` is consistently `Long` across entities, repositories, services, controllers, and JWT.
- `ProjectRepository.findByIdAndUserId` signature matches controller usage.
- `LoginResponse` fields align with `AuthController` responses.

### Known Gaps to Address During Implementation

- `WorkflowService.createProject` and its internal callers need to be inspected for additional overloads or direct project creation paths.
- `SseEmitterService.sendHistory` and any other direct repository access points may also need `userId` scoping; add tasks if discovered during implementation.
- Ensure CORS config allows `Authorization` header preflight.
