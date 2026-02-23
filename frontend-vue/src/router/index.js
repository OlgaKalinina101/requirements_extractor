import { createRouter, createWebHistory } from 'vue-router'
import ProjectsView from '../views/ProjectsView.vue'
import ProjectView from '../views/ProjectView.vue'
import HomeView from '../views/HomeView.vue'
import ReviewView from '../views/ReviewView.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
