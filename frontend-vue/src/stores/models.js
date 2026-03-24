import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'
import { AVAILABLE_MODELS } from '@/utils/constants'

export const useModelsStore = defineStore('models', () => {
  const models = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchModels() {
    if (models.value.length > 0) return models.value
    loading.value = true
    error.value = null
    try {
      const res = await api.get('/api/models')
      models.value = res.data ?? []
      return models.value
    } catch (e) {
      error.value = e?.message || 'Failed to load models'
      models.value = []
      return []
    } finally {
      loading.value = false
    }
  }

  /** Models for selection (from API or fallback to constants) */
  const availableModels = computed(() => {
    if (models.value.length > 0) return models.value
    return AVAILABLE_MODELS
  })

  return {
    models,
    loading,
    error,
    fetchModels,
    availableModels,
  }
})
