<template>
  <div class="p-8 overflow-y-auto h-full">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold">提示词库</h1>
        <p class="text-gray-500 text-sm mt-1">层级结构：事项 → 材料 → 要素 → 提示词</p>
      </div>
      <div class="flex gap-2">
        <button @click="showExcelDialog = true"
          class="flex items-center gap-1.5 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          导入 Excel
        </button>
        <button @click="loadCases"
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300">刷新</button>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="bg-white p-4 rounded-lg shadow mb-4 flex gap-3 items-center flex-wrap">
      <div class="flex-1 relative min-w-[200px]">
        <svg class="absolute left-3 top-2.5 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
        <input v-model="searchQuery" @input="onSearch" type="text" placeholder="搜索事项、材料、要素名称、提示词内容..."
          class="w-full pl-9 pr-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-300" />
      </div>
      <select v-model="filterItem" @change="onSearch"
        class="px-3 py-2 border rounded-lg text-sm text-gray-700 focus:outline-none min-w-[120px]">
        <option value="">全部事项</option>
        <option v-for="i in itemNames" :key="i" :value="i">{{ i }}</option>
      </select>
      <select v-model="filterMaterial" @change="onSearch"
        class="px-3 py-2 border rounded-lg text-sm text-gray-700 focus:outline-none min-w-[120px]">
        <option value="">全部材料</option>
        <option v-for="m in materialTypes" :key="m" :value="m">{{ m }}</option>
      </select>
      <span class="text-sm text-gray-500 whitespace-nowrap">共 {{ filteredCases.length }} 条要素</span>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <svg class="animate-spin w-6 h-6 text-blue-500 mr-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      <span class="text-gray-500">加载中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="allCases.length === 0" class="text-center py-20">
      <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
      </div>
      <div class="text-gray-500 font-medium mb-2">提示词库为空</div>
      <div class="text-gray-400 text-sm mb-6">点击「导入 Excel」按钮导入提示词案例</div>
    </div>

    <!-- 搜索无结果 -->
    <div v-else-if="filteredCases.length === 0" class="text-center py-16 text-gray-400 text-sm">
      未找到匹配的要素
    </div>

    <!-- 三级层级列表：事项 → 材料 → 要素 -->
    <div v-else class="space-y-4">
      <div v-for="itemGroup in pagedItemGroups" :key="itemGroup.item_name" class="bg-white rounded-xl shadow overflow-hidden">
        <!-- 事项标题（Level 1） -->
        <div class="flex items-center gap-3 px-5 py-3 bg-indigo-50 border-b cursor-pointer hover:bg-indigo-100 transition"
          @click="toggleItem(itemGroup.item_name)">
          <svg class="w-5 h-5 text-indigo-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
          </svg>
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <span class="font-bold text-gray-800">{{ itemGroup.item_name || '未分类事项' }}</span>
              <span class="text-xs text-gray-400">{{ itemGroup.materialCount }} 个材料 · {{ itemGroup.factorCount }} 个要素</span>
            </div>
          </div>
          <svg class="w-4 h-4 text-gray-400 transition-transform" :class="expandedItems.includes(itemGroup.item_name) ? 'rotate-180' : ''"
            fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </div>

        <!-- 材料列表（Level 2） -->
        <div v-if="expandedItems.includes(itemGroup.item_name)">
          <div v-for="matGroup in itemGroup.materials" :key="matGroup.material_name" class="border-b last:border-b-0">
            <div class="flex items-center gap-3 px-5 py-2.5 bg-gray-50 cursor-pointer hover:bg-gray-100 transition pl-10"
              @click="toggleMaterial(itemGroup.item_name + '::' + matGroup.material_name)">
              <svg class="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <div class="flex-1">
                <span class="font-semibold text-gray-700 text-sm">{{ matGroup.material_name || '未知材料' }}</span>
                <span class="text-xs text-gray-400 ml-2">{{ matGroup.factors.length }} 个要素</span>
              </div>
              <svg class="w-3.5 h-3.5 text-gray-400 transition-transform"
                :class="expandedMaterials.includes(itemGroup.item_name + '::' + matGroup.material_name) ? 'rotate-180' : ''"
                fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </div>

            <!-- 要素列表（Level 3） -->
            <div v-if="expandedMaterials.includes(itemGroup.item_name + '::' + matGroup.material_name)" class="divide-y divide-gray-100">
              <div v-for="(factor, fIdx) in matGroup.factors" :key="fIdx"
                class="px-5 py-3 hover:bg-gray-50 transition pl-16">
                <div class="flex items-start gap-3">
                  <div class="w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center text-xs text-blue-600 flex-shrink-0 mt-0.5">
                    {{ fIdx + 1 }}
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                      <span class="text-sm font-medium text-gray-800">{{ factor.factor_name }}</span>
                    </div>
                    <div v-if="factor.extract_desc" class="text-xs text-gray-400 mb-1">{{ factor.extract_desc }}</div>
                    <div v-if="factor.extraction_rule" class="text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded leading-relaxed"
                      :class="expandedRules.includes(factor.id) ? '' : 'line-clamp-2 cursor-pointer'"
                      @click="toggleRule(factor.id)">
                      {{ factor.extraction_rule }}
                    </div>
                  </div>
                  <button @click="deleteCase(factor)"
                    class="flex-shrink-0 p-1 text-gray-300 hover:text-red-500 rounded hover:bg-red-50 transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 pt-2">
        <button @click="page = Math.max(1, page - 1)" :disabled="page === 1"
          class="px-3 py-1 text-sm rounded border disabled:opacity-40 hover:bg-gray-100">上一页</button>
        <span class="text-sm text-gray-500">{{ page }} / {{ totalPages }}</span>
        <button @click="page = Math.min(totalPages, page + 1)" :disabled="page === totalPages"
          class="px-3 py-1 text-sm rounded border disabled:opacity-40 hover:bg-gray-100">下一页</button>
      </div>
    </div>

    <!-- Excel 导入对话框 -->
    <div v-if="showExcelDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl p-6 w-[520px] shadow-2xl">
        <h3 class="text-lg font-bold mb-1">导入事项 AI 配置 Excel</h3>
        <p class="text-sm text-gray-500 mb-4">从生产环境导出的 Excel 中提取要素提示词，导入到提示词库</p>
        <div class="space-y-4 mb-4">
          <div>
            <label class="block text-sm font-medium mb-1.5">选择 Excel 文件</label>
            <div class="flex gap-2">
              <input v-model="excelPath" type="text" placeholder="事项AI配置信息_xxx.xlsx"
                class="flex-1 px-3 py-2 border rounded text-sm" readonly />
              <button @click="selectExcelFile"
                class="px-3 py-2 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300 whitespace-nowrap">浏览</button>
            </div>
          </div>
          <label class="flex items-start gap-2 p-3 rounded-lg border cursor-pointer hover:bg-gray-50"
            :class="excelOverwrite ? 'border-orange-300 bg-orange-50' : ''">
            <input type="checkbox" v-model="excelOverwrite" class="mt-0.5" />
            <div><div class="text-sm font-medium">覆盖已有同名案例</div><div class="text-xs text-gray-500">勾选后会替换已存在的（事项+材料+要素）相同条目</div></div>
          </label>
        </div>
        <div v-if="excelResult" class="mb-4 px-3 py-2 rounded text-sm"
          :class="excelResult.ok ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'">
          {{ excelResult.message }}
        </div>
        <div class="flex justify-end gap-3">
          <button @click="closeExcelDialog" class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">关闭</button>
          <button @click="doExcelImport" :disabled="!excelPath || excelImporting"
            class="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50">
            {{ excelImporting ? '导入中...' : '确认导入' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div v-if="showDeleteConfirm" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl shadow-2xl p-6 max-w-sm mx-4">
        <h3 class="text-lg font-bold mb-2">确认删除？</h3>
        <p class="text-sm text-gray-500 mb-6">确定删除要素「{{ deletingCase?.factor_name }}」的提示词案例？此操作不可撤销。</p>
        <div class="flex gap-3 justify-end">
          <button @click="showDeleteConfirm = false; deletingCase = null" class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300">取消</button>
          <button @click="confirmDelete" class="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { invoke } from '../tauri/tauri.js'

// ─── 数据状态 ──────────────────────────────────────
const loading = ref(false)
const allCases = ref([])
const searchQuery = ref('')
const filterItem = ref('')
const filterMaterial = ref('')
const page = ref(1)
const PAGE_SIZE = 15

// ─── 展开状态 ──────────────────────────────────────
const expandedItems = ref([])
const expandedMaterials = ref([])
const expandedRules = ref([])

// 删除确认状态
const showDeleteConfirm = ref(false)
const deletingCase = ref(null)

// Excel 导入状态
const showExcelDialog = ref(false)
const excelPath = ref('')
const excelOverwrite = ref(false)
const excelImporting = ref(false)
const excelResult = ref(null)

// ─── 计算属性 ──────────────────────────────────────
const itemNames = computed(() => {
  const set = new Set(allCases.value.map(c => c.item_name).filter(Boolean))
  return Array.from(set).sort()
})

const materialTypes = computed(() => {
  let list = allCases.value
  if (filterItem.value) list = list.filter(c => c.item_name === filterItem.value)
  const set = new Set(list.map(c => c.material_name).filter(Boolean))
  return Array.from(set).sort()
})

const filteredCases = computed(() => {
  let list = allCases.value
  if (filterItem.value) {
    list = list.filter(c => c.item_name === filterItem.value)
  }
  if (filterMaterial.value) {
    list = list.filter(c => c.material_name === filterMaterial.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(c =>
      (c.item_name || '').toLowerCase().includes(q) ||
      (c.material_name || '').toLowerCase().includes(q) ||
      (c.factor_name || '').toLowerCase().includes(q) ||
      (c.extract_desc || '').toLowerCase().includes(q) ||
      (c.extraction_rule || '').toLowerCase().includes(q)
    )
  }
  return list
})

// 按 item_name → material_name 分组
const allItemGroups = computed(() => {
  const itemMap = new Map()
  for (const c of filteredCases.value) {
    const iName = c.item_name || ''
    if (!itemMap.has(iName)) {
      itemMap.set(iName, new Map())
    }
    const matMap = itemMap.get(iName)
    const mName = c.material_name || ''
    if (!matMap.has(mName)) {
      matMap.set(mName, [])
    }
    matMap.get(mName).push(c)
  }
  const result = []
  for (const [iName, matMap] of itemMap) {
    const materials = []
    let factorCount = 0
    for (const [mName, factors] of matMap) {
      materials.push({ material_name: mName, factors })
      factorCount += factors.length
    }
    result.push({ item_name: iName, materials, materialCount: materials.length, factorCount })
  }
  return result
})

const totalPages = computed(() => Math.max(1, Math.ceil(allItemGroups.value.length / PAGE_SIZE)))

const pagedItemGroups = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE
  return allItemGroups.value.slice(start, start + PAGE_SIZE)
})

// ─── 展开/折叠 ──────────────────────────────────────
function toggleItem(name) {
  const idx = expandedItems.value.indexOf(name)
  if (idx >= 0) expandedItems.value.splice(idx, 1)
  else expandedItems.value.push(name)
}
function toggleMaterial(key) {
  const idx = expandedMaterials.value.indexOf(key)
  if (idx >= 0) expandedMaterials.value.splice(idx, 1)
  else expandedMaterials.value.push(key)
}
function toggleRule(id) {
  const idx = expandedRules.value.indexOf(id)
  if (idx >= 0) expandedRules.value.splice(idx, 1)
  else expandedRules.value.push(id)
}

function onSearch() {
  page.value = 1
}

// ─── 生命周期 ──────────────────────────────────────
onMounted(() => {
  loadCases()
})

// ─── 数据加载 ──────────────────────────────────────
async function loadCases() {
  loading.value = true
  try {
    const lib = await invoke('load_case_library')
    const cases = lib.cases || []
    allCases.value = cases.map(c => ({
      item_name: c.item_name || '',
      material_name: c.material_name || c.material_type || '',
      factor_name: c.factor_name || c.fields?.[0]?.field_name || '',
      extract_desc: c.extract_desc || c.fields?.[0]?.description || '',
      extraction_rule: c.extraction_rule || c.fields?.[0]?.extraction_rule || '',
      tags: c.tags || [],
      id: c.id || null,
      _raw: c
    }))
    // 默认展开第一个事项
    if (allCases.value.length > 0 && expandedItems.value.length === 0) {
      const firstName = allCases.value[0].item_name || ''
      expandedItems.value = [firstName]
    }
  } catch (e) {
    console.error('load_case_library failed:', e)
    allCases.value = []
  } finally {
    loading.value = false
  }
}

function deleteCase(c) {
  if (!c.id) {
    alert('该案例无法删除（缺少 ID）')
    return
  }
  deletingCase.value = c
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  const c = deletingCase.value
  if (!c) return
  try {
    await invoke('delete_case', { caseId: c.id })
    await loadCases()
  } catch (e) {
    alert(`删除失败: ${e}`)
  } finally {
    showDeleteConfirm.value = false
    deletingCase.value = null
  }
}

// ─── Excel 导入 ──────────────────────────────────────
async function selectExcelFile() {
  try {
    const selected = await invoke('select_file', {
      filters: [{ name: 'Excel', extensions: ['xlsx', 'xls'] }]
    })
    if (selected) excelPath.value = selected
  } catch (e) { console.error(e) }
}

async function doExcelImport() {
  if (!excelPath.value || excelImporting.value) return
  excelImporting.value = true
  excelResult.value = null
  try {
    const result = await invoke('import_cases_excel', {
      filePath: excelPath.value,
      overwrite: excelOverwrite.value
    })
    const s = result.summary || {}
    excelResult.value = {
      ok: true,
      message: `导入成功！事项「${result.item_name || ''}」${s.material_count || 0} 个材料、${s.factor_count || 0} 个要素。新增 ${result.imported} 个，跳过 ${result.skipped} 个，库总计 ${result.total_cases} 条`
    }
    await loadCases()
  } catch (e) {
    excelResult.value = { ok: false, message: `导入失败: ${e}` }
  } finally {
    excelImporting.value = false
  }
}

function closeExcelDialog() {
  showExcelDialog.value = false
  excelPath.value = ''
  excelResult.value = null
  excelOverwrite.value = false
}
</script>
