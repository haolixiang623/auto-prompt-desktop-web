import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const filePath = path.resolve('src/views/LoginView.vue')

test('LoginView always redirects to the homepage after login', () => {
  const source = fs.readFileSync(filePath, 'utf8')

  assert.match(source, /window\.location\.replace\('\/'\)/, 'login should always redirect to the homepage')
  assert.equal(source.includes('route.query.redirect'), false, 'login should not resume unfinished pages after login')
})
