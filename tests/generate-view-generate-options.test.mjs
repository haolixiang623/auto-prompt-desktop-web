import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const filePath = path.resolve('src/views/GenerateView.vue')

test('GenerateView exposes per-run generation options for case library and extract profile', () => {
  const source = fs.readFileSync(filePath, 'utf8')

  assert.match(source, /优先使用提示词库/, 'users should be able to opt in or out of case-library reuse per run')
  assert.match(source, /ruleProfileId|selectedRuleProfileId/, 'the selected extract profile should be tracked in component state')
  assert.match(source, /useCaseLibrary/, 'generation requests should include the case-library toggle')
})
