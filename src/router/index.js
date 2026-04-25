import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import { ensureAuthLoaded, hasAuthSession, isAdminUser } from '../services/authService.js'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true, hideChrome: true }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/generate',
    name: 'GenerateList',
    component: () => import('../views/GenerateListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/generate/new',
    name: 'Generate',
    component: () => import('../views/GenerateView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/classify',
    name: 'ClassifyList',
    component: () => import('../views/ClassifyListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/classify/new',
    name: 'Classify',
    component: () => import('../views/ClassifyView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/cases',
    name: 'Cases',
    component: () => import('../views/CaseLibraryView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/factor-json',
    name: 'FactorJson',
    component: () => import('../views/FactorJsonView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { requiresAuth: true, adminOnly: true }
  },
  {
    path: '/users',
    name: 'Users',
    component: () => import('../views/UsersView.vue'),
    meta: { requiresAuth: true, adminOnly: true }
  },
  {
    path: '/review-rule',
    name: 'ReviewRuleList',
    component: () => import('../views/ReviewRuleListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/review-rule/new',
    name: 'ReviewRule',
    component: () => import('../views/ReviewRuleView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/rule-library',
    name: 'RuleLibrary',
    component: () => import('../views/ReviewRuleLibraryView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/llm-log',
    name: 'LlmLog',
    component: () => import('../views/LlmLogView.vue'),
    meta: { requiresAuth: true, adminOnly: true }
  },
  {
    path: '/env-check',
    name: 'EnvCheck',
    component: () => import('../views/EnvCheckView.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  await ensureAuthLoaded()

  if (to.meta.public) {
    if (to.path === '/login' && hasAuthSession()) {
      return '/'
    }
    return true
  }

  if (!hasAuthSession()) {
    return {
      path: '/login',
      query: to.fullPath !== '/' ? { redirect: to.fullPath } : {}
    }
  }

  if (to.meta.adminOnly && !isAdminUser()) {
    return '/'
  }

  return true
})

export default router
