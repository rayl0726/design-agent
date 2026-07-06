<template>
  <div class="chat-app">
    <!-- 左侧会话边栏 -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-logo">
          <span class="logo-icon">M</span>
          <span class="logo-text">美陈 Agent</span>
        </div>
      </div>

      <div class="sidebar-actions">
        <el-button
          type="primary"
          size="large"
          class="new-chat-btn"
          :loading="creating"
          @click="createNewSession"
        >
          <el-icon><Plus /></el-icon>
          新建对话
        </el-button>
      </div>

      <div class="session-list">
        <div class="list-header">
          <span>会话历史</span>
          <span class="list-count">{{ sessions.length }}</span>
        </div>
        <div
          v-for="s in sortedSessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === sessionId }"
          @click="goSession(s.id)"
        >
          <el-icon class="session-icon"><ChatDotRound /></el-icon>
          <div class="session-info">
            <p class="session-name">{{ s.name || '未命名会话' }}</p>
            <p class="session-time">{{ formatDate(s.createdAt) }}</p>
          </div>
        </div>
        <el-empty v-if="sessions.length === 0" description="暂无会话" :image-size="60" />
      </div>
    </aside>

    <!-- 右侧聊天区域 -->
    <main class="chat-main">
      <header class="chat-header">
        <div class="header-title">
          <h2>{{ session.name || '新对话' }}</h2>
          <p v-if="sessionId" class="header-subtitle">{{ sessionId }}</p>
        </div>
        <div class="header-actions">
          <el-button text @click="openLogDrawer">
            <el-icon><Document /></el-icon>
            <span class="header-action-text">日志</span>
          </el-button>
          <el-button v-if="sessionId" text @click="deleteSession">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </header>

      <div ref="messageList" class="message-list">
        <!-- 空状态欢迎页 -->
        <div v-if="!sessionId" class="welcome-center">
          <div class="welcome-card">
            <div class="welcome-icon">
              <el-icon :size="48"><MagicStick /></el-icon>
            </div>
            <h1>美陈设计 Agent</h1>
            <p class="welcome-desc">
              告诉我你的设计需求，我将为你生成创意方案、现场效果图和可落地方案。
            </p>
            <div class="welcome-examples">
              <div class="example-chip" @click="quickStart('夏日海洋主题购物中心中庭吊饰，预算15万')">
                夏日海洋主题购物中心中庭吊饰，预算15万
              </div>
              <div class="example-chip" @click="quickStart('新春国潮快闪店，包含门头、DP点、合影墙')">
                新春国潮快闪店，包含门头、DP点、合影墙
              </div>
              <div class="example-chip" @click="quickStart('轻奢风格百货商场入口美陈，需要灯光装置')">
                轻奢风格百货商场入口美陈，需要灯光装置
              </div>
            </div>
            <el-button type="primary" size="large" class="welcome-start" @click="createNewSession">
              开始新对话
            </el-button>
          </div>
        </div>

        <!-- 消息列表 -->
        <template v-if="sessionId">
          <template v-for="(msg, idx) in messages" :key="msg.id">
            <div
              class="message-wrapper"
              :class="msg.role"
            >
              <div class="message-avatar">
                <div v-if="msg.role === 'user'" class="avatar user-avatar">我</div>
                <div v-else class="avatar ai-avatar">AI</div>
              </div>
              <div class="message-content-box">
                <div class="message-meta">
                  <span class="message-author">{{ msg.role === 'user' ? '你' : 'AI 助手' }}</span>
                  <span class="message-time">{{ formatTime(msg.createdAt) }}</span>
                </div>
                <div class="message-body">
                  <TextMessage v-if="msg.messageType === 'text' || msg.messageType === 'summary'" :content="msg.content" />
                  <IdeaGallery v-else-if="msg.messageType === 'idea_gallery'" :ideas="parseJson(msg.content)" :project-id="sessionId" />
                  <pre v-else class="raw-content">{{ msg.content }}</pre>
                </div>
              </div>
            </div>

            <!-- 思考过程：紧跟最后一个用户消息，完成后折叠，后续 AI 回复在其后输出 -->
            <div
              v-if="idx === lastUserMessageIndex && (thinkingLogs.length > 0 || session.status === 'PARSING')"
              class="thinking-wrapper"
            >
              <ThinkingProcess :logs="thinkingLogs" :is-running="session.status === 'PARSING'" />
            </div>
          </template>
        </template>
      </div>

      <!-- 底部输入区 -->
      <footer v-if="sessionId" class="chat-input-area">
        <div class="input-container">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="2"
            resize="none"
            placeholder="描述你的美陈设计需求，按 Enter 发送..."
            class="chat-input"
            @keydown.enter.prevent="sendMessage"
          />
          <div class="input-actions">
            <el-button text class="attach-btn">
              <el-icon><Paperclip /></el-icon>
            </el-button>
            <el-button
              type="primary"
              class="send-btn"
              :loading="sending"
              :disabled="!inputText.trim()"
              @click="sendMessage"
            >
              <el-icon><Promotion /></el-icon>
            </el-button>
          </div>
        </div>
        <p class="input-hint">按 Enter 发送，Shift + Enter 换行</p>
      </footer>
    </main>
  </div>

  <el-drawer
    v-model="logDrawerOpen"
    title="系统日志"
    direction="rtl"
    size="720px"
  >
    <div class="log-toolbar">
      <el-button size="small" @click="loadAgentLogs" :loading="logLoading">刷新</el-button>
    </div>
    <div v-loading="logLoading" class="log-content">
      <pre v-if="logLines.length">{{ logLines.join('\n') }}</pre>
      <el-empty v-else description="暂无日志" :image-size="60" />
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ChatDotRound, Delete, MagicStick, Paperclip, Promotion, Document } from '@element-plus/icons-vue'
import { projectApi, messageApi, thinkingApi, logApi } from '../api/client.js'
import TextMessage from '../components/chat/TextMessage.vue'
import IdeaGallery from '../components/chat/IdeaGallery.vue'
import ThinkingProcess from '../components/chat/ThinkingProcess.vue'

const route = useRoute()
const router = useRouter()
const sessionId = ref(route.params.id || null)
const session = ref({})
const sessions = ref([])
const messages = ref([])
const inputText = ref('')
const sending = ref(false)
const creating = ref(false)
const messageList = ref(null)
const thinkingLogs = ref([])
const logDrawerOpen = ref(false)
const logLines = ref([])
const logLoading = ref(false)
let eventSource = null
let sseReconnectTimer = null

const sortedSessions = computed(() => {
  return [...sessions.value].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
})

const lastUserMessageIndex = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') return i
  }
  return -1
})

const formatDate = (str) => {
  if (!str) return ''
  const d = new Date(str)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

const formatTime = (str) => {
  if (!str) return ''
  return new Date(str).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messageList.value) {
      messageList.value.scrollTop = messageList.value.scrollHeight
    }
  })
}

const loadSession = async () => {
  if (!sessionId.value) {
    session.value = {}
    return
  }
  try {
    const res = await projectApi.get(sessionId.value)
    session.value = res.data
  } catch (e) {
    ElMessage.error('加载会话失败')
  }
}

const loadMessages = async () => {
  if (!sessionId.value) {
    messages.value = []
    return
  }
  try {
    const res = await messageApi.list(sessionId.value)
    messages.value = res.data
    scrollToBottom()
  } catch (e) {
    ElMessage.error('加载消息失败')
  }
}

const loadThinkingLogs = async () => {
  if (!sessionId.value) {
    thinkingLogs.value = []
    return
  }
  try {
    const res = await thinkingApi.list(sessionId.value)
    thinkingLogs.value = res.data
  } catch (e) {
    console.error(e)
  }
}

const openLogDrawer = async () => {
  logDrawerOpen.value = true
  await loadAgentLogs()
}

const loadAgentLogs = async () => {
  logLoading.value = true
  try {
    const res = await logApi.agentApi(300)
    logLines.value = res.data.lines || []
  } catch (e) {
    ElMessage.error('加载系统日志失败')
  } finally {
    logLoading.value = false
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

const createNewSession = async () => {
  creating.value = true
  try {
    const res = await projectApi.create({
      name: '新对话',
      description: '',
      inputs: [],
    })
    await loadSessions()
    router.push(`/project/${res.data.id}`)
  } catch (e) {
    ElMessage.error('创建会话失败')
  } finally {
    creating.value = false
  }
}

const quickStart = async (text) => {
  await createNewSession()
  inputText.value = text
  // createNewSession 会改变 route，等跳转完成后再发送
  setTimeout(() => sendMessage(), 300)
}

const connectSse = (projectId) => {
  disconnectSse()
  if (!projectId) return

  const url = `http://localhost:8080/api/v1/projects/${projectId}/events`
  try {
    eventSource = new EventSource(url)

    eventSource.addEventListener('status', (e) => {
      try {
        const data = JSON.parse(e.data)
        session.value.status = data.status
        if (data.current_level) session.value.currentLevel = data.current_level
      } catch (err) {
        console.error('Invalid status event', err)
      }
    })

    eventSource.addEventListener('message', (e) => {
      try {
        const data = JSON.parse(e.data)
        const exists = messages.value.find((m) => m.id === data.id)
        if (!exists) {
          // 如果是真实用户消息，替换掉相同内容的临时消息
          if (data.role === 'user') {
            const tempIndex = messages.value.findIndex(
              (m) => m.role === 'user' && m.id.startsWith('temp-') && m.content === data.content
            )
            if (tempIndex >= 0) {
              messages.value[tempIndex] = {
                id: data.id,
                projectId: projectId,
                role: data.role,
                messageType: data.message_type,
                content: data.content,
                createdAt: data.created_at,
              }
              scrollToBottom()
              return
            }
          }
          messages.value.push({
            id: data.id,
            projectId: projectId,
            role: data.role,
            messageType: data.message_type,
            content: data.content,
            createdAt: data.created_at,
          })
          scrollToBottom()
        }
      } catch (err) {
        console.error('Invalid message event', err)
      }
    })

    eventSource.addEventListener('thinking', (e) => {
      try {
        const data = JSON.parse(e.data)
        const existing = thinkingLogs.value.find((l) => l.nodeName === data.node_name)
        if (existing) {
          existing.status = data.status
          existing.message = data.message
          existing.createdAt = new Date().toISOString()
        } else {
          thinkingLogs.value.push({
            nodeName: data.node_name,
            status: data.status,
            message: data.message,
            createdAt: new Date().toISOString(),
          })
        }
        scrollToBottom()
      } catch (err) {
        console.error('Invalid thinking event', err)
      }
    })

    eventSource.addEventListener('error', (e) => {
      try {
        const data = JSON.parse(e.data)
        ElMessage.error(data.message || '处理出错')
      } catch (err) {
        console.error('SSE error', err)
      }
      // 非用户主动关闭时自动重连
      scheduleReconnect(projectId)
    })

    eventSource.onopen = () => {
      if (sseReconnectTimer) {
        clearTimeout(sseReconnectTimer)
        sseReconnectTimer = null
      }
    }
  } catch (e) {
    console.error('Failed to connect SSE', e)
    scheduleReconnect(projectId)
  }
}

const scheduleReconnect = (projectId) => {
  if (sseReconnectTimer) return
  sseReconnectTimer = setTimeout(() => {
    sseReconnectTimer = null
    connectSse(projectId)
  }, 3000)
}

const disconnectSse = () => {
  if (sseReconnectTimer) {
    clearTimeout(sseReconnectTimer)
    sseReconnectTimer = null
  }
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || !sessionId.value) return
  sending.value = true

  // 乐观更新：用户消息立即上屏
  const tempId = `temp-${Date.now()}`
  messages.value.push({
    id: tempId,
    projectId: sessionId.value,
    role: 'user',
    messageType: 'text',
    content: text,
    createdAt: new Date().toISOString(),
  })
  inputText.value = ''
  scrollToBottom()

  try {
    await messageApi.send(sessionId.value, text)
  } catch (e) {
    ElMessage.error('发送失败')
    // 发送失败时移除临时消息
    messages.value = messages.value.filter((m) => m.id !== tempId)
  } finally {
    sending.value = false
  }
}

const deleteSession = async () => {
  try {
    await ElMessageBox.confirm('确定删除这个会话吗？', '删除会话', { type: 'warning' })
    await projectApi.delete?.(sessionId.value) || ElMessage.warning('后端暂未提供删除接口')
    await loadSessions()
    router.push('/')
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
    }
  }
}

const parseJson = (str) => {
  try {
    return JSON.parse(str)
  } catch (e) {
    return []
  }
}

const goSession = (id) => {
  router.push(`/project/${id}`)
}

onMounted(() => {
  loadSessions()
  loadSession()
  loadMessages()
  loadThinkingLogs()
  connectSse(sessionId.value)
})

onUnmounted(() => {
  disconnectSse()
})

watch(() => route.params.id, (newId) => {
  sessionId.value = newId || null
  loadSession()
  loadMessages()
  loadThinkingLogs()
  connectSse(newId)
})
</script>

<style scoped>
.chat-app {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: #f8fafc;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* 左侧边栏 */
.sidebar {
  width: 280px;
  background: #1e293b;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-brand {
  padding: 20px 16px 16px;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
  color: #fff;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.sidebar-actions {
  padding: 0 16px 16px;
}

.new-chat-btn {
  width: 100%;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border: none;
  border-radius: 10px;
  font-weight: 500;
}

.new-chat-btn:hover {
  background: linear-gradient(135deg, #2563eb, #4f46e5);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 8px 8px;
  font-size: 12px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.list-count {
  background: #334155;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
}

.session-item:hover {
  background: #334155;
}

.session-item.active {
  background: #3b82f6;
}

.session-icon {
  font-size: 18px;
  color: #94a3b8;
}

.session-item.active .session-icon {
  color: #fff;
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-name {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 500;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-time {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
}

/* 右侧主区域 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f8fafc;
}

.chat-header {
  height: 64px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}

.header-title h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.header-subtitle {
  margin: 2px 0 0;
  font-size: 11px;
  color: #94a3b8;
  font-family: monospace;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

/* 欢迎页 */
.welcome-center {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100%;
}

.welcome-card {
  max-width: 560px;
  text-align: center;
  padding: 48px;
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04);
}

.welcome-icon {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #eff6ff, #ede9fe);
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  color: #3b82f6;
}

.welcome-card h1 {
  margin: 0 0 12px;
  font-size: 28px;
  color: #1e293b;
}

.welcome-desc {
  margin: 0 0 32px;
  color: #64748b;
  font-size: 15px;
  line-height: 1.6;
}

.welcome-examples {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 32px;
}

.example-chip {
  padding: 12px 16px;
  background: #f1f5f9;
  border-radius: 12px;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.example-chip:hover {
  background: #e2e8f0;
  transform: translateX(4px);
}

.welcome-start {
  border-radius: 10px;
  padding: 12px 32px;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border: none;
}

/* 聊天欢迎 */
.welcome-chat {
  display: flex;
  align-items: flex-start;
  max-width: 800px;
}

.ai-greeting {
  display: flex;
  gap: 14px;
}

.ai-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.greeting-bubble {
  background: #fff;
  padding: 18px 20px;
  border-radius: 18px;
  border-top-left-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  max-width: 600px;
}

.greeting-bubble p {
  margin: 0 0 8px;
  color: #334155;
  line-height: 1.6;
}

.greeting-bubble ul {
  margin: 8px 0 0;
  padding-left: 20px;
  color: #475569;
  line-height: 1.8;
}

/* 消息列表 */
.message-wrapper {
  display: flex;
  gap: 14px;
  margin-bottom: 24px;
  width: 100%;
}

.message-wrapper.user {
  flex-direction: row-reverse;
  margin-left: auto;
  max-width: 80%;
}

.message-avatar {
  flex-shrink: 0;
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.user-avatar {
  background: #e2e8f0;
  color: #475569;
}

.ai-avatar {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: #fff;
}

.message-content-box {
  flex: 1;
  min-width: 0;
  max-width: calc(100% - 60px);
}

.message-wrapper:not(.user) .message-content-box {
  max-width: 100%;
}

.message-wrapper.user .message-content-box {
  align-items: flex-end;
  max-width: 100%;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}

.message-wrapper.user .message-meta {
  justify-content: flex-end;
}

.message-author {
  font-weight: 500;
  color: #334155;
}

.message-time {
  color: #94a3b8;
}

.message-body {
  background: #fff;
  padding: 14px 18px;
  border-radius: 18px;
  border-top-left-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  color: #334155;
  font-size: 14px;
  line-height: 1.6;
}

.message-wrapper.user .message-body {
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  border-top-left-radius: 18px;
  border-top-right-radius: 4px;
}

.raw-content {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
}

/* 输入区 */
.chat-input-area {
  background: #fff;
  border-top: 1px solid #e2e8f0;
  padding: 16px 24px 20px;
  flex-shrink: 0;
}

.input-container {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  background: #f1f5f9;
  border-radius: 16px;
  padding: 10px 12px 10px 16px;
  border: 1px solid transparent;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-container:focus-within {
  border-color: #bfdbfe;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  background: #fff;
}

.chat-input {
  flex: 1;
}

.chat-input :deep(.el-textarea__inner) {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 6px 0;
  font-size: 15px;
  color: #1e293b;
}

.chat-input :deep(.el-textarea__inner::placeholder) {
  color: #94a3b8;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.attach-btn {
  color: #64748b;
}

.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  padding: 0;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border: none;
}

.send-btn:disabled {
  background: #cbd5e1;
}

.input-hint {
  margin: 8px 0 0;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
}

.thinking-wrapper {
  margin-bottom: 24px;
  padding-left: 52px;
}

.header-action-text {
  margin-left: 4px;
}

.log-toolbar {
  margin-bottom: 12px;
  display: flex;
  justify-content: flex-end;
}

.log-content {
  height: calc(100vh - 140px);
  overflow: auto;
  background: #0f172a;
  border-radius: 8px;
  padding: 12px;
}

.log-content pre {
  margin: 0;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
</style>
