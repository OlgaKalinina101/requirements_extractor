<template>
  <div>
    <h1 class="text-h4 mb-2">
      <v-icon left color="primary" class="mr-3">mdi-text-box-outline</v-icon>
      Промпты извлечения
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">
      Системные промпты для парсинга требований. Текст инструкции и шаблон пользователя доступны для редактирования.
      Формат ответа (JSON-схема) защищён от изменений.
    </p>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <div v-if="!loading && prompts.length === 0" class="text-center text-medium-emphasis py-10">
      <v-icon size="48" class="mb-2">mdi-text-box-remove-outline</v-icon>
      <div>Промпты не найдены</div>
    </div>

    <div v-else class="prompts-grid">
      <v-card
        v-for="p in editStates"
        :key="p.id"
        class="prompt-card"
        variant="outlined"
      >
        <!-- Header -->
        <v-card-title class="prompt-card__title">
          <v-icon :icon="promptIcon(p.id)" size="20" class="mr-2" :color="promptColor(p.id)" />
          {{ p.name }}
          <v-chip size="x-small" class="ml-2" variant="tonal" color="grey">
            v{{ p.version }}
          </v-chip>
          <v-spacer />
          <span v-if="p.temperature != null" class="text-caption text-medium-emphasis mr-3">
            temp: {{ p.temperature }}
          </span>
          <span v-if="p.max_tokens" class="text-caption text-medium-emphasis mr-4">
            max_tokens: {{ p.max_tokens }}
          </span>
          <v-btn
            size="small"
            variant="tonal"
            color="warning"
            :loading="p.resetting"
            class="mr-2"
            @click="resetPrompt(p)"
          >
            <v-icon size="16" class="mr-1">mdi-restore</v-icon>
            Сбросить
          </v-btn>
          <v-btn
            size="small"
            variant="flat"
            color="primary"
            :loading="p.saving"
            :disabled="!p.dirty"
            @click="savePrompt(p)"
          >
            <v-icon size="16" class="mr-1">mdi-content-save</v-icon>
            Сохранить
          </v-btn>
        </v-card-title>

        <v-divider />

        <v-card-text class="prompt-card__body">
          <!-- Instruction — editable -->
          <div class="prompt-section mb-5">
            <div class="prompt-section__label">
              <v-icon size="14">mdi-robot</v-icon>
              Инструкция (редактируемая)
            </div>
            <v-textarea
              v-model="p.instruction"
              variant="outlined"
              density="compact"
              auto-grow
              rows="6"
              hide-details
              class="prompt-textarea"
              @update:model-value="p.dirty = true"
            />
          </div>

          <!-- Response format — read-only -->
          <div class="prompt-section mb-5">
            <div class="prompt-section__label">
              <v-icon size="14">mdi-lock-outline</v-icon>
              Формат ответа (только просмотр)
              <v-chip size="x-small" variant="tonal" color="grey" class="ml-2">read-only</v-chip>
            </div>
            <pre class="prompt-section__content prompt-section__content--readonly">{{ p.response_format }}</pre>
          </div>

          <v-divider class="my-4" />

          <!-- User template — editable -->
          <div class="prompt-section">
            <div class="prompt-section__label">
              <v-icon size="14">mdi-account</v-icon>
              Шаблон пользователя (редактируемый, с переменными)
            </div>
            <v-textarea
              v-model="p.user_template"
              variant="outlined"
              density="compact"
              auto-grow
              rows="4"
              hide-details
              class="prompt-textarea"
              @update:model-value="p.dirty = true"
            />
          </div>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { promptsApi } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'

const notifications = useNotificationsStore()
const loading = ref(true)
const prompts = ref([])
const editStates = ref([])

const promptIcon = (id) => {
  if (id.includes('image')) return 'mdi-image-text'
  return 'mdi-text'
}

const promptColor = (id) => {
  if (id.includes('image')) return 'purple'
  return 'blue'
}

function buildEditState(p) {
  return {
    id: p.id,
    name: p.name,
    version: p.version,
    temperature: p.temperature,
    max_tokens: p.max_tokens,
    instruction: p.instruction,
    response_format: p.response_format,
    user_template: p.user_template,
    dirty: false,
    saving: false,
    resetting: false,
  }
}

async function savePrompt(p) {
  p.saving = true
  try {
    await promptsApi.update(p.id, {
      instruction: p.instruction,
      user_template: p.user_template,
    })
    p.dirty = false
    notifications.notifySuccess('Промпт сохранён')
  } catch {
    notifications.notifyError('Не удалось сохранить промпт')
  } finally {
    p.saving = false
  }
}

async function resetPrompt(p) {
  p.resetting = true
  try {
    await promptsApi.reset(p.id)
    const res = await promptsApi.getAll()
    const fresh = (res.data?.prompts ?? []).find((x) => x.id === p.id)
    if (fresh) {
      p.instruction = fresh.instruction
      p.user_template = fresh.user_template
      p.dirty = false
    }
    notifications.notifySuccess('Промпт сброшен к значениям по умолчанию')
  } catch {
    notifications.notifyError('Не удалось сбросить промпт')
  } finally {
    p.resetting = false
  }
}

onMounted(async () => {
  try {
    const res = await promptsApi.getAll()
    prompts.value = res.data?.prompts ?? []
    editStates.value = prompts.value.map(buildEditState)
  } catch {
    notifications.notifyError('Не удалось загрузить промпты')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.prompts-grid {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.prompt-card {
  border-radius: 12px;
  overflow: hidden;
}

.prompt-card__title {
  font-size: 16px !important;
  font-weight: 600;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.prompt-card__body {
  padding: 20px !important;
}

.prompt-section__label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: #666;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.prompt-textarea :deep(textarea) {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.prompt-section__content {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  padding: 14px 16px;
  border-radius: 8px;
  color: #212529;
  max-height: 360px;
  overflow-y: auto;
}

.prompt-section__content--readonly {
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  cursor: not-allowed;
  opacity: 0.85;
}

.prompt-section__content::-webkit-scrollbar {
  width: 8px;
}

.prompt-section__content::-webkit-scrollbar-track {
  background: #f1f3f5;
  border-radius: 4px;
}

.prompt-section__content::-webkit-scrollbar-thumb {
  background: #adb5bd;
  border-radius: 4px;
}

.prompt-section__content::-webkit-scrollbar-thumb:hover {
  background: #868e96;
}
</style>
