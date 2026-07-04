<template>
  <div class="app-container">
    <aside class="sidebar">
      <div class="brand">
        <h1>美陈设计</h1>
        <span class="tag">AI Agent</span>
      </div>
      <nav class="nav-menu">
        <router-link to="/" exact-active-class="active">
          <el-icon><Document /></el-icon>
          <span>项目列表</span>
        </router-link>
        <router-link v-if="false" to="/new" exact-active-class="active">
          <el-icon><Plus /></el-icon>
          <span>新建项目</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <p>Meichen Design Agent</p>
      </div>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { Document, Plus } from '@element-plus/icons-vue'
</script>

<style scoped>
.app-container {
  display: flex;
  min-height: 100vh;
  background: #f5f5f7;
}

.sidebar {
  width: 220px;
  background: #0f0f0f;
  color: #fff;
  display: flex;
  flex-direction: column;
  padding: 32px 24px;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
}

.brand h1 {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 2px;
  margin: 0;
}

.brand .tag {
  display: inline-block;
  margin-top: 8px;
  font-size: 11px;
  color: #a0a0a0;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.nav-menu {
  margin-top: 48px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.nav-menu a {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  color: #999;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}

.nav-menu a:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.06);
}

.nav-menu a.active {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.sidebar-footer {
  font-size: 11px;
  color: #555;
  margin-top: auto;
}

.main-content {
  margin-left: 220px;
  flex: 1;
  padding: 40px 48px;
  min-height: 100vh;
}
</style>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  color: #1a1a1a;
}
</style>
