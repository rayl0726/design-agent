<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <el-icon size="24"><Setting /></el-icon>
        <span>Admin 后台</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.path"
          :index="item.path"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <h2>{{ currentTitle }}</h2>
        </div>
        <div class="header-right">
          <el-button text @click="showTokenDialog = true">
            <el-icon><Key /></el-icon>
            Token 设置
          </el-button>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>

    <el-dialog v-model="showTokenDialog" title="Admin Token 设置" width="450px">
      <el-input
        v-model="tokenInput"
        placeholder="输入 X-Admin-Token"
        type="password"
        show-password
      />
      <template #footer>
        <el-button @click="showTokenDialog = false">取消</el-button>
        <el-button type="primary" @click="saveToken">保存</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { getToken, setToken } from '../api/client'
import { ElMessage } from 'element-plus'

const route = useRoute()
const showTokenDialog = ref(false)
const tokenInput = ref(getToken())

const menuItems = [
  { path: '/dashboard', title: '指标看板', icon: 'Odometer' },
  { path: '/feedbacks', title: '反馈管理', icon: 'ChatDotRound' },
  { path: '/prompt-templates', title: 'Prompt 模板', icon: 'Document' },
  { path: '/intent-taxonomy', title: '意图词库', icon: 'Collection' },
  { path: '/ai-monitoring', title: 'AI 模型监控', icon: 'Monitor' },
  { path: '/system-health', title: '系统健康', icon: 'Cpu' }
]

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta?.title || 'Admin 后台')

function saveToken() {
  setToken(tokenInput.value)
  showTokenDialog.value = false
  ElMessage.success('Token 已保存')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
  overflow: hidden;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid #3a4a5f;
}

.sidebar-menu {
  border-right: none;
  background-color: #304156;
}

:deep(.el-menu) {
  background-color: #304156;
}

:deep(.el-menu-item) {
  color: #bfcbd9;
}

:deep(.el-menu-item:hover) {
  background-color: #263445;
  color: #fff;
}

:deep(.el-menu-item.is-active) {
  background-color: #1f2d3d;
  color: #409eff;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e6e6e6;
  background-color: #fff;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>
