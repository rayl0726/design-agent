<template>
  <div v-if="toolCallInfo" class="tool-call-fallback">
    <div class="tool-call-label">工具调用</div>
    <div class="tool-call-query" v-if="toolCallInfo.query">查询：{{ toolCallInfo.query }}</div>
    <pre>{{ toolCallInfo.raw }}</pre>
  </div>
  <div v-else class="text-message">{{ content }}</div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ content: String })

const toolCallInfo = computed(() => {
  if (!props.content || !props.content.includes('<tool_call>')) return null
  const match = props.content.match(/<tool_call>([\s\S]*?)<\/tool_call>/)
  const raw = match ? match[1] : props.content
  const queryMatch = raw.match(/<arg_key>query<\/arg_key>\s*<arg_value>([\s\S]*?)<\/arg_value>/)
  return { raw, query: queryMatch ? queryMatch[1].trim() : '' }
})
</script>

<style scoped>
.text-message {
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.tool-call-fallback {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 14px;
  color: #374151;
}

.tool-call-label {
  font-weight: 600;
  color: #111827;
  margin-bottom: 6px;
}

.tool-call-query {
  color: #4b5563;
  margin-bottom: 6px;
}

.tool-call-fallback pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  color: #6b7280;
  font-size: 12px;
}
</style>
