import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'
import { getRoleColor, getRoleName } from '@/utils/formatters'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isAuthenticated = computed(() => !!token.value)
  const role = computed(() => user.value?.role || null)
  const isAdmin = computed(() => role.value === 'admin')
  const isManager = computed(() => ['admin', 'manager', 'department_head'].includes(role.value))
  const roleColor = computed(() => getRoleColor(role.value))
  const roleName  = computed(() => getRoleName(role.value))

  async function login(email, password) {
    const { data } = await api.post('/api/auth/login', { email, password })
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
  }

  async function fetchMe() {
    try {
      const { data } = await api.get('/api/auth/me')
      user.value = data
      localStorage.setItem('user', JSON.stringify(data))
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { token, user, isAuthenticated, role, isAdmin, isManager, roleColor, roleName, login, fetchMe, logout }
})
