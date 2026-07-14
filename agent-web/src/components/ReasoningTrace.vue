<template>
  <div class="reasoning-trace">
    <div class="summary" @click="expanded = !expanded">
      <el-icon class="trace-icon"><Cpu /></el-icon>
      <span>思考过程</span>
      <el-icon class="expand-icon" :class="{ expanded }"><ArrowDown /></el-icon>
    </div>
    <div v-if="expanded" class="details">
      <div
        v-for="(item, idx) in trace"
        :key="idx"
        class="trace-item"
        :class="item.type"
      >
        <span class="trace-type">{{ formatType(item.type) }}</span>
        <span class="trace-content">{{ item.content || item.tool_name || item.reason || '-' }}</span>
      </div>
      <div v-if="trace.length === 0" class="trace-empty">暂无推理记录</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Cpu, ArrowDown } from '@element-plus/icons-vue'
import type { TraceItem } from '@/types/agent'

defineProps<{ trace: TraceItem[] }>()

const expanded = ref(false)

const typeLabels: Record<string, string> = {
  thought: '思考',
  tool_call: '工具',
  observation: '观察',
  error: '错误',
}

const formatType = (type?: string) => typeLabels[type || ''] || type || '未知'
</script>

<style scoped>
.reasoning-trace {
  margin: 8px 0;
  border-radius: 8px;
  background: #f5f7fa;
  overflow: hidden;
}

.summary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  cursor: pointer;
  color: #606266;
  font-size: 13px;
  user-select: none;
}

.summary:hover {
  color: #409eff;
}

.trace-icon {
  font-size: 14px;
}

.expand-icon {
  margin-left: auto;
  transition: transform 0.2s ease;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.details {
  padding: 0 12px 12px;
}

.trace-item {
  display: flex;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
  border-bottom: 1px dashed #e4e7ed;
}

.trace-item:last-child {
  border-bottom: none;
}

.trace-type {
  flex-shrink: 0;
  width: 48px;
  color: #909399;
}

.trace-content {
  color: #303133;
  word-break: break-word;
}

.trace-item.error .trace-content {
  color: #f56c6c;
}

.trace-empty {
  padding: 8px 0;
  color: #909399;
  font-size: 13px;
}
</style>
