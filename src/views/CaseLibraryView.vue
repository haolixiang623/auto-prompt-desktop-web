<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold">提示词库</h1>
        <p class="text-gray-500 text-sm mt-1">提示词案例库，支持搜索、导入、删除</p>
      </div>
      <div class="flex gap-2">
        <button @click="showTxtDialog = true"
          class="flex items-center gap-1.5 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          从 TXT 更新案例
        </button>
        <button @click="showImportDialog = true"
          class="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
          </svg>
          导入 JSON
        </button>
        <button @click="loadCases"
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300">刷新</button>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="bg-white p-4 rounded-lg shadow mb-4 flex gap-3 items-center">
      <div class="flex-1 relative">
        <svg class="absolute left-3 top-2.5 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
        <input v-model="searchQuery" @input="onSearch" type="text" placeholder="搜索材料类型、要素名称..."
          class="w-full pl-9 pr-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-300" />
      </div>
      <select v-model="filterMaterial" @change="onSearch"
        class="px-3 py-2 border rounded-lg text-sm text-gray-700 focus:outline-none">
        <option value="">all materials</option>
        <option v-for="m in materialTypes" :key="m" :value="m">{{ m }}</option>
      </select>
      <span class="text-sm text-gray-500 whitespace-nowrap">共 {{ filteredCases.length }} 条</span>
    </div>

    <!-- 案例列表 -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <svg class="animate-spin w-6 h-6 text-blue-500 mr-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      <span class="text-gray-500">加载中...</span>
    </div>

    <div v-else-if="filteredCases.length === 0" class="bg-white rounded-lg shadow p-12 text-center">
      <svg class="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
      </svg>
      <p class="text-gray-400">案例库为空，请导入案例库 JSON 文件</p>
    </div>

    <div v-else class="space-y-3">
      <div v-for="(c, idx) in paginatedCases" :key="idx"
        class="bg-white rounded-lg shadow hover:shadow-md transition overflow-hidden">
        <div class="p-4">
          <div class="flex items-start justify-between gap-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs font-medium flex-shrink-0">{{ c.material_name }}</span>
                <span class="font-semibold text-gray-900 truncate">{{ c.factor_name }}</span>
              </div>
              <p v-if="c.extract_desc" class="text-sm text-gray-500 mb-2">{{ c.extract_desc }}</p>
              <div v-if="c.extraction_rule" class="bg-gray-50 rounded p-2 text-xs text-gray-600 leading-relaxed line-clamp-2">
                {{ c.extraction_rule }}
              </div>
            </div>
            <button @click="deleteCase(c, idx)"
              class="flex-shrink-0 p-1.5 text-gray-400 hover:text-red-500 rounded hover:bg-red-50 transition">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
            </button>
          </div>
          <div v-if="c.tags && c.tags.length" class="flex flex-wrap gap-1 mt-2">
            <span v-for="tag in c.tags" :key="tag"
              class="px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">{{ tag }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="flex justify-center gap-2 mt-6">
      <button @click="page = Math.max(1, page - 1)" :disabled="page === 1"
        class="px-3 py-1 rounded border text-sm disabled:opacity-40 hover:bg-gray-50">&lt;</button>
      <span class="px-3 py-1 text-sm text-gray-600">{{ page }} / {{ totalPages }}</span>
      <button @click="page = Math.min(totalPages, page + 1)" :disabled="page === totalPages"
        class="px-3 py-1 rounded border text-sm disabled:opacity-40 hover:bg-gray-50">&gt;</button>
    </div>

    <!-- 原有 JSON 导入对话框 -->
    <div v-if="showImportDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl p-6 w-[480px] shadow-2xl">
        <h3 class="text-lg font-bold mb-4">导入案例库 (JSON)</h3>
        <div class="space-y-4 mb-4">
          <div>
            <label class="block text-sm font-medium mb-1.5">选择案例库 JSON 文件</label>
            <div class="flex gap-2">
              <input v-model="importPath" type="text" placeholder="case_library.json 文件路径"
                class="flex-1 px-3 py-2 border rounded text-sm" readonly />
              <button @click="selectImportFile"
                class="px-3 py-2 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300">浏览</button>
            </div>
          </div>
          <div class="space-y-2">
            <label class="block text-sm font-medium">导入模式</label>
            <label class="flex items-start gap-2 p-3 rounded-lg border cursor-pointer hover:bg-gray-50"
              :class="importMode === 'overwrite' ? 'border-blue-400 bg-blue-50' : ''">
              <input type="radio" v-model="importMode" value="overwrite" class="mt-0.5" />
              <div><div class="text-sm font-medium">全量覆盖</div><div class="text-xs text-gray-500">直接替换现有案例库</div></div>
            </label>
            <label class="flex items-start gap-2 p-3 rounded-lg border cursor-pointer hover:bg-gray-50"
              :class="importMode === 'merge' ? 'border-blue-400 bg-blue-50' : ''">
              <input type="radio" v-model="importMode" value="merge" class="mt-0.5" />
              <div><div class="text-sm font-medium">增量合并</div><div class="text-xs text-gray-500">仅添加不存在的案例</div></div>
            </label>
          </div>
        </div>
        <div v-if="importResult" class="mb-4 px-3 py-2 rounded text-sm"
          :class="importResult.ok ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'">
          {{ importResult.message }}
        </div>
        <div class="flex justify-end gap-3">
          <button @click="closeImport" class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">关闭</button>
          <button @click="doImport" :disabled="!importPath || importing"
            class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
            {{ importing ? '导入中...' : '确认导入' }}
          </button>
        </div>
      </div>
    </div>

    <!-- TXT 上传对话框 -->
    <div v-if="showTxtDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl shadow-2xl w-[560px] max-h-[80vh] flex flex-col">
        <!-- Header -->
        <div class="px-6 pt-6 pb-4 border-b">
          <h3 class="text-lg font-bold">从提示词 TXT 更新案例库</h3>
          <p class="text-sm text-gray-500 mt-1">选择一个或多个提示词 TXT 文件，解析要素规则并写入案例库（增量合并）</p>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          <!-- 文件路径输入 -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <label class="text-sm font-medium">添加 TXT 文件</label>
              <button @click="txtFiles = []" v-if="txtFiles.length"
                class="text-xs px-2.5 py-1 bg-gray-100 text-gray-500 rounded hover:bg-gray-200">
                清空全部
              </button>
            </div>

            <!-- 拖拽/点击上传区域 -->
            <div
              @drop.prevent="handleDrop"
              @dragover.prevent="isDragging = true"
              @dragleave.prevent="isDragging = false"
              @click="openFilePicker()"
              class="border-2 border-dashed rounded-lg p-8 mb-3 text-center transition-all cursor-pointer"
              :class="[
                isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-gray-50 hover:border-blue-300 hover:bg-blue-50'
              ]"
            >
              <svg class="w-12 h-12 mx-auto mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
              </svg>
              <p class="text-sm font-medium text-gray-700 mb-1">
                点击选择或拖拽 TXT 文件
              </p>
              <p class="text-xs text-gray-500">支持多个文件同时添加</p>
            </div>

            <!-- 已添加文件列表 -->
            <div v-if="txtFiles.length === 0" class="border-2 border-dashed border-gray-200 rounded-lg py-6 text-center">
              <svg class="w-6 h-6 text-gray-300 mx-auto mb-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <p class="text-xs text-gray-400">暂无文件</p>
            </div>

            <div v-else class="space-y-1.5 max-h-48 overflow-y-auto">
              <div v-for="(f, i) in txtFiles" :key="i"
                class="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-100">
                <svg class="w-4 h-4 text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <span class="text-xs text-gray-700 flex-1 truncate">{{ f.split('/').pop() }}</span>
                <!-- per-file result badge -->
                <span v-if="txtFileResults[f]" class="text-xs px-1.5 py-0.5 rounded"
                  :class="txtFileResults[f].error ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-700'">
                  {{ txtFileResults[f].error || `+${txtFileResults[f].added}` }}
                </span>
                <button @click="txtFiles.splice(i, 1)" class="text-gray-300 hover:text-red-400 flex-shrink-0">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- 结果摘要 -->
          <div v-if="txtImportResult" class="px-4 py-3 rounded-lg text-sm"
            :class="txtImportResult.ok ? 'bg-green-50 border border-green-200 text-green-800' : 'bg-red-50 border border-red-200 text-red-700'">
            {{ txtImportResult.message }}
          </div>
        </div>

        <!-- Footer -->
        <div class="px-6 py-4 border-t flex justify-between items-center">
          <span v-if="txtImporting" class="flex items-center gap-1.5 text-sm text-blue-600">
            <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            解析并写入案例库...
          </span>
          <span v-else class="text-xs text-gray-400">解析后自动增量合并，不覆盖已有案例</span>
          <div class="flex gap-3">
            <button @click="closeTxtDialog" class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 text-sm">关闭</button>
            <button @click="doTxtImport" :disabled="!txtFiles.length || txtImporting"
              class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm font-medium">
              {{ txtImporting ? '导入中...' : `导入 ${txtFiles.length} 个文件` }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { apiClient } from '../services/apiClient.js'
// Tauri listen removed

const loading = ref(false)
const allCases = ref([])
const searchQuery = ref('')
const filterMaterial = ref('')
const page = ref(1)
const PAGE_SIZE = 15

const showImportDialog = ref(false)
const importPath = ref('')
const importMode = ref('overwrite')
const importing = ref(false)
const importResult = ref(null)

// TXT 导入状态
const showTxtDialog = ref(false)
const txtFiles = ref([])
const txtImporting = ref(false)
const txtImportResult = ref(null)
const txtFileResults = ref({})  // { filePath: { added, skipped, error } }
const isDragging = ref(false)
let unlistenFileDrop = null

const materialTypes = computed(() => {
  const set = new Set(allCases.value.map(c => c.material_name).filter(Boolean))
  return Array.from(set).sort()
})

const filteredCases = computed(() => {
  let list = allCases.value
  if (filterMaterial.value) {
    list = list.filter(c => c.material_name === filterMaterial.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(c =>
      (c.material_name || '').toLowerCase().includes(q) ||
      (c.factor_name || '').toLowerCase().includes(q) ||
      (c.extract_desc || '').toLowerCase().includes(q) ||
      (c.extraction_rule || '').toLowerCase().includes(q) ||
      (c.tags || []).some(t => t.toLowerCase().includes(q))
    )
  }
  return list
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredCases.value.length / PAGE_SIZE)))

const paginatedCases = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE
  return filteredCases.value.slice(start, start + PAGE_SIZE)
})

function onSearch() {
  page.value = 1
}

onMounted(async () => {
  loadCases()
  
  // 监听 Tauri 文件拖拽事件
  unlistenFileDrop = await listen('tauri://file-drop', (event) => {
    console.log('[file-drop] 接收到文件:', event.payload)
    console.log('[file-drop] 对话框状态:', showTxtDialog.value)
    if (showTxtDialog.value) {
      const paths = event.payload
      for (const path of paths) {
        console.log('[file-drop] 处理文件:', path)
        if (path.toLowerCase().endsWith('.txt') && !txtFiles.value.includes(path)) {
          txtFiles.value.push(path)
          console.log('[file-drop] 文件已添加:', path)
        }
      }
      isDragging.value = false
    }
  })
  
  // 同时监听 drag-hover 和 drag-cancelled 事件用于调试
  await listen('tauri://file-drop-hover', (event) => {
    console.log('[file-drop-hover] 文件悬停:', event.payload)
    if (showTxtDialog.value) {
      isDragging.value = true
    }
  })
  
  await listen('tauri://file-drop-cancelled', () => {
    console.log('[file-drop-cancelled] 拖拽取消')
    isDragging.value = false
  })
})

onUnmounted(() => {
  if (unlistenFileDrop) unlistenFileDrop()
})

async function loadCases() {
  loading.value = true
  try {
    const lib = await invoke('load_case_library')
    // Support both old Case struct format and raw JSON format
    const cases = lib.cases || []
    allCases.value = cases.map(c => ({
      material_name: c.material_name || c.material_type || '',
      factor_name: c.factor_name || c.fields?.[0]?.field_name || '',
      extract_desc: c.extract_desc || c.fields?.[0]?.description || '',
      extraction_rule: c.extraction_rule || c.fields?.[0]?.extraction_rule || '',
      tags: c.tags || [],
      id: c.id || null,
      _raw: c
    }))
  } catch (e) {
    console.error('load_case_library failed:', e)
    allCases.value = []
  } finally {
    loading.value = false
  }
}

async function deleteCase(c, idx) {
  if (!c.id) {
    alert('该案例无法删除（缺少 ID）')
    return
  }
  if (!confirm(`确定删除「${c.factor_name}」这个案例？`)) return
  try {
    await invoke('delete_case', { caseId: c.id })
    await loadCases()
  } catch (e) {
    alert(`删除失败: ${e}`)
  }
}

async function selectImportFile() {
  try {
    const selected = await invoke('select_file', {
      filters: [{ name: 'JSON', extensions: ['json'] }]
    })
    if (selected) importPath.value = selected
  } catch (e) { console.error(e) }
}

async function doImport() {
  if (!importPath.value) return
  importing.value = true
  importResult.value = null
  try {
    const result = await invoke('import_case_library_json', {
      sourcePath: importPath.value,
      overwrite: importMode.value === 'overwrite'
    })
    importResult.value = {
      ok: true,
      message: `导入成功！新增 ${result.imported} 个，跳过 ${result.skipped} 个，共 ${result.total_cases} 个案例`
    }
    await loadCases()
  } catch (e) {
    importResult.value = { ok: false, message: `导入失败: ${e}` }
  } finally {
    importing.value = false
  }
}

function closeImport() {
  showImportDialog.value = false
  importPath.value = ''
  importResult.value = null
}

function handleDrop(e) {
  // Tauri 会通过 'tauri://file-drop' 事件处理文件路径
  // 这里只需要重置拖拽状态
  isDragging.value = false
}

async function openFilePicker() {
  try {
    const paths = await invoke('select_files', {
      filters: [{ name: '提示词文件', extensions: ['txt'] }]
    })
    if (!paths) return
    for (const p of paths) {
      if (!txtFiles.value.includes(p)) txtFiles.value.push(p)
    }
  } catch (e) {
    console.error('文件选择器错误:', e)
  }
}

async function doTxtImport() {
  if (!txtFiles.value.length || txtImporting.value) return
  txtImporting.value = true
  txtImportResult.value = null
  txtFileResults.value = {}
  try {
    const result = await invoke('import_cases_from_txt', { filePaths: txtFiles.value })
    // map per-file results
    if (result.file_results) {
      for (const fr of result.file_results) {
        const match = txtFiles.value.find(f => f.endsWith(fr.file) || f.split('/').pop() === fr.file)
        if (match) txtFileResults.value[match] = fr
      }
    }
    txtImportResult.value = {
      ok: true,
      message: `导入完成！新增 ${result.imported} 个案例，跳过重复 ${result.skipped} 个，失败 ${result.failed} 个，案例库共 ${result.total_cases} 个`
    }
    await loadCases()
  } catch (e) {
    txtImportResult.value = { ok: false, message: `导入失败: ${e}` }
  } finally {
    txtImporting.value = false
  }
}

function closeTxtDialog() {
  showTxtDialog.value = false
  txtFiles.value = []
  txtImportResult.value = null
  txtFileResults.value = {}
}
</script>
