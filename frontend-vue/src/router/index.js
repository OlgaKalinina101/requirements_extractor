import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ProjectsView from '../views/ProjectsView.vue'
import ProjectView from '../views/ProjectView.vue'
import HomeView from '../views/HomeView.vue'
import ReviewView from '../views/ReviewView.vue'
import AdminView from '../views/AdminView.vue'
import RequirementDetailView from '../views/RequirementDetailView.vue'
import DashboardRouterView from '../views/DashboardRouterView.vue'
import LoginView from '../views/LoginView.vue'
import UsersView from '../views/UsersView.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { public: true }
  },
  {
    path: '/',
    name: 'projects',
    component: ProjectsView
  },
  {
    path: '/projects',
    redirect: '/'
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
    component: HomeView,
    meta: { requiresRole: 'manager' }
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
    component: AdminView,
    meta: { requiresRole: 'admin' }
  },
  {
    path: '/users',
    name: 'users',
    component: UsersView,
    meta: { requiresRole: 'admin' }
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
    component: DashboardRouterView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  // Public routes don't need a token
  if (to.meta.public) return true

  // Not logged in — send to login page
  if (!auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // Role-restricted route
  if (to.meta.requiresRole) {
    const required = to.meta.requiresRole
    const role = auth.role
    const allowed =
      required === 'admin' ? auth.isAdmin :
      required === 'manager' ? auth.isManager :
      true
    if (!allowed) return { name: 'projects' }
  }

  return true
})

export default router
