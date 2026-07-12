<template>
  <div class="prompt-templates">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">Prompt 模板管理</span>
          <el-button :loading="loading" @click="loadTemplates">
            <el-icon><Refresh /></el-icon>
            <span>刷新</span>
          </el-button>
        </div>
      </template>

      <el-table
        :data="templates"
        v-loading="loading"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column label="模板名称" min-width="220">
          <template #default="{ row }">
            <span class="template-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="适用空间类型"
          prop="spaceType"
          min-width="220"
          show-overflow-tooltip
        />
        <el-table-column label="版本" width="110" align="center">
          <template #default="{ row }">
            <el-tag type="info" effect="plain">{{ row.version }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openPerformance(row)">
              <el-icon><DataLine /></el-icon>
              <span>查看效果</span>
            </el-button>
            <el-button size="small" type="primary" @click="openPreview(row)">
              <el-icon><View /></el-icon>
              <span>预览</span>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 模板效果统计对话框 -->
    <el-dialog
      v-model="perfDialogVisible"
      title="模板效果统计"
      width="580px"
      destroy-on-close
    >
      <div v-loading="perfLoading" class="perf-body">
        <el-empty
          v-if="!perfLoading && !hasPerfData"
          description="暂无效果数据"
        />
        <template v-else-if="performance">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="模板名称">
              {{ performance.templateName || currentTemplate?.name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="总反馈数">
              {{ performance.totalFeedbacks }}
            </el-descriptions-item>
            <el-descriptions-item label="正面反馈">
              <span class="count-positive">{{ performance.positiveCount }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="负面反馈">
              <span class="count-negative">{{ performance.negativeCount }}</span>
            </el-descriptions-item>
          </el-descriptions>

          <div class="rate-section">
            <div class="rate-label">正面率</div>
            <el-progress
              :percentage="positivePercentage"
              :color="rateColor"
              :stroke-width="18"
              :text-inside="true"
            />
          </div>
        </template>
      </div>
    </el-dialog>

    <!-- Prompt 预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      title="Prompt 预览"
      width="760px"
      destroy-on-close
    >
      <el-form :model="previewForm" label-width="100px">
        <el-form-item label="模板名称">
          <el-input v-model="previewForm.templateName" readonly />
        </el-form-item>
        <el-form-item label="主题">
          <el-input
            v-model="previewForm.theme"
            placeholder="请输入主题"
            clearable
          />
        </el-form-item>
        <el-form-item label="空间类型">
          <el-input
            v-model="previewForm.spaceType"
            placeholder="请输入空间类型"
            clearable
          />
        </el-form-item>
        <el-form-item label="预算等级">
          <el-select v-model="previewForm.budgetLevel" style="width: 100%">
            <el-option label="低 (low)" value="low" />
            <el-option label="中 (medium)" value="medium" />
            <el-option label="高 (high)" value="high" />
          </el-select>
        </el-form-item>
        <el-form-item label="点位名称">
          <el-input
            v-model="previewForm.pointName"
            placeholder="请输入点位名称"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="previewLoading"
            @click="doPreview"
          >
            <el-icon><VideoPlay /></el-icon>
            <span>预览</span>
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider v-if="previewResult || previewError" />

      <div v-if="previewError" class="preview-error">
        <el-alert
          :title="previewError"
          type="error"
          :closable="false"
          show-icon
        />
      </div>

      <div v-if="previewResult" class="preview-result" v-loading="previewLoading">
        <div class="result-tags">
          <el-tag type="info">
            版本: {{ previewResult.template_version || '-' }}
          </el-tag>
          <el-tag type="success">
            宽高比: {{ previewResult.aspect_ratio || '-' }}
          </el-tag>
        </div>

        <div class="result-item">
          <div class="result-label">Positive Prompt</div>
          <el-input
            type="textarea"
            :model-value="previewResult.positive"
            readonly
            :rows="5"
            resize="vertical"
          />
        </div>

        <div class="result-item">
          <div class="result-label">Negative Prompt</div>
          <el-input
            type="textarea"
            :model-value="previewResult.negative"
            readonly
            :rows="5"
            resize="vertical"
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'

// ---------- 模板列表 ----------
const loading = ref(false)
const templates = ref([])

async function loadTemplates() {
  loading.value = true
  try {
    const data = await client.get('/prompt-templates')
    templates.value = Array.isArray(data) ? data : []
  } catch (e) {
    // 错误提示已由 axios 拦截器统一处理
    templates.value = []
  } finally {
    loading.value = false
  }
}

// ---------- 模板效果统计 ----------
const perfDialogVisible = ref(false)
const perfLoading = ref(false)
const performance = ref(null)
const currentTemplate = ref(null)

/**
 * 后端实际返回的是数组（按版本聚合的多条记录），任务描述中为单个对象。
 * 这里对两种格式做兼容：若为数组则汇总求和，若为单对象则直接使用。
 */
function normalizePerformance(data) {
  const items = Array.isArray(data) ? data : [data]
  let total = 0
  let positive = 0
  let negative = 0
  let name = ''
  for (const item of items) {
    if (!item) continue
    const t = item.totalCount ?? item.totalFeedbacks ?? 0
    const p = item.positiveCount ?? 0
    const n = item.negativeCount ?? 0
    total += Number(t) || 0
    positive += Number(p) || 0
    negative += Number(n) || 0
    if (!name) name = item.promptTemplateVersion || item.templateName || ''
  }
  const rate = total > 0 ? positive / total : 0
  return {
    templateName: name,
    totalFeedbacks: total,
    positiveCount: positive,
    negativeCount: negative,
    positiveRate: rate
  }
}

const hasPerfData = computed(
  () => performance.value && performance.value.totalFeedbacks > 0
)

const positivePercentage = computed(() => {
  if (!performance.value) return 0
  return Math.round(performance.value.positiveRate * 100)
})

const rateColor = computed(() => {
  const r = performance.value?.positiveRate ?? 0
  if (r >= 0.8) return '#67c23a'
  if (r >= 0.5) return '#e6a23c'
  return '#f56c6c'
})

async function openPerformance(row) {
  currentTemplate.value = row
  perfDialogVisible.value = true
  perfLoading.value = true
  performance.value = null
  try {
    const data = await client.get(
      `/prompt-templates/${encodeURIComponent(row.name)}/performance`
    )
    performance.value = normalizePerformance(data)
  } catch (e) {
    // 错误提示已由 axios 拦截器统一处理
    performance.value = null
  } finally {
    perfLoading.value = false
  }
}

// ---------- Prompt 预览 ----------
const previewDialogVisible = ref(false)
const previewLoading = ref(false)
const previewResult = ref(null)
const previewError = ref('')

const previewForm = ref({
  templateName: '',
  theme: '圣诞节',
  spaceType: '购物中心中庭',
  budgetLevel: 'medium',
  pointName: '门头'
})

function openPreview(row) {
  currentTemplate.value = row
  // 默认填充模板对应的空间类型（取第一个），无则回退到默认值
  const firstSpaceType =
    row.spaceType?.split(',')[0]?.trim() || '购物中心中庭'
  previewForm.value = {
    templateName: row.name,
    theme: '圣诞节',
    spaceType: firstSpaceType,
    budgetLevel: 'medium',
    pointName: '门头'
  }
  previewResult.value = null
  previewError.value = ''
  previewDialogVisible.value = true
}

async function doPreview() {
  previewLoading.value = true
  previewResult.value = null
  previewError.value = ''
  try {
    const data = await client.post('/prompt-templates/preview', {
      ...previewForm.value
    })
    previewResult.value = data
    ElMessage.success('预览生成成功')
  } catch (e) {
    // agent-core 可能未启动，此处给出更友好的提示
    const msg =
      e.response?.data?.message ||
      e.message ||
      '预览失败，可能 agent-core 未启动'
    previewError.value = msg
  } finally {
    previewLoading.value = false
  }
}

// ---------- 初始化 ----------
onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.prompt-templates {
  width: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.template-name {
  font-weight: 600;
  color: #409eff;
}

/* 效果统计 */
.perf-body {
  min-height: 120px;
}

.count-positive {
  color: #67c23a;
  font-weight: 600;
}

.count-negative {
  color: #f56c6c;
  font-weight: 600;
}

.rate-section {
  margin-top: 20px;
}

.rate-label {
  margin-bottom: 10px;
  font-size: 14px;
  color: #606266;
}

/* 预览结果 */
.preview-error {
  margin-bottom: 16px;
}

.preview-result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-tags {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.result-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.result-label {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}
</style>
