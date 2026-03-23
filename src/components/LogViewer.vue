<template>
  <div class="card">
    <div class="card-header flex justify-between items-center">
      <h3 class="text-lg font-medium text-gray-900">执行日志</h3>
      <div class="flex items-center gap-2">
        <button @click="autoScroll = !autoScroll" class="text-sm text-gray-500 hover:text-gray-700">
          {{ autoScroll ? '停止滚动' : '自动滚动' }}
        </button>
        <button @click="clearLogs" class="text-sm text-gray-500 hover:text-gray-700">
          清除
        </button>
      </div>
    </div>
    <div class="card-body p-0">
      <div ref="logContainer" class="log-container max-h-96">
        <div
          v-for="(log, index) in logs"
          :key="index"
          class="log-line"
          :class="getLogClass(log.type)"
        >
          <span class="text-gray-500 mr-2">{{ formatTime(log.timestamp) }}</span>
          <span>{{ log.message }}</span>
        </div>
        <div v-if="logs.length === 0" class="text-gray-500 italic">
          等待执行...
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useSkillsStore } from '../stores/skills.js'

const props = defineProps({
  logs: {
    type: Array,
    default: () => []
  }
})

const skillsStore = useSkillsStore()
const logContainer = ref(null)
const autoScroll = ref(true)

function getLogClass(type) {
  switch (type) {
    case 'error': return 'log-error'
    case 'success': return 'log-success'
    case 'warning': return 'log-warning'
    case 'info':
    default: return 'log-info'
  }
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

function clearLogs() {
  skillsStore.clearLogs()
}

function scrollToBottom() {
  if (autoScroll.value && logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

watch(() => props.logs, () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })
</script>
