<template>
  <div class="image-gen-monitoring" v-loading="loading">
    <!-- 时间范围选择器 -->
    <div class="header">
      <el-radio-group v-model="hours" size="small" @change="loadAll">
        <el-radio-button :label="24">24h</el-radio-button>
        <el-radio-button :label="72">72h</el-radio-button>
        <el-radio-button :label="168">7d</el-radio-button>
        <el-radio-button :label="720">30d</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 概览卡片 -->
    <el-row :gutter="16">
      <el-col :span="4" v-for="card in overviewCards" :key="card.key">
        <el-card shadow="never" class="overview-card">
          <div class="card-value" :style="{ color: card.color }">{{ card.value }}</div>
          <div class="card-label">{{ card.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Provider 分布 + 反馈率 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="14">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">Provider 分布</span></div>
          <v-chart class="chart" :option="providerChartOption" autoresize style="height: 320px" />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">反馈率</span></div>
          <v-chart class="chart" :option="feedbackGaugeOption" autoresize style="height: 320px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 标签分布 + 反馈趋势 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="10">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">标签分布</span></div>
          <v-chart class="chart" :option="tagDistributionOption" autoresize style="height: 300px" />
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">反馈趋势</span></div>
          <v-chart class="chart" :option="feedbackTrendOption" autoresize style="height: 300px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 生成分布趋势 -->
    <el-card shadow="never" class="chart-card" style="margin-top: 20px;">
      <div class="chart-header"><span class="chart-title">生成趋势（成功/失败/限流）</span></div>
      <v-chart class="chart" :option="distributionOption" autoresize style="height: 320px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import client from '../api/client'
import { use } from 'echarts/core'
import VChart from 'vue-echarts'
import { BarChart, PieChart, GaugeChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CanvasRenderer, BarChart, PieChart, GaugeChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(false)
const hours = ref(24)
const overview = ref({ totalGenerated: 0, successCount: 0, failedCount: 0, successRate: 0, avgGenerationMs: 0, avgImagesPerProject: 0 })
const providers = ref([])
const feedback = ref({ totalImages: 0, imagesWithFeedback: 0, feedbackRate: 0, tagDistribution: {} })
const feedbackTrend = ref([])
const distribution = ref([])

const overviewCards = computed(() => [
  { key: 'total', label: '总生成数', value: overview.value.totalGenerated, color: '#409eff' },
  { key: 'success', label: '成功数', value: overview.value.successCount, color: '#67c23a' },
  { key: 'failed', label: '失败数', value: overview.value.failedCount, color: '#f56c6c' },
  { key: 'rate', label: '成功率', value: overview.value.successRate.toFixed(1) + '%', color: '#e6a23c' },
  { key: 'avg', label: '平均耗时(ms)', value: Math.round(overview.value.avgGenerationMs), color: '#909399' },
  { key: 'perProj', label: '每项目图数', value: overview.value.avgImagesPerProject.toFixed(1), color: '#9c27b0' },
])

const providerChartOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { data: ['成功', '失败'] },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: providers.value.map(p => p.provider) },
  yAxis: { type: 'value' },
  series: [
    { name: '成功', type: 'bar', stack: 'total', data: providers.value.map(p => p.callCount * p.successRate / 100), itemStyle: { color: '#67c23a' } },
    { name: '失败', type: 'bar', stack: 'total', data: providers.value.map(p => p.callCount * (1 - p.successRate / 100)), itemStyle: { color: '#f56c6c' } },
  ],
}))

const feedbackGaugeOption = computed(() => ({
  series: [{
    type: 'gauge',
    progress: { show: true, width: 18 },
    axisLine: { lineStyle: { width: 18 } },
    detail: { formatter: '{value}%', fontSize: 24 },
    data: [{ value: feedback.value.feedbackRate.toFixed(1), name: '反馈率' }],
  }],
}))

const tagDistributionOption = computed(() => {
  const entries = Object.entries(feedback.value.tagDistribution || {})
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: entries.map(([tag, count]) => ({ name: tag, value: count })),
    }],
  }
})

const feedbackTrendOption = computed(() => {
  const dates = feedbackTrend.value.map(d => d.date)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['正面', '负面'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' },
    series: [
      { name: '正面', type: 'line', smooth: true, data: feedbackTrend.value.map(d => d.positive), itemStyle: { color: '#67c23a' } },
      { name: '负面', type: 'line', smooth: true, data: feedbackTrend.value.map(d => d.negative), itemStyle: { color: '#f56c6c' } },
    ],
  }
})

const distributionOption = computed(() => {
  const dates = distribution.value.map(d => d.date)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['成功', '失败', '限流'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' },
    series: [
      { name: '成功', type: 'bar', stack: 'total', data: distribution.value.map(d => d.success), itemStyle: { color: '#67c23a' } },
      { name: '失败', type: 'bar', stack: 'total', data: distribution.value.map(d => d.failed), itemStyle: { color: '#f56c6c' } },
      { name: '限流', type: 'bar', stack: 'total', data: distribution.value.map(d => d.rateLimited), itemStyle: { color: '#e6a23c' } },
    ],
  }
})

async function loadAll() {
  loading.value = true
  try {
    const params = { hours: hours.value }
    const [ov, prov, fb, fbTrend, dist] = await Promise.all([
      client.get('/metrics/image-generation/overview', { params }),
      client.get('/metrics/image-generation/by-provider', { params }),
      client.get('/metrics/image-generation/feedback', { params }),
      client.get('/metrics/image-generation/feedback-trend', { params }),
      client.get('/metrics/image-generation/distribution', { params }),
    ])
    overview.value = ov
    providers.value = prov
    feedback.value = fb
    feedbackTrend.value = fbTrend
    distribution.value = dist
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.image-gen-monitoring { width: 100%; }
.header { margin-bottom: 20px; }
.overview-card { text-align: center; }
.card-value { font-size: 24px; font-weight: 700; }
.card-label { font-size: 13px; color: #909399; margin-top: 4px; }
.chart-card { background: #fff; }
.chart-header { margin-bottom: 12px; }
.chart-title { font-size: 15px; font-weight: 600; color: #303133; }
</style>
