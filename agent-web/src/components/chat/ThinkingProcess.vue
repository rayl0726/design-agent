<template>
  <div class="thinking-process">
    <div class="thinking-header" @click="expanded = !expanded">
      <div class="thinking-title">
        <el-icon v-if="isRunning" class="thinking-icon spinning"><Loading /></el-icon>
        <el-icon v-else class="thinking-icon"><Opportunity /></el-icon>
        <span>{{ isRunning ? 'AI 正在思考...' : `思考过程（${completedSteps}/${logs.length}）` }}</span>
      </div>
      <div class="thinking-actions">
        <span v-if="isRunning" class="thinking-current">{{ currentStep }}</span>
        <el-icon class="expand-icon" :class="{ expanded }"><ArrowDown /></el-icon>
      </div>
    </div>
    <div v-show="expanded" class="thinking-body">
      <div
        v-for="log in logs"
        :key="log.id"
        class="thinking-item"
        :class="log.status"
      >
        <div class="thinking-dot">
          <el-icon v-if="log.status === 'completed'" class="status-icon success"><Check /></el-icon>
          <el-icon v-else-if="log.status === 'failed'" class="status-icon error"><Close /></el-icon>
          <span v-else class="status-pulse"></span>
        </div>
        <div class="thinking-info">
          <p class="thinking-message">{{ log.message }}</p>
          <p class="thinking-time">{{ formatTime(log.createdAt) }}</p>
        </div>
      </div>
      <div v-if="logs.length === 0" class="thinking-empty">
        暂无思考记录
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Loading, Opportunity, ArrowDown, Check, Close } from '@element-plus/icons-vue'

const props = defineProps({
  logs: { type: Array, default: () => [] },
  isRunning: { type: Boolean, default: false },
})

const expanded = ref(true)

const completedSteps = computed(() => props.logs.filter(l => l.status === 'completed').length)

const currentStep = computed(() => {
  const running = props.logs.find(l => l.status === 'started')
  return running ? running.message : '准备中...'
})

const formatTime = (str) => {
  if (!str) return ''
  return new Date(str).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<style scoped>
.thinking-process {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  max-width: 560px;
}

.thinking-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.thinking-header:hover {
  background: #f1f5f9;
}

.thinking-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}

.thinking-icon {
  font-size: 14px;
  color: #3b82f6;
}

.thinking-icon.spinning {
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.thinking-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.thinking-current {
  font-size: 12px;
  color: #64748b;
  max-width: 160px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.expand-icon {
  font-size: 12px;
  color: #94a3b8;
  transition: transform 0.2s;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.thinking-body {
  padding: 0 14px 12px;
}

.thinking-item {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px dashed #e2e8f0;
}

.thinking-item:last-child {
  border-bottom: none;
}

.thinking-dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.thinking-item.started .thinking-dot {
  background: #dbeafe;
}

.status-pulse {
  width: 6px;
  height: 6px;
  background: #3b82f6;
  border-radius: 50%;
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.status-icon {
  font-size: 10px;
}

.status-icon.success {
  color: #10b981;
}

.status-icon.error {
  color: #ef4444;
}

.thinking-info {
  flex: 1;
}

.thinking-message {
  margin: 0;
  font-size: 13px;
  color: #334155;
  line-height: 1.5;
}

.thinking-time {
  margin: 2px 0 0;
  font-size: 11px;
  color: #94a3b8;
}

.thinking-empty {
  padding: 12px 0;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
}
</style>
