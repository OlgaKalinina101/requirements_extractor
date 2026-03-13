<template>
  <div>
    <h1 class="text-h4 mb-4">
      <v-icon left color="primary" class="mr-3">mdi-cog</v-icon>
      Администрирование
    </h1>

    <v-row>
      <!-- Dictionaries List -->
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>Справочники</v-card-title>
          <v-list>
            <v-list-item
              v-for="dict in dictionaries"
              :key="dict.id"
              :class="{ 'bg-blue-lighten-5': selectedDict?.id === dict.id }"
              @click="selectDictionary(dict)"
            >
              <template #prepend>
                <v-icon :color="dict.color">{{ dict.icon }}</v-icon>
              </template>
              <v-list-item-title>{{ dict.title }}</v-list-item-title>
              <v-list-item-subtitle>{{ dict.count }} записей</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <!-- Dictionary Items -->
      <v-col cols="12" md="8">
        <v-card v-if="selectedDict">
          <v-card-title class="d-flex align-center">
            {{ selectedDict.title }}
            <v-spacer />
            <v-btn color="primary" prepend-icon="mdi-plus" @click="openAddDialog">
              Добавить
            </v-btn>
          </v-card-title>

          <v-progress-linear v-if="loadingItems" indeterminate color="primary" />

          <v-card-text>
            <v-data-table
              :headers="tableHeaders"
              :items="currentItems"
              :items-per-page="15"
              class="elevation-0"
            >
              <template #item.name="{ item }">
                <v-chip v-if="item.color" :color="item.color" size="small">
                  {{ item.name }}
                </v-chip>
                <span v-else>{{ item.name }}</span>
              </template>

              <template #item.is_active="{ item }">
                <v-chip :color="item.is_active ? 'green' : 'grey'" size="small">
                  {{ item.is_active ? 'Активно' : 'Неактивно' }}
                </v-chip>
              </template>

              <template #item.actions="{ item }">
                <v-btn icon size="small" variant="text" @click="editItem(item)">
                  <v-icon>mdi-pencil</v-icon>
                </v-btn>
                <v-btn icon size="small" variant="text" color="error" @click="confirmDelete(item)">
                  <v-icon>mdi-delete</v-icon>
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>

        <v-alert v-else type="info" variant="tonal" class="mt-4">
          Выберите справочник для редактирования
        </v-alert>
      </v-col>
    </v-row>

    <!-- Add/Edit Dialog -->
    <v-dialog v-model="showAddDialog" max-width="600">
      <v-card>
        <v-card-title>
          {{ editingItem ? 'Редактировать запись' : 'Добавить запись' }}
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="formData.name"
            label="Название"
            variant="outlined"
            class="mb-3"
          />

          <v-text-field
            v-if="selectedDict?.id !== 'statuses'"
            v-model="formData.code"
            label="Код (латиница, напр. Technical)"
            variant="outlined"
            class="mb-3"
          />

          <v-textarea
            v-model="formData.description"
            label="Описание"
            variant="outlined"
            rows="3"
            class="mb-3"
          />

          <v-select
            v-model="formData.color"
            :items="colorOptions"
            item-title="label"
            item-value="value"
            label="Цвет"
            variant="outlined"
            class="mb-3"
            clearable
          >
            <template #selection="{ item }">
              <v-chip :color="item.value" size="small">{{ item.title }}</v-chip>
            </template>
          </v-select>

          <v-text-field
            v-model.number="formData.sort_order"
            label="Порядок сортировки"
            type="number"
            variant="outlined"
            class="mb-3"
          />

          <v-checkbox v-model="formData.is_active" label="Активно" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddDialog = false">Отмена</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveItem">Сохранить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirm Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title>Удалить запись?</v-card-title>
        <v-card-text>
          Вы уверены, что хотите удалить <strong>{{ deletingItem?.name }}</strong>?
          Это действие нельзя отменить.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDeleteDialog = false">Отмена</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteItem">Удалить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import api from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'

const notifications = useNotificationsStore()

const dictionaries = ref([
  { id: 'requirement_types', title: 'Типы требований',         icon: 'mdi-shape',         color: 'blue',   count: 0 },
  { id: 'priorities',        title: 'Приоритеты',              icon: 'mdi-flag',          color: 'orange', count: 0 },
  { id: 'statuses',          title: 'Статусы жизненного цикла', icon: 'mdi-traffic-light', color: 'green',  count: 0 },
])

const colorOptions = [
  { label: 'Красный',     value: 'red' },
  { label: 'Оранжевый',   value: 'orange' },
  { label: 'Синий',       value: 'blue' },
  { label: 'Голубой',     value: 'cyan' },
  { label: 'Зелёный',     value: 'green' },
  { label: 'Бирюзовый',   value: 'teal' },
  { label: 'Фиолетовый',  value: 'purple' },
  { label: 'Коричневый',  value: 'brown' },
  { label: 'Серый',       value: 'grey' },
  { label: 'Лаймовый',    value: 'lime-darken-2' },
]

const selectedDict   = ref(null)
const currentItems   = ref([])
const loadingItems   = ref(false)
const showAddDialog  = ref(false)
const showDeleteDialog = ref(false)
const editingItem    = ref(null)
const deletingItem   = ref(null)
const saving         = ref(false)
const deleting       = ref(false)

const emptyForm = () => ({ name: '', code: '', description: '', color: '', sort_order: 0, is_active: true })
const formData = ref(emptyForm())

const tableHeaders = computed(() => {
  if (!selectedDict.value) return []

  const cols = [
    { title: 'Название',  key: 'name',        sortable: true  },
    { title: 'Описание',  key: 'description', sortable: false },
  ]

  if (selectedDict.value.id !== 'statuses') {
    cols.splice(1, 0, { title: 'Код', key: 'code', sortable: true })
  }

  cols.push({ title: 'Статус',    key: 'is_active',  sortable: true })
  cols.push({ title: 'Порядок',   key: 'sort_order', sortable: true })
  cols.push({ title: 'Действия',  key: 'actions',    sortable: false, align: 'end' })

  return cols
})

async function loadItems(dict) {
  loadingItems.value = true
  try {
    const data = await api.get(`/api/dictionaries/${dict.id}`)
    currentItems.value = data.data
    // update count badge
    const found = dictionaries.value.find(d => d.id === dict.id)
    if (found) found.count = data.data.length
  } catch (e) {
    notifications.notifyError(`Не удалось загрузить справочник: ${e.message}`)
  } finally {
    loadingItems.value = false
  }
}

async function selectDictionary(dict) {
  selectedDict.value = dict
  await loadItems(dict)
}

function openAddDialog() {
  editingItem.value = null
  formData.value = emptyForm()
  showAddDialog.value = true
}

function editItem(item) {
  editingItem.value = item
  formData.value = {
    name: item.name,
    code: item.code || '',
    description: item.description || '',
    color: item.color || '',
    sort_order: item.sort_order ?? 0,
    is_active: item.is_active,
  }
  showAddDialog.value = true
}

async function saveItem() {
  if (!formData.value.name.trim()) {
    notifications.notifyError('Поле «Название» обязательно')
    return
  }
  saving.value = true
  try {
    const payload = { ...formData.value }
    if (editingItem.value) {
      await api.put(`/api/dictionaries/${selectedDict.value.id}/${editingItem.value.id}`, payload)
      notifications.notifySuccess('Запись обновлена')
    } else {
      await api.post(`/api/dictionaries/${selectedDict.value.id}`, payload)
      notifications.notifySuccess('Запись добавлена')
    }
    showAddDialog.value = false
    await loadItems(selectedDict.value)
  } catch (e) {
    notifications.notifyError(`Ошибка сохранения: ${e.response?.data?.detail || e.message}`)
  } finally {
    saving.value = false
  }
}

function confirmDelete(item) {
  deletingItem.value = item
  showDeleteDialog.value = true
}

async function deleteItem() {
  if (!deletingItem.value) return
  deleting.value = true
  try {
    await api.delete(`/api/dictionaries/${selectedDict.value.id}/${deletingItem.value.id}`)
    notifications.notifySuccess(`«${deletingItem.value.name}» удалено`)
    showDeleteDialog.value = false
    await loadItems(selectedDict.value)
  } catch (e) {
    notifications.notifyError(`Ошибка удаления: ${e.response?.data?.detail || e.message}`)
  } finally {
    deleting.value = false
    deletingItem.value = null
  }
}
</script>

<style scoped>
.v-list-item {
  cursor: pointer;
}
</style>
