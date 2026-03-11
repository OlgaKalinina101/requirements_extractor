<template>
  <v-app>
    <v-app-bar v-if="auth.isAuthenticated" color="primary" dark>
      <v-btn icon @click="goHome">
        <v-icon>mdi-clipboard-check-multiple</v-icon>
      </v-btn>
      <v-app-bar-title class="app-title" @click="goHome">
        Система управления требованиями
      </v-app-bar-title>
      <v-spacer></v-spacer>
      <v-btn variant="text" to="/dashboard" prepend-icon="mdi-view-dashboard">
        Дашборд
      </v-btn>
      <v-btn variant="text" to="/" prepend-icon="mdi-folder-multiple">
        Проекты
      </v-btn>
      <v-btn v-if="auth.isManager" variant="text" to="/upload" prepend-icon="mdi-upload">
        Быстрая загрузка
      </v-btn>
      <v-btn v-if="auth.isAdmin" variant="text" to="/admin" prepend-icon="mdi-cog">
        Справочники
      </v-btn>
      <v-btn v-if="auth.isAdmin" variant="text" to="/users" prepend-icon="mdi-account-group">
        Пользователи
      </v-btn>

      <!-- User menu -->
      <v-menu>
        <template #activator="{ props }">
          <v-btn v-bind="props" variant="text" class="ml-2">
            <v-icon start>mdi-account-circle</v-icon>
            {{ auth.user?.full_name || auth.user?.email }}
            <v-icon end>mdi-chevron-down</v-icon>
          </v-btn>
        </template>
        <v-list density="compact" min-width="200">
          <v-list-item>
            <v-list-item-title class="text-caption text-medium-emphasis">
              {{ auth.user?.email }}
            </v-list-item-title>
            <v-list-item-subtitle>
              <v-chip :color="roleColor" size="x-small" variant="tonal">{{ roleName }}</v-chip>
            </v-list-item-subtitle>
          </v-list-item>
          <v-divider />
          <v-list-item prepend-icon="mdi-logout" title="Выйти" @click="handleLogout" />
        </v-list>
      </v-menu>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <router-view />
      </v-container>
    </v-main>

    <v-footer v-if="auth.isAuthenticated" app color="primary" dark>
      <v-spacer></v-spacer>
      <span>&copy; 2026 Requirements Management System</span>
    </v-footer>

    <!-- Global notification snackbar -->
    <v-snackbar
      v-model="notifications.snackbar.show"
      :color="notifications.snackbar.color"
      :timeout="notifications.snackbar.timeout"
      location="bottom right"
    >
      {{ notifications.snackbar.text }}
      <template #actions>
        <v-btn variant="text" @click="notifications.snackbar.show = false">
          Закрыть
        </v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const notifications = useNotificationsStore()
const auth = useAuthStore()

const roleColor = computed(() => {
  if (auth.role === 'admin') return 'error'
  if (auth.role === 'manager') return 'primary'
  return 'secondary'
})

const roleName = computed(() => {
  if (auth.role === 'admin') return 'Администратор'
  if (auth.role === 'manager') return 'Менеджер'
  return 'Пользователь'
})

const goHome = () => router.push('/')

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-title {
  cursor: pointer;
}
</style>
