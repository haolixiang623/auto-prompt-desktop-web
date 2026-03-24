<template>
  <div class="min-h-screen bg-slate-950 text-white flex items-center justify-center px-6 py-12">
    <div class="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.18),_transparent_35%),radial-gradient(circle_at_bottom,_rgba(14,165,233,0.12),_transparent_30%)]"></div>

    <div class="relative w-full max-w-md rounded-3xl border border-white/10 bg-white/6 backdrop-blur-xl shadow-2xl p-8">
      <div class="mb-8">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 text-blue-200 text-xs uppercase tracking-[0.2em]">
          Auto-Prompt
        </div>
        <h1 class="mt-4 text-3xl font-bold text-white">登录工作台</h1>
        <p class="mt-2 text-sm text-slate-300">
          多用户模式已启用。请使用管理员或已分配的账号登录。
        </p>
      </div>

      <form class="space-y-4" @submit.prevent="handleLogin">
        <div>
          <label class="block text-sm text-slate-200 mb-2">账号</label>
          <input
            v-model.trim="username"
            autocomplete="username"
            placeholder="请输入账号"
            class="w-full px-4 py-3 rounded-2xl bg-slate-900/70 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>

        <div>
          <label class="block text-sm text-slate-200 mb-2">密码</label>
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="请输入密码"
            class="w-full px-4 py-3 rounded-2xl bg-slate-900/70 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>

        <div v-if="errorMessage" class="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {{ errorMessage }}
        </div>

        <button
          type="submit"
          :disabled="submitting || !username || !password"
          class="w-full px-4 py-3 rounded-2xl bg-blue-600 text-white font-semibold hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {{ submitting ? '登录中...' : '登录' }}
        </button>
      </form>

      <div class="mt-6 rounded-2xl border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-xs text-amber-100 leading-6">
        初始管理员默认账号：`admin`
        初始管理员默认密码：`admin123456`
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '../services/authService.js'

const route = useRoute()
const router = useRouter()
const username = ref('')
const password = ref('')
const submitting = ref(false)
const errorMessage = ref('')

async function handleLogin() {
  submitting.value = true
  errorMessage.value = ''

  try {
    await login(username.value, password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    window.location.replace(redirect)
  } catch (error) {
    errorMessage.value = String(error?.message || error || '登录失败')
  } finally {
    submitting.value = false
  }
}
</script>
