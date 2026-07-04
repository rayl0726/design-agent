<template>
  <div class="idea-gallery">
    <p class="gallery-title">已生成 {{ ideas.length }} 个创意方向：</p>
    <div class="cards-grid">
      <div v-for="(idea, idx) in ideas" :key="idx" class="idea-card">
        <h4 class="idea-title">{{ idea.title || `创意 ${idx + 1}` }}</h4>
        <p class="idea-theme"><strong>主题：</strong>{{ idea.theme || idea.concept || '暂无' }}</p>
        <p class="idea-style"><strong>风格：</strong>{{ idea.style || '暂无' }}</p>
        <div v-if="idea.colorPalette && idea.colorPalette.length" class="color-palette">
          <span
            v-for="(c, i) in idea.colorPalette"
            :key="i"
            class="color-dot"
            :style="{ background: c.hex || c }"
            :title="c.name || c"
          />
        </div>
        <p class="idea-summary">{{ idea.summary || idea.story || '' }}</p>
        <el-button size="small" type="primary" @click="$emit('select', idx)">基于这个创意继续</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ ideas: Array })
defineEmits(['select'])
</script>

<style scoped>
.idea-gallery {
  width: 100%;
}
.gallery-title {
  font-weight: 500;
  margin-bottom: 12px;
}
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.idea-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: 16px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.idea-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}
.idea-title {
  margin: 0 0 10px;
  font-size: 16px;
  color: #303133;
}
.idea-theme,
.idea-style,
.idea-summary {
  margin: 6px 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}
.color-palette {
  display: flex;
  gap: 8px;
  margin: 10px 0;
}
.color-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid #dcdfe6;
}
</style>
