import test from 'node:test'
import assert from 'node:assert/strict'

import {
  applyFactorPromptEdit,
  buildPreviewPrompt,
  normalizeArtifact,
} from '../src/views/generateArtifactState.js'

test('normalizeArtifact fills defaults and preserves factor-level prompts', () => {
  const normalized = normalizeArtifact(
    {
      carriername: '营业证照',
      template: { prompt_template: 'HEAD\n$(factors)\nTAIL' },
      factors: [
        {
          name: '统一社会信用代码',
          factoruse: '企业识别',
          factor_prompt: '识别18位字母数字组合',
        },
      ],
    },
    '营业证照',
  )

  assert.equal(normalized.version, '1')
  assert.equal(normalized.carriername, '营业证照')
  assert.equal(normalized.factors[0].factorname, '统一社会信用代码')
  assert.equal(normalized.factors[0].factortype, '1')
  assert.equal(normalized.factors[0].source, 'manual_edit')
})

test('buildPreviewPrompt injects factor prompts into the template', () => {
  const preview = buildPreviewPrompt('HEAD\n$(factors)\nTAIL', [
    { factorname: '统一社会信用代码', factor_prompt: '识别18位字母数字组合' },
    { factorname: '企业名称', factor_prompt: '识别完整企业名称' },
  ])

  assert.match(preview, /HEAD/)
  assert.match(preview, /## 1\.统一社会信用代码/)
  assert.match(preview, /识别18位字母数字组合/)
  assert.match(preview, /## 2\.企业名称/)
  assert.match(preview, /TAIL/)
})

test('applyFactorPromptEdit updates the selected factor and marks the result dirty', () => {
  const current = {
    success: true,
    artifact: {
      version: '1',
      carriername: '营业证照',
      template: { prompt_template: 'HEAD\n$(factors)\nTAIL' },
      meta: {},
      factors: [
        {
          index: 1,
          factorname: '统一社会信用代码',
          factortype: '1',
          factoruse: '企业识别',
          factor_prompt: '旧规则',
          source: 'ai_generated',
        },
      ],
    },
    preview_prompt: 'old preview',
    prompt_template: 'old preview',
    dirty: false,
  }

  const next = applyFactorPromptEdit(current, 0, '新规则')

  assert.equal(next.artifact.factors[0].factor_prompt, '新规则')
  assert.equal(next.artifact.factors[0].source, 'manual_edit')
  assert.equal(next.dirty, true)
  assert.match(next.preview_prompt, /新规则/)
  assert.equal(next.prompt_template, next.preview_prompt)
})
