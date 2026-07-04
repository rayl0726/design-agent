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
