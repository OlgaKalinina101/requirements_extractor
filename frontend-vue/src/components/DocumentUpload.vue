<template>
  <div>
    <v-card v-if="!uploading && !showResults">
      <v-card-title>
        <v-icon left>mdi-file-upload</v-icon>
        Загрузить документ ТЗ
      </v-card-title>
      
      <v-card-text>
        <v-file-input
          v-model="file"
          label="Выберите PDF файл"
          accept=".pdf"
          prepend-icon="mdi-file-pdf-box"
          show-size
          :disabled="uploading"
          @change="onFileSelected"
        ></v-file-input>

        <v-select
          v-model="selectedModel"
          :items="availableModels"
          label="AI модель"
          item-title="name"
          item-value="id"
          :disabled="uploading"
          class="mt-4"
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
        <v-btn
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
import { ref } from 'vue'
import { useDocumentsStore } from '../stores/documents'
import { useRouter } from 'vue-router'
import ProcessingStatus from './ProcessingStatus.vue'
import ExtractionResults from './ExtractionResults.vue'

const props = defineProps({
  projectId: { type: [String, Number], default: null }
})

const emit = defineEmits(['uploaded', 'results-shown', 'results-hidden'])

const documentsStore = useDocumentsStore()
const router = useRouter()

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

const availableModels = [
  { id: 'claude-sonnet-4.5', name: 'Claude Sonnet 4.5' },
  { id: 'claude-opus-4.6', name: 'Claude Opus 4.6' },
  { id: 'gpt-4.1', name: 'GPT-4.1' },
  { id: 'qwen-3.5-plus', name: 'Qwen3.5 Plus 2026-02-15' },
  { id: 'gemini-3.1-pro', name: 'Gemini 3.1 Pro Preview' }
]

const onFileSelected = (event) => {
  if (event.target.files && event.target.files.length > 0) {
    file.value = event.target.files[0]
  }
}

const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/ws/logs`
  
  try {
    ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log('WebSocket connected')
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'progress') {
          progress.value = data.progress || 0
          currentStep.value = data.step || ''
          statusMessage.value = data.message || ''
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    ws.onclose = () => {
      console.log('WebSocket closed')
    }
  } catch (error) {
    console.error('Failed to connect WebSocket:', error)
  }
}

const handleUpload = async () => {
  if (!file.value) return

  uploading.value = true
  showResults.value = false
  extractionResults.value = null
  progress.value = 0
  currentStep.value = 'Инициализация...'
  statusMessage.value = 'Подготовка к загрузке'
  
  // Connect WebSocket for real-time updates
  connectWebSocket()
  
  try {
    const result = await documentsStore.uploadDocument(file.value, selectedModel.value, generateWord.value, props.projectId)
    
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
    console.error('Upload failed:', error)
    
    // Close WebSocket on error
    if (ws) {
      ws.close()
      ws = null
    }
    
    statusMessage.value = `Ошибка: ${error.response?.data?.detail || error.message}`
    alert(`Ошибка загрузки: ${error.response?.data?.detail || error.message}`)
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
</script>
