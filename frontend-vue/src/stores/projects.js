import { defineStore } from 'pinia'
import { projectsApi } from '../services/api'

export const useProjectsStore = defineStore('projects', {
  state: () => ({
    projects: [],
    currentProject: null,
    loading: false,
    error: null
  }),

  actions: {
    async fetchProjects() {
      this.loading = true
      this.error = null
      try {
        const response = await projectsApi.getAll()
        this.projects = response.data.projects || []
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    async fetchProject(id) {
      this.loading = true
      this.error = null
      try {
        const response = await projectsApi.getById(id)
        this.currentProject = response.data
        return response.data
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async createProject(name, code = null, description = null, requirement_manager_id = null) {
      this.loading = true
      this.error = null
      try {
        const response = await projectsApi.create(name, code, description, requirement_manager_id)
        await this.fetchProjects()
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateProject(id, data) {
      this.loading = true
      this.error = null
      try {
        const response = await projectsApi.update(id, data)
        if (this.currentProject?.id === id) {
          this.currentProject = { ...this.currentProject, ...response.data }
        }
        await this.fetchProjects()
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteProject(id) {
      try {
        await projectsApi.delete(id)
        await this.fetchProjects()
        if (this.currentProject?.id === id) {
          this.currentProject = null
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    }
  }
})
