import { apiClient } from './apiClient.js'
import { emitEvent } from './eventBus.js'

const WORKSPACE_REGISTRY_KEY = 'auto-prompt.workspace-registry'
const workspaceRegistry = new Map(loadWorkspaceRegistry())
let dropBridgeReady = false

function loadWorkspaceRegistry() {
  if (typeof window === 'undefined') return []

  try {
    const raw = window.localStorage.getItem(WORKSPACE_REGISTRY_KEY)
    if (!raw) return []
    const data = JSON.parse(raw)
    return Array.isArray(data) ? data : []
  } catch (error) {
    console.warn('failed to restore workspace registry', error)
    return []
  }
}

function persistWorkspaceRegistry() {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.setItem(
      WORKSPACE_REGISTRY_KEY,
      JSON.stringify(Array.from(workspaceRegistry.entries())),
    )
  } catch (error) {
    console.warn('failed to persist workspace registry', error)
  }
}

function filtersToAccept(filters = []) {
  return filters
    .flatMap((filter) => (filter.extensions || []).map((extension) => `.${extension}`))
    .join(',')
}

function pickFiles({ directory = false, multiple = false, filters = [] } = {}) {
  return new Promise((resolve) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = multiple || directory
    input.accept = filtersToAccept(filters)
    if (directory) {
      input.setAttribute('webkitdirectory', '')
      input.setAttribute('directory', '')
    }
    input.addEventListener('change', () => {
      resolve(Array.from(input.files || []))
    }, { once: true })
    input.click()
  })
}

function buildManifest(files) {
  return files.map((file) => ({
    relativePath: file.webkitRelativePath || file.name
  }))
}

async function uploadFiles(path, files, extraFields = {}) {
  if (!files.length) return null

  const formData = new FormData()
  Object.entries(extraFields).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      formData.append(key, value)
    }
  })

  formData.append('manifest', JSON.stringify(buildManifest(files)))
  files.forEach((file) => {
    formData.append('files', file, file.name)
  })

  return apiClient.upload(path, formData)
}

export async function selectWorkspace() {
  const files = await pickFiles({ directory: true })
  if (!files.length) return null

  const result = await uploadFiles('/api/workspaces', files, {
    name: files[0]?.webkitRelativePath?.split('/')[0] || 'workspace'
  })

  if (result?.rootPath && result?.id) {
    workspaceRegistry.set(result.rootPath, result.id)
    persistWorkspaceRegistry()
  }

  return result
}

export async function selectUploadedFiles(filters = [], multiple = false) {
  const files = await pickFiles({ filters, multiple })
  if (!files.length) return multiple ? [] : null

  const result = await uploadFiles('/api/uploads', files)
  const paths = result?.paths || []
  return multiple ? paths : (paths[0] || null)
}

export async function uploadDroppedFiles(fileList) {
  const files = Array.from(fileList || [])
  if (!files.length) return []
  const result = await uploadFiles('/api/uploads', files)
  return result?.paths || []
}

export function resolveWorkspaceId(rootPath) {
  return workspaceRegistry.get(rootPath) || null
}

export function ensureWindowDropBridge() {
  if (dropBridgeReady || typeof window === 'undefined') return
  dropBridgeReady = true

  window.addEventListener('dragover', (event) => {
    if (!event.dataTransfer?.files?.length) return
    event.preventDefault()
    emitEvent('tauri://file-drop-hover', [])
  })

  window.addEventListener('dragleave', () => {
    emitEvent('tauri://file-drop-cancelled', null)
  })

  window.addEventListener('drop', async (event) => {
    if (!event.dataTransfer?.files?.length) return
    event.preventDefault()
    try {
      const paths = await uploadDroppedFiles(event.dataTransfer.files)
      emitEvent('tauri://file-drop', paths)
    } catch (error) {
      emitEvent('tauri://file-drop-cancelled', String(error))
    }
  })
}
