<template>
  <Transition name="repair-desk">
    <div
      v-if="open"
      class="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-sm"
      @click.self="requestClose"
    >
      <div class="flex h-full w-full xl:justify-end">
        <div class="flex h-full w-full flex-col bg-white xl:max-w-[calc(100vw-48px)]">
          <header class="border-b border-slate-200 bg-white/95 px-5 py-5 backdrop-blur sm:px-6">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div class="max-w-3xl">
                <p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                  Workspace Validation
                </p>
                <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                  工作区校验与修复台
                </h2>
                <p class="mt-2 text-sm leading-6 text-slate-500">
                  这里会集中展示当前工作区的校验问题。左侧是问题导航，右侧是 factors.xlsx 修复区；保存后会立即重新校验，再返回业务页继续。
                </p>
              </div>

              <div class="flex flex-wrap gap-2">
                <button
                  type="button"
                  class="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                  @click="downloadWorkbook"
                >
                  下载修复后的 factors.xlsx
                </button>
                <button
                  type="button"
                  class="rounded-xl bg-slate-900 px-3.5 py-2 text-xs font-medium text-white transition hover:bg-slate-800"
                  @click="requestClose"
                >
                  返回业务页继续
                </button>
              </div>
            </div>
          </header>

          <div class="flex min-h-0 flex-1 flex-col xl:flex-row">
            <aside class="border-b border-slate-200 bg-slate-50/80 xl:w-80 xl:flex-shrink-0 xl:border-b-0 xl:border-r">
              <div class="flex h-full min-h-0 flex-col px-4 py-4 sm:px-5">
                <div class="grid grid-cols-3 gap-2">
                  <div class="rounded-2xl border border-slate-200 bg-white px-3 py-3">
                    <p class="text-[11px] uppercase tracking-[0.18em] text-slate-400">问题</p>
                    <p class="mt-2 text-xl font-semibold text-slate-900">{{ issueList.length }}</p>
                  </div>
                  <div class="rounded-2xl border border-slate-200 bg-white px-3 py-3">
                    <p class="text-[11px] uppercase tracking-[0.18em] text-slate-400">列数</p>
                    <p class="mt-2 text-xl font-semibold text-slate-900">{{ localHeaders.length }}</p>
                  </div>
                  <div class="rounded-2xl border border-slate-200 bg-white px-3 py-3">
                    <p class="text-[11px] uppercase tracking-[0.18em] text-slate-400">行数</p>
                    <p class="mt-2 text-xl font-semibold text-slate-900">{{ localRows.length }}</p>
                  </div>
                </div>

                <div class="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-xs font-semibold text-slate-800">问题导航</p>
                      <p class="mt-1 text-[11px] leading-5 text-slate-500">
                        点选问题后会自动定位到对应列或单元格。
                      </p>
                    </div>
                    <button
                      type="button"
                      class="rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] font-medium text-slate-500 transition hover:bg-slate-50"
                      @click="reloadWorkbook"
                    >
                      重新载入
                    </button>
                  </div>

                  <div class="mt-4 space-y-4 overflow-y-auto xl:max-h-[calc(100vh-280px)]">
                    <section v-for="group in issueGroups" :key="group.id">
                      <div class="mb-2 flex items-center justify-between">
                        <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                          {{ group.title }}
                        </p>
                        <span class="text-[11px] text-slate-400">{{ group.items.length }}</span>
                      </div>
                      <div class="space-y-2">
                        <button
                          v-for="issue in group.items"
                          :key="issue.id"
                          type="button"
                          class="w-full rounded-2xl border px-3 py-3 text-left transition"
                          :class="selectedIssueId === issue.id
                            ? 'border-slate-900 bg-slate-900 text-white shadow-sm'
                            : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50'"
                          @click="focusIssue(issue)"
                        >
                          <div class="flex items-start justify-between gap-3">
                            <div class="min-w-0">
                              <p class="text-xs font-semibold">
                                {{ issue.message }}
                              </p>
                              <p
                                class="mt-1 text-[11px] leading-5"
                                :class="selectedIssueId === issue.id ? 'text-slate-300' : 'text-slate-400'"
                              >
                                {{ issueCaption(issue) }}
                              </p>
                            </div>
                            <span
                              class="rounded-full px-2 py-1 text-[10px] font-semibold"
                              :class="selectedIssueId === issue.id ? 'bg-white/10 text-white' : issueToneClass(issue)"
                            >
                              {{ issueTag(issue) }}
                            </span>
                          </div>
                        </button>
                      </div>
                    </section>

                    <div
                      v-if="issueList.length === 0"
                      class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm leading-6 text-emerald-700"
                    >
                      当前没有待处理的校验问题。你可以继续返回业务页，也可以下载修复后的 factors.xlsx。
                    </div>
                  </div>
                </div>
              </div>
            </aside>

            <main class="min-h-0 flex-1 overflow-auto bg-slate-50">
              <div class="mx-auto flex max-w-[1500px] flex-col gap-4 px-4 py-4 sm:px-6">
                <div
                  ref="toolbarAnchor"
                  data-repair-target="toolbar-anchor"
                  class="rounded-2xl border border-slate-200 bg-white p-4"
                  :class="focusedTargetId === 'toolbar-anchor' ? 'ring-2 ring-blue-200' : ''"
                >
                  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p class="text-sm font-semibold text-slate-900">{{ currentFileName }}</p>
                      <p class="mt-1 text-xs leading-5 text-slate-500">
                        优先处理左侧导航中的问题，再保存并重新校验。缺列问题可直接点“补齐必需列”快速补全。
                      </p>
                    </div>
                    <div class="flex flex-wrap gap-2">
                      <button
                        type="button"
                        class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                        @click="addRow"
                      >
                        新增行
                      </button>
                      <button
                        type="button"
                        class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                        @click="addColumn"
                      >
                        新增列
                      </button>
                      <button
                        type="button"
                        class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                        @click="addMissingRequiredColumns"
                      >
                        补齐必需列
                      </button>
                      <button
                        type="button"
                        class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                        @click="reloadWorkbook"
                      >
                        放弃未保存修改
                      </button>
                      <button
                        type="button"
                        class="rounded-xl bg-blue-600 px-3 py-2 text-xs font-medium text-white transition hover:bg-blue-700 disabled:opacity-60"
                        :disabled="saving"
                        @click="saveWorkbook"
                      >
                        {{ saving ? '保存中...' : '保存并重新校验' }}
                      </button>
                    </div>
                  </div>

                  <div class="mt-4 flex flex-wrap gap-2 text-[11px] text-slate-500">
                    <span class="rounded-full bg-slate-100 px-2.5 py-1">{{ workbook.exists ? '已读取工作簿' : '尚未读取工作簿' }}</span>
                    <span v-if="hasDraftChanges" class="rounded-full bg-amber-50 px-2.5 py-1 text-amber-700">有未保存修改</span>
                    <span v-if="selectedIssue" class="rounded-full bg-blue-50 px-2.5 py-1 text-blue-700">
                      当前定位：{{ issueCaption(selectedIssue) }}
                    </span>
                  </div>
                </div>

                <div
                  v-if="loadError"
                  class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-700"
                >
                  {{ loadError }}
                </div>
                <div
                  v-else-if="loading"
                  class="rounded-2xl border border-slate-200 bg-white px-4 py-10 text-center text-sm text-slate-500"
                >
                  正在读取 factors.xlsx...
                </div>
                <div
                  v-else-if="statusMessage"
                  class="rounded-2xl border px-4 py-3 text-sm leading-6"
                  :class="statusTone === 'success'
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : 'border-amber-200 bg-amber-50 text-amber-700'"
                >
                  {{ statusMessage }}
                </div>

                <div v-if="selectedIssueAdvice" class="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                  <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">当前建议</p>
                  <p class="mt-2 text-sm leading-6 text-slate-600">{{ selectedIssueAdvice }}</p>
                </div>

                <div class="overflow-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
                  <table class="min-w-full divide-y divide-slate-200 text-left text-xs">
                    <thead class="bg-slate-50">
                      <tr>
                        <th class="min-w-20 px-3 py-3 font-semibold text-slate-600">行号</th>
                        <th
                          v-for="(header, columnIndex) in localHeaders"
                          :key="`header-${columnIndex}`"
                          class="min-w-56 px-3 py-3 align-top"
                        >
                          <div
                            class="rounded-2xl border border-transparent p-2 transition"
                            :class="focusedTargetId === headerTargetId(columnIndex) ? 'border-blue-200 bg-blue-50' : ''"
                            :data-repair-target="headerTargetId(columnIndex)"
                          >
                            <div class="flex items-start gap-2">
                              <input
                                v-model="localHeaders[columnIndex]"
                                type="text"
                                class="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200"
                                placeholder="列名"
                              />
                              <button
                                type="button"
                                class="rounded-md border border-slate-200 px-2 py-1 text-[11px] text-slate-500 transition hover:bg-slate-100 disabled:opacity-40"
                                :disabled="localHeaders.length === 1"
                                @click="removeColumn(columnIndex)"
                              >
                                删列
                              </button>
                            </div>
                            <p
                              v-for="(item, index) in headerDiagnostics(columnIndex)"
                              :key="`header-diagnostic-${columnIndex}-${index}`"
                              class="mt-2 rounded-xl bg-red-100 px-2 py-2 text-[11px] leading-4 text-red-600"
                            >
                              {{ item.message }}
                            </p>
                          </div>
                        </th>
                        <th class="w-24 px-3 py-3 font-semibold text-slate-600">操作</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-200 bg-white">
                      <tr v-if="localRows.length === 0">
                        <td :colspan="localHeaders.length + 2" class="px-4 py-10 text-center text-sm text-slate-400">
                          暂无数据行，可以先新增行再补录材料、要素和审查要点信息。
                        </td>
                      </tr>
                      <tr v-for="(row, rowIndex) in localRows" :key="row.clientId" class="align-top">
                        <td class="px-3 py-3 text-slate-500">
                          {{ row.rowNumber || `新增${rowIndex + 1}` }}
                        </td>
                        <td
                          v-for="(header, columnIndex) in localHeaders"
                          :key="`${row.clientId}-${columnIndex}`"
                          class="px-3 py-3"
                        >
                          <div
                            class="rounded-2xl border border-transparent p-2 transition"
                            :class="focusedTargetId === cellTargetId(row.rowNumber, columnIndex) ? 'border-blue-200 bg-blue-50' : ''"
                            :data-repair-target="cellTargetId(row.rowNumber, columnIndex)"
                          >
                            <textarea
                              v-if="isLongTextColumn(header)"
                              v-model="row.values[columnIndex]"
                              rows="3"
                              class="w-full rounded-lg border px-2.5 py-2 text-xs leading-5 text-slate-700 focus:outline-none focus:ring-2"
                              :class="cellInputClass(row.rowNumber, columnIndex)"
                              placeholder="请输入内容"
                            />
                            <input
                              v-else
                              v-model="row.values[columnIndex]"
                              type="text"
                              class="w-full rounded-lg border px-2.5 py-2 text-xs text-slate-700 focus:outline-none focus:ring-2"
                              :class="cellInputClass(row.rowNumber, columnIndex)"
                              placeholder="请输入内容"
                            />
                            <p
                              v-for="(item, index) in cellDiagnostics(row.rowNumber, columnIndex)"
                              :key="`${row.clientId}-cell-diagnostic-${columnIndex}-${index}`"
                              class="mt-2 rounded-xl bg-red-100 px-2 py-2 text-[11px] leading-4 text-red-600"
                            >
                              {{ item.message }}
                            </p>
                          </div>
                        </td>
                        <td class="px-3 py-3">
                          <button
                            type="button"
                            class="rounded-lg border border-red-200 px-2.5 py-1.5 text-[11px] font-medium text-red-600 transition hover:bg-red-50"
                            @click="removeRow(rowIndex)"
                          >
                            删除行
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </main>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

import { apiClient } from '../services/apiClient.js'

const REQUIRED_HEADERS = ['材料名称', '要素字段名称', '审查要点名称', '审查要点规则说明']
const WORKSPACE_ONLY_CODES = new Set([
  'workspace_not_found',
  'missing_factors_xlsx',
  'invalid_factors_file',
  'parse_failed',
  'missing_material_directories',
  'missing_material_directory',
  'selected_material_missing_directory',
])

const props = defineProps({
  workDir: {
    type: String,
    required: true,
  },
  errors: {
    type: Array,
    default: () => [],
  },
  diagnostics: {
    type: Array,
    default: () => [],
  },
  open: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'validation-updated', 'log'])

const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
const statusMessage = ref('')
const statusTone = ref('warning')
const workbook = ref({ filePath: '', headers: [], rows: [], exists: false })
const localHeaders = ref([])
const localRows = ref([])
const selectedIssueId = ref('')
const focusedTargetId = ref('')
const lastSavedSignature = ref('')
const toolbarAnchor = ref(null)

let nextClientRowId = 0

const downloadPath = computed(() => workbook.value.filePath || (props.workDir ? `${props.workDir}/factors.xlsx` : ''))
const currentFileName = computed(() => {
  const pathValue = downloadPath.value || ''
  return pathValue.split(/[/\\]/).pop() || 'factors.xlsx'
})
const materialColumnIndex = computed(() => localHeaders.value.findIndex((header) => String(header || '').includes('材料名称')))

const issueList = computed(() => {
  if (Array.isArray(props.diagnostics) && props.diagnostics.length > 0) {
    return props.diagnostics.map((item, index) => ({
      id: `diagnostic-${index}`,
      ...item,
    }))
  }
  return (Array.isArray(props.errors) ? props.errors : []).map((message, index) => ({
    id: `fallback-${index}`,
    code: 'generic_error',
    message,
  }))
})

const selectedIssue = computed(() => issueList.value.find((item) => item.id === selectedIssueId.value) || null)

const issueGroups = computed(() => {
  const groups = [
    { id: 'workbook', title: '可在线修复', items: [] },
    { id: 'workspace', title: '需检查工作区目录', items: [] },
    { id: 'settings', title: '需维护内置变量', items: [] },
  ]
  for (const issue of issueList.value) {
    groups.find((group) => group.id === issueCategory(issue))?.items.push(issue)
  }
  return groups.filter((group) => group.items.length > 0)
})

const hasDraftChanges = computed(() => buildCurrentSignature() !== lastSavedSignature.value)

const selectedIssueAdvice = computed(() => {
  const issue = selectedIssue.value
  if (!issue) return ''
  if (issueCategory(issue) === 'workspace') {
    return '这类问题需要回到工作区目录处理，例如补样本附件、补材料子目录，或确认 factors.xlsx 文件存在且格式正确。'
  }
  if (issueCategory(issue) === 'settings') {
    return '这是一个未识别的内置变量占位符。你可以直接修改规则说明文本，或者回到设置页维护对应的内置变量。'
  }
  if (issue.code === 'missing_required_column') {
    return '这是缺失必需列问题。可以直接点击上方“补齐必需列”，再补充对应列值。'
  }
  return '优先修复当前问题后再保存并重新校验，问题导航会持续定位到对应列或单元格。'
})

watch(
  () => props.workDir,
  () => {
    loadError.value = ''
    statusMessage.value = ''
    workbook.value = { filePath: '', headers: [], rows: [], exists: false }
    localHeaders.value = []
    localRows.value = []
    selectedIssueId.value = ''
    focusedTargetId.value = ''
    lastSavedSignature.value = ''
  },
)

watch(
  () => props.open,
  async (value) => {
    if (!value) return
    await reloadWorkbook()
    await nextTick()
    if (issueList.value.length > 0) {
      await focusIssue(issueList.value[0])
    }
  },
  { immediate: true },
)

watch(
  () => issueList.value.map((item) => item.id).join('|'),
  async () => {
    if (!props.open || issueList.value.length === 0) return
    if (!issueList.value.some((item) => item.id === selectedIssueId.value)) {
      await nextTick()
      await focusIssue(issueList.value[0])
    }
  },
)

function normalizeRowValues(values, targetSize) {
  const next = Array.isArray(values) ? [...values] : []
  while (next.length < targetSize) {
    next.push('')
  }
  return next.slice(0, targetSize)
}

function buildEditableRow(row = {}) {
  nextClientRowId += 1
  return {
    clientId: `factors-row-${nextClientRowId}`,
    rowNumber: Number.isFinite(row.rowNumber) ? row.rowNumber : null,
    values: normalizeRowValues(row.values || [], Math.max(localHeaders.value.length, 1)),
  }
}

function buildSignature(headers, rows) {
  return JSON.stringify({
    headers,
    rows: rows.map((row) => row.values),
  })
}

function buildCurrentSignature() {
  return buildSignature(localHeaders.value, localRows.value)
}

function applyWorkbookData(data = {}) {
  workbook.value = data
  localHeaders.value = Array.isArray(data.headers) && data.headers.length > 0 ? [...data.headers] : ['']
  localRows.value = Array.isArray(data.rows) ? data.rows.map((row) => buildEditableRow(row)) : []
  syncRowSizes()
  lastSavedSignature.value = buildCurrentSignature()
}

function syncRowSizes() {
  const width = Math.max(localHeaders.value.length, 1)
  localRows.value = localRows.value.map((row) => ({
    ...row,
    values: normalizeRowValues(row.values, width),
  }))
}

async function reloadWorkbook() {
  if (!props.workDir) return
  loading.value = true
  loadError.value = ''
  statusMessage.value = ''
  try {
    const response = await apiClient.get('/api/workspaces/factors-workbook', { workDir: props.workDir })
    applyWorkbookData(response?.data || {})
    emit('log', '已读取 factors.xlsx，可在修复台继续处理。', 'info')
  } catch (error) {
    loadError.value = `读取 factors.xlsx 失败: ${error}`
    emit('log', loadError.value, 'error')
  } finally {
    loading.value = false
  }
}

function addRow() {
  const values = Array.from({ length: Math.max(localHeaders.value.length, 1) }, () => '')
  if (materialColumnIndex.value >= 0) {
    const previousMaterial = [...localRows.value]
      .reverse()
      .map((row) => row.values[materialColumnIndex.value])
      .find((value) => String(value || '').trim())
    if (previousMaterial) {
      values[materialColumnIndex.value] = previousMaterial
    }
  }
  localRows.value.push(buildEditableRow({ values }))
}

function removeRow(index) {
  localRows.value.splice(index, 1)
}

function addColumn() {
  localHeaders.value.push('')
  syncRowSizes()
}

function addMissingRequiredColumns() {
  for (const header of REQUIRED_HEADERS) {
    if (!localHeaders.value.includes(header)) {
      localHeaders.value.push(header)
    }
  }
  syncRowSizes()
  focusedTargetId.value = 'toolbar-anchor'
}

function removeColumn(index) {
  if (localHeaders.value.length === 1) return
  localHeaders.value.splice(index, 1)
  localRows.value = localRows.value.map((row) => {
    const nextValues = [...row.values]
    nextValues.splice(index, 1)
    return {
      ...row,
      values: nextValues,
    }
  })
  syncRowSizes()
}

function isLongTextColumn(header) {
  const value = String(header || '')
  return value.includes('说明') || value.includes('规则')
}

function issueCategory(issue) {
  if (issue.code === 'invalid_placeholder' && issue.token && !String(issue.token).includes('-')) {
    return 'settings'
  }
  if (WORKSPACE_ONLY_CODES.has(issue.code)) {
    return 'workspace'
  }
  return 'workbook'
}

function issueTag(issue) {
  if (issueCategory(issue) === 'workspace') return '目录处理'
  if (issueCategory(issue) === 'settings') return '设置处理'
  return '在线修复'
}

function issueToneClass(issue) {
  if (issueCategory(issue) === 'workspace') return 'bg-amber-50 text-amber-700'
  if (issueCategory(issue) === 'settings') return 'bg-purple-50 text-purple-700'
  return 'bg-blue-50 text-blue-700'
}

function issueCaption(issue) {
  const parts = []
  if (issue.row) parts.push(`第 ${issue.row} 行`)
  if (issue.column) parts.push(issue.column)
  if (issue.materialName) parts.push(`材料：${issue.materialName}`)
  if (!parts.length) return '工作区级问题'
  return parts.join(' · ')
}

function headerTargetId(columnIndex) {
  return `header-${columnIndex}`
}

function cellTargetId(rowNumber, columnIndex) {
  return rowNumber ? `cell-${rowNumber}-${columnIndex}` : `draft-cell-${columnIndex}`
}

function resolveIssueTargetId(issue) {
  if (issue?.column) {
    const columnIndex = localHeaders.value.findIndex((header) => header === issue.column)
    if (issue.row && columnIndex >= 0) {
      return cellTargetId(issue.row, columnIndex)
    }
    if (columnIndex >= 0) {
      return headerTargetId(columnIndex)
    }
  }
  return 'toolbar-anchor'
}

async function focusIssue(issue) {
  if (!issue) return
  selectedIssueId.value = issue.id
  focusedTargetId.value = resolveIssueTargetId(issue)
  await nextTick()
  const target = document.querySelector(`[data-repair-target="${focusedTargetId.value}"]`)
  if (!target) return
  target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
  const focusable = target.querySelector('input, textarea, button')
  focusable?.focus?.()
}

function headerDiagnostics(columnIndex) {
  const columnName = localHeaders.value[columnIndex] || ''
  return (Array.isArray(props.diagnostics) ? props.diagnostics : []).filter(
    (item) => !item?.row && item?.column === columnName,
  )
}

function cellDiagnostics(rowNumber, columnIndex) {
  if (!rowNumber) return []
  const columnName = localHeaders.value[columnIndex] || ''
  return (Array.isArray(props.diagnostics) ? props.diagnostics : []).filter(
    (item) => Number(item?.row) === Number(rowNumber) && item?.column === columnName,
  )
}

function cellInputClass(rowNumber, columnIndex) {
  const hasIssue = headerDiagnostics(columnIndex).length > 0 || cellDiagnostics(rowNumber, columnIndex).length > 0
  if (hasIssue) {
    return 'border-red-300 bg-red-50 text-red-700 focus:ring-red-200'
  }
  return 'border-slate-200 bg-white focus:ring-blue-200'
}

async function saveWorkbook() {
  if (!props.workDir || saving.value) return
  saving.value = true
  loadError.value = ''
  statusMessage.value = ''
  try {
    const response = await apiClient.put('/api/workspaces/factors-workbook', {
      workDir: props.workDir,
      headers: localHeaders.value,
      rows: localRows.value.map((row) => ({ values: row.values })),
    })
    const payload = response?.data || {}
    applyWorkbookData(payload.workbook || {})
    emit('validation-updated', payload.validation || {})
    if (payload.validation?.ok) {
      statusTone.value = 'success'
      statusMessage.value = '保存成功，统一工作区校验已通过。'
      emit('log', 'factors.xlsx 已保存并通过校验。', 'success')
    } else {
      statusTone.value = 'warning'
      statusMessage.value = `保存成功，但仍有 ${(payload.validation?.errors || []).length} 个问题待处理。`
      emit('log', statusMessage.value, 'warning')
      await nextTick()
      if (issueList.value.length > 0) {
        await focusIssue(issueList.value[0])
      }
    }
  } catch (error) {
    loadError.value = `保存 factors.xlsx 失败: ${error}`
    emit('log', loadError.value, 'error')
  } finally {
    saving.value = false
  }
}

function downloadWorkbook() {
  if (!downloadPath.value) return
  apiClient.download('/api/files/download', { path: downloadPath.value })
  emit('log', '已开始下载修复后的 factors.xlsx。', 'success')
}

function requestClose() {
  if (hasDraftChanges.value && typeof window !== 'undefined') {
    const confirmed = window.confirm('修复台内还有未保存修改，确认先返回业务页吗？')
    if (!confirmed) return
  }
  emit('close')
}
</script>

<style scoped>
.repair-desk-enter-active,
.repair-desk-leave-active {
  transition: opacity 0.2s ease;
}

.repair-desk-enter-from,
.repair-desk-leave-to {
  opacity: 0;
}
</style>
