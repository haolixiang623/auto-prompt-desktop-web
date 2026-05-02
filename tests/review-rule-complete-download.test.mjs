import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const filePath = path.resolve('src/views/ReviewRuleView.vue')

test('ReviewRuleView auto-downloads reviewed JSON outputs when review is completed', () => {
  const source = fs.readFileSync(filePath, 'utf8')

  assert.match(source, /async function completeReview/, 'completeReview should handle async save and download flow')
  assert.match(source, /downloadReviewedJsons|triggerReviewedJsonDownload/, 'review completion should delegate to a download helper')
  assert.match(source, /\/api\/files\/download-batch/, 'review completion should trigger batch JSON download')
})
