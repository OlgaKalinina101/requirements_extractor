<template>
  <v-card
    class="mb-4 requirement-card"
    :color="cardBgColor"
    @click="handleCardClick"
    @mouseenter="$emit('highlight', requirement)"
    @mouseleave="$emit('highlight', null)"
  >
    <v-card-title class="d-flex align-center flex-wrap gap-1">
      <v-chip size="small" class="mr-2">{{ requirement.requirement_id }}</v-chip>
      <v-spacer></v-spacer>

      <v-chip
        :color="dicts.statusColor(requirement.status)"
        size="small"
        variant="flat"
      >
        {{ dicts.statusName(requirement.status) }}
      </v-chip>
    </v-card-title>

    <v-card-text>
      <div class="text-body-1 mb-2">{{ displayContent.intro }}</div>

      <!-- Subitems -->
      <v-list v-if="displayContent.subitems.length > 0" density="compact" class="ml-4 mt-2">
        <v-list-item v-for="(item, index) in displayContent.subitems" :key="index" class="subitem">
          <template #prepend>
            <v-icon size="small" color="primary">mdi-circle-small</v-icon>
          </template>
          <v-list-item-title class="text-body-2">{{ item }}</v-list-item-title>
        </v-list-item>
      </v-list>

      <v-chip-group>
        <v-chip size="small" :color="dicts.typeColor(requirement.type)" variant="tonal" v-if="requirement.type">
          {{ dicts.typeName(requirement.type) }}
        </v-chip>
        <v-chip size="small" :color="dicts.priorityColor(requirement.priority)" variant="tonal" v-if="requirement.priority">
          {{ dicts.priorityName(requirement.priority) }}
        </v-chip>
        <v-chip
          size="small"
          v-if="requirement.page_number"
          @click.stop="$emit('view-page', requirement.page_number)"
          color="primary"
          variant="tonal"
          prepend-icon="mdi-file-document"
          style="cursor: pointer;"
        >
          Страница {{ requirement.page_number }}
        </v-chip>
        <v-chip
          size="small"
          variant="tonal"
          v-if="requirement.discipline"
          color="deep-purple"
          prepend-icon="mdi-robot-outline"
          :title="'Дисциплина (предложено AI)'"
        >
          {{ requirement.discipline }}
        </v-chip>
        <v-chip size="small" variant="tonal" v-if="requirement.verification_method" color="teal">
          {{ requirement.verification_method }}
        </v-chip>
        <v-chip size="small" variant="tonal" v-if="requirement.deadline" color="orange">
          <v-icon start size="small">mdi-calendar</v-icon>
          {{ requirement.deadline.slice(0, 10) }}
        </v-chip>
      </v-chip-group>

      <!-- Assignee info (always visible) -->
      <div class="d-flex align-center mt-3 text-body-2 text-medium-emphasis">
        <v-icon size="16" class="mr-1">mdi-account-outline</v-icon>
        <span>Исполнитель:</span>
        <strong class="ml-1">{{ assigneeName || '—' }}</strong>
      </div>

      <!-- History panel for modified -->
      <v-expansion-panels v-if="requirement.status === 'modified'" class="mt-4">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon left>mdi-history</v-icon>
            История изменений
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <div class="mb-2">
              <strong>AI предложил:</strong>
              <div class="text-body-2 text-medium-emphasis mt-1">{{ requirement.ai_suggested }}</div>
              <ul v-if="requirement.subitems && requirement.subitems.length > 0" class="text-body-2 text-medium-emphasis ml-4 mt-1">
                <li v-for="(item, index) in requirement.subitems" :key="'history-' + index">{{ item }}</li>
              </ul>
            </div>
            <v-divider class="my-2" />
            <div>
              <strong>Человек изменил на:</strong>
              <div class="text-body-2 mt-1">{{ humanEditedDisplay.intro }}</div>
              <ul v-if="humanEditedDisplay.subitems.length > 0" class="text-body-2 ml-4 mt-1">
                <li v-for="(item, index) in humanEditedDisplay.subitems" :key="'human-' + index">{{ item }}</li>
              </ul>
            </div>
            <div v-if="requirement.edit_reason" class="mt-2">
              <strong>Причина:</strong>
              <div class="text-body-2 text-medium-emphasis">{{ requirement.edit_reason }}</div>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>

    <v-divider v-if="showDetailLink" />

    <!-- Подробнее — только на экране требований, не на review -->
    <v-card-actions v-if="showDetailLink" class="px-3 py-1">
      <v-btn
        size="small"
        variant="text"
        prepend-icon="mdi-comment-text-outline"
        @click.stop="goToDetail"
      >
        Подробнее и комментарии
      </v-btn>
    </v-card-actions>

    <v-divider v-if="showDetailLink" />

    <!-- Assignment & execution status row — always visible -->
    <v-card-actions class="px-3 py-2 flex-wrap ga-2">
      <!-- Assign button (manager+) -->
      <v-menu v-if="auth.isManager" :close-on-content-click="true">
        <template #activator="{ props: menuProps }">
          <v-btn
            v-bind="menuProps"
            size="small"
            :variant="requirement.assignee_id ? 'tonal' : 'outlined'"
            :color="requirement.assignee_id ? 'primary' : 'default'"
            prepend-icon="mdi-account-plus"
            @click.stop
          >
            {{ assigneeName || 'Назначить' }}
          </v-btn>
        </template>
        <v-list density="compact" min-width="220">
          <v-list-subheader>Исполнитель</v-list-subheader>
          <v-list-item
            v-for="u in users"
            :key="u.id"
            :title="u.label"
            :prepend-icon="u.id === requirement.assignee_id ? 'mdi-check' : 'mdi-account'"
            @click="assignUser(u.id)"
          />
          <v-divider />
          <v-list-item
            v-if="requirement.assignee_id"
            title="Снять назначение"
            prepend-icon="mdi-account-off"
            @click="assignUser(null)"
          />
        </v-list>
      </v-menu>

      <!-- Execution status button (assignee or manager) -->
      <v-menu v-if="canSetExecutionStatus" :close-on-content-click="true">
        <template #activator="{ props: menuProps }">
          <v-btn
            v-bind="menuProps"
            size="small"
            :variant="isExecutionStatus(requirement.status) ? 'tonal' : 'outlined'"
            :color="isExecutionStatus(requirement.status) ? dicts.statusColor(requirement.status) : 'default'"
            prepend-icon="mdi-progress-check"
            @click.stop
          >
            {{ isExecutionStatus(requirement.status) ? dicts.statusName(requirement.status) : 'Статус работы' }}
          </v-btn>
        </template>
        <v-list density="compact" min-width="180">
          <v-list-subheader>Статус выполнения</v-list-subheader>
          <v-list-item
            v-for="s in dicts.executionStatusOptions"
            :key="s.value"
            :title="s.label"
            :prepend-icon="requirement.status === s.value ? 'mdi-check' : s.icon"
            @click="changeExecutionStatus(s.value)"
          />
        </v-list>
      </v-menu>
    </v-card-actions>

    <!-- Manager review actions (pending only) -->
    <template v-if="auth.isManager && requirement.status === 'pending'">
      <v-divider />
      <v-card-actions class="px-3 py-2">
        <v-btn color="success" variant="flat" size="small" @click.stop="$emit('accept')">
          <v-icon start>mdi-check</v-icon>Принять
        </v-btn>
        <v-btn color="error" variant="flat" size="small" @click.stop="showRejectDialog = true">
          <v-icon start>mdi-close</v-icon>Отклонить
        </v-btn>
        <v-btn color="primary" variant="flat" size="small" @click.stop="showEditDialog = true">
          <v-icon start>mdi-pencil</v-icon>Редактировать
        </v-btn>
      </v-card-actions>
    </template>
  </v-card>

  <!-- Reject Dialog -->
  <v-dialog v-model="showRejectDialog" max-width="500">
    <v-card>
      <v-card-title>Отклонить требование</v-card-title>
      <v-card-text>
        <v-textarea v-model="rejectReason" label="Причина отклонения (опционально)" rows="3" />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="showRejectDialog = false">Отмена</v-btn>
        <v-btn color="error" @click="handleReject">Отклонить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Edit Dialog -->
  <v-dialog v-model="showEditDialog" max-width="700">
    <v-card>
      <v-card-title>Редактировать требование</v-card-title>
      <v-card-text>
        <div class="mb-4">
          <strong>AI предложил:</strong>
          <div class="text-body-2 text-medium-emphasis mt-1">{{ requirement.ai_suggested }}</div>
          <ul v-if="requirement.subitems && requirement.subitems.length > 0" class="text-body-2 text-medium-emphasis ml-4 mt-1">
            <li v-for="(item, index) in requirement.subitems" :key="index">{{ item }}</li>
          </ul>
        </div>
        <v-textarea v-model="editedText" label="Ваша версия" rows="4" required />

        <v-row class="mt-3">
          <v-col cols="6">
            <v-select
              v-model="editType"
              :items="dicts.typeOptions"
              label="Тип"
              density="compact"
              variant="outlined"
              clearable
            />
          </v-col>
          <v-col cols="6">
            <v-select
              v-model="editPriority"
              :items="dicts.priorityOptions"
              label="Приоритет"
              density="compact"
              variant="outlined"
              clearable
            />
          </v-col>
        </v-row>

        <v-row class="mt-2">
          <v-col cols="6">
            <v-select
              v-model="editDiscipline"
              :items="dicts.disciplineOptions"
              label="Дисциплина"
              density="compact"
              variant="outlined"
              clearable
            />
          </v-col>
          <v-col cols="6">
            <v-select
              v-model="editVerificationMethod"
              :items="dicts.verificationMethodOptions"
              label="Метод подтверждения"
              density="compact"
              variant="outlined"
              clearable
            />
          </v-col>
        </v-row>

        <v-row class="mt-2">
          <v-col cols="6">
            <v-text-field
              v-model="editDeadline"
              label="Срок выполнения"
              type="date"
              density="compact"
              variant="outlined"
              clearable
            />
          </v-col>
        </v-row>

        <v-textarea v-model="editReason" label="Причина изменения (опционально)" rows="2" class="mt-2" />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="showEditDialog = false">Отмена</v-btn>
        <v-btn color="primary" @click="handleEdit">Сохранить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch, computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useDictionariesStore } from '@/stores/dictionaries'
import { requirementsApi } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'
import { parseRequirementWithSubitems } from '@/utils/requirementText'

const auth = useAuthStore()
const dicts = useDictionariesStore()
const notifications = useNotificationsStore()
const router = useRouter()

// Users list injected from parent ReviewView
const users = inject('users', ref([]))
const documentId = inject('documentId', ref(null))

const props = defineProps({
  requirement: { type: Object, required: true },
  showDetailLink: { type: Boolean, default: true },
})

const emit = defineEmits(['accept', 'reject', 'edit', 'view-page', 'assigned', 'status-changed', 'highlight'])

const showRejectDialog = ref(false)
const showEditDialog = ref(false)
const rejectReason = ref('')
const editedText = ref('')
const editReason = ref('')
const editType = ref('')
const editPriority = ref('')
const editDiscipline = ref('')
const editVerificationMethod = ref('')
const editDeadline = ref('')

watch(() => props.requirement, (newReq) => {
  if (newReq.status === 'modified' && newReq.human_edited) {
    editedText.value = newReq.human_edited
  } else if (newReq.subitems && newReq.subitems.length > 0) {
    editedText.value = newReq.text + '\n' + newReq.subitems.map(item => '- ' + item).join('\n')
  } else {
    editedText.value = newReq.text
  }
  editType.value = newReq.type || ''
  editPriority.value = newReq.priority || ''
  editDiscipline.value = newReq.discipline || ''
  editVerificationMethod.value = newReq.verification_method || ''
  editDeadline.value = newReq.deadline ? newReq.deadline.slice(0, 10) : ''
}, { immediate: true })

// Display content: when modified + human_edited, parse it; else use text + subitems
const displayContent = computed(() => {
  const r = props.requirement
  if (r.status === 'modified' && r.human_edited) {
    return parseRequirementWithSubitems(r.human_edited)
  }
  return {
    intro: r.text || '',
    subitems: r.subitems || []
  }
})

// Parsed human_edited for history panel
const humanEditedDisplay = computed(() => {
  const r = props.requirement
  if (!r.human_edited) return { intro: '', subitems: [] }
  return parseRequirementWithSubitems(r.human_edited)
})

// Resolve assignee name from injected users list
const assigneeName = computed(() => {
  if (!props.requirement.assignee_id) return null
  const u = users.value.find(x => x.id === props.requirement.assignee_id)
  return u ? u.label : `#${props.requirement.assignee_id}`
})

const isExecutionStatus = (s) => ['in_progress', 'done', 'blocked'].includes(s)

const canSetExecutionStatus = computed(() => {
  if (auth.isManager) return true
  return Number(props.requirement.assignee_id) === Number(auth.user?.id)
})

// Soft background tint derived from the status color in the dictionary
const cardBgColor = computed(() => {
  const base = dicts.statusColor(props.requirement.status)
  if (!base || base === 'grey') return 'grey-lighten-5'
  // Append lighten-5 to any plain color name for a subtle tint
  return base.includes('-') ? base : `${base}-lighten-5`
})

async function assignUser(userId) {
  try {
    await requirementsApi.assign(props.requirement.id, userId)
    emit('assigned', { requirementId: props.requirement.id, assigneeId: userId })
    notifications.notifySuccess(userId ? 'Исполнитель назначен' : 'Назначение снято')
  } catch {
    notifications.notifyError('Ошибка назначения')
  }
}

async function changeExecutionStatus(status) {
  try {
    await requirementsApi.setStatus(props.requirement.id, status)
    emit('status-changed', { requirementId: props.requirement.id, status })
    notifications.notifySuccess(`Статус: ${dicts.statusName(status)}`)
  } catch (e) {
    notifications.notifyError(e.response?.data?.detail || 'Ошибка смены статуса')
  }
}

const handleReject = () => {
  emit('reject', rejectReason.value || null)
  showRejectDialog.value = false
  rejectReason.value = ''
}

const handleEdit = () => {
  if (!editedText.value.trim()) return
  emit('edit', {
    text: editedText.value,
    reason: editReason.value || null,
    type: editType.value || null,
    priority: editPriority.value || null,
    discipline: editDiscipline.value || null,
    verification_method: editVerificationMethod.value || null,
    deadline: editDeadline.value || null,
  })
  showEditDialog.value = false
  editReason.value = ''
}

function goToDetail() {
  const docId = documentId?.value
  if (docId) {
    router.push({ path: `/requirement/${props.requirement.id}`, query: { from: docId } })
  } else {
    router.push(`/requirement/${props.requirement.id}`)
  }
}

const handleCardClick = (event) => {
  if (
    event.target.closest('button') ||
    event.target.closest('.v-btn') ||
    event.target.closest('.v-chip') ||
    event.target.closest('.v-expansion-panel') ||
    event.target.closest('.v-menu')
  ) return
  if (props.requirement.page_number) emit('view-page', props.requirement.page_number)
}
</script>

<style scoped>
.requirement-card {
  cursor: pointer;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.requirement-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
  transform: translateY(-2px);
}
.requirement-card:active { transform: translateY(0); }
.subitem {
  background-color: rgba(var(--v-theme-surface-variant), 0.3);
  border-left: 2px solid rgb(var(--v-theme-primary));
  margin-bottom: 4px;
  padding: 4px 8px;
  border-radius: 4px;
}
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
</style>
