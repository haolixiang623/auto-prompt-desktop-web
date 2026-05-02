import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const classifyViewPath = path.resolve('src/views/ClassifyView.vue')
const reviewRuleViewPath = path.resolve('src/views/ReviewRuleView.vue')

test('ClassifyView validates the workspace before starting classify generation', () => {
  const source = fs.readFileSync(classifyViewPath, 'utf8')

  assert.match(source, /\/api\/classify\/validate-workdir/, 'classify generation should call the shared workspace validation endpoint first')
  assert.match(
    source,
    /validateClassifyWorkspace\(\{ openRepairOnFail: true, silentSuccess: true \}\)/,
    'classify generation should open the repair desk immediately when validation fails',
  )
  assert.match(source, /showFactorsWorkbookRepair\.value = true/, 'classify view should keep the shared repair desk as the failure recovery path')
})

test('ReviewRuleView routes validation controls through the shared status bar', () => {
  const source = fs.readFileSync(reviewRuleViewPath, 'utf8')

  assert.match(source, /WorkspaceValidationStatusBar/, 'review-rule view should render the shared validation status bar')
  assert.match(source, /:status="reviewValidationStatus"/, 'review-rule view should bind validation state into the status bar')
  assert.match(source, /runReviewRuleWorkspaceValidation/, 'review-rule view should expose an explicit validate action from the status bar')
  assert.match(source, /openFactorsWorkbookRepairDesk/, 'review-rule view should open the shared repair desk from the status bar')
  assert.match(source, /downloadFactorsWorkbook/, 'review-rule view should allow downloading factors.xlsx from the status bar')
})
