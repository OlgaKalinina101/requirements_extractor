<template>
  <div class="requirements-page">
    <div class="requirements-page__sticky">
      <h1 class="text-h4 mb-4">
        <v-icon left color="primary" class="mr-3">mdi-format-list-checks</v-icon>
        Все требования
      </h1>

      <!-- Filters (grey panel, like dashboard) -->
      <div class="filter-panel mb-4">
      <div class="filter-panel__label">
        <v-icon size="16" class="mr-1">mdi-filter-variant</v-icon>
        Фильтры
      </div>
      <v-row align="center" dense class="filter-panel__selects">
        <v-col cols="12" md="2">
          <v-select
            v-model="filters.project_id"
            :items="projectOptions"
            item-title="title"
            item-value="value"
            label="Проект"
            density="compact"
            hide-details
            clearable
            variant="outlined"
            @update:model-value="onFilterChange"
          >
            <template #prepend-inner>
              <v-icon size="16">mdi-folder-outline</v-icon>
            </template>
          </v-select>
        </v-col>
        <v-col cols="12" md="2">
          <v-select
            v-model="filters.assignee_id"
            :items="userOptions"
            item-title="title"
            item-value="value"
            label="Ответственный"
            density="compact"
            hide-details
            clearable
            variant="outlined"
            @update:model-value="onFilterChange"
          >
            <template #prepend-inner>
              <v-icon size="16">mdi-account-outline</v-icon>
            </template>
          </v-select>
        </v-col>
        <v-col cols="12" md="2">
          <v-select
            v-model="filters.discipline"
            :items="disciplineOptions"
            item-title="title"
            item-value="value"
            label="Дисциплина"
            density="compact"
            hide-details
            clearable
            variant="outlined"
            @update:model-value="onFilterChange"
          >
            <template #prepend-inner>
              <v-icon size="16">mdi-tag-outline</v-icon>
            </template>
          </v-select>
        </v-col>
        <v-col cols="12" md="2">
          <v-select
            v-model="filters.status"
            :items="statusOptions"
            item-title="title"
            item-value="value"
            label="Статус"
            density="compact"
            hide-details
            clearable
            variant="outlined"
            @update:model-value="onFilterChange"
          />
        </v-col>
        <v-col cols="12" md="2">
          <v-select
            v-model="filters.priority"
            :items="priorityOptions"
            item-title="title"
            item-value="value"
            label="Приоритет"
            density="compact"
            hide-details
            clearable
            variant="outlined"
            @update:model-value="onFilterChange"
          />
        </v-col>
        <v-col cols="12" md="2" class="d-flex align-center justify-end">
          <v-btn
            variant="outlined"
            color="grey-darken-1"
            class="filter-reset-btn"
            :disabled="!hasActiveFilters"
            @click="resetFilters"
          >
            <v-icon start size="16">mdi-refresh</v-icon>
            Сбросить
          </v-btn>
        </v-col>
      </v-row>
      <v-row align="center" dense class="filter-panel__selects mt-2">
        <v-col cols="12" md="6">
          <v-text-field
            v-model="filters.search"
            label="Поиск по тексту"
            density="compact"
            hide-details
            clearable
            variant="outlined"
            prepend-inner-icon="mdi-magnify"
            @update:model-value="onSearchChange"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-select
            v-model="filters.type"
            :items="typeOptions"
            item-title="title"
            item-value="value"
            label="Тип"
            density="compact"
            hide-details
            clearable
            variant="outlined"
            @update:model-value="onFilterChange"
          />
        </v-col>
        <v-col cols="12" md="3" class="text-right text-medium-emphasis">
          Найдено: {{ requirements.length }}
        </v-col>
      </v-row>
    </div>

      <!-- Add requirement button (managers only) -->
      <div v-if="auth.isManager" class="mb-4 d-flex justify-end">
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openAddDialog">
          Добавить требование
        </v-btn>
      </div>

      <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />
    </div>

    <div v-if="!loading && requirements.length === 0" class="text-center text-medium-emphasis py-10">
      <v-icon size="48" class="mb-2">mdi-format-list-checks</v-icon>
      <div>Требований не найдено</div>
    </div>

    <!-- Список требований — отдельный компонент со своей прокруткой -->
    <div v-else class="requirements-page__list-wrap">
      <AllRequirementsList
        :grouped-requirements="groupedRequirements"
        :scroll-to-req-id="scrollToReqId"
        :users="allUsers"
        @open-card="openReqCard"
        @delete="confirmDelete"
      />
    </div>

    <!-- Requirement card modal (on click, centered) -->
    <v-dialog v-model="reqCardShow" max-width="680" transition="dialog-transition">
      <v-card v-if="reqCardReq">
        <v-card-title class="d-flex align-center">
          <span class="text-h6">{{ reqCardReq.requirement_id }}</span>
          <v-spacer />
          <v-btn icon variant="text" @click="reqCardShow = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <div class="text-body-1 mb-3">
            <span>{{ reqModalContent.intro }}</span>
            <ul v-if="reqModalContent.subitems.length" class="req-modal__subitems">
              <li v-for="(item, i) in reqModalContent.subitems" :key="i">{{ item }}</li>
            </ul>
          </div>

          <!-- Live status / meta chips — update immediately after actions -->
          <v-chip-group class="mb-3">
            <v-chip size="small" :color="dicts.statusColor(reqCardReq.status)" variant="flat">
              {{ dicts.statusName(reqCardReq.status) }}
            </v-chip>
            <v-chip v-if="reqCardReq.type" size="small" :color="dicts.typeColor(reqCardReq.type)" variant="tonal">
              {{ dicts.typeName(reqCardReq.type) }}
            </v-chip>
            <v-chip v-if="reqCardReq.priority" size="small" :color="dicts.priorityColor(reqCardReq.priority)" variant="tonal">
              {{ dicts.priorityName(reqCardReq.priority) }}
            </v-chip>
            <v-chip v-if="reqCardReq.discipline" size="small" variant="tonal" color="grey">
              {{ reqCardReq.discipline }}
            </v-chip>
            <v-chip
              v-if="reqCardReq.assignee_id"
              size="small"
              variant="tonal"
              color="blue"
              prepend-icon="mdi-account"
            >
              {{ allUsers.find(u => u.id === reqCardReq.assignee_id)?.full_name
                 || allUsers.find(u => u.id === reqCardReq.assignee_id)?.email
                 || `#${reqCardReq.assignee_id}` }}
            </v-chip>
            <v-chip v-else size="small" variant="tonal" color="grey" prepend-icon="mdi-account-off">
              Не назначен
            </v-chip>
          </v-chip-group>

          <v-divider class="my-3" />
          <div class="text-caption text-medium-emphasis mb-2">Действия</div>
          <div class="d-flex flex-wrap gap-2">
            <v-menu v-if="auth.isManager">
              <template #activator="{ props }">
                <v-btn v-bind="props" size="small" variant="outlined" prepend-icon="mdi-swap-horizontal">Статус</v-btn>
              </template>
              <v-list density="compact">
                <v-list-item
                  v-for="s in allStatusOptions"
                  :key="s.value"
                  @click="changeStatus(reqCardReq, s.value)"
                  :disabled="reqCardReq.status === s.value"
                >
                  <v-list-item-title>{{ s.title }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
            <v-menu v-if="auth.isManager">
              <template #activator="{ props }">
                <v-btn v-bind="props" size="small" variant="outlined" prepend-icon="mdi-account-plus">Назначить</v-btn>
              </template>
              <v-list density="compact">
                <v-list-item @click="assignUser(reqCardReq, null)">
                  <v-list-item-title>— Снять</v-list-item-title>
                </v-list-item>
                <v-list-item v-for="u in usersForAssign" :key="u.id" @click="assignUser(reqCardReq, u.id)">
                  <v-list-item-title>{{ u.full_name || u.email }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
            <v-btn v-if="auth.isManager" size="small" variant="outlined" prepend-icon="mdi-pencil" @click="openEdit(reqCardReq)">
              Редактировать
            </v-btn>
            <v-btn size="small" color="primary" variant="flat" :to="{ path: `/requirement/${reqCardReq.id}`, query: { from: 'requirements' } }">
              Подробнее
            </v-btn>
          </div>

          <!-- Hierarchy & links -->
          <div v-if="reqCardReq.parent_id || reqCardReq.children?.length || reqCardReq.outgoing_links?.length || reqCardReq.incoming_links?.length" class="mt-4">
            <v-divider class="mb-2" />
            <div class="text-caption text-medium-emphasis mb-2">Связи</div>
            <div class="hierarchy-links">
              <template v-if="reqCardReq.parent_id">
                <router-link :to="`/requirement/${reqCardReq.parent_id}`" class="hierarchy-chip parent">
                  <v-icon size="12">mdi-arrow-up-bold</v-icon>
                  {{ reqCardReq.parent_requirement_id || '#' + reqCardReq.parent_id }}
                </router-link>
              </template>
              <template v-if="reqCardReq.children?.length">
                <router-link v-for="ch in reqCardReq.children" :key="ch.id" :to="`/requirement/${ch.id}`" class="hierarchy-chip child">
                  <v-icon size="12">mdi-arrow-down-bold</v-icon>
                  {{ ch.requirement_id }}
                </router-link>
              </template>
              <template v-for="lnk in (reqCardReq.outgoing_links || [])" :key="'out-' + lnk.id">
                <router-link :to="`/requirement/${lnk.requirement_id}`" class="hierarchy-chip link-out">{{ lnk.requirement_requirement_id }} ({{ dicts.linkTypeName(lnk.link_type) }})</router-link>
              </template>
              <template v-for="lnk in (reqCardReq.incoming_links || [])" :key="'in-' + lnk.id">
                <router-link :to="`/requirement/${lnk.requirement_id}`" class="hierarchy-chip link-in">{{ lnk.requirement_requirement_id }} ({{ dicts.linkTypeName(lnk.link_type) }})</router-link>
              </template>
            </div>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Edit Dialog -->
    <v-dialog v-model="editDialog.show" max-width="640">
      <v-card>
        <v-card-title>Редактировать требование</v-card-title>
        <v-card-text>
          <v-textarea
            v-model="editDialog.text"
            label="Текст требования"
            rows="4"
            auto-grow
            class="mb-3"
          />
          <v-row dense>
            <v-col cols="6">
              <v-select
                v-model="editDialog.type"
                :items="typeOptions"
                item-title="title"
                item-value="value"
                label="Тип"
                density="compact"
                clearable
              />
            </v-col>
            <v-col cols="6">
              <v-select
                v-model="editDialog.priority"
                :items="priorityOptions"
                item-title="title"
                item-value="value"
                label="Приоритет"
                density="compact"
                clearable
              />
            </v-col>
            <v-col cols="6">
              <v-select
                v-model="editDialog.discipline"
                :items="disciplineOptions"
                item-title="title"
                item-value="value"
                label="Дисциплина"
                density="compact"
                clearable
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model="editDialog.deadline"
                label="Дедлайн (ГГГГ-ММ-ДД)"
                density="compact"
                clearable
              />
            </v-col>
            <v-col cols="12">
              <v-text-field
                v-model="editDialog.reason"
                label="Причина изменения"
                density="compact"
              />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="editDialog.show = false">Отмена</v-btn>
          <v-btn color="primary" :loading="editDialog.saving" @click="saveEdit">Сохранить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add Requirement Dialog -->
    <v-dialog v-model="addDialog.show" max-width="640">
      <v-card>
        <v-card-title>Добавить требование</v-card-title>
        <v-card-text>
          <v-select
            v-model="addDialog.document_id"
            :items="documentOptions"
            item-title="title"
            item-value="value"
            label="Документ *"
            class="mb-3"
          />
          <v-textarea
            v-model="addDialog.text"
            label="Текст требования *"
            rows="3"
            auto-grow
            class="mb-3"
          />
          <v-row dense>
            <v-col cols="6">
              <v-text-field
                v-model="addDialog.requirement_id"
                label="ID требования (авто если пусто)"
                density="compact"
              />
            </v-col>
            <v-col cols="6">
              <v-select
                v-model="addDialog.type"
                :items="typeOptions"
                item-title="title"
                item-value="value"
                label="Тип"
                density="compact"
                clearable
              />
            </v-col>
            <v-col cols="6">
              <v-select
                v-model="addDialog.priority"
                :items="priorityOptions"
                item-title="title"
                item-value="value"
                label="Приоритет"
                density="compact"
                clearable
              />
            </v-col>
            <v-col cols="6">
              <v-select
                v-model="addDialog.discipline"
                :items="disciplineOptions"
                item-title="title"
                item-value="value"
                label="Дисциплина"
                density="compact"
                clearable
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model="addDialog.page_number"
                label="Страница"
                type="number"
                density="compact"
              />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="addDialog.show = false">Отмена</v-btn>
          <v-btn
            color="primary"
            :loading="addDialog.saving"
            :disabled="!addDialog.document_id || !addDialog.text"
            @click="saveAdd"
          >
            Добавить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirm Dialog -->
    <v-dialog v-model="deleteDialog.show" max-width="420">
      <v-card>
        <v-card-title>Удалить требование?</v-card-title>
        <v-card-text>
          <strong>{{ deleteDialog.req?.requirement_id }}</strong> — {{ (deleteDialog.req?.text || '').slice(0, 100) }}
          <div class="mt-2 text-caption text-error">Это действие нельзя отменить.</div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog.show = false">Отмена</v-btn>
          <v-btn color="error" :loading="deleteDialog.deleting" @click="doDelete">Удалить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { requirementsApi, projectsApi, usersApi, documentsApi } from '@/services/api'
import AllRequirementsList from '@/components/AllRequirementsList.vue'
import { useDictionariesStore } from '@/stores/dictionaries'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { parseRequirementWithSubitems } from '@/utils/requirementText'

const route = useRoute()
const dicts = useDictionariesStore()
const auth = useAuthStore()
const notify = useNotificationsStore()

// ---------- state ----------
const loading = ref(false)
const requirements = ref([])
const allProjects = ref([])
const allUsers = ref([])
const allDocuments = ref([])

const filters = reactive({
  project_id: null,
  assignee_id: null,
  discipline: null,
  status: null,
  priority: null,
  type: null,
  search: null,
})

// ---------- computed options ----------
const projectOptions = computed(() =>
  [{ title: 'Все проекты', value: null }, ...allProjects.value.map(p => ({ title: p.name, value: p.id }))]
)

const userOptions = computed(() =>
  [{ title: 'Все', value: null }, ...allUsers.value.map(u => ({ title: u.full_name || u.email, value: u.id }))]
)

const usersForAssign = computed(() => allUsers.value)

const disciplineOptions = computed(() =>
  [{ title: 'Все', value: null }, ...dicts.disciplines.map(d => ({ title: d.name, value: d.code }))]
)

const statusOptions = computed(() =>
  [{ title: 'Все', value: null }, ...dicts.statuses.map(s => ({ title: s.name, value: s.code }))]
)

const allStatusOptions = computed(() =>
  dicts.statuses.map(s => ({ title: s.name, value: s.code }))
)

const priorityOptions = computed(() =>
  [{ title: 'Все', value: null }, ...dicts.priorities.map(p => ({ title: p.name, value: p.code }))]
)

const typeOptions = computed(() =>
  [{ title: 'Все', value: null }, ...dicts.types.map(t => ({ title: t.name, value: t.code }))]
)

const hasActiveFilters = computed(() =>
  filters.project_id || filters.assignee_id || filters.discipline || filters.status || filters.priority || filters.type || (filters.search && filters.search.trim())
)

const scrollToReqId = computed(() => {
  const id = route.query.fromReq
  return id ? Number(id) : null
})

const reqModalContent = computed(() => getDisplayContent(reqCardReq.value))

const documentOptions = computed(() => {
  const projMap = Object.fromEntries(allProjects.value.map(p => [p.id, p.name]))
  return allDocuments.value.map(d => ({
    title: `${d.filename} (${d.project_id ? projMap[d.project_id] || 'Проект #' + d.project_id : 'без проекта'})`,
    value: d.id,
  }))
})

// ---------- grouped view (сортировка: проект, документ, страница, requirement_id) ----------
const groupedRequirements = computed(() => {
  const map = new Map()
  for (const req of requirements.value) {
    const projId = req.project_id ?? 0
    const projName = req.project_name ?? 'Без проекта'
    if (!map.has(projId)) map.set(projId, { projectId: projId, projectName: projName, documents: new Map(), total: 0, expanded: true })
    const proj = map.get(projId)
    proj.total++
    const docId = req.document_id
    if (!proj.documents.has(docId)) proj.documents.set(docId, { documentId: docId, filename: req.document_filename || `Документ #${docId}`, requirements: [] })
    proj.documents.get(docId).requirements.push(req)
  }
  const groups = Array.from(map.values())
    .sort((a, b) => (a.projectName || '').localeCompare(b.projectName || '') || a.projectId - b.projectId)
    .map(p => ({
    ...p,
    documents: Array.from(p.documents.values()).sort((a, b) =>
      (a.filename || '').localeCompare(b.filename || '') || a.documentId - b.documentId
    ),
  }))
  // Сортировка внутри каждого документа: страница, requirement_id
  const fromReqId = route.query.fromReq ? Number(route.query.fromReq) : null
  for (const group of groups) {
    for (const doc of group.documents) {
      doc.requirements.sort((a, b) => {
        const pa = a.page_number ?? 99999
        const pb = b.page_number ?? 99999
        if (pa !== pb) return pa - pb
        const ra = a.requirement_id || ''
        const rb = b.requirement_id || ''
        return ra.localeCompare(rb) || a.id - b.id
      })
      // Раскрыть группу, если в ней целевое требование для прокрутки
      if (fromReqId && doc.requirements.some(r => r.id === fromReqId)) {
        group.expanded = true
      }
    }
  }
  return groups
})

// ---------- helpers ----------
const getDisplayContent = (req) => {
  if (!req) return { intro: '', subitems: [] }
  if (req.human_edited) return parseRequirementWithSubitems(req.human_edited)
  return { intro: req.text || '', subitems: req.subitems || [] }
}

// ---------- fetch ----------
let searchTimeout = null

const buildParams = () => {
  const p = {}
  if (filters.project_id) p.project_id = filters.project_id
  if (filters.assignee_id) p.assignee_id = filters.assignee_id
  if (filters.discipline) p.discipline = filters.discipline
  if (filters.status) p.status = filters.status
  if (filters.priority) p.priority = filters.priority
  if (filters.type) p.type = filters.type
  if (filters.search && filters.search.trim()) p.search = filters.search.trim()
  return p
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await requirementsApi.getAll(buildParams())
    requirements.value = res.data.requirements || []
  } catch (e) {
    notify.notifyError('Не удалось загрузить требования')
  } finally {
    loading.value = false
  }
}

const onFilterChange = () => fetchData()

const onSearchChange = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(fetchData, 400)
}

const resetFilters = () => {
  Object.assign(filters, { project_id: null, assignee_id: null, discipline: null, status: null, priority: null, type: null, search: null })
  fetchData()
}

// ---------- actions ----------
const changeStatus = async (req, newStatus) => {
  try {
    await requirementsApi.setStatus(req.id, newStatus)
    req.status = newStatus
    notify.notifySuccess(`Статус изменён: ${dicts.statusName(newStatus)}`)
  } catch {
    notify.notifyError('Не удалось изменить статус')
  }
}

const assignUser = async (req, userId) => {
  try {
    await requirementsApi.assign(req.id, userId)
    req.assignee_id = userId
    const user = allUsers.value.find(u => u.id === userId)
    notify.notifySuccess(userId ? `Назначен: ${user?.full_name || user?.email}` : 'Исполнитель снят')
  } catch {
    notify.notifyError('Не удалось назначить ответственного')
  }
}

// -- Requirement card drawer --
// We store only the ID; the actual req is computed from the live requirements array
// so that any mutation (status, assignee) is immediately reflected in the modal.
const reqCardShow = ref(false)
const reqCardId   = ref(null)

const reqCardReq = computed(() =>
  reqCardId.value != null
    ? requirements.value.find(r => r.id === reqCardId.value) ?? null
    : null
)

const openReqCard = (req) => {
  reqCardId.value  = req.id
  reqCardShow.value = true
}

// -- Edit --
const editDialog = reactive({ show: false, req: null, text: '', type: null, priority: null, discipline: null, deadline: null, reason: '', saving: false })

const openEdit = (req) => {
  let text = req.human_edited || req.text
  if (!req.human_edited && req.subitems?.length) {
    text = (req.text || '') + '\n' + req.subitems.map(item => '- ' + item).join('\n')
  }
  Object.assign(editDialog, {
    show: true, req,
    text,
    type: req.type || null,
    priority: req.priority || null,
    discipline: req.discipline || null,
    deadline: req.deadline ? req.deadline.slice(0, 10) : null,
    reason: '',
    saving: false,
  })
}

const saveEdit = async () => {
  if (!editDialog.req) return
  editDialog.saving = true
  try {
    await requirementsApi.edit(
      editDialog.req.id,
      editDialog.text,
      editDialog.reason || null,
      null,
      editDialog.type,
      editDialog.priority,
      editDialog.discipline,
      null,
      editDialog.deadline,
    )
    const req = requirements.value.find(r => r.id === editDialog.req.id)
    if (req) {
      req.text = editDialog.text
      req.human_edited = editDialog.text
      req.status = 'modified'
      if (editDialog.type !== undefined) req.type = editDialog.type
      if (editDialog.priority !== undefined) req.priority = editDialog.priority
      if (editDialog.discipline !== undefined) req.discipline = editDialog.discipline
      if (editDialog.deadline !== undefined) req.deadline = editDialog.deadline
    }
    editDialog.show = false
    notify.notifySuccess('Требование обновлено')
  } catch {
    notify.notifyError('Не удалось сохранить изменения')
  } finally {
    editDialog.saving = false
  }
}

// -- Add --
const addDialog = reactive({ show: false, document_id: null, text: '', requirement_id: '', type: null, priority: null, discipline: null, page_number: null, saving: false })

const openAddDialog = () => {
  Object.assign(addDialog, { show: true, document_id: null, text: '', requirement_id: '', type: null, priority: null, discipline: null, page_number: null, saving: false })
}

const saveAdd = async () => {
  if (!addDialog.document_id || !addDialog.text) return
  addDialog.saving = true
  try {
    const res = await documentsApi.createRequirement(addDialog.document_id, {
      text: addDialog.text,
      requirement_id: addDialog.requirement_id || undefined,
      type: addDialog.type || undefined,
      priority: addDialog.priority || undefined,
      discipline: addDialog.discipline || undefined,
      page_number: addDialog.page_number ? Number(addDialog.page_number) : undefined,
    })
    addDialog.show = false
    notify.notifySuccess('Требование добавлено')
    await fetchData()
  } catch {
    notify.notifyError('Не удалось добавить требование')
  } finally {
    addDialog.saving = false
  }
}

// -- Delete --
const deleteDialog = reactive({ show: false, req: null, deleting: false })

const confirmDelete = (req) => {
  deleteDialog.req = req
  deleteDialog.show = true
  deleteDialog.deleting = false
}

const doDelete = async () => {
  if (!deleteDialog.req) return
  deleteDialog.deleting = true
  try {
    await requirementsApi.delete(deleteDialog.req.id)
    requirements.value = requirements.value.filter(r => r.id !== deleteDialog.req.id)
    deleteDialog.show = false
    notify.notifySuccess('Требование удалено')
  } catch {
    notify.notifyError('Не удалось удалить требование')
  } finally {
    deleteDialog.deleting = false
  }
}

// ---------- mount ----------
onMounted(async () => {
  await dicts.loadAll()
  const [projRes, usersRes, docsRes] = await Promise.allSettled([
    projectsApi.getAll(),
    usersApi.getAll(),
    documentsApi.getAll(),
  ])
  if (projRes.status === 'fulfilled') {
    const pd = projRes.value.data
    allProjects.value = pd?.projects || (Array.isArray(pd) ? pd : [])
  }
  if (usersRes.status === 'fulfilled') {
    const ud = usersRes.value.data
    allUsers.value = Array.isArray(ud) ? ud : (ud?.users || [])
  }
  if (docsRes.status === 'fulfilled') {
    const docs = docsRes.value.data
    allDocuments.value = docs?.documents || (Array.isArray(docs) ? docs : [])
  }
  await fetchData()
})
</script>

<style scoped>
/* ── Sticky header + filters ────────────────────────────────── */
.requirements-page__sticky {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--v-theme-surface, #fff);
  padding-bottom: 4px;
  margin-bottom: 0;
}

/* ── Filter Panel ───────────────────────────────────────────── */
.filter-panel {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.filter-panel__label {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-panel__selects {
  position: relative;
}

.filter-reset-btn {
  text-transform: none;
  font-size: 14px;
  font-weight: 500;
  min-height: 40px;
  background: #fff;
  border-color: #cbd5e1;
  color: #475569;
}
.filter-reset-btn:disabled {
  opacity: 0.5;
}

.filter-panel :deep(.v-field) {
  background: #fff;
}

.filter-panel :deep(.v-field__outline) {
  --v-field-border-opacity: 1;
  color: #cbd5e1;
}

.filter-panel :deep(.v-label),
.filter-panel :deep(.v-field input),
.filter-panel :deep(.v-field .v-field__input),
.filter-panel :deep(.v-field .v-select__selection-text) {
  color: #334155;
  font-size: 14px;
}

.filter-panel :deep(.v-field__prepend-inner .v-icon),
.filter-panel :deep(.v-field__clearable .v-icon) {
  color: #94a3b8;
}

/* ── Список требований (своя прокрутка) ───────────────────── */
.requirements-page__list-wrap {
  display: flex;
  flex-direction: column;
  min-height: 400px;
  max-height: calc(100vh - 280px);
}

.req-modal__subitems {
  margin: 6px 0 0 1em;
  padding-left: 1em;
  list-style: disc;
}

.req-modal__subitems li {
  margin-bottom: 2px;
}

.hierarchy-links {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.hierarchy-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.2s, color 0.2s;
}

.hierarchy-chip.parent {
  background: #E3F2FD;
  color: #1565C0;
}

.hierarchy-chip.parent:hover {
  background: #BBDEFB;
}

.hierarchy-chip.child {
  background: #E8F5E9;
  color: #2E7D32;
}

.hierarchy-chip.child:hover {
  background: #C8E6C9;
}

.hierarchy-chip.link-out {
  background: #FFF3E0;
  color: #E65100;
}

.hierarchy-chip.link-out:hover {
  background: #FFE0B2;
}

.hierarchy-chip.link-in {
  background: #F3E5F5;
  color: #7B1FA2;
}

.hierarchy-chip.link-in:hover {
  background: #E1BEE7;
}

.hierarchy-chip .link-type {
  font-size: 10px;
  opacity: 0.85;
  margin-left: 2px;
}
</style>
