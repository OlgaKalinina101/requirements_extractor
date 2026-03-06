<template>
  <v-card 
    class="mb-4 requirement-card" 
    :color="getStatusColor(requirement.status)"
    @click="handleCardClick"
  >
    <v-card-title class="d-flex align-center">
      <v-chip size="small" class="mr-2">{{ requirement.requirement_id }}</v-chip>
      <v-spacer></v-spacer>
      <v-chip
        :color="getStatusChipColor(requirement.status)"
        size="small"
        variant="flat"
      >
        {{ getStatusText(requirement.status) }}
      </v-chip>
    </v-card-title>
    
    <v-card-text>
      <div class="text-body-1 mb-2">{{ requirement.text }}</div>
      
      <!-- Subitems list if present -->
      <v-list v-if="requirement.subitems && requirement.subitems.length > 0" density="compact" class="ml-4 mt-2">
        <v-list-item
          v-for="(item, index) in requirement.subitems"
          :key="index"
          class="subitem"
        >
          <template v-slot:prepend>
            <v-icon size="small" color="primary">mdi-circle-small</v-icon>
          </template>
          <v-list-item-title class="text-body-2">{{ item }}</v-list-item-title>
        </v-list-item>
      </v-list>
      
      <v-chip-group>
        <v-chip size="small" v-if="requirement.type">
          {{ translateType(requirement.type) }}
        </v-chip>
        <v-chip size="small" v-if="requirement.priority">
          {{ translatePriority(requirement.priority) }}
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
      </v-chip-group>

      <!-- AI vs Human comparison -->
      <v-expansion-panels v-if="requirement.status === 'modified'" class="mt-4">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon left>mdi-history</v-icon>
            История изменений
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <div class="mb-2">
              <strong>AI предложил:</strong>
              <div class="text-body-2 text-medium-emphasis mt-1">
                {{ requirement.ai_suggested }}
              </div>
              <!-- Show subitems if present -->
              <ul v-if="requirement.subitems && requirement.subitems.length > 0" class="text-body-2 text-medium-emphasis ml-4 mt-1">
                <li v-for="(item, index) in requirement.subitems" :key="'history-' + index">{{ item }}</li>
              </ul>
            </div>
            <v-divider class="my-2"></v-divider>
            <div>
              <strong>Человек изменил на:</strong>
              <div class="text-body-2 mt-1">
                {{ requirement.human_edited }}
              </div>
            </div>
            <div v-if="requirement.edit_reason" class="mt-2">
              <strong>Причина:</strong>
              <div class="text-body-2 text-medium-emphasis">{{ requirement.edit_reason }}</div>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
    
    <v-card-actions v-if="requirement.status === 'pending'">
      <v-btn
        color="success"
        variant="flat"
        @click.stop="$emit('accept')"
      >
        <v-icon left>mdi-check</v-icon>
        Принять
      </v-btn>
      <v-btn
        color="error"
        variant="flat"
        @click.stop="showRejectDialog = true"
      >
        <v-icon left>mdi-close</v-icon>
        Отклонить
      </v-btn>
      <v-btn
        color="primary"
        variant="flat"
        @click.stop="showEditDialog = true"
      >
        <v-icon left>mdi-pencil</v-icon>
        Редактировать
      </v-btn>
    </v-card-actions>
  </v-card>

  <!-- Reject Dialog -->
  <v-dialog v-model="showRejectDialog" max-width="500">
    <v-card>
      <v-card-title>Отклонить требование</v-card-title>
      <v-card-text>
        <v-textarea
          v-model="rejectReason"
          label="Причина отклонения (опционально)"
          rows="3"
        ></v-textarea>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
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
          <div class="text-body-2 text-medium-emphasis mt-1">
            {{ requirement.ai_suggested }}
          </div>
          <!-- Show subitems if present -->
          <ul v-if="requirement.subitems && requirement.subitems.length > 0" class="text-body-2 text-medium-emphasis ml-4 mt-1">
            <li v-for="(item, index) in requirement.subitems" :key="index">{{ item }}</li>
          </ul>
        </div>
        
        <v-textarea
          v-model="editedText"
          label="Ваша версия"
          rows="4"
          required
        ></v-textarea>
        
        <v-textarea
          v-model="editReason"
          label="Причина изменения (опционально)"
          rows="2"
          class="mt-4"
        ></v-textarea>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="showEditDialog = false">Отмена</v-btn>
        <v-btn color="primary" @click="handleEdit">Сохранить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRequirementTranslations } from '@/composables/useRequirementTranslations'

const { translateType, translatePriority } = useRequirementTranslations()

const props = defineProps({
  requirement: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['accept', 'reject', 'edit', 'view-page'])

const showRejectDialog = ref(false)
const showEditDialog = ref(false)
const rejectReason = ref('')
const editedText = ref('')
const editReason = ref('')

watch(() => props.requirement, (newReq) => {
  // Combine text with subitems for editing
  if (newReq.subitems && newReq.subitems.length > 0) {
    editedText.value = newReq.text + '\n' + newReq.subitems.map(item => '- ' + item).join('\n')
  } else {
    editedText.value = newReq.text
  }
}, { immediate: true })

const getStatusColor = (status) => {
  const colors = {
    pending: 'grey-lighten-5',
    accepted: 'green-lighten-5',
    rejected: 'red-lighten-5',
    modified: 'blue-lighten-5'
  }
  return colors[status] || ''
}

const getStatusChipColor = (status) => {
  const colors = {
    pending: 'grey',
    accepted: 'green',
    rejected: 'red',
    modified: 'blue'
  }
  return colors[status] || 'grey'
}

const getStatusText = (status) => {
  const texts = {
    pending: 'Pending',
    accepted: 'Accepted',
    rejected: 'Rejected',
    modified: 'Modified'
  }
  return texts[status] || status
}

const handleReject = () => {
  emit('reject', rejectReason.value || null)
  showRejectDialog.value = false
  rejectReason.value = ''
}

const handleEdit = () => {
  if (!editedText.value.trim()) {
    return
  }
  emit('edit', {
    text: editedText.value,
    reason: editReason.value || null
  })
  showEditDialog.value = false
  editReason.value = ''
}

const handleCardClick = (event) => {
  // Don't trigger if clicking on buttons or interactive elements
  if (
    event.target.closest('button') ||
    event.target.closest('.v-btn') ||
    event.target.closest('.v-chip') ||
    event.target.closest('.v-expansion-panel')
  ) {
    return
  }
  
  // Emit view-page event with the page number
  if (props.requirement.page_number) {
    emit('view-page', props.requirement.page_number)
  }
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

.requirement-card:active {
  transform: translateY(0);
}

.subitem {
  background-color: rgba(var(--v-theme-surface-variant), 0.3);
  border-left: 2px solid rgb(var(--v-theme-primary));
  margin-bottom: 4px;
  padding: 4px 8px;
  border-radius: 4px;
}
</style>
