# Admin Dashboard 后端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建独立的 `agent-admin-backend` Spring Boot 模块，提供反馈管理、系统指标、Prompt 模板管理和意图词库管理的 REST API。

**Architecture:** 独立 Spring Boot 应用（端口 8081），直接连接现有 MySQL `meichen` 数据库只读查询。写操作仅限反馈标记处理和 taxonomy YAML 编辑。认证采用配置式 static token。Prompt 模板预览通过 HTTP 调用 agent-core 的 `/api/v1/prompt-preview` 端点。

**Tech Stack:** Spring Boot 3.2.5, Java 17, Spring Data JPA, MySQL Connector, Flyway (validate only), Jackson YAML, WebFlus (HTTP client to agent-core)

## Global Constraints

- Spring Boot 3.2.5 / Java 17（与 agent-api 一致）
- 数据库连接：`jdbc:mysql://localhost:3306/meichen`，用户 `meichen` / `meichen123`
- `spring.jpa.hibernate.ddl-auto=validate`（不修改表结构）
- Flyway `migration-strategy=validate`（不执行迁移）
- 表名：`java_projects`（不是 `projects`）、`feedbacks`、`stage_logs`、`stage_log_stats`
- 没有 `generated_images` 表 — 图像数据从 `feedbacks` 表派生
- 端口：8081（agent-api 用 8080）
- 认证：请求头 `X-Admin-Token`，值从配置文件读取
- agent-core 端点：`http://localhost:8000/api/v1/prompt-preview`
- agent-core 数据目录：`/Users/liulei/private-work/design-agent/agent-core/data`
- intent_taxonomy.yaml 路径：`agent-core/data/intent_taxonomy.yaml`
- prompt 模板目录：`agent-core/data/prompt_templates/`
- Java 测试命令：`cd agent-admin-backend && mvn test -Dtest=<ClassName>#<methodName> -q`
- Java 编译必须启用 `-Xlint:all`

---

## File Structure

```
agent-admin-backend/
├── pom.xml                                    # Maven 配置
├── src/main/java/com/meichen/admin/
│   ├── AdminApplication.java                  # 主启动类
│   ├── config/
│   │   ├── SecurityConfig.java                # Static token 认证过滤器
│   │   └── CorsConfig.java                    # CORS 配置
│   ├── entity/
│   │   ├── FeedbackRead.java                  # feedbacks 表只读实体
│   │   ├── ProjectRead.java                   # java_projects 表只读实体
│   │   ├── StageLogRead.java                  # stage_logs 表只读实体
│   │   └── StageLogStatsRead.java             # stage_log_stats 表只读实体
│   ├── repository/
│   │   ├── FeedbackReadRepository.java         # 反馈分页查询
│   │   ├── ProjectReadRepository.java          # 项目计数查询
│   │   ├── StageLogReadRepository.java         # 阶段耗时聚合查询
│   │   └── StageLogStatsReadRepository.java    # 阶段统计查询
│   ├── dto/
│   │   ├── FeedbackDTO.java                   # 反馈列表响应
│   │   ├── MetricsOverviewDTO.java            # 指标概览响应
│   │   ├── StageDurationDTO.java              # 阶段耗时响应
│   │   ├── FeedbackDistributionDTO.java       # 反馈分布响应
│   │   ├── PromptTemplateInfoDTO.java         # 模板元数据响应
│   │   ├── PromptTemplatePerformanceDTO.java  # 模板效果响应
│   │   ├── PromptPreviewRequestDTO.java       # 模板预览请求
│   │   ├── PromptPreviewResponseDTO.java      # 模板预览响应
│   │   ├── TaxonomyDTO.java                   # taxonomy 完整结构响应
│   │   ├── AliasProposalDTO.java              # alias 提议响应
│   │   └── ProcessFeedbackRequestDTO.java     # 标记处理请求
│   ├── service/
│   │   ├── FeedbackAdminService.java          # 反馈管理业务逻辑
│   │   ├── MetricsAdminService.java           # 指标聚合业务逻辑
│   │   ├── PromptTemplateAdminService.java    # 模板管理业务逻辑
│   │   └── IntentTaxonomyAdminService.java    # 词库管理业务逻辑
│   └── controller/
│       ├── FeedbackAdminController.java       # /api/admin/feedbacks
│       ├── MetricsAdminController.java        # /api/admin/metrics
│       ├── PromptTemplateAdminController.java # /api/admin/prompt-templates
│       └── IntentTaxonomyAdminController.java # /api/admin/intent-taxonomy
├── src/main/resources/
│   └── application.yml                        # 应用配置
└── src/test/java/com/meichen/admin/
    ├── service/
    │   ├── FeedbackAdminServiceTest.java
    │   ├── MetricsAdminServiceTest.java
    │   ├── PromptTemplateAdminServiceTest.java
    │   └── IntentTaxonomyAdminServiceTest.java
    └── controller/
        ├── FeedbackAdminControllerTest.java
        ├── MetricsAdminControllerTest.java
        ├── PromptTemplateAdminControllerTest.java
        └── IntentTaxonomyAdminControllerTest.java
```

---

### Task 1: 后端脚手架

**Files:**
- Create: `agent-admin-backend/pom.xml`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/AdminApplication.java`
- Create: `agent-admin-backend/src/main/resources/application.yml`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/config/SecurityConfig.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/config/CorsConfig.java`
- Create: `agent-admin-backend/src/test/java/com/meichen/admin/AdminApplicationTest.java`

**Interfaces:**
- Produces: `AdminApplication` 主类，端口 8081，static token 认证过滤器

- [ ] **Step 1: 创建 pom.xml**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.5</version>
        <relativePath/>
    </parent>

    <groupId>com.meichen</groupId>
    <artifactId>agent-admin-backend</artifactId>
    <version>0.1.0</version>
    <packaging>jar</packaging>
    <name>agent-admin-backend</name>

    <properties>
        <java.version>17</java.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>com.mysql</groupId>
            <artifactId>mysql-connector-j</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-webflux</artifactId>
        </dependency>
        <dependency>
            <groupId>com.fasterxml.jackson.dataformat</groupId>
            <artifactId>jackson-dataformat-yaml</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
                <configuration>
                    <compilerArgs>
                        <arg>-Xlint:all</arg>
                    </compilerArgs>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

- [ ] **Step 2: 创建 AdminApplication.java**

```java
package com.meichen.admin;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class AdminApplication {
    public static void main(String[] args) {
        SpringApplication.run(AdminApplication.class, args);
    }
}
```

- [ ] **Step 3: 创建 application.yml**

```yaml
server:
  port: 8081

spring:
  datasource:
    url: jdbc:mysql://localhost:3306/meichen
    username: meichen
    password: meichen123
    hikari:
      maximum-pool-size: 10
      minimum-idle: 5
  jpa:
    hibernate:
      ddl-auto: validate
    open-in-view: false
  flyway:
    enabled: false

admin:
  token: ${ADMIN_TOKEN:admin-secret-2026}
  agent-core:
    base-url: http://localhost:8000
    data-dir: ${AGENT_CORE_DATA_DIR:/Users/liulei/private-work/design-agent/agent-core/data}
```

- [ ] **Step 4: 创建 SecurityConfig.java（static token 认证）**

```java
package com.meichen.admin.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collections;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http, AdminTokenFilter adminTokenFilter) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
            .addFilterBefore(adminTokenFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    @Component
    public static class AdminTokenFilter extends OncePerRequestFilter {

        private final String expectedToken;

        public AdminTokenFilter(@Value("${admin.token}") String expectedToken) {
            this.expectedToken = expectedToken;
        }

        @Override
        protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                        FilterChain filterChain) throws ServletException, IOException {
            String token = request.getHeader("X-Admin-Token");
            if (token == null || !token.equals(expectedToken)) {
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                response.setContentType("application/json");
                response.getWriter().write("{\"error\":\"Unauthorized\",\"message\":\"Invalid or missing X-Admin-Token header\"}");
                return;
            }
            filterChain.doFilter(request, response);
        }
    }
}
```

- [ ] **Step 5: 创建 CorsConfig.java**

```java
package com.meichen.admin.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;

@Configuration
public class CorsConfig {

    @Bean
    public CorsFilter corsFilter() {
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        CorsConfiguration config = new CorsConfiguration();
        config.addAllowedOriginPattern("*");
        config.addAllowedHeader("*");
        config.addAllowedMethod("*");
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }
}
```

- [ ] **Step 6: 创建 AdminApplicationTest.java（验证上下文加载）**

```java
package com.meichen.admin;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;

@SpringBootTest
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:h2:mem:testdb",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.datasource.username=sa",
    "spring.datasource.password=",
    "spring.jpa.hibernate.ddl-auto=none",
    "spring.flyway.enabled=false",
    "admin.token=test-token",
    "admin.agent-core.base-url=http://localhost:8000",
    "admin.agent-core.data-dir=/tmp"
})
class AdminApplicationTest {

    @Test
    void contextLoads() {
    }
}
```

- [ ] **Step 7: 运行测试验证上下文加载**

Run: `cd agent-admin-backend && mvn test -Dtest=AdminApplicationTest -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add agent-admin-backend/
git commit -m "feat(admin): scaffold agent-admin-backend Spring Boot module"
```

---

### Task 2: 数据访问层 — 只读实体和仓库

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/entity/FeedbackRead.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/entity/ProjectRead.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/entity/StageLogRead.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/entity/StageLogStatsRead.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/repository/FeedbackReadRepository.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/repository/ProjectReadRepository.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/repository/StageLogReadRepository.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/repository/StageLogStatsReadRepository.java`
- Create: `agent-admin-backend/src/test/java/com/meichen/admin/repository/FeedbackReadRepositoryTest.java`

**Interfaces:**
- Consumes: MySQL `meichen` database tables: `feedbacks`, `java_projects`, `stage_logs`, `stage_log_stats`
- Produces: `FeedbackReadRepository` (分页查询 + 按 feedbackType/category/processed 筛选), `ProjectReadRepository` (计数), `StageLogReadRepository` (聚合查询), `StageLogStatsReadRepository` (统计查询)

- [ ] **Step 1: 创建 FeedbackRead 实体**

```java
package com.meichen.admin.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import java.time.LocalDateTime;

@Entity
@Table(name = "feedbacks")
public class FeedbackRead {

    @Id
    @Column(length = 36)
    private String id;

    @Column(name = "project_id", length = 36)
    private String projectId;

    @Column(name = "feedback_type", length = 20)
    private String feedbackType;

    @Column(name = "category", length = 30)
    private String category;

    @Column(name = "intent_field", length = 50)
    private String intentField;

    @Column(name = "original_value", columnDefinition = "TEXT")
    private String originalValue;

    @Column(name = "corrected_value", columnDefinition = "TEXT")
    private String correctedValue;

    @Column(name = "processed")
    private Boolean processed;

    @Column(name = "notes", columnDefinition = "TEXT")
    private String notes;

    @Column(name = "idea_index")
    private Integer ideaIndex;

    @Column(name = "point_name", length = 100)
    private String pointName;

    @Column(name = "image_index")
    private Integer imageIndex;

    @Column(name = "image_url", length = 500)
    private String imageUrl;

    @Column(name = "prompt_template_version", length = 100)
    private String promptTemplateVersion;

    @Column(name = "tag", length = 50)
    private String tag;

    @Column(name = "comment", columnDefinition = "TEXT")
    private String comment;

    @CreationTimestamp
    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "user_id")
    private Long userId;

    @Column(name = "public_id", length = 32)
    private String publicId;

    public String getId() { return id; }
    public String getProjectId() { return projectId; }
    public String getFeedbackType() { return feedbackType; }
    public String getCategory() { return category; }
    public String getIntentField() { return intentField; }
    public String getOriginalValue() { return originalValue; }
    public String getCorrectedValue() { return correctedValue; }
    public Boolean getProcessed() { return processed; }
    public String getNotes() { return notes; }
    public Integer getIdeaIndex() { return ideaIndex; }
    public String getPointName() { return pointName; }
    public Integer getImageIndex() { return imageIndex; }
    public String getImageUrl() { return imageUrl; }
    public String getPromptTemplateVersion() { return promptTemplateVersion; }
    public String getTag() { return tag; }
    public String getComment() { return comment; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public Long getUserId() { return userId; }
    public String getPublicId() { return publicId; }

    public void setProcessed(Boolean processed) { this.processed = processed; }
    public void setNotes(String notes) { this.notes = notes; }
}
```

- [ ] **Step 2: 创建 ProjectRead 实体**

```java
package com.meichen.admin.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import java.time.LocalDateTime;

@Entity
@Table(name = "java_projects")
public class ProjectRead {

    @Id
    @Column(length = 36)
    private String id;

    @Column(name = "name")
    private String name;

    @Column(name = "status")
    private String status;

    @Column(name = "current_level")
    private String currentLevel;

    @CreationTimestamp
    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "user_id")
    private Long userId;

    public String getId() { return id; }
    public String getName() { return name; }
    public String getStatus() { return status; }
    public String getCurrentLevel() { return currentLevel; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public Long getUserId() { return userId; }
}
```

- [ ] **Step 3: 创建 StageLogRead 实体**

```java
package com.meichen.admin.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "stage_logs")
public class StageLogRead {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "project_id", length = 36)
    private String projectId;

    @Column(name = "stage_name")
    private String stageName;

    @Column(name = "stage_label")
    private String stageLabel;

    @Column(name = "status")
    private String status;

    @Column(name = "duration_ms")
    private Long durationMs;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    public Long getId() { return id; }
    public String getProjectId() { return projectId; }
    public String getStageName() { return stageName; }
    public String getStageLabel() { return stageLabel; }
    public String getStatus() { return status; }
    public Long getDurationMs() { return durationMs; }
    public LocalDateTime getStartedAt() { return startedAt; }
    public LocalDateTime getCompletedAt() { return completedAt; }
}
```

- [ ] **Step 4: 创建 StageLogStatsRead 实体**

```java
package com.meichen.admin.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "stage_log_stats")
public class StageLogStatsRead {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "stage_name")
    private String stageName;

    @Column(name = "window_start")
    private LocalDateTime windowStart;

    @Column(name = "window_end")
    private LocalDateTime windowEnd;

    @Column(name = "avg_ms")
    private Double avgMs;

    @Column(name = "p95_ms")
    private Double p95Ms;

    @Column(name = "max_ms")
    private Long maxMs;

    @Column(name = "success_count")
    private Integer successCount;

    @Column(name = "failed_count")
    private Integer failedCount;

    public String getStageName() { return stageName; }
    public LocalDateTime getWindowStart() { return windowStart; }
    public LocalDateTime getWindowEnd() { return windowEnd; }
    public Double getAvgMs() { return avgMs; }
    public Double getP95Ms() { return p95Ms; }
    public Long getMaxMs() { return maxMs; }
    public Integer getSuccessCount() { return successCount; }
    public Integer getFailedCount() { return failedCount; }
}
```

- [ ] **Step 5: 创建 FeedbackReadRepository**

```java
package com.meichen.admin.repository;

import com.meichen.admin.entity.FeedbackRead;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface FeedbackReadRepository extends JpaRepository<FeedbackRead, String> {

    Page<FeedbackRead> findAllByOrderByCreatedAtDesc(Pageable pageable);

    @Query("SELECT f FROM FeedbackRead f WHERE " +
           "(:feedbackType IS NULL OR f.feedbackType = :feedbackType) AND " +
           "(:category IS NULL OR f.category = :category) AND " +
           "(:processed IS NULL OR f.processed = :processed) " +
           "ORDER BY f.createdAt DESC")
    Page<FeedbackRead> findByFilters(
            @Param("feedbackType") String feedbackType,
            @Param("category") String category,
            @Param("processed") Boolean processed,
            Pageable pageable);

    @Query("SELECT f.promptTemplateVersion, COUNT(f), " +
           "SUM(CASE WHEN f.tag IN ('good', 'like', 'positive') THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN f.tag IN ('bad', 'dislike', 'negative', 'composition', 'quality') THEN 1 ELSE 0 END) " +
           "FROM FeedbackRead f " +
           "WHERE f.promptTemplateVersion IS NOT NULL " +
           "GROUP BY f.promptTemplateVersion")
    List<Object[]> countByPromptTemplateVersion();

    @Query("SELECT f.tag, f.feedbackType, COUNT(f) FROM FeedbackRead f " +
           "GROUP BY f.tag, f.feedbackType ORDER BY COUNT(f) DESC")
    List<Object[]> countByTagAndType();

    long countByFeedbackType(String feedbackType);

    @Query("SELECT f FROM FeedbackRead f WHERE f.feedbackType = 'intent' AND f.processed = false " +
           "ORDER BY f.createdAt DESC")
    List<FeedbackRead> findUnprocessedIntentCorrections();
}
```

- [ ] **Step 6: 创建 ProjectReadRepository**

```java
package com.meichen.admin.repository;

import com.meichen.admin.entity.ProjectRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface ProjectReadRepository extends JpaRepository<ProjectRead, String> {

    long count();

    long countByStatus(String status);

    @Query("SELECT COUNT(DISTINCT f.projectId) FROM FeedbackRead f")
    long countProjectsWithFeedback();
}
```

- [ ] **Step 7: 创建 StageLogReadRepository**

```java
package com.meichen.admin.repository;

import com.meichen.admin.entity.StageLogRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface StageLogReadRepository extends JpaRepository<StageLogRead, Long> {

    @Query("SELECT s.stageName, AVG(s.durationMs), " +
           "PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY s.durationMs), " +
           "MAX(s.durationMs), " +
           "SUM(CASE WHEN s.status = 'SUCCESS' THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN s.status != 'SUCCESS' THEN 1 ELSE 0 END) " +
           "FROM StageLogRead s WHERE s.startedAt >= :since " +
           "GROUP BY s.stageName ORDER BY AVG(s.durationMs) DESC")
    List<Object[]> aggregateByStageNameSince(@Param("since") LocalDateTime since);

    long count();
}
```

- [ ] **Step 8: 创建 StageLogStatsReadRepository**

```java
package com.meichen.admin.repository;

import com.meichen.admin.entity.StageLogStatsRead;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface StageLogStatsReadRepository extends JpaRepository<StageLogStatsRead, Long> {

    List<StageLogStatsRead> findAllByOrderByWindowStartDesc();
}
```

- [ ] **Step 9: 创建 FeedbackReadRepositoryTest（H2 内存数据库测试）**

```java
package com.meichen.admin.repository;

import com.meichen.admin.entity.FeedbackRead;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.test.context.TestPropertySource;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:h2:mem:testdb;MODE=MySQL",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "spring.flyway.enabled=false"
})
class FeedbackReadRepositoryTest {

    @Autowired
    private FeedbackReadRepository repository;

    @Test
    void findByFilters_returnsFilteredResults() {
        FeedbackRead fb = new FeedbackRead();
        fb.setId("test-1");
        fb.setFeedbackType("intent");
        fb.setCategory("intent_correction");
        fb.setProcessed(false);
        repository.save(fb);

        Page<FeedbackRead> result = repository.findByFilters(
            "intent", "intent_correction", false, PageRequest.of(0, 10));

        assertThat(result.getContent()).hasSize(1);
        assertThat(result.getContent().get(0).getId()).isEqualTo("test-1");
    }

    @Test
    void findByFilters_returnsAllWhenNullFilters() {
        FeedbackRead fb = new FeedbackRead();
        fb.setId("test-2");
        fb.setFeedbackType("image");
        fb.setProcessed(true);
        repository.save(fb);

        Page<FeedbackRead> result = repository.findByFilters(
            null, null, null, PageRequest.of(0, 10));

        assertThat(result.getContent()).hasSize(1);
    }

    @Test
    void findUnprocessedIntentCorrections_returnsOnlyUnprocessed() {
        FeedbackRead unprocessed = new FeedbackRead();
        unprocessed.setId("unproc-1");
        unprocessed.setFeedbackType("intent");
        unprocessed.setProcessed(false);
        repository.save(unprocessed);

        FeedbackRead processed = new FeedbackRead();
        processed.setId("proc-1");
        processed.setFeedbackType("intent");
        processed.setProcessed(true);
        repository.save(processed);

        List<FeedbackRead> result = repository.findUnprocessedIntentCorrections();

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getId()).isEqualTo("unproc-1");
    }
}
```

- [ ] **Step 10: 运行测试**

Run: `cd agent-admin-backend && mvn test -Dtest=FeedbackReadRepositoryTest -q`
Expected: 3 tests PASS

- [ ] **Step 11: Commit**

```bash
git add agent-admin-backend/
git commit -m "feat(admin): add read-only JPA entities and repositories with pagination"
```

---

### Task 3: 反馈管理 API

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/FeedbackDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/ProcessFeedbackRequestDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/service/FeedbackAdminService.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/controller/FeedbackAdminController.java`
- Create: `agent-admin-backend/src/test/java/com/meichen/admin/service/FeedbackAdminServiceTest.java`
- Create: `agent-admin-backend/src/test/java/com/meichen/admin/controller/FeedbackAdminControllerTest.java`

**Interfaces:**
- Consumes: `FeedbackReadRepository` (from Task 2)
- Produces: `GET /api/admin/feedbacks` (分页 + 筛选), `POST /api/admin/feedbacks/{id}/process` (标记处理)

- [ ] **Step 1: 创建 FeedbackDTO**

```java
package com.meichen.admin.dto;

import java.time.LocalDateTime;

public record FeedbackDTO(
    String id,
    String projectId,
    String feedbackType,
    String category,
    String intentField,
    String originalValue,
    String correctedValue,
    Boolean processed,
    String notes,
    Integer ideaIndex,
    String pointName,
    Integer imageIndex,
    String imageUrl,
    String promptTemplateVersion,
    String tag,
    String comment,
    LocalDateTime createdAt,
    String publicId
) {}
```

- [ ] **Step 2: 创建 ProcessFeedbackRequestDTO**

```java
package com.meichen.admin.dto;

public record ProcessFeedbackRequestDTO(
    String notes
) {}
```

- [ ] **Step 3: 创建 FeedbackAdminService**

```java
package com.meichen.admin.service;

import com.meichen.admin.dto.FeedbackDTO;
import com.meichen.admin.dto.ProcessFeedbackRequestDTO;
import com.meichen.admin.entity.FeedbackRead;
import com.meichen.admin.repository.FeedbackReadRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class FeedbackAdminService {

    private final FeedbackReadRepository repository;

    public FeedbackAdminService(FeedbackReadRepository repository) {
        this.repository = repository;
    }

    public Page<FeedbackDTO> listFeedbacks(String feedbackType, String category, Boolean processed, Pageable pageable) {
        if (feedbackType == null && category == null && processed == null) {
            return repository.findAllByOrderByCreatedAtDesc(pageable).map(this::toDTO);
        }
        return repository.findByFilters(feedbackType, category, processed, pageable).map(this::toDTO);
    }

    @Transactional
    public FeedbackDTO processFeedback(String id, ProcessFeedbackRequestDTO request) {
        FeedbackRead feedback = repository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Feedback not found: " + id));
        feedback.setProcessed(true);
        if (request != null && request.notes() != null) {
            feedback.setNotes(request.notes());
        }
        repository.save(feedback);
        return toDTO(feedback);
    }

    private FeedbackDTO toDTO(FeedbackRead f) {
        return new FeedbackDTO(
            f.getId(), f.getProjectId(), f.getFeedbackType(), f.getCategory(),
            f.getIntentField(), f.getOriginalValue(), f.getCorrectedValue(),
            f.getProcessed(), f.getNotes(), f.getIdeaIndex(), f.getPointName(),
            f.getImageIndex(), f.getImageUrl(), f.getPromptTemplateVersion(),
            f.getTag(), f.getComment(), f.getCreatedAt(), f.getPublicId()
        );
    }
}
```

- [ ] **Step 4: 创建 FeedbackAdminController**

```java
package com.meichen.admin.controller;

import com.meichen.admin.dto.FeedbackDTO;
import com.meichen.admin.dto.ProcessFeedbackRequestDTO;
import com.meichen.admin.service.FeedbackAdminService;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin/feedbacks")
public class FeedbackAdminController {

    private final FeedbackAdminService service;

    public FeedbackAdminController(FeedbackAdminService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<Page<FeedbackDTO>> listFeedbacks(
            @RequestParam(required = false) String feedbackType,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) Boolean processed,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<FeedbackDTO> result = service.listFeedbacks(feedbackType, category, processed, PageRequest.of(page, size));
        return ResponseEntity.ok(result);
    }

    @PostMapping("/{id}/process")
    public ResponseEntity<FeedbackDTO> processFeedback(
            @PathVariable String id,
            @RequestBody(required = false) ProcessFeedbackRequestDTO request) {
        return ResponseEntity.ok(service.processFeedback(id, request));
    }
}
```

- [ ] **Step 5: 创建 FeedbackAdminServiceTest**

```java
package com.meichen.admin.service;

import com.meichen.admin.dto.FeedbackDTO;
import com.meichen.admin.dto.ProcessFeedbackRequestDTO;
import com.meichen.admin.entity.FeedbackRead;
import com.meichen.admin.repository.FeedbackReadRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class FeedbackAdminServiceTest {

    private FeedbackReadRepository repository;
    private FeedbackAdminService service;

    @BeforeEach
    void setUp() {
        repository = mock(FeedbackReadRepository.class);
        service = new FeedbackAdminService(repository);
    }

    @Test
    void listFeedbacks_noFilters_usesFindAll() {
        FeedbackRead fb = new FeedbackRead();
        fb.setId("fb-1");
        fb.setFeedbackType("image");
        fb.setProcessed(false);
        Page<FeedbackRead> page = new PageImpl<>(List.of(fb));
        when(repository.findAllByOrderByCreatedAtDesc(any())).thenReturn(page);

        Page<FeedbackDTO> result = service.listFeedbacks(null, null, null, PageRequest.of(0, 10));

        assertThat(result.getContent()).hasSize(1);
        assertThat(result.getContent().get(0).id()).isEqualTo("fb-1");
        verify(repository).findAllByOrderByCreatedAtDesc(any());
    }

    @Test
    void listFeedbacks_withFilters_usesFindByFilters() {
        FeedbackRead fb = new FeedbackRead();
        fb.setId("fb-2");
        fb.setFeedbackType("intent");
        fb.setProcessed(false);
        Page<FeedbackRead> page = new PageImpl<>(List.of(fb));
        when(repository.findByFilters(eq("intent"), isNull(), eq(false), any())).thenReturn(page);

        Page<FeedbackDTO> result = service.listFeedbacks("intent", null, false, PageRequest.of(0, 10));

        assertThat(result.getContent()).hasSize(1);
        verify(repository).findByFilters(eq("intent"), isNull(), eq(false), any());
    }

    @Test
    void processFeedback_marksProcessed_andSetsNotes() {
        FeedbackRead fb = new FeedbackRead();
        fb.setId("fb-3");
        fb.setProcessed(false);
        when(repository.findById("fb-3")).thenReturn(Optional.of(fb));
        when(repository.save(any())).thenReturn(fb);

        FeedbackDTO result = service.processFeedback("fb-3", new ProcessFeedbackRequestDTO("reviewed"));

        assertThat(result.processed()).isTrue();
        assertThat(fb.getProcessed()).isTrue();
        assertThat(fb.getNotes()).isEqualTo("reviewed");
    }

    @Test
    void processFeedback_throwsWhenNotFound() {
        when(repository.findById("nonexistent")).thenReturn(Optional.empty());
        try {
            service.processFeedback("nonexistent", null);
            assert false : "Should have thrown";
        } catch (IllegalArgumentException e) {
            assertThat(e.getMessage()).contains("Feedback not found");
        }
    }
}
```

- [ ] **Step 6: 运行测试**

Run: `cd agent-admin-backend && mvn test -Dtest=FeedbackAdminServiceTest -q`
Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add agent-admin-backend/
git commit -m "feat(admin): add feedback management API with pagination and process endpoint"
```

---

### Task 4: 系统指标 API

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/MetricsOverviewDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/StageDurationDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/FeedbackDistributionDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/service/MetricsAdminService.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/controller/MetricsAdminController.java`
- Create: `agent-admin-backend/src/test/java/com/meichen/admin/service/MetricsAdminServiceTest.java`

**Interfaces:**
- Consumes: `ProjectReadRepository`, `FeedbackReadRepository`, `StageLogReadRepository` (from Task 2)
- Produces: `GET /api/admin/metrics/overview`, `GET /api/admin/metrics/stages`, `GET /api/admin/metrics/feedback-distribution`

- [ ] **Step 1: 创建 DTO 类**

```java
package com.meichen.admin.dto;

public record MetricsOverviewDTO(
    long projectCount,
    long feedbackCount,
    long imageFeedbackCount,
    long intentCorrectionCount,
    long stageLogCount,
    long projectsWithFeedbackCount
) {}
```

```java
package com.meichen.admin.dto;

public record StageDurationDTO(
    String stageName,
    Double avgMs,
    Double p95Ms,
    Long maxMs,
    Integer successCount,
    Integer failedCount
) {}
```

```java
package com.meichen.admin.dto;

public record FeedbackDistributionDTO(
    String tag,
    String feedbackType,
    Long count
) {}
```

- [ ] **Step 2: 创建 MetricsAdminService**

```java
package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.meichen.admin.repository.ProjectReadRepository;
import com.meichen.admin.repository.StageLogReadRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class MetricsAdminService {

    private final ProjectReadRepository projectRepo;
    private final FeedbackReadRepository feedbackRepo;
    private final StageLogReadRepository stageLogRepo;

    public MetricsAdminService(ProjectReadRepository projectRepo,
                               FeedbackReadRepository feedbackRepo,
                               StageLogReadRepository stageLogRepo) {
        this.projectRepo = projectRepo;
        this.feedbackRepo = feedbackRepo;
        this.stageLogRepo = stageLogRepo;
    }

    public MetricsOverviewDTO getOverview() {
        return new MetricsOverviewDTO(
            projectRepo.count(),
            feedbackRepo.count(),
            feedbackRepo.countByFeedbackType("image"),
            feedbackRepo.countByFeedbackType("intent"),
            stageLogRepo.count(),
            projectRepo.countProjectsWithFeedback()
        );
    }

    public List<StageDurationDTO> getStageDurations(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = stageLogRepo.aggregateByStageNameSince(since);
        return rows.stream().map(row -> new StageDurationDTO(
            (String) row[0],
            row[1] != null ? ((Number) row[1]).doubleValue() : null,
            row[2] != null ? ((Number) row[2]).doubleValue() : null,
            row[3] != null ? ((Number) row[3]).longValue() : null,
            row[4] != null ? ((Number) row[4]).intValue() : 0,
            row[5] != null ? ((Number) row[5]).intValue() : 0
        )).toList();
    }

    public List<FeedbackDistributionDTO> getFeedbackDistribution() {
        List<Object[]> rows = feedbackRepo.countByTagAndType();
        return rows.stream().map(row -> new FeedbackDistributionDTO(
            (String) row[0],
            (String) row[1],
            ((Number) row[2]).longValue()
        )).toList();
    }
}
```

- [ ] **Step 3: 创建 MetricsAdminController**

```java
package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.MetricsAdminService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/metrics")
public class MetricsAdminController {

    private final MetricsAdminService service;

    public MetricsAdminController(MetricsAdminService service) {
        this.service = service;
    }

    @GetMapping("/overview")
    public ResponseEntity<MetricsOverviewDTO> getOverview() {
        return ResponseEntity.ok(service.getOverview());
    }

    @GetMapping("/stages")
    public ResponseEntity<List<StageDurationDTO>> getStageDurations(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(service.getStageDurations(hours));
    }

    @GetMapping("/feedback-distribution")
    public ResponseEntity<List<FeedbackDistributionDTO>> getFeedbackDistribution() {
        return ResponseEntity.ok(service.getFeedbackDistribution());
    }
}
```

- [ ] **Step 4: 创建 MetricsAdminServiceTest**

```java
package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.meichen.admin.repository.ProjectReadRepository;
import com.meichen.admin.repository.StageLogReadRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class MetricsAdminServiceTest {

    private ProjectReadRepository projectRepo;
    private FeedbackReadRepository feedbackRepo;
    private StageLogReadRepository stageLogRepo;
    private MetricsAdminService service;

    @BeforeEach
    void setUp() {
        projectRepo = mock(ProjectReadRepository.class);
        feedbackRepo = mock(FeedbackReadRepository.class);
        stageLogRepo = mock(StageLogReadRepository.class);
        service = new MetricsAdminService(projectRepo, feedbackRepo, stageLogRepo);
    }

    @Test
    void getOverview_aggregatesCounts() {
        when(projectRepo.count()).thenReturn(10L);
        when(feedbackRepo.count()).thenReturn(50L);
        when(feedbackRepo.countByFeedbackType("image")).thenReturn(30L);
        when(feedbackRepo.countByFeedbackType("intent")).thenReturn(20L);
        when(stageLogRepo.count()).thenReturn(200L);
        when(projectRepo.countProjectsWithFeedback()).thenReturn(8L);

        MetricsOverviewDTO result = service.getOverview();

        assertThat(result.projectCount()).isEqualTo(10);
        assertThat(result.feedbackCount()).isEqualTo(50);
        assertThat(result.imageFeedbackCount()).isEqualTo(30);
        assertThat(result.intentCorrectionCount()).isEqualTo(20);
        assertThat(result.stageLogCount()).isEqualTo(200);
        assertThat(result.projectsWithFeedbackCount()).isEqualTo(8);
    }

    @Test
    void getStageDurations_mapsRows() {
        Object[] row = {"concept_design", 5000.0, 8000.0, 12000L, 5, 1};
        when(stageLogRepo.aggregateByStageNameSince(any())).thenReturn(List.of(row));

        List<StageDurationDTO> result = service.getStageDurations(24);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).stageName()).isEqualTo("concept_design");
        assertThat(result.get(0).avgMs()).isEqualTo(5000.0);
        assertThat(result.get(0).p95Ms()).isEqualTo(8000.0);
        assertThat(result.get(0).maxMs()).isEqualTo(12000L);
        assertThat(result.get(0).successCount()).isEqualTo(5);
        assertThat(result.get(0).failedCount()).isEqualTo(1);
    }

    @Test
    void getFeedbackDistribution_mapsRows() {
        Object[] row = {"composition", "image", 15L};
        when(feedbackRepo.countByTagAndType()).thenReturn(List.of(row));

        List<FeedbackDistributionDTO> result = service.getFeedbackDistribution();

        assertThat(result).hasSize(1);
        assertThat(result.get(0).tag()).isEqualTo("composition");
        assertThat(result.get(0).feedbackType()).isEqualTo("image");
        assertThat(result.get(0).count()).isEqualTo(15L);
    }
}
```

- [ ] **Step 5: 运行测试**

Run: `cd agent-admin-backend && mvn test -Dtest=MetricsAdminServiceTest -q`
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add agent-admin-backend/
git commit -m "feat(admin): add system metrics API with overview, stage durations, and feedback distribution"
```

---

### Task 5: Prompt 模板管理 API

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/PromptTemplateInfoDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/PromptTemplatePerformanceDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/PromptPreviewRequestDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/PromptPreviewResponseDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/service/PromptTemplateAdminService.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/controller/PromptTemplateAdminController.java`
- Create: `agent-admin-backend/src/test/java/com/meichen/admin/service/PromptTemplateAdminServiceTest.java`

**Interfaces:**
- Consumes: `FeedbackReadRepository.countByPromptTemplateVersion()` (from Task 2), agent-core `/api/v1/prompt-preview` HTTP 端点, `agent-core/data/prompt_templates/*.yaml` 文件系统
- Produces: `GET /api/admin/prompt-templates`, `GET /api/admin/prompt-templates/{name}/performance`, `POST /api/admin/prompt-templates/preview`

- [ ] **Step 1: 创建 DTO 类**

```java
package com.meichen.admin.dto;

public record PromptTemplateInfoDTO(
    String name,
    String spaceType,
    String version
) {}
```

```java
package com.meichen.admin.dto;

public record PromptTemplatePerformanceDTO(
    String promptTemplateVersion,
    long totalCount,
    long positiveCount,
    long negativeCount
) {}
```

```java
package com.meichen.admin.dto;

public record PromptPreviewRequestDTO(
    String theme,
    String spaceType,
    Integer budget,
    String style
) {}
```

```java
package com.meichen.admin.dto;

public record PromptPreviewResponseDTO(
    String positivePrompt,
    String negativePrompt,
    String templateName,
    String templateVersion
) {}
```

- [ ] **Step 2: 创建 PromptTemplateAdminService**

```java
package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class PromptTemplateAdminService {

    private final FeedbackReadRepository feedbackRepo;
    private final WebClient agentCoreClient;
    private final String dataDir;
    private final ObjectMapper yamlMapper;

    public PromptTemplateAdminService(
            FeedbackReadRepository feedbackRepo,
            @Value("${admin.agent-core.base-url}") String agentCoreBaseUrl,
            @Value("${admin.agent-core.data-dir}") String dataDir) {
        this.feedbackRepo = feedbackRepo;
        this.agentCoreClient = WebClient.builder().baseUrl(agentCoreBaseUrl).build();
        this.dataDir = dataDir;
        this.yamlMapper = new YAMLMapper();
    }

    public List<PromptTemplateInfoDTO> listTemplates() {
        List<PromptTemplateInfoDTO> templates = new ArrayList<>();
        File templateDir = new File(dataDir, "prompt_templates");
        File[] files = templateDir.listFiles((dir, name) -> name.endsWith(".yaml") || name.endsWith(".yml"));
        if (files == null) return templates;
        for (File file : files) {
            try {
                @SuppressWarnings("unchecked")
                Map<String, Object> yaml = yamlMapper.readValue(file, Map.class);
                String name = file.getName().replace(".yaml", "").replace(".yml", "");
                String spaceType = (String) yaml.getOrDefault("space_type", "");
                String version = (String) yaml.getOrDefault("version", "1.0");
                templates.add(new PromptTemplateInfoDTO(name, spaceType, version));
            } catch (Exception e) {
                templates.add(new PromptTemplateInfoDTO(
                    file.getName().replace(".yaml", "").replace(".yml", ""), "unknown", "unknown"));
            }
        }
        return templates;
    }

    public List<PromptTemplatePerformanceDTO> getPerformance(String templateName) {
        List<Object[]> rows = feedbackRepo.countByPromptTemplateVersion();
        return rows.stream()
            .map(row -> new PromptTemplatePerformanceDTO(
                (String) row[0],
                ((Number) row[1]).longValue(),
                ((Number) row[2]).longValue(),
                ((Number) row[3]).longValue()
            ))
            .filter(dto -> templateName == null || dto.promptTemplateVersion().contains(templateName))
            .toList();
    }

    public PromptPreviewResponseDTO previewPrompt(PromptPreviewRequestDTO request) {
        return agentCoreClient.post()
            .uri("/api/v1/prompt-preview")
            .bodyValue(Map.of(
                "theme", request.theme() != null ? request.theme() : "",
                "space_type", request.spaceType() != null ? request.spaceType() : "",
                "budget", request.budget() != null ? request.budget() : 0,
                "style", request.style() != null ? request.style() : ""
            ))
            .retrieve()
            .bodyToMono(PromptPreviewResponseDTO.class)
            .block();
    }
}
```

- [ ] **Step 3: 创建 PromptTemplateAdminController**

```java
package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.PromptTemplateAdminService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/prompt-templates")
public class PromptTemplateAdminController {

    private final PromptTemplateAdminService service;

    public PromptTemplateAdminController(PromptTemplateAdminService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<List<PromptTemplateInfoDTO>> listTemplates() {
        return ResponseEntity.ok(service.listTemplates());
    }

    @GetMapping("/{name}/performance")
    public ResponseEntity<List<PromptTemplatePerformanceDTO>> getPerformance(
            @PathVariable String name) {
        return ResponseEntity.ok(service.getPerformance(name));
    }

    @PostMapping("/preview")
    public ResponseEntity<PromptPreviewResponseDTO> previewPrompt(
            @RequestBody PromptPreviewRequestDTO request) {
        return ResponseEntity.ok(service.previewPrompt(request));
    }
}
```

- [ ] **Step 4: 创建 PromptTemplateAdminServiceTest**

```java
package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.FeedbackReadRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.File;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class PromptTemplateAdminServiceTest {

    private FeedbackReadRepository feedbackRepo;
    private PromptTemplateAdminService service;

    @TempDir
    File tempDir;

    @BeforeEach
    void setUp() throws Exception {
        feedbackRepo = mock(FeedbackReadRepository.class);
        File templateDir = new File(tempDir, "prompt_templates");
        templateDir.mkdirs();
        File templateFile = new File(templateDir, "shopping_mall_atrium.yaml");
        templateFile.createNewFile();
        java.nio.file.Files.writeString(templateFile.toPath(),
            "space_type: \"购物中心中庭\"\nversion: \"1.0\"\n");

        service = new PromptTemplateAdminService(feedbackRepo, "http://localhost:8000", tempDir.getAbsolutePath());
    }

    @Test
    void listTemplates_readsYamlFiles() {
        List<PromptTemplateInfoDTO> result = service.listTemplates();

        assertThat(result).hasSize(1);
        assertThat(result.get(0).name()).isEqualTo("shopping_mall_atrium");
        assertThat(result.get(0).spaceType()).isEqualTo("购物中心中庭");
        assertThat(result.get(0).version()).isEqualTo("1.0");
    }

    @Test
    void getPerformance_mapsRepositoryRows() {
        Object[] row = {"atrium-v1", 10L, 7L, 3L};
        when(feedbackRepo.countByPromptTemplateVersion()).thenReturn(List.of(row));

        List<PromptTemplatePerformanceDTO> result = service.getPerformance(null);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).promptTemplateVersion()).isEqualTo("atrium-v1");
        assertThat(result.get(0).totalCount()).isEqualTo(10);
        assertThat(result.get(0).positiveCount()).isEqualTo(7);
        assertThat(result.get(0).negativeCount()).isEqualTo(3);
    }

    @Test
    void getPerformance_filtersByTemplateName() {
        Object[] row1 = {"atrium-v1", 10L, 7L, 3L};
        Object[] row2 = {"generic-v1", 5L, 4L, 1L};
        when(feedbackRepo.countByPromptTemplateVersion()).thenReturn(List.of(row1, row2));

        List<PromptTemplatePerformanceDTO> result = service.getPerformance("atrium");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).promptTemplateVersion()).isEqualTo("atrium-v1");
    }
}
```

- [ ] **Step 5: 运行测试**

Run: `cd agent-admin-backend && mvn test -Dtest=PromptTemplateAdminServiceTest -q`
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add agent-admin-backend/
git commit -m "feat(admin): add prompt template management API with list, performance, and preview"
```

---

### Task 6: 意图词库管理 API

**Files:**
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/TaxonomyDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/AliasProposalDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/ApplyAliasRequestDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/dto/AddAliasRequestDTO.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/service/IntentTaxonomyAdminService.java`
- Create: `agent-admin-backend/src/main/java/com/meichen/admin/controller/IntentTaxonomyAdminController.java`
- Create: `agent-admin-backend/src/test/java/com/meichen/admin/service/IntentTaxonomyAdminServiceTest.java`

**Interfaces:**
- Consumes: `FeedbackReadRepository.findUnprocessedIntentCorrections()` (from Task 2), `agent-core/data/intent_taxonomy.yaml` 文件系统
- Produces: `GET /api/admin/intent-taxonomy`, `GET /api/admin/intent-taxonomy/alias-proposals`, `POST /api/admin/intent-taxonomy/alias-proposals/apply`, `POST /api/admin/intent-taxonomy/aliases`

- [ ] **Step 1: 创建 DTO 类**

```java
package com.meichen.admin.dto;

import java.util.List;
import java.util.Map;

public record TaxonomyDTO(
    String version,
    List<TaxonomyEntry> spaceTypes,
    List<TaxonomyEntry> points,
    List<TaxonomyEntry> budgetLevels,
    List<TaxonomyEntry> styles,
    List<TaxonomyEntry> materials,
    Map<String, Object> fieldDefaults
) {
    public record TaxonomyEntry(String name, List<String> aliases) {}
}
```

```java
package com.meichen.admin.dto;

public record AliasProposalDTO(
    String intentField,
    String originalValue,
    String correctedValue,
    long occurrenceCount,
    String status
) {}
```

```java
package com.meichen.admin.dto;

public record ApplyAliasRequestDTO(
    String intentField,
    String originalValue,
    String correctedValue
) {}
```

```java
package com.meichen.admin.dto;

public record AddAliasRequestDTO(
    String section,
    String canonicalName,
    String alias
) {}
```

- [ ] **Step 2: 创建 IntentTaxonomyAdminService**

```java
package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.entity.FeedbackRead;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.File;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class IntentTaxonomyAdminService {

    private final FeedbackReadRepository feedbackRepo;
    private final String dataDir;
    private final ObjectMapper yamlMapper;

    public IntentTaxonomyAdminService(
            FeedbackReadRepository feedbackRepo,
            @Value("${admin.agent-core.data-dir}") String dataDir) {
        this.feedbackRepo = feedbackRepo;
        this.dataDir = dataDir;
        this.yamlMapper = new YAMLMapper();
    }

    @SuppressWarnings("unchecked")
    public TaxonomyDTO getTaxonomy() {
        File file = new File(dataDir, "intent_taxonomy.yaml");
        try {
            Map<String, Object> yaml = yamlMapper.readValue(file, Map.class);
            return new TaxonomyDTO(
                (String) yaml.getOrDefault("version", "1.0"),
                parseEntries(yaml.get("space_types")),
                parseEntries(yaml.get("points")),
                parseEntries(yaml.get("budget_levels")),
                parseEntries(yaml.get("styles")),
                parseEntries(yaml.get("materials")),
                (Map<String, Object>) yaml.getOrDefault("field_defaults", Map.of())
            );
        } catch (Exception e) {
            throw new RuntimeException("Failed to read taxonomy: " + e.getMessage(), e);
        }
    }

    @SuppressWarnings("unchecked")
    private List<TaxonomyDTO.TaxonomyEntry> parseEntries(Object raw) {
        if (!(raw instanceof List<?> list)) return List.of();
        return list.stream()
            .filter(item -> item instanceof Map<?, ?>)
            .map(item -> {
                Map<String, Object> map = (Map<String, Object>) item;
                String name = (String) map.get("name");
                List<String> aliases = (List<String>) map.getOrDefault("aliases", List.of());
                return new TaxonomyDTO.TaxonomyEntry(name, aliases != null ? aliases : List.of());
            })
            .toList();
    }

    public List<AliasProposalDTO> getAliasProposals() {
        List<FeedbackRead> unprocessed = feedbackRepo.findUnprocessedIntentCorrections();
        Map<String, Long> grouped = unprocessed.stream()
            .filter(f -> f.getOriginalValue() != null && f.getCorrectedValue() != null)
            .collect(Collectors.groupingBy(
                f -> f.getIntentField() + "|" + f.getOriginalValue() + "|" + f.getCorrectedValue(),
                Collectors.counting()
            ));
        return grouped.entrySet().stream()
            .filter(e -> e.getValue() >= 3)
            .map(e -> {
                String[] parts = e.getKey().split("\\|", 3);
                return new AliasProposalDTO(parts[0], parts[1], parts[2], e.getValue(), "pending");
            })
            .toList();
    }

    @SuppressWarnings("unchecked")
    public void applyAlias(ApplyAliasRequestDTO request) {
        File file = new File(dataDir, "intent_taxonomy.yaml");
        try {
            Map<String, Object> yaml = yamlMapper.readValue(file, Map.class);
            String sectionKey = mapFieldToSection(request.intentField());
            List<Map<String, Object>> entries = (List<Map<String, Object>>) yaml.get(sectionKey);
            if (entries == null) throw new IllegalArgumentException("Unknown section: " + sectionKey);
            boolean found = false;
            for (Map<String, Object> entry : entries) {
                if (request.correctedValue().equals(entry.get("name"))) {
                    List<String> aliases = (List<String>) entry.getOrDefault("aliases", new ArrayList<>());
                    if (!aliases.contains(request.originalValue())) {
                        aliases.add(request.originalValue());
                        entry.put("aliases", aliases);
                    }
                    found = true;
                    break;
                }
            }
            if (!found) throw new IllegalArgumentException("Canonical value not found: " + request.correctedValue());
            yamlMapper.writeValue(file, yaml);
        } catch (Exception e) {
            throw new RuntimeException("Failed to apply alias: " + e.getMessage(), e);
        }
    }

    @SuppressWarnings("unchecked")
    public void addAlias(AddAliasRequestDTO request) {
        File file = new File(dataDir, "intent_taxonomy.yaml");
        try {
            Map<String, Object> yaml = yamlMapper.readValue(file, Map.class);
            List<Map<String, Object>> entries = (List<Map<String, Object>>) yaml.get(request.section());
            if (entries == null) throw new IllegalArgumentException("Unknown section: " + request.section());
            boolean found = false;
            for (Map<String, Object> entry : entries) {
                if (request.canonicalName().equals(entry.get("name"))) {
                    List<String> aliases = (List<String>) entry.getOrDefault("aliases", new ArrayList<>());
                    if (!aliases.contains(request.alias())) {
                        aliases.add(request.alias());
                        entry.put("aliases", aliases);
                    }
                    found = true;
                    break;
                }
            }
            if (!found) throw new IllegalArgumentException("Canonical name not found: " + request.canonicalName());
            yamlMapper.writeValue(file, yaml);
        } catch (Exception e) {
            throw new RuntimeException("Failed to add alias: " + e.getMessage(), e);
        }
    }

    private String mapFieldToSection(String intentField) {
        return switch (intentField) {
            case "space_type" -> "space_types";
            case "budget", "budget_level" -> "budget_levels";
            case "style" -> "styles";
            default -> throw new IllegalArgumentException("Cannot map field: " + intentField);
        };
    }
}
```

- [ ] **Step 3: 创建 IntentTaxonomyAdminController**

```java
package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.IntentTaxonomyAdminService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/intent-taxonomy")
public class IntentTaxonomyAdminController {

    private final IntentTaxonomyAdminService service;

    public IntentTaxonomyAdminController(IntentTaxonomyAdminService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<TaxonomyDTO> getTaxonomy() {
        return ResponseEntity.ok(service.getTaxonomy());
    }

    @GetMapping("/alias-proposals")
    public ResponseEntity<List<AliasProposalDTO>> getAliasProposals() {
        return ResponseEntity.ok(service.getAliasProposals());
    }

    @PostMapping("/alias-proposals/apply")
    public ResponseEntity<Void> applyAlias(@RequestBody ApplyAliasRequestDTO request) {
        service.applyAlias(request);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/aliases")
    public ResponseEntity<Void> addAlias(@RequestBody AddAliasRequestDTO request) {
        service.addAlias(request);
        return ResponseEntity.ok().build();
    }
}
```

- [ ] **Step 4: 创建 IntentTaxonomyAdminServiceTest**

```java
package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.entity.FeedbackRead;
import com.meichen.admin.repository.FeedbackReadRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.File;
import java.nio.file.Files;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class IntentTaxonomyAdminServiceTest {

    private FeedbackReadRepository feedbackRepo;
    private IntentTaxonomyAdminService service;

    @TempDir
    File tempDir;

    @BeforeEach
    void setUp() throws Exception {
        feedbackRepo = mock(FeedbackReadRepository.class);
        File taxonomyFile = new File(tempDir, "intent_taxonomy.yaml");
        Files.writeString(taxonomyFile.toPath(),
            "version: \"1.0\"\n" +
            "space_types:\n" +
            "  - name: \"购物中心中庭\"\n" +
            "    aliases: [\"商场中庭\", \"中庭\"]\n" +
            "styles:\n" +
            "  - name: \"现代\"\n" +
            "    aliases: [\"modern\"]\n"
        );
        service = new IntentTaxonomyAdminService(feedbackRepo, tempDir.getAbsolutePath());
    }

    @Test
    void getTaxonomy_readsYaml() {
        TaxonomyDTO result = service.getTaxonomy();

        assertThat(result.version()).isEqualTo("1.0");
        assertThat(result.spaceTypes()).hasSize(1);
        assertThat(result.spaceTypes().get(0).name()).isEqualTo("购物中心中庭");
        assertThat(result.spaceTypes().get(0).aliases()).containsExactly("商场中庭", "中庭");
    }

    @Test
    void getAliasProposals_groupsByCorrection() {
        FeedbackRead fb1 = new FeedbackRead();
        fb1.setIntentField("space_type");
        fb1.setOriginalValue("商厦中庭");
        fb1.setCorrectedValue("购物中心中庭");
        FeedbackRead fb2 = new FeedbackRead();
        fb2.setIntentField("space_type");
        fb2.setOriginalValue("商厦中庭");
        fb2.setCorrectedValue("购物中心中庭");
        FeedbackRead fb3 = new FeedbackRead();
        fb3.setIntentField("space_type");
        fb3.setOriginalValue("商厦中庭");
        fb3.setCorrectedValue("购物中心中庭");
        when(feedbackRepo.findUnprocessedIntentCorrections()).thenReturn(List.of(fb1, fb2, fb3));

        List<AliasProposalDTO> result = service.getAliasProposals();

        assertThat(result).hasSize(1);
        assertThat(result.get(0).originalValue()).isEqualTo("商厦中庭");
        assertThat(result.get(0).correctedValue()).isEqualTo("购物中心中庭");
        assertThat(result.get(0).occurrenceCount()).isEqualTo(3);
    }

    @Test
    void getAliasProposals_filtersBelowThreshold() {
        FeedbackRead fb1 = new FeedbackRead();
        fb1.setIntentField("space_type");
        fb1.setOriginalValue("商厦中庭");
        fb1.setCorrectedValue("购物中心中庭");
        FeedbackRead fb2 = new FeedbackRead();
        fb2.setIntentField("space_type");
        fb2.setOriginalValue("商场");
        fb2.setCorrectedValue("购物中心中庭");
        when(feedbackRepo.findUnprocessedIntentCorrections()).thenReturn(List.of(fb1, fb2));

        List<AliasProposalDTO> result = service.getAliasProposals();

        assertThat(result).isEmpty();
    }

    @Test
    void applyAlias_addsAliasToYaml() {
        service.applyAlias(new ApplyAliasRequestDTO("space_type", "商厦中庭", "购物中心中庭"));

        TaxonomyDTO result = service.getTaxonomy();
        assertThat(result.spaceTypes().get(0).aliases()).contains("商厦中庭");
    }

    @Test
    void addAlias_addsAliasManually() {
        service.addAlias(new AddAliasRequestDTO("styles", "现代", "modern2"));

        TaxonomyDTO result = service.getTaxonomy();
        assertThat(result.styles().get(0).aliases()).contains("modern2");
    }

    @Test
    void addAlias_throwsForUnknownCanonical() {
        try {
            service.addAlias(new AddAliasRequestDTO("styles", "不存在", "alias"));
            assert false : "Should have thrown";
        } catch (IllegalArgumentException e) {
            assertThat(e.getMessage()).contains("Canonical name not found");
        }
    }
}
```

- [ ] **Step 5: 运行测试**

Run: `cd agent-admin-backend && mvn test -Dtest=IntentTaxonomyAdminServiceTest -q`
Expected: 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add agent-admin-backend/
git commit -m "feat(admin): add intent taxonomy management API with alias proposals and YAML editing"
```

---

## Self-Review

### 1. Spec coverage

| Spec 需求 | 覆盖任务 |
|-----------|---------|
| admin-feedback-management: GET /api/admin/feedbacks (分页+筛选) | Task 3 |
| admin-feedback-management: POST /api/admin/feedbacks/{id}/process | Task 3 |
| admin-system-metrics: GET /api/admin/metrics/overview | Task 4 |
| admin-system-metrics: GET /api/admin/metrics/stages (24h) | Task 4 |
| admin-system-metrics: GET /api/admin/metrics/feedback-distribution | Task 4 |
| admin-prompt-template-management: GET /api/admin/prompt-templates | Task 5 |
| admin-prompt-template-management: GET /api/admin/prompt-templates/{name}/performance | Task 5 |
| admin-prompt-template-management: POST /api/admin/prompt-templates/preview | Task 5 |
| admin-intent-lexicon-management: GET /api/admin/intent-taxonomy | Task 6 |
| admin-intent-lexicon-management: GET /api/admin/intent-taxonomy/alias-proposals | Task 6 |
| admin-intent-lexicon-management: POST /api/admin/intent-taxonomy/alias-proposals/apply | Task 6 |
| admin-intent-lexicon-management: POST /api/admin/intent-taxonomy/aliases | Task 6 |
| Backend scaffolding (pom, main, config, CORS, auth) | Task 1 |
| Data access layer (read-only entities + repositories) | Task 2 |

无遗漏。

### 2. Placeholder scan

无 TBD/TODO。所有步骤包含完整代码。`previewPrompt` 方法调用 agent-core HTTP 端点，测试中不覆盖（需要集成测试），但 Service 层其他方法有完整单元测试覆盖。

### 3. Type consistency

- `FeedbackReadRepository.findByFilters(String, String, Boolean, Pageable)` → Task 3 `FeedbackAdminService.listFeedbacks` 调用签名一致 ✓
- `FeedbackReadRepository.countByPromptTemplateVersion()` → Task 5 `PromptTemplateAdminService.getPerformance` 调用一致 ✓
- `FeedbackReadRepository.findUnprocessedIntentCorrections()` → Task 6 `IntentTaxonomyAdminService.getAliasProposals` 调用一致 ✓
- `FeedbackReadRepository.countByTagAndType()` → Task 4 `MetricsAdminService.getFeedbackDistribution` 调用一致 ✓
- DTO record 类名在 Service 和 Controller 之间一致 ✓
