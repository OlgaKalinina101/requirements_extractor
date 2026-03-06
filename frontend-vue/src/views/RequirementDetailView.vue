<template>
  <div>
    <v-breadcrumbs :items="breadcrumbs" class="px-0 mb-2">
      <template v-slot:divider>
        <v-icon>mdi-chevron-right</v-icon>
      </template>
    </v-breadcrumbs>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <v-card v-if="requirement">
      <!-- Header -->
      <v-card-title class="d-flex align-center bg-blue-lighten-5">
        <v-chip color="primary" class="mr-3">{{ requirement.requirement_id }}</v-chip>
        <span class="text-h6">{{ requirement.text }}</span>
        <v-spacer></v-spacer>
        <v-chip :color="getStatusColor(requirement.status)" variant="flat">
          {{ requirement.status }}
        </v-chip>
      </v-card-title>

      <v-divider></v-divider>

      <!-- Main Info -->
      <v-card-text>
        <v-row>
          <v-col cols="12" md="8">
            <!-- Full Text -->
            <div class="mb-4">
              <div class="text-subtitle-2 text-medium-emphasis mb-2">Полный текст требования</div>
              <div class="text-body-1">{{ requirement.text }}</div>
            </div>

            <!-- Attributes -->
            <v-row class="mb-4">
              <v-col cols="6" md="3">
                <div class="text-caption text-medium-emphasis">Тип требования</div>
                <v-chip color="blue" size="small" class="mt-1">
                  {{ requirement.type || '—' }}
                </v-chip>
              </v-col>

              <v-col cols="6" md="3">
                <div class="text-caption text-medium-emphasis">Приоритет</div>
                <v-chip :color="getPriorityColor(requirement.priority)" size="small" class="mt-1">
                  {{ requirement.priority || '—' }}
                </v-chip>
              </v-col>

              <v-col cols="6" md="3">
                <div class="text-caption text-medium-emphasis">Статус</div>
                <v-chip :color="getStatusColor(requirement.status)" size="small" class="mt-1">
                  {{ requirement.status }}
                </v-chip>
              </v-col>

              <v-col cols="6" md="3">
                <div class="text-caption text-medium-emphasis">Страница</div>
                <div class="mt-1">{{ requirement.page_number || '—' }}</div>
              </v-col>
            </v-row>

            <!-- Source Info -->
            <v-alert type="info" variant="tonal" density="compact" class="mb-4">
              <div class="d-flex align-center">
                <v-icon left>mdi-file-document</v-icon>
                <div>
                  <strong>Документ ID:</strong> {{ requirement.document_id }}
                  <span v-if="requirement.page_number" class="ml-2 text-medium-emphasis">
                    Страница {{ requirement.page_number }}
                  </span>
                </div>
                <v-spacer></v-spacer>
                <v-btn
                  v-if="requirement.document_id"
                  size="small"
                  variant="outlined"
                  prepend-icon="mdi-open-in-new"
                  :to="`/review/${requirement.document_id}`"
                >
                  Открыть документ
                </v-btn>
              </div>
            </v-alert>

            <!-- Hierarchy -->
            <div class="mb-4" v-if="requirement.parent || requirement.children.length > 0">
              <div class="text-subtitle-2 mb-2">Иерархия требований</div>
              
              <div v-if="requirement.parent" class="mb-2">
                <div class="text-caption text-medium-emphasis">Родительское требование:</div>
                <v-chip
                  color="blue-grey"
                  variant="outlined"
                  class="mt-1"
                  prepend-icon="mdi-arrow-up"
                  @click="goToRequirement(requirement.parent.id)"
                >
                  {{ requirement.parent.id }}: {{ requirement.parent.text }}
                </v-chip>
              </div>

              <div v-if="requirement.children.length > 0">
                <div class="text-caption text-medium-emphasis">Дочерние требования:</div>
                <div class="d-flex flex-wrap gap-2 mt-1">
                  <v-chip
                    v-for="child in requirement.children"
                    :key="child.id"
                    color="blue-grey"
                    variant="outlined"
                    size="small"
                    prepend-icon="mdi-arrow-down"
                    @click="goToRequirement(child.id)"
                  >
                    {{ child.id }}
                  </v-chip>
                </div>
              </div>
            </div>

            <!-- Comments -->
            <div class="mb-4">
              <div class="text-subtitle-2 mb-2">Комментарии</div>
              <v-textarea
                variant="outlined"
                placeholder="Добавить комментарий..."
                rows="3"
                append-inner-icon="mdi-send"
              ></v-textarea>
              
              <div class="mt-3">
                <v-card variant="outlined" class="mb-2">
                  <v-card-text class="py-2">
                    <div class="d-flex align-center mb-1">
                      <v-avatar size="24" color="primary" class="mr-2">
                        <span class="text-caption">ИИ</span>
                      </v-avatar>
                      <strong class="text-body-2">Иванов Иван</strong>
                      <span class="text-caption text-medium-emphasis ml-2">2 часа назад</span>
                    </div>
                    <div class="text-body-2">Требование согласовано с отделом КИПиА</div>
                  </v-card-text>
                </v-card>
              </div>
            </div>
          </v-col>

          <!-- Right Sidebar -->
          <v-col cols="12" md="4">
            <!-- Actions -->
            <v-card variant="outlined" class="mb-3">
              <v-card-title class="text-subtitle-1">Действия</v-card-title>
              <v-card-text>
                <v-btn block color="success" class="mb-2" prepend-icon="mdi-check">
                  Утвердить
                </v-btn>
                <v-btn block color="warning" class="mb-2" prepend-icon="mdi-pencil">
                  Редактировать
                </v-btn>
                <v-btn block color="error" prepend-icon="mdi-close">
                  Отклонить
                </v-btn>
              </v-card-text>
            </v-card>

            <!-- Audit Log -->
            <v-card variant="outlined">
              <v-card-title class="text-subtitle-1">История изменений</v-card-title>
              <v-card-text>
                <v-timeline side="end" density="compact" class="ma-0">
                  <v-timeline-item
                    v-for="(event, i) in requirement.auditLog"
                    :key="i"
                    :dot-color="event.color"
                    size="small"
                  >
                    <template v-slot:icon>
                      <v-icon size="x-small">{{ event.icon }}</v-icon>
                    </template>
                    <div class="text-caption">
                      <div class="font-weight-bold">{{ event.action }}</div>
                      <div class="text-medium-emphasis">{{ event.user }}</div>
                      <div class="text-medium-emphasis">{{ event.date }}</div>
                    </div>
                  </v-timeline-item>
                </v-timeline>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { requirementsApi } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'

const router = useRouter()
const route = useRoute()
const notifications = useNotificationsStore()

const loading = ref(true)
const requirement = ref(null)

const breadcrumbs = computed(() => [
  { title: 'Проекты', to: '/projects', disabled: false },
  { title: 'Требования', disabled: true },
  { title: requirement.value?.requirement_id || '...', disabled: true }
])

const getStatusColor = (status) => {
  const colors = {
    pending: 'grey',
    accepted: 'green',
    rejected: 'red',
    modified: 'orange'
  }
  return colors[status] || 'grey'
}

const getPriorityColor = (priority) => {
  const colors = {
    Mandatory: 'red',
    Recommended: 'orange',
    Optional: 'blue',
    Unknown: 'grey'
  }
  return colors[priority] || 'grey'
}

const goToRequirement = (reqId) => {
  router.push(`/requirement/${reqId}`)
}

const buildAuditLog = (req) => {
  const log = [{ action: 'Создано AI', user: 'System', date: req.created_at, icon: 'mdi-robot', color: 'blue' }]
  if (req.status === 'modified' && req.edited_at) {
    log.push({ action: 'Отредактировано', user: req.edited_by || 'N/A', date: req.edited_at, icon: 'mdi-pencil', color: 'orange' })
  }
  if (req.status === 'accepted') {
    log.push({ action: 'Принято', user: req.edited_by || 'N/A', date: req.edited_at || req.created_at, icon: 'mdi-check', color: 'green' })
  }
  if (req.status === 'rejected') {
    log.push({ action: 'Отклонено', user: req.edited_by || 'N/A', date: req.edited_at || req.created_at, icon: 'mdi-close', color: 'red' })
  }
  return log
}

onMounted(async () => {
  const reqId = route.params.requirementId
  if (!reqId) return
  try {
    const { data } = await requirementsApi.getById(reqId)
    requirement.value = {
      ...data,
      auditLog: buildAuditLog(data),
      parent: null,
      children: []
    }
  } catch (err) {
    notifications.notifyError('Не удалось загрузить требование')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.gap-2 {
  gap: 8px;
}
</style>
