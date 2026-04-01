<template>
  <div class="p-8 overflow-y-auto h-full">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold">审查规则库</h1>
        <p class="text-gray-500 text-sm mt-1">管理审查规则 JSON，支持导入、搜索查询、JSON 模板参考</p>
      </div>
      <div class="flex gap-2">
        <button @click="showTemplates = !showTemplates"
          class="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm transition"
          :class="showTemplates ? 'bg-amber-100 text-amber-700 border border-amber-300' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          JSON 模板
        </button>
        <button @click="showImportDialog = true"
          class="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
          </svg>
          导入 JSON
        </button>
        <button @click="loadLibrary"
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300">刷新</button>
        <button v-if="allRules.length > 0" @click="showClearConfirm = true"
          class="px-4 py-2 bg-red-50 text-red-600 rounded-lg text-sm hover:bg-red-100 border border-red-200">清空</button>
      </div>
    </div>

    <!-- JSON 模板面板 -->
    <div v-if="showTemplates" class="bg-white rounded-xl shadow mb-6 overflow-hidden">
      <div class="flex border-b">
        <button v-for="t in templateTabs" :key="t.key"
          @click="activeTemplate = t.key"
          class="px-5 py-3 text-sm font-medium transition border-b-2 -mb-px"
          :class="activeTemplate === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'">
          {{ t.label }}
        </button>
      </div>
      <div class="p-4 relative">
        <button @click="copyTemplate"
          class="absolute top-3 right-3 px-3 py-1 text-xs rounded transition"
          :class="copiedTemplate ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'">
          {{ copiedTemplate ? '已复制' : '复制' }}
        </button>
        <pre class="text-xs text-gray-700 overflow-x-auto max-h-80 leading-relaxed pr-16">{{ currentTemplateContent }}</pre>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="bg-white p-4 rounded-lg shadow mb-4 flex gap-3 items-center">
      <div class="flex-1 relative">
        <svg class="absolute left-3 top-2.5 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
        <input v-model="searchQuery" type="text" placeholder="搜索材料名称、审查要点名称、规则说明..."
          class="w-full pl-9 pr-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-300" />
      </div>
      <select v-model="filterMaterial"
        class="px-3 py-2 border rounded-lg text-sm text-gray-700 focus:outline-none min-w-32">
        <option value="">全部材料</option>
        <option v-for="m in materialNames" :key="m" :value="m">{{ m }}</option>
      </select>
      <select v-model="filterRuleType"
        class="px-3 py-2 border rounded-lg text-sm text-gray-700 focus:outline-none">
        <option value="">全部类型</option>
        <option value="1">大模型 (1)</option>
        <option value="2">规则对比 (2)</option>
        <option value="3">Groovy脚本 (3)</option>
      </select>
      <span class="text-sm text-gray-500 whitespace-nowrap">共 {{ filteredKeypoints.length }} 条要点</span>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <svg class="animate-spin w-6 h-6 text-blue-500 mr-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      <span class="text-gray-500 text-sm">加载中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="allRules.length === 0" class="text-center py-20">
      <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
        </svg>
      </div>
      <div class="text-gray-500 font-medium mb-2">审查规则库为空</div>
      <div class="text-gray-400 text-sm mb-6">点击「导入 JSON」按钮导入审查规则文件</div>
      <button @click="showImportDialog = true"
        class="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
        导入 JSON
      </button>
    </div>

    <!-- 搜索无结果 -->
    <div v-else-if="filteredKeypoints.length === 0" class="text-center py-16 text-gray-400 text-sm">
      未找到匹配的审查要点
    </div>

    <!-- 要点列表（按材料分组展示） -->
    <div v-else class="space-y-4">
      <div v-for="group in groupedKeypoints" :key="group.materialname" class="bg-white rounded-xl shadow overflow-hidden">
        <!-- 材料标题 -->
        <div class="flex items-center gap-3 px-5 py-3 bg-gray-50 border-b cursor-pointer hover:bg-gray-100 transition"
          @click="toggleGroup(group.materialname)">
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <span class="font-semibold text-gray-800">{{ group.materialname }}</span>
              <span class="text-xs text-gray-400">{{ group.keypoints.length }} 个要点</span>
              <div class="flex gap-1">
                <span v-if="group.counts[2]" class="px-1.5 py-0.5 bg-blue-100 text-blue-600 rounded text-xs">规则对比×{{ group.counts[2] }}</span>
                <span v-if="group.counts[1]" class="px-1.5 py-0.5 bg-purple-100 text-purple-600 rounded text-xs">大模型×{{ group.counts[1] }}</span>
                <span v-if="group.counts[3]" class="px-1.5 py-0.5 bg-orange-100 text-orange-600 rounded text-xs">Groovy×{{ group.counts[3] }}</span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button @click.stop="copyMaterialJson(group)"
              class="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs transition"
              :class="copiedMaterial === group.materialname ? 'bg-green-100 text-green-700' : 'bg-white text-gray-600 hover:bg-gray-200 border'">
              {{ copiedMaterial === group.materialname ? '已复制' : '复制JSON' }}
            </button>
            <button @click.stop="deleteMaterial(group.materialname)"
              class="flex items-center gap-1 px-2.5 py-1 bg-white border text-red-500 rounded-lg text-xs hover:bg-red-50 transition">
              删除
            </button>
            <svg class="w-4 h-4 text-gray-400 transition-transform"
              :class="expandedGroups.includes(group.materialname) ? 'rotate-180' : ''"
              fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </div>
        </div>

        <!-- 要点行 -->
        <div v-if="expandedGroups.includes(group.materialname)" class="divide-y">
          <div v-for="(kp, idx) in group.keypoints" :key="idx"
            class="px-5 py-3 hover:bg-gray-50 transition">
            <div class="flex items-start gap-3">
              <div class="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs text-gray-500 flex-shrink-0 mt-0.5">
                {{ idx + 1 }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap mb-1">
                  <span class="text-sm font-medium text-gray-800">{{ kp.kpname }}</span>
                  <span class="px-2 py-0.5 rounded-full text-xs font-medium"
                    :class="getRuleTypeClass(kp.review_rule)">
                    {{ getRuleTypeLabel(kp.review_rule) }}
                  </span>
                </div>
                <div v-if="kp.review_rule_text" class="text-xs text-gray-400 mb-1">
                  {{ kp.review_rule_text }}
                </div>
                <div v-if="kp.content && kp.review_rule === '1'" class="text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded line-clamp-2">
                  {{ kp.content }}
                </div>
                <!-- 规则对比条件预览 -->
                <div v-if="kp.review_rule === '2' && kp.review_conditions?.groups?.length" class="text-xs text-blue-600 mt-1">
                  <span v-for="(g, gi) in kp.review_conditions.groups" :key="gi">
                    <span v-for="(c, ci) in g.conditions" :key="ci">
                      {{ c.elementA }} {{ operatorLabel(c.operator) }} {{ c.elementB }}
                      <span v-if="ci < g.conditions.length - 1"> {{ c.logicToNext || 'AND' }} </span>
                    </span>
                    <span v-if="gi < kp.review_conditions.groups.length - 1"> | </span>
                  </span>
                </div>
              </div>
              <!-- 查看 JSON -->
              <button @click="toggleKeypointJson(group.materialname, idx)"
                class="flex-shrink-0 px-2.5 py-1 rounded-lg text-xs transition border"
                :class="activeKeypointJson === `${group.materialname}:${idx}`
                  ? 'bg-blue-50 border-blue-300 text-blue-700'
                  : 'bg-white border-gray-200 text-gray-500 hover:border-gray-300'">
                {{ activeKeypointJson === `${group.materialname}:${idx}` ? '收起' : '查看JSON' }}
              </button>
            </div>
            <!-- 要点 JSON 展开 -->
            <div v-if="activeKeypointJson === `${group.materialname}:${idx}`" class="mt-2 ml-9 relative">
              <button @click="copyKeypointJson(kp, group.materialname, idx)"
                class="absolute top-2 right-2 px-2 py-0.5 text-xs rounded transition z-10"
                :class="copiedKp === `${group.materialname}:${idx}` ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'">
                {{ copiedKp === `${group.materialname}:${idx}` ? '已复制' : '复制' }}
              </button>
              <pre class="text-xs text-gray-600 bg-gray-50 border rounded-lg p-3 overflow-x-auto max-h-64 leading-relaxed">{{ JSON.stringify(kp, null, 2) }}</pre>
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

    <!-- 导入对话框 -->
    <div v-if="showImportDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4">
        <div class="flex items-center justify-between px-6 py-4 border-b">
          <h2 class="text-lg font-bold">导入审查规则 JSON</h2>
          <button @click="closeImportDialog" class="text-gray-400 hover:text-gray-600">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="px-6 py-5 space-y-4">
          <!-- 导入模式 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">导入模式</label>
            <div class="grid grid-cols-2 gap-2">
              <label v-for="opt in importModeOptions" :key="opt.value"
                class="flex items-start gap-2 p-3 border rounded-lg cursor-pointer transition"
                :class="importMode === opt.value ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'">
                <input type="radio" v-model="importMode" :value="opt.value" class="mt-0.5 flex-shrink-0" />
                <div>
                  <div class="text-sm font-medium text-gray-800">{{ opt.label }}</div>
                  <div class="text-xs text-gray-400 mt-0.5">{{ opt.desc }}</div>
                </div>
              </label>
            </div>
          </div>

          <!-- 文件选择 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">选择 JSON 文件（可多选）</label>
            <div class="flex gap-2">
              <input v-model="importPathDisplay" type="text" readonly
                placeholder="点击「选择文件」选择一个或多个 JSON 文件"
                class="flex-1 px-3 py-2 border rounded-lg text-sm bg-gray-50 text-gray-600" />
              <button @click="selectJsonFiles"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 whitespace-nowrap">
                选择文件
              </button>
            </div>
            <div v-if="importFiles.length > 0" class="mt-2 space-y-1">
              <div v-for="(f, i) in importFiles" :key="i"
                class="flex items-center gap-2 px-3 py-1.5 bg-gray-50 rounded text-xs text-gray-600">
                <svg class="w-3.5 h-3.5 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <span class="flex-1 truncate">{{ f.split('/').pop() }}</span>
                <span v-if="importFileResults[f]" class="px-1.5 py-0.5 rounded text-xs font-medium"
                  :class="importFileResults[f].error ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-700'">
                  {{ importFileResults[f].error || `+${importFileResults[f].added}` }}
                </span>
                <button @click="importFiles.splice(i, 1)" class="text-gray-300 hover:text-red-400">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- 导入结果摘要 -->
          <div v-if="importResult" class="px-4 py-3 rounded-lg text-sm"
            :class="importResult.ok ? 'bg-green-50 border border-green-200 text-green-800' : 'bg-red-50 border border-red-200 text-red-700'">
            {{ importResult.message }}
          </div>
        </div>
        <div class="px-6 py-4 border-t flex justify-between items-center">
          <span v-if="importing" class="flex items-center gap-1.5 text-sm text-blue-600">
            <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            导入中...
          </span>
          <span v-else class="text-xs text-gray-400">
            {{ importMode === 'merge' ? '增量合并：相同材料名则合并要点，不重复' : '覆盖：同名材料整体替换' }}
          </span>
          <div class="flex gap-3">
            <button @click="closeImportDialog" class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 text-sm">关闭</button>
            <button @click="doImport" :disabled="importFiles.length === 0 || importing"
              class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm font-medium">
              {{ importing ? '导入中...' : `导入 ${importFiles.length} 个文件` }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 清空确认 -->
    <div v-if="showClearConfirm" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl shadow-2xl p-6 max-w-sm mx-4">
        <h3 class="text-lg font-bold mb-2">确认清空？</h3>
        <p class="text-sm text-gray-500 mb-6">将删除审查规则库中所有 {{ allRules.length }} 条材料规则，此操作不可撤销。</p>
        <div class="flex gap-3 justify-end">
          <button @click="showClearConfirm = false" class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300">取消</button>
          <button @click="clearLibrary" class="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700">确认清空</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiClient } from '../services/apiClient.js'
import { parseJsonFilePayload } from '../services/jsonFile.js'
import { invoke } from '../tauri/tauri.js'

// ─── 数据状态 ──────────────────────────────────────
const loading = ref(false)
const allRules = ref([])   // [{ materialname, keypoints[] }]
const searchQuery = ref('')
const filterMaterial = ref('')
const filterRuleType = ref('')
const page = ref(1)
const PAGE_SIZE = 10

// ─── 展开状态 ──────────────────────────────────────
const expandedGroups = ref([])
const activeKeypointJson = ref(null)
const copiedMaterial = ref(null)
const copiedKp = ref(null)

// ─── 模板 ──────────────────────────────────────────
const showTemplates = ref(false)
const activeTemplate = ref('rule2')
const copiedTemplate = ref(false)

const templateTabs = [
  { key: 'rule2', label: '规则对比（review_rule=2）' },
  { key: 'rule1', label: '大模型（review_rule=1）' },
  { key: 'rule3', label: 'Groovy脚本（review_rule=3）' },
]

const TEMPLATES = {
  rule2: {
    materialname: '{{材料名称}}',
    keypoints: [{
      kpname: '{{审查要点名称}}',
      content: '',
      review_rule_text: '{{审查规则描述}}',
      passreason: '',
      nopassreason: '',
      review_rule: '2',
      review_conditions: {
        groups: [{
          logicToNext: null,
          groupFailReason: '{{材料A}}:{{字段A}}【&${{材料A}}:{{字段A}}$@】应等于【&${{材料B}}:{{字段B}}$@】',
          conditions: [{
            elementA: '${{材料A}}:{{字段A}}$',
            elementAType: 'factor',
            elementADisplay: '${{材料A}}:{{字段A}}$',
            operator: 'eq',
            dataType: 'string',
            elementB: '${{材料B}}:{{字段B}}$',
            elementBType: 'factor',
            elementBDisplay: '${{材料B}}:{{字段B}}$',
            logicToNext: null,
            stringReplacements: null,
            delimiter: null,
            arrayKeys: null
          }]
        }]
      },
      is_point: '0',
      is_contrast: '1',
      pre_rule_enabled: 0,
      pre_conditions: null
    }]
  },
  rule1: {
    materialname: '{{材料名称}}',
    keypoints: [{
      kpname: '{{审查要点名称}}',
      content: '{{LLM提示词，可使用$材料:字段$引用要素}}',
      nopassreason: '{{审核不通过原因}}',
      passreason: '{{审核通过原因}}',
      review_rule: '1',
      is_point: '0'
    }]
  },
  rule3: {
    materialname: '{{材料名称}}',
    keypoints: [{
      kpname: '{{审查要点名称}}',
      content: '',
      review_rule: '3',
      review_rule_js: 'def value = input.get("{{材料}}:{{字段}}")\nif (value == null || value.isEmpty()) {\n    return [pass: false, reason: "{{字段}}未识别到"]\n}\n// TODO: 实现审查逻辑\nreturn [pass: true, reason: "审查通过"]',
      nopassreason: '{{审核不通过原因}}',
      passreason: '{{审核通过原因}}'
    }]
  }
}

const currentTemplateContent = computed(() =>
  JSON.stringify(TEMPLATES[activeTemplate.value] || {}, null, 2)
)

// ─── 导入状态 ──────────────────────────────────────
const showImportDialog = ref(false)
const importMode = ref('merge')
const importFiles = ref([])
const importPathDisplay = ref('')
const importing = ref(false)
const importResult = ref(null)
const importFileResults = ref({})
const showClearConfirm = ref(false)

const importModeOptions = [
  { value: 'merge', label: '增量合并', desc: '相同材料名则合并要点，不重复导入' },
  { value: 'overwrite', label: '覆盖导入', desc: '同名材料整体替换，保留其他材料' },
]

// ─── 计算属性 ──────────────────────────────────────
const materialNames = computed(() => {
  const set = new Set(allRules.value.map(r => r.materialname).filter(Boolean))
  return Array.from(set).sort()
})

// 所有要点扁平化，带材料名
const allKeypoints = computed(() => {
  const result = []
  for (const rule of allRules.value) {
    for (const kp of (rule.keypoints || [])) {
      result.push({ ...kp, _materialname: rule.materialname })
    }
  }
  return result
})

const filteredKeypoints = computed(() => {
  let list = allKeypoints.value
  if (filterMaterial.value) {
    list = list.filter(k => k._materialname === filterMaterial.value)
  }
  if (filterRuleType.value) {
    list = list.filter(k => k.review_rule === filterRuleType.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(k =>
      (k._materialname || '').toLowerCase().includes(q) ||
      (k.kpname || '').toLowerCase().includes(q) ||
      (k.review_rule_text || '').toLowerCase().includes(q) ||
      (k.content || '').toLowerCase().includes(q)
    )
  }
  return list
})

// 将过滤后要点重新按材料分组
const groupedKeypoints = computed(() => {
  const map = new Map()
  for (const kp of pagedKeypoints.value) {
    if (!map.has(kp._materialname)) {
      map.set(kp._materialname, { materialname: kp._materialname, keypoints: [], counts: {} })
    }
    const g = map.get(kp._materialname)
    g.keypoints.push(kp)
    const rt = Number(kp.review_rule)
    g.counts[rt] = (g.counts[rt] || 0) + 1
  }
  return Array.from(map.values())
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredKeypoints.value.length / PAGE_SIZE)))

const pagedKeypoints = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE
  return filteredKeypoints.value.slice(start, start + PAGE_SIZE)
})

// ─── 展开分组 ──────────────────────────────────────
function toggleGroup(materialname) {
  const idx = expandedGroups.value.indexOf(materialname)
  if (idx >= 0) expandedGroups.value.splice(idx, 1)
  else expandedGroups.value.push(materialname)
}

function toggleKeypointJson(material, idx) {
  const key = `${material}:${idx}`
  activeKeypointJson.value = activeKeypointJson.value === key ? null : key
}

// ─── 工具函数 ──────────────────────────────────────
function getRuleTypeLabel(v) {
  return { '1': '大模型', '2': '规则对比', '3': 'Groovy脚本' }[v] || v
}
function getRuleTypeClass(v) {
  return {
    '1': 'bg-purple-100 text-purple-700',
    '2': 'bg-blue-100 text-blue-700',
    '3': 'bg-orange-100 text-orange-700',
  }[v] || 'bg-gray-100 text-gray-600'
}
function operatorLabel(op) {
  return { eq: '=', neq: '≠', gt: '>', gte: '≥', lt: '<', lte: '≤', contains: '包含', notContains: '不含' }[op] || op
}

// ─── 存储层（服务端持久化） ────────────────────────
async function saveLibrary() {
  try {
    await invoke('save_review_rule_library', { rules: allRules.value })
  } catch (e) {
    console.error('保存失败', e)
    throw e
  }
}

async function loadLibrary() {
  loading.value = true
  try {
    const data = await invoke('load_review_rule_library')
    allRules.value = Array.isArray(data) ? data : []
    // 默认展开第一个材料
    if (allRules.value.length > 0 && expandedGroups.value.length === 0) {
      expandedGroups.value = [allRules.value[0].materialname]
    }
  } catch (e) {
    allRules.value = []
    console.error('加载失败', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadLibrary() })

// ─── 导入逻辑 ──────────────────────────────────────
async function selectJsonFiles() {
  try {
    const selected = await invoke('select_files', { filters: [{ name: 'JSON', extensions: ['json'] }] })
    if (!selected || selected.length === 0) return
    importFiles.value = selected
    importPathDisplay.value = selected.length === 1
      ? selected[0].split('/').pop()
      : `已选择 ${selected.length} 个文件`
    importFileResults.value = {}
    importResult.value = null
  } catch (e) {
    console.error('选择文件失败', e)
  }
}

async function doImport() {
  if (!importFiles.value.length || importing.value) return
  importing.value = true
  importResult.value = null
  importFileResults.value = {}

  let totalAdded = 0
  let totalFailed = 0

  for (const filePath of importFiles.value) {
    try {
      const raw = await invoke('read_json_file', { path: filePath })
      const data = parseJsonFilePayload(raw)

      // 支持单个材料对象 { materialname, keypoints } 或数组
      const items = Array.isArray(data) ? data : [data]
      let addedCount = 0

      for (const item of items) {
        if (!item.materialname || !Array.isArray(item.keypoints)) continue

        const existingIdx = allRules.value.findIndex(r => r.materialname === item.materialname)

        if (existingIdx >= 0) {
          if (importMode.value === 'overwrite') {
            allRules.value[existingIdx] = item
            addedCount += item.keypoints.length
          } else {
            // merge: 按 kpname 去重
            const existingKpNames = new Set(allRules.value[existingIdx].keypoints.map(k => k.kpname))
            const newKps = item.keypoints.filter(k => !existingKpNames.has(k.kpname))
            allRules.value[existingIdx].keypoints.push(...newKps)
            addedCount += newKps.length
          }
        } else {
          allRules.value.push(item)
          addedCount += item.keypoints.length
        }
      }

      importFileResults.value[filePath] = { added: addedCount }
      totalAdded += addedCount
    } catch (e) {
      importFileResults.value[filePath] = { error: String(e).slice(0, 40) }
      totalFailed++
    }
  }

  try {
    await saveLibrary()
    importResult.value = {
      ok: totalFailed === 0,
      message: totalFailed === 0
        ? `导入成功！共新增 ${totalAdded} 个审查要点，库中现有 ${allRules.value.length} 个材料`
        : `部分导入失败（${totalFailed} 个文件），成功新增 ${totalAdded} 个要点`
    }

    // 展开第一个导入的材料
    if (allRules.value.length > 0 && expandedGroups.value.length === 0) {
      expandedGroups.value = [allRules.value[0].materialname]
    }
  } catch (error) {
    importResult.value = {
      ok: false,
      message: `导入结果保存失败：${error}`
    }
  } finally {
    importing.value = false
  }
}

function closeImportDialog() {
  showImportDialog.value = false
  importFiles.value = []
  importPathDisplay.value = ''
  importResult.value = null
  importFileResults.value = {}
}

async function deleteMaterial(materialname) {
  allRules.value = allRules.value.filter(r => r.materialname !== materialname)
  expandedGroups.value = expandedGroups.value.filter(m => m !== materialname)
  try {
    await saveLibrary()
  } catch (error) {
    console.error(error)
  }
}

async function clearLibrary() {
  allRules.value = []
  expandedGroups.value = []
  activeKeypointJson.value = null
  try {
    await invoke('clear_review_rule_library')
  } catch (error) {
    console.error(error)
  }
  showClearConfirm.value = false
}

// ─── 复制 ──────────────────────────────────────────
async function copyMaterialJson(group) {
  try {
    const rule = allRules.value.find(r => r.materialname === group.materialname)
    if (!rule) return
    await navigator.clipboard.writeText(JSON.stringify(rule, null, 2))
    copiedMaterial.value = group.materialname
    setTimeout(() => { copiedMaterial.value = null }, 2000)
  } catch (e) { console.error(e) }
}

async function copyKeypointJson(kp, material, idx) {
  try {
    const { _materialname, ...rest } = kp
    await navigator.clipboard.writeText(JSON.stringify(rest, null, 2))
    copiedKp.value = `${material}:${idx}`
    setTimeout(() => { copiedKp.value = null }, 2000)
  } catch (e) { console.error(e) }
}

async function copyTemplate() {
  try {
    await navigator.clipboard.writeText(currentTemplateContent.value)
    copiedTemplate.value = true
    setTimeout(() => { copiedTemplate.value = false }, 2000)
  } catch (e) { console.error(e) }
}
</script>
