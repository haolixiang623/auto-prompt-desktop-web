import { apiClient } from './apiClient.js'
import { emitEvent } from './eventBus.js'

const WORKSPACE_REGISTRY_KEY = 'auto-prompt.workspace-registry'
const INPUT_CANCEL_POLL_MS = 250
const INPUT_CANCEL_MAX_WAIT_MS = 10000
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

function normalizePickedFiles(files = []) {
  return files.map((file) => ({
    file,
    relativePath: file.webkitRelativePath || file.name
  }))
}

function normalizeUploadEntries(files = []) {
  return files.map((entry) => {
    if (entry?.file && entry?.relativePath) return entry
    return {
      file: entry,
      relativePath: entry?.webkitRelativePath || entry?.name || 'upload.bin'
    }
  })
}

async function pickDirectoryWithFsAccess() {
  if (typeof window === 'undefined' || typeof window.showDirectoryPicker !== 'function') {
    return null
  }

  const rootHandle = await window.showDirectoryPicker()
  const pickedFiles = []

  async function walkDirectory(handle, prefix = '') {
    for await (const entry of handle.values()) {
      const relativePath = prefix ? `${prefix}/${entry.name}` : entry.name
      if (entry.kind === 'file') {
        const file = await entry.getFile()
        pickedFiles.push({
          file,
          relativePath: `${rootHandle.name}/${relativePath}`
        })
        continue
      }

      if (entry.kind === 'directory') {
        await walkDirectory(entry, relativePath)
      }
    }
  }

  await walkDirectory(rootHandle)
  return pickedFiles
}

function pickFilesWithInput({ directory = false, multiple = false, filters = [] } = {}) {
  return new Promise((resolve, reject) => {
    const input = document.createElement('input')
    let settled = false
    let cancelTimer = null

    const cleanup = () => {
      window.removeEventListener('focus', handleWindowFocus)
      if (cancelTimer) {
        window.clearTimeout(cancelTimer)
        cancelTimer = null
      }
      input.remove()
    }

    const finish = (files) => {
      if (settled) return
      settled = true
      cleanup()
      resolve(normalizePickedFiles(files))
    }

    const pollForSelectionOrCancel = (elapsedMs = 0) => {
      cancelTimer = window.setTimeout(() => {
        if (settled) return

        const files = Array.from(input.files || [])
        if (files.length) {
          finish(files)
          return
        }

        if (elapsedMs >= INPUT_CANCEL_MAX_WAIT_MS) {
          finish([])
          return
        }

        pollForSelectionOrCancel(elapsedMs + INPUT_CANCEL_POLL_MS)
      }, INPUT_CANCEL_POLL_MS)
    }

    const handleWindowFocus = () => {
      pollForSelectionOrCancel()
    }

    input.type = 'file'
    input.multiple = multiple || directory
    input.accept = filtersToAccept(filters)
    input.style.position = 'fixed'
    input.style.left = '-9999px'
    input.style.top = '0'
    input.style.opacity = '0'
    input.style.pointerEvents = 'none'

    if (directory) {
      input.setAttribute('webkitdirectory', '')
      input.setAttribute('directory', '')
      if ('webkitdirectory' in input) {
        input.webkitdirectory = true
      }
    }

    input.addEventListener('change', () => {
      finish(Array.from(input.files || []))
    }, { once: true })

    input.addEventListener('cancel', () => {
      finish([])
    }, { once: true })

    window.addEventListener('focus', handleWindowFocus, { once: true })
    document.body.appendChild(input)

    try {
      if (typeof input.showPicker === 'function') {
        input.showPicker()
      } else {
        input.click()
      }
    } catch (error) {
      cleanup()
      reject(error)
    }
  })
}

async function pickFiles(options = {}) {
  const { directory = false } = options

  if (directory) {
    try {
      const directoryFiles = await pickDirectoryWithFsAccess()
      if (directoryFiles) return directoryFiles
    } catch (error) {
      if (error?.name !== 'AbortError') {
        console.warn('showDirectoryPicker failed, falling back to input upload', error)
      } else {
        return []
      }
    }
  }

  return pickFilesWithInput(options)
}

function buildManifest(files) {
  return normalizeUploadEntries(files).map((entry) => ({
    relativePath: entry.relativePath
  }))
}

async function uploadFiles(path, files, extraFields = {}) {
  if (!files.length) return null
  const entries = normalizeUploadEntries(files)

  const formData = new FormData()
  Object.entries(extraFields).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      formData.append(key, value)
    }
  })

  formData.append('manifest', JSON.stringify(buildManifest(entries)))
  entries.forEach((entry) => {
    formData.append('files', entry.file, entry.file.name)
  })

  return apiClient.upload(path, formData)
}

export async function selectWorkspace() {
  const files = await pickFiles({ directory: true })
  if (!files.length) return null

  const result = await uploadFiles('/api/workspaces', files, {
    name: files[0]?.relativePath?.split('/')[0] || 'workspace'
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
