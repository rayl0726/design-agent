<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">导出文档</h2>
        <p class="page-subtitle">选择格式下载完整方案文档</p>
      </div>
    </div>

    <div class="export-grid">
      <div class="export-card" @click="download('html')">
        <div class="export-icon html-icon">
          <el-icon :size="32"><Document /></el-icon>
        </div>
        <h3>HTML 网页</h3>
        <p>适合在线浏览和分享，自适应多端显示</p>
        <el-button type="primary" text>立即下载</el-button>
      </div>

      <div class="export-card" @click="download('ppt')">
        <div class="export-icon ppt-icon">
          <el-icon :size="32"><DataAnalysis /></el-icon>
        </div>
        <h3>PPT 演示文稿</h3>
        <p>适合向甲方汇报展示，含完整配图</p>
        <el-button type="primary" text>立即下载</el-button>
      </div>

      <div class="export-card" @click="download('pdf')">
        <div class="export-icon pdf-icon">
          <el-icon :size="32"><Collection /></el-icon>
        </div>
        <h3>PDF 文档</h3>
        <p>适合打印和归档，版式固定</p>
        <el-button type="primary" text>立即下载</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { Document, DataAnalysis, Collection } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const route = useRoute()

const download = (format) => {
  const id = route.params.id
  const url = `http://localhost:8080/api/v1/projects/${id}/export?format=${format}`
  window.open(url, '_blank')
  ElMessage.success(`开始下载 ${format.toUpperCase()}`)
}
</script>

<style scoped>
.page-header {
  margin-bottom: 32px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #888;
  margin-top: 6px;
}

.export-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.export-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  border: 1px solid transparent;
}

.export-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0,0,0,0.08);
  border-color: #eee;
}

.export-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  color: #fff;
}

.html-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.ppt-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.pdf-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.export-card h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px;
}

.export-card p {
  font-size: 13px;
  color: #888;
  margin: 0 0 20px;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .export-grid {
    grid-template-columns: 1fr;
  }
}
</style>
