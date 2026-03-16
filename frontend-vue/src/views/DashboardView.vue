<template>
  <div>
    <h1 class="text-h4 mb-4">
      <v-icon left color="primary" class="mr-3">mdi-view-dashboard</v-icon>
      Дашборд
    </h1>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <!-- Summary Cards -->
    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="4">
        <v-card color="blue" dark>
          <v-card-text>
            <div class="text-h3">{{ stats.totalRequirements }}</div>
            <div class="text-subtitle-1">Всего требований</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="4">
        <v-card color="green" dark>
          <v-card-text>
            <div class="text-h3">{{ stats.totalDocuments }}</div>
            <div class="text-subtitle-1">Документов</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="4">
        <v-card color="purple" dark>
          <v-card-text>
            <div class="text-h3">{{ stats.totalProjects }}</div>
            <div class="text-subtitle-1">Проектов</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Distribution charts -->
    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>По статусам</v-card-title>
          <v-card-text>
            <div v-if="stats.by_status.length === 0" class="text-body-2 text-medium-emphasis">Нет данных</div>
            <div v-else class="d-flex flex-column ga-2">
              <div v-for="item in stats.by_status" :key="item.status" class="d-flex align-center ga-2">
                <span class="text-body-2" style="min-width: 100px">{{ statusLabel(item.status) }}</span>
                <v-progress-linear
                  :model-value="stats.totalRequirements > 0 ? (item.count / stats.totalRequirements) * 100 : 0"
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

      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>По приоритетам</v-card-title>
          <v-card-text>
            <div v-if="stats.by_priority.length === 0" class="text-body-2 text-medium-emphasis">Нет данных</div>
            <div v-else class="d-flex flex-column ga-2">
              <div v-for="item in stats.by_priority" :key="item.priority" class="d-flex align-center ga-2">
                <span class="text-body-2" style="min-width: 100px">{{ priorityLabel(item.priority) }}</span>
                <v-progress-linear
                  :model-value="stats.totalRequirements > 0 ? (item.count / stats.totalRequirements) * 100 : 0"
                  color="secondary"
                  height="8"
                  rounded
                />
                <span class="text-caption text-medium-emphasis">{{ item.count }}</span>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>По типам</v-card-title>
          <v-card-text>
            <div v-if="stats.by_type.length === 0" class="text-body-2 text-medium-emphasis">Нет данных</div>
            <div v-else class="d-flex flex-column ga-2">
              <div v-for="item in stats.by_type" :key="item.type" class="d-flex align-center ga-2">
                <span class="text-body-2" style="min-width: 100px">{{ typeLabel(item.type) }}</span>
                <v-progress-linear
                  :model-value="stats.totalRequirements > 0 ? (item.count / stats.totalRequirements) * 100 : 0"
                  color="success"
                  height="8"
                  rounded
                />
                <span class="text-caption text-medium-emphasis">{{ item.count }}</span>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Assignee workload -->
    <v-row class="mb-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Нагрузка по ответственным</v-card-title>
          <v-card-text>
            <div v-if="stats.assignee_workload.length === 0" class="text-body-2 text-medium-emphasis">
              Нет назначенных требований
            </div>
            <div v-else class="d-flex flex-column ga-3">
              <div v-for="a in stats.assignee_workload" :key="a.assignee_id" class="d-flex flex-column ga-1">
                <div class="d-flex justify-space-between align-center">
                  <span class="text-body-2 font-weight-medium">{{ a.assignee_name }}</span>
                  <span class="text-caption text-medium-emphasis">
                    {{ a.done }} / {{ a.total }} выполнено
                  </span>
                </div>
                <v-progress-linear
                  :model-value="a.total > 0 ? (a.done / a.total) * 100 : 0"
                  color="primary"
                  height="10"
                  rounded
                />
                <div class="d-flex ga-2 text-caption text-medium-emphasis">
                  <span>Выполнено: {{ a.done }}</span>
                  <span>В работе: {{ a.in_progress }}</span>
                  <span>Ожидает: {{ a.pending }}</span>
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Recent activity + Projects -->
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Последняя активность</v-card-title>
          <v-card-text>
            <div v-if="stats.recent_activity.length === 0" class="text-body-2 text-medium-emphasis">
              Нет активности
            </div>
            <v-list v-else density="compact" class="py-0">
              <v-list-item
                v-for="(act, idx) in stats.recent_activity.slice(0, 15)"
                :key="idx"
                :to="activityLink(act)"
                class="px-0"
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
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Проекты</v-card-title>
          <v-card-text>
            <v-alert v-if="!loading && projects.length === 0" type="info" variant="tonal">
              Проектов пока нет. <v-btn variant="text" to="/">Создать проект</v-btn>
            </v-alert>
            <v-table v-else density="compact">
              <thead>
                <tr>
                  <th>Проект</th>
                  <th>Статус</th>
                  <th>Документов</th>
                  <th>Требований</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in projects" :key="p.id">
                  <td>{{ p.name }}</td>
                  <td><v-chip size="small" :color="p.status === 'active' ? 'green' : 'grey'">{{ p.status }}</v-chip></td>
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { dashboardApi, projectsApi } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'

const notifications = useNotificationsStore()
const loading = ref(true)
const projects = ref([])

const stats = reactive({
  totalRequirements: 0,
  totalDocuments: 0,
  totalProjects: 0,
  by_status: [],
  by_priority: [],
  by_type: [],
  assignee_workload: [],
  recent_activity: [],
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

const priorityLabels = {
  Mandatory: 'Обязательное',
  Recommended: 'Рекомендуемое',
  Optional: 'Опциональное',
  Critical: 'Критический',
  High: 'Высокий',
  Medium: 'Средний',
  Low: 'Низкий',
  unknown: 'Неизвестно',
}

const priorityLabel = (p) => priorityLabels[p] || p || 'Неизвестно'

const typeLabel = (t) => t || 'Неизвестно'

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
    const [dashboardRes, projectsRes] = await Promise.all([
      dashboardApi.getStats(),
      projectsApi.getAll(),
    ])
    const d = dashboardRes.data
    Object.assign(stats, {
      totalRequirements: d.total_requirements ?? 0,
      totalDocuments: d.total_documents ?? 0,
      totalProjects: d.total_projects ?? 0,
      by_status: d.by_status ?? [],
      by_priority: d.by_priority ?? [],
      by_type: d.by_type ?? [],
      assignee_workload: d.assignee_workload ?? [],
      recent_activity: d.recent_activity ?? [],
    })
    projects.value = projectsRes.data?.projects ?? []
  } catch (err) {
    notifications.notifyError('Не удалось загрузить данные дашборда')
  } finally {
    loading.value = false
  }
})
</script>
