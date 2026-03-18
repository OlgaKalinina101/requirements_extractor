<template>
  <div>
    <h1 class="text-h4 mb-4">
      <v-icon left color="primary" class="mr-3">mdi-text-box-outline</v-icon>
      Промпты извлечения
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-4">
      Системные промпты для парсинга требований из текста и изображений. Только просмотр.
    </p>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <div v-if="!loading && prompts.length === 0" class="text-center text-medium-emphasis py-10">
      <v-icon size="48" class="mb-2">mdi-text-box-remove-outline</v-icon>
      <div>Промпты не найдены</div>
    </div>

    <div v-else class="prompts-grid">
      <v-card
        v-for="p in prompts"
        :key="p.id"
        class="prompt-card"
        variant="outlined"
      >
        <v-card-title class="prompt-card__title">
          <v-icon :icon="promptIcon(p.id)" size="20" class="mr-2" :color="promptColor(p.id)" />
          {{ p.name }}
          <v-chip size="x-small" class="ml-2" variant="tonal" color="grey">
            v{{ p.version }}
          </v-chip>
          <v-spacer />
          <span v-if="p.temperature != null" class="text-caption text-medium-emphasis mr-2">
            temp: {{ p.temperature }}
          </span>
          <span v-if="p.max_tokens" class="text-caption text-medium-emphasis">
            max_tokens: {{ p.max_tokens }}
          </span>
        </v-card-title>

        <v-divider />

        <v-card-text class="prompt-card__body">
          <div class="prompt-section">
            <div class="prompt-section__label">
              <v-icon size="14">mdi-robot</v-icon>
              System prompt
            </div>
            <pre class="prompt-section__content">{{ p.system }}</pre>
          </div>

          <v-divider class="my-4" />

          <div class="prompt-section">
            <div class="prompt-section__label">
              <v-icon size="14">mdi-account</v-icon>
              User template (с переменными)
            </div>
            <pre class="prompt-section__content">{{ p.user_template }}</pre>
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

const promptIcon = (id) => {
  if (id.includes('image')) return 'mdi-image-text'
  return 'mdi-text'
}

const promptColor = (id) => {
  if (id.includes('image')) return 'purple'
  return 'blue'
}

onMounted(async () => {
  try {
    const res = await promptsApi.getAll()
    prompts.value = res.data?.prompts ?? []
  } catch (err) {
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
}

.prompt-card__body {
  padding: 20px !important;
}

.prompt-section {
  margin-bottom: 0;
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

.prompt-section__content {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  color: #212529;
  max-height: 420px;
  overflow-y: auto;
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
