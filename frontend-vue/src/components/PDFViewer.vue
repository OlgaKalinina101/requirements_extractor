<template>
  <div class="pdf-viewer">
    <v-card class="fill-height d-flex flex-column">
      <v-card-title class="d-flex align-center flex-shrink-0">
        <v-icon left>mdi-file-pdf-box</v-icon>
        PDF Документ
        <v-spacer></v-spacer>
        <v-chip v-if="totalPages" size="small" color="primary">
          {{ currentPage }} / {{ totalPages }} стр.
        </v-chip>
      </v-card-title>

      <div class="pdf-container flex-grow-1">
        <!-- Loading indicator -->
        <div v-if="loading" class="loading-overlay">
          <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
          <div class="mt-4 text-h6">Загрузка PDF...</div>
        </div>

        <!-- Error indicator -->
        <div v-if="error" class="error-overlay">
          <v-icon size="64" color="error">mdi-alert-circle</v-icon>
          <div class="mt-4 text-h6">Ошибка загрузки PDF</div>
          <div class="text-body-2">{{ error }}</div>
          <v-btn class="mt-4" color="primary" :href="blobUrl || pdfUrl" target="_blank">
            Открыть в новой вкладке
          </v-btn>
        </div>

        <!-- PDF Canvas Container -->
        <div v-if="!isImageDocument" ref="canvasContainer" class="canvas-container">
          <canvas ref="pdfCanvas" class="pdf-canvas"></canvas>
        </div>

        <!-- Image Container -->
        <div v-else class="image-container">
          <img :src="blobUrl" class="document-image" alt="Document" />
        </div>
      </div>

      <v-card-actions class="flex-shrink-0 px-2">
        <v-btn
          size="small"
          variant="tonal"
          color="primary"
          :href="blobUrl || pdfUrl"
          target="_blank"
          prepend-icon="mdi-open-in-new"
        >
          Открыть в новой вкладке
        </v-btn>
        <v-spacer></v-spacer>
        
        <!-- Zoom controls -->
        <v-btn
          icon
          size="small"
          variant="text"
          @click="zoomOut"
          :disabled="scale <= 0.5"
        >
          <v-icon>mdi-minus</v-icon>
        </v-btn>
        <v-chip size="small">{{ Math.round(scale * 100) }}%</v-chip>
        <v-btn
          icon
          size="small"
          variant="text"
          @click="zoomIn"
          :disabled="scale >= 3"
        >
          <v-icon>mdi-plus</v-icon>
        </v-btn>
        
        <v-divider vertical class="mx-2"></v-divider>
        
        <!-- Page navigation -->
        <v-btn
          v-if="totalPages"
          icon
          size="small"
          variant="text"
          :disabled="currentPage <= 1"
          @click="changePage(-1)"
        >
          <v-icon>mdi-chevron-left</v-icon>
        </v-btn>
        <v-text-field
          v-if="totalPages"
          v-model.number="pageInput"
          type="number"
          :min="1"
          :max="totalPages"
          density="compact"
          hide-details
          variant="outlined"
          style="max-width: 70px"
          @keyup.enter="goToPage"
        ></v-text-field>
        <v-btn
          v-if="totalPages"
          icon
          size="small"
          variant="text"
          :disabled="currentPage >= totalPages"
          @click="changePage(1)"
        >
          <v-icon>mdi-chevron-right</v-icon>
        </v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import api, { exportUrls } from '@/services/api'

// Worker from CDN (bundled worker fails in Docker/nginx due to .mjs MIME type)
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`

const props = defineProps({
  documentId: {
    type: [String, Number],
    required: true
  },
  filename: {
    type: String,
    default: ''
  },
  initialPage: {
    type: Number,
    default: 1
  },
  totalPagesCount: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['page-changed', 'loaded'])

// Refs
const pdfCanvas = ref(null)
const canvasContainer = ref(null)
const currentPage = ref(props.initialPage)
const pageInput = ref(props.initialPage)
const totalPages = ref(props.totalPagesCount || 0)
const loading = ref(true)
const error = ref(null)
const scale = ref(1.0)
const isImageDocument = ref(false)

// Blob URL created from authenticated fetch — used for pdf.js, img src, and "open in new tab"
const blobUrl = ref(null)

// PDF.js objects
let pdfDocument = null
let currentPageObj = null

const pdfUrl = computed(() => {
  if (!props.documentId) return ''
  return exportUrls.pdf(props.documentId)
})

// Fetch PDF bytes via axios (carries Authorization header), return { arrayBuffer, contentType }
const fetchPdfWithAuth = async () => {
  const response = await api.get(pdfUrl.value, { responseType: 'arraybuffer' })
  const contentType = response.headers['content-type'] || 'application/pdf'
  return { arrayBuffer: response.data, contentType }
}

// Load PDF document or image
const loadPDF = async () => {
  try {
    loading.value = true
    error.value = null

    const { arrayBuffer, contentType } = await fetchPdfWithAuth()

    // Create a blob URL so "open in new tab" and <img> also work without re-fetching
    const blob = new Blob([arrayBuffer], { type: contentType })
    blobUrl.value = URL.createObjectURL(blob)

    if (contentType.startsWith('image/')) {
      isImageDocument.value = true
      totalPages.value = 1
      loading.value = false
      emit('loaded')
      return
    }

    // Pass raw ArrayBuffer to pdf.js — no second HTTP request needed
    const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer })
    pdfDocument = await loadingTask.promise

    totalPages.value = pdfDocument.numPages

    await renderPage(currentPage.value)

    loading.value = false
    emit('loaded')
  } catch (err) {
    error.value = `Не удалось загрузить PDF: ${err?.message || err}`
    loading.value = false
  }
}

// Render specific page
const renderPage = async (pageNum) => {
  if (!pdfDocument || !pdfCanvas.value) return
  
  try {
    currentPageObj = await pdfDocument.getPage(pageNum)
    
    const viewport = currentPageObj.getViewport({ scale: scale.value })
    
    const canvas = pdfCanvas.value
    const context = canvas.getContext('2d')
    canvas.height = viewport.height
    canvas.width = viewport.width
    
    await currentPageObj.render({ canvasContext: context, viewport }).promise
  } catch (err) {
    error.value = `Ошибка рендеринга страницы ${pageNum}: ${err?.message || err}`
  }
}

// Navigation
const changePage = async (delta) => {
  const newPage = currentPage.value + delta
  if (newPage >= 1 && newPage <= totalPages.value) {
    currentPage.value = newPage
    pageInput.value = newPage
    await renderPage(currentPage.value)
  }
}

const goToPage = async () => {
  const page = parseInt(pageInput.value)
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    await renderPage(currentPage.value)
  } else {
    pageInput.value = currentPage.value
  }
}

const jumpToPage = async (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    pageInput.value = page
    await renderPage(page)
  }
}

// Zoom
const zoomIn = async () => {
  if (scale.value < 3) {
    scale.value = Math.min(scale.value + 0.25, 3)
    await renderPage(currentPage.value)
  }
}

const zoomOut = async () => {
  if (scale.value > 0.5) {
    scale.value = Math.max(scale.value - 0.25, 0.5)
    await renderPage(currentPage.value)
  }
}

defineExpose({ jumpToPage })

watch(currentPage, (newPage) => {
  emit('page-changed', newPage)
})

watch(() => props.initialPage, async (newPage) => {
  if (newPage !== currentPage.value) {
    currentPage.value = newPage
    pageInput.value = newPage
    await renderPage(newPage)
  }
})

onMounted(() => {
  loadPDF()
})

onBeforeUnmount(() => {
  if (pdfDocument) {
    pdfDocument.destroy()
  }
  if (blobUrl.value) {
    URL.revokeObjectURL(blobUrl.value)
  }
})
</script>

<style scoped>
.pdf-viewer {
  height: 100%;
}

.pdf-container {
  position: relative;
  overflow: auto;
  background-color: #525659;
  min-height: 300px;
}

.canvas-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.image-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow: auto;
}

.document-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.pdf-canvas {
  max-width: 100%;
  height: auto;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.loading-overlay,
.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: rgba(82, 86, 89, 0.9);
  color: white;
  z-index: 10;
}
</style>
