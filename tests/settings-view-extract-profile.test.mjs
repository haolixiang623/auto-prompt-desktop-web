import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const filePath = path.resolve('src/views/SettingsView.vue')

test('SettingsView exposes extract profile controls', () => {
  const source = fs.readFileSync(filePath, 'utf8')

  assert.match(source, /extract_profiles|extractProfiles/, 'settings view should load and persist extract profiles')
  assert.match(source, /default_extract_profile_id|defaultExtractProfileId/, 'settings view should track the default extract profile id')
  assert.match(source, /未命中规则|提取规则配置|提取 Profile/, 'settings view should render extract profile editing controls')
  assert.match(source, /review_rule_builtin_variables|reviewRuleBuiltinVariables/, 'settings view should expose review-rule builtin variable controls')
})
