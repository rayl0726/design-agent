<template>
  <div class="chat-app">
    <!-- 左侧会话边栏 -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-logo">
          <span class="logo-icon">M</span>
          <span class="logo-text">Agent</span>
        </div>
      </div>

      <div class="sidebar-actions">
        <el-button
          type="primary"
          size="large"
          class="new-chat-btn"
          :loading="creating"
          @click="createNewSession('generic')"
        >
          <el-icon><Plus /></el-icon>
          新建对话
        </el-button>
      </div>

      <div class="session-list">
        <!-- 通用 Agent 会话组 -->
        <div class="session-group">
          <div class="list-header">
            <span>通用会话</span>
            <span class="list-count">{{ genericSessions.length }}</span>
          </div>
          <div
            v-for="s in genericSessions"
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
            <div class="session-actions" @click.stop>
              <el-button text size="small" @click="startRename(s)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button text size="small" @click="deleteSession(s.id)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <el-empty v-if="genericSessions.length === 0" description="暂无通用会话" :image-size="40" />
        </div>

        <!-- 美陈 Agent 会话组 -->
        <div class="session-group">
          <div class="list-header">
            <span>美陈项目</span>
            <span class="list-count">{{ meichenSessions.length }}</span>
          </div>
          <div
            v-for="s in meichenSessions"
            :key="s.id"
            class="session-item"
            :class="{ active: s.id === sessionId }"
            @click="goSession(s.id)"
          >
            <el-icon class="session-icon"><MagicStick /></el-icon>
            <div class="session-info">
              <p class="session-name">{{ s.name || '未命名项目' }}</p>
              <p class="session-time">{{ formatDate(s.createdAt) }}</p>
            </div>
            <div class="session-actions" @click.stop>
              <el-button text size="small" @click="startRename(s)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button text size="small" @click="deleteSession(s.id)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <el-empty v-if="meichenSessions.length === 0" description="暂无美陈项目" :image-size="40" />
        </div>
      </div>
    </aside>

    <!-- 右侧聊天区域 -->
    <main class="chat-main">
      <header class="chat-header">
        <div class="header-title">
          <h2>{{ pageTitle }}</h2>
          <p v-if="sessionId" class="header-subtitle">{{ sessionId }}</p>
        </div>
        <div class="header-actions">
          <el-button text @click="openLogDrawer">
            <el-icon><Document /></el-icon>
            <span class="header-action-text">日志</span>
          </el-button>
          <el-dropdown trigger="click" @command="handleUserCommand">
            <span class="user-info">
              <el-icon><User /></el-icon>
              <span class="user-phone">{{ authStore.phone || '未知用户' }}</span>
              <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <div ref="messageList" class="message-list">
        <!-- 空状态：居中提示 -->
        <div v-if="!sessionId" class="empty-chat">
          <h1 class="empty-title">{{ welcomeTitle }}</h1>
          <p class="empty-desc">{{ welcomeDesc }}</p>
        </div>

        <!-- 消息列表 -->
        <template v-if="sessionId">
          <template v-for="(msg, idx) in renderMessages" :key="msg.id">
            <div class="message-wrapper" :class="msg.role">
              <div class="message-avatar">
                <div v-if="msg.role === 'user'" class="avatar user-avatar">我</div>
                <div v-else class="avatar ai-avatar">AI</div>
              </div>
              <div class="message-content-box">
                <div class="message-meta">
                  <span class="message-author">{{ msg.role === 'user' ? '你' : 'AI 助手' }}</span>
                  <span class="message-time">{{ formatTime(msg.createdAt) }}</span>
                </div>
                <ReasoningTrace v-if="msg.role !== 'user' && msg.reasoningTrace && msg.reasoningTrace.length" :trace="msg.reasoningTrace" />
                <div v-if="msg.role === 'tool' || isToolCallMessage(msg)" class="tool-card">
                  <div class="tool-header">
                    <span class="tool-icon">🔍</span>
                    <span class="tool-name">{{ toolDisplay(msg).toolName }}</span>
                    <span :class="['tool-status', toolDisplay(msg).status === 'done' ? 'done' : 'running']">{{ getToolStatusLabel(toolDisplay(msg).status) }}</span>
                  </div>
                  <div v-if="toolDisplay(msg).toolArguments && toolDisplay(msg).toolArguments.query" class="tool-query">
                    查询：{{ toolDisplay(msg).toolArguments.query }}
                  </div>
                  <div v-if="toolDisplay(msg).detail" class="tool-detail">
                    {{ toolDisplay(msg).detail }}
                  </div>
                  <div v-if="toolDisplay(msg).observation" class="tool-body">
                    <pre>{{ toolDisplay(msg).observation }}</pre>
                  </div>
                </div>
                <div v-else class="message-body">
                  <TextMessage v-if="msg.messageType === 'text' || msg.messageType === 'summary'" :content="msg.content" />
                  <IdeaGallery v-else-if="msg.messageType === 'idea_gallery'" :ideas="parseJson(msg.content)" :project-id="sessionId" />
                  <pre v-else class="raw-content">{{ msg.content }}</pre>
                </div>
              </div>
            </div>

            <div
              v-if="idx === lastUserMessageIndex && (thinkingLogs.length > 0 || session.status === 'PARSING')"
              class="thinking-wrapper"
            >
              <ThinkingProcess :logs="thinkingLogs" :is-running="session.status === 'PARSING'" />
              <RecognitionDebug v-if="recognitionSummary" :summary="recognitionSummary" />
            </div>
          </template>
        </template>
      </div>

      <!-- 底部输入区：始终显示 -->
      <footer class="chat-input-area">
        <div class="input-wrapper">
          <div class="input-container">
            <el-input
              v-model="inputText"
              type="textarea"
              :rows="2"
              resize="none"
              :placeholder="inputPlaceholder"
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
          <div class="input-footer">
            <AgentSelector :model-value="currentAgentType" @select="onAgentSelect" />
            <p class="input-hint">按 Enter 发送，Shift + Enter 换行</p>
          </div>
        </div>
      </footer>
    </main>
  </div>

  <!-- 重命名对话框 -->
  <el-dialog v-model="renameDialogOpen" title="重命名会话" width="400px">
    <el-input v-model="renameValue" placeholder="输入新名称" @keydown.enter.prevent="confirmRename" />
    <template #footer>
      <el-button @click="renameDialogOpen = false">取消</el-button>
      <el-button type="primary" :disabled="!renameValue.trim()" @click="confirmRename">确定</el-button>
    </template>
  </el-dialog>

  <el-drawer
    v-model="logDrawerOpen"
    title="流程阶段日志"
    direction="rtl"
    size="720px"
  >
    <div class="log-toolbar">
      <el-button size="small" @click="loadStageLogs" :loading="logLoading">刷新</el-button>
    </div>
    <div v-loading="logLoading" class="log-content">
      <div v-if="stageLogs.length" class="stage-log-list">
        <div
          v-for="log in stageLogTree"
          :key="log.id"
          class="stage-log-item"
          :class="'status-' + log.status.toLowerCase()"
        >
          <div class="stage-log-header">
            <span class="stage-status-dot"></span>
            <span class="stage-name">{{ log.stageLabel || log.stageName }}</span>
            <span class="stage-status">{{ formatStageStatus(log.status) }}</span>
            <el-tag v-if="log.timeAnomaly" size="small" type="warning">时间异常</el-tag>
            <el-tag v-if="log.subStageOverflow" size="small" type="danger">子阶段溢出</el-tag>
          </div>
          <div class="stage-log-meta">
            <span v-if="log.startedAt">开始：{{ formatTime(log.startedAt) }}</span>
            <span v-if="log.completedAt">结束：{{ formatTime(log.completedAt) }}</span>
            <span v-if="log.durationMs != null">耗时：{{ formatDuration(log.durationMs) }}</span>
          </div>
          <div v-if="log.errorMessage" class="stage-log-error">
            失败原因：{{ log.errorMessage }}
          </div>
          <div v-if="hasImageStats(log.metadata)" class="stage-log-stats">
            图片生成：{{ log.metadata.success_images }}/{{ log.metadata.total_images }} 成功
            <span v-if="log.metadata.failed_images > 0" class="stage-log-fail-count">
              （{{ log.metadata.failed_images }} 张失败）
            </span>
          </div>
          <div v-if="log.children && log.children.length" class="stage-log-children">
            <div
              v-for="child in log.children"
              :key="child.id"
              class="stage-log-child"
              :class="'status-' + child.status.toLowerCase()"
            >
              <span class="stage-name">{{ child.stageLabel || child.stageName }}</span>
              <span v-if="child.durationMs != null" class="stage-duration">{{ formatDuration(child.durationMs) }}</span>
            </div>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无阶段日志" :image-size="60" />
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ChatDotRound, Delete, MagicStick, Paperclip, Promotion, Document, User, ArrowDown, Edit } from '@element-plus/icons-vue'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import { projectApi, messageApi, thinkingApi, stageLogApi } from '../api/client.js'
import { useAuthStore } from '@/stores/auth'
import TextMessage from '../components/chat/TextMessage.vue'
import IdeaGallery from '../components/chat/IdeaGallery.vue'
import ThinkingProcess from '../components/chat/ThinkingProcess.vue'
import RecognitionDebug from '../components/chat/RecognitionDebug.vue'
import AgentSelector from '../components/AgentSelector.vue'
import ReasoningTrace from '../components/ReasoningTrace.vue'
import { parseToolMessage, getToolStatusLabel } from '@/utils/toolMessage'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const sessionId = ref(route.params.id || null)
const session = ref({})
const sessions = ref([])
const messages = ref([])
const inputText = ref('')
const sending = ref(false)
const creating = ref(false)
const messageList = ref(null)
const thinkingLogs = ref([])
const recognitionSummary = ref(null)
const logDrawerOpen = ref(false)
const stageLogs = ref([])
const logLoading = ref(false)
const currentAgentType = ref('generic')
const renameDialogOpen = ref(false)
const renameValue = ref('')
const renamingSession = ref(null)
let eventSource = null
let sseReconnectTimer = null

const genericSessions = computed(() => {
  return sessions.value
    .filter((s) => s.agentType === 'generic' || !s.agentType)
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
})

const meichenSessions = computed(() => {
  return sessions.value
    .filter((s) => s.agentType === 'meichen')
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
})

const pageTitle = computed(() => {
  if (sessionId.value) {
    return session.value.name || (session.value.agentType === 'meichen' ? '美陈项目' : '新对话')
  }
  return currentAgentType.value === 'meichen' ? '美陈设计 Agent' : '通用 Agent'
})

const welcomeTitle = computed(() => {
  return currentAgentType.value === 'meichen' ? '美陈设计 Agent' : '通用 Agent'
})

const welcomeDesc = computed(() => {
  return currentAgentType.value === 'meichen'
    ? '告诉我你的设计需求，我将为你生成创意方案、现场效果图和可落地方案。'
    : '向我提出任何问题，我会自主规划任务、调用工具并给出可靠答案。'
})

const inputPlaceholder = computed(() => {
  return currentAgentType.value === 'meichen'
    ? '描述你的美陈设计需求，按 Enter 发送...'
    : '输入你的问题或任务，按 Enter 发送...'
})

const stageLogTree = computed(() => {
  const parents = stageLogs.value.filter((l) => l.parentId == null)
  const children = stageLogs.value.filter((l) => l.parentId != null)
  return parents.map((p) => ({
    ...p,
    children: children.filter((c) => c.parentId === p.id)
  }))
})

const isPureToolCall = (content) => {
  if (!content || typeof content !== 'string') return false
  return /^\s*<tool_call>[\s\S]*?<\/tool_call>\s*$/.test(content)
}

const renderMessages = computed(() => {
  return messages.value.filter((msg) => {
    // 过滤掉旧版 assistant 消息中只包含 tool_call 标记的脏数据，
    // 这些调用过程应由 role='tool' 的消息或 SSE tool_start/tool_result 展示。
    return !(msg.role === 'assistant' && isPureToolCall(msg.content))
  })
})

const lastUserMessageIndex = computed(() => {
  for (let i = renderMessages.value.length - 1; i >= 0; i--) {
    if (renderMessages.value[i].role === 'user') return i
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
  return new Date(str).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const formatStageStatus = (status) => {
  const map = {
    PENDING: '等待中',
    RUNNING: '执行中',
    SUCCESS: '成功',
    FAILED: '失败',
  }
  return map[status] || status
}

const formatDuration = (ms) => {
  if (ms == null) return ''
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  const minutes = Math.floor(ms / 60000)
  const seconds = ((ms % 60000) / 1000).toFixed(0)
  return `${minutes}m ${seconds}s`
}

const hasImageStats = (metadata) => {
  return metadata && metadata.total_images != null
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messageList.value) {
      messageList.value.scrollTop = messageList.value.scrollHeight
    }
  })
}

const isToolCallMessage = (msg) => {
  if (!msg || !msg.content || typeof msg.content !== 'string') return false
  return msg.content.includes('<tool_call>')
}

const toolDisplay = (msg) => parseToolMessage(msg?.content)

const loadSession = async () => {
  if (!sessionId.value) {
    session.value = {}
    return
  }
  const currentId = sessionId.value
  try {
    const res = await projectApi.get(sessionId.value)
    if (sessionId.value !== currentId) return
    session.value = res.data
    if (res.data.agentType) {
      currentAgentType.value = res.data.agentType
    }
  } catch (e) {
    ElMessage.error('加载会话失败')
  }
}

const loadMessages = async () => {
  if (!sessionId.value) {
    messages.value = []
    return
  }
  const currentId = sessionId.value
  try {
    const res = await messageApi.list(sessionId.value)
    if (sessionId.value !== currentId) return
    messages.value = res.data
    scrollToBottom()
  } catch (e) {
    ElMessage.error('加载消息失败')
  }
}

const loadThinkingLogs = async () => {
  recognitionSummary.value = null
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
  await loadStageLogs()
}

const loadStageLogs = async () => {
  if (!sessionId.value) {
    stageLogs.value = []
    return
  }
  logLoading.value = true
  try {
    const res = await stageLogApi.list(sessionId.value)
    stageLogs.value = res.data || []
  } catch (e) {
    ElMessage.error('加载阶段日志失败')
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

const createNewSession = async (agentType = 'generic') => {
  creating.value = true
  try {
    const name = agentType === 'meichen' ? '新美陈项目' : '新对话'
    const res = await projectApi.create({
      name,
      description: '',
      agent_type: agentType,
      inputs: [],
    })
    currentAgentType.value = agentType
    await loadSessions()
    router.push(`/project/${res.data.id}`)
  } catch (e) {
    ElMessage.error('创建会话失败')
  } finally {
    creating.value = false
  }
}

const onAgentSelect = async (agentType) => {
  if (agentType === currentAgentType.value) return
  await createNewSession(agentType)
}

const connectSse = (projectId) => {
  disconnectSse()
  if (!projectId) return

  const url = `/api/v1/projects/${projectId}/events`
  const ctrl = new AbortController()
  eventSource = ctrl

  fetchEventSource(url, {
    headers: {
      Authorization: `Bearer ${authStore.token}`,
    },
    signal: ctrl.signal,
    openWhenHidden: true,
    onopen() {
      if (sseReconnectTimer) {
        clearTimeout(sseReconnectTimer)
        sseReconnectTimer = null
      }
    },
    onmessage(msg) {
      try {
        const data = JSON.parse(msg.data)
        if (msg.event === 'status') {
          session.value.status = data.status
          if (data.current_level) session.value.currentLevel = data.current_level
        } else if (msg.event === 'tool_start') {
          const payload = JSON.parse(msg.data)
          const toolMsg = {
            id: `tool-${Date.now()}`,
            projectId: projectId,
            role: 'tool',
            messageType: 'tool',
            content: JSON.stringify({
              id: payload.id,
              tool_name: payload.tool_name,
              arguments: payload.arguments,
              status: 'searching',
              detail: '正在搜索...',
              observation: '',
            }),
            createdAt: new Date().toISOString(),
          }
          const lastUserIndex = messages.value.map((m) => m.role).lastIndexOf('user')
          if (lastUserIndex >= 0) {
            messages.value.splice(lastUserIndex + 1, 0, toolMsg)
          } else {
            messages.value.push(toolMsg)
          }
          scrollToBottom()
        } else if (msg.event === 'tool_result') {
          const payload = JSON.parse(msg.data)
          const toolMsg = messages.value.find(
            (m) => m.role === 'tool' && m.content && m.content.includes(`"id":"${payload.id}"`)
          )
          if (toolMsg) {
            try {
              const data = JSON.parse(toolMsg.content)
              data.observation = payload.observation
              data.status = 'done'
              toolMsg.content = JSON.stringify(data)
            } catch (e) {
              toolMsg.content = JSON.stringify({
                id: payload.id,
                tool_name: payload.tool_name,
                arguments: payload.arguments,
                observation: payload.observation,
                status: 'done',
              })
            }
            scrollToBottom()
          } else {
            messages.value.push({
              id: `tool-${Date.now()}`,
              projectId: projectId,
              role: 'tool',
              messageType: 'tool',
              content: JSON.stringify({
                id: payload.id,
                tool_name: payload.tool_name,
                arguments: payload.arguments,
                observation: payload.observation,
                status: 'done',
              }),
              createdAt: new Date().toISOString(),
            })
            scrollToBottom()
          }
        } else if (msg.event === 'tool_progress') {
          const payload = JSON.parse(msg.data)
          const existing = messages.value.find(
            (m) => m.role === 'tool' && m.content && m.content.includes(`"id":"${payload.id}"`)
          )
          if (existing) {
            try {
              const data = JSON.parse(existing.content)
              data.status = payload.status
              data.detail = payload.detail || ''
              existing.content = JSON.stringify(data)
            } catch (e) {
              // ignore
            }
          }
          scrollToBottom()
        } else if (msg.event === 'text_delta') {
          let delta = ''
          try {
            const parsed = JSON.parse(msg.data)
            delta = typeof parsed === 'string' ? parsed : (parsed.delta || '')
          } catch (e) {
            delta = msg.data || ''
          }
          const streamingMsg = messages.value.find(
            (m) => m.role === 'assistant' && m.streaming
          )
          if (streamingMsg && delta) {
            streamingMsg.content += delta
            scrollToBottom()
          }
        } else if (msg.event === 'message') {
          const exists = messages.value.find((m) => m.id === data.id)
          if (!exists) {
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
            const streamingIndex = messages.value.findIndex(
              (m) => m.role === 'assistant' && m.streaming
            )
            if (data.role === 'assistant' && streamingIndex >= 0) {
              messages.value[streamingIndex] = {
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
        } else if (msg.event === 'thinking') {
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
        } else if (msg.event === 'recognition') {
          recognitionSummary.value = data
        } else if (msg.event === 'error') {
          ElMessage.error(data.message || '处理出错')
        }
      } catch (err) {
        console.error('Invalid SSE event', msg.event, err)
      }
    },
    onclose() {
    },
    onerror(err) {
      console.error('SSE error', err)
      scheduleReconnect(projectId)
      throw err
    },
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      console.error('SSE connection failed', err)
    }
  })
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
    eventSource.abort()
    eventSource = null
  }
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text) return

  let projectId = sessionId.value
  if (!projectId) {
    // 无会话时先创建通用 Agent 会话
    const name = text.length > 20 ? text.slice(0, 20) + '...' : text
    try {
      const res = await projectApi.create({
        name,
        description: '',
        agent_type: currentAgentType.value,
        inputs: [],
      })
      projectId = res.data.id
      await loadSessions()
      router.push(`/project/${projectId}`)
    } catch (e) {
      ElMessage.error('创建会话失败')
      return
    }
  }

  sending.value = true
  const tempId = `temp-${Date.now()}`
  const streamingId = `streaming-${Date.now()}`
  messages.value.push({
    id: tempId,
    projectId: projectId,
    role: 'user',
    messageType: 'text',
    content: text,
    createdAt: new Date().toISOString(),
  })
  messages.value.push({
    id: streamingId,
    projectId: projectId,
    role: 'assistant',
    messageType: 'text',
    content: '',
    createdAt: new Date().toISOString(),
    streaming: true,
  })
  inputText.value = ''
  scrollToBottom()

  try {
    await messageApi.send(projectId, text)
  } catch (e) {
    ElMessage.error('发送失败')
    messages.value = messages.value.filter((m) => m.id !== tempId && m.id !== streamingId)
  } finally {
    sending.value = false
  }
}

const deleteSession = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除这个会话吗？', '删除会话', { type: 'warning' })
    await projectApi.delete(id)
    await loadSessions()
    if (sessionId.value === id) {
      router.push('/')
    }
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
    }
  }
}

const startRename = (s) => {
  renamingSession.value = s
  renameValue.value = s.name || ''
  renameDialogOpen.value = true
}

const confirmRename = async () => {
  if (!renamingSession.value || !renameValue.value.trim()) return
  try {
    await projectApi.update(renamingSession.value.id, { name: renameValue.value.trim() })
    renamingSession.value.name = renameValue.value.trim()
    if (sessionId.value === renamingSession.value.id) {
      session.value.name = renameValue.value.trim()
    }
    ElMessage.success('重命名成功')
  } catch (e) {
    ElMessage.error('重命名失败')
  } finally {
    renameDialogOpen.value = false
    renamingSession.value = null
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

const handleUserCommand = (command) => {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
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

watch(() => route.params.id, async (newId) => {
  sessionId.value = newId || null
  disconnectSse()
  messages.value = []
  await loadSession()
  await loadMessages()
  await loadThinkingLogs()
  connectSse(newId)
})
</script>

<style scoped>
.chat-app {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* 左侧边栏：GPT 风格深色 */
.sidebar {
  width: 260px;
  background: #171717;
  color: #ececf1;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  border-right: 1px solid #2d2d2d;
}

.sidebar-brand {
  padding: 14px 14px 8px;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  width: 30px;
  height: 30px;
  background: #10a37f;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  color: #fff;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.sidebar-actions {
  padding: 0 14px 12px;
}

.new-chat-btn {
  width: 100%;
  background: transparent;
  border: 1px solid #4b4b4b;
  border-radius: 8px;
  font-weight: 500;
  color: #ececf1;
}

.new-chat-btn:hover {
  background: #2b2b2b;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 10px;
}

.session-group {
  margin-bottom: 16px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 6px 6px;
  font-size: 12px;
  color: #8e8ea0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.list-count {
  background: #2b2b2b;
  padding: 2px 6px;
  border-radius: 8px;
  font-size: 11px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 2px;
}

.session-item:hover {
  background: #2b2b2b;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.session-item.active {
  background: #10a37f;
}

.session-item.active .session-icon,
.session-item.active .session-name,
.session-item.active .session-time {
  color: #fff;
}

.session-icon {
  font-size: 16px;
  color: #8e8ea0;
  flex-shrink: 0;
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-name {
  margin: 0 0 2px;
  font-size: 13px;
  font-weight: 500;
  color: #ececf1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-time {
  margin: 0;
  font-size: 11px;
  color: #8e8ea0;
}

.session-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.2s;
}

.session-actions :deep(.el-button) {
  color: #8e8ea0;
  padding: 4px;
}

.session-actions :deep(.el-button:hover) {
  color: #fff;
}

/* 右侧主区域 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
}

.chat-header {
  height: 56px;
  background: #ffffff;
  border-bottom: 1px solid #e5e5e5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.header-title h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #202123;
}

.header-subtitle {
  margin: 0;
  font-size: 11px;
  color: #8e8ea0;
  font-family: monospace;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

/* 空状态 */
.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  text-align: center;
}

.empty-title {
  margin: 0 0 12px;
  font-size: 32px;
  font-weight: 600;
  color: #202123;
}

.empty-desc {
  margin: 0;
  color: #6e6e80;
  font-size: 15px;
}

/* 消息列表 */
.message-wrapper {
  display: flex;
  gap: 16px;
  padding: 20px 0;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

.message-wrapper.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.avatar {
  width: 30px;
  height: 30px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.user-avatar {
  background: #10a37f;
  color: #fff;
}

.ai-avatar {
  background: #202123;
  color: #fff;
}

.message-content-box {
  flex: 1;
  min-width: 0;
}

.message-wrapper.user .message-content-box {
  align-items: flex-end;
}

.message-meta {
  display: none;
}

.message-body {
  color: #374151;
  font-size: 15px;
  line-height: 1.6;
}

.message-wrapper.user .message-body {
  background: #f7f7f8;
  padding: 12px 16px;
  border-radius: 12px;
  color: #202123;
}

.raw-content {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
}

.tool-card {
  margin: 8px 0;
  padding: 12px 16px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  max-width: 640px;
  font-size: 14px;
  color: #374151;
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.tool-icon {
  font-size: 14px;
}

.tool-name {
  font-weight: 600;
  color: #111827;
}

.tool-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
  margin-left: auto;
}

.tool-status.running {
  background: #fef3c7;
  color: #b45309;
}

.tool-status.done {
  background: #d1fae5;
  color: #047857;
}

.tool-query {
  color: #4b5563;
  margin-bottom: 8px;
}

.tool-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  color: #374151;
  line-height: 1.5;
}

/* 输入区：GPT 风格底部居中 */
.chat-input-area {
  background: #ffffff;
  padding: 12px 20px 24px;
  flex-shrink: 0;
}

.input-wrapper {
  max-width: 768px;
  margin: 0 auto;
}

.input-container {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #ffffff;
  border-radius: 16px;
  padding: 8px 12px;
  border: 1px solid #d9d9e3;
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.06);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-container:focus-within {
  border-color: #10a37f;
  box-shadow: 0 0 15px rgba(16, 163, 127, 0.15);
}

.chat-input {
  flex: 1;
}

.chat-input :deep(.el-textarea__inner) {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 8px 0;
  font-size: 15px;
  color: #202123;
  resize: none;
}

.chat-input :deep(.el-textarea__inner::placeholder) {
  color: #8e8ea0;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.attach-btn {
  color: #8e8ea0;
}

.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  padding: 0;
  background: #10a37f;
  border: none;
}

.send-btn:hover {
  background: #0d8c6d;
}

.send-btn:disabled {
  background: #d9d9e3;
}

.input-footer {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.input-hint {
  margin: 0;
  font-size: 11px;
  color: #8e8ea0;
}

.thinking-wrapper {
  max-width: 800px;
  margin: 0 auto 20px;
  padding-left: 46px;
}

.header-action-text {
  margin-left: 4px;
}

.user-info {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 12px;
  padding: 4px 8px;
  cursor: pointer;
  border-radius: 6px;
  color: #475569;
  font-size: 14px;
  transition: background 0.2s;
}

.user-info:hover {
  background: #f7f7f8;
}

.user-phone {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-icon {
  font-size: 12px;
}

.log-toolbar {
  margin-bottom: 12px;
  display: flex;
  justify-content: flex-end;
}

.log-content {
  height: calc(100vh - 140px);
  overflow: auto;
  background: #f8fafc;
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

.stage-log-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stage-log-item {
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  border-left: 4px solid #94a3b8;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.stage-log-item.status-success {
  border-left-color: #22c55e;
}

.stage-log-item.status-failed {
  border-left-color: #ef4444;
}

.stage-log-item.status-running {
  border-left-color: #3b82f6;
}

.stage-log-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.stage-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}

.status-success .stage-status-dot {
  background: #22c55e;
}

.status-failed .stage-status-dot {
  background: #ef4444;
}

.status-running .stage-status-dot {
  background: #3b82f6;
}

.stage-name {
  flex: 1;
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
}

.stage-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
  background: #f1f5f9;
  color: #475569;
}

.status-success .stage-status {
  background: #dcfce7;
  color: #166534;
}

.status-failed .stage-status {
  background: #fee2e2;
  color: #991b1b;
}

.status-running .stage-status {
  background: #dbeafe;
  color: #1e40af;
}

.stage-log-meta {
  font-size: 12px;
  color: #64748b;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.stage-log-error {
  font-size: 12px;
  color: #991b1b;
  background: #fee2e2;
  padding: 8px 10px;
  border-radius: 6px;
  margin-top: 8px;
}

.stage-log-stats {
  font-size: 12px;
  color: #475569;
  margin-top: 6px;
}

.stage-log-fail-count {
  color: #dc2626;
  font-weight: 500;
}

.stage-log-children {
  margin-top: 8px;
  padding-left: 16px;
  border-left: 2px solid #e4e7ed;
}

.stage-log-child {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;
  color: #606266;
}

.stage-log-child .stage-duration {
  font-family: monospace;
}
</style>
