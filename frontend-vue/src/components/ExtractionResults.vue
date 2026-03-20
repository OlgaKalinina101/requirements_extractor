<template>
  <v-card class="extraction-results">
    <v-card-title class="d-flex align-center">
      <v-icon left color="success">mdi-check-circle</v-icon>
      Обработка завершена
      <v-spacer></v-spacer>
      <v-chip color="success" variant="flat">
        {{ results.requirements_count }} требований
      </v-chip>
    </v-card-title>

    <v-divider></v-divider>

    <!-- Statistics -->
    <v-card-text>
      <v-row>
        <v-col cols="6" md="3">
          <div class="stat-item">
            <div class="stat-value">{{ results.requirements_count || 0 }}</div>
            <div class="stat-label">Требований</div>
          </div>
        </v-col>
        
        <v-col cols="6" md="3">
          <div class="stat-item">
            <div class="stat-value">{{ results.sections_count || 0 }}</div>
            <div class="stat-label">Секций</div>
          </div>
        </v-col>
        
        <v-col cols="6" md="3">
          <div class="stat-item">
            <div class="stat-value">{{ formatNumber(results.total_tokens || 0) }}</div>
            <div class="stat-label">Токенов</div>
          </div>
        </v-col>
        
        <v-col cols="6" md="3">
          <div class="stat-item">
            <div class="stat-value">${{ (results.total_cost || 0).toFixed(4) }}</div>
            <div class="stat-label">Стоимость</div>
          </div>
        </v-col>
      </v-row>

      <v-row class="mt-2">
        <v-col cols="12" md="6">
          <div class="stat-item">
            <div class="stat-value">{{ (results.processing_time || 0).toFixed(1) }}с</div>
            <div class="stat-label">Время обработки</div>
          </div>
        </v-col>
        
        <v-col cols="12" md="6">
          <div class="stat-item">
            <div class="stat-value">{{ displayModelName }}</div>
            <div class="stat-label">AI модель</div>
          </div>
        </v-col>
      </v-row>
    </v-card-text>

    <v-divider></v-divider>

    <!-- Warning if document_id is missing -->
    <v-card-text v-if="!results.document_id">
      <v-alert
        type="warning"
        variant="tonal"
        density="compact"
      >
        <v-icon left size="small">mdi-alert</v-icon>
        Документ не был сохранен в базу данных. Файлы для скачивания недоступны.
      </v-alert>
    </v-card-text>

    <!-- Download Files from DB -->
    <v-card-text v-if="results.document_id">
      <div class="text-subtitle-1 font-weight-bold mb-3">
        <v-icon left>mdi-download</v-icon>
        Скачать отчеты
      </div>

      <v-list density="compact">
        <v-list-item
          class="download-item"
          @click="triggerExport('word')"
          :disabled="exportingFormat === 'word'"
        >
          <template v-slot:prepend>
            <v-icon color="blue">mdi-file-word</v-icon>
          </template>
          <v-list-item-title>Word документ</v-list-item-title>
          <v-list-item-subtitle>Реестр требований + метрики покрытия</v-list-item-subtitle>
          <template v-slot:append>
            <v-progress-circular v-if="exportingFormat === 'word'" indeterminate size="20" width="2" />
            <v-icon v-else>mdi-download</v-icon>
          </template>
        </v-list-item>

        <v-list-item
          class="download-item"
          @click="triggerExport('xlsx')"
          :disabled="exportingFormat === 'xlsx'"
        >
          <template v-slot:prepend>
            <v-icon color="success">mdi-file-excel</v-icon>
          </template>
          <v-list-item-title>Excel (XLSX)</v-list-item-title>
          <v-list-item-subtitle>Реестр требований с полной структурой</v-list-item-subtitle>
          <template v-slot:append>
            <v-progress-circular v-if="exportingFormat === 'xlsx'" indeterminate size="20" width="2" />
            <v-icon v-else>mdi-download</v-icon>
          </template>
        </v-list-item>

        <v-list-item
          class="download-item"
          @click="triggerExport('json')"
          :disabled="exportingFormat === 'json'"
        >
          <template v-slot:prepend>
            <v-icon color="orange">mdi-code-json</v-icon>
          </template>
          <v-list-item-title>JSON реестр</v-list-item-title>
          <v-list-item-subtitle>Структурированный реестр требований</v-list-item-subtitle>
          <template v-slot:append>
            <v-progress-circular v-if="exportingFormat === 'json'" indeterminate size="20" width="2" />
            <v-icon v-else>mdi-download</v-icon>
          </template>
        </v-list-item>

        <v-list-item
          class="download-item"
          @click="triggerExport('txt')"
          :disabled="exportingFormat === 'txt'"
        >
          <template v-slot:prepend>
            <v-icon color="green">mdi-chart-line</v-icon>
          </template>
          <v-list-item-title>Отчёт TXT</v-list-item-title>
          <v-list-item-subtitle>Полный реестр в текстовом формате</v-list-item-subtitle>
          <template v-slot:append>
            <v-progress-circular v-if="exportingFormat === 'txt'" indeterminate size="20" width="2" />
            <v-icon v-else>mdi-download</v-icon>
          </template>
        </v-list-item>
      </v-list>

      <v-alert
        type="info"
        variant="tonal"
        density="compact"
        class="mt-3"
      >
        <v-icon left size="small">mdi-information</v-icon>
        Файлы генерируются из базы данных в реальном времени
      </v-alert>
    </v-card-text>

    <v-divider></v-divider>

    <!-- Actions -->
    <v-card-actions>
      <v-btn
        color="primary"
        variant="flat"
        prepend-icon="mdi-eye"
        @click="$emit('view-requirements')"
      >
        Просмотреть требования
      </v-btn>
      <v-spacer></v-spacer>
      <v-btn
        variant="text"
        @click="$emit('close')"
      >
        Закрыть
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { downloadExport } from '@/services/api'

const props = defineProps({
  results: {
    type: Object,
    required: true
  }
})

defineEmits(['view-requirements', 'close'])

const formatNumber = (num) => num.toLocaleString()

const modelDisplayNames = {
  'claude-sonnet-4.5': 'Claude Sonnet 4.5',
  'claude-opus-4.6': 'Claude Opus 4.6',
  'gpt-4.1': 'GPT-4.1',
  'qwen-3.5-plus': 'Qwen 3.5 Plus',
  'gemini-3.1-pro': 'Gemini 3.1 Pro'
}

const displayModelName = computed(() => {
  if (!props.results?.model_used) return 'Unknown'
  return modelDisplayNames[props.results.model_used] || props.results.model_used
})

const exportingFormat = ref(null)

async function triggerExport(format) {
  if (!props.results?.document_id || exportingFormat.value) return
  exportingFormat.value = format
  try {
    await downloadExport(props.results.document_id, format)
  } catch (e) {
    console.error('Export failed', e)
  } finally {
    exportingFormat.value = null
  }
}
</script>

<style scoped>
.extraction-results {
  margin-top: 16px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  border-radius: 8px;
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: rgb(var(--v-theme-primary));
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.6);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.download-item {
  margin-bottom: 8px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 8px;
  transition: all 0.2s;
}

.download-item:hover {
  background-color: rgba(var(--v-theme-primary), 0.05);
  border-color: rgb(var(--v-theme-primary));
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>
