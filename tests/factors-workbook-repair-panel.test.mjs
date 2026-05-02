import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const componentPath = path.resolve('src/components/FactorsWorkbookRepairPanel.vue')
const statusBarPath = path.resolve('src/components/WorkspaceValidationStatusBar.vue')
const generateViewPath = path.resolve('src/views/GenerateView.vue')
const classifyViewPath = path.resolve('src/views/ClassifyView.vue')
const reviewRuleViewPath = path.resolve('src/views/ReviewRuleView.vue')

test('FactorsWorkbookRepairPanel becomes a full-screen repair desk instead of an inline page block', () => {
  const source = fs.readFileSync(componentPath, 'utf8')

  assert.match(source, /工作区校验与修复台/, 'repair panel should present a dedicated repair workspace title')
  assert.match(source, /fixed inset-0/, 'repair panel should render as a full-screen overlay instead of stretching the page')
  assert.match(source, /返回业务页继续/, 'repair panel should let the user leave the repair workspace and continue the original task')
  assert.match(source, /问题导航/, 'repair panel should surface a focused issue navigator')
  assert.match(source, /下载修复后的 factors\.xlsx/, 'repair panel should expose a repaired workbook download action')
  assert.match(source, /保存并重新校验/, 'repair panel should save workbook edits and immediately re-run validation')
})

test('WorkspaceValidationStatusBar exposes compact validation actions', () => {
  const source = fs.readFileSync(statusBarPath, 'utf8')

  assert.match(source, /立即校验/, 'status bar should allow running validation on demand')
  assert.match(source, /查看并修复/, 'status bar should open the dedicated repair workspace')
  assert.match(source, /下载 factors\.xlsx/, 'status bar should expose direct workbook download')
  assert.match(source, /校验通过|校验失败|未校验/, 'status bar should summarize validation state in a compact strip')
})

test('GenerateView mounts the shared validation status bar and repair desk', () => {
  const source = fs.readFileSync(generateViewPath, 'utf8')

  assert.match(source, /WorkspaceValidationStatusBar/, 'generate view should show the compact validation strip')
  assert.match(source, /FactorsWorkbookRepairPanel/, 'generate view should reuse the shared factors workbook repair panel')
  assert.equal(
    source.includes('统一工作区校验未通过'),
    false,
    'generate view should no longer inline the long validation error block inside the main page flow',
  )
})

test('ClassifyView mounts the shared validation status bar and repair desk', () => {
  const source = fs.readFileSync(classifyViewPath, 'utf8')

  assert.match(source, /WorkspaceValidationStatusBar/, 'classify view should show the compact validation strip')
  assert.match(source, /FactorsWorkbookRepairPanel/, 'classify view should reuse the shared factors workbook repair panel')
})

test('ReviewRuleView mounts the shared validation status bar and repair desk', () => {
  const source = fs.readFileSync(reviewRuleViewPath, 'utf8')

  assert.match(source, /WorkspaceValidationStatusBar/, 'review-rule view should show the compact validation strip')
  assert.match(source, /FactorsWorkbookRepairPanel/, 'review-rule view should reuse the shared factors workbook repair panel')
})
