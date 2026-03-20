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

// On 401 — clear token and redirect to /login (unless skipAuthRedirect)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const skipRedirect = error.config?.skipAuthRedirect === true
      if (!skipRedirect && !window.location.pathname.startsWith('/login')) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`
      }
    }
    return Promise.reject(error)
  }
)

// Dashboard API (manager)
export const dashboardApi = {
  getStats: (params = {}) => api.get('/api/dashboard', { params }),
  getActivity: (params = {}) => api.get('/api/dashboard/activity', { params }),
}

// Projects API
export const projectsApi = {
  getAll: (params = {}) => api.get('/api/projects', { params }),
  getById: (id) => api.get(`/api/projects/${id}`),
  create: (name, code = null, description = null, requirement_manager_id = null) => {
    const formData = new FormData()
    formData.append('name', name)
    if (code) formData.append('code', code)
    if (description) formData.append('description', description)
    if (requirement_manager_id != null && requirement_manager_id !== '') formData.append('requirement_manager_id', requirement_manager_id)
    return api.post('/api/projects', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  update: (id, data) => {
    const formData = new FormData()
    Object.entries(data).forEach(([key, value]) => {
      if (value !== null && value !== undefined) formData.append(key, value)
      else if (key === 'requirement_manager_id') formData.append(key, 0)  // 0 = clear
    })
    return api.put(`/api/projects/${id}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  delete: (id) => api.delete(`/api/projects/${id}`),
}

// Documents API
export const documentsApi = {
  getAll: (projectId = null, options = {}) => {
    const params = projectId ? { project_id: projectId } : {}
    return api.get('/api/documents', { params, ...options })
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

  createRequirement: (documentId, data) =>
    api.post(`/api/documents/${documentId}/requirements`, data),

  getMetrics: (documentId) => {
    return api.get(`/api/documents/${documentId}/metrics`)
  }
}

// Requirements API
export const requirementsApi = {
  getAll: (params = {}) => api.get('/api/requirements', { params }),
  delete: (id) => api.delete(`/api/requirements/${id}`),
  getById: (id) => api.get(`/api/requirements/${id}`),
  accept: (id) => api.post(`/api/requirements/${id}/accept`),
  reject: (id, reason = null) => api.post(`/api/requirements/${id}/reject`, reason ? { reason } : {}),
  edit: (id, editedText, reason = null, editedBy = null, type = null, priority = null, discipline = null, verification_method = null, deadline = null) =>
    api.post(`/api/requirements/${id}/edit`, { edited_text: editedText, reason, edited_by: editedBy, type, priority, discipline, verification_method, deadline }),
  assign: (id, assigneeId) =>
    api.post(`/api/requirements/${id}/assign`, { assignee_id: assigneeId }),
  setStatus: (id, status) =>
    api.post(`/api/requirements/${id}/set-status`, { status }),
  getComments: (id) => api.get(`/api/requirements/${id}/comments`),
  getHistory: (id) => api.get(`/api/requirements/${id}/history`),
  addComment: (id, text) => api.post(`/api/requirements/${id}/comments`, { text }),
  deleteComment: (commentId) => api.delete(`/api/comments/${commentId}`),
  createLink: (requirementId, targetRequirementId, linkType) =>
    api.post(`/api/requirements/${requirementId}/links`, { target_requirement_id: targetRequirementId, link_type: linkType }),
  deleteLink: (requirementId, linkId) =>
    api.delete(`/api/requirements/${requirementId}/links/${linkId}`),
}

// Auth API
export const authApi = {
  login: (email, password) => api.post('/api/auth/login', { email, password }),
  me: () => api.get('/api/auth/me'),
}

// Prompts API (admin)
export const promptsApi = {
  getAll: () => api.get('/api/prompts'),
  update: (key, data) => api.put(`/api/prompts/${key}`, data),
  reset: (key) => api.post(`/api/prompts/${key}/reset`),
}

// Users API (admin)
export const usersApi = {
  getAll: () => api.get('/api/users'),
  create: (data) => api.post('/api/users', data),
  update: (id, data) => api.put(`/api/users/${id}`, data),
  deactivate: (id) => api.delete(`/api/users/${id}`),
}

// Export URL builders
export const exportUrls = {
  word: (documentId) => `/api/documents/${documentId}/export/word`,
  json: (documentId) => `/api/documents/${documentId}/export/json`,
  txt:  (documentId) => `/api/documents/${documentId}/export/txt`,
  xlsx: (documentId) => `/api/documents/${documentId}/export/xlsx`,
  pdf:  (documentId) => `/api/documents/${documentId}/pdf`,
}

// Download export file via axios (carries Authorization header, avoids 401)
export async function downloadExport(documentId, format) {
  const url = exportUrls[format]?.(documentId)
  if (!url) throw new Error(`Unknown export format: ${format}`)

  const mimeTypes = {
    word: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    json: 'application/json',
    txt:  'text/plain',
  }
  const extensions = { word: 'docx', xlsx: 'xlsx', json: 'json', txt: 'txt' }

  const response = await api.get(url, { responseType: 'blob' })

  const contentDisposition = response.headers['content-disposition'] || ''
  let filename = contentDisposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';\n]+)/i)?.[1]
    || `requirements_${documentId}.${extensions[format] || format}`

  const blob = new Blob([response.data], { type: mimeTypes[format] || 'application/octet-stream' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = decodeURIComponent(filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
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
