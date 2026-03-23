import { apiClient } from './apiClient.js'
import { emitEvent } from './eventBus.js'

const POLL_INTERVAL_MS = 1000

export function diffTaskLogs(offset, logs) {
  const safeOffset = Math.max(0, Math.min(offset, logs.length))
  return {
    nextOffset: logs.length,
    lines: logs.slice(safeOffset)
  }
}

export function unwrapTaskResult(task) {
  if (task.status === 'failed') {
    throw new Error(task.error || 'Task failed')
  }
  return task.result
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function waitForTask(taskId, eventName = 'skill-log') {
  let offset = 0

  while (true) {
    const [task, logPayload] = await Promise.all([
      apiClient.get(`/api/task-runs/${taskId}`),
      apiClient.get(`/api/task-runs/${taskId}/logs`)
    ])

    const diff = diffTaskLogs(offset, logPayload.logs || [])
    offset = diff.nextOffset
    diff.lines.forEach((line) => emitEvent(eventName, line))

    if (task.status === 'succeeded' || task.status === 'failed') {
      return unwrapTaskResult(task)
    }

    await delay(POLL_INTERVAL_MS)
  }
}

export async function runTask(kind, payload, eventName = 'skill-log') {
  const task = await apiClient.post(`/api/tasks/${kind}`, payload)
  return waitForTask(task.id, eventName)
}
