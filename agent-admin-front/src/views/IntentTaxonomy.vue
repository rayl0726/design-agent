<template>
  <div class="intent-taxonomy">
    <el-tabs v-model="activeMainTab" class="main-tabs">
      <!-- 词库浏览 -->
      <el-tab-pane label="词库浏览" name="browse">
        <div class="toolbar">
          <el-select
            v-model="activeCategory"
            placeholder="选择类别"
            style="width: 200px"
            @change="handleCategoryChange"
          >
            <el-option
              v-for="cat in categories"
              :key="cat.key"
              :label="cat.label"
              :value="cat.key"
            />
          </el-select>
          <el-button :icon="Refresh" @click="loadTaxonomy" :loading="loading">
            刷新
          </el-button>
        </div>

        <el-table
          :data="currentEntries"
          v-loading="loading"
          border
          stripe
          style="width: 100%"
        >
          <el-table-column label="序号" type="index" width="70" align="center" />
          <el-table-column label="名称" prop="name" min-width="160">
            <template #default="{ row }">
              <span class="entry-name">{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column label="别名" min-width="360">
            <template #default="{ row }">
              <div class="alias-list">
                <el-tag
                  v-for="alias in row.aliases"
                  :key="alias"
                  type="info"
                  effect="plain"
                  class="alias-tag"
                  disable-transitions
                >
                  {{ alias }}
                </el-tag>
                <span v-if="!row.aliases || row.aliases.length === 0" class="empty-aliases">
                  暂无别名
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" align="center" fixed="right">
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                :icon="Plus"
                @click="openAddAliasDialog(row)"
              >
                添加别名
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 别名提议 -->
      <el-tab-pane name="proposals">
        <template #label>
          <span>别名提议</span>
          <el-badge
            v-if="proposals.length > 0"
            :value="proposals.length"
            class="proposal-badge"
          />
        </template>

        <div class="toolbar">
          <el-button :icon="Refresh" @click="loadProposals" :loading="proposalsLoading">
            刷新
          </el-button>
        </div>

        <el-table
          :data="proposals"
          v-loading="proposalsLoading"
          border
          stripe
          style="width: 100%"
        >
          <el-table-column label="序号" type="index" width="70" align="center" />
          <el-table-column label="类别" width="140">
            <template #default="{ row }">
              <el-tag type="warning" effect="plain">
                {{ categoryLabel(row.category) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="规范名" prop="canonical" min-width="160" />
          <el-table-column label="提议别名" prop="proposedAlias" min-width="140">
            <template #default="{ row }">
              <el-tag type="success">{{ row.proposedAlias }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="原值" prop="originalValue" min-width="140" />
          <el-table-column label="修正值" prop="correctedValue" min-width="160" />
          <el-table-column label="操作" width="180" align="center" fixed="right">
            <template #default="{ row }">
              <el-button
                type="success"
                size="small"
                :icon="Check"
                :loading="applyingId === row.id"
                @click="applyProposal(row)"
              >
                应用
              </el-button>
              <el-button
                size="small"
                :icon="Close"
                :loading="ignoringId === row.id"
                @click="ignoreProposal(row)"
              >
                忽略
              </el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无别名提议" :image-size="120" />
          </template>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加别名对话框 -->
    <el-dialog
      v-model="addAliasDialogVisible"
      title="添加别名"
      width="480px"
      :close-on-click-modal="false"
      @closed="resetAddAliasForm"
    >
      <el-form :model="addAliasForm" label-width="90px" ref="addAliasFormRef" :rules="addAliasRules">
        <el-form-item label="类别">
          <el-input :model-value="addAliasForm.categoryLabel" readonly />
        </el-form-item>
        <el-form-item label="名称">
          <el-input :model-value="addAliasForm.canonical" readonly />
        </el-form-item>
        <el-form-item label="新别名" prop="alias">
          <el-input
            v-model="addAliasForm.alias"
            placeholder="请输入新别名"
            clearable
            @keyup.enter="confirmAddAlias"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addAliasDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="addingAlias"
          @click="confirmAddAlias"
        >
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Check, Close, Refresh } from '@element-plus/icons-vue'
import client from '../api/client'

// 类别配置：key 对应词库字段，apiCategory 对应接口 category 值
const categories = [
  { key: 'spaceTypes', label: '空间类型', apiCategory: 'space_type' },
  { key: 'points', label: '点位', apiCategory: 'point' },
  { key: 'budgetLevels', label: '预算等级', apiCategory: 'budget_level' },
  { key: 'styles', label: '风格', apiCategory: 'style' },
  { key: 'materials', label: '材料', apiCategory: 'material' }
]

const activeMainTab = ref('browse')
const activeCategory = ref('spaceTypes')

// 词库数据
const taxonomy = ref({
  version: '',
  spaceTypes: [],
  points: [],
  budgetLevels: [],
  styles: [],
  materials: []
})
const loading = ref(false)

// 别名提议
const proposals = ref([])
const proposalsLoading = ref(false)
const applyingId = ref('')
const ignoringId = ref('')

// 添加别名对话框
const addAliasDialogVisible = ref(false)
const addingAlias = ref(false)
const addAliasFormRef = ref(null)
const addAliasForm = ref({
  category: '',
  categoryLabel: '',
  canonical: '',
  alias: ''
})
const addAliasRules = {
  alias: [
    { required: true, message: '请输入新别名', trigger: 'blur' },
    { min: 1, max: 50, message: '别名长度需在 1-50 个字符之间', trigger: 'blur' }
  ]
}

// 当前类别的词条列表
const currentEntries = computed(() => {
  return taxonomy.value[activeCategory.value] || []
})

// 根据 apiCategory 获取中文标签
function categoryLabel(apiCategory) {
  const cat = categories.find(c => c.apiCategory === apiCategory)
  return cat ? cat.label : apiCategory
}

// 根据 key 获取 apiCategory
function apiCategoryByKey(key) {
  const cat = categories.find(c => c.key === key)
  return cat ? cat.apiCategory : ''
}

// 加载词库
async function loadTaxonomy() {
  loading.value = true
  try {
    const data = await client.get('/intent-taxonomy')
    taxonomy.value = {
      version: data.version || '',
      spaceTypes: data.spaceTypes || [],
      points: data.points || [],
      budgetLevels: data.budgetLevels || [],
      styles: data.styles || [],
      materials: data.materials || []
    }
  } catch (e) {
    // 错误已由拦截器统一处理
  } finally {
    loading.value = false
  }
}

// 加载别名提议
async function loadProposals() {
  proposalsLoading.value = true
  try {
    const data = await client.get('/intent-taxonomy/alias-proposals')
    proposals.value = Array.isArray(data) ? data : []
  } catch (e) {
    // 错误已由拦截器统一处理
  } finally {
    proposalsLoading.value = false
  }
}

function handleCategoryChange() {
  // 类别切换无需额外请求，数据已在本地
}

// 打开添加别名对话框
function openAddAliasDialog(row) {
  addAliasForm.value = {
    category: apiCategoryByKey(activeCategory.value),
    categoryLabel: categoryLabel(apiCategoryByKey(activeCategory.value)),
    canonical: row.name,
    alias: ''
  }
  addAliasDialogVisible.value = true
}

// 重置表单
function resetAddAliasForm() {
  addAliasForm.value = {
    category: '',
    categoryLabel: '',
    canonical: '',
    alias: ''
  }
  addAliasFormRef.value?.clearValidate()
}

// 确认添加别名
async function confirmAddAlias() {
  if (!addAliasFormRef.value) return
  try {
    await addAliasFormRef.value.validate()
  } catch {
    return
  }

  addingAlias.value = true
  try {
    await client.post('/intent-taxonomy/add-alias', {
      category: addAliasForm.value.category,
      canonical: addAliasForm.value.canonical,
      alias: addAliasForm.value.alias.trim()
    })
    ElMessage.success('别名添加成功')
    addAliasDialogVisible.value = false
    // 刷新词库以展示新别名
    await loadTaxonomy()
  } catch (e) {
    // 错误已由拦截器统一处理
  } finally {
    addingAlias.value = false
  }
}

// 应用别名提议
async function applyProposal(row) {
  applyingId.value = row.id
  try {
    await client.post('/intent-taxonomy/apply-alias', {
      category: row.category,
      canonical: row.canonical,
      alias: row.proposedAlias,
      feedbackId: row.id
    })
    ElMessage.success('已应用别名提议')
    // 从列表移除该项
    proposals.value = proposals.value.filter(p => p.id !== row.id)
    // 刷新词库以展示最新数据
    await loadTaxonomy()
  } catch (e) {
    // 错误已由拦截器统一处理
  } finally {
    applyingId.value = ''
  }
}

// 忽略别名提议
async function ignoreProposal(row) {
  try {
    await ElMessageBox.confirm(
      `确定忽略该别名提议（${row.proposedAlias}）吗？`,
      '确认忽略',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }

  ignoringId.value = row.id
  try {
    // 忽略操作：仅在前端移除，无对应后端接口
    proposals.value = proposals.value.filter(p => p.id !== row.id)
    ElMessage.success('已忽略该提议')
  } finally {
    ignoringId.value = ''
  }
}

onMounted(() => {
  loadTaxonomy()
  loadProposals()
})
</script>

<style scoped>
.intent-taxonomy {
  background-color: #fff;
  padding: 20px;
  border-radius: 4px;
  min-height: calc(100vh - 140px);
}

.main-tabs {
  width: 100%;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.entry-name {
  font-weight: 600;
  color: #303133;
}

.alias-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.alias-tag {
  margin: 0;
}

.empty-aliases {
  color: #c0c4cc;
  font-size: 13px;
}

.proposal-badge {
  margin-left: 6px;
  margin-top: -2px;
}

:deep(.el-badge__content) {
  font-size: 12px;
}
</style>
