import { createRouter, createWebHistory } from 'vue-router'
import ProjectList from '../views/ProjectList.vue'
import NewProject from '../views/NewProject.vue'
import ChatView from '../views/ChatView.vue'
import ProjectExport from '../views/ProjectExport.vue'

const routes = [
  { path: '/', name: 'ProjectList', component: ProjectList },
  { path: '/new', name: 'NewProject', component: NewProject },
  { path: '/project/:id', name: 'ChatView', component: ChatView },
  { path: '/project/:id/export', name: 'ProjectExport', component: ProjectExport },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
