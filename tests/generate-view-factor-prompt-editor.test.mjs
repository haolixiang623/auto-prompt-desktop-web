import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const filePath = path.resolve('src/views/GenerateView.vue')

test('GenerateView Step 2 is centered on per-factor prompt editing', () => {
  const source = fs.readFileSync(filePath, 'utf8')

  assert.match(source, /要素提示词/, 'Step 2 should surface a factor-prompt editing section')
  assert.match(source, /factor_prompt/, 'field editors should bind to factor-level prompts')
  assert.match(source, /提示词库|AI生成|人工修改/, 'factor rows should expose a source badge')
  assert.equal(
    source.includes('提示词内容'),
    false,
    'the old full-prompt editor should no longer be the primary Step 2 label',
  )
})
