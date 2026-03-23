import test from 'node:test'
import assert from 'node:assert/strict'

import { diffTaskLogs, unwrapTaskResult } from '../src/services/taskService.js'

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
