<template>
  <div class="dashboard" v-loading="loading">
    <!-- 时间范围选择器 -->
    <div class="dashboard-header">
      <el-radio-group v-model="timeRange" size="small">
        <el-radio-button :label="24">24h</el-radio-button>
        <el-radio-button :label="72">72h</el-radio-button>
        <el-radio-button :label="168">7d</el-radio-button>
        <el-radio-button :label="720">30d</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 概览卡片 -->
    <el-row :gutter="20" class="overview-row">
      <el-col
        v-for="card in overviewCards"
        :key="card.key"
        :xs="12"
        :sm="8"
        :md="6"
        :lg="3"
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

    <!-- 项目漏斗 + 创建趋势 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header">
            <span class="chart-title">项目漏斗</span>
          </div>
          <v-chart
            class="chart"
            :option="funnelChartOption"
            autoresize
            style="height: 300px"
          />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header">
            <span class="chart-title">项目创建趋势</span>
          </div>
          <v-chart
            class="chart"
            :option="trendChartOption"
            autoresize
            style="height: 300px"
          />
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
import { ref, computed, onMounted, watch } from 'vue'
import client from '../api/client'
import { use } from 'echarts/core'
import VChart from 'vue-echarts'
import { BarChart, PieChart, FunnelChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CanvasRenderer, BarChart, PieChart, FunnelChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(false)
const overview = ref({})
const stages = ref([])
const feedbackDist = ref([])
const hours = ref(24)
const timeRange = ref(24)
const funnelData = ref({})
const conversationStats = ref({})
const projectTrend = ref([])

const overviewCards = computed(() => [
  { key: 'projectCount', label: '项目总数', icon: 'Document', color: '#409eff' },
  { key: 'feedbackCount', label: '反馈总数', icon: 'ChatDotRound', color: '#67c23a' },
  { key: 'imageFeedbackCount', label: '图像反馈数', icon: 'Picture', color: '#e6a23c' },
  { key: 'intentCorrectionCount', label: '意图纠正数', icon: 'Edit', color: '#f56c6c' },
  { key: 'stageLogCount', label: '阶段日志数', icon: 'Timer', color: '#9c27b0' },
  { key: 'projectsWithFeedbackCount', label: '有反馈项目数', icon: 'Warning', color: '#ff9800' },
  { key: 'activeProjectsInWindow', label: '期内活跃项目', icon: 'View', color: '#00bcd4' },
  { key: 'completedProjectsInWindow', label: '期内完成数', icon: 'CircleCheck', color: '#4caf50' }
])

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

const funnelChartOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c}' },
  series: [
    {
      name: '项目漏斗',
      type: 'funnel',
      left: '10%',
      width: '80%',
      minSize: '30%',
      maxSize: '100%',
      sort: 'descending',
      gap: 2,
      label: { show: true, position: 'inside', formatter: '{b}: {c}' },
      data: [
        { value: funnelData.value.draftCount || 0, name: 'Draft' },
        { value: funnelData.value.generatingCount || 0, name: 'Generating' },
        { value: funnelData.value.completedCount || 0, name: 'Completed' }
      ]
    }
  ]
}))

const trendChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['每日新建', '累计项目'] },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: {
    type: 'category',
    data: projectTrend.value.map(t => t.date),
    axisLabel: { rotate: 30 }
  },
  yAxis: [
    { type: 'value', name: '每日新建' },
    { type: 'value', name: '累计' }
  ],
  series: [
    {
      name: '每日新建',
      type: 'bar',
      data: projectTrend.value.map(t => t.count),
      itemStyle: { color: '#409eff' }
    },
    {
      name: '累计项目',
      type: 'line',
      yAxisIndex: 1,
      data: projectTrend.value.map(t => t.cumulativeCount),
      itemStyle: { color: '#67c23a' },
      smooth: true
    }
  ]
}))

async function loadOverview() {
  overview.value = await client.get('/metrics/overview', { params: { hours: timeRange.value } })
}

async function loadStages() {
  stages.value = await client.get('/metrics/stages', { params: { hours: hours.value } })
}

async function loadFeedbackDist() {
  feedbackDist.value = await client.get('/metrics/feedback-distribution')
}

async function loadFunnel() {
  const days = Math.ceil(timeRange.value / 24)
  funnelData.value = await client.get('/metrics/funnel', { params: { days } })
}

async function loadConversations() {
  const days = Math.ceil(timeRange.value / 24)
  conversationStats.value = await client.get('/metrics/conversations', { params: { days } })
}

async function loadTrend() {
  const days = Math.ceil(timeRange.value / 24)
  projectTrend.value = await client.get('/metrics/trend/projects', { params: { days } })
}

async function loadAll() {
  loading.value = true
  try {
    await Promise.all([
      loadOverview(),
      loadStages(),
      loadFeedbackDist(),
      loadFunnel(),
      loadConversations(),
      loadTrend()
    ])
  } finally {
    loading.value = false
  }
}

watch(timeRange, () => loadAll())

onMounted(loadAll)
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
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
