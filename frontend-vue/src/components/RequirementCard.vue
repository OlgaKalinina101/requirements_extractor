<template>
  <v-card
    class="mb-4 requirement-card"
    :color="getStatusColor(requirement.status)"
    @click="handleCardClick"
  >
    <v-card-title class="d-flex align-center flex-wrap gap-1">
      <v-chip size="small" class="mr-2">{{ requirement.requirement_id }}</v-chip>
      <v-spacer></v-spacer>

      <!-- Execution status chip (in_progress / done / blocked) -->
      <v-chip
        v-if="isExecutionStatus(requirement.status)"
        :color="getStatusChipColor(requirement.status)"
        size="small"
        variant="flat"
        class="mr-1"
      >
        {{ getStatusText(requirement.status) }}
      </v-chip>

      <!-- Review status chip -->
      <v-chip
        v-else
        :color="getStatusChipColor(requirement.status)"
        size="small"
        variant="flat"
      >
        {{ getStatusText(requirement.status) }}
      </v-chip>
    </v-card-title>

    <v-card-text>
      <div class="text-body-1 mb-2">{{ requirement.text }}</div>

      <!-- Subitems -->
      <v-list v-if="requirement.subitems && requirement.subitems.length > 0" density="compact" class="ml-4 mt-2">
        <v-list-item v-for="(item, index) in requirement.subitems" :key="index" class="subitem">
          <template #prepend>
            <v-icon size="small" color="primary">mdi-circle-small</v-icon>
          </template>
          <v-list-item-title class="text-body-2">{{ item }}</v-list-item-title>
        </v-list-item>
      </v-list>

      <v-chip-group>
        <v-chip size="small" v-if="requirement.type">{{ translateType(requirement.type) }}</v-chip>
        <v-chip size="small" v-if="requirement.priority">{{ translatePriority(requirement.priority) }}</v-chip>
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
              <div class="text-body-2 mt-1">{{ requirement.human_edited }}</div>
            </div>
            <div v-if="requirement.edit_reason" class="mt-2">
              <strong>Причина:</strong>
              <div class="text-body-2 text-medium-emphasis">{{ requirement.edit_reason }}</div>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>

    <v-divider />

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
            :color="isExecutionStatus(requirement.status) ? getStatusChipColor(requirement.status) : 'default'"
            prepend-icon="mdi-progress-check"
            @click.stop
          >
            {{ isExecutionStatus(requirement.status) ? getStatusText(requirement.status) : 'Статус работы' }}
          </v-btn>
        </template>
        <v-list density="compact" min-width="180">
          <v-list-subheader>Статус выполнения</v-list-subheader>
          <v-list-item
            v-for="s in executionStatuses"
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
        <v-textarea v-model="editReason" label="Причина изменения (опционально)" rows="2" class="mt-4" />
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
import { useRequirementTranslations } from '@/composables/useRequirementTranslations'
import { useAuthStore } from '@/stores/auth'
import { requirementsApi } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'

const { translateType, translatePriority } = useRequirementTranslations()
const auth = useAuthStore()
const notifications = useNotificationsStore()

// Users list injected from parent ReviewView
const users = inject('users', ref([]))

const props = defineProps({
  requirement: { type: Object, required: true },
})

const emit = defineEmits(['accept', 'reject', 'edit', 'view-page', 'assigned', 'status-changed'])

const showRejectDialog = ref(false)
const showEditDialog = ref(false)
const rejectReason = ref('')
const editedText = ref('')
const editReason = ref('')

watch(() => props.requirement, (newReq) => {
  if (newReq.subitems && newReq.subitems.length > 0) {
    editedText.value = newReq.text + '\n' + newReq.subitems.map(item => '- ' + item).join('\n')
  } else {
    editedText.value = newReq.text
  }
}, { immediate: true })

// Resolve assignee name from injected users list
const assigneeName = computed(() => {
  if (!props.requirement.assignee_id) return null
  const u = users.value.find(x => x.id === props.requirement.assignee_id)
  return u ? u.label : `#${props.requirement.assignee_id}`
})

const executionStatuses = [
  { value: 'in_progress', label: 'В работе', icon: 'mdi-progress-clock' },
  { value: 'done', label: 'Выполнено', icon: 'mdi-check-circle' },
  { value: 'blocked', label: 'Заблокировано', icon: 'mdi-alert-circle' },
]

const isExecutionStatus = (s) => ['in_progress', 'done', 'blocked'].includes(s)

// User can change execution status if: they are the assignee, or manager/admin
const canSetExecutionStatus = computed(() => {
  if (auth.isManager) return true
  // Compare as numbers — assignee_id from API is int, user.id from JWT is int
  return Number(props.requirement.assignee_id) === Number(auth.user?.id)
})

const getStatusColor = (status) => ({
  pending: 'grey-lighten-5',
  accepted: 'green-lighten-5',
  rejected: 'red-lighten-5',
  modified: 'blue-lighten-5',
  in_progress: 'orange-lighten-5',
  done: 'teal-lighten-5',
  blocked: 'deep-orange-lighten-5',
}[status] || '')

const getStatusChipColor = (status) => ({
  pending: 'grey',
  accepted: 'green',
  rejected: 'red',
  modified: 'blue',
  in_progress: 'orange',
  done: 'teal',
  blocked: 'deep-orange',
}[status] || 'grey')

const getStatusText = (status) => ({
  pending: 'На рассмотрении',
  accepted: 'Принято',
  rejected: 'Отклонено',
  modified: 'Изменено',
  in_progress: 'В работе',
  done: 'Выполнено',
  blocked: 'Заблокировано',
}[status] || status)

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
    notifications.notifySuccess(`Статус: ${getStatusText(status)}`)
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
  emit('edit', { text: editedText.value, reason: editReason.value || null })
  showEditDialog.value = false
  editReason.value = ''
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
