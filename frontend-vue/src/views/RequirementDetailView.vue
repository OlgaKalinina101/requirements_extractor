<template>
  <div>
    <v-breadcrumbs :items="breadcrumbs" class="px-0 mb-2">
      <template #divider><v-icon>mdi-chevron-right</v-icon></template>
    </v-breadcrumbs>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <v-card v-if="requirement">
      <!-- Header -->
      <v-card-title class="d-flex align-center bg-blue-lighten-5 flex-wrap gap-2">
        <v-chip color="primary" class="mr-2">{{ requirement.requirement_id }}</v-chip>
        <span class="text-h6 flex-grow-1">{{ requirement.text }}</span>
        <v-chip :color="getStatusColor(requirement.status)" variant="flat">
          {{ statusLabel(requirement.status) }}
        </v-chip>
      </v-card-title>

      <v-divider />

      <v-card-text>
        <v-row>
          <!-- Left column -->
          <v-col cols="12" md="8">
            <!-- Attributes -->
            <v-row class="mb-4">
              <v-col cols="6" sm="3">
                <div class="text-caption text-medium-emphasis">Тип</div>
                <v-chip color="blue" size="small" class="mt-1">{{ requirement.type || '—' }}</v-chip>
              </v-col>
              <v-col cols="6" sm="3">
                <div class="text-caption text-medium-emphasis">Приоритет</div>
                <v-chip :color="getPriorityColor(requirement.priority)" size="small" class="mt-1">
                  {{ requirement.priority || '—' }}
                </v-chip>
              </v-col>
              <v-col cols="6" sm="3">
                <div class="text-caption text-medium-emphasis">Страница</div>
                <div class="mt-1">{{ requirement.page_number || '—' }}</div>
              </v-col>
              <v-col cols="6" sm="3">
                <div class="text-caption text-medium-emphasis">Документ</div>
                <v-btn
                  v-if="requirement.document_id"
                  size="small"
                  variant="text"
                  :to="`/review/${requirement.document_id}`"
                  class="mt-1 pa-0"
                  prepend-icon="mdi-open-in-new"
                >
                  #{{ requirement.document_id }}
                </v-btn>
              </v-col>
            </v-row>

            <!-- AI text vs edited text -->
            <div v-if="requirement.human_edited" class="mb-4">
              <div class="text-subtitle-2 text-medium-emphasis mb-1">Исходный текст AI</div>
              <div class="text-body-2 text-medium-emphasis font-italic">{{ requirement.ai_suggested }}</div>
              <v-divider class="my-2" />
              <div class="text-subtitle-2 mb-1">Отредактированный текст</div>
              <div class="text-body-1">{{ requirement.human_edited }}</div>
              <div v-if="requirement.edit_reason" class="text-caption text-medium-emphasis mt-1">
                Причина: {{ requirement.edit_reason }}
              </div>
            </div>

            <!-- Assignee picker (managers only) -->
            <div class="mb-4">
              <div class="text-subtitle-2 mb-2">Ответственный исполнитель</div>
              <v-autocomplete
                v-if="auth.isManager"
                v-model="selectedAssignee"
                :items="users"
                item-title="label"
                item-value="id"
                clearable
                variant="outlined"
                density="compact"
                placeholder="Не назначен"
                :loading="assignLoading"
                @update:model-value="saveAssignee"
              />
              <div v-else class="text-body-2">
                {{ assigneeName || '—' }}
              </div>
            </div>

            <!-- Comments -->
            <div class="mb-2">
              <div class="text-subtitle-2 mb-3">Комментарии ({{ comments.length }})</div>

              <div v-for="c in comments" :key="c.id" class="mb-2">
                <v-card variant="outlined">
                  <v-card-text class="py-2">
                    <div class="d-flex align-center mb-1">
                      <v-avatar size="24" color="primary" class="mr-2">
                        <span class="text-caption">{{ initials(c.author_name) }}</span>
                      </v-avatar>
                      <strong class="text-body-2">{{ c.author_name || 'Пользователь' }}</strong>
                      <span class="text-caption text-medium-emphasis ml-2">{{ formatDate(c.created_at) }}</span>
                      <v-spacer />
                      <v-btn
                        v-if="c.user_id === auth.user?.id || auth.isAdmin"
                        icon
                        size="x-small"
                        variant="text"
                        color="error"
                        @click="removeComment(c.id)"
                      >
                        <v-icon size="small">mdi-delete</v-icon>
                      </v-btn>
                    </div>
                    <div class="text-body-2">{{ c.text }}</div>
                  </v-card-text>
                </v-card>
              </div>

              <div class="d-flex align-start gap-2 mt-3">
                <v-textarea
                  v-model="newComment"
                  variant="outlined"
                  placeholder="Добавить комментарий..."
                  rows="2"
                  hide-details
                  class="flex-grow-1"
                  @keydown.ctrl.enter="postComment"
                />
                <v-btn
                  color="primary"
                  icon
                  :loading="commentLoading"
                  :disabled="!newComment.trim()"
                  @click="postComment"
                >
                  <v-icon>mdi-send</v-icon>
                </v-btn>
              </div>
            </div>
          </v-col>

          <!-- Right sidebar -->
          <v-col cols="12" md="4">
            <!-- Actions (managers only) -->
            <v-card v-if="auth.isManager" variant="outlined" class="mb-3">
              <v-card-title class="text-subtitle-1">Действия</v-card-title>
              <v-card-text>
                <v-btn
                  block
                  color="success"
                  class="mb-2"
                  prepend-icon="mdi-check"
                  :disabled="requirement.status === 'accepted'"
                  :loading="actionLoading === 'accept'"
                  @click="doAccept"
                >
                  Принять
                </v-btn>
                <v-btn
                  block
                  color="error"
                  prepend-icon="mdi-close"
                  :disabled="requirement.status === 'rejected'"
                  :loading="actionLoading === 'reject'"
                  @click="rejectDialog = true"
                >
                  Отклонить
                </v-btn>
              </v-card-text>
            </v-card>

            <!-- Audit log -->
            <v-card variant="outlined">
              <v-card-title class="text-subtitle-1">История</v-card-title>
              <v-card-text>
                <v-timeline side="end" density="compact" class="ma-0">
                  <v-timeline-item
                    v-for="(event, i) in auditLog"
                    :key="i"
                    :dot-color="event.color"
                    size="small"
                  >
                    <template #icon><v-icon size="x-small">{{ event.icon }}</v-icon></template>
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

    <!-- Reject dialog -->
    <v-dialog v-model="rejectDialog" max-width="400">
      <v-card>
        <v-card-title>Отклонить требование</v-card-title>
        <v-card-text>
          <v-textarea
            v-model="rejectReason"
            label="Причина (необязательно)"
            variant="outlined"
            rows="3"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="rejectDialog = false">Отмена</v-btn>
          <v-btn color="error" :loading="actionLoading === 'reject'" @click="doReject">Отклонить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { requirementsApi, usersApi } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const notifications = useNotificationsStore()
const auth = useAuthStore()

const loading = ref(true)
const requirement = ref(null)
const comments = ref([])
const users = ref([])
const selectedAssignee = ref(null)
const assigneeName = ref(null)
const assignLoading = ref(false)
const newComment = ref('')
const commentLoading = ref(false)
const actionLoading = ref(null)
const rejectDialog = ref(false)
const rejectReason = ref('')

const breadcrumbs = computed(() => [
  { title: 'Проекты', to: '/', disabled: false },
  { title: requirement.value?.requirement_id || '...', disabled: true }
])

const auditLog = computed(() => {
  if (!requirement.value) return []
  const r = requirement.value
  const log = [{ action: 'Создано AI', user: 'System', date: formatDate(r.created_at), icon: 'mdi-robot', color: 'blue' }]
  if (r.status === 'modified' && r.edited_at) {
    log.push({ action: 'Отредактировано', user: r.edited_by || '—', date: formatDate(r.edited_at), icon: 'mdi-pencil', color: 'orange' })
  }
  if (r.status === 'accepted') {
    log.push({ action: 'Принято', user: r.edited_by || '—', date: formatDate(r.edited_at || r.created_at), icon: 'mdi-check', color: 'green' })
  }
  if (r.status === 'rejected') {
    log.push({ action: 'Отклонено', user: r.edited_by || '—', date: formatDate(r.edited_at || r.created_at), icon: 'mdi-close', color: 'red' })
  }
  return log
})

function getStatusColor(s) {
  return { pending: 'grey', accepted: 'success', rejected: 'error', modified: 'warning' }[s] || 'grey'
}

function statusLabel(s) {
  return { pending: 'На рассмотрении', accepted: 'Принято', rejected: 'Отклонено', modified: 'Изменено' }[s] || s
}

function getPriorityColor(p) {
  return { Mandatory: 'error', Recommended: 'warning', Optional: 'info', Unknown: 'grey' }[p] || 'grey'
}

function initials(name) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function loadComments() {
  const { data } = await requirementsApi.getComments(route.params.requirementId)
  comments.value = data
}

async function postComment() {
  if (!newComment.value.trim()) return
  commentLoading.value = true
  try {
    const { data } = await requirementsApi.addComment(route.params.requirementId, newComment.value.trim())
    comments.value.push(data)
    newComment.value = ''
  } catch {
    notifications.notifyError('Не удалось добавить комментарий')
  } finally {
    commentLoading.value = false
  }
}

async function removeComment(commentId) {
  try {
    await requirementsApi.deleteComment(commentId)
    comments.value = comments.value.filter(c => c.id !== commentId)
  } catch {
    notifications.notifyError('Не удалось удалить комментарий')
  }
}

async function saveAssignee(val) {
  assignLoading.value = true
  try {
    await requirementsApi.assign(route.params.requirementId, val ?? null)
    const user = users.value.find(u => u.id === val)
    assigneeName.value = user?.label || null
    notifications.notifySuccess('Исполнитель назначен')
  } catch {
    notifications.notifyError('Ошибка назначения')
  } finally {
    assignLoading.value = false
  }
}

async function doAccept() {
  actionLoading.value = 'accept'
  try {
    await requirementsApi.accept(route.params.requirementId)
    requirement.value.status = 'accepted'
    notifications.notifySuccess('Требование принято')
  } catch {
    notifications.notifyError('Ошибка')
  } finally {
    actionLoading.value = null
  }
}

async function doReject() {
  actionLoading.value = 'reject'
  try {
    await requirementsApi.reject(route.params.requirementId, rejectReason.value || null)
    requirement.value.status = 'rejected'
    rejectDialog.value = false
    notifications.notifyInfo('Требование отклонено')
  } catch {
    notifications.notifyError('Ошибка')
  } finally {
    actionLoading.value = null
  }
}

onMounted(async () => {
  const reqId = route.params.requirementId
  if (!reqId) return
  try {
    const [reqRes, commentRes, usersRes] = await Promise.all([
      requirementsApi.getById(reqId),
      requirementsApi.getComments(reqId),
      usersApi.getAll(),
    ])
    requirement.value = reqRes.data
    comments.value = commentRes.data
    users.value = usersRes.data.map(u => ({ id: u.id, label: u.full_name || u.email }))

    if (requirement.value.assignee_id) {
      selectedAssignee.value = requirement.value.assignee_id
      const u = usersRes.data.find(x => x.id === requirement.value.assignee_id)
      assigneeName.value = u ? (u.full_name || u.email) : null
    }
  } catch {
    notifications.notifyError('Не удалось загрузить требование')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.gap-2 { gap: 8px; }
</style>
