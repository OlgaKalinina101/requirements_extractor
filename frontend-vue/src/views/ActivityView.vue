<template>
  <div>
    <h1 class="text-h4 mb-4">
      <v-icon left color="primary" class="mr-3">mdi-history</v-icon>
      Последняя активность
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-4">
      Кто что изменял в системе. Доступно только администратору.
    </p>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <v-card>
      <v-card-text>
        <div v-if="!loading && activities.length === 0" class="text-body-2 text-medium-emphasis">Нет активности</div>
        <v-list v-else density="compact" class="py-0">
          <v-list-item
            v-for="(act, idx) in activities"
            :key="idx"
            :to="activityLink(act)"
            class="px-0"
            :active="false"
          >
            <template v-slot:prepend>
              <v-icon size="small" :icon="activityIcon(act)" :color="activityColor(act)" />
            </template>
            <v-list-item-title class="text-body-2">
              {{ activityText(act) }}
            </v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              {{ formatTime(act.timestamp) }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { dashboardApi } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'

const notifications = useNotificationsStore()
const loading = ref(true)
const activities = ref([])

const activityIcon = (act) => {
  if (act.type === 'requirement_created') return 'mdi-plus-circle'
  if (act.type === 'requirement_edited') return 'mdi-pencil'
  if (act.type === 'comment_added') return 'mdi-comment'
  return 'mdi-circle'
}

const activityColor = (act) => {
  if (act.type === 'requirement_created') return 'success'
  if (act.type === 'requirement_edited') return 'warning'
  if (act.type === 'comment_added') return 'info'
  return 'grey'
}

const activityText = (act) => {
  if (act.type === 'requirement_created') return `Создано требование ${act.requirement_code}`
  if (act.type === 'requirement_edited') return `Изменено ${act.requirement_code}${act.edited_by ? ` (${act.edited_by})` : ''}`
  if (act.type === 'comment_added') return `Комментарий к требованию #${act.requirement_id}`
  return ''
}

const activityLink = (act) => {
  if (act.requirement_id) return `/requirement/${act.requirement_id}`
  if (act.document_id) return `/review/${act.document_id}`
  return null
}

const formatTime = (ts) => {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    const now = new Date()
    const diff = now - d
    if (diff < 60000) return 'только что'
    if (diff < 3600000) return `${Math.floor(diff / 60000)} мин. назад`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} ч. назад`
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ts
  }
}

onMounted(async () => {
  try {
    const res = await dashboardApi.getActivity({ limit: 200 })
    activities.value = res.data?.activities ?? []
  } catch (err) {
    notifications.notifyError('Не удалось загрузить активность')
  } finally {
    loading.value = false
  }
})
</script>
