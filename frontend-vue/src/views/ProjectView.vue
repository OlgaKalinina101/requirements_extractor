<template>
  <div>
    <!-- Breadcrumbs -->
    <v-breadcrumbs :items="breadcrumbs" class="px-0 mb-2">
      <template v-slot:divider>
        <v-icon>mdi-chevron-right</v-icon>
      </template>
    </v-breadcrumbs>

    <v-row v-if="loading" class="py-8">
      <v-col cols="12" class="text-center">
        <v-progress-circular indeterminate color="primary" size="48" />
      </v-col>
    </v-row>

    <template v-else-if="project">
      <!-- Project header -->
      <v-row class="mb-4" align="center">
        <v-col>
          <h1 class="text-h4 d-flex align-center">
            <v-icon left color="primary" class="mr-3" size="36">mdi-folder</v-icon>
            {{ project.name }}
            <v-chip
              :color="project.status === 'active' ? 'green' : 'grey'"
              size="small"
              variant="tonal"
              class="ml-3"
            >
              {{ project.status === 'active' ? 'Активный' : project.status }}
            </v-chip>
          </h1>
          <div v-if="project.code" class="text-subtitle-1 text-medium-emphasis mt-1">
            Код: {{ project.code }}
          </div>
          <div v-if="project.description" class="text-body-2 text-medium-emphasis mt-1">
            {{ project.description }}
          </div>
        </v-col>
      </v-row>

      <v-row>
        <!-- Upload column - full width when showing results -->
        <v-col :cols="12" :md="showingResults ? 12 : 8">
          <DocumentUpload 
            :project-id="projectId" 
            @uploaded="onDocumentUploaded"
            @results-shown="onResultsShown"
            @results-hidden="onResultsHidden"
          />
        </v-col>

        <!-- Documents list column - hidden when showing results -->
        <v-col v-if="!showingResults" cols="12" md="4">
          <v-card>
            <v-card-title>
              <v-icon left>mdi-file-document-multiple</v-icon>
              Документы проекта
              <v-chip size="small" class="ml-2" variant="tonal">
                {{ project.documents?.length || 0 }}
              </v-chip>
            </v-card-title>

            <v-card-text>
              <v-list v-if="project.documents && project.documents.length > 0" density="compact">
                <v-list-item
                  v-for="doc in project.documents"
                  :key="doc.id"
                  :title="doc.filename"
                  :subtitle="formatDocSubtitle(doc)"
                  :prepend-icon="getStatusIcon(doc.status)"
                  @click="goToReview(doc.id)"
                >
                  <template v-slot:append>
                    <v-chip
                      :color="getStatusColor(doc.status)"
                      size="x-small"
                      variant="flat"
                    >
                      {{ getStatusText(doc.status) }}
                    </v-chip>
                  </template>
                </v-list-item>
              </v-list>

              <div v-else class="text-center text-medium-emphasis py-4">
                Загрузите документ ТЗ слева
              </div>
            </v-card-text>

            <v-card-actions>
              <v-btn variant="text" @click="refreshProject" :loading="loading">
                <v-icon left>mdi-refresh</v-icon>
                Обновить
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </template>

    <v-alert v-else type="error" variant="tonal">
      Проект не найден
    </v-alert>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '../stores/projects'
import DocumentUpload from '../components/DocumentUpload.vue'

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()

const props = defineProps({
  projectId: { type: [String, Number], required: true }
})

const loading = ref(false)
const project = ref(null)
const showingResults = ref(false)

const breadcrumbs = computed(() => [
  { title: 'Проекты', to: '/projects', disabled: false },
  { title: project.value?.name || '...', disabled: true },
])

const refreshProject = async () => {
  loading.value = true
  try {
    const data = await projectsStore.fetchProject(props.projectId)
    project.value = data
  } catch (e) {
    project.value = null
  } finally {
    loading.value = false
  }
}

const onDocumentUploaded = () => {
  // Don't refresh immediately - it will reset DocumentUpload component state
  // refreshProject() will be called when user closes ExtractionResults
}

const onResultsShown = () => {
  showingResults.value = true
}

const onResultsHidden = () => {
  showingResults.value = false
  // Refresh project list after closing results
  refreshProject()
}

const formatDocSubtitle = (doc) => {
  const parts = []
  if (doc.total_pages) parts.push(`${doc.total_pages} стр.`)
  if (doc.requirements_count) parts.push(`${doc.requirements_count} треб.`)
  if (doc.uploaded_at) {
    parts.push(new Date(doc.uploaded_at).toLocaleDateString('ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric'
    }))
  }
  return parts.join(' \u2022 ')
}

const getStatusIcon = (status) => {
  const icons = { pending: 'mdi-clock-outline', processing: 'mdi-loading', completed: 'mdi-check-circle', failed: 'mdi-alert-circle' }
  return icons[status] || 'mdi-file'
}

const getStatusColor = (status) => {
  const colors = { pending: 'grey', processing: 'blue', completed: 'green', failed: 'red' }
  return colors[status] || 'grey'
}

const getStatusText = (status) => {
  const texts = { pending: 'Ожидает', processing: 'Обработка', completed: 'Готово', failed: 'Ошибка' }
  return texts[status] || status
}

const goToReview = (documentId) => {
  router.push(`/review/${documentId}`)
}

watch(() => props.projectId, () => { refreshProject() })

onMounted(() => {
  refreshProject()
})
</script>
