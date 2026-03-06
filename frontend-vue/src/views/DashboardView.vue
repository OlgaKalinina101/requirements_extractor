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

    <!-- Projects Table -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>Проекты</v-card-title>
          <v-card-text>
            <v-alert v-if="!loading && projects.length === 0" type="info" variant="tonal">
              Проектов пока нет. <v-btn variant="text" to="/projects">Создать проект</v-btn>
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
import { ref, computed, onMounted } from 'vue'
import { projectsApi } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'

const notifications = useNotificationsStore()
const loading = ref(true)
const projects = ref([])

const stats = computed(() => {
  const total = projects.value.reduce((s, p) => s + (p.requirements_count || 0), 0)
  return {
    totalRequirements: total,
    totalProjects: projects.value.length,
    totalDocuments: projects.value.reduce((s, p) => s + (p.documents_count || 0), 0),
  }
})

const statusDistribution = ref([])
const priorityDistribution = ref([])

onMounted(async () => {
  try {
    const { data } = await projectsApi.getAll()
    projects.value = data.projects || []
  } catch (err) {
    notifications.notifyError('Не удалось загрузить данные дашборда')
  } finally {
    loading.value = false
  }
})
</script>
