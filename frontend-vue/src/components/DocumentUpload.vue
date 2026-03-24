<template>
  <div>
    <v-card v-if="!uploading && !showResults">
      <v-card-title>
        <v-icon left>mdi-file-upload</v-icon>
        Загрузить документ ТЗ
      </v-card-title>
      
      <v-card-text>
        <!-- Project selector — shown only when projectId is not passed as a prop -->
        <v-autocomplete
          v-if="!props.projectId"
          v-model="selectedProjectId"
          :items="projectOptions"
          item-title="label"
          item-value="id"
          label="Проект *"
          prepend-icon="mdi-folder-open"
          :loading="projectsStore.loading"
          :disabled="uploading"
          placeholder="Выберите проект"
          no-data-text="Нет доступных проектов"
          clearable
          class="mb-2"
        >
          <template #item="{ item, props: itemProps }">
            <v-list-item v-bind="itemProps">
              <template #prepend>
                <v-icon color="primary" size="small">mdi-folder</v-icon>
              </template>
            </v-list-item>
          </template>
        </v-autocomplete>

        <!-- Project badge when pre-selected via prop -->
        <v-chip
          v-else
          color="primary"
          variant="tonal"
          prepend-icon="mdi-folder"
          class="mb-4"
        >
          {{ projectLabel }}
        </v-chip>

        <v-file-input
          v-model="file"
          label="Выберите PDF файл"
          accept=".pdf"
          prepend-icon="mdi-file-pdf-box"
          show-size
          :disabled="uploading"
        ></v-file-input>

        <v-select
          v-model="selectedModel"
          :items="availableModels"
          label="AI модель"
          item-title="name"
          item-value="id"
          :disabled="uploading"
          class="mt-2"
        ></v-select>

        <v-checkbox
          v-model="generateWord"
          label="Генерировать Word документ"
          :disabled="uploading"
          class="mt-2"
        ></v-checkbox>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-tooltip
          v-if="!effectiveProjectId"
          text="Выберите проект перед загрузкой"
          location="top"
        >
          <template #activator="{ props: tooltipProps }">
            <span v-bind="tooltipProps">
              <v-btn color="primary" disabled>
                <v-icon left>mdi-upload</v-icon>
                Загрузить и обработать
              </v-btn>
            </span>
          </template>
        </v-tooltip>
        <v-btn
          v-else
          color="primary"
          :disabled="!file || uploading"
          :loading="uploading"
          @click="handleUpload"
        >
          <v-icon left>mdi-upload</v-icon>
          Загрузить и обработать
        </v-btn>
      </v-card-actions>
    </v-card>

    <ProcessingStatus
      v-if="uploading"
      :processing="uploading"
      :progress="progress"
      :current-step="currentStep"
      :message="statusMessage"
    />

    <ExtractionResults
      v-if="showResults"
      :results="extractionResults"
      @view-requirements="goToReview"
      @close="resetUpload"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDocumentsStore } from '@/stores/documents'
import { useProjectsStore } from '@/stores/projects'
import { useModelsStore } from '@/stores/models'
import { useNotificationsStore } from '@/stores/notifications'
import { useRouter } from 'vue-router'
import ProcessingStatus from './ProcessingStatus.vue'
import ExtractionResults from './ExtractionResults.vue'

const props = defineProps({
  projectId: { type: [String, Number], default: null }
})

const emit = defineEmits(['uploaded', 'results-shown', 'results-hidden'])

const documentsStore = useDocumentsStore()
const projectsStore  = useProjectsStore()
const modelsStore    = useModelsStore()
const notifications  = useNotificationsStore()
const router = useRouter()

// Local project selection (used when no projectId prop is given)
const selectedProjectId = ref(null)

// The project ID actually used for upload: prop takes priority, otherwise local selection
const effectiveProjectId = computed(() =>
  props.projectId != null ? props.projectId : selectedProjectId.value
)

// Flat list for v-autocomplete
const projectOptions = computed(() =>
  projectsStore.projects.map(p => ({
    id: p.id,
    label: p.code ? `[${p.code}] ${p.name}` : p.name,
  }))
)

// Display label for pre-selected project (via prop)
const projectLabel = computed(() => {
  if (!props.projectId) return ''
  const p = projectsStore.projects.find(p => p.id === Number(props.projectId))
  if (!p) return `Проект #${props.projectId}`
  return p.code ? `[${p.code}] ${p.name}` : p.name
})

const file = ref(null)
const uploading = ref(false)
const generateWord = ref(true)
const selectedModel = ref('claude-sonnet-4.5')
const progress = ref(0)
const currentStep = ref('')
const statusMessage = ref('')
const showResults = ref(false)
const extractionResults = ref(null)
let ws = null

const availableModels = computed(() => modelsStore.availableModels)

const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/ws/logs`
  
  try {
    ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {}
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'progress') {
          progress.value = data.progress || 0
          currentStep.value = data.step || ''
          statusMessage.value = data.message || ''
        }
      } catch {
        // Malformed message; skip
      }
    }
    
    ws.onerror = () => {}
    
    ws.onclose = () => {}
  } catch {
    // WebSocket is best-effort; upload proceeds regardless
  }
}

const handleUpload = async () => {
  if (!file.value || !effectiveProjectId.value) return

  uploading.value = true
  showResults.value = false
  extractionResults.value = null
  progress.value = 0
  currentStep.value = 'Инициализация...'
  statusMessage.value = 'Подготовка к загрузке'
  
  // Connect WebSocket for real-time updates
  connectWebSocket()
  
  try {
    const result = await documentsStore.uploadDocument(file.value, selectedModel.value, generateWord.value, effectiveProjectId.value)
    
    progress.value = 100
    statusMessage.value = 'Обработка завершена!'
    
    // Close WebSocket
    if (ws) {
      ws.close()
      ws = null
    }
    
    extractionResults.value = result
    emit('uploaded', result)
    
    // Set states immediately without setTimeout
    uploading.value = false
    showResults.value = true
    emit('results-shown')
    
  } catch (error) {
    
    // Close WebSocket on error
    if (ws) {
      ws.close()
      ws = null
    }
    
    statusMessage.value = `Ошибка: ${error.response?.data?.detail || error.message}`
    notifications.notifyError(`Ошибка загрузки: ${error.response?.data?.detail || error.message}`)
    uploading.value = false
  }
}

const goToReview = () => {
  if (extractionResults.value?.document_id) {
    router.push(`/review/${extractionResults.value.document_id}`)
  }
}

const resetUpload = () => {
  showResults.value = false
  extractionResults.value = null
  file.value = null
  emit('results-hidden')
}

onMounted(() => {
  if (projectsStore.projects.length === 0) {
    projectsStore.fetchProjects()
  }
})
</script>
