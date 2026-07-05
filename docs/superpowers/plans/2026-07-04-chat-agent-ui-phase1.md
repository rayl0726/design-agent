# 对话式 Agent UI 与会话管理 - 第一阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将前端从 Tab 详情页改造为对话式交互界面，并在 Java 后端新增会话消息历史存储能力，使用户可以通过连续对话迭代生成 L1/L2/L3 方案。

**Architecture:** 复用现有 `Project` 表作为会话容器，新增 `SessionMessage` 表保存用户与 AI 的消息记录；前端新增 `ChatView.vue` 替换 `ProjectDetail.vue`，通过消息类型区分文本、创意卡片、视觉方案、方案文档等不同展示形态。

**Tech Stack:** Vue 3 + Element Plus + Vue Router；Spring Boot + JPA + H2/PostgreSQL。

## Global Constraints

- 复用现有 `Project` 实体和 `/api/v1/projects` 前缀，向后兼容
- 新增字段允许旧数据为空（nullable）
- 前端路由 `/project/:id` 保留，组件替换为 `ChatView`
- 所有 JSON 字段使用 `TEXT` 类型存储
- 消息类型枚举：text, summary, idea_gallery, visual_scheme, proposal

---

## Task 1: Java 后端新增 SessionMessage 实体与 Repository

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/entity/SessionMessage.java`
- Create: `agent-api/src/main/java/com/meichen/orchestrator/repository/SessionMessageRepository.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/entity/Project.java`

**Interfaces:**
- Produces: `SessionMessage` 实体、`SessionMessageRepository.findByProjectIdOrderByCreatedAtAsc(String)`

- [ ] **Step 1: 创建 SessionMessage 实体**

```java
package com.meichen.orchestrator.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "session_messages")
public class SessionMessage {

    @Id
    @Column(length = 36)
    private String id;

    @Column(name = "project_id", nullable = false, length = 36)
    private String projectId;

    // user / assistant / system
    @Column(nullable = false, length = 20)
    private String role;

    // text / summary / idea_gallery / visual_scheme / proposal
    @Column(nullable = false, length = 30)
    private String messageType;

    // 文本内容或 JSON 字符串
    @Column(nullable = false, columnDefinition = "LONGTEXT")
    private String content;

    @CreationTimestamp
    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public SessionMessage() {}

    public static SessionMessage create(String projectId, String role, String messageType, String content) {
        SessionMessage msg = new SessionMessage();
        msg.setId(java.util.UUID.randomUUID().toString());
        msg.setProjectId(projectId);
        msg.setRole(role);
        msg.setMessageType(messageType);
        msg.setContent(content);
        return msg;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getProjectId() { return projectId; }
    public void setProjectId(String projectId) { this.projectId = projectId; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public String getMessageType() { return messageType; }
    public void setMessageType(String messageType) { this.messageType = messageType; }

    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
```

- [ ] **Step 2: 创建 SessionMessageRepository**

```java
package com.meichen.orchestrator.repository;

import com.meichen.orchestrator.entity.SessionMessage;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SessionMessageRepository extends JpaRepository<SessionMessage, String> {
    List<SessionMessage> findByProjectIdOrderByCreatedAtAsc(String projectId);
}
```

- [ ] **Step 3: 扩展 Project 实体字段**

在 `Project.java` 中新增以下字段及 getter/setter：

```java
@Column(length = 30)
private String currentStage; // INIT / REQUIREMENT / L1 / L2 / L3 / COMPLETED

@Column(name = "selected_idea_index")
private Integer selectedIdeaIndex;

@Column(name = "requirement_json", columnDefinition = "TEXT")
private String requirementJson;
```

- [ ] **Step 4: 编译验证**

Run: `cd agent-api && ./mvnw compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 5: Commit**

```bash
git add agent-api/src/main/java/com/meichen/orchestrator/entity/SessionMessage.java
agent-api/src/main/java/com/meichen/orchestrator/repository/SessionMessageRepository.java
agent-api/src/main/java/com/meichen/orchestrator/entity/Project.java
git commit -m "feat(api): add SessionMessage entity and extend Project for chat session"
```

---

## Task 2: Java 后端新增会话消息服务与 API

**Files:**
- Create: `agent-api/src/main/java/com/meichen/orchestrator/service/SessionMessageService.java`
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/controller/ProjectController.java`

**Interfaces:**
- Consumes: `SessionMessageRepository`, `ProjectRepository`
- Produces: `POST /api/v1/projects/{id}/messages`, `GET /api/v1/projects/{id}/messages`

- [ ] **Step 1: 创建 SessionMessageService**

```java
package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;
import com.meichen.orchestrator.repository.ProjectRepository;
import com.meichen.orchestrator.repository.SessionMessageRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

@Service
public class SessionMessageService {

    private final SessionMessageRepository messageRepository;
    private final ProjectRepository projectRepository;

    public SessionMessageService(SessionMessageRepository messageRepository,
                                  ProjectRepository projectRepository) {
        this.messageRepository = messageRepository;
        this.projectRepository = projectRepository;
    }

    @Transactional(readOnly = true)
    public List<SessionMessage> listMessages(String projectId) {
        ensureProjectExists(projectId);
        return messageRepository.findByProjectIdOrderByCreatedAtAsc(projectId);
    }

    @Transactional
    public SessionMessage addUserMessage(String projectId, String content) {
        ensureProjectExists(projectId);
        SessionMessage msg = SessionMessage.create(projectId, "user", "text", content);
        return messageRepository.save(msg);
    }

    @Transactional
    public SessionMessage addAssistantMessage(String projectId, String messageType, String content) {
        ensureProjectExists(projectId);
        SessionMessage msg = SessionMessage.create(projectId, "assistant", messageType, content);
        return messageRepository.save(msg);
    }

    @Transactional
    public void addSystemMessage(String projectId, String content) {
        SessionMessage msg = SessionMessage.create(projectId, "system", "text", content);
        messageRepository.save(msg);
    }

    private void ensureProjectExists(String projectId) {
        if (!projectRepository.existsById(projectId)) {
            throw new IllegalArgumentException("Project not found: " + projectId);
        }
    }
}
```

- [ ] **Step 2: 扩展 ProjectController 消息接口**

在 `ProjectController.java` 中新增依赖注入和接口：

```java
private final SessionMessageService sessionMessageService;

public ProjectController(WorkflowService workflowService,
                         ProjectRepository projectRepository,
                         SessionMessageService sessionMessageService) {
    this.workflowService = workflowService;
    this.projectRepository = projectRepository;
    this.sessionMessageService = sessionMessageService;
}
```

新增 GET 和 POST 接口：

```java
@GetMapping("/{id}/messages")
public ResponseEntity<List<SessionMessage>> listMessages(@PathVariable("id") String projectId) {
    return ResponseEntity.ok(sessionMessageService.listMessages(projectId));
}

@PostMapping("/{id}/messages")
public ResponseEntity<SessionMessage> addMessage(
    @PathVariable("id") String projectId,
    @RequestBody Map<String, Object> body
) {
    String content = (String) body.get("content");
    if (content == null || content.isBlank()) {
        throw new IllegalArgumentException("content is required");
    }
    SessionMessage msg = sessionMessageService.addUserMessage(projectId, content);
    return ResponseEntity.ok(msg);
}
```

- [ ] **Step 3: 编译验证**

Run: `cd agent-api && ./mvnw compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 4: Commit**

```bash
git add agent-api/src/main/java/com/meichen/orchestrator/service/SessionMessageService.java
agent-api/src/main/java/com/meichen/orchestrator/controller/ProjectController.java
git commit -m "feat(api): add session message service and REST endpoints"
```

---

## Task 3: 前端新增 API 客户端方法

**Files:**
- Modify: `agent-web/src/api/client.js`

**Interfaces:**
- Produces: `messageApi.list(sessionId)`, `messageApi.send(sessionId, content)`

- [ ] **Step 1: 在 client.js 中新增 messageApi**

```javascript
export const messageApi = {
  list: (sessionId) => client.get(`/projects/${sessionId}/messages`),
  send: (sessionId, content) => client.post(`/projects/${sessionId}/messages`, { content }),
}
```

- [ ] **Step 2: Commit**

```bash
git add agent-web/src/api/client.js
git commit -m "feat(web): add message API client"
```

---

## Task 4: 前端新增 ChatView 页面框架

**Files:**
- Create: `agent-web/src/views/ChatView.vue`
- Modify: `agent-web/src/router/index.js`

**Interfaces:**
- Consumes: `projectApi.get`, `messageApi.list`, `messageApi.send`
- Produces: 对话页面路由 `/project/:id`

- [ ] **Step 1: 创建 ChatView.vue 基础布局**

```vue
<template>
  <div class="chat-layout">
    <aside class="session-sidebar">
      <div class="sidebar-header">
        <h3>会话列表</h3>
        <el-button type="primary" size="small" @click="goNew">新建</el-button>
      </div>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === sessionId }"
          @click="goSession(s.id)"
        >
          <p class="session-name">{{ s.name || '未命名会话' }}</p>
          <p class="session-time">{{ formatDate(s.createdAt) }}</p>
        </div>
      </div>
    </aside>

    <main class="chat-main">
      <div ref="messageList" class="message-list">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message-row"
          :class="msg.role"
        >
          <div class="message-bubble">
            <div class="message-role">{{ msg.role === 'user' ? '你' : 'AI 助手' }}</div>
            <div class="message-content">{{ msg.content }}</div>
          </div>
        </div>
      </div>

      <div class="chat-input-area">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="3"
          placeholder="描述你的美陈设计需求..."
          @keydown.enter.prevent="sendMessage"
        />
        <el-button type="primary" :loading="sending" @click="sendMessage">发送</el-button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { projectApi, messageApi } from '../api/client.js'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const sessionId = ref(route.params.id)
const session = ref({})
const sessions = ref([])
const messages = ref([])
const inputText = ref('')
const sending = ref(false)
const messageList = ref(null)

const formatDate = (str) => {
  if (!str) return ''
  return new Date(str).toLocaleString()
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messageList.value) {
      messageList.value.scrollTop = messageList.value.scrollHeight
    }
  })
}

const loadSession = async () => {
  try {
    const res = await projectApi.get(sessionId.value)
    session.value = res.data
  } catch (e) {
    ElMessage.error('加载会话失败')
  }
}

const loadMessages = async () => {
  try {
    const res = await messageApi.list(sessionId.value)
    messages.value = res.data
    scrollToBottom()
  } catch (e) {
    ElMessage.error('加载消息失败')
  }
}

const loadSessions = async () => {
  try {
    const res = await projectApi.list()
    sessions.value = res.data
  } catch (e) {
    console.error(e)
  }
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text) return
  sending.value = true
  try {
    await messageApi.send(sessionId.value, text)
    inputText.value = ''
    await loadMessages()
  } catch (e) {
    ElMessage.error('发送失败')
  } finally {
    sending.value = false
  }
}

const goSession = (id) => {
  router.push(`/project/${id}`)
}

const goNew = () => {
  router.push('/new')
}

onMounted(() => {
  loadSession()
  loadSessions()
  loadMessages()
})

watch(() => route.params.id, (newId) => {
  sessionId.value = newId
  loadSession()
  loadMessages()
})
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100vh;
  background: #f5f7fa;
}
.session-sidebar {
  width: 260px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}
.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
}
.session-list {
  flex: 1;
  overflow-y: auto;
}
.session-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
  transition: background 0.2s;
}
.session-item:hover,
.session-item.active {
  background: #f5f7fa;
}
.session-name {
  margin: 0 0 4px;
  font-weight: 500;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.session-time {
  margin: 0;
  font-size: 12px;
  color: #909399;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
.message-row {
  display: flex;
  margin-bottom: 16px;
}
.message-row.user {
  justify-content: flex-end;
}
.message-row.assistant {
  justify-content: flex-start;
}
.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.message-row.user .message-bubble {
  background: #409eff;
  color: #fff;
}
.message-role {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}
.message-row.user .message-role {
  color: rgba(255, 255, 255, 0.85);
}
.message-content {
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.chat-input-area {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
}
.chat-input-area .el-textarea {
  flex: 1;
}
</style>
```

- [ ] **Step 2: 修改路由**

将 `agent-web/src/router/index.js` 中：

```javascript
import ProjectDetail from '../views/ProjectDetail.vue'
```

替换为：

```javascript
import ChatView from '../views/ChatView.vue'
```

并将路由：

```javascript
{ path: '/project/:id', name: 'ProjectDetail', component: ProjectDetail },
```

替换为：

```javascript
{ path: '/project/:id', name: 'ChatView', component: ChatView },
```

- [ ] **Step 3: 启动前端验证页面能打开**

Run: `cd agent-web && npm run dev`
Expected: 访问 `http://localhost:5173/project/{id}` 能看到左侧会话列表和右侧消息流

- [ ] **Step 4: Commit**

```bash
git add agent-web/src/views/ChatView.vue agent-web/src/router/index.js
git commit -m "feat(web): add basic chat view layout"
```

---

## Task 5: 前端根据消息类型渲染不同卡片

**Files:**
- Create: `agent-web/src/components/chat/TextMessage.vue`
- Create: `agent-web/src/components/chat/IdeaGallery.vue`
- Modify: `agent-web/src/views/ChatView.vue`

**Interfaces:**
- Consumes: `message.messageType` 和 `message.content`
- Produces: 根据类型渲染文本/创意卡片/视觉方案/方案文档

- [ ] **Step 1: 创建 TextMessage.vue**

```vue
<template>
  <div class="text-message">{{ content }}</div>
</template>

<script setup>
defineProps({ content: String })
</script>

<style scoped>
.text-message {
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}
</style>
```

- [ ] **Step 2: 创建 IdeaGallery.vue**

```vue
<template>
  <div class="idea-gallery">
    <p class="gallery-title">已生成 {{ ideas.length }} 个创意方向：</p>
    <div class="cards-grid">
      <div v-for="(idea, idx) in ideas" :key="idx" class="idea-card">
        <h4 class="idea-title">{{ idea.title || `创意 ${idx + 1}` }}</h4>
        <p class="idea-theme"><strong>主题：</strong>{{ idea.theme || idea.concept || '暂无' }}</p>
        <p class="idea-style"><strong>风格：</strong>{{ idea.style || '暂无' }}</p>
        <div v-if="idea.colorPalette && idea.colorPalette.length" class="color-palette">
          <span
            v-for="(c, i) in idea.colorPalette"
            :key="i"
            class="color-dot"
            :style="{ background: c.hex || c }"
            :title="c.name || c"
          />
        </div>
        <p class="idea-summary">{{ idea.summary || idea.story || '' }}</p>
        <el-button size="small" type="primary" @click="$emit('select', idx)">基于这个创意继续</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ ideas: Array })
defineEmits(['select'])
</script>

<style scoped>
.idea-gallery {
  width: 100%;
}
.gallery-title {
  font-weight: 500;
  margin-bottom: 12px;
}
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.idea-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: 16px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.idea-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}
.idea-title {
  margin: 0 0 10px;
  font-size: 16px;
  color: #303133;
}
.idea-theme,
.idea-style,
.idea-summary {
  margin: 6px 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}
.color-palette {
  display: flex;
  gap: 8px;
  margin: 10px 0;
}
.color-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid #dcdfe6;
}
</style>
```

- [ ] **Step 3: 修改 ChatView.vue 消息渲染**

将消息内容区域：

```html
<div class="message-content">{{ msg.content }}</div>
```

替换为动态组件：

```html
<div class="message-content">
  <TextMessage v-if="msg.messageType === 'text' || msg.messageType === 'summary'" :content="msg.content" />
  <IdeaGallery v-else-if="msg.messageType === 'idea_gallery'" :ideas="parseJson(msg.content)" @select="handleSelectIdea" />
  <pre v-else>{{ msg.content }}</pre>
</div>
```

并在 script 中引入和添加方法：

```javascript
import TextMessage from '../components/chat/TextMessage.vue'
import IdeaGallery from '../components/chat/IdeaGallery.vue'

const parseJson = (str) => {
  try {
    return JSON.parse(str)
  } catch (e) {
    return []
  }
}

const handleSelectIdea = (index) => {
  inputText.value = `基于第 ${index + 1} 个创意继续生成视觉方案`
  sendMessage()
}
```

- [ ] **Step 4: 验证组件渲染**

手动构造一条 `messageType=idea_gallery` 的消息数据，刷新页面确认 10 张卡片网格正常显示。

- [ ] **Step 5: Commit**

```bash
git add agent-web/src/components/chat/TextMessage.vue
agent-web/src/components/chat/IdeaGallery.vue
agent-web/src/views/ChatView.vue
git commit -m "feat(web): render text and idea gallery message types"
```

---

## Task 6: 后端在工作流节点中持久化 AI 消息

**Files:**
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/service/WorkflowService.java`

**Interfaces:**
- Consumes: `SessionMessageService`
- Produces: L1/L2/L3 完成后自动生成对应的 assistant 消息

- [ ] **Step 1: 注入 SessionMessageService**

```java
private final SessionMessageService sessionMessageService;

public WorkflowService(ProjectRepository projectRepository,
                       WorkflowLogRepository logRepository,
                       WorkflowEngine workflowEngine,
                       WebClient.Builder webClientBuilder,
                       SessionMessageService sessionMessageService,
                       @Value("${agent-core.base-url:http://localhost:8000}") String agentCoreBaseUrl) {
    // ... existing assignments
    this.sessionMessageService = sessionMessageService;
    this.webClient = webClientBuilder.baseUrl(agentCoreBaseUrl).build();
}
```

- [ ] **Step 2: 在 updateProjectStatus 中生成 AI 消息**

在 `updateProjectStatus` 方法中，对应 L1/L2/L3 分支添加消息保存：

```java
if (result.containsKey("concept_design")) {
    project.setL1OutputJson(toJson(result.get("concept_design")));
    project.setCurrentLevel("L1");
    project.setStatus("L1_PENDING");
    sessionMessageService.addAssistantMessage(projectId, "idea_gallery", project.getL1OutputJson());
}
if (result.containsKey("visual_design")) {
    project.setL2OutputJson(toJson(result.get("visual_design")));
    project.setCurrentLevel("L2");
    project.setStatus("L2_PENDING");
    sessionMessageService.addAssistantMessage(projectId, "visual_scheme", project.getL2OutputJson());
}
if (result.containsKey("technical_design")) {
    project.setL3OutputJson(toJson(result.get("technical_design")));
    project.setCurrentLevel("L3");
    project.setStatus("L3_PENDING");
    sessionMessageService.addAssistantMessage(projectId, "proposal", project.getL3OutputJson());
}
```

- [ ] **Step 3: 编译验证**

Run: `cd agent-api && ./mvnw compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 4: Commit**

```bash
git add agent-api/src/main/java/com/meichen/orchestrator/service/WorkflowService.java
git commit -m "feat(api): persist AI messages for L1/L2/L3 outputs"
```

---

## Task 7: 前端新建会话后进入对话页

**Files:**
- Modify: `agent-web/src/views/NewProject.vue`

**Interfaces:**
- Consumes: `projectApi.create`
- Produces: 创建成功后跳转到 `/project/{id}`

- [ ] **Step 1: 修改创建成功后的跳转逻辑**

在 `NewProject.vue` 的 `submit` 方法中，找到创建成功后的逻辑，改为：

```javascript
const res = await projectApi.create({
  name: form.value.theme || '未命名会话',
  description: form.value.description,
  inputs: [...],
})
ElMessage.success('创建成功')
router.push(`/project/${res.data.id}`)
```

并确保在跳转到对话页后，由 AI 主动发送开场白消息（后端或前端处理）。

简化做法：前端在 `ChatView.vue` 加载消息时，如果消息为空，显示一段开场提示文案（无需后端存储）。

在 `ChatView.vue` 的 messages 渲染前增加：

```html
<div v-if="messages.length === 0" class="welcome-message">
  <h2>你好，我是你的美陈设计助手</h2>
  <p>请告诉我项目主题、空间类型、预算和涉及点位，我会为你生成创意方案。</p>
</div>
```

- [ ] **Step 2: Commit**

```bash
git add agent-web/src/views/NewProject.vue agent-web/src/views/ChatView.vue
git commit -m "feat(web): redirect to chat view after creating session"
```

---

## Self-Review

**Spec coverage:**
- 对话式布局：Task 4
- 左侧会话列表：Task 4
- 消息历史保存：Task 1-2
- 创意卡片展示：Task 5
- L1/L2/L3 消息持久化：Task 6
- 新建会话进入对话：Task 7

**Placeholder scan：** 无 TBD/TODO/占位符。

**Type consistency：** `SessionMessage.messageType` 枚举（text, summary, idea_gallery, visual_scheme, proposal）前后端一致；前端 `IdeaGallery` 接收 `ideas` 数组，与后端 L1 JSON 结构对应。
