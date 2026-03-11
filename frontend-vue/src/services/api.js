import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// On 401 — clear token and redirect to /login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Avoid redirect loop on the login page itself
      if (!window.location.pathname.startsWith('/login')) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`
      }
    }
    return Promise.reject(error)
  }
)

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
  
  getRequirements: (documentId, params = {}) =>
    api.get(`/api/documents/${documentId}/requirements`, { params }),
  
  getMetrics: (documentId) => {
    return api.get(`/api/documents/${documentId}/metrics`)
  }
}

// Requirements API
export const requirementsApi = {
  getById: (id) => api.get(`/api/requirements/${id}`),
  accept: (id) => api.post(`/api/requirements/${id}/accept`),
  reject: (id, reason = null) => api.post(`/api/requirements/${id}/reject`, reason ? { reason } : {}),
  edit: (id, editedText, reason = null, editedBy = null) =>
    api.post(`/api/requirements/${id}/edit`, { edited_text: editedText, reason, edited_by: editedBy }),
  assign: (id, assigneeId) =>
    api.post(`/api/requirements/${id}/assign`, { assignee_id: assigneeId }),
  setStatus: (id, status) =>
    api.post(`/api/requirements/${id}/set-status`, { status }),
  getComments: (id) => api.get(`/api/requirements/${id}/comments`),
  addComment: (id, text) => api.post(`/api/requirements/${id}/comments`, { text }),
  deleteComment: (commentId) => api.delete(`/api/comments/${commentId}`),
}

// Auth API
export const authApi = {
  login: (email, password) => api.post('/api/auth/login', { email, password }),
  me: () => api.get('/api/auth/me'),
}

// Users API (admin)
export const usersApi = {
  getAll: () => api.get('/api/users'),
  create: (data) => api.post('/api/users', data),
  update: (id, data) => api.put(`/api/users/${id}`, data),
  deactivate: (id) => api.delete(`/api/users/${id}`),
}

// Export URLs (use as href for download links)
export const exportUrls = {
  word: (documentId) => `${API_BASE_URL}/api/documents/${documentId}/export/word`,
  json: (documentId) => `${API_BASE_URL}/api/documents/${documentId}/export/json`,
  txt: (documentId) => `${API_BASE_URL}/api/documents/${documentId}/export/txt`,
  pdf: (documentId) => `${API_BASE_URL}/api/documents/${documentId}/pdf`,
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
