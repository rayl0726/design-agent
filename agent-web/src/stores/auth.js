import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const phone = ref(localStorage.getItem('phone') || '')

  const isLoggedIn = computed(() => !!token.value)

  function setAuth(newToken, newPhone) {
    token.value = newToken
    phone.value = newPhone
    localStorage.setItem('token', newToken)
    localStorage.setItem('phone', newPhone)
  }

  function logout() {
    token.value = ''
    phone.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('phone')
  }

  return { token, phone, isLoggedIn, setAuth, logout }
})
