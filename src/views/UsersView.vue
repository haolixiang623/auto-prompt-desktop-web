<template>
  <div class="h-full overflow-y-auto bg-gray-50">
    <div class="bg-white border-b px-6 py-4">
      <h1 class="text-xl font-bold text-gray-900">用户管理</h1>
      <p class="text-sm text-gray-500 mt-0.5">管理员可以手动创建、禁用和重置用户密码。</p>
    </div>

    <div class="p-6 space-y-6">
      <section class="bg-white rounded-xl shadow-sm border p-5">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-base font-semibold text-gray-800">新增用户</h2>
            <p class="text-xs text-gray-400 mt-1">只需要填写名称、账号和密码。</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            v-model.trim="form.name"
            placeholder="名称"
            class="px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
          <input
            v-model.trim="form.username"
            placeholder="账号"
            class="px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
          <input
            v-model="form.password"
            type="password"
            placeholder="密码"
            class="px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
        </div>

        <div v-if="saveMessage" class="mt-4 p-3 rounded-lg text-sm" :class="saveMessage.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'">
          {{ saveMessage.message }}
        </div>

        <div class="mt-4 flex justify-end">
          <button
            @click="handleCreateUser"
            :disabled="saving || !form.name || !form.username || !form.password"
            class="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
          >
            {{ saving ? '保存中...' : '新增用户' }}
          </button>
        </div>
      </section>

      <section class="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div class="px-5 py-4 border-b flex items-center justify-between">
          <div>
            <h2 class="text-base font-semibold text-gray-800">用户列表</h2>
            <p class="text-xs text-gray-400 mt-1">当前共 {{ users.length }} 个用户。</p>
          </div>
          <button
            @click="loadUsers"
            :disabled="loading"
            class="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50"
          >
            刷新
          </button>
        </div>

        <div v-if="loading" class="px-5 py-8 text-sm text-gray-400 text-center">加载中...</div>
        <div v-else-if="users.length === 0" class="px-5 py-8 text-sm text-gray-400 text-center">暂无用户</div>

        <div v-else class="divide-y">
          <div v-for="user in users" :key="user.id" class="px-5 py-4 flex items-center justify-between gap-4">
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-semibold text-gray-800">{{ user.name }}</span>
                <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="user.role === 'admin' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'">
                  {{ user.role === 'admin' ? '管理员' : '普通用户' }}
                </span>
                <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="user.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'">
                  {{ user.active ? '启用中' : '已禁用' }}
                </span>
              </div>
              <div class="text-sm text-gray-500 mt-1">{{ user.username }}</div>
              <div class="text-xs text-gray-400 mt-1">创建于 {{ formatDate(user.createdAt) }}</div>
            </div>

            <div class="flex items-center gap-2 flex-shrink-0">
              <button
                v-if="user.role !== 'admin'"
                @click="toggleUserStatus(user)"
                class="px-3 py-1.5 rounded-lg text-xs font-medium"
                :class="user.active ? 'bg-gray-100 text-gray-700 hover:bg-gray-200' : 'bg-green-100 text-green-700 hover:bg-green-200'"
              >
                {{ user.active ? '禁用' : '启用' }}
              </button>
              <button
                @click="resetPassword(user)"
                class="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100"
              >
                重置密码
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { apiClient } from '../services/apiClient.js'

const loading = ref(false)
const saving = ref(false)
const users = ref([])
const saveMessage = ref(null)
const form = ref({
  name: '',
  username: '',
  password: ''
})

function formatDate(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

async function loadUsers() {
  loading.value = true
  try {
    users.value = await apiClient.get('/api/users')
  } finally {
    loading.value = false
  }
}

async function handleCreateUser() {
  saving.value = true
  saveMessage.value = null

  try {
    await apiClient.post('/api/users', { ...form.value })
    saveMessage.value = { type: 'success', message: '用户已创建。' }
    form.value = { name: '', username: '', password: '' }
    await loadUsers()
  } catch (error) {
    saveMessage.value = { type: 'error', message: String(error?.message || error || '创建失败') }
  } finally {
    saving.value = false
  }
}

async function toggleUserStatus(user) {
  try {
    await apiClient.put(`/api/users/${encodeURIComponent(user.id)}/status`, { active: !user.active })
    await loadUsers()
  } catch (error) {
    saveMessage.value = { type: 'error', message: String(error?.message || error || '更新状态失败') }
  }
}

async function resetPassword(user) {
  const nextPassword = window.prompt(`请输入 ${user.name} 的新密码`, '')
  if (!nextPassword) return

  try {
    await apiClient.post(`/api/users/${encodeURIComponent(user.id)}/password`, { password: nextPassword })
    saveMessage.value = { type: 'success', message: `${user.name} 的密码已重置。` }
  } catch (error) {
    saveMessage.value = { type: 'error', message: String(error?.message || error || '重置密码失败') }
  }
}

onMounted(() => {
  loadUsers()
})
</script>
