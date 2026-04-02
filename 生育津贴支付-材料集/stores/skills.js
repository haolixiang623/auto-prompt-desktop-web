import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { invoke } from '../tauri/tauri.js'
import { listen } from '../tauri/event.js'

export const useSkillsStore = defineStore('skills', () => {
  // State
  const isRunning = ref(false)
  const currentSkill = ref(null)
  const logs = ref([])
  const results = ref(null)
  const unlisten = ref(null)

  // Getters
  const hasResults = computed(() => results.value !== null)
  const logLines = computed(() => logs.value)

  // Actions
  async function startLogListener() {
    // Clean up previous listener if exists
    if (unlisten.value) {
      unlisten.value()
      unlisten.value = null
    }

    // Listen for log events from Rust
    unlisten.value = await listen('skill-log', (event) => {
      logs.value.push({
        timestamp: new Date().toISOString(),
        message: event.payload,
        type: getLogType(event.payload)
      })
    })
  }

  function getLogType(message) {
    if (message.includes('[ERROR]')) return 'error'
    if (message.includes('[OK]') || message.includes('成功')) return 'success'
    if (message.includes('[WARN]')) return 'warning'
    if (message.includes('[INFO]')) return 'info'
    return 'info'
  }

  function clearLogs() {
    logs.value = []
  }

  async function generatePrompt(workDir, materialName = null) {
    isRunning.value = true
    currentSkill.value = 'generate'
    results.value = null
    clearLogs()

    await startLogListener()

    try {
      const result = await invoke('generate_prompt', { workDir, materialName })
      results.value = result
      return result
    } catch (error) {
      logs.value.push({
        timestamp: new Date().toISOString(),
        message: `[ERROR] ${error}`,
        type: 'error'
      })
      throw error
    } finally {
      isRunning.value = false
      if (unlisten.value) {
        unlisten.value()
        unlisten.value = null
      }
    }
  }

  async function classifyMaterials(workDir, maxRounds) {
    isRunning.value = true
    currentSkill.value = 'classify'
    results.value = null
    clearLogs()

    await startLogListener()

    try {
      const result = await invoke('classify_materials', { workDir, maxRounds })
      results.value = result
      return result
    } catch (error) {
      logs.value.push({
        timestamp: new Date().toISOString(),
        message: `[ERROR] ${error}`,
        type: 'error'
      })
      throw error
    } finally {
      isRunning.value = false
      if (unlisten.value) {
        unlisten.value()
        unlisten.value = null
      }
    }
  }

  async function importCases(sourceDir = null) {
    isRunning.value = true
    currentSkill.value = 'import'
    results.value = null
    clearLogs()

    await startLogListener()

    try {
      const result = await invoke('import_cases', { sourceDir })
      results.value = result
      return result
    } catch (error) {
      logs.value.push({
        timestamp: new Date().toISOString(),
        message: `[ERROR] ${error}`,
        type: 'error'
      })
      throw error
    } finally {
      isRunning.value = false
      if (unlisten.value) {
        unlisten.value()
        unlisten.value = null
      }
    }
  }

  return {
    // State
    isRunning,
    currentSkill,
    logs,
    results,
    // Getters
    hasResults,
    logLines,
    // Actions
    generatePrompt,
    classifyMaterials,
    importCases,
    clearLogs
  }
})
