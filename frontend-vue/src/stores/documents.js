import { defineStore } from 'pinia'
import { documentsApi } from '../services/api'

export const useDocumentsStore = defineStore('documents', {
  state: () => ({
    documents: [],
    currentDocument: null,
    loading: false,
    error: null
  }),

  actions: {
    async fetchDocuments(projectId = null) {
      this.loading = true
      this.error = null
      try {
        const response = await documentsApi.getAll(projectId)
        this.documents = response.data.documents || []
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    async fetchDocument(id) {
      this.loading = true
      this.error = null
      try {
        const response = await documentsApi.getById(id)
        this.currentDocument = response.data
        return response.data
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async uploadDocument(file, model = 'claude-sonnet-4.5', generateWord = true, projectId = null) {
      this.loading = true
      this.error = null
      try {
        const response = await documentsApi.uploadAndExtract(file, model, generateWord, projectId)
        await this.fetchDocuments(projectId)
        return response.data
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})
