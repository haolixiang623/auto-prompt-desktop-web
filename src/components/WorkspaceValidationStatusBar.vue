<template>
  <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
    <div class="flex flex-col gap-4 px-4 py-4 sm:px-5 lg:flex-row lg:items-center lg:justify-between">
      <div class="flex min-w-0 items-start gap-3">
        <div
          class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl border"
          :class="badgeShellClass"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.8"
              d="M9 12l2 2 4-4m5 2A9 9 0 1112 3a9 9 0 019 9z"
            />
          </svg>
        </div>
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <p class="text-sm font-semibold text-slate-900">工作区校验</p>
            <span
              class="rounded-full px-2.5 py-1 text-[11px] font-semibold"
              :class="badgeClass"
            >
              {{ statusLabel }}
            </span>
            <span
              v-if="issueCount > 0"
              class="rounded-full bg-red-50 px-2.5 py-1 text-[11px] font-semibold text-red-600"
            >
              {{ issueCount }} 个问题
            </span>
          </div>
          <p class="mt-1 text-sm leading-6 text-slate-500">
            {{ statusDescription }}
          </p>
          <p v-if="checkedAtLabel" class="mt-1 text-[11px] text-slate-400">
            最近校验：{{ checkedAtLabel }}
          </p>
        </div>
      </div>

      <div class="flex flex-wrap gap-2 lg:justify-end">
        <button
          type="button"
          class="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
          :disabled="disabled || checking"
          @click="$emit('validate')"
        >
          {{ checking ? '校验中...' : '立即校验' }}
        </button>
        <button
          type="button"
          class="rounded-xl border border-blue-200 bg-blue-50 px-3.5 py-2 text-xs font-medium text-blue-700 transition hover:bg-blue-100 disabled:opacity-50"
          :disabled="disabled"
          @click="$emit('open-repair')"
        >
          查看并修复
        </button>
        <button
          type="button"
          class="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
          :disabled="disabled"
          @click="$emit('download-workbook')"
        >
          下载 factors.xlsx
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'idle',
  },
  issueCount: {
    type: Number,
    default: 0,
  },
  checking: {
    type: Boolean,
    default: false,
  },
  checkedAt: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['validate', 'open-repair', 'download-workbook'])

const statusLabel = computed(() => {
  if (props.checking) return '校验中'
  if (props.status === 'valid') return '校验通过'
  if (props.status === 'invalid') return '校验失败'
  return '未校验'
})

const statusDescription = computed(() => {
  if (props.checking) {
    return '正在检查 factors.xlsx、材料目录与审查要点引用关系。'
  }
  if (props.status === 'valid') {
    return '当前工作区结构完整，可以继续开始生成。'
  }
  if (props.status === 'invalid') {
    return props.issueCount > 0
      ? `发现 ${props.issueCount} 个问题，建议先进入修复台处理后再继续。`
      : '发现工作区问题，建议先进入修复台处理后再继续。'
  }
  return '开始任务前建议先执行一次校验，确认工作区结构与 factors.xlsx 可用。'
})

const badgeShellClass = computed(() => {
  if (props.checking) return 'border-blue-200 bg-blue-50 text-blue-600'
  if (props.status === 'valid') return 'border-emerald-200 bg-emerald-50 text-emerald-600'
  if (props.status === 'invalid') return 'border-red-200 bg-red-50 text-red-600'
  return 'border-slate-200 bg-slate-50 text-slate-500'
})

const badgeClass = computed(() => {
  if (props.checking) return 'bg-blue-50 text-blue-600'
  if (props.status === 'valid') return 'bg-emerald-50 text-emerald-600'
  if (props.status === 'invalid') return 'bg-red-50 text-red-600'
  return 'bg-slate-100 text-slate-500'
})

const checkedAtLabel = computed(() => {
  if (!props.checkedAt) return ''
  const parsed = new Date(props.checkedAt)
  if (Number.isNaN(parsed.getTime())) return props.checkedAt
  return parsed.toLocaleString()
})
</script>
