import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const reviewRuleViewPath = path.resolve('src/views/ReviewRuleView.vue')
const generateViewPath = path.resolve('src/views/GenerateView.vue')

test('ReviewRuleView exposes a stop action for running generation tasks', () => {
  const source = fs.readFileSync(reviewRuleViewPath, 'utf8')

  assert.match(source, /停止生成/, 'review-rule generation should provide a visible stop action')
  assert.match(source, /cancelReviewRuleGeneration|stopReviewRuleGeneration/, 'review-rule view should wire a dedicated stop handler')
  assert.match(source, /currentTaskId|runningTaskId/, 'review-rule view should track the running task id for cancellation')
})

test('GenerateView exposes a stop action for batch prompt generation', () => {
  const source = fs.readFileSync(generateViewPath, 'utf8')

  assert.match(source, /停止生成/, 'prompt generation should provide a visible stop action')
  assert.match(source, /cancelBatchGeneration|stopBatchGeneration/, 'generate view should wire a dedicated stop handler')
  assert.match(source, /startTask\(\s*'generate'/, 'generate view should use cancellable backend tasks for prompt generation')
})
