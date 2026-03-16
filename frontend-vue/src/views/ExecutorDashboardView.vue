<template>
  <div>
    <h1 class="text-h4 mb-4">
      <v-icon left color="primary" class="mr-3">mdi-view-dashboard</v-icon>
      Дашборд
    </h1>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <!-- Summary: My requirements -->
    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="4">
        <v-card color="primary" dark>
          <v-card-text>
            <div class="text-h3">{{ stats.total }}</div>
            <div class="text-subtitle-1">Мои требования</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="4">
        <v-card variant="tonal" color="primary">
          <v-card-text>
            <div class="text-h3">{{ doneCount }}</div>
            <div class="text-subtitle-1">Выполнено</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="4">
        <v-card variant="tonal" color="warning">
          <v-card-text>
            <div class="text-h3">{{ inProgressCount }}</div>
            <div class="text-subtitle-1">В работе</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- By status -->
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Мои требования по статусам</v-card-title>
          <v-card-text>
            <div v-if="stats.by_status.length === 0" class="text-body-2 text-medium-emphasis">
              Нет назначенных требований
            </div>
            <div v-else class="d-flex flex-column ga-2">
              <div v-for="item in stats.by_status" :key="item.status" class="d-flex align-center ga-2">
                <span class="text-body-2" style="min-width: 120px">{{ statusLabel(item.status) }}</span>
                <v-progress-linear
                  :model-value="stats.total > 0 ? (item.count / stats.total) * 100 : 0"
                  color="primary"
                  height="8"
                  rounded
                />
                <span class="text-caption text-medium-emphasis">{{ item.count }}</span>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Проекты</v-card-title>
          <v-card-text>
            <v-alert v-if="!loading && projects.length === 0" type="info" variant="tonal">
              Проектов пока нет.
            </v-alert>
            <v-table v-else density="compact">
              <thead>
                <tr>
                  <th>Проект</th>
                  <th>Документов</th>
                  <th>Требований</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in projects" :key="p.id">
                  <td>{{ p.name }}</td>
                  <td>{{ p.documents_count }}</td>
                  <td>{{ p.requirements_count }}</td>
                  <td>
                    <v-btn size="small" variant="text" :to="`/projects/${p.id}`" icon="mdi-arrow-right" />
                  </td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Recent my requirements -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>Последние назначенные требования</v-card-title>
          <v-card-text>
            <div v-if="stats.recent_requirements.length === 0" class="text-body-2 text-medium-emphasis">
              Нет назначенных требований
            </div>
            <v-list v-else density="compact">
              <v-list-item
                v-for="r in stats.recent_requirements"
                :key="r.id"
                :to="`/requirement/${r.id}`"
                class="px-0"
              >
                <template v-slot:prepend>
                  <v-chip size="small" color="primary" variant="tonal">{{ r.requirement_id }}</v-chip>
                </template>
                <v-list-item-title class="text-body-2">{{ r.text }}</v-list-item-title>
                <v-list-item-subtitle>
                  <v-chip size="x-small" :color="statusColor(r.status)">{{ statusLabel(r.status) }}</v-chip>
                  <span v-if="r.document_id" class="ml-2">Документ #{{ r.document_id }}</span>
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { dashboardApi, projectsApi } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'

const notifications = useNotificationsStore()
const loading = ref(true)
const projects = ref([])

const stats = reactive({
  total: 0,
  by_status: [],
  recent_requirements: [],
})

const statusLabels = {
  pending: 'Ожидает',
  accepted: 'Принято',
  rejected: 'Отклонено',
  modified: 'Изменено',
  in_progress: 'В работе',
  done: 'Выполнено',
  blocked: 'Заблокировано',
  unknown: 'Неизвестно',
}

const statusLabel = (s) => statusLabels[s] || s || 'Неизвестно'

const statusColor = (s) => {
  const colors = { pending: 'grey', accepted: 'green', rejected: 'red', modified: 'blue', in_progress: 'orange', done: 'green', blocked: 'red' }
  return colors[s] || 'grey'
}

const doneCount = computed(() => {
  return stats.by_status
    .filter((x) => ['accepted', 'modified', 'rejected', 'done'].includes(x.status))
    .reduce((s, x) => s + x.count, 0)
})

const inProgressCount = computed(() => {
  return stats.by_status
    .filter((x) => ['in_progress', 'blocked'].includes(x.status))
    .reduce((s, x) => s + x.count, 0)
})

onMounted(async () => {
  try {
    const [dashboardRes, projectsRes] = await Promise.all([
      dashboardApi.getStats(),
      projectsApi.getAll(),
    ])
    const d = dashboardRes.data
    stats.total = d.total ?? 0
    stats.by_status = d.by_status ?? []
    stats.recent_requirements = d.recent_requirements ?? []
    projects.value = projectsRes.data?.projects ?? []
  } catch (err) {
    notifications.notifyError('Не удалось загрузить данные дашборда')
  } finally {
    loading.value = false
  }
})
</script>
