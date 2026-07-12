import { createRouter, createWebHistory } from 'vue-router'
import AdminLayout from '../layouts/AdminLayout.vue'

const routes = [
  {
    path: '/',
    component: AdminLayout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '指标看板', icon: 'Odometer' }
      },
      {
        path: 'feedbacks',
        name: 'FeedbackList',
        component: () => import('../views/FeedbackList.vue'),
        meta: { title: '反馈管理', icon: 'ChatDotRound' }
      },
      {
        path: 'prompt-templates',
        name: 'PromptTemplates',
        component: () => import('../views/PromptTemplates.vue'),
        meta: { title: 'Prompt 模板', icon: 'Document' }
      },
      {
        path: 'intent-taxonomy',
        name: 'IntentTaxonomy',
        component: () => import('../views/IntentTaxonomy.vue'),
        meta: { title: '意图词库', icon: 'Collection' }
      },
      {
        path: 'ai-monitoring',
        name: 'AiModelMonitoring',
        component: () => import('../views/AiModelMonitoring.vue'),
        meta: { title: 'AI 模型监控', icon: 'Monitor' }
      },
      {
        path: 'system-health',
        name: 'SystemHealth',
        component: () => import('../views/SystemHealth.vue'),
        meta: { title: '系统健康', icon: 'Cpu' }
      },
      {
        path: 'intent-quality',
        name: 'IntentQuality',
        component: () => import('../views/IntentQuality.vue'),
        meta: { title: '意图质量', icon: 'Aim' }
      },
      {
        path: 'image-gen-monitoring',
        name: 'ImageGenMonitoring',
        component: () => import('../views/ImageGenMonitoring.vue'),
        meta: { title: '图像生成监控', icon: 'PictureFilled' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
