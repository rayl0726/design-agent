<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ project.name || '项目详情' }}</h2>
        <p class="page-subtitle">
          <el-tag :type="statusType(project.status)" effect="light" round size="small">
            {{ statusLabel(project.status) }}
          </el-tag>
          <span class="meta">创建于 {{ formatDate(project.createdAt) }}</span>
        </p>
      </div>
      <div class="header-actions">
        <router-link :to="`/project/${project.id}/export`">
          <el-button size="large" :icon="Download">导出文档</el-button>
        </router-link>
        <el-button
          v-if="project.status === 'INIT'"
          size="large"
          type="primary"
          :loading="starting"
          @click="handleStartWorkflow"
        >
          开始设计
        </el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" type="border-card" class="detail-tabs">
      <el-tab-pane label="L1 概念方向" name="l1">
        <div v-if="l1Data" class="proposal-section">
          <h3 class="section-title">方案标题</h3>
          <p class="section-body">{{ l1Data.story?.title || '暂无内容' }}</p>

          <h3 class="section-title">设计主题故事</h3>
          <p class="section-body">{{ l1Data.story?.story || '暂无内容' }}</p>

          <h3 class="section-title">核心概念</h3>
          <p class="section-body">{{ l1Data.story?.concept || '暂无内容' }}</p>

          <h3 class="section-title">场景叙事</h3>
          <p class="section-body">{{ l1Data.story?.narrative || '暂无内容' }}</p>

          <h3 class="section-title">关键词</h3>
          <div class="keyword-tags">
            <el-tag v-for="(kw, idx) in l1Data.story?.keywords || []" :key="idx" size="small">{{ kw }}</el-tag>
          </div>

          <h3 class="section-title">氛围描述</h3>
          <p class="section-body">{{ l1Data.atmosphere?.paragraph || '暂无内容' }}</p>

          <h3 class="section-title">视觉关键词</h3>
          <div class="keyword-tags">
            <el-tag v-for="(kw, idx) in l1Data.atmosphere?.visual || []" :key="idx" size="small">{{ kw }}</el-tag>
          </div>

          <h3 class="section-title">参考情绪板</h3>
          <div class="moodboard">
            <el-image
              v-for="(img, idx) in l1Data.moodboard?.generated_images || []"
              :key="idx"
              :src="img"
              fit="cover"
              class="mood-image"
              :preview-src-list="l1Data.moodboard?.generated_images || []"
            />
            <el-empty v-if="!(l1Data.moodboard?.generated_images && l1Data.moodboard.generated_images.length)" description="等待生成" />
          </div>

          <div v-if="project.status === 'L1_PENDING'" class="action-bar">
            <el-input
              v-model="feedback"
              type="textarea"
              :rows="3"
              placeholder="如有修改意见，请在此填写..."
              class="feedback-input"
            />
            <div class="action-buttons">
              <el-button size="large" @click="handleReject('L1')">驳回修改</el-button>
              <el-button size="large" type="primary" :loading="confirming" @click="handleConfirm('L1')">
                确认通过并生成 L2
              </el-button>
            </div>
          </div>
          
          <div v-if="project.status === 'L1_CONFIRMED' && !l2Data" class="action-bar">
            <div class="action-buttons">
              <el-button size="large" type="primary" :loading="generatingL2" @click="handleGenerateL2">
                生成 L2 视觉方案
              </el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="L1 概念方向尚未生成" />
      </el-tab-pane>

      <el-tab-pane label="L2 视觉方案" name="l2">
        <div v-if="l2Data" class="proposal-section">
          <h3 class="section-title">AI 概念效果图</h3>
          <div class="render-grid">
            <el-image
              v-for="(img, idx) in l2Data.concept_images || []"
              :key="idx"
              :src="img.path"
              fit="cover"
              class="render-image"
              :preview-src-list="(l2Data.concept_images || []).map(i => i.path)"
            />
            <el-empty v-if="!(l2Data.concept_images && l2Data.concept_images.length)" description="等待生成" />
          </div>

          <h3 class="section-title">色彩材质板</h3>
          <div v-if="l2Data.color_material_board" class="color-board">
            <el-image
              :src="l2Data.color_material_board"
              fit="contain"
              class="board-image"
            />
          </div>
          <el-empty v-else description="等待生成" />

          <div v-if="project.status === 'L2_PENDING'" class="action-bar">
            <el-input
              v-model="feedback"
              type="textarea"
              :rows="3"
              placeholder="如有修改意见，请在此填写..."
              class="feedback-input"
            />
            <div class="action-buttons">
              <el-button size="large" @click="handleReject('L2')">驳回修改</el-button>
              <el-button size="large" type="primary" :loading="confirming" @click="handleConfirm('L2')">
                确认通过并生成 L3
              </el-button>
            </div>
          </div>
          
          <div v-if="project.status === 'L2_CONFIRMED' && !l3Data" class="action-bar">
            <div class="action-buttons">
              <el-button size="large" type="primary" :loading="generatingL3" @click="handleGenerateL3">
                生成 L3 可落地方案
              </el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="L2 视觉方案尚未生成" />
      </el-tab-pane>

      <el-tab-pane label="L3 可落地方案" name="l3">
        <div v-if="l3Data" class="proposal-section">
          <h3 class="section-title">点位平面布置图</h3>
          <div v-if="l3Data.layout_annotation" class="layout-section">
            <div v-if="l3Data.layout_annotation.layout_image" class="layout-image-wrapper">
              <el-image
                :src="l3Data.layout_annotation.layout_image"
                fit="contain"
                class="layout-image"
              />
            </div>
            <div v-else-if="l3Data.layout_annotation.layout_svg" class="layout-svg-wrapper">
              <div v-html="l3Data.layout_annotation.layout_svg" class="svg-preview" />
            </div>
            <p v-if="l3Data.layout_annotation.note" class="layout-note">{{ l3Data.layout_annotation.note }}</p>
          </div>
          <el-empty v-else description="等待生成" />

          <h3 class="section-title">物料清单</h3>
          <el-table :data="l3Data.material_list || []" style="width: 100%" stripe>
            <el-table-column prop="name" label="材料名称" min-width="160" />
            <el-table-column prop="size" label="规格尺寸" min-width="120" />
            <el-table-column prop="quantity" label="数量" width="100" />
            <el-table-column prop="unit_price" label="单价" width="120" />
            <el-table-column prop="total_price" label="小计" width="120" />
          </el-table>

          <h3 class="section-title">预算表</h3>
          <div class="budget-card">
            <div class="budget-row">
              <span>材料费用</span>
              <strong>¥{{ l3Data.budget?.material_cost?.toLocaleString() || 0 }}</strong>
            </div>
            <div class="budget-row">
              <span>制作费用</span>
              <strong>¥{{ l3Data.budget?.production_cost?.toLocaleString() || 0 }}</strong>
            </div>
            <div class="budget-row">
              <span>安装费用</span>
              <strong>¥{{ l3Data.budget?.installation_cost?.toLocaleString() || 0 }}</strong>
            </div>
            <div class="budget-row">
              <span>设计费用</span>
              <strong>¥{{ l3Data.budget?.design_fee?.toLocaleString() || 0 }}</strong>
            </div>
            <el-divider />
            <div class="budget-row total">
              <span>总预算</span>
              <strong>¥{{ l3Data.budget?.total?.toLocaleString() || 0 }}</strong>
            </div>
          </div>

          <div v-if="project.status === 'L3_PENDING'" class="action-bar">
            <el-input
              v-model="feedback"
              type="textarea"
              :rows="3"
              placeholder="如有修改意见，请在此填写..."
              class="feedback-input"
            />
            <div class="action-buttons">
              <el-button size="large" @click="handleReject('L3')">驳回修改</el-button>
              <el-button size="large" type="primary" @click="handleConfirm('L3')">
                确认通过
              </el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="L3 可落地方案尚未生成" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Download } from '@element-plus/icons-vue'
import { projectApi } from '../api/client.js'
import { ElMessage } from 'element-plus'

const route = useRoute()
const activeTab = ref('l1')
const feedback = ref('')
const starting = ref(false)
const confirming = ref(false)
const generatingL2 = ref(false)
const generatingL3 = ref(false)

const project = ref({})
const l1Data = ref(null)
const l2Data = ref(null)
const l3Data = ref(null)

const statusMap = {
  INIT: { label: '初始化', type: 'info' },
  PARSING: { label: '解析中', type: '' },
  L1_PENDING: { label: 'L1 待确认', type: 'warning' },
  L1_CONFIRMED: { label: 'L1 已确认', type: 'success' },
  L2_PENDING: { label: 'L2 待确认', type: 'warning' },
  L2_CONFIRMED: { label: 'L2 已确认', type: 'success' },
  L3_PENDING: { label: 'L3 待确认', type: 'warning' },
  L3_CONFIRMED: { label: '已完成', type: 'success' },
  FAILED: { label: '失败', type: 'danger' },
}

const statusLabel = (s) => statusMap[s]?.label || s
const statusType = (s) => statusMap[s]?.type || 'info'
const formatDate = (d) => (d ? new Date(d).toLocaleString('zh-CN') : '-')

const formatImagePath = (path) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  if (path.startsWith('/')) return `http://localhost:8080${path}`
  if (path.startsWith('data/')) {
    return `http://localhost:8000/${path}`
  }
  return `http://localhost:8000/data/images/${path}`
}

const fetchProject = async () => {
  try {
    const res = await projectApi.get(route.params.id)
    project.value = res.data
    
    if (res.data.l1OutputJson) {
      l1Data.value = JSON.parse(res.data.l1OutputJson)
      if (l1Data.value.moodboard && l1Data.value.moodboard.generated_images) {
        l1Data.value.moodboard.generated_images = l1Data.value.moodboard.generated_images.map(
          img => formatImagePath(img)
        )
      }
    } else {
      l1Data.value = null
    }
    
    if (res.data.l2OutputJson) {
      l2Data.value = JSON.parse(res.data.l2OutputJson)
      if (l2Data.value.concept_images) {
        l2Data.value.concept_images = l2Data.value.concept_images.map(img => ({
          ...img,
          path: formatImagePath(img.path)
        }))
      }
      if (l2Data.value.color_material_board) {
        l2Data.value.color_material_board = formatImagePath(l2Data.value.color_material_board)
      }
    } else {
      l2Data.value = null
    }
    
    if (res.data.l3OutputJson) {
      l3Data.value = JSON.parse(res.data.l3OutputJson)
      if (l3Data.value.layout_annotation && l3Data.value.layout_annotation.layout_image) {
        l3Data.value.layout_annotation.layout_image = formatImagePath(l3Data.value.layout_annotation.layout_image)
      }
    } else {
      l3Data.value = null
    }
  } catch (e) {
    console.error(e)
  }
}

const handleStartWorkflow = async () => {
  try {
    starting.value = true
    await projectApi.startWorkflow(project.value.id, 'L3')
    ElMessage.success('设计流程已启动，正在生成方案...')
    setTimeout(fetchProject, 3000)
  } catch (e) {
    ElMessage.error('启动失败：' + (e.response?.data?.message || e.message))
  } finally {
    starting.value = false
  }
}

const handleConfirm = async (level) => {
  try {
    confirming.value = true
    await projectApi.confirm(project.value.id, level, feedback.value)
    ElMessage.success(`L${level.replace('L', '')} 已确认，正在生成下一阶段方案...`)
    await fetchProject()
    feedback.value = ''
    if (level === 'L1') {
      activeTab.value = 'l2'
    } else if (level === 'L2') {
      activeTab.value = 'l3'
    }
  } catch (e) {
    ElMessage.error('操作失败')
  } finally {
    confirming.value = false
  }
}

const handleGenerateL2 = async () => {
  try {
    generatingL2.value = true
    await projectApi.confirm(project.value.id, 'L1', '')
    ElMessage.success('正在生成 L2 视觉方案...')
    await fetchProject()
    activeTab.value = 'l2'
  } catch (e) {
    ElMessage.error('生成失败')
  } finally {
    generatingL2.value = false
  }
}

const handleGenerateL3 = async () => {
  try {
    generatingL3.value = true
    await projectApi.confirm(project.value.id, 'L2', '')
    ElMessage.success('正在生成 L3 可落地方案...')
    await fetchProject()
    activeTab.value = 'l3'
  } catch (e) {
    ElMessage.error('生成失败')
  } finally {
    generatingL3.value = false
  }
}

const handleReject = async (level) => {
  try {
    await projectApi.reject(project.value.id, level, feedback.value)
    ElMessage.info('已驳回，等待修改')
    await fetchProject()
    feedback.value = ''
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

onMounted(fetchProject)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.page-subtitle {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.meta {
  font-size: 13px;
  color: #888;
}

.detail-tabs {
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.detail-tabs :deep(.el-tabs__header) {
  background: #fafafa;
  border-bottom: 1px solid #eee;
}

.detail-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
  padding: 0 28px;
  height: 52px;
  line-height: 52px;
}

.proposal-section {
  padding: 8px 16px 24px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 24px 0 12px;
}

.section-body {
  font-size: 15px;
  line-height: 1.8;
  color: #444;
  white-space: pre-wrap;
}

.keyword-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.moodboard,
.render-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.mood-image,
.render-image {
  width: 100%;
  height: 180px;
  border-radius: 12px;
  object-fit: cover;
}

.palette {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.palette-item {
  width: 100px;
  height: 100px;
  border-radius: 12px;
  display: flex;
  align-items: flex-end;
  padding: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.palette-item span {
  font-size: 11px;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
  font-weight: 500;
}

.layout-image {
  width: 100%;
  max-height: 500px;
  border-radius: 12px;
  background: #f5f5f7;
}

.budget-card {
  background: #fafafa;
  border-radius: 12px;
  padding: 24px;
  max-width: 480px;
}

.budget-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  font-size: 14px;
  color: #555;
}

.budget-row.total {
  font-size: 16px;
  color: #1a1a1a;
  font-weight: 600;
}

.action-bar {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid #eee;
}

.feedback-input {
  margin-bottom: 16px;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
