import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'
import LoginView from '../views/LoginView.vue'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', name: 'Login', component: LoginView, meta: { public: true } },
  { path: '/', name: 'ChatHome', component: ChatView },
  { path: '/project/:id', name: 'ChatView', component: ChatView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const authStore = useAuthStore()
  if (!to.meta?.public && !authStore.isLoggedIn) {
    return { path: '/login' }
  }
  if (to.path === '/login' && authStore.isLoggedIn) {
    return { path: '/' }
  }
})

export default router
