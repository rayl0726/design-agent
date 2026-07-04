<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">项目列表</h2>
        <p class="page-subtitle">管理所有美陈设计项目</p>
      </div>
      <router-link to="/new">
        <el-button type="primary" size="large" :icon="Plus">新建项目</el-button>
      </router-link>
    </div>

    <div class="card">
      <el-table :data="projects" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="项目ID" width="140">
          <template #default="{ row }">
            <span class="project-id">{{ row.id.substring(0, 8) }}...</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="项目名称" min-width="200">
          <template #default="{ row }">
            <router-link :to="`/project/${row.id}`" class="project-link">
              {{ row.name }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="160">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" effect="light" round>
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <router-link :to="`/project/${row.id}`">
              <el-button link type="primary">查看</el-button>
            </router-link>
            <router-link :to="`/project/${row.id}/export`">
              <el-button link type="primary">导出</el-button>
            </router-link>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && projects.length === 0" description="暂无项目，点击右上角新建" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { projectApi } from '../api/client.js'

const loading = ref(true)
const projects = ref([])

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

const formatDate = (d) => {
  if (!d) return '-'
  const date = new Date(d)
  return date.toLocaleString('zh-CN')
}

onMounted(async () => {
  try {
    const res = await projectApi.list()
    projects.value = res.data
  } catch (e) {
    console.error(e)
    projects.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

.card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.project-link {
  color: #1a1a1a;
  text-decoration: none;
  font-weight: 500;
}

.project-link:hover {
  color: #409eff;
}

.project-id {
  font-family: monospace;
  font-size: 12px;
  color: #999;
}
</style>
