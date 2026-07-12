<template>
  <div class="intent-quality" v-loading="loading">
    <el-row :gutter="20">
      <!-- Source Distribution -->
      <el-col :span="12">
        <el-card>
          <template #header>识别来源分布</template>
          <v-chart class="chart" :option="sourceChartOption" autoresize style="height: 300px" />
        </el-card>
      </el-col>

      <!-- Confidence Distribution -->
      <el-col :span="12">
        <el-card>
          <template #header>
            置信度分布
            <el-tag v-if="confidenceData.lowConfidenceRate > 0.3" type="danger" size="small">
              低置信度: {{ (confidenceData.lowConfidenceRate * 100).toFixed(1) }}%
            </el-tag>
          </template>
          <v-chart class="chart" :option="confidenceChartOption" autoresize style="height: 300px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- Correction Rate -->
      <el-col :span="14">
        <el-card>
          <template #header>字段纠正率</template>
          <v-chart class="chart" :option="correctionChartOption" autoresize style="height: 300px" />
        </el-card>
      </el-col>

      <!-- Alias Proposals -->
      <el-col :span="10">
        <el-card>
          <template #header>别名学习统计</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="总提案数">{{ aliasStats.totalProposals }}</el-descriptions-item>
            <el-descriptions-item label="待处理">{{ aliasStats.pendingCount }}</el-descriptions-item>
            <el-descriptions-item label="已应用">{{ aliasStats.appliedCount }}</el-descriptions-item>
            <el-descriptions-item label="拒绝率">{{ (aliasStats.rejectionRate * 100).toFixed(1) }}%</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- Correction Details Table -->
    <el-card style="margin-top: 20px;" v-if="correctionData.length > 0">
      <template #header>纠正详情</template>
      <el-table :data="correctionData" stripe>
        <el-table-column prop="field" label="字段" width="150" />
        <el-table-column prop="totalRecognitions" label="总识别数" width="120" />
        <el-table-column prop="correctionCount" label="纠正数" width="100" />
        <el-table-column prop="correctionRate" label="纠正率" width="100">
          <template #default="{ row }">{{ row.correctionRate.toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column label="最常被纠正的值">
          <template #default="{ row }">
            <el-tag v-for="v in row.topCorrectedValues" :key="v.original" size="small" style="margin: 2px;">
              {{ v.original }} ({{ v.count }})
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
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
const sourceData = ref([])
const confidenceData = ref({ buckets: [], lowConfidenceRate: 0 })
const correctionData = ref([])
const aliasStats = ref({ totalProposals: 0, pendingCount: 0, appliedCount: 0, rejectionRate: 0 })

const sourceChartOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { bottom: 0 },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    data: sourceData.value.map(s => ({ name: s.source, value: s.count })),
  }],
}))

const confidenceChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: confidenceData.value.buckets.map(b => b.bucket) },
  yAxis: { type: 'value' },
  series: [{
    type: 'bar',
    data: confidenceData.value.buckets.map(b => b.count),
    itemStyle: { color: '#409eff' },
  }],
}))

const correctionChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: correctionData.value.map(d => d.field) },
  yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
  series: [{
    type: 'bar',
    data: correctionData.value.map(d => d.correctionRate),
    itemStyle: { color: '#e6a23c' },
    label: { show: true, position: 'top', formatter: '{c}%' },
  }],
}))

async function loadAll() {
  loading.value = true
  try {
    const [sources, confidence, corrections, alias] = await Promise.all([
      client.get('/metrics/intent-quality/sources', { params: { days: 30 } }),
      client.get('/metrics/intent-quality/confidence', { params: { days: 30 } }),
      client.get('/metrics/intent-quality/correction-rate', { params: { days: 30 } }),
      client.get('/metrics/intent-quality/alias-proposals'),
    ])
    sourceData.value = sources
    confidenceData.value = confidence
    correctionData.value = corrections
    aliasStats.value = alias
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.intent-quality {
  width: 100%;
}
.chart {
  width: 100%;
}
</style>
