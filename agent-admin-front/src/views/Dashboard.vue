<template>
  <div class="dashboard" v-loading="loading">
    <!-- 概览卡片 -->
    <el-row :gutter="20" class="overview-row">
      <el-col
        v-for="card in overviewCards"
        :key="card.key"
        :xs="12"
        :sm="8"
        :md="6"
        :lg="4"
      >
        <el-card shadow="hover" class="stat-card">
          <div class="stat-card-body">
            <div class="stat-icon" :style="{ backgroundColor: card.color }">
              <el-icon :size="28">
                <component :is="card.icon" />
              </el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ overview[card.key] ?? 0 }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 阶段耗时图表 -->
    <el-card shadow="never" class="chart-card">
      <div class="chart-header">
        <span class="chart-title">阶段耗时统计</span>
        <el-radio-group v-model="hours" size="small" @change="loadStages">
          <el-radio-button :label="24">24h</el-radio-button>
          <el-radio-button :label="72">72h</el-radio-button>
          <el-radio-button :label="168">168h</el-radio-button>
        </el-radio-group>
      </div>
      <v-chart
        class="chart"
        :option="stageChartOption"
        autoresize
        style="height: 350px"
      />
    </el-card>

    <!-- 反馈分布图表 -->
    <el-card shadow="never" class="chart-card">
      <div class="chart-header">
        <span class="chart-title">反馈分布</span>
      </div>
      <v-chart
        class="chart"
        :option="feedbackChartOption"
        autoresize
        style="height: 300px"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import client from '../api/client'
import { use } from 'echarts/core'
import VChart from 'vue-echarts'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CanvasRenderer, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(false)
const overview = ref({})
const stages = ref([])
const feedbackDist = ref([])
const hours = ref(24)

const overviewCards = computed(() => [
  { key: 'projectCount', label: '项目总数', icon: 'Document', color: '#409eff' },
  { key: 'feedbackCount', label: '反馈总数', icon: 'ChatDotRound', color: '#67c23a' },
  { key: 'imageFeedbackCount', label: '图像反馈数', icon: 'Picture', color: '#e6a23c' },
  { key: 'intentCorrectionCount', label: '意图纠正数', icon: 'Edit', color: '#f56c6c' },
  { key: 'stageLogCount', label: '阶段日志数', icon: 'Timer', color: '#9c27b0' },
  { key: 'projectsWithFeedbackCount', label: '有反馈项目数', icon: 'Warning', color: '#ff9800' }
])

// 将毫秒格式化为可读时长：>= 60s 显示分钟，否则显示秒
function formatDuration(ms) {
  const seconds = ms / 1000
  if (seconds >= 60) {
    return (seconds / 60).toFixed(1) + ' 分'
  }
  return seconds.toFixed(1) + ' 秒'
}

const stageChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
    formatter: (params) => {
      const p = params[0]
      const idx = p.dataIndex
      const item = stages.value[idx]
      if (!item) return ''
      return [
        `${p.name}`,
        `平均耗时: ${formatDuration(item.avgMs)}`,
        `P95: ${formatDuration(item.p95Ms)}`,
        `最大: ${formatDuration(item.maxMs)}`,
        `成功: ${item.successCount}`,
        `失败: ${item.failedCount}`
      ].join('<br/>')
    }
  },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: {
    type: 'category',
    data: stages.value.map(s => s.stageName),
    axisLabel: { rotate: 30, interval: 0 }
  },
  yAxis: {
    type: 'value',
    name: '平均耗时(秒)',
    axisLabel: {
      formatter: (val) => (val >= 60 ? (val / 60).toFixed(0) + '分' : val.toFixed(0))
    }
  },
  series: [
    {
      name: '平均耗时',
      type: 'bar',
      data: stages.value.map(s => Number((s.avgMs / 1000).toFixed(1))),
      itemStyle: { color: '#409eff', borderRadius: [4, 4, 0, 0] },
      barMaxWidth: 40
    }
  ]
}))

const feedbackChartOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { orient: 'vertical', left: 'left', top: 'center' },
  series: [
    {
      name: '反馈分布',
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['60%', '50%'],
      avoidLabelOverlap: true,
      data: feedbackDist.value.map(f => ({ name: f.tag, value: f.count })),
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      },
      label: { show: true, formatter: '{b}: {c}' }
    }
  ]
}))

async function loadOverview() {
  overview.value = await client.get('/metrics/overview')
}

async function loadStages() {
  stages.value = await client.get('/metrics/stages', { params: { hours: hours.value } })
}

async function loadFeedbackDist() {
  feedbackDist.value = await client.get('/metrics/feedback-distribution')
}

async function loadAll() {
  loading.value = true
  try {
    await Promise.all([loadOverview(), loadStages(), loadFeedbackDist()])
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview-row {
  margin-bottom: 0;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-card-body {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.chart-card {
  margin-bottom: 0;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.chart {
  width: 100%;
}
</style>
