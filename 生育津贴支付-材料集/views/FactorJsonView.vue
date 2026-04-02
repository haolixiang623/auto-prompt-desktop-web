<template>
  <div class="p-8">
    <h1 class="text-2xl font-bold mb-4">要素JSON生成</h1>
    <p class="text-gray-600 mb-6">根据 factors.xlsx 和提示词文件，生成要素信息录入JSON模板</p>

    <!-- 工作区选择 -->
    <div class="bg-white p-6 rounded-lg shadow mb-6">
      <h3 class="text-lg font-bold mb-4">上传工作区</h3>
      <div class="flex gap-4">
        <input v-model="workDir" type="text" placeholder="上传后会显示服务端工作区路径"
          class="flex-1 px-4 py-2 border rounded" readonly />
        <button @click="selectWorkDir" class="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">上传文件夹...</button>
      </div>
      <p class="mt-2 text-sm text-gray-500">
        工作区需包含 factors.xlsx 和材料子目录（每个子目录含对应的提示词 .txt 文件）
      </p>
    </div>

    <!-- 说明 -->
    <div v-if="workDir" class="bg-blue-50 border border-blue-200 p-4 rounded-lg mb-6 text-sm text-blue-800">
      <div class="font-medium mb-1">处理流程</div>
      <ol class="list-decimal list-inside space-y-1">
        <li>读取 <code>factors.xlsx</code> 获取各材料的要素定义</li>
        <li>在每个材料子目录中找到对应的提示词 .txt 文件</li>
        <li>从提示词中提取识别规则，结合要素定义生成 JSON 模板</li>
        <li>输出到各材料目录：<code>[材料名]--要素信息录入.json</code></li>
      </ol>
    </div>

    <!-- 操作按钮 -->
    <div class="flex gap-4 mb-6">
      <button @click="generate" :disabled="!workDir || isRunning"
        class="px-6 py-2 rounded transition"
        :class="workDir && !isRunning ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed'">
        <span v-if="isRunning">生成中...</span>
        <span v-else>开始生成</span>
      </button>
      <button @click="clear" :disabled="isRunning" class="px-6 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">清除</button>
    </div>

    <!-- 日志 -->
    <div v-if="logs.length > 0" class="bg-gray-900 text-gray-100 p-4 rounded-lg mb-6">
      <h3 class="text-lg font-bold mb-2">执行日志</h3>
      <div ref="logContainer" class="space-y-1 max-h-96 overflow-y-auto">
        <div v-for="(log, i) in logs" :key="i" class="text-sm font-mono">
          <span class="text-gray-500">{{ log.time }} </span>
          <span :class="getLogClass(log.type)">{{ log.message }}</span>
        </div>
      </div>
    </div>

      <!-- 结果 -->
    <div v-if="results.length > 0" class="bg-white rounded-xl shadow overflow-hidden">
      <div class="flex items-center justify-between px-5 py-4 border-b">
        <h3 class="font-semibold text-gray-800">生成结果</h3>
        <div class="flex items-center gap-3 text-sm">
          <span class="text-green-600 font-medium">✓ {{ results.filter(r => r.success).length }} 成功</span>
          <span v-if="results.filter(r => !r.success).length > 0" class="text-red-500">
            ✗ {{ results.filter(r => !r.success).length }} 失败
          </span>
          <span class="text-gray-400">共 {{ results.length }} 个</span>
          <button @click="downloadAll" :disabled="!results.filter(r => r.success).length"
            class="px-3 py-1 rounded text-xs transition"
            :class="results.filter(r => r.success).length > 0 ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed'">
            <span v-if="downloadingAll">下载中...</span>
            <span v-else>全部下载JSON</span>
          </button>
        </div>
      </div>

      <div class="divide-y">
        <div v-for="r in results" :key="r.material">
          <!-- 结果行 -->
          <div class="flex items-center gap-3 px-5 py-3"
            :class="r === previewItem ? 'bg-blue-50' : 'hover:bg-gray-50'">
            <div class="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center"
              :class="r.success ? 'bg-green-100' : 'bg-red-100'">
              <svg v-if="r.success" class="w-3.5 h-3.5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
              <svg v-else class="w-3.5 h-3.5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-gray-800">{{ r.material }}</div>
              <div class="text-xs text-gray-400 truncate">{{ r.success ? r.output : r.error }}</div>
            </div>
            <div v-if="r.success" class="flex items-center gap-2 flex-shrink-0">
              <button @click="togglePreview(r)"
                class="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs transition"
                :class="previewItem === r ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                {{ previewItem === r ? '收起' : '预览' }}
              </button>
              <button @click="downloadJson(r)"
                class="flex items-center gap-1 px-2.5 py-1 bg-blue-100 text-blue-700 rounded-lg text-xs hover:bg-blue-200 transition">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                </svg>
                下载JSON
              </button>
              <button @click="copyJson(r)"
                class="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs transition"
                :class="copiedItem === r.material ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'">
                <svg v-if="copiedItem === r.material" class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                <svg v-else class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                </svg>
                {{ copiedItem === r.material ? '已复制' : '复制' }}
              </button>
            </div>
          </div>

          <!-- JSON 预览展开区 -->
          <div v-if="previewItem === r" class="px-5 pb-4 bg-blue-50 border-t border-blue-100">
            <div v-if="r.loadingPreview" class="py-6 text-center text-sm text-gray-400">
              加载中...
            </div>
            <div v-else-if="r.previewContent" class="mt-3">
              <pre class="text-xs text-gray-700 bg-white rounded-lg p-4 max-h-80 overflow-y-auto border border-blue-100 leading-relaxed">{{ r.previewContent }}</pre>
            </div>
            <div v-else class="py-4 text-sm text-red-400">{{ r.previewError || '无法加载预览' }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
  import { ref, onMounted, onUnmounted, nextTick } from 'vue'
  import { useRoute } from 'vue-router'
  import { apiClient } from '../services/apiClient.js'
  import { parseJsonFilePayload } from '../services/jsonFile.js'
  import { listen } from '../tauri/event.js'
  import { invoke } from '../tauri/tauri.js'
  import { getScopedStorageItem, removeScopedStorageItem, setScopedStorageItem } from '../services/authState.js'

const route = useRoute()
const WORKDIR_STORAGE_KEY = 'auto-prompt.factor-json.workdir'
const workDir = ref('')
const isRunning = ref(false)
const logs = ref([])
const results = ref([])
const logContainer = ref(null)
const previewItem = ref(null)
const copiedItem = ref(null)
const downloadingAll = ref(false)

let unlistenLog = null

onMounted(async () => {
  // Auto-fill workDir from route query (passed from GenerateView)
  if (route.query.workDir) {
    workDir.value = String(route.query.workDir)
    persistWorkDir()
    addLog(`已从上一步载入工作区: ${workDir.value}`, 'info')
  } else if (typeof window !== 'undefined') {
    const storedWorkDir = getScopedStorageItem(WORKDIR_STORAGE_KEY)
    if (storedWorkDir) {
      workDir.value = storedWorkDir
      addLog(`已恢复上次工作区: ${workDir.value}`, 'info')
    }
  }

  unlistenLog = await listen('skill-log', (event) => {
    const line = event.payload
    const type = line.includes('[错误]') ? 'error'
      : line.includes('[完成]') || line.includes('✓') ? 'success'
      : line.includes('[警告]') ? 'warning'
      : 'info'
    addLog(line, type)
    nextTick(() => {
      if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight
    })
  })
})

onUnmounted(() => { if (unlistenLog) unlistenLog() })

function getLogClass(type) {
  return { error: 'text-red-400', success: 'text-green-400', warning: 'text-yellow-400', info: 'text-blue-300' }[type] || 'text-gray-400'
}

function addLog(message, type = 'info') {
  logs.value.push({ time: new Date().toLocaleTimeString(), message, type })
}

function persistWorkDir() {
  if (typeof window === 'undefined') return
  if (workDir.value) {
    setScopedStorageItem(WORKDIR_STORAGE_KEY, workDir.value)
  } else {
    removeScopedStorageItem(WORKDIR_STORAGE_KEY)
  }
}

async function selectWorkDir() {
  try {
    const selected = await invoke('select_directory')
    if (!selected) return
    workDir.value = selected
    persistWorkDir()
    addLog(`已上传工作区: ${selected}`, 'info')
  } catch (e) {
    addLog(`上传工作区失败: ${e}`, 'error')
  }
}

async function generate() {
  if (!workDir.value || isRunning.value) return
  isRunning.value = true
  results.value = []
  addLog('开始生成要素JSON...', 'info')
  addLog(`工作目录: ${workDir.value}`, 'info')
  try {
    const res = await invoke('generate_factor_json', { workDir: workDir.value })
    results.value = res
    const successCount = res.filter(r => r.success).length
    addLog(`生成完成！共 ${res.length} 个材料，成功 ${successCount} 个`, 'success')
  } catch (e) {
    addLog(`生成失败: ${e}`, 'error')
  } finally {
    isRunning.value = false
  }
}

async function togglePreview(r) {
  if (previewItem.value === r) {
    previewItem.value = null
    return
  }
  previewItem.value = r
  if (!r.previewContent && !r.loadingPreview) {
    r.loadingPreview = true
    try {
      const content = await invoke('read_json_file', { path: r.output })
      r.previewContent = JSON.stringify(parseJsonFilePayload(content), null, 2)
    } catch (e) {
      r.previewError = String(e)
    } finally {
      r.loadingPreview = false
    }
  }
}

async function downloadJson(r) {
  try {
    const filename = r.output.split(/[/\\]/).pop()
    apiClient.open('/api/files/download', { path: r.output })
    addLog(`已下载: ${filename}`, 'success')
  } catch (e) {
    addLog(`下载失败: ${e}`, 'error')
  }
}

async function copyJson(r) {
  try {
    let content = r.previewContent
    if (!content) {
      const raw = await invoke('read_json_file', { path: r.output })
      content = JSON.stringify(parseJsonFilePayload(raw), null, 2)
    }
    await navigator.clipboard.writeText(content)
    copiedItem.value = r.material
    setTimeout(() => { copiedItem.value = null }, 2000)
  } catch (e) {
    addLog(`复制失败: ${e}`, 'error')
  }
}

async function downloadAll() {
  const successResults = results.value.filter(r => r.success)
  if (successResults.length === 0) return

  downloadingAll.value = true
  addLog('开始批量下载 JSON...', 'info')

  try {
    apiClient.open('/api/files/download-batch', {
      pathsJson: JSON.stringify(successResults.map(r => r.output)),
    })
    addLog(`开始下载 ${successResults.length} 个 JSON 文件`, 'success')
  } catch (e) {
    addLog(`批量下载失败: ${e}`, 'error')
  } finally {
    downloadingAll.value = false
  }
}

function clear() {
  workDir.value = ''
  persistWorkDir()
  logs.value = []
  results.value = []
  previewItem.value = null
  copiedItem.value = null
  downloadingAll.value = false
}
</script>
