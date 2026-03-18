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
                <v-btn
                  v-if="auth.isManager"
                  size="small"
                  variant="tonal"
                  color="primary"
                  prepend-icon="mdi-plus"
                  @click="showAddRequirementDialog = true"
                >
                  Добавить
                </v-btn>
                <v-chip size="small" color="primary" class="ml-2">
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
                  :show-detail-link="false"
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

    <!-- Add requirement dialog -->
    <v-dialog v-model="showAddRequirementDialog" max-width="600" persistent>
      <v-card>
        <v-card-title>Новое требование</v-card-title>
        <v-card-text>
          <v-textarea
            v-model="newRequirement.text"
            label="Текст требования *"
            rows="4"
            :rules="[v => !!v?.trim() || 'Обязательное поле']"
          />
          <v-text-field
            v-model="newRequirement.requirement_id"
            label="Идентификатор (REQ-...)"
            hint="Оставьте пустым для авто-генерации"
            persistent-hint
            class="mt-2"
          />
          <v-row class="mt-2">
            <v-col cols="6">
              <v-select
                v-model="newRequirement.type"
                :items="typeOptions"
                item-title="title"
                item-value="value"
                label="Тип"
                clearable
                density="compact"
              />
            </v-col>
            <v-col cols="6">
              <v-select
                v-model="newRequirement.priority"
                :items="priorityOptions"
                item-title="title"
                item-value="value"
                label="Приоритет"
                clearable
                density="compact"
              />
            </v-col>
          </v-row>
          <v-select
            v-model="newRequirement.discipline"
            :items="dicts.disciplineOptions || []"
            item-title="title"
            item-value="value"
            label="Дисциплина"
            clearable
            density="compact"
            class="mt-2"
          />
          <v-text-field
            v-model.number="newRequirement.page_number"
            label="Номер страницы"
            type="number"
            min="1"
            density="compact"
            class="mt-2"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddRequirementDialog = false">Отмена</v-btn>
          <v-btn
            color="primary"
            :disabled="!newRequirement.text?.trim()"
            :loading="creatingRequirement"
            @click="createRequirement"
          >
            Создать
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
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
const showAddRequirementDialog = ref(false)
const creatingRequirement = ref(false)
const newRequirement = ref({
  text: '',
  requirement_id: '',
  type: null,
  priority: null,
  discipline: '',
  page_number: null,
})

// Users list for assignee dropdowns in RequirementCard
const users = ref([])
provide('users', users)
provide('documentId', computed(() => route.params.documentId))

// Filter options come from the dictionaries store (loaded from DB)
const statusOptions = computed(() => dicts.statusOptions)
const typeOptions = computed(() => dicts.typeOptions)
const priorityOptions = computed(() => dicts.priorityOptions)
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

const createRequirement = async () => {
  const documentId = route.params.documentId
  if (!documentId || !newRequirement.value.text?.trim()) return
  creatingRequirement.value = true
  try {
    const data = {
      text: newRequirement.value.text.trim(),
      requirement_id: newRequirement.value.requirement_id?.trim() || undefined,
      type: newRequirement.value.type || undefined,
      priority: newRequirement.value.priority || undefined,
      discipline: newRequirement.value.discipline?.trim() || undefined,
      page_number: newRequirement.value.page_number || undefined,
    }
    await requirementsStore.createRequirement(documentId, data)
    showAddRequirementDialog.value = false
    newRequirement.value = { text: '', requirement_id: '', type: null, priority: null, discipline: '', page_number: null }
  } catch (e) {
    // Store handles error; could show notification
  } finally {
    creatingRequirement.value = false
  }
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
