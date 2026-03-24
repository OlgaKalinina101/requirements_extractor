import { defineStore } from 'pinia'
import { ref } from 'vue'
import { projectsApi } from '@/services/api'

export const useProjectsStore = defineStore('projects', () => {
  const projects       = ref([])
  const currentProject = ref(null)
  const loading        = ref(false)
  const error          = ref(null)

  async function fetchProjects() {
    loading.value = true
    error.value   = null
    try {
      const { data } = await projectsApi.getAll()
      projects.value = data.projects || []
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id) {
    loading.value = true
    error.value   = null
    try {
      const { data } = await projectsApi.getById(id)
      currentProject.value = data
      return data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createProject(name, code = null, description = null, requirement_manager_id = null) {
    loading.value = true
    error.value   = null
    try {
      const { data } = await projectsApi.create(name, code, description, requirement_manager_id)
      await fetchProjects()
      return data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateProject(id, payload) {
    loading.value = true
    error.value   = null
    try {
      const { data } = await projectsApi.update(id, payload)
      if (currentProject.value?.id === id) {
        currentProject.value = { ...currentProject.value, ...data }
      }
      await fetchProjects()
      return data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteProject(id) {
    error.value = null
    try {
      await projectsApi.delete(id)
      await fetchProjects()
      if (currentProject.value?.id === id) currentProject.value = null
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  return { projects, currentProject, loading, error, fetchProjects, fetchProject, createProject, updateProject, deleteProject }
})
