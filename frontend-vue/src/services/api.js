import axios from 'axios'

// Use relative URLs to leverage Vite's proxy configuration
// This ensures all requests go through the dev server (localhost:3000)
// which then proxies them to the API server (localhost:8000)
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Projects API
export const projectsApi = {
  getAll: () => api.get('/api/projects'),
  getById: (id) => api.get(`/api/projects/${id}`),
  create: (name, code = null, description = null) => {
    const formData = new FormData()
    formData.append('name', name)
    if (code) formData.append('code', code)
    if (description) formData.append('description', description)
    return api.post('/api/projects', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  update: (id, data) => {
    const formData = new FormData()
    Object.entries(data).forEach(([key, value]) => {
      if (value !== null && value !== undefined) formData.append(key, value)
    })
    return api.put(`/api/projects/${id}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  delete: (id) => api.delete(`/api/projects/${id}`),
}

// Documents API
export const documentsApi = {
  getAll: (projectId = null) => {
    const params = projectId ? { project_id: projectId } : {}
    return api.get('/api/documents', { params })
  },
  
  getById: (id) => api.get(`/api/documents/${id}`),
  
  uploadAndExtract: (file, model = 'claude-sonnet-4.5', generateWord = true, projectId = null) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('model', model)
    formData.append('generate_word', generateWord)
    if (projectId) formData.append('project_id', projectId)
    return api.post('/api/extract', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  getRequirements: (documentId, params = {}) => {
    return api.get(`/api/documents/${documentId}/requirements`, { params })
  },
  
  getMetrics: (documentId) => {
    return api.get(`/api/documents/${documentId}/metrics`)
  }
}

// Requirements API
export const requirementsApi = {
  // Get requirement by ID
  getById: (id) => api.get(`/api/requirements/${id}`),
  
  // Accept requirement
  accept: (id) => api.post(`/api/requirements/${id}/accept`),
  
  // Reject requirement
  reject: (id, reason = null) => {
    return api.post(`/api/requirements/${id}/reject`, reason ? { reason } : {})
  },
  
  // Edit requirement
  edit: (id, editedText, reason = null, editedBy = null) => {
    return api.post(`/api/requirements/${id}/edit`, {
      edited_text: editedText,
      reason,
      edited_by: editedBy
    })
  }
}

// WebSocket connection for real-time updates
// Use relative WebSocket URL to connect through the same host
export const createWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host // Will be localhost:3000 in dev
  const wsUrl = `${protocol}//${host}/ws/logs`
  return new WebSocket(wsUrl)
}

export default api
