<template>
  <div class="feedback-list">
    <!-- 筛选栏 -->
    <el-form :inline="true" class="filter-bar">
      <el-form-item label="反馈类型">
        <el-select
          v-model="filters.feedbackType"
          placeholder="全部"
          clearable
          style="width: 180px"
        >
          <el-option label="全部" value="" />
          <el-option label="like" value="like" />
          <el-option label="dislike" value="dislike" />
          <el-option label="image_feedback" value="image_feedback" />
          <el-option label="intent_correction" value="intent_correction" />
        </el-select>
      </el-form-item>

      <el-form-item label="处理状态">
        <el-select
          v-model="filters.processed"
          placeholder="全部"
          clearable
          style="width: 140px"
        >
          <el-option label="全部" value="" />
          <el-option label="未处理" :value="false" />
          <el-option label="已处理" :value="true" />
        </el-select>
      </el-form-item>

      <el-form-item label="每页条数">
        <el-select v-model="filters.size" style="width: 100px">
          <el-option :value="10" label="10" />
          <el-option :value="20" label="20" />
          <el-option :value="50" label="50" />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="handleQuery">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 反馈列表表格 -->
    <el-table
      :data="tableData"
      v-loading="tableLoading"
      border
      stripe
      style="width: 100%"
    >
      <el-table-column label="反馈类型" width="140" align="center">
        <template #default="{ row }">
          <el-tag :type="feedbackTagType(row.feedbackType)">
            {{ row.feedbackType }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column
        label="评论内容"
        prop="comment"
        min-width="200"
        show-overflow-tooltip
      >
        <template #default="{ row }">
          {{ row.comment || '-' }}
        </template>
      </el-table-column>

      <el-table-column label="项目 ID" width="120" align="center">
        <template #default="{ row }">
          <span :title="row.projectId">
            {{ row.projectId ? row.projectId.slice(0, 8) : '-' }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="意图字段" width="140" align="center">
        <template #default="{ row }">
          <span v-if="row.feedbackType === 'intent_correction'">
            {{ row.intentField || '-' }}
          </span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>

      <el-table-column label="原值 → 修正值" min-width="220">
        <template #default="{ row }">
          <template v-if="row.feedbackType === 'intent_correction'">
            <span class="original-value">{{ row.originalValue || '-' }}</span>
            <el-icon class="arrow-icon"><Right /></el-icon>
            <span class="corrected-value">{{ row.correctedValue || '-' }}</span>
          </template>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>

      <el-table-column
        label="模板版本"
        prop="promptTemplateVersion"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          {{ row.promptTemplateVersion ?? '-' }}
        </template>
      </el-table-column>

      <el-table-column label="处理状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.processed ? 'success' : 'warning'">
            {{ row.processed ? '已处理' : '未处理' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="创建时间" width="160" align="center">
        <template #default="{ row }">
          {{ formatDateTime(row.createdAt) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="120" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="!row.processed"
            type="primary"
            size="small"
            :loading="processLoading && currentRow?.id === row.id"
            @click="openProcessDialog(row)"
          >
            标记已处理
          </el-button>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 标记已处理对话框 -->
    <el-dialog
      v-model="processDialogVisible"
      title="标记反馈为已处理"
      width="520px"
    >
      <div v-if="currentRow" class="process-summary">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="反馈 ID">
            {{ currentRow.publicId || currentRow.id }}
          </el-descriptions-item>
          <el-descriptions-item label="反馈类型">
            <el-tag :type="feedbackTagType(currentRow.feedbackType)" size="small">
              {{ currentRow.feedbackType }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="评论内容">
            {{ currentRow.comment || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="项目 ID">
            {{ currentRow.projectId }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDateTime(currentRow.createdAt) }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="notes-input">
          <label>处理备注（可选）</label>
          <el-input
            v-model="processNotes"
            type="textarea"
            :rows="4"
            placeholder="请输入处理备注..."
            maxlength="500"
            show-word-limit
          />
        </div>
      </div>

      <template #footer>
        <el-button @click="processDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="processLoading"
          @click="confirmProcess"
        >
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'

// 筛选条件
const filters = reactive({
  feedbackType: '',
  processed: '',
  size: 20
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 表格数据
const tableData = ref([])
const tableLoading = ref(false)

// 标记处理对话框
const processDialogVisible = ref(false)
const currentRow = ref(null)
const processNotes = ref('')
const processLoading = ref(false)

// 反馈类型对应的 tag 颜色
function feedbackTagType(type) {
  const map = {
    like: 'success',
    dislike: 'danger',
    image_feedback: 'warning',
    intent_correction: 'info'
  }
  return map[type] || 'info'
}

// 时间格式化 yyyy-MM-dd HH:mm
function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return dateStr
  const pad = (n) => String(n).padStart(2, '0')
  const year = date.getFullYear()
  const month = pad(date.getMonth() + 1)
  const day = pad(date.getDate())
  const hours = pad(date.getHours())
  const minutes = pad(date.getMinutes())
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

// 构建查询参数
function buildQueryParams() {
  const params = {
    page: pagination.page - 1,
    size: pagination.size
  }
  if (filters.feedbackType) {
    params.feedbackType = filters.feedbackType
  }
  if (filters.processed !== '' && filters.processed !== null) {
    params.processed = filters.processed
  }
  return params
}

// 加载数据
async function loadData() {
  tableLoading.value = true
  try {
    const res = await client.get('/feedbacks', { params: buildQueryParams() })
    tableData.value = res.content || []
    pagination.total = res.totalElements || 0
  } catch (e) {
    // 错误由 client 拦截器统一处理
  } finally {
    tableLoading.value = false
  }
}

// 查询
function handleQuery() {
  pagination.page = 1
  loadData()
}

// 重置
function handleReset() {
  filters.feedbackType = ''
  filters.processed = ''
  filters.size = 20
  pagination.page = 1
  pagination.size = 20
  loadData()
}

// 分页变化
function handlePageChange(page) {
  pagination.page = page
  loadData()
}

function handleSizeChange(size) {
  pagination.size = size
  filters.size = size
  pagination.page = 1
  loadData()
}

// 打开标记处理对话框
function openProcessDialog(row) {
  currentRow.value = row
  processNotes.value = ''
  processDialogVisible.value = true
}

// 确认标记已处理
async function confirmProcess() {
  if (!currentRow.value) return
  processLoading.value = true
  try {
    await client.post(`/feedbacks/${currentRow.value.id}/process`, {
      notes: processNotes.value || undefined
    })
    ElMessage.success('已标记为已处理')
    processDialogVisible.value = false
    loadData()
  } catch (e) {
    // 错误由 client 拦截器统一处理
  } finally {
    processLoading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.feedback-list {
  background-color: #fff;
  padding: 20px;
  border-radius: 4px;
}

.filter-bar {
  margin-bottom: 20px;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.text-muted {
  color: #c0c4cc;
}

.original-value {
  color: #f56c6c;
  text-decoration: line-through;
}

.corrected-value {
  color: #67c23a;
  font-weight: 500;
}

.arrow-icon {
  margin: 0 6px;
  color: #909399;
  vertical-align: middle;
}

.process-summary {
  margin-bottom: 10px;
}

.notes-input {
  margin-top: 16px;
}

.notes-input label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #606266;
}
</style>
