<template>
  <div class="all-requirements-list">
    <template v-for="group in groupedRequirements" :key="group.projectId">
      <v-card class="mb-3">
        <v-card-title class="d-flex align-center py-2 px-4">
          <v-icon size="small" class="mr-2" color="primary">mdi-folder</v-icon>
          <span class="text-subtitle-1 font-weight-medium">{{ group.projectName }}</span>
          <v-chip size="x-small" class="ml-2" color="primary" variant="tonal">{{ group.total }}</v-chip>
          <v-spacer />
          <v-btn
            variant="text"
            density="compact"
            :icon="group.expanded ? 'mdi-chevron-up' : 'mdi-chevron-down'"
            @click="group.expanded = !group.expanded"
          />
        </v-card-title>
        <v-divider />
        <v-expand-transition>
          <div v-if="group.expanded">
            <template v-for="doc in group.documents" :key="doc.documentId">
              <div class="px-4 py-2 bg-grey-lighten-5">
                <v-icon size="small" class="mr-1" color="grey-darken-1">mdi-file-document-outline</v-icon>
                <span class="text-body-2 text-medium-emphasis">{{ doc.filename }}</span>
                <v-chip size="x-small" class="ml-2" variant="tonal">{{ doc.requirements.length }}</v-chip>
                <v-btn
                  size="x-small"
                  variant="text"
                  :href="`/review/${doc.documentId}`"
                  class="ml-1"
                  icon="mdi-open-in-new"
                  title="Открыть документ"
                />
              </div>
              <v-divider />
              <div class="req-cards">
                <div
                  v-for="req in doc.requirements"
                  :key="req.id"
                  :id="`req-${req.id}`"
                  class="req-card"
                  :class="rowBgClass(req.status)"
                  @click="$emit('open-card', req)"
                >
                  <div class="req-card__header">
                    <v-chip
                      size="small"
                      :color="dicts.statusColor(req.status)"
                      variant="flat"
                      class="req-card__status"
                    >
                      {{ dicts.statusName(req.status) }}
                    </v-chip>
                    <span class="req-card__id">{{ req.requirement_id }}</span>
                    <div class="req-card__actions" @click.stop>
                      <v-btn icon size="small" variant="text" :to="{ path: `/requirement/${req.id}`, query: { from: 'requirements' } }" title="Подробнее">
                        <v-icon size="small">mdi-open-in-new</v-icon>
                      </v-btn>
                      <v-btn v-if="auth.isManager" icon size="small" variant="text" color="error" title="Удалить" @click="$emit('delete', req)">
                        <v-icon size="small">mdi-delete</v-icon>
                      </v-btn>
                    </div>
                  </div>
                  <div class="req-card__text">
                    <span>{{ getDisplayContent(req).intro }}</span>
                    <ul v-if="getDisplayContent(req).subitems.length" class="req-card__subitems">
                      <li v-for="(item, i) in getDisplayContent(req).subitems" :key="i">{{ item }}</li>
                    </ul>
                  </div>
                  <div class="req-card__meta">
                    <v-chip v-if="req.type" size="small" :color="dicts.typeColor(req.type)" variant="tonal">{{ dicts.typeName(req.type) }}</v-chip>
                    <v-chip v-if="req.priority" size="small" :color="dicts.priorityColor(req.priority)" variant="tonal">{{ dicts.priorityName(req.priority) }}</v-chip>
                    <v-chip v-if="req.discipline" size="small" variant="tonal" color="grey">{{ req.discipline }}</v-chip>
                    <v-chip v-if="req.assignee_id" size="small" variant="tonal" color="blue" prepend-icon="mdi-account">{{ userName(req.assignee_id) }}</v-chip>
                    <v-chip v-if="req.deadline" size="small" variant="tonal" color="orange" prepend-icon="mdi-calendar">{{ req.deadline.slice(0,10) }}</v-chip>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </v-expand-transition>
      </v-card>
    </template>
  </div>
</template>

<script setup>
import { watch, nextTick } from 'vue'
import { useDictionariesStore } from '@/stores/dictionaries'
import { useAuthStore } from '@/stores/auth'
import { parseRequirementWithSubitems } from '@/utils/requirementText'

const props = defineProps({
  groupedRequirements: { type: Array, required: true },
  scrollToReqId: { type: [Number, String], default: null },
  users: { type: Array, default: () => [] },
})

defineEmits(['open-card', 'delete'])

const dicts = useDictionariesStore()
const auth = useAuthStore()

const getDisplayContent = (req) => {
  if (!req) return { intro: '', subitems: [] }
  if (req.human_edited) return parseRequirementWithSubitems(req.human_edited)
  return { intro: req.text || '', subitems: req.subitems || [] }
}

const userName = (id) => {
  if (!id) return ''
  const u = props.users.find(u => u.id === id)
  return u ? (u.full_name || u.email) : `#${id}`
}

const rowBgClass = (status) => {
  if (status === 'accepted') return 'bg-green-lighten-5'
  if (status === 'rejected') return 'bg-red-lighten-5'
  if (status === 'modified') return 'bg-blue-lighten-5'
  return ''
}

// Прокрутка к требованию при возврате с экрана детали
watch(() => props.scrollToReqId, async (id) => {
  if (!id) return
  await nextTick()
  // Небольшая задержка для раскрытия групп (v-expand-transition)
  setTimeout(() => {
    const el = document.getElementById(`req-${id}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, 150)
}, { immediate: true })
</script>

<style scoped>
.all-requirements-list {
  overflow-y: auto;
  flex: 1 1 auto;
  min-height: 0;
}

.req-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 16px 16px;
}

.req-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px 16px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.req-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  border-color: #d1d5db;
}

.req-card__header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.req-card__status {
  flex-shrink: 0;
  min-width: 100px;
  justify-content: center;
}

.req-card__id {
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
}

.req-card__actions {
  margin-left: auto;
  display: flex;
  gap: 0;
}

.req-card__text {
  font-size: 15px;
  line-height: 1.5;
  color: #1f2937;
  margin-bottom: 10px;
}

.req-card__subitems {
  margin: 6px 0 0 1em;
  padding-left: 1em;
  list-style: disc;
}

.req-card__subitems li {
  margin-bottom: 2px;
}

.req-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
