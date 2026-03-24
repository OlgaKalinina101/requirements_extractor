<template>
  <div class="pdf-viewer">
    <v-card class="fill-height d-flex flex-column">
      <v-card-title class="d-flex align-center flex-shrink-0">
        <v-icon left>mdi-file-pdf-box</v-icon>
        PDF Документ
        <v-spacer></v-spacer>
        <v-chip v-if="isOcrPage" size="small" color="deep-purple" class="mr-2" prepend-icon="mdi-ocr">
          OCR
        </v-chip>
        <v-chip v-if="totalPages" size="small" color="primary">
          {{ currentPage }} / {{ totalPages }} стр.
        </v-chip>
      </v-card-title>

      <div class="pdf-container flex-grow-1">
        <div v-if="loading" class="loading-overlay">
          <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
          <div class="mt-4 text-h6">Загрузка PDF...</div>
        </div>

        <div v-if="error" class="error-overlay">
          <v-icon size="64" color="error">mdi-alert-circle</v-icon>
          <div class="mt-4 text-h6">Ошибка загрузки PDF</div>
          <div class="text-body-2">{{ error }}</div>
          <v-btn class="mt-4" color="primary" :href="blobUrl || pdfUrl" target="_blank">
            Открыть в новой вкладке
          </v-btn>
        </div>

        <div v-if="!isImageDocument" ref="canvasContainer" class="canvas-container">
          <div class="canvas-wrapper" ref="canvasWrapper">
            <canvas ref="pdfCanvas" class="pdf-canvas"></canvas>
            <canvas ref="overlayCanvas" class="overlay-canvas"></canvas>
          </div>
        </div>

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

        <v-btn icon size="small" variant="text" @click="zoomOut" :disabled="scale <= 0.5">
          <v-icon>mdi-minus</v-icon>
        </v-btn>
        <v-chip size="small">{{ Math.round(scale * 100) }}%</v-chip>
        <v-btn icon size="small" variant="text" @click="zoomIn" :disabled="scale >= 3">
          <v-icon>mdi-plus</v-icon>
        </v-btn>

        <v-divider vertical class="mx-2"></v-divider>

        <v-btn v-if="totalPages" icon size="small" variant="text" :disabled="currentPage <= 1" @click="changePage(-1)">
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
          @keyup.enter="jumpToPage(pageInput)"
        ></v-text-field>
        <v-btn v-if="totalPages" icon size="small" variant="text" :disabled="currentPage >= totalPages" @click="changePage(1)">
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
import { usePageHighlight, findMatchingBlocks } from '@/composables/usePageHighlight'

pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`

const props = defineProps({
  documentId:      { type: [String, Number], required: true },
  initialPage:     { type: Number, default: 1 },
  totalPagesCount: { type: Number, default: 0 },
  activeRequirement: { type: Object, default: null },
})

const emit = defineEmits(['page-changed', 'loaded'])

// ─── Refs ──────────────────────────────────────────────────────────────────

const pdfCanvas    = ref(null)
const overlayCanvas = ref(null)
const canvasWrapper = ref(null)
const canvasContainer = ref(null)
const currentPage  = ref(1)
const pageInput    = ref(1)
const totalPages   = ref(props.totalPagesCount || 0)
const loading      = ref(true)
const error        = ref(null)
const scale        = ref(1.0)
const isImageDocument = ref(false)
const isOcrPage    = ref(false)
const blobUrl      = ref(null)

let pdfDocument    = null
let currentPageObj = null
let highlightVersion = 0

const documentIdRef = computed(() => props.documentId)
const { loadPageBlocks, syncOverlaySize, clearOverlay, drawOverlay } =
  usePageHighlight(documentIdRef, pdfCanvas, overlayCanvas, () => currentPageObj)

const pdfUrl = computed(() => props.documentId ? exportUrls.pdf(props.documentId) : '')

// ─── Highlight ────────────────────────────────────────────────────────────

async function refreshHighlight() {
  const version = ++highlightVersion

  if (!currentPageObj) {
    clearOverlay()
    return
  }

  const pageData = await loadPageBlocks(currentPage.value)
  if (version !== highlightVersion) return

  const blocks = pageData?.text_blocks || []
  isOcrPage.value = pageData?.is_ocr || false

  if (!props.activeRequirement || props.activeRequirement.page_number !== currentPage.value) {
    clearOverlay()
    return
  }

  const matching = findMatchingBlocks(blocks, props.activeRequirement)
  if (version !== highlightVersion) return

  drawOverlay(matching)
}

// ─── PDF loading & rendering ──────────────────────────────────────────────

async function fetchPdfWithAuth() {
  const response = await api.get(pdfUrl.value, { responseType: 'arraybuffer' })
  return {
    arrayBuffer: response.data,
    contentType: response.headers['content-type'] || 'application/pdf',
  }
}

async function loadPDF() {
  try {
    loading.value = true
    error.value = null

    const { arrayBuffer, contentType } = await fetchPdfWithAuth()
    const blob = new Blob([arrayBuffer], { type: contentType })
    blobUrl.value = URL.createObjectURL(blob)

    if (contentType.startsWith('image/')) {
      isImageDocument.value = true
      totalPages.value = 1
      loading.value = false
      emit('loaded')
      return
    }

    const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer })
    pdfDocument = await loadingTask.promise
    totalPages.value = pdfDocument.numPages

    let startPage = props.initialPage
    if (startPage < 1 || startPage > pdfDocument.numPages) startPage = 1
    currentPage.value = startPage
    pageInput.value   = startPage

    await renderPage(currentPage.value)
    loading.value = false
    emit('loaded')
  } catch (err) {
    error.value   = `Не удалось загрузить PDF: ${err?.message || err}`
    loading.value = false
  }
}

async function renderPage(pageNum) {
  if (!pdfDocument || !pdfCanvas.value) return
  if (pageNum < 1 || pageNum > pdfDocument.numPages) return

  try {
    currentPageObj = await pdfDocument.getPage(pageNum)
    const viewport = currentPageObj.getViewport({ scale: scale.value })
    const canvas   = pdfCanvas.value
    const ctx      = canvas.getContext('2d')
    canvas.height  = viewport.height
    canvas.width   = viewport.width
    await currentPageObj.render({ canvasContext: ctx, viewport }).promise
    syncOverlaySize()
    await refreshHighlight()
  } catch (err) {
    error.value = `Ошибка рендеринга страницы ${pageNum}: ${err?.message || err}`
  }
}

// ─── Navigation & zoom ────────────────────────────────────────────────────

async function changePage(delta) {
  const newPage = currentPage.value + delta
  if (newPage >= 1 && newPage <= totalPages.value) {
    currentPage.value = newPage
    pageInput.value   = newPage
    await renderPage(newPage)
  }
}

async function jumpToPage(page) {
  const p = parseInt(page)
  if (!isNaN(p) && p >= 1 && p <= totalPages.value) {
    currentPage.value = p
    pageInput.value   = p
    await renderPage(p)
  } else {
    pageInput.value = currentPage.value
  }
}

async function zoomIn() {
  if (scale.value < 3) {
    scale.value = Math.min(scale.value + 0.25, 3)
    await renderPage(currentPage.value)
  }
}

async function zoomOut() {
  if (scale.value > 0.5) {
    scale.value = Math.max(scale.value - 0.25, 0.5)
    await renderPage(currentPage.value)
  }
}

defineExpose({ jumpToPage })

// ─── Watchers ─────────────────────────────────────────────────────────────

watch(currentPage, (p) => emit('page-changed', p))

watch(() => props.initialPage, async (newPage) => {
  if (pdfDocument && newPage !== currentPage.value && newPage >= 1 && newPage <= pdfDocument.numPages) {
    currentPage.value = newPage
    pageInput.value   = newPage
    await renderPage(newPage)
  }
})

watch(() => props.activeRequirement, () => refreshHighlight())

onMounted(() => loadPDF())

onBeforeUnmount(() => {
  if (pdfDocument) pdfDocument.destroy()
  if (blobUrl.value) URL.revokeObjectURL(blobUrl.value)
})
</script>

<style scoped>
.pdf-viewer { height: 100%; }

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

.canvas-wrapper {
  position: relative;
  display: inline-block;
  line-height: 0;
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
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

.pdf-canvas {
  max-width: 100%;
  height: auto;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  display: block;
}

.overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
  max-width: 100%;
  height: auto;
  pointer-events: none;
}

.loading-overlay,
.error-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: rgba(82, 86, 89, 0.9);
  color: white;
  z-index: 10;
}
</style>
