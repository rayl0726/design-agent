<template>
  <div class="system-health" v-loading="loading">
    <!-- 时间范围选择器 -->
    <div class="header">
      <el-radio-group v-model="days" size="small" @change="loadDbMetrics">
        <el-radio-button :label="1">24h</el-radio-button>
        <el-radio-button :label="7">7d</el-radio-button>
        <el-radio-button :label="30">30d</el-radio-button>
      </el-radio-group>
      <el-radio-group v-model="httpHours" size="small" @change="loadHttpMetrics" style="margin-left: 12px">
        <el-radio-button :label="1">HTTP 1h</el-radio-button>
        <el-radio-button :label="6">HTTP 6h</el-radio-button>
        <el-radio-button :label="24">HTTP 24h</el-radio-button>
      </el-radio-group>
      <el-button size="small" @click="loadInfraMetrics" style="margin-left: 12px">
        <el-icon><Refresh /></el-icon> 刷新基础设施
      </el-button>
    </div>

    <!-- 工作流成功率 + 异常 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">工作流成功率</span></div>
          <v-chart class="chart" :option="workflowGaugeOption" autoresize style="height: 280px" />
          <el-table :data="workflowSuccess" stripe size="small" style="margin-top: 12px">
            <el-table-column prop="stageName" label="阶段" />
            <el-table-column prop="totalCount" label="总数" width="80" />
            <el-table-column prop="successCount" label="成功" width="80" />
            <el-table-column prop="failedCount" label="失败" width="80" />
            <el-table-column label="成功率" width="100">
              <template #default="{ row }">{{ row.successRate.toFixed(1) }}%</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">异常事件</span></div>
          <el-row :gutter="16" style="margin-bottom: 16px">
            <el-col :span="12">
              <div class="anomaly-card">
                <div class="anomaly-value">{{ anomalies.timeAnomalyCount }}</div>
                <div class="anomaly-label">时间异常</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="anomaly-card">
                <div class="anomaly-value">{{ anomalies.subStageOverflowCount }}</div>
                <div class="anomaly-label">子阶段溢出</div>
              </div>
            </el-col>
          </el-row>
          <el-table :data="anomalies.affectedStages" stripe size="small">
            <el-table-column prop="stageName" label="受影响阶段" />
            <el-table-column prop="timeAnomalyCount" label="时间异常" width="100" />
            <el-table-column prop="subStageOverflowCount" label="子阶段溢出" width="120" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 重试 + 错误分布 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">重试分布</span></div>
          <v-chart class="chart" :option="retryChartOption" autoresize style="height: 280px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">错误分布</span></div>
          <el-table :data="errors" stripe size="small">
            <el-table-column prop="nodeName" label="节点" />
            <el-table-column prop="errorCount" label="错误次数" width="100" />
            <el-table-column prop="errorMessage" label="错误信息" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- HTTP 指标 -->
    <el-card shadow="never" class="chart-card">
      <div class="chart-header"><span class="chart-title">HTTP 请求指标</span></div>
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="4">
          <div class="http-stat"><div class="http-value">{{ httpMetrics.totalRequests }}</div><div class="http-label">总请求</div></div>
        </el-col>
        <el-col :span="4">
          <div class="http-stat"><div class="http-value" :class="{ 'error-text': httpMetrics.errorCount > 0 }">{{ httpMetrics.errorCount }}</div><div class="http-label">错误数</div></div>
        </el-col>
        <el-col :span="4">
          <div class="http-stat"><div class="http-value">{{ httpMetrics.errorRate.toFixed(2) }}%</div><div class="http-label">错误率</div></div>
        </el-col>
        <el-col :span="4">
          <div class="http-stat"><div class="http-value">{{ httpMetrics.avgDurationMs.toFixed(0) }}ms</div><div class="http-label">平均响应</div></div>
        </el-col>
        <el-col :span="4">
          <div class="http-stat"><div class="http-value">{{ httpMetrics.maxDurationMs }}ms</div><div class="http-label">最大响应</div></div>
        </el-col>
      </el-row>
      <el-table :data="httpMetrics.topEndpoints" stripe size="small">
        <el-table-column prop="pathPattern" label="路径" />
        <el-table-column prop="requestCount" label="请求数" width="100" />
        <el-table-column prop="errorCount" label="错误数" width="100" />
        <el-table-column label="平均响应(ms)" width="130">
          <template #default="{ row }">{{ row.avgDurationMs.toFixed(0) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 线程池 + DB 连接池 -->
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">线程池状态</span></div>
          <el-row :gutter="16">
            <el-col v-for="pool in threadPools" :key="pool.name" :span="12">
              <div class="pool-card">
                <div class="pool-name">{{ pool.name }}</div>
                <v-chart class="chart" :option="getPoolGaugeOption(pool)" autoresize style="height: 200px" />
                <div class="pool-stats">
                  <span>Active: {{ pool.active }}</span>
                  <span>Core: {{ pool.core }}</span>
                  <span>Max: {{ pool.max }}</span>
                  <span>Queue: {{ pool.queueSize }}</span>
                  <span>Completed: {{ pool.completedTaskCount }}</span>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="chart-card">
          <div class="chart-header"><span class="chart-title">DB 连接池</span></div>
          <v-chart class="chart" :option="dbPoolGaugeOption" autoresize style="height: 200px" />
          <div class="pool-stats" style="text-align: center">
            <span>Active: {{ dbPool.active }}</span>
            <span>Idle: {{ dbPool.idle }}</span>
            <span>Max: {{ dbPool.max }}</span>
            <span>Pending: {{ dbPool.pending }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import client from '../api/client'
import { use } from 'echarts/core'
import VChart from 'vue-echarts'
import { GaugeChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { Refresh } from '@element-plus/icons-vue'

use([CanvasRenderer, GaugeChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(false)
const days = ref(7)
const httpHours = ref(1)

const workflowSuccess = ref([])
const retries = ref([])
const errors = ref([])
const anomalies = ref({ timeAnomalyCount: 0, subStageOverflowCount: 0, affectedStages: [] })
const httpMetrics = ref({ totalRequests: 0, errorCount: 0, errorRate: 0, avgDurationMs: 0, maxDurationMs: 0, topEndpoints: [] })
const threadPools = ref([])
const dbPool = ref({ active: 0, idle: 0, max: 0, pending: 0 })

const overallSuccessRate = computed(() => {
  const total = workflowSuccess.value.reduce((sum, w) => sum + w.totalCount, 0)
  const success = workflowSuccess.value.reduce((sum, w) => sum + w.successCount, 0)
  return total > 0 ? (success / total * 100) : 0
})

const workflowGaugeOption = computed(() => ({
  series: [{
    type: 'gauge',
    progress: { show: true, width: 18 },
    axisLine: { lineStyle: { width: 18 } },
    detail: { valueAnimation: true, formatter: '{value}%', fontSize: 28 },
    data: [{ value: overallSuccessRate.value.toFixed(1) }],
    max: 100,
  }],
}))

const retryChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['总执行', '重试次数'] },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: retries.value.map(r => r.nodeName), axisLabel: { rotate: 20 } },
  yAxis: { type: 'value' },
  series: [
    { name: '总执行', type: 'bar', data: retries.value.map(r => r.totalExecutions) },
    { name: '重试次数', type: 'bar', data: retries.value.map(r => r.totalRetries) },
  ],
}))

function getPoolGaugeOption(pool) {
  const usage = pool.max > 0 ? (pool.active / pool.max * 100) : 0
  return {
    series: [{
      type: 'gauge',
      progress: { show: true, width: 14 },
      axisLine: { lineStyle: { width: 14 } },
      detail: { valueAnimation: true, formatter: '{value}%', fontSize: 20 },
      data: [{ value: usage.toFixed(1) }],
      max: 100,
    }],
  }
}

const dbPoolGaugeOption = computed(() => {
  const usage = dbPool.value.max > 0 ? (dbPool.value.active / dbPool.value.max * 100) : 0
  return {
    series: [{
      type: 'gauge',
      progress: { show: true, width: 14 },
      axisLine: { lineStyle: { width: 14 } },
      detail: { valueAnimation: true, formatter: '{value}%', fontSize: 20 },
      data: [{ value: usage.toFixed(1) }],
      max: 100,
    }],
  }
})

async function loadDbMetrics() {
  loading.value = true
  try {
    const [wf, rt, err, anom] = await Promise.all([
      client.get('/metrics/system/workflow-success', { params: { days: days.value } }),
      client.get('/metrics/system/retries', { params: { days: days.value } }),
      client.get('/metrics/system/errors', { params: { days: days.value } }),
      client.get('/metrics/system/anomalies', { params: { days: days.value } }),
    ])
    workflowSuccess.value = wf
    retries.value = rt
    errors.value = err
    anomalies.value = anom
  } finally {
    loading.value = false
  }
}

async function loadHttpMetrics() {
  const http = await client.get('/metrics/system/http', { params: { hours: httpHours.value } })
  httpMetrics.value = http
}

async function loadInfraMetrics() {
  const [tp, dbp] = await Promise.all([
    client.get('/metrics/system/thread-pools'),
    client.get('/metrics/system/db-pool'),
  ])
  threadPools.value = tp
  dbPool.value = dbp
}

onMounted(() => {
  loadDbMetrics()
  loadHttpMetrics()
  loadInfraMetrics()
})
</script>

<style scoped>
.system-health { display: flex; flex-direction: column; gap: 20px; }
.header { display: flex; align-items: center; justify-content: flex-end; }
.chart-card { margin-bottom: 0; }
.chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.chart-title { font-size: 16px; font-weight: 600; color: #303133; }
.chart { width: 100%; }
.anomaly-card { text-align: center; padding: 20px; background: #f5f7fa; border-radius: 8px; }
.anomaly-value { font-size: 32px; font-weight: 700; color: #e6a23c; }
.anomaly-label { font-size: 14px; color: #909399; margin-top: 4px; }
.http-stat { text-align: center; padding: 16px; background: #f5f7fa; border-radius: 8px; }
.http-value { font-size: 22px; font-weight: 700; color: #303133; }
.http-value.error-text { color: #f56c6c; }
.http-label { font-size: 12px; color: #909399; margin-top: 4px; }
.pool-card { text-align: center; padding: 12px; background: #f5f7fa; border-radius: 8px; }
.pool-name { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.pool-stats { display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; font-size: 12px; color: #606266; margin-top: 8px; }
</style>
