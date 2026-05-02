import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const filePath = path.resolve('src/views/ReviewRuleView.vue')

test('ReviewRuleView validates the workspace before starting review-rule generation', () => {
  const source = fs.readFileSync(filePath, 'utf8')

  assert.match(source, /\/api\/review-rule\/validate-workspace/, 'review-rule generation should call the workspace validation endpoint first')
  assert.match(source, /审查要点名称|审查要点规则说明/, 'the UI should mention the required review-rule columns')
})
