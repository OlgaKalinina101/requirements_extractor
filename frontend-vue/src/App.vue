<template>
  <v-app>
    <v-app-bar color="primary" dark>
      <v-btn icon @click="goHome">
        <v-icon>mdi-clipboard-check-multiple</v-icon>
      </v-btn>
      <v-app-bar-title @click="goHome" style="cursor: pointer">
        Система управления требованиями
      </v-app-bar-title>
      <v-spacer></v-spacer>
      <v-btn variant="text" to="/projects" prepend-icon="mdi-folder-multiple">
        Проекты
      </v-btn>
      <v-btn variant="text" to="/upload" prepend-icon="mdi-upload">
        Быстрая загрузка
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
  </v-app>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
const goHome = () => router.push('/')
</script>
