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
        <div v-if="messages.length === 0" class="welcome-message">
          <div class="welcome-bubble">
            <h2>你好，我是你的美陈设计助手</h2>
            <p>请告诉我：</p>
            <ul>
              <li>项目主题（如：夏日海洋、新春国潮）</li>
              <li>空间类型（购物中心 / 百货 / 快闪店 / 展厅等）</li>
              <li>预算区间</li>
              <li>涉及哪些点位？每个点位需要几个？</li>
            </ul>
            <p class="welcome-hint">我会基于你的需求生成 10 个创意方向。</p>
          </div>
        </div>
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message-row"
          :class="msg.role"
        >
          <div class="message-bubble">
            <div class="message-role">{{ msg.role === 'user' ? '你' : 'AI 助手' }}</div>
            <div class="message-content">
              <TextMessage v-if="msg.messageType === 'text' || msg.messageType === 'summary'" :content="msg.content" />
              <IdeaGallery v-else-if="msg.messageType === 'idea_gallery'" :ideas="parseJson(msg.content)" @select="handleSelectIdea" />
              <pre v-else>{{ msg.content }}</pre>
            </div>
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
import TextMessage from '../components/chat/TextMessage.vue'
import IdeaGallery from '../components/chat/IdeaGallery.vue'

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
.welcome-message {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}
.welcome-bubble {
  max-width: 640px;
  padding: 24px 32px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  text-align: center;
}
.welcome-bubble h2 {
  margin: 0 0 16px;
  font-size: 20px;
  color: #303133;
}
.welcome-bubble p {
  margin: 8px 0;
  color: #606266;
}
.welcome-bubble ul {
  text-align: left;
  color: #606266;
  line-height: 1.8;
  margin: 12px 0;
  padding-left: 24px;
}
.welcome-hint {
  margin-top: 16px;
  color: #909399;
  font-size: 13px;
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
