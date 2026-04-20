<template>
  <div class="h-full flex flex-col bg-gray-50">
    <!-- 顶部标题栏 -->
    <div class="flex items-center justify-between px-6 py-4 bg-white border-b flex-shrink-0">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center" :class="iconBgClass">
          <svg class="w-4 h-4" :class="iconClass" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="iconPath" />
          </svg>
        </div>
        <div>
          <h1 class="text-base font-semibold text-gray-800">{{ title }}</h1>
          <p class="text-xs text-gray-400">{{ subtitle }}</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <button @click="loadList" :disabled="loading"
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition disabled:opacity-50">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          刷新
        </button>
        <router-link :to="createRoute"
          class="flex items-center gap-1.5 px-4 py-1.5 text-xs text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition font-medium">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          {{ createLabel }}
        </router-link>
      </div>
    </div>

    <!-- 列表区域 -->
    <div class="flex-1 overflow-y-auto p-4">
      <!-- 加载中 -->
      <div v-if="loading" class="flex items-center justify-center h-48 text-gray-400 text-sm">
        <svg class="w-5 h-5 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
        加载中...
      </div>

      <!-- 空状态 -->
      <div v-else-if="workspaces.length === 0" class="flex flex-col items-center justify-center h-64 text-gray-400">
        <svg class="w-14 h-14 mb-3 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
        </svg>
        <p class="text-sm font-medium text-gray-500">暂无历史记录</p>
        <p class="text-xs mt-1">点击上方「{{ createLabel }}」开始</p>
      </div>

      <!-- 工作区卡片列表 -->
      <div v-else class="space-y-3">
        <div v-for="ws in workspaces" :key="ws.id"
          class="bg-white rounded-xl border hover:shadow-md transition group">
          <div class="px-5 py-4">
            <div class="flex items-start justify-between gap-4">
              <!-- 左侧信息 -->
              <div class="min-w-0 flex-1 cursor-pointer" @click="$emit('open', ws)">
                <div class="flex items-center gap-2 mb-1.5">
                  <svg class="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                  </svg>
                  <span class="text-sm font-semibold text-gray-800 truncate">{{ ws.id.slice(0, 8) }}</span>
                  <span v-if="ws.genStatus === 'generating'" class="flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-100 text-blue-600 text-xs font-medium">
                    <svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                    </svg>
                    生成中
                  </span>
                  <span v-else-if="ws.genStatus === 'done'" class="px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-medium">已完成</span>
                  <span v-else-if="ws.genStatus === 'error'" class="px-2 py-0.5 rounded-full bg-red-100 text-red-600 text-xs font-medium">生成失败</span>
                  <span class="text-xs text-gray-400">{{ formatDate(ws.createdAt) }}</span>
                </div>
                <div class="flex items-center gap-3 text-xs text-gray-500 mb-2">
                  <span class="flex items-center gap-1">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                    </svg>
                    {{ ws.materialCount }} 个材料
                  </span>
                  <span class="flex items-center gap-1">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
                    </svg>
                    {{ ws.fileCount }} 个文件
                  </span>
                </div>
                <!-- 材料标签 -->
                <div v-if="ws.materials.length" class="flex flex-wrap gap-1.5">
                  <span v-for="mat in ws.materials.slice(0, 8)" :key="mat"
                    class="px-2 py-0.5 rounded-full text-xs bg-blue-50 text-blue-600 border border-blue-100">
                    {{ mat }}
                  </span>
                  <span v-if="ws.materials.length > 8"
                    class="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-500">
                    +{{ ws.materials.length - 8 }}
                  </span>
                </div>
              </div>

              <!-- 右侧操作 -->
              <div class="flex items-center gap-2 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                <button @click="$emit('open', ws)"
                  class="flex items-center gap-1 px-3 py-1.5 text-xs text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition font-medium">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                  </svg>
                  打开
                </button>
                <button @click.stop="handleDelete(ws)"
                  class="flex items-center gap-1 px-3 py-1.5 text-xs text-red-500 bg-red-50 rounded-lg hover:bg-red-100 transition font-medium">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                  删除
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部统计 -->
    <div v-if="workspaces.length > 0" class="px-6 py-3 bg-white border-t flex-shrink-0">
      <span class="text-xs text-gray-400">共 {{ workspaces.length }} 条记录</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated, onUnmounted } from 'vue'
import { apiClient } from '../services/apiClient.js'

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  createRoute: { type: String, required: true },
  createLabel: { type: String, default: '新增' },
  iconPath: { type: String, default: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z' },
  iconBgClass: { type: String, default: 'bg-blue-100' },
  iconClass: { type: String, default: 'text-blue-600' },
  module: { type: String, default: '' },
})

const emit = defineEmits(['open'])

const loading = ref(false)
const workspaces = ref([])

function formatDate(value) {
  if (!value) return '-'
  try {
    const d = new Date(value)
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return value
  }
}

async function loadList() {
  loading.value = true
  try {
    const query = props.module ? { module: props.module } : undefined
    workspaces.value = await apiClient.get('/api/workspaces/list', query)
  } catch (e) {
    console.error('加载工作区列表失败:', e)
  } finally {
    loading.value = false
  }
  // 有生成中的任务时启动轮询，否则停止
  const hasGenerating = workspaces.value.some(ws => ws.genStatus === 'generating')
  if (hasGenerating && !pollTimer) {
    pollTimer = setInterval(loadList, 3000)
  } else if (!hasGenerating && pollTimer) {
    stopPolling()
  }
}

async function handleDelete(ws) {
  const materialNames = ws.materials.length ? ws.materials.join('、') : ws.id.slice(0, 8)
  if (!confirm(`确认删除工作区？\n\n包含材料：${materialNames}\n\n此操作不可恢复。`)) return
  try {
    await apiClient.delete(`/api/workspaces/${encodeURIComponent(ws.id)}`)
    workspaces.value = workspaces.value.filter(w => w.id !== ws.id)
  } catch (e) {
    alert('删除失败: ' + (e?.message || e))
  }
}

let pollTimer = null

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(loadList)

onActivated(loadList)

onUnmounted(stopPolling)

defineExpose({ loadList })
</script>
