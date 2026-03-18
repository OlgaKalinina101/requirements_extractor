<template>
  <v-container>
    <div class="d-flex align-center justify-space-between mb-6">
      <h1 class="text-h5">Управление пользователями</h1>
      <v-btn color="primary" prepend-icon="mdi-account-plus" @click="openCreate">
        Добавить пользователя
      </v-btn>
    </div>

    <v-card>
      <v-data-table
        :headers="headers"
        :items="users"
        :loading="loading"
        item-value="id"
        hover
      >
        <template #item.role="{ item }">
          <v-chip :color="roleColor(item.role)" size="small" variant="tonal">
            {{ roleName(item.role) }}
          </v-chip>
        </template>
        <template #item.is_active="{ item }">
          <v-icon :color="item.is_active ? 'success' : 'error'">
            {{ item.is_active ? 'mdi-check-circle' : 'mdi-close-circle' }}
          </v-icon>
        </template>
        <template #item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>
        <template #item.actions="{ item }">
          <v-btn icon size="small" variant="text" @click="openEdit(item)">
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
          <v-btn
            v-if="item.id !== auth.user?.id"
            icon
            size="small"
            variant="text"
            :color="item.is_active ? 'error' : 'success'"
            @click="toggleActive(item)"
          >
            <v-icon>{{ item.is_active ? 'mdi-account-off' : 'mdi-account-check' }}</v-icon>
          </v-btn>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create / Edit dialog -->
    <v-dialog v-model="dialog" max-width="480" persistent>
      <v-card>
        <v-card-title>{{ editingUser ? 'Редактировать пользователя' : 'Новый пользователь' }}</v-card-title>
        <v-card-text>
          <v-form ref="form">
            <v-text-field
              v-model="formData.email"
              label="Email"
              type="email"
              variant="outlined"
              :rules="[v => !!v || 'Обязательное поле']"
              :disabled="!!editingUser"
              class="mb-3"
            />
            <v-text-field
              v-model="formData.full_name"
              label="Полное имя"
              variant="outlined"
              class="mb-3"
            />
            <v-select
              v-model="formData.role"
              label="Роль"
              :items="roleOptions"
              item-title="label"
              item-value="value"
              variant="outlined"
              class="mb-3"
            />
            <v-text-field
              v-model="formData.password"
              :label="editingUser ? 'Новый пароль (оставьте пустым — без изменений)' : 'Пароль'"
              type="password"
              variant="outlined"
              :rules="editingUser ? [] : [v => !!v || 'Обязательное поле']"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Отмена</v-btn>
          <v-btn color="primary" :loading="saving" @click="save">Сохранить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usersApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'

const auth = useAuthStore()
const notifications = useNotificationsStore()

const users = ref([])
const loading = ref(false)
const dialog = ref(false)
const saving = ref(false)
const editingUser = ref(null)
const form = ref(null)

const formData = ref({ email: '', full_name: '', role: 'user', password: '' })

const headers = [
  { title: 'Email', key: 'email' },
  { title: 'Имя', key: 'full_name' },
  { title: 'Роль', key: 'role', sortable: false },
  { title: 'Активен', key: 'is_active', sortable: false },
  { title: 'Создан', key: 'created_at' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

const roleOptions = [
  { label: 'Администратор', value: 'admin' },
  { label: 'Менеджер требований', value: 'manager' },
  { label: 'Руководитель отдела по задачам', value: 'department_head' },
  { label: 'Пользователь (исполнитель)', value: 'user' },
]

function roleColor(role) {
  return role === 'admin' ? 'error' : role === 'manager' ? 'primary' : role === 'department_head' ? 'teal' : 'secondary'
}

function roleName(role) {
  return roleOptions.find(r => r.value === role)?.label || role
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('ru-RU')
}

async function loadUsers() {
  loading.value = true
  try {
    const { data } = await usersApi.getAll()
    users.value = data
  } catch {
    notifications.notifyError('Не удалось загрузить пользователей')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingUser.value = null
  formData.value = { email: '', full_name: '', role: 'user', password: '' }
  dialog.value = true
}

function openEdit(user) {
  editingUser.value = user
  formData.value = { email: user.email, full_name: user.full_name || '', role: user.role, password: '' }
  dialog.value = true
}

async function save() {
  const { valid } = await form.value.validate()
  if (!valid) return

  saving.value = true
  try {
    if (editingUser.value) {
      const payload = { full_name: formData.value.full_name, role: formData.value.role }
      if (formData.value.password) payload.password = formData.value.password
      await usersApi.update(editingUser.value.id, payload)
      notifications.notifySuccess('Пользователь обновлён')
    } else {
      await usersApi.create(formData.value)
      notifications.notifySuccess('Пользователь создан')
    }
    dialog.value = false
    await loadUsers()
  } catch (e) {
    notifications.notifyError(e.response?.data?.detail || 'Ошибка сохранения')
  } finally {
    saving.value = false
  }
}

async function toggleActive(user) {
  try {
    if (user.is_active) {
      await usersApi.deactivate(user.id)
      notifications.notifyInfo(`${user.email} деактивирован`)
    } else {
      await usersApi.update(user.id, { is_active: true })
      notifications.notifySuccess(`${user.email} активирован`)
    }
    await loadUsers()
  } catch (e) {
    notifications.notifyError(e.response?.data?.detail || 'Ошибка')
  }
}

onMounted(loadUsers)
</script>
