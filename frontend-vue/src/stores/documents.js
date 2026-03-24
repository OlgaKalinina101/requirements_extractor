import { defineStore } from 'pinia'
import { ref } from 'vue'
import { documentsApi } from '@/services/api'

export const useDocumentsStore = defineStore('documents', () => {
  const documents        = ref([])
  const currentDocument  = ref(null)
  const loading          = ref(false)
  const error            = ref(null)

  async function fetchDocuments(projectId = null) {
    loading.value = true
    error.value   = null
    try {
      const { data } = await documentsApi.getAll(projectId)
      documents.value = data.documents || []
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchDocument(id) {
    loading.value = true
    error.value   = null
    try {
      const { data } = await documentsApi.getById(id)
      currentDocument.value = data
      return data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function uploadDocument(file, model = 'claude-sonnet-4.5', generateWord = true, projectId = null) {
    loading.value = true
    error.value   = null
    try {
      const { data } = await documentsApi.uploadAndExtract(file, model, generateWord, projectId)
      // Best-effort refresh — don't break on auth expiry
      try {
        const docsRes = await documentsApi.getAll(projectId, { skipAuthRedirect: true })
        documents.value = docsRes.data.documents || []
      } catch {
        // ignore
      }
      return data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return { documents, currentDocument, loading, error, fetchDocuments, fetchDocument, uploadDocument }
})
