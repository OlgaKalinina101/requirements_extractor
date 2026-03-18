<template>
  <div>
    <div class="d-flex align-center mb-2">
      <v-btn
        v-if="requirement?.document_id"
        variant="text"
        prepend-icon="mdi-arrow-left"
        @click="goBack"
        class="mr-2"
      >
        Назад
      </v-btn>
      <v-breadcrumbs :items="breadcrumbs" class="px-0">
        <template #divider><v-icon>mdi-chevron-right</v-icon></template>
      </v-breadcrumbs>
    </div>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <v-card v-if="requirement">
      <!-- Header -->
      <v-card-title class="d-flex align-center bg-blue-lighten-5 flex-wrap gap-2">
        <v-chip color="primary" class="mr-2">{{ requirement.requirement_id }}</v-chip>
        <span class="text-h6 flex-grow-1">{{ requirement.text }}</span>
        <v-chip :color="dicts.statusColor(requirement.status)" variant="flat">
          {{ dicts.statusName(requirement.status) }}
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
                <v-chip :color="dicts.typeColor(requirement.type)" variant="tonal" size="small" class="mt-1">
                  {{ dicts.typeName(requirement.type) || '—' }}
                </v-chip>
              </v-col>
              <v-col cols="6" sm="3">
                <div class="text-caption text-medium-emphasis">Приоритет</div>
                <v-chip :color="dicts.priorityColor(requirement.priority)" variant="tonal" size="small" class="mt-1">
                  {{ dicts.priorityName(requirement.priority) || '—' }}
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
              <v-col cols="6" sm="3">
                <div class="text-caption text-medium-emphasis">Дисциплина</div>
                <div class="mt-1">{{ requirement.discipline || '—' }}</div>
              </v-col>
              <v-col cols="6" sm="3">
                <div class="text-caption text-medium-emphasis">Метод подтверждения</div>
                <div class="mt-1">{{ requirement.verification_method || '—' }}</div>
              </v-col>
              <v-col cols="6" sm="3">
                <div class="text-caption text-medium-emphasis">Срок выполнения</div>
                <div class="mt-1">{{ requirement.deadline ? formatDateOnly(requirement.deadline) : '—' }}</div>
              </v-col>
            </v-row>

            <!-- Hierarchy: parent / children -->
            <div v-if="requirement.parent_requirement_id || (requirement.children && requirement.children.length)" class="mb-3">
              <div class="text-caption text-medium-emphasis">Иерархия</div>
              <div class="text-body-2 mt-1">
                <div v-if="requirement.parent_requirement_id" class="mb-1">
                  <span class="text-medium-emphasis">Родительское:</span>
                  <v-btn
                    v-if="requirement.parent_id"
                    size="small"
                    variant="text"
                    :to="`/requirement/${requirement.parent_id}`"
                    class="ml-1 pa-0"
                  >
                    {{ requirement.parent_requirement_id }}
                  </v-btn>
                </div>
                <div v-if="requirement.children && requirement.children.length">
                  <span class="text-medium-emphasis">Дочерние:</span>
                  <v-btn
                    v-for="ch in requirement.children"
                    :key="ch.id"
                    size="small"
                    variant="tonal"
                    class="ml-1 mb-1"
                    :to="`/requirement/${ch.id}`"
                  >
                    {{ ch.requirement_id }}
                  </v-btn>
                </div>
              </div>
            </div>

            <!-- Links (relations) -->
            <div class="mb-3">
              <div class="text-caption text-medium-emphasis mb-1">Связи между требованиями</div>
              <div class="text-body-2">
                <div v-if="allLinks.length === 0 && !showAddLinkForm" class="text-medium-emphasis mb-1">
                  Нет связей
                </div>
                <div v-for="link in allLinks" :key="link.id" class="d-flex align-center mb-1">
                  <v-chip size="small" variant="tonal" color="purple" class="mr-2">
                    {{ dicts.linkTypeName(link.link_type) || link.link_type }}
                  </v-chip>
                  <v-btn
                    size="small"
                    variant="text"
                    :to="`/requirement/${link.requirement_id}`"
                    class="pa-0"
                  >
                    {{ link.requirement_requirement_id }}
                  </v-btn>
                  <span class="text-medium-emphasis ml-1">— {{ link.requirement_text_preview }}</span>
                  <v-btn
                    v-if="auth.isManager"
                    icon
                    size="x-small"
                    variant="text"
                    color="error"
                    class="ml-1"
                    @click="removeLink(link)"
                  >
                    <v-icon size="small">mdi-delete</v-icon>
                  </v-btn>
                </div>
                <v-btn
                  v-if="auth.isManager && !showAddLinkForm"
                  size="small"
                  variant="tonal"
                  prepend-icon="mdi-link-plus"
                  class="mt-1"
                  @click="showAddLinkForm = true"
                >
                  Добавить связь
                </v-btn>
                <div v-if="showAddLinkForm && auth.isManager" class="mt-2 pa-2 bg-grey-lighten-4 rounded">
                  <v-autocomplete
                    v-model="newLinkTargetId"
                    :items="documentRequirementsForLink"
                    item-title="label"
                    item-value="id"
                    label="Целевое требование"
                    density="compact"
                    variant="outlined"
                    clearable
                    :loading="loadingDocReqs"
                  />
                  <v-select
                    v-model="newLinkType"
                    :items="dicts.linkTypeOptions"
                    label="Тип связи"
                    density="compact"
                    variant="outlined"
                    class="mt-2"
                  />
                  <div class="d-flex gap-2 mt-2">
                    <v-btn size="small" color="primary" :loading="addingLink" @click="addLink">Добавить</v-btn>
                    <v-btn size="small" variant="text" @click="cancelAddLink">Отмена</v-btn>
                  </div>
                </div>
              </div>
            </div>

            <!-- Section -->
            <div v-if="requirement.section_number || requirement.section_title" class="mb-3">
              <div class="text-caption text-medium-emphasis">Раздел</div>
              <div class="text-body-2 mt-1">
                <strong v-if="requirement.section_number">{{ requirement.section_number }}</strong>
                {{ requirement.section_title }}
              </div>
            </div>

            <!-- Main text + subitems -->
            <div class="mb-4">
              <div class="text-subtitle-2 mb-1">Текст требования</div>
              <div class="text-body-1">{{ requirementDisplayContent.intro }}</div>
              <v-list
                v-if="requirementDisplayContent.subitems.length"
                density="compact"
                class="ml-4 mt-2 pa-0"
              >
                <v-list-item
                  v-for="(item, i) in requirementDisplayContent.subitems"
                  :key="i"
                  class="subitem px-2 mb-1"
                >
                  <template #prepend>
                    <v-icon size="small" color="primary">mdi-circle-small</v-icon>
                  </template>
                  <v-list-item-title class="text-body-2">{{ item }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </div>

            <!-- AI text vs edited text -->
            <div v-if="requirement.human_edited" class="mb-4">
              <div class="text-subtitle-2 text-medium-emphasis mb-1">Исходный текст AI</div>
              <div class="text-body-2 text-medium-emphasis font-italic">{{ requirement.ai_suggested }}</div>
              <ul v-if="requirement.subitems && requirement.subitems.length" class="text-body-2 text-medium-emphasis font-italic ml-4 mt-1">
                <li v-for="(item, i) in requirement.subitems" :key="i">{{ item }}</li>
              </ul>
              <v-divider class="my-2" />
              <div class="text-subtitle-2 mb-1">Отредактированный текст</div>
              <div class="text-body-1">{{ humanEditedParsed.intro }}</div>
              <ul v-if="humanEditedParsed.subitems.length" class="text-body-1 ml-4 mt-1">
                <li v-for="(item, i) in humanEditedParsed.subitems" :key="i">{{ item }}</li>
              </ul>
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
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { requirementsApi, usersApi, documentsApi } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'
import { useAuthStore } from '@/stores/auth'
import { useDictionariesStore } from '@/stores/dictionaries'
import { parseRequirementWithSubitems } from '@/utils/requirementText'

const router = useRouter()
const route = useRoute()
const notifications = useNotificationsStore()
const auth = useAuthStore()
const dicts = useDictionariesStore()

const loading = ref(true)
const requirement = ref(null)
const comments = ref([])
const history = ref([])
const users = ref([])
const selectedAssignee = ref(null)
const assigneeName = ref(null)
const assignLoading = ref(false)
const newComment = ref('')
const commentLoading = ref(false)
const actionLoading = ref(null)
const rejectDialog = ref(false)
const rejectReason = ref('')
const showAddLinkForm = ref(false)
const newLinkTargetId = ref(null)
const newLinkType = ref(null)
const documentRequirementsForLink = ref([])
const loadingDocReqs = ref(false)
const addingLink = ref(false)

const allLinks = computed(() => {
  const r = requirement.value
  if (!r) return []
  const out = (r.outgoing_links || []).map(l => ({ ...l, direction: 'out' }))
  const inc = (r.incoming_links || []).map(l => ({ ...l, direction: 'in' }))
  return [...out, ...inc]
})

const breadcrumbs = computed(() => [
  { title: 'Проекты', to: '/', disabled: false },
  { title: requirement.value?.requirement_id || '...', disabled: true }
])

function goBack() {
  const r = requirement.value
  const from = route.query.from
  if (from === 'requirements') {
    router.push({ path: '/requirements', query: { fromReq: r?.id } })
  } else if (r?.document_id) {
    const query = { scrollTo: r.id }
    if (r.page_number) query.page = r.page_number
    router.push({ path: `/review/${r.document_id}`, query })
  } else {
    router.push('/')
  }
}

// Display content: when human_edited exists, parse it; else use text + subitems
const requirementDisplayContent = computed(() => {
  const r = requirement.value
  if (!r) return { intro: '', subitems: [] }
  if (r.human_edited) {
    return parseRequirementWithSubitems(r.human_edited)
  }
  return {
    intro: r.text || '',
    subitems: r.subitems || []
  }
})

// Parsed human_edited for the "Отредактированный текст" block
const humanEditedParsed = computed(() => {
  const r = requirement.value
  if (!r?.human_edited) return { intro: '', subitems: [] }
  return parseRequirementWithSubitems(r.human_edited)
})

const auditLog = computed(() => {
  const fromHistory = history.value.map((e) => {
    const actionLabels = {
      accepted: 'Принято',
      rejected: 'Отклонено',
      edited: 'Отредактировано',
      assigned: 'Назначен исполнитель',
      status_changed: 'Изменён статус',
      comment_added: 'Добавлен комментарий',
      comment_deleted: 'Удалён комментарий',
    }
    const icons = {
      accepted: 'mdi-check',
      rejected: 'mdi-close',
      edited: 'mdi-pencil',
      assigned: 'mdi-account',
      status_changed: 'mdi-update',
      comment_added: 'mdi-comment',
      comment_deleted: 'mdi-comment-remove',
    }
    const colors = {
      accepted: 'green',
      rejected: 'red',
      edited: 'orange',
      assigned: 'blue',
      status_changed: 'purple',
      comment_added: 'grey',
      comment_deleted: 'orange',
    }
    let action = actionLabels[e.action] || e.action
    if (e.action === 'assigned' && e.new_value) action += `: ${e.new_value}`
    if (e.action === 'status_changed' && e.new_value) action += `: ${e.new_value}`
    if (e.action === 'edited' && e.comment) action += ` (${e.comment})`
    if (e.action === 'comment_deleted' && e.comment) action += `: "${e.comment}"`
    return {
      action,
      user: e.user_name || '—',
      date: formatDate(e.created_at),
      icon: icons[e.action] || 'mdi-circle',
      color: colors[e.action] || 'grey',
    }
  })
  if (fromHistory.length === 0 && requirement.value?.created_at) {
    return [{
      action: 'Создано',
      user: 'System',
      date: formatDate(requirement.value.created_at),
      icon: 'mdi-robot',
      color: 'blue',
    }]
  }
  return fromHistory
})


function initials(name) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatDateOnly(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
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
    await refreshHistory()
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
    await refreshHistory()
    notifications.notifySuccess('Исполнитель назначен')
  } catch {
    notifications.notifyError('Ошибка назначения')
  } finally {
    assignLoading.value = false
  }
}

async function refreshHistory() {
  try {
    const { data } = await requirementsApi.getHistory(route.params.requirementId)
    history.value = data || []
  } catch { /* ignore */ }
}

async function loadDocumentRequirementsForLink() {
  const docId = requirement.value?.document_id
  if (!docId) return
  loadingDocReqs.value = true
  try {
    const { data } = await documentsApi.getRequirements(docId)
    const reqs = data?.requirements || data || []
    documentRequirementsForLink.value = reqs
      .filter(r => r.id !== requirement.value?.id)
      .map(r => ({ id: r.id, label: `${r.requirement_id} — ${((r.text || '').slice(0, 50))}${(r.text || '').length > 50 ? '...' : ''}` }))
  } catch {
    documentRequirementsForLink.value = []
  } finally {
    loadingDocReqs.value = false
  }
}

function cancelAddLink() {
  showAddLinkForm.value = false
  newLinkTargetId.value = null
  newLinkType.value = null
}

async function addLink() {
  if (!newLinkTargetId.value || !newLinkType.value) return
  addingLink.value = true
  try {
    await requirementsApi.createLink(route.params.requirementId, newLinkTargetId.value, newLinkType.value)
    const { data } = await requirementsApi.getById(route.params.requirementId)
    requirement.value = data
    cancelAddLink()
    notifications.notifySuccess('Связь добавлена')
  } catch {
    notifications.notifyError('Не удалось добавить связь')
  } finally {
    addingLink.value = false
  }
}

async function removeLink(link) {
  try {
    await requirementsApi.deleteLink(route.params.requirementId, link.id)
    const { data } = await requirementsApi.getById(route.params.requirementId)
    requirement.value = data
    notifications.notifySuccess('Связь удалена')
  } catch {
    notifications.notifyError('Не удалось удалить связь')
  }
}

watch(showAddLinkForm, (val) => {
  if (val) loadDocumentRequirementsForLink()
})

async function doAccept() {
  actionLoading.value = 'accept'
  try {
    await requirementsApi.accept(route.params.requirementId)
    requirement.value.status = 'accepted'
    await refreshHistory()
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
    await refreshHistory()
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
    const [reqRes, commentRes, historyRes, usersRes] = await Promise.all([
      requirementsApi.getById(reqId),
      requirementsApi.getComments(reqId),
      requirementsApi.getHistory(reqId),
      usersApi.getAll(),
    ])
    requirement.value = reqRes.data
    comments.value = commentRes.data
    history.value = historyRes.data || []
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
