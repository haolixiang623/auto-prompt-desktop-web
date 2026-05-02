import test from 'node:test'
import assert from 'node:assert/strict'

import { TaskCancelledError, diffTaskLogs, unwrapTaskResult } from '../src/services/taskService.js'
import { getApiKeySaveState } from '../src/views/settingsState.js'

test('diffTaskLogs returns only unseen lines from the latest offset', () => {
  const first = diffTaskLogs(0, ['a', 'b'])
  assert.deepEqual(first, { nextOffset: 2, lines: ['a', 'b'] })

  const second = diffTaskLogs(first.nextOffset, ['a', 'b', 'c'])
  assert.deepEqual(second, { nextOffset: 3, lines: ['c'] })
})

test('unwrapTaskResult throws the backend error for failed tasks', () => {
  assert.throws(
    () => unwrapTaskResult({ status: 'failed', error: 'boom', result: null }),
    /boom/,
  )
})

test('unwrapTaskResult returns the payload for succeeded tasks', () => {
  const payload = { ok: true }
  assert.deepEqual(
    unwrapTaskResult({ status: 'succeeded', error: null, result: payload }),
    payload,
  )
})

test('unwrapTaskResult throws TaskCancelledError for cancelled tasks', () => {
  assert.throws(
    () => unwrapTaskResult({ status: 'cancelled', error: '已停止生成', result: null }),
    (error) => error instanceof TaskCancelledError && /已停止生成/.test(error.message),
  )
})

test('getApiKeySaveState marks autofilled but unsaved keys as warning', () => {
  assert.deepEqual(
    getApiKeySaveState({
      apiKey: 'sk-autofilled',
      savedApiKey: '',
      apiKeyConfigured: false,
    }),
    {
      tone: 'warning',
      label: '未保存',
      message: '检测到当前输入框已有内容，但服务端尚未保存，请点击“保存设置”。'
    },
  )
})

test('getApiKeySaveState reports success only when backend configuration is saved', () => {
  assert.deepEqual(
    getApiKeySaveState({
      apiKey: 'sk-saved',
      savedApiKey: 'sk-saved',
      apiKeyConfigured: true,
    }),
    {
      tone: 'success',
      label: '已配置',
      message: '服务端已保存 API Key，可直接用于生成提示词。'
    },
  )
})
