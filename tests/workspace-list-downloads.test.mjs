import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const generateListPath = path.resolve('src/views/GenerateListView.vue')
const reviewRuleListPath = path.resolve('src/views/ReviewRuleListView.vue')
const workspaceListPath = path.resolve('src/views/WorkspaceListView.vue')

test('GenerateListView exposes a download action for completed workspaces', () => {
  const source = fs.readFileSync(generateListPath, 'utf8')

  assert.match(source, /:showDownload="true"/, 'generate workspace list should enable the shared download button')
  assert.match(source, /downloadLabel="下载结果ZIP"/, 'generate workspace list should use a result-zip label')
  assert.match(source, /\/api\/generate\/download-result/, 'generate workspace list should point at the generate result download endpoint')
})

test('ReviewRuleListView exposes a download action for completed workspaces', () => {
  const source = fs.readFileSync(reviewRuleListPath, 'utf8')

  assert.match(source, /:showDownload="true"/, 'review-rule workspace list should enable the shared download button')
  assert.match(source, /downloadLabel="下载结果ZIP"/, 'review-rule workspace list should use a result-zip label')
  assert.match(source, /\/api\/review-rule\/download-result/, 'review-rule workspace list should point at the review-rule result download endpoint')
})

test('WorkspaceListView only renders the download action for eligible rows', () => {
  const source = fs.readFileSync(workspaceListPath, 'utf8')

  assert.match(source, /showDownload && canDownload\(ws\)/, 'shared workspace list should gate downloads per workspace')
  assert.match(source, /canDownload: \{ type: Function/, 'shared workspace list should accept a per-row download predicate')
})
