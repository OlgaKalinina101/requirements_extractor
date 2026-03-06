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
              <template v-slot:prepend>
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
            <v-spacer></v-spacer>
            <v-btn color="primary" prepend-icon="mdi-plus" @click="showAddDialog = true">
              Добавить
            </v-btn>
          </v-card-title>

          <v-card-text>
            <v-data-table
              :headers="tableHeaders"
              :items="getCurrentItems()"
              :items-per-page="10"
              class="elevation-0"
            >
              <template v-slot:item.color="{ item }">
                <v-chip :color="item.color" size="small" v-if="item.color">
                  {{ item.name }}
                </v-chip>
                <span v-else>{{ item.name }}</span>
              </template>

              <template v-slot:item.active="{ item }">
                <v-chip :color="item.active ? 'green' : 'grey'" size="small">
                  {{ item.active ? 'Активно' : 'Неактивно' }}
                </v-chip>
              </template>

              <template v-slot:item.actions="{ item }">
                <v-btn icon size="small" variant="text" @click="editItem(item)">
                  <v-icon>mdi-pencil</v-icon>
                </v-btn>
                <v-btn icon size="small" variant="text" color="error" @click="deleteItem(item)">
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
          {{ editingItem ? 'Редактировать' : 'Добавить' }} запись
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="formData.name"
            label="Название"
            variant="outlined"
            class="mb-3"
          ></v-text-field>

          <v-text-field
            v-if="selectedDict?.id === 'requirement_types' || selectedDict?.id === 'priorities'"
            v-model="formData.code"
            label="Код"
            variant="outlined"
            class="mb-3"
          ></v-text-field>

          <v-textarea
            v-model="formData.description"
            label="Описание"
            variant="outlined"
            rows="3"
            class="mb-3"
          ></v-textarea>

          <v-select
            v-if="selectedDict?.id === 'priorities'"
            v-model="formData.color"
            :items="['red', 'orange', 'blue', 'grey']"
            label="Цвет"
            variant="outlined"
            class="mb-3"
          ></v-select>

          <v-checkbox
            v-model="formData.active"
            label="Активно"
          ></v-checkbox>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showAddDialog = false">Отмена</v-btn>
          <v-btn color="primary" @click="saveItem">Сохранить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'

const dictionaries = ref([
  {
    id: 'requirement_types',
    title: 'Типы требований',
    icon: 'mdi-shape',
    color: 'blue',
    count: 5
  },
  {
    id: 'priorities',
    title: 'Приоритеты',
    icon: 'mdi-flag',
    color: 'orange',
    count: 4
  },
  {
    id: 'statuses',
    title: 'Статусы жизненного цикла',
    icon: 'mdi-traffic-light',
    color: 'green',
    count: 6
  },
  {
    id: 'users',
    title: 'Пользователи',
    icon: 'mdi-account-group',
    color: 'pink',
    count: 12
  }
])

// Mock data
const mockData = {
  requirement_types: [
    { id: 1, name: 'Functional', code: 'FUNC', description: 'Функциональное требование', active: true },
    { id: 2, name: 'Non-Functional', code: 'NFUNC', description: 'Нефункциональное требование', active: true },
    { id: 3, name: 'Technical', code: 'TECH', description: 'Техническое требование', active: true },
    { id: 4, name: 'Performance', code: 'PERF', description: 'Требование к производительности', active: true },
    { id: 5, name: 'Safety', code: 'SAFE', description: 'Требование безопасности', active: true }
  ],
  priorities: [
    { id: 1, name: 'Critical', code: 'CRIT', color: 'red', description: 'Критический приоритет', active: true },
    { id: 2, name: 'High', code: 'HIGH', color: 'orange', description: 'Высокий приоритет', active: true },
    { id: 3, name: 'Medium', code: 'MED', color: 'blue', description: 'Средний приоритет', active: true },
    { id: 4, name: 'Low', code: 'LOW', color: 'grey', description: 'Низкий приоритет', active: true }
  ],
  statuses: [
    { id: 1, name: 'Draft', description: 'Черновик', active: true },
    { id: 2, name: 'In Review', description: 'На проверке', active: true },
    { id: 3, name: 'Approved', description: 'Утверждено', active: true },
    { id: 4, name: 'Implemented', description: 'Реализовано', active: true },
    { id: 5, name: 'Verified', description: 'Проверено', active: true },
    { id: 6, name: 'Rejected', description: 'Отклонено', active: true }
  ],
  users: [
    { id: 1, name: 'Иванов Иван', email: 'ivanov@example.com', role: 'Менеджер требований', active: true },
    { id: 2, name: 'Петров Пётр', email: 'petrov@example.com', role: 'Пользователь', active: true },
    { id: 3, name: 'Сидоров Сидор', email: 'sidorov@example.com', role: 'Пользователь', active: true },
    { id: 4, name: 'Козлова Мария', email: 'kozlova@example.com', role: 'Менеджер требований', active: true },
    { id: 5, name: 'Смирнов Алексей', email: 'smirnov@example.com', role: 'Пользователь', active: true }
  ]
}

const selectedDict = ref(null)
const showAddDialog = ref(false)
const editingItem = ref(null)
const formData = ref({
  name: '',
  code: '',
  description: '',
  color: '',
  active: true
})

const tableHeaders = computed(() => {
  if (!selectedDict.value) return []
  
  const baseHeaders = [
    { title: 'Название', key: 'name', sortable: true },
    { title: 'Описание', key: 'description', sortable: false }
  ]

  if (selectedDict.value.id === 'requirement_types' || selectedDict.value.id === 'priorities') {
    baseHeaders.splice(1, 0, { title: 'Код', key: 'code', sortable: true })
  }

  if (selectedDict.value.id === 'priorities') {
    baseHeaders[0] = { title: 'Название', key: 'color', sortable: true }
  }

  if (selectedDict.value.id === 'users') {
    baseHeaders.splice(1, 0, { title: 'Email', key: 'email', sortable: true })
    baseHeaders.splice(2, 0, { title: 'Роль', key: 'role', sortable: true })
  }

  baseHeaders.push({ title: 'Статус', key: 'active', sortable: true })
  baseHeaders.push({ title: 'Действия', key: 'actions', sortable: false, align: 'end' })

  return baseHeaders
})

const selectDictionary = (dict) => {
  selectedDict.value = dict
}

const getCurrentItems = () => {
  if (!selectedDict.value) return []
  return mockData[selectedDict.value.id] || []
}

const notifications = useNotificationsStore()

const editItem = (item) => {
  editingItem.value = item
  formData.value = { ...item }
  showAddDialog.value = true
}

const deleteItem = (item) => {
  notifications.notifyInfo(`Удаление "${item.name}" временно недоступно`)
}

const saveItem = () => {
  notifications.notifyInfo('Редактирование справочников временно недоступно')
  showAddDialog.value = false
  formData.value = { name: '', code: '', description: '', color: '', active: true }
  editingItem.value = null
}
</script>

<style scoped>
.v-list-item {
  cursor: pointer;
}
</style>
