<template>
  <div>
    <v-row>
      <v-col cols="12" md="8">
        <DocumentUpload />
      </v-col>
      
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-file-document</v-icon>
            Последние документы
          </v-card-title>
          
          <v-card-text>
            <v-list v-if="documentsStore.documents.length > 0" density="compact">
              <v-list-item
                v-for="doc in documentsStore.documents.slice(0, 5)"
                :key="doc.id"
                :title="doc.filename"
                :subtitle="`${doc.total_pages || 0} страниц • ${formatDate(doc.uploaded_at)}`"
                :prepend-icon="getStatusIcon(doc.status)"
                @click="goToReview(doc.id)"
              >
                <template v-slot:append>
                  <v-chip
                    :color="getStatusColor(doc.status)"
                    size="small"
                    variant="flat"
                  >
                    {{ getStatusText(doc.status) }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
            
            <div v-else class="text-center text-medium-emphasis py-4">
              Нет загруженных документов
            </div>
          </v-card-text>
          
          <v-card-actions>
            <v-btn
              variant="text"
              @click="documentsStore.fetchDocuments()"
              :loading="documentsStore.loading"
            >
              Обновить
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDocumentsStore } from '../stores/documents'
import DocumentUpload from '../components/DocumentUpload.vue'

const router = useRouter()
const documentsStore = useDocumentsStore()

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getStatusIcon = (status) => {
  const icons = {
    pending: 'mdi-clock-outline',
    processing: 'mdi-loading',
    completed: 'mdi-check-circle',
    failed: 'mdi-alert-circle'
  }
  return icons[status] || 'mdi-file'
}

const getStatusColor = (status) => {
  const colors = {
    pending: 'grey',
    processing: 'blue',
    completed: 'green',
    failed: 'red'
  }
  return colors[status] || 'grey'
}

const getStatusText = (status) => {
  const texts = {
    pending: 'Ожидает',
    processing: 'Обработка',
    completed: 'Готово',
    failed: 'Ошибка'
  }
  return texts[status] || status
}

const goToReview = (documentId) => {
  router.push(`/review/${documentId}`)
}

onMounted(() => {
  documentsStore.fetchDocuments()
})
</script>
