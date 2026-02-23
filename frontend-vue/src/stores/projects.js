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
        console.error('Failed to fetch projects:', error)
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
        console.error('Failed to fetch project:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async createProject(name, code = null, description = null) {
      this.loading = true
      this.error = null
      try {
        const response = await projectsApi.create(name, code, description)
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
