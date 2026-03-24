<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon left>mdi-chart-box</v-icon>
      Метрики покрытия
    </v-card-title>

    <v-card-text>
      <div v-if="loading" class="text-center py-4">
        <v-progress-circular indeterminate color="primary"></v-progress-circular>
      </div>

      <div v-else-if="error" class="text-center py-4">
        <v-icon size="48" color="error">mdi-alert-circle</v-icon>
        <div class="text-body-2 text-medium-emphasis mt-2">{{ error }}</div>
      </div>

      <div v-else-if="metrics">
        <!-- Coverage Progress -->
        <div class="mb-4">
          <div class="d-flex justify-space-between mb-2">
            <span class="text-body-2 font-weight-bold">Покрытие документа</span>
            <span class="text-body-2 font-weight-bold" :class="getCoverageColor()">
              {{ Math.round(metrics.coverage_percent) }}%
            </span>
          </div>
          <div class="text-caption text-medium-emphasis mb-2">
            Обработано {{ metrics.processed_pages }} из {{ metrics.total_pages }} страниц
            <span v-if="metrics.skipped_pages && metrics.skipped_pages.length > 0" class="text-warning">
              (пропущено: {{ metrics.skipped_pages.length }})
            </span>
          </div>
          <v-progress-linear
            :model-value="metrics.coverage_percent"
            height="24"
            :color="getCoverageColorName()"
            rounded
          >
            <strong>{{ Math.round(metrics.coverage_percent) }}%</strong>
          </v-progress-linear>
        </div>

        <v-divider class="my-3"></v-divider>

        <!-- Requirements Count -->
        <div class="mb-3">
          <div class="text-body-2 font-weight-bold mb-2">
            <v-icon left size="small">mdi-clipboard-list</v-icon>
            Всего требований: {{ metrics.requirements_count }}
          </div>
        </div>

        <!-- Requirements by Type -->
        <div v-if="metrics.requirements_by_type && Object.keys(metrics.requirements_by_type).length > 0" class="mb-3">
          <div class="text-body-2 font-weight-bold mb-2">По типам:</div>
          <v-list density="compact" class="py-0">
            <v-list-item
              v-for="(count, type) in sortedRequirementsByType"
              :key="type"
              class="px-0 py-1"
            >
              <v-list-item-title class="text-body-2">
                {{ type }}
              </v-list-item-title>
              <template v-slot:append>
                <v-chip size="x-small" color="primary">{{ count }}</v-chip>
              </template>
            </v-list-item>
          </v-list>
        </div>

        <v-divider class="my-3"></v-divider>

        <!-- Skipped Pages -->
        <div v-if="metrics.skipped_pages && metrics.skipped_pages.length > 0">
          <div class="text-body-2 font-weight-bold mb-2">
            <v-icon left size="small" color="warning">mdi-alert</v-icon>
            Пропущено страниц: {{ metrics.skipped_pages.length }}
          </div>
          <v-chip-group column>
            <v-chip
              v-for="page in visibleSkippedPages"
              :key="page"
              size="x-small"
              variant="outlined"
              class="chip-clickable"
              @click="goToPage(page)"
            >
              {{ page }}
            </v-chip>
            <v-chip
              v-if="metrics.skipped_pages.length > 10 && !expandedSkipped"
              size="x-small"
              variant="text"
              class="chip-clickable"
              @click="expandedSkipped = true"
            >
              +{{ metrics.skipped_pages.length - 10 }} ещё
            </v-chip>
            <v-chip
              v-else-if="metrics.skipped_pages.length > 10 && expandedSkipped"
              size="x-small"
              variant="tonal"
              class="chip-clickable"
              @click="expandedSkipped = false"
            >
              Свернуть
            </v-chip>
          </v-chip-group>
        </div>

        <!-- Last Updated -->
        <div class="text-caption text-medium-emphasis mt-3">
          Обновлено: {{ formatDate(metrics.calculated_at) }}
        </div>
      </div>

      <div v-else class="text-center py-4">
        <v-icon size="48" color="grey">mdi-chart-box-outline</v-icon>
        <div class="text-body-2 text-medium-emphasis mt-2">Метрики пока недоступны</div>
      </div>
    </v-card-text>

    <v-card-actions v-if="!loading && !error">
      <v-btn
        variant="text"
        size="small"
        @click="refreshMetrics"
        :loading="loading"
      >
        <v-icon left>mdi-refresh</v-icon>
        Обновить
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { documentsApi } from '@/services/api'

const props = defineProps({
  documentId: {
    type: [String, Number],
    required: true
  }
})

const emit = defineEmits(['view-page'])

const loading = ref(false)
const error = ref(null)
const metrics = ref(null)
const expandedSkipped = ref(false)

const visibleSkippedPages = computed(() => {
  if (!metrics.value?.skipped_pages) return []
  const pages = metrics.value.skipped_pages
  return expandedSkipped.value ? pages : pages.slice(0, 10)
})

const goToPage = (page) => {
  emit('view-page', page)
}

const sortedRequirementsByType = computed(() => {
  if (!metrics.value?.requirements_by_type) return {}
  
  const entries = Object.entries(metrics.value.requirements_by_type)
  entries.sort((a, b) => b[1] - a[1]) // Sort by count descending
  
  return Object.fromEntries(entries)
})

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getCoverageColorName = () => {
  if (!metrics.value) return 'grey'
  const percent = metrics.value.coverage_percent
  if (percent >= 90) return 'success'
  if (percent >= 70) return 'primary'
  if (percent >= 50) return 'warning'
  return 'error'
}

const getCoverageColor = () => {
  if (!metrics.value) return 'text-grey'
  const percent = metrics.value.coverage_percent
  if (percent >= 90) return 'text-success'
  if (percent >= 70) return 'text-primary'
  if (percent >= 50) return 'text-warning'
  return 'text-error'
}

const fetchMetrics = async () => {
  if (!props.documentId) return
  
  loading.value = true
  error.value = null
  
  try {
    const response = await documentsApi.getMetrics(props.documentId)
    metrics.value = response.data
  } catch (err) {
    error.value = err.response?.data?.detail || 'Не удалось загрузить метрики'
  } finally {
    loading.value = false
  }
}

const refreshMetrics = () => {
  fetchMetrics()
}

watch(() => props.documentId, () => {
  expandedSkipped.value = false
  fetchMetrics()
})

onMounted(() => {
  fetchMetrics()
})
</script>

<style scoped>
.v-progress-linear {
  border-radius: 4px;
}

.chip-clickable {
  cursor: pointer;
}
.chip-clickable:hover {
  opacity: 0.85;
}
</style>
