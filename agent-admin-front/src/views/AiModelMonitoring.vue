<template>
  <div class="ai-monitoring" v-loading="loading">
    <!-- 时间范围选择器 -->
    <div class="header">
      <el-radio-group v-model="hours" size="small" @change="loadAll">
        <el-radio-button :label="24">24h</el-radio-button>
        <el-radio-button :label="168">7d</el-radio-button>
        <el-radio-button :label="720">30d</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 调用概览卡片 -->
    <el-row :gutter="20" class="overview-row">
      <el-col v-for="card in summaryCards" :key="card.key" :xs="12" :sm="8" :md="6" :lg="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-body">
            <div class="stat-icon" :style="{ backgroundColor: card.color }">
              <el-icon :size="24"><component :is="card.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Provider 分布 + 调用趋势 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">Provider 分布</span></div>
          <v-chart class="chart" :option="providerChartOption" autoresize style="height: 320px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">调用趋势</span></div>
          <v-chart class="chart" :option="timelineChartOption" autoresize style="height: 320px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Token 用量 -->
    <el-card shadow="never" class="chart-card">
      <div class="chart-header"><span class="chart-title">Token 用量趋势</span></div>
      <v-chart class="chart" :option="tokenChartOption" autoresize style="height: 350px" />
    </el-card>

    <!-- 错误分析表格 -->
    <el-card shadow="never" class="chart-card">
      <div class="chart-header"><span class="chart-title">Provider 调用明细</span></div>
      <el-table :data="providerBreakdown" stripe style="width: 100%">
        <el-table-column prop="provider" label="Provider" width="120" />
        <el-table-column prop="model" label="Model" />
        <el-table-column prop="callCount" label="调用次数" width="100" />
        <el-table-column prop="successRate" label="成功率" width="100">
          <template #default="{ row }">{{ row.successRate.toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column prop="avgLatencyMs" label="平均延迟(ms)" width="120">
          <template #default="{ row }">{{ row.avgLatencyMs.toFixed(0) }}</template>
        </el-table-column>
        <el-table-column prop="totalTokens" label="总Token" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import client from '../api/client'
import { use } from 'echarts/core'
import VChart from 'vue-echarts'
import { BarChart, PieChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CanvasRenderer, BarChart, PieChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(false)
const hours = ref(24)
const summary = ref([])
const providerBreakdown = ref([])
const timeline = ref([])
const tokenUsage = ref([])

const summaryCards = computed(() => {
  const cards = []
  const types = [
    { type: 'llm', label: 'LLM 调用', icon: 'ChatLineSquare', color: '#409eff' },
    { type: 'vlm', label: 'VLM 调用', icon: 'Picture', color: '#67c23a' },
    { type: 'embedding', label: 'Embedding', icon: 'Histogram', color: '#e6a23c' },
    { type: 'image_gen', label: '图像生成', icon: 'Image', color: '#f56c6c' },
  ]
  for (const t of types) {
    const s = summary.value.find(s => s.callType === t.type)
    cards.push({
      key: t.type,
      label: t.label,
      icon: t.icon,
      color: t.color,
      value: s ? s.totalCount : 0,
    })
  }
  const totalCalls = summary.value.reduce((sum, s) => sum + s.totalCount, 0)
  const totalSuccess = summary.value.reduce((sum, s) => sum + s.successCount, 0)
  const totalTokens = summary.value.reduce((sum, s) => sum + s.totalInputTokens + s.totalOutputTokens, 0)
  cards.push(
    { key: 'total', label: '总调用', icon: 'DataLine', color: '#9c27b0', value: totalCalls },
    { key: 'successRate', label: '成功率', icon: 'CircleCheck', color: '#4caf50', value: totalCalls > 0 ? ((totalSuccess / totalCalls) * 100).toFixed(1) + '%' : '0%' },
    { key: 'tokens', label: '总Token', icon: 'Coin', color: '#ff9800', value: totalTokens },
  )
  return cards
})

const providerChartOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { orient: 'vertical', left: 'left', top: 'center' },
  series: [{
    type: 'pie',
    radius: ['40%', '65%'],
    center: ['60%', '50%'],
    data: providerBreakdown.value.map(p => ({ name: `${p.provider}/${p.model}`, value: p.callCount })),
    label: { show: true, formatter: '{b}: {c}' },
  }],
}))

const timelineChartOption = computed(() => {
  const dates = [...new Set(timeline.value.map(t => t.date))].sort()
  const types = [...new Set(timeline.value.map(t => t.callType))]
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: types },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' },
    series: types.map(type => ({
      name: type,
      type: 'bar',
      stack: 'total',
      data: dates.map(d => {
        const item = timeline.value.find(t => t.date === d && t.callType === type)
        return item ? item.count : 0
      }),
    })),
  }
})

const tokenChartOption = computed(() => {
  const dates = [...new Set(tokenUsage.value.map(t => t.date))].sort()
  const providers = [...new Set(tokenUsage.value.map(t => t.provider))]
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: providers },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: 'Tokens' },
    series: providers.map(prov => ({
      name: prov,
      type: 'line',
      smooth: true,
      data: dates.map(d => {
        const item = tokenUsage.value.find(t => t.date === d && t.provider === prov)
        return item ? item.totalTokens : 0
      }),
    })),
  }
})

async function loadAll() {
  loading.value = true
  try {
    const [s, p, t, tokens] = await Promise.all([
      client.get('/metrics/ai-calls/summary', { params: { hours: hours.value } }),
      client.get('/metrics/ai-calls/by-provider', { params: { hours: hours.value } }),
      client.get('/metrics/ai-calls/timeline', { params: { hours: hours.value } }),
      client.get('/metrics/ai-calls/tokens', { params: { hours: hours.value } }),
    ])
    summary.value = s
    providerBreakdown.value = p
    timeline.value = t
    tokenUsage.value = tokens
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.ai-monitoring { display: flex; flex-direction: column; gap: 20px; }
.header { display: flex; align-items: center; justify-content: flex-end; }
.overview-row { margin-bottom: 0; }
.stat-card { margin-bottom: 20px; }
.stat-body { display: flex; align-items: center; gap: 16px; }
.stat-icon { width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #fff; flex-shrink: 0; }
.stat-info { display: flex; flex-direction: column; justify-content: center; min-width: 0; }
.stat-value { font-size: 24px; font-weight: 700; color: #303133; line-height: 1.2; }
.stat-label { font-size: 12px; color: #909399; margin-top: 4px; }
.chart-card { margin-bottom: 0; }
.chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.chart-title { font-size: 16px; font-weight: 600; color: #303133; }
.chart { width: 100%; }
</style>
