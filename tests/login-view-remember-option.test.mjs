import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const filePath = path.resolve('src/views/LoginView.vue')

test('LoginView merges remember options into a single checkbox', () => {
  const source = fs.readFileSync(filePath, 'utf8')

  assert.match(source, /保持登录状态/, 'login page should expose one merged remember option')
  assert.equal(source.includes('记住账号 1 天'), false, 'legacy remembered-username checkbox should be removed')
  assert.equal(source.includes('记住登录 1 天'), false, 'legacy remember-login checkbox should be removed')
  assert.equal(source.includes('rememberUsername'), false, 'component state should use a single remember flag')
})
