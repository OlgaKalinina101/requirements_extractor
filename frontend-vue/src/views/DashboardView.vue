<template>
  <div>
    <!-- ── Header: Title + Filter toggle ──────────────────────── -->
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">
        <v-icon left color="primary" class="mr-3">mdi-view-dashboard</v-icon>
        Дашборд
      </h1>
      <v-spacer />
      <v-badge
        :content="activeFilterCount"
        :model-value="activeFilterCount > 0"
        color="primary"
        overlap
        offset-x="4"
        offset-y="4"
      >
        <v-btn
          :variant="showFilters ? 'flat' : 'outlined'"
          :color="showFilters ? 'primary' : 'grey-darken-1'"
          @click="showFilters = !showFilters"
        >
          <v-icon start>mdi-filter-variant</v-icon>
          Фильтры
        </v-btn>
      </v-badge>
    </div>

    <!-- ── Collapsible filters panel ──────────────────────────── -->
    <v-expand-transition>
      <div v-show="showFilters">
        <div class="filter-panel mb-4">
          <v-row align="center" dense>
            <v-col cols="12" md="3">
              <v-select
                v-model="filterProjectId"
                :items="projectOptions"
                item-title="title"
                item-value="value"
                label="Проект"
                density="compact"
                hide-details
                clearable
                variant="outlined"
                @update:model-value="onFilterChange"
              >
                <template #prepend-inner>
                  <v-icon size="16">mdi-folder-outline</v-icon>
                </template>
              </v-select>
            </v-col>
            <v-col cols="12" md="3">
              <v-select
                v-model="filterAssigneeId"
                :items="userOptions"
                item-title="title"
                item-value="value"
                label="Ответственный"
                density="compact"
                hide-details
                clearable
                variant="outlined"
                @update:model-value="onFilterChange"
              >
                <template #prepend-inner>
                  <v-icon size="16">mdi-account-outline</v-icon>
                </template>
              </v-select>
            </v-col>
            <v-col cols="12" md="3">
              <v-select
                v-model="filterDiscipline"
                :items="disciplineOptions"
                item-title="title"
                item-value="value"
                label="Дисциплина"
                density="compact"
                hide-details
                clearable
                variant="outlined"
                @update:model-value="onFilterChange"
              >
                <template #prepend-inner>
                  <v-icon size="16">mdi-tag-outline</v-icon>
                </template>
              </v-select>
            </v-col>
            <v-col cols="12" md="3" />
          </v-row>
          <v-row align="center" dense class="mt-2">
            <v-col cols="12" md="3">
              <v-select
                v-model="filterStatus"
                :items="statusOptions"
                item-title="title"
                item-value="value"
                label="Статус"
                density="compact"
                hide-details
                clearable
                variant="outlined"
                @update:model-value="onFilterChange"
              />
            </v-col>
            <v-col cols="12" md="3">
              <v-select
                v-model="filterPriority"
                :items="priorityOptions"
                item-title="title"
                item-value="value"
                label="Приоритет"
                density="compact"
                hide-details
                clearable
                variant="outlined"
                @update:model-value="onFilterChange"
              />
            </v-col>
            <v-col cols="12" md="3">
              <v-select
                v-model="filterType"
                :items="typeOptions"
                item-title="title"
                item-value="value"
                label="Тип"
                density="compact"
                hide-details
                clearable
                variant="outlined"
                @update:model-value="onFilterChange"
              />
            </v-col>
            <v-col cols="12" md="3" class="d-flex align-center justify-end">
              <v-btn
                variant="outlined"
                color="grey-darken-1"
                class="filter-reset-btn"
                :disabled="activeFilterCount === 0"
                @click="resetFilters"
              >
                <v-icon start size="16">mdi-refresh</v-icon>
                Сбросить
              </v-btn>
            </v-col>
          </v-row>
        </div>
      </div>
    </v-expand-transition>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <!-- ── Summary Cards ──────────────────────────────────────── -->
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

    <!-- ── Distribution Charts ────────────────────────────────── -->
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
                <span class="text-caption text-medium-emphasis" style="min-width: 28px; text-align: right">{{ item.count }}</span>
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
                <span class="text-caption text-medium-emphasis" style="min-width: 28px; text-align: right">{{ item.count }}</span>
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
                <span class="text-caption text-medium-emphasis" style="min-width: 28px; text-align: right">{{ item.count }}</span>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- ── Workload + Projects ────────────────────────────────── -->
    <v-row>
      <v-col cols="12" md="7">
        <v-card class="workload-card">
          <v-card-title class="workload-card__title">
            <v-icon class="mr-2" color="primary">mdi-account-group</v-icon>
            Нагрузка по ответственным
          </v-card-title>
          <v-card-text class="workload-card__body">
            <div v-if="stats.assignee_workload.length === 0" class="text-body-2 text-medium-emphasis pa-4 text-center">
              <v-icon size="36" color="grey-lighten-2" class="d-block mx-auto mb-2">mdi-account-off-outline</v-icon>
              Нет назначенных требований
            </div>
            <v-row v-else dense>
              <v-col
                v-for="(a, idx) in stats.assignee_workload"
                :key="a.assignee_id"
                cols="12" sm="6" lg="4"
              >
                <div class="assignee-card" :style="{ '--accent': assigneeColors[idx % assigneeColors.length] }">
                  <div class="assignee-card__header">
                    <div class="assignee-card__avatar">
                      {{ avatarInitials(a.assignee_name) }}
                    </div>
                    <div class="assignee-card__info">
                      <div class="assignee-card__name">{{ a.assignee_name }}</div>
                      <div class="assignee-card__total">{{ a.total }} требований</div>
                    </div>
                    <div class="assignee-card__pct">
                      {{ a.total > 0 ? Math.round((a.done / a.total) * 100) : 0 }}%
                    </div>
                  </div>
                  <div class="assignee-card__bar-wrap">
                    <div class="assignee-card__bar-track">
                      <div class="assignee-card__bar-seg assignee-card__bar-done"    :style="{ width: barPct(a.done, a.total) + '%' }"       :title="`Выполнено: ${a.done}`" />
                      <div class="assignee-card__bar-seg assignee-card__bar-progress" :style="{ width: barPct(a.in_progress, a.total) + '%' }" :title="`В работе: ${a.in_progress}`" />
                      <div class="assignee-card__bar-seg assignee-card__bar-pending"  :style="{ width: barPct(a.pending, a.total) + '%' }"     :title="`Ожидает: ${a.pending}`" />
                    </div>
                  </div>
                  <div class="assignee-card__stats">
                    <div class="assignee-card__stat">
                      <span class="assignee-card__stat-dot done" />
                      <span>Выполнено</span>
                      <strong>{{ a.done }}</strong>
                    </div>
                    <div class="assignee-card__stat">
                      <span class="assignee-card__stat-dot progress" />
                      <span>В работе</span>
                      <strong>{{ a.in_progress }}</strong>
                    </div>
                    <div class="assignee-card__stat">
                      <span class="assignee-card__stat-dot pending" />
                      <span>Ожидает</span>
                      <strong>{{ a.pending }}</strong>
                    </div>
                  </div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="5">
        <v-card class="projects-card">
          <v-card-title>
            <v-icon class="mr-2" color="primary">mdi-folder-multiple</v-icon>
            Проекты
          </v-card-title>
          <v-card-text class="projects-card__body pa-0">
            <v-alert v-if="!loading && projects.length === 0" type="info" variant="tonal" class="ma-3">
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
import { ref, reactive, onMounted, computed } from 'vue'
import { dashboardApi, projectsApi, usersApi } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'
import { useDictionariesStore } from '@/stores/dictionaries'

const notifications = useNotificationsStore()
const dictionaries = useDictionariesStore()
const loading = ref(true)
const projects = ref([])
const showFilters = ref(false)
const filterProjectId = ref(null)
const filterAssigneeId = ref(null)
const filterDiscipline = ref(null)
const filterStatus = ref(null)
const filterPriority = ref(null)
const filterType = ref(null)
const projectsForFilter = ref([])
const usersForFilter = ref([])

const projectOptions = computed(() => [
  { title: 'Все', value: null },
  ...projectsForFilter.value.map(p => ({ title: p.name, value: p.id })),
])
const userOptions = computed(() => [
  { title: 'Все', value: null },
  ...usersForFilter.value.filter(u => u.is_active).map(u => ({
    title: u.full_name || u.email,
    value: u.id,
  })),
])
const disciplineOptions = computed(() => [
  { title: 'Все', value: null },
  ...(dictionaries.disciplineOptions || []),
])
const statusOptions = computed(() => [
  { title: 'Все', value: null },
  ...dictionaries.statuses.map(s => ({ title: s.name, value: s.code })),
])
const priorityOptions = computed(() => [
  { title: 'Все', value: null },
  ...dictionaries.priorities.map(p => ({ title: p.name, value: p.code })),
])
const typeOptions = computed(() => [
  { title: 'Все', value: null },
  ...dictionaries.types.map(t => ({ title: t.name, value: t.code })),
])

const activeFilterCount = computed(() =>
  [filterProjectId, filterAssigneeId, filterDiscipline, filterStatus, filterPriority, filterType]
    .filter(f => f.value != null)
    .length
)

const stats = reactive({
  totalRequirements: 0,
  totalDocuments: 0,
  totalProjects: 0,
  by_status: [],
  by_priority: [],
  by_type: [],
  assignee_workload: [],
})

const assigneeColors = [
  '#5C6BC0', '#26A69A', '#EF5350', '#AB47BC',
  '#42A5F5', '#FFA726', '#66BB6A', '#EC407A',
]

const avatarInitials = (name) => {
  if (!name) return '?'
  const parts = name.trim().split(' ')
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

const barPct = (val, total) => {
  if (!total) return 0
  return Math.min(100, Math.round((val / total) * 100))
}

const statusLabel = (s) => dictionaries.statusName(s) || s || 'Неизвестно'
const priorityLabel = (p) => dictionaries.priorityName(p) || p || 'Неизвестно'
const typeLabel = (t) => dictionaries.typeName(t) || t || 'Неизвестно'

function buildParams() {
  const params = {}
  if (filterProjectId.value != null && filterProjectId.value !== '') params.project_id = filterProjectId.value
  if (filterAssigneeId.value != null && filterAssigneeId.value !== '') params.assignee_id = filterAssigneeId.value
  if (filterDiscipline.value != null && filterDiscipline.value !== '') params.discipline = filterDiscipline.value
  if (filterStatus.value) params.status = filterStatus.value
  if (filterPriority.value) params.priority = filterPriority.value
  if (filterType.value) params.type = filterType.value
  return params
}

async function fetchData() {
  loading.value = true
  try {
    const params = buildParams()
    const projectsParams = params.project_id != null ? { project_id: params.project_id } : {}
    const [dashboardRes, projectsRes] = await Promise.all([
      dashboardApi.getStats(params),
      projectsApi.getAll(projectsParams),
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
    })
    projects.value = projectsRes.data?.projects ?? []
  } catch (err) {
    notifications.notifyError('Не удалось загрузить данные дашборда')
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  fetchData()
}

function resetFilters() {
  filterProjectId.value = null
  filterAssigneeId.value = null
  filterDiscipline.value = null
  filterStatus.value = null
  filterPriority.value = null
  filterType.value = null
  fetchData()
}

onMounted(async () => {
  try {
    await dictionaries.loadAll()
    const [projectsRes, usersRes] = await Promise.all([
      projectsApi.getAll(),
      usersApi.getAll(),
    ])
    projectsForFilter.value = projectsRes.data?.projects ?? []
    usersForFilter.value = usersRes.data ?? []
    await fetchData()
  } catch (err) {
    notifications.notifyError('Не удалось загрузить данные дашборда')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
/* ── Filter Panel ───────────────────────────────────────────── */
.filter-panel {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.filter-reset-btn {
  text-transform: none;
  font-size: 14px;
  font-weight: 500;
  min-height: 40px;
  background: #fff;
  border-color: #cbd5e1;
  color: #475569;
}
.filter-reset-btn:disabled {
  opacity: 0.5;
}

.filter-panel :deep(.v-field) {
  background: #fff;
}

.filter-panel :deep(.v-field__outline) {
  --v-field-border-opacity: 1;
  color: #cbd5e1;
}

.filter-panel :deep(.v-label),
.filter-panel :deep(.v-field input),
.filter-panel :deep(.v-field .v-field__input),
.filter-panel :deep(.v-field .v-select__selection-text) {
  color: #334155;
  font-size: 14px;
}

.filter-panel :deep(.v-field__prepend-inner .v-icon),
.filter-panel :deep(.v-field__clearable .v-icon) {
  color: #94a3b8;
}

/* ── Workload Section ──────────────────────────────────────── */
.workload-card {
  border-radius: 12px !important;
  overflow: hidden;
}

.workload-card__title {
  font-size: 15px !important;
  font-weight: 700;
  padding-top: 16px;
  padding-bottom: 4px;
}

.workload-card__body {
  max-height: 400px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

.projects-card {
  border-radius: 12px !important;
  overflow: hidden;
}

.projects-card__body {
  max-height: 400px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

/* ── Assignee Cards ────────────────────────────────────────── */
.assignee-card {
  background: #fff;
  border: 1.5px solid #f0f0f0;
  border-radius: 12px;
  padding: 14px 16px 12px;
  transition: box-shadow 0.2s, transform 0.2s;
  height: 100%;
}

.assignee-card:hover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.10);
  transform: translateY(-2px);
}

.assignee-card__header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.assignee-card__avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--accent, #5C6BC0);
  color: white;
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  letter-spacing: 0.5px;
}

.assignee-card__info {
  flex: 1;
  min-width: 0;
}

.assignee-card__name {
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #1a1a2e;
}

.assignee-card__total {
  font-size: 12px;
  color: #888;
  margin-top: 1px;
}

.assignee-card__pct {
  font-size: 20px;
  font-weight: 800;
  color: var(--accent, #5C6BC0);
  min-width: 46px;
  text-align: right;
  letter-spacing: -0.5px;
}

.assignee-card__bar-wrap {
  margin-bottom: 10px;
}

.assignee-card__bar-track {
  height: 8px;
  background: #f0f0f0;
  border-radius: 99px;
  overflow: hidden;
  display: flex;
}

.assignee-card__bar-seg {
  height: 100%;
  transition: width 0.5s ease;
}

.assignee-card__bar-done    { background: #4CAF50; }
.assignee-card__bar-progress { background: #42A5F5; }
.assignee-card__bar-pending  { background: #E0E0E0; }

.assignee-card__stats {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.assignee-card__stat {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
}

.assignee-card__stat strong {
  color: #1a1a2e;
  font-weight: 700;
  margin-left: 2px;
}

.assignee-card__stat-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

.assignee-card__stat-dot.done     { background: #4CAF50; }
.assignee-card__stat-dot.progress { background: #42A5F5; }
.assignee-card__stat-dot.pending  { background: #BDBDBD; }
</style>
