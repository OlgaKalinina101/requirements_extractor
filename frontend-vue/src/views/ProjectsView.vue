<template>
  <div>
    <v-row class="mb-4" align="center">
      <v-col>
        <h1 class="text-h4">Проекты</h1>
      </v-col>
      <v-col cols="auto">
        <v-btn v-if="auth.isManager" color="primary" @click="showCreateDialog = true" prepend-icon="mdi-plus">
          Новый проект
        </v-btn>
      </v-col>
    </v-row>

    <v-row v-if="projectsStore.loading">
      <v-col cols="12" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" size="48"></v-progress-circular>
      </v-col>
    </v-row>

    <v-row v-else-if="projectsStore.projects.length === 0">
      <v-col cols="12">
        <v-card class="text-center py-12" variant="outlined">
          <v-icon size="64" color="grey-lighten-1" class="mb-4">mdi-folder-open-outline</v-icon>
          <div class="text-h6 text-medium-emphasis">Нет проектов</div>
          <div class="text-body-2 text-medium-emphasis mb-4">
            Создайте проект, чтобы начать работу с документами
          </div>
          <v-btn color="primary" @click="showCreateDialog = true" prepend-icon="mdi-plus">
            Создать первый проект
          </v-btn>
        </v-card>
      </v-col>
    </v-row>

    <v-row v-else>
      <v-col
        v-for="project in projectsStore.projects"
        :key="project.id"
        cols="12"
        md="6"
        lg="4"
      >
        <v-card
          hover
          @click="goToProject(project.id)"
          class="project-card"
        >
          <v-card-title class="d-flex align-center">
            <v-icon left color="primary" class="mr-2">mdi-folder</v-icon>
            {{ project.name }}
            <v-spacer />
            <v-chip
              :color="project.status === 'active' ? 'green' : 'grey'"
              size="small"
              variant="tonal"
            >
              {{ project.status === 'active' ? 'Активный' : project.status }}
            </v-chip>
          </v-card-title>

          <v-card-subtitle v-if="project.code" class="mt-1">
            Код: {{ project.code }}
          </v-card-subtitle>

          <v-card-text>
            <div v-if="project.description" class="text-body-2 mb-3 description-text">
              {{ project.description }}
            </div>
            <v-row dense>
              <v-col cols="6">
                <div class="text-caption text-medium-emphasis">Документов</div>
                <div class="text-h6">{{ project.documents_count || 0 }}</div>
              </v-col>
              <v-col cols="6">
                <div class="text-caption text-medium-emphasis">Требований</div>
                <div class="text-h6">{{ project.requirements_count || 0 }}</div>
              </v-col>
            </v-row>
          </v-card-text>

          <v-card-actions>
            <v-btn size="small" variant="text" color="grey" @click.stop="confirmDelete(project)">
              <v-icon size="small">mdi-delete</v-icon>
            </v-btn>
            <v-spacer />
            <span class="text-caption text-medium-emphasis">
              {{ formatDate(project.created_at) }}
            </span>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Create project dialog -->
    <v-dialog v-model="showCreateDialog" max-width="500">
      <v-card>
        <v-card-title>Новый проект</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="newProject.name"
            label="Название проекта *"
            placeholder="Например: КС Пермская"
            :rules="[v => !!v || 'Обязательное поле']"
          />
          <v-text-field
            v-model="newProject.code"
            label="Код проекта"
            placeholder="Например: KS-PERM-2026"
            hint="Уникальный идентификатор (необязательно)"
            persistent-hint
            class="mt-2"
          />
          <v-textarea
            v-model="newProject.description"
            label="Описание"
            rows="3"
            class="mt-2"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showCreateDialog = false">Отмена</v-btn>
          <v-btn
            color="primary"
            :disabled="!newProject.name"
            :loading="creating"
            @click="createProject"
          >
            Создать
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete confirm -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title>Удалить проект?</v-card-title>
        <v-card-text>
          Проект <strong>{{ projectToDelete?.name }}</strong> и все его документы
          будут удалены безвозвратно.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDeleteDialog = false">Отмена</v-btn>
          <v-btn color="error" @click="doDelete">Удалить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '../stores/projects'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const projectsStore = useProjectsStore()
const auth = useAuthStore()

const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const projectToDelete = ref(null)
const creating = ref(false)
const newProject = ref({ name: '', code: '', description: '' })

const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleDateString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric'
  })
}

const goToProject = (id) => {
  router.push(`/projects/${id}`)
}

const createProject = async () => {
  creating.value = true
  try {
    const created = await projectsStore.createProject(
      newProject.value.name,
      newProject.value.code || null,
      newProject.value.description || null
    )
    showCreateDialog.value = false
    newProject.value = { name: '', code: '', description: '' }
    router.push(`/projects/${created.id}`)
  } catch (e) {
    alert(projectsStore.error || 'Ошибка создания проекта')
  } finally {
    creating.value = false
  }
}

const confirmDelete = (project) => {
  projectToDelete.value = project
  showDeleteDialog.value = true
}

const doDelete = async () => {
  if (!projectToDelete.value) return
  try {
    await projectsStore.deleteProject(projectToDelete.value.id)
  } catch (e) {
    alert('Ошибка удаления')
  }
  showDeleteDialog.value = false
  projectToDelete.value = null
}

onMounted(() => {
  projectsStore.fetchProjects()
})
</script>

<style scoped>
.project-card {
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}
.project-card:hover {
  transform: translateY(-2px);
}
.description-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
