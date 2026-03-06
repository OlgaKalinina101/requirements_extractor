<template>
  <v-app>
    <v-app-bar color="primary" dark>
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
      <v-btn variant="text" to="/projects" prepend-icon="mdi-folder-multiple">
        Проекты
      </v-btn>
      <v-btn variant="text" to="/upload" prepend-icon="mdi-upload">
        Быстрая загрузка
      </v-btn>
      <v-btn variant="text" to="/admin" prepend-icon="mdi-cog">
        Администрирование
      </v-btn>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <router-view />
      </v-container>
    </v-main>

    <v-footer app color="primary" dark>
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
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'

const router = useRouter()
const notifications = useNotificationsStore()

const goHome = () => router.push('/')
</script>

<style scoped>
.app-title {
  cursor: pointer;
}
</style>
