import { createRouter, createWebHistory } from 'vue-router'
import ProjectList from '../views/ProjectList.vue'
import NewProject from '../views/NewProject.vue'
import ProjectDetail from '../views/ProjectDetail.vue'
import ProjectExport from '../views/ProjectExport.vue'

const routes = [
  { path: '/', name: 'ProjectList', component: ProjectList },
  { path: '/new', name: 'NewProject', component: NewProject },
  { path: '/project/:id', name: 'ProjectDetail', component: ProjectDetail },
  { path: '/project/:id/export', name: 'ProjectExport', component: ProjectExport },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
