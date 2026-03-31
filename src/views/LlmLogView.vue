<template>
  <div class="flex flex-col h-full bg-gray-50">
    <!-- 顶部标题栏 -->
    <div class="flex items-center justify-between px-6 py-4 bg-white border-b">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center">
          <svg class="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
          </svg>
        </div>
        <div>
          <h1 class="text-base font-semibold text-gray-800">大模型调用日志</h1>
          <p class="text-xs text-gray-400">记录本次运行中所有 AI 请求，最多保留 2000 条</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-xs text-gray-400">共 {{ total }} 条</span>
        <button @click="refresh" class="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          刷新
        </button>
        <button @click="clearLogs" class="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-500 border border-red-200 rounded-lg hover:bg-red-50 transition">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
          </svg>
          清空
        </button>
      </div>
    </div>

    <!-- 日志列表 -->
    <div class="flex-1 overflow-y-auto p-4">
      <!-- 空状态 -->
      <div v-if="entries.length === 0" class="flex flex-col items-center justify-center h-64 text-gray-400">
        <svg class="w-12 h-12 mb-3 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
        </svg>
        <p class="text-sm">暂无调用记录</p>
        <p class="text-xs mt-1">执行生成提示词、验证提取或材料分类后将自动记录</p>
      </div>

      <!-- 日志卡片列表 -->
      <div v-else class="space-y-2">
        <div v-for="entry in entries" :key="entry.id"
          class="bg-white rounded-xl border overflow-hidden hover:shadow-sm transition cursor-pointer"
          @click="toggleExpand(entry.id)">
          <!-- 卡片头部 -->
          <div class="flex items-center gap-3 px-4 py-3">
            <!-- 状态圆点 -->
            <div :class="entry.success ? 'bg-green-500' : 'bg-red-500'" class="w-2 h-2 rounded-full flex-shrink-0"></div>
            <!-- 场景标签 -->
            <span :class="sceneClass(entry.scene)" class="text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0">
              {{ entry.scene }}
            </span>
            <!-- 模型名 -->
            <span class="text-xs font-mono text-gray-500 truncate flex-shrink-0 max-w-48">{{ entry.model }}</span>
            <!-- 提示词摘要 -->
            <span class="text-xs text-gray-500 truncate flex-1 min-w-0">{{ entry.prompt_summary }}</span>
            <!-- 右侧信息 -->
            <div class="flex items-center gap-3 flex-shrink-0 ml-2">
              <span v-if="entry.elapsed_s != null" class="text-xs font-mono text-blue-500 font-semibold">{{ entry.elapsed_s.toFixed(1) }}s</span>
              <span v-else class="text-xs text-gray-300">-</span>
              <span class="text-xs text-gray-400 tabular-nums">{{ entry.time }}</span>
              <svg class="w-4 h-4 text-gray-300 transition-transform" :class="expandedId === entry.id ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </div>
          </div>

          <!-- 展开详情 -->
          <div v-if="expandedId === entry.id" class="border-t bg-gray-50 px-4 py-3 space-y-3">
            <div class="grid grid-cols-2 gap-3">
              <!-- 提示词 -->
              <div>
                <div class="text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">提示词摘要（前2000字）</div>
                <pre class="text-xs text-gray-700 bg-white rounded-lg border p-3 whitespace-pre-wrap break-all font-mono leading-relaxed max-h-40 overflow-y-auto">{{ entry.prompt_summary }}</pre>
              </div>
              <!-- 响应 -->
              <div>
                <div class="text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">响应摘要（前2000字）</div>
                <pre v-if="entry.success" class="text-xs text-gray-700 bg-white rounded-lg border p-3 whitespace-pre-wrap break-all font-mono leading-relaxed max-h-40 overflow-y-auto">{{ entry.response_summary }}</pre>
                <div v-else class="text-xs text-red-600 bg-red-50 rounded-lg border border-red-200 p-3 max-h-40 overflow-y-auto break-all">{{ entry.error }}</div>
              </div>
            </div>
            <!-- 元信息行 -->
            <div class="flex items-center gap-4 text-xs text-gray-400 pt-1 border-t">
              <span>模型: <span class="font-mono text-gray-600">{{ entry.model }}</span></span>
              <span>场景: <span class="text-gray-600">{{ entry.scene }}</span></span>
              <span v-if="entry.elapsed_s != null">耗时: <span class="font-mono text-blue-500 font-semibold">{{ entry.elapsed_s.toFixed(1) }}s</span></span>
              <span>状态: <span :class="entry.success ? 'text-green-600' : 'text-red-600'">{{ entry.success ? '成功' : '失败' }}</span></span>
              <span>时间: {{ entry.time }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > 0" class="px-6 py-3 bg-white border-t flex items-center justify-between">
      <span class="text-xs text-gray-400">
        第 {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, total) }} 条 / 共 {{ total }} 条
      </span>
      <div class="flex items-center gap-1">
        <button @click="gotoPage(1)" :disabled="currentPage === 1"
          class="px-2 py-1 text-xs rounded border disabled:opacity-40 hover:bg-gray-50 transition">«</button>
        <button @click="gotoPage(currentPage - 1)" :disabled="currentPage === 1"
          class="px-2 py-1 text-xs rounded border disabled:opacity-40 hover:bg-gray-50 transition">‹</button>
        <span v-for="p in pageNumbers" :key="p">
          <button v-if="p !== '...'" @click="gotoPage(p)"
            class="px-2.5 py-1 text-xs rounded border transition"
            :class="p === currentPage ? 'bg-blue-600 text-white border-blue-600' : 'hover:bg-gray-50'">{{ p }}</button>
          <span v-else class="px-1 text-xs text-gray-400">…</span>
        </span>
        <button @click="gotoPage(currentPage + 1)" :disabled="currentPage === totalPages"
          class="px-2 py-1 text-xs rounded border disabled:opacity-40 hover:bg-gray-50 transition">›</button>
        <button @click="gotoPage(totalPages)" :disabled="currentPage === totalPages"
          class="px-2 py-1 text-xs rounded border disabled:opacity-40 hover:bg-gray-50 transition">»</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiClient } from '../services/apiClient.js'

const entries = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const expandedId = ref(null)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const pageNumbers = computed(() => {
  const pages = []
  const tp = totalPages.value
  const cp = currentPage.value
  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pages.push(i)
  } else {
    pages.push(1)
    if (cp > 3) pages.push('...')
    for (let i = Math.max(2, cp - 1); i <= Math.min(tp - 1, cp + 1); i++) pages.push(i)
    if (cp < tp - 2) pages.push('...')
    pages.push(tp)
  }
  return pages
})

async function refresh() {
  try {
    const result = await invoke('get_llm_logs', { page: currentPage.value, pageSize })
    entries.value = result.entries
    total.value = result.total
  } catch (e) {
    console.error('加载日志失败:', e)
  }
}

async function clearLogs() {
  if (!confirm('确认清空所有大模型调用日志？')) return
  await invoke('clear_llm_logs')
  entries.value = []
  total.value = 0
  currentPage.value = 1
  expandedId.value = null
}

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id
}

async function gotoPage(p) {
  if (typeof p !== 'number') return
  currentPage.value = Math.max(1, Math.min(p, totalPages.value))
  expandedId.value = null
  await refresh()
}

function sceneClass(scene) {
  if (scene === '验证提取') return 'bg-blue-100 text-blue-700'
  if (scene === '提示词生成') return 'bg-green-100 text-green-700'
  if (scene === '材料分类-步骤1') return 'bg-orange-100 text-orange-700'
  if (scene === '材料分类-步骤2') return 'bg-amber-100 text-amber-700'
  if (scene.startsWith('材料分类-优化')) return 'bg-purple-100 text-purple-700'
  if (scene === '材料分类-汇总') return 'bg-gray-100 text-gray-600'
  if (scene === '材料分类') return 'bg-orange-100 text-orange-700'
  return 'bg-gray-100 text-gray-600'
}

onMounted(refresh)
</script>
