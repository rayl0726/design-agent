<template>
  <div class="agent-selector">
    <button
      v-if="modelValue === 'generic'"
      data-testid="meichen"
      class="agent-chip"
      @click="$emit('select', 'meichen')"
    >
      美陈 Agent
    </button>
    <button
      v-else
      data-testid="generic"
      class="agent-chip active"
      @click="$emit('select', 'generic')"
    >
      通用 Agent
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{ modelValue: string }>()
defineEmits<{ (e: 'select', agentType: string): void }>()
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
  border: 1px solid #e0e0e0;
  background: #fff;
  color: #666;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s ease;
}

.agent-chip:hover {
  border-color: #10a37f;
  color: #10a37f;
}

.agent-chip.active {
  background: #10a37f;
  border-color: #10a37f;
  color: #fff;
}
</style>
