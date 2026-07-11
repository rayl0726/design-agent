<template>
  <div class="recognition-debug">
    <div class="debug-header" @click="expanded = !expanded">
      <el-icon class="debug-icon"><View /></el-icon>
      <span class="debug-title">意图识别调试</span>
      <el-icon class="expand-icon" :class="{ expanded }"><ArrowDown /></el-icon>
    </div>
    <div v-show="expanded" class="debug-body">
      <div class="debug-section">
        <p class="section-label">输入文本</p>
        <p class="section-value">{{ summary.input_text }}</p>
      </div>
      <div class="debug-section">
        <p class="section-label">Trace ID</p>
        <p class="section-value mono">{{ summary.trace_id || '—' }}</p>
      </div>
      <div class="debug-section">
        <p class="section-label">识别字段</p>
        <div class="field-grid">
          <div v-for="field in parsedFields" :key="field.name" class="field-item">
            <span class="field-name">{{ field.name }}</span>
            <span class="field-value" :class="{ missing: !field.present }">{{ field.display }}</span>
            <span v-if="field.present" class="field-meta">{{ field.source }} · {{ (field.confidence * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>
      <div v-if="summary.discarded_fields && Object.keys(summary.discarded_fields).length > 0" class="debug-section warn">
        <p class="section-label">已丢弃字段</p>
        <div v-for="(value, key) in summary.discarded_fields" :key="key" class="discarded-item">
          <span class="field-name">{{ key }}</span>
          <span class="field-value rejected">{{ value }}</span>
        </div>
      </div>
      <div v-if="summary.missing_core_fields && summary.missing_core_fields.length > 0" class="debug-section warn">
        <p class="section-label">缺失核心字段</p>
        <p class="section-value">{{ summary.missing_core_fields.join('、') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { View, ArrowDown } from '@element-plus/icons-vue'

const props = defineProps({
  summary: { type: Object, default: () => ({}) },
})

const expanded = ref(false)

const FIELD_LABELS = {
  theme: '主题',
  space_type: '空间类型',
  budget: '预算',
  budget_level: '预算等级',
  style: '风格',
}

const parsedFields = computed(() => {
  const meta = props.summary.recognition_meta || {}
  return Object.entries(FIELD_LABELS).map(([key, label]) => {
    const source = meta[`${key}_source`]
    const confidence = meta[`${key}_confidence`] || 0
    const rawText = meta[`${key}_raw_text`]
    return {
      name: label,
      present: source != null,
      display: rawText || (source != null ? '已识别' : '未识别'),
      source: source || '—',
      confidence,
    }
  })
})
</script>

<style scoped>
.recognition-debug {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  max-width: 560px;
  margin-bottom: 12px;
}

.debug-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
}

.debug-header:hover {
  background: #e2e8f0;
}

.debug-icon {
  font-size: 13px;
  color: #64748b;
}

.debug-title {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
  flex: 1;
}

.expand-icon {
  font-size: 11px;
  color: #94a3b8;
  transition: transform 0.2s;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.debug-body {
  padding: 0 12px 10px;
}

.debug-section {
  padding: 6px 0;
  border-bottom: 1px dashed #cbd5e1;
}

.debug-section:last-child {
  border-bottom: none;
}

.debug-section.warn {
  background: #fef3c7;
  margin: 0 -12px;
  padding: 6px 12px;
}

.section-label {
  margin: 0 0 2px;
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
}

.section-value {
  margin: 0;
  font-size: 13px;
  color: #334155;
}

.section-value.mono {
  font-family: monospace;
  font-size: 11px;
  word-break: break-all;
}

.field-grid {
  display: grid;
  gap: 4px;
}

.field-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.field-name {
  color: #64748b;
  min-width: 60px;
}

.field-value {
  color: #1e293b;
  flex: 1;
}

.field-value.missing {
  color: #cbd5e1;
}

.field-value.rejected {
  color: #ef4444;
  text-decoration: line-through;
}

.field-meta {
  font-size: 10px;
  color: #94a3b8;
  font-family: monospace;
}

.discarded-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 2px 0;
}
</style>
