import test from 'node:test'
import assert from 'node:assert/strict'

function createStorageMock() {
  const store = new Map()
  return {
    getItem(key) {
      return store.has(key) ? store.get(key) : null
    },
    setItem(key, value) {
      store.set(key, String(value))
    },
    removeItem(key) {
      store.delete(key)
    },
    clear() {
      store.clear()
    },
  }
}

function installWindow() {
  const localStorage = createStorageMock()
  const sessionStorage = createStorageMock()
  globalThis.window = {
    localStorage,
    sessionStorage,
  }
  return { localStorage, sessionStorage }
}

function cleanupWindow() {
  delete globalThis.window
}

async function loadAuthStateModule() {
  return import(`../src/services/authState.js?test=${Date.now()}-${Math.random()}`)
}

test('setAuthSession stores remembered login in localStorage with an expiry', async () => {
  const { localStorage, sessionStorage } = installWindow()
  const auth = await loadAuthStateModule()

  auth.setAuthSession(
    {
      token: 'remember-token',
      expiresAt: '2030-01-01T00:00:00',
      user: { id: 'user-1', username: 'alice', role: 'user' },
    },
    { rememberMe: true },
  )

  assert.equal(localStorage.getItem('auto-prompt.auth-token'), 'remember-token')
  assert.equal(localStorage.getItem('auto-prompt.auth-expiry'), '2030-01-01T00:00:00')
  assert.equal(sessionStorage.getItem('auto-prompt.auth-token'), null)

  cleanupWindow()
})

test('setAuthSession stores non-remembered login in sessionStorage only', async () => {
  const { localStorage, sessionStorage } = installWindow()
  const auth = await loadAuthStateModule()

  auth.setAuthSession(
    {
      token: 'session-token',
      expiresAt: '2030-01-01T00:00:00',
      user: { id: 'user-1', username: 'alice', role: 'user' },
    },
    { rememberMe: false },
  )

  assert.equal(sessionStorage.getItem('auto-prompt.auth-token'), 'session-token')
  assert.equal(localStorage.getItem('auto-prompt.auth-token'), null)

  cleanupWindow()
})

test('remembered username expires after one day', async () => {
  const { localStorage } = installWindow()
  const auth = await loadAuthStateModule()
  const originalNow = Date.now
  const start = 1_700_000_000_000
  Date.now = () => start

  auth.setRememberedUsername('alice')
  assert.equal(auth.getRememberedUsername(), 'alice')

  Date.now = () => start + (24 * 60 * 60 * 1000) + 1
  assert.equal(auth.getRememberedUsername(), '')
  assert.equal(localStorage.getItem('auto-prompt.remembered-username'), null)

  Date.now = originalNow
  cleanupWindow()
})
