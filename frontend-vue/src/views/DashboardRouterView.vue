<template>
  <DashboardView v-if="auth.isManager || auth.isAdmin" />
  <ExecutorDashboardView v-else />
</template>

<script setup>
import { useAuthStore } from '@/stores/auth'
import DashboardView from './DashboardView.vue'
import ExecutorDashboardView from './ExecutorDashboardView.vue'

const auth = useAuthStore()
</script>
