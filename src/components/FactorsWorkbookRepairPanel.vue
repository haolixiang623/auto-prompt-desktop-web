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
                  这里会集中展示当前工作区的校验问题。左侧是问题导航，右侧是 factors.xlsx 修复区；支持新增行、复制行、删除行，保存后会立即重新校验，再返回业务页继续。
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

                  <div class="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                    <div class="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2">
                      <svg class="h-3.5 w-3.5 flex-shrink-0 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M21 21l-4.35-4.35m1.85-5.15a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      <input
                        v-model="searchKeyword"
                        type="text"
                        class="w-full border-0 bg-transparent p-0 text-xs text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-0"
                        placeholder="搜索材料名称 / 要素字段名称 / 审查要点规则说明"
                      />
                      <button
                        v-if="hasActiveSearch"
                        type="button"
                        class="rounded-lg px-2 py-1 text-[11px] font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
                        @click="clearSearch"
                      >
                        清空
                      </button>
                    </div>
                    <p class="mt-2 text-[11px] leading-5 text-slate-500">
                      支持按“材料名称”“要素字段名称”和“审查要点规则说明”筛选，方便快速定位对应行并处理相关问题。
                    </p>
                    <p v-if="hasActiveSearch" class="mt-1 text-[11px] leading-5 text-slate-400">
                      搜索结果列表会按命中字段定位：命中材料名称时跳到材料名称，命中要素字段名称时跳到要素字段，命中审查要点规则说明时跳到对应规则说明。
                    </p>
                    <p v-if="hasActiveSearch" class="mt-2 text-[11px] font-medium text-slate-600">
                      {{ searchResultSummary }}
                    </p>
                  </div>

                  <div class="mt-4 space-y-4 overflow-y-auto xl:max-h-[calc(100vh-280px)]">
                    <template v-if="hasActiveSearch">
                      <section>
                        <div class="mb-2 flex items-center justify-between">
                          <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                            搜索结果
                          </p>
                          <span class="text-[11px] text-slate-400">{{ searchResultItems.length }}</span>
                        </div>
                        <div class="space-y-2">
                          <button
                            v-for="item in searchResultItems"
                            :key="item.id"
                            type="button"
                            class="w-full rounded-2xl border px-3 py-3 text-left transition"
                            :class="isSearchResultActive(item)
                              ? 'border-slate-900 bg-slate-900 text-white shadow-sm'
                              : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50'"
                            @click="focusSearchResult(item)"
                          >
                            <p class="truncate text-xs font-semibold">
                              {{ item.factorName || item.materialName || '未填写要素字段名称' }}
                            </p>
                            <p
                              v-if="item.ruleDescriptionPreview"
                              class="mt-1 line-clamp-2 text-[11px] leading-5"
                              :class="isSearchResultActive(item) ? 'text-slate-300' : 'text-slate-500'"
                            >
                              {{ item.ruleDescriptionPreview }}
                            </p>
                            <p
                              class="mt-1 text-[11px] leading-5"
                              :class="isSearchResultActive(item) ? 'text-slate-300' : 'text-slate-400'"
                            >
                              {{ item.caption }}
                            </p>
                          </button>
                        </div>
                      </section>
                    </template>
                    <template v-else>
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
                    </template>

                    <div
                      v-if="hasActiveSearch && filteredIssueList.length === 0 && issueList.length > 0"
                      class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm leading-6 text-slate-500"
                    >
                      当前搜索词没有匹配到问题导航项。可尝试搜索要素字段名称、规则说明里的关键词，或清空搜索后查看全部问题。
                    </div>

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
                        优先处理左侧导航中的问题，再保存并重新校验。修复台支持新增行、复制行、删除行；列结构仍保持只读，不支持增删列。
                      </p>
                    </div>
                    <div class="flex flex-wrap gap-2">
                      <button
                        type="button"
                        class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-60"
                        :disabled="loading || saving"
                        @click="addRow()"
                      >
                        新增行
                      </button>
                      <button
                        v-if="!showAllColumns"
                        type="button"
                        class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                        @click="showAllColumnsNow"
                      >
                        显示全部列
                      </button>
                      <button
                        v-else
                        type="button"
                        class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                        @click="restoreDefaultColumns"
                      >
                        恢复默认列
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
                    <span v-if="hasPendingRowStructureChanges" class="rounded-full bg-amber-50 px-2.5 py-1 text-amber-700">
                      行结构已调整，待保存后刷新校验
                    </span>
                    <span v-if="hiddenColumnsCount > 0" class="rounded-full bg-slate-100 px-2.5 py-1 text-slate-600">
                      默认展示 {{ visibleColumnIndices.length }} / {{ localHeaders.length }} 列
                    </span>
                    <span v-if="mergedRangeCount > 0" class="rounded-full bg-slate-100 px-2.5 py-1 text-slate-600">
                      合并单元格已按原表结构展开显示，共 {{ mergedRangeCount }} 组
                    </span>
                    <span v-if="rowsWithIssuesCount > 0" class="rounded-full bg-red-50 px-2.5 py-1 text-red-700">
                      默认前置 {{ rowsWithIssuesCount }} 行问题数据
                    </span>
                    <span v-if="hasActiveSearch" class="rounded-full bg-slate-100 px-2.5 py-1 text-slate-600">{{ searchResultSummary }}</span>
                    <span v-if="currentFocusLabel" class="rounded-full bg-blue-50 px-2.5 py-1 text-blue-700">
                      当前定位：{{ currentFocusLabel }}
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
                        <th class="sticky top-0 z-10 min-w-20 bg-slate-50 px-3 py-3 font-semibold text-slate-600">行号</th>
                        <th class="sticky top-0 z-10 min-w-32 bg-slate-50 px-3 py-3 font-semibold text-slate-600">操作</th>
                        <th
                          v-for="column in visibleColumns"
                          :key="`header-${column.columnIndex}`"
                          class="sticky top-0 z-10 min-w-56 bg-slate-50 px-3 py-3 align-top"
                        >
                          <div
                            class="rounded-2xl border border-transparent p-2 transition"
                            :class="focusedTargetId === headerTargetId(column.columnIndex) ? 'border-blue-200 bg-blue-50' : ''"
                            :data-repair-target="headerTargetId(column.columnIndex)"
                          >
                            <div class="flex items-start gap-2">
                              <input
                                v-model="localHeaders[column.columnIndex]"
                                type="text"
                                class="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200"
                                placeholder="列名"
                                @input="syncMergedHeader(column.columnIndex, localHeaders[column.columnIndex])"
                              />
                            </div>
                            <p
                              v-for="(item, index) in headerDiagnostics(column.columnIndex)"
                              :key="`header-diagnostic-${column.columnIndex}-${index}`"
                              class="mt-2 rounded-xl bg-red-100 px-2 py-2 text-[11px] leading-4 text-red-600"
                            >
                              {{ item.message }}
                            </p>
                          </div>
                        </th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-200 bg-white">
                      <tr v-if="localRows.length === 0">
                        <td :colspan="visibleColumns.length + 2" class="px-4 py-10 text-center text-sm text-slate-400">
                          当前未读取到可编辑的数据行。你可以先点击上方“新增行”补一行，再继续填写并保存校验。
                        </td>
                      </tr>
                      <tr v-for="displayedRow in displayedRows" :key="displayedRow.row.clientId" class="align-top">
                        <td class="px-3 py-3 text-slate-500">
                          {{ displayedRow.row.rowNumber || `新增${displayedRow.sourceIndex + 1}` }}
                        </td>
                        <td class="px-3 py-3">
                          <div class="flex min-w-28 flex-col gap-2">
                            <button
                              type="button"
                              class="rounded-lg border border-slate-200 px-2.5 py-2 text-[11px] font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-60"
                              :disabled="loading || saving"
                              @click="addRow(displayedRow.row.rowNumber)"
                            >
                              新增行
                            </button>
                            <button
                              type="button"
                              class="rounded-lg border border-slate-200 px-2.5 py-2 text-[11px] font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-60"
                              :disabled="loading || saving"
                              @click="copyRow(displayedRow.row.rowNumber)"
                            >
                              复制行
                            </button>
                            <button
                              type="button"
                              class="rounded-lg border border-red-200 px-2.5 py-2 text-[11px] font-medium text-red-600 transition hover:bg-red-50 disabled:opacity-60"
                              :disabled="loading || saving"
                              @click="deleteRow(displayedRow.row.rowNumber)"
                            >
                              删除行
                            </button>
                          </div>
                        </td>
                        <td
                          v-for="column in visibleColumns"
                          :key="`${displayedRow.row.clientId}-${column.columnIndex}`"
                          class="px-3 py-3"
                        >
                          <div
                            class="rounded-2xl border border-transparent p-2 transition"
                            :class="focusedTargetId === cellTargetId(displayedRow.row.rowNumber, column.columnIndex) ? 'border-blue-200 bg-blue-50' : ''"
                            :data-repair-target="cellTargetId(displayedRow.row.rowNumber, column.columnIndex)"
                          >
                            <textarea
                              v-if="isLongTextColumn(column.header)"
                              v-model="displayedRow.row.values[column.columnIndex]"
                              rows="3"
                              class="w-full rounded-lg border px-2.5 py-2 text-xs leading-5 text-slate-700 focus:outline-none focus:ring-2"
                              :class="cellInputClass(displayedRow.row.rowNumber, column.columnIndex)"
                              placeholder="请输入内容"
                              @input="syncMergedCell(displayedRow.row.rowNumber, column.columnIndex, displayedRow.row.values[column.columnIndex])"
                            />
                            <input
                              v-else
                              v-model="displayedRow.row.values[column.columnIndex]"
                              type="text"
                              class="w-full rounded-lg border px-2.5 py-2 text-xs text-slate-700 focus:outline-none focus:ring-2"
                              :class="cellInputClass(displayedRow.row.rowNumber, column.columnIndex)"
                              placeholder="请输入内容"
                              @input="syncMergedCell(displayedRow.row.rowNumber, column.columnIndex, displayedRow.row.values[column.columnIndex])"
                            />
                            <p
                              v-for="(item, index) in cellDiagnostics(displayedRow.row.rowNumber, column.columnIndex)"
                              :key="`${displayedRow.row.clientId}-cell-diagnostic-${column.columnIndex}-${index}`"
                              class="mt-2 rounded-xl bg-red-100 px-2 py-2 text-[11px] leading-4 text-red-600"
                            >
                              {{ item.message }}
                            </p>
                          </div>
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
import {
  buildSearchTerms,
  countMatchedSearchTerms,
  issueMatchesWorkbookSearch,
  normalizeSearchText,
  resolveWorkbookSearchMatchTarget,
  rowMatchesWorkbookSearch,
} from './factorsWorkbookSearch.js'
import { deleteWorkbookRow, insertWorkbookRow } from './factorsWorkbookRowOperations.js'

const FACTOR_FIELD_HEADER_ALIASES = ['要素字段名称', '要素名称']
const DEFAULT_VISIBLE_HEADER_PATTERNS = ['事项名称', '材料名称', '要素字段名称', '要素名称', '审查要点名称', '审查要点规则说明']
const DISPLAY_CARRY_FORWARD_HEADER_PATTERNS = ['事项名称', '材料名称']
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
const hasPendingRowStructureChanges = ref(false)
const workbook = ref({ filePath: '', headers: [], rows: [], exists: false, mergedRanges: [] })
const localHeaders = ref([])
const localRows = ref([])
const selectedIssueId = ref('')
const focusedTargetId = ref('')
const lastSavedSignature = ref('')
const toolbarAnchor = ref(null)
const searchKeyword = ref('')
const showAllColumns = ref(false)
const revealedColumnIndices = ref([])

let nextClientRowId = 0

const downloadPath = computed(() => workbook.value.filePath || (props.workDir ? `${props.workDir}/factors.xlsx` : ''))
const currentFileName = computed(() => {
  const pathValue = downloadPath.value || ''
  return pathValue.split(/[/\\]/).pop() || 'factors.xlsx'
})
const materialColumnIndex = computed(() => localHeaders.value.findIndex((header) => String(header || '').includes('材料名称')))
const factorColumnIndex = computed(() => localHeaders.value.findIndex((header) => isFactorFieldHeader(header)))
const keypointColumnIndex = computed(() => localHeaders.value.findIndex((header) => String(header || '').includes('审查要点名称')))
const ruleDescriptionColumnIndex = computed(() => localHeaders.value.findIndex((header) => String(header || '').includes('审查要点规则说明')))
const searchTerms = computed(() => buildSearchTerms(searchKeyword.value))
const hasActiveSearch = computed(() => searchTerms.value.length > 0)
const defaultVisibleColumnIndices = computed(() => {
  const matches = localHeaders.value
    .map((header, columnIndex) => (isDefaultVisibleHeader(header) ? columnIndex : -1))
    .filter((columnIndex) => columnIndex >= 0)
  if (matches.length > 0) {
    return matches
  }
  return localHeaders.value.map((_, columnIndex) => columnIndex).slice(0, Math.min(localHeaders.value.length, 6))
})
const visibleColumnIndices = computed(() => {
  if (showAllColumns.value) {
    return localHeaders.value.map((_, columnIndex) => columnIndex)
  }
  const mergedIndices = new Set(defaultVisibleColumnIndices.value)
  for (const columnIndex of revealedColumnIndices.value) {
    if (columnIndex >= 0 && columnIndex < localHeaders.value.length) {
      mergedIndices.add(columnIndex)
    }
  }
  return [...mergedIndices].sort((left, right) => left - right)
})
const visibleColumns = computed(() =>
  visibleColumnIndices.value.map((columnIndex) => ({
    columnIndex,
    header: localHeaders.value[columnIndex] || '',
  })),
)
const hiddenColumnsCount = computed(() => Math.max(0, localHeaders.value.length - visibleColumnIndices.value.length))
const mergedRanges = computed(() => (Array.isArray(workbook.value.mergedRanges) ? workbook.value.mergedRanges : []))
const mergedRangeCount = computed(() => mergedRanges.value.length)
const shouldPrioritizeIssueRows = computed(() => !hasPendingRowStructureChanges.value)

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

const filteredIssueList = computed(() => issueList.value.filter((item) => matchesIssueSearch(item)))
const selectedIssue = computed(() => filteredIssueList.value.find((item) => item.id === selectedIssueId.value) || null)

const rowIssueSummaryMap = computed(() => {
  const map = new Map()
  for (const issue of issueList.value) {
    const rowNumber = Number(issue?.row)
    if (!Number.isFinite(rowNumber) || rowNumber <= 0) continue
    map.set(rowNumber, (map.get(rowNumber) || 0) + 1)
  }
  return map
})

const displayedRows = computed(() =>
  localRows.value
    .map((row, sourceIndex) => ({
      row,
      sourceIndex,
      issueCount: shouldPrioritizeIssueRows.value && row?.rowNumber ? rowIssueSummaryMap.value.get(Number(row.rowNumber)) || 0 : 0,
    }))
    .sort((left, right) => {
      const issueDelta = Number(right.issueCount > 0) - Number(left.issueCount > 0)
      if (issueDelta !== 0) return issueDelta
      return left.sourceIndex - right.sourceIndex
    }),
)

const searchMatchedRows = computed(() => displayedRows.value.filter(({ row }) => matchesRowSearch(row)))
const rowsWithIssuesCount = computed(() => displayedRows.value.filter((item) => item.issueCount > 0).length)

const searchResultItems = computed(() => {
  if (!hasActiveSearch.value) return []
  return searchMatchedRows.value.map(({ row, sourceIndex }) => {
    const anchorIssue = filteredIssueList.value.find((issue) => Number(issue?.row) === Number(row.rowNumber)) || null
    const matchTarget = resolveSearchResultMatchTarget(row)
    const hasRuleDescriptionMatch = countMatchedSearchTerms(rowRuleDescriptionSearchValue(row), searchTerms.value) > 0
    return {
      id: `search-result-${row.clientId}`,
      materialName: rowMaterialSearchValue(row),
      factorName: rowFactorSearchValue(row),
      ruleDescriptionPreview: hasRuleDescriptionMatch ? buildRuleDescriptionPreview(rowRuleDescriptionSearchValue(row)) : '',
      caption: buildSearchResultCaption(row, sourceIndex),
      matchTarget,
      row,
      sourceIndex,
      anchorIssue,
    }
  })
})

const searchResultSummary = computed(() => {
  if (!hasActiveSearch.value) return ''
  return `已匹配 ${searchMatchedRows.value.length} / ${localRows.value.length} 行 · ${filteredIssueList.value.length} / ${issueList.value.length} 个问题`
})

const issueGroups = computed(() => {
  const groups = [
    { id: 'workbook', title: '可在线修复', items: [] },
    { id: 'structure', title: '需调整表结构', items: [] },
    { id: 'workspace', title: '需检查工作区目录', items: [] },
    { id: 'settings', title: '需维护内置变量', items: [] },
  ]
  for (const issue of filteredIssueList.value) {
    groups.find((group) => group.id === issueCategory(issue))?.items.push(issue)
  }
  return groups.filter((group) => group.items.length > 0)
})

const hasDraftChanges = computed(() => buildCurrentSignature() !== lastSavedSignature.value)
const currentFocusLabel = computed(() => buildTargetLocationLabel(focusedTargetId.value))

const selectedIssueAdvice = computed(() => {
  if (hasPendingRowStructureChanges.value) {
    return '已调整行结构，左侧问题和定位仍基于上一次校验结果。建议先保存并重新校验，再继续按问题导航处理。'
  }
  const issue = selectedIssue.value
  if (!issue) return ''
  if (issueCategory(issue) === 'structure') {
    return '当前修复台支持新增行、复制行和删除行，但列结构仍保持只读，不支持增删列。若缺少必需列，需要回到原始 factors.xlsx 补齐列结构后重新载入。'
  }
  if (issueCategory(issue) === 'workspace') {
    return '这类问题需要回到工作区目录处理，例如补样本附件、补材料子目录，或确认 factors.xlsx 文件存在且格式正确。'
  }
  if (issueCategory(issue) === 'settings') {
    return '这是一个未识别的内置变量占位符。你可以直接修改规则说明文本，或者回到设置页维护对应的内置变量。'
  }
  return '优先修复当前问题后再保存并重新校验，问题导航会持续定位到对应列或单元格。'
})

watch(
  () => props.workDir,
  () => {
    loadError.value = ''
    statusMessage.value = ''
    workbook.value = { filePath: '', headers: [], rows: [], exists: false, mergedRanges: [] }
    localHeaders.value = []
    localRows.value = []
    selectedIssueId.value = ''
    focusedTargetId.value = ''
    lastSavedSignature.value = ''
    searchKeyword.value = ''
    showAllColumns.value = false
    revealedColumnIndices.value = []
    hasPendingRowStructureChanges.value = false
  },
)

watch(
  () => props.open,
  async (value) => {
    if (!value) return
    await reloadWorkbook()
    await nextTick()
    if (filteredIssueList.value.length > 0) {
      await focusIssue(filteredIssueList.value[0])
    } else {
      selectedIssueId.value = ''
      focusedTargetId.value = 'toolbar-anchor'
    }
  },
  { immediate: true },
)

watch(
  () => filteredIssueList.value.map((item) => item.id).join('|'),
  async () => {
    if (!props.open) return
    if (filteredIssueList.value.length === 0) {
      selectedIssueId.value = ''
      focusedTargetId.value = 'toolbar-anchor'
      return
    }
    if (!filteredIssueList.value.some((item) => item.id === selectedIssueId.value)) {
      await nextTick()
      await focusIssue(filteredIssueList.value[0])
    }
  },
)

function isFactorFieldHeader(header) {
  const headerText = String(header || '').trim()
  return FACTOR_FIELD_HEADER_ALIASES.some((alias) => headerText.includes(alias))
}

function isDefaultVisibleHeader(header) {
  const headerText = String(header || '').trim()
  return DEFAULT_VISIBLE_HEADER_PATTERNS.some((pattern) => headerText.includes(pattern)) || isFactorFieldHeader(header)
}

function rowMaterialSearchValue(row) {
  if (materialColumnIndex.value < 0) return ''
  return row?.values?.[materialColumnIndex.value] ?? ''
}

function rowFactorSearchValue(row) {
  if (factorColumnIndex.value < 0) return ''
  return row?.values?.[factorColumnIndex.value] ?? ''
}

function rowKeypointSearchValue(row) {
  if (keypointColumnIndex.value < 0) return ''
  return row?.values?.[keypointColumnIndex.value] ?? ''
}

function rowRuleDescriptionSearchValue(row) {
  if (ruleDescriptionColumnIndex.value < 0) return ''
  return row?.values?.[ruleDescriptionColumnIndex.value] ?? ''
}

function issueFactorFieldName(issue) {
  const relatedRow = issue?.row ? findRowByNumber(issue.row) : null
  return String(relatedRow ? rowFactorSearchValue(relatedRow) : issue?.factorName || '').trim()
}

function matchesRowSearch(row) {
  return rowMatchesWorkbookSearch({
    searchTerms: searchTerms.value,
    materialName: rowMaterialSearchValue(row),
    factorName: rowFactorSearchValue(row),
    ruleDescription: rowRuleDescriptionSearchValue(row),
  })
}

function findRowByNumber(rowNumber) {
  return localRows.value.find((row) => Number(row.rowNumber) === Number(rowNumber)) || null
}

function matchesIssueSearch(issue) {
  const relatedRow = issue?.row ? findRowByNumber(issue.row) : null
  return issueMatchesWorkbookSearch({
    searchTerms: searchTerms.value,
    materialName: relatedRow ? rowMaterialSearchValue(relatedRow) : issue?.materialName || '',
    factorName: issueFactorFieldName(issue),
    ruleDescription: relatedRow ? rowRuleDescriptionSearchValue(relatedRow) : '',
    message: issue?.message,
  })
}

function clearSearch() {
  searchKeyword.value = ''
}

function buildRuleDescriptionPreview(value) {
  const normalized = String(value || '').trim().replace(/\s+/g, ' ')
  if (!normalized) return ''
  return normalized.length > 48 ? `${normalized.slice(0, 48)}...` : normalized
}

function buildSearchResultCaption(row, rowIndex) {
  const parts = []
  parts.push(row.rowNumber ? `第 ${row.rowNumber} 行` : `新增${rowIndex + 1}`)
  const materialName = String(rowMaterialSearchValue(row) || '').trim()
  if (materialName) {
    parts.push(`材料：${materialName}`)
  }
  const keypointName = String(rowKeypointSearchValue(row) || '').trim()
  if (keypointName) {
    parts.push(`审查要点：${keypointName}`)
  }
  return parts.join(' · ')
}

function findRowByFactorFieldName(factorName) {
  const normalizedFactorName = normalizeSearchText(factorName)
  if (!normalizedFactorName) return null
  return localRows.value.find((row) => normalizeSearchText(rowFactorSearchValue(row)) === normalizedFactorName) || null
}

function columnLabel(columnIndex) {
  if (columnIndex < 0) return ''
  return String(localHeaders.value[columnIndex] || '').trim() || `第 ${columnIndex + 1} 列`
}

function buildTargetLocationLabel(targetId) {
  const normalizedTargetId = String(targetId || '')
  if (!normalizedTargetId || normalizedTargetId === 'toolbar-anchor') {
    return ''
  }

  const headerMatch = /^header-(\d+)$/.exec(normalizedTargetId)
  if (headerMatch) {
    const columnIndex = Number(headerMatch[1])
    return `列头 · ${columnLabel(columnIndex)}`
  }

  const cellMatch = /^cell-(\d+)-(\d+)$/.exec(normalizedTargetId)
  if (cellMatch) {
    const rowNumber = Number(cellMatch[1])
    const columnIndex = Number(cellMatch[2])
    const row = findRowByNumber(rowNumber)
    const parts = [`第 ${rowNumber} 行`, columnLabel(columnIndex)]
    const materialName = materialColumnIndex.value >= 0 ? String(row?.values?.[materialColumnIndex.value] || '').trim() : ''
    if (materialName) {
      parts.push(`材料：${materialName}`)
    }
    return parts.join(' · ')
  }

  const draftCellMatch = /^draft-cell-(\d+)$/.exec(normalizedTargetId)
  if (draftCellMatch) {
    return `未编号行 · ${columnLabel(Number(draftCellMatch[1]))}`
  }

  return ''
}

function resolveRowFactorFieldTargetId(row) {
  if (factorColumnIndex.value < 0) {
    return 'toolbar-anchor'
  }
  return cellTargetId(row?.rowNumber, factorColumnIndex.value)
}

function resolveRowMaterialTargetId(row) {
  if (materialColumnIndex.value < 0) {
    return resolveRowFactorFieldTargetId(row)
  }
  return cellTargetId(row?.rowNumber, materialColumnIndex.value)
}

function resolveRowRuleDescriptionTargetId(row) {
  if (ruleDescriptionColumnIndex.value >= 0) {
    return cellTargetId(row?.rowNumber, ruleDescriptionColumnIndex.value)
  }
  return resolveRowFactorFieldTargetId(row)
}

function resolveSearchResultMatchTarget(row) {
  return resolveWorkbookSearchMatchTarget({
    searchTerms: searchTerms.value,
    materialName: rowMaterialSearchValue(row),
    factorName: rowFactorSearchValue(row),
    ruleDescription: rowRuleDescriptionSearchValue(row),
  })
}

function resolveRuleDescriptionTargetId(issue, factorName = '') {
  if (ruleDescriptionColumnIndex.value < 0) {
    return resolveIssueTargetId(issue)
  }
  if (issue?.row) {
    return cellTargetId(issue.row, ruleDescriptionColumnIndex.value)
  }
  const matchedRow = findRowByFactorFieldName(factorName || issueFactorFieldName(issue))
  if (matchedRow?.rowNumber) {
    return cellTargetId(matchedRow.rowNumber, ruleDescriptionColumnIndex.value)
  }
  return headerTargetId(ruleDescriptionColumnIndex.value)
}

function columnIndexFromTargetId(targetId) {
  const normalizedTargetId = String(targetId || '')
  const headerMatch = /^header-(\d+)$/.exec(normalizedTargetId)
  if (headerMatch) {
    return Number(headerMatch[1])
  }
  const cellMatch = /^cell-(\d+)-(\d+)$/.exec(normalizedTargetId)
  if (cellMatch) {
    return Number(cellMatch[2])
  }
  const draftCellMatch = /^draft-cell-(\d+)$/.exec(normalizedTargetId)
  if (draftCellMatch) {
    return Number(draftCellMatch[1])
  }
  return -1
}

function revealColumn(columnIndex) {
  if (showAllColumns.value || columnIndex < 0 || columnIndex >= localHeaders.value.length) return
  if (visibleColumnIndices.value.includes(columnIndex)) return
  revealedColumnIndices.value = [...revealedColumnIndices.value, columnIndex].sort((left, right) => left - right)
}

function showAllColumnsNow() {
  showAllColumns.value = true
}

function restoreDefaultColumns() {
  showAllColumns.value = false
  revealedColumnIndices.value = []
}

async function focusTarget(targetId) {
  revealColumn(columnIndexFromTargetId(targetId))
  focusedTargetId.value = targetId
  await nextTick()
  const target = document.querySelector(`[data-repair-target="${targetId}"]`)
  if (!target) return
  target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
  const focusable = target.querySelector('input, textarea, button')
  focusable?.focus?.()
}

function searchResultTargetId(item) {
  if (item?.matchTarget === 'material') {
    return resolveRowMaterialTargetId(item?.row)
  }
  if (item?.matchTarget === 'factor') {
    return resolveRowFactorFieldTargetId(item?.row)
  }
  return resolveRowRuleDescriptionTargetId(item?.row)
}

function isSearchResultActive(item) {
  return focusedTargetId.value === searchResultTargetId(item)
}

async function focusSearchResult(item) {
  if (!item?.row) return
  selectedIssueId.value = item.anchorIssue ? item.anchorIssue.id : ''
  await focusTarget(searchResultTargetId(item))
}

function normalizeRowValues(values, targetSize) {
  const next = Array.isArray(values) ? [...values] : []
  while (next.length < targetSize) {
    next.push('')
  }
  return next.slice(0, targetSize)
}

function buildEditableRow(row = {}) {
  const parsedRowNumber = Number(row?.rowNumber)
  return {
    clientId: row?.clientId || `factors-row-${++nextClientRowId}`,
    rowNumber: Number.isFinite(parsedRowNumber) ? parsedRowNumber : null,
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

function normalizeMergedRangeMeta(mergedRange) {
  const startRow = Number(mergedRange?.startRow)
  const endRow = Number(mergedRange?.endRow)
  const startColumn = Number(mergedRange?.startColumn)
  const endColumn = Number(mergedRange?.endColumn)
  if (
    !Number.isFinite(startRow) ||
    !Number.isFinite(endRow) ||
    !Number.isFinite(startColumn) ||
    !Number.isFinite(endColumn) ||
    startRow < 1 ||
    endRow < startRow ||
    startColumn < 1 ||
    endColumn < startColumn
  ) {
    return null
  }
  return { startRow, endRow, startColumn, endColumn }
}

function collectDisplayRowNumbers(rows, mergedRangeMeta) {
  const rowNumbers = new Set(
    rows
      .map((row) => Number(row?.rowNumber))
      .filter((rowNumber) => Number.isFinite(rowNumber) && rowNumber >= 2),
  )
  for (const mergedRange of mergedRangeMeta) {
    for (let rowNumber = Math.max(2, mergedRange.startRow); rowNumber <= mergedRange.endRow; rowNumber += 1) {
      rowNumbers.add(rowNumber)
    }
  }
  return [...rowNumbers].sort((left, right) => left - right)
}

function firstNonEmptyValue(cells) {
  return cells.find((value) => String(value ?? '').trim()) || ''
}

function carryForwardDisplayColumns(headers, rows) {
  const carryIndices = headers
    .map((header, index) => (DISPLAY_CARRY_FORWARD_HEADER_PATTERNS.some((pattern) => String(header || '').includes(pattern)) ? index : -1))
    .filter((index) => index >= 0)
  if (carryIndices.length === 0) return rows

  const lastValues = Array.from({ length: headers.length }, () => '')
  return rows.map((row) => {
    const nextValues = normalizeRowValues(row.values || [], headers.length)
    for (const index of carryIndices) {
      if (String(nextValues[index] || '').trim()) {
        lastValues[index] = nextValues[index]
      } else if (lastValues[index]) {
        nextValues[index] = lastValues[index]
      }
    }
    return {
      ...row,
      values: nextValues,
    }
  })
}

function expandMergedWorkbookData(data = {}) {
  const mergedRangeMeta = (Array.isArray(data.mergedRanges) ? data.mergedRanges : [])
    .map((item) => normalizeMergedRangeMeta(item))
    .filter(Boolean)

  const width = Math.max(
    1,
    Array.isArray(data.headers) ? data.headers.length : 0,
    ...(Array.isArray(data.rows) ? data.rows.map((row) => Array.isArray(row?.values) ? row.values.length : 0) : [0]),
    ...mergedRangeMeta.map((item) => item.endColumn),
  )

  const headers = normalizeRowValues(Array.isArray(data.headers) ? data.headers : [], width)
  const rowMap = new Map()
  for (const row of Array.isArray(data.rows) ? data.rows : []) {
    const rowNumber = Number(row?.rowNumber)
    if (!Number.isFinite(rowNumber) || rowNumber < 2) continue
    rowMap.set(rowNumber, {
      rowNumber,
      values: normalizeRowValues(row?.values || [], width),
    })
  }

  for (const rowNumber of collectDisplayRowNumbers(Array.from(rowMap.values()), mergedRangeMeta)) {
    if (!rowMap.has(rowNumber)) {
      rowMap.set(rowNumber, {
        rowNumber,
        values: normalizeRowValues([], width),
      })
    }
  }

  for (const mergedRange of mergedRangeMeta) {
    const startColumnIndex = mergedRange.startColumn - 1
    const endColumnIndex = mergedRange.endColumn - 1

    if (mergedRange.startRow === 1) {
      const anchorValue = firstNonEmptyValue(headers.slice(startColumnIndex, endColumnIndex + 1))
      for (let columnIndex = startColumnIndex; columnIndex <= endColumnIndex; columnIndex += 1) {
        headers[columnIndex] = anchorValue
      }
      continue
    }

    const anchorCells = []
    for (let rowNumber = mergedRange.startRow; rowNumber <= mergedRange.endRow; rowNumber += 1) {
      const row = rowMap.get(rowNumber)
      if (!row) continue
      for (let columnIndex = startColumnIndex; columnIndex <= endColumnIndex; columnIndex += 1) {
        anchorCells.push(row.values[columnIndex] || '')
      }
    }
    const anchorValue = firstNonEmptyValue(anchorCells)
    for (let rowNumber = Math.max(2, mergedRange.startRow); rowNumber <= mergedRange.endRow; rowNumber += 1) {
      const row = rowMap.get(rowNumber)
      if (!row) continue
      for (let columnIndex = startColumnIndex; columnIndex <= endColumnIndex; columnIndex += 1) {
        row.values[columnIndex] = anchorValue
      }
    }
  }

  return {
    headers,
    rows: carryForwardDisplayColumns(headers, [...rowMap.values()].sort((left, right) => left.rowNumber - right.rowNumber)),
    mergedRanges: mergedRangeMeta,
  }
}

function mergedRangeForCell(rowNumber, columnIndex) {
  const normalizedRowNumber = Number(rowNumber)
  const normalizedColumnIndex = Number(columnIndex)
  if (!Number.isFinite(normalizedRowNumber) || !Number.isFinite(normalizedColumnIndex) || normalizedColumnIndex < 0) {
    return null
  }
  const normalizedColumn = normalizedColumnIndex + 1
  return mergedRanges.value.find(
    (item) =>
      normalizedRowNumber >= Number(item.startRow) &&
      normalizedRowNumber <= Number(item.endRow) &&
      normalizedColumn >= Number(item.startColumn) &&
      normalizedColumn <= Number(item.endColumn),
  ) || null
}

function syncMergedHeader(columnIndex, value) {
  const targetRange = mergedRangeForCell(1, columnIndex)
  if (!targetRange) return
  const nextHeaders = [...localHeaders.value]
  for (let currentColumn = Number(targetRange.startColumn) - 1; currentColumn < Number(targetRange.endColumn); currentColumn += 1) {
    nextHeaders[currentColumn] = value
  }
  localHeaders.value = nextHeaders
}

function syncMergedCell(rowNumber, columnIndex, value) {
  const targetRange = mergedRangeForCell(rowNumber, columnIndex)
  if (!targetRange) return
  const nextValue = String(value ?? '')
  localRows.value = localRows.value.map((row) => {
    const currentRowNumber = Number(row.rowNumber)
    if (
      !Number.isFinite(currentRowNumber) ||
      currentRowNumber < Number(targetRange.startRow) ||
      currentRowNumber > Number(targetRange.endRow)
    ) {
      return row
    }
    const nextValues = [...row.values]
    for (let currentColumn = Number(targetRange.startColumn) - 1; currentColumn < Number(targetRange.endColumn); currentColumn += 1) {
      nextValues[currentColumn] = nextValue
    }
    return {
      ...row,
      values: nextValues,
    }
  })
}

function applyWorkbookData(data = {}) {
  const expandedData = expandMergedWorkbookData(data)
  workbook.value = {
    ...data,
    headers: expandedData.headers,
    rows: expandedData.rows,
    mergedRanges: expandedData.mergedRanges,
  }
  localHeaders.value = expandedData.headers.length > 0 ? [...expandedData.headers] : ['']
  localRows.value = expandedData.rows.map((row) => buildEditableRow(row))
  syncRowSizes()
  lastSavedSignature.value = buildCurrentSignature()
  hasPendingRowStructureChanges.value = false
}

function syncRowSizes() {
  const width = Math.max(localHeaders.value.length, 1)
  localRows.value = localRows.value.map((row) => ({
    ...row,
    values: normalizeRowValues(row.values, width),
  }))
}

function replaceMergedRanges(nextMergedRanges) {
  workbook.value = {
    ...workbook.value,
    mergedRanges: Array.isArray(nextMergedRanges) ? nextMergedRanges : [],
  }
}

function replaceLocalRows(nextRows) {
  localRows.value = (Array.isArray(nextRows) ? nextRows : []).map((row) => buildEditableRow(row))
  syncRowSizes()
}

function markPendingRowStructureChange(message) {
  hasPendingRowStructureChanges.value = true
  loadError.value = ''
  statusTone.value = 'warning'
  statusMessage.value = message
  selectedIssueId.value = ''
  emit('log', message, 'warning')
}

async function applyRowOperation(result, message, focusRowNumber) {
  replaceLocalRows(result?.rows || [])
  replaceMergedRanges(result?.mergedRanges || [])
  markPendingRowStructureChange(message)
  await nextTick()
  const targetRow = focusRowNumber ? findRowByNumber(focusRowNumber) : null
  if (targetRow) {
    await focusTarget(resolveRowFactorFieldTargetId(targetRow))
    return
  }
  await focusTarget('toolbar-anchor')
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

function isLongTextColumn(header) {
  const value = String(header || '')
  return value.includes('说明') || value.includes('规则')
}

async function addRow(afterRowNumber = null) {
  if (loading.value || saving.value) return
  const result = insertWorkbookRow({
    rows: localRows.value,
    headers: localHeaders.value,
    mergedRanges: mergedRanges.value,
    sourceRowNumber: afterRowNumber,
    mode: 'blank',
    createRow: (row) => buildEditableRow(row),
  })
  const message = afterRowNumber
    ? `已在第 ${afterRowNumber} 行后新增空白行，请保存后重新校验。`
    : '已在末尾新增空白行，请保存后重新校验。'
  await applyRowOperation(result, message, result?.insertedRowNumber)
}

async function copyRow(rowNumber) {
  if (loading.value || saving.value) return
  const result = insertWorkbookRow({
    rows: localRows.value,
    headers: localHeaders.value,
    mergedRanges: mergedRanges.value,
    sourceRowNumber: rowNumber,
    mode: 'copy',
    createRow: (row) => buildEditableRow(row),
  })
  await applyRowOperation(result, `已复制第 ${rowNumber} 行，请保存后重新校验。`, result?.insertedRowNumber)
}

async function deleteRow(rowNumber) {
  if (loading.value || saving.value) return
  if (typeof window !== 'undefined') {
    const confirmed = window.confirm(`确认删除第 ${rowNumber} 行吗？`)
    if (!confirmed) return
  }
  const result = deleteWorkbookRow({
    rows: localRows.value,
    mergedRanges: mergedRanges.value,
    rowNumber,
  })
  if (!result?.deleted) return
  await applyRowOperation(result, `已删除第 ${rowNumber} 行，请保存后重新校验。`, result?.focusRowNumber)
}

function issueCategory(issue) {
  if (issue.code === 'invalid_placeholder' && issue.token && !String(issue.token).includes('-')) {
    return 'settings'
  }
  if (issue.code === 'missing_required_column') {
    return 'structure'
  }
  if (WORKSPACE_ONLY_CODES.has(issue.code)) {
    return 'workspace'
  }
  return 'workbook'
}

function issueTag(issue) {
  if (issueCategory(issue) === 'structure') return '结构处理'
  if (issueCategory(issue) === 'workspace') return '目录处理'
  if (issueCategory(issue) === 'settings') return '设置处理'
  return '在线修复'
}

function issueToneClass(issue) {
  if (issueCategory(issue) === 'structure') return 'bg-amber-50 text-amber-700'
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
  if (hasPendingRowStructureChanges.value) {
    statusTone.value = 'warning'
    statusMessage.value = '已调整行结构，当前问题定位仍基于上一次校验结果；保存后会刷新为最新行号。'
  }
  await focusTarget(resolveIssueTargetId(issue))
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
      mergedRanges: mergedRanges.value,
      rows: localRows.value.map((row) => ({ rowNumber: row.rowNumber, values: row.values })),
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
      if (filteredIssueList.value.length > 0) {
        await focusIssue(filteredIssueList.value[0])
      } else if (issueList.value.length > 0) {
        searchKeyword.value = ''
        await nextTick()
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
