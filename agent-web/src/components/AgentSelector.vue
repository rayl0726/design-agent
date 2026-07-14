<template>
  <div class="agent-selector">
    <button
      v-for="agent in agents"
      :key="agent.id"
      :data-testid="agent.id"
      :class="['agent-chip', { active: modelValue === agent.id }]"
      @click="$emit('select', agent.id)"
    >
      {{ agent.name }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { AgentOption } from '@/types/agent'

defineProps<{ modelValue: string }>()
defineEmits<{ (e: 'select', agentType: string): void }>()

const agents: AgentOption[] = [
  { id: 'generic', name: '通用 Agent' },
  { id: 'meichen', name: '美陈 Agent' },
]
</script>

<style scoped>
.agent-selector {
  display: flex;
  gap: 8px;
  padding: 8px 0;
}

.agent-chip {
  padding: 6px 12px;
  border-radius: 16px;
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s ease;
}

.agent-chip:hover {
  border-color: #409eff;
  color: #409eff;
}

.agent-chip.active {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}
</style>
