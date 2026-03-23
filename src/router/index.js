import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/generate',
    name: 'Generate',
    component: () => import('../views/GenerateView.vue')
  },
  {
    path: '/classify',
    name: 'Classify',
    component: () => import('../views/ClassifyView.vue')
  },
  {
    path: '/cases',
    name: 'Cases',
    component: () => import('../views/CaseLibraryView.vue')
  },
  {
    path: '/factor-json',
    name: 'FactorJson',
    component: () => import('../views/FactorJsonView.vue')
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue')
  },
  {
    path: '/review-rule',
    name: 'ReviewRule',
    component: () => import('../views/ReviewRuleView.vue')
  },
  {
    path: '/rule-library',
    name: 'RuleLibrary',
    component: () => import('../views/ReviewRuleLibraryView.vue')
  },
  {
    path: '/llm-log',
    name: 'LlmLog',
    component: () => import('../views/LlmLogView.vue')
  },
  {
    path: '/env-check',
    name: 'EnvCheck',
    component: () => import('../views/EnvCheckView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
