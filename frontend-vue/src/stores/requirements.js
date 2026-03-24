import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { documentsApi, requirementsApi } from '@/services/api'

export const useRequirementsStore = defineStore('requirements', () => {
  const requirements      = ref([])
  const currentRequirement = ref(null)
  const filters = ref({
    status:     null,
    type:       null,
    discipline: null,
  })
  const loading = ref(false)
  const error   = ref(null)

  // ── Getters ───────────────────────────────────────────────────────────────

  const filteredRequirements = computed(() => {
    let list = requirements.value
    if (filters.value.status)     list = list.filter(r => r.status     === filters.value.status)
    if (filters.value.type)       list = list.filter(r => r.type       === filters.value.type)
    if (filters.value.discipline) list = list.filter(r => r.discipline === filters.value.discipline)
    return list
  })

  const stats = computed(() => {
    const s = { total: requirements.value.length, pending: 0, accepted: 0, rejected: 0, modified: 0 }
    requirements.value.forEach(r => { if (r.status in s) s[r.status]++ })
    return s
  })

  // ── Actions ───────────────────────────────────────────────────────────────

  async function fetchRequirements(documentId, params = {}) {
    loading.value = true
    error.value   = null
    try {
      const { data } = await documentsApi.getRequirements(documentId, params)
      requirements.value = data.requirements || []
      return requirements.value
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchRequirement(id) {
    loading.value = true
    error.value   = null
    try {
      const { data } = await requirementsApi.getById(id)
      currentRequirement.value = data
      return data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchAllRequirements(params = {}) {
    loading.value = true
    error.value   = null
    try {
      const { data } = await requirementsApi.getAll(params)
      requirements.value = data.requirements || []
      return requirements.value
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function acceptRequirement(id) {
    error.value = null
    try {
      await requirementsApi.accept(id)
      const req = requirements.value.find(r => r.id === id)
      if (req) req.status = 'accepted'
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function rejectRequirement(id, reason = null) {
    error.value = null
    try {
      await requirementsApi.reject(id, reason)
      const req = requirements.value.find(r => r.id === id)
      if (req) { req.status = 'rejected'; req.edit_reason = reason }
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function editRequirement(id, editedText, reason = null, editedBy = null, type = null, priority = null, discipline = null, verification_method = null, deadline = null) {
    error.value = null
    try {
      const { data } = await requirementsApi.edit(id, editedText, reason, editedBy, type, priority, discipline, verification_method, deadline)
      const req = requirements.value.find(r => r.id === id)
      if (req) {
        req.text               = editedText
        req.status             = 'modified'
        req.human_edited       = editedText
        req.edit_reason        = reason
        req.edited_by          = editedBy
        req.edited_at          = data.edited_at
        if (type !== null)                req.type                = type
        if (priority !== null)            req.priority            = priority
        if (discipline !== undefined)     req.discipline          = discipline
        if (verification_method !== undefined) req.verification_method = verification_method
        if (deadline !== undefined)       req.deadline            = deadline
      }
      return data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function createRequirement(documentId, payload) {
    error.value = null
    try {
      const { data } = await documentsApi.createRequirement(documentId, payload)
      await fetchRequirements(documentId)
      return data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function deleteRequirement(id) {
    error.value = null
    try {
      await requirementsApi.delete(id)
      requirements.value = requirements.value.filter(r => r.id !== id)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  function setFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters }
  }

  return {
    requirements, currentRequirement, filters, loading, error,
    filteredRequirements, stats,
    fetchRequirements, fetchRequirement, fetchAllRequirements,
    acceptRequirement, rejectRequirement, editRequirement,
    createRequirement, deleteRequirement,
    setFilters,
  }
})
