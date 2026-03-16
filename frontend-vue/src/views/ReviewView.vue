<template>
  <div class="review-container">
    <!-- Header -->
    <v-card class="mb-2">
      <v-card-title class="d-flex align-center">
        <v-icon left>mdi-file-document-edit</v-icon>
        Review требований
        <v-spacer></v-spacer>
        <v-chip v-if="documentsStore.currentDocument" class="mr-4" size="small">
          {{ documentsStore.currentDocument.filename }}
        </v-chip>
        <v-menu v-if="documentsStore.currentDocument" location="bottom">
          <template v-slot:activator="{ props: menuProps }">
            <v-btn v-bind="menuProps" variant="text" prepend-icon="mdi-download">
              Экспорт
            </v-btn>
          </template>
          <v-list density="compact">
            <v-list-item :href="exportUrls.word(documentsStore.currentDocument.id)" target="_blank">
              <template v-slot:prepend><v-icon color="blue">mdi-file-word</v-icon></template>
              <v-list-item-title>Word</v-list-item-title>
            </v-list-item>
            <v-list-item :href="exportUrls.xlsx(documentsStore.currentDocument.id)" target="_blank">
              <template v-slot:prepend><v-icon color="success">mdi-file-excel</v-icon></template>
              <v-list-item-title>Excel (XLSX)</v-list-item-title>
            </v-list-item>
            <v-list-item :href="exportUrls.json(documentsStore.currentDocument.id)" target="_blank">
              <template v-slot:prepend><v-icon color="orange">mdi-code-json</v-icon></template>
              <v-list-item-title>JSON</v-list-item-title>
            </v-list-item>
            <v-list-item :href="exportUrls.txt(documentsStore.currentDocument.id)" target="_blank">
              <template v-slot:prepend><v-icon color="green">mdi-chart-line</v-icon></template>
              <v-list-item-title>TXT</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
        <v-btn
          icon
          variant="text"
          @click="$router.push('/')"
        >
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>
      </v-card-title>
    </v-card>

    <!-- Split View: PDF Viewer + Requirements -->
    <v-row class="fill-height ma-0">
      <!-- Left: PDF Viewer -->
      <v-col cols="12" md="6" class="pa-1" style="height: calc(100vh - 140px)">
        <PDFViewer
          v-if="documentsStore.currentDocument"
          :document-id="documentsStore.currentDocument.id"
          :filename="documentsStore.currentDocument.filename"
          :initial-page="currentPdfPage"
          :total-pages-count="documentsStore.currentDocument.total_pages || 0"
          @page-changed="onPdfPageChanged"
          @loaded="onPdfLoaded"
          ref="pdfViewer"
        />
      </v-col>

      <!-- Right: Requirements List + Sidebar -->
      <v-col cols="12" md="6" class="pa-1 d-flex flex-column" style="height: calc(100vh - 140px)">
        <v-row class="ma-0 flex-grow-1">
          <!-- Requirements List -->
          <v-col cols="12" lg="8" class="pa-1 d-flex flex-column">
            <v-card class="d-flex flex-column" style="height: 100%;">
              <v-card-title class="flex-shrink-0">
                <v-icon left>mdi-clipboard-list</v-icon>
                Требования
                <v-spacer></v-spacer>
                <v-chip size="small" color="primary">
                  {{ requirementsStore.filteredRequirements.length }} / {{ requirementsStore.requirements.length }}
                </v-chip>
              </v-card-title>
              
              <v-card-text class="pa-2 d-flex flex-column" style="flex: 1 1 auto; height: 0; min-height: 0;">
                <div ref="requirementsScrollContainer" class="requirements-scroll-container flex-grow-1" style="overflow-y: auto; min-height: 0;">
                <div v-if="requirementsStore.loading" class="text-center py-8">
                  <v-progress-circular indeterminate color="primary"></v-progress-circular>
                </div>
                
                <div v-else-if="requirementsStore.filteredRequirements.length === 0" class="text-center py-8">
                  <v-icon size="64" color="grey">mdi-file-document-remove</v-icon>
                  <div class="text-h6 mt-4">Нет требований</div>
                  <div class="text-body-2 text-medium-emphasis">
                    {{ requirementsStore.requirements.length > 0 ? 'Измените фильтры' : 'Требования появятся после обработки документа' }}
                  </div>
                </div>
                
                <RequirementsList
                  v-else
                  :requirements="requirementsStore.filteredRequirements"
                  @accept="handleAccept"
                  @reject="handleReject"
                  @edit="handleEdit"
                  @view-page="jumpToPdfPage"
                  @assigned="handleAssigned"
                  @status-changed="handleStatusChanged"
                />
                </div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Filters & Stats Sidebar -->
          <v-col cols="12" lg="4" class="pa-1 d-flex flex-column">
            <!-- Filters -->
            <v-card class="mb-2">
              <v-card-title class="text-body-1">
                <v-icon left size="small">mdi-filter</v-icon>
                Фильтры
              </v-card-title>
              <v-card-text class="py-2">
                <v-select
                  v-model="statusFilter"
                  :items="statusOptions"
                  label="Статус"
                  density="compact"
                  clearable
                  @update:model-value="updateFilters"
                ></v-select>

                <v-select
                  v-model="typeFilter"
                  :items="typeOptions"
                  label="Тип"
                  density="compact"
                  clearable
                  @update:model-value="updateFilters"
                  class="mt-2"
                ></v-select>

                <v-select
                  v-model="disciplineFilter"
                  :items="disciplineOptions"
                  label="Дисциплина"
                  density="compact"
                  clearable
                  @update:model-value="updateFilters"
                  class="mt-2"
                ></v-select>

                <v-switch
                  v-model="onlyMine"
                  label="Только мои требования"
                  density="compact"
                  color="primary"
                  hide-details
                  class="mt-2"
                  @update:model-value="toggleOnlyMine"
                ></v-switch>
              </v-card-text>
            </v-card>
            
            <!-- Statistics -->
            <v-card class="mb-2">
              <v-card-title class="text-body-1">
                <v-icon left size="small">mdi-chart-bar</v-icon>
                Статистика
              </v-card-title>
              <v-card-text class="py-2">
                <v-list density="compact">
                  <v-list-item class="px-0">
                    <v-list-item-title class="text-body-2">Всего</v-list-item-title>
                    <template v-slot:append>
                      <strong>{{ requirementsStore.stats.total }}</strong>
                    </template>
                  </v-list-item>
                  <v-divider class="my-1"></v-divider>
                  <v-list-item class="px-0">
                    <v-list-item-title class="text-body-2">Pending</v-list-item-title>
                    <template v-slot:append>
                      <v-chip size="x-small" color="grey">{{ requirementsStore.stats.pending }}</v-chip>
                    </template>
                  </v-list-item>
                  <v-list-item class="px-0">
                    <v-list-item-title class="text-body-2">Accepted</v-list-item-title>
                    <template v-slot:append>
                      <v-chip size="x-small" color="green">{{ requirementsStore.stats.accepted }}</v-chip>
                    </template>
                  </v-list-item>
                  <v-list-item class="px-0">
                    <v-list-item-title class="text-body-2">Modified</v-list-item-title>
                    <template v-slot:append>
                      <v-chip size="x-small" color="blue">{{ requirementsStore.stats.modified }}</v-chip>
                    </template>
                  </v-list-item>
                  <v-list-item class="px-0">
                    <v-list-item-title class="text-body-2">Rejected</v-list-item-title>
                    <template v-slot:append>
                      <v-chip size="x-small" color="red">{{ requirementsStore.stats.rejected }}</v-chip>
                    </template>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>

            <!-- Metrics Panel -->
            <MetricsPanel
              v-if="documentsStore.currentDocument"
              :document-id="documentsStore.currentDocument.id"
              class="flex-grow-1"
              @view-page="jumpToPdfPage"
            />
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, provide, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDocumentsStore } from '../stores/documents'
import { useRequirementsStore } from '../stores/requirements'
import RequirementsList from '../components/RequirementsList.vue'
import PDFViewer from '../components/PDFViewer.vue'
import MetricsPanel from '../components/MetricsPanel.vue'
import { useAuthStore } from '@/stores/auth'
import { useDictionariesStore } from '@/stores/dictionaries'
import { usersApi, exportUrls } from '@/services/api'

const route = useRoute()
const router = useRouter()
const documentsStore = useDocumentsStore()
const requirementsStore = useRequirementsStore()
const auth = useAuthStore()
const dicts = useDictionariesStore()

const pdfViewer = ref(null)
const requirementsScrollContainer = ref(null)
const currentPdfPage = ref(1)
const statusFilter = ref(null)
const typeFilter = ref(null)
const disciplineFilter = ref(null)
const onlyMine = ref(false)

// Users list for assignee dropdowns in RequirementCard
const users = ref([])
provide('users', users)
provide('documentId', computed(() => route.params.documentId))

// Filter options come from the dictionaries store (loaded from DB)
const statusOptions = computed(() => dicts.statusOptions)
const typeOptions   = computed(() => dicts.typeOptions)
const disciplineOptions = computed(() => {
  const disciplines = new Set()
  requirementsStore.requirements.forEach(r => {
    if (r.discipline) disciplines.add(r.discipline)
  })
  return [...disciplines].sort()
})

const updateFilters = () => {
  requirementsStore.setFilters({
    status: statusFilter.value,
    type: typeFilter.value,
    discipline: disciplineFilter.value,
  })
}

const toggleOnlyMine = () => {
  const documentId = route.params.documentId
  if (!documentId) return
  requirementsStore.fetchRequirements(
    documentId,
    onlyMine.value ? { assignee_id: 'me' } : {}
  )
}

// Handle assignee update in-place without full reload
const handleAssigned = ({ requirementId, assigneeId }) => {
  const req = requirementsStore.requirements.find(r => r.id === requirementId)
  if (req) req.assignee_id = assigneeId
}

// Handle execution status change in-place
const handleStatusChanged = ({ requirementId, status }) => {
  const req = requirementsStore.requirements.find(r => r.id === requirementId)
  if (req) req.status = status
}

const handleAccept = async (requirementId) => {
  try {
    await requirementsStore.acceptRequirement(requirementId)
  } catch { /* store handles error */ }
}

const handleReject = async (requirementId, reason) => {
  try {
    await requirementsStore.rejectRequirement(requirementId, reason)
  } catch { /* store handles error */ }
}

const handleEdit = async (requirementId, editedText, reason, type = null, priority = null, discipline = null, verification_method = null, deadline = null) => {
  try {
    await requirementsStore.editRequirement(requirementId, editedText, reason, null, type, priority, discipline, verification_method, deadline)
  } catch { /* store handles error */ }
}

const jumpToPdfPage = (pageNumber) => {
  if (pdfViewer.value && pageNumber) {
    currentPdfPage.value = pageNumber
    pdfViewer.value.jumpToPage(pageNumber)
  }
}

const onPdfPageChanged = (page) => { currentPdfPage.value = page }
const pendingPdfPageOnLoad = ref(null)
const onPdfLoaded = () => {
  if (pendingPdfPageOnLoad.value && pdfViewer.value) {
    pdfViewer.value.jumpToPage(pendingPdfPageOnLoad.value)
    pendingPdfPageOnLoad.value = null
  }
}

const loadData = async () => {
  const documentId = route.params.documentId
  if (documentId) {
    try {
      await documentsStore.fetchDocument(documentId)
      await requirementsStore.fetchRequirements(documentId)

      const scrollToId = route.query.scrollTo
      const scrollToPage = route.query.page ? parseInt(route.query.page, 10) : null
      if (scrollToId && scrollToPage) {
        currentPdfPage.value = scrollToPage
      } else {
        const firstRequirement = requirementsStore.filteredRequirements[0]
        if (firstRequirement?.page_number) currentPdfPage.value = firstRequirement.page_number
      }

      if (scrollToId) {
        if (scrollToPage) pendingPdfPageOnLoad.value = scrollToPage
        await nextTick()
        if (scrollToPage && pdfViewer.value) {
          pdfViewer.value.jumpToPage(scrollToPage)
          pendingPdfPageOnLoad.value = null
        }
        const container = requirementsScrollContainer.value ?? document.querySelector('.requirements-scroll-container')
        const el = document.getElementById(`req-${scrollToId}`)
        if (container && el) {
          const containerRect = container.getBoundingClientRect()
          const elRect = el.getBoundingClientRect()
          const scrollTop = container.scrollTop + (elRect.top - containerRect.top)
          container.scrollTo({ top: Math.max(0, scrollTop), behavior: 'smooth' })
        }
        router.replace({ path: route.path, query: {} })
      }
    } catch { /* stores handle error */ }
  }
}

onMounted(async () => {
  loadData()
  try {
    const { data } = await usersApi.getAll()
    users.value = data.map(u => ({ id: u.id, label: u.full_name || u.email }))
  } catch { /* non-critical */ }
})

watch(() => route.params.documentId, () => { loadData() })
</script>

<style scoped>
.review-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.requirements-scroll-container {
  overflow-y: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;
  /* Custom scrollbar */
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;
}

.requirements-scroll-container::-webkit-scrollbar {
  width: 8px;
}

.requirements-scroll-container::-webkit-scrollbar-track {
  background: transparent;
}

.requirements-scroll-container::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.requirements-scroll-container::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.3);
}
</style>
