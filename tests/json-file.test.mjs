import test from 'node:test'
import assert from 'node:assert/strict'

import { parseJsonFilePayload } from '../src/services/jsonFile.js'

test('parseJsonFilePayload parses string payloads from legacy read_json_file responses', () => {
  assert.deepEqual(
    parseJsonFilePayload('{"keypoints":[{"kpname":"姓名"}]}'),
    { keypoints: [{ kpname: '姓名' }] },
  )
})

test('parseJsonFilePayload returns object payloads from current read_json_file responses', () => {
  const payload = { keypoints: [{ kpname: '姓名' }] }
  assert.equal(parseJsonFilePayload(payload), payload)
})
