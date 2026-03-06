import { createRouter, createWebHistory } from 'vue-router'
import ProjectsView from '../views/ProjectsView.vue'
import ProjectView from '../views/ProjectView.vue'
import HomeView from '../views/HomeView.vue'
import ReviewView from '../views/ReviewView.vue'
import AdminView from '../views/AdminView.vue'
import RequirementDetailView from '../views/RequirementDetailView.vue'
import DashboardView from '../views/DashboardView.vue'

const routes = [
  {
    path: '/',
    name: 'projects',
    component: ProjectsView
  },
  {
    path: '/projects/:projectId',
    name: 'project',
    component: ProjectView,
    props: true
  },
  {
    path: '/upload',
    name: 'home',
    component: HomeView
  },
  {
    path: '/review/:documentId?',
    name: 'review',
    component: ReviewView,
    props: true
  },
  {
    path: '/admin',
    name: 'admin',
    component: AdminView
  },
  {
    path: '/requirement/:requirementId',
    name: 'requirement-detail',
    component: RequirementDetailView,
    props: true
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
