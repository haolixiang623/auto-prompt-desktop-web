import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const generateViewPath = path.resolve('src/views/GenerateView.vue')

test('GenerateView persists workspace activity when generation starts', () => {
  const source = fs.readFileSync(generateViewPath, 'utf8')

  assert.match(source, /\/api\/workspaces\/activity/, 'generate view should persist workspace activity through the shared workspace endpoint')
  assert.match(source, /module:\s*'generate'/, 'generate view should mark the workspace as generate module')
  assert.match(source, /persistGenerateWorkspaceActivity\('generating'\)/, 'generate view should persist the generating status before batch execution')
})
