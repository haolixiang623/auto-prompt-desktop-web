<template>
  <router-view v-if="route.meta.hideChrome" />

  <div v-else class="flex h-screen bg-gray-100 overflow-hidden">
    <aside
      class="relative flex flex-col bg-gray-900 text-white transition-all duration-300 flex-shrink-0"
      :style="{ width: expanded ? '236px' : '60px' }"
      @mouseenter="expanded = true"
      @mouseleave="expanded = false"
    >
      <div class="flex items-center gap-2.5 px-3.5 py-4 border-b border-gray-800 overflow-hidden h-16 flex-shrink-0">
        <div class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
          <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div v-if="expanded" class="overflow-hidden min-w-0">
          <div class="text-sm font-bold text-white leading-tight whitespace-nowrap">Auto-Prompt</div>
          <div class="text-xs text-gray-400 whitespace-nowrap">Multi-user workspace</div>
        </div>
      </div>

      <nav class="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        <router-link
          v-for="item in visibleNavItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-2.5 py-2.5 rounded-lg transition-all group relative"
          :class="route.path === item.to ? 'bg-blue-600 text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
        >
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" :d="item.icon" />
          </svg>
          <span v-if="expanded" class="text-sm font-medium whitespace-nowrap overflow-hidden">{{ item.label }}</span>
          <div
            v-if="!expanded"
            class="absolute left-full ml-2 px-2.5 py-1.5 bg-gray-700 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150 z-50 shadow-lg"
          >
            {{ item.label }}
          </div>
        </router-link>
      </nav>

      <div class="py-3 px-2 border-t border-gray-800 space-y-2 flex-shrink-0">
        <div class="px-2.5 py-2 rounded-lg bg-gray-800/70 overflow-hidden">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-full bg-blue-500/20 text-blue-300 flex items-center justify-center text-xs font-semibold flex-shrink-0">
              {{ userInitial }}
            </div>
            <div v-if="expanded" class="min-w-0 flex-1">
              <div class="text-sm text-white truncate">{{ authState.user?.name || 'Unknown User' }}</div>
              <div class="text-xs text-gray-400 truncate">
                {{ authState.user?.username || '' }} · {{ authState.user?.role === 'admin' ? '管理员' : '普通用户' }}
              </div>
            </div>
          </div>
        </div>

        <button
          @click="handleLogout"
          class="w-full flex items-center gap-3 px-2.5 py-2.5 rounded-lg transition-all group relative text-gray-400 hover:bg-gray-800 hover:text-white"
        >
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M17 16l4-4m0 0l-4-4m4 4H9m4 4v1a2 2 0 01-2 2H6a2 2 0 01-2-2V7a2 2 0 012-2h5a2 2 0 012 2v1" />
          </svg>
          <span v-if="expanded" class="text-sm font-medium whitespace-nowrap">退出登录</span>
          <div
            v-if="!expanded"
            class="absolute left-full ml-2 px-2.5 py-1.5 bg-gray-700 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150 z-50 shadow-lg"
          >
            退出登录
          </div>
        </button>
      </div>
    </aside>

    <main class="flex-1 overflow-hidden flex flex-col min-w-0">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" class="flex-1 min-h-0 h-full" :key="route.name" />
        </keep-alive>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { authState } from './services/authState.js'
import { logout } from './services/authService.js'

const route = useRoute()
const expanded = ref(false)

const navItems = [
  {
    to: '/',
    label: '概览',
    icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6'
  },
  {
    to: '/generate',
    label: '要素提示词',
    icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z'
  },
  {
    to: '/classify',
    label: '材料分类',
    icon: 'M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01'
  },
  {
    to: '/review-rule',
    label: '审查规则生成',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4'
  },
  {
    to: '/cases',
    label: '提示词库',
    icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10'
  },
  {
    to: '/rule-library',
    label: '审查规则库',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01'
  },
  {
    to: '/factor-json',
    label: '要素 JSON',
    icon: 'M7 8h10M7 12h6m-6 4h10M5 3h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2z'
  },
  {
    to: '/env-check',
    label: '环境检测',
    icon: 'M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18'
  },
  {
    to: '/settings',
    label: '设置',
    icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
    adminOnly: true
  },
  {
    to: '/users',
    label: '用户管理',
    icon: 'M17 20h5v-1a4 4 0 00-5-3.874M9 20H4v-1a4 4 0 015-3.874M16 6a4 4 0 11-8 0 4 4 0 018 0zm6 14v-1a6 6 0 00-9-5.197M2 20v-1a6 6 0 019-5.197',
    adminOnly: true
  },
  {
    to: '/llm-log',
    label: '调用日志',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
    adminOnly: true
  }
]

const visibleNavItems = computed(() => navItems.filter((item) => !item.adminOnly || authState.user?.role === 'admin'))

const userInitial = computed(() => {
  const name = authState.user?.name || authState.user?.username || 'U'
  return name.slice(0, 1).toUpperCase()
})

async function handleLogout() {
  await logout()
  window.location.replace('/login')
}
</script>
