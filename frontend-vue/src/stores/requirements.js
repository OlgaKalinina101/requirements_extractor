import { defineStore } from 'pinia'
import { documentsApi, requirementsApi } from '../services/api'

export const useRequirementsStore = defineStore('requirements', {
  state: () => ({
    requirements: [],
    currentRequirement: null,
    filters: {
      status: null,
      type: null
    },
    loading: false,
    error: null
  }),

  getters: {
    filteredRequirements: (state) => {
      let filtered = state.requirements

      if (state.filters.status) {
        filtered = filtered.filter(r => r.status === state.filters.status)
      }

      if (state.filters.type) {
        filtered = filtered.filter(r => r.type === state.filters.type)
      }

      return filtered
    },

    stats: (state) => {
      const stats = {
        total: state.requirements.length,
        pending: 0,
        accepted: 0,
        rejected: 0,
        modified: 0
      }

      state.requirements.forEach(req => {
        if (req.status in stats) {
          stats[req.status]++
        }
      })

      return stats
    }
  },

  actions: {
    async fetchRequirements(documentId, filters = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await documentsApi.getRequirements(documentId, filters)
        this.requirements = response.data.requirements || []
        return this.requirements
      } catch (error) {
        this.error = error.message
        console.error('Failed to fetch requirements:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchRequirement(id) {
      this.loading = true
      this.error = null
      try {
        const response = await requirementsApi.getById(id)
        this.currentRequirement = response.data
        return response.data
      } catch (error) {
        this.error = error.message
        console.error('Failed to fetch requirement:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async acceptRequirement(id) {
      try {
        await requirementsApi.accept(id)
        // Update local state
        const req = this.requirements.find(r => r.id === id)
        if (req) {
          req.status = 'accepted'
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async rejectRequirement(id, reason = null) {
      try {
        await requirementsApi.reject(id, reason)
        // Update local state
        const req = this.requirements.find(r => r.id === id)
        if (req) {
          req.status = 'rejected'
          req.edit_reason = reason
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async editRequirement(id, editedText, reason = null, editedBy = null) {
      try {
        const response = await requirementsApi.edit(id, editedText, reason, editedBy)
        // Update local state
        const req = this.requirements.find(r => r.id === id)
        if (req) {
          req.text = editedText
          req.status = 'modified'
          req.human_edited = editedText
          req.edit_reason = reason
          req.edited_by = editedBy
          req.edited_at = response.data.edited_at
        }
        return response.data
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
    }
  }
})
